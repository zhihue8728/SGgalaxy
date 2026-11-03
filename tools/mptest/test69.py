"""test69 (user 2026-10-25 21:27: Ghast walk animation wrong, no footprints): an NPC unit out of range of its target
gets a MOVE first (client move state: walk animation + footprints), the attack 0x2B only once it is in range."""
import sys, os, time, struct
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
S.LOG = open('/tmp/mp/server69.log', 'w', encoding='utf-8')
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
nid = 1
S.npc_ensure_roster(nid)
pid = next(p for p in S.planet_provinces(S.nation_planet(nid)) if p not in S.CAPITALS.values())
g = S.Ghost(pid, nid)
B = S.BF.new_battle(map=pid, t0=g.t0, targets=g.targets, pocs={}, members=set(), owner=g, ghost=g, defender=0,
                    npc_attacker=nid, opened=time.time())
g.battle = B
n = S.npc_of(nid)[3]
S.NPC_RT.pop(n["id"], None)
S._npc_put_squad(g, nid, n, 0, (1000, 1000), "assault")
S.NPC_RT[n["id"]]["B"] = B
class W:
    def is_closing(self): return False
class P:
    def __init__(s):
        s.acc = 'hhhhhhhh'; s.cmd = {'nation': 2}; s.w = W(); s.battle = B; s.map = pid; s.lang = 'zh-cn'; s.enc = 'gbk'
        s.alive_units = {5001}; s.unit_pos = {5001: (1900, 1000)}; s.put_args = {}
        s.targets = g.targets; s.spectator = False; s.sent = []
    def send(s, d, **k): s.sent.append(d)
p = P()
B["members"] = {p}
sent = []
_og = S.order_gate
S.order_gate = lambda s_, b_, msgs, now_, who="AI": (sent.append((now_, list(msgs))), _og(s_, b_, msgs, now_, who))[1]
now = time.time()
for k in range(40):
    S.npc_step(g, B, now + k)
mine = {t for t, tg in g.targets.items() if tg.get("npc") == n["id"]}
first = {}
bad = []
for t_, ms in sent:
    for m in ms:
        if m[:1] in (b"\x1a", b"\x2b"):
            uid = struct.unpack_from(">I", m, 1)[0]
            if uid in mine and uid not in first:
                first[uid] = m[:1]
            if m[:1] == b"\x2b" and uid in mine:
                tg = g.targets[uid]
                if tg.get("pos") and S.AL.dist(tg["pos"], (1900, 1000)) > S.npc_weapon_range(tg) + 200:
                    bad.append(uid)
melee_like = [u for u in mine if S.npc_weapon_range(g.targets[u]) < 600]
chk("units out of range are first sent a MOVE, not an attack", melee_like and all(first.get(u) == b"\x1a" for u in melee_like if u in first),
    {u: first.get(u) for u in melee_like})
chk("they attack once in range", any(m[:1] == b"\x2b" for _t, ms in sent for m in ms), len(sent))
chk("no attack order sent from far out of range", not bad, bad)
