/* sgcrypt.h - AES-128 (CTR), SHA-256 and X25519 for the game folder's DLLs (2026-11-02, user 13:56 "1/2/3都要加密").
 * Used by ddraw.dll (ddraw_proxy.c: the encrypted .dat files and the encrypted connection) and SGRender.dll (SGHud.pak).
 * Self-contained C (no Windows crypto API: the same code on every Windows / wine).  Checked against Python's
 * cryptography package (tools/sgcrypt_selftest.c, run by tools/mptest/test120.py).
 *   AES: FIPS-197, encryption only (CTR needs no decryption), T-tables built from the S-box at first use.
 *   CTR block = nonce (8 bytes) || block index (8 bytes, big-endian) - the same as Python's CTR(nonce + 8 x 00)
 *   started at block 0; sgc_ctr_xor() works at any byte offset (random-access reads of a file).
 *   X25519: TweetNaCl crypto_scalarmult (public domain).  SHA-256: FIPS 180-4. */
#ifndef SGCRYPT_H
#define SGCRYPT_H
#include <stdint.h>
#include <string.h>
#include <stdlib.h>

/* ---- AES-128 ---------------------------------------------------------------------------------------------------- */
static const uint8_t SGC_SBOX[256] = {
    0x63,0x7c,0x77,0x7b,0xf2,0x6b,0x6f,0xc5,0x30,0x01,0x67,0x2b,0xfe,0xd7,0xab,0x76,
    0xca,0x82,0xc9,0x7d,0xfa,0x59,0x47,0xf0,0xad,0xd4,0xa2,0xaf,0x9c,0xa4,0x72,0xc0,
    0xb7,0xfd,0x93,0x26,0x36,0x3f,0xf7,0xcc,0x34,0xa5,0xe5,0xf1,0x71,0xd8,0x31,0x15,
    0x04,0xc7,0x23,0xc3,0x18,0x96,0x05,0x9a,0x07,0x12,0x80,0xe2,0xeb,0x27,0xb2,0x75,
    0x09,0x83,0x2c,0x1a,0x1b,0x6e,0x5a,0xa0,0x52,0x3b,0xd6,0xb3,0x29,0xe3,0x2f,0x84,
    0x53,0xd1,0x00,0xed,0x20,0xfc,0xb1,0x5b,0x6a,0xcb,0xbe,0x39,0x4a,0x4c,0x58,0xcf,
    0xd0,0xef,0xaa,0xfb,0x43,0x4d,0x33,0x85,0x45,0xf9,0x02,0x7f,0x50,0x3c,0x9f,0xa8,
    0x51,0xa3,0x40,0x8f,0x92,0x9d,0x38,0xf5,0xbc,0xb6,0xda,0x21,0x10,0xff,0xf3,0xd2,
    0xcd,0x0c,0x13,0xec,0x5f,0x97,0x44,0x17,0xc4,0xa7,0x7e,0x3d,0x64,0x5d,0x19,0x73,
    0x60,0x81,0x4f,0xdc,0x22,0x2a,0x90,0x88,0x46,0xee,0xb8,0x14,0xde,0x5e,0x0b,0xdb,
    0xe0,0x32,0x3a,0x0a,0x49,0x06,0x24,0x5c,0xc2,0xd3,0xac,0x62,0x91,0x95,0xe4,0x79,
    0xe7,0xc8,0x37,0x6d,0x8d,0xd5,0x4e,0xa9,0x6c,0x56,0xf4,0xea,0x65,0x7a,0xae,0x08,
    0xba,0x78,0x25,0x2e,0x1c,0xa6,0xb4,0xc6,0xe8,0xdd,0x74,0x1f,0x4b,0xbd,0x8b,0x8a,
    0x70,0x3e,0xb5,0x66,0x48,0x03,0xf6,0x0e,0x61,0x35,0x57,0xb9,0x86,0xc1,0x1d,0x9e,
    0xe1,0xf8,0x98,0x11,0x69,0xd9,0x8e,0x94,0x9b,0x1e,0x87,0xe9,0xce,0x55,0x28,0xdf,
    0x8c,0xa1,0x89,0x0d,0xbf,0xe6,0x42,0x68,0x41,0x99,0x2d,0x0f,0xb0,0x54,0xbb,0x16 };
