"""GAME EXE ICON (user 2026-11-02 17:47: the icon -> the planet horizon of login background D).
SG.exe has three icon groups (101, 127, 128), each one 32x32 24-bit image (3240 bytes: header, BGR rows, AND mask).
Their pixels are overwritten IN PLACE with deploy/go_icon32.png (made by tools/make_go_icon.py), so no section moves.
Only .rsrc changes: the F16 / F34 code checksums (.text + .dbgmov) stay the same.  Idempotent.
usage: python tools/set_exe_icon.py SG_debug.exe out/SG_cn.exe out/SG_tw.exe out/SG_en.exe"""
import os, struct, sys
from PIL import Image

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def icons(b):
    """file offsets of the RT_ICON images (walks the resource directory)"""
    pe = struct.unpack_from("<I", b, 0x3c)[0]
    nsec = struct.unpack_from("<H", b, pe + 6)[0]
    opt = pe + 24
    rsrc_rva = struct.unpack_from("<I", b, opt + 96 + 2 * 8)[0]
    sec = opt + struct.unpack_from("<H", b, pe + 20)[0]
    for i in range(nsec):
        s = sec + 40 * i
        va, raw = struct.unpack_from("<I", b, s + 12)[0], struct.unpack_from("<I", b, s + 20)[0]
        vsz = max(struct.unpack_from("<I", b, s + 8)[0], struct.unpack_from("<I", b, s + 16)[0])
        if va <= rsrc_rva < va + vsz:
            base = raw + rsrc_rva - va
            delta = raw - va
            break
    else:
        raise SystemExit("no .rsrc")

    def entries(off):
        n = sum(struct.unpack_from("<HH", b, off + 12))
        return [struct.unpack_from("<II", b, off + 16 + 8 * i) for i in range(n)]
    out = []
    for name, sub in entries(base):
        if name != 3 or not sub & 0x80000000:
            continue
        for _, s2 in entries(base + (sub & 0x7fffffff)):
            for _, leaf in entries(base + (s2 & 0x7fffffff)):
                rva, size = struct.unpack_from("<II", b, base + leaf)
                out.append((rva + delta, size))
    return out


def main():
    img = Image.open(os.path.join(REPO, "deploy", "go_icon32.png")).convert("RGB")
    assert img.size == (32, 32)
    pix = img.tobytes("raw", "BGR", 0, -1)                 # bottom-up rows, 96 bytes (no padding)
    for p in sys.argv[1:]:
        b = bytearray(open(p, "rb").read())
        n = 0
        for off, size in icons(b):
            hdr = struct.unpack_from("<IiiHHI", b, off)
            if hdr[:5] != (40, 32, 64, 1, 24) or size != 3240:
                print(f"{p}: icon at {off:#x} is not 32x32 24-bit, left"); continue
            b[off + 40:off + 40 + 3072] = pix
            b[off + 40 + 3072:off + 3240] = bytes(128)        # AND mask: all opaque
            n += 1
        open(p, "wb").write(b)
        print(f"{p}: {n} icon(s) set")


if __name__ == "__main__":
    main()
