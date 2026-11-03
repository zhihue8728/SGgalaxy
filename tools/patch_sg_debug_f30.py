#!/usr/bin/env python3
"""F30 NPC ALLIES / CRASH GUARDS (2026-10-23): usage: patch_sg_debug_f30.py SG.exe SG_debug.exe   (= F29 + F30)
Windows error reports of the player's crashes:
  * 12:31 / 12:47 / 13:36 - 0xC000000D at 00609e0f (CRT _invalid_parameter_noinfo -> Watson, process killed).  Each time
    units of the player's OWN side owned by an NPC commander were on the map (NPC allies).  Some secure CRT call
    (strcpy_s / sprintf_s ...) gets an invalid argument for such a unit.  With no handler installed the CRT kills the
    process.  F30: 00609df5 (`push 2; call _crt_debugger_hook...`) -> `pop ebp; ret`: the CRT function returns EINVAL
    (empty / truncated string) instead of terminating - what _set_invalid_parameter_handler(noop) would do.
  * 13:20 - 0xC0000005 at 004adaa8 (FUN_004ad690, the per-frame loop over the unit manager list [0x6ba7d4]+0x30):
    a NULL slot (or NULL list) was dereferenced right after the "DeployedUnitHealthSum is zero" box.  F30 rewrites
    004ada91..004adaae so NULL list / NULL entry / index past the count are skipped."""
import os, struct, subprocess, sys, tempfile
from keystone import Ks, KS_ARCH_X86, KS_MODE_32
src, dst = sys.argv[1], sys.argv[2]
here = os.path.dirname(os.path.abspath(__file__))
tmp = os.path.join(tempfile.gettempdir(), "sg_f29_tmp30.exe")
subprocess.check_call([sys.executable, os.path.join(here, "patch_sg_debug_f29.py"), src, tmp])
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
# 1. invalid parameter: return instead of Watson
A = 0x609df5
assert d[off(A):off(A) + 2] == bytes([0x6a, 0x02]), "00609df5 not found"
d[off(A):off(A) + 2] = bytes([0x5d, 0xc3])
# 2. unit list loop NULL guard
L0, L1 = 0x4ada91, 0x4adaaf
orig = bytes(d[off(L0):off(L1)])
assert orig.startswith(bytes.fromhex("8b4130")) and orig.endswith(bytes.fromhex("8b118b4204ffd0")), orig.hex()
ks = Ks(KS_ARCH_X86, KS_MODE_32)
code, _ = ks.asm(f"""
    mov eax, dword ptr [ecx+0x30]
    test eax, eax
    je {L1}
    cmp esi, dword ptr [ecx+0x28]
    jge {L1}
    mov ecx, dword ptr [eax+esi*4]
    test ecx, ecx
    je {L1}
    mov edx, dword ptr [ecx]
    mov eax, dword ptr [edx+4]
    call eax
""", L0)
code = bytes(code)
n = L1 - L0
assert len(code) <= n, (len(code), n)
# the call must end exactly at L1 (its return address): put the NOPs FIRST
code = b"\x90" * (n - len(code)) + bytes(ks.asm(f"""
    mov eax, dword ptr [ecx+0x30]
    test eax, eax
    je {L1}
    cmp esi, dword ptr [ecx+0x28]
    jge {L1}
    mov ecx, dword ptr [eax+esi*4]
    test ecx, ecx
    je {L1}
    mov edx, dword ptr [ecx]
    mov eax, dword ptr [edx+4]
    call eax
""", L0 + (n - len(code)))[0])
assert len(code) == n
d[off(L0):off(L1)] = code
open(dst, "wb").write(d)
print("F30 patched ->", dst)
