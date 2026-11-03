"""test82 (user 2026-10-27 'aliens move without a leg animation'): an alien attacking a target OUT of range gets a MOVE
(lump 0x1A, client walk state) toward it first, the attack 0x2B only in range; re-aimed when the target moves; an
attacking alien whose target walked away (snapshot position) walks after it instead of sliding in the attack state."""
import struct, sys, os, time
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
for f in ('npcs.json', 'world.json'):
    if os.path.exists(f): os.remove(f)
import sgserver as S
S.LOG = open('/tmp/mp/server82.log', 'w', encoding='utf-8')
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
def mk(pos=(1000.0, 1000.0), rng=200, spd=20):
    st9 = [10, 0, 100, 50, rng, 100, 0, 0, 100]
    return {"hp": 500, "max": 500, "pos": pos, "home": pos, "state": "idle", "target": None,
            "put": {"st9": st9, "spd": spd, "kind": 1}}
now = 1000.0
# 1. out of range -> walk, no attack
tg = mk(); m = []
r = S.order_attack(60001, tg, 7, (2000.0, 1000.0), now, m)
chk('out of range: no attack yet', r is False and all(x[0] != 0x2B for x in m))
chk('out of range: one MOVE lump 0x1A with the 11-byte player layout', len(m) == 1 and m[0][0] == 0x1A and len(m[0]) == 12
    and struct.unpack_from('>I', m[0], 1)[0] == 60001 and m[0][9:] == b'\0\0\0', m[0].hex() if m else None)
x, y = struct.unpack_from('>HH', m[0], 5)
chk('walks to 3/4 of its range in front of the target', abs(x - (2000 - 150)) <= 1 and y == 1000, (x, y))
chk('chase + walk leg recorded', tg.get("chase") and tg["chase"][0] == 7 and tg.get("mv") and tg["state"] == "combat")
# 2. in range -> attack at once
tg2 = mk(); m = []
r = S.order_attack(60002, tg2, 7, (1150.0, 1000.0), now, m)
chk('in range: attack 0x2B at once', r is True and len(m) == 1 and m[0][0] == 0x2B and not tg2.get("chase"))
# 3. chase step: still walking -> nothing new; target moved after REDO -> re-aim; arrived (snapshot) -> attack
m = []
walking = S.chase_step(60001, tg, (2000.0, 1000.0), now + 1, m)
chk('chasing: walking, no new order within REDO', walking is True and m == [], m)
m = []
walking = S.chase_step(60001, tg, (2000.0, 1400.0), now + 3, m)
chk('target moved: re-aimed with a new MOVE', walking is True and len(m) == 1 and m[0][0] == 0x1A)
S.snapshot_pos(tg, (1980.0, 1250.0), now + 4)           # snapshot: the alien is now close to the target
m = []
walking = S.chase_step(60001, tg, (2000.0, 1400.0), now + 4.2, m)
chk('in range after the walk: attack 0x2B, chase over', walking is False and len(m) == 1 and m[0][0] == 0x2B
    and not tg.get("chase") and tg.get("mv") is None, [x.hex() for x in m])
# 4. attacking, target walked away (snapshot) -> walk after it
S.snapshot_pos(tg, (1980.0, 1250.0), now + 8)
m = []
walking = S.chase_step(60001, tg, (3000.0, 1250.0), now + 8.5, m)
chk('target ran away: walks after it (0x1A), no sliding attack', walking is True and len(m) == 1 and m[0][0] == 0x1A
    and tg.get("chase"), [x.hex() for x in m])
# 5. estimate along the walk leg
tg3 = mk(pos=(0.0, 0.0), spd=10); m = []
S.order_attack(60003, tg3, 8, (4000.0, 0.0), now, m)
p = S._npc_est_pos(tg3, now + 10)                          # 20 px/s, leg is 1.3x slower in the model
chk('position estimate moves along the leg', 100 < p[0] < 200 and p[1] == 0, p)
# 6. support / no weapon -> plain attack order as before
tg4 = mk(rng=0); m = []
chk('no weapon range: attack order as before', S.order_attack(60004, tg4, 7, (3000.0, 0.0), now, m) and m[0][0] == 0x2B)
