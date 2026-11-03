"""test52 (user 2026-10-24 20:18): after units retreated through a portal, F7 in the battle opens the deploy window and
the chosen off-field units (retreated / reserve, alive) enter again as a reinforcement squad."""
import sys, os, struct, time
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
for f in ('npcs.json', 'world.json'):
    if os.path.exists(f): os.remove(f)
import sgserver as S
S.LOG = open('/tmp/mp/server52.log', 'w', encoding='utf-8')
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
put = []
_real_put = S.put_squad
S.put_squad = lambda s, sq: put.append([q[0] for q in sq])
class W:
    def is_closing(self): return False
acc = 'jjjjjjjj'
accs, a = S.get_account(acc)
a["units"] = [{"uid": 2001 + i, "chassis": "Imp", "deploy": i + 1, "hp": 900} for i in range(4)]
S.save_accounts({**accs, acc: a})
class Pl:
    def __init__(s):
        s.acc = acc; s.cmd = {'nation': 1}; s.w = W(); s.map = 600001; s.battle = {'map': 600001}; s.battle_mode = 1
        s.hero_uid = 4; s.alive_units = {2001, 2002}; s.lost_units = set(); s.sent = []; s.spectator = False
        s.reserve = []; s.last_reinforce = 0; s.lang = 'en'; s.enc = 'latin-1'
    def send(s, d): s.sent.append(d)
p = Pl()   # 2003 and 2004 retreated earlier (not on the field, alive)
S._pkt_19(p, bytes([0x19, 0]), 0x19)
chk("F7 in battle with units off the field -> deploy window (0x1C)", getattr(p, "f7_choose", False) and any(d[:1] == b"\x1c" for d in p.sent))
body = bytes([0x19, 1, 4]) + b"".join(struct.pack(">IB", 2001 + i, i + 1) for i in range(4))
S._pkt_19(p, body, 0x19)
chk("OK in the deploy window -> the chosen retreated units enter (not the ones on the field)", put and set(put[-1]) == {2003, 2004}, put)
p2 = Pl(); p2.last_reinforce = time.time()
S._pkt_19(p2, bytes([0x19, 0]), 0x19)
chk("F7 during the cooldown -> wait notice, no window", not getattr(p2, "f7_choose", False) and any(d[:1] == b"\x5b" for d in p2.sent))
# (21:56) whole squad retreated: the re-deploy box's REINFORCE (client 0x53) opens the deploy window first; the
# division chosen there enters after OK
put.clear()
p3 = Pl(); p3.alive_units = set(); p3.redeploy_pending = True; p3.redeploy_chosen = False
S._pkt_53(p3, bytes([0x53]), 0x53)
chk("REINFORCE after a retreat -> deploy window, nobody enters yet", any(d[:1] == b"\x1c" for d in p3.sent) and not put)
body = bytes([0x19, 1, 4]) + bytes(struct.pack(">IB", 2003, 1) + struct.pack(">IB", 2004, 2) + struct.pack(">IB", 2001, 0) + struct.pack(">IB", 2002, 0))
S._pkt_19(p3, body, 0x19)
chk("OK -> the chosen squad enters", put and set(put[-1]) == {2003, 2004} and not p3.redeploy_pending, put)
# (23:51) a unit that already was on this battle map (left through the portal) re-enters with a NEW id
S.put_squad = _real_put
p4 = Pl(); p4.alive_units = set(); p4.put_args = {2003: {"slot": 0}, 2004: {"slot": 1}}; p4.unit_pos = {}; p4.unit_cmb = {}
p4.entry_pos = (500, 500); p4.battle_stats = {"units": [2003, 2004], "kills": {2003: 2}}; p4.sent = []
p4.t0 = time.monotonic()
S.battle_members = lambda s: [s]
sq = [(2003, 1, 1, 900, 100, [100] * 9, 10), (2005, 1, 1, 900, 100, [100] * 9, 10)]
a = S.get_account(acc)[1]; a["units"].append({"uid": 2005, "chassis": "Imp", "deploy": 0, "hp": 900}); S.save_accounts({**S.get_account(acc)[0], acc: a})
S.put_squad(p4, sq)
ids = sorted(p4.alive_units)
chk("re-entering unit gets a new id, a fresh one keeps its id", 2003 not in ids and 2005 in ids and len(ids) == 2, ids)
new = [x for x in ids if x != 2005][0]
chk("its battle records follow it (kills)", p4.battle_stats["kills"].get(new) == 2 and new in p4.battle_stats["units"])
chk("the account unit has the new id", any(u["uid"] == new for u in S.get_account(acc)[1]["units"]))
chk("client told: old id removed, new id added (0x16 sub 3 / sub 2)", any(d[:2] == b"\x16\x03" for d in p4.sent) and any(d[:2] == b"\x16\x02" for d in p4.sent))
chk("slots 0.. for the division panels", sorted(p4.put_args[u]["slot"] for u in ids) == [0, 1], [p4.put_args[u]["slot"] for u in ids])
