"""Shattered Galaxy v1.8.5 packet framing + cipher, recovered from SG.exe.
Sources: FUN_005a9240 (send), FUN_005a9340 (recv frame), FUN_005a8c80 (encode),
FUN_005a8ad0 (decode), FUN_005a8910 (xor), FUN_005a9e80 (key setup).

Frame on the wire:   0xAA | len16 (big endian) | payload[len]
Plain payload types (no cipher):
   client->server: 0,1,5,6,0xd     server->client: 0,3,0xb,0xc,0xd
Other payloads are encoded:  type | seq | body' | chk1 | chk2   (len+3 bytes for a len-byte original)
"""
import struct

# PACKET KEY (user 2026-11-02 13:42 "固定密钥改成@iloveyou").  The client reads it from .data 0x6b6908 (key setup
# 005a9e80: strlen, then 4 copies into the key buffer) - patch F53 (tools/patch_sg_debug_f53.py) writes KEY there.
# Same length as the original (9), so the frame format does not change.  Not covered by the F16 code checksum (.data).
# OLD_KEY: clients built before F53 (<= 1.0.89) still connect - the server finds a connection's key from the first
# encrypted packet the client sends (the client always sends one before the server's first encrypted packet).
KEY = b"@iloveyou"
OLD_KEY = b"NexonInc."
KEYS = (KEY, OLD_KEY)       # the order the server tries them
L = len(KEY)
KEYBUF = KEY * 4            # 36 bytes = 9 u32 words
_KW = {}


def key_words(key):
    """(words, L) of a key: the key tiled 4x read as len(key) u32 words (L = len(key) is also the block size)."""
    kw = _KW.get(key)
    if kw is None:
        kw = _KW[key] = (list(struct.unpack('<%dI' % len(key), key * 4)), len(key))
    return kw
MAX_LEN = 0x3FFDF
CLIENT_PLAIN = {0, 1, 5, 6, 0xD}
SERVER_PLAIN = {0, 3, 0xB, 0xC, 0xD}


def _xor_words(data: bytearray, keyw, nwords_mod):
    """FUN_005a8910 with a real key: xor u32 words with keyw[i % nwords_mod], tail bytewise."""
    n = len(data)
    nw = n >> 2
    for i in range(nw):
        k = keyw[i % nwords_mod]
        v = struct.unpack_from('<I', data, i * 4)[0] ^ k
        struct.pack_into('<I', data, i * 4, v)
    rem = n & 3
    if rem:
        k = keyw[nw % nwords_mod]
        kb = struct.pack('<I', k)
        for j in range(rem):
            data[nw * 4 + j] ^= kb[j]


KEYW = key_words(KEY)[0]


def _xor_byte(data: bytearray, b: int):
    for i in range(len(data)):
        data[i] ^= b


class Cipher:
    def __init__(self, seq=0, key=KEY):
        self.seq = seq & 0xFF           # DAT_00d69270 (send counter)
        self.set_key(key)

    def set_key(self, key):
        self.key = key
        self.kw, self.L = key_words(key)

    def encode(self, src: bytes) -> bytes:
        n = len(src)
        out = bytearray()
        out.append(src[0])
        seq = self.seq
        out.append(seq)
        self.seq = (seq + 1) & 0xFF
        chk_orig = sum(src) & 0xFF
        if n - 1 > 0:
            body = bytearray(src[1:])
            L = self.L
            _xor_words(body, self.kw, L)
            blocks = (n - 2) // L + 1
            for k in range(blocks):
                if (k & 0xFF) != seq:
                    _xor_byte_inplace(body, k * L, min((k + 1) * L, len(body)), k & 0xFF)
            _xor_byte(body, seq)
            out += body
            s = sum(out) & 0xFF
            out.append((-s) & 0xFF)
            out.append((-chk_orig) & 0xFF)
            out.append(0)
            return bytes(out[:n + 3])
        out.append(0)
        return bytes(out[:n + 1])

    @staticmethod
    def decode(src: bytes, key=KEY) -> bytes:
        kw, L = key_words(key)
        n = len(src)
        if n - 1 > 0 and (sum(src[:n - 1]) & 0xFF) != 0:
            raise ValueError("CheckSumError")
        seq = src[1]
        out = bytearray([src[0]])
        if n - 4 > 0:
            body = bytearray(src[2:2 + n - 4])
            _xor_byte(body, seq)
            blocks = (n - 5) // L + 1
            for k in range(blocks):
                if (k & 0xFF) != seq:
                    _xor_byte_inplace(body, k * L, min((k + 1) * L, len(body)), k & 0xFF)
            _xor_words(body, kw, L)
            out += body
        total = n - 3
        out = out[:total] if len(out) >= total else out
        if (src[n - 1] + sum(out[:total])) & 0xFF != 0:
            raise ValueError("CheckSumOrigError")
        return bytes(out)


def _xor_byte_inplace(buf, lo, hi, b):
    for i in range(lo, hi):
        buf[i] ^= b


def frame(payload: bytes) -> bytes:
    return b"\xAA" + struct.pack(">H", len(payload)) + payload


def parse_frames(buf: bytes):
    """Yield complete payloads from a byte stream; returns (payloads, remainder)."""
    out = []
    i = 0
    while len(buf) - i >= 3:
        if buf[i] != 0xAA:
            raise ValueError("bad magic at %d" % i)
        ln = struct.unpack_from(">H", buf, i + 1)[0]
        if len(buf) - i - 3 < ln:
            break
        out.append(buf[i + 3:i + 3 + ln])
        i += 3 + ln
    return out, buf[i:]


if __name__ == "__main__":
    import os
    c = Cipher()
    for n in [2, 3, 8, 9, 10, 17, 100, 1000, 5000]:   # n=1 is not decodable by the original client either
        for _ in range(20):
            msg = os.urandom(n)
            assert Cipher.decode(c.encode(msg)) == msg, n
    print("roundtrip ok")
