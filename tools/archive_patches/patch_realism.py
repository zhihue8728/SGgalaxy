"""NPC commanders follow the PLAYER rules (user 2026-10-22 22:22: "NPC的兵科等級要能實裝, 新手星沒轉生的NPC不會有12隻單位"):
every NPC has a believable commander - branch levels (novice planet <= 35), reincarnations (none on the novice planet),
attribute points = create points + 1 per branch level + 2 per reincarnation, spread by personality - and from it:
  * deploy limit = Tactics // 20 + 6 (max 12) units on the field at a time (also each F7-like squad),
  * unit kinds only up to the INFLUENCE of their branch (branch level + Clout // 2), like the Factory,
  * unit levels at most the branch level + 3.
The profile window / user info shows the same attributes and reincarnations."""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else "server/sgserver.py"
src = open(P, encoding="utf-8").read()
def rep(old, new, cnt=1):
    global src
    if new in src:
        return
    n = src.count(old)
    assert n == cnt, (n, old[:90])
    src = src.replace(old, new)

rep('''            pool.append({"code": name, "min": infl, "rank": float(infl), "spd": speed(name)})
    for adv, _code, base, uq, _zh in ADVANCED:
        if _TAB.get(base) in (0, 1) and adv not in NPC_NO_UNITS:
            pool.append({"code": adv, "min": uq, "rank": uq / 8.0, "spd": speed(adv)})''', '''            pool.append({"code": name, "min": infl, "rank": float(infl), "spd": speed(name),
                         "branch": "inf" if tab == 0 else "mob"})
    for adv, _code, base, uq, _zh in ADVANCED:
        if _TAB.get(base) in (0, 1) and adv not in NPC_NO_UNITS:
            pool.append({"code": adv, "min": uq, "rank": uq / 8.0, "spd": speed(adv),
                         "branch": "inf" if _TAB.get(base) == 0 else "mob"})''')

rep('''def npc_cmd(n):''', '''# ---- a commander like a player's (user 2026-10-22 22:22) ------------------------------------------------------------------
NPC_CREATE_POINTS = 40       # attribute points spread on the New-commander screen
NPC_ATTR_SPLIT = {           # Tactics, Clout, Education, Mech share of the points, by personality
    "warlike": (0.45, 0.25, 0.15, 0.15), "lone": (0.40, 0.30, 0.15, 0.15), "follower": (0.35, 0.30, 0.20, 0.15),
    "cautious": (0.30, 0.30, 0.25, 0.15), "guard": (0.35, 0.25, 0.20, 0.20)}

def npc_profile(n):
    """branch levels, reincarnations and attributes of an NPC commander (cached; drawn from its id, so it never jumps)."""
    key = [n["level"], n.get("persona")]
    pr = n.get("prof")
    if pr and pr.get("key") == key:
        return pr
    h = npc_history(n)
    tier = PLANET_TIER.get(nation_planet(n["nation"]), 1)
    r = random.Random(n["id"] * 104729 + n["level"])
    reinc = 0 if tier == 1 else (r.choice((0, 0, 1)) if tier == 2 else r.randint(0, 3))
    cap = PG.NOVICE_BRANCH_CAP if tier == 1 else PG.DIVISION_MAX_LEVEL + reinc
    br = [min(cap, max(1, int(x))) for x in [n["level"]] + list(h["lv"][1:])]
    pts = NPC_CREATE_POINTS + sum(x - 1 for x in br) + PG.REINC_POINTS * reinc
    w = NPC_ATTR_SPLIT.get(n.get("persona"), NPC_ATTR_SPLIT["lone"])
    attrs = [min(PG.ATTR_MAX, int(pts * f)) for f in w]
    pr = n["prof"] = {"key": key, "attrs": attrs, "reinc": reinc, "br": dict(zip(PG.BRANCHES, br))}
    return pr

def npc_deploy(n):
    """units of this NPC on the battle field at a time = the player rule Tactics // 20 + 6 (max 12)."""
    return PG.deploy_limit({"attrs": npc_profile(n)["attrs"]})

def npc_influence(n, branch):
    pr = npc_profile(n)
    return pr["br"].get(branch, 1) + pr["attrs"][1] // 2

def npc_realism(n):
    """only unit kinds its branches can field (influence) and unit levels <= branch level + 3.  True = changed."""
    pool = npc_pool()
    pr = npc_profile(n)
    allowed = [p for p in pool if p["min"] <= npc_influence(n, p.get("branch", "inf"))] \\
        or sorted(pool, key=lambda p: p["min"])[:3]
    codes = {p["code"] for p in allowed}
    changed = False
    doc = n.get("doctrine")
    if not doc or any(doc.get(k) not in codes for k in ("main", "second", "fast")):
        main = doc["main"] if doc and doc.get("main") in codes else None
        n["doctrine"] = doc = NP.pick_doctrine(allowed, 10 ** 6, random.Random(n["id"] * 31 + n["level"]), main)
        changed = True
    sq = n["squad"]
    if changed or any(c not in codes for c, _l in sq):
        levels = sorted((l for _c, l in sq), reverse=True)
        n["squad"] = [[c, l] for c, l in zip(NP.doctrine_kinds(doc, len(sq)), levels)]
        n["hl"] = None
        changed = True
    branch_of = {p["code"]: p.get("branch", "inf") for p in pool}
    for u in n["squad"]:
        cap = max(1, min(PG.UNIT_MAX_LEVEL, pr["br"].get(branch_of.get(u[0], "inf"), 1) + 3))
        if u[1] > cap:
            u[1] = cap
            changed = True
    return changed

def npc_cmd(n):''')
rep('''    br = {k: {"level": l, "xp": x} for k, l, x in zip(("inf", "mob", "avi", "org"), h["lv"], h["xp"])}
    br["inf"]["level"] = lv
    return {"nation": n["nation"], "look": n["look"], "attrs": [min(120, 20 + lv), min(120, lv), min(120, lv), min(120, lv // 2)],''',
'''    pr = npc_profile(n)
    br = {k: {"level": pr["br"][k], "xp": x} for k, x in zip(("inf", "mob", "avi", "org"), h["xp"])}
    return {"nation": n["nation"], "look": n["look"], "attrs": list(pr["attrs"]),''')
