"""F43 (2026-10-27, user: "英文版也要保持星星"): DBCS text on a non-Chinese Windows (English client) is decoded as
GBK (code page 936) instead of the original Korean table.  F18's glyph stub (0xeb39f0) maps text through
MultiByteToWideChar(GetACP()) only for 950 / 936 and otherwise falls back to the Korean NOG.fnt mapping (only hangul,
everything else = glyph 0x961 '?').  Names and the copper/silver/gold stars go out as GBK, and the Simplified unicode
glyphs (dns.dat NOG.fnt, F18) are in every channel, so on any other code page we now take the 936 path.
  0xeb3a04: 'mov ax,[esp+4]; push 0x4ba805; ret' (11 bytes) -> 'mov eax, 936; jmp 0xeb3a16' + nops
usage: python patch_sg_debug_f43.py SG_debug.exe [more exes]   (needs F18; idempotent)"""
import sys, struct, shutil
VA = 0xeb3a04
ORIG = bytes.fromhex("668b4424046805a84b00c3")
NEW = bytes.fromhex("b8a8030000eb0b") + b"\x90" * 4          # mov eax,0x3a8 ; jmp 0xeb3a16
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
    o = off(d, VA)
    if bytes(d[o:o + 11]) == NEW:
        print(f"{fn}: F43 already applied"); continue
    if bytes(d[o:o + 11]) != ORIG:
        raise SystemExit(f"{fn}: unexpected bytes at {VA:#x}: {d[o:o+11].hex()} (needs F18)")
    shutil.copy(fn, fn + ".before_f43")
    d[o:o + 11] = NEW
    open(fn, "wb").write(d)
    print(f"{fn}: F43 applied")