static uint32_t sgc_T[4][256];
static int sgc_T_ready;
static void sgc_tables(void)
{
    if (sgc_T_ready) return;
    for (int i = 0; i < 256; i++) {
        uint32_t s = SGC_SBOX[i], s2 = (s << 1) ^ ((s & 0x80) ? 0x11b : 0), s3 = s2 ^ s;
        uint32_t t = (s2 << 24) | (s << 16) | (s << 8) | s3;          /* column (2s, s, s, 3s), big-endian bytes */
        sgc_T[0][i] = t;
        sgc_T[1][i] = (t >> 8) | (t << 24);
        sgc_T[2][i] = (t >> 16) | (t << 16);
        sgc_T[3][i] = (t >> 24) | (t << 8);
    }
    sgc_T_ready = 1;
}
typedef struct { uint32_t rk[44]; } SgcAes;
static uint32_t sgc_be32(const uint8_t *p) { return (uint32_t)p[0] << 24 | (uint32_t)p[1] << 16 | (uint32_t)p[2] << 8 | p[3]; }
static void sgc_put32(uint8_t *p, uint32_t v) { p[0] = (uint8_t)(v >> 24); p[1] = (uint8_t)(v >> 16); p[2] = (uint8_t)(v >> 8); p[3] = (uint8_t)v; }
static void sgc_aes_init(SgcAes *a, const uint8_t key[16])
{
    static const uint8_t rcon[10] = { 1, 2, 4, 8, 16, 32, 64, 128, 0x1b, 0x36 };
    sgc_tables();
    for (int i = 0; i < 4; i++) a->rk[i] = sgc_be32(key + 4 * i);
    for (int i = 4; i < 44; i++) {
        uint32_t t = a->rk[i - 1];
        if (i % 4 == 0)
            t = ((uint32_t)SGC_SBOX[(t >> 16) & 255] << 24 | (uint32_t)SGC_SBOX[(t >> 8) & 255] << 16
                 | (uint32_t)SGC_SBOX[t & 255] << 8 | SGC_SBOX[t >> 24]) ^ ((uint32_t)rcon[i / 4 - 1] << 24);
        a->rk[i] = a->rk[i - 4] ^ t;
    }
}
static void sgc_aes_block(const SgcAes *a, const uint8_t in[16], uint8_t out[16])
{
    const uint32_t *rk = a->rk;
    uint32_t s0 = sgc_be32(in) ^ rk[0], s1 = sgc_be32(in + 4) ^ rk[1], s2 = sgc_be32(in + 8) ^ rk[2], s3 = sgc_be32(in + 12) ^ rk[3];
    for (int r = 1; r < 10; r++) {
        rk += 4;
        uint32_t t0 = sgc_T[0][s0 >> 24] ^ sgc_T[1][(s1 >> 16) & 255] ^ sgc_T[2][(s2 >> 8) & 255] ^ sgc_T[3][s3 & 255] ^ rk[0];
        uint32_t t1 = sgc_T[0][s1 >> 24] ^ sgc_T[1][(s2 >> 16) & 255] ^ sgc_T[2][(s3 >> 8) & 255] ^ sgc_T[3][s0 & 255] ^ rk[1];
        uint32_t t2 = sgc_T[0][s2 >> 24] ^ sgc_T[1][(s3 >> 16) & 255] ^ sgc_T[2][(s0 >> 8) & 255] ^ sgc_T[3][s1 & 255] ^ rk[2];
        uint32_t t3 = sgc_T[0][s3 >> 24] ^ sgc_T[1][(s0 >> 16) & 255] ^ sgc_T[2][(s1 >> 8) & 255] ^ sgc_T[3][s2 & 255] ^ rk[3];
        s0 = t0; s1 = t1; s2 = t2; s3 = t3;
    }
    rk += 4;
#define SGC_F(a_, b_, c_, d_) ((uint32_t)SGC_SBOX[(a_) >> 24] << 24 | (uint32_t)SGC_SBOX[((b_) >> 16) & 255] << 16 \
                             | (uint32_t)SGC_SBOX[((c_) >> 8) & 255] << 8 | SGC_SBOX[(d_) & 255])
    sgc_put32(out, SGC_F(s0, s1, s2, s3) ^ rk[0]);
    sgc_put32(out + 4, SGC_F(s1, s2, s3, s0) ^ rk[1]);
    sgc_put32(out + 8, SGC_F(s2, s3, s0, s1) ^ rk[2]);
    sgc_put32(out + 12, SGC_F(s3, s0, s1, s2) ^ rk[3]);
