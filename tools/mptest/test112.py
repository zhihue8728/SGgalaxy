"""test112 (user 2026-10-31 11:48 "the NPCs only watch from outside"; log: 215 x "battle is full"): the NPC side cap of
one battle (NPC_JOIN_SIDE_MAX, now 12) is checked BEFORE an NPC marches there, and one that still finds it full does not
watch for 3 minutes:
A. npc_battle_room counts the side's commanders on the map + the ones marching there;
B. a full battle: npc_follow / the no-target fallback do not send anyone; with room they do;
C. arriving at a full battle: after NPC_JOIN_TRIES (3) tries it is released with a short rest (a new decision soon)."""
import sys, os, time, random
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
for f in ('npcs.json', 'world.json'):
    if os.path.exists(f): os.remove(f)
import sgserver as S
import npc as NP
import battle_ai as BAI
S.LOG = open('/tmp/mp/server112.log', 'w', encoding='utf-8')
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
random.seed(12)
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
for m in S.npc_of(NA):
    m['task'] = None; m['walk'] = None; m.pop('post', None); m['rest_until'] = 0; m['state'] = 'active'
    for i in range(len(NP.health(m))): m['hl'][i] = 1.0
act = S.npc_of(NA)
lead, n = act[0], act[1]
c = {'pid': tgt, 'owner': 3, 'kind': 'enemy', 'garrison': 0, 'dist_cap': 2, 'def_power': 10.0}
S.npc_send([lead], c, now)
class W:
    def is_closing(self): return False
class Own:
    w = W(); targets = {}
B = {'map': tgt, 'owner': Own(), 'defender': 3, 'targets': {}, 'pocs': {}}
S.BATTLES[tgt] = B
chk('A0 cap raised to 12, no waiting', S.NPC_JOIN_SIDE_MAX == 12 and S.NPC_JOIN_TRIES == 0)
r0 = S.npc_battle_room(tgt, NA)
chk('A1 the marching leader takes a slot', r0 == S.NPC_JOIN_SIDE_MAX - 1, r0)
for i in range(S.NPC_JOIN_SIDE_MAX - 1):
    B['targets'][90000 + i] = {'npc': 50000 + i, 'nation': NA, 'hp': 10}
chk('A2 full: room 0', S.npc_battle_room(tgt, NA) == 0, S.npc_battle_room(tgt, NA))
chk('B1 full: npc_follow does not send', not S.npc_follow(n, lead, now) and not n.get('task'))
chk('B2 full: no-target fallback does not join it', not (S.npc_no_target(n, now) and n['task'].get('target') == tgt))
n['task'] = None
B['targets'].pop(90000)
chk('B3 a slot free: npc_follow sends', S.npc_follow(n, lead, now) and n['task']['target'] == tgt)
# C: arriving while full -> another front at once (user 12:36)
B['targets'][90000] = {'npc': 50000, 'nation': NA, 'hp': 10}
B['targets'][90099] = {'npc': 50099, 'nation': NA, 'hp': 10}
other = next(q for q in nbr(S.CAPITALS[NA]) if q not in caps and q != tgt)
S.set_province_owner(other, 3)
k = act[2]
k['task'] = dict(lead['task'], phase='march', arrive=now, path=lead['task']['path'], wait=0)
real = S.npc_targets
S.npc_targets = lambda nid, now: [{'pid': tgt, 'owner': 3, 'kind': 'enemy', 'garrison': 0, 'dist_cap': 1, 'def_power': 1.0},
                                  {'pid': other, 'owner': 3, 'kind': 'enemy', 'garrison': 0, 'dist_cap': 1, 'def_power': 1.0}]
S.npc_begin([k], now)
S.npc_targets = real
chk('C1 full on arrival: no waiting - at once an attack on another province', k.get('task') and k['task']['kind'] == 'attack'
    and k['task']['target'] == other and k['task']['phase'] == 'march', k.get('task'))
S.LOG.flush()
chk('C2 logged', 'they open another front' in open('/tmp/mp/server112.log', encoding='utf-8').read())
