"""F57 FHQ EXIT IN ONE CLICK (2026-11-03, user 02:20 "點擊離開要點擊兩次").
The FHQ is a hub (F.H.Q / DOMESTIC POLICY / VOTE / FOREIGN POLICY + exit; 0056ea00.., vtable 0065a8ac) with three
pages.  A page's exit (Domestic 0047c558, Vote 004b95a3, Foreign 005e64b7) does "hub->56ee00(4); page->close", and
the window manager then shows the hub again: its show (0056ec..) sets state 1 (+0x5d9c, intro), target 0 (+0x5da0)
and plays the intro - a second click on the hub's exit was needed to leave.  The hub's own exit (id 0x13) is
"target 0, 56ee00(3)": at the next animation callback (56f0e0) state 3 with target 0 closes the hub = leaves the FHQ.
Measured 11-03 02:33 (memory poll of the hub): doing the hub exit right after the page's close does not work - the
hub is shown again ~0.2 s later (state 1).
Now: a page's exit also sets a flag (TABLE slot 31 = 0xEAFFFC, the F48 TABLE page; SGRender does not use it), and the
hub's show starts in state 3 instead of 1 when the flag is set (flag cleared): its first animation callback closes it.
usage: python patch_sg_debug_f57.py SG.exe [more exes]   (idempotent; checks the bytes first)"""
import sys, os, shutil, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import patch_sg_debug_f49 as F49
from keystone import Ks, KS_ARCH_X86, KS_MODE_32

GO = 0x56ee00
FLAG = F49.TABLE + 0x7c                # TABLE slot 31
CAVE_VA = 0xeb4d10                     # after F56's cave (0xeb4cb0..0xeb4d0b), free to the end of .dbgmov (0xeb5000)
CAVE_END = 0xeb4d60
EXITS = [0x47c55a, 0x4b95a5, 0x5e64b9]  # "push 4; call 0x56ee00" in the three pages' exit (ecx = the hub)
SHOW = 0x56ed68                         # mov dword ptr [esi+0x5d9c], 1  (10 bytes, esi = the hub)
SHOW_OLD = bytes.fromhex("c7869c5d000001000000")
SRC = f"""
exit_hook:
    mov dword ptr [{FLAG:#x}], 1
    jmp {GO:#x}
show_hook:
    cmp dword ptr [{FLAG:#x}], 0
    jne leave
    mov dword ptr [esi + 0x5d9c], 1
    ret
leave:
    mov dword ptr [{FLAG:#x}], 0
    mov dword ptr [esi + 0x5d9c], 3
    ret
"""
ks = Ks(KS_ARCH_X86, KS_MODE_32)
CAVE = bytes(ks.asm(SRC, CAVE_VA)[0])
assert CAVE_VA + len(CAVE) <= CAVE_END, hex(CAVE_VA + len(CAVE))
SHOW_HOOK = CAVE_VA + 15                # mov [abs32], imm32 (10) + jmp rel32 (5)
assert CAVE[15] == 0x83


def call_bytes(at, to):
    return b"\xe8" + struct.pack("<i", to - (at + 5))


SHOW_NEW = call_bytes(SHOW, SHOW_HOOK) + b"\x90" * 5

if __name__ == "__main__":
    for fn in sys.argv[1:]:
        d = bytearray(open(fn, "rb").read())
        s = F49.off(d, CAVE_VA)
        at = lambda va, n: bytes(d[F49.off(d, va):F49.off(d, va) + n])
        if at(CAVE_VA, len(CAVE)) == CAVE and at(SHOW, 10) == SHOW_NEW and all(at(c, 5) == call_bytes(c, CAVE_VA) for c in EXITS):
            print(f"{fn}: F57 already applied"); continue
        assert d[s:s + len(CAVE)] == bytes(len(CAVE)), f"{fn}: cave area not free"
        assert at(SHOW, 10) == SHOW_OLD, f"{fn}: unexpected bytes at {SHOW:#x}"
        for c in EXITS:
            assert at(c - 2, 7) == b"\x6a\x04" + call_bytes(c, GO), f"{fn}: unexpected bytes at {c:#x}"
        shutil.copy(fn, fn + ".before_f57")
        d[s:s + len(CAVE)] = CAVE
        o = F49.off(d, SHOW); d[o:o + 10] = SHOW_NEW
        for c in EXITS:
            o = F49.off(d, c); d[o:o + 5] = call_bytes(c, CAVE_VA)
        open(fn, "wb").write(d)
        print(f"{fn}: F57 applied ({len(CAVE)}-byte cave at {CAVE_VA:#x}, {len(EXITS)} exits + the hub's show)")