rep('''            "reincarnations": 0, "stats": {"kills": (h["wins"] + n.get("wins", 0)) * 4}, "npc": True}''',
    '''            "reincarnations": pr["reinc"], "stats": {"kills": (h["wins"] + n.get("wins", 0)) * 4}, "npc": True}''')
# the deploy limit applies to every squad an NPC puts on a map
rep('''    hl, sq = NP.health(npc), npc["squad"]
    nf = NP.fast_count(len(sq))''', '''    hl, sq = NP.health(npc), npc["squad"]
    k = min(k, npc_deploy(npc))                   # player rule: Tactics // 20 + 6 units at a time (user 2026-10-22 22:22)
    nf = NP.fast_count(len(sq))''')
# rosters / renewals follow the rules
rep('''    doc = sum(1 for n in mine if NP.ensure_doctrine(n, tier, npc_pool()))  # rosters made before the doctrines (main kind)''',
    '''    doc = sum(1 for n in mine if NP.ensure_doctrine(n, tier, npc_pool()))  # rosters made before the doctrines (main kind)
    real = sum(1 for n in mine if npc_realism(n))                          # unit kinds / levels a commander can field
    if real:
        npc_dirty()
        log(f"   NPC: {real} commanders of nation {nid} limited to the unit kinds / levels of their branches")''')
rep('''            NP.refresh(n, PLANET_TIER.get(nation_planet(n["nation"]), 1), npc_pool())''',
    '''            NP.refresh(n, PLANET_TIER.get(nation_planet(n["nation"]), 1), npc_pool())
            npc_realism(n)''')
open(P, "w", encoding="utf-8").write(src)
print("patched")
rep('''        n = NP.new_npc(nid, tier, uid, taken, npc_pool())
''', '''        n = NP.new_npc(nid, tier, uid, taken, npc_pool())
        st["npcs"][str(uid)] = n
        npc_realism(n)
''')
open(P, "w", encoding="utf-8").write(src)
