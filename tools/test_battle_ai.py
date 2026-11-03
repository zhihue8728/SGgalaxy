#!/usr/bin/env python3
"""unit checks of server/battle_ai.py (no server needed)"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "server"))
import battle_ai as BA
ok = True
def chk(n, c, i=""):
    global ok
    ok &= bool(c); print(("PASS " if c else "FAIL ") + n, i)
same = lambda a, b: a == b
Z = {"react": (0, 0), "apm": 999, "mistake": 0, "focus": 5, "retreat": 0.5, "flank": 0}
BA.PROFILES[9] = Z
def U(i, side, p, role="line", rng=300, dmg=100, ai=False, hp=1000, capt=False, squad=1):
    return BA.U(i, side, p, hp, hp, False, 0 if role == "support" else dmg, 0, rng, 0, 1.5, 10, role, squad=squad, ai=ai,
                home=p, gate=(100, 100), capt=capt)
# support never attacks, stays behind the fighters
us = {1: U(1, 1, (1000, 1000), ai=True), 2: U(2, 1, (1000, 1050), ai=True), 3: U(3, 1, (980, 1000), "support", ai=True),
      10: U(10, 2, (1250, 1000))}
o = BA.Brain(tier=9).decide(us, {}, same, 0.0, controlled={1})
chk("support gets no attack order", not any(x[0] == "attack" and x[1] == 3 for x in o), o)
mv = [x for x in o if x[1] == 3 and x[0] == "move"]
chk("support moves behind its squad (away from the enemy)", mv and mv[0][2][0] < 1000, mv)
chk("fighters attack the enemy in range", sum(1 for x in o if x[0] == "attack" and x[2] == 10) == 2, o)
# artillery: enemy too close -> fall back to stand-off
us = {1: U(1, 1, (1000, 1000), "artillery", rng=650, ai=True), 10: U(10, 2, (1150, 1000))}
o = BA.Brain(tier=9).decide(us, {}, same, 0.0, controlled={1})
chk("artillery kites away from a close enemy", o and o[0][0] == "move" and o[0][2][0] < 1000, o)
us = {1: U(1, 1, (1000, 1000), "artillery", rng=650, ai=True), 10: U(10, 2, (1600, 1000))}
o = BA.Brain(tier=9).decide(us, {}, same, 0.0, controlled={1})
chk("artillery bombards from range", o and o[0][0] == "attack", o)
# order gate: the same intent is not sent twice
br = BA.Brain(tier=9)
us = {1: U(1, 1, (1000, 1000), ai=True), 10: U(10, 2, (1200, 1000))}
a = br.decide(us, {}, same, 0.0, controlled={1}); b = br.decide(us, {}, same, 1.0, controlled={1})
chk("same intent not re-sent", a and not b, (a, b))
# capturer takes a free POC while the others fight
us = {1: U(1, 1, (1000, 1000), ai=True), 2: U(2, 1, (1000, 1040), ai=True, capt=True), 3: U(3, 1, (1040, 1000), ai=True),
      10: U(10, 2, (1250, 1000))}
P = {7: {"x": 1000, "y": 1800, "owner": 0}}
o = BA.Brain(tier=9).decide(us, P, same, 0.0, controlled={1})
chk("capturer goes to the POC", any(x[1] == 2 and x[0] == "move" and x[2] == (1000, 1800) for x in o), o)
# outnumbered squad falls back
us = {1: U(1, 1, (1000, 1000), ai=True, hp=300)}
for k in range(6):
    us[10 + k] = U(10 + k, 2, (1300, 900 + 40 * k), hp=2000, dmg=200)
o = BA.Brain(tier=9).decide(us, {}, same, 0.0, controlled={1})
chk("hopeless squad falls back", o and o[0][0] == "move", o)
# reaction time: novice brain does not answer every new intent at once
br = BA.Brain(tier=1, seed=3); n_now = 0
for k in range(40):
    us = {1: U(1, 1, (1000, 1000), ai=True), 10 + k: U(10 + k, 2, (1000 + 200, 1000))}
    br.last.clear(); br.intent.clear(); br.last[1] = (("move", (0, 0)), -9)
    n_now += bool(br.decide(us, {}, same, 100.0 + k, controlled={1}))
chk("novice reacts late on most new intents", n_now < 30, n_now)
# aliens: wounded / territorial
us = {1: U(1, 0, (1000, 1000), ai=True, hp=1000), 10: U(10, 2, (1100, 1000))}
br = BA.Brain(tier=9, alien=True); us[1].hp = 100
o = br.decide(us, {}, lambda a, b: a == b, 0.0, controlled={0})
chk("wounded alien flees home", o and o[0][0] == "move", o)

# ---- 2026-10-24 flexibility ----
def V(i, side, p, rng=300, dmg=100, ai=False, hp=1000, air=False, role="line", spd=10, adm=0):
    return BA.U(i, side, p, hp, hp, air, 0 if role == "support" else dmg, adm, rng, 0, 1.5, spd, role, squad=1, ai=ai,
                home=p, gate=(100, 100))
# self-propelled gun: never runs from aircraft it cannot hit, takes position at range from a ground enemy
us = {1: V(1, 1, (1000, 1000), rng=650, role="artillery", ai=True), 2: V(2, 1, (950, 1000), ai=True),
      10: V(10, 2, (1100, 1000), air=True), 11: V(11, 2, (1900, 1000))}
o = BA.Brain(tier=9).decide(us, {}, same, 0.0, controlled={1})
m = [x for x in o if x[1] == 1]
chk("artillery ignores aircraft, moves to firing range of the ground enemy", m and m[0][0] == "move" and 1250 < m[0][2][0] < 1400, o)
# only aircraft around: the gun stays with its army (no wandering)
us = {1: V(1, 1, (1000, 1000), rng=650, role="artillery", ai=True), 2: V(2, 1, (950, 1000), ai=True),
      10: V(10, 2, (1100, 1000), air=True)}
o = BA.Brain(tier=9).decide(us, {7: {"x": 3500, "y": 3500, "owner": 2}}, same, 0.0, controlled={1})
m = [x for x in o if x[1] == 1]
chk("artillery with nothing to hit escorts the army", m and m[0][0] == "move" and abs(m[0][2][0] - 950) < 400 and abs(m[0][2][1] - 1000) < 400, o)
# something in range is shot before a 'better' target that must be walked to
us = {1: V(1, 1, (1000, 1000), rng=300, ai=True, hp=9000, dmg=400), 10: V(10, 2, (1250, 1000), hp=3000, dmg=10),
      11: V(11, 2, (1600, 1000), hp=200, dmg=300)}
o = BA.Brain(tier=9).decide(us, {}, same, 0.0, controlled={1})
chk("in-range target before walking", o and o[0] == ("attack", 1, 10), o)
# no overkill: a nearly dead target gets one shooter, the rest take the next one
us = {1: V(1, 1, (1000, 1000), ai=True), 2: V(2, 1, (1000, 1040), ai=True), 3: V(3, 1, (1000, 960), ai=True),
      10: V(10, 2, (1200, 1000), hp=80), 11: V(11, 2, (1200, 1080), hp=900)}
o = BA.Brain(tier=9).decide(us, {}, same, 0.0, controlled={1})
chk("no overkill on a nearly dead target", sum(1 for x in o if x[0] == "attack" and x[2] == 10) == 1
    and sum(1 for x in o if x[0] == "attack" and x[2] == 11) == 2, o)
# kite: a ranged unit steps back from a melee unit it outranges
BA.PROFILES[9]["kite"] = True
us = {1: V(1, 1, (1000, 1000), rng=350, ai=True, hp=9000, dmg=400), 10: V(10, 2, (1100, 1000), rng=90, dmg=300)}
o = BA.Brain(tier=9).decide(us, {}, same, 0.0, controlled={1})
chk("ranged unit kites a melee unit", o and o[0][0] == "move" and 600 < o[0][2][0] < 1000 and o[0][2][1] == 1000, o)
BA.PROFILES[9]["kite"] = False
print("ALL OK" if ok else "SOME FAILED")
# ---- support skills (2026-10-23 14:51)
def S(i, p, skills, hp=1000):
    u = U(i, 1, p, "support", ai=True, hp=hp); u.skills = frozenset(skills); return u
us = {1: U(1, 1, (1000, 1000), ai=True), 2: U(2, 1, (1050, 1000), ai=True), 3: S(3, (1020, 1040), ["heal"]),
      10: U(10, 2, (1300, 1000))}
us[1].bio = True; us[1].hp = 300
o = BA.Brain(tier=9).decide(us, {}, same, 0.0, controlled={1})
chk("healer heals the wounded bio unit", any(x[0] == "skill" and x[1] == 3 and x[2][:2] == (6, 1) for x in o), o)
us[1].bio = False; us[3].skills = frozenset(["heal"])
o = BA.Brain(tier=9).decide(us, {}, same, 0.0, controlled={1})
chk("healer does not heal a machine", not any(x[0] == "skill" and x[1] == 3 for x in o), o)
us[3].skills = frozenset(["repair"])
o = BA.Brain(tier=9).decide(us, {}, same, 0.0, controlled={1})
chk("repairer repairs the machine", any(x[0] == "skill" and x[2][:2] == (10, 1) for x in o), o)
us[1].pos = (1600, 1600)
o = BA.Brain(tier=9).decide(us, {}, same, 0.0, controlled={1})
chk("repairer walks to a far patient first", any(x[0] == "move" and x[1] == 3 for x in o), o)
# shield: friends inside, enemies close, things going badly
us = {1: U(1, 1, (1000, 1000), ai=True), 2: U(2, 1, (1040, 1000), ai=True), 3: S(3, (1020, 1020), ["shield"]),
      10: U(10, 2, (1300, 1000))}
us[1].hp = 400
br = BA.Brain(tier=9)
o = br.decide(us, {}, same, 0.0, controlled={1})
chk("shield raised over wounded friends under fire", any(x[0] == "skill" and x[2] == (40, 1) for x in o), o)
del us[10]
o2 = br.decide(us, {}, same, 1.0, controlled={1}); o3 = br.decide(us, {}, same, 9.0, controlled={1})
chk("shield lowered when the enemy is gone", any(x[0] == "skill" and x[2] == (40, 0) for x in o3), (o2, o3))
# teleport: badly wounded friend under fire -> pulled out
us = {1: U(1, 1, (1000, 1000), ai=True), 2: U(2, 1, (900, 900), ai=True), 3: S(3, (800, 800), ["teleport"]),
      10: U(10, 2, (1200, 1000))}
us[1].hp = 200
o = BA.Brain(tier=9).decide(us, {}, same, 0.0, controlled={1})
chk("teleport pulls the wounded unit out", any(x[0] == "skill" and x[2][0] == 5 and x[2][1] == 1 for x in o), o)

# ---- 2026-10-24 flexibility ----
def V(i, side, p, rng=300, dmg=100, ai=False, hp=1000, air=False, role="line", spd=10, adm=0):
    return BA.U(i, side, p, hp, hp, air, 0 if role == "support" else dmg, adm, rng, 0, 1.5, spd, role, squad=1, ai=ai,
                home=p, gate=(100, 100))
# self-propelled gun: never runs from aircraft it cannot hit, takes position at range from a ground enemy
us = {1: V(1, 1, (1000, 1000), rng=650, role="artillery", ai=True), 2: V(2, 1, (950, 1000), ai=True),
      10: V(10, 2, (1100, 1000), air=True), 11: V(11, 2, (1900, 1000))}
o = BA.Brain(tier=9).decide(us, {}, same, 0.0, controlled={1})
m = [x for x in o if x[1] == 1]
chk("artillery ignores aircraft, moves to firing range of the ground enemy", m and m[0][0] == "move" and 1250 < m[0][2][0] < 1400, o)
# only aircraft around: the gun stays with its army (no wandering)
us = {1: V(1, 1, (1000, 1000), rng=650, role="artillery", ai=True), 2: V(2, 1, (950, 1000), ai=True),
      10: V(10, 2, (1100, 1000), air=True)}
o = BA.Brain(tier=9).decide(us, {7: {"x": 3500, "y": 3500, "owner": 2}}, same, 0.0, controlled={1})
m = [x for x in o if x[1] == 1]
chk("artillery with nothing to hit escorts the army", m and m[0][0] == "move" and abs(m[0][2][0] - 950) < 400 and abs(m[0][2][1] - 1000) < 400, o)
# something in range is shot before a 'better' target that must be walked to
us = {1: V(1, 1, (1000, 1000), rng=300, ai=True, hp=9000, dmg=400), 10: V(10, 2, (1250, 1000), hp=3000, dmg=10),
      11: V(11, 2, (1600, 1000), hp=200, dmg=300)}
o = BA.Brain(tier=9).decide(us, {}, same, 0.0, controlled={1})
chk("in-range target before walking", o and o[0] == ("attack", 1, 10), o)
# no overkill: a nearly dead target gets one shooter, the rest take the next one
us = {1: V(1, 1, (1000, 1000), ai=True), 2: V(2, 1, (1000, 1040), ai=True), 3: V(3, 1, (1000, 960), ai=True),
      10: V(10, 2, (1200, 1000), hp=80), 11: V(11, 2, (1200, 1080), hp=900)}
o = BA.Brain(tier=9).decide(us, {}, same, 0.0, controlled={1})
chk("no overkill on a nearly dead target", sum(1 for x in o if x[0] == "attack" and x[2] == 10) == 1
    and sum(1 for x in o if x[0] == "attack" and x[2] == 11) == 2, o)
# kite: a ranged unit steps back from a melee unit it outranges
BA.PROFILES[9]["kite"] = True
us = {1: V(1, 1, (1000, 1000), rng=350, ai=True, hp=9000, dmg=400), 10: V(10, 2, (1100, 1000), rng=90, dmg=300)}
o = BA.Brain(tier=9).decide(us, {}, same, 0.0, controlled={1})
chk("ranged unit kites a melee unit", o and o[0][0] == "move" and 600 < o[0][2][0] < 1000 and o[0][2][1] == 1000, o)
BA.PROFILES[9]["kite"] = False
# (user 2026-10-24 06:57) a helper NPC counts the player's army: it does not regroup / run when the side as a whole is strong
us = {1: U(1, 1, (1000, 1000), ai=True, squad="n"), 2: U(2, 1, (1000, 1040), ai=True, squad="n")}
for k in range(10):
    us[100 + k] = U(100 + k, 1, (1100 + 20 * k, 1000))                        # the player's units (side 1, not AI)
for k in range(6):
    us[200 + k] = U(200 + k, 2, (1700 + 20 * k, 1000), ai=True, squad="e")    # the enemy
br = BA.Brain(tier=9)
br.decide(us, {}, same, 0.0, controlled={1})
pl = br.plans.get(1) or {}
chk("helper NPC with a player's army: no regroup", pl.get("kind") != "regroup" and pl.get("ratio", 0) >= 1.0, pl)
for k in range(10):
    us.pop(100 + k)
br2 = BA.Brain(tier=9)
br2.decide(us, {}, same, 0.0, controlled={1})
chk("the same NPC alone against them: regroups", (br2.plans.get(1) or {}).get("kind") == "regroup", br2.plans.get(1))
for k in range(3):
    us[100 + k] = U(100 + k, 1, (400 + 20 * k, 1600))                          # a weak player army far away
br3 = BA.Brain(tier=9)
br3.decide(us, {}, same, 0.0, controlled={1})
p3 = br3.plans.get(1) or {}
chk("regrouping with allies on the map: towards the allies, not the gate",
    p3.get("kind") != "regroup" or (abs(p3["point"][0] - 420) < 60 and abs(p3["point"][1] - 1600) < 60), p3)

# (user 2026-10-24 07:06) weaker side: a squad strung out from its gate closes up first, then goes in together
def column(n, x0=100):
    return {i: U(i, 1, (x0 + 120 * i, 100), ai=True, squad="g") for i in range(1, n + 1)}
us = column(6)
for k in range(10):
    us[300 + k] = U(300 + k, 2, (2600 + 20 * k, 2600), ai=True, squad="e")
br = BA.Brain(tier=9)
o = br.decide(us, {}, same, 0.0, controlled={1})
g = [x for x in o if x[1] < 100]
lead = [x for x in g if x[1] == 6]
chk("weaker, strung out: the squad gathers (head waits, tail closes up)", g and all(x[0] == "move" for x in g)
    and lead and lead[0][2][0] < us[6].pos[0], g)
rp = br._rally([us[i] for i in us if i < 100])
chk("rally point is not on the gate (exit portal)", BA.dist(rp, (100, 100)) >= BA.GATE_CLEAR - 1, rp)
for i in us:
    if i < 100: us[i].pos = (rp[0] + 10 * i, rp[1] + 10)
o2 = br.decide(us, {}, same, 10.0, controlled={1})
mv = [x for x in o2 if x[1] < 100 and x[0] == "move"]
chk("... gathered: it advances together", mv and all(x[2][0] > rp[0] + 60 for x in mv), mv)
us2 = column(6)
for k in range(2):
    us2[300 + k] = U(300 + k, 2, (2600 + 20 * k, 2600), ai=True, squad="e")
o3 = BA.Brain(tier=9).decide(us2, {}, same, 0.0, controlled={1})
chk("stronger side does not wait to gather", any(x[1] == 6 and x[0] == "move" and x[2][0] > us2[6].pos[0] for x in o3), o3)
br4 = BA.Brain(tier=9)
us = column(6)
for k in range(10):
    us[300 + k] = U(300 + k, 2, (2600 + 20 * k, 2600), ai=True, squad="e")
br4.decide(us, {}, same, 0.0, controlled={1})
o4 = br4.decide(us, {}, same, BA.GATHER_MAX + 1, controlled={1})
chk("gathering never takes longer than GATHER_MAX", any(x[1] == 6 and x[2][0] > us[6].pos[0] for x in o4 if x[0] == "move"), o4)

print("ALL OK" if ok else "SOME FAILED")
