"""F46 FRAME LIMIT (2026-10-27, user: "升級窗口的單位動畫過快 - this happened twice, make sure animations are right").
ROOT CAUSE.  Every UI / effect animation of the client steps ONCE PER DRAWN FRAME (005f47e0 frame+1 per call: lab
upgrade tree CCtrlGraph 0044de40, unit lists CCtrlListEx 00514400, portraits, effects ...).  The main loop 0054abf0
(and the modal loops 00478ec0) does one frame 00549640 per iteration and then Sleep(1).  On the original systems the
timer ticked every 10-15.6 ms, so Sleep(1) slept ~15 ms and the game ran at ~60-65 frames/s - the speed every
animation was drawn for.  F28 (2026-10-22) calls timeBeginPeriod(1): Sleep(1) now really sleeps 1 ms, the loop runs
at several hundred frames/s and every per-frame animation runs several times too fast.  F40 (lab list only) patched
one symptom; the lab UPGRADE tree is another control and was still too fast.
F46 fixes it at the root: the frame function 00549640 starts with a frame limiter - if less than FRAME_MS ms passed
since the last frame start it Sleeps the rest (timeGetTime / Sleep, 1 ms exact thanks to F28) -> at most 62.5
frames/s everywhere, like before F28.  Battle simulation is clock-driven (lock-step ticks), not frame-driven: it is
not slowed, it only draws 62 times per second.  F40's 80 ms gate is opened to 0 (it would now make the lists 5x too
slow); the list animations run at the frame rate again like every other animation.
Hook: 00549640 'push esi / mov esi,ecx / lea eax,[esi+0x24]' (6 bytes) -> jmp 0xeb4940 + nop; the stub replays them.
Variable: 0xEAFF60 (last frame start), page tail after .data, outside the checksum like F26/F28/F40/F42.
usage: python patch_sg_debug_f46.py SG_debug.exe [more exes]   (idempotent)"""
import sys, struct, shutil
from keystone import Ks, KS_ARCH_X86, KS_MODE_32
FRAME_MS = 16
HOOK, BACK, VA, LAST = 0x549640, 0x549646, 0xeb4940, 0xEAFF60
TIMEGETTIME, SLEEP = 0x64c30c, 0x64c1ec
ORIG = bytes.fromhex("568bf18d4624")
SRC = f"""
    push ecx
    call dword ptr [{TIMEGETTIME}]
    mov edx, eax
    sub eax, dword ptr [{LAST}]
    cmp eax, {FRAME_MS}
    jae done
    mov ecx, {FRAME_MS}
    sub ecx, eax
    push ecx
    call dword ptr [{SLEEP}]
    call dword ptr [{TIMEGETTIME}]
    mov edx, eax
done:
    mov dword ptr [{LAST}], edx
    pop ecx
    push esi
    mov esi, ecx
    lea eax, [esi+0x24]
    jmp {BACK}
"""
F40_STUB, F40_CMP_OLD, F40_CMP_NEW = 0xeb47c0, bytes.fromhex("83f850"), bytes.fromhex("83f800")
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
assert len(STUB) <= 0x60, len(STUB)
JMP = b"\xe9" + struct.pack("<i", VA - (HOOK + 5)) + b"\x90"
for fn in sys.argv[1:]:
    d = bytearray(open(fn, "rb").read())
    h, s = off(d, HOOK), off(d, VA)
    if bytes(d[h:h + 6]) == JMP and bytes(d[s:s + len(STUB)]) == STUB:
        print(f"{fn}: F46 already applied"); continue
    assert bytes(d[h:h + 6]) == ORIG, f"{fn}: unexpected bytes at {HOOK:#x}: {bytes(d[h:h + 6]).hex()}"
    assert d[s:s + 0x60] == bytes(0x60), f"{fn}: stub area {VA:#x} not free"
    f40 = off(d, F40_STUB)
    blk = bytes(d[f40:f40 + 0x30])
    i = blk.find(F40_CMP_OLD)
    assert i >= 0, f"{fn}: F40 stub not found at {F40_STUB:#x} (apply F40 first)"
    shutil.copy(fn, fn + ".before_f46")
    d[s:s + len(STUB)] = STUB
    d[h:h + 6] = JMP
    d[f40 + i:f40 + i + 3] = F40_CMP_NEW
    open(fn, "wb").write(d)
    print(f"{fn}: F46 applied ({len(STUB)}-byte stub at {VA:#x}, {FRAME_MS} ms per frame; F40 gate opened)")
