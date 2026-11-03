#!/usr/bin/env python3
"""F26 MAP TAB STAYS (2026-10-22): province info (0x2e) no longer switches the WAR / BATTLE / USERS tab on a refresh.
usage: patch_sg_debug_f26.py SG.exe SG_debug.exe   (= F25 + F26)
00437370 (new 0x2e info) always picked a tab: 3 BATTLE (battle there), 2 USERS (users listed), 4 WAR (no record) -
so the server's 30 s cave-status push and REFRESH jumped to USERS.  Hook at 004375ee: when the info is for the SAME
province as the last one and a tab is already selected ([edi+0x3a4] != 0), skip the auto-select (-> 00437658).
The last province id is kept at 0xEAFF08 (free page tail after .data, outside the checksum, like F22's 0xEAFF00)."""
import os, struct, subprocess, sys, tempfile
from keystone import Ks, KS_ARCH_X86, KS_MODE_32
src, dst = sys.argv[1], sys.argv[2]
here = os.path.dirname(os.path.abspath(__file__))
tmp = os.path.join(tempfile.gettempdir(), "sg_f25_tmp.exe")
subprocess.check_call([sys.executable, os.path.join(here, "patch_sg_debug_f25.py"), src, tmp])
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
SITE, BASE = 0x4375ee, 0xeb3d80
assert d[off(SITE):off(SITE) + 6] == bytes.fromhex("8b0dc8a76b00"), "004375ee: mov ecx,[0x6ba7c8] expected"
assert not any(d[off(BASE):off(BASE) + 0x60]), "0xeb3d80 not free"
ks = Ks(KS_ARCH_X86, KS_MODE_32)
code, _ = ks.asm("""
    mov ecx, dword ptr [esi+4]
    cmp ecx, dword ptr [0xeaff08]
    mov dword ptr [0xeaff08], ecx
    jne changed
    cmp dword ptr [edi+0x3a4], 0
    je changed
    push 0x437658
    ret
changed:
    mov ecx, dword ptr [0x6ba7c8]
    push 0x4375f4
    ret
""", BASE)
d[off(BASE):off(BASE) + len(code)] = bytes(code)
d[off(SITE)] = 0xE9
struct.pack_into('<i', d, off(SITE) + 1, BASE - (SITE + 5))
d[off(SITE) + 5] = 0x90
open(dst, "wb").write(d)
print("F26 patched ->", dst, f"({len(code)} bytes at {BASE:#x})")
