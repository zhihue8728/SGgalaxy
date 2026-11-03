"""test46 (user 2026-10-24 06:37): the battle-control dialog (0x1e) lists NPC commanders like players, and an NPC
commander without units leaves the battle.
Dialog layout (004af1e0): u32 map, u8, u8, u32 defender, s8 title, u8 n x {s8 name, u32 NATION, u32 SIDE}, u8 wait,
u8 can-enter.  NATION must be a 0x0F table id (attacker list 00408749 dereferences the lookup)."""
import sys, os, time, random, struct
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
for f in ('npcs.json', 'world.json'):
    if os.path.exists(f): os.remove(f)
import sgserver as S
S.LOG = open('/tmp/mp/server46.log', 'w', encoding='utf-8')
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
random.seed(4)
now = time.time()
S.npc_tick(now)
S.npc_sync = lambda *a, **k: None
for m in S.npc_all():
    m['state'] = 'active'; m['rest_until'] = 0; m['task'] = None

def parse_1e(d):
    o = 0
    assert d[0] == 0x1E; o = 1
    mp, = struct.unpack_from('>I', d, o); o += 4
    o += 2
    dfd, = struct.unpack_from('>I', d, o); o += 4
    L = d[o]; o += 1 + L
    n = d[o]; o += 1
    rows = []
    for _ in range(n):
        L = d[o]; name = d[o + 1:o + 1 + L]; o += 1 + L
        nat, side = struct.unpack_from('>II', d, o); o += 8
        rows.append((name, nat, side))
    wait, can = d[o], d[o + 1]
    return mp, dfd, rows, wait, can, len(d) - o - 2

class W:
    def is_closing(self): return False
class Pl:
    def __init__(s, acc, nat):
        s.acc = acc; s.cmd = {'nation': nat}; s.w = W(); s.battle_gen = 1; s.spectator = False; s.client_hash = 'x'
        s.client_release = '9.9.9'; s.targets = {}; s.logged_in = True; s.alive_units = set(); s.unit_hp = {}
        s.sent = []; s.lang = 'zh-tw'
    def send(s, d, *a, **k): s.sent.append(bytes(d))
PL = S.nation_planet(1)
P = PL * 100000 + 3
A = 1
D = next(n for n, *_ in S.NATIONS if n != 1 and S.nation_planet(n) == PL and not S.same_side(n, 1))
fighter = Pl('jjjjjjjj', D)
B = S.BF.new_battle(map=P, t0=0, targets=fighter.targets, members={fighter}, owner=fighter, defender=D,
                    pocs={1: {'x': 500, 'y': 500, 'strength': 10, 'progress': 10, 'owner': D, 'capturing': False}})