#undef SGC_F
}
/* CTR: xor buf (len bytes) with the key stream at byte offset off; counter block = nonce || be64(off / 16) */
static void sgc_ctr_xor(const SgcAes *a, const uint8_t nonce[8], uint64_t off, uint8_t *buf, size_t len)
{
    uint8_t cb[16], ks[16];
    memcpy(cb, nonce, 8);
    uint64_t blk = off >> 4;
    size_t skip = (size_t)(off & 15), i = 0;
    while (i < len) {
        for (int k = 0; k < 8; k++) cb[8 + k] = (uint8_t)(blk >> (56 - 8 * k));
        sgc_aes_block(a, cb, ks);
        size_t n = 16 - skip; if (n > len - i) n = len - i;
        for (size_t k = 0; k < n; k++) buf[i + k] ^= ks[skip + k];
        i += n; skip = 0; blk++;
    }
}

/* ---- SHA-256 ---------------------------------------------------------------------------------------------------- */
typedef struct { uint32_t h[8]; uint8_t b[64]; uint64_t n; } SgcSha;
static const uint32_t SGC_K[64] = {
    0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,
    0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,
    0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,
    0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
    0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,
    0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,
    0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2 };
#define SGC_ROR(x, n) (((x) >> (n)) | ((x) << (32 - (n))))
static void sgc_sha_blk(SgcSha *s, const uint8_t *p)
{
    uint32_t w[64], a, b, c, d, e, f, g, h;
    for (int i = 0; i < 16; i++) w[i] = sgc_be32(p + 4 * i);
    for (int i = 16; i < 64; i++) {
        uint32_t s0 = SGC_ROR(w[i - 15], 7) ^ SGC_ROR(w[i - 15], 18) ^ (w[i - 15] >> 3);
        uint32_t s1 = SGC_ROR(w[i - 2], 17) ^ SGC_ROR(w[i - 2], 19) ^ (w[i - 2] >> 10);
        w[i] = w[i - 16] + s0 + w[i - 7] + s1;
    }
    a = s->h[0]; b = s->h[1]; c = s->h[2]; d = s->h[3]; e = s->h[4]; f = s->h[5]; g = s->h[6]; h = s->h[7];
    for (int i = 0; i < 64; i++) {
        uint32_t t1 = h + (SGC_ROR(e, 6) ^ SGC_ROR(e, 11) ^ SGC_ROR(e, 25)) + ((e & f) ^ (~e & g)) + SGC_K[i] + w[i];
        uint32_t t2 = (SGC_ROR(a, 2) ^ SGC_ROR(a, 13) ^ SGC_ROR(a, 22)) + ((a & b) ^ (a & c) ^ (b & c));
        h = g; g = f; f = e; e = d + t1; d = c; c = b; b = a; a = t1 + t2;
    }
    s->h[0] += a; s->h[1] += b; s->h[2] += c; s->h[3] += d; s->h[4] += e; s->h[5] += f; s->h[6] += g; s->h[7] += h;
}
static void sgc_sha_init(SgcSha *s)
{
    static const uint32_t iv[8] = { 0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19 };
    memcpy(s->h, iv, sizeof iv); s->n = 0;
}
static void sgc_sha_add(SgcSha *s, const void *data, size_t len)
{
    const uint8_t *p = (const uint8_t *)data;
    while (len) {
        size_t o = (size_t)(s->n & 63), n = 64 - o; if (n > len) n = len;
        memcpy(s->b + o, p, n); s->n += n; p += n; len -= n;
        if ((s->n & 63) == 0) sgc_sha_blk(s, s->b);
    }
}
static void sgc_sha_end(SgcSha *s, uint8_t out[32])
{
    uint64_t bits = s->n * 8;
    uint8_t pad = 0x80, z = 0, lb[8];
    sgc_sha_add(s, &pad, 1);
    while ((s->n & 63) != 56) sgc_sha_add(s, &z, 1);
    for (int i = 0; i < 8; i++) lb[i] = (uint8_t)(bits >> (56 - 8 * i));
    sgc_sha_add(s, lb, 8);
    for (int i = 0; i < 8; i++) sgc_put32(out + 4 * i, s->h[i]);
}

