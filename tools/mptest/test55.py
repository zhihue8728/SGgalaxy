"""test55 (user 2026-10-24 22:48): NPC path finding in live battles - ground NPC units get way points from the walk grid
(A* on 64 px cells, smoothed), destinations on walkable ground, legs followed one after the other."""
import sys, os, time, struct
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
S.LOG = open('/tmp/mp/server55.log', 'w', encoding='utf-8')
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
import json, random
W = json.load(open('walk_grids.json'))
# raw path quality on every map
fails = n = 0; bad_leg = 0; t0 = time.time()
for k in list(W):
    g = S.BSIM.Grid.from_entry(W[k]); r = random.Random(7)
    for _ in range(8):
        a = g.snap((r.uniform(0, g.w * 32), r.uniform(0, g.h * 32)), 16); b = g.snap((r.uniform(0, g.w * 32), r.uniform(0, g.h * 32)), 16)
        if not a or not b:
            continue
        p = g.path(a, b); n += 1
        if p is None:
            fails += 1; continue
        pts = [a] + p
        bad_leg += sum(1 for q in p[:-1] if not g.ok(*g.cell(q)))
ms = (time.time() - t0) * 1000 / max(1, n)
chk("A* way points on every map (random pairs)", n > 300 and fails <= n * 0.05, (n, fails))
chk("way points on walkable ground", bad_leg == 0, bad_leg)
chk("a path costs a few ms", ms < 25, round(ms, 1))
# live battle: the brain's moves become legs
nid = 1
S.npc_ensure_roster(nid)
n_ = S.npc_of(nid)[2]
pid = next(p for p in S.planet_provinces(S.nation_planet(nid)) if p not in S.CAPITALS.values())
g = S.Ghost(pid, nid)
B = S.BF.new_battle(map=pid, t0=g.t0, targets=g.targets, pocs={}, members=set(), owner=g, ghost=g, defender=0,
                    npc_attacker=nid, opened=time.time())
g.battle = B
grid = S.npc_map_grid(g)
chk("battle map has a walk grid", grid is not None)
S.NPC_RT.pop(n_["id"], None)
spots = sorted((tuple(p) for p in S.SPAWN_SPOTS.get(S.alien_context(g, pid)[3], [])))
S._npc_put_squad(g, nid, n_, 0, spots[0], "assault")
S.NPC_RT[n_["id"]]["B"] = B
sent = []
_og = S.order_gate
def cap(s, b, msgs, now, who="AI"):
    sent.extend(m for m in msgs if m[:1] == b"\x1a")
    return _og(s, b, msgs, now, who)
S.order_gate = cap
far = max(spots, key=lambda p: (p[0] - spots[0][0]) ** 2 + (p[1] - spots[0][1]) ** 2)
tid, tg = next((t, x) for t, x in g.targets.items() if x.get("npc") == n_["id"] and (x.get("put") or {}).get("kind") != 2)
# the move_to of npc_step is local: drive it through one brain-less step with a forced order
B["pocs"].update({7: {"x": far[0], "y": far[1], "strength": 100, "progress": 100, "owner": 2, "capturing": False}})
g.pocs = B["pocs"]
now = time.time()
S.npc_step(g, B, now)
routes = [x for x in g.targets.values() if x.get("route")]
print("units with a route after the first step:", len(routes))
# direct check: give one unit a far destination through the same code path (brain order)
br = B.get("brains") or {}
mv0 = len(sent)
for k in range(30):
    S.npc_step(g, B, now + k)
legs = [struct.unpack_from(">IHH", m, 1) for m in sent]
okp = [grid.ok(x // 32, y // 32) for _u, x, y in legs]
chk("NPC move orders go to walkable ground", legs and sum(okp) >= len(okp) * 0.97, (len(legs), len(okp) - sum(okp)))
chk("some moves are split into legs (route)", any(x.get("leg_t") for x in g.targets.values()))
rc = B.get("_routes") or {}
multi = [v[1] for v in rc.values() if v[1] and len(v[1]) > 1]
chk("long moves across the map get multi-leg routes", len(multi) >= 1, (len(rc), len(multi)))
