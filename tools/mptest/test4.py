import asyncio, struct, sys, os, time
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
from mpclient import Client, s8
from test3 import join
S.LOG = open('/tmp/mp/server4.log', 'w', encoding='utf-8')
S.REINFORCE_COOLDOWN = 1; S.REINFORCE_DELAY = 50
PORT = 3996
def chk(name, ok, info=''): print(('PASS ' if ok else 'FAIL ') + name, info, flush=True)
async def main():
    S.ensure_unique_unit_ids()
    srv = await asyncio.start_server(S.handle, '127.0.0.1', PORT)
    A, B, C = Client('jjjjjjjj'), Client('kkkkkkkk'), Client('llllllll')
    for X in (A, B, C):
        await X.connect(PORT); await X.login()
    MAP = 600400
    A.send(bytes([0x2e]) + struct.pack('>IHHBB', MAP, 0x100, 0x1c0, 2, 0)); await asyncio.sleep(1.0)
    Bt = S.BATTLES[MAP]
    await join(B, A, MAP)
    ua = [p[0] for p in A.puts() if p[2] == 'jjjjjjjj' and p[0] > 1000]
    A.send(bytes([0x2f]) + struct.pack('>IHIiHHHH', ua[0], 0, 0, -1, 0x80, 0x80, 0x80, 0x80)); await asyncio.sleep(1.5)
    t1 = time.monotonic(); A.send(bytes([0x19, 0])); await asyncio.sleep(1.0)
    chk('F7 after a loss: delayed PUT 0x50 to A and B', len(A.got(0x50, t1)) == 1 and len(B.got(0x50, t1)) == 1,
        (len(A.got(0x50, t1)), len(B.got(0x50, t1))))
    p50 = A.got(0x50, t1)
    if p50:
        tick = struct.unpack_from('>I', p50[0], 1)[0]; chk('0x50 scheduled in the future', tick > S.game_time(Bt['owner']) - 60, tick)
    # PvP: enemy C (nation 2) enters a province held by nation 1 where nobody fights
    t2 = time.monotonic(); PV = 600300
    print('owner of', PV, S.province_owner(PV))
    C.send(bytes([0x2e]) + struct.pack('>IHHBB', PV, 0x100, 0x1c0, 2, 0)); await asyncio.sleep(1.5)
    sc = next(o for o in S.ONLINE if getattr(o, 'acc', '') == 'llllllll')
    print('C map', getattr(sc, 'map', None), 'battle', bool(getattr(sc, 'battle', None)), 'kind', getattr(sc, 'battle_kind', None),
          'targets', len(getattr(sc, 'targets', {}) or {}))
    print('A/B notified of attack?', [b.hex()[:40] for b in A.got(0x31, t2) + A.got(0x1f, t2) + A.got(0x24, t2)])
    for X in (A, B, C): X.close()
    await asyncio.sleep(0.5); srv.close()
asyncio.run(main())
