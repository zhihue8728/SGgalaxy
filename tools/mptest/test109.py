"""test109 (user 2026-10-31 10:16 / 10:26 "NPCs coordinate in the channel and support each other; stronger strategy in
the battle" - both):
A. pincer: an NPC marching on an enemy province calls in the ally channel; idle comrades in OTHER own provinces next to
   the target march in from there - each its own group (its own gate), all arriving together, answers in the channel;
B. calls for help: 4 helpers (3-5), a side weaker than the enemy (ratio < 1.0) calls, calls every 180 s, nearest first;
C. battle brain (battle_ai.Brain.plan): the side goes for the least defended enemy POC next to its own ground; losing but
   holding POCs / with help on the way it digs in on its own POC (defend) instead of falling back to the gate; outnumbered
   with help coming it does not open a new POC."""
import sys, os, time, random
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
for f in ('npcs.json', 'world.json'):
    if os.path.exists(f): os.remove(f)
import sgserver as S
import npc as NP
import battle_ai as BAI
S.LOG = open('/tmp/mp/server109.log', 'w', encoding='utf-8')
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
random.seed(9)
now = time.time()
S.npc_tick(now)
NA = 1
cap = S.CAPITALS[NA]
pl = cap // 100000
nbr = lambda p: [pl * 100000 + q for q in S.PORTAL_LINKS.get(p % 100000, ())]
caps = set(S.CAPITALS.values())
# a target with at least 3 neighbours: all but the target ours, target enemy
tgt = next(p for p in S.planet_provinces(pl) if p not in caps and len([q for q in nbr(p) if q not in caps]) >= 3
           and all(q not in caps for q in nbr(p)))
for q in nbr(tgt):
    S.set_province_owner(q, NA)
    for r in nbr(q):                                   # a road from the capital: make the neighbours' neighbours ours too
        if r not in caps and r != tgt:
            S.set_province_owner(r, NA)
S.set_province_owner(tgt, 3)
# own land connected to the capital: walk outward from the capital
S.set_province_owner(cap, NA)
fr = [cap]; seen = {cap}
while fr:
    p = fr.pop()
    for q in nbr(p):
        if q not in seen and q not in caps and q != tgt:
            seen.add(q); S.set_province_owner(q, NA); fr.append(q)
for m in S.npc_of(NA):
    m['task'] = None; m['walk'] = None; m.pop('post', None); m['rest_until'] = 0; m['state'] = 'active'
    for i in range(len(NP.health(m))): m['hl'][i] = 1.0
lead = S.npc_of(NA)[0]
c = {'pid': tgt, 'owner': 3, 'kind': 'enemy', 'garrison': 0, 'dist_cap': 2, 'def_power': 10.0}
S.npc_send([lead], c, now)
S.NPC_PINCER_CHANCE = 1.0
picks = S.npc_pincer([lead], c, now)
S.LOG.flush()
lg = open('/tmp/mp/server109.log', encoding='utf-8').read()
origins = {m['task']['origin'] for m in picks}
chk('A1 pincer: comrades from other provinces next to the target', len(picks) >= 2 and lead['task']['origin'] not in origins
    and all(o in nbr(tgt) for o in origins), (len(picks), origins, lead['task'].get('origin')))
chk('A2 each direction its own group, all on the target', len({m['task']['group'] for m in picks} | {lead['task'].get('group')}) == len(picks) + 1
    and all(m['task']['target'] == tgt for m in picks))
chk('A3 all arrive together (the pincer a few seconds after the lead)', all(0 < m['task']['arrive'] - lead['task']['arrive'] < 15 for m in picks))
chk('A4 the call and the answers in the log', 'pincer on' in lg)
chk('B1 calls for help: 4 helpers, weaker side calls, every 180 s', S.NPC_SOS_HELPERS == 4 and S.NPC_SOS_RATIO >= 1.0 and S.NPC_SOS_GAP <= 180)
# C: battle brain
def unit(i, side, x, y, hp=300):
    return BAI.U(i, side, (x, y), hp, hp, dmg_g=30, rng_g=200, cd=1.0, squad=f"{side}-a", mode="assault")
same = lambda a, b: a == b
br = BAI.Brain(tier=2, seed=1)
mine = [unit(i, 1, 1000 + i * 10, 2000) for i in range(6)]
foes = [unit(100 + i, 2, 2600, 1000 + i * 10) for i in range(6)]          # guards POC 1
pocs = {0: {'x': 1100, 'y': 2100, 'owner': 1}, 1: {'x': 2600, 'y': 1000, 'owner': 2}, 2: {'x': 1700, 'y': 2600, 'owner': 2}}
pl1 = br.plan(1, mine, foes, pocs, same, 100.0, 'assault', friends=mine)
chk('C1 goes for the unguarded POC next to its own one (not the guarded one)', pl1['kind'] == 'assault' and pl1['poc'] == 2, pl1)
br2 = BAI.Brain(tier=2, seed=2)
strong = [unit(200 + i, 2, 1300, 2050 + i * 10, 2000) for i in range(16)]   # in contact, much stronger
br2.incoming[1] = 2
pl2 = br2.plan(1, mine, strong, pocs, same, 100.0, 'assault', friends=mine)
chk('C2 losing, help on the way: digs in on its own POC (defend), not back to the gate', pl2['kind'] == 'defend' and pl2['poc'] == 0, pl2)
br3 = BAI.Brain(tier=2, seed=3)
pl3 = br3.plan(1, mine, strong, {2: pocs[2]}, same, 100.0, 'assault', friends=mine)
chk('C3 losing, no POC to hold: falls back (regroup)', pl3['kind'] == 'regroup', pl3)
