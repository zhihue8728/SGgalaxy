"""test108 (user 2026-10-31 10:10-10:14 "NPCs must attack more, many just stand"; "after a battle the NPC goes back to the
capital's factory to repair, no 30 min wait"; "no limit for a win chance below the personality's threshold"):
A. score never rejects a target for a low win chance (npc.py MIN_WIN_GATE False) - even the cautious / guard personas;
B. a damaged NPC whose task ends walks home to the capital (no fallback post next door);
C. home in the capital it is repaired at once (every unit 100 %), not over HEAL_SECONDS; on the road it is not;
D. idle reasons are counted and logged every 10 min (npc_idle_report)."""
import sys, os, time, random
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
for f in ('npcs.json', 'world.json'):
    if os.path.exists(f): os.remove(f)
import sgserver as S
import npc as NP
S.LOG = open('/tmp/mp/server108.log', 'w', encoding='utf-8')
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
random.seed(8)
now = time.time()
S.npc_tick(now)
NA = 1
cap = S.CAPITALS[NA]
n = next(x for x in S.npc_of(NA) if x['state'] == 'active')
c = {'pid': 1, 'owner': 3, 'kind': 'enemy', 'dist_cap': 1, 'def_power': 10000.0}
ok = all(NP.score(c, dict(n, persona=p), 10.0) is not None for p in NP.PERSONAS)
chk('A  a hopeless target is still acceptable for every persona (no min_win gate)', ok)
# B: a damaged NPC in an enemy province after its task
pl = cap // 100000
nb = [pl * 100000 + q for q in S.PORTAL_LINKS.get(cap % 100000, ())]
a = nb[0]
S.set_province_owner(a, NA)
b = next(pl * 100000 + q for q in S.PORTAL_LINKS.get(a % 100000, ()) if pl * 100000 + q not in (cap,) and pl * 100000 + q not in S.CAPITALS.values())
S.set_province_owner(b, 3)
for _ in range(3):
    S.npc_ensure_roster(NA)                         # (repo roster: its one-time migrations settle first)
hl = NP.health(n)
for i in range(len(hl)): hl[i] = 0.4
n['walk'] = None; n.pop('post', None)
n['task'] = {'kind': 'attack', 'phase': 'battle', 'target': b, 'origin': a, 'depart': now - 99, 'arrive': now - 50, 'since': now - 99}
t1 = now + 10
S.BATTLES[b] = {'map': b, 'defender': 3, 'npc_attacker': NA, 'targets': {}}
S.npc_release(n, t1, 60, False)
S.BATTLES.pop(b, None)
chk('B  damaged after the battle: walks home to the capital, no fallback post', not n.get('post') and n.get('walk')
    and n['walk']['path'][-1] == cap, (n.get('post'), n.get('walk')))
n['heal_t'] = t1                                   # (a roster from the repo files carries an old heal time)
S.npc_tick(t1 + 5)
chk('C1 still on the road: not repaired', min(NP.health(n)) < 0.5, min(NP.health(n)))
t2 = n['walk']['arrive'] + 5
S.npc_tick(t2)
chk('C2 home in the capital: every unit repaired at once', min(NP.health(n)) >= 1.0 and NP.readiness(n) >= 1.0, min(NP.health(n)))
log = open('/tmp/mp/server108.log', encoding='utf-8').read() if S.LOG.flush() is None else ''
chk('C3 logged as a factory repair', "repaired" in log and "capital's factory" in log)
for k in range(80):
    S.npc_tick(t2 + 10 + k * 10)
S.LOG.flush()
log = open('/tmp/mp/server108.log', encoding='utf-8').read()
chk('D  idle report written', 'NPC idle report nation' in log)