/* ---- X25519 (TweetNaCl, public domain) -------------------------------------------------------------------------- */
typedef int64_t sgc_gf[16];
static void sgc_car(sgc_gf o)
{
    for (int i = 0; i < 16; i++) {
        o[i] += (int64_t)1 << 16;
        int64_t c = o[i] >> 16;
        o[(i + 1) * (i < 15)] += c - 1 + 37 * (c - 1) * (i == 15);
        o[i] -= c * ((int64_t)1 << 16);
    }
}
static void sgc_sel(sgc_gf p, sgc_gf q, int b)
{
    int64_t c = ~(int64_t)(b - 1);
    for (int i = 0; i < 16; i++) { int64_t t = c & (p[i] ^ q[i]); p[i] ^= t; q[i] ^= t; }
}
static void sgc_pack(uint8_t *o, const sgc_gf n)
{
    sgc_gf m, t;
    memcpy(t, n, sizeof t);
    sgc_car(t); sgc_car(t); sgc_car(t);
    for (int j = 0; j < 2; j++) {
        m[0] = t[0] - 0xffed;
        for (int i = 1; i < 15; i++) { m[i] = t[i] - 0xffff - ((m[i - 1] >> 16) & 1); m[i - 1] &= 0xffff; }
        m[15] = t[15] - 0x7fff - ((m[14] >> 16) & 1);
        int b = (int)((m[15] >> 16) & 1);
        m[14] &= 0xffff;
        sgc_sel(t, m, 1 - b);
    }
    for (int i = 0; i < 16; i++) { o[2 * i] = (uint8_t)(t[i] & 0xff); o[2 * i + 1] = (uint8_t)(t[i] >> 8); }
}
static void sgc_unpack(sgc_gf o, const uint8_t *n)
{
    for (int i = 0; i < 16; i++) o[i] = n[2 * i] + ((int64_t)n[2 * i + 1] << 8);
    o[15] &= 0x7fff;
}
static void sgc_A(sgc_gf o, const sgc_gf a, const sgc_gf b) { for (int i = 0; i < 16; i++) o[i] = a[i] + b[i]; }
static void sgc_Z(sgc_gf o, const sgc_gf a, const sgc_gf b) { for (int i = 0; i < 16; i++) o[i] = a[i] - b[i]; }
static void sgc_M(sgc_gf o, const sgc_gf a, const sgc_gf b)
{
    int64_t t[31];
    for (int i = 0; i < 31; i++) t[i] = 0;
    for (int i = 0; i < 16; i++) for (int j = 0; j < 16; j++) t[i + j] += a[i] * b[j];
    for (int i = 0; i < 15; i++) t[i] += 38 * t[i + 16];
    for (int i = 0; i < 16; i++) o[i] = t[i];
    sgc_car(o); sgc_car(o);
}
static void sgc_inv(sgc_gf o, const sgc_gf i_)
{
    sgc_gf c;
    memcpy(c, i_, sizeof c);
    for (int a = 253; a >= 0; a--) { sgc_M(c, c, c); if (a != 2 && a != 4) sgc_M(c, c, i_); }
    memcpy(o, c, sizeof c);
}
static void sgc_x25519(uint8_t q[32], const uint8_t n[32], const uint8_t p[32])
{
    static const sgc_gf k121665 = { 0xDB41, 1 };
    uint8_t z[32];
    int64_t x[80];
    sgc_gf a, b, c, d, e, f;
    memcpy(z, n, 32);
    z[31] = (uint8_t)((n[31] & 127) | 64); z[0] &= 248;
    sgc_unpack(x, p);
    for (int i = 0; i < 16; i++) { b[i] = x[i]; d[i] = a[i] = c[i] = 0; }
    a[0] = d[0] = 1;
    for (int i = 254; i >= 0; --i) {
        int r = (z[i >> 3] >> (i & 7)) & 1;
        sgc_sel(a, b, r); sgc_sel(c, d, r);
        sgc_A(e, a, c); sgc_Z(a, a, c); sgc_A(c, b, d); sgc_Z(b, b, d);
        sgc_M(d, e, e); sgc_M(f, a, a); sgc_M(a, c, a); sgc_M(c, b, e);
        sgc_A(e, a, c); sgc_Z(a, a, c); sgc_M(b, a, a); sgc_Z(c, d, f);
        sgc_M(a, c, k121665); sgc_A(a, a, d); sgc_M(c, c, a); sgc_M(a, d, f);
        sgc_M(d, b, x); sgc_M(b, e, e);
        sgc_sel(a, b, r); sgc_sel(c, d, r);
    }
    for (int i = 0; i < 16; i++) { x[i + 16] = a[i]; x[i + 32] = c[i]; x[i + 48] = b[i]; x[i + 64] = d[i]; }
    sgc_inv(x + 32, x + 32);
    sgc_M(x + 16, x + 16, x + 32);
    sgc_pack(q, x + 16);
}
static void sgc_x25519_base(uint8_t q[32], const uint8_t n[32])
{
    static const uint8_t nine[32] = { 9 };
    sgc_x25519(q, n, nine);
}
/* ---- encrypted game files, format 2 (tools/sgcrypt_files.py; 2026-11-02 "改": updates stay small) --------------------
 * file = encrypted chunks (same bytes as the plain file, in order) | index | trailer (32 bytes)
 *   chunks   the plain file cut by content (gear hash, the launcher's own cutting: average 8 KB, 2..64 KB); each chunk is
 *            AES-128-CTR with its OWN nonce = SHA-256(chunk)[:8], counter from 0 - an unchanged chunk gives the same
 *            bytes wherever it moved, so the launcher's delta download (launcher/Ota.cs Cdc) still finds it
 *   index    n x { u32 plain length (LE), nonce[8] }
 *   trailer  "SGCRYPT2" | SHA-256(plain)[:8] | u64 plain size (LE) | u32 n (LE) | u32 0 */
