"""F44 (2026-10-27, user screenshot 11:18: typing "SOS" in chat popped "Shattered Galaxy detected that you were about to
transmit your password ..."): the chat password guard is switched off.
Chat Enter (0043bf51) -> 00550ad0: text.find(password at [[0x6ba7d8]+0x394]) != npos -> 00439b70 shows
ksPasswordDetected (OK / CANCEL).  The stored password is not what the player typed at login on this server (launcher
log-in, saved / short values), so ordinary words matched; an empty value would even match every line.  The server
never asks for passwords in chat, so the guard is not needed: 00550afe 'je 00550b17' (74 17) -> 'jmp' (eb 17), the
function always returns 0 (no match) and frees its string as before.
usage: python patch_sg_debug_f44.py SG_debug.exe [more exes]   (idempotent)"""
import sys, struct, shutil
VA = 0x550afe
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
    if bytes(d[o:o + 2]) == b"\xeb\x17":
        print(f"{fn}: F44 already applied"); continue
    if bytes(d[o:o + 2]) != b"\x74\x17" or bytes(d[o - 4:o]) != bytes.fromhex("83f8ff5e"):
        raise SystemExit(f"{fn}: unexpected bytes at {VA:#x}: {d[o-4:o+2].hex()}")
    shutil.copy(fn, fn + ".before_f44")
    d[o] = 0xEB
    open(fn, "wb").write(d)
    print(f"{fn}: F44 applied")
