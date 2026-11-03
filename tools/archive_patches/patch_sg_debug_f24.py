#!/usr/bin/env python3
"""F24 LOGIN DIGITS (2026-10-22): the login ID / password boxes were letters-only.
usage: patch_sg_debug_f24.py SG.exe SG_debug.exe   (= F23 + F24)
The edit box char handler 0043f470 has a 'letters only' mode (box flag 0x400): only backspace, a-z, A-Z (0043f511..
0043f52c), used by the login boxes, so an ID like SG001 or a password with digits / symbols could not be typed.
0043f515 je 0x43f52e -> jmp 0x43f52e: every box takes printable ASCII 0x20..0x7e (and Chinese via F22).
The server still only accepts account names [A-Za-z][A-Za-z0-9_]{2,15} at registration."""
import os, subprocess, sys, tempfile
src, dst = sys.argv[1], sys.argv[2]
here = os.path.dirname(os.path.abspath(__file__))
tmp = os.path.join(tempfile.gettempdir(), "sg_f23_tmp.exe")
subprocess.check_call([sys.executable, os.path.join(here, "patch_sg_debug_f23.py"), src, tmp])
d = bytearray(open(tmp, "rb").read())
os.remove(tmp)
def put(foff, old, new):
    old, new = bytes.fromhex(old), bytes.fromhex(new)
    assert d[foff:foff + len(old)] == old, (hex(foff), d[foff:foff + len(old)].hex())
    d[foff:foff + len(new)] = new
put(0x3f515, "7417", "eb17")              # 0043f515: letters-only mode -> normal printable-ASCII path
open(dst, "wb").write(d)
print("F24 patched ->", dst)
