#!/usr/bin/env python3
"""F32 TOWN MINIMAP OWN DOT (2026-10-23 23:09, user screenshot: out of battle every dot on the minimap was yellow,
the player's own dot must be green).  usage: patch_sg_debug_f32.py SG.exe SG_debug.exe   (= F30 + F31 + F32)
Minimap painter 005b66d0, unit loop: friendly unit -> 005b6a21 cmp [win+0xa0e9],0 / je 005b6aae.  win+0xa0e9 is the
main window's BATTLE flag (set by 005b7230), so out of battle the "is it mine" test 0x5093a0(unit+0xb9) was skipped
and every friendly dot got the ally colour (original: all green; after F31: all yellow).
F32: 005b6a28 je (0f 84 80 00 00 00) -> 6 x NOP: the own test runs in town too -> own green, others yellow."""
import os, struct, subprocess, sys, tempfile
src, dst = sys.argv[1], sys.argv[2]
here = os.path.dirname(os.path.abspath(__file__))
tmp = os.path.join(tempfile.gettempdir(), "sg_f31_tmp32.exe")
subprocess.check_call([sys.executable, os.path.join(here, "patch_sg_debug_f31.py"), src, tmp])
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
A = 0x5b6a28
assert d[off(A):off(A) + 6] == bytes.fromhex("0f8480000000"), d[off(A):off(A) + 6].hex()
d[off(A):off(A) + 6] = b"\x90" * 6
open(dst, "wb").write(d)
print("F32 patched ->", dst)
