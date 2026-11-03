"""test107 (user 2026-10-30 22:30 "an enemy took a province next to our capital: NPCs briefly up to 30 and more eager to
attack, for 12 hours"): the capital alarm (npc.py ALARM_*, sgs/npc_world.py npc_update_alarm / npc_sync / npc_may_attack,
npc.py want_active / think_delay / choose / score).
A. no enemy next to the capital: no alarm, 20 active at most;  B. an enemy-held neighbour of the capital: alarm for 12 h,
roster grows to 30, all 30 take the field (players online still take places);  C. more aggressive: faster decisions, worse
odds accepted, never 'stays home', no pause after a conquest, the enemy land next to the capital scores highest;
D. after 12 h with the threat gone the alarm ends and the NPCs go back to 20; still threatened -> a new alarm."""
import sys, os, time, random
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
for f in ('npcs.json', 'world.json'):
    if os.path.exists(f): os.remove(f)
import sgserver as S
import npc as NP
S.LOG = open('/tmp/mp/server107.log', 'w', encoding='utf-8')
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
random.seed(7)
now = time.time()
S.npc_tick(now)
NA = 1
cap = S.CAPITALS[NA]
pl = cap // 100000
nb = [pl * 100000 + q for q in S.PORTAL_LINKS.get(cap % 100000, ())]
for q in nb:
    S.set_province_owner(q, NA)
active = lambda: [n for n in S.npc_of(NA) if n['state'] == 'active']
for k in range(3):
    S.npc_sync(NA, now + 700 * (k + 1))
chk('A  no enemy next to the capital: no alarm, at most 20 active', not S.npc_alarm(NA, now + 2200) and len(active()) <= NP.NPC_CAP,
    (S.npc_alarm(NA, now + 2200), len(active())))
ENEMY = 3
S.set_province_owner(nb[0], ENEMY)
t1 = now + 3000
S.npc_sync(NA, t1)
chk('B1 enemy holds a neighbour of the capital: alarm on for 12 h', S.npc_alarm(NA, t1) and
    abs(S.npc_state()['alarm'][str(NA)] - (t1 + 12 * 3600)) < 2, S.npc_state()['alarm'].get(str(NA)))
chk('B2 roster grows to 30', len(S.npc_of(NA)) >= 30, len(S.npc_of(NA)))
for k in range(3):
    S.npc_sync(NA, t1 + 700 * (k + 1))
chk('B3 30 commanders take the field', len(active()) == 30, len(active()))
chk('B4 a player online still takes an NPC place', NP.want_active(1, False, True) == 29 and NP.want_active(0, False, False) == 20)
n = active()[0]
random.seed(1); a = [NP.think_delay(dict(n, alarm=True)) for _ in range(400)]
random.seed(1); b = [NP.think_delay(dict(n, alarm=False)) for _ in range(400)]
chk('C1 decisions twice as often', abs(sum(a) / sum(b) - 0.5) < 0.01, sum(a) / sum(b))
S.npc_state()['gain'][str(NA)] = t1 + 99999
chk('C2 no pause after a conquest during the alarm', S.npc_may_attack(NA, t1 + 100))
near = {'pid': nb[0], 'owner': ENEMY, 'kind': 'enemy', 'dist_cap': 1, 'def_power': 100.0}
far = {'pid': 1, 'owner': ENEMY, 'kind': 'enemy', 'dist_cap': 4, 'def_power': 100.0}
alien = {'pid': 2, 'owner': 0, 'kind': 'alien', 'garrison': 20.0, 'dist_cap': 1, 'def_power': 100.0}
p = dict(n, persona='cautious', alarm=True)
picks = [NP.choose([near, far, alien], p, 100.0)['pid'] for _ in range(300)]
chk('C3 the enemy land next to the capital is the first target', picks.count(nb[0]) > 0.8 * len(picks), picks.count(nb[0]))
wp_low = 90.0      # cautious min_win 0.45: rejected without the alarm, accepted with it
chk('C4 worse odds accepted', NP.score(near, dict(p, alarm=False), wp_low) is None or NP.score(near, p, wp_low) is not None)
chk('C5 never stays home', all(NP.choose([near], dict(p, persona='guard'), 100.0) for _ in range(300)))
S.npc_state()['gain'][str(NA)] = 0
t2 = t1 + 12 * 3600 + 60
S.npc_sync(NA, t2)
chk('D1 still threatened after 12 h: a new alarm', S.npc_alarm(NA, t2) and S.npc_state()['alarm'][str(NA)] > t2 + 11 * 3600)
S.set_province_owner(nb[0], NA)
t3 = t2 + 12 * 3600 + 60
for k in range(4):
    S.npc_sync(NA, t3 + 700 * k)
    for x in S.npc_of(NA):
        if x.get('task'): x['task'] = None
    S.npc_sync(NA, t3 + 700 * k + 1)
chk('D2 threat gone: alarm over, back to 20 active', not S.npc_alarm(NA, t3 + 3000) and len(active()) <= NP.NPC_CAP,
    (S.npc_alarm(NA, t3 + 3000), len(active())))