fighter.battle = B
S.BATTLES[P] = B
na, nd = S.npc_of(A)[0], S.npc_of(D)[0]
B['targets'][70001] = {'npc': na['id'], 'nation': A, 'hp': 100, 'max': 100, 'urole': 'line'}
B['targets'][70002] = {'npc': nd['id'], 'nation': D, 'hp': 100, 'max': 100, 'urole': 'line'}
B['targets'][60001] = {'hp': 50}                                     # an alien
viewer = Pl('hhhhhhhh', A)
S.send_battle_control(viewer, P, 300, 300)
pk = next(d for d in viewer.sent if d[0] == 0x1E)
mp, dfd, rows, wait, can, rest = parse_1e(pk)
names = [r[0].decode('latin-1', 'replace') for r in rows]
ids = {n[0] for n in S.NATIONS} | {0}
chk('dialog parses to the end (wait, can-enter last)', rest == 0 and mp == P and dfd == D, (rest, mp, dfd))
chk('player listed with his NATION (not the hero uid)', ('jjjjjjjj', D, D) in [(n, r[1], r[2]) for n, r in zip(names, rows)], rows)
chk('attacking NPC listed', any(n == na['name'] and r[1] == A and r[2] == A for n, r in zip(names, rows)), names)
chk('defending NPC listed', any(n == nd['name'] and r[1] == D for n, r in zip(names, rows)), names)
chk('alien garrison listed as nation 0', any(r[1] == 0 and r[2] == 0 for r in rows), rows)
chk('every NATION is a 0x0F table id (no crash in the attacker list)', all(r[1] in ids for r in rows), rows)
chk('the count byte matches the rows', len(rows) == 4, len(rows))
# NPC exit
rt_a = S.npc_rt_attach(na['id'], B, A); rt_a.update(units=6, waves=S.NPC_WAVES_MAX, dead=6)
rt_d = S.npc_rt_attach(nd['id'], B, D); rt_d.update(units=6, waves=0)
na['task'] = {'kind': 'attack', 'target': P, 'phase': 'battle', 'since': now}
nd['task'] = {'kind': 'defend', 'target': P, 'phase': 'battle', 'since': now}
B['npc_ids'] = [na['id'], nd['id']]
B['targets'][70001]['hp'] = 0                                       # the attacker's last unit dies
left = S.npc_exit_check(fighter, B, now)
chk('NPC without units leaves the battle', na['id'] in left and not na.get('task') and na['id'] not in B['npc_ids'], (left, na.get('task')))
chk('... and walks home on the strategic map', bool(na.get('walk')) or S.npc_here(na, now) == S.CAPITALS[A], na.get('walk'))
chk('NPC with fighting units stays', nd['id'] not in left and nd.get('task'), left)
# only a support unit left, no reserve -> it walks out, then the commander leaves
B['targets'][70002]['urole'] = 'support'
rt_d['waves'] = S.NPC_WAVES_MAX
S.npc_exit_check(fighter, B, now)
chk('support-only NPC: its units walk out', B['targets'][70002].get('withdraw'), B['targets'][70002])
B['targets'].pop(70002)                                             # reached its gate
left = S.npc_exit_check(fighter, B, now + 5)
chk('... then the commander leaves', nd['id'] in left and not nd.get('task'), left)
viewer.sent.clear()
S.send_battle_control(viewer, P, 300, 300)
_, _, rows2, *_ = parse_1e(next(d for d in viewer.sent if d[0] == 0x1E))
chk('the dialog no longer lists commanders that left', not any(r[0].decode('latin-1') in (na['name'], nd['name']) for r in rows2), rows2)
# (user 2026-10-24 10:53) the server's AIs can never steer a player's unit
fighter.alive_units = {1032, 1033}
ok_m = bytes([0x1A]) + struct.pack('>IHH', 70002, 100, 100) + b'\0\0\0'
bad_m = bytes([0x1A]) + struct.pack('>IHH', 1032, 100, 100) + b'\0\0\0'
bad_a = bytes([0x2B]) + struct.pack('>II', 1033, 70002)
B['targets'][70002] = {'npc': nd['id'], 'nation': D, 'hp': 100, 'max': 100}
got = S.server_orders_only(fighter, [fighter], [ok_m, bad_m, bad_a])
chk('server AI orders for player units are dropped', got == [ok_m], [m.hex() for m in got])
# (user 2026-10-24 11:16) a dead NPC unit is removed from the clients (0x19) and its id is never reused
S.NPC_CORPSE_SECONDS = 0
fighter.sent.clear()
B['targets'][70003] = {'npc': nd['id'], 'nation': D, 'hp': 0, 'max': 100, 'pos': (100, 100), 'x': 100, 'y': 100,
                       'last_hitter': 1032}
S.alien_died(fighter, 70003)
rm = [d for d in fighter.sent if d[:1] == b'\x19' and struct.unpack_from('>I', d, 1)[0] == 70003]
chk('dead NPC unit: the clients are told to remove it (0x19)', bool(rm), [d.hex() for d in fighter.sent][:5])
chk('... and its id is never given out again', 70003 in S.dead_aliens(fighter) and S.next_alien_id(fighter) != 70003)
# (user 2026-10-24 12:18) PUT_UNIT +0x21 (unit behaviour mode): players' units get the client's own default 2,
# server-owned units keep 0
pp = S.build_put_unit(1032, 'Falcon', 'SG001', 100, 100, 2, 3, 1, hp=3300, stats9=[100] * 9, abilities=2)
ps = S.put_server_unit(60001, 'Ghast', 'KaelRhodes', 100, 100, 2, 3, 3, hp=3300, stats9=[100] * 9, abilities=2)
pp2 = S.build_put_unit(60001, 'Ghast', 'KaelRhodes', 100, 100, 2, 3, 3, hp=3300, stats9=[100] * 9, abilities=2)
diff = [i for i in range(len(ps)) if ps[i] != pp2[i]]
chk('player unit mode 2 / server unit mode 0, nothing else changes', len(ps) == len(pp2) and len(diff) == 1
    and pp2[diff[0]] == 2 and ps[diff[0]] == 0, diff)