#define SGC_TRAILER 32
typedef struct { uint32_t n; uint64_t plain; uint64_t *off; uint8_t *non; } SgcIdx;
static uint64_t sgc_le64(const uint8_t *p) { uint64_t v = 0; for (int i = 7; i >= 0; i--) v = v << 8 | p[i]; return v; }
static uint32_t sgc_le32(const uint8_t *p) { return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24; }
/* the last 32 bytes of a file of fsize bytes: 1 = an encrypted file (plain size, chunk count out) */
static int sgc_trailer(const uint8_t t[SGC_TRAILER], uint64_t fsize, uint64_t *plain, uint32_t *n)
{
    if (fsize < SGC_TRAILER || memcmp(t, "SGCRYPT2", 8)) return 0;
    *plain = sgc_le64(t + 16); *n = sgc_le32(t + 24);
    return *plain + 12ull * *n + SGC_TRAILER == fsize;
}
/* index bytes (12 x n) -> chunk offsets; 0 when they do not add up to the plain size */
static int sgc_idx_load(SgcIdx *x, const uint8_t *idx, uint32_t n, uint64_t plain)
{
    x->n = n; x->plain = plain;
    x->off = (uint64_t *)malloc(sizeof(uint64_t) * ((size_t)n + 1));
    x->non = (uint8_t *)malloc(8 * (size_t)n + 1);
    if (!x->off || !x->non) { free(x->off); free(x->non); x->off = NULL; x->non = NULL; return 0; }
    uint64_t o = 0;
    for (uint32_t i = 0; i < n; i++) {
        uint32_t len = sgc_le32(idx + 12 * (size_t)i);
        if (!len) { free(x->off); free(x->non); x->off = NULL; x->non = NULL; return 0; }
        x->off[i] = o; o += len;
        memcpy(x->non + 8 * (size_t)i, idx + 12 * (size_t)i + 4, 8);
    }
    x->off[n] = o;
    if (o != plain) { free(x->off); free(x->non); x->off = NULL; x->non = NULL; return 0; }
    return 1;
}
static void sgc_idx_free(SgcIdx *x) { free(x->off); free(x->non); x->off = NULL; x->non = NULL; }
/* decrypt (xor) len bytes that sit at plain offset pos (any offset, any length; nothing past the plain end) */
static void sgc_idx_xor(const SgcAes *a, const SgcIdx *x, uint64_t pos, uint8_t *buf, size_t len)
{
    if (!x->n || pos >= x->plain) return;
    if (len > x->plain - pos) len = (size_t)(x->plain - pos);
    uint32_t lo = 0, hi = x->n - 1;                 /* the chunk with off[c] <= pos < off[c + 1] */
    while (lo < hi) { uint32_t m = (lo + hi + 1) / 2; if (x->off[m] <= pos) lo = m; else hi = m - 1; }
    for (uint32_t c = lo; len && c < x->n; c++) {
        uint64_t in = pos - x->off[c], take = x->off[c + 1] - pos;
        if (take > len) take = len;
        sgc_ctr_xor(a, x->non + 8 * (size_t)c, in, buf, (size_t)take);
        buf += take; pos += take; len -= (size_t)take;
    }
}

#endif
