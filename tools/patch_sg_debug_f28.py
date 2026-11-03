#!/usr/bin/env python3
"""F28 TIMER 1 ms (2026-10-22): the client asks Windows for 1 ms timer resolution.
usage: patch_sg_debug_f28.py SG.exe SG_debug.exe   (= F27 + F28)
SG.exe times everything with timeGetTime / GetTickCount / Sleep but never calls timeBeginPeriod, so on a PC where no
other program raised the system timer the clock ticks every 15.6 ms: unit movement, command timestamps and the
lock-step clock advance in uneven steps.  F28 extends F27's connect hook (005a9890 -> 0xeb3e00): its last three
instructions (mov eax,[0x6ba840] / push 0x5a9895 / ret at 0xeb3e35) become `jmp 0xeb3e80`; the new stub calls
winmm!timeBeginPeriod(1) once (flag at 0xEAFF10, free page tail outside the checksum like F26's 0xEAFF08), resolved at
run time with LoadLibraryA("winmm") + GetProcAddress("timeBeginPeriod"), then runs the three original instructions."""
import os, struct, subprocess, sys, tempfile
from keystone import Ks, KS_ARCH_X86, KS_MODE_32
src, dst = sys.argv[1], sys.argv[2]
here = os.path.dirname(os.path.abspath(__file__))
tmp = os.path.join(tempfile.gettempdir(), "sg_f27_tmp.exe")
subprocess.check_call([sys.executable, os.path.join(here, "patch_sg_debug_f27.py"), src, tmp])
d = bytearray(open(tmp, "rb").read())
os.remove(tmp)
pe = struct.unpack_from('<I', d, 0x3c)[0]
nsec = struct.unpack_from('<H', d, pe + 6)[0]
opt = struct.unpack_from('<H', d, pe + 20)[0]
ib = struct.unpack_from('<I', d, pe + 52)[0]
secs = [struct.unpack_from('<8sIIII', d, pe + 24 + opt + 40 * i) for i in range(nsec)]
def off(va):
    for name, vs, vaa, rs, ra in secs:
        if vaa <= va - ib < vaa + max(vs, rs):
            return va - ib - vaa + ra
    raise ValueError(hex(va))
TAIL, BASE = 0xeb3e35, 0xeb3e80
LOADLIB, GETPROC, FLAG = 0x64c1b0, 0x64c1ac, 0xeaff10
S_WINMM, S_TBP = BASE + 0x60, BASE + 0x68
assert d[off(TAIL):off(TAIL) + 11] == bytes.fromhex("a140a86b00" "6895985a00" "c3"), "F27 tail not found"
assert not any(d[off(BASE):off(BASE) + 0x90]), "0xeb3e80 not free"
ks = Ks(KS_ARCH_X86, KS_MODE_32)
code, _ = ks.asm(f"""
    pushfd
    pushad
    cmp dword ptr [{FLAG}], 0
    jne done
    mov dword ptr [{FLAG}], 1
    push {S_WINMM}
    call dword ptr [{LOADLIB}]
    test eax, eax
    jz done
    push {S_TBP}
    push eax
    call dword ptr [{GETPROC}]
    test eax, eax
    jz done
    push 1
    call eax
done:
    popad
    popfd
    mov eax, dword ptr [0x6ba840]
    push 0x5a9895
    ret
""", BASE)
code = bytes(code)
assert len(code) < 0x60, len(code)
blob = code.ljust(0x60, b"\xcc") + b"winmm\0\0\0" + b"timeBeginPeriod\0"
d[off(BASE):off(BASE) + len(blob)] = blob
d[off(TAIL)] = 0xE9
struct.pack_into('<i', d, off(TAIL) + 1, BASE - (TAIL + 5))
open(dst, "wb").write(d)
print("F28 patched ->", dst, f"({len(code)} bytes at {BASE:#x})")
