"""test45 (user 2026-10-24 06:16: many NPCs on the strategic map, none in the battle): an NPC battle whose NPC_RT had an
entry without "nid" crashed the end check (KeyError) - the battle loop stopped, the NPC units froze, the battle never
ended.  Checks: the end check survives such entries, NPCs that get no unit onto the map do not stay "in battle",
and an error in one tick does not stop the battle loop."""
import sys, os, time, random, asyncio
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
for f in ('npcs.json', 'world.json'):
    if os.path.exists(f): os.remove(f)
import sgserver as S
S.LOG = open('/tmp/mp/server45.log', 'w', encoding='utf-8')
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
random.seed(2)
now = time.time()
S.npc_tick(now)
S.npc_sync = lambda *a, **k: None
for m in S.npc_all():
    m['state'] = 'active'; m['rest_until'] = 0; m['task'] = None
PL = S.nation_planet(1)
P = PL * 100000 + 3
A, D = 1, next(n for n, *_ in S.NATIONS if n != 1 and S.nation_planet(n) == PL and not S.same_side(n, 1))
g = S.Ghost(P, A)
B = S.BF.new_battle(map=P, t0=g.t0, targets=g.targets, pocs={1: {'x': 500, 'y': 500, 'strength': 10, 'progress': 10,
                    'owner': D, 'capturing': False}}, members=set(), owner=g, ghost=g, defender=D, npc_attacker=A)
g.battle = B
S.BATTLES[P] = B
da = S.npc_of(A)[0]; dd = S.npc_of(D)[0]
B['targets'][70001] = {'npc': dd['id'], 'nation': D, 'hp': 100, 'max': 100}
S.NPC_RT[dd['id']] = {'B': B, 'dead': 0, 'units': 1, 'nid': D, 'waves': 0}
S.NPC_RT[da['id']] = {'dead': 0, 'units': 0, 'B': B}          # the old-style entry without "nid"
try:
    S.battle_judge(None, 'tick', B)
    chk('end check survives an NPC_RT entry without nid', True)
except Exception as e:
    chk('end check survives an NPC_RT entry without nid', False, repr(e))
chk('attackers without units on the map -> battle decided', bool(B.get('won')), B.get('won'))
# join: an NPC that npc_spawn cannot place does not stay "in battle"
S.BATTLES.clear(); B['won'] = False
S.set_province_owner(PL * 100000 + S.GATE_SPOTS[P % 100000][0][0], A)   # (10-31) NPCs enter only through a gate of their side
class W:
    def is_closing(self): return False
class Pl:
    def __init__(s):
        s.acc = 'SG001'; s.cmd = {'nation': A}; s.w = W(); s.battle_gen = 1; s.spectator = False; s.client_hash = 'x'
        s.client_release = '9.9.9'; s.targets = {}; s.logged_in = True; s.alive_units = set(); s.unit_hp = {}; s.map = P
    def send(s, *a, **k): pass
pl = Pl()
B2 = S.BF.new_battle(map=P, t0=0, targets=pl.targets, pocs=dict(B['pocs']), members={pl}, owner=pl, defender=D)
pl.battle = B2
S.BATTLES[P] = B2
S.spawn = lambda c: (c.close() if hasattr(c, 'close') else None)
ns = [m for m in S.npc_of(A) if m is not da][:3]
for m in ns:
    m['task'] = {'kind': 'attack', 'target': P, 'phase': 'march', 'depart': now - 100, 'arrive': now, 'path': [P - 1, P]}
real_spawn = S.npc_spawn
def spawn_two(s, mapid, nid, npcs, *a, **k):          # room for two of the three
    return real_spawn(s, mapid, nid, npcs[:2], *a, **k)
S.npc_spawn = spawn_two
why = S.npc_join_attack(ns, B2, now)
S.npc_spawn = real_spawn
inb = [m['name'] for m in ns if (m.get('task') or {}).get('phase') == 'battle']
chk('join: entered', why is None, why)
chk('join: only the placed NPCs are in battle, the third goes home', len(inb) == 2 and not ns[2].get('task'), (inb, ns[2].get('task')))
chk('join: every NPC_RT entry of the battle has its nation', all(rt.get('nid') for rt in S.NPC_RT.values() if rt.get('B') is B2))
# the battle loop goes on after an error in one tick
calls = {'n': 0}
real_poc = S.poc_step
def bad_poc(s, b):
    calls['n'] += 1
    if calls['n'] == 1:
        raise KeyError('nid')
    return calls['n'] >= 3
S.poc_step = bad_poc
LOGGED = []
real_log = S.log
S.log = lambda m, *a, **k: LOGGED.append(m)          # the expected error is logged, not printed
S.POC_TICK = 0.01
pl.battle = None; pl.battle_gen = 7; pl.poc_won = False
async def go():
    await S.battle_loop(pl, 7)
asyncio.run(asyncio.wait_for(go(), 10))
S.poc_step = real_poc
S.log = real_log
chk('battle loop survives one bad tick', calls['n'] >= 3, calls)
chk('... and logs the error', any('battle loop error #1' in m for m in LOGGED), len(LOGGED))
