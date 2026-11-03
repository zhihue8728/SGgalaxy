"""test83 (user 2026-10-27 "NPC too?"): an NPC unit ATTACKING whose target walks out of range (true position from the
0x1d snapshot) walks after it (0x1A, walk animation) instead of being dragged by client patch F6 in the attack state."""
import sys, os, time, struct
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
S.LOG = open('/tmp/mp/server83.log', 'w', encoding='utf-8')
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
att = [t for t in mine if g.targets[t].get("state") == "combat" and g.targets[t].get("target") == 5001]
chk("NPC units attack the player unit after the approach", att, len(mine))
p.unit_pos[5001] = (3400, 1000)                     # the target runs away
S.player_unit_moved = None
n0 = len(sent)
for k in range(40, 46):
    for t in att:                                   # snapshot: the NPC still stands where it was shooting
        tg = g.targets.get(t)
        if tg is not None and not tg.get("chase"):
            tg["spos"], tg["snap_t"] = tuple(tg["pos"]), now + k
    S.npc_step(g, B, now + k)
moves = {struct.unpack_from(">I", m, 1)[0] for _t, ms in sent[n0:] for m in ms if m[:1] == b"\x1a"}
chk("attacking units whose target ran out of range walk after it (MOVE 0x1A)", att and all(t in moves for t in att), (att, moves))
slide = [t for t in att if t in g.targets and g.targets[t].get("state") == "combat" and not g.targets[t].get("chase")
         and S.AL.dist(g.targets[t].get("spos") or g.targets[t]["pos"], (3400, 1000)) > S.npc_weapon_range(g.targets[t]) + 200]
chk("no unit left in the attack state far out of range (F6 slide)", not slide, slide)
