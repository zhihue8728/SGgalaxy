"""patch_npc_aggr (user 2026-10-23 09:11: "few NPCs attack, be more aggressive, NPCs should cooperate"): shorter thinking
time, fewer 'stay home' rolls, shorter pauses between conquests, up to 3 campaigns, more hunts, RALLY (an NPC that picks a
target takes 1-4 idle comrades along, their combined power counts), higher follow chances, allied nations help defend.
usage: patch_npc_aggr.py server/sgserver.py server/npc.py   (idempotent)"""
import sys, re
PS, PN = (sys.argv[1] if len(sys.argv) > 1 else "server/sgserver.py"), (sys.argv[2] if len(sys.argv) > 2 else "server/npc.py")
def patch(path, edits):
    src = open(path, encoding="utf-8").read()
    for old, new in edits:
        if new in src:
            continue
        assert src.count(old) == 1, (path, src.count(old), old[:80])
        src = src.replace(old, new)
    open(path, "w", encoding="utf-8").write(src)

patch(PN, [
 ("THINK = (60, 480) ", "THINK = (30, 180) "),
 ("SORTIE_EVERY = (900, 2700)", "SORTIE_EVERY = (420, 1200)"),
 ("SORTIE_SIZE = (3, 8)", "SORTIE_SIZE = (4, 10)"),
 ("MARCH_STEP = (40, 120)", "MARCH_STEP = (30, 90)"),
 ("PROTECT_SECONDS = (1800, 3600)", "PROTECT_SECONDS = (900, 1800)"),
 ('''    "lone":     {"w": 3.0, "stay": 0.25, "enemy": 0,  "min_win": 0.35, "follow": 0.0, "think": 1.0},
    "follower": {"w": 2.0, "stay": 0.30, "enemy": 0,  "min_win": 0.45, "follow": 0.5, "think": 1.0},
    "warlike":  {"w": 2.0, "stay": 0.15, "enemy": 18, "min_win": 0.25, "follow": 0.1, "think": 0.8},
    "cautious": {"w": 2.0, "stay": 0.35, "enemy": -5, "min_win": 0.62, "follow": 0.2, "think": 1.2},
    "guard":    {"w": 1.5, "stay": 0.70, "enemy": 0,  "min_win": 0.55, "follow": 0.0, "think": 1.1},''',
  '''    "lone":     {"w": 3.0, "stay": 0.10, "enemy": 4,  "min_win": 0.30, "follow": 0.30, "think": 1.0},
    "follower": {"w": 2.0, "stay": 0.12, "enemy": 4,  "min_win": 0.40, "follow": 0.80, "think": 1.0},
    "warlike":  {"w": 2.0, "stay": 0.05, "enemy": 20, "min_win": 0.20, "follow": 0.45, "think": 0.7},
    "cautious": {"w": 2.0, "stay": 0.20, "enemy": 0,  "min_win": 0.55, "follow": 0.50, "think": 1.1},
    "guard":    {"w": 1.5, "stay": 0.35, "enemy": 0,  "min_win": 0.50, "follow": 0.30, "think": 1.0},'''),
])

patch(PS, [
 ("NPC_GAIN_GAP = (600, 1500)\nNPC_GAP_GROWTH = 3.0", "NPC_GAIN_GAP = (300, 900)\nNPC_GAP_GROWTH = 2.0"),
 ("NPC_MAX_SHARE = 1.5\n", "NPC_MAX_SHARE = 2.0\n"),
 ("    return len(targets) < (2 if npc_owned(nid) < npc_fair(nid) / 2 else 1)",
  "    return len(targets) < (3 if npc_owned(nid) < npc_fair(nid) * 0.75 else 2)"),
 ("NPC_HUNT_CHANCE = 0.5 ", "NPC_HUNT_CHANCE = 0.8 "),
 ("NPC_HUNT_MAX = 3 ", "NPC_HUNT_MAX = 5 "),
 ('''    cands = npc_targets(nid, now) if npc_may_attack(nid, now) else []
    c = NP.choose(cands, n, NP.power_of(n)) if cands else None
''', '''    cands = npc_targets(nid, now) if npc_may_attack(nid, now) else []
    team = [n]
    if cands and random.random() < NPC_RALLY_CHANCE:         # RALLY: take idle comrades along, their power adds up
        free = [m for m in npc_of(nid) if m is not n and m["state"] == "active" and not m["task"] and now >= m["rest_until"]
                and not m.get("retire") and NP.readiness(m) >= NP.MIN_READY]
        if free:
            team += random.sample(free, min(len(free), random.randint(*NPC_RALLY_SIZE)))
    c = NP.choose(cands, n, sum(NP.power_of(m) for m in team)) if cands else None
'''),
 ('''    if c:
        npc_send([n], c, now)
    else:
        log(f"   NPC: {n['name']} ({n['persona']}) stays home")''', '''    if c:
        npc_send(team, c, now, group=len(team) > 1)
        if len(team) > 1:
            log(f"   NPC: {n['name']} rallies {len(team) - 1} comrade(s) for {c['pid']}")
    else:
        log(f"   NPC: {n['name']} ({n['persona']}) stays home")'''),
 ("def npc_think(n, now):", "NPC_RALLY_CHANCE = 0.6          # an NPC that looks for a target takes idle comrades along with this chance\nNPC_RALLY_SIZE = (1, 4)\nNPC_ALLY_HELP = 0.5            # share of NPC_REACT_CHANCE with which idle NPCs of ALLIED nations (same planet) help a defence\n\ndef npc_think(n, now):"),
 ('''        idle = _npc_idle_of(owner, now)
        if not idle:
            continue
        n = random.choice(idle)
        n["task"] = npc_reinf_task("support", owner, pid, now)''', '''        idle = _npc_idle_of(owner, now)
        if not idle and random.random() < NPC_ALLY_HELP:      # allied nations on the same planet come to help
            idle = [m for (a_, b_) in NATION_ALLIES for m in _npc_idle_of(b_ if a_ == owner else a_, now)
                    if owner in (a_, b_) and nation_planet(m["nation"]) == pid // 100000]
        if not idle:
            continue
        n = random.choice(idle)
        n["task"] = npc_reinf_task("support", n["nation"], pid, now)'''),
])
print("patched")
patch(PS, [
 ("NPC_HUNT_MAX = 5 ", "NPC_HUNT_MAX = 6 "),
 ("    if p[\"follow\"] and random.random() < p[\"follow\"]:\n        mates = [m for m in npc_of(nid) if m is not n and m[\"state\"] == \"active\" and m[\"task\"]\n                 and m[\"task\"].get(\"kind\") == \"attack\" and m[\"task\"].get(\"phase\") == \"march\" and m[\"task\"][\"arrive\"] > now + 30]",
  "    fchance = p[\"follow\"] if npc_may_attack(nid, now) else max(p[\"follow\"], NPC_JOIN_CHANCE)   # campaigns capped: help a comrade instead\n    if fchance and random.random() < fchance:\n        mates = [m for m in npc_of(nid) if m is not n and m[\"state\"] == \"active\" and m[\"task\"]\n                 and m[\"task\"].get(\"kind\") == \"attack\" and m[\"task\"].get(\"phase\") == \"march\" and m[\"task\"][\"arrive\"] > now + 8]"),
 ("NPC_RALLY_SIZE = (1, 4)\n", "NPC_RALLY_SIZE = (1, 4)\nNPC_JOIN_CHANCE = 0.7           # idle NPC of a nation whose campaigns are capped joins a marching comrade with this chance\n"),
])
print("patched 2")

