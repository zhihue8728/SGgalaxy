"""test23: NPCs besieging a neutral province are really on the map when a player enters (siege + aliens together)."""
import asyncio, struct, sys, os, time, random
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
for f in ('npcs.json', 'world.json'):
    if os.path.exists(f): os.remove(f)
import sgserver as S
from mpclient import Client
S.LOG = open('/tmp/mp/server23.log', 'w', encoding='utf-8')
PORT = 3988
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
async def main():
    random.seed(5)
    S.ensure_unique_unit_ids()
    srv = await asyncio.start_server(S.handle, '127.0.0.1', PORT)
    S.npc_tick(time.time())
    A = Client('jjjjjjjj'); await A.connect(PORT); await A.login(); await asyncio.sleep(1.0)
    s = next(iter(S.ONLINE)); HN = s.cmd['nation']
    NA = next(x for x in (11, 12, 13) if x != HN)
    cand = [c for c in S.npc_candidates(NA, time.time()) if c['kind'] == 'alien']
    P = cand[0]['pid']
    team = [n for n in S.npc_of(NA) if n['state'] == 'active' and not n['task']][:3]
    for n in team: n['squad'] = [[c, 40] for c, _l in n['squad']]; n['level'] = 40
    t0 = time.time(); S.npc_send(team, cand[0], t0, group=True)
    for n in team: n['task']['arrive'] = t0 - 1
    S.npc_tick(t0)
    chk('siege = real battle already running (server-simulated)', P in S.BATTLES and all(n['task']['phase'] == 'battle' for n in team))
    t = time.monotonic()
    S.enter_field(s, P, 0x400, 0x400); await asyncio.sleep(2.0)
    B = S.BATTLES.get(P)
    npcs = {k: g for k, g in s.targets.items() if g.get('npc') is not None}
    ali = {k: g for k, g in s.targets.items() if g.get('npc') is None}
    chk('aliens AND NPC units on the map', len(npcs) >= 3 and len(ali) >= 1, (len(npcs), len(ali)))
    chk('NPC units sent to the client as PUT_UNIT', sum(1 for p in A.puts(t) if p[2] in {x for n in team for x in (n['name'], S.NP.name_zh(n['name']).encode('gbk').decode('latin-1'))}) >= 3)
    chk('battle knows the NPC side', bool(B) and B.get('npc_side') == NA and B.get('npc_raid'), B and B.get('npc_side'))
    chk('NPC tasks switched to battle', all(n['task']['phase'] == 'battle' for n in team))
    await asyncio.sleep(3.0)
    moves = [m for _tk, m in A.lump_msgs(t) if m and m[0] == 0x1A and struct.unpack_from('>I', m, 1)[0] in npcs]
    chk('NPC AI moves its units (alien AI leaves them alone)', len(moves) >= 1, len(moves))
    S.leave_map(s, 'test'); await asyncio.sleep(0.3)
    srv.close()
asyncio.run(main())
