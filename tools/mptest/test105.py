"""test105 (user 2026-10-28 22:19 / 22:20 "a yellow province must not hold NPCs or players of another colour; NPCs follow
the battlefield rules"): an NPC is never placed in another nation's province without a battle there
(npc_may_stand / npc_location / npc_rule_fix in sgs/npc_world.py).
A. a marcher whose next step became enemy land is never drawn there; the tick re-routes it over own land or calls the
   march off;  B. a walker going home around a province that changed hands;  C. with a battle running (RAIDS) the
   attacker may stand in the enemy province;  D. the strategic-map position of every NPC after 3 h of simulated ticks
   is a province of its side, unowned land or a province with a battle."""
import sys, os, time, random
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
for f in ('npcs.json', 'world.json'):
    if os.path.exists(f): os.remove(f)
import sgserver as S
S.LOG = open('/tmp/mp/server105.log', 'w', encoding='utf-8')
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
random.seed(5)
now = time.time()
S.npc_tick(now)
NA = 1
cap = S.CAPITALS[NA]
own = lambda q: S.same_side(S.province_owner(q), NA)
# a road of 3 provinces from the capital, made ours
pl = cap // 100000
def nbrs(p): return [pl * 100000 + x for x in S.PORTAL_LINKS.get(p % 100000, ())]
a = next(q for q in nbrs(cap) if q not in S.CAPITALS.values())
b = next(q for q in nbrs(a) if q not in S.CAPITALS.values() and q != cap)
c = next(q for q in nbrs(b) if q not in S.CAPITALS.values() and q not in (a, cap))
for q in (a, b): S.set_province_owner(q, NA)
n = next(x for x in S.npc_of(NA) if x['state'] == 'active' and not x['task'])
n['walk'] = None; n.pop('post', None)
n['task'] = {'kind': 'attack', 'phase': 'march', 'target': c, 'origin': cap, 'path': [cap, a, b, c], 'depart': now - 1, 'arrive': now + 300, 'since': now}
t_mid = now + 220                                  # in b by then (step 2 of 3)
chk('A0 marching through own land: drawn in b at mid-way', S.npc_location(n, t_mid)[0] == b, S.npc_location(n, t_mid))
OTHER = 4 if NA != 4 else 3
S.set_province_owner(b, OTHER)                     # b changes hands, no battle there
S.BATTLES.pop(b, None); S.RAIDS.pop(b, None)
loc = S.npc_location(n, t_mid)[0]
chk('A1 b became enemy land: never drawn there (last own province)', loc != b and S.npc_may_stand(loc, NA), (loc, b))
S.npc_rule_fix(n, t_mid)
t = n.get('task')
ok = (t is None) or (b not in (t.get('path') or []))
chk('A2 the tick re-routes around b or calls the march off', ok, t and t.get('path'))
# B: walker home through a province that changes hands
n['task'] = None
S.set_province_owner(b, NA)
n['walk'] = {'path': [c, b, a, cap], 'depart': now, 'arrive': now + 300}
S.set_province_owner(c, NA)
S.set_province_owner(a, OTHER)
loc = S.npc_location(n, now + 220)[0]
chk('B1 walker: never drawn in a (enemy, no battle)', loc != a and S.npc_may_stand(loc, NA), loc)
S.npc_rule_fix(n, now + 220)
w = n.get('walk')
chk('B2 walker re-routed (no step in a) or sent straight home', (not w) or a not in w['path'], w)
# C: battle running in the enemy province -> attacker may stand there
S.RAIDS[a] = {'npc': NA, 'attacker': NA}
chk('C  with a raid running in a the attacker may stand there', S.npc_may_stand(a, NA))
S.RAIDS.pop(a, None)
# D: simulated ticks
bad = []
for k in range(1080):                              # 3 h of 10-s ticks
    tt = now + 400 + k * 10
    try:
        S.npc_tick(tt)
    except Exception as e:
        bad.append(('tick', repr(e))); break
    if k % 30 == 0:
        for x in S.npc_all():
            if x.get('state') != 'active': continue
            p = S.npc_location(x, tt)[0]
            if p and not S.npc_may_stand(p, x['nation']):
                bad.append((x['name'], x['nation'], p, S.province_owner(p), (x.get('task') or {}).get('kind'), (x.get('task') or {}).get('phase')))
chk('D  3 h of NPC ticks: every NPC stands in its side / unowned land / a province with a battle', not bad, bad[:5])
# E (user 10-29 23:43 "red NPCs inside a blue-vs-yellow battle, red has no province next to it"): a battle of two OTHER
# nations does not let a left-over NPC stay - only a side that takes part (attacker / defender / units on the map)
E_A, E_D = 3, 4                                     # blue attacks yellow
pe = next(q for q in S.planet_provinces(pl) if S.province_owner(q) == E_D and q not in S.CAPITALS.values())
S.BATTLES[pe] = {'map': pe, 'defender': E_D, 'npc_attacker': E_A, 'targets': {}}
chk('E1 battle exception only for its sides', S.npc_may_stand(pe, E_A) and not S.npc_may_stand(pe, 1), (pe,))
m = next(x for x in S.npc_of(1) if x['state'] == 'active' and x is not n)
m['walk'] = None; m.pop('post', None)
m['task'] = {'kind': 'attack', 'phase': 'battle', 'target': pe, 'origin': pe, 'depart': tt - 999, 'arrive': tt - 900, 'since': tt - 999}
loc = S.npc_location(m, tt)[0]
chk('E2 a left-over red NPC is not drawn in the blue-vs-yellow battle', loc != pe, (loc, pe))
S.npc_tick(tt + 10)
chk('E3 the tick sends it home', not (m.get('task') and m['task'].get('target') == pe), m.get('task'))
S.BATTLES.pop(pe, None)
