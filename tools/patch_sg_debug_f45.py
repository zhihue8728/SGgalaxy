"""F45 (2026-10-27 19:46, user: on the Simulation Center, a selected province's ENTER did nothing; the board showed the
WAR tab with the nation tally): F39 opened the WAR tab for every new province - also on the SIMULATION board, whose
tabs are hidden and whose ENTER / JOIN works from the tab the original code picks (3 BATTLE: every sim record has an
open battle).  F45: when the panel's parent board (panel +0x138 = CBoardWnd, loaded into ebp at 004375e2) is in sim
mode (+0x129f5, set by 00422cb0) the original auto-select at 004375f4 runs; otherwise F39 as before (WAR tab).
Hook: F39 stub 0xeb47a0 -> jmp 0xeb4900 (new stub, .dbgmov).
usage: python patch_sg_debug_f45.py SG_debug.exe [more exes]   (needs F39; idempotent)"""
import sys, struct, shutil
from keystone import Ks, KS_ARCH_X86, KS_MODE_32
HOOK, VA = 0xeb47a0, 0xeb4900
F39 = bytes.fromhex("8b0dc8a76b0080b9b1250000000f85a52e58ffe98e2e58ff")
SRC = """
    mov ecx, dword ptr [0x6ba7c8]
    test ebp, ebp
    je normal
    cmp byte ptr [ebp+0x129f5], 0
    jne 0x4375f4
normal:
    cmp byte ptr [ecx+0x25b1], 0
    jne 0x437658
    jmp 0x437646
"""
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
ks = Ks(KS_ARCH_X86, KS_MODE_32)
STUB = bytes(ks.asm(SRC, VA)[0])
JMP = b"\xe9" + struct.pack("<i", VA - (HOOK + 5))
for fn in sys.argv[1:]:
    d = bytearray(open(fn, "rb").read())
    h, s = off(d, HOOK), off(d, VA)
    if bytes(d[h:h + 5]) == JMP and bytes(d[s:s + len(STUB)]) == STUB:
        print(f"{fn}: F45 already applied"); continue
    if bytes(d[h:h + len(F39)]) != F39:
        raise SystemExit(f"{fn}: F39 stub not found at {HOOK:#x}: {d[h:h+len(F39)].hex()}")
    assert d[s:s + 0x40] == bytes(0x40), "stub area not free"
    shutil.copy(fn, fn + ".before_f45")
    d[s:s + len(STUB)] = STUB
    d[h:h + 5] = JMP
    open(fn, "wb").write(d)
    print(f"{fn}: F45 applied ({len(STUB)} bytes at {VA:#x})")
