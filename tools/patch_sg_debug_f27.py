#!/usr/bin/env python3
"""F27 TCP_NODELAY (2026-10-22): the client sends its commands without Nagle's algorithm.
usage: patch_sg_debug_f27.py SG.exe SG_debug.exe   (= F26 + F27)
User 2026-10-22 22:47: "sending commands is not smooth, units stutter".  SG.exe never calls setsockopt (WSOCK32 import
table: socket 23, connect 4, send 19, recv 16, WSAAsyncSelect 101 ...), so Windows' default Nagle algorithm holds every
small packet while an earlier one is not ACKed yet: a move order sent right after a position report waits one RTT
(+ the server's delayed ACK).  F27 hooks the successful connect() in the client's socket class (005a9890, right after
`test eax,eax / je` of the call at 005a9869; ebp = CSocket, [ebp+8] = the socket) and calls
setsockopt(sock, IPPROTO_TCP, TCP_NODELAY, &1, 4).  The function is resolved at run time (LoadLibraryA("wsock32") +
GetProcAddress(h, 21)) because setsockopt is not in the import table; both are imported by the exe.
The stub lives at 0xeb3e00 in .dbgmov (inside the code checksum, so the checksum of the client changes)."""
import os, struct, subprocess, sys, tempfile
from keystone import Ks, KS_ARCH_X86, KS_MODE_32
src, dst = sys.argv[1], sys.argv[2]
here = os.path.dirname(os.path.abspath(__file__))
tmp = os.path.join(tempfile.gettempdir(), "sg_f26_tmp.exe")
subprocess.check_call([sys.executable, os.path.join(here, "patch_sg_debug_f26.py"), src, tmp])
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
SITE, BASE = 0x5a9890, 0xeb3e00
LOADLIB, GETPROC = 0x64c1b0, 0x64c1ac            # IAT slots of KERNEL32 LoadLibraryA / GetProcAddress
STR = BASE + 0x60
assert d[off(SITE):off(SITE) + 5] == bytes.fromhex("a140a86b00"), "005a9890: mov eax,[0x6ba840] expected"
assert not any(d[off(BASE):off(BASE) + 0x80]), "0xeb3e00 not free"
ks = Ks(KS_ARCH_X86, KS_MODE_32)
code, _ = ks.asm(f"""
    pushfd
    pushad
    push 1
    push {STR}
    call dword ptr [{LOADLIB}]
    test eax, eax
    jz done
    push 21
    push eax
    call dword ptr [{GETPROC}]
    test eax, eax
    jz done
    mov ebx, eax
    mov edx, esp
    push 4
    push edx
    push 1
    push 6
    push dword ptr [ebp+8]
    call ebx
done:
    add esp, 4
    popad
    popfd
    mov eax, dword ptr [0x6ba840]
    push 0x5a9895
    ret
""", BASE)
code = bytes(code)
assert len(code) < 0x60, len(code)
blob = code.ljust(0x60, b"\xcc") + b"wsock32\0"
d[off(BASE):off(BASE) + len(blob)] = blob
d[off(SITE)] = 0xE9
struct.pack_into('<i', d, off(SITE) + 1, BASE - (SITE + 5))
open(dst, "wb").write(d)
print("F27 patched ->", dst, f"({len(code)} bytes at {BASE:#x}, string at {STR:#x})")
