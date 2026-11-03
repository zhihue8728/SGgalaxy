# ---- NPC NATIONS (claude/NPC_NATIONS_PLAN.md; user decisions 2026-10-22 13:08 - 13:13) -------------------------------
# Every nation has a roster of NP.NPC_CAP computer commanders ("NPC"), stored in server/npcs.json.  They look like normal
# players (hall of fame, player search, user info, strategic map).  ACTIVE NPCs of a nation = 20 - players online.
# Each active NPC decides on its own random timer: stay, sortie alone, follow a comrade, or (random group event of the
# nation) sortie together.  Without a player in the province the battle is abstract (NP.resolve); with a player in it the
# NPC squads are put on the battle map as server-owned units (npc_spawn / npc_ai), which fight and capture POCs.
import npc as NP

NPC_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "npcs.json")
NPC_TICK = 10.0
NPC_BATTLE_FACTOR = 1.2            # NPC units on a battle map = this x the human units fighting them ...
NPC_BATTLE_UNITS = (6, 36)         # ... but between these limits
NPC_DEFENDERS_MAX = 3              # NPC squads that defend one attacked province
NPC_NO_UNITS = {"Sapper", "Sapper-MK2", "Virus", "Medic", "Triage", "Triage-MK2", "Volte", "Mantlet", "Gear-Doc"}
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
            with open(NPC_FILE, encoding="utf-8") as f:
                NPC_STATE = json.load(f)
        except Exception:
            NPC_STATE = {}
        for k, v in (("next_id", 1), ("npcs", {}), ("refill", {}), ("sortie", {}), ("protect", {}), ("stand", {}),
                     ("stand_cool", {}), ("peak", {}), ("warm", {}), ("group", 1)):
            NPC_STATE.setdefault(k, v)
        for n in NPC_STATE["npcs"].values():          # tasks do not survive a restart
            n["task"] = None
    return NPC_STATE

def npc_dirty():
    global NPC_DIRTY
    NPC_DIRTY = True

