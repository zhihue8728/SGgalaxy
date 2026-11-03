#!/usr/bin/env python3
"""F31 MINIMAP ALLY COLOUR (2026-10-23 21:49, user: own units bright green, ALLIES must be YELLOW on the battle minimap,
enemies red).  usage: patch_sg_debug_f31.py SG.exe SG_debug.exe   (= F30 + F31)
Battle minimap painter 005b66d0 (reversed 2026-10-23): it builds a colour table once (flags 0xd6931c):
  0xd69318 green (own)   0xd69314 blue    0xd69310 yellow   0xd6930c yellow   0xd69308 blue   0xd69304 red   0xd69300 black
and per unit (loop 005b6930): friendly flag unit+0x69 -> 0x5093a0(unit+0xb9) ? 0xd69314 (BLUE = allied commander's units)
: 0xd69318 (GREEN = own); others -> red (visible enemy) / blue / yellow (special cases).
F31 (v2): own units 005b6a44 [0xd69314] blue -> [0xd69318] green; allied units 005b6aae [0xd69318] green -> [0xd69310] yellow.
Changes .text -> new client checksum (anti-cheat version table: deploy SG_debug.exe + publish the OTA release)."""
import os, struct, subprocess, sys, tempfile
src, dst = sys.argv[1], sys.argv[2]
here = os.path.dirname(os.path.abspath(__file__))
tmp = os.path.join(tempfile.gettempdir(), "sg_f30_tmp31.exe")
subprocess.check_call([sys.executable, os.path.join(here, "patch_sg_debug_f30.py"), src, tmp])
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
# v2 (22:23, screenshot: the player's OWN units turned yellow): 0x5093a0(unit+0xb9) is "owned by ME" - the original
# draws OWN units BLUE (0xd69314) and ALLIED units GREEN (0xd69318).  Wanted: own green, allies yellow, enemies red.
A = 0x5b6a44                             # own units:    [0xd69314] blue  -> [0xd69318] green
assert d[off(A):off(A) + 7] == bytes.fromhex("0fb7351493d600"), d[off(A):off(A) + 7].hex()
d[off(A) + 3] = 0x18
B = 0x5b6aae                             # allied units: [0xd69318] green -> [0xd69310] yellow
assert d[off(B):off(B) + 7] == bytes.fromhex("0fb7351893d600"), d[off(B):off(B) + 7].hex()
d[off(B) + 3] = 0x10
open(dst, "wb").write(d)
print("F31 patched ->", dst)
