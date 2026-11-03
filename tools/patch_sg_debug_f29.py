#!/usr/bin/env python3
"""F29 NO-HEALTH CRASH (2026-10-23): "DeployedUnitHealthSum is zero" + OK crashed the client.
usage: patch_sg_debug_f29.py SG.exe SG_debug.exe   (= F27 + F29; F28 timeBeginPeriod is NOT in the shipped client)
A commander whose deployed units all have 0 HP walks into a province gate: the portal handler 004d0b30 calls the check
004c6900 -> 0051cbb0, which shows the message box (string 0x656844, translated by build_i18n_exe.py) and then sends
the hero to the portal of type 2 (0049adc0(2), path 0056bbd0, move 004dc100).  The client crashed after OK in that
walk.  F29: right after the message box (0051cc56) jump to the function's cleanup + `return 1` (0051ccd6) - the gate
is still refused (caller 004c695c returns 0), the message stays, the hero is not moved.  2 bytes: EB 7E."""
import os, struct, subprocess, sys, tempfile
src, dst = sys.argv[1], sys.argv[2]
here = os.path.dirname(os.path.abspath(__file__))
tmp = os.path.join(tempfile.gettempdir(), "sg_f27_tmp29.exe")
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
SITE, CLEANUP = 0x51cc56, 0x51ccd6
assert d[off(SITE):off(SITE) + 5] == bytes.fromhex("a1d8a76b00"), "0051cc56 not found"
assert d[off(CLEANUP):off(CLEANUP) + 4] == bytes.fromhex("8d4c2410"), "0051ccd6 not found"
d[off(SITE):off(SITE) + 2] = bytes([0xEB, CLEANUP - (SITE + 2)])
open(dst, "wb").write(d)
print("F29 patched ->", dst)
