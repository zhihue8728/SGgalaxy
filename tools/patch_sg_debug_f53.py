"""F53 PACKET KEY (2026-11-02, user 13:42 "固定密钥改成@iloveyou").
The packet cipher's key is the 9-byte string at .data 0x6b6908 (original "NexonInc."): the key setup 005a9e80 takes its
strlen as the key length L and copies it 4 times into the key buffer 0xd69274 (sgproto.py has the same cipher).
F53 writes sgproto.KEY there (same length, so nothing else moves).  .data is not in the F16 code checksum, so the
client's checksum - and the server's version table - stay the same; the server tells the keys apart by trying them
(sgs/core_net.py Session.rx_decode).  The other "NexonInc." in .data (0x6b4330) is not used by the cipher - left alone.
Needs F52 (the chain); idempotent.
usage: python patch_sg_debug_f53.py SG.exe [more exes]"""
import sys, os, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import patch_sg_debug_f49 as F49
import patch_sg_debug_f52 as F52
from sgproto import KEY, OLD_KEY

KEY_VA = 0x6b6908
assert len(KEY) == len(OLD_KEY) == 9

def apply(fn):
    d = bytearray(open(fn, "rb").read())
    o = F49.off(d, KEY_VA)
    cur = bytes(d[o:o + 10])
    if cur == KEY + b"\0":
        print(f"{fn}: F53 already applied"); return
    f52 = F49.off(d, F52.STUB_VA)
    assert bytes(d[f52:f52 + len(F52.STUB)]) == F52.STUB, f"{fn}: apply F52 first"
    assert cur == OLD_KEY + b"\0", f"{fn}: unexpected bytes at {KEY_VA:#x}: {cur!r}"
    shutil.copy(fn, fn + ".before_f53")
    d[o:o + len(KEY)] = KEY
    open(fn, "wb").write(d)
    print(f"{fn}: F53 applied (packet key {KEY!r} at {KEY_VA:#x})")

if __name__ == "__main__":
    for fn in sys.argv[1:]:
        apply(fn)
