import asyncio, struct, sys, os, time
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
from mpclient import Client, s8
S.LOG = open('/tmp/mp/server13.log', 'w', encoding='utf-8')
PORT = 3997
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
def G(X, ty, t): return [m[1:] for m in X.got(ty, t)]
def r8(b, o): n = b[o]; return b[o+1:o+1+n].decode('latin-1'), o+1+n
async def main():
    S.ensure_unique_unit_ids()
    srv = await asyncio.start_server(S.handle, '127.0.0.1', PORT)
    A, B = Client('jjjjjjjj'), Client('kkkkkkkk')
    for X in (A, B):
        await X.connect(PORT); await X.login()
    # --- user info of another player: 0x23 [02][s8 name]
    t = time.monotonic(); A.send(bytes([0x23, 2]) + s8('kkkkkkkk')); await asyncio.sleep(0.4)
    g = G(A, 0x27, t)
    ok = bool(g) and g[-1][0] == 1
    if ok:
        b = g[-1]; nm, o = r8(b, 1); ok = nm == 'kkkkkkkk'
        o += 1 + 4 + 2; title, o = r8(b, o); o += 1
        for _ in range(4):
            o += 1; _r, o = r8(b, o); o += 2 + 8
        o += 1 + 12; n = b[o]; o += 1
        for _ in range(n): o += 4; _t, o = r8(b, o)
        o += 4; sup, o = r8(b, o); ln = struct.unpack_from('>H', b, o)[0]; o += 2 + ln
        chk('0x27 sub 1 parses to the end', o == len(b), (o, len(b)))
    chk('user info by name', ok, g and g[-1][:12].hex())
    # --- word of honor: A asks B
    t = time.monotonic(); A.send(bytes([0x55, 0, 0]) + s8('kkkkkkkk')); await asyncio.sleep(0.4)
    g = G(B, 0x54, t); chk('B is asked (0x54 05)', g and g[0][:2] == bytes([5, 0]) and r8(g[0], 2)[0] == 'jjjjjjjj', g)
    t = time.monotonic(); B.send(bytes([0x55, 3, 1]) + s8('jjjjjjjj')); await asyncio.sleep(0.4)
    g = G(A, 0x54, t); chk('A told accepted (0x54 06 01 name)', g and g[0][:2] == bytes([6, 1]) and r8(g[0], 2)[0] == 'kkkkkkkk', g)
    chk('superior stored', S.load_accounts()['jjjjjjjj']['commander'].get('superior') == 'kkkkkkkk')
    g = G(A, 0x27, t); chk('F4 refreshed with the superior', bool(g) and b'kkkkkkkk' in g[-1])
    # offline / missing target -> busy reply (client would otherwise wait 30 s)
    t = time.monotonic(); A.send(bytes([0x55, 0, 0]) + s8('nobodyxx')); await asyncio.sleep(0.3)
    g = G(A, 0x54, t); chk('missing target -> 0x54 06 02', g and g[0][:2] == bytes([6, 2]), g)
    # release
    t = time.monotonic(); A.send(bytes([0x5C, 0]) + s8('kkkkkkkk')); await asyncio.sleep(0.3)
    chk('word released', S.load_accounts()['jjjjjjjj']['commander'].get('superior') == '')
    # --- player search
    t = time.monotonic(); A.send(bytes([0x57]) + s8('kkkk')); await asyncio.sleep(0.3)
    chk('search -> 0x3b entry', bool(G(A, 0x3B, t))); g = G(A, 0x54, t)
    chk('search -> 0x54 00 row', g and g[0][0] == 0 and r8(g[0], 3)[0] == 'kkkkkkkk', g)
    # --- exchange
    t = time.monotonic(); A.send(bytes([0x34]) + struct.pack('>IB', 77, 1)); await asyncio.sleep(0.3)
    g = G(A, 0x34, t); chk('exchange rates 0x34 00', g and len(g[0]) == 29, g and len(g[0]))
    accs = S.load_accounts(); accs['jjjjjjjj']['resources'] = [1000, 10, 10, 10, 10]; S.save_accounts(accs)
    t = time.monotonic(); A.send(bytes([0x34]) + struct.pack('>IB4i', 77, 2, 10, -5, 0, 0)); await asyncio.sleep(0.4)
    g = G(A, 0x34, t); chk('exchange ok reply', g and g[-1] == bytes([1, 1]), g)
    r = S.load_accounts()['jjjjjjjj']['resources']
    cost = 10 * 4 - 5 * 6; fee = (40 + 30) // 3
    chk('resources updated', r[:3] == [1000 - cost - fee, 20, 5], r)
    t = time.monotonic(); A.send(bytes([0x34]) + struct.pack('>IB4i', 77, 2, 9000, 0, 0, 0)); await asyncio.sleep(0.3)
    g = G(A, 0x34, t); chk('too expensive refused', g and g[-1] == bytes([1, 0]), g)
    A.close(); B.close(); await asyncio.sleep(0.2)
asyncio.run(main())
