#!/usr/bin/env python3
"""F23 SERVER ADDRESS (2026-10-22): the client connects to the IP in the registry, no hosts file needed.
usage: patch_sg_debug_f23.py SG.exe SG_debug.exe   (= F22 + F23)

Original start-up (004300d0): default 64.124.47.70:3000 -> read HKLM\\SOFTWARE\\Nexon\\TacticalCommanders REG_SG_IP
(0042f540) -> ALWAYS resolve sg0.kru.com (0042fff0), which overwrote the registry IP (or reset it to 64.124.47.70).
  * 00430152 jne 0x43015b -> jne 0x430162: REG_SG_IP read ok -> sg0.kru.com is not resolved.  (If the connect to
    that IP fails, 005a159e still falls back to sg0.kru.com once, because [+0xb18] stays 0.)
  * 0042f565 / 0042e2a2 push HKLM -> push HKCU: the launcher writes HKCU\\SOFTWARE\\Nexon\\TacticalCommanders
    REG_SG_IP = "a.b.c.d" without administrator rights (the client also saves the chosen server there).
Port stays 3000 (0xbb8)."""
import os, subprocess, sys, tempfile
src, dst = sys.argv[1], sys.argv[2]
here = os.path.dirname(os.path.abspath(__file__))
tmp = os.path.join(tempfile.gettempdir(), "sg_f22_tmp.exe")
subprocess.check_call([sys.executable, os.path.join(here, "patch_sg_debug_f22.py"), src, tmp])
d = bytearray(open(tmp, "rb").read())
os.remove(tmp)
def put(foff, old, new):
    old, new = bytes.fromhex(old), bytes.fromhex(new)
    assert d[foff:foff + len(old)] == old, (hex(foff), d[foff:foff + len(old)].hex())
    d[foff:foff + len(new)] = new
put(0x30152, "7507", "750e")              # 00430152: skip sg0.kru.com when REG_SG_IP was read
put(0x2f565, "6802000080", "6801000080")  # 0042f565: read REG_SG_IP from HKCU
put(0x2e2a2, "6802000080", "6801000080")  # 0042e2a2: write REG_SG_IP to HKCU
open(dst, "wb").write(d)
print("F23 patched ->", dst)
