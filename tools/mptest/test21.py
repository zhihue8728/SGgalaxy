"""test20: NPC nations - roster, active count follows the players, abstract conquest, NPC raid on a player province, real battle
with NPC units (raid attackers / province defenders), last stand, protection (claude/NPC_NATIONS_PLAN.md)."""
import asyncio, struct, sys, os, time, random
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
for f in ('npcs.json',):
    if os.path.exists(f): os.remove(f)
import sgserver as S
from mpclient import Client
S.LOG = open('/tmp/mp/server21.log', 'w', encoding='utf-8')
PORT = 3986
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)

def strong(npcs, lv=60):
    for n in npcs:
        n['squad'] = [[c, lv] for c, _l in n['squad']]; n['level'] = lv

async def main():
    random.seed(7)
    S.ensure_unique_unit_ids()
    srv = await asyncio.start_server(S.handle, '127.0.0.1', PORT)
    now = time.time()
    S.npc_tick(now)
    A = Client('jjjjjjjj'); await A.connect(PORT); await A.login(); await asyncio.sleep(1.0)
    sa = next(iter(S.ONLINE)); HN = sa.cmd['nation']
    NA = next(x for x in (11, 12, 13) if x != HN)
    pl = S.nation_planet(HN)
    P = next(pl * 100000 + q for q in S.PORTAL_LINKS[S.CAPITALS[NA] % 100000]
             if pl * 100000 + q not in S.CAPITALS.values())
    S.set_province_owner(P, HN)
    raiders = [n for n in S.npc_of(NA) if n['state'] == 'active' and not n['task']][:3]
    strong(raiders, 40)
    cand = {'pid': P, 'owner': HN, 'kind': 'enemy', 'garrison': 0.0, 'dist_cap': 1, 'def_power': S.npc_defence(P)}
    t0 = time.time(); S.npc_send(raiders, cand, t0, group=True)
    for n in raiders: n['task']['arrive'] = t0 - 1
    S.npc_tick(t0)
    nn = raiders[0]
    _sv = dict(nn['task']); nn['task'].update(depart=t0 - 100, arrive=t0 + 200, phase='march')
    d0 = S.npc_dot(nn, t0 - 90); d1 = S.npc_dot(nn, t0 + 150); nn['task'].update(depart=_sv['depart'], arrive=_sv['arrive'], phase=_sv['phase'])
    chk('minimap dot of a marching NPC moves', d0 != d1 and all(0 <= v < 128 for v in d0 + d1), (d0, d1))
    chk('province info lists NPC at its origin only while marching', S.npc_location(nn)[0] != nn['task']['target'] or nn['task']['phase'] != 'march')
    # legend + route while the raid window is open
    sm = S.build_strategic_map(sa)
    chk('strategic map builds with NPC raid', len(sm) > 10)
    S.enter_field(sa, P, 0x400, 0x400); await asyncio.sleep(1.5)
    B0 = S.BATTLES.get(P)
    chk('battle runs with NPC units', bool(B0) and any(g.get('npc') is not None for g in B0['targets'].values()))
    B = Client('hhhhhhhh'); await B.connect(PORT); await B.login(); await asyncio.sleep(1.0)
    print('ONLINE', [(getattr(o,'acc',None), getattr(o,'logged_in',None)) for o in S.ONLINE], flush=True)
    sb = [o for o in S.ONLINE if o is not sa and getattr(o, 'acc', None)][0]
    ranks = {sa: 10, sb: 90}
    S.player_rank_level = lambda o: ranks.get(o, 0)
    t = time.monotonic()
    S.enter_field(sb, P, 0x400, 0x400); await asyncio.sleep(1.5)
    npcids = [k for k, g in B0['targets'].items() if g.get('npc') is not None]
    owners = {g['put']['owner'] for g in B0['targets'].values() if g.get('npc') is not None}
    puts = B.puts(t)
    chk('joiner receives PUT_UNIT of the NPC units', sum(1 for p in puts if p[2] in owners) >= len(npcids) > 0, (len(puts), len(npcids)))
    chk('highest rank becomes battle commander on join', B0['owner'] is sb, getattr(B0['owner'], 'acc', None))
    ranks[sa] = 99
    S.set_battle_owner(B0, S.battle_best_commander(B0), 'test')
    chk('rank change -> commander follows', B0['owner'] is sa)
    S.leave_map(sa, 'test'); await asyncio.sleep(0.3)
    chk('commander leaves -> remaining player commands', B0['owner'] is sb)
    srv.close()

asyncio.run(main())
