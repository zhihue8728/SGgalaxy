# sgserver part "npc_world": NPC nations: roster, decisions, tasks, ghost battles, chat, diplomacy, interception.
# Loaded by sgserver.py into ONE shared namespace (exec, in the order of PARTS) - not an importable module;
# every name here is a sgserver global.  Checks: python tools/check_server.py
# ---- NPC NATIONS (claude/NPC_NATIONS_PLAN.md; user decisions 2026-10-22 13:08 - 13:13) -------------------------------
# Every nation has a roster of NP.NPC_CAP computer commanders ("NPC"), stored in server/npcs.json.  They look like normal
# players (hall of fame, player search, user info, strategic map).  ACTIVE NPCs of a nation = 20 - players online.
# Each active NPC decides on its own random timer: stay, sortie alone, follow a comrade, or (random group event of the
# nation) sortie together.  Without a player in the province the battle is abstract (NP.resolve); with a player in it the
# NPC squads are put on the battle map as server-owned units (npc_spawn / npc_ai), which fight and capture POCs.
import npc as NP
import battlesim as BSIM

NPC_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "npcs.json")
NPC_TICK = 10.0
NPC_BATTLE_FACTOR = 1.2            # NPC units on a battle map = this x the human units fighting them ...
NPC_BATTLE_UNITS = (6, 36)         # ... but between these limits
NPC_DEFENDERS_MAX = 3              # NPC squads that defend one attacked province
NPC_NO_UNITS = {"Sapper", "Sapper-MK2", "Virus", "Medic", "Triage", "Triage-MK2", "Volte", "Mantlet", "Gear-Doc"}
# War Pigeon attacks only with Carpet Bomb (a skill the NPC AI does not use) -> no NPC War Pigeons (15:11)
NPC_NO_UNITS |= {"War Pigeon"} | {"War Pigeon-MK%d" % _k for _k in range(2, 10)}
NPC_STATE = None
NPC_DIRTY = False
NPC_SAVED_AT = 0.0
NPC_RT = {}                        # npc id -> {"B": battle, "dead": n, "units": n}   (runtime only)
NPC_RESULT = {}                    # province -> True / False: the NPC attackers won / lost the real battle
_NPC_POOL = {}
_NPC_UNITS = {}
_CAP_DIST = {}

class NpcSide:
    """stands in for a session in poc_loop: an NPC capturer standing on a POC."""
    is_npc = True
    def __init__(self, tg):
        self.acc = tg.get("put", {}).get("owner", "NPC")
        self.cmd = {"nation": tg["nation"]}
        self.side_nation = tg["nation"]

def npc_owned(nid):
    return sum(1 for v in world_state()["owners"].values() if int(v) == nid)

def npc_state():
    global NPC_STATE
    if NPC_STATE is None:
        try:
            NPC_STATE = STORE.kv_get(db(), "npcs") or {}
        except Exception:
            NPC_STATE = {}
        for k, v in (("next_id", 1), ("npcs", {}), ("refill", {}), ("sortie", {}), ("protect", {}), ("stand", {}),
                     ("stand_cool", {}), ("peak", {}), ("warm", {}), ("group", 1), ("gain", {}), ("alarm", {})):
            NPC_STATE.setdefault(k, v)
        for n in NPC_STATE["npcs"].values():          # tasks do not survive a restart
            n["task"] = None
            n["think_at"] = time.time() + random.uniform(*NPC_START_DELAY)     # no land grab right after a start
        # pauses / protections saved by an older version can be hours long: never longer than the current rules
        _now = time.time()
        for _k, _mx in (("gain", NPC_GAIN_GAP[1] * (1 + NPC_GAP_GROWTH * NPC_MAX_SHARE ** 2)),
                        ("protect", NP.PROTECT_SECONDS[1]), ("sortie", NP.SORTIE_EVERY[1])):
            for _nid, _until in list(NPC_STATE[_k].items()):
                if isinstance(_until, (int, float)) and _until > _now + _mx:
                    NPC_STATE[_k][_nid] = _now + random.uniform(0, _mx / 4)
    return NPC_STATE

def npc_dirty():
    global NPC_DIRTY
    NPC_DIRTY = True

def npc_save(force=False):
    global NPC_DIRTY, NPC_SAVED_AT
    if NPC_STATE is not None and NPC_DIRTY and (force or time.time() - NPC_SAVED_AT > 60):
        NPC_DIRTY = False
        NPC_SAVED_AT = time.time()
        if force:
            STORE.kv_put(db(), "npcs", NPC_STATE)
        else:
            import marshal
            snap = marshal.dumps(NPC_STATE)                 # fast copy; json + disk happen in a thread
            def work():
                STORE.kv_put(db(), "npcs", marshal.loads(snap))
            try:
                asyncio.get_event_loop().run_in_executor(None, work)
            except RuntimeError:
                work()

def npc_all():
    return list(npc_state()["npcs"].values())

def npc_active():
    return [n for n in npc_all() if n["state"] == "active"]

def npc_of(nid):
    return [n for n in npc_all() if n["nation"] == nid]

def npc_name_taken(name):
    low = (name or "").lower()
    return any(n["name"].lower() == low for n in npc_all())

def npc_humans(nid):
    return sum(1 for o in list(ONLINE) if getattr(o, "logged_in", False) and not o.w.is_closing()
               and getattr(o, "cmd", {}).get("nation") == nid)

def npc_stand(nid):
    return npc_state()["stand"].get(str(nid), 0) > time.time()

def npc_alarm(nid, now=None):
    """capital alarm running (NP.ALARM_*, user 2026-10-30 22:30)."""
    return npc_state()["alarm"].get(str(nid), 0) > (now or time.time())

def npc_capital_threat(nid):
    """an enemy-held province within NP.ALARM_RANGE portal steps of the capital (None = none)."""
    cap = CAPITALS.get(nid)
    if not cap:
        return None
    pl, seen, ring = cap // 100000, {cap}, [cap]
    for _ in range(NP.ALARM_RANGE):
        nxt = []
        for p in ring:
            for q in PORTAL_LINKS.get(p % 100000, ()):
                q = pl * 100000 + q
                if q in seen:
                    continue
                seen.add(q)
                nxt.append(q)
                o = province_owner(q)
                if o and not same_side(o, nid):
                    return q
        ring = nxt
    return None

def npc_update_alarm(nid, now):
    st = npc_state()
    k = str(nid)
    if st["alarm"].get(k, 0) > now:
        return True
    q = npc_capital_threat(nid)
    if q is None:
        if k in st["alarm"]:
            st["alarm"].pop(k, None)
            log(f"   NPC: nation {nid} capital alarm over")
            npc_dirty()
        return False
    st["alarm"][k] = now + NP.ALARM_SECONDS
    npc_dirty()
    raid_notify(nid, f"CAPITAL ALARM: the enemy holds {province_label(q)} next to our capital.  For "
                     f"{NP.ALARM_SECONDS // 3600} hours up to {NP.ALARM_ACTIVE} commanders take the field and strike back.",
                (255, 150, 120))
    log(f"   NPC: nation {nid} CAPITAL ALARM - {q} (nation {province_owner(q)}) borders the capital; "
        f"up to {NP.ALARM_ACTIVE} NPCs, more aggressive for {NP.ALARM_SECONDS // 3600} h")
    return True

def npc_stand_mult(nid):
    try:
        return NP.LAST_STAND_HP if npc_stand(nid) else 1.0
    except Exception:
        return 1.0

