"""F39 (2026-10-27, user: "點大地圖的省，先顯示的頁面是war 不是battle或是user"): clicking a province on the strategic
map opens the WAR tab first.
00437370 (new 0x2e province info) picked a tab by itself: 3 BATTLE (battle there), 2 USERS (users listed), 4 WAR.
F26 already skips that choice when the info is for the SAME province again (refresh / 30 s push) and a tab is
selected; its "new province" path returned to 004375f4.  F39 sends that path to the WAR branch 00437646 (push 4 ->
00434590 tab 4, 00421600(4)) instead, keeping the original guard 'cmp byte [ecx+0x25b1],0 / jne 00437658'.
Hook: F26 stub 0xeb3da0 (mov ecx,[0x6ba7c8]; push 0x4375f4; ret = 12 bytes) -> jmp 0xeb47a0.
usage: python patch_sg_debug_f39.py SG_debug.exe [more exes]   (needs F26; idempotent)"""
import sys, struct, shutil
from keystone import Ks, KS_ARCH_X86, KS_MODE_32
HOOK, VA = 0xeb3da0, 0xeb47a0
ORIG = bytes.fromhex("8b0dc8a76b0068f4754300c3")
SRC = """
    mov ecx, dword ptr [0x6ba7c8]
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
JMP = b"\xe9" + struct.pack("<i", VA - (HOOK + 5)) + b"\x90" * 7
for fn in sys.argv[1:]:
    d = bytearray(open(fn, "rb").read())
    h, s = off(d, HOOK), off(d, VA)
    if bytes(d[h:h + 12]) == JMP:
        print(f"{fn}: F39 already applied"); continue
    if bytes(d[h:h + 12]) != ORIG:
        raise SystemExit(f"{fn}: F26 stub not found at {HOOK:#x}: {d[h:h+12].hex()}")
    assert d[s:s + 0x40] == bytes(0x40), "stub area not free"
    shutil.copy(fn, fn + ".before_f39")
    d[s:s + len(STUB)] = STUB
    d[h:h + 12] = JMP
    open(fn, "wb").write(d)
    print(f"{fn}: F39 applied (stub {len(STUB)} bytes at {VA:#x})")
