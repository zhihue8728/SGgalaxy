#!/usr/bin/env python3
"""F25 EARLY LANGUAGE (2026-10-22): the client tells the server its code page BEFORE the game.
usage: patch_sg_debug_f25.py SG.exe SG_debug.exe   (= F24 + F25)
The 0xF6 report (code checksum + patch version + GetACP, F16/F18) was only sent after the in-game keep-alive, so the
New-commander screen (nation names, intros, planet names) was built in English.  F25 sends the same 0xF6 right before
the login (0x03), register (0x02), nation table (0x0F) and start-planet list (0x42) requests.  Patch version 0x19."""
import os, struct, subprocess, sys, tempfile
from keystone import Ks, KS_ARCH_X86, KS_MODE_32
src, dst = sys.argv[1], sys.argv[2]
here = os.path.dirname(os.path.abspath(__file__))
tmp = os.path.join(tempfile.gettempdir(), "sg_f24_tmp.exe")
subprocess.check_call([sys.executable, os.path.join(here, "patch_sg_debug_f24.py"), src, tmp])
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
BASE = 0xeb3c00                       # free tail of .dbgmov (F1..F22 end at 0xeb3bde)
assert not any(d[off(BASE):off(BASE) + 0x300]), "space at 0xeb3c00 not free"
SITES = [(0x4330da, 0x03, 0x10), (0x59de09, 0x03, 0x10), (0x5a16b4, 0x02, 0x14),
         (0x547838, 0x0f, 0x04), (0x5561a8, 0x42, 0x04), (0x597f08, 0x42, 0x04)]
F6 = BASE + 32 * len(SITES)          # send_f6; each site stub takes 32 bytes
ks = Ks(KS_ARCH_X86, KS_MODE_32)
stubs = []
for i, (site, typ, disp) in enumerate(SITES):
    assert d[off(site):off(site) + 6] == bytes([0x6a, typ, 0x8d, 0x4c, 0x24, disp]), hex(site)
    c, _ = ks.asm(f"call {F6}; push {typ}; lea ecx, [esp+{disp}]; push {site + 6}; ret", BASE + 32 * i)
    assert len(c) <= 32
    stubs.append(bytes(c).ljust(32, b"\xcc"))
asm = ""
asm += """
send_f6:
    pushfd
    pushad
    xor eax, eax
    mov esi, 0x401000
    mov ecx, 0x928ef
h1:
    rol eax, 5
    xor eax, dword ptr [esi]
    add esi, 4
    dec ecx
    jnz h1
    mov esi, 0xeb3000
    mov ecx, 0x800
h2:
    rol eax, 5
    xor eax, dword ptr [esi]
    add esi, 4
    dec ecx
    jnz h2
    mov ebx, eax
    sub esp, 0x60
    lea ecx, [esp]
    call 0x5a8ee0
    mov dword ptr [esp], 0x64c738
    push 0xF6
    lea ecx, [esp+4]
    call 0x5a8f80
    push ebx
    lea ecx, [esp+4]
    call 0x5a9070
    push 0x19
    lea ecx, [esp+4]
    call 0x5a9070
    call dword ptr [0x64c0a8]
    push eax
    lea ecx, [esp+4]
    call 0x5a9070
    lea ecx, [esp]
    call 0x5aa1e0
    lea ecx, [esp]
    call 0x5a8f50
    add esp, 0x60
    popad
    popfd
    ret
"""
code, _ = ks.asm(asm, F6)
code = b"".join(stubs) + bytes(code)
assert len(code) < 0x300
d[off(BASE):off(BASE) + len(code)] = code
for i, (site, typ, disp) in enumerate(SITES):
    d[off(site)] = 0xE9
    struct.pack_into('<i', d, off(site) + 1, BASE + 32 * i - (site + 5))
    d[off(site) + 5] = 0x90
open(dst, "wb").write(d)
print("F25 patched ->", dst, f"({len(code)} bytes at {BASE:#x})")
