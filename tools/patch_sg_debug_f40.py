"""F40 (2026-10-27, user: "LAB升級的動畫速度太快"): the unit animations in the lab UPGRADE tree run at a fixed speed.
The tree's draw method 00514400 (vtable 0x656124) steps every unit sprite with 005f47e0 (frame +1 per call) at
005145e3 and 00514678, i.e. once per DRAWN FRAME - with cnc-ddraw the screen redraws far more often than the old
DirectDraw path, so the units ran several times too fast.  (The html <img> animation 00501a29 already limits itself
to one step per 50 ms with GetTickCount; the tree did not.)
F40: at the start of each tree draw a gate is opened only when >= STEP_MS have passed (timeGetTime, 1 ms since F28's
timeBeginPeriod); both call sites go through a wrapper that steps the sprite when the gate is open and otherwise only
stores the position like the tree's own 'not animated' branch (005145ea: +0xec x, +0xf0 y, +0xf4 dir, +0xf8 arg4).
Variables in the free page tail after .data (outside the checksum, like F26/F28): 0xEAFF40 last step, 0xEAFF44 gate.
Hooks: 00514403 'call 005064d0' -> jmp stub (replays the call); 005145e3 / 00514678 'call 005f47e0' -> call wrapper.
usage: python patch_sg_debug_f40.py SG_debug.exe [more exes]   (idempotent)"""
import sys, struct, shutil
from keystone import Ks, KS_ARCH_X86, KS_MODE_32
STEP_MS = 80                                   # ~12 animation frames per second
LAST, GATE = 0xEAFF40, 0xEAFF44
ENTRY, ENTRY_BACK = 0x514403, 0x514408
SITES = (0x5145e3, 0x514678)
V_ENTRY, V_WRAP = 0xeb47c0, 0xeb4800
ENTRY_SRC = f"""
    push ecx
    call dword ptr [0x64c30c]
    mov edx, eax
    sub eax, dword ptr [{LAST}]
    cmp eax, {STEP_MS}
    jb closed
    mov dword ptr [{LAST}], edx
    mov byte ptr [{GATE}], 1
    jmp go
closed:
    mov byte ptr [{GATE}], 0
go:
    pop ecx
    call 0x5064d0
    jmp {ENTRY_BACK}
"""
WRAP_SRC = f"""
    cmp byte ptr [{GATE}], 0
    je hold
    jmp 0x5f47e0
hold:
    push eax
    mov eax, dword ptr [esp+8]
    mov dword ptr [ecx+0xec], eax
    mov eax, dword ptr [esp+0xc]
    mov dword ptr [ecx+0xf0], eax
    mov eax, dword ptr [esp+0x10]
    mov byte ptr [ecx+0xf4], al
    mov eax, dword ptr [esp+0x14]
    mov dword ptr [ecx+0xf8], eax
    pop eax
    ret 0x14
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
def rel(op, src, dst): return op + struct.pack("<i", dst - (src + 5))
ks = Ks(KS_ARCH_X86, KS_MODE_32)
E = bytes(ks.asm(ENTRY_SRC, V_ENTRY)[0]); W = bytes(ks.asm(WRAP_SRC, V_WRAP)[0])
assert len(E) <= V_WRAP - V_ENTRY and len(W) <= 0x40, (len(E), len(W))
for fn in sys.argv[1:]:
    d = bytearray(open(fn, "rb").read())
    he = off(d, ENTRY)
    if bytes(d[he:he + 5]) == rel(b"\xe9", ENTRY, V_ENTRY):
        print(f"{fn}: F40 already applied"); continue
    assert bytes(d[he:he + 5]) == rel(b"\xe8", ENTRY, 0x5064d0), f"{fn}: unexpected bytes at {ENTRY:#x}"
    for s in SITES:
        assert bytes(d[off(d, s):off(d, s) + 5]) == rel(b"\xe8", s, 0x5f47e0), f"{fn}: unexpected bytes at {s:#x}"
    so = off(d, V_ENTRY)
    assert d[so:so + 0x80] == bytes(0x80), "stub area not free"
    shutil.copy(fn, fn + ".before_f40")
    d[so:so + len(E)] = E
    d[off(d, V_WRAP):off(d, V_WRAP) + len(W)] = W
    d[he:he + 5] = rel(b"\xe9", ENTRY, V_ENTRY)
    for s in SITES:
        d[off(d, s):off(d, s) + 5] = rel(b"\xe8", s, V_WRAP)
    open(fn, "wb").write(d)
    print(f"{fn}: F40 applied (stubs {len(E)}+{len(W)} bytes at {V_ENTRY:#x}/{V_WRAP:#x}, {STEP_MS} ms per frame)")
