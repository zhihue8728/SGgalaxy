"""test61 (user 2026-10-25 11:05): bombArd landing zone = gun pos + aim x ground range, radius = sight; NPCs inside walk out."""
import sys, os, time, types
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
S.LOG = open('/tmp/mp/server61.log', 'w', encoding='utf-8')
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
mine = {t: tg for t, tg in g.targets.items() if tg.get("npc") is not None and tg["hp"] > 0}
ids = list(mine); now = time.time()
a, b_, c = mine[ids[0]], mine[ids[1]], mine[ids[2]]
for tg in (a, b_, c): tg["nation"] = nid; tg.pop("mv", None)
GP = (1000, 1000); AIM = (1000 + 800, 1000)           # gun fires east
rng = 560
a["pos"] = (GP[0] + rng + 20, GP[1])                   # inside the circle
b_["pos"] = (GP[0] - 300, GP[1])                       # behind the gun: outside
c["pos"] = (GP[0] + rng, GP[1] + 900)                  # far away
enemy = 2 if nid != 2 else 3
S.side_nation = lambda o: enemy
st9 = [60, 0, 5, 40, rng, 30, 0, 0, 0]
o = types.SimpleNamespace(spectator=False, alive_units={77}, unit_pos={77: GP}, unit_cmb={77: (st9, 60)},
                          move_dest={77: (AIM, now - 1)}, put_args={77: {"sight": 300}})
S.npc_arty_zones(g, [o], mine, now)            # first call: the gun just stopped
S.npc_arty_zones(g, [o], mine, now + 3)        # stood still 3 s: zone counts
chk("NPC inside the circle is marked", a.get("shell_zone") is not None, a.get("shell_zone"))
chk("circle centre = gun + aim x range", a.get("shell_zone") and abs(a["shell_zone"][0][0] - (GP[0] + rng)) < 2)
chk("NPC behind the gun is not marked", "shell_zone" not in b_)
chk("far NPC is not marked", "shell_zone" not in c)
moves = []
def mv(tid, tg, dest, poc_id=None): moves.append((tid, dest)); tg["mv"] = None
S.npc_dodge(g, nid, mine, now + 3, mv)
d = [dd for t, dd in moves if t == ids[0]]
chk("the NPC walks out of the circle", d and S.AL.dist(d[0], a["shell_zone"][0]) >= 300, d)
chk("others stay", not any(t in (ids[1], ids[2]) for t, _ in moves))
