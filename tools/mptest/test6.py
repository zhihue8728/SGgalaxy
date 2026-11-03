import asyncio, struct, sys, os, time, logging
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
from mpclient import Client
S.LOG = open('/tmp/mp/server6.log', 'w', encoding='utf-8')
PORT = 3996
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
bad = []
class H(logging.Handler):
    def emit(self, r): bad.append(r.getMessage())
logging.getLogger('asyncio').addHandler(H())
async def main():
    S.ensure_unique_unit_ids()
    srv = await asyncio.start_server(S.handle, '127.0.0.1', PORT)
    A, B = Client('jjjjjjjj'), Client('kkkkkkkk')
    for X in (A, B):
        await X.connect(PORT); await X.login()
    MAP = 600700; S.set_province_owner(MAP, 0)
    for X in (A,):
        X.send(bytes([0x2e]) + struct.pack('>IHHBB', MAP, 0x100, 0x1c0, 2, 0)); await asyncio.sleep(1.0)
    sa = next(o for o in S.ONLINE if o.acc == 'jjjjjjjj')
    uid = next(iter(sa.alive_units))
    # order an attack (attack loop) then kill the connection abruptly (RST)
    tid = next(iter(sa.targets))
    A.send(bytes([0x30]) + struct.pack('>IHHI', uid, 0, 0, tid)) if False else None
    sa.attacks[uid] = asyncio.get_event_loop().create_task(S.attack_loop(sa, uid, tid))
    await asyncio.sleep(0.5)
    A.w.transport.abort()
    await asyncio.sleep(6)
    chk('no tasks left attacking for the dead session', all(t.done() for t in sa.attacks.values()))
    chk('battle loops stopped (gen -1)', sa.battle_gen == -1)
    chk('no asyncio send warnings', not [m for m in bad if 'send' in m or 'raised' in m], bad[:3])
    chk('session removed', sa not in S.ONLINE)
asyncio.run(main())
