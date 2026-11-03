"""test37: NPC commanders follow the player rules - novice planet: no reincarnation, branch <= 35, deploy limit
Tactics // 20 + 6 (< 12); unit kinds within the branch influence; unit levels <= branch + 3; battle squads <= deploy limit."""
import sys, os, time
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
for f in ('npcs.json', 'world.json'):
    if os.path.exists(f): os.remove(f)
import sgserver as S
S.LOG = open('/tmp/mp/server37.log', 'w')
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
S.npc_tick(time.time())
tier = lambda n: S.PLANET_TIER.get(S.nation_planet(n['nation']), 1)
nov = [n for n in S.npc_all() if tier(n) == 1]
chk('novice NPCs: no reincarnation, branches <= 35', all(S.npc_profile(n)['reinc'] == 0 and max(S.npc_profile(n)['br'].values()) <= 35 for n in nov))
dep = [S.npc_deploy(n) for n in nov]
chk('novice NPCs deploy 6..9 units (never 12)', min(dep) >= 6 and max(dep) <= 9, (min(dep), max(dep)))
chk('deploy = Tactics // 20 + 6', all(S.npc_deploy(n) == min(12, S.npc_profile(n)['attrs'][0] // 20 + 6) for n in S.npc_all()))
pool = {p['code']: p for p in S.S.npc_pool()} if hasattr(S, 'S') else {p['code']: p for p in S.npc_pool()}
chk('unit kinds within the branch influence', all(pool[c]['min'] <= S.npc_influence(n, pool[c]['branch']) for n in S.npc_all() for c, _l in n['squad']))
chk('unit levels <= branch level + 3', all(l <= S.npc_profile(n)['br'][pool[c]['branch']] + 3 for n in S.npc_all() for c, l in n['squad']))
n = nov[0]
# (2026-10-24 22:48) platoons: every PLATOON stays within the deploy limit (6..8), 3..4 platoons go in together
_bu = S.npc_battle_units(n, 12, n['nation'])
_pl = {}
for _u in _bu: _pl[S.npc_platoon_of(n, _u[6])] = _pl.get(S.npc_platoon_of(n, _u[6]), 0) + 1
chk('battle units within the deploy limit (user 10-31 13:23: at most 12 like a player)', sum(_pl.values()) <= S.npc_deploy(n) and all(v <= max(6, min(8, S.npc_deploy(n))) for v in _pl.values()), (_pl, S.npc_deploy(n)))
c = S.npc_cmd(n)
chk('profile window shows the same attributes', c['attrs'] == S.npc_profile(n)['attrs'] and c['reincarnations'] == 0)
chk('higher planets: some 12-unit veterans', any(S.npc_deploy(m) == 12 for m in S.npc_all() if tier(m) == 3))
