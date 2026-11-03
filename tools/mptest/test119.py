"""test119 (user 2026-11-02 13:42 "固定密钥改成@iloveyou"): packet key.  sgproto.KEY = @iloveyou (F53 clients), OLD_KEY =
NexonInc. (clients built before F53).  The server finds each connection's key from the client's first encrypted packet and
answers with it; both kinds of client play side by side; the old key's cipher is unchanged byte for byte."""
import asyncio, struct, sys, os, random
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
import sgproto as P
from mpclient import Client
S.LOG = open('/tmp/mp/server119.log', 'w', encoding='utf-8')
PORT = 3919
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)

async def main():
    chk('KEY is @iloveyou, same length as the old key', P.KEY == b'@iloveyou' and len(P.KEY) == len(P.OLD_KEY) == 9)
    random.seed(7); ok = True
    for i in range(500):
        m = bytes([random.randrange(7, 256)]) + bytes(random.randrange(256) for _ in range(random.randrange(1, 200)))
        for k in P.KEYS:
            e = P.Cipher(random.randrange(256), key=k).encode(m)
            ok &= P.Cipher.decode(e, k) == m
    chk('round trip with both keys', ok)
    e = P.Cipher(5, key=P.KEY).encode(b'\x03' + bytes(range(40)))
    try:
        P.Cipher.decode(e, P.OLD_KEY); chk('new-key packet fails with the old key', False)
    except ValueError:
        chk('new-key packet fails with the old key', True)
    S.ensure_unique_unit_ids()
    srv = await asyncio.start_server(S.handle, '127.0.0.1', PORT)
    A = Client('jjjjjjjj')                       # new client
    B = Client('kkkkkkkk', key=P.OLD_KEY)        # old client
    await A.connect(PORT); await A.login(); await B.connect(PORT); await B.login(); await asyncio.sleep(1.2)
    sa = next(o for o in S.ONLINE if getattr(o, 'acc', '') == 'jjjjjjjj')
    sb = next(o for o in S.ONLINE if getattr(o, 'acc', '') == 'kkkkkkkk')
    chk('new client: connection key = KEY', sa.ckey == P.KEY and sa.cipher.key == P.KEY, sa.ckey)
    chk('old client: connection key = OLD_KEY', sb.ckey == P.OLD_KEY and sb.cipher.key == P.OLD_KEY, sb.ckey)
    chk('both logged in', getattr(sa, 'logged_in', False) and getattr(sb, 'logged_in', False))
    chk('new client could decode every server packet', A.bad == 0 and len(A.inbox) > 3, (A.bad, len(A.inbox)))
    chk('old client could decode every server packet', B.bad == 0 and len(B.inbox) > 3, (B.bad, len(B.inbox)))
    # chat between them goes out with each one's own key
    n0a, n0b = len(A.inbox), len(B.inbox)
    A.send(bytes([0x2a, 0]) + S._s8('hello from new') + bytes([255, 255, 255])); await asyncio.sleep(0.6)
    B.send(bytes([0x2a, 0]) + S._s8('hello from old') + bytes([255, 255, 255])); await asyncio.sleep(0.6)
    chk('traffic after login still decodes on both', A.bad == 0 and B.bad == 0 and len(A.inbox) > n0a and len(B.inbox) > n0b,
        (A.bad, B.bad))
    S.LOG.flush(); log = open('/tmp/mp/server119.log', encoding='utf-8').read()
    chk('no decode failure logged', 'decode failed' not in log)
    chk('no encrypted packet before the key was known', 'before the client' not in log)
    chk('old client noted in the log', 'packet key: OLD' in log)
    A.close(); B.close(); srv.close()
asyncio.run(main())
