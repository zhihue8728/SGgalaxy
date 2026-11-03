"""F58 HD UNIT DRAW RECORD (2026-11-03, user: HD field units drawn by the GPU at screen resolution, prototype g039;
plan: Claude Docs "HD 戰場單位疊加：g039 原型規劃", project doc claude/HD_UNIT_OVERLAY_PLAN.md).
A unit's sprite layers are all drawn inside the animation draw 0x5f59d0 (called from the unit draw 004ce920 through
0x5f5ed0).  It calls seven sprite draws, all thiscall on the Cxpf (ecx) with the same first five stack arguments:
    (CGraph*, x, y, direction, frame, ...)       x, y = viewport coordinates of the sprite's pivot
and at every call esi = the sprite's file name (char *, e.g. "g039mo.xpf").  Each call now goes through a 12-byte
entry that pushes its target and its site number and jumps to one common stub; when SGRender.dll set TABLE slot 17
(0xEAFFC4, hd_record) the stub calls
    void __cdecl hd_record(int site, void *cxpf, const char *name, DWORD *args)     (args -> the 5+ stack args)
with every register saved.  It returns 0 -> the stub jumps to the original draw (unchanged game); nonzero -> the stub
returns to the caller with the draw's stack arguments popped (ARGB below): the DLL drew the sprite itself (it calls
the original and keeps the pixels it wrote, for the HD occlusion mask) or skips it (a glow / shadow layer that the
HD version replaces).  v2 (11-03): v1 (always the original) is upgraded in place.
Without the DLL (slot 17 = 0) the stub goes straight to the original.  Display only: no lock-step concern, but .text
changes -> run deploy.bat (client checksum) before publish.
Sites (site number = index): 0 5f5b8e normal 5ee7f0 · 1 5f5cb5 alpha 5ef880 · 2 5f5cdd add 5f02f0 · 3 5f5d33 tint 5f1db0
· 4 5f5df2 add 5f02f0 (layer 2) · 5 5f5e44 add 5f02f0 · 6 5f5e5c dispatch 4032a0.
usage: python patch_sg_debug_f58.py SG.exe [more exes]   (idempotent; checks the bytes first)"""
import sys, os, shutil, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import patch_sg_debug_f49 as F49
from keystone import Ks, KS_ARCH_X86, KS_MODE_32

T = F49.TABLE
SLOT = T + 0x44                        # TABLE slot 17 (free: slots 16 and 31 are used by F57 / others)
CAVE_VA = 0xeb4d60                     # after F57's cave (0xeb4d10..0xeb4d60), free to the end of .dbgmov (0xeb5000)
CAVE_END = 0xeb4e40
ARGB = [0x18, 0x1c, 0x1c, 0x20, 0x1c, 0x1c, 0x1c]  # each draw's "ret N" (stack bytes the callee pops)
SITES = [(0x5f5b8e, 0x5ee7f0), (0x5f5cb5, 0x5ef880), (0x5f5cdd, 0x5f02f0), (0x5f5d33, 0x5f1db0),
         (0x5f5df2, 0x5f02f0), (0x5f5e44, 0x5f02f0), (0x5f5e5c, 0x4032a0)]
ENTRY = 12                             # push imm32 (5) + push imm8 (2) + jmp rel32 (5)

ks = Ks(KS_ARCH_X86, KS_MODE_32)
COMMON_VA = CAVE_VA + ENTRY * len(SITES)
# stack at common: [esp] site, [esp+4] original draw, [esp+8] caller's return, [esp+12..] the draw's arguments
COMMON_V1 = f"""
    mov eax, dword ptr [{SLOT:#x}]
    test eax, eax
    je go
    pushad
    lea edx, [esp + 44]
    push edx
    push esi
    push ecx
    push dword ptr [esp + 44]
    call eax
    add esp, 16
    popad
go:
    add esp, 4
    ret
"""
ARGB_VA = COMMON_VA + 0x60
COMMON = f"""
    mov eax, dword ptr [{SLOT:#x}]
    test eax, eax
    je go
    pushad
    lea edx, [esp + 44]
    push edx
    push esi
    push ecx
    push dword ptr [esp + 44]
    call eax
    add esp, 16
    mov dword ptr [esp + 28], eax
    popad
    test eax, eax
    jne skip
go:
    add esp, 4
    ret
skip:
    pop eax
    add esp, 4
    pop edx
    movzx ecx, byte ptr [{ARGB_VA:#x} + eax]
    add esp, ecx
    jmp edx
"""


def build(common=None):
    common = common or COMMON
    code = b""
    for k, (site, orig) in enumerate(SITES):
        va = CAVE_VA + k * ENTRY
        # written out: keystone would pick a short jmp; every entry must be exactly ENTRY bytes
        e = b"\x68" + struct.pack("<I", orig) + bytes([0x6a, k]) + b"\xe9" + struct.pack("<i", COMMON_VA - (va + ENTRY))
        assert len(e) == ENTRY, (k, len(e))
        code += e
    c = bytes(ks.asm(common, COMMON_VA)[0])
    if common is COMMON:
        assert len(c) <= ARGB_VA - COMMON_VA, len(c)
        c = c.ljust(ARGB_VA - COMMON_VA, b"\x90") + bytes(ARGB)
    code += c
    assert CAVE_VA + len(code) <= CAVE_END, hex(CAVE_VA + len(code))
    return code


CODE = build()
CODE_V1 = build(COMMON_V1)


def call_bytes(at, to):
    return b"\xe8" + struct.pack("<i", to - (at + 5))


def applied(d):
    s = F49.off(d, CAVE_VA)
    return bytes(d[s:s + len(CODE)]) == CODE and all(
        bytes(d[F49.off(d, a):F49.off(d, a) + 5]) == call_bytes(a, CAVE_VA + k * ENTRY) for k, (a, _) in enumerate(SITES))


def applied_v1(d):
    s = F49.off(d, CAVE_VA)
    return bytes(d[s:s + len(CODE_V1)]) == CODE_V1 and all(
        bytes(d[F49.off(d, a):F49.off(d, a) + 5]) == call_bytes(a, CAVE_VA + k * ENTRY) for k, (a, _) in enumerate(SITES))


def apply(d):
    s = F49.off(d, CAVE_VA)
    if applied_v1(d):                                    # upgrade v1 -> v2: only the cave changes
        d[s:s + len(CODE)] = CODE.ljust(len(CODE), b"\0"); return
    assert d[s:s + len(CODE)] == bytes(len(CODE)), "cave not free"
    for a, orig in SITES:
        o = F49.off(d, a)
        assert bytes(d[o:o + 5]) == call_bytes(a, orig), f"unexpected bytes at {a:#x}"
    d[s:s + len(CODE)] = CODE
    for k, (a, _) in enumerate(SITES):
        o = F49.off(d, a)
        d[o:o + 5] = call_bytes(a, CAVE_VA + k * ENTRY)


if __name__ == "__main__":
    for fn in sys.argv[1:]:
        d = bytearray(open(fn, "rb").read())
        if applied(d):
            print(f"{fn}: F58 already applied"); continue
        v1 = applied_v1(d)
        apply(d)
        if v1:
            open(fn, "wb").write(d); print(f"{fn}: F58 v1 upgraded to v2"); continue
        shutil.copy(fn, fn + ".before_f58")
        open(fn, "wb").write(d)
        print(f"{fn}: F58 applied ({len(CODE)}-byte cave at {CAVE_VA:#x}, {len(SITES)} calls)")
