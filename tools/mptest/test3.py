import asyncio, struct, sys, os, time
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
from mpclient import Client, s8
S.LOG = open('/tmp/mp/server3.log', 'w', encoding='utf-8')
S.REINFORCE_COOLDOWN = 1; S.REINFORCE_DELAY = 50
PORT = 3997; MAP = 600300
def chk(name, ok, info=''): print(('PASS ' if ok else 'FAIL ') + name, info, flush=True)

async def join(X, cmdr, MAP, watch=False):
    t = time.monotonic()
    if watch:
        X.send(bytes([0x20, 13]) + struct.pack('>I', MAP))
    else:
        X.send(bytes([0x2e]) + struct.pack('>IHHBB', MAP, 0x100, 0x1c0, 2, 0)); await asyncio.sleep(0.5)
        X.send(bytes([0x1b, 1]) + struct.pack('>IHH', MAP, 0x100, 0x1c0))
    await asyncio.sleep(0.6)
    req = cmdr.got(0x24, t)
    if req:
        cmdr.send(bytes([0x20, req[-1][1] + 2]) + s8(X.name))
    await asyncio.sleep(1.2)
    return t

async def main():
    S.ensure_unique_unit_ids()
    srv = await asyncio.start_server(S.handle, '127.0.0.1', PORT)
    A, B, C = Client('jjjjjjjj'), Client('kkkkkkkk'), Client('llllllll')
    for X in (A, B, C):
        await X.connect(PORT); await X.login()
    t0 = time.monotonic()
    A.send(bytes([0x2e]) + struct.pack('>IHHBB', MAP, 0x100, 0x1c0, 2, 0)); await asyncio.sleep(1.0)
    Bt = S.BATTLES[MAP]
    tb = await join(B, A, MAP)
    chk('B joined', {o.acc for o in Bt['members']} == {'jjjjjjjj', 'kkkkkkkk'})
    # --- spectator C (other nation) watches
    tc = await join(C, A, MAP, watch=True)
    sc = next((o for o in S.ONLINE if getattr(o, 'acc', '') == 'llllllll'), None)
    chk('C entered as spectator', sc is not None and getattr(sc, 'spectator', False) and getattr(sc, 'map', None) == MAP,
        (getattr(sc, 'spectator', None), getattr(sc, 'map', None)))
    chk('C sees the battle (aliens put)', any(p[2] == 'Alien' for p in C.puts(tc)))
    chk('C puts no units of his own', not any(p[2] == 'llllllll' and p[0] > 1000 for p in A.puts(tc)))
    # --- F7 reinforcement for A (13 units, deploy limit 12 -> 1 in reserve)
    sa = Bt['owner']
    chk('A has a reserve', bool(getattr(sa, 'reserve', None)), getattr(sa, 'reserve', None))
    t1 = time.monotonic(); await asyncio.sleep(1.2)
    A.send(bytes([0x19, 0])); await asyncio.sleep(1.0)
    put50a = A.got(0x50, t1); put50b = B.got(0x50, t1)
    # all deploy slots are occupied and the cooldown is running -> F7 must be refused (the accepted case is test4)
    chk('F7 refused while the field is full (no 0x50)', len(put50a) == 0 and len(put50b) == 0, (len(put50a), len(put50b)))
    # --- retreat of one B unit
    ub = [p[0] for p in B.puts(tb) if p[2] == 'kkkkkkkk' and p[0] > 1000]
    t2 = time.monotonic()
    B.send(bytes([0x2f]) + struct.pack('>IHIiHHHH', ub[0], 0, 0, -1, 0x80, 0x80, 0x80, 0x80))
    await asyncio.sleep(0.8)
    rem_a = [b.hex() for b in A.got(0x19, t2)]
    chk('A told that B unit left (0x19)', any(int(h[2:10], 16) == ub[0] for h in rem_a), rem_a)
    # --- commander A disconnects mid-battle
    t3 = time.monotonic(); A.close(); await asyncio.sleep(1.5)
    chk('battle continues without A', MAP in S.BATTLES and Bt['owner'].acc == 'kkkkkkkk', Bt['owner'].acc)
    chk('B told A left (0x19 / 0xc5)', len(B.got(0xc5, t3)) >= 1 or len(B.got(0x19, t3)) >= 1)
    await asyncio.sleep(3)
    ai = [m for tk, m in B.lump_msgs(t3) if m[0] == 0x2b and struct.unpack_from('>I', m, 1)[0] >= 60001]
    chk('aliens still get attack orders after A left', len(ai) > 0, len(ai))
    # --- B finishes: kill all, capture
    tg = Bt['targets']
    for i in tg: tg[i]['hp'] = 50
    ub = [u for u in ub[1:]]
    B.lumps(*[bytes([0x29]) + struct.pack('>II', ub[k % len(ub)], i) for k, i in enumerate(list(tg))])
    await asyncio.sleep(4)
    chk('all aliens dead', not tg, list(tg))
    t4 = time.monotonic()
    B.send(bytes([0x5a]) + struct.pack('>IBIB', 1, 1, MAP, 1)); await asyncio.sleep(S.BATTLE_END_DELAY + 2.5)
    chk('B victory result', any(r[1] == 0 for r in B.got(0x25, t4)))
    chk('spectator C got no result window', not C.got(0x25, t4))
    chk('spectator C returned to his capital', any(struct.unpack_from('>I', b, 1)[0] == S.CAPITALS[2] for b in C.got(0x17, t4)))
    B.close(); C.close(); await asyncio.sleep(0.5); srv.close()
if __name__ == "__main__":
    asyncio.run(main())
