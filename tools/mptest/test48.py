"""test48 (user 2026-10-24 12:34): the client sends 0x2f about 5 s after a unit died (004e3c70 -> 004e1990).  That is
not a retreat: a dead unit's 0x2f must not make the commander leave, even when it was his last unit."""
import sys, os, struct
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
for f in ('npcs.json', 'world.json'):
    if os.path.exists(f): os.remove(f)
import sgserver as S
S.LOG = open('/tmp/mp/server48.log', 'w', encoding='utf-8')
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
calls = []
S.squad_lost = lambda s, why: calls.append(("squad_lost", why))
S.map_peers = lambda s: []
class W:
    def is_closing(self): return False
class Pl:
    def __init__(s):
        s.acc = 'jjjjjjjj'; s.cmd = {'nation': 1}; s.w = W(); s.map = 600001; s.battle = {'map': 600001}
        s.hero_uid = 4; s.alive_units = set(); s.lost_units = {1018}; s.sent = []; s.spectator = False
        s.targets = {}
    def send(s, d): s.sent.append(d)
p = Pl()
S.retreat(p, 1018, 600000)
chk("0x2f of the dead last unit: commander does not leave", not getattr(p, "retreating", False) and not calls and not p.sent,
    (getattr(p, "retreating", False), calls, len(p.sent)))
p = Pl(); p.alive_units = {1020, 1021}
S.retreat(p, 1018, 600000)
chk("0x2f of a dead unit while others fight: nothing happens", p.alive_units == {1020, 1021} and not p.sent)
p = Pl(); p.alive_units = {1020, 1021}
S.retreat(p, 1020, 600000)
chk("a living unit at the exit portal still retreats", p.alive_units == {1021} and any(d[0] == 0x19 for d in p.sent))
p = Pl(); p.alive_units = {1020}
S.retreat(p, 1020, 600000)
chk("the last living unit retreating -> reinforce box", calls == [("squad_lost", "retreated")], calls)
b = bytes([0x2f]) + struct.pack(">IHIi", 1018, 0, 0, 600000) + struct.pack(">HH", 100, 100)
p = Pl(); calls.clear()
S._pkt_2f(p, b, 0x2f)
chk("packet path: dead unit 0x2f ignored", not calls and not getattr(p, "retreating", False))
# (20:13) no retreat through a gate into an ENEMY province (while a friendly / neutral neighbour exists)
S.side_nation = lambda s: 1
_nb = [600000 + q for q in S.PORTAL_LINKS.get(1, ())]
_enemy = next(q for q in _nb if q != 600000)
S.set_province_owner(_enemy, 2); S.set_province_owner(600000, 1)
p = Pl(); p.alive_units = {1020, 1021}
S.retreat(p, 1020, _enemy)
chk("retreat through the gate to an enemy province is refused (unit stays, notice)", p.alive_units == {1020, 1021}
    and not any(d[0] == 0x19 for d in p.sent) and p.sent, (p.alive_units, [d[:1].hex() for d in p.sent]))
p = Pl(); p.alive_units = {1020, 1021}
S.retreat(p, 1020, 600000)
chk("retreat through the gate to an own province still works", p.alive_units == {1021})
