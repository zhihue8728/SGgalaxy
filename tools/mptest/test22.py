"""test22: idle NPC commanders are shown on the capital map (hero + minimap dot)."""
import asyncio, struct, sys, os, time, random
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
for f in ('npcs.json',):
    if os.path.exists(f): os.remove(f)
import sgserver as S
from mpclient import Client
S.LOG = open('/tmp/mp/server22.log', 'w', encoding='utf-8')
PORT = 3987
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
async def main():
    S.ensure_unique_unit_ids()
    srv = await asyncio.start_server(S.handle, '127.0.0.1', PORT)
    S.npc_tick(time.time())
    A = Client('jjjjjjjj'); t = time.monotonic()
    await A.connect(PORT); await A.login(); await asyncio.sleep(1.5)
    s = next(iter(S.ONLINE)); nid = s.cmd['nation']
    idle = [n for n in S.npc_of(nid) if n['state'] == 'active' and not n['task']]
    puts = A.puts(t)
    ids = {p[0] for p in puts} if puts and isinstance(puts[0], tuple) else None
    chk('NPC commanders appear on the capital map', len(s.npc_town) == len(idle) > 0, (len(s.npc_town), len(idle)))
    chk('client received their PUT_UNITs', sum(1 for p in puts if p[2] in {x for n in idle for x in (n['name'], S.NP.name_zh(n['name']).encode('gbk').decode('latin-1'))}) >= len(idle), len(puts))
    n0 = idle[0]
    n0['task'] = {'kind': 'attack', 'target': 1, 'origin': 1, 'depart': time.time(), 'arrive': time.time() + 99, 'phase': 'march', 'group': None, 'since': time.time(), 'wait': 0}
    S.npc_dot_push(time.time()); await asyncio.sleep(0.3)
    chk('an NPC leaving on a task first WALKS to a gate', n0['id'] in s.npc_town and s.npc_town[n0['id']]['leave_at'] is not None)
    s.npc_town[n0['id']]['leave_at'] = 0
    S.npc_dot_push(time.time()); await asyncio.sleep(0.3)
    chk('...then disappears from the capital', n0['id'] not in s.npc_town)
    xs = [r['x'] for r in s.npc_town.values()]; ys = [r['y'] for r in s.npc_town.values()]
    chk('idle NPCs stand spread over the whole map (not clustered)', max(xs) - min(xs) > 1500 and max(ys) - min(ys) > 1500, (min(xs), max(xs), min(ys), max(ys)))
    for r in s.npc_town.values(): r['next'] = 0
    t2 = time.monotonic(); S.npc_dot_push(time.time()); await asyncio.sleep(0.4)
    mv = [m for _tk, m in A.lump_msgs(t2) if m and m[0] == 0x1A]
    chk('idle NPCs wander (move orders sent)', len(mv) >= 5, len(mv))
    srv.close()
asyncio.run(main())
