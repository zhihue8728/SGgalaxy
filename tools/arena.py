#!/usr/bin/env python3
"""ARENA (claude/NPC_BATTLE_AI_ARCH.md): offline battles to tune server/battle_ai.py.
Two mirrored armies on an open 4096 px field with 3 POCs; simple physics (move at speed, shoot in range with the weapon
cooldown, damage = weapon damage).  Side A = battle_ai.Brain, side B = the OLD greedy rule (attack the nearest enemy in
aggro range, else walk to the nearest enemy POC / enemy).  Prints win rate, survivors, POCs.
usage: arena.py [N battles] [tier] [persona]"""
import sys, os, random, math
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "server"))
import battle_ai as BA

ARMY = [  # name, hp, gdmg, grng, gcd(s), spd(px/s/2), role
    ("Behemoth", 2600, 324, 368, 3.0, 9, "line"), ("Behemoth", 2600, 324, 368, 3.0, 9, "line"),
    ("Shade", 1500, 216, 304, 2.2, 11, "line"), ("Shade", 1500, 216, 304, 2.2, 11, "line"),
    ("Imp", 1100, 99, 214, 1.4, 12, "line"), ("Imp", 1100, 99, 214, 1.4, 12, "line"),
    ("Ghast", 1700, 259, 90, 1.3, 13, "melee"), ("Pegasus", 1200, 228, 398, 2.8, 18, "line"),
    ("Arbalest", 1300, 148, 620, 1.5, 8, "artillery"), ("Trebuchet", 1200, 110, 706, 2.0, 8, "artillery"),
    ("Orbus", 1400, 60, 248, 1.5, 10, "support"), ("Imp", 1100, 99, 214, 1.4, 12, "line"),
]
AGGRO = 384