def npc_save(force=False):
    global NPC_DIRTY, NPC_SAVED_AT
    if NPC_STATE is not None and NPC_DIRTY and (force or time.time() - NPC_SAVED_AT > 60):
        _atomic_json(NPC_FILE, NPC_STATE, 0)
        NPC_DIRTY = False
        NPC_SAVED_AT = time.time()

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
    for _code, tab, infl, name in UNITS:
        if tab in (0, 1) and name not in NPC_NO_UNITS:
            pool.append({"code": name, "min": infl, "rank": float(infl), "spd": speed(name)})
    for adv, _code, base, uq, _zh in ADVANCED:
        if _TAB.get(base) in (0, 1) and adv not in NPC_NO_UNITS:
            pool.append({"code": adv, "min": uq, "rank": uq / 8.0, "spd": speed(adv)})
    med = sorted(p["spd"] for p in pool)[len(pool) // 2]
    for p in pool:
        p["fast"] = p["spd"] >= med
    _NPC_POOL["p"] = pool
    return pool

def npc_ensure_roster(nid):
    st = npc_state()
    mine = npc_of(nid)
    if len(mine) >= NP.NPC_CAP:
        return mine
    tier = PLANET_TIER.get(nation_planet(nid), 1)
    taken = {n["name"].lower() for n in st["npcs"].values()} | {a.lower() for a in load_accounts()}
    while len(mine) < NP.NPC_CAP:
        uid = st["next_id"]
        st["next_id"] += 1
        n = NP.new_npc(nid, tier, uid, taken, npc_pool())
        taken.add(n["name"].lower())
        st["npcs"][str(uid)] = n
        mine.append(n)
    npc_dirty()
    log(f"   NPC: roster of nation {nid} created ({len(mine)} commanders)")
    return mine

def npc_cmd(n):
    """the commander record the directory / hall of fame / user info windows read."""
    lv = n["level"]
    return {"nation": n["nation"], "look": n["look"], "attrs": [min(120, 20 + lv), min(120, lv), min(120, lv), min(120, lv // 2)],
            "points": 0, "tier": PLANET_TIER.get(nation_planet(n["nation"]), 1),
            "branches": {"inf": {"level": lv, "xp": 0}, "mob": {"level": max(1, lv - 5), "xp": 0},
                         "avi": {"level": 1, "xp": 0}, "org": {"level": 1, "xp": 0}},
            "honor": n.get("honor", 0), "wins": n.get("wins", 0), "losses": n.get("losses", 0), "medals": [],
            "reincarnations": 0, "stats": {"kills": n.get("wins", 0) * 4}, "npc": True}

def npc_account(n):
    return {"commander": npc_cmd(n), "units": [], "resources": list(START_RESOURCES), "npc": True}

def npc_directory_rows(only=None):
    return [(n["name"], npc_cmd(n)) for n in npc_all() if only is None or uid_of(n["name"]) == only]

def npc_by_name(name):
    low = (name or "").strip().lower()
    return next((n for n in npc_all() if n["name"].lower() == low), None)

# ---- strategic-map presence ---------------------------------------------------------------------------------------------
def npc_location(n):
    """(province the NPC is drawn in, travel target)."""
    cap = CAPITALS.get(n["nation"])
    t = n.get("task")
    if t and t.get("kind") in ("attack", "defend"):
        if t.get("phase") == "march":
            return t.get("origin") or cap, t["target"]
        return t["target"], t["target"]
    return cap, cap

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
    _NPC_UNITS[key] = u
    return u

def npc_battle_units(npc, k, nid):
    """first k ARMED units of the squad: (name, level, stats9, hp, energy, speed)."""
    out = []
    for name, lv in npc["squad"]:
        u = npc_unit(name, lv)
        st9 = unit_stats9(u)
        if st9[3] <= 0 and st9[6] <= 0:
            continue
        hp, en = unit_battle_stats(u)
        out.append((name, lv, st9, max(1, int(hp * npc_stand_mult(nid))), en, unit_speed(u)))
        if len(out) >= k:
            break
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
    p = 40.0 * tier + 20.0 * npc_humans(owner) + 0.4 * sum(NP.power(n["squad"]) for n in idle)
    return p * (NP.LAST_STAND_HP if npc_stand(owner) else 1.0)

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
    for pid in mine:
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
                        "owner_small": bool(o) and counts.get(o, 0) <= 2}
    return list(out.values())

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
    mine = npc_ensure_roster(nid)
    stand = npc_update_stand(nid, now)
    want = NP.want_active(npc_humans(nid), stand)
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
            for n in sleepers[:want - len(active)]:
                n["state"] = "active"
                n["retire"] = False
                n["think_at"] = now + random.uniform(10, 600)
            st["refill"].pop(k, None)
            st["warm"][k] = 1
            npc_dirty()
    else:
        st["refill"].pop(k, None)
        for n in active:
            n["retire"] = False

# ---- decisions -----------------------------------------------------------------------------------------------------
def npc_send(ns, cand, now, group=False):
    st = npc_state()
    nid = ns[0]["nation"]
    steps = max(1, int(cand["dist_cap"]))
    arrive = now + (max(NP.march_seconds(steps) for _ in ns) if group else NP.march_seconds(steps))
    pl = cand["pid"] // 100000
    origin = next((pl * 100000 + q for q in PORTAL_LINKS.get(cand["pid"] % 100000, ())
                   if province_owner(pl * 100000 + q) == nid), CAPITALS.get(nid))
    gid = None
    if group and len(ns) > 1:
        gid = st["group"]
        st["group"] += 1
    for n in ns:
        n["task"] = {"kind": "attack", "target": cand["pid"], "origin": origin, "depart": now, "arrive": arrive,
                     "phase": "march", "group": gid, "since": now, "wait": 0}
    npc_dirty()
    log(f"   NPC: {[n['name'] for n in ns]} (nation {nid}) march on {cand['pid']} ({cand['kind']}, power "
        f"{sum(NP.power(n['squad']) for n in ns):.0f} vs {cand['def_power']:.0f}), arrive in {arrive - now:.0f}s")
    if len(ns) > 1:
        raid_notify(nid, f"{len(ns)} commanders ({', '.join(n['name'] for n in ns[:3])}...) march on "
                         f"{province_label(cand['pid'])}.", (180, 220, 255))

def npc_think(n, now):
    n["think_at"] = now + NP.think_delay(n)
    nid = n["nation"]
    p = NP.PERSONAS[n["persona"]]
    if p["follow"] and random.random() < p["follow"]:
        mates = [m for m in npc_of(nid) if m is not n and m["state"] == "active" and m["task"]
                 and m["task"].get("kind") == "attack" and m["task"].get("phase") == "march" and m["task"]["arrive"] > now + 30]
        if mates:
            m = random.choice(mates)
            st = npc_state()
            gid = m["task"].get("group")
            if gid is None:
                gid = st["group"]
                st["group"] += 1
                m["task"]["group"] = gid
            n["task"] = dict(m["task"], since=now, wait=0)
            log(f"   NPC: {n['name']} follows {m['name']} to {m['task']['target']}")
            return
    cands = npc_candidates(nid, now)
    c = NP.choose(cands, n, NP.power(n["squad"]))
    if c:
        npc_send([n], c, now)
    else:
        log(f"   NPC: {n['name']} ({n['persona']}) stays home") if random.random() < 0.05 else None

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
    free = [n for n in active if not n["task"] and now >= n["rest_until"] and not n.get("retire")]
    if len(free) < NP.SORTIE_SIZE[0]:
        return
    team = random.sample(free, min(len(free), random.randint(*NP.SORTIE_SIZE)))
    att = sum(NP.power(n["squad"]) for n in team)
    c = NP.choose(npc_candidates(nid, now), {"persona": "warlike"}, att)
    if c:
        npc_send(team, c, now, group=True)

# ---- tasks ----------------------------------------------------------------------------------------------------------
def npc_release(n, now, rest, won=None):
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
    names = ", ".join(n["name"] for n in ns[:3]) + ("..." if len(ns) > 3 else "")
    if won:
        if not battle and owner != nid:
            set_province_owner(pid, nid)
            if not owner:
                AL.set_garrison(world_state(), pid, 0.0)
                save_world(world_state())
        raid_notify(nid, f"{names} captured {province_label(pid)}!", (120, 255, 120))
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
    att = sum(NP.power(n["squad"]) for n in ns) * (NP.LAST_STAND_HP if npc_stand(ns[0]["nation"]) else 1.0)
    dfn = npc_defence(t["target"])
    won, a, d = NP.resolve(att, dfn)
    log(f"   NPC: abstract battle on {t['target']}: attackers {a:.0f} vs defence {d:.0f} -> {'WON' if won else 'lost'}")
    npc_finish(ns, won, now)

def npc_begin(ns, now):
    t = ns[0]["task"]
    nid, pid = ns[0]["nation"], t["target"]
    owner = province_owner(pid)
    if owner and same_side(nid, owner):
        npc_finish(ns, None, now)
        return
    if pid in BATTLES or pid in RAIDS:
        t["wait"] = t.get("wait", 0) + 1
        if t["wait"] > 4:
            npc_finish(ns, None, now)
        else:
            t["arrive"] = now + 150
        return
    if owner and npc_humans(owner) > 0:
        RAIDS[pid] = {"nation": owner, "until": now + AL.RAID_DEFEND_SECONDS, "from": t.get("origin"), "npc": nid,
                      "force": [n["id"] for n in ns]}
        for n in ns:
            n["task"].update(phase="raid", until=now + AL.RAID_DEFEND_SECONDS)
        raid_notify(owner, f"Commanders of nation {nid} ({', '.join(n['name'] for n in ns[:3])}) are attacking "
                           f"{province_label(pid)}!  Defend it within {AL.RAID_DEFEND_SECONDS // 60} minutes or it is lost.")
        log(f"   NPC: RAID on {pid} (nation {owner}) by {[n['name'] for n in ns]}")
    else:
        for n in ns:
            n["task"].update(phase="siege", resolve_at=now + random.uniform(*NP.SIEGE), wait=0)

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

def npc_tick(now=None):
    now = now or time.time()
    st = npc_state()
    nations = [n[0] for n in NATIONS]
    for nid in nations:
        npc_sync(nid, now)
    forces = {}
    for n in npc_all():
        t = n["task"]
        if not t:
            continue
        if t.get("kind") == "attack":
            forces.setdefault((n["nation"], t["target"], t.get("group") or ("s", n["id"])), []).append(n)
        elif t.get("kind") == "defend":
            npc_defend_step(n, now)
    for ns in forces.values():
        if ns[0]["task"]:
            npc_force_step(ns, now)
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
    npc_save()

async def npc_cycle():
    await asyncio.sleep(8)
    while True:
        try:
            npc_tick()
        except Exception as e:
            import traceback
            log(f"   NPC tick error: {e!r} {traceback.format_exc()[-400:]}")
        await asyncio.sleep(NPC_TICK)

# ---- hooks called from the rest of the server ------------------------------------------------------------------------
def npc_owner_changed(pid, old, new):
    """a nation that just lost a province is left alone by the NPCs for a while."""
    if old and old != new and pid not in set(CAPITALS.values()):
        npc_state()["protect"][str(old)] = time.time() + random.uniform(*NP.PROTECT_SECONDS)
        npc_dirty()

def npc_unit_died(tg):
    rt = NPC_RT.get(tg.get("npc"))
    if rt is not None:
        rt["dead"] = rt.get("dead", 0) + 1

def npc_battle_result(pid, npc_won):
    NPC_RESULT[pid] = bool(npc_won)

def npc_battle_started(s, B):
    meta = getattr(s, "alien_meta", None) or {}
    if not meta.get("npc"):
        return
    B["npc_side"], B["npc_raid"] = meta["npc_nation"], bool(meta.get("raid"))
    B["npc_ids"] = list(meta.get("npc_ids", []))
    now = time.time()
    for i in B["npc_ids"]:
        NPC_RT.setdefault(i, {"dead": 0, "units": 0})["B"] = B
        n = npc_state()["npcs"].get(str(i))
        if n and n["task"]:
            n["task"]["phase"] = "battle"
            n["task"]["since"] = now
    log(f"   NPC battle on {B['map']}: {'attackers' if B['npc_raid'] else 'defenders'} of nation {B['npc_side']} {B['npc_ids']}")

def npc_battle_closed(b):
    """the last human left a battle against NPC raiders without a result: the raid is decided abstractly soon."""
    if b.get("npc_raid") and not b.get("won"):
        r = RAIDS.get(b["map"])
        if r:
            r["until"] = min(r["until"], time.time() + 60)
            for i in r.get("force", []):
                n = npc_state()["npcs"].get(str(i))
                if n and n["task"]:
                    n["task"].update(phase="raid", until=r["until"])

def npc_won_battle(b):
    if b.get("won"):
        return
    b["won"] = True
    nat, pid = b["npc_side"], b["map"]
    RAIDS.pop(pid, None)
    if province_owner(pid) != nat:
        set_province_owner(pid, nat)
    NPC_RESULT[pid] = True
    log(f"   NPC: the raiders of nation {nat} captured every POC of {pid}")
    raid_notify(province_owner(pid), f"{province_label(pid)} was lost!", (255, 120, 120))
    for o in list(b["members"]):
        asyncio.get_event_loop().create_task(
            end_battle(o, o.battle_gen, won=(same_side(side_nation(o), nat) and not getattr(o, "spectator", False))))

def npc_time_up(b):
    nat = b.get("npc_side")
    if not nat or not b.get("npc_raid"):
        return
    pocs = list(b.get("pocs", {}).values())
    mine = sum(1 for p in pocs if p["owner"] and same_side(nat, p["owner"]))
    won = bool(pocs) and mine > len(pocs) - mine
    pid = b["map"]
    RAIDS.pop(pid, None)
    if won and province_owner(pid) != nat:
        set_province_owner(pid, nat)
        raid_notify(province_owner(pid), f"{province_label(pid)} was lost!", (255, 120, 120))
    NPC_RESULT[pid] = won

# ---- NPC squads on a battle map (server-owned units, like the aliens) ---------------------------------------------------
def npc_spawn(s, mapid, nid, npcs, budget, homes, mode, x, y, raid, pocs=()):
    tier, dist, _cave, mapname = alien_context(s, mapid)
    s.targets = s.targets if isinstance(getattr(s, "targets", None), dict) else {}
    s.alien_meta = {"npc": True, "npc_nation": nid, "tier": tier, "dist": dist, "cave": None, "map": mapname, "branch": 0,
                    "players": 1, "mapid": mapid, "full": 0, "waves_left": 0, "next_wave": 0, "squad_n": 0,
                    "arrival": (x, y), "raid": raid, "sim": False, "npc_ids": []}
    per = max(2, budget // max(1, len(npcs)))
    npcs = npcs[:max(1, budget // per)]
    for qi, (n, home) in enumerate(zip(npcs, homes)):
        units = npc_battle_units(n, per, nid)
        if not units:
            continue
        off = AL.formation(len(units), 26)
        NPC_RT[n["id"]] = {"B": None, "dead": 0, "units": len(units)}
        poc = pocs[qi % len(pocs)] if pocs else None
        for k, (name, lv, st9, hp, en, spd) in enumerate(units):
            tid = next_alien_id(s)
            px, py = int(home[0] + off[k][0]), int(home[1] + off[k][1])
            _t, akind, anum = unit_kind(name)
            sight = unit_sight(st9)
            capt = k < NP.SQUAD_FAST
            foff = AL.formation(NP.SQUAD_FAST, 16)[k] if capt else (off[k][0] * 2, off[k][1] * 2)
            s.targets[tid] = {"hp": hp, "max": hp, "x": px, "y": py, "armor": st9[0], "arow": st9[1], "level": lv,
                              "aggressive": True, "target": None, "name": name, "home": (px, py), "pos": (px, py),
                              "squad": n["id"], "state": "idle", "boss": False, "next_patrol": 0,
                              "npc": n["id"], "nation": nid, "mode": mode, "role": "capturer" if capt else "fighter",
                              "off": foff, "spd": spd, "poc": poc[0] if poc else None,
                              "put": {"name": name, "owner": n["name"], "kind": akind, "num": anum, "nation": nid,
                                      "st9": st9, "sight": sight, "spd": spd, "abil": ABILITY_ATTACK}}
            s.send(build_put_unit(tid, name, n["name"], px, py, akind, anum, nid, hp=hp, energy=max(1, en), stats9=st9,
                                  sight=sight, speed=spd, abilities=ABILITY_ATTACK))
        s.alien_meta["npc_ids"].append(n["id"])
    log(f"   NPC: {len(s.targets)} unit(s) of nation {nid} ({[n['name'] for n in npcs]}) on {mapid}, mode {mode}")

def npc_budget(n_units):
    lo, hi = NPC_BATTLE_UNITS
    return max(lo, min(hi, int(round(NPC_BATTLE_FACTOR * max(1, n_units)))))

def npc_spawn_attackers(s, mapid, x, y, pocs, n_units):
    r = RAIDS.get(mapid) or {}
    st = npc_state()
    npcs = [st["npcs"][str(i)] for i in r.get("force", []) if str(i) in st["npcs"]]
    if not npcs:
        return
    _t, _d, _c, mapname = alien_context(s, mapid)
    homes = spawn_homes(mapname, (x, y), len(npcs))
    npc_spawn(s, mapid, r["npc"], npcs, npc_budget(n_units), homes, "assault", x, y, True)

def npc_spawn_defenders(s, mapid, x, y, pocs, n_units):
    owner = province_owner(mapid)
    if not owner or not pocs or same_side(owner, side_nation(s)) or getattr(s, "spectator", False):
        return False
    now = time.time()
    cand = [n for n in npc_of(owner) if n["state"] == "active" and now >= n["rest_until"]
            and not (n["task"] and n["task"].get("kind") in ("defend", "attack") and n["task"].get("phase") != "march")]
    if not cand:
        return False
    cand.sort(key=lambda n: (bool(n["task"]), -NP.power(n["squad"])))
    picked = cand[:NPC_DEFENDERS_MAX]
    for n in picked:
        n["task"] = {"kind": "defend", "target": mapid, "phase": "battle", "since": now}
    homes = [(pocs[i % len(pocs)][1], pocs[i % len(pocs)][2]) for i in range(len(picked))]
    npc_spawn(s, mapid, owner, picked, npc_budget(n_units), homes, "hold", x, y, False, pocs)
    npc_dirty()
    return True

def _npc_est_pos(tg, now):
    mv = tg.get("mv")
    if not mv:
        return tg["pos"]
    (x0, y0), (x1, y1), t0, t1 = mv
    f = 1.0 if t1 <= t0 else max(0.0, min(1.0, (now - t0) / (t1 - t0)))
    return (x0 + (x1 - x0) * f, y0 + (y1 - y0) * f)

async def npc_ai(s, gen):
    """once per second: NPC units fight what is in reach, otherwise walk to the nearest enemy POC and capture it (the
    capturers stand ON it, poc_loop counts them); defenders hold their POC and take it back."""
    await asyncio.sleep(2.0)
    b, mapid = getattr(s, "battle", None), getattr(s, "map", None)
    def alive():
        if b is not None:
            return BATTLES.get(mapid) is b and not b.get("won")
        return getattr(s, "battle_gen", None) == gen and not s.w.is_closing()
    try:
        while alive():
            now = time.time()
            meta = getattr(s, "alien_meta", None) or {}
            nat = meta.get("npc_nation")
            tier = meta.get("tier", 1)
            members = [o for o in b["members"] if not o.w.is_closing()] if b is not None else battle_members(s)
            pos, hp = {}, {}
            for o in members:
                if getattr(o, "spectator", False) or same_side(side_nation(o), nat):
                    continue
                for u in getattr(o, "alive_units", set()):
                    pos[u] = o.unit_pos.get(u, (0, 0))
                    hp[u] = getattr(o, "unit_hp", {}).get(u, 9999)
            pocs = b["pocs"] if b is not None else s.pocs
            enemy_pocs = {pid: p for pid, p in pocs.items() if not same_side(nat, p["owner"])}
            msgs = []
            mine = {tid: tg for tid, tg in s.targets.items() if tg.get("npc") is not None and tg["hp"] > 0}
            busy = {}
            for tg in mine.values():
                if tg.get("state") == "combat" and tg.get("target") is not None:
                    busy[tg["target"]] = busy.get(tg["target"], 0) + 1
            def engage(tid, tg, target):
                old = tg.get("target") if tg.get("state") == "combat" else None
                if old is not None and busy.get(old):
                    busy[old] -= 1
                busy[target] = busy.get(target, 0) + 1
                tg["target"], tg["state"] = target, "combat"
                tg["pos"] = pos.get(target, tg["pos"])
                tg["mv"], tg["on_poc"], tg["dest"] = None, None, None
                tg["hp_mark_t"] = None
                msgs.append(bytes([0x2B]) + struct.pack(">II", tid, target))
            for tid, tg in list(mine.items()):
                tg["pos"] = _npc_est_pos(tg, now) if tg.get("state", "idle") != "combat" else tg["pos"]
                R = AL.AGGRO[tier] * (0.6 if tg["role"] == "capturer" else 1.0)
                if tg.get("state") == "combat":
                    tgt = tg.get("target")
                    far = tg["mode"] == "hold" and AL.dist(tg["pos"], tg["home"]) > AL.LEASH[tier]
                    if tgt not in pos or far or tg.get("ignore", {}).get(tgt, 0) > now:
                        tg["state"], tg["target"], tg["dest"] = "idle", None, None
                    else:
                        tg["pos"] = pos[tgt]
                        # no damage for FUTILE_SECONDS (out of range / defensive matrix) -> pick another unit
                        if tg.get("hp_mark_t") is None or tg.get("hp_mark_u") != tgt:
                            tg["hp_mark_t"], tg["hp_mark_u"], tg["hp_mark"] = now, tgt, hp.get(tgt, 9999)
                        elif now - tg["hp_mark_t"] >= FUTILE_SECONDS:
                            if hp.get(tgt, 9999) >= tg["hp_mark"]:
                                tg.setdefault("ignore", {})[tgt] = now + FUTILE_IGNORE
                                tg["state"], tg["target"], tg["dest"] = "idle", None, None
                            tg["hp_mark_t"], tg["hp_mark"] = now, hp.get(tgt, 9999)
                        if tg["state"] == "combat":
                            continue
                ign = tg.get("ignore", {})
                cand = {u: p for u, p in pos.items() if ign.get(u, 0) < now}
                t2 = AL.pick_target(tier, tg["pos"], cand, lambda u: hp.get(u, 9999), R, busy)
                if t2 is not None:
                    engage(tid, tg, t2)
                    for tid2, tg2 in mine.items():           # the squad helps
                        if tid2 != tid and tg2.get("npc") == tg["npc"] and tg2.get("state", "idle") != "combat":
                            t3 = AL.pick_target(tier, tg2["pos"], cand, lambda u: hp.get(u, 9999), AL.AGGRO[tier] * 1.5, busy) or t2
                            engage(tid2, tg2, t3)
                    continue
                # nothing to shoot: the objective
                poc_id, dest = None, None
                if tg["mode"] == "assault" and enemy_pocs:
                    poc_id = min(enemy_pocs, key=lambda i: AL.dist(tg["pos"], (enemy_pocs[i]["x"], enemy_pocs[i]["y"])))
                elif tg["mode"] == "hold" and tg.get("poc") in enemy_pocs:
                    poc_id = tg["poc"]
                if poc_id is not None:
                    p = enemy_pocs[poc_id]
                    dest = (p["x"] + tg["off"][0], p["y"] + tg["off"][1])
                elif tg["mode"] == "hold":
                    dest = tg["home"]
                elif pos:
                    dest = min(pos.values(), key=lambda q: AL.dist(tg["pos"], q))
                if dest is None:
                    continue
                if tg.get("dest") != (poc_id, dest) or tg.get("state") == "idle" and tg.get("dest") is None:
                    d = AL.dist(tg["pos"], dest)
                    if d > 20:
                        msgs.append(_alien_order_move(tid, *dest))
                    dur = d * 1.3 / max(1.0, tg["spd"] * 2.0) + 1.0
                    tg["mv"] = (tuple(tg["pos"]), tuple(dest), now, now + dur)
                    tg["arrive_t"] = now + dur
                    tg["dest"] = (poc_id, dest)
                tg["on_poc"] = poc_id if (poc_id is not None and tg["role"] == "capturer" and now >= tg.get("arrive_t", 0)) else None
            if msgs:
                for o in members:
                    pk = bytes([0x80, 0, 0]) + struct.pack(">IH", game_time(o) + 10, len(msgs))
                    for m in msgs:
                        pk += struct.pack(">H", len(m)) + m
                    o.send(pk)
            await asyncio.sleep(1.0)
    except Exception as e:
        import traceback
        log(f"   NPC AI stopped: {e!r} {traceback.format_exc()[-300:]}")

# ---- GM: /npc ------------------------------------------------------------------------------------------------------------
def npc_gm(s, parts):
    """/npc status | /npc go PID [N] | /npc stand [HOURS] | /npc fill | /npc reset"""
    nid = s.cmd.get("nation", 1)
    say = lambda t: s.send(chat_line(0x0A, t, (200, 200, 255)))
    sub = parts[1] if len(parts) > 1 else "status"
    now = time.time()
    if sub == "status":
        for n_, _nm, _c in NATIONS:
            mine = npc_of(n_)
            act = [n for n in mine if n["state"] == "active"]
            busy = [n for n in act if n["task"]]
            say(f"nation {n_}: {len(act)}/{len(mine)} active (want {NP.want_active(npc_humans(n_), npc_stand(n_))}), "
                f"{len(busy)} on a task, owns {npc_owned(n_)}{' LAST STAND' if npc_stand(n_) else ''}")
    elif sub == "go" and len(parts) > 2:
        pid, k = int(parts[2]), int(parts[3]) if len(parts) > 3 else 5
        free = [n for n in npc_of(nid) if n["state"] == "active" and not n["task"]][:k]
        if not free:
            say("no free active NPC in your nation (/npc fill)")
            return
        cand = {"pid": pid, "owner": province_owner(pid), "kind": "enemy" if province_owner(pid) else "alien",
                "garrison": 0.0, "dist_cap": 1, "def_power": npc_defence(pid)}
        npc_send(free, cand, now, group=True)
        for n in free:
            n["task"]["arrive"] = now + 5
        say(f"{len(free)} NPC(s) of your nation attack {pid} in 5 s")
    elif sub == "stand":
        st = npc_state()
        st["stand"][str(nid)] = now + (float(parts[2]) if len(parts) > 2 else 1.0) * 3600
        npc_dirty()
        say("last stand on")
    elif sub == "fill":
        for n in npc_of(nid):
            n["state"], n["retire"] = "active", False
            n["think_at"] = now + random.uniform(5, 60)
        npc_dirty()
        say("all NPCs of your nation active (the next tick may retire some again)")
    elif sub == "reset":
        npc_state()["npcs"].clear()
        for n_, _nm, _c in NATIONS:
            npc_ensure_roster(n_)
        say("NPC rosters recreated")
    npc_save(True)
