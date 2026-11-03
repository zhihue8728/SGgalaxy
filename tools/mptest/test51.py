"""test51 (user 2026-10-24 19:45): the NPC battle brain uses its units' functions (battle_ai._tactics):
grenade at a group, virus on the strongest, artillery turns then deploys bombArd / Flak and stops moving, Volte energy
production + refuel, Sapper mines at its POC, booster on a long walk.  Lump formats: npc_battle skill encoding."""
import sys, os
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import battle_ai as BAI
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
U = BAI.U
same = lambda a, b: a == b
def run(units, pocs=None, ticks=4):
    br = BAI.Brain(tier=2, seed=1)
    br.p["react"] = (0.0, 0.0); br.p["apm"] = 999
    allo = []
    for k in range(ticks):
        allo += br.decide({u.id: u for u in units}, pocs or {}, same, 100.0 + k * 1.5, controlled={1})
    return allo
sk = lambda os_, act: [o for o in os_ if o[0] == "skill" and o[2][0] == act]
# grenade: 3 enemies packed together near a Daeva
d = U(1, 1, (1000, 1000), 500, dmg_g=40, rng_g=180, ai=True, squad="a", skills=["grenade"], role="line")
es = [U(100 + i, 2, (1150 + i * 30, 1000), 500, dmg_g=30, rng_g=150) for i in range(3)]
o = run([d] + es)
chk("Daeva throws a grenade at the packed enemies", sk(o, 21) and sk(o, 21)[0][2][1] in (100, 101, 102), sk(o, 21))
# artillery bombArd: turns (move) then deploys, then no more move orders
a = U(2, 1, (1000, 1000), 600, dmg_g=60, rng_g=700, ai=True, squad="b", skills=["bombard"], role="artillery")
e = U(200, 2, (1500, 1000), 800, dmg_g=30, rng_g=150)
o = run([a, e], ticks=6)
seq = [x[0] if x[0] != "skill" else ("skill", x[2]) for x in o if x[1] == 2]
dep = sk(o, 9)
chk("artillery turns toward the enemy, then deploys bombArd [u8 1] and stops moving",
    dep and dep[0][2][1] == 1 and not any(x[0] == "move" and x[3] != "face for bombard" for x in o[o.index(dep[0]):] if x[1] == 2), seq)
# flak vs air
b = U(3, 1, (1000, 1000), 600, dmg_a=50, rng_a=1000, rng_g=1000, ai=True, squad="c", skills=["flak"], role="antiair")
ea = U(300, 2, (1500, 1000), 500, air=True, dmg_g=30, rng_g=200)
o = run([b, ea], ticks=6)
chk("Ballista deploys Flak Attack against aircraft", sk(o, 34) and sk(o, 34)[0][2][1] == 1, sk(o, 34))
# Volte energy production + refuel
v = U(4, 1, (1000, 1000), 600, ai=True, squad="d", skills=["energy", "refuel"], role="support")
fr = [U(40 + i, 1, (1050 + i * 40, 1020), 600, dmg_g=30, rng_g=150, ai=True, squad="d") for i in range(3)]
e2 = U(400, 2, (1700, 1000), 600, dmg_g=30, rng_g=150)
o = run([v] + fr + [e2], ticks=8)
chk("Volte goes into energy production and refuels its friends", sk(o, 55) and sk(o, 12), (sk(o, 55), sk(o, 12)))
# virus
vi = U(5, 1, (1000, 1000), 600, dmg_g=40, rng_g=150, ai=True, squad="e", skills=["virus"], role="line")
o = run([vi, U(500, 2, (1200, 1000), 900, dmg_g=80, rng_g=150)])
chk("Virus infects the enemy (Virus attack 59)", sk(o, 59), sk(o, 59))
# sapper mine at an own POC, no enemy close
sp = U(6, 1, (1000, 1000), 600, dmg_g=20, rng_g=120, ai=True, squad="f", skills=["mine"], role="line", mode="hold")
o = run([sp, U(600, 2, (3000, 3000), 600, dmg_g=20, rng_g=120)], pocs={1: {"x": 1010, "y": 1000, "owner": 1}})
chk("Sapper lays a mine where it holds", sk(o, 8), sk(o, 8))
# booster on a long walk
bo = U(7, 1, (300, 300), 600, dmg_g=30, rng_g=150, ai=True, squad="g", skills=["booster"], role="line", spd=20)
o = run([bo, U(700, 2, (3500, 3500), 600, dmg_g=20, rng_g=120)])
chk("Booster on for a long walk", sk(o, 35) and sk(o, 35)[0][2][1] == 1, sk(o, 35))
# server encoding of the new actions (npc_battle)
src = open('/tmp/mp/sgs/npc_battle.py', encoding='utf-8').read()
chk("npc_battle encodes the new actions (u32 target / u8 toggle / mine)",
    "act in (6, 10, 21, 59, 60, 12)" in src and "act in (9, 34, 35, 55)" in src and "elif act == 8:" in src)