def make(side, x0, y0, ai):
    us = {}
    for k, (nm, hp, d, r, cd, spd, role) in enumerate(ARMY):
        uid = side * 1000 + k
        p = (x0 + (k % 4) * 40, y0 + (k // 4) * 40)
        us[uid] = BA.U(uid, side, p, hp, hp, False, d if role != "support" else 0, 0, r, 0, cd, spd, role, squad=side * 10 + k // 6,
                       ai=ai, home=p, mode="assault", gate=p, capt=(k == 7 or k == 4), name=nm)
    return us


def greedy_orders(units, pocs, side):
    out = []
    mine = [u for u in units.values() if u.side == side and u.hp > 0]
    en = [u for u in units.values() if u.side != side and u.hp > 0]
    for u in mine:
        if u.role == "support":
            continue
        close = [e for e in en if BA.dist(e.pos, u.pos) <= max(AGGRO, u.rng_g)]
        if close:
            out.append(("attack", u.id, min(close, key=lambda e: BA.dist(e.pos, u.pos)).id))
        else:
            ep = [p for p in pocs.values() if p["owner"] != side]
            if ep:
                p = min(ep, key=lambda p: BA.dist((p["x"], p["y"]), u.pos))
                out.append(("move", u.id, (p["x"], p["y"])))
            elif en:
                out.append(("move", u.id, min(en, key=lambda e: BA.dist(e.pos, u.pos)).pos))
    return out


def battle(seed, tier, persona, swap=False):
    rnd = random.Random(seed)
    A, B = (1, 2)
    units = {}
    units.update(make(A, 400, 400 + rnd.randint(-100, 100), True))
    for uid, u in make(B, 400, 400 + rnd.randint(-100, 100), False).items():     # exact mirror of A
        u.pos = (4096 - u.pos[0], 4096 - u.pos[1]); u.home = u.gate = u.pos
        units[uid] = u
    pocs = {1: {"x": 2048, "y": 2048, "owner": 0}, 2: {"x": 1200, "y": 2900, "owner": 0}, 3: {"x": 2900, "y": 1200, "owner": 0}}
    cap = {i: [0, 0] for i in pocs}
    brain = BA.Brain(tier=tier, seed=seed, persona=persona)
    cmd = {}                                   # uid -> ("move", (x,y)) | ("attack", tid)
    cdl = {u: 0.0 for u in units}
    t, dt = 0.0, 0.25
    same = lambda a, b: a == b
    while t < 900:
        if int(t / 1.0) != int((t - dt) / 1.0):     # both AIs think once a second
            for o in brain.decide(units, pocs, same, t, controlled={A}):
                cmd[o[1]] = (o[0], o[2])
            for o in greedy_orders(units, pocs, B):
                cmd[o[1]] = (o[0], o[2])
        for u in units.values():
            if u.hp <= 0:
                continue
            c = cmd.get(u.id)
            spd = u.spd * 2.0 * dt * 4                # (game speed x4 to keep runs short)
            cdl[u.id] -= dt * 4
            if c and c[0] == "attack":
                e = units.get(c[1])
                if e is None or e.hp <= 0:
                    cmd.pop(u.id, None); continue
                d = BA.dist(u.pos, e.pos)
                if d <= u.rng_g:
                    if cdl[u.id] <= 0:
                        e.hp -= u.dmg_g; cdl[u.id] = u.cd
                else:
                    u.pos = BA.toward(u.pos, e.pos, min(spd, d - u.rng_g * 0.9))
            else:
                if c and c[0] == "move":
                    d = BA.dist(u.pos, c[1])
                    if d > 4:
                        u.pos = BA.toward(u.pos, c[1], min(spd, d))
                # idle units shoot back at anything in range (the client does that by itself)
                if u.dmg_g > 0:
                    en = [e for e in units.values() if e.side != u.side and e.hp > 0 and BA.dist(e.pos, u.pos) <= u.rng_g]
                    if en and cdl[u.id] <= 0:
                        e = min(en, key=lambda e: e.hp); e.hp -= u.dmg_g; cdl[u.id] = u.cd
        # POC capture: 6 s standing alone on it
        for i, p in pocs.items():
            on = {u.side for u in units.values() if u.hp > 0 and BA.dist(u.pos, (p["x"], p["y"])) < 60}
            if len(on) == 1:
                s = next(iter(on))
                if p["owner"] != s:
                    cap[i][s - 1] += dt * 4
                    if cap[i][s - 1] >= 6:
                        p["owner"] = s; cap[i] = [0, 0]
        aliveA = sum(1 for u in units.values() if u.side == A and u.hp > 0)
        aliveB = sum(1 for u in units.values() if u.side == B and u.hp > 0)
        if aliveA == 0 or aliveB == 0 or all(p["owner"] == A for p in pocs.values()) or all(p["owner"] == B for p in pocs.values()):
            break
        t += dt
    pa = sum(p["owner"] == A for p in pocs.values()); pb = sum(p["owner"] == B for p in pocs.values())
    win = "A" if (aliveB == 0 or pa == 3 or (aliveA > aliveB and pa >= pb)) else ("B" if (aliveA == 0 or pb == 3 or aliveB > aliveA) else "draw")
    return win, aliveA, aliveB, pa, pb, t, brain.log


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    tier = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    persona = sys.argv[3] if len(sys.argv) > 3 else "lone"
    res = [battle(s, tier, persona) for s in range(n)]
    w = {k: sum(1 for r in res if r[0] == k) for k in ("A", "B", "draw")}
    print(f"tier {tier} {persona}: brain(A) vs greedy(B) over {n}: {w}  survivors A {sum(r[1] for r in res)/n:.1f} "
          f"B {sum(r[2] for r in res)/n:.1f}  POCs A {sum(r[3] for r in res)/n:.1f} B {sum(r[4] for r in res)/n:.1f}  "
          f"avg time {sum(r[5] for r in res)/n:.0f}s")
    print("plans (first battle):", res[0][6][:12])
