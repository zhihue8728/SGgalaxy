"""test54 (user 2026-10-24 22:48): NPC platoons - 42 units per NPC in platoons of one kind (6..8 = deploy rule), 3..4
complementary platoons go into a battle, chosen by the enemy on the map, worn-out / useless platoons are replaced."""
import sys, os, collections
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
S.LOG = open('/tmp/mp/server54.log', 'w', encoding='utf-8')
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
nid = 1
S.npc_ensure_roster(nid)
ns = S.npc_of(nid)
chk("every NPC carries 42 units", all(len(n["squad"]) == 42 for n in ns), collections.Counter(len(n["squad"]) for n in ns))
pls = [(n, S.npc_platoons(n)) for n in ns]
chk("platoons of one kind", all(len({n["squad"][i][0] for i in idx}) == 1 for n, pl in pls for _r, _k, idx in pl))
chk("platoon size = deploy rule 6..8", all(len(idx) <= n["doctrine"]["pp"] and 6 <= len(idx) <= 8 for n, pl in pls for _r, _k, idx in pl))
chk("(10-31) platoons into a battle, never more units than the deploy limit", all(1 <= len({S.npc_platoon_of(n, u[6]) for u in S.npc_battle_units(n, 0, nid)})
    and len(S.npc_battle_units(n, 0, nid)) <= S.npc_deploy(n) for n in ns[:10]))
n = next(n for n in ns if n["doctrine"].get("aa"))
pl = S.npc_platoons(n)
aa_k = next(k for k, (r, _c, _i) in enumerate(pl) if r == "aa")
# enemy on the map: aircraft only
air = S.npc_pool()
fly = next(p for p in air if p.get("air") and p.get("armed"))
st9 = S.unit_stats9(S.npc_unit(fly["code"], 30))
B = {"members": [], "targets": {70000 + i: {"hp": 900, "npc": 999, "nation": 2, "put": {"st9": st9, "kind": 2}} for i in range(12)}}
u = S.npc_battle_units(n, 0, nid, ctx=B)
chk("enemy aircraft -> the anti-air platoon comes", aa_k in {S.npc_platoon_of(n, x[6]) for x in u},
    sorted({(S.npc_platoon_of(n, x[6]), x[0]) for x in u}))
chk("the capturers come with the fast platoon", sum(1 for x in u if x[7]) == S.NP.SQUAD_FAST and
    all(pl[S.npc_platoon_of(n, x[6])][0] == "fast" for x in u if x[7]))
chk("units carry their platoon (brain squads)", True)
# ---- swap: a worn-down platoon is replaced by a fresh one, a useless one leaves
import time
pid = next(p for p in S.planet_provinces(S.nation_planet(nid)) if p not in S.CAPITALS.values())
g = S.Ghost(pid, nid)
B = S.BF.new_battle(map=pid, t0=g.t0, targets=g.targets, pocs={}, members=set(), owner=g, ghost=g, defender=0,
                    npc_attacker=nid, opened=time.time())
g.battle = B
n = ns[1]
S.NPC_RT.pop(n["id"], None)
S._npc_put_squad(g, nid, n, 0, (800, 800), "assault")
rt = S.NPC_RT[n["id"]]
rt["B"] = B
on = collections.Counter(tg["plt"] for tg in g.targets.values() if tg.get("npc") == n["id"])
chk("(10-31) fielded within the deploy limit, every unit knows its platoon", sum(on.values()) <= S.npc_deploy(n) and len(rt["fielded"]) == len(on), dict(on))
k0 = max(on)                     # wear one platoon down to 1 unit
dead = [t for t, tg in g.targets.items() if tg.get("plt") == k0][1:]
for t in dead:
    g.targets[t]["hp"] = 0
now = time.time()
rt["wave_t"] = now - 1
mine_ = [(t, tg) for t, tg in g.targets.items() if tg.get("npc") == n["id"] and tg["hp"] > 0]
S._platoon_wave(g, B, now, n["id"], rt, n, mine_, None)
on2 = collections.Counter(tg["plt"] for tg in g.targets.values() if tg.get("npc") == n["id"] and tg["hp"] > 0)
new = set(on2) - set(on)
chk("worn-down platoon -> a fresh platoon comes in (up to the deploy limit)", len(new) == 1 and sum(on2.values()) <= S.npc_deploy(n), (dict(on), dict(on2)))
chk("... and is a different platoon of the reserve", k0 not in new)
# the enemy turns out to be aircraft only: platoons that cannot hit air leave, anti-air comes
fly_st = S.unit_stats9(S.npc_unit(fly["code"], 30))
for i in range(10):
    g.targets[90000 + i] = {"hp": 900, "npc": 999, "nation": 2, "put": {"st9": fly_st, "kind": 2}, "pos": (900, 900)}
th = S.battle_threat(B, nid)
g.targets[95000] = {"hp": 500, "npc": 777777, "nation": nid, "put": {}}   # (10-31) not alone: swapping allowed
B["pocs"][3] = {"x": 500, "y": 500, "owner": 0}
rt["wave_t"] = now - 1
mine_ = [(t, tg) for t, tg in g.targets.items() if tg.get("npc") == n["id"] and tg["hp"] > 0]
before = {tg["plt"] for _t, tg in mine_}
_useless = {tg["plt"] for _t, tg in mine_ if tg.get("plt") != 0 and tg.get("plt") in rt["fielded"] and all(S.unit_effect((x.get("put") or {}).get("st9"), th) <= 0
             for _t2, x in mine_ if x.get("plt") == tg["plt"])}
S._platoon_wave(g, B, now + 100, n["id"], rt, n, mine_, th)
gone = [tg for _t, tg in mine_ if tg.get("withdraw")]
chk("platoons that cannot hit aircraft walk out, the capturers stay (POCs left)", {tg["plt"] for tg in gone} == _useless
    and not any(tg.get("plt") == 0 for tg in gone), (_useless, {tg["plt"] for tg in gone}))
u = S.npc_battle_units(n, 0, nid, ctx=B, platoons=1, capture=False)
chk("a replacement against aircraft never brings guns that cannot hit them",
    not u or all(S.unit_effect(x[2], th) > 0 for x in u), sorted({x[0] for x in u}))
