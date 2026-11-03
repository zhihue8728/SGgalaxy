"""test41: GM /amove and /aatk (walking-animation A/B test): a passive spawned alien receives a 0x1A move / 0x2B attack lump."""
import asyncio, struct, sys, os, time, random
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
for f in ('npcs.json', 'world.json'):
    if os.path.exists(f): os.remove(f)
import sgserver as S
from mpclient import Client
S.LOG = open('/tmp/mp/server41.log', 'w', encoding='utf-8')
PORT = 3992
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
def lump_msgs(b):
    n = struct.unpack_from('>H', b, 7)[0]; p = 9; out = []
    for _ in range(n):
        l = struct.unpack_from('>H', b, p)[0]; out.append(b[p + 2:p + 2 + l]); p += 2 + l
    return out
async def main():
    random.seed(5)
    S.ensure_unique_unit_ids()
    srv = await asyncio.start_server(S.handle, '127.0.0.1', PORT)
    S.npc_tick(time.time())
    A = Client('jjjjjjjj'); await A.connect(PORT); await A.login(); await asyncio.sleep(1.0)
    s = next(iter(S.ONLINE))
    P = next(c['pid'] for c in S.npc_candidates(11, time.time()) if c['kind'] == 'alien')
    S.enter_field(s, P, 0x400, 0x400); await asyncio.sleep(0.5)
    S.gm_command(s, '/spawn g011 10 1'); await asyncio.sleep(0.3)
    tid = max(S.s_targets(s) if hasattr(S, 's_targets') else s.targets)
    for cmd, typ in (('/amove', 0x1A), ('/aatk', 0x2B)):
        n0 = len(A.inbox)
        S.gm_command(s, cmd); await asyncio.sleep(0.4)
        got = [m for ts, b in A.inbox[n0:] if b[0] == 0x80 and len(b) > 9 for m in lump_msgs(b)]
        chk(f'{cmd} sends a {typ:#x} lump for the spawned alien', any(m[0] == typ and struct.unpack_from('>I', m, 1)[0] == tid for m in got), [m[:1].hex() for m in got][:6])
    A.close(); await asyncio.sleep(0.3); srv.close()
asyncio.run(main())