# ---- roster -----------------------------------------------------------------------------------------------------------
def npc_pool():
    """chassis an NPC may use: ground Infantry / Mobile units (Factory + Lab forms), by display NAME (that is how the
    server stores advanced forms).  fast = faster than the median = POC capturer material."""
    if "p" in _NPC_POOL:
        return _NPC_POOL["p"]
    pool = []
    def speed(name):
        return float(UNIT_MANUAL.get(str(name).lower(), {}).get("speed_m_s", 10) or 10)
    # user 2026-10-23 21:23: NPCs field AVIATION too (tab 2, branch avi).  Aircraft are never the main kind or the
    # POC capturers of a doctrine (npc.pick_doctrine), they come as the second kind / counter picks.
    _BR = {0: "inf", 1: "mob", 2: "avi"}
    for _code, tab, infl, name in UNITS:
        if tab in _BR and name not in NPC_NO_UNITS:
            # (10-24) the Factory now sells every Mk1 chassis (Chimera, Hydra ... were Lab forms): those keep the old
            # Lab-form weight (influence / 8) so the NPC unit mix stays as before
            pool.append({"code": name, "min": infl, "rank": float(infl) if infl <= 14 else infl / 8.0, "spd": speed(name),
                         "branch": _BR[tab], "air": tab == 2})
    for adv, _code, base, uq, _zh in ADVANCED:
        if _TAB.get(base) in _BR and adv not in NPC_NO_UNITS:
            pool.append({"code": adv, "min": uq, "rank": uq / 8.0, "spd": speed(adv),
                         "branch": _BR[_TAB.get(base)], "air": _TAB.get(base) == 2})
    med = sorted(p["spd"] for p in pool)[len(pool) // 2]
    for p in pool:
        p["fast"] = p["spd"] >= med
        try:                      # can it hit GROUND units? (anti-air only kinds are never the main kind of a doctrine)
            _st = unit_stats9(npc_unit(p["code"], max(1, int(p["min"]))))
            p["ground"] = _st[3] > 0
            p["armed"] = _st[3] > 0 or _st[6] > 0
            p["aa"] = _st[6] > 0                                    # (22:48 platoons) can hit aircraft
            p["arty"] = _st[3] > 0 and _st[4] >= NPC_ARTY_RANGE      # long-range gun
        except Exception:
            p["ground"], p["armed"], p["aa"], p["arty"] = True, True, False, False
    pool = [p for p in pool if not p.get("air") or p.get("armed", True)]   # unarmed aircraft: no use in an army
    _NPC_POOL["p"] = pool
    return pool

NPC_AIR_SHARE = 0.3          # share of the existing NPCs that switch their second kind to aircraft once

def npc_air_wing(n):
    """one-time: an existing NPC whose aviation branch can field an armed aircraft takes it as its second kind
    (chance NPC_AIR_SHARE, drawn from its id so it is stable).  True = changed."""
    if n.get("air_mig"):
        return False
    n["air_mig"] = True
    doc = n.get("doctrine")
    r = random.Random(n["id"] * 7717)
    if not doc or r.random() >= NPC_AIR_SHARE:
        return False
    air = [p for p in npc_pool() if p.get("air") and npc_can_field(n, p)]
    if not air or any(p["code"] in (doc["main"], doc["second"]) for p in air):
        return False
    new = r.choice(air)["code"]
    old, doc["second"] = doc["second"], new
    for u in n["squad"]:
        if u[0] == old:
            u[0] = new
    return True

_ROSTER_OK = {}               # npc id -> key of the roster last checked (2026-10-23 22:10: the checks ran for all 240
                              # NPCs every 10 s tick = ~70 ms of the game loop; now only after a change)

def _roster_key(n):
    d = n.get("doctrine") or {}
    return (n.get("level"), n.get("persona"), d.get("main"), d.get("second"), d.get("fast"), d.get("pp"), d.get("aa"),
            d.get("arty"), len(n.get("squad") or ()),
            n.get("air_mig"), tuple(c for c, _l in (n.get("squad") or ())[:1]))

def npc_ensure_roster(nid, size=None):
    st = npc_state()
    size = max(NP.NPC_CAP, size or 0)              # (10-30 22:30) a capital alarm grows the roster to NP.ALARM_ACTIVE
    allm = npc_of(nid)
    tier = PLANET_TIER.get(nation_planet(nid), 1)
    mine = [n for n in allm if _ROSTER_OK.get(n["id"]) != _roster_key(n)]
    avi = sum(1 for n in mine if npc_avi_mig(n))                          # (10-27 22:06) most NPCs have an aviation branch
    if avi:
        npc_dirty()
        log(f"   NPC: {avi} commanders of nation {nid} got an aviation branch")
    plt = sum(1 for n in mine if npc_platoon_mig(n, tier))                 # (22:48) 42 units in platoons of one kind
    if plt:
        npc_dirty()
        log(f"   NPC: {plt} commanders of nation {nid} re-formed into platoons (42 units, {NP.PLATOON_RANGE} per platoon)")
    fixed = sum(1 for n in mine if NP.conform(n, tier, npc_pool()))      # rosters made before the planet level floors
    doc = sum(1 for n in mine if NP.ensure_doctrine(n, tier, npc_pool()))  # rosters made before the doctrines (main kind)
    air = sum(1 for n in mine if npc_air_wing(n))                          # (2026-10-23 21:23) some take aircraft along
    real = sum(1 for n in mine if npc_realism(n))                          # unit kinds / levels a commander can field
    if air:
        npc_dirty()
        log(f"   NPC: {air} commanders of nation {nid} now field aircraft as their second kind")
    for n in mine:
        _ROSTER_OK[n["id"]] = _roster_key(n)
    mine = allm
    if real:
        npc_dirty()
        log(f"   NPC: {real} commanders of nation {nid} limited to the unit kinds / levels of their branches")
    if doc:
        npc_dirty()
        log(f"   NPC: {doc} commanders of nation {nid} re-formed by doctrine (main + second kind + capturers)")
    if fixed:
        npc_dirty()
        log(f"   NPC: {fixed} commanders of nation {nid} moved into the level range of tier {tier}")
    if len(mine) >= size:
        return mine
    taken = {n["name"].lower() for n in st["npcs"].values()} | {a.lower() for a in load_accounts()}
    while len(mine) < size:
        uid = st["next_id"]
        st["next_id"] += 1
        n = NP.new_npc(nid, tier, uid, taken, npc_pool())
        st["npcs"][str(uid)] = n
        npc_realism(n)
        npc_platoon_mig(n, tier)                           # (22:48) platoons from the start
        taken.add(n["name"].lower())
        st["npcs"][str(uid)] = n
        mine.append(n)
    npc_dirty()
    log(f"   NPC: roster of nation {nid} created ({len(mine)} commanders)")
    return mine

NPC_AVI_SHARE = 0.85         # NPC commanders with an aviation branch (2026-10-27 22:06 "NPCs must use aircraft")
NPC_AVI_MIG = 1              # existing NPCs get their aviation branch re-drawn once (n["hist"]["avi_mig"])

def npc_avi_mig(n):
    """one-time: an NPC made before NPC_AVI_SHARE gets the new aviation level (its stored history keeps the rest)."""
    h = npc_history(n)
    if h.get("avi_mig") == NPC_AVI_MIG:
        return False
    h["avi_mig"] = NPC_AVI_MIG
    lv = n["level"]
    r = random.Random(n["id"] * 7919 + lv + 17)
    new = max(1, lv - r.randint(0, 12)) if r.random() < NPC_AVI_SHARE else 1
    if new <= h["lv"][2]:
        return False
    h["lv"][2] = new
    n.pop("prof", None)                                    # branch levels -> influence / what it can field
    return True

def npc_history(n):
    """a believable past for the profile window (user 2026-10-22 14:59: NPC profiles were all zero).  Drawn once from the
    NPC id so it never jumps around; real wins / losses since then are added on top."""
    h = n.get("hist")
    if h:
        return h
    lv = n["level"]
    r = random.Random(n["id"] * 7919 + lv)
    lv_mob = max(1, lv - r.randint(0, 12))
    lv_avi = max(1, lv - r.randint(0, 12)) if r.random() < NPC_AVI_SHARE else 1   # (10-27 22:06: was 60 %, lv-5..30)
    lv_org = max(1, lv - r.randint(10, 35)) if r.random() < 0.4 else 1
    wins = r.randint(lv, lv * 4)
    h = n["hist"] = {
        "lv": [lv, lv_mob, lv_avi, lv_org],
        "xp": [int(PG.branch_xp_need(x) * r.uniform(0.05, 0.95)) for x in (lv, lv_mob, lv_avi, lv_org)],
        "wins": wins, "losses": r.randint(wins // 4, max(wins // 4 + 1, int(wins * 0.9))),
        "honor": r.randint(lv * 40, lv * 160),              # shown / 100
    }
    return h

# ---- a commander like a player's (user 2026-10-22 22:22) ------------------------------------------------------------------
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

def npc_can_field(n, p):
    """the NPC may take unit kind p (pool entry): influence of its branch, and for aircraft an aviation branch high enough
    that the aircraft are not below the planet's unit level floor (branch level + 3 = their cap)."""
    if p["min"] > npc_influence(n, p.get("branch", "inf")):
        return False
    if p.get("air"):
        tier = PLANET_TIER.get(nation_planet(n["nation"]), 1)
        return npc_profile(n)["br"].get("avi", 1) + 3 >= max(NP.TIER_UNIT_FLOOR.get(tier, 1), 10)
    return True

# ---- PLATOONS (user 2026-10-24 22:48) ------------------------------------------------------------------------------------
# Every NPC carries 42 units in platoons of ONE kind, 6..8 units each (its deploy rule = the "politics" points: Tactics //
# 20 + 6, kept inside NP.PLATOON_RANGE).  Platoon k = the k-th slice of the roster (NP.platoon_sizes), role by
# NP.PLATOON_ROLES: capturers (fast), main line, anti-air, artillery, more line / the second kind.  3..4 platoons of
# different roles go into a battle (npc_battle_units) and are swapped by the battle situation (npc_fresh_wave).
NPC_FIELD_PLATOONS = (3, 4)
NPC_SIDE_UNITS = 96          # all NPC units of one side on a battle map at a time: above it NPCs field fewer platoons
NPC_MIN_PLATOONS = 2         # ... but never fewer than this

def npc_platoon_size(n):
    return max(NP.PLATOON_RANGE[0], min(NP.PLATOON_RANGE[1], npc_deploy(n)))

def npc_platoon_roles(n, allowed=None):
    """anti-air and artillery kinds of the doctrine from what the NPC may field (None when it has none)."""
    allowed = allowed or [p for p in npc_pool() if npc_can_field(n, p)] or npc_pool()[:3]
    doc = n["doctrine"]
    rank = lambda p: (p["rank"], p["min"])
    aa = [p for p in allowed if p.get("aa") and p["code"] != doc.get("main")]
    gaa = [p for p in aa if not p.get("air")]                 # ground anti-air first (it can also hold POCs)
    doc["aa"] = max(gaa or aa, key=rank)["code"] if (gaa or aa) else None
    ar = [p for p in allowed if p.get("arty") and not p.get("air") and p["code"] != doc.get("main")]
    doc["arty"] = max(ar, key=rank)["code"] if ar else None
    # (2026-10-27 22:06) the air platoon: best armed aircraft, ground attackers first (they fight anything)
    doc["air"] = npc_pick_air(n, allowed)

def npc_pick_air(n, allowed):
    """(user 2026-10-27 23:26 "the NPCs only bring Roc"): the air platoon's kind.  max(rank) always gave Roc (its
    Factory rank 10 beats every other low-level aircraft), now: a FAMILY drawn per NPC (stable, from its id) among the
    families of armed aircraft it can field - ground attackers weight 1, anti-air-only 0.5 - then the best Mk of it."""
    air = [p for p in allowed if p.get("air") and p.get("armed", True)]
    if not air:
        return None
    fam = {}
    for p in air:
        fam.setdefault(str(p["code"]).split("-MK")[0], []).append(p)
    names = sorted(fam)
    r = random.Random(n["id"] * 131 + 7)
    w = [1.0 if any(p.get("ground") for p in fam[f]) else 0.5 for f in names]
    f = r.choices(names, w)[0]
    return max(fam[f], key=lambda p: (p["min"], p["rank"]))["code"]

NPC_PMIG = 4                 # roster form version (3 = 22:06 air platoon, 4 = 23:26 varied aircraft); lower = re-formed once

def npc_platoon_mig(n, tier):
    """an NPC without platoons: 42 units, platoon size from its deploy rule, aa / artillery kinds; the levels it had are
    kept (best first), new units get its usual level.  True = changed."""
    doc = n.get("doctrine")
    if doc and doc.get("pp") and doc.get("pmig") == NPC_PMIG and len(n.get("squad") or ()) == NP.SQUAD_RANGE[1]:
        return False
    if not doc:
        NP.ensure_doctrine(n, tier, npc_pool())
        doc = n["doctrine"]
    doc["pp"] = npc_platoon_size(n)
    doc["pmig"] = NPC_PMIG
    npc_platoon_roles(n)
    size = NP.SQUAD_RANGE[1]
    r = random.Random(n["id"] * 911 + n["level"])
    lv = sorted((l for _c, l in n.get("squad") or ()), reverse=True)
    lv += [NP.unit_level(n["level"], r, tier) for _ in range(size - len(lv))]
    kinds = NP.doctrine_kinds(doc, size)
    n["squad"] = [[c, l] for c, l in zip(kinds, sorted(lv[:size], reverse=True))]
    n["hl"] = None
    npc_realism(n)
    return True

def npc_platoons(n):
    """[(role, kind, [roster indices])] of n's platoons (slices of the roster; a platoon whose units changed kind keeps
    the kind most of its units have)."""
    doc = n.get("doctrine") or {}
    sq = n["squad"]
    if not doc.get("pp"):
        return [("main", sq[0][0] if sq else None, list(range(len(sq))))]
    out, i0 = [], 0
    for k, sz in enumerate(NP.platoon_sizes(len(sq), doc["pp"])):
        idx = list(range(i0, min(len(sq), i0 + sz)))
        i0 += sz
        if not idx:
            continue
        kinds = [sq[i][0] for i in idx]
        out.append((NP.PLATOON_ROLES[k % len(NP.PLATOON_ROLES)], max(set(kinds), key=kinds.count), idx))
    return out

def npc_platoon_of(n, idx):
    for k, (_r, _c, ix) in enumerate(npc_platoons(n)):
        if idx in ix:
            return k
    return 0

def npc_realism(n):
    """only unit kinds its branches can field (influence) and unit levels <= branch level + 3.  True = changed."""
    pool = npc_pool()
    pr = npc_profile(n)
    allowed = [p for p in pool if npc_can_field(n, p)] \
        or sorted(pool, key=lambda p: p["min"])[:3]
    codes = {p["code"] for p in allowed}
    changed = False
    doc = n.get("doctrine")
    if not doc or any(doc.get(k) not in codes for k in ("main", "second", "fast")):
        main = doc["main"] if doc and doc.get("main") in codes else None
        _keep = {k: doc[k] for k in ("pp", "pmig") if doc.get(k)} if doc else {}
        _keep.update({k: doc[k] for k in ("aa", "arty", "air") if doc and doc.get(k) in codes})
        n["doctrine"] = doc = NP.pick_doctrine(allowed, 10 ** 6, random.Random(n["id"] * 31 + n["level"]), main)
        doc.update(_keep)                                   # (22:48) platoon size and the aa / artillery kinds stay
        changed = True
    if doc and doc.get("pp") and (any(doc.get(k) and doc[k] not in codes for k in ("aa", "arty", "air"))
                                  or (doc.get("air") is None and any(p.get("air") for p in allowed))):
        npc_platoon_roles(n, allowed)
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

def npc_cmd(n):
    """the commander record the directory / hall of fame / user info windows read."""
    lv = n["level"]
    h = npc_history(n)
    pr = npc_profile(n)
    br = {k: {"level": pr["br"][k], "xp": x} for k, x in zip(("inf", "mob", "avi", "org"), h["xp"])}
    return {"nation": n["nation"], "look": n["look"], "attrs": list(pr["attrs"]),
            "points": 0, "tier": PLANET_TIER.get(nation_planet(n["nation"]), 1), "branches": br,
            "honor": h["honor"] + n.get("honor", 0), "wins": h["wins"] + n.get("wins", 0),
            "losses": h["losses"] + n.get("losses", 0), "medals": [],
            "reincarnations": pr["reinc"], "stats": {"kills": (h["wins"] + n.get("wins", 0)) * 4}, "npc": True}

def npc_account(n):
    return {"commander": npc_cmd(n), "units": [], "resources": list(START_RESOURCES), "npc": True}

def npc_directory_rows(only=None):
    return [(n["name"], npc_cmd(n)) for n in npc_all() if only is None or uid_of(n["name"]) == only]

def npc_by_name(name):
    low = (name or "").strip().lower()
    return next((n for n in npc_all() if n["name"].lower() == low), None)

# ---- strategic-map presence ---------------------------------------------------------------------------------------------
def _walk_pos(path, depart, arrive, now, last_ok=False):
    """the province a walker is in: step by step along path (it reaches the last one only at `arrive`)"""
    if not path:
        return None
    if len(path) == 1:
        return path[0]
    f = 0.0 if arrive <= depart else max(0.0, min(1.0, (now - depart) / (arrive - depart)))
    i = int(f * (len(path) - 1))
    return path[min(i, len(path) - (1 if last_ok and f >= 1.0 else 2))]

def npc_here(n, now=None):
    """the province an NPC is in right now (marching / walking home step by step, else its task's target / capital)"""
    return npc_location(n, now)[0]

def npc_march_path(n, target, now=None, pace=1.0, start=None):
    """user 2026-10-23 15:09: NPCs move province by province like players (no appearing in an empty province): the road
    from where the NPC is now, only through provinces of its nation / allies (the target excepted).
    -> (path, seconds) or (None, None) when there is no such road."""
    now = now or time.time()
    st = start or npc_here(n, now) or CAPITALS.get(n["nation"])
    nid = n["nation"]
    # user 2026-10-25 21:17 (red NPCs attacked a blue province with no red province next to it): a march starts only
    # from own / allied land - an NPC still standing in another nation's or alien province (after a battle there) has
    # no road from there; it goes home first.
    if st != target and not same_side(province_owner(st), nid):
        return None, None
    path = _route(st, target, lambda q: same_side(province_owner(q), nid))
    if not path:
        return None, None
    return path, NP.march_seconds(max(1, len(path) - 1)) * pace

def npc_may_stand(pid, nid):
    """(user 2026-10-28 22:19/22:20 "a yellow province must not hold NPCs or players of another colour - NPCs follow the
    battlefield rules"): an NPC may be in its own / allied province, unowned (alien) land, or a province with a battle
    running there (a real battle not yet won, or an NPC assault / raid)."""
    if not pid:
        return True
    own = province_owner(pid)
    if not own or same_side(own, nid):
        return True
    B = BATTLES.get(pid)
    if B is not None and not B.get("won"):
        return battle_involves(B, nid)
    r = RAIDS.get(pid)
    return bool(r) and (same_side(r.get("npc") or 0, nid) or same_side(r.get("nation") or 0, nid))

def battle_involves(B, nid):
    """(user 2026-10-29 23:43: red NPCs stood in a blue-vs-yellow battle although red had no province next to it - left
    over from an earlier battle there, a new battle there let them stay): the battle exception holds only for a side that
    really takes part - the attacker, the defender, or a side with units still alive on the map."""
    if nid is None:
        return False
    for k in ("npc_attacker", "defender"):
        v = B.get(k)
        if v and same_side(v, nid):
            return True
    for tg in (B.get("targets") or {}).values():
        if tg.get("hp", 1) > 0 and tg.get("nation") is not None and same_side(tg["nation"], nid):
            return True
    return False

def _npc_safe_step(path, here, nid):
    """the last province before `here` on `path` where the NPC may stand (else its capital)"""
    if npc_may_stand(here, nid):
        return here
    i = path.index(here) if path and here in path else 0
    for q in reversed((path or [])[:i]):
        if npc_may_stand(q, nid):
            return q
    return CAPITALS.get(nid)

def npc_rule_fix(n, now):
    """the battlefield rule for walkers / marchers (npc_tick): one whose next step lies in a province that became
    another nation's (no battle there) does not walk through it - it re-routes from the last province of its side over
    own / allied land, or (no such road) a march is called off and the NPC goes home the same way."""
    nid = n["nation"]
    ok = lambda q: same_side(province_owner(q), nid)
    t = n.get("task")
    if t and t.get("phase") == "march" and t.get("path"):
        raw = _walk_pos(t["path"], t["depart"], t["arrive"], now)
        if raw is not None and not npc_may_stand(raw, nid):
            safe = _npc_safe_step(t["path"], raw, nid)
            path, secs = npc_march_path(n, t["target"], now, start=safe) if safe else (None, None)
            if path:
                t.update(path=path, depart=now, arrive=now + secs, origin=path[0])
                log(f"   NPC: {n['name']} re-routes around {raw} (taken by nation {province_owner(raw)}) via {path}")
            else:
                log(f"   NPC: {n['name']} calls off its {t.get('kind')} on {t.get('target')} - {raw} was taken by "
                    f"nation {province_owner(raw)}, no road over own land")
                t["path"] = [safe] if safe else None
                npc_release(n, now, random.uniform(60, 300))
        return
    w = n.get("walk")
    if not t and w and now < w["arrive"]:
        raw = _walk_pos(w["path"], w["depart"], w["arrive"], now)
        if raw is not None and not npc_may_stand(raw, nid):
            safe = _npc_safe_step(w["path"], raw, nid)
            cap = CAPITALS.get(nid)
            path = _route(safe, cap, ok) if safe and safe != cap else None
            if path and len(path) >= 2:
                n["walk"] = {"path": path, "depart": now, "arrive": now + NP.march_seconds(len(path) - 1)}
            else:
                n.pop("walk", None)                    # no road over own land: straight home
            log(f"   NPC: {n['name']} walks home around {raw} (taken by nation {province_owner(raw)})")

def npc_location(n, now=None):
    """(province the NPC is drawn in, travel target).  Never a province of another nation without a battle there
    (npc_may_stand): a step that became enemy land shows the NPC in the last province of its side (npc_rule_fix
    re-routes it at the next tick)."""
    here, tgt = _npc_location_raw(n, now)
    if here is not None and not npc_may_stand(here, n["nation"]):
        t = n.get("task") or {}
        w = n.get("walk") or {}
        path = t.get("path") if t.get("phase") == "march" else (w.get("path") if not t else None)
        here = _npc_safe_step(path, here, n["nation"])
        if tgt is not None and not npc_may_stand(tgt, n["nation"]) and not t:
            tgt = here
    return here, tgt

def _npc_location_raw(n, now=None):
    """(province the NPC is drawn in, travel target)."""
    cap = CAPITALS.get(n["nation"])
    t = n.get("task")
    now = now or time.time()
    if not t:
        w = n.get("walk")                              # walking home after a task (province by province)
        if w and now < w["arrive"]:
            here = _walk_pos(w["path"], w["depart"], w["arrive"], now)
            return here, here
        post = n.get("post")                           # (22:41) stays in a cut-off enclave to strike its bridge
        if post:
            if post in npc_enclaves_cached(n["nation"], now) or (
                    n.get("post_kind") == "fallback" and same_side(province_owner(post), n["nation"])):
                return post, post                      # (23:27) or holds the nearest province after a lost battle
            n.pop("post", None)                        # reconnected (or lost): home as usual
        return cap, cap
    if t.get("path") and t.get("phase") == "march":
        here = _walk_pos(t["path"], t["depart"], t["arrive"], now)
        return here, here
    if t and t.get("kind") in ("attack", "defend", "intercept", "support", "patrol"):
        if t.get("phase") in ("march", "ambushed"):
            # 2026-10-22 15:15 (user): the NPC showed up in the target province before the battle started there, and the
            # white route line pointed the wrong way.  Now: the whole march happens in its OWN province (the dot walks to
            # the border, no route line = field is the province itself); it enters the target only when it arrives, and
            # the battle starts at that moment.  In the target the field is the province it CAME FROM: the client draws
            # the white line from that field to the province the record is listed in (origin -> target).
            o = t.get("origin") or cap
            return o, o
        return t["target"], (t.get("origin") or t["target"])
    return cap, cap

NPC_ENTER_SECONDS = 30.0      # an NPC that arrived in a province walks from its border to the centre in this time (minimap)

def _dot_dir(a, b):
    """unit vector in TILE axes of a province preview map that points, ON SCREEN, from province a toward province b.
    (user 2026-10-23 15:38: a dot walked up / up-right while the NPC went down-left.)  The old code mixed up the column
    and the row of CCRR and ignored that the map is drawn isometric: screen (sx, sy) -> tile x = sy + sx/2,
    y = sy - sx/2."""
    import math
    (ax, ay), (bx, by) = _strat(a % 100000), _strat(b % 100000)
    sx, sy = bx - ax, by - ay
    tx, ty = sy + sx / 2.0, sy - sx / 2.0
    L = math.hypot(tx, ty) or 1.0
    return tx / L, ty / L

def npc_dot(n, now=None):
    """(x, y) of the NPC's dot on the province preview minimap (0x2e user record +0x2c / +0x30, tile units of a 128 map).
    Marching: leaves the centre of its province toward the target province (progress = time).  Fighting: circles the
    province centre.  Home: wanders near the centre."""
    import math
    now = now or time.time()
    tk = n.get("task") or {}
    c = 64.0
    if tk.get("kind") in ("attack", "defend", "intercept", "support", "patrol") and tk.get("phase") == "march":
        a = tk.get("depart", now)
        f = min(1.0, max(0.0, (now - a) / max(1.0, tk.get("arrive", a + 1) - a)))
        o, g = tk.get("origin") or 0, tk.get("target") or 0
        pth = tk.get("path")
        if pth and len(pth) >= 2:                      # province by province: the leg it is walking now
            F = f * (len(pth) - 1)
            i = min(int(F), len(pth) - 2)
            o, g, f = pth[i], pth[i + 1], F - i
        dc, dr = _dot_dir(o, g)
        ln = 1.0
        r = 8 + 48 * f
        return int(max(2, min(125, c + dc / ln * r))), int(max(2, min(125, c + dr / ln * r)))
    if tk.get("kind") in ("attack", "defend", "intercept", "support", "patrol") and tk.get("phase") in ("siege", "raid", "battle", "ambush", "support", "patrol") \
            and tk.get("origin"):
        # just arrived: walks in from the border it came through toward the centre (first NPC_ENTER_SECONDS)
        f = (now - tk.get("entered", 0)) / NPC_ENTER_SECONDS
        if 0.0 <= f < 1.0:
            o, g = tk.get("origin") or 0, tk.get("target") or 0
            dc, dr = _dot_dir(g, o)
            ln = 1.0
            r = 56 - 44 * f
            return int(max(2, min(125, c + dc / ln * r))), int(max(2, min(125, c + dr / ln * r)))
    if not tk:
        # at home in the capital (user 2026-10-23 15:52: 10 NPCs listed, no dot seen): a walkable spot of the capital map,
        # different for every NPC and changing every few minutes (like the commanders wandering in town), instead of a
        # small circle in the middle of the map
        try:
            spots = _CAPS.get("spots") or []
            if spots:
                x, y = spots[(n["id"] * 7919 + int(now // 150) * 104729) % len(spots)]
                return int(max(2, min(125, x // 32))), int(max(2, min(125, y // 32)))
        except Exception:
            pass
    ph = 0.00045 * now * (1 + (n["id"] % 5) * 0.2) + n["id"]
    rad = 12 if tk else 22
    return int(c + rad * math.cos(ph)), int(c + rad * math.sin(ph * 1.3))

# ---- equipment ---------------------------------------------------------------------------------------------------------
def _w_score(it):
    st = it.get("stats", {})
    cd = float(st.get("Ground Cooldown") or st.get("Air Cooldown") or 1.5) or 1.5
    return (float(st.get("Ground Damage", 0) or 0) + 0.5 * float(st.get("Air Damage", 0) or 0)) / max(0.5, cd)

def _a_score(it):
    st = it.get("stats", {})
    return float(st.get("Health", 0) or 0) + 10.0 * float(st.get("Armor", 0) or 0)

def npc_unit(name, level):
    """roster-style unit dict of an NPC unit: the stock loadout with the best weapon and armour that still fit."""
    key = (name, int(level))
    u = _NPC_UNITS.get(key)
    if u is not None:
        return u
    cmd = PG.ensure_commander({"attrs": [40, min(120, level), min(120, level + 10), 60]})
    u = {"uid": 0, "chassis": name, "level": int(level)}
    u["items"] = stock_loadout(u, cmd)
    code = CODE_OF.get(DISPLAY.get(name, name), name)
    maxtl = int(level) + PG.attr(cmd, 2) // 2
    if code != "g037":
        slots = dict(UNIT_SLOTS.get(code, []))
        for kind, typ, sc in (("Weapon", 4, _w_score), ("Armor", 5, _a_score)):
            for sid, k in slots.items():
                if k != kind:
                    continue
                cands = [it for it in ITEMS if it.get("slot") == sid and it.get("type") == typ and not it.get("gold")
                         and not it.get("demon") and not it.get("air_only") and not special_item(it) and _itl(it) <= maxtl]
                cands.sort(key=sc, reverse=True)
                others = [i for i in u["items"] if ITEM_BY_ID.get(i, {}).get("slot") != sid]
                for it in cands[:12]:
                    if not equip_problems(u, cmd, others + [it["id"]]):
                        u["items"] = others + [it["id"]]
                        break
        # (user 2026-10-23 22:49) a Detector / Cloak item when the chassis can carry one (Red-Eye / Arbalest detect;
        # the Cloak items are biodrives = organic units only), lowest tech first
        # (10-24) support skills come only from equipment now: the role items (Heal, Repair, Teleport, Shield)
        _taken = set()                       # slots already holding a role item: never swapped for a later one
        for bit in tuple(NPC_SKILL_BITS.get(code, ())) + (NPC_DETECT_BIT, NPC_CLOAK_BIT):
            if any(bit in _skill_item_bits(ITEM_BY_ID.get(i, {})) for i in u["items"]):
                continue
            sp = sorted((it for it in ITEMS if bit in _skill_item_bits(it) and _itl(it) <= maxtl and not it.get("gold")
                         and not it.get("demon") and it.get("slot") not in _taken), key=_itl)
            for it in sp[:8]:
                others = [i for i in u["items"] if ITEM_BY_ID.get(i, {}).get("slot") != it.get("slot")]
                if not equip_problems(u, cmd, others + [it["id"]]):
                    u["items"] = others + [it["id"]]
                    _taken.add(it.get("slot"))
                    break
    _NPC_UNITS[key] = u
    return u

# ---- COUNTER PICKS (user 2026-10-23 21:09: "NPC能更换对战场有利的单位进行作战") ----------------------------------------
# What the enemy has on the map (air share, armour classes, mean armour) decides which units of the NPC's roster go in:
# expected damage per second against that mix with the client's damage rule (damage_types.py), times the unit's health.
# (2026-10-23 22:09, short pauses) an uncached npc_unit() is an equipment search of ~4 ms; scoring the whole pool at a
# new level could cost 200 ms in the game loop.  Pool scoring uses levels rounded to 5 and computes at most
# _ST9_BUDGET new entries per second (the rest count as unknown until a later call).
_ST9 = {}
_ST9_BUDGET = [0, 0.0]
_ST9_PER_SEC = 4

def pool_st9(code, lv):
    lv = max(1, min(99, int(round(lv / 5.0)) * 5 or 1))
    k = (code, lv)
    if k in _ST9:
        return _ST9[k]
    now = time.monotonic()
    if now - _ST9_BUDGET[1] >= 1.0:
        _ST9_BUDGET[0], _ST9_BUDGET[1] = 0, now
    if _ST9_BUDGET[0] >= _ST9_PER_SEC:
        return None
    _ST9_BUDGET[0] += 1
    try:
        _ST9[k] = unit_stats9(npc_unit(code, lv))
    except Exception:
        _ST9[k] = ()
    return _ST9[k]

def battle_threat(ctx, nid):
    """{'air': share, 'rows': {armour row: weight}, 'armor': mean, 'n': units} of the units fighting nation nid on the
    map of ctx (a battle dict or a session); None when nothing is known."""
    try:
        B = ctx if isinstance(ctx, dict) else (getattr(ctx, "battle", None) or {"members": [ctx], "targets": getattr(ctx, "targets", {})})
        tot = air = arm = 0.0
        aa = [0.0]
        rows = {}
        def add(st9, kind, hp):
            nonlocal tot, air, arm
            if not st9 or len(st9) < 9:
                return
            w = max(1.0, float(hp))
            tot += w
            air += w if kind == 2 else 0.0
            aa[0] += w if st9[6] > 0 else 0.0
            arm += w * st9[0]
            rows[st9[1]] = rows.get(st9[1], 0.0) + w
        for nat, st9, kind, hp in battle_units(B):          # (battle_rules: the one listing)
            if nat is not None and same_side(nat, nid):
                continue
            add(st9, kind, hp)
        if tot <= 0:
            return None
        return {"air": air / tot, "aa": aa[0] / tot, "rows": {r: w / tot for r, w in rows.items()}, "armor": arm / tot, "n": tot}
    except Exception as e:
        log(f"   battle_threat: {e!r}")
        return None

def unit_effect(st9, th):
    """expected damage per second of a unit with stats9 st9 against the threat th (client rule:
    max(1, dmg - armour x (100 + TABLE[row][class]) / 100) per cooldown)."""
    if not th or len(st9) < 9:
        return 0.0
    dcl = st9[2] // 100
    def per_layer(dmg, cd):
        if dmg <= 0:
            return 0.0
        e = 0.0
        for row, w in th["rows"].items():
            e += w * DT.hit_damage(dmg, th["armor"], row, dcl)      # (damage_types: the one formula)
        return e / max(0.3, cd / 100.0)
    return (1 - th["air"]) * per_layer(st9[3], st9[5]) + th["air"] * per_layer(st9[6], st9[8])

NPC_ADAPT_EVERY = 3 * 3600      # an NPC re-thinks its second unit kind at most this often
NPC_ADAPT_GAIN = 1.3            # ... and only for a kind this much better against what it has been fighting

def npc_remember_threat(npc, th, a=0.3):
    """moving average of the enemies this NPC met (air share, armour classes, mean armour); JSON-safe (str keys)."""
    old = npc.get("seen")
    new_rows = {str(r): w for r, w in th["rows"].items()}
    if not old:
        npc["seen"] = {"air": th["air"], "armor": th["armor"], "rows": new_rows}
        return
    old["air"] = (1 - a) * old["air"] + a * th["air"]
    old["armor"] = (1 - a) * old["armor"] + a * th["armor"]
    rows = {str(r): (1 - a) * w for r, w in old.get("rows", {}).items()}
    for r, w in new_rows.items():
        rows[r] = rows.get(r, 0.0) + a * w
    old["rows"] = rows

def npc_adapt(n, now):
    """user 2026-10-23 21:09: the NPC changes its army to what works on this front - between battles, its SECOND unit
    kind becomes the pool kind with the best expected damage against the enemies it has met (e.g. anti-air after
    fighting aircraft); the units of the old second kind are re-equipped as the new kind (same levels)."""
    seen, doc = n.get("seen"), n.get("doctrine")
    if not seen or not doc or now < n.get("adapt_t", 0):
        return
    n["adapt_t"] = now + NPC_ADAPT_EVERY
    th = {"air": seen["air"], "armor": seen["armor"], "rows": {int(r): w for r, w in seen.get("rows", {}).items()}}
    lv = max(1, n.get("level", 1))
    def eff(code):
        try:
            st_ = pool_st9(code, lv)
            return unit_effect(st_, th) if st_ else 0.0
        except Exception:
            return 0.0
    use = [p["code"] for p in npc_pool() if npc_can_field(n, p)]
    if not use:
        return
    if pool_st9(doc["second"], lv) is None or any(pool_st9(c, lv) is None for c in use):
        n["adapt_t"] = now + 30                        # (22:38) values not computed yet: decide later, not on zeros
        return
    best = max(use, key=eff)
    cur = max(eff(doc["second"]), 0.01)
    if best in (doc["second"], doc["main"], doc["fast"]) or eff(best) < NPC_ADAPT_GAIN * cur:
        return
    old = doc["second"]
    if not any(c == old for c, _l in n["squad"]):
        return                                         # its army has none of that kind: nothing to change
    doc["second"] = best
    k = 0
    for i, (c, l) in enumerate(n["squad"]):
        if c == old:
            n["squad"][i] = [best, l]
            k += 1
    npc_realism(n)                                  # unit levels <= branch level + 3 (aviation has its own branch)
    npc_dirty()
    log(f"   NPC: {n['name']} (nation {n['nation']}) adapts its army: {old} -> {best} x{k} "
        f"(enemy air {seen['air']:.0%}, damage {cur:.0f} -> {eff(best):.0f}/s)")

def npc_field_platoons(n, n_npcs=1, ctx=None):
    """how many platoons NPC n takes into a battle: 3..4 (4 for warlike commanders and one in three of the others),
    fewer only when its side would exceed NPC_SIDE_UNITS units on the map (n_npcs NPCs of the side coming in now, plus
    the side's units already there)."""
    lo, hi = NPC_FIELD_PLATOONS
    want = hi if n.get("persona") == "warlike" or (n["id"] % 3 == 0) else lo
    p = npc_platoon_size(n)
    have = 0
    try:
        tg_ = (ctx.get("targets") if isinstance(ctx, dict) else getattr(ctx, "targets", None)) or {}
        have = sum(1 for tg in tg_.values() if tg.get("npc") is not None and tg.get("hp", 0) > 0
                   and same_side(tg.get("nation"), n["nation"]))
    except Exception:
        pass
    while want > NPC_MIN_PLATOONS and have + want * p * max(1, n_npcs) > NPC_SIDE_UNITS:
        want -= 1
    return want

def npc_pick_platoons(npc, nid, n_pl, exclude=(), ctx=None, capture=True):
    """the n_pl platoons that suit this battle best (user 2026-10-24 22:48: complementary platoons, swapped by the
    situation): the capturer platoon first (POCs to take), then by health x effect against the enemy actually on the map
    (enemy aircraft -> the anti-air platoon, ground armies -> artillery); a second platoon of a role / kind already
    taken counts less.  -> [(platoon no, role, [roster indices fit to fight])]"""
    hl, sq = NP.health(npc), npc["squad"]
    th = battle_threat(ctx, nid) if ctx is not None else None
    cands = []
    for k, (role, kind, idx) in enumerate(npc_platoons(npc)):
        ok = []
        for i in idx:
            if i in exclude or hl[i] < 0.35:
                continue
            st9 = unit_stats9(npc_unit(*sq[i]))
            if st9[3] <= 0 and st9[6] <= 0:
                continue
            ok.append(i)
        if len(ok) < max(2, (len(idx) + 1) // 2):
            continue                                  # a worn-out platoon recovers at home
        st9 = unit_stats9(npc_unit(*sq[ok[0]]))
        eff = unit_effect(st9, th) if th else 1.0
        cands.append({"k": k, "role": role, "kind": kind, "idx": ok, "eff": eff,
                      "h": sum(hl[i] for i in ok) / len(ok) * len(ok) / max(1, len(idx))})
    if not cands:
        return []
    top = max(c["eff"] for c in cands) or 1.0
    air = (th or {}).get("air", 0.0)
    for c in cands:
        e = c["eff"] / top
        c["s"] = c["h"] * (0.35 + 0.65 * e) + (1.2 * air if c["role"] == "aa" else 0.0) \
            + (0.25 * (1 - air) if c["role"] == "arty" else 0.0) + (0.15 if c["role"] == "main" else 0.0) \
            + (0.35 * (1 - (th or {}).get("aa", 0.3)) if c["role"] == "air" else 0.0) \
            - (0.6 if th and e < 0.05 else 0.0)
    picked = []
    if capture:
        fast = [c for c in cands if c["role"] == "fast"]
        if fast:
            picked.append(max(fast, key=lambda c: c["s"]))
    for c in cands:
        c["useless"] = bool(th) and c["eff"] / top < 0.05
    while len(picked) < n_pl:
        rest = [c for c in cands if c not in picked]
        # (23:20 log: a platoon that cannot hurt the enemy came in and was pulled out again a minute later) never bring
        # guns that cannot hurt this enemy while a platoon that can is left
        if any(not c["useless"] for c in rest):
            rest = [c for c in rest if not c["useless"]]
        elif picked:
            break
        if not rest:
            break
        def val(c):
            dup = sum(1 for q in picked if q["role"] == c["role"] or q["kind"] == c["kind"])
            return c["s"] * (0.55 ** dup)
        picked.append(max(rest, key=val))
    if th:
        npc_remember_threat(npc, th)
    return [(c["k"], c["role"], c["idx"]) for c in picked]

def npc_on_map(ctx, npc_id):
    """living units of NPC npc_id on the battle map of ctx (a session or a battle: its targets), walking out included."""
    try:
        tg_ = (ctx.get("targets") if isinstance(ctx, dict) else getattr(ctx, "targets", None)) or {}
        return sum(1 for tg in tg_.values() if tg.get("npc") == npc_id and tg.get("hp", 0) > 0)
    except Exception:
        return 0

def npc_room(npc, ctx):
    """(user 2026-10-31 13:23 "an NPC brings at most 12 units into a battle like a player, how many by its attributes"):
    units NPC npc may still put on the map = its deploy limit (Tactics // 20 + 6, max 12) - its units there now."""
    return max(0, npc_deploy(npc) - (npc_on_map(ctx, npc["id"]) if ctx is not None else 0))

def npc_battle_units(npc, k, nid, exclude=(), ctx=None, platoons=None, capture=True):
    """units of NPC npc for a battle: (name, level, stats9, hp, energy, speed, squad index, capturer?).
    Platoon NPCs (2026-10-24 22:48): whole platoons (npc_pick_platoons, `platoons` of them, default npc_field_platoons);
    the capturers are SQUAD_FAST healthy units of the fast platoon.  Older rosters: the k healthiest ARMED units
    (user 2026-10-22 14:05: the NPC swaps wounded units for healthy ones)."""
    hl, sq = NP.health(npc), npc["squad"]
    room = npc_room(npc, ctx)                      # (10-31 13:23) never more than the deploy limit on the map
    if room <= 0:
        return []
    if (npc.get("doctrine") or {}).get("pp"):
        n_pl = platoons or npc_field_platoons(npc, 1, ctx)
        p_sz = npc_platoon_size(npc)
        slim = room < 2 * p_sz                     # (10-31) little room: only the capturers of the fast platoon come,
        fill = room - (NP.SQUAD_FAST if slim and capture else 0)   # the rest of the room = the platoon(s) the battle needs
        n_pl = max(1, min(n_pl, (1 if slim and capture else 0) + -(-max(1, fill) // p_sz)))
        out = []
        for _k, role, idx in npc_pick_platoons(npc, nid, n_pl, exclude, ctx, capture):
            capt = set(sorted(idx, key=lambda i: -hl[i])[:NP.SQUAD_FAST]) if role == "fast" else set()
            if role == "fast" and slim and capture:
                idx = [i for i in idx if i in capt]
            for i in idx:
                if len(out) >= room:
                    break
                name, lv = sq[i]
                u = npc_unit(name, lv)
                st9 = unit_stats9(u)
                hp, en = unit_battle_stats(u)
                out.append((name, lv, st9, max(1, int(hp * npc_stand_mult(nid) * max(0.35, hl[i]))), en, unit_speed(u), i,
                            i in capt))
        return out[:room]
    k = min(k, npc_deploy(npc), room)             # player rule: Tactics // 20 + 6 units at a time (user 2026-10-22 22:22)
    nf = NP.fast_count(len(sq))
    cand = []
    for i, (name, lv) in enumerate(sq):
        if i in exclude or hl[i] < 0.35:
            continue
        st9 = unit_stats9(npc_unit(name, lv))
        if st9[3] <= 0 and st9[6] <= 0:
            continue
        cand.append(i)
    capt = sorted((i for i in cand if i < nf), key=lambda i: -hl[i])[:NP.SQUAD_FAST]
    th = battle_threat(ctx, nid) if ctx is not None else None
    if th and cand:
        eff = {i: unit_effect(unit_stats9(npc_unit(*sq[i])), th) for i in cand}
        top = max(eff.values()) or 1.0
        good = [i for i in cand if eff[i] > 0.05 * top]
        if len(good) >= min(k, len(cand)) // 2:                # units that cannot hurt this enemy stay in reserve
            cand = good + [i for i in capt if i not in good]
        rest = sorted((i for i in cand if i not in capt), key=lambda i: (-(hl[i] * (0.3 + 0.7 * eff[i] / top)), -sq[i][1]))
        npc_remember_threat(npc, th)
    else:
        rest = sorted((i for i in cand if i not in capt), key=lambda i: (-hl[i], -sq[i][1]))
    out = []
    doc = npc.get("doctrine") or {}
    krank = {doc.get("fast"): 0, doc.get("main"): 1}
    pick = sorted((capt + rest)[:k], key=lambda i: (i not in capt, krank.get(sq[i][0], 2), sq[i][0]))   # one kind = one block
    for i in pick:
        name, lv = sq[i]
        u = npc_unit(name, lv)
        st9 = unit_stats9(u)
        hp, en = unit_battle_stats(u)
        out.append((name, lv, st9, max(1, int(hp * npc_stand_mult(nid) * max(0.35, hl[i]))), en, unit_speed(u), i, i in capt))
    return out

# ---- world view for decisions ---------------------------------------------------------------------------------------------
def npc_dist_from(cap):
    key = cap % 100000
    if key not in _CAP_DIST:
        d, q = {key: 0}, [key]
        while q:
            a = q.pop(0)
            for b2 in PORTAL_LINKS.get(a, ()):
                if b2 not in d:
                    d[b2] = d[a] + 1
                    q.append(b2)
        _CAP_DIST[key] = d
    return _CAP_DIST[key]

def npc_defence(pid):
    """defence power of a province for the abstract battle (same scale as NP.power)."""
    w = world_state()
    owner = province_owner(pid)
    tier = PLANET_TIER.get((pid // 100000) % 1000, 1)
    if not owner:
        g = AL.garrison(w, pid)
        dist = max(1, province_distance(pid))
        base, step = AL.TIER_LEVEL[tier][0], AL.TIER_LEVEL[tier][1]
        lv = base + step * max(0, dist - 1)
        near, far = AL.PROVINCE_SQUADS[tier]
        sq = near if dist <= 2 else far
        return sq * 8 * (lv + 10) * 0.7 * g / 100.0
    idle = [n for n in npc_of(owner) if n["state"] == "active" and not n["task"]]
    sup = [n for n in npc_of(owner) if n["task"] and n["task"].get("kind") == "support" and n["task"].get("target") == pid
           and n["task"].get("phase", "support") == "support"]     # marching / ambushed squads do not defend yet
    p = 40.0 * tier + 20.0 * npc_humans(owner) + 0.4 * sum(NP.power_of(n) for n in idle) \
        + 1.0 * sum(NP.power_of(n) for n in sup)
    return p * (NP.LAST_STAND_HP if npc_stand(owner) else 1.0)

NPC_LOST = {}                   # (11-02) province -> (nation that lost it, when); in memory, fed by npc_owner_changed

def npc_army_map(nid, now):
    """(11-02 seek the fight) for nation nid: {province: enemy NPC squads standing / fighting / marching there} and the
    provinces from which enemy NPCs march on nid's land."""
    army, source = {}, set()
    for m in npc_all():
        if m["state"] != "active" or same_side(m["nation"], nid):
            continue
        try:
            here, _tgt = npc_location(m, now)
        except Exception:
            here = None
        if here is not None:
            army[here] = army.get(here, 0) + 1
        t = m.get("task")
        if t and t.get("kind") == "attack" and province_owner(t.get("target")) == nid and t.get("origin"):
            source.add(t["origin"])
    return army, source

def npc_candidates(nid, now):
    st, w = npc_state(), world_state()
    pl = nation_planet(nid)
    caps = set(CAPITALS.values())
    mine = {int(p) for p, o in w["owners"].items() if int(o) == nid and int(p) // 100000 == pl}
    if not mine or nid not in CAPITALS:
        return []
    counts = {}
    for o in w["owners"].values():
        o = int(o)
        if o:
            counts[o] = counts.get(o, 0) + 1
    big = max(counts, key=counts.get) if counts else 0
    dcap = npc_dist_from(CAPITALS[nid])
    taken = {n["task"]["target"] for n in npc_all() if n["task"] and n["task"].get("kind") == "attack" and n["nation"] == nid}
    out = {}
    # user 2026-10-23 16:22: 4 NPCs appeared in a green province with no road to the rest of their land.  Targets only
    # next to provinces the NPCs can WALK to from the capital (own / allied land connected to it), not cut-off enclaves.
    conn = npc_home_land(nid)
    bridges = npc_bridges(nid, conn)
    army, source = npc_army_map(nid, now)
    for pid in mine & conn:
        for q in PORTAL_LINKS.get(pid % 100000, ()):
            qid = pl * 100000 + q
            if qid in mine or qid in caps or qid in out or qid in taken or qid in BATTLES or qid in RAIDS:
                continue
            o = province_owner(qid)
            if o and same_side(nid, o):
                continue
            if o and st["protect"].get(str(o), 0) > now:
                continue
            out[qid] = {"pid": qid, "owner": o, "kind": "enemy" if o else "alien",
                        "garrison": AL.garrison(w, qid) if not o else 0.0, "dist_cap": dcap.get(q, 3),
                        "def_power": npc_defence(qid), "owner_big": bool(o) and o == big and counts.get(o, 0) >= 6,
                        "owner_small": bool(o) and counts.get(o, 0) <= 2, "bridge": qid in bridges,
                        "army": army.get(qid, 0) if o else 0, "source": bool(o) and qid in source,
                        "retake": bool(o) and NPC_LOST.get(qid, (0, 0))[0] == nid
                                  and now - NPC_LOST.get(qid, (0, 0))[1] < NP.RETAKE_SECONDS}
    return list(out.values())

# ENCLAVES (user 2026-10-27 22:41, screenshot: a blue province cut off from the blue land by one enemy / alien
# province; "the blue NPCs should attack downward like a real player, so the land is not isolated"): a province that
# borders BOTH an own enclave (own land not connected to the capital) and the connected home land is a BRIDGE.  Taking
# (or holding) it joins the enclave again, so bridges come first: a big score bonus, allowed even when the nation's
# campaigns are capped, battles on them first; and NPCs standing in an enclave strike the bridge FROM the enclave (their
# road starts there, they enter through the gate facing the enclave).
NPC_BRIDGE_BONUS = 40.0         # score bonus of a bridge province (npc.score)
NPC_BRIDGE_MIN_WIN = 0.15       # lowest estimated win chance accepted for a bridge

def npc_enclaves(nid, conn=None):
    """own provinces of nid on its planet that its capital cannot reach through own / allied land."""
    conn = npc_home_land(nid) if conn is None else conn
    pl = nation_planet(nid)
    return {int(p) for p, o in world_state()["owners"].items()
            if int(o) == nid and int(p) // 100000 == pl and int(p) not in conn}

_ENCL_CACHE = {}

def npc_enclaves_cached(nid, now=None):
    k = (nid, int((now or time.time()) // 5))
    v = _ENCL_CACHE.get(k)
    if v is None:
        if len(_ENCL_CACHE) > 200:
            _ENCL_CACHE.clear()
        v = _ENCL_CACHE[k] = npc_enclaves(nid)
    return v

def npc_bridges(nid, conn=None):
    """provinces (not of nid's side) that border an own enclave AND the home land of nid."""
    conn = npc_home_land(nid) if conn is None else conn
    encl = npc_enclaves(nid, conn)
    if not encl:
        return set()
    pl = nation_planet(nid)
    out = set()
    for e in encl:
        for q in PORTAL_LINKS.get(e % 100000, ()):
            qid = pl * 100000 + q
            if qid in conn or qid in encl or same_side(province_owner(qid), nid):
                continue
            if any(pl * 100000 + r in conn for r in PORTAL_LINKS.get(q, ())):
                out.add(qid)
    return out

def npc_home_land(nid):
    """own / allied provinces the NPCs of nid can walk to from their capital (cut-off enclaves excluded)."""
    cap = CAPITALS.get(nid)
    if cap is None:
        return set()
    pl = cap // 100000
    conn, q_ = {cap}, [cap]
    while q_:
        x = q_.pop()
        for y in PORTAL_LINKS.get(x % 100000, ()):
            yid = pl * 100000 + y
            if yid not in conn and same_side(province_owner(yid), nid):
                conn.add(yid)
                q_.append(yid)
    return conn

def npc_front_ok(nid, pid):
    """an NPC of nid may attack / enter the battle in pid only if pid borders land of its side that is connected to
    its capital (user 2026-10-25 21:17: no attack where no province of its side is next to it).  Checked again on
    arrival - the road may have been cut while it marched."""
    pl = pid // 100000
    home = npc_home_land(nid)
    return any(pl * 100000 + q in home for q in PORTAL_LINKS.get(pid % 100000, ()))

# ---- roster size follows the players -------------------------------------------------------------------------------
def npc_update_stand(nid, now):
    st = npc_state()
    k = str(nid)
    owned = npc_owned(nid)
    st["peak"][k] = max(st["peak"].get(k, 0), owned)
    if st["stand"].get(k, 0) > now:
        return True
    # a nation that LOST ground (it once held at least 6 provinces) and is down to a few gets a short "last stand"
    if owned <= NP.LAST_STAND_PROVINCES and st["peak"].get(k, 0) >= 6 and now >= st["stand_cool"].get(k, 0):
        st["stand"][k] = now + NP.LAST_STAND_SECONDS
        st["stand_cool"][k] = now + NP.LAST_STAND_SECONDS + NP.LAST_STAND_COOLDOWN
        npc_dirty()
        raid_notify(nid, f"LAST STAND: your nation is down to {owned} province(s).  For {NP.LAST_STAND_SECONDS // 3600} hours "
                         f"your units have +{int((NP.LAST_STAND_HP - 1) * 100)}% HP and more commanders fight for you.",
                    (255, 220, 120))
        log(f"   NPC: nation {nid} LAST STAND ({owned} provinces, peak {st['peak'][k]})")
        return True
    return False

def npc_sync(nid, now):
    st = npc_state()
    alarm = npc_update_alarm(nid, now)
    mine = npc_ensure_roster(nid, NP.ALARM_ACTIVE if alarm else None)
    stand = npc_update_stand(nid, now)
    want = NP.want_active(npc_humans(nid), stand, alarm)
    for n in mine:
        n["alarm"] = alarm                          # NP.think_delay / choose / score read it
    active = [n for n in mine if n["state"] == "active"]
    k = str(nid)
    if len(active) > want:
        extra = len(active) - want
        idle = [n for n in active if not n["task"]]
        random.shuffle(idle)
        for n in idle[:extra]:
            n["state"] = "sleep"
            extra -= 1
        busy = [n for n in active if n["task"] and not n.get("retire")]
        random.shuffle(busy)
        for n in busy[:max(0, extra)]:
            n["retire"] = True                       # leaves when its task is over
        st["refill"].pop(k, None)
        npc_dirty()
    elif len(active) < want:
        for n in active:
            n["retire"] = False
        r = st["refill"].get(k)
        if k not in st["warm"]:
            r = now                                  # server start: the first NPCs of a nation appear at once
        if r is None:
            st["refill"][k] = now + random.uniform(*NP.REFILL_DELAY)
        elif now >= r:
            sleepers = [n for n in mine if n["state"] == "sleep"]
            random.shuffle(sleepers)
            first = k not in st["warm"]
            for n in sleepers[:want - len(active)]:
                n["state"] = "active"
                n["retire"] = False
                n["think_at"] = now + random.uniform(*(NPC_START_DELAY if first else (10, 600)))
            st["refill"].pop(k, None)
            st["warm"][k] = 1
            npc_dirty()
    else:
        st["refill"].pop(k, None)
        for n in active:
            n["retire"] = False

# ---- decisions -----------------------------------------------------------------------------------------------------
# Pace of conquest (user 2026-10-22 13:51: right after the start many provinces were taken at once).
# 2026-10-22 20:47 (user): NPCs more aggressive (waits were too long) WITH a brake against expanding too fast:
#   FAIR = the planet's provinces / its nations (about 20 on 85 provinces, 4 nations).
#   * pause after each conquest NPC_GAIN_GAP x (1 + NPC_GAP_GROWTH x (owned / FAIR)^2): 10-25 min while small,
#     about 40-100 min at a fair share, longer beyond;
#   * 2 campaigns at a time while the nation holds < FAIR / 2, then 1;
#   * no new conquest at all above NPC_MAX_SHARE x FAIR;
#   * attackers from a nation above its fair share fight at a penalty (defenders rally against the leader);
#   * the other nations prefer to attack the biggest one (npc_candidates owner_big), a nation that just lost land is
#     protected for a while, a nearly wiped-out nation gets LAST STAND (unchanged).
# CONQUEST MODE (user 2026-10-27 10:35: "NPC AI 要保持進攻狀態，目標佔領 81 個省"): every nation's NPCs keep attacking
# until the whole planet (all provinces but the capitals) is theirs - no size cap, no growing pause, no leader penalty.
# The previous brakes (2026-10-22/23) were NPC_GAIN_GAP (300, 900), NPC_GAP_GROWTH 2.0, NPC_MAX_SHARE 2.0,
# NPC_LEADER_PENALTY 0.5, 3/2 campaigns at a time.
NPC_GAIN_GAP = (60, 240)
NPC_GAP_GROWTH = 0.0
NPC_ALIEN_SHARE = 0.6
NPC_MAX_SHARE = 99.0
NPC_LEADER_PENALTY = 0.0         # attack power / (1 + this x (owned / FAIR - 1)) above the fair share
NPC_CAMPAIGNS = 10               # conquest targets of one nation under way at the same time (2026-10-31: was 6, 4)
NPC_START_DELAY = (120, 600)     # first decision of a nation's NPCs after a server start (was 30-120 min)

def npc_fair(nid):
    pl = nation_planet(nid)
    nats = sum(1 for n_, _nm, _c in NATIONS if nation_planet(n_) == pl) or 4
    return max(4.0, len(planet_provinces(pl)) / nats)

def npc_gain_gap(nid):
    share = npc_owned(nid) / npc_fair(nid)
    return random.uniform(*NPC_GAIN_GAP) * (1 + NPC_GAP_GROWTH * share * share)

def npc_attack_factor(nid):
    over = npc_owned(nid) / npc_fair(nid) - 1
    return 1.0 / (1 + NPC_LEADER_PENALTY * max(0.0, over))

NPC_ALARM_CAMPAIGNS = 14         # campaigns at the same time during a capital alarm (no pause after a conquest)

def npc_may_attack(nid, now):
    st = npc_state()
    alarm = npc_alarm(nid, now)
    if now < st["gain"].get(str(nid), 0) and not alarm:
        return False
    targets = {n["task"]["target"] for n in npc_of(nid) if n["task"] and n["task"].get("kind") == "attack"
               and not n["task"].get("hunt")}
    return len(targets) < (NPC_ALARM_CAMPAIGNS if alarm else NPC_CAMPAIGNS)

# HUNTS (user 2026-10-22 20:56: online NPCs should keep going into battle like active players).  While its nation must
# not conquer (pause after a conquest / too big / no target) an idle NPC goes HUNTING: it marches into a neighbouring
# alien province and fights the garrison like a siege (players may join), but a won hunt only thins the garrison -
# the province is NOT taken, so hunting never speeds up the expansion.
NPC_HUNT_CHANCE = 0.3          # per decision of an idle NPC that cannot conquer now (was 0.8; 2026-10-27 22:12 fewer hunts)
NPC_HUNT_MAX = 3               # hunts of one nation under way at the same time (2026-10-27 22:12: was 10 / 6)
NPC_HUNT_GARRISON = 0.6        # garrison x this after a won hunt (x 0.85 after a lost one)

def npc_hunt_target(nid, now):
    hunts = {n["task"]["target"] for n in npc_of(nid) if n["task"] and n["task"].get("hunt")}
    if len(hunts) >= NPC_HUNT_MAX:
        return None
    c = [x for x in npc_candidates(nid, now) if x["kind"] == "alien" and x["pid"] not in hunts]
    return random.choice(c) if c else None

def npc_targets(nid, now):
    cands = npc_candidates(nid, now)
    owned, fair = npc_owned(nid), npc_fair(nid)
    if owned >= NPC_MAX_SHARE * fair:
        # user 2026-10-23 20:50: a big nation sat idle in its capital.  Over the cap it still conquers, but one campaign
        # at a time, against nations only, and the pause after each conquest (npc_gain_gap) grows with its size
        if any(m["task"] and m["task"].get("kind") == "attack" and not m["task"].get("hunt") for m in npc_of(nid)):
            return []
        return [c for c in cands if c["kind"] == "enemy"]
    # no hard stop on alien land below NPC_MAX_SHARE (20:56: NPCs sat idle once they had 12 provinces and no enemy
    # border) - the growing pause after each conquest (npc_gain_gap) is the brake
    return cands

# PINCER (user 2026-10-31 10:16 "NPCs coordinate in the channel and support each other"): an NPC that marches on an
# enemy province asks in the ally channel for a pincer; idle comrades next to the target on OTHER sides answer and march in
# from there - each direction its own group (its own gate), all arriving together.
NPC_PINCER_CHANCE = 0.6
NPC_PINCER_MAX = 3              # extra directions

def npc_pincer(team, c, now):
    if c.get("kind") != "enemy" or random.random() >= NPC_PINCER_CHANCE:
        return []
    lead = team[0]
    nid, pid = lead["nation"], c["pid"]
    t = lead.get("task") or {}
    if t.get("target") != pid or t.get("kind") != "attack":
        return []
    pl = pid // 100000
    used = {(m.get("task") or {}).get("path", [None, None])[-2] for m in team if (m.get("task") or {}).get("path")}
    sides = [pl * 100000 + q for q in PORTAL_LINKS.get(pid % 100000, ())
             if province_owner(pl * 100000 + q) == nid and pl * 100000 + q not in used]
    random.shuffle(sides)
    idle = [m for m in _npc_idle_of(nid, now) if m not in team and NP.readiness(m) >= NP.MIN_READY
            and not m.get("retire")]
    picks = []
    st = npc_state()
    for side in sides:
        if len(picks) >= NPC_PINCER_MAX or not idle:
            break
        best = None
        for m in idle:
            here = npc_here(m, now) or CAPITALS.get(nid)
            pth = [here] if here == side else _route(here, side, lambda q: same_side(province_owner(q), nid))
            if pth and (best is None or len(pth) < len(best[1])):
                best = (m, pth)
        if not best:
            continue
        m, pth = best
        idle.remove(m)
        full = pth + [pid]
        gid = st["group"]
        st["group"] += 1
        m["task"] = {"kind": "attack", "target": pid, "origin": side, "depart": now,
                     "arrive": now + NP.march_seconds(max(1, len(full) - 1)), "phase": "march", "group": gid,
                     "since": now, "wait": 0, "from_owner": province_owner(pid), "path": full, "pincer": True}
        m.pop("walk", None)
        picks.append((m, side))
    if not picks:
        return []
    # everybody arrives together (the pincer groups a few seconds after the lead, so its battle is open)
    arrive = max([t["arrive"]] + [m["task"]["arrive"] for m, _s in picks])
    for m in team:
        if (m.get("task") or {}).get("target") == pid:
            m["task"]["arrive"] = arrive
    for k, (m, _s) in enumerate(picks):
        m["task"]["arrive"] = arrive + 3 + 2 * k
    npc_dirty()
    sides_txt = [s_ for _m, s_ in picks]
    def call(lang, _P=pid, _S=sides_txt, _o=t.get("origin")):
        lb, fr = province_label_lang(_P, lang), province_label_lang(_o, lang) if _o else "?"
        if lang in ("zh-cn", "zh-tw"):
            return (f"我从{fr}进攻{lb}，需要多路夹击！" if lang == "zh-cn" else f"我從{fr}進攻{lb}，需要多路夾擊！")
        return f"Attacking {lb} from {fr} - need a pincer!"
    npc_say(nid, lead, ("pincer", pid), call, now, gap=120, urgent=True)
    for m, side in picks:
        def ans(lang, _P=pid, _s=side):
            lb, fr = province_label_lang(_P, lang), province_label_lang(_s, lang)
            if lang in ("zh-cn", "zh-tw"):
                return (f"收到，我从{fr}夹击{lb}。" if lang == "zh-cn" else f"收到，我從{fr}夾擊{lb}。")
            return f"Copy - hitting {lb} from {fr}."
        npc_say(nid, m, ("pincer_ans", pid, m["id"]), ans, now, gap=120, urgent=True)
    log(f"   NPC: pincer on {pid} (nation {nid}): {lead['name']} from {t.get('origin')}, "
        + ", ".join(f"{m['name']} from {s_}" for m, s_ in picks) + f", all arrive in {arrive - now:.0f}s")
    return [m for m, _s in picks]

def npc_send(ns, cand, now, group=False):
    st = npc_state()
    nid = ns[0]["nation"]
    steps = max(1, int(cand["dist_cap"]))
    arrive = now + (max(NP.march_seconds(steps) for _ in ns) if group else NP.march_seconds(steps))
    pl = cand["pid"] // 100000
    origin = next((pl * 100000 + q for q in PORTAL_LINKS.get(cand["pid"] % 100000, ())
                   if province_owner(pl * 100000 + q) == nid), CAPITALS.get(nid))
    # (2026-10-23 15:09) the real road from where each NPC is: the group leaves together and arrives with the slowest
    paths, secs = {}, []
    for n in ns:
        pth, sec = npc_march_path(n, cand["pid"], now)
        if pth:
            paths[n["id"]] = pth
            secs.append(sec)
    if secs:
        arrive = now + max(secs)
    lost = [n["name"] for n in ns if n["id"] not in paths]
    ns = [n for n in ns if n["id"] in paths]          # (2026-10-23 16:22) no road -> it does not go (no jumping)
    if lost:
        log(f"   NPC: {lost} (nation {nid}) have no road to {cand['pid']} - stay")
    if not ns:
        return
    gid = None
    if group and len(ns) > 1:
        gid = st["group"]
        st["group"] += 1
    for n in ns:
        n["task"] = {"kind": "attack", "target": cand["pid"], "origin": origin, "depart": now, "arrive": arrive,
                     "phase": "march", "group": gid, "since": now, "wait": 0,
                     "from_owner": province_owner(cand["pid"])}      # who held it when the march began
        if n["id"] in paths:
            n["task"]["path"] = paths[n["id"]]
            n["task"]["origin"] = paths[n["id"]][-2] if len(paths[n["id"]]) >= 2 else origin
        n.pop("walk", None)
    npc_dirty()
    log(f"   NPC: {[n['name'] for n in ns]} (nation {nid}) march on {cand['pid']} ({cand['kind']}, power "
        f"{sum(NP.power_of(n) for n in ns):.0f} vs {cand['def_power']:.0f}), arrive in {arrive - now:.0f}s")
    if len(ns) > 1:
        raid_notify(nid, f"{len(ns)} commanders ({', '.join(n['name'] for n in ns[:3])}...) march on "
                         f"{province_label(cand['pid'])}.", (180, 220, 255))

NPC_RALLY_CHANCE = 0.8          # an NPC that looks for a target takes idle comrades along with this chance (was 0.6)
NPC_JOIN_FIGHTING = True        # idle NPCs also reinforce comrades already fighting at their target (2026-10-27 22:03)
NPC_RALLY_SIZE = (1, 4)
NPC_JOIN_CHANCE = 0.9           # idle NPC of a nation whose campaigns are capped joins a marching comrade with this chance
NPC_ALLY_HELP = 0.9            # share of NPC_REACT_CHANCE with which idle NPCs of ALLIED nations (same planet) help a defence

# SURFACE BATTLES FIRST (user 2026-10-27 22:12 "fewer hunts - if an NPC can join a surface battle, that comes first"):
# before anything else an idle NPC looks for a running battle on a surface province of its planet where its side
# fights - defending a province of its nation / allies (players there), or attacking with its nation's players or
# NPCs - and marches in (a 'defend' reinforcement, or an 'assist' attack that enters through a gate).  The side that
# needs help most (lowest strength ratio), then the nearest; at most NPC_SURFACE_JOIN_MAX NPCs per side and battle.
NPC_SURFACE_JOIN = 0.9          # chance per decision of an idle, healthy NPC
NPC_SURFACE_JOIN_MAX = 5        # NPCs of one side heading to / fighting in one battle through this rule

def npc_surface_battle(n, now):
    """(kind 'defend' | 'assist', province, battle) of the best surface battle n may join, or None."""
    nid = n["nation"]
    pl = nation_planet(nid)
    best = None
    for pid, B in list(BATTLES.items()):
        if (pid >= 100000000 or pid // 100000 != pl or (pid // 10000) % 10 or B.get("won") or B.get("sim")
                or B.get("ambush") or B.get("hunt") or B.get("npc_raid") or is_star_province(pid)):
            continue
        live = [o for o in B.get("members", ()) if not getattr(o, "spectator", False) and not o.w.is_closing()]
        dfd = B.get("defender") or province_owner(pid)
        if dfd and same_side(nid, dfd):
            if not live:
                continue                              # NPC-only defences have their own reinforcements
            kind, X = "defend", dfd
        else:
            sides = {B["npc_attacker"]} if B.get("npc_attacker") else set()
            sides |= {side_nation(o) for o in live if not dfd or not same_side(side_nation(o), dfd)}
            X = next((x for x in sides if same_side(nid, x)), None)
            if X is None or not npc_front_ok(nid, pid):
                continue
            if any(not ally_client_ok(o) for o in live if same_side(side_nation(o), X)):
                continue                              # old client: allied NPC units on its map crash it
            kind = "assist"
        going = sum(1 for m in npc_all() if m["task"] and m["task"].get("target") == pid and same_side(m["nation"], X)
                    and m["task"].get("kind") in ("attack", "defend", "support"))
        if going >= NPC_SURFACE_JOIN_MAX or (npc_battle_room(pid, X) or 0) <= 0:
            continue
        me_, them_ = side_strength(B, X)
        if them_ <= 0:
            continue
        ratio = me_ / max(1.0, them_)
        steps = len(npc_march_path(n, pid, now)[0] or ()) or 99
        key = (pid not in npc_bridges(nid), round(min(ratio, 3.0), 1), steps)   # (22:41) bridges to an enclave first
        if best is None or key < best[0]:
            best = (key, kind, pid, B, X)
    return best[1:] if best else None

def npc_join_surface(n, now, force=None):
    """send n to the best surface battle (npc_surface_battle; force = that choice).  True = it marches."""
    if force is None and (random.random() >= NPC_SURFACE_JOIN or NP.readiness(n) < NP.MIN_READY):
        return False
    j = force or npc_surface_battle(n, now)
    if not j:
        return False
    kind, pid, B, X = j
    nid = n["nation"]
    if kind == "defend":
        tk = npc_reinf_task("defend", nid, pid, now, n)
        if tk is None:
            return False
        n["task"] = tk
        n["task"]["slot"] = B.get("reinf", 0)
        B["reinf"] = B.get("reinf", 0) + 1
    else:
        npc_send([n], {"pid": pid, "owner": B.get("defender") or province_owner(pid), "kind": "assist", "garrison": 0,
                       "dist_cap": 1, "def_power": 0.0}, now)
        if not n.get("task"):
            return False
        as_reinforcement(n, now)
    eta = n["task"].get("arrive", now) - now
    _help_notice(B, X, n, eta)
    npc_dirty()
    log(f"   NPC: {n['name']} (nation {nid}) joins the surface battle on {pid} ({kind}, arrives in {eta:.0f}s)")
    return True

def npc_bridge_strike(n, now):
    """(22:41) a bridge next to an enclave: attacked first - from the enclave when the NPC stands in it."""
    nid = n["nation"]
    if NP.readiness(n) < NP.MIN_READY:
        return False
    cands = [c for c in npc_candidates(nid, now) if c.get("bridge")]
    if not cands:
        return False
    here = npc_here(n, now)
    near = [c for c in cands if any((c["pid"] // 100000) * 100000 + q == here for q in PORTAL_LINKS.get(c["pid"] % 100000, ()))]
    c = NP.choose(near or cands, n, NP.power_of(n))
    if not c:
        return False
    team = [n]
    free = [m for m in npc_of(nid) if m is not n and m["state"] == "active" and not m["task"] and now >= m["rest_until"]
            and not m.get("retire") and NP.readiness(m) >= NP.MIN_READY]
    team += random.sample(free, min(len(free), random.randint(1, 3)))
    npc_send(team, c, now, group=len(team) > 1)
    if n.get("task") and n["task"].get("target") == c["pid"]:
        log(f"   NPC: {n['name']} (nation {nid}) strikes the bridge {c['pid']} to its enclave"
            f"{' from the enclave' if here in npc_enclaves(nid) else ''} ({len(team)} commander(s))")
        return True
    return False

# (2026-10-31 10:10 "many NPCs just stand"): why an idle NPC did not leave, counted per nation and logged every 10 min
NPC_IDLE_WHY = {}
NPC_IDLE_LOG = [0.0]

def _idle(n, why):
    d = NPC_IDLE_WHY.setdefault(n["nation"], {})
    d[why] = d.get(why, 0) + 1

def npc_idle_report(now):
    if now - NPC_IDLE_LOG[0] < 600:
        return
    NPC_IDLE_LOG[0] = now
    for nid in sorted(set(NPC_IDLE_WHY) | set(NPC_FALLBACK)):
        d = NPC_IDLE_WHY.get(nid, {})
        act = [n for n in npc_of(nid) if n["state"] == "active"]
        busy = sum(1 for n in act if n["task"])
        fb = NPC_FALLBACK.get(nid, {})
        log(f"   NPC idle report nation {nid}: {len(act)} active, {busy} on a task, idle decisions "
            + ", ".join(f"{k} {v}" for k, v in sorted(d.items(), key=lambda kv: -kv[1]))
            + f"; no-target fallback join {fb.get('join', 0)}, front {fb.get('front', 0)}")
    NPC_IDLE_WHY.clear()
    NPC_FALLBACK.clear()

def npc_follow(n, m, now):
    """n marches (its own road) to the attack of comrade m and joins m's group.  True = it goes."""
    room = npc_battle_room(m["task"]["target"], n["nation"])
    if room is not None and room <= 0:           # (10-31) the battle there is full: do not march over to watch
        return False
    st = npc_state()
    gid = m["task"].get("group")
    if gid is None:
        gid = st["group"]
        st["group"] += 1
        m["task"]["group"] = gid
    pth, sec = npc_march_path(n, m["task"]["target"], now)
    if not pth:                                  # its own road from where it is (2026-10-23 16:22: no jumping)
        return False
    n["task"] = dict(m["task"], since=now, wait=0, depart=now, path=pth, phase="march",
                     arrive=max(m["task"]["arrive"], now + sec) if m["task"].get("phase") == "march" else now + sec,
                     origin=pth[-2] if len(pth) >= 2 else m["task"].get("origin"))
    n.pop("walk", None)
    log(f"   NPC: {n['name']} follows {m['name']} to {m['task']['target']}")
    return True

# NO TARGET (user 2026-10-31 11:21 "loosen no_target"): every free province next to the land already has a campaign of
# the nation (or a battle, or truce).  Instead of standing at home the NPC 1) joins the nearest running attack of a
# comrade that is not full yet, else 2) moves up to a border province (a front post, patrol rules) and strikes from there.
NPC_NT_JOIN_MAX = 8             # NPCs of one nation in one attack (counting the leader) before it is full
NPC_NT_STAGE = 0.8              # chance to move up to the front when there is no attack to join
NPC_STAGE_MAX = 10              # border posts of one nation at the same time through this rule (patrols included)
NPC_FALLBACK = {}

def npc_no_target(n, now):
    nid = n["nation"]
    d = NPC_FALLBACK.setdefault(nid, {})
    by = {}
    for m in npc_of(nid):
        t = m.get("task")
        if m is n or not t or t.get("kind") != "attack" or t.get("hunt"):
            continue
        if t.get("phase") == "march" and t.get("arrive", 0) > now + 8:
            by.setdefault(t["target"], []).append(m)
        elif NPC_JOIN_FIGHTING and t.get("phase") in ("siege", "raid", "battle"):
            by.setdefault(t["target"], []).append(m)
    opts = [(pid, ms) for pid, ms in by.items() if len(ms) < NPC_NT_JOIN_MAX and npc_front_ok(nid, pid)
            and (npc_battle_room(pid, nid) is None or npc_battle_room(pid, nid) > 0)]
    random.shuffle(opts)
    best = None
    for pid, ms in opts[:4]:
        pth, sec = npc_march_path(n, pid, now)
        if pth and (best is None or sec < best[0]):
            best = (sec, ms)
    if best and npc_follow(n, random.choice(best[1]), now):
        d["join"] = d.get("join", 0) + 1
        return True
    if random.random() < NPC_NT_STAGE and npc_patrol(n, now, cap=NPC_STAGE_MAX):
        d["front"] = d.get("front", 0) + 1
        return True
    return False

def npc_think(n, now):
    n.setdefault("idle_since", now)
    n["bored"] = not n.get("task") and now - n.get("idle_since", now) > NP.BORED_SECONDS
    n["think_at"] = now + NP.think_delay(n)
    nid = n["nation"]
    if npc_join_surface(n, now):                 # (22:12) a running surface battle of its side comes first
        return
    if npc_bridge_strike(n, now):                # (22:41) reconnect a cut-off enclave
        return
    p = NP.PERSONAS[n["persona"]]
    fchance = p["follow"] if npc_may_attack(nid, now) else max(p["follow"], NPC_JOIN_CHANCE)   # campaigns capped: help a comrade instead
    if fchance and random.random() < fchance:
        # (user 2026-10-27 22:03 "NPCs patrol but hardly attack") also comrades already FIGHTING at their target
        # (siege / battle): the follower marches there and enters the running battle (npc_begin -> npc_join_attack)
        mates = [m for m in npc_of(nid) if m is not n and m["state"] == "active" and m["task"]
                 and m["task"].get("kind") == "attack" and not m["task"].get("hunt")
                 and ((m["task"].get("phase") == "march" and m["task"]["arrive"] > now + 8)
                      or (NPC_JOIN_FIGHTING and m["task"].get("phase") in ("siege", "raid", "battle")))]
        if mates and npc_follow(n, random.choice(mates), now):
            return
    if NP.readiness(n) < NP.MIN_READY:           # wounded: stay home until the units are healthy again
        _idle(n, "wounded")
        return
    may = npc_may_attack(nid, now)
    cands = npc_targets(nid, now) if may else []
    team = [n]
    if cands and (n.get("alarm") or random.random() < NPC_RALLY_CHANCE):   # RALLY: take idle comrades along, their power adds up
        free = [m for m in npc_of(nid) if m is not n and m["state"] == "active" and not m["task"] and now >= m["rest_until"]
                and not m.get("retire") and NP.readiness(m) >= NP.MIN_READY]
        if free:
            team += random.sample(free, min(len(free), random.randint(*NPC_RALLY_SIZE)))
    c = NP.choose(cands, n, sum(NP.power_of(m) for m in team)) if cands else None
    if cands and not c:                                      # (10-31) too weak alone: try once with every idle comrade
        free = [m for m in npc_of(nid) if m is not n and m not in team and m["state"] == "active" and not m["task"]
                and now >= m["rest_until"] and not m.get("retire") and NP.readiness(m) >= NP.MIN_READY]
        if free:
            team += random.sample(free, min(len(free), 6))
            c = NP.choose(cands, n, sum(NP.power_of(m) for m in team))
    if not c and may and not cands and npc_no_target(n, now):   # (11:21) nothing free to conquer: help or move up
        return
    if not c:
        _idle(n, "campaign_cap_or_pause" if not may else "no_target" if not cands else "odds_low")
    if not c and random.random() < NPC_HUNT_CHANCE:
        h = npc_hunt_target(nid, now)
        if h:
            npc_send([n], h, now)
            if n.get("task"):                     # (no road there: npc_send gives no task)
                n["task"]["hunt"] = True
                log(f"   NPC: {n['name']} goes hunting in {h['pid']}")
                return
    if c:
        npc_send(team, c, now, group=len(team) > 1)
        if len(team) > 1:
            log(f"   NPC: {n['name']} rallies {len(team) - 1} comrade(s) for {c['pid']}")
        try:
            npc_pincer(team, c, now)                   # (10-31) other directions join in through the ally channel
        except Exception as e:
            log(f"   NPC pincer error: {e!r}")
    elif random.random() < NPC_PATROL_CHANCE and npc_patrol(n, now):
        return
    else:
        log(f"   NPC: {n['name']} ({n['persona']}) stays home") if random.random() < 0.05 else None

# BORDER PATROL (user 2026-10-23 20:50: the NPCs of a big nation never moved).  An idle NPC walks (province by
# province) to a province of its nation that borders an enemy, guards it for a while, then walks home.  It is drawn
# there on the strategic map, and when that province is attacked it is the first to enter the battle (present).
# (user 2026-10-27 22:03 "NPCs patrol but hardly attack"): patrols are only the last resort of an idle NPC - fewer,
# shorter, and a patrol that sees a possible conquest from its border post leaves to attack (npc_patrol_strike)
NPC_PATROL_CHANCE = 0.1        # was 0.2, 0.5 (2026-10-31: attacks first)
NPC_PATROL_MAX = 3             # patrols of one nation at the same time (was 6)
NPC_PATROL_STAY = (240, 600)   # s on station (was 600-1500)

def npc_patrol(n, now, cap=None):
    nid = n["nation"]
    pl = nation_planet(nid)
    busy = {m["task"]["target"] for m in npc_of(nid) if m["task"] and m["task"].get("kind") == "patrol"}
    if len(busy) >= (cap or NPC_PATROL_MAX):
        return False
    w = world_state()
    border = []
    for k, o in w["owners"].items():
        pid = int(k)
        if int(o) != nid or pid // 100000 != pl or pid in busy or pid in BATTLES or pid in set(CAPITALS.values()):
            continue
        if any(province_owner(pl * 100000 + q) and not same_side(province_owner(pl * 100000 + q), nid)
               for q in PORTAL_LINKS.get(pid % 100000, ())):
            border.append(pid)
    random.shuffle(border)
    for pid in border[:6]:
        pth, sec = npc_march_path(n, pid, now)
        if not pth:
            continue
        n["task"] = {"kind": "patrol", "target": pid, "origin": pth[-2] if len(pth) >= 2 else pid, "depart": now,
                     "arrive": now + sec, "phase": "march", "since": now, "path": pth,
                     "until": now + sec + random.uniform(*NPC_PATROL_STAY)}
        n.pop("walk", None)
        npc_dirty()
        log(f"   NPC: {n['name']} (nation {nid}) patrols the border at {pid} (arrives in {sec:.0f}s)")
        return True
    return False

NPC_PATROL_STRIKE = 0.12       # per NPC tick (10 s): a patrol looks for a conquest next to its post

def npc_patrol_strike(n, now):
    """a border patrol that sees a province it may attack next to its post goes for it (2026-10-27 22:03)."""
    if random.random() >= NPC_PATROL_STRIKE or NP.readiness(n) < NP.MIN_READY:
        return False
    nid, post = n["nation"], n["task"]["target"]
    if not npc_may_attack(nid, now):
        return False
    near = {(post // 100000) * 100000 + q for q in PORTAL_LINKS.get(post % 100000, ())}
    cands = [c for c in npc_targets(nid, now) if c["pid"] in near]
    c = NP.choose(cands, n, NP.power_of(n)) if cands else None
    if not c:
        return False
    npc_send([n], c, now)
    if n.get("task") and n["task"].get("kind") == "attack":
        log(f"   NPC: {n['name']} (nation {nid}) leaves its patrol at {post} to attack {c['pid']}")
        return True
    return False

def npc_sortie(nid, active, now):
    st = npc_state()
    k = str(nid)
    due = st["sortie"].get(k)
    if due is None:
        st["sortie"][k] = now + random.uniform(*NP.SORTIE_EVERY)
        return
    if now < due:
        return
    st["sortie"][k] = now + random.uniform(*NP.SORTIE_EVERY)
    free = [n for n in active if not n["task"] and now >= n["rest_until"] and not n.get("retire")
            and NP.readiness(n) >= NP.MIN_READY]
    if len(free) < NP.SORTIE_SIZE[0] or not npc_may_attack(nid, now):
        return
    team = random.sample(free, min(len(free), random.randint(*NP.SORTIE_SIZE)))
    att = sum(NP.power_of(n) for n in team)
    c = NP.choose(npc_targets(nid, now), {"persona": "warlike"}, att)
    if c:
        npc_send(team, c, now, group=True)

# ---- tasks ----------------------------------------------------------------------------------------------------------
NPC_FALLBACK_NEAREST = True     # (23:27) after losing a province: to the nearest province of its side, not the capital

def npc_fallback_province(nid, here):
    """nearest province of nid's side next to `here` (own land connected to the capital first), else None."""
    pl = here // 100000
    nb = [pl * 100000 + q for q in PORTAL_LINKS.get(here % 100000, ())]
    mine = [q for q in nb if province_owner(q) and same_side(province_owner(q), nid)]
    if not mine:
        return None
    home = npc_home_land(nid)
    cap = CAPITALS.get(nid)
    dcap = npc_dist_from(cap) if cap else {}
    return min(mine, key=lambda q: (q not in home, dcap.get(q % 100000, 99)))

def npc_damaged(n):
    """(user 2026-10-31 10:13) units hurt: home to the capital's factory instead of a post next door."""
    return any(h < NP.REPAIR_BELOW for h in NP.health(n))

def npc_factory_repair(n, now):
    """an idle NPC standing in its capital (not walking) gets every unit repaired at once (no HEAL_SECONDS wait)."""
    if n.get("task") or n.get("post"):
        return False
    w = n.get("walk")
    if w and now < w.get("arrive", 0):
        return False
    hl = NP.health(n)
    if all(h >= 1.0 for h in hl):
        return False
    if npc_location(n, now)[0] != CAPITALS.get(n["nation"]):
        return False
    lost = sum(1 for h in hl if h < 1.0)
    for i in range(len(hl)):
        hl[i] = 1.0
    n["heal_t"] = now
    npc_dirty()
    log(f"   NPC: {n['name']} (nation {n['nation']}) repaired {lost} unit(s) at the capital's factory")
    return True

def npc_release(n, now, rest, won=None):
    try:
        here = npc_here(n, now) if n.get("task") else None
        n.pop("post", None)
        n.pop("post_kind", None)
        cap = CAPITALS.get(n["nation"])
        if here and here in npc_enclaves(n["nation"]) and npc_bridges(n["nation"]):
            # (22:41) task over inside a cut-off enclave: it stays there and strikes the bridge from it (npc_think)
            n["post"] = here
            rest = min(rest, 60)
            log(f"   NPC: {n['name']} (nation {n['nation']}) stays in the enclave {here} to reopen the road home")
            here = None                                # no walk home
        elif (here and NPC_FALLBACK_NEAREST and province_owner(here) and not npc_damaged(n)
              and not same_side(province_owner(here), n["nation"])):
            # (user 2026-10-27 23:27 "when an NPC's own province is taken, the battle should send it back to the NEAREST
            # province"): out of the lost / enemy province into the nearest province of its side next door (one held
            # from the capital first) - it stays there (post) instead of walking all the way to the capital
            fb = npc_fallback_province(n["nation"], here)
            if fb is not None:
                n["post"], n["post_kind"] = fb, "fallback"
                n["walk"] = {"path": [here, fb], "depart": now, "arrive": now + NP.march_seconds(1) * 0.5}
                log(f"   NPC: {n['name']} (nation {n['nation']}) falls back from {here} to the nearest province {fb}")
                here = None
        if n.get("post_kind") == "fallback":
            pass                                       # keeps its one-step walk to the fallback province
        elif here and cap and here != cap:
            # (22:56 "red NPCs standing in a green province"): no walk home THROUGH enemy land - without a road over own /
            # allied provinces it goes straight back (was: any road, drawn province by province in enemy land)
            path = _route(here, cap, lambda q: same_side(province_owner(q), n["nation"])) or [here, cap]
            if len(path) >= 2 and province_owner(here) and not same_side(province_owner(here), n["nation"]):
                path = path[1:]           # (21:47) out of another nation's province at once, then walk on from next door
                # user 2026-10-25 14:32: no neighbouring province of its own / allied / unowned land to fall back to
                # -> straight back to the capital (no walk through enemy land)
                try:
                    _pl, _h = here // 100000, here % 100000
                    _nb = [q for q in (_pl * 100000 + x for x in PORTAL_LINKS.get(_h, ()))
                           if not province_owner(q) or same_side(province_owner(q), n["nation"])]
                    if not _nb:
                        path = [cap]
                except Exception:
                    pass
            if len(path) >= 2:            # (18:55) next door = the capital itself: no walk, it is home at once
                n["walk"] = {"path": path, "depart": now, "arrive": now + NP.march_seconds(max(1, len(path) - 1))}
            else:
                n.pop("walk", None)
        else:
            n.pop("walk", None)
    except Exception:
        n.pop("walk", None)
    n["task"] = None
    n["rest_until"] = now + rest
    if won is True:
        n["wins"] = n.get("wins", 0) + 1
        n["honor"] = n.get("honor", 0) + 1000
    elif won is False:
        n["losses"] = n.get("losses", 0) + 1
    if n.get("retire"):
        n["state"], n["retire"] = "sleep", False
    NPC_RT.pop(n["id"], None)
    npc_dirty()

def npc_finish(ns, won, now, battle=False):
    """won: True / False / None (cancelled).  Applies the result of an assault."""
    t = ns[0]["task"]
    pid, nid = t["target"], ns[0]["nation"]
    r = RAIDS.get(pid)
    if r and r.get("npc") == nid:
        RAIDS.pop(pid, None)
    if won is None:
        for n in ns:
            npc_release(n, now, random.uniform(60, 300))
        log(f"   NPC: assault on {pid} cancelled")
        return
    owner = province_owner(pid)
    if won and owner and owner != nid and same_side(owner, nid):
        won = None                       # (22:37) the owner became an ally meanwhile: the assault is called off
        for n in ns:
            npc_release(n, now, random.uniform(60, 300))
        log(f"   NPC: assault on {pid} called off - nation {nid} and the owner {owner} are allies now")
        return
    names = ", ".join(n["name"] for n in ns[:3]) + ("..." if len(ns) > 3 else "")
    if t.get("hunt"):                                     # a hunt never takes the province
        if not battle:
            w = world_state()
            AL.set_garrison(w, pid, AL.garrison(w, pid) * (NPC_HUNT_GARRISON if won else 0.85))
            save_world(w)
        log(f"   NPC: {names} {'won' if won else 'lost'} a hunt in {pid}")
        for n in ns:
            npc_release(n, now, NP.rest_seconds(bool(won)) / 3, bool(won))
        return
    if won:
        npc_state()["gain"][str(nid)] = now + npc_gain_gap(nid)
        if not battle and owner != nid:
            capture_province(pid, nid)
        raid_notify(nid, f"{names} captured {province_label(pid)}!", (120, 255, 120))
        try:
            def _won(lang, _p=pid, _o=owner, _fo=t.get("from_owner")):
                lb = province_label_lang(_p, lang)
                # (user 2026-10-26 20:51) "from whom" = the nation that held the province BEFORE the assault, never our own
                # nation (a battle may already have flipped the owner when we get here): recorded when the march began
                fo = _fo if _fo is not None else _o
                if fo == nid:                           # already ours: nothing to say about "from"
                    return {"zh-cn": f"拿下{lb}了！", "zh-tw": f"拿下{lb}了！"}.get(lang, f"{lb} is ours!")
                on = _owner_name(fo, lang)
                return {"zh-cn": f"拿下{lb}了！（从{on}手中）", "zh-tw": f"拿下{lb}了！（從{on}手中）"}.get(lang, f"{lb} is ours (taken from {on})!")
            npc_say(nid, ns[0], ("won", pid), _won, now, gap=600)
        except Exception:
            pass
        if owner and owner != nid:
            raid_notify(owner, f"{province_label(pid)} was taken by {names} of nation {nid}.", (255, 120, 120))
        log(f"   NPC: {names} took {pid} from {owner or 'the aliens'}")
    else:
        if not owner:
            w = world_state()
            AL.set_garrison(w, pid, AL.garrison(w, pid) * 0.75)
            save_world(w)
        log(f"   NPC: {names} failed to take {pid}")
    for n in ns:
        npc_release(n, now, NP.rest_seconds(bool(won)), bool(won))

def npc_resolve(ns, now):
    t = ns[0]["task"]
    att = sum(NP.power_of(n) for n in ns) * (NP.LAST_STAND_HP if npc_stand(ns[0]["nation"]) else 1.0)
    att *= npc_attack_factor(ns[0]["nation"])            # the leader fights at a penalty
    dfn = npc_defence(t["target"])
    won, a, d = NP.resolve(att, dfn)
    log(f"   NPC: abstract battle on {t['target']}: attackers {a:.0f} vs defence {d:.0f} -> {'WON' if won else 'lost'}")
    npc_finish(ns, won, now)

NPC_JOIN_SIDE_MAX = 12       # NPC commanders of ONE side that fight in one battle at the same time (10-31: was 8;
                             # the side's units stay capped by NPC_SIDE_UNITS - more commanders field fewer platoons)
NPC_JOIN_RETRY = 20          # s between tries when the battle is full (a slot frees when a commander's units are gone)
NPC_JOIN_TRIES = 0           # (user 10-31 12:36 "full: open another battlefield, no waiting") was 9 = 3 min outside

def npc_battle_room(pid, nid):
    """(user 2026-10-31 11:48 "the NPCs only watch from outside" - 215 'battle is full' waits): free commander slots
    of nid's side in the battle on pid: NPC_JOIN_SIDE_MAX minus the side's commanders with units on the map and the
    ones of the side already marching there.  None when there is no battle on pid."""
    B = BATTLES.get(pid)
    if B is None:
        return None
    live = {tg.get("npc") for tg in (B.get("targets") or {}).values()
            if tg.get("npc") is not None and tg.get("hp", 1) > 0 and tg.get("nation") is not None
            and same_side(tg["nation"], nid)}
    going = {m["id"] for m in npc_all() if m.get("task") and m["task"].get("target") == pid
             and m["task"].get("phase") == "march" and same_side(m["nation"], nid)} - live
    return NPC_JOIN_SIDE_MAX - len(live) - len(going)

def npc_join_check(B, nid):
    """None = an NPC force of nation nid may enter the running battle B now, else why not:
    'over' / 'ambush' / 'own side' / 'client' (permanent) or 'full' (try again later).
    user 2026-10-24 05:58: allied NPCs answered "on my way" and then stood in the next province - every NPC commander
    ever put on the map (the enemy defenders too, dead or alive) counted toward one cap of 8.  Now only commanders of
    the joining side that still have units count."""
    own = B.get("owner")
    if own is None or B.get("won") or own.w.is_closing():
        return "over"
    if B.get("ambush"):
        return "ambush"
    d = B.get("defender") or province_owner(B["map"])
    if d and same_side(nid, d):
        return "own side"
    if npc_side_blocked(own, nid):
        return "client"              # a player of that side runs a client that crashes on NPC allies
    live = {tg.get("npc") for tg in (B.get("targets") or {}).values()
            if tg.get("npc") is not None and tg.get("hp", 1) > 0 and tg.get("nation") is not None
            and same_side(tg["nation"], nid)}
    if len(live) >= NPC_JOIN_SIDE_MAX:
        return "full"
    return None

def npc_join_attack(ns, B, now):
    """an attacking NPC force reaches a province where a battle is already running (players, other NPCs, aliens): its
    squads enter the map at a GATE and fight (assault) instead of waiting outside and going home.
    -> None when it entered, else the reason (npc_join_check)."""
    pid, nid = B["map"], ns[0]["nation"]
    why = npc_join_check(B, nid)
    if why:
        return why
    own = B["owner"]
    budget = npc_budget(0)
    _pth = (ns[0].get("task") or {}).get("path") or []
    starts = gate_starts(pid, len(ns), nid, frm=_pth[-2] if len(_pth) >= 2 else None)   # the gate of its road
    _t, _d, _c, mapname = alien_context(own, pid)
    homes = spawn_homes(mapname, (0x400, 0x400), len(ns))
    for n in ns:
        NPC_RT.pop(n["id"], None)                # (06:16) only what npc_spawn really puts on the map counts
    npc_spawn(own, pid, nid, ns, budget, homes, "assault", 0, 0, True, keep_meta=True, starts=starts)
    placed = [n for n in ns if NPC_RT.get(n["id"], {}).get("units", 0) > 0]
    if not placed:
        return "no units"
    for n in ns:
        if n not in placed:                      # no room / no fit unit for it: it does not stand there doing nothing
            log(f"   NPC: {n['name']} (nation {nid}) got no unit onto {pid} - goes home")
            npc_release(n, now, random.uniform(60, 200))
    for n in placed:
        n["task"].update(phase="battle", since=now, entered=now)
        npc_rt_attach(n["id"], B, nid)
        B.setdefault("npc_ids", []).append(n["id"])
    spawn(npc_ai(own, getattr(own, "battle_gen", 0) or 0))
    log(f"   NPC: {[n['name'] for n in placed][:3]} (nation {nid}) enter the running battle on {pid} through a gate")
    npc_dirty()
    return None

def npc_full_redirect(ns, pid, now):
    """(user 2026-10-31 12:36 "when it is full, open another battlefield - do not wait") the force that found the battle
    on pid full attacks another province at once (the best target from its own road; a pincer may join), else each
    NPC decides again right away (comrade's attack with room, a front post ...)."""
    nid = ns[0]["nation"]
    for n in ns:
        npc_release(n, now, 0)
        n["rest_until"] = now
    cands = [c for c in (npc_targets(nid, now) if npc_may_attack(nid, now) else []) if c["pid"] != pid]
    team = [n for n in ns if NP.readiness(n) >= NP.MIN_READY]
    c = NP.choose(cands, team[0], sum(NP.power_of(m) for m in team)) if cands and team else None
    if c:
        npc_send(team, c, now, group=len(team) > 1)
        if team[0].get("task") and team[0]["task"].get("target") == c["pid"]:
            log(f"   NPC: {[n['name'] for n in team][:3]} (nation {nid}) - {pid} is full, they open another front on {c['pid']}")
            try:
                npc_pincer(team, c, now)
            except Exception as e:
                log(f"   NPC pincer error: {e!r}")
            return
    for n in ns:
        if not n.get("task"):
            n["think_at"] = now
            npc_think(n, now)

def npc_begin(ns, now):
    t = ns[0]["task"]
    nid, pid = ns[0]["nation"], t["target"]
    owner = province_owner(pid)
    if owner and same_side(nid, owner):
        npc_finish(ns, None, now)
        return
    if not npc_front_ok(nid, pid):
        log(f"   NPC: {[n['name'] for n in ns][:3]} (nation {nid}) reach {pid} but no province of their side borders "
            f"it any more (road cut) - no attack, go home")
        for n in ns:
            if n["task"].get("assist"):
                _assist_gave_up(n, pid, "road", now)
        npc_finish(ns, None, now)
        return
    if pid in BATTLES:
        why = npc_join_attack(ns, BATTLES[pid], now)
        if why is None:
            return                 # the squad came through the gate INTO the running battle (user 2026-10-23 11:45)
        t["wait"] = t.get("wait", 0) + 1
        if why == "full" and t["wait"] <= NPC_JOIN_TRIES:
            for n in ns:
                n["task"]["arrive"] = now + NPC_JOIN_RETRY
            if t["wait"] == 1:
                log(f"   NPC: {[n['name'] for n in ns][:3]} (nation {nid}) wait at {pid}: the battle is full")
            return
        log(f"   NPC: {[n['name'] for n in ns][:3]} (nation {nid}) cannot enter the battle on {pid} ({why}) - "
            f"{'looks for another task' if why == 'full' else 'go home'}")
        for n in ns:
            if n["task"].get("assist"):
                _assist_gave_up(n, pid, why, now)
        if why == "full":                         # (10-31 12:36) no waiting: at once another front from where they stand
            npc_full_redirect(ns, pid, now)
            return
        npc_finish(ns, None, now)
        return
    if pid in RAIDS:
        t["wait"] = t.get("wait", 0) + 1
        if t["wait"] > 4:
            npc_finish(ns, None, now)
        else:
            t["arrive"] = now + 150
        return
    if NPC_GHOST_BATTLES:
        if _OPEN_BUDGET[0] <= 0:                  # enough battles opened in this tick: a few seconds later
            for n in ns:
                n["task"]["arrive"] = now + random.uniform(3, 9)
            return
        _OPEN_BUDGET[0] -= 1
        if npc_open_battle(pid, ns, now):
            if owner and npc_humans(owner) > 0:
                _notify_side(owner, f"第 {nid} 国的 {', '.join(NP.disp(n['name'], 'zh-cn') for n in ns[:3])} 正在进攻 {province_label(pid)}！进入该省防守（战斗最长 30 分钟）。",
                             f"第 {nid} 國的 {', '.join(NP.disp(n['name'], 'zh-tw') for n in ns[:3])} 正在進攻 {province_label(pid)}！進入該省防守（戰鬥最長 30 分鐘）。",
                             f"Commanders of nation {nid} ({', '.join(n['name'] for n in ns[:3])}) are attacking "
                             f"{province_label(pid)}! Enter it to defend (the battle lasts up to 30 minutes).", (255, 120, 120))
        else:
            npc_finish(ns, None, now)
        return
    if owner and npc_humans(owner) > 0:
        RAIDS[pid] = {"nation": owner, "until": now + AL.RAID_DEFEND_SECONDS, "from": t.get("origin"), "npc": nid,
                      "force": [n["id"] for n in ns]}
        for n in ns:
            n["task"].update(phase="raid", until=now + AL.RAID_DEFEND_SECONDS, entered=now)
        raid_notify(owner, f"Commanders of nation {nid} ({', '.join(n['name'] for n in ns[:3])}) are attacking "
                           f"{province_label(pid)}!  Defend it within {AL.RAID_DEFEND_SECONDS // 60} minutes or it is lost.")
        log(f"   NPC: RAID on {pid} (nation {owner}) by {[n['name'] for n in ns]}")
    else:
        for n in ns:
            n["task"].update(phase="siege", resolve_at=now + random.uniform(*NP.SIEGE), wait=0, entered=now)

def npc_force_step(ns, now):
    t = ns[0]["task"]
    pid, ph = t["target"], t.get("phase")
    if ph == "march":
        if now >= t["arrive"]:
            npc_begin(ns, now)
    elif ph == "raid":
        if now >= t["until"]:
            if pid in BATTLES:
                t["until"] = now + 60
                return
            RAIDS.pop(pid, None)
            npc_resolve(ns, now)
    elif ph == "siege":
        if now >= t["resolve_at"]:
            if pid in BATTLES:
                t["wait"] = t.get("wait", 0) + 1
                t["resolve_at"] = now + 120
                if t["wait"] > 4:
                    npc_finish(ns, None, now)
                return
            npc_resolve(ns, now)
    elif ph == "battle":
        B = NPC_RT.get(ns[0]["id"], {}).get("B")
        if B is not None and BATTLES.get(pid) is B:
            return
        res = NPC_RESULT.pop(pid, None)
        won = res if res is not None else (province_owner(pid) == ns[0]["nation"])
        npc_finish(ns, won, now, battle=True)

def npc_defend_step(n, now):
    t = n["task"]
    rt = NPC_RT.get(n["id"], {})
    B = rt.get("B")
    if (B is None and now - t.get("since", now) > 120) or (B is not None and BATTLES.get(t["target"]) is not B):
        dead = rt.get("dead", 0) / max(1, rt.get("units", 1))
        won = province_owner(t["target"]) == n["nation"]
        npc_release(n, now, NP.rest_seconds(dead < 0.5 and won), won)
        log(f"   NPC: {n['name']} finished defending {t['target']} ({'held' if won else 'lost'}, {dead:.0%} lost)")

NPC_SUPPORT_MAX = 3         # NPC squads that answer an attack on one province of their nation (abstract battle)
NPC_REACT_CHANCE = 0.7      # per tick (10 s) and attacked province: chance that one more idle NPC sorties (was 0.25;
                            # 11-02 "NPC 不打": defenders come, so the armies really meet)
NPC_RECALL_STEPS = 2        # (11-02) no idle defender: a squad of the nation marching on another target within this many
                            # provinces of the attacked one turns back to defend it
NPC_RECALL_GAP = 90         # s between two such recalls of one nation
NPC_REINFORCE_MAX = 2       # extra NPC squads that join a running battle in a province of their nation (+3 at the capital)

def _npc_idle_of(nid, now):
    return [n for n in npc_of(nid) if n["state"] == "active" and not n["task"] and now >= n["rest_until"]
            and not n.get("retire") and NP.readiness(n) >= 0.3]

def npc_react(now):
    """an attack on a province of an NPC nation (hostile NPCs, or a player in a battle there) makes its idle NPCs sortie
    at random moments - the 'land grab' cool-down does not apply (user 2026-10-22 13:59)."""
    st = npc_state()
    attacked = {}
    for n in npc_all():
        tk = n["task"]
        if tk and tk.get("kind") == "attack" and tk.get("phase") in ("march", "siege", "raid", "battle"):
            owner = province_owner(tk["target"])
            if owner and not same_side(owner, n["nation"]) and (tk["target"] not in BATTLES
                                                                 or BATTLES[tk["target"]].get("npc_attacker") == n["nation"]):
                attacked[tk["target"]] = owner
    for pid, owner in attacked.items():
        have = [n for n in npc_of(owner) if n["task"] and n["task"].get("kind") == "support" and n["task"].get("target") == pid]
        if len(have) >= NPC_SUPPORT_MAX or random.random() > NPC_REACT_CHANCE:
            continue
        idle = _npc_idle_of(owner, now)
        if not idle and random.random() < NPC_ALLY_HELP:      # allied nations on the same planet come to help
            idle = [m for (a_, b_) in NATION_ALLIES for m in _npc_idle_of(b_ if a_ == owner else a_, now)
                    if owner in (a_, b_) and nation_planet(m["nation"]) == pid // 100000]
        recalled = False
        rk = st.setdefault("recall_at", {})
        if not idle and now >= rk.get(str(owner), 0):  # (11-02) everybody is out: the nearest marching squad turns back
            best = None
            for m in npc_of(owner):
                t_ = m.get("task")
                if (m["state"] != "active" or not t_ or t_.get("kind") != "attack" or t_.get("phase") != "march"
                        or t_.get("hunt") or t_.get("target") == pid
                        or now - t_.get("depart", now) > 0.5 * (t_.get("arrive", now) - t_.get("depart", now))):
                    continue                          # (only squads still in the first half of their march)
                tk_ = npc_reinf_task("support", owner, pid, now, m)
                if tk_ and len(tk_["path"]) - 1 <= NPC_RECALL_STEPS and (best is None or len(tk_["path"]) < len(best[1]["path"])):
                    best = (m, tk_)
            if best:
                m, tk_ = best
                log(f"   NPC: {m['name']} (nation {owner}) calls off its march on {m['task'].get('target')} to defend {pid}")
                m["task"] = tk_
                rk[str(owner)] = now + NPC_RECALL_GAP
                npc_dirty()
                recalled = True
        if recalled or not idle:
            continue
        n = random.choice(idle)
        tk = npc_reinf_task("support", n["nation"], pid, now, n)
        if tk is None:
            continue                                  # cut off: no road through friendly provinces
        n["task"] = tk
        log(f"   NPC: {n['name']} (nation {owner}) sorties to help {pid} (attacked by NPCs, via {n['task'].get('route')}, "
            f"arrives in {n['task']['arrive'] - now:.0f}s)")
        npc_dirty()
    # player battles in a province of an NPC nation: more NPC squads walk in at random times
    for mid, B in list(BATTLES.items()):
        dfd = B.get("defender", 0)
        if not dfd or B.get("won") or B.get("sim") or B.get("npc_raid") or mid >= 100000000:
            continue
        cl = npc_closeness(mid)
        if B.get("reinf", 0) >= NPC_REINFORCE_MAX + int(round(3 * cl)):      # more squads near the capital
            continue
        if now < B.get("reinf_at", 0):
            continue
        own = B.get("owner")
        if own is None or own.w.is_closing():
            continue
        # user 2026-10-23 21:09: also when NPCs attack (a player of the nation defends against NPC squads); losing
        # defences get help sooner, allied nations' NPCs come too
        if not any(not getattr(o, "spectator", False) and not o.w.is_closing() for o in B["members"]):
            continue                                  # NPC-only battles: no extra marching (CPU / traffic)
        me_, them_ = side_strength(B, dfd)
        if them_ <= 0:
            continue
        ratio = me_ / max(1.0, them_)
        B["reinf_at"] = now + random.uniform(40, 180) * (1.5 - cl) * (0.4 if ratio < 0.7 else 1.0 if ratio < 1.5 else 2.0)
        if ratio > 2.5:
            continue
        idle = _npc_idle_of(dfd, now)
        if not idle:
            idle = [m for (a_, b_) in NATION_ALLIES for m in _npc_idle_of(b_ if a_ == dfd else a_, now)
                    if dfd in (a_, b_) and nation_planet(m["nation"]) == mid // 100000]
        if not idle:
            continue
        n = max(idle, key=lambda m: NP.power_of(m)) if random.random() < cl else random.choice(idle)
        pocs = [(pid, p["x"], p["y"], p["strength"], POC_TYPE, p["owner"]) for pid, p in B["pocs"].items()]
        if not pocs:
            continue
        tk = npc_reinf_task("defend", dfd, mid, now, n)
        if tk is None:
            continue                                  # cut off: no road through friendly provinces
        n["task"] = tk
        # (07:16) no extra speed near the capital any more: every reinforcement walks NPC_REINF_STEP per province
        n["task"]["slot"] = B.get("reinf", 0)
        B["reinf"] = B.get("reinf", 0) + 1
        _help_notice(B, dfd, n, n["task"]["arrive"] - now)
        log(f"   NPC: {n['name']} (nation {n['nation']}) marches to reinforce the defence of {mid} (via {n['task'].get('route')}, "
            f"arrives in {n['task']['arrive'] - now:.0f}s, force ratio {ratio:.2f})")
        npc_dirty()

# ---- GHOST BATTLES -----------------------------------------------------------------------------------------------------
NPC_ASSIST_CHANCE = 0.5      # per tick (10 s) and running attack: chance that one more idle friendly / allied NPC joins it
NPC_ASSIST_MAX = 4           # NPC squads of one side that march to help one attack
NPC_ASSIST_STEPS = 6         # ... from at most this many portal steps away

def side_strength(B, X):
    """(power of side X, power of everybody else) on the map of battle B: hit points of the living units weighted by
    their damage per second (players: alive units; NPC / alien units: server targets)."""
    me = them = 0.0
    def w(st9, hp):
        st9 = st9 or ()
        dps = max(st9[3] if len(st9) > 3 else 0, st9[6] if len(st9) > 6 else 0) or 20
        return max(1.0, float(hp)) * (1.0 + dps / 100.0)
    for nat, st9, _kind, hp in battle_units(B):              # (battle_rules: the one listing)
        v = w(st9, hp)
        if nat is not None and same_side(nat, X):
            me += v
        else:
            them += v
    return me, them

def _help_notice(B, X, n, eta):
    """tell the players of side X in battle B that an NPC is on its way (user 2026-10-23 21:09)."""
    for o in B.get("members", ()):
        if getattr(o, "spectator", False) or o.w.is_closing() or not same_side(side_nation(o), X):
            continue
        try:
            _say_lang(o, f"友军 {NP.disp(n['name'], 'zh-cn')} 正赶来支援，约 {int(eta)} 秒后从星门进场。",
                      f"友軍 {NP.disp(n['name'], 'zh-tw')} 正趕來支援，約 {int(eta)} 秒後從星門進場。",
                      f"Allied commander {n['name']} is coming to help - enters through a gate in about {int(eta)} s.",
                      (140, 220, 255))
        except Exception:
            pass

# ---- NPC CALLS FOR SUPPORT IN THE ALLY CHAT (user 2026-10-23 21:33) ----------------------------------------------------
# An NPC side that is losing a battle, or has nothing that hurts the enemy mix (e.g. aircraft), asks in the [Allies]
# channel for help and names the unit kind it needs; idle NPCs of its side / allies re-equip that kind (same levels,
# their branch must allow it) and march in from where they are; they answer in the channel.  Players read it too.
NPC_SOS_GAP = 180              # s between two calls of one side in one battle (2026-10-31: was 300)
NPC_SOS_NATION_GAP = 60        # s between two calls of one nation anywhere (no chat spam) (was 120)
NPC_SOS_HELPERS = 4            # NPCs answering one call (2026-10-31 "support each other": was 2)
NPC_SOS_RATIO = 1.0            # a side weaker than the enemy x this calls (was 0.8)
NPC_SOS_REFIT = 6              # units an answering NPC re-equips as the requested kind (at most)
_DCLASS_ZH = {1: ("实弹", "實彈"), 2: ("导弹", "導彈"), 3: ("火焰", "火焰"), 4: ("激光", "雷射"), 5: ("穿甲", "穿甲"), 6: ("爆破", "爆破")}

def unit_name_lang(code, lang):
    if lang == "zh-cn":
        return UN.CN.get(code, code)
    if lang == "zh-tw":
        return UN.TW.get(code, code)
    return code

def ally_tag(o):
    """channel tag of the ally chat in the receiver's language (user 2026-10-23 22:08)."""
    return {"zh-cn": "[同盟]", "zh-tw": "[同盟]"}.get(_mail_lang(o), "[Allies]")

def npc_ally_chat(nid, speaker, texts, to=None):
    """an NPC line in the [Allies] channel of side nid; texts(lang) -> text.  to = only these sessions (2026-10-25
    20:16: battle reports with grid cells go to the players of that side IN that battle, not to the whole nation)."""
    for o in list(ONLINE if to is None else to):
        try:
            if getattr(o, "logged_in", False) and not o.w.is_closing() and same_side(side_nation(o), nid):
                _lg = _mail_lang(o)
                o.send(chat_line(3, f"{ally_tag(o)} {NP.disp(speaker, _lg)}: {texts(_lg)}", (150, 255, 150), tr=False))
        except Exception:
            pass

NPC_CHAT_GAP = 25             # s between two NPC lines of one nation (urgent lines may come sooner)
NPC_CHAT_GAP_URGENT = 8

def npc_say(nid, n, key, texts, now, gap=300, urgent=False, to=None):
    """one NPC line in the [Allies] channel, rate limited per nation and per topic (key).  True = said."""
    g = NPC_CHAT_T
    if now < g.get(key, 0) or (not urgent and now < g.get(("n", nid), 0)):
        return False                                  # (urgent lines - calls, answers, warnings - only per topic)
    if len(g) > 600:
        for k_ in [k_ for k_, t_ in g.items() if t_ < now]:
            g.pop(k_, None)
    g[key], g[("n", nid)] = now + gap, now + NPC_CHAT_GAP
    npc_ally_chat(nid, n["name"], texts, to=to)
    log(f"   NPC chat: {n['name']} (nation {nid}) [{key}] {texts('zh-cn')}")
    return True

NPC_CHAT_T = {}                # topic / nation -> time (runtime only)

def _owner_name(owner, lang):
    if not owner:
        return {"zh-cn": "外星驻军", "zh-tw": "外星駐軍"}.get(lang, "the alien garrison")
    return nation_name(owner, lang)

def npc_squad_reports(B, pid, now):
    """user 2026-10-23 21:57: every NPC on the map reports what ITS squad runs into - heavy losses (asks for more
    units, one helper comes), units that cannot hurt the enemy (it swaps them), a POC taken / lost."""
    for nid_, rt in list(NPC_RT.items()):
        if rt.get("B") is not B:
            continue
        n = npc_state()["npcs"].get(str(nid_))
        if n is None or not rt.get("units"):
            continue
        side = n["nation"]
        alive = sum(1 for tg in B["targets"].values() if tg.get("npc") == nid_ and tg.get("hp", 0) > 0)
        lost = rt.get("dead", 0) / max(1, rt["units"])
        if lost >= 0.5 and not rt.get("cried") and alive:
            rt["cried"] = True
            def t(lang, _a=alive):
                lb = province_label_lang(pid, lang)
                return {"zh-cn": f"我在{lb}损失过半，只剩 {_a} 个单位，请求增援！",
                        "zh-tw": f"我在{lb}損失過半，只剩 {_a} 個單位，請求增援！"}.get(lang, f"Lost half my units at {lb} ({_a} left) - need reinforcements!")
            if npc_say(side, n, ("loss", pid, nid_), t, now, gap=600, urgent=True):
                try:
                    kind, _why = _sos_need(B, side, max(1, n.get("level", 1)))
                    npc_sos_answer(B, pid, side, kind, now, helpers=1)
                except Exception as e:
                    log(f"   squad report answer: {e!r}")
        if alive == 0 and rt.get("units") and not rt.get("wiped"):
            rt["wiped"] = True
            def t(lang):
                lb = province_label_lang(pid, lang)
                return {"zh-cn": f"我在{lb}的部队全灭了，先撤回整补。", "zh-tw": f"我在{lb}的部隊全滅了，先撤回整補。"}.get(lang, f"My squad at {lb} is wiped out - falling back to refit.")
            npc_say(side, n, ("wiped", pid, nid_), t, now, gap=900)

def _sos_need(B, side, lv):
    """(needed pool kind, why) for NPC side `side` in battle B, or (None, None)."""
    th = battle_threat(B, side)
    if not th:
        return None, None
    own = [tg for tg in (B.get("targets") or {}).values() if tg.get("npc") is not None and tg.get("hp", 0) > 0
           and same_side(tg.get("nation"), side) and tg.get("urole") != "support"]
    if not own:
        return None, None
    mine = sum(unit_effect((tg.get("put") or {}).get("st9") or (), th) for tg in own) / len(own)
    best, beff = None, 0.0
    for p in npc_pool():
        if p["min"] > lv + 10:
            continue
        st_ = pool_st9(p["code"], lv)
        if not st_:
            continue
        e = unit_effect(st_, th)
        if e > beff:
            best, beff = p["code"], e
    if best is None or mine >= 0.6 * beff:
        return None, None
    return best, ("air" if th["air"] >= 0.35 else "armour")

def npc_sos(now):
    st = npc_state()
    gap = st.setdefault("sos_t", {})
    for pid, B in list(BATTLES.items()):
        if B.get("won") or pid >= 100000000 or B.get("sim"):
            continue
        sides = {tg.get("nation") for tg in (B.get("targets") or {}).values() if tg.get("npc") is not None and tg.get("hp", 0) > 0}
        try:
            npc_squad_reports(B, pid, now)
        except Exception as e:
            log(f"   squad reports: {e!r}")
        for side in sides:
            if not side:
                continue
            sos = B.setdefault("sos", {})
            if now < sos.get(side, 0) or now < gap.get(str(side), 0):
                continue
            me_, them_ = side_strength(B, side)
            if them_ <= 0:
                continue
            ratio = me_ / max(1.0, them_)
            if ratio >= NPC_SOS_RATIO:
                _th = battle_threat(B, side)
                if not _th or _th["air"] < 0.35 and ratio >= 1.2:
                    sos[side] = now + 30                   # fine for now: look again in 30 s
                    continue
            lead_id = max((tg["npc"] for tg in B["targets"].values() if tg.get("npc") is not None and tg.get("nation") == side),
                          key=lambda i: sum(1 for t2 in B["targets"].values() if t2.get("npc") == i), default=None)
            lead = st["npcs"].get(str(lead_id)) if lead_id is not None else None
            if lead is None:
                continue
            kind, why = _sos_need(B, side, max(1, lead.get("level", 1)))
            if kind is None and ratio >= NPC_SOS_RATIO:
                sos[side] = now + 30
                continue                                   # winning and the right units are there: no call
            sos[side], gap[str(side)] = now + NPC_SOS_GAP, now + NPC_SOS_NATION_GAP
            def ask(lang, _k=kind, _w=why, _r=ratio):
                k = unit_name_lang(_k, lang) if _k else None
                lb = province_label_lang(pid, lang)
                if lang in ("zh-cn", "zh-tw"):
                    cn = lang == "zh-cn"
                    if _r < NPC_SOS_RATIO:
                        t = f"{lb}战况吃紧，请求支援！" if cn else f"{lb}戰況吃緊，請求支援！"
                    else:
                        t = f"{lb}需要换兵种支援！" if cn else f"{lb}需要換兵種支援！"
                    if k:
                        t += (f"敌方{'空中单位多' if _w == 'air' else '装甲厚，我们打不动'}，请带{k}来。" if cn else
                              f"敵方{'空中單位多' if _w == 'air' else '裝甲厚，我們打不動'}，請帶{k}來。")
                    return t
                return f"{lb}: need support!" + (f" Bring {k} ({'anti-air' if _w == 'air' else 'vs. their armour'})." if k else "")
            npc_say(side, lead, ("sos", pid, side), ask, now, gap=NPC_SOS_GAP, urgent=True)
            log(f"   NPC SOS: {lead['name']} (nation {side}) on {pid}: ratio {ratio:.2f}, needs {kind or 'any'} ({why})")
            npc_sos_answer(B, pid, side, kind, now)

def _assist_gave_up(n, pid, why, now):
    """a helper that promised to come could not enter: it says so in the ally channel (no silent waiting)."""
    def say(lang, _P=pid, _w=why):
        lb = province_label_lang(_P, lang)
        r = {"full": ("那边人太多，进不去", "那邊人太多，進不去", "too crowded to get in"),
             "over": ("战斗已经结束", "戰鬥已經結束", "the battle is over"),
             "ambush": ("那是伏击战，进不去", "那是伏擊戰，進不去", "it is an ambush, no way in"),
             "no units": ("那边放不下我的部队", "那邊放不下我的部隊", "no room for my squad"),
             "road": ("去那边的路被切断了", "去那邊的路被切斷了", "my road there was cut")}.get(
            _w, ("进不去", "進不去", "cannot get in"))
        return {"zh-cn": f"{lb}{r[0]}，我先回去了。", "zh-tw": f"{lb}{r[1]}，我先回去了。"}.get(
            lang, f"{lb}: {r[2]} - going back.")
    npc_say(n["nation"], n, ("gaveup", pid, n["id"]), say, now, gap=300, urgent=True)

NPC_SOS_NEAR_KINDS = ("patrol", "support")   # (16:39) NPCs posted in a nearby province (no battle there) may answer too
NPC_SOS_ETA_JITTER = (0.85, 1.3)              # march time x this, + 0..NPC_SOS_ETA_EXTRA s (getting ready)
NPC_SOS_ETA_EXTRA = 25

def _sos_alt_kinds(B, side, lv, kind, n=3):
    """the n best pool kinds against the enemy in B (besides `kind`) for an NPC of level lv."""
    th = battle_threat(B, side)
    if not th:
        return []
    sc = []
    for p in npc_pool():
        if p["min"] > lv + 10 or p["code"] == kind:
            continue
        st_ = pool_st9(p["code"], lv)
        if st_:
            sc.append((unit_effect(st_, th), p["code"]))
    sc.sort(reverse=True)
    return [c for _e, c in sc[:n]]

def _sos_posted(nat, pid, now):
    """NPCs of nation nat on a patrol / support post in some province that has no battle running (they may leave it
    for a call), not the battle province itself."""
    out = []
    for m in npc_of(nat):
        t = m.get("task")
        if (m["state"] != "active" or not t or t.get("kind") not in NPC_SOS_NEAR_KINDS or t.get("phase") == "march"
                or t.get("target") == pid or m.get("retire") or NP.readiness(m) < 0.3):
            continue
        Bt = BATTLES.get(t.get("target"))
        if Bt is not None and not Bt.get("won"):
            continue
        out.append(m)
    return out

# PROACTIVE HELP + FASTER HELP ON A CALL (user 2026-10-27 23:14 "NPCs should reinforce on their own, not only after an
# SOS; after an SOS the help must come faster"):
#  * npc_auto_reinforce (every NPC tick): every surface battle with players gets NPC helpers of the players' side without
#    any call - how many depends on how the side is doing (losing: up to NPC_SURFACE_JOIN_MAX), one more every
#    NPC_AUTO_GAP s, the nearest idle NPC first (same rules as npc_join_surface: defence / assist, front rule).
#  * a player's call ("help", "支援" ...): helpers march at NPC_SOS_RUSH x the reinforcement time (no getting-ready
#    delay), NPC_SOS_RUSH_EXTRA more of them, and helpers already on the way to that battle hurry the same way.
NPC_AUTO_GAP = 15.0             # s between two automatic helpers for one side of one battle
NPC_SOS_RUSH = 0.5              # march time x this for helpers called by a player
NPC_SOS_RUSH_MIN = 15.0         # s: never faster than this
NPC_SOS_RUSH_EXTRA = 1          # helpers more than a normal answer

def npc_auto_want(ratio):
    return NPC_SURFACE_JOIN_MAX if ratio < 0.8 else 3 if ratio < 1.5 else 2 if ratio < 3.0 else 1

def npc_auto_reinforce(now):
    for pid, B in list(BATTLES.items()):
        if (pid >= 100000000 or (pid // 10000) % 10 or B.get("won") or B.get("sim") or B.get("hunt")
                or B.get("npc_raid") or is_star_province(pid)):
            continue
        live = [o for o in B.get("members", ()) if not getattr(o, "spectator", False) and not o.w.is_closing()]
        if not live:
            continue
        sides = {side_nation(o) for o in live}
        auto = B.setdefault("auto_t", {})
        for X in sides:
            if now < auto.get(X, 0):
                continue
            me_, them_ = side_strength(B, X)
            if them_ <= 0:
                continue
            going = sum(1 for m in npc_all() if m["task"] and m["task"].get("target") == pid and same_side(m["nation"], X)
                        and m["task"].get("kind") in ("attack", "defend", "support"))
            if going >= npc_auto_want(me_ / max(1.0, them_)):
                continue
            nations = {X} | {b_ if a_ == X else a_ for (a_, b_) in NATION_ALLIES if X in (a_, b_)}
            idle = [m for nat in nations for m in _npc_idle_of(nat, now)
                    if nation_planet(m["nation"]) == pid // 100000 and NP.readiness(m) >= NP.MIN_READY]
            cands = []
            for m in idle:
                pth, sec = npc_march_path(m, pid, now)
                if pth and len(pth) - 1 <= NPC_ASSIST_STEPS:
                    cands.append((sec, m))
            for _sec, m in sorted(cands, key=lambda c: c[0]):
                j = npc_surface_battle(m, now)
                if j and j[1] == pid and npc_join_surface(m, now, force=j):
                    auto[X] = now + NPC_AUTO_GAP
                    log(f"   NPC: {m['name']} comes to help nation {X} on {pid} without a call ({going + 1} helper(s))")
                    break

def npc_rush_incoming(pid, side, now):
    """helpers of side already marching to pid hurry (once): remaining time x NPC_SOS_RUSH.  -> how many."""
    n_ = 0
    for m in npc_all():
        t = m.get("task") or {}
        if (t.get("target") == pid and t.get("phase") == "march" and not t.get("rushed") and same_side(m["nation"], side)
                and t.get("kind") in ("attack", "defend", "support") and t.get("arrive", 0) > now + NPC_SOS_RUSH_MIN):
            left = t["arrive"] - now
            new = max(NPC_SOS_RUSH_MIN, left * NPC_SOS_RUSH)
            if t.get("path") and t.get("depart") is not None:   # keep the drawn position continuous on the road
                done = (now - t["depart"]) / max(1.0, t["arrive"] - t["depart"])
                total = new / max(0.05, 1.0 - done)
                t["depart"] = now - done * total
            t["arrive"] = now + new
            t["rushed"] = True
            n_ += 1
    if n_:
        npc_dirty()
        log(f"   NPC: {n_} helper(s) on the way to {pid} hurry (call for help)")
    return n_

def npc_sos_answer(B, pid, side, kind, now, helpers=None, rush=False):
    """idle NPCs of the side / its allies on the planet re-equip and march to the battle.
    user 2026-10-25 16:39 (every call got the same two answers - same unit, same ETA): the helpers are chosen with some
    chance among the nearest ones (also NPCs on a patrol / support post in a nearby province, and ones walking home),
    each brings its own mix (the first one the needed kind, the others another good kind or their own squad), the ETA
    varies (march time x 0.85-1.3 + getting ready) and the answers are worded differently."""
    if B.get("owner") is not None and npc_side_blocked(B["owner"], side):
        log(f"   NPC SOS on {pid}: no helpers - a player of nation {side} runs a client without NPC-ally support")
        return
    nations = {side} | {b_ if a_ == side else a_ for (a_, b_) in NATION_ALLIES if side in (a_, b_)}
    idle = [m for nat in nations for m in _npc_idle_of(nat, now) if nation_planet(m["nation"]) == pid // 100000]
    idle += [m for nat in nations for m in _sos_posted(nat, pid, now)
             if nation_planet(m["nation"]) == pid // 100000 and m not in idle]
    dfd = B.get("defender") or province_owner(pid)
    pool = {p["code"]: p for p in npc_pool()}
    cands = []
    for m in idle:
        path, sec = npc_march_path(m, pid, now, NPC_REINF_PACE)       # from where it is now
        if not path or len(path) - 1 > NPC_ASSIST_STEPS:
            continue
        cands.append((sec * random.uniform(0.9, 1.15), m, path))      # the nearest first (10-31: was x 0.7-1.4)
    cands.sort(key=lambda c: c[0])
    want = helpers or random.choice((NPC_SOS_HELPERS - 1, NPC_SOS_HELPERS, NPC_SOS_HELPERS, NPC_SOS_HELPERS + 1))
    if rush:
        want += NPC_SOS_RUSH_EXTRA                   # (23:14) a player's call brings more help, faster
    room = npc_battle_room(pid, side)
    if room is not None and not same_side(side, dfd):            # (10-31) attacking side: only as many as fit in
        want = min(want, max(0, room))
    used_kinds = []
    for order, (_sec, m, path) in enumerate(cands[:want]):
        lv = max(1, m.get("level", 1))
        # what this helper brings: helper 0 the needed kind; the others another good kind, the needed one, or as they are
        bring = kind
        if order > 0 or kind is None:
            alts = [c for c in _sos_alt_kinds(B, side, lv, kind) if c not in used_kinds]
            r = random.random()
            bring = (random.choice(alts) if alts and r < 0.5 else (kind if r < 0.75 else None))
        if bring and not any(c == bring for c, _l in m["squad"]) and not (bring in pool and npc_can_field(m, pool[bring])):
            bring = None                                   # cannot field it: comes with its own squad
        k = 0
        if bring and not any(c == bring for c, _l in m["squad"]):
            refit = random.randint(max(1, NPC_SOS_REFIT - 2), NPC_SOS_REFIT)
            nf = NP.fast_count(len(m["squad"]))
            for i in range(nf, len(m["squad"])):           # never the capturers
                if k >= refit:
                    break
                if m["squad"][i][0] != (m.get("doctrine") or {}).get("main"):
                    m["squad"][i] = [bring, m["squad"][i][1]]
                    k += 1
            for i in range(len(m["squad"]) - 1, nf - 1, -1):  # not enough second-kind units: some of the main kind
                if k >= min(refit, 3):
                    break
                if m["squad"][i][0] != bring:
                    m["squad"][i] = [bring, m["squad"][i][1]]
                    k += 1
            npc_realism(m)
        elif bring:
            k = sum(1 for c, _l in m["squad"] if c == bring)
        if bring:
            used_kinds.append(bring)
        if m.get("task"):                                  # leaves its patrol / support post
            log(f"   NPC SOS: {m['name']} leaves its {m['task'].get('kind')} post at {m['task'].get('target')} for {pid}")
            _here = path[0]
            m["task"] = None
            m["walk"] = {"path": [_here], "depart": now - 1, "arrive": now + 5}   # starts from its post, not the capital
        if dfd and same_side(m["nation"], dfd):
            tk = npc_reinf_task("defend", m["nation"], pid, now, m)
            if tk is None:
                continue
            m["task"] = tk
            m["task"]["slot"] = B.get("reinf", 0)
            B["reinf"] = B.get("reinf", 0) + 1
        else:
            npc_send([m], {"pid": pid, "owner": dfd, "kind": "assist", "garrison": 0, "dist_cap": len(path) - 1,
                           "def_power": 0.0}, now)
        if not m.get("task"):
            continue
        as_reinforcement(m, now)
        t_ = m["task"]
        if t_.get("arrive"):                               # every helper needs its own time to get ready and march
            if rush:                                       # (23:14) called by a player: forced march, no getting ready
                t_["arrive"] = now + max(NPC_SOS_RUSH_MIN, (t_["arrive"] - now) * NPC_SOS_RUSH * random.uniform(0.9, 1.1))
                t_["rushed"] = True
            else:
                t_["arrive"] = now + (t_["arrive"] - now) * random.uniform(*NPC_SOS_ETA_JITTER) + random.uniform(0, NPC_SOS_ETA_EXTRA)
        eta = int(t_["arrive"] - now)
        steps = max(1, len(path) - 1)
        def reply(lang, _k=bring, _n=min(k, NPC_GHOST_DEPLOY), _e=eta, _st=steps, _v=random.randrange(6)):
            kn = unit_name_lang(_k, lang) if _k else None
            lb = province_label_lang(pid, lang)
            if lang in ("zh-cn", "zh-tw"):
                cn = lang == "zh-cn"
                w = (f"{_n} 只{kn}" if cn else f"{_n} 隻{kn}") if (kn and _n) else (kn or "")
                if cn:
                    opts = [f"收到，{'带' + w if w else '我'}前往{lb}，约 {_e} 秒到。",
                            f"我离{lb}{'不远' if _st <= 2 else '有点远'}，{_e} 秒左右到{'，带了' + w if w else ''}。",
                            f"马上出发！{'带' + w + '，' if w else ''}{_e} 秒内赶到{lb}。",
                            f"撑住，我{'带' + w if w else ''}过去，大约 {_e} 秒。",
                            f"{lb}是吧？{_e} 秒后到{'，' + w + '跟我走' if w else ''}。",
                            f"收到求援，{_st} 个省的路，约 {_e} 秒{'，带' + w if w else ''}。"]
                else:
                    opts = [f"收到，{'帶' + w if w else '我'}前往{lb}，約 {_e} 秒到。",
                            f"我離{lb}{'不遠' if _st <= 2 else '有點遠'}，{_e} 秒左右到{'，帶了' + w if w else ''}。",
                            f"馬上出發！{'帶' + w + '，' if w else ''}{_e} 秒內趕到{lb}。",
                            f"撐住，我{'帶' + w if w else ''}過去，大約 {_e} 秒。",
                            f"{lb}是吧？{_e} 秒後到{'，' + w + '跟我走' if w else ''}。",
                            f"收到求援，{_st} 個省的路，約 {_e} 秒{'，帶' + w if w else ''}。"]
                return opts[_v]
            opts = [f"On my way to {lb}{' with ' + kn if kn else ''}, about {_e} s.",
                    f"Hold on, {_e} s to {lb}{' - bringing ' + kn if kn else ''}.",
                    f"Moving out{' with ' + kn if kn else ''}, {_st} province(s) away, ~{_e} s."]
            return opts[_v % len(opts)]
        npc_say(m["nation"], m, ("reply", pid, m["id"]), reply, now, gap=300, urgent=True)
        _help_notice(B, side, m, eta)
        npc_dirty()
        log(f"   NPC SOS: {m['name']} (nation {m['nation']}) answers for {pid}: brings {bring or 'own squad'} "
            f"({k} unit(s)), {steps} step(s), eta {eta}s")

def npc_reply_going(m, P, eta, now, kind=None, k=0):
    """an idle NPC answers a call in the ally channel: it is on its way."""
    def reply(lang, _P=P, _e=int(eta), _k=kind, _n=min(k, NPC_GHOST_DEPLOY)):
        lb = province_label_lang(_P, lang)
        kn = unit_name_lang(_k, lang) if _k else None
        if lang == "zh-cn":
            return f"收到，{('带 ' + str(_n) + ' 只' + kn) if (kn and _n) else ('带' + kn if kn else '我')}前往{lb}，约 {_e} 秒到。"
        if lang == "zh-tw":
            return f"收到，{('帶 ' + str(_n) + ' 隻' + kn) if (kn and _n) else ('帶' + kn if kn else '我')}前往{lb}，約 {_e} 秒到。"
        return f"On my way to {lb}{' with ' + kn if kn else ''}, about {_e} s."
    return npc_say(m["nation"], m, ("reply", P, m["id"]), reply, now, gap=300, urgent=True)

# players ask in the ally channel ("有人吗 / 支援 / help"): idle NPCs answer and come (user 2026-10-23 21:57)
NPC_HEAR_WORDS = ("支援", "增援", "救", "援", "help", "有人", "來人", "来人", "帮", "幫", "sos")
NPC_HEAR_GAP = 120
_HEAR_T = {}

NPC_HEAR_ATTACK = ("进攻", "進攻", "攻打", "攻", "打", "attack", "集合", "一起")
NPC_HEAR_DEFEND = ("防守", "守", "defend", "保护", "保護")

def _heard_province(s, text):
    """a province named in a chat line: "41号省" / "41號" / "#41" / "41省" -> province id on the player's planet."""
    import re as _re
    m = _re.search(r"#\s*(\d{1,2})|(\d{1,2})\s*(?:号|號|省)", text or "")
    if not m:
        return None
    k = int(m.group(1) or m.group(2))
    pl = current_planet(s)
    provs = planet_provinces(pl)
    return provs[k - 1] if 1 <= k <= len(provs) else None

def npc_hear_order(s, text, now):
    """user 2026-10-23 22:05: a player's request names a province - idle NPCs of his side answer and go there
    (attack it with him, or defend it).  True = handled."""
    P = _heard_province(s, text)
    if P is None:
        return False
    low = text.lower()
    me = side_nation(s)
    own = province_owner(P)
    defend = own and same_side(own, me)
    if not defend and not any(w in low for w in NPC_HEAR_ATTACK + NPC_HEAR_WORDS):
        return False
    if defend and not any(w in low for w in NPC_HEAR_DEFEND + NPC_HEAR_WORDS + NPC_HEAR_ATTACK):
        return False
    nations = {me} | {b_ if a_ == me else a_ for (a_, b_) in NATION_ALLIES if me in (a_, b_)}
    idle = [m for nat in nations for m in _npc_idle_of(nat, now) if nation_planet(m["nation"]) == P // 100000
            and NP.readiness(m) >= NP.MIN_READY]
    went = 0
    for m in sorted(idle, key=lambda m: -NP.power_of(m)):
        if went >= 2:
            break
        if defend:
            tk = npc_reinf_task("support", m["nation"], P, now, m)
            if tk is None:
                continue
            m["task"] = tk
        else:
            pth, _sec = npc_march_path(m, P, now)
            if not pth or len(pth) - 1 > NPC_ASSIST_STEPS:
                continue
            npc_send([m], {"pid": P, "owner": own, "kind": "assist", "garrison": 0, "dist_cap": len(pth) - 1,
                           "def_power": 0.0}, now)
            if not m.get("task"):
                continue
            as_reinforcement(m, now)
        npc_dirty()
        went += 1
        eta = int(m["task"]["arrive"] - now)
        def reply(lang, _P=P, _e=eta, _d=defend, _n=getattr(s, "acc", "")):
            lb, nm = province_label_lang(_P, lang), display_name(_n)
            if lang == "zh-cn":
                return f"{nm}，收到！{'我去守' if _d else '跟你一起打'}{lb}，约 {_e} 秒到。"
            if lang == "zh-tw":
                return f"{nm}，收到！{'我去守' if _d else '跟你一起打'}{lb}，約 {_e} 秒到。"
            return f"{nm}, roger! {'Defending' if _d else 'Attacking'} {lb} with you, about {_e} s."
        npc_say(m["nation"], m, ("order", P, m["id"]), reply, now, gap=300, urgent=True)
    if not went:
        spk = next((m for m in npc_all() if same_side(m["nation"], me) and m["state"] == "active"), None)
        if spk:
            npc_say(spk["nation"], spk, ("busy", getattr(s, "acc", "")), lambda lang, _P=P: {
                "zh-cn": f"现在没人能去{province_label_lang(_P, lang)}（都在忙或路被截断）。",
                "zh-tw": f"現在沒人能去{province_label_lang(_P, lang)}（都在忙或路被截斷）。"}.get(
                lang, f"Nobody can go to {province_label_lang(_P, lang)} now (busy or cut off)."), now, gap=60, urgent=True)
    return True

def npc_hear(s, text):
    now = time.time()
    low = (text or "").lower()
    if now < _HEAR_T.get(getattr(s, "acc", ""), 0):
        # (user 2026-10-24 11:42) a call during the cool-down was ignored without a word - say when it counts again
        if any(w in low for w in NPC_HEAR_WORDS):
            try:
                _w = int(_HEAR_T[getattr(s, "acc", "")] - now) + 1
                _say_lang(s, f"求援已送出，{_w} 秒后可以再喊。", f"求援已送出，{_w} 秒後可以再喊。",
                          f"Your call is out - you can call again in {_w} s.", (200, 220, 255))
            except Exception:
                pass
        return
    if npc_hear_order(s, text, now):                  # "一起打41号省" / "守39号" / "#12 help"
        _HEAR_T[getattr(s, "acc", "")] = now + NPC_HEAR_GAP
        return
    if not any(w in low for w in NPC_HEAR_WORDS):
        return
    _HEAR_T[getattr(s, "acc", "")] = now + NPC_HEAR_GAP
    me = side_nation(s)
    B = getattr(s, "battle", None)
    pid = province_of(B["map"]) if B else None
    if B is not None and pid and pid < 100000000 and not B.get("won"):
        th = battle_threat(B, me)
        kind = None
        if th:
            lv = max([1] + [u.get("level", 1) for u in (get_account(s.acc)[1].get("units") or [])])
            kind = max((p["code"] for p in npc_pool() if p["min"] <= lv + 10),
                       key=lambda c: unit_effect(pool_st9(c, lv) or (), th), default=None)
        before = {m["id"] for m in npc_all() if m.get("task")}
        sped = npc_rush_incoming(pid, me, now)           # (23:14) helpers already on the way march faster
        npc_sos_answer(B, pid, me, kind, now, rush=True)
        went = [m for m in npc_all() if m.get("task") and m["id"] not in before]
        if went or sped:
            if sped and not went:
                _say_lang(s, f"已催促 {sped} 支正在赶来的友军加速前进。", f"已催促 {sped} 支正在趕來的友軍加速前進。",
                          f"{sped} allied squad(s) on the way are hurrying now.", (200, 220, 255))
            return
        spk = next(iter(_npc_idle_of(me, now)), None) or next((m for m in npc_all() if same_side(m["nation"], me)
                                                              and m["state"] == "active"), None)
        if spk:
            npc_say(spk["nation"], spk, ("busy", s.acc), lambda lang: {"zh-cn": "大家都在忙或过不去，再撑一下！",
                    "zh-tw": "大家都在忙或過不去，再撐一下！"}.get(lang, "Everyone is busy or cut off - hold on!"), now, gap=60, urgent=True)
        return
    spk = next(iter(_npc_idle_of(me, now)), None)
    if spk:
        def hi(lang, _n=getattr(s, "acc", "")):
            return {"zh-cn": f"{display_name(_n)}，我在。在战斗里喊「支援」，有空的会过去。",
                    "zh-tw": f"{display_name(_n)}，我在。在戰鬥裡喊「支援」，有空的會過去。"}.get(lang, f"{display_name(_n)}, here. Call 'help' in a battle and free commanders come.")
        npc_say(spk["nation"], spk, ("hi", s.acc), hi, now, gap=300, urgent=True)

def npc_strategy_chat(now):
    """user 2026-10-23 21:57: strategic needs in the ally channel - an enemy force marching on our province (a defender
    is sent), a campaign leaving (others may join), a nation in its last stand."""
    st = npc_state()
    seen = set()
    for n in npc_all():
        t = n.get("task")
        if not t or t.get("kind") != "attack" or t.get("phase") != "march" or t.get("hunt"):
            continue
        P, A = t["target"], n["nation"]
        Y = province_owner(P)
        key = (A, P, t.get("group") or n["id"])
        if key in seen:
            continue
        seen.add(key)
        # (a) the attacked nation sees it coming (about 2 province steps away)
        left = t["arrive"] - now
        if Y and not same_side(Y, A) and 20 < left < 240 and not t.get("warned"):
            t["warned"] = True
            force = [m for m in npc_all() if m.get("task") and m["task"].get("target") == P and m["nation"] == A
                     and m["task"].get("phase") == "march"]
            spk = next(iter(_npc_idle_of(Y, now)), None) or next((m for m in npc_of(Y) if m["state"] == "active"), None)
            if spk is not None:
                def warn(lang, _A=A, _P=P, _k=len(force), _l=int(left)):
                    lb, an = province_label_lang(_P, lang), nation_name(_A, lang)
                    return {"zh-cn": f"发现{an} {_k} 支部队正向{lb}推进，约 {_l} 秒后到达，请求防守！",
                            "zh-tw": f"發現{an} {_k} 支部隊正向{lb}推進，約 {_l} 秒後到達，請求防守！"}.get(
                        lang, f"{_k} squad(s) of {an} marching on {lb}, there in about {_l} s - defend it!")
                if npc_say(Y, spk, ("warn", P), warn, now, gap=600, urgent=True):
                    for m in ([x for x in _npc_idle_of(Y, now) if x is not spk] or _npc_idle_of(Y, now))[:1]:   # one defender at once
                        tk = npc_reinf_task("support", Y, P, now, m)
                        if tk:
                            m["task"] = tk
                            npc_dirty()
                            npc_reply_going(m, P, tk["arrive"] - now, now)
        # (b) a campaign announces itself to its side (players / NPCs may join)
        if not t.get("announced") and now - t.get("depart", now) < 30:
            t["announced"] = True
            k = sum(1 for m in npc_all() if m.get("task") and m["task"].get("target") == P and m["nation"] == A)
            if k >= 2 or random.random() < 0.3:
                def camp(lang, _P=P, _k=k, _Y=Y, _l=int(left)):
                    lb, on = province_label_lang(_P, lang), _owner_name(_Y, lang)
                    return {"zh-cn": f"我们 {_k} 人进攻{lb}（{on}），约 {_l} 秒到，有空的一起来！",
                            "zh-tw": f"我們 {_k} 人進攻{lb}（{on}），約 {_l} 秒到，有空的一起來！"}.get(
                        lang, f"{_k} of us attack {lb} ({on}), there in about {_l} s - join us!")
                if npc_say(A, n, ("camp", P), camp, now, gap=900):
                    for m in _npc_idle_of(A, now)[:random.randint(0, 2)]:
                        if NP.readiness(m) < NP.MIN_READY:
                            continue
                        pth, sec = npc_march_path(m, P, now)
                        if not pth:
                            continue
                        m["task"] = dict(t, since=now, wait=0, depart=now, path=pth, arrive=max(t["arrive"], now + sec),
                                         origin=pth[-2] if len(pth) >= 2 else t.get("origin"), announced=True)
                        m.pop("walk", None)
                        npc_dirty()
                        npc_reply_going(m, P, m["task"]["arrive"] - now, now)
    # (c) last stand
    for nid, until in list(st.get("stand", {}).items()):
        nid = int(nid)
        if until > now:
            spk = next((m for m in npc_of(nid) if m["state"] == "active"), None)
            if spk is not None:
                def stand(lang, _o=npc_owned(nid)):
                    return {"zh-cn": f"我国只剩 {_o} 个省了，全员回防，守住首都！",
                            "zh-tw": f"我國只剩 {_o} 個省了，全員回防，守住首都！"}.get(lang, f"We hold only {_o} provinces - everyone back to defend the capital!")
                npc_say(nid, spk, ("stand", nid), stand, now, gap=3600)

# ---- NPC DIPLOMACY (user 2026-10-23 22:01: every nation wants the whole planet; alliances are a strategy and can be
# dropped when the course changes) ------------------------------------------------------------------------------------
# Every DIP_EVERY s per planet:
#  * FORM: when one nation leads (>= DIP_LEADER_SHARE of the owned land), the two strongest others that are not allied
#    and not each other's main front ally against it (balance of power).
#  * BREAK: an ally that has become the leader, an alliance whose common enemy fell below DIP_RELAX_SHARE, or an
#    alliance that leaves a nation no enemy to conquer (only the ally and itself left next to its land) - after at
#    least DIP_MIN_HOURS; the pair cannot ally again for DIP_COOLDOWN.
#  * a nation with a HUMAN president decides itself (the NPCs only advise in the ally channel).
#  * never while units of the two nations fight side by side (the clients take the alliance groups at PUT time).
DIP_EVERY = 600
DIP_LEADER_SHARE = 0.38
DIP_RELAX_SHARE = 0.25
DIP_MIN_HOURS = 1.0
DIP_COOLDOWN = 3 * 3600

def _human_led(nid):
    pres = politics(nid).get("president") or ""
    return bool(pres) and pres in load_accounts()

def _fighting_together(a, b):
    for B in BATTLES.values():
        if B.get("won"):
            continue
        sides = {side_nation(o) for o in B.get("members", ()) if not getattr(o, "spectator", False)}
        sides |= {tg.get("nation") for tg in (B.get("targets") or {}).values() if tg.get("npc") is not None and tg.get("hp", 0) > 0}
        if a in sides and b in sides:
            return True
    return False

def _at_war_now(a, b):
    """a battle between a and b runs, or an attack of one on the other's province is under way."""
    for B in BATTLES.values():
        if B.get("won"):
            continue
        sides = {side_nation(o) for o in B.get("members", ()) if not getattr(o, "spectator", False)}
        sides |= {tg.get("nation") for tg in (B.get("targets") or {}).values() if tg.get("npc") is not None and tg.get("hp", 0) > 0}
        sides |= {B.get("defender") or 0, B.get("npc_attacker") or 0}
        if a in sides and b in sides:
            return True
    for n in npc_all():
        t = n.get("task")
        if t and t.get("kind") == "attack" and n["nation"] in (a, b):
            if province_owner(t["target"]) == (b if n["nation"] == a else a):
                return True
    return False

def _neighbours_of(nid):
    pl = nation_planet(nid)
    out = set()
    for k, o in world_state()["owners"].items():
        if int(o) != nid or int(k) // 100000 != pl:
            continue
        for q in PORTAL_LINKS.get(int(k) % 100000, ()):
            ow = province_owner(pl * 100000 + q)
            if ow != nid:
                out.add(ow)
    return out

def set_alliance(a, b, on, why_cn, why_tw, why_en):
    pr = (min(a, b), max(a, b))
    have = [(min(x, y), max(x, y)) for x, y in NATION_ALLIES]
    if on and pr not in have:
        NATION_ALLIES.append(pr)
    elif not on:
        NATION_ALLIES[:] = [(x, y) for x, y in NATION_ALLIES if (min(x, y), max(x, y)) != pr]
    WORLD_allies_save()
    dip = npc_state().setdefault("dip", {})
    k = f"{pr[0]}-{pr[1]}"
    if on:
        dip[k] = {"since": time.time()}
        for n in npc_all():                       # marches on the new ally's land turn back
            t = n.get("task")
            if t and t.get("kind") == "attack" and n["nation"] in (a, b) and t.get("phase") == "march" \
                    and province_owner(t["target"]) == (b if n["nation"] == a else a):
                npc_release(n, time.time(), 0)
    else:
        dip[k] = {"broken": time.time()}
    npc_dirty()
    for t in list(ONLINE):
        if getattr(t, "logged_in", False) and not t.w.is_closing():
            try:
                t.send(build_relations())
                lang = _mail_lang(t)
                an, bn = nation_name(a, lang), nation_name(b, lang)
                if on:
                    txt = {"zh-cn": f"【外交】{an}与{bn}结盟：{why_cn}", "zh-tw": f"【外交】{an}與{bn}結盟：{why_tw}"}.get(lang, f"[Diplomacy] {an} and {bn} are now allied: {why_en}")
                else:
                    txt = {"zh-cn": f"【外交】{an}解除与{bn}的同盟：{why_cn}", "zh-tw": f"【外交】{an}解除與{bn}的同盟：{why_tw}"}.get(lang, f"[Diplomacy] {an} ends the alliance with {bn}: {why_en}")
                t.send(chat_line(0x0A, txt, (255, 220, 120), tr=False))
            except Exception:
                pass
    log(f"   DIPLOMACY: {a} and {b} {'ALLIED' if on else 'alliance BROKEN'} - {why_en}")

def npc_diplomacy(now):
    st = npc_state()
    if now < st.get("dip_t", 0):
        return
    st["dip_t"] = now + DIP_EVERY
    dip = st.setdefault("dip", {})
    for pl in {nation_planet(n[0]) for n in NATIONS}:
        nats = [n[0] for n in NATIONS if nation_planet(n[0]) == pl]
        land = {n: npc_owned(n) for n in nats}
        total = max(1, sum(land.values()))
        share = {n: land[n] / total for n in nats}
        alive = [n for n in nats if land[n] > 0]
        leader = max(alive, key=lambda n: land[n], default=None)
        pairs = [(min(x, y), max(x, y)) for x, y in NATION_ALLIES if x in nats and y in nats]
        # ---- break
        for a, b in pairs:
            rec = dip.get(f"{a}-{b}", {})
            if now - rec.get("since", 0) < DIP_MIN_HOURS * 3600 or _fighting_together(a, b):
                continue
            enemies = [n for n in alive if n not in (a, b)]
            strongest_enemy = max((share[n] for n in enemies), default=0.0)
            why = None
            for x, y in ((a, b), (b, a)):
                if _human_led(x):
                    continue
                if x != leader and y == leader and share[y] >= DIP_LEADER_SHARE and share[y] > 1.4 * share[x]:
                    why = (x, y, "盟友已成为最大威胁", "盟友已成為最大威脅", "the ally has become the biggest threat")
                elif not enemies or strongest_enemy < DIP_RELAX_SHARE:
                    why = (x, y, "共同的敌人已不足为惧，我们要统一这颗星球", "共同的敵人已不足為懼，我們要統一這顆星球",
                           "the common enemy is no threat any more - we want the whole planet")
                elif _neighbours_of(x) - {x} <= {y}:
                    why = (x, y, "我们只剩盟友可以扩张", "我們只剩盟友可以擴張", "there is nobody else to conquer")
                if why:
                    break
            if why:
                set_alliance(why[0], why[1], False, why[2], why[3], why[4])
                spk = next((m for m in npc_of(why[0]) if m["state"] == "active"), None)
                if spk:
                    npc_say(why[0], spk, ("dipbreak", why[1]), lambda lang, _y=why[1]: {
                        "zh-cn": f"从现在起{nation_name(_y, lang)}是敌人了，准备进攻！",
                        "zh-tw": f"從現在起{nation_name(_y, lang)}是敵人了，準備進攻！"}.get(lang, f"{nation_name(_y, lang)} is our enemy now - get ready!"),
                        now, gap=1800, urgent=True)
                pairs = [(x, y) for x, y in pairs if (x, y) != (a, b)]
        # ---- form (each nation in at most one alliance)
        if leader is None or share[leader] < DIP_LEADER_SHARE:
            continue
        busy = {x for p in pairs for x in p}
        cands = sorted([n for n in alive if n != leader and n not in busy], key=lambda n: -land[n])
        for i in range(len(cands)):
            for j in range(i + 1, len(cands)):
                a, b = cands[i], cands[j]
                pr = (min(a, b), max(a, b))
                if now - dip.get(f"{pr[0]}-{pr[1]}", {}).get("broken", 0) < DIP_COOLDOWN:
                    continue
                if share[a] + share[b] > 1.2 * share[leader]:
                    continue                                   # together already stronger: no need
                if _at_war_now(a, b):
                    continue                                   # (22:37) they are fighting each other right now
                if _human_led(a) or _human_led(b):
                    for x, y in ((a, b), (b, a)):              # human president: the NPCs only advise
                        spk = next((m for m in npc_of(x) if m["state"] == "active"), None)
                        if spk and _human_led(x):
                            npc_say(x, spk, ("dipadvise", y), lambda lang, _y=y, _l=leader: {
                                "zh-cn": f"建议总统与{nation_name(_y, lang)}结盟，一起对抗{nation_name(_l, lang)}。",
                                "zh-tw": f"建議總統與{nation_name(_y, lang)}結盟，一起對抗{nation_name(_l, lang)}。"}.get(
                                lang, f"Advice: ally with {nation_name(_y, lang)} against {nation_name(_l, lang)}."), now, gap=3600)
                    continue
                set_alliance(a, b, True, f"共同对抗{nation_name(leader, 'zh-cn')}", f"共同對抗{nation_name(leader, 'zh-tw')}",
                             f"together against {nation_name(leader, 'en')}")
                busy |= {a, b}
                break
            if cands[i] in busy:
                break

def npc_assist(now):
    """user 2026-10-23 12:26: when players OR NPCs attack a province (a running battle), idle NPCs of their nation and of
    its allies on the same planet march in at once to help capture the POCs / destroy the enemy (they enter the battle
    through a gate on arrival, npc_join_attack)."""
    for pid, B in list(BATTLES.items()):
        if B.get("won") or B.get("ambush") or pid >= 100000000 or B.get("sim") or B.get("npc_raid") or B.get("hunt"):
            continue
        own = B.get("owner")
        if own is None or own.w.is_closing():
            continue
        dfd = B.get("defender") or province_owner(pid)
        sides = set()
        if B.get("npc_attacker"):
            sides.add(B["npc_attacker"])
        for o in B.get("members", ()):
            if not getattr(o, "spectator", False) and not o.w.is_closing():
                sn = side_nation(o)
                if not dfd or not same_side(sn, dfd):
                    sides.add(sn)
        for X in sides:
            # user 2026-10-23 21:09: help where it is needed - a side that is losing gets help at once and more of it,
            # a side that clearly wins gets none.  (Players fighting aliens on neutral land are a side too.)
            me_, them_ = side_strength(B, X)
            ratio = me_ / max(1.0, them_)
            if them_ <= 0 or ratio > 1.8:
                continue
            if random.random() > (1.0 if ratio < 1.0 else NPC_ASSIST_CHANCE):
                continue
            if any(not ally_client_ok(o) for o in B.get("members", ()) if not getattr(o, "spectator", False)
                   and same_side(side_nation(o), X) and not o.w.is_closing()):
                continue                              # old client: allied NPC units on its map crash it
            helpers = [m for m in npc_all() if m["task"] and m["task"].get("kind") == "attack" and m["task"].get("target") == pid
                       and same_side(m["nation"], X)]
            if len(helpers) >= NPC_ASSIST_MAX + (2 if ratio < 0.6 else 0):
                continue
            nations = {X} | {b_ if a_ == X else a_ for (a_, b_) in NATION_ALLIES if X in (a_, b_)}
            idle = [m for nat in nations for m in _npc_idle_of(nat, now) if nation_planet(m["nation"]) == pid // 100000]
            idle = [m for m in idle if not (dfd and same_side(m["nation"], dfd))]
            best = None
            for m in idle:
                path, _sec = npc_march_path(m, pid, now)          # from where it is now (no jumping)
                if path and len(path) - 1 <= NPC_ASSIST_STEPS and (best is None or len(path) < best[0]):
                    best = (len(path), m)
            if best is None:
                continue
            m = best[1]
            npc_send([m], {"pid": pid, "owner": dfd, "kind": "assist", "garrison": 0, "dist_cap": best[0] - 1, "def_power": 0.0}, now)
            if m.get("task"):
                as_reinforcement(m, now)
                _help_notice(B, X, m, m["task"]["arrive"] - now)
                log(f"   NPC: {m['name']} (nation {m['nation']}) marches to help the attack of nation {X} on {pid} "
                    f"(force ratio {ratio:.2f})")

NPC_GHOST_BATTLES = True       # False = the old abstract sieges / raid windows
NPC_GHOST_DEPLOY = 12          # units one NPC brings onto the map at a time (its next squads follow like F7)
NPC_OPEN_PER_TICK = 2          # real battles opened per NPC tick at most (CPU: ~50-180 ms each before the warm-up)
_OPEN_BUDGET = [NPC_OPEN_PER_TICK]

async def npc_warm_units():
    """compute the battle loadout of every (unit kind, level) the NPC armies use, one per event-loop turn, so opening
    a battle later does not stall the server (each new one costs an equipment search of ~20 ms)."""
    await asyncio.sleep(20)
    n_new, t0 = 0, time.monotonic()
    for n in list(npc_all()):
        for name, lv in list(n["squad"]):
            if (name, int(lv)) in _NPC_UNITS:
                continue
            try:
                npc_unit(name, lv)
                n_new += 1
            except Exception:
                pass
            await asyncio.sleep(0)
    log(f"   NPC: {n_new} unit loadouts prepared in the background ({time.monotonic() - t0:.0f}s)")
try:
    _WALK = data_json("walk_grids.json")
except Exception:
    _WALK = {}                 # tools/gen_walk_grids.py; without it the units walk in straight lines
_GRIDS = {}

def _walk_grid(name):
    if name not in _GRIDS:
        e = _WALK.get(name or "")
        _GRIDS[name] = BSIM.Grid.from_entry(e) if e else None
    return _GRIDS[name]

class _GhostW:
    def is_closing(self):
        return False

class Ghost:
    """stands in for the creator of an NPC battle while no player is on the map (sends go nowhere)."""
    is_ghost = True
    spectator = True
    logged_in = False
    join_mode = 1                       # players may always join (no permission dialog)
    def __init__(self, mapid, nation):
        self.acc = f"~npc{nation}"
        self.map, self.side_nation, self.cmd = mapid, nation, {"nation": nation, "look": 1}
        self.targets, self.pocs, self.battle, self.battle_gen = {}, {}, None, 1
        self.t0 = time.monotonic()
        self.alien_meta = self.npc_extra = None
        self.unit_pos, self.alive_units, self.attacks, self.last_hitter = {}, set(), {}, {}
        self.w = _GhostW()
        self.poc_won = False
    def send(self, *a, **k):
        pass

def _live(B):
    return [o for o in B["members"] if not o.w.is_closing()]

def _npc_put_squad(s, nid, n, per, home, mode, poc=None, hp_mult=1.0, start=None):
    units = npc_battle_units(n, per, nid, ctx=s)
    per = max(per, len(units))
    if not units:
        return False
    NPC_RT[n["id"]] = {"B": s.battle, "dead": 0, "units": len(units), "used": set(), "waves": 0, "wave_t": 0, "per": per,
                       "home": home, "poc": poc, "mode": mode, "nid": nid, "hp_mult": hp_mult, "ally": False, "start": start}
    npc_put_units(s, nid, n, units, home, mode, poc, hp_mult, False, start=start)
    return True

def npc_open_battle(pid, ns, now, ambush=None):
    """the NPCs ns arrive in province pid: a real battle starts there (BATTLES[pid], ghost creator).  Neutral: the alien
    garrison is on the map; owned: the owner's NPC defenders hold the POCs.  ambush = {"d": nation, "d_ns": [...]}: an
    NPC-vs-NPC ambush on the road (no POCs, the side that is wiped out loses)."""
    if pid in BATTLES:
        return False
    nid = ns[0]["nation"]
    # user 2026-10-25 12:05: NO battle without POCs any more - an interception is an ordinary province battle: the
    # province's owner defends (the ambushed squads hold its POCs), the interceptors attack, POCs decide.
    NPC_RESULT.pop(pid, None)                     # a result of an earlier battle here must not decide this one
    owner = province_owner(pid)
    g = Ghost(pid, nid)
    tier, _dist, _cave, name = alien_context(g, pid)
    pocs = province_pocs(pid)
    if ambush and not pocs:
        log(f"   NPC: interception battle on {pid} not opened - the province has no POC")
        return False
    g.pocs = {p[0]: {"x": p[1], "y": p[2], "strength": p[3], "progress": p[3], "owner": p[5], "capturing": False} for p in pocs}
    x, y = sim_arrival(pid, g)
    spots = sorted((tuple(p) for p in SPAWN_SPOTS.get(name or "", [])), key=lambda p: (p[0] - x) ** 2 + (p[1] - y) ** 2) or [(x, y)]
    homes = [spots[i % min(len(spots), 4)] for i in range(len(ns))]
    budget = min(NPC_BATTLE_UNITS[1], NPC_GHOST_DEPLOY * len(ns))      # their next squads follow (F7-like waves)
    B = BF.new_battle(map=pid, t0=g.t0, targets=g.targets, pocs=g.pocs, members=set(), owner=g, ghost=g,
                      defender=owner, npc_attacker=nid, hunt=bool(ns[0]["task"].get("hunt")),
                      opened=now)
    g.battle = B
    _pth = (ns[0].get("task") or {}).get("path") or []
    _frm = _pth[-2] if len(_pth) >= 2 else None      # (10-24 12:29) the gate of the road it marched in on
    if not owner and not ambush:
        g.pocs_pending = [(p[1], p[2]) for p in pocs]
        spawn_aliens_initial(g, pid, "province", x, y)
        npc_spawn(g, pid, nid, ns, budget, homes, "assault", x, y, True, keep_meta=True,
                  starts=gate_starts(pid, len(ns), nid, frm=_frm))
    else:
        npc_spawn(g, pid, nid, ns, budget, homes, "assault", x, y, True, starts=gate_starts(pid, len(ns), nid, frm=_frm))
    if ambush and ambush.get("d_ns"):             # the ambushed squads hold the POCs of the province they were marching through
        for i, n in enumerate(ambush["d_ns"]):
            pc = pocs[i % len(pocs)]
            _npc_put_squad(g, ambush["d"], n, NPC_GHOST_DEPLOY, (pc[1], pc[2]), "hold", pc, 1.0,
                           start=(gate_starts(pid, 1 + i, ambush["d"]) or [None])[-1])
    elif owner:                                   # the owner's NPCs defend (like npc_spawn_defenders)
        cand = [n for n in npc_of(owner) if n["state"] == "active" and now >= n["rest_until"] and not n["task"]]
        cand.sort(key=lambda n: -NP.power_of(n))
        cl = npc_closeness(pid)
        picked = cand[:NPC_DEFENDERS_MAX + int(round(3 * cl))]
        per = max(4, int(NPC_BATTLE_UNITS[1] * (1 + cl)) // max(1, len(picked)))      # 36 .. 72 defenders in all
        # user 2026-10-23 16:22: no NPC appears without walking there - only the ones already in pid (the capital)
        # fight at once, the others march in from where they are and enter through a gate (npc_reinforce_enter)
        here_ = [n for n in picked if npc_here(n, now) == pid]
        for i, n in enumerate([n for n in picked if npc_here(n, now) != pid]):
            pth, sec = npc_march_path(n, pid, now, NPC_REINF_PACE)
            if not pth:
                continue
            rt_ = pth[-2] if len(pth) >= 2 else None
            n["task"] = {"kind": "defend", "target": pid, "since": now, "phase": "march", "depart": now,
                         "arrive": now + reinf_seconds(len(pth) - 1), "route": rt_, "origin": rt_ or pid, "path": pth,
                         "slot": len(here_) + i, "budget": per}
            n.pop("walk", None)
            log(f"   NPC: {n['name']} (nation {owner}) marches to defend {pid} (arrives in {n['task']['arrive'] - now:.0f}s)")
        picked = here_
        for i, n in enumerate(picked):
            pc = pocs[i % len(pocs)] if pocs else None
            n["task"] = {"kind": "defend", "target": pid, "phase": "battle", "since": now}
            _npc_put_squad(g, owner, n, per, (pc[1], pc[2]) if pc else (x, y), "hold", pc, 1.0 + 0.5 * cl,
                           start=(gate_starts(pid, 1 + i, owner) or [None])[-1])     # (10-24) only gates to its own side
    if not any(tg.get("npc") is not None for tg in g.targets.values()):
        log(f"   NPC: no unit could be put on {pid} - battle not opened")
        return False
    BATTLES[pid] = B
    npc_battle_started(g, B)
    for i, rt in NPC_RT.items():
        if rt.get("B") is None and any(tg.get("npc") == i for tg in g.targets.values()):
            rt["B"] = B
    loop = asyncio.get_event_loop()
    if g.alien_meta and not g.alien_meta.get("npc"):
        loop.create_task(alien_ai(g, g.battle_gen))
    loop.create_task(npc_ai(g, g.battle_gen))
    if g.pocs:
        loop.create_task(poc_loop(g, g.battle_gen))
    loop.create_task(battle_timer(B))
    loop.call_soon(lambda: pull_into_battle(B, pid, g))          # (19:26) players standing in pid join like defenders
    log(f"   NPC: REAL battle on {pid} ({'ambush' if ambush else 'hunt' if B['hunt'] else 'assault'}) by nation {nid} "
        f"{[n['name'] for n in ns]} vs {'aliens' if not owner and not ambush else 'nation ' + str(ambush['d'] if ambush else owner)}: "
        f"{len(g.targets)} unit(s) on the map")
    return True

def _ghost_death(B, tid, tg):
    g = B["ghost"]
    B["targets"].pop(tid, None)
    dead_aliens(g).add(tid)
    alien_removed(g, tid, tg)

NPC_WORKERS = max(1, min(4, (os.cpu_count() or 2) - 1))     # simulation worker processes
_POOL = [None]

def ghost_pool():
    """the worker processes (created on first use; None = simulate in the game loop, e.g. in tests)."""
    if _POOL[0] is None and NPC_WORKERS > 0:
        try:
            import concurrent.futures, multiprocessing
            _POOL[0] = concurrent.futures.ProcessPoolExecutor(max_workers=NPC_WORKERS,
                                                              mp_context=multiprocessing.get_context(
                "fork" if "fork" in multiprocessing.get_all_start_methods() else "spawn"))
            log(f"   NPC simulation: {NPC_WORKERS} worker process(es)")
        except Exception as e:
            log(f"   NPC simulation workers unavailable ({e!r}) - simulating in the game loop")
            _POOL[0] = False
    return _POOL[0] or None

def ghost_payload(B, now, dt):
    g = B["ghost"]
    pid = B["map"]
    tier = PLANET_TIER.get((pid // 100000) % 1000, 1)
    params = {"map": alien_context(g, pid)[3], "walk_path": os.path.join(os.path.dirname(os.path.abspath(__file__)), "walk_grids.json"),
              "now": now, "dt": dt, "aggro": AL.AGGRO[tier], "leash": AL.LEASH[tier], "focus": AL.FOCUS_MAX,
              "poc_radius": POC_RADIUS, "hunt_from": (g.alien_meta or {}).get("hunt_from", 0),
              "allies": [list(x) for x in NATION_ALLIES], "damage_types": bool(DAMAGE_TYPES),
              "brain": USE_BRAIN, "tier": tier}
    return BSIM.pack(B["targets"], B["pocs"], lambda tg: tg.get("nation") if tg.get("npc") is not None else ALIEN_NATION,
                     params)

def ghost_apply(B, res):
    """results of a worker step -> the battle (units that died or vanished meanwhile are skipped)."""
    for tid, f in res["units"].items():
        tg = B["targets"].get(tid)
        if tg is None or tg.get("hp", 0) <= 0:
            continue
        tg.update(f)                                  # nothing else changes a simulated battle while no player is there
    for tid in res["dead"]:
        tg = B["targets"].get(tid)
        if tg is not None:
            tg["hp"] = min(tg.get("hp", 0), 0)
            _ghost_death(B, tid, tg)

def ghost_step(B, now, dt=1.0, result=None):
    """one simulated step of a battle without players (result = a worker's step, else simulated here)."""
    g = B["ghost"]
    pid = B["map"]
    if result is not None:
        ghost_apply(B, result)
        return _ghost_after(B, now, dt)
    tier = PLANET_TIER.get((pid // 100000) % 1000, 1)
    ctx = BSIM.Ctx()
    ctx.grid = _walk_grid(alien_context(g, pid)[3])
    ctx.now, ctx.aggro, ctx.leash, ctx.focus, ctx.poc_radius = now, AL.AGGRO[tier], AL.LEASH[tier], AL.FOCUS_MAX, POC_RADIUS
    ctx.hunt_from = (g.alien_meta or {}).get("hunt_from", 0)
    ctx.brain, ctx.tier = USE_BRAIN, tier
    ctx.side_of = lambda tg: tg.get("nation") if tg.get("npc") is not None else ALIEN_NATION
    ctx.same_side = same_side
    ctx.damage = hit_damage
    ctx.on_death = lambda tid, tg: _ghost_death(B, tid, tg)
    BSIM.step(B["targets"], B["pocs"], ctx, dt)
    _ghost_after(B, now, dt)

def _ghost_after(B, now, dt):
    g = B["ghost"]
    for tg in B["targets"].values():              # wounds are remembered (the NPC picks healthy units next time)
        if tg.get("npc") is not None and tg.get("idx") is not None:
            n_ = npc_state()["npcs"].get(str(tg["npc"]))
            if n_ is not None:
                NP.health(n_)[tg["idx"]] = max(0.0, min(1.0, tg["hp"] / max(1, tg["max"])))
    npc_fresh_wave(g, B, now)
    try:
        ghost_withdraw(B, now)
    except Exception as e:
        log(f"   ghost withdraw error on {B.get('map')}: {e!r}")
    _ghost_pocs(B, dt)
    ghost_check_end(B, now)
    try:
        ghost_stale_check(B, now)
    except Exception as e:
        log(f"   ghost stale check error on {B.get('map')}: {e!r}")

GHOST_STALE_S = 30.0

def ghost_stale_check(B, now):
    """user 2026-10-25 11:53 (province 57: 0 NPC in / heading for it, the countdown still ran): a battle with no NPC unit
    on the map, no reserve and no NPC marching to it is an empty shell - end it by the TIME UP rule now instead of
    waiting for the 30 minutes (POC majority decides)."""
    if B.get("won"):
        return
    pid = B.get("map")
    if any(tg.get("npc") is not None and tg.get("hp", 0) > 0 for tg in B["targets"].values()):
        B.pop("stale_since", None)
        return
    if _reserve(B, B.get("npc_attacker")) or _reserve(B, B.get("npc_attacker"), enemy=True):
        B.pop("stale_since", None)
        return
    for n in npc_all():
        tk = n.get("task") or {}
        if tk.get("target") == pid and tk.get("phase") in ("march", "support"):
            B.pop("stale_since", None)
            return
    t0 = B.setdefault("stale_since", now)
    if now - t0 >= GHOST_STALE_S:
        log(f"   ghost battle {pid}: no NPC unit, reserve or marching help for {now - t0:.0f} s - ended by the time-up rule")
        ghost_time_up(B)

# STRATEGY of an NPC side in a battle = the task its commanders carry (n["task"]["kind"]):
#   attack            assault: win by taking the POCs - may give up when it is hopeless and has no help coming
#   defend / support  hold until time is up or help arrives (defenders win by time)  -> never gives up
#   intercept / ambushed  DELAY: a small force that ties down a big one on purpose (user 2026-10-25 10:52: "以少拖多")
#                     or waits for follow-up support  -> never runs away because of low HP
NPC_GIVEUP_ENABLED = False     # fight to the end: only wipe-out or TIME UP ends an NPC side's battle
NPC_STRATEGY_HOLD = ("defend", "support", "intercept", "patrol")

def npc_side_strategy(B, nat):
    """-> (strategy, why): 'delay' | 'hold' | 'assault' for the side nat in battle B."""
    pid = B.get("map")
    if B.get("ambush") or pid in AMBUSH:
        return "delay", "blockade / interception"
    kinds = set()
    for n in npc_all():
        tk = n.get("task") or {}
        if not same_side(n["nation"], nat):
            continue
        if tk.get("target") == pid or NPC_RT.get(n["id"], {}).get("B") is B:
            kinds.add("ambushed" if tk.get("phase") == "ambushed" else tk.get("kind"))
            if tk.get("phase") in ("march", "support") and tk.get("target") == pid:
                return "delay", "help is marching to this battle"
    if kinds & {"intercept", "ambushed"}:
        return "delay", "interception"
    dfd = B.get("defender") or 0
    if (dfd and same_side(nat, dfd)) or kinds & set(NPC_STRATEGY_HOLD):
        return "hold", "defence: win by time"
    return "assault", "attack"

def npc_side_may_giveup(B, nat):
    """user 2026-10-25 10:54: an ASSAULT fights to the death, a defence holds, a delaying force ties the enemy down or waits
    for help - NO strategy runs away because its HP is low (NPC_GIVEUP_ENABLED = False).  The strategy is still logged."""
    st = npc_side_strategy(B, nat)
    seen = B.setdefault("strategy_logged", {})
    if seen.get(nat) != st[0]:
        seen[nat] = st[0]
        log(f"   NPC strategy on {B.get('map')}: nation {nat} = {st[0]} ({st[1]})")
    if not NPC_GIVEUP_ENABLED:
        return False
    return st[0] == "assault" and not _reserve(B, nat)

GHOST_WITHDRAW_S = 15.0       # s a simulated unit needs to walk out through its gate

def ghost_withdraw(B, now):
    """user 2026-10-25: a battle without a player only ran the simulation, never the parts of npc_step that live in the
    clients' battle loop: units flagged 'withdraw' (a beaten side's give-up, units pulled for a swap, set while a player
    was there) stayed on the map for ever and kept counting as alive, and a hopeless side never gave up - the battle only
    ended at TIME UP, and only a real client's arrival (npc_step) got it moving.  Here: (1) a hopeless side gives up
    like in npc_step (force ratio < NPC_GIVEUP_RATIO for NPC_GIVEUP_AFTER s, after NPC_GIVEUP_GRACE s on the map),
    (2) flagged units leave after GHOST_WITHDRAW_S s."""
    T = B["targets"]
    sides = {}
    for tg in T.values():
        if tg.get("hp", 0) <= 0 or tg.get("hive") or tg.get("withdraw"):
            continue
        nat = tg.get("nation") if tg.get("npc") is not None else ALIEN_NATION
        sides[nat] = sides.get(nat, 0.0) + max(0.0, tg.get("hp", 0))
    seen = B.setdefault("side_seen", {})
    gu = B.setdefault("side_weak", {})
    for nat, hp in sides.items():
        if nat == ALIEN_NATION:
            continue
        seen.setdefault(nat, now)
        foe = sum(h for n2, h in sides.items() if not same_side(n2, nat))
        ratio = hp / foe if foe > 0 else 9.9
        if ratio < NPC_GIVEUP_RATIO and now - seen[nat] >= NPC_GIVEUP_GRACE and npc_side_may_giveup(B, nat):
            gu.setdefault(nat, now)
            if now - gu[nat] >= NPC_GIVEUP_AFTER:
                n_out = 0
                for tg in T.values():
                    if tg.get("npc") is not None and tg.get("nation") == nat and tg.get("hp", 0) > 0 and not tg.get("withdraw"):
                        tg["withdraw"], tg["wd_t"] = True, now
                        n_out += 1
                if n_out:
                    log(f"   ghost battle {B['map']}: nation {nat} is beaten (force ratio {ratio:.2f}) - {n_out} unit(s) retreat")
        else:
            gu.pop(nat, None)
    gone = 0
    for tid, tg in list(T.items()):
        if tg.get("withdraw") and tg.get("hp", 0) > 0:
            tg.setdefault("wd_t", now)
            if now - tg["wd_t"] >= GHOST_WITHDRAW_S:
                T.pop(tid, None)
                dead_aliens(B["ghost"]).add(tid)
                tg["_tid"] = tid
                npc_unit_left(tg)
                gone += 1
    if gone:
        log(f"   ghost battle {B['map']}: {gone} withdrawing unit(s) left the map")

def _ghost_pocs(B, dt):
    """POC capture while no player is on the map (same speed as poc_loop for NPC capturers)."""
    for pid_, p in B["pocs"].items():
        caps = [tg for tg in B["targets"].values() if tg.get("npc") is not None and tg.get("on_poc") == pid_
                and tg.get("hp", 0) > 0 and not same_side(tg.get("nation"), p["owner"])]
        if caps:
            nat = caps[0]["nation"]
            if not p["capturing"] or p.get("cap_nat") != nat:
                p["capturing"], p["progress"], p["cap_nat"] = True, p["strength"], nat
            else:
                p["progress"] -= POC_RATE * dt
            if p["progress"] < -0.15 * p["strength"]:
                p["owner"], p["progress"], p["capturing"] = nat, 0, False
                log(f"   POC {pid_} of {B['map']}: CAPTURED by nation {nat} (simulated)")
        elif p["capturing"]:
            p["capturing"] = False

def _side_alive(B, nat):
    return sum(1 for tg in B["targets"].values() if tg.get("hp", 0) > 0 and not tg.get("hive")
               and same_side(tg.get("nation") if tg.get("npc") is not None else ALIEN_NATION, nat))

def _reserve(B, nat, enemy=False):
    return any(rt.get("B") is B and rt.get("nid") is not None and rt.get("units", 0) > 0
               and rt.get("waves", 0) < NPC_WAVES_MAX
               and (not same_side(rt["nid"], nat) if enemy else same_side(rt["nid"], nat))
               for rt in NPC_RT.values())

def ghost_check_end(B, now):
    """NPC battle running check (every step, players on the map or not): battlefield.judge kind 'npc'."""
    if not B.get("won"):
        battle_judge(None, "tick", B)

def ghost_time_up(B):
    """NPC battle TIME UP: battlefield.judge kind 'npc', event 'time'."""
    if not B.get("won"):
        battle_judge(None, "time", B)

def ghost_finish(B, att_won, win_side=None):
    """result of a battle an NPC nation started (with or without players on the map)."""
    if B.get("won"):
        return
    B["won"] = True
    pid, A = B["map"], B.get("npc_attacker")
    NPC_RESULT[pid] = bool(att_won)
    RAIDS.pop(pid, None)
    old = province_owner(pid)
    if att_won and A and old and old != A and same_side(old, A):
        att_won = False                  # (22:37) allied meanwhile: an ally's province is never taken
        log(f"   NPC battle on {pid}: nation {A} and the owner {old} are allies now - no capture")
    if att_won and A and not B.get("hunt") and not B.get("ambush") and pid not in AMBUSH and old != A:   # (interceptions never take it)
        capture_province(pid, A)
    live = _live(B)
    for o in list(live):
        # (2026-10-25 audit C) winners = the attackers, or when they lost the defender's side / the third side that
        # holds every POC; a third-party player is not a winner merely for not being an attacker
        _ws = A if att_won else (win_side if win_side is not None else (B.get("defender") or old))
        spawn(end_battle(o, o.battle_gen, won=(not getattr(o, "spectator", False)
                                                and bool(_ws) and same_side(side_nation(o), _ws))))
    if not live and BATTLES.get(pid) is B:
        del BATTLES[pid]
    log(f"   NPC battle on {pid} over: attackers of nation {A} {'WON' if att_won else 'lost'} "
        f"({'with players' if live else 'simulated'}, {int(time.monotonic() - B['t0'])}s)")

def ghost_handover(B):
    """the first player enters a simulated battle: every unit is where the simulation left it; the AIs give new orders."""
    for tg in B["targets"].values():
        tg["state"], tg["target"], tg["mv"], tg["dest"], tg["on_poc"] = "idle", None, None, None, None
        # (audit S1) states the clients never got while the server simulated: the brain sends them again
        tg["route"] = None
        tg.pop("wd_sent", None)
        tg["cloaked"] = False
        tg["detect_on"] = False
        tg.pop("modes", None)
        if tg.get("pos"):
            tg["x"], tg["y"] = int(tg["pos"][0]), int(tg["pos"][1])
    for tid in list(B["targets"]):
        CLOAKED.pop(tid, None)
        SHIELDS.pop(tid, None)
    B.pop("_ord_last", None)
    B.pop("_ord_pend", None)
    log(f"   battle on {B['map']}: player enters the simulated battle ({len(B['targets'])} unit(s))")

def ghost_resume(B):
    """the last player left: the server simulates on from the estimated positions."""
    now = time.time()
    g = B["ghost"]
    grid = _walk_grid(alien_context(g, B["map"])[3])
    for tg in B["targets"].values():
        p = _npc_est_pos(tg, now) if tg.get("npc") is not None else tg.get("pos")
        if p is None:
            continue
        if grid is not None:
            p = grid.snap(p) or p
        tg["pos"] = (float(p[0]), float(p[1]))
        tg["x"], tg["y"] = int(p[0]), int(p[1])
        tg["state"], tg["target"], tg["mv"] = "idle", None, None
    B["owner"] = g
    log(f"   battle on {B['map']}: no player left - the server simulates on")

GHOST_TICK = 2.0            # s per simulation step (CPU: ~5 ms per battle and step, + path fields)

async def ghost_cycle():
    """steps every battle without players; the battles are spread over the tick so the game traffic is never held up
    for long."""
    await asyncio.sleep(3)
    while True:
        t0 = time.monotonic()
        BSIM.Grid.spent = 0
        todo = [(pid, B) for pid, B in list(BATTLES.items()) if B.get("ghost") and not B.get("won") and not _live(B)]
        pool = ghost_pool() if todo else None
        if pool is not None:
            # every battle steps in parallel in the worker processes; the game loop only packs and applies
            loop = asyncio.get_event_loop()
            futs = []
            for pid, B in todo:
                try:
                    futs.append((pid, B, loop.run_in_executor(pool, BSIM.step_remote, ghost_payload(B, time.time(), GHOST_TICK))))
                except Exception as e:
                    log(f"   ghost battle {pid}: worker submit failed {e!r}")
            for pid, B, fu in futs:
                try:
                    res = await fu
                except Exception as e:
                    log(f"   ghost battle {pid}: worker step failed {e!r}")
                    continue
                if BATTLES.get(pid) is not B or B.get("won") or _live(B):
                    continue                             # a player entered meanwhile: the clients simulate now
                try:
                    ghost_step(B, time.time(), dt=GHOST_TICK, result=res)
                except Exception as e:
                    import traceback
                    log(f"   ghost battle {pid} error: {e!r} {traceback.format_exc()[-300:]}")
                await asyncio.sleep(0)
            todo = []
        for pid, B in todo:
            if BATTLES.get(pid) is not B or B.get("won") or _live(B):
                continue
            try:
                _t1 = time.monotonic()
                ghost_step(B, time.time(), dt=GHOST_TICK)
                if time.monotonic() - _t1 > 0.1:
                    log(f"   ghost battle {pid}: step took {(time.monotonic() - _t1) * 1000:.0f} ms ({len(B['targets'])} units)")
            except Exception as e:
                import traceback
                log(f"   ghost battle {pid} error: {e!r} {traceback.format_exc()[-300:]}")
            await asyncio.sleep(0)                       # let the network handlers run between two battles
        await asyncio.sleep(max(0.05, GHOST_TICK - (time.monotonic() - t0)))

def npc_reinforce_enter(n, now):
    """a marching NPC reinforcement reaches the battle: its squad enters the map at a POC of its nation."""
    t = n["task"]
    mid, dfd = t["target"], n["nation"]
    B = BATTLES.get(mid)
    own = battle_ctx(B) if B else None               # (audit A/B/J) the battle's context, not whoever commands it now
    pocs = [(pid, p["x"], p["y"], p["strength"], POC_TYPE, p["owner"]) for pid, p in B["pocs"].items()] if B else []
    if B is None or B.get("won") or own is None or own.w.is_closing() or not pocs:
        npc_release(n, now, random.uniform(60, 300))
        log(f"   NPC: {n['name']} arrived at {mid} - the battle is over, goes home "
            f"({'no battle' if B is None else 'won' if B.get('won') else 'no commander' if own is None or own.w.is_closing() else 'no POC'})")
        return
    cl = npc_closeness(mid)
    first = not B.get("npc_side")
    t.update(phase="battle", since=now, entered=now)
    # (user 2026-10-28 00:26 "a player attacks and loses at once"): log 600104 - an NPC of the PLAYER's nation had joined
    # his attack (npc_side 3, npc_raid), then the owner's defender ZedKnox entered and OVERWROTE npc_side with 1 while
    # npc_raid stayed set -> the defender's own POC counted as "the raiders of nation 1 captured every POC" 4 s in.
    # A defender entering never takes over the raiding side.
    if first:
        B["npc_side"] = dfd
        B["npc_raid"] = False
    k = t.get("slot", 0)
    homes = [(pocs[k % len(pocs)][1], pocs[k % len(pocs)][2])]
    NPC_RT.pop(n["id"], None)
    npc_spawn(own, mid, dfd, [n], t.get("budget") or 6 + int(round(4 * cl)), homes, "hold", 0, 0, False, pocs,
              hp_mult=1.0 + 0.5 * cl, starts=gate_starts(mid, 1, dfd, None, frm=t.get("route") or t.get("origin")),
              keep_meta=bool(getattr(own, "alien_meta", None)))     # (audit C7) the battle's meta stays
    if NPC_RT.get(n["id"], {}).get("units", 0) <= 0:          # (06:16) nothing of it got onto the map
        npc_release(n, now, random.uniform(60, 300))
        log(f"   NPC: {n['name']} got no unit onto {mid} - goes home")
        return
    npc_rt_attach(n["id"], B, dfd)
    B.setdefault("npc_ids", []).append(n["id"])
    if first:
        spawn(npc_ai(own, (getattr(own, "battle_gen", 0) or 0) + 1))
    log(f"   NPC: {n['name']} (nation {dfd}) reinforces the defence of {mid}")
    npc_dirty()

# ---- INTERCEPTION (user 2026-10-22 21:30, answers 1.B 2.B): an NPC nation that fights somewhere watches the enemy's
# reinforcements - NPC squads marching to the battle AND players walking toward it on the strategic map - and sends
# idle commanders to the province on their route.  There they BLOCK the road: an NPC reinforcement is stopped and
# fought (abstract, or a REAL battle with the units of both sides as soon as a player enters that province); a player
# finds the blockers on the map when he enters the province (a real battle, other players may join).  A won ambush
# sends the reinforcement home wounded; an interception never takes the province (no effect on the expansion pace).
NPC_INTERCEPT_CHANCE = 0.6     # per reinforcement seen
NPC_INTERCEPT_MAX = 2          # interceptions of one nation under way at the same time
NPC_INTERCEPT_SEEN = 600       # s: one player / target pair is looked at once in this time
NPC_AMBUSH_BATTLES = False      # user 2026-10-25: an ambush battle without POCs no longer exists (see npc_open_battle)
NPC_AMBUSH_WAIT = 240          # s: a blockade waits this long for the player it was set up for
NPC_BLOCKADE_BATTLE = True     # (2026-10-27 22:56) a blockade opens a real battle at once (owner's NPCs defend)
NPC_REINF_PACE = 0.75          # reinforcements march faster than an assault (march time x this)
# user 2026-10-24 07:16: the enemy's defenders walked 4 provinces while a helper NPC walked 1 - defenders had the
# reinforcement pace x up to 0.5 near their capital, a helper (sent as an 'assist' attack) the slow random assault pace
# (30-90 s per step).  Now EVERY reinforcement - defenders and helpers of either side - walks the same fixed time per
# province, and the ETA it announces is exactly that.
NPC_REINF_STEP = 40.0          # s per province step of any reinforcement march

def reinf_seconds(steps):
    return NPC_REINF_STEP * max(1, int(steps))

def as_reinforcement(m, now):
    """an NPC just sent to help (npc_send 'assist'): march at the reinforcement pace along its road."""
    t = m.get("task") or {}
    if t.get("path"):
        t["depart"], t["arrive"] = now, now + reinf_seconds(len(t["path"]) - 1)
        t["assist"] = True
NPC_INTERCEPT_PACE = 0.5       # interceptors are light, fast squads (march time x this)
NPC_AMBUSH_DEF = 1.25          # an ambushed squad fights back in formation (its power x this in the abstract ambush)
AMBUSH = {}                    # province -> {"R", "o", "o_ids", "d", "d_ids", "P", "acc", "B", "until"}   (runtime)
INTERCEPT_SEEN = {}            # (account, target province) -> time

def _route(a, b, ok=None):
    """shortest portal path a -> b (full province ids, both ends included) on one planet, None if none.
    ok(province id) -> False forbids a province as an INTERMEDIATE step (the end b is always allowed)."""
    if a is None or b is None or a // 100000 != b // 100000:
        return None
    base, s0, g = a // 100000 * 100000, a % 100000, b % 100000
    prev, q = {s0: None}, [s0]
    while q:
        x = q.pop(0)
        if x == g:
            break
        for y in PORTAL_LINKS.get(x, ()):
            if y not in prev and (ok is None or y == g or ok(base + y)):
                prev[y] = x
                q.append(y)
    if g not in prev:
        return None
    p, x = [], g
    while x is not None:
        p.append(base + x)
        x = prev[x]
    return p[::-1]

def npc_reinf_task(kind, nid, pid, now, n=None):
    """task of a reinforcement that marches from the capital (or where NPC n is now) to pid; route = the last province
    before pid."""
    cap = CAPITALS.get(nid)
    if n is not None:
        try:
            cap = npc_here(n, now) or cap              # (2026-10-23 16:22: from where it is - no jumping)
        except Exception:
            pass
    # user 2026-10-23 13:34: reinforcements marched THROUGH an enemy province that cut them off.  The road may only
    # cross provinces of the nation or its allies (the target itself is the battle); no such road -> cut off (None).
    path = _route(cap, pid, lambda q: same_side(province_owner(q), nid)) if cap is not None else None
    if not path:
        return None
    route = path[-2] if path and len(path) >= 3 else None
    steps = len(path) - 1 if path else 1               # (2026-10-23 15:09: the whole road, walked province by province)
    t = reinf_seconds(steps)
    return {"kind": kind, "target": pid, "since": now, "phase": "march", "depart": now, "arrive": now + t,
            "route": route, "origin": route or cap, "path": path}

def _in_ambush(i):
    return any(i in A.get("d_ids", ()) for A in AMBUSH.values())

def _npc_wound(n, f):
    hl = NP.health(n)
    for i in range(len(hl)):
        hl[i] = max(0.0, hl[i] * f)

def _say_lang(o, zh_cn, zh_tw, en, rgb=(255, 200, 120)):
    lang = _mail_lang(o)
    o.send(chat_line(0x0A, {"zh-cn": zh_cn, "zh-tw": zh_tw}.get(lang, en), rgb, tr=False))

def _notify_side(nid, zh_cn, zh_tw, en, rgb=(255, 200, 120)):
    notify_side(nid, en, rgb, zh_cn, zh_tw)            # (battle_rules: the one side notice)

def npc_hot_provinces():
    """province -> nations fighting there (battles, NPC assaults / raids)."""
    hot = {}
    for mid, B in list(BATTLES.items()):
        if mid >= 100000000 or B.get("sim") or B.get("won") or map_kind(mid) != "province":
            continue
        sides = {B.get("defender") or 0, B.get("npc_side") or 0}
        for o in B["members"]:
            if not getattr(o, "spectator", False):
                sides.add(side_nation(o))
        hot.setdefault(province_of(mid), set()).update(sides)
    for n in npc_all():
        t = n["task"]
        if t and t.get("kind") == "attack" and t.get("phase") in ("siege", "raid", "battle"):
            hot.setdefault(t["target"], set()).update({n["nation"], province_owner(t["target"]) or 0})
    for k in hot:
        hot[k].discard(0)
    return hot

def npc_intercept_scan(now):
    for k in [k for k, t in INTERCEPT_SEEN.items() if now - t > NPC_INTERCEPT_SEEN]:
        del INTERCEPT_SEEN[k]
    moves = []
    for n in npc_all():                     # NPC reinforcements on the road
        t = n["task"]
        if not t or t.get("kind") not in ("support", "defend") or t.get("phase") != "march" or not t.get("route") \
                or t.get("cut_tried") or t["arrive"] - now < 25:
            continue
        t["cut_tried"] = True
        P = t["target"]
        if t["kind"] == "support":
            opp = {m["nation"] for m in npc_all() if m["task"] and m["task"].get("kind") == "attack"
                   and m["task"].get("target") == P and not same_side(m["nation"], n["nation"])}
        else:
            B = BATTLES.get(P) or {}
            opp = {side_nation(o) for o in B.get("members", ()) if not getattr(o, "spectator", False)
                   and not same_side(side_nation(o), n["nation"])}
        opp.discard(0)
        if opp:
            moves.append({"N": n["nation"], "P": P, "R": t["route"], "eta": t["arrive"], "npc": n, "opp": opp})
    hot = None
    for o in list(ONLINE):                  # players walking toward a battle of their side
        mv = getattr(o, "moved", None)
        if not mv or now - mv[2] > 120 or not getattr(o, "logged_in", False) or getattr(o, "battle", None) \
                or o.w.is_closing():
            continue
        if hot is None:
            hot = npc_hot_provinces()
        N, a, c = side_nation(o), mv[0], mv[1]
        for P, sides in hot.items():
            if P // 100000 != c // 100000 or not any(same_side(N, x) for x in sides):
                continue
            opp = {x for x in sides if not same_side(x, N)}
            key = (o.acc, P)
            if not opp or key in INTERCEPT_SEEN:
                continue
            path = _route(c, P)
            if not path or not 3 <= len(path) <= 5:          # 2 .. 4 steps away
                continue
            pa = _route(a, P)
            if not pa or len(pa) <= len(path):               # not coming closer
                continue
            INTERCEPT_SEEN[key] = now
            moves.append({"N": N, "P": P, "R": path[1], "eta": None, "acc": o.acc, "opp": opp})
    for m in moves:
        if random.random() > NPC_INTERCEPT_CHANCE:
            continue
        for O in sorted(m["opp"], key=lambda x: -len(_npc_idle_of(x, now))):
            if npc_launch_intercept(O, m, now):
                break

def npc_launch_intercept(O, m, now):
    R, N = m["R"], m["N"]
    if R in BATTLES or R in RAIDS or R in AMBUSH or R in set(CAPITALS.values()) or R == m["P"]:
        return False
    own = province_owner(R)
    if own and not (same_side(own, O) or same_side(own, N)):
        return False                        # a third nation's land: not this road
    busy = {n["task"]["target"] for n in npc_of(O) if n["task"] and n["task"].get("kind") == "intercept"}
    if len(busy) >= NPC_INTERCEPT_MAX or R in busy:
        return False
    idle = [n for n in _npc_idle_of(O, now) if NP.readiness(n) >= NP.MIN_READY]
    if not idle:
        return False
    # user 2026-10-23 15:09: the interceptors WALK from where they are (the capital, or on their way home), province by
    # province, only through provinces of their side (12:10) - they no longer appear next to the road out of nowhere
    best, pths = None, {}
    for n in idle:
        p = npc_here(n, now) or CAPITALS.get(O)
        path = _route(p, R, lambda q: bool(province_owner(q)) and same_side(province_owner(q), O))
        if path:
            pths[n["id"]] = path
        if path and (best is None or len(path) < len(best)):
            best = path
    idle = [n for n in idle if n["id"] in pths and len(pths[n["id"]]) <= len(best or ()) + 1]   # (16:22: each walks its own road)
    if best is None:
        log(f"   NPC: nation {O} has no road through its own land to {R} - no interception")
        return False
    d = len(best) - 1
    if m.get("acc"):
        if d > 3:
            log(f"   NPC: nation {O} is {d} provinces from {R} - too far to block {m.get('acc')}")
            return False                    # players walk fast: only a nation close to the road blocks it
        arrive = now + NP.march_seconds(max(1, d)) * NPC_INTERCEPT_PACE
    else:
        if d > 8:                           # (the walk time decides below: arrive before the enemy does)
            log(f"   NPC: nation {O} is {d} provinces from {R} - too far to intercept")
            return False
        arrive = now + NP.march_seconds(max(1, d)) * NPC_INTERCEPT_PACE
        if arrive > m["eta"] - 5:
            log(f"   NPC: nation {O} cannot cut off {m['P']} at {R} in time ({d} province(s) to walk)")
            return False                    # too late
    need = NP.power_of(m["npc"]) if m.get("npc") else 0.0
    idle.sort(key=lambda n: -NP.power_of(n))
    idle = idle[:max(1, (len(idle) + 1) // 2)]          # one of the stronger half (not always the very best)
    random.shuffle(idle)
    team = idle[:2] if len(idle) > 1 and NP.power_of(idle[0]) < need * NPC_AMBUSH_DEF else idle[:1]
    st = npc_state()
    gid = st["group"]
    st["group"] += 1
    origin = best[-2] if len(best) >= 2 else R
    pace_ = (arrive - now) / max(1.0, NP.march_seconds(max(1, d)))
    arrive = max(arrive, max(now + NP.march_seconds(max(1, len(pths[n["id"]]) - 1)) * pace_ for n in team))
    for n in team:
        pn = pths[n["id"]]
        n["task"] = {"kind": "intercept", "target": R, "origin": pn[-2] if len(pn) >= 2 else R, "depart": now,
                     "arrive": arrive, "phase": "march", "since": now, "group": gid, "vs": N, "P": m["P"],
                     "ref": [m["npc"]["id"]] if m.get("npc") else [], "acc": m.get("acc"), "wait": 0, "path": pn}
        n.pop("walk", None)
    npc_dirty()
    who = m["npc"]["name"] if m.get("npc") else m["acc"]
    log(f"   NPC: {[n['name'] for n in team]} (nation {O}) go to {R} to cut off {who} (nation {N}) on the way to "
        f"{m['P']}, arrive in {arrive - now:.0f}s")
    return True

def npc_intercept_step(ns, now):
    t = ns[0]["task"]
    R, O = t["target"], ns[0]["nation"]
    ph = t.get("phase")
    if ph == "march":
        if now < t["arrive"]:
            return
        if R in BATTLES or R in AMBUSH:
            for n in ns:
                npc_release(n, now, random.uniform(60, 240))
            log(f"   NPC: interception at {R} given up (road busy)")
            return
        d_ids = []
        for i in t.get("ref") or []:
            m = npc_state()["npcs"].get(str(i))
            mt = m and m.get("task")
            if mt and mt.get("kind") in ("support", "defend") and mt.get("phase") == "march" and mt.get("route") == R \
                    and now < mt["arrive"]:
                mt["phase"], mt["left"] = "ambushed", max(10.0, mt["arrive"] - now)
                d_ids.append(i)
        if t.get("ref") and not d_ids:
            for n in ns:
                npc_release(n, now, random.uniform(60, 240))
            log(f"   NPC: interception at {R} too late - the reinforcement has passed")
            return
        acc = t.get("acc")
        AMBUSH[R] = {"R": R, "o": O, "o_ids": [n["id"] for n in ns], "d": t["vs"], "d_ids": d_ids, "P": t["P"],
                     "acc": acc, "B": None, "t0": now,
                     "until": now + (NPC_AMBUSH_WAIT if acc else random.uniform(*NP.SIEGE))}
        if NPC_GHOST_BATTLES and (d_ids or (NPC_BLOCKADE_BATTLE and province_owner(R))):
            # (user 2026-10-27 22:56 "9 red NPCs stand in a green province - why no battle?"): a blockade set up for a
            # PLAYER waited up to NPC_AMBUSH_WAIT s with no battle on the map.  Now it is a real battle at once: the
            # owner's NPCs defend the POCs (players of that side can join), the blockers attack; it never takes the
            # province (ghost_finish: pid in AMBUSH).
            d_ns = [npc_state()["npcs"][str(i)] for i in d_ids]
            if npc_open_battle(R, ns, now, ambush={"d": t["vs"], "d_ns": d_ns}):
                AMBUSH[R]["B"] = BATTLES[R]
                AMBUSH[R]["until"] = now + BATTLE_SECONDS + 60
        for n in ns:
            n["task"].update(phase="ambush", entered=now)
        names = ", ".join(n["name"] for n in ns)
        lr, lp = province_label(R), province_label(t["P"])
        if d_ids:
            dn = ", ".join(npc_state()["npcs"][str(i)]["name"] for i in d_ids)
            _notify_side(t["vs"], f"增援部队 {dn} 在 {lr} 遭到第 {O} 国 {names} 伏击！进入 {lr} 可以参战。",
                         f"增援部隊 {dn} 在 {lr} 遭到第 {O} 國 {names} 伏擊！進入 {lr} 可以參戰。",
                         f"Reinforcements {dn} were ambushed in {lr} by {names} (nation {O})! Enter {lr} to fight.")
        else:
            _notify_side(t["vs"], f"第 {O} 国 {names} 在 {lr} 封锁了前往 {lp} 的道路！",
                         f"第 {O} 國 {names} 在 {lr} 封鎖了前往 {lp} 的道路！",
                         f"{names} (nation {O}) block the road to {lp} in {lr}!")
        _notify_side(O, f"{names} 已在 {lr} 截断敌方增援路线。", f"{names} 已在 {lr} 截斷敵方增援路線。",
                     f"{names} are cutting the enemy reinforcements off in {lr}.", (180, 220, 255))
        log(f"   NPC: AMBUSH in {R}: {names} (nation {O}) vs {d_ids or acc} (nation {t['vs']})")
        npc_dirty()
        return
    if ph == "ambush":
        A = AMBUSH.get(R)
        if A is None or A["o"] != O:
            for n in ns:
                npc_release(n, now, random.uniform(60, 240))
            return
        B = A.get("B")
        if B is not None:
            if BATTLES.get(R) is B and not B.get("won"):
                return
            def frac(ids):
                d = sum(NPC_RT.get(i, {}).get("dead", 0) for i in ids)
                u = sum(NPC_RT.get(i, {}).get("units", 0) for i in ids)
                return d / u if u else 1.0
            if R in NPC_RESULT:                       # the POC battle was decided (ghost_finish): the interceptors won it or not
                won = bool(NPC_RESULT[R])
            else:
                of = frac(A["o_ids"])
                won = of < frac(A["d_ids"]) if A["d_ids"] else of < 0.5
            npc_ambush_end(A, won, now, battle=True)
            return
        if now < A["until"]:
            return
        ds = [npc_state()["npcs"][str(i)] for i in A["d_ids"] if str(i) in npc_state()["npcs"]]
        if not ds:
            npc_ambush_end(A, None, now)
            return
        won, a, d = NP.resolve(sum(NP.power_of(n) for n in ns) * npc_attack_factor(O),
                               sum(NP.power_of(n) for n in ds) * NPC_AMBUSH_DEF)
        log(f"   NPC: abstract ambush in {R}: {a:.0f} vs {d:.0f} -> {'CUT OFF' if won else 'broke through'}")
        npc_ambush_end(A, won, now)

def npc_ambush_end(A, won, now, battle=False):
    """won: True = the reinforcement is cut off, False = it broke through, None = nobody came."""
    R = A["R"]
    AMBUSH.pop(R, None)
    st = npc_state()["npcs"]
    os_ = [st[str(i)] for i in A["o_ids"] if str(i) in st and st[str(i)]["task"]
           and st[str(i)]["task"].get("kind") == "intercept"]
    ds = [st[str(i)] for i in A["d_ids"] if str(i) in st and st[str(i)]["task"]
          and st[str(i)]["task"].get("phase") == "ambushed"]
    lr = province_label(R)
    if won is None:
        for n in os_:
            npc_release(n, now, random.uniform(60, 240))
        log(f"   NPC: blockade of {R} lifted (nobody came)")
        return
    if not battle:
        for n in (ds if won else os_):
            _npc_wound(n, 0.55)
        for n in (os_ if won else ds):
            _npc_wound(n, 0.85)
    for n in os_:
        npc_release(n, now, NP.rest_seconds(bool(won)) / 2, bool(won))
    for n in ds:
        if won:
            npc_release(n, now, NP.rest_seconds(False), False)
        else:
            n["task"].update(phase="march", arrive=now + n["task"].get("left", 30.0))
    if won:
        _notify_side(A["d"], f"{lr} 的增援路线被第 {A['o']} 国截断了。", f"{lr} 的增援路線被第 {A['o']} 國截斷了。",
                     f"The reinforcements were cut off in {lr} by nation {A['o']}.", (255, 120, 120))
        _notify_side(A["o"], f"在 {lr} 截断了敌方增援！", f"在 {lr} 截斷了敵方增援！",
                     f"Enemy reinforcements cut off in {lr}!", (120, 255, 120))
    else:
        _notify_side(A["d"], f"增援部队冲破了 {lr} 的封锁！", f"增援部隊衝破了 {lr} 的封鎖！",
                     f"The reinforcements broke through the blockade in {lr}!", (120, 255, 120))
    log(f"   NPC: ambush in {R} over: {'cut off' if won else 'broke through'} ({'battle' if battle else 'abstract'})")
    npc_dirty()

def npc_spawn_ambush(s, mapid, x, y, pocs, n_units):
    """a player enters a province with a blockade: the blockers AND the ambushed NPC reinforcement are on the map
    (each side allied to the players of its side)."""
    A = AMBUSH.get(mapid)
    if not NPC_AMBUSH_BATTLES:                    # user 2026-10-25 12:05: ambush battles (no POC) are abolished
        return False
    if A is None or A.get("B") is not None or getattr(s, "spectator", False):
        return False
    st = npc_state()["npcs"]
    me = side_nation(s)
    tier, _d, _c, mapname = alien_context(s, mapid)
    s.targets = s.targets if isinstance(getattr(s, "targets", None), dict) else {}
    budget = npc_budget(n_units)
    ids = []
    for nid, lst in ((A["o"], A["o_ids"]), (A["d"], A["d_ids"])):
        ns = [st[str(i)] for i in lst if str(i) in st]
        if not ns:
            continue
        ally = same_side(nid, me)
        homes = [(x + 0x50 * (j + 1), y + 0x40 * (j % 2)) for j in range(len(ns))] if ally else \
            spawn_homes(mapname, (x, y), len(ns), avoid=500)
        per = max(2, budget // max(1, len(ns)))
        gs = gate_starts(mapid, len(ns), nid, (x, y)) or [None] * len(ns)   # 2026-10-23: they enter through a gate
        for n, home, gst in zip(ns, homes, gs):
            units = npc_battle_units(n, per, nid, ctx=s, platoons=npc_field_platoons(n, len(ns), s)
                                     if (n.get("doctrine") or {}).get("pp") else None)
            if not units:
                continue
            NPC_RT[n["id"]] = {"B": None, "dead": 0, "units": len(units), "used": set(), "waves": 0, "wave_t": 0,
                               "per": max(per, len(units)), "home": home, "poc": None, "mode": "assault", "nid": nid, "hp_mult": 1.0,
                               "ally": ally, "start": gst}
            npc_put_units(s, nid, n, units, home, "assault", None, 1.0, ally, start=gst)
            ids.append(n["id"])
    if not ids:
        return False
    s.ambush_meta = {"R": mapid, "ids": ids}
    try:
        _say_lang(s, f"遭遇伏击！第 {A['o']} 国的部队在此截断增援。", f"遭遇伏擊！第 {A['o']} 國的部隊在此截斷增援。",
                  f"Ambush! Units of nation {A['o']} block this road.", (255, 160, 80))
    except Exception:
        pass
    log(f"   NPC: ambush battle in {mapid}: {len(ids)} NPC squad(s) on the map for {s.acc}")
    return True

def npc_tick(now=None):
    now = now or time.time()
    _OPEN_BUDGET[0] = NPC_OPEN_PER_TICK
    st = npc_state()
    for n in npc_all():
        try:
            npc_rule_fix(n, now)
        except Exception as e:
            log(f"   NPC rule fix error {n.get('name')}: {e!r}")
        # user 2026-10-23 16:55: after the green NPCs took the province, a red figure stayed in it.  A defender /
        # supporter whose province fell to the enemy and has no battle running any more goes home (walks).
        _tk = n.get("task")
        if _tk and _tk.get("target") and (_tk.get("kind") in ("defend", "support", "patrol") and _tk.get("phase") not in ("march", "ambushed")
                                          or _tk.get("kind") == "attack" and _tk.get("phase") == "battle"):
            _B = BATTLES.get(_tk["target"])
            _own = province_owner(_tk["target"])
            if (_B is None or _B.get("won") or not battle_involves(_B, n["nation"])) and _own \
                    and not same_side(_own, n["nation"]) and now - _tk.get("since", now) > 15:
                log(f"   NPC: {n['name']} leaves {_tk['target']} - the province fell to nation {_own}")
                npc_release(n, now, random.uniform(60, 300), False)
        # (user 2026-10-24 18:55: a province taken by red still showed 4 green NPC figures) ANY task: an NPC drawn in a
        # province that changed hands to a nation not of its side AFTER the NPC got there, with no battle running any
        # more, leaves at once to a neighbouring province of its side (else its capital) - like evict_province for
        # players.  Attackers besieging an enemy province are not affected (that province did not change hands).
        _tk = n.get("task")
        if _tk and _tk.get("phase") not in ("march", "ambushed"):
            try:
                _loc = _npc_location_raw(n, now)[0]
                _own = province_owner(_loc) if _loc else 0
                # user 2026-10-25 14:40 (strict): an NPC may stand only in a province of its side (unowned land: only
                # with a battle running); the old 'changed hands after the NPC arrived' condition is gone
                if _loc and _loc not in CAPITALS.values() and ((_own and not same_side(_own, n["nation"]))
                                                               or (not _own and _tk.get("kind") != "attack")):
                    _B = BATTLES.get(_loc)
                    _chg = float(((WORLD or load_world()).get("since") or {}).get(str(_loc), 0) or 0)
                    if (_B is None or _B.get("won") or not battle_involves(_B, n["nation"])) \
                            and not (_loc in RAIDS and npc_may_stand(_loc, n["nation"])) \
                            and now - max(_chg, _tk.get("since", 0)) > 15:
                        log(f"   NPC: {n['name']} ({_tk.get('kind')}/{_tk.get('phase')}) evicted from {_loc} - "
                            f"taken by nation {_own}")
                        npc_release(n, now, random.uniform(60, 300), False if _tk.get("kind") == "defend" else None)
            except Exception as e:
                log(f"   NPC evict check error {n.get('name')}: {e!r}")
        if n.get("task") and n["task"].get("phase") == "battle":
            n["heal_t"] = now                     # no healing in the middle of a battle
        elif not npc_factory_repair(n, now):      # (10-31) home in the capital: repaired at once
            NP.heal(n, now)
        if "refresh_at" not in n:                 # every NPC renews part of its units once a day, each at its own time
            n["refresh_at"] = now + random.uniform(0, NP.REFRESH_EVERY)
        elif not n.get("task") and n.get("seen") and now >= n.get("adapt_t", 0):
            npc_adapt(n, now)
        elif now >= n["refresh_at"] and not n.get("task"):
            NP.refresh(n, PLANET_TIER.get(nation_planet(n["nation"]), 1), npc_pool())
            npc_realism(n)
            n["refresh_at"] = now + NP.REFRESH_EVERY * random.uniform(0.8, 1.2)
            npc_dirty()
            log(f"   NPC: {n['name']} renewed part of its units ({len(n['squad'])} now)")
    nations = [n[0] for n in NATIONS]
    for nid in nations:
        npc_sync(nid, now)
    forces, icpt = {}, {}
    for n in npc_all():
        t = n["task"]
        if not t:
            continue
        if t.get("kind") == "attack":
            forces.setdefault((n["nation"], t["target"], t.get("group") or ("s", n["id"])), []).append(n)
        elif t.get("kind") == "intercept":
            icpt.setdefault((n["nation"], t["target"], t.get("group") or ("s", n["id"])), []).append(n)
        elif t.get("phase") == "ambushed":
            if not _in_ambush(n["id"]):           # the blockade is gone (server restart): march on
                t.update(phase="march", arrive=now + t.get("left", 30.0))
        elif t.get("kind") == "defend":
            if t.get("phase") == "march":
                if now >= t.get("arrive", 0):
                    npc_reinforce_enter(n, now)
            else:
                npc_defend_step(n, now)
        elif t.get("kind") == "patrol":
            if t.get("phase") == "march" and now >= t.get("arrive", 0):
                t.update(phase="patrol", entered=now)
            elif t.get("phase") == "patrol" and npc_patrol_strike(n, now):
                pass                                  # left its post to attack next door
            elif t.get("phase") == "patrol" and (now >= t.get("until", 0) or t["target"] in BATTLES
                                                 and BATTLES[t["target"]].get("won")):
                npc_release(n, now, random.uniform(60, 300))
        elif t.get("kind") == "support":
            pid = t["target"]
            if t.get("phase") == "march" and now >= t.get("arrive", 0):
                t.update(phase="support", entered=now)
                log(f"   NPC: {n['name']} arrived to support {pid}")
                _B = BATTLES.get(pid)
                if _B is not None and _B.get("npc_attacker") is not None and not _B.get("won"):
                    own = _B["owner"]
                    pocs_ = list(_B["pocs"].items())
                    pc = pocs_[0] if pocs_ else None
                    home = (pc[1]["x"], pc[1]["y"]) if pc else next(iter(_B["targets"].values()), {}).get("home", (512, 512))
                    if _npc_put_squad(own, n["nation"], n, NPC_GHOST_DEPLOY, home, "hold",
                                      (pc[0], pc[1]["x"], pc[1]["y"]) if pc else None,
                                      start=(gate_starts(pid, 1, n["nation"]) or [None])[0]):
                        NPC_RT[n["id"]]["B"] = _B
                        n["task"] = {"kind": "defend", "target": pid, "phase": "battle", "since": now}
                        log(f"   NPC: {n['name']} joins the battle on {pid} as a defender")
                        continue
            if now - t.get("since", now) > 60 and not any(m["task"] and m["task"].get("kind") == "attack"
                                                         and m["task"].get("target") == pid for m in npc_all()):
                npc_release(n, now, random.uniform(60, 400), True)
                log(f"   NPC: {n['name']} returns from supporting {pid}")
    for ns in forces.values():
        if ns[0]["task"]:
            npc_force_step(ns, now)
    for ns in icpt.values():
        if ns[0]["task"]:
            npc_intercept_step(ns, now)
    for nid in nations:
        active = [n for n in npc_of(nid) if n["state"] == "active"]
        for n in active:
            if not n["task"] and n.get("retire"):
                n["state"], n["retire"] = "sleep", False
        active = [n for n in active if n["state"] == "active"]
        npc_sortie(nid, active, now)
        for n in active:
            if n["task"] or now < n["think_at"] or now < n["rest_until"]:
                continue
            npc_think(n, now)
            if n["task"]:
                n.pop("idle_since", None)          # (10-31) boredom counts from the end of its last task
    npc_idle_report(now)
    npc_save()

NPC_TOWN_BASE = 40000       # unit id of an NPC commander walking around his capital = base + NPC id
NPC_TOWN_MAX = 40          # (11-01) every NPC the people list shows (it has no limit)

try:
    _CAPS = data_json("capital_spots.json")
except Exception:
    _CAPS = {"spots": [[512, 512]], "doors": [[512, 512]]}
NPC_TOWN_SPEED = 110 * TOWN_SPEED_SLOW / 100.0     # px / s the idle NPCs walk at (estimate: speed 100 ~ 110 px/s)

def _npc_town_walk(s, uid, x, y):
    """order the NPC commander to walk to (x, y) on the town map (lump 0x1A for this session)."""
    msg = _alien_order_move(uid, x, y)
    s.send(bytes([0x80, 0, 0]) + struct.pack(">IH", game_time(s) + RELAY_DELAY, 1) + struct.pack(">H", len(msg)) + msg)

def _npc_town_put(s, n, x, y):
    uid = NPC_TOWN_BASE + n["id"]
    look = max(1, min(int(n.get("look", 1)), 11))
    s.send(put_server_unit(uid, n["name"], n["name"], x, y, 0, look, n["nation"], speed=TOWN_SPEED_SLOW))
    s.send(build_hero(uid, n["name"], x, y, 0, look, n["nation"], 100, 0, 0))

def npc_town_sync(s):
    """idle NPC commanders of the capital's nation stand and wander on the capital map like other players (hero + minimap
    dot, user 2026-10-22 14:13): random spots over the whole map, an NPC that leaves for a battle walks to a gate first, one
    that comes back walks in from a gate."""
    if not getattr(s, "logged_in", False) or getattr(s, "battle", None) or not getattr(s, "hero_uid", None):
        return
    now = time.time()
    m = getattr(s, "map", None)
    nid = next((k for k, c in CAPITALS.items() if c == m), None)
    shown = getattr(s, "npc_town", None)
    first = shown is None or getattr(s, "npc_town_map", None) != m
    if first:
        shown = s.npc_town = {}
        s.npc_town_map = m
    want = {}
    if nid is not None:
        # (user 2026-11-01 15:42 "the NPC count on the minimap and the strategic map differ"): the same rule as the
        # strategic map's people list (build_province_info) - an NPC is in the capital when npc_location says so.  The
        # old rule "no task" also showed NPCs still walking home from a battle, or holding a post in another province.
        cap_pv = province_of(m)
        for n in npc_of(nid):
            if n["state"] == "active" and len(want) < NPC_TOWN_MAX and npc_location(n, now)[0] in (m, cap_pv) \
                    and (n.get("task") or {}).get("phase") not in ("battle", "siege", "raid"):
                want[n["id"]] = n
        spots, doors = _CAPS["spots"], _CAPS["doors"]
    else:
        # a province town map: every NPC the strategic map draws in this province (user 2026-10-22 22:15)
        pv = province_of(m) if m and m < 100000000 and map_kind(m) == "province" else None
        if pv is None or getattr(s, "battle_mode", 0):
            return
        for n in npc_active():
            if len(want) < NPC_TOWN_MAX and npc_location(n)[0] == pv \
                    and (n.get("task") or {}).get("phase") not in ("battle", "siege", "raid"):
                want[n["id"]] = n
        if not want and not shown:
            return
        spots = [tuple(p) for p in SPAWN_SPOTS.get(alien_context(s, m)[3] or "", [])] or [(512, 512)]
        cx = sum(p[0] for p in spots) / len(spots)
        cy = sum(p[1] for p in spots) / len(spots)
        doors = sorted(spots, key=lambda p: -((p[0] - cx) ** 2 + (p[1] - cy) ** 2))[:6]     # near the map edges
    for i in list(shown):
        rec = shown[i]
        uid = NPC_TOWN_BASE + i
        if i not in want:                       # leaving: walk to the nearest gate, then disappear
            if rec.get("leave_at") is None:
                gx, gy = min(doors, key=lambda g: (g[0] - rec["x"]) ** 2 + (g[1] - rec["y"]) ** 2)
                _npc_town_walk(s, uid, gx, gy)
                rec["leave_at"] = now + math.hypot(gx - rec["x"], gy - rec["y"]) / NPC_TOWN_SPEED + 1.5
            elif now >= rec["leave_at"]:
                s.send(bytes([0x19]) + struct.pack(">II", uid, 0))
                del shown[i]
        else:
            rec["leave_at"] = None
            if now >= rec["next"]:              # wander to another spot a few hundred px away
                near = [p for p in spots if 150 < math.hypot(p[0] - rec["x"], p[1] - rec["y"]) < 900] or spots
                x, y = random.choice(near)
                _npc_town_walk(s, uid, x, y)
                rec["x"], rec["y"] = x, y
                rec["next"] = now + random.uniform(30, 150)
    for i, n in want.items():
        if i not in shown:
            if first:                           # already standing somewhere when the player arrives
                x, y = random.choice(spots)
            else:                               # coming back from a battle: walks in from a gate
                x, y = random.choice(doors)
            _npc_town_put(s, n, x, y)
            shown[i] = {"x": x, "y": y, "next": now + random.uniform(5, 90), "leave_at": None}
            if not first:
                tx, ty = random.choice(spots)
                _npc_town_walk(s, NPC_TOWN_BASE + i, tx, ty)
                shown[i].update(x=tx, y=ty)

NPC_MAP_PUSH = False     # push the strategic map when NPC icons / battles changed (only to players who just used it)
NPC_DOT_PUSH = True      # re-send the open province preview so the NPC dots on its minimap move (user 2026-10-22 13:43)

def npc_dot_push(now):
    for o in list(ONLINE):
        try:
            npc_town_sync(o)
        except Exception as e:
            log(f"   npc town sync error: {e!r}")
    for o in list(ONLINE):
        pid = getattr(o, "info_pid", None)
        if not pid or not getattr(o, "logged_in", False) or now - getattr(o, "info_t", 0) > (600 if CAVE_ROWS else 90) \
                or getattr(o, "battle", None):
            continue
        try:
            if o.w.is_closing():
                continue
            _npc_here = any(npc_location(n)[0] == pid for n in npc_active())
            if not _npc_here and not (CAVE_ROWS and now - getattr(o, "info_push_t", 0) >= 30):
                continue                         # cave status rows: renewed every 30 s even without NPCs
            o.info_push_t = now
            o.send(build_province_info(o, pid))
        except Exception as e:
            log(f"   npc dot push error: {e!r}")
    if NPC_MAP_PUSH:                       # the open strategic map follows the NPC marches (only when something changed)
        sigs = {}
        for o in list(ONLINE):
            if not getattr(o, "logged_in", False) or getattr(o, "battle", None) or now - getattr(o, "info_t", 0) > 90 \
                    or getattr(o, "sim_board", False):       # the Simulation Center board is not the strategic map
                continue
            try:
                if o.w.is_closing():
                    continue
                pl = current_planet(o)
                sigs.setdefault(pl, _map_signature(pl))
                if getattr(o, "map_sig", None) != sigs[pl]:
                    o.map_sig = sigs[pl]
                    send_strategic_map(o)
            except Exception as e:
                log(f"   npc map push error: {e!r}")

async def npc_cycle():
    await asyncio.sleep(8)
    while True:
        try:
            _t0 = time.monotonic()
            npc_tick()
            npc_react(time.time())
            npc_assist(time.time())
            try:
                npc_auto_reinforce(time.time())         # (2026-10-27 23:14) helpers come without a call for help
            except Exception as e:
                log(f"   npc auto reinforce error: {e!r}")
            evict_sweep(time.time())
            try:
                npc_sos(time.time())                    # NPC calls for support in the ally chat (2026-10-23 21:33)
                npc_strategy_chat(time.time())          # threats / campaigns / last stand (2026-10-23 21:57)
                npc_diplomacy(time.time())              # alliances formed / broken by strategy (2026-10-23 22:01)
            except Exception as e:
                log(f"   npc_sos error: {e!r}")
            npc_intercept_scan(time.time())
            if time.monotonic() - _t0 > 0.15:
                log(f"   NPC tick took {(time.monotonic() - _t0) * 1000:.0f} ms")
            if NPC_DOT_PUSH:
                npc_dot_push(time.time())
        except Exception as e:
            import traceback
            log(f"   NPC tick error: {e!r} {traceback.format_exc()[-400:]}")
        gc_idle()
        await asyncio.sleep(NPC_TICK)
