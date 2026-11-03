"""F41 (2026-10-27, user: name line like the original Chinese servers - rank badges + stars over the name):
the commander's title line (0x20 s8 title -> +0xc6, drawn by 004ce920 at 004cf0f5) is printed as "%s" in teal
instead of "<%s>" in gray, so the server can put stars (e.g. "★★★★") there.
  .rdata 0x65348c "<%s>" -> "%s"  (only user: 004cf0f6)
  004cf11e/23/28 push 0xc8,0xc8,0xc8 (B, G, R for 00402f40) -> B 0xc8, G 0xe6, R 0x50
usage: python patch_sg_debug_f41.py SG_debug.exe [more exes]   (idempotent)"""
import sys, struct, shutil
FMT = 0x65348c
COL = {0x4cf11f: 0xc8, 0x4cf124: 0xe6, 0x4cf129: 0x50}      # imm8 of push B / push G / push R
def sections(d):
    pe = struct.unpack_from("<I", d, 0x3c)[0]
    n = struct.unpack_from("<H", d, pe + 6)[0]
    opt = struct.unpack_from("<H", d, pe + 20)[0]
    return [struct.unpack_from("<8sIIII", d, pe + 24 + opt + 40 * i) for i in range(n)]
def off(d, va):
    for _nm, vs, sva, rs, ro in sections(d):
        if 0x400000 + sva <= va < 0x400000 + sva + min(vs, rs):
            return va - 0x400000 - sva + ro
    raise SystemExit(f"VA {va:#x} not in any section's raw data")
for fn in sys.argv[1:]:
    d = bytearray(open(fn, "rb").read())
    f = off(d, FMT)
    if bytes(d[f:f + 5]) == b"%s\0\0\0":
        print(f"{fn}: F41 already applied"); continue
    assert bytes(d[f:f + 5]) == b"<%s>\0", f"{fn}: unexpected format at {FMT:#x}"
    for va in COL:
        o = off(d, va)
        assert d[o - 1] == 0x68 and d[o:o + 4] == bytes([0xc8, 0, 0, 0]), f"{fn}: unexpected push at {va - 1:#x}"
    shutil.copy(fn, fn + ".before_f41")
    d[f:f + 5] = b"%s\0\0\0"
    for va, v in COL.items():
        d[off(d, va)] = v
    open(fn, "wb").write(d)
    print(f"{fn}: F41 applied")
