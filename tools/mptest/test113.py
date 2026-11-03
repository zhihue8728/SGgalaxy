"""test113 (user 2026-10-31 13:23 "an NPC enters a battle like a player: at most 12 units at a time, how many by its
attributes; it may pull units back to swap them as the battle needs - not when it is alone on the field"):
A. npc_deploy = the player rule min(12, Tactics // 20 + 6) from the NPC's attributes; a stronger NPC brings more;
B. npc_battle_units never gives more than the deploy limit, and only the room left (its units already on the map count);
C. swap: a platoon that cannot hurt the enemy is pulled back only when another commander of its side is on the map."""
import sys, os, time, random
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
for f in ('npcs.json', 'world.json'):
    if os.path.exists(f): os.remove(f)
import sgserver as S
import npc as NP
import progression as PG
S.LOG = open('/tmp/mp/server113.log', 'w', encoding='utf-8')
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
random.seed(13)
now = time.time()
S.npc_tick(now)
ns = [n for n in S.npc_all() if (n.get('doctrine') or {}).get('pp')]
lo = min(ns, key=lambda n: S.npc_profile(n)['attrs'][0]); hi = max(ns, key=lambda n: S.npc_profile(n)['attrs'][0])
ok = all(S.npc_deploy(n) == min(12, S.npc_profile(n)['attrs'][0] // 20 + 6) for n in ns)
chk('A1 deploy limit = min(12, Tactics // 20 + 6) for every NPC', ok)
chk('A2 by attributes: the NPC with more Tactics may bring more', S.npc_deploy(hi) >= S.npc_deploy(lo) and max(S.npc_deploy(n) for n in ns) <= 12,
    (S.npc_deploy(lo), S.npc_deploy(hi)))
class G: pass
worst = 0
for n in ns[:40]:
    for i in range(len(NP.health(n))): n['hl'][i] = 1.0
    g = G(); g.targets = {}
    u = S.npc_battle_units(n, 30, n['nation'], ctx=g, platoons=4)
    worst = max(worst, len(u) - S.npc_deploy(n))
chk('B1 never more units than its deploy limit (even asked for 4 platoons)', worst <= 0, worst)
n = hi
g = G(); g.targets = {90000 + i: {'npc': n['id'], 'hp': 10} for i in range(S.npc_deploy(n) - 3)}
u = S.npc_battle_units(n, 30, n['nation'], ctx=g)
chk('B2 units already on the map count: only the room left', 0 < len(u) <= 3, len(u))
g.targets.update({91000 + i: {'npc': n['id'], 'hp': 10} for i in range(3)})
chk('B3 at the limit: none', S.npc_battle_units(n, 30, n['nation'], ctx=g) == [])
# C: swap rule
S.unit_effect = lambda st9, th: 0.0                       # every gun useless against this enemy
th = {'n': 6, 'air': 1.0}
def scene(company):
    g = G(); g.targets = {}
    for i in range(len(NP.health(n))): n['hl'][i] = 1.0
    units = S.npc_battle_units(n, 30, n['nation'], ctx=g)
    g.targets = {}
    for k, u in enumerate(units):
        g.targets[80000 + k] = {'npc': n['id'], 'hp': 10, 'nation': n['nation'], 'idx': u[6], 'plt': S.npc_platoon_of(n, u[6]),
                                'put': {'st9': u[2]}, 'urole': 'fighter'}
    if company:
        g.targets[89999] = {'npc': 424242, 'hp': 10, 'nation': n['nation']}
    fielded = {}
    for tg in g.targets.values():
        if tg.get('npc') == n['id']: fielded[tg['plt']] = fielded.get(tg['plt'], 0) + 1
    rt = {'nid': n['nation'], 'fielded': fielded, 'used': set(), 'units': len(units), 'waves': 0, 'home': (500, 500),
          'mode': 'assault', 'poc': None}
    b = {'map': 600003, 'targets': g.targets, 'pocs': {}, 'members': set()}
    mine_ = [(t, tg) for t, tg in g.targets.items() if tg.get('npc') == n['id']]
    S._platoon_wave(g, b, now, n['id'], rt, n, mine_, th)
    return sum(1 for _t, tg in mine_ if tg.get('withdraw'))
w0 = scene(False)
w1 = scene(True)
chk('C1 alone on the field: nothing is pulled back to swap', w0 == 0, w0)
chk('C2 with another commander of its side there: useless platoons are swapped out', w1 > 0, w1)
