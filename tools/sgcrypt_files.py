"""ENCRYPTED GAME FILES (2026-11-02, user "1/2/3都要加密" -> "HUD 资料包 + 全部 .dat"; format 2 after "改": updates stay small).
Makes the encrypted copies the launcher ships (deploy/ota_files.json points at out/enc/...) from the plain files listed in
deploy/encrypt_files.json {"out/enc/X": "plain source"}.  publish.ps1 runs it before every release.

Format 2 (client/sgrender/sgcrypt.h reads it):  encrypted chunks | index | trailer
  chunks   the plain file cut by CONTENT with the launcher's own cutting (launcher/Ota.cs Cdc: gear hash, mask 13 bits,
           2 KB .. 64 KB, average 8 KB); every chunk is AES-128-CTR with its own nonce = SHA-256(chunk)[:8], counter 0.
           An unchanged chunk therefore gives the same bytes wherever it moved: the launcher's delta download finds it,
           and a small edit costs a few chunks instead of the whole file (format 1, one nonce per file, did).
  index    n x { u32 plain length LE, nonce[8] }
  trailer  "SGCRYPT2" | SHA-256(plain)[:8] | u64 plain size LE | u32 n LE | u32 0          (32 bytes)
  key      SGFILE_KEY in client/sgrender/sgfile_key.h (built into ddraw.dll and SGRender.dll, which decrypt while the game
           reads: client/sgrender/sgcrypt_hooks.h, hud_pack_get in sghud_draw.h).  It has to be in the client, so this
           only keeps the files from being opened by hand.
Needs the 'cryptography' package; 'numpy' makes the cutting fast (without it: pure Python, minutes for 300 MB).
usage: python tools/sgcrypt_files.py            build what is missing or out of date
       python tools/sgcrypt_files.py --check    exit 1 when an encrypted copy is missing / out of date
       python tools/sgcrypt_files.py --decrypt IN OUT   (to look at a shipped file)"""
import hashlib, json, os, re, struct, sys

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
LIST = os.path.join(REPO, "deploy", "encrypt_files.json")
KEY_H = os.path.join(REPO, "client", "sgrender", "sgfile_key.h")
MAGIC = b"SGCRYPT2"
TRAILER = 32
CDC_MIN, CDC_MAX, CDC_MASK = 2048, 65536, (1 << 13) - 1      # = launcher/Ota.cs


def gear():
    g, x = [], 2463534242
    for _ in range(256):
        x ^= (x << 13) & 0xFFFFFFFF; x ^= x >> 17; x ^= (x << 5) & 0xFFFFFFFF
        g.append(x)
    return g


GEAR = gear()


def cut_points(data):
    """chunk ends, exactly like Ota.Cdc (h = (h << 1) + Gear[b], reset at every cut; a cut needs >= 2 KB, so h is then
    a function of the last 32 bytes only, which lets numpy compute it for every position at once)"""
    n = len(data)
    try:
        import numpy as np
        g = np.array(GEAR, dtype=np.uint32)[np.frombuffer(data, dtype=np.uint8)]
        h = np.zeros(n, dtype=np.uint32)
        for k in range(32):
            h[k:] += g[:n - k] << np.uint32(k)
        cand = (np.nonzero((h & np.uint32(CDC_MASK)) == 0)[0] + 1).tolist()      # a cut AFTER byte i
    except ImportError:
        cand, hh = [], 0
        for i, b in enumerate(data):
            hh = ((hh << 1) + GEAR[b]) & 0xFFFFFFFF
            if not hh & CDC_MASK:
                cand.append(i + 1)
    ends, start, ci = [], 0, 0
    while start < n:
        while ci < len(cand) and cand[ci] - start < CDC_MIN:
            ci += 1
        e = cand[ci] if ci < len(cand) and cand[ci] - start <= CDC_MAX else min(start + CDC_MAX, n)
        ends.append(e); start = e
    return ends


def file_key():
    t = open(KEY_H, encoding="utf-8").read()
    body = t[t.index("SGFILE_KEY"):]
    k = bytes(int(x, 16) for x in re.findall(r"0x([0-9a-fA-F]{2})", body[:body.index("}")]))
    assert len(k) == 16, "sgfile_key.h: 16 bytes expected"
    return k


def _ctr(key, nonce):
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    return Cipher(algorithms.AES(key), modes.CTR(nonce + bytes(8))).encryptor()


def encrypt_bytes(data, key):
    out, idx, start = [], [], 0
    for e in cut_points(data):
        c = data[start:e]
        nonce = hashlib.sha256(c).digest()[:8]
        out.append(_ctr(key, nonce).update(c)); idx.append(struct.pack("<I", len(c)) + nonce)
        start = e
    tr = MAGIC + hashlib.sha256(data).digest()[:8] + struct.pack("<QII", len(data), len(idx), 0)
    return b"".join(out) + b"".join(idx) + tr


def decrypt_bytes(enc, key):
    t = enc[-TRAILER:]
    assert t[:8] == MAGIC, "not an encrypted file (format 2)"
    plain, n, _ = struct.unpack("<QII", t[16:])
    assert plain + 12 * n + TRAILER == len(enc), "size"
    out, pos = [], 0
    for i in range(n):
        ln, nonce = struct.unpack_from("<I", enc, plain + 12 * i)[0], enc[plain + 12 * i + 4:plain + 12 * i + 12]
        out.append(_ctr(key, nonce).update(enc[pos:pos + ln])); pos += ln
    d = b"".join(out)
    assert hashlib.sha256(d).digest()[:8] == t[8:16], "checksum"
    return d


def encrypt_file(src, dst, key):
    os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
    tmp = dst + ".tmp"
    with open(src, "rb") as f:
        data = f.read()
    with open(tmp, "wb") as o:
        o.write(encrypt_bytes(data, key))
    os.replace(tmp, dst)


def decrypt_file(src, dst, key):
    open(dst, "wb").write(decrypt_bytes(open(src, "rb").read(), key))


def up_to_date(src, dst):
    """the copy is current when its trailer names the source's size and SHA-256 (no decryption needed)"""
    if not os.path.exists(dst) or os.path.getsize(dst) < os.path.getsize(src) + TRAILER:
        return False
    with open(dst, "rb") as f:
        f.seek(-TRAILER, 2)
        t = f.read(TRAILER)
    h = hashlib.sha256()
    with open(src, "rb") as f:
        for b in iter(lambda: f.read(16 << 20), b""):
            h.update(b)
    plain, n, _ = struct.unpack("<QII", t[16:])
    return (t[:8] == MAGIC and t[8:16] == h.digest()[:8] and plain == os.path.getsize(src)
            and os.path.getsize(dst) == plain + 12 * n + TRAILER)


def main(argv):
    if argv[:1] == ["--decrypt"]:
        decrypt_file(argv[1], argv[2], file_key()); return 0
    lst = {k: v for k, v in json.load(open(LIST, encoding="utf-8")).items() if not k.startswith("_")}
    key, bad = file_key(), 0
    for dst, src in lst.items():
        s, d = os.path.join(REPO, src), os.path.join(REPO, dst)
        if not os.path.exists(s):
            print("MISSING source", src); bad += 1; continue
        if up_to_date(s, d):
            continue
        if "--check" in argv:
            print("out of date:", dst, "<-", src); bad += 1; continue
        encrypt_file(s, d, key)
        print("encrypted", src, "->", dst)
    if "--check" not in argv:
        print(f"{len(lst)} encrypted file(s) up to date" if not bad else f"{bad} problem(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
