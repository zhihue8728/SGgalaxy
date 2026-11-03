import asyncio, struct, time
from sgproto import Cipher, frame, parse_frames, CLIENT_PLAIN, SERVER_PLAIN, KEY
import sgnet          # (2026-11-02) the encrypted connection, like the game's ddraw.dll: SGX1 hello, then AES-128-CTR

def s8(t): b = t.encode('latin-1'); return bytes([len(b)]) + b

class Client:
    def __init__(self, name, pw='ji3g4go6', key=KEY):
        self.name, self.pw, self.key = name, pw, key          # key: sgproto.OLD_KEY = a client built before F53
        self.cipher = Cipher(key=key); self.inbox = []; self.t0 = time.monotonic(); self.bad = 0
    async def connect(self, port, sgx=True):
        """sgx=False: a client without the encrypted connection (an old ddraw.dll) - the server must close it"""
        self.r, self.w = await asyncio.open_connection('127.0.0.1', port)
        self.enc = self.dec = lambda b: b
        if sgx:
            priv, _ = sgnet.load_server_key()          # tests: SG_NETKEY_FILE (run_tests.py makes a test key)
            hello, self.enc, self.dec = sgnet.client_hello(sgnet.raw_pub(priv))
            self.w.write(hello)
        self.task = asyncio.get_event_loop().create_task(self._read())
    async def _read(self):
        buf = b''
        try:
            while True:
                c = await self.r.read(65536)
                if not c: break
                buf += self.dec(c)
                ps, buf = parse_frames(buf)
                for p in ps:
                    if p[0] in SERVER_PLAIN or p[:6] == b'SERVER':
                        body = p
                    else:
                        try: body = Cipher.decode(p, self.key)
                        except Exception: body = p; self.bad += 1     # (the real client would exit here)
                    self.inbox.append((time.monotonic(), body))
        except Exception as e:
            self.inbox.append((time.monotonic(), b'\xff' + repr(e).encode()))
    def send(self, body):
        data = body if body[0] in CLIENT_PLAIN else self.cipher.encode(body)
        self.w.write(self.enc(frame(data)))
    def lumps(self, *msgs):
        self.send(bytes([0x80, 0, 0]) + struct.pack('>H', len(msgs)) + b''.join(struct.pack('>H', len(m)) + m for m in msgs))
    async def login(self):
        self.send(bytes([3]) + s8(self.name) + s8(self.pw) + bytes.fromhex('010c1ee56b0002060200'))
        await asyncio.sleep(0.5)
        self.send(bytes.fromhex('58003036f400'))     # keepalive -> enters the capital
        await asyncio.sleep(0.5)
    def close(self): self.w.close()
    # ---- inspection helpers
    def got(self, t, since=0):
        return [b for ts, b in self.inbox if b[0] == t and ts >= since]
    def lump_msgs(self, since=0):
        out = []
        for ts, b in self.inbox:
            if b[0] == 0x80 and ts >= since and len(b) >= 9:
                tick, n = struct.unpack_from('>IH', b, 3); o = 9
                for _ in range(n):
                    ln = struct.unpack_from('>H', b, o)[0]; out.append((tick, b[o + 2:o + 2 + ln])); o += 2 + ln
        return out
    def puts(self, since=0):
        """0x18 / 0x50 PUT_UNIT -> [(uid, name, owner)]"""
        res = []
        for b in self.got(0x18, since):
            o = 5; n1 = b[o]; name = b[o+1:o+1+n1].decode('latin-1'); o += 1 + n1
            n2 = b[o]; owner = b[o+1:o+1+n2].decode('latin-1'); o += 1 + n2
            # uid after fixed block: find via layout: hp,en(4)+1+4+1+18+2+8 then u8 n skills*5
            o2 = o + 4 + 1 + 4 + 1 + 18 + 2 + 8
            ns = b[o2]; o2 += 1 + 5 * ns
            uid = struct.unpack_from('>I', b, o2)[0]
            res.append((uid, name, owner, struct.unpack_from('>I', b, o2 + 4)[0]))
        return res
