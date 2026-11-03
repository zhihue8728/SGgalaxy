"""F55 STRAIGHT PATHS (2026-11-02, user 18:58 "开始做方案 B": units should not walk "on a grid").
The client's A* (8 directions, 8 px cells) hands its cell list to 0x413c60, which builds the unit's path polyline
(CPath, unit +0x7410) - a zig-zag of 0/45/90 degree pieces that the mover follows.  The 5 calls of 0x413c60 now go
through a stub that calls SGRender.dll (TABLE+0x3c, path_build: the original, then the path pulled straight, see
client/sgrender/sgpath.h).  Without the DLL (TABLE+0x3c = 0) the stub jumps to the original: the old paths.
LOCK-STEP: every player in a battle must run the same build (publish with -Min).
usage: python patch_sg_debug_f55.py SG.exe [more exes]   (idempotent; checks the bytes first)"""
import sys, os, shutil, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import patch_sg_debug_f49 as F49
from keystone import Ks, KS_ARCH_X86, KS_MODE_32

T = F49.TABLE
ORIG = 0x413c60
STUB_VA = 0xeb4c90                     # free after F53's code (ends 0xeb4c7b) up to the end of .dbgmov (0xeb5000)
STUB_END = 0xeb4d00
CALLS = [0x41615f, 0x416320, 0x416345, 0x416442, 0x416463]   # every "call 0x413c60" in the exe (ecx = the A*)
SRC = f"""
    mov eax, dword ptr [{T + 0x3c:#x}]
    test eax, eax
    je orig
    jmp eax
orig:
    jmp {ORIG:#x}
"""
ks = Ks(KS_ARCH_X86, KS_MODE_32)
STUB = bytes(ks.asm(SRC, STUB_VA)[0])
assert STUB_VA + len(STUB) <= STUB_END, hex(STUB_VA + len(STUB))


def call_bytes(at, to):
    return b"\xe8" + struct.pack("<i", to - (at + 5))


if __name__ == "__main__":
    for fn in sys.argv[1:]:
        d = bytearray(open(fn, "rb").read())
        s = F49.off(d, STUB_VA)
        if bytes(d[s:s + len(STUB)]) == STUB and all(bytes(d[F49.off(d, c):F49.off(d, c) + 5]) == call_bytes(c, STUB_VA) for c in CALLS):
            print(f"{fn}: F55 already applied"); continue
        assert d[s:s + len(STUB)] == bytes(len(STUB)), f"{fn}: stub area not free"
        for c in CALLS:
            o = F49.off(d, c)
            assert bytes(d[o:o + 5]) == call_bytes(c, ORIG), f"{fn}: unexpected bytes at {c:#x}"
        shutil.copy(fn, fn + ".before_f55")
        d[s:s + len(STUB)] = STUB
        for c in CALLS:
            o = F49.off(d, c)
            d[o:o + 5] = call_bytes(c, STUB_VA)
        open(fn, "wb").write(d)
        print(f"{fn}: F55 applied ({len(STUB)}-byte stub at {STUB_VA:#x}, {len(CALLS)} calls)")
