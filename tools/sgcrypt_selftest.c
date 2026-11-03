/* sgcrypt_selftest.c - test driver for client/sgrender/sgcrypt.h (2026-11-02): reads command lines on stdin ("ctr KEY NONCE OFF DATA", "fdec KEY FILE OFF LEN", "sha DATA", "pub SECRET", "x25519 SECRET PUBLIC", hex), prints the results in hex.  tools/mptest/test120.py builds it with gcc and compares with Python cryptography. */
#include <stdio.h>
#include <stdlib.h>
#include "sgcrypt.h"
static int hx(const char *s, uint8_t *o) { int n = 0; while (s[0] && s[1] && s[0] != '\n') { sscanf(s, "%2hhx", &o[n++]); s += 2; } return n; }
static void ph(const uint8_t *p, int n) { for (int i = 0; i < n; i++) printf("%02x", p[i]); printf("\n"); }
int main(void)
{
    static char line[1 << 20]; static uint8_t a[1 << 19], b[1 << 19], c[1 << 19];
    while (fgets(line, sizeof line, stdin)) {
        char *sp1 = strchr(line, ' '); if (!sp1) continue; *sp1++ = 0;
        if (!strcmp(line, "ctr")) {           /* ctr KEY NONCE OFF DATA */
            char *k = sp1, *n = strchr(k, ' '); *n++ = 0; char *of = strchr(n, ' '); *of++ = 0; char *d = strchr(of, ' '); *d++ = 0;
            uint8_t key[16], non[8]; hx(k, key); hx(n, non); int len = hx(d, a);
            SgcAes ae; sgc_aes_init(&ae, key); sgc_ctr_xor(&ae, non, strtoull(of, 0, 10), a, len); ph(a, len);
        } else if (!strcmp(line, "sha")) { int len = hx(sp1, a); SgcSha s; sgc_sha_init(&s); sgc_sha_add(&s, a, len); sgc_sha_end(&s, b); ph(b, 32); }
        else if (!strcmp(line, "x25519")) { char *p = strchr(sp1, ' '); *p++ = 0; hx(sp1, a); hx(p, b); sgc_x25519(c, a, b); ph(c, 32); }
        else if (!strcmp(line, "fdec")) {     /* fdec KEY PATH OFF LEN: an encrypted file (format 2), plain bytes OFF.. */
            char *k = sp1, *pa = strchr(k, ' '); *pa++ = 0; char *of = strchr(pa, ' '); *of++ = 0; char *ln = strchr(of, ' '); *ln++ = 0;
            uint8_t key[16]; hx(k, key);
            FILE *f = fopen(pa, "rb"); if (!f) { printf("nofile\n"); continue; }
            fseek(f, 0, SEEK_END); long fs = ftell(f); fseek(f, 0, SEEK_SET);
            uint8_t *all = malloc(fs); fread(all, 1, fs, f); fclose(f);
            uint64_t plain; uint32_t n; SgcIdx x;
            if (!sgc_trailer(all + fs - SGC_TRAILER, fs, &plain, &n) || !sgc_idx_load(&x, all + plain, n, plain)) { printf("bad\n"); free(all); continue; }
            uint64_t o = strtoull(of, 0, 10); size_t l = strtoul(ln, 0, 10);
            if (o + l > plain) l = (size_t)(plain - o);
            uint8_t *b2 = malloc(l + 1); memcpy(b2, all + o, l);
            SgcAes ae; sgc_aes_init(&ae, key); sgc_idx_xor(&ae, &x, o, b2, l); ph(b2, (int)l);
            free(b2); free(all); sgc_idx_free(&x);
        }
        else if (!strcmp(line, "pub")) { hx(sp1, a); sgc_x25519_base(c, a); ph(c, 32); }
        fflush(stdout);
    }
    return 0;
}
