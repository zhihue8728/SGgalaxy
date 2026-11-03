"""test28: a player joins a siege of his OWN nation's NPCs: the NPC squads are allies and fight the aliens (user 15:16)."""
import asyncio, struct, sys, os, time, random
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
for f in ('npcs.json', 'world.json'):
    if os.path.exists(f): os.remove(f)
import sgserver as S
from mpclient import Client
S.LOG = open('/tmp/mp/server28.log', 'w', encoding='utf-8')
PORT = 3994
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
async def main():
    random.seed(5)
    S.ensure_unique_unit_ids()
    srv = await asyncio.start_server(S.handle, '127.0.0.1', PORT)
    S.npc_tick(time.time())
    A = Client('jjjjjjjj'); await A.connect(PORT); await A.login(); await asyncio.sleep(1.0)
    s = next(iter(S.ONLINE)); HN = s.cmd['nation']
    cand = [c for c in S.npc_candidates(HN, time.time()) if c['kind'] == 'alien']
    P = cand[0]['pid']
    team = [n for n in S.npc_of(HN) if n['state'] == 'active' and not n['task']][:2]
    for n in team: n['squad'] = [[c, 40] for c, _l in n['squad']]; n['level'] = 40
    t0 = time.time(); S.npc_send(team, cand[0], t0, group=True)
    for n in team: n['task']['arrive'] = t0 - 1
    S.npc_tick(t0)
    t = time.monotonic()
    S.enter_field(s, P, 0x400, 0x400); await asyncio.sleep(1.5)
    B = S.BATTLES.get(P)
    npcs = {k: g for k, g in s.targets.items() if g.get('npc') is not None}
    ali = {k: g for k, g in s.targets.items() if g.get('npc') is None}
    chk('own-nation NPC squads are on the map as allies', len(npcs) >= 3 and all(g['nation'] == HN for g in npcs.values()), len(npcs))
    chk('client got their PUT_UNITs', sum(1 for p in A.puts(t) if p[2] in {n['name'] for n in team}) >= 3)
    chk('allied siege: the NPC side is the player\'s side', bool(B) and S.same_side(B.get('npc_side'), HN))
    # bring one NPC unit next to an alien
    aid, ag = next(iter(ali.items())); nid_, ng = next(iter(npcs.items()))
    ng['pos'] = ng['home'] = (ag['pos'][0] + 30, ag['pos'][1]); ng['mv'] = None
    t = time.monotonic(); await asyncio.sleep(3.0)
    atk = [struct.unpack_from('>II', m, 1) for _tk, m in A.lump_msgs(t) if m and m[0] == 0x2B]
    chk('allied NPC attacks an alien (0x2B npc -> alien)', any(a in npcs and b in ali for a, b in atk), atk[:6])
    chk('aliens fight back at the NPC units', any(a in ali and b in npcs for a, b in atk), atk[:6])
    chk('NPC units never attack the player', not any(a in npcs and b in s.alive_units for a, b in atk))
    S.leave_map(s, 'test'); await asyncio.sleep(0.3)
    srv.close()
asyncio.run(main())
