# sgserver part "battle_flow": alien spawning and AI step, squad lost / redeploy, end of battle, retreat, town walking.
# Loaded by sgserver.py into ONE shared namespace (exec, in the order of PARTS) - not an importable module;
# every name here is a sgserver global.  Checks: python tools/check_server.py
# ---- ALIEN SPAWNING / AI (aliens.py, claude/ALIEN_PLAN.md) ------------------------------------------------------
_PROV_DIST = None
def province_distance(pid):
    """portal steps from the nearest capital (0 = capital) on the 9x9 layout (same for every planet)."""
    global _PROV_DIST
    if _PROV_DIST is None:
        caps = [0, 800, 8, 808]; d = {c: 0 for c in caps}; q = list(caps)
        while q:
            n = q.pop(0)
            for m in PORTAL_LINKS.get(n, ()):
                if m not in d:
                    d[m] = d[n] + 1; q.append(m)
        _PROV_DIST = d
    return _PROV_DIST.get(pid % 10000 if (pid // 10000) % 10 else pid % 100000, 3)

def alien_context(s, mapid):
    """(tier, distance, cave depth 0..3, spawn-spot map name) of a battle map."""
    mapid = real_map(mapid)                      # a simulation map: the aliens of its province
    if mapid < 100000000:
        tier = PLANET_TIER.get((mapid // 100000) % 1000, 1)
        if is_star_province(mapid):       # demon star: the monsters are as strong as the visitor's home planet
            tier = PLANET_TIER.get((CAPITALS.get(getattr(s, "cmd", {}).get("nation"), 600000) // 100000) % 1000, 1)
        k = (mapid // 10000) % 10
        dist = max(1, province_distance(mapid))
        if k in (1, 2, 3):
            return tier, dist, k, f"mon{k}"
        vk = LAYOUT.get((mapid // 100000) % 1000, 2) * 100000 + mapid % 100000
        return tier, dist, 0, VINU_NAME.get(vk)
    ret = getattr(s, "return_to", None)
    rm = ret[0] if ret else CAPITALS.get(getattr(s, "cmd", {}).get("nation"), 600000)
    return PLANET_TIER.get((rm // 100000) % 1000, 1), 3, 2, "cave1"

def branch_max(sessions):
    best = 0
    for o in sessions:
        try:
            br = PG.ensure_commander(get_account(o.acc)[1].setdefault("commander", {}))["branches"]
            best = max(best, max(v["level"] for v in br.values()))
        except Exception:
            pass
    return best

try:
    GATE_SPOTS = {int(k): v for k, v in data_json("gate_spots.json").items()}
except Exception as _e:
    GATE_SPOTS = {}
    print("gate_spots.json:", _e)

def _strat(p):                       # strategic-map position of CCRR (odd columns half a row higher)
    c, r = p // 100, p % 100
    return c * 0.866, r - 0.5 * (c % 2)

def entry_gate(mapid, nid, frm=None):
    """user 2026-10-23 22:31: a commander enters a battle map at the gate of the province HE COMES FROM (a neighbour of
    his side), never at a gate leading to the enemy.  frm = the province he came from (when it is a neighbour);
    otherwise the gate toward the nearest province of his side (closest to his capital).  None = no gate data."""
    gates = GATE_SPOTS.get(int(mapid) % 100000)
    if not gates:
        return None
    pl = int(mapid) // 100000
    if frm and int(frm) // 100000 == pl and (not nid or same_side(province_owner(int(frm)), nid)):
        g = next((g for g in gates if g[0] == int(frm) % 100000), None)
        if g:
            return (g[1], g[2])
    own = [g for g in gates if nid and province_owner(pl * 100000 + g[0]) == nid] or \
          [g for g in gates if nid and same_side(province_owner(pl * 100000 + g[0]), nid)]
    if not own:
        return None
    cap = CAPITALS.get(nid)
    if cap:
        cx, cy = _strat(cap % 100000)
        own.sort(key=lambda g: math.dist(_strat(g[0]), (cx, cy)))
    return (own[0][1], own[0][2])

def gate_starts(mapid, n, nid=None, avoid=None, min_dist=900, frm=None):
    """2026-10-23 (user: NPC units must not stand on the POCs the moment a player enters; reinforcements enter through a
    GATE): n entry points (pixels) at the neighbour gates of province map mapid.  None when the map has no gates.
    Every gate is bound to ONE neighbour province (gate_spots.json from portals.por, same as the client's portals).
    user 2026-10-24 12:29 (a blue NPC came in at the gate of the neighbouring RED province): the n squads used to be
    spread over ALL gates in order of preference, so the 2nd, 3rd ... squad took gates that face the enemy.  Now only
    the best class is used:
      1. the gate of the province the squad marches in from (frm);
      2. else the gates to provinces of the squad's own side / allies (closest to its capital / origin first);
      3. else (no own neighbour) the one gate closest to its capital / origin.
    avoid (the player's arrival): inside that class the gates >= min_dist away are taken; if none, the farthest one of
    the class - never a gate of another class."""
    gates = GATE_SPOTS.get(int(mapid) % 100000)
    if not gates:
        return None
    pl_ = int(mapid) // 100000
    ref = frm if frm else (CAPITALS.get(nid) if nid else None)
    if ref is not None:
        cx, cy = _strat(int(ref) % 100000)
        gates = sorted(gates, key=lambda g: math.dist(_strat(g[0]), (cx, cy)))
    # (user 2026-10-31 11:45, screenshot: NPCs came in through a gate of another nation) the road's gate only when that
    # province is still of its side; then the gates to ITS OWN nation's provinces, then allied ones; never another gate
    frm_ok = frm and (not nid or same_side(province_owner(pl_ * 100000 + int(frm) % 100000), nid))
    pick = [g for g in gates if frm_ok and g[0] == int(frm) % 100000]
    if not pick and nid:
        pick = [g for g in gates if province_owner(pl_ * 100000 + g[0]) == nid]
    if not pick and nid:
        pick = [g for g in gates if same_side(province_owner(pl_ * 100000 + g[0]), nid)]
    if not pick and nid:
        log(f"   gates for nation {nid} on {mapid}: no gate to a province of its side - it may not enter")
        return []
    if not pick:
        pick = gates[:1]
    if avoid is not None:
        far = [g for g in pick if AL.dist((g[1], g[2]), avoid) >= min_dist]
        pick = far or [max(pick, key=lambda g: AL.dist((g[1], g[2]), avoid))]
    log(f"   gates for nation {nid} on {mapid}: {n} squad(s) via the gate(s) to {sorted({g[0] for g in pick})}"
        f"{' (came from ' + str(int(frm) % 100000) + ')' if frm else ''}")
    return [(pick[i % len(pick)][1], pick[i % len(pick)][2]) for i in range(n)]

def gate_neighbour(mapid, x, y):
    """the neighbour province (CCRR) of the gate at pixel (x, y) of province map mapid, None if no gate is that close."""
    best = min(GATE_SPOTS.get(int(mapid) % 100000, ()), key=lambda g: AL.dist((g[1], g[2]), (x, y)), default=None)
    return best[0] if best and AL.dist((best[1], best[2]), (x, y)) < 200 else None

def spawn_homes(name, arrival, n, avoid=800, near=None):
    """n squad home points (pixels) on walkable ground, far from the arrival point and from each other."""
    import random
    spots = [tuple(p) for p in SPAWN_SPOTS.get(name or "", [])]
    if not spots:
        ax, ay = arrival
        spots = [(max(0x100, min(0xF00, ax + dx)), max(0x100, min(0xF00, ay + dy)))
                 for dx in (-0x500, 0, 0x500) for dy in (-0x500, 0, 0x500) if dx or dy]
    far = [p for p in spots if AL.dist(p, arrival) >= avoid] or spots
    random.shuffle(far)
    homes = []
    if near is not None:
        homes.append(min(far, key=lambda p: AL.dist(p, near)))
    while len(homes) < n:
        c = max(far, key=lambda p: min([AL.dist(p, h) for h in homes] or [AL.dist(p, arrival)]))
        homes.append(c)
    return homes

def put_alien_specs(s, members, specs, delayed=False):
    """create the server records of new aliens and PUT them for every member (0x50 with a common game time when
    the battle is already running, so every lock-step client adds them on the same frame)."""
    # (the squad is stamped at send time: delayed_put)
    _sizes = {}
    for _sp in specs:
        _sizes[_sp[4]] = _sizes.get(_sp[4], 0) + 1
    for tid, name, lv, (x, y), squad, boss in specs:
        r = AL.ROLES[name]
        # same-species squads of 5-12: each alien weaker so a squad is about as strong as before (user 2026-10-22)
        _sc = 1.0 if (boss or name == "Hive" or squad is None or squad < 0) else AL.squad_scale(_sizes.get(squad, 4))
        hp, st9, spd = AL.stats(name, lv, boss, _sc)
        if DAMAGE_TYPES:
            st9 = list(st9); st9[1] = DT.ALIEN                  # alien carapace (weak against flame)
        _t, akind, anum = unit_kind(r["code"])
        label = ("Hive Nest" if name == "Hive" else f"{name}{' Primus' if boss else ''}") + f" L{lv}"
        s.targets[tid] = {"hp": hp, "max": hp, "x": x, "y": y, "armor": st9[0], "arow": st9[1], "level": lv, "aggressive": True,
                          "target": None, "name": name, "home": (x, y), "pos": (x, y), "squad": squad,
                          "state": "idle", "boss": boss, "next_patrol": time.time() + random.uniform(10, 30),
                          "put": {"name": label, "owner": alien_owner(s), "kind": akind, "num": anum,
                                  "nation": ALIEN_NATION, "st9": st9, "sight": unit_sight(st9), "spd": spd,
                                  "abil": ABILITY_ATTACK}}
        _abil = 0 if name == "Hive" else ABILITY_ATTACK
        s.targets[tid]["put"]["abil"] = _abil
        body = put_server_unit(tid, label, alien_owner(s), x, y, akind, anum, ALIEN_NATION, hp=hp, energy=1000,
                              stats9=st9, sight=unit_sight(st9), speed=spd, abilities=_abil)
        if delayed:                                   # (battle_rules.delayed_put: the one way, no clock jump)
            s.targets[tid]["enter_t"] = delayed_put(s, body, still=lambda _t=tid: _t in s.targets)
        else:
            for o in members:
                o.send(body)

def next_alien_id(s):
    used = set(s.targets) | set(dead_aliens(s))
    i = 60001
    while i in used:
        i += 1
    return i

def plan_squads(s, squads_, tier, dist, cave, homes, branch_cap_lv, boss_last=False, squad_base=0):
    specs = []
    for qi, (sq, home) in enumerate(zip(squads_, homes)):
        _off = AL.formation(len(sq))
        for k, name in enumerate(sq):
            lv = AL.cap_level(tier, AL.level_for(tier, dist, cave), branch_cap_lv)
            pos = (int(home[0] + _off[k][0]), int(home[1] + _off[k][1]))
            specs.append([None, name, lv, pos, squad_base + qi, False])
    if boss_last and specs:
        b = specs[-1]; b[5] = True
        b[2] = AL.cap_level(tier, AL.TIER_LEVEL[tier][3], branch_cap_lv) if tier == 1 else AL.TIER_LEVEL[tier][3]
    for sp in specs:
        sp[0] = next_alien_id(s); s.targets[sp[0]] = {}       # reserve the id
    for sp in specs:
        s.targets.pop(sp[0], None)
    return [tuple(x) for x in specs]

def spawn_aliens_initial(s, mapid, kind, x, y, raid=False, sim=False):
    """first player of an alien battle: garrison x squads (provinces) or the first wave (hunting grounds/caves)."""
    global WORLD
    tier, dist, cave, name = alien_context(s, mapid)
    bm = branch_max([s])
    s.targets = s.targets if isinstance(getattr(s, "targets", None), dict) else {}
    s.alien_meta = {"tier": tier, "dist": dist, "cave": cave, "map": name, "branch": bm, "players": 1,
                    "mapid": mapid, "full": 0, "waves_left": 0, "next_wave": 0, "squad_n": 0, "arrival": (x, y)}
    s.alien_meta["raid"] = raid
    s.alien_meta["sim"] = sim
    if kind == "province":
        if WORLD is None:
            WORLD = load_world()
        g = 100.0 if (raid or sim) else AL.garrison(WORLD, mapid)
        _msz = MAP_SIZES.get(name or "")
        _st = is_star_province(mapid)
        sq = AL.province_units(tier, dist, g, 1, size=AL.map_factor(_msz[2] if _msz else 0), star=_st)
        if _st and mapid % 100000 == STAR_CENTER and not raid:
            sq.append([AL.STAR_BOSS])     # the centre of a demon star: Miasam boss
            s.alien_meta["star_boss"] = True
        s.alien_meta["full"] = sum(len(q) for q in AL.province_units(tier, dist, 100, 1))
        pocs = list(getattr(s, "pocs_pending", []) or [])
        homes = spawn_homes(name, (x, y), len(sq), near=(pocs[0] if pocs else None))
        log(f"   aliens: tier {tier} distance {dist} garrison {g:.0f}% -> {len(sq)} squad(s)")
        if not raid and not sim:
            try:
                s.send(chat_line(0x0A, f"Alien garrison of this province: {g:.0f}%.", (255, 200, 80)))
            except Exception:
                pass
    elif mapid < 100000000 and cave in (1, 2, 3):
        # HIVE MODE (CAVE_DESIGN.md, user 2026-10-21 23:31): many more aliens, hives in every cave, every hive
        # destroyed = victory, more aliens per player.  The cave GARRISON (0-100 %, own value per cave id) scales
        # the run (at least 50 %), kills lower it, it recovers +10 %/h.
        if WORLD is None:
            WORLD = load_world()
        g = max(50.0, AL.garrison(WORLD, mapid))
        total, n_hives, cap = AL.cave_plan(tier, cave, 1)
        total = max(10, int(round(total * g / 100.0)))
        start = int(total * AL.CAVE_START_SHARE)
        sq = AL.squads_for(start, tier)
        # (user 2026-10-24 18:05) NO HIVE NESTS any more: the run's aliens appear at random places of the cave
        # (n_hives = number of squads that appear together every AL.HIVE_SPAWN_SECONDS); the cave is won when the
        # whole run (budget) has appeared and every alien is dead.
        homes = spawn_homes(name, (x, y), len(sq))
        s.hive_pre = None
        s.alien_meta.update(hive=True, budget=total - sum(len(q) for q in sq), cap=cap, full=total,
                            hunt_from=time.time() + CAVE_HUNT_DELAY, streams=max(1, n_hives),
                            next_spawn=time.time() + AL.HIVE_SPAWN_SECONDS)
        log(f"   aliens: CAVE {cave} random-spawn mode tier {tier} garrison {g:.0f}%: {total} aliens "
            f"({len(sq)} squad(s) now, {s.alien_meta['budget']} to appear, {max(1, n_hives)} squad(s) every "
            f"{AL.HIVE_SPAWN_SECONDS}s), alive cap {cap}")
        try:
            s.send(chat_line(0x0A, f"Alien garrison of this cave: {g:.0f}%.  Aliens keep appearing around the cave - "
                                   f"destroy all {total} to win!  "
                                   f"To retreat, move your units back to the exit portal at your arrival point.", (255, 200, 80)))
        except Exception:
            pass
    else:
        # (17:58) the demon star (social STAR_MAP) has its own monsters and cave-3 levels
        _star = mapid == STAR_MAP
        if _star:
            cave = 3
            s.alien_meta.update(star=True, cave=3)
        sq = AL.cave_wave(tier, cave or 2, 1, 1, star=_star)
        homes = spawn_homes(name, (x, y), len(sq))
        s.alien_meta["waves_left"] = AL.CAVE_WAVES - 1
        s.alien_meta["next_wave"] = time.time() + AL.WAVE_SECONDS
        # (user 2026-10-24 19:32) underground caves / the demon star: every alien goes for the nearest unit at once
        s.alien_meta.update(hunt_all=True, hunt_from=time.time() + CAVE_HUNT_DELAY)
        log(f"   aliens: hunting ground tier {tier} cave {cave} wave 1/{AL.CAVE_WAVES}: {len(sq)} squad(s)")
    specs = plan_squads(s, sq, tier, dist, cave, homes, bm, boss_last=bool(s.alien_meta.get("star_boss")))
    s.alien_meta["squad_n"] = len(sq)
    put_alien_specs(s, [s], specs)
    if raid:
        for sp in specs:
            s.targets[sp[0]]["raid"] = True
    assign_squad_modes(s, specs, name, kind, raid)

def assign_squad_modes(s, specs, mapname, kind, raid=False):
    """2026-10-22 (claude/ALIEN_SQUADS_PLAN.md): every squad gets a behaviour.
    caves (hive mode) / raids: all HUNT the players.  provinces: squad 0 GUARDS its spot (the POC), the last one
    (with 2+ squads) HUNTS after HUNTER_DELAY_PROVINCE s, the others PATROL a route of spawn spots in formation."""
    import random as _r
    meta = s.alien_meta
    squads = sorted({sp[4] for sp in specs if sp[4] is not None and sp[4] >= 0})
    hive = meta.get("hive")
    if (hive or meta.get("hunt_all")) and not raid:
        cave_squad_modes(s, specs, mapname)          # (14:05) caves: part hunts, part patrols
        return
    if kind == "province" and not raid and not hive:
        meta["hunt_from"] = time.time() + AL.HUNTER_DELAY_PROVINCE
    spots = [tuple(p) for p in SPAWN_SPOTS.get(mapname or "", [])]
    routes = meta.setdefault("routes", {})
    for i, q in enumerate(squads):
        mem = [sp for sp in specs if sp[4] == q]
        if hive or raid or (kind == "province" and len(squads) >= 2 and i == len(squads) - 1):
            mode = "hunt"
        elif kind == "province" and i == 0:
            mode = "guard"
        else:
            mode = "patrol"
        home = s.targets[mem[0][0]]["home"]
        if mode == "patrol":
            near = sorted(spots, key=lambda p: AL.dist(p, home))[1:8]
            pts = _r.sample(near, min(3, len(near))) if near else []
            routes[q] = {"pts": [home] + pts, "i": 0, "next": time.time() + _r.uniform(*AL.PATROL_STEP_SECONDS)}
        for k, sp in enumerate(mem):
            tg = s.targets[sp[0]]
            tg["mode"], tg["slot"] = mode, k
            if mode == "hunt":
                tg["hunter"] = True
    log(f"   alien squads: " + ", ".join(f"#{q} {len([sp for sp in specs if sp[4] == q])}x"
                                         f"{next(sp[1] for sp in specs if sp[4] == q)} "
                                         f"{s.targets[next(sp[0] for sp in specs if sp[4] == q)].get('mode')}"
                                         for q in squads))

def cave_squad_modes(s, specs, mapname):
    """(user 2026-10-27 14:05 "一部份主动攻击, 一部份巡逻") cave squads - also the ones that appear later - take turns:
    AL.CAVE_HUNTER_SHARE of them HUNT the players, the others PATROL a route of spawn spots near where they appeared
    (in formation, they fight whatever comes into their aggro radius and call the squads around them)."""
    import random as _r
    meta = s.alien_meta
    spots = [tuple(p) for p in SPAWN_SPOTS.get(mapname or "", [])]
    routes = meta.setdefault("routes", {})
    for q in sorted({sp[4] for sp in specs if sp[4] is not None}):
        mem = [sp for sp in specs if sp[4] == q]
        n = meta.get("cave_sq_n", 0)
        meta["cave_sq_n"] = n + 1
        hunt = int((n + 1) * AL.CAVE_HUNTER_SHARE) > int(n * AL.CAVE_HUNTER_SHARE)     # 0.5 -> every second squad
        home = s.targets[mem[0][0]]["home"]
        mode = "hunt" if hunt else "patrol"
        if mode == "patrol":
            near = sorted(spots, key=lambda p: AL.dist(p, home))[1:12]
            pts = _r.sample(near, min(AL.CAVE_PATROL_POINTS, len(near))) if near else []
            if pts:
                routes[q] = {"pts": [home] + pts, "i": 0, "next": time.time() + _r.uniform(*AL.PATROL_STEP_SECONDS)}
            else:
                mode = "wander"                       # no spawn spots on this map: random steps around its home
        for k, sp in enumerate(mem):
            tg = s.targets[sp[0]]
            tg["mode"], tg["slot"] = mode, k
            tg["hunter"] = mode == "hunt"
    log(f"   cave squads: " + ", ".join(f"#{q} {s.targets[next(sp[0] for sp in specs if sp[4] == q)].get('mode')}"
                                       for q in sorted({sp[4] for sp in specs if sp[4] is not None})))

def spawn_join_squad(B, joiner):
    """a player joins a running alien battle: one more squad (aliens.PARTICIPANT_FACTOR)."""
    owner = B.get("owner"); meta = getattr(owner, "alien_meta", None)
    if not meta or not owner.targets and not meta.get("waves_left"):
        return
    if B.get("defender") or B.get("ambush") or province_owner(B.get("map") or 0):
        # owned province / NPC-vs-NPC ambush on the road: no aliens there.  2026-10-23: a player who joined a nation-1 vs
        # nation-3 ambush got 7 Poda (alien nation) 3 s later and the client crashed (no alien side in that battle)
        return
    meta["players"] += 1
    if meta.get("hive"):
        # hive mode: a joining player raises the run budget (+75 % of a solo run) and the alive cap (+15)
        add = int(round(AL.CAVE_TOTAL[meta["tier"]][meta["cave"]] * AL.CAVE_PLAYER_FACTOR))
        meta["budget"] = meta.get("budget", 0) + add
        meta["cap"] = min(AL.CAVE_ALIVE_MAX, meta.get("cap", AL.CAVE_ALIVE_CAP) + AL.CAVE_ALIVE_STEP)
        meta["branch"] = max(meta["branch"], branch_max([joiner]))
        log(f"   aliens: {joiner.acc} joined the cave -> +{add} aliens to hatch, alive cap {meta['cap']}")
        return
    if len(owner.targets) >= AL.MAX_ALIENS:
        return
    members = [o for o in B["members"] if not o.w.is_closing()]
    meta["branch"] = max(meta["branch"], branch_max([joiner]))
    sq = [AL.squads(meta["tier"])]
    homes = spawn_homes(meta["map"], meta["arrival"], 1)
    specs = plan_squads(owner, sq, meta["tier"], meta["dist"], meta["cave"], homes, meta["branch"],
                        squad_base=meta["squad_n"])
    meta["squad_n"] += 1
    put_alien_specs(owner, members, specs, delayed=True)
    log(f"   aliens: {joiner.acc} joined -> +1 squad {[sp[1] for sp in specs]}")

HIVE_MARK_BASE = 900001

def hive_markers(s, mapid, x, y, B, battle, watch):
    """minimap markers of the hives of a hive-mode cave.  First player: chooses the hive places (kept in s.hive_pre
    for spawn_aliens_initial); joiners: the battle's markers with their current owner."""
    if B:
        return [dict(m) for m in (B.get("hive_marks") or [])]
    s.hive_pre = None
    return []          # (18:05) no hive nests any more -> no hive markers
    if not battle or watch or mapid >= 100000000:
        return []
    try:
        tier, dist, cave, name = alien_context(s, mapid)
    except Exception:
        return []
    if cave not in (1, 2, 3) or map_kind(mapid) != "hunt":
        return []
    _t, n_hives, _c = AL.cave_plan(tier, cave, 1)
    homes = spawn_homes(name, (x, y), n_hives)
    marks = [{"id": HIVE_MARK_BASE + k, "x": int(hx), "y": int(hy), "owner": ALIEN_NATION} for k, (hx, hy) in enumerate(homes)]
    s.hive_pre = marks
    log(f"   hive markers for {mapid}: {[(m['x'], m['y']) for m in marks]}")
    return marks

def hive_marker_destroyed(s, tg):
    mid = tg.get("mark")
    if not mid:
        return
    b = getattr(s, "battle", None) or {}
    owner = getattr(b.get("owner"), "cmd", {}).get("nation", 1) if b else getattr(s, "cmd", {}).get("nation", 1)
    for m in b.get("hive_marks") or []:
        if m["id"] == mid:
            m["owner"] = owner
    pk = bytes([0x49]) + struct.pack(">IHIB", mid, 0, owner, 0)
    for o in (list(b.get("members", [])) or [s]):
        o.send(pk)
    log(f"   hive marker {mid} -> destroyed (owner {owner})")

def alien_removed(s, tid, tg):
    """bookkeeping when an alien dies: province garrison goes down."""
    if tg.get("npc") is not None:
        npc_unit_died(tg)
        return
    if tg.get("hive"):
        hive_marker_destroyed(s, tg)
    meta = getattr(s, "alien_meta", None) or getattr((getattr(s, "battle", None) or {}).get("owner"), "alien_meta", None)
    if meta and (meta.get("cave") == 0 or meta.get("hive")) and meta.get("mapid", 0) < 100000000 and not tg.get("raid") \
            and not meta.get("sim"):
        global WORLD
        if WORLD is None:
            WORLD = load_world()
        AL.garrison_kill(WORLD, meta["mapid"], meta.get("full") or 10)
        save_world(WORLD)

# FUTILE_SECONDS -> battlefield.py (2026-10-24, the battle rules in one place)
# FUTILE_IGNORE -> battlefield.py (2026-10-24, the battle rules in one place)

def _alien_order_move(tid, x, y):
    return bytes([0x1A]) + struct.pack(">IHH", tid, max(0, int(x)), max(0, int(y))) + b"\0\0\0"

# attack / chase orders of the aliens: sgs/unit_orders.py (order_attack, chase_step, dispatch_orders)

CAVE_HUNT_DELAY = 5          # s after the start before the cave aliens set out (the client needs a moment to place units)

def hunt_target(tier, tg, pos, hp, busy=None):
    """hunter target: elite planet = weakest player unit within 1.5 x aggro, else the nearest unit on the map
    (units that already have AL.FOCUS_MAX aliens on them come last)."""
    if not pos:
        return None
    if tier >= 3:
        t = AL.pick_target(tier, tg["pos"], pos, lambda u: hp.get(u, 9999), AL.AGGRO[tier] * 1.5, busy)
        if t is not None:
            return t
    cand = [u for u in pos if not busy or busy.get(u, 0) < AL.FOCUS_MAX] or list(pos)
    return min(cand, key=lambda u: AL.dist(tg["pos"], pos[u]))

def alien_step(s, b, now):
    """one second of the server-owned aliens of a battle (battle_loop; orders = lumps every client simulates):
    idle at home / patrol -> a player unit inside the AGGRO radius starts a fight (and alerts the squad; elite: every
    alien within HELP_RADIUS) -> target choice by tier -> beyond LEASH from home: give up and walk back.
    Also brings the next hunting-ground wave, the hive hatchlings and the boss's call for help.  No aliens = no-op."""
    meta = getattr(s, "alien_meta", None) or {"tier": 1}
    tier = meta.get("tier", 1)
    members = [o for o in b["members"] if not o.w.is_closing()] if b is not None else battle_members(s)
    pos, hp = {}, {}
    _hid_a = set()
    _dets = detectors(s.targets)
    for o in members:
        for u in getattr(o, "alive_units", set()):
            if hidden(u, o.unit_pos.get(u, (0, 0)), _dets):
                _hid_a.add(u)
                continue                 # cloaked and not detected: the aliens cannot see it
            pos[u] = o.unit_pos.get(u, (0, 0))
            hp[u] = getattr(o, "unit_hp", {}).get(u, 9999)
    for _tid, _tg in s.targets.items():         # NPC squads allied to the players are enemies of the aliens too
        if _tg.get("npc") is not None and _tg.get("hp", 0) > 0 and _tg.get("pos"):
            pos[_tid] = _tg["pos"]; hp[_tid] = _tg["hp"]
    msgs = []
    if _hid_a:
        release_hidden(s, _hid_a, msgs, "alien AI")
    # focus spread: how many aliens are already on each player unit (AL.FOCUS_MAX)
    busy = {}
    for _t in s.targets.values():
        if _t.get("state") == "combat" and _t.get("target") is not None:
            busy[_t["target"]] = busy.get(_t["target"], 0) + 1
    def engage(tid, tg, target):
        old = tg.get("target") if tg.get("state") == "combat" else None
        if old is not None and busy.get(old):
            busy[old] -= 1
        busy[target] = busy.get(target, 0) + 1
        order_attack(tid, tg, target, pos.get(target), now, msgs)
    # BATTLE BRAIN for the aliens (claude/NPC_BATTLE_AI_ARCH.md): the squad focuses the most valuable target
    # it can reach (dangerous + easy to kill, artillery / support first), at most `focus` aliens per target,
    # a tier-dependent share of wrong choices; the old nearest / weakest rule when the brain has nothing
    _ab = {}
    def apick(tid, tg, R):
        if ALIEN_BRAIN:
            try:
                if not _ab:
                    holder = b if b is not None else s.__dict__
                    br = holder.get("alien_brain")
                    if br is None:
                        br = holder["alien_brain"] = BAI.Brain(tier=tier, seed=tid, alien=True)
                    br._load = {}
                    uw, _P, _st = brain_world(s, members, now, None)
                    for _u, _p in pos.items():               # (positions as alien_ai sees them)
                        if _u in uw:
                            uw[_u].pos = (float(_p[0]), float(_p[1]))
                    _ab.update(br=br, units=uw, enemies=[x for _u, x in uw.items() if _u in pos], rank={})
                br, uw = _ab["br"], _ab["units"]
                me = uw.get(tid)
                if me is not None:
                    sq = tg.get("squad")
                    if sq not in _ab["rank"]:
                        mates = [x for x in uw.values() if x.side == ALIEN_NATION and x.squad == ("a", sq)] or [me]
                        _ab["rank"][sq] = br.focus(mates, _ab["enemies"], now)
                    e = br._pick(me, _ab["rank"][sq], _ab["enemies"], max_d=max(R, me.max_rng() + 20))
                    if e is not None:
                        return e.id
            except Exception as e:
                log(f"   alien brain error: {e!r}")
        # (user 2026-10-23 15:11) only what its weapons can hit: aircraft need an air weapon
        _st = (tg.get("put") or {}).get("st9") or ()
        _aa = len(_st) > 6 and _st[6] > 0
        _gd = len(_st) < 4 or _st[3] > 0
        _air = {u for o in members for u, pa in (getattr(o, "put_args", {}) or {}).items() if (pa or {}).get("kind") == 2}
        cands = {u: p for u, p in pos.items() if (_aa if u in _air else _gd)}
        return AL.pick_target(tier, tg["pos"], cands, lambda u: hp.get(u, 9999), R, busy)
    # wounded aliens (not bosses / hunters / hives) break off and run home, like a beast would
    for tid, tg in list(s.targets.items()):
        if (ALIEN_BRAIN and tg.get("npc") is None and tg.get("state") == "combat" and not tg.get("boss")
                and not tg.get("hunter") and not tg.get("hive") and "home" in tg
                and tg.get("hp_c", tg["hp"]) < 0.2 * tg.get("max", tg["hp"]) and not tg.get("fled")):
            tg["fled"] = True
            tg["state"], tg["target"], tg["return_until"] = "return", None, now + 10
            stop_chase(tg)
            msgs.append(_alien_order_move(tid, *tg["home"]))
    # PATROL squads walk their route in formation (claude/ALIEN_SQUADS_PLAN.md)
    for q, rt in list((meta.get("routes") or {}).items()):
        mem = [(tid, tg) for tid, tg in s.targets.items() if tg.get("squad") == q and tg.get("mode") == "patrol"]
        if not mem:
            meta["routes"].pop(q, None)
            continue
        if now < rt["next"] or any(tg.get("state", "idle") != "idle" for _t, tg in mem) or len(rt["pts"]) < 2:
            continue
        rt["i"] = (rt["i"] + 1) % len(rt["pts"])
        rt["next"] = now + random.uniform(*AL.PATROL_STEP_SECONDS)
        px, py = rt["pts"][rt["i"]]
        offs = AL.formation(len(mem))
        for k, (tid, tg) in enumerate(sorted(mem, key=lambda m: m[1].get("slot", 0))):
            dest = (px + offs[k][0], py + offs[k][1])
            tg["pos"] = tg["home"] = dest             # the leash / return point follows the route
            msgs.append(_alien_order_move(tid, *dest))
    for tid, tg in list(s.targets.items()):
        if not tg.get("aggressive") or "home" not in tg or tg.get("npc") is not None:
            continue
        st = tg.get("state", "idle")
        if st == "return":
            if now >= tg.get("return_until", 0):
                tg["state"], tg["pos"] = "idle", tg["home"]
            continue
        if st == "combat":
            _leash = AL.CAVE_LEASH if meta.get("hive") else AL.LEASH[tier]
            if not tg.get("hunter") and AL.dist(_npc_est_pos(tg, now), tg["home"]) > _leash:
                tg["state"], tg["target"] = "return", None
                stop_chase(tg)
                tg["return_until"] = now + 8
                msgs.append(_alien_order_move(tid, *tg["home"]))
                continue
            if tg.get("target") in pos:
                if chase_step(tid, tg, pos[tg["target"]], now, msgs):
                    continue                            # walking to its target (unit_orders)
                # NO-DAMAGE CHECK (client 004d0420 gives 0 damage when the target is out of range at the
                # hit tick or when attacker and target are on different sides of a DEFENSIVE MATRIX circle
                # - the attack animation still plays).  If the target's reported HP (0x21, every ~5 s)
                # has not dropped after FUTILE_SECONDS, ignore it for a while and pick another one; with
                # no other target walk onto it (inside the matrix the hits count again).
                tgt = tg["target"]
                if tg.get("hp_mark_t") is None or tg.get("hp_mark_u") != tgt:
                    tg["hp_mark_t"], tg["hp_mark_u"], tg["hp_mark"] = now, tgt, hp.get(tgt, 9999)
                elif now - tg["hp_mark_t"] >= FUTILE_SECONDS:
                    if hp.get(tgt, 9999) >= tg["hp_mark"]:
                        tg.setdefault("ignore", {})[tgt] = now + FUTILE_IGNORE
                        others = {u: p for u, p in pos.items() if tg["ignore"].get(u, 0) < now}
                        t2 = AL.pick_target(tier, tg["pos"], others, lambda u: hp.get(u, 9999), AL.AGGRO[tier] * 1.5, busy)
                        if t2 is not None:
                            log(f"   alien {tid}: no damage on {tgt} for {FUTILE_SECONDS}s -> switches to {t2}")
                            engage(tid, tg, t2)
                        else:
                            log(f"   alien {tid}: no damage on {tgt} for {FUTILE_SECONDS}s -> walks onto it")
                            stop_chase(tg)
                            _plain_move(tid, tg, pos[tgt], now, msgs)
                            tg["move_then_attack"] = (tgt, now + 3)
                    tg["hp_mark_t"], tg["hp_mark"] = now, hp.get(tgt, 9999)
                mta = tg.get("move_then_attack")
                if mta and now >= mta[1]:
                    tg.pop("move_then_attack", None)
                    if mta[0] in pos:
                        order_attack(tid, tg, mta[0], pos[mta[0]], now, msgs)
                continue
            t2 = apick(tid, tg, AL.AGGRO[tier] * 1.5)
            if t2 is None and tg.get("hunter"):
                t2 = hunt_target(tier, tg, pos, hp, busy)  # hunters: next player unit anywhere
            if t2 is not None:
                engage(tid, tg, t2)
            else:
                tg["state"], tg["target"] = "return", None
                stop_chase(tg)
                tg["return_until"] = now + 8
                msgs.append(_alien_order_move(tid, *tg["home"]))
            continue
        # idle / patrol
        t2 = apick(tid, tg, AL.AGGRO[tier])
        if t2 is None and tg.get("hunter") and now >= meta.get("hunt_from", 0):
            # HUNTER (caves, raids, one province squad): the nearest player unit anywhere, whole squad
            t2 = hunt_target(tier, tg, pos, hp, busy)
        if t2 is not None:
            engage(tid, tg, t2)
            for tid2, tg2 in s.targets.items():          # call for help: the squad + squads close by
                if tid2 == tid or tg2.get("state") == "combat" or "home" not in tg2 or not tg2.get("aggressive"):
                    continue
                if tg2.get("squad") == tg.get("squad") or AL.dist(tg2["pos"], tg["pos"]) <= AL.HELP_RADIUS:
                    t3 = apick(tid2, tg2, AL.AGGRO[tier] * 2) or t2
                    engage(tid2, tg2, t3)
            continue
        if tg.get("mode") == "patrol":
            continue                                    # moved with its squad (route above)
        if now >= tg.get("next_patrol", 0):
            tg["next_patrol"] = now + random.uniform(20, 40)
            hx, hy = tg["home"]
            dx, dy = random.uniform(-AL.PATROL_RADIUS, AL.PATROL_RADIUS), random.uniform(-AL.PATROL_RADIUS, AL.PATROL_RADIUS)
            tg["pos"] = (hx + dx, hy + dy)
            msgs.append(_alien_order_move(tid, hx + dx, hy + dy))
        # boss: call help once at half HP
    for tid, tg in list(s.targets.items()):
        if tg.get("boss") and not tg.get("boss_called") and tg["hp"] <= tg["max"] / 2:
            tg["boss_called"] = True
            sq = [AL.squads(tier)]
            specs = plan_squads(s, sq, tier, meta.get("dist", 3), meta.get("cave", 0), [tg["home"]],
                                meta.get("branch", 0), squad_base=meta.get("squad_n", 0))
            meta["squad_n"] = meta.get("squad_n", 0) + 1
            put_alien_specs(s, members, specs, delayed=True)
            log(f"   boss {tid} at half HP: calls {[sp[1] for sp in specs]}")
    # random-spawn caves (18:05, replaces the hive nests): every HIVE_SPAWN_SECONDS `streams` hunter squads appear at
    # random walkable places away from the players, until the run budget is used up
    if meta.get("hive") and meta.get("budget", 0) > 0 and now >= meta.get("next_spawn", 0):
        import random as _r
        meta["next_spawn"] = now + AL.HIVE_SPAWN_SECONDS
        alive_n = len(s.targets)
        _pp = [p for o in members for p in (getattr(o, "unit_pos", None) or {}).values()] or [meta.get("arrival", (0x400, 0x400))]
        _spots = [tuple(p) for p in SPAWN_SPOTS.get(meta.get("map") or "", [])] or [meta.get("arrival", (0x400, 0x400))]
        _far = [p for p in _spots if min(AL.dist(p, q) for q in _pp) >= 800] or _spots
        for _k in range(meta.get("streams", 1)):
            if alive_n >= meta.get("cap", AL.CAVE_ALIVE_CAP) or meta.get("budget", 0) <= 0:
                break
            sq = [AL.squads(tier)]
            meta["budget"] = meta.get("budget", 0) - len(sq[0])
            specs = plan_squads(s, sq, tier, meta.get("dist", 3), meta.get("cave", 1), [_r.choice(_far)],
                                meta.get("branch", 0), squad_base=meta.get("squad_n", 0))
            meta["squad_n"] = meta.get("squad_n", 0) + 1
            put_alien_specs(s, members, specs, delayed=True)
            cave_squad_modes(s, specs, meta.get("map"))
            alive_n += len(specs)
            log(f"   cave: {[sp[1] for sp in specs]} appeared at {specs[0][3]} (budget left {meta['budget']}, alive {alive_n})")
    # hunting-ground waves
    if meta.get("waves_left", 0) > 0 and (now >= meta.get("next_wave", 0) or not s.targets):
        meta["waves_left"] -= 1
        meta["next_wave"] = now + AL.WAVE_SECONDS
        sq = AL.cave_wave(tier, meta.get("cave") or 2, meta.get("players", 1), AL.CAVE_WAVES - meta["waves_left"],
                          star=bool(meta.get("star")))
        homes = spawn_homes(meta.get("map"), meta.get("arrival", (0x400, 0x400)), len(sq))
        specs = plan_squads(s, sq, tier, meta.get("dist", 3), meta.get("cave", 2), homes, meta.get("branch", 0),
                            boss_last=(meta["waves_left"] == 0), squad_base=meta.get("squad_n", 0))
        meta["squad_n"] = meta.get("squad_n", 0) + len(sq)
        put_alien_specs(s, members, specs, delayed=True)
        if meta.get("hunt_all"):
            cave_squad_modes(s, specs, meta.get("map"))
        log(f"   hunting ground: wave {AL.CAVE_WAVES - meta['waves_left']}/{AL.CAVE_WAVES} "
            f"({len(specs)} aliens{', boss' if meta['waves_left'] == 0 else ''})")
    msgs = dispatch_orders(s, b, members, msgs, now, "alien AI")
    if msgs:
        clog(f"   alien AI: {len(msgs)} order(s)")

def acid_bura_death(s, uid):
    """a dying unit that carries Acid Bura bursts (Self Destruct rules, CONFIRMED 004d8c10: 280 px, POWER of bit 4).
    The clients draw it from the injected lump 0x30 [uid][25] (needs client F21); the server applies the same damage
    to its aliens.  -> True when the unit has the item."""
    import math
    _accs, a = get_account(getattr(s, "acc", None))
    u = next((x for x in a.get("units", []) if x["uid"] == uid), None)
    if not u or ACID_BURA_ID not in u.get("items", []):
        return False
    ux, uy = s.unit_pos.get(uid, (-9999, -9999))
    pw = skill_power(uid, 25) or SELF_DESTRUCT_DEFAULT
    delay = max(1, getattr(s, "lump_exec_t", game_time(s) + RELAY_DELAY) - game_time(s))
    hit = [t for t, tg in list(getattr(s, "targets", {}).items())
           if math.hypot(tg["x"] - ux, tg["y"] - uy) <= SELF_DESTRUCT_RADIUS]
    for t in hit:
        damage_target(s, uid, t, pw, "Acid Bura", delay)
    log(f"   ACID BURA: unit {uid} burst at ({ux},{uy}), power {pw}, {len(hit)} alien(s) hit")
    return True

def on_unit_lost(s, uid):
    """A player's unit died (its owner reported 0x1e 'Death').  Its HP is kept at 0 until repaired."""
    if uid not in getattr(s, "alive_units", set()):
        return
    s.alive_units.discard(uid)
    s.lost_units = getattr(s, "lost_units", set()) | {uid}
    SHIELDS.pop(uid, None)
    CLOAKED.pop(uid, None)
    CARRIED.pop(uid, None)
    if uid in CARRIED.values():
        release_passengers(s, uid, kill=True)
    stop_attack(s, uid)
    accs, a = get_account(getattr(s, "acc", None))
    u = next((x for x in a["units"] if x["uid"] == uid), None)
    if u is not None:
        u["hp"] = 0
        accs[s.acc] = a
        save_accounts(accs)
    try:                                                     # (10-24) TAB window: the NPC that killed it
        _k = npc_killer_of(s, uid)
        if _k is not None:
            npc_score_kill(s, _k, (u or {}).get("level", 1))
    except Exception as e:
        log(f"   npc kill credit error: {e!r}")
    log(f"   player unit {uid} destroyed, {len(s.alive_units)} left")
    if not s.alive_units and getattr(s, "targets", None):
        squad_lost(s, "destroyed")

# ---- SQUAD LOST -> RE-DEPLOY or RETREAT (CONFIRMED 2026-10-21, client 004a6d70 / 004a4fa0 / 004a71a0 / 004a6f20) --
# server class-B 0x51 [u32 WAIT s][u32 WINDOW s] (battle mode only) opens the reinforce box:
#   during WAIT  "You can reinforce after %d seconds. Press <F7> to ready your next squad!" (F7 / Deploy enabled:
#                client 0x19 [00] -> server 0x1C deploy window -> client 0x19 [01] new division);
#   after WAIT   "You must reinforce now or you will retreat in %d seconds."  REINFORCE (box button 0x22) ->
#                004a6f20: division empty -> ksNoUnitActive + deploy window, else CLIENT 0x53 [] = enter with the
#                current division;  RETREAT button (0x26) or WINDOW over -> client 0x54 (forced retreat).
# REDEPLOY_WAIT -> battlefield.py (2026-10-24, the battle rules in one place)
# REDEPLOY_WINDOW -> battlefield.py (2026-10-24, the battle rules in one place)

REDEPLOY_NO_BOX = False     # user 2026-10-25 16:30: after a retreat the RETREAT / REINFORCE box (0x51) must appear

def squad_lost(s, why):
    if getattr(s, "spectator", False) or not getattr(s, "battle", None):
        return
    import time as _t
    s.redeploy_pending = True
    s.redeploy_chosen = False
    s.redeploy_why = why
    s.redeploy_t0 = _t.time()
    # user 2026-10-25 00:38: with the 0x51 box up the client blocks F7 and the box makes the player wait REDEPLOY_WAIT s.
    # While living units are left, no box: the deploy window is opened by F7 / Reinforce (0x1C) and F7 (0x19 [00] -> 0x1C) keeps working;
    # the watchdog below still ends the wait.  Nothing left to send -> the box (REINFORCE -> defeat) as before.
    _left = any(hp_alive(u) and u["uid"] not in getattr(s, "lost_units", set())
                for u in get_account(s.acc)[1].get("units", []))
    # user 2026-10-25 15:28: an ATTACK with nobody of the attacking side left on the field (own players, allied NPC units)
    # is lost at once (result window); with a teammate still fighting the player gets the reinforce box instead.
    try:
        _b = getattr(s, "battle", None)
        _m = getattr(s, "map", None) or 0
        _me = side_nation(s)
        _dfd = (_b or {}).get("defender") or 0
        _atk = (0 < _m < 100000000 and map_kind(_m) == "province" and not (_dfd and same_side(_me, _dfd)))
        _mates = any(o is not s and getattr(o, "alive_units", None) and not getattr(o, "spectator", False)
                     and same_side(side_nation(o), _me) for o in list((_b or {}).get("members", ())))
        _mates = _mates or any(tg.get("npc") is not None and tg.get("hp", 0) > 0 and same_side(tg.get("nation"), _me)
                               for tg in ((_b or {}).get("targets") or {}).values())
    except Exception as e:
        log(f"   squad_lost mates check error: {e!r}")
        _atk, _mates = False, False
    if _atk and why == "destroyed" and not _mates:
        _left = False                                    # no reserve counts: the attack failed
        s.redeploy_pending = False
        _say_lang(s, "进攻方场上已没有任何单位，进攻失败。", "進攻方場上已沒有任何單位，進攻失敗。",
                  "No unit of the attacking side is left on the field - the attack failed.", (255, 160, 120))
        log(f"   attack lost: nobody of the attackers left on {_m} -> defeat now ({s.acc})")
        gen1 = getattr(s, "battle_gen", None)

        async def _atk_lost():
            await asyncio.sleep(3)
            if getattr(s, "battle_gen", None) == gen1 and not s.w.is_closing() and getattr(s, "battle", None):
                await end_battle(s, gen1, won=False)
        spawn(_atk_lost())
        return
    if _atk and why == "destroyed" and _mates:
        s.send(bytes([0x51]) + struct.pack(">II", REDEPLOY_WAIT, REDEPLOY_WINDOW))
        log(f"   squad destroyed, teammates still fighting: 0x51 reinforce box -> {s.acc}")
        _left = True
        gen = getattr(s, "battle_gen", None)

        async def watchdog2():
            await asyncio.sleep(REDEPLOY_WAIT + REDEPLOY_WINDOW + 15)
            if getattr(s, "battle_gen", None) != gen or s.w.is_closing() or not getattr(s, "redeploy_pending", False):
                return
            s.redeploy_pending = False
            log(f"   re-deploy window over without an answer -> {s.acc} leaves the battle")
            retreat(s, getattr(s, "hero_uid", HERO_UID), *retreat_target(s), confirmed=True)
        spawn(watchdog2())
        return
    if REDEPLOY_NO_BOX and _left:
        _say_lang(s, "队伍已撤出战场。按 F7 或「增援」键打开派兵窗口，选择下一队，按 OK 后进场。",
                  "隊伍已撤出戰場。按 F7 或「增援」鍵開啟派兵視窗，選擇下一隊，按 OK 後進場。",
                  "Your squad is out. Press F7 or Reinforce to open the deploy window, choose the next squad, OK to enter.",
                  (255, 220, 120))
        log(f"   squad {why}: no 0x51 box, F7 / Reinforce open the deploy window -> {s.acc}")
    elif not _left and why == "destroyed":
        # user 2026-10-25 15:26: every unit of the commander is dead and nothing is in reserve - there is nothing to wait
        # for (the box with its 20 + 60 s only left the player staring at an empty map): the battle is lost NOW, result
        # window, then straight back to the capital (end_battle: no unit alive).
        s.redeploy_pending = False
        _say_lang(s, "所有单位都已阵亡，战斗失败。", "所有單位都已陣亡，戰鬥失敗。",
                  "Every unit is destroyed - the battle is lost.", (255, 160, 120))
        log(f"   squad destroyed and no unit left alive -> defeat now ({s.acc})")
        gen0 = getattr(s, "battle_gen", None)

        async def _lose_now():
            await asyncio.sleep(3)
            if getattr(s, "battle_gen", None) == gen0 and not s.w.is_closing() and getattr(s, "battle", None):
                await end_battle(s, gen0, won=False)
        spawn(_lose_now())
        return
    else:
        s.send(bytes([0x51]) + struct.pack(">II", REDEPLOY_WAIT, REDEPLOY_WINDOW))
        log(f"   squad {why}: 0x51 re-deploy box ({REDEPLOY_WAIT} s wait, {REDEPLOY_WINDOW} s to choose) -> {s.acc}")
    gen = getattr(s, "battle_gen", None)

    async def watchdog():
        await asyncio.sleep(REDEPLOY_WAIT + REDEPLOY_WINDOW + 15)
        if getattr(s, "battle_gen", None) != gen or s.w.is_closing() or not getattr(s, "redeploy_pending", False):
            return
        s.redeploy_pending = False
        log(f"   re-deploy window over without an answer -> {s.acc} leaves the battle")
        if why == "destroyed":
            spawn(end_battle(s, gen, won=False))
        else:
            retreat(s, getattr(s, "hero_uid", HERO_UID), *retreat_target(s), confirmed=True)
    spawn(watchdog())

REDEPLOY_CHOOSE = True

def redeploy(s):
    """client 0x53 []: enter the battle again with the division chosen in the deploy window."""
    import time as _t
    if not getattr(s, "battle", None) or getattr(s, "spectator", False):
        return
    if getattr(s, "alive_units", None):
        log("   0x53 re-deploy ignored: units still on the field")
        return
    # (user 2026-10-24 21:56: after a retreat F7 could not open the deploy window - the client blocks F7 while the
    # re-deploy box is up, log 21:55: no 0x19 at all) REINFORCE in the box now opens the deploy window first; the
    # division chosen there enters after OK (set_deploy -> redeploy with redeploy_chosen set).
    if REDEPLOY_CHOOSE and not getattr(s, "redeploy_chosen", False) \
            and any(hp_alive(u) and u["uid"] not in getattr(s, "lost_units", set())
                    for u in get_account(s.acc)[1].get("units", [])):
        s.send(bytes([0x1C, 0]))
        _say_lang(s, "请在派兵窗口选择这次要进场的单位，按 OK 后进场。", "請在派兵視窗選擇這次要進場的單位，按 OK 後進場。",
                  "Choose the units to send in, they enter after OK.", (255, 220, 120))
        log("   0x53 re-deploy: deploy window first (choose the next squad)")
        return
    # the 20 s wait of the original box (REDEPLOY_WAIT) is kept without the box: an early OK enters when it is over
    # (16:34) F7 works while the box is up (client F33): the 20 s regroup wait is enforced here for both ways in
    rem = REDEPLOY_WAIT - (_t.time() - getattr(s, "redeploy_t0", 0))
    if rem > 0.5 and getattr(s, "redeploy_pending", False):
        if not getattr(s, "redeploy_timer", False):
            s.redeploy_timer = True
            _say_lang(s, f"部队整补中，{int(rem + 0.5)} 秒后进场。", f"部隊整補中，{int(rem + 0.5)} 秒後進場。",
                      f"Regrouping - the squad enters in {int(rem + 0.5)} s.", (255, 220, 120))
            gen_ = getattr(s, "battle_gen", None)

            async def _later():
                await asyncio.sleep(rem)
                s.redeploy_timer = False
                if getattr(s, "battle_gen", None) == gen_ and not s.w.is_closing() and getattr(s, "redeploy_pending", False) \
                        and not getattr(s, "alive_units", None):
                    redeploy(s)
            spawn(_later())
        log(f"   0x53 re-deploy: wait {rem:.0f} s more")
        return
    s.redeploy_chosen = False
    accs, a = get_account(s.acc)
    cmd = PG.ensure_commander(a.setdefault("commander", {}))
    lost = getattr(s, "lost_units", set())

    _cur = lambda u: hp_battle_en(cmd, u)               # (sgs/unit_hp.py)
    div = sorted((u for u in a["units"] if int(u.get("deploy", 0) or 0) and hp_alive(u)
                  and u["uid"] not in lost), key=lambda u: int(u["deploy"]))[:PG.deploy_limit(cmd)]
    if not div:
        if not any(hp_alive(u) and u["uid"] not in lost for u in a["units"]):
            # user 2026-10-23 13:14: every unit dead, nothing in reserve -> the deploy window only offered dead units
            # and RETREAT then hung.  Nothing left to send: the battle is lost, result window, back home.
            s.redeploy_pending = False
            _say_lang(s, "没有可以出战的单位了，战斗失败，退回邻省。", "沒有可以出戰的單位了，戰鬥失敗，退回鄰省。",
                      "No unit left to deploy - the battle is lost, falling back to a neighbouring province.", (255, 160, 120))
            log(f"   0x53 re-deploy: {s.acc} has no living unit left -> defeat")
            spawn(end_battle(s, getattr(s, "battle_gen", None), won=False))
            return
        s.send(bytes([0x1C, 0]))   # 1-byte packets cannot be decoded by the client (CheckSumError) -> pad
        _say_lang(s, "请在派兵窗口选择还活着的单位，按 OK 后会自动进场。", "請在派兵視窗選擇還活著的單位，按 OK 後會自動進場。",
                  "Choose living units in the deploy window - they enter the battle after OK.", (255, 220, 120))
        log("   0x53 re-deploy: division empty -> deploy window")
        return
    squad = [(u["uid"],) + unit_kind(u["chassis"])[1:] + _cur(u) + (unit_stats9(u), unit_speed(u)) for u in div]
    s.redeploy_pending = False
    s.reserve = [r for r in getattr(s, "reserve", []) if r[0] not in {q[0] for q in squad}]
    put_squad(s, squad)
    s.send(arrival_notice())
    s.reinforce_count = getattr(s, "reinforce_count", 0) + 1
    s.last_reinforce = _t.time()
    log(f"   RE-DEPLOY: {s.acc} enters again with {[q[0] for q in squad]}")

def detectors_off(s):
    """switch every server unit's Detector (action 43) off for this client when the battle is over: the client draws the
    detection ring for as long as it is on."""
    b = getattr(s, "battle", None)
    T = (b.get("targets") if b else None) or getattr(s, "targets", None) or {}
    msgs = []
    for tid, tg in T.items():
        if tg.get("detect_on"):
            tg["detect_on"] = False
            msgs.append(bytes([0x30]) + struct.pack(">I", tid) + bytes([43, 0]))
    if msgs and not s.w.is_closing():
        pk = bytes([0x80, 0, 0]) + struct.pack(">IH", game_time(s) + 2, len(msgs))
        for m in msgs:
            pk += struct.pack(">H", len(m)) + m
        s.send(pk)
        log(f"   battle over: {len(msgs)} Detector ring(s) switched off for {getattr(s, 'acc', '?')}")

async def end_battle(s, gen, won):
    """All enemies destroyed -> leave the battle map and go back to the commander's capital.
    TODO: the real result window is server type 0x27 (client FUN_004b4980, 'fldhinfo'/'fldinfo5..9':
    4 side records {u8, s8, u8, u8, u32, u32}, ...) -- not decoded yet, so for now we only return to town."""
    try:                                         # user 2026-10-25 12:03: the Detector ring must not stay on after the battle
        detectors_off(s)
    except Exception as e:
        log(f"   detectors_off error: {e!r}")
    await asyncio.sleep(BATTLE_END_DELAY)
    if getattr(s, "battle_gen", None) != gen or s.w.is_closing():
        return
    if getattr(s, "spectator", False):
        log(f"   battle over -> spectator {s.acc} returns to his capital")
        s.spectator = False
        enter_field(s, CAPITALS.get(s.cmd.get("nation"), 600000), 0x200, 0x200, capital=True)
        return
    for t in list(getattr(s, "attacks", {}).values()):
        t.cancel()
    s.attacks = {}
    if getattr(s, "sim_snap", None) is not None:
        await sim_finish(s, gen, won)
        return
    _stored = hp_store(s)                              # (sgs/unit_hp.py) live battle HP -> roster
    if _stored:
        log(f"   unit HP after battle (roster, equipment scale): {_stored}")
    s.unit_hp = {}
    cmd = getattr(s, "cmd", {"nation": 1})
    prov = getattr(s, "cur_province", None)
    # a real conquest = the province changes hands (winning a defence of your own province is not a capture)
    captured = bool(won and prov and getattr(s, "battle_kind", "") == "province"
                    and getattr(s, "prov_owner0", province_owner(prov)) != side_nation(s))
    try:
        record_battle(s, won, getattr(s, "battle_kind", ""), captured)
    except Exception as e:
        import traceback
        log(f"   record_battle error: {e!r} {traceback.format_exc()[-400:]}")
    try:                                                # (10-31 14:36) the units' honor records
        _own0 = getattr(s, "prov_owner0", province_owner(prov)) if prov else None
        units_battle_end(s, won, captured, bool(won and prov and getattr(s, "battle_kind", "") == "province" and _own0
                                                  and same_side(_own0, side_nation(s))))
    except Exception as e:
        log(f"   units_battle_end error: {e!r}")
    reward = [0] * 5
    if captured:                                        # defenders holding their province get no capture reward
        capture_province(prov, side_nation(s))         # (one logic; a second winner of the same battle: no-op)
        tier = PLANET_TIER.get((prov // 100000) % 1000, 1)
        reward = apply_abundance([r * tier for r in PROVINCE_CAPTURE_REWARD], prov)
        accs, a = get_account(getattr(s, "acc", None))
        res_add(a, reward)
        accs[s.acc] = a
        save_accounts(accs)
        log(f"   province {prov} captured for nation {cmd['nation']}, capture reward {reward}")
        if is_star_province(prov) and prov % 100000 == STAR_CENTER:
            try:
                nation_say(side_nation(s), "Your faction holds the centre of the demon star! Its Lab now sells "
                                           "demon-star equipment.", (255, 200, 60))
            except Exception as e:
                log(f"   star centre notice: {e!r}")
    try:
        pay_damage_xp(s)
    except Exception as e:
        log(f"   damage XP error: {e!r}")
    try:
        if won:
            award_victory_xp(s, captured=captured)
        record_faction(s, won)
    except Exception as e:
        import traceback
        log(f"   battle bookkeeping error: {e!r} {traceback.format_exc()[-400:]}")
    try:
        award_bonus_xp(s)
    except Exception as e:
        log(f"   bonus XP error: {e!r}")
    if won and getattr(s, "side_nation", None):
        # mercenary: paid in resources for his service (MERCENARY_BONUS_PCT of the battle's gains)
        st = getattr(s, "battle_stats", {}) or {}
        bonus = [int((g + r) * MERCENARY_BONUS_PCT / 100) for g, r in zip(st.get("gain", [0] * 5), reward)]
        accs, a = get_account(s.acc)
        res_add(a, bonus)
        accs[s.acc] = a
        save_accounts(accs)
        reward = [r + b for r, b in zip(reward, bonus)]
        log(f"   mercenary bonus {bonus}")
    battle_report(s, 1 if won else 0, reward)          # (10-31 15:01) the HUD's battle report
    try:
        s.send(build_battle_result(s, won, reward))
        log(f"   battle result window (0x25) sent: gain {getattr(s, 'battle_stats', {}).get('gain')} + reward {reward}")
        xp_summary(s)
    except Exception as e:
        log(f"   battle result window failed: {e!r}")
    await asyncio.sleep(RESULT_SHOW_SECONDS)
    if getattr(s, "battle_gen", None) != gen or s.w.is_closing():
        return
    _accs, a = get_account(getattr(s, "acc", None))
    s.send(build_commander(s.acc, cmd["nation"], cmd.get("attrs", (0, 0, 0, 0)), resources=a["resources"]))
    if won and prov and getattr(s, "battle_kind", "") == "province" \
            and not (province_owner(prov) and not same_side(province_owner(prov), side_nation(s))):
        # (user 2026-10-23 21:47: only on land of his side - a province another nation holds is left after the result)
        # design (user 2026-10-20): after capturing a province the commander STAYS on that map - it is now his
        # nation's territory, so it is re-entered as a town map (battle 0) at the place where the fight ended.
        pts = [s.unit_pos[u] for u in getattr(s, "alive_units", set()) if u in getattr(s, "unit_pos", {})]
        x, y = pts[0] if pts else (0x800, 0x800)
        log(f"   battle over (victory) -> staying on captured province {prov} at ({x},{y})")
        s.battle_kind = ""
        # close this battle FIRST: enter_field decides town/battle from "mapid in BATTLES", and the finished battle
        # was still registered there -> the captured province was re-entered as a NEW battle (units could not move)
        leave_map(s, "battle over")
        enter_field(s, prov, x, y, capital=False)
        return
    ret = getattr(s, "return_to", None)
    if ret and (getattr(s, "map", 0) >= 100000000 or map_kind(getattr(s, "map", 0) or 0) == "hunt"):
        # cave / CTF: back to the province (or capital) whose portal the commander used
        (rm, (rx, ry), rcap) = ret
        s.return_to = None
        log(f"   battle over ({'victory' if won else 'defeat'}) -> back to {rm} at ({rx},{ry})")
        enter_field(s, rm, rx, ry, capital=rcap)
        return
    if prov and getattr(s, "battle_kind", "") == "province":
        # user 2026-10-25 00:20: an attack that ends (POC taken by the enemy / squad lost) falls back ONE province, not
        # to the capital.  Target: the province came from, else the best own / allied neighbour; never enemy land.
        # user 2026-10-25 13:51: a province lost in battle (attacker or defender) = ONE step back towards the capital; only a
        # commander whose units are ALL dead is sent straight to the capital.
        _alive = any(hp_alive(u) and u["uid"] not in getattr(s, "lost_units", set())
                     for u in get_account(getattr(s, "acc", None))[1].get("units", []))
        tgt, dest = (capital_fallback(s, prov) if _alive else (None, None))
        if tgt is None and _alive:
            tgt, dest = retreat_target(s)
        if not _alive:
            log(f"   no unit left alive -> straight back to the capital")
        me = side_nation(s)
        if tgt and tgt != prov and province_owner(tgt) and not same_side(province_owner(tgt), me):
            tgt = None
            try:
                _pl, _here = prov // 100000, province_of(prov) % 100000
                _cap = CAPITALS.get(cmd.get("nation"), 600000)
                _nb = [q for q in (_pl * 100000 + x for x in PORTAL_LINKS.get(_here, ()))
                       if not province_owner(q) or same_side(province_owner(q), me)]
                if _nb:
                    tgt = min(_nb, key=lambda q: len(_route(_cap, q) or ()) or 99)
                    g = next((g for g in GATE_SPOTS.get(tgt % 100000, ()) if g[0] == _here), None)
                    dest = (g[1], g[2]) if g else None
            except Exception as e:
                log(f"   fall-back target error: {e!r}")
        if tgt and tgt != prov and (not province_owner(tgt) or same_side(province_owner(tgt), me)):
            dx, dy = dest if dest else (0x200, 0x200)
            log(f"   battle over ({'victory' if won else 'defeat'}) -> {prov} belongs to nation {province_owner(prov)}, leaves for {tgt}")
            leave_map(s, "battle over")
            enter_field(s, tgt, dx, dy, capital=(tgt in CAPITALS.values()))
            return
    log(f"   battle over ({'victory' if won else 'defeat'}) -> back to capital")
    enter_field(s, CAPITALS.get(cmd["nation"], 200000000), 0x200, 0x200, capital=True)

HERO_UID = 1   # legacy default; every account now has its own hero uid (hero_uid(), unique on shared maps)

# ---- walking speed on town maps (user 2026-10-22 14:39: too fast, the fast walk becomes a paid feature) ------------------
TOWN_SPEED_SLOW = 50          # PUT_UNIT speed x10 of free accounts (the old speed for everybody was 100)
TOWN_SPEED_FAST = 100         # paid accounts / active speed boost
SPEED_BOOST_URA = 20          # PLACEHOLDER price of /speed (3 hours of fast walking)
SPEED_BOOST_HOURS = 3

def town_speed(a):
    if a and (a.get("paid") or a.get("speed_boost_until", 0) > time.time()):
        return TOWN_SPEED_FAST
    return TOWN_SPEED_SLOW

def hero_uid(acc):
    """Stable per-account commander unit id (2..999; unit ids are >= 1001, aliens 50001+/60001+)."""
    accs = load_accounts()
    a = accs.get(acc)
    if a is None:
        return 1
    if not a.get("hero_uid"):
        used = {x.get("hero_uid") for x in accs.values() if isinstance(x, dict)}
        a["hero_uid"] = next(i for i in range(2, 1000) if i not in used)
        accs[acc] = a
        save_accounts(accs)
    return a["hero_uid"]

def ensure_unique_unit_ids():
    """Unit ids must be unique across ALL accounts once players share a map (PUT/0x19/lumps use them)."""
    accs = load_accounts()
    seen, changed = set(), 0
    top = max([u["uid"] for a in accs.values() if isinstance(a, dict) for u in a.get("units", [])] + [1000])
    for name in sorted(accs):
        a = accs[name]
        if not isinstance(a, dict):
            continue
        for u in a.get("units", []):
            if u["uid"] in seen:
                top += 1
                u["uid"] = top
                changed += 1
            seen.add(u["uid"])
        a["next_uid"] = max(a.get("next_uid", 1001), top + 1)
    # hero (commander) uids must be unique too: two accounts with the same hero uid control each other's hero
    used_h = set()
    for name in sorted(accs):
        a = accs[name]
        if not isinstance(a, dict) or not a.get("hero_uid"):
            continue
        if a["hero_uid"] in used_h:
            a["hero_uid"] = next(i for i in range(2, 1000) if i not in used_h
                                 and i not in {x.get("hero_uid") for x in accs.values() if isinstance(x, dict)})
            changed += 1
            log(f"   hero uid of {name} was shared -> {a['hero_uid']}")
        used_h.add(a["hero_uid"])
    if changed:
        save_accounts(accs)
    log(f"unit ids: {len(seen)} unit(s), {changed} renumbered to be globally unique")

def new_unit_uid(accs):
    """next free unit id over ALL accounts (unit ids are shared on maps), >= 1001."""
    top = max([u["uid"] for x in accs.values() if isinstance(x, dict) for u in x.get("units", [])]
              + [x.get("next_uid", 1001) - 1 for x in accs.values() if isinstance(x, dict)] + [1000])
    return top + 1


def retreat_target(s):
    """user 2026-10-23 13:17: a retreat with units still alive goes to a NEIGHBOURING province (the one the commander came
    from, else an own / allied neighbour nearest to the capital, else any neighbour).  If that province was cut off (an
    enemy holds it, a blockade, aliens) the commander has to fight his way in again: enter_field opens a battle there.
    Only a squad that was wiped out flies back to the capital (end_battle).  -> (target map, arrival point at the gate
    that faces the battle province)."""
    cmd = getattr(s, "cmd", {"nation": 1})
    cap = CAPITALS.get(cmd.get("nation"), 600000)
    m = getattr(s, "map", None) or 0
    if not (0 < m < 100000000) or map_kind(m) != "province":
        return (getattr(s, "came_from", None) or -1), None
    pl, here = m // 100000, province_of(m) % 100000
    nb = [pl * 100000 + q for q in PORTAL_LINKS.get(here, ())]
    cf = getattr(s, "came_from", None)
    if cf in nb:
        tgt = cf
    elif nb:
        me = side_nation(s)
        def key(q):
            path = _route(cap, q) if cap is not None else None
            return (0 if same_side(province_owner(q), me) else 1, len(path) if path else 99)
        tgt = min(nb, key=key)
    else:
        return cap, None
    g = next((g for g in GATE_SPOTS.get(tgt % 100000, ()) if g[0] == here), None)
    return tgt, ((g[1], g[2]) if g else None)

def capital_fallback(s, prov):
    """user 2026-10-25 13:51: the neighbour of province prov that lies nearest to the capital (own / allied / unowned land
    only, never enemy land) and the gate that faces prov.  -> (province, arrival point) or (None, None)."""
    try:
        me = side_nation(s)
        cap = CAPITALS.get(getattr(s, "cmd", {}).get("nation"), 600000)
        pl, here = prov // 100000, province_of(prov) % 100000
        if prov == cap:
            return None, None
        nb = [q for q in (pl * 100000 + x for x in PORTAL_LINKS.get(here, ()))
              if not province_owner(q) or same_side(province_owner(q), me)]
        if not nb:
            return None, None
        def dist_cap(q):
            if q == cap:
                return 0
            path = _route(cap, q)
            return len(path) if path else 99
        tgt = min(nb, key=dist_cap)
        if dist_cap(tgt) >= 99 and cap != tgt:
            return None, None
        g = next((g for g in GATE_SPOTS.get(tgt % 100000, ()) if g[0] == here), None)
        return tgt, ((g[1], g[2]) if g else None)
    except Exception as e:
        log(f"   capital_fallback error: {e!r}")
        return None, None

GATE_ASSIST_R = 230          # px: a unit this close to a gate it was sent to ...
GATE_ASSIST_STILL = 3.0      # ... that has stood still this long (stuck in a crowd / on a rock) leaves through it
GATE_ASSIST_REPEAT = 12.0
GATE_ASK_REPEAT = 20.0      # s between two 'confirm the retreat' notices for the same unit
GATE_DWELL = 8.0            # s a unit that was asked stays at the gate -> counts as 'yes'
GATE_ASK_VALID = 90.0       # s a unit at a gate stays eligible for /retreat
# user 2026-10-25 15:49 / 16:03 + client RE (004d17c0): a unit that reaches an exit portal makes the CLIENT open its own
# confirm box (dialog type 5, 00402eb0, text ksRetreat); only OK (00403130 -> unit 004da400 -> 004e1990) sends 0x2f, and
# only for THAT unit.  The box is skipped only after the RETREAT button (004a5270 sets main+0x29bf4 = everybody walks
# out), which is the "retreat all, no question" of the user.  So 0x2f is already confirmed: the server retreats the unit
# at once.  The server-side gate_assist (retreat units stuck NEAR a gate) would bypass the player's OK: off.
GATE_CLIENT_CONFIRMS = True
GATE_ASSIST_ON = False

def gate_assist(s, uid, pos):
    """user 2026-10-25 00:35: units ordered to an exit gate get stuck next to it (crowd, edge of the platform) and never
    reach the portal cell, so the client never sends 0x2f.  The periodic position report (0x18) tells the server: a unit
    that was sent to a gate (last move order within GATE_ASSIST_R of it), is within GATE_ASSIST_R of it and has not moved
    for GATE_ASSIST_STILL s retreats through that gate exactly as if it had arrived."""
    if not GATE_ASSIST_ON:
        return
    m = getattr(s, "map", None) or 0
    if not (0 < m < 100000000) or map_kind(m) != "province" or not getattr(s, "battle", None):
        return
    if uid not in getattr(s, "alive_units", set()) or getattr(s, "spectator", False):
        return
    now = time.time()
    # user 2026-10-25 15:46: the OK of the client's message box does not reach the server, so a unit that was asked
    # (retreat() -> gate_pending) and keeps standing at that gate for GATE_DWELL s without a new move order retreats;
    # a new order that takes it away cancels the question.
    gp = getattr(s, "gate_pending", None) or {}
    pend = gp.get(uid)
    if pend:
        _t_first = pend[3] or pend[2]
        md0 = (getattr(s, "move_dest", {}) or {}).get(uid)
        here0 = province_of(m) % 100000
        near = any(AL.dist(pos, (gx, gy)) <= GATE_ASSIST_R for to, gx, gy in GATE_SPOTS.get(here0, ()))
        if md0 and md0[1] > _t_first + 1 and not any(AL.dist(md0[0], (gx, gy)) <= GATE_ASSIST_R
                                                   for to, gx, gy in GATE_SPOTS.get(here0, ())):
            gp.pop(uid, None)                              # ordered away from the gate: no retreat
            log(f"   GATE ASK: unit {uid} was ordered away from the gate - cancelled")
        elif near and now - _t_first >= GATE_DWELL:
            gp.pop(uid, None)
            log(f"   GATE DWELL: unit {uid} of {getattr(s, 'acc', '?')} stayed {now - _t_first:.0f} s at the gate - retreats")
            retreat(s, uid, pend[0], pend[1], confirmed=True)
            return
    ga = s.__dict__.setdefault("gate_still", {})
    old = ga.get(uid)
    if old is None or AL.dist(old[0], pos) > 24:
        ga[uid] = (pos, now, old[2] if old else 0)
        return
    if now - old[1] < GATE_ASSIST_STILL or now - old[2] < GATE_ASSIST_REPEAT:
        return
    md = (getattr(s, "move_dest", {}) or {}).get(uid)
    here = province_of(m) % 100000
    best = None
    for to, gx, gy in GATE_SPOTS.get(here, ()):
        d = AL.dist(pos, (gx, gy))
        if d <= GATE_ASSIST_R and md and AL.dist(md[0], (gx, gy)) <= GATE_ASSIST_R and (best is None or d < best[0]):
            best = (d, to, gx, gy)
    if best is None:
        return
    ga[uid] = (pos, old[1], now)
    pl = m // 100000
    target = pl * 100000 + best[1]
    g = next((g for g in GATE_SPOTS.get(best[1], ()) if g[0] == here), None)
    log(f"   GATE ASSIST: unit {uid} of {getattr(s, 'acc', '?')} stuck {best[0]:.0f} px from the gate to {target} "
        f"for {now - old[1]:.0f} s - retreats through it")
    retreat(s, uid, target, (g[1], g[2]) if g else None)

def retreat(s, uid, target, dest=None, confirmed=True):
    """client 0x2f (FUN_004e1990, sent when a unit reaches an EXIT PORTAL of a battle map):
    u32 unit id, u16, u32 (0 = retreat), u32 TARGET map (neighbouring province / -1), u16 x, u16 y, u16, u16.
    Without an answer the client says 'Too much time has passed since X reached an exit portal' (ksRetreatTimeOut).
    Design (user, 2026-10-20): every unit that reaches the exit portal retreats ON ITS OWN (removed from the battle
    map with server 0x19 [u32 uid][u32 0], client 004a5ee0 -> 004dcbf0 plain remove), keeping its HP.  When the
    COMMANDER reaches the portal, or the last unit has left, the commander leaves the battle for the target map.
    A retreat is neither a win nor a loss and captures nothing."""
    cmd = getattr(s, "cmd", {"nation": 1})
    cap = CAPITALS.get(cmd.get("nation"), 600000)
    if not (0 < target < 100000000) or province_of(target) not in planet_provinces((target // 100000) % 1000):
        target = cap
    alive = getattr(s, "alive_units", set())
    # user 2026-10-24 12:34: the client also sends 0x2f about 5 s after a unit DIED (004e3c70 -> 004e1990, log 12:04:25
    # unit 1018 destroyed, 12:04:30 "retreat" of 1018).  That is no retreat: when it was the last unit the old code took
    # it for the commander leaving the battle (while the reinforce box was open).  A unit that died in this battle and
    # is not alive again is ignored.
    if uid in getattr(s, "lost_units", set()) and uid not in alive:
        log(f"   0x2f for dead unit {uid} from {getattr(s, 'acc', '?')} (sent after its death) - not a retreat, ignored")
        return
    log(f"   retreat request {getattr(s, 'acc', '?')}: unit {uid} (hero {getattr(s, 'hero_uid', HERO_UID)}) -> {target}, "
        f"{len(alive)} alive, battle {bool(getattr(s, 'battle', None))}")
    # (user 2026-10-24 20:13) no retreat through a gate that leads into an ENEMY province: only gates to a province of
    # one's own side (or a neutral one) are a way out.  If every neighbour is enemy land the commander may still leave
    # (to his capital).  The unit stays on the field; the player gets a notice.
    try:
        _m = getattr(s, "map", None) or 0
        _own = province_owner(target) if 0 < target < 100000000 else 0
        if (0 < _m < 100000000 and map_kind(_m) == "province" and _own and not same_side(_own, side_nation(s))
                and getattr(s, "battle", None)):
            _pl, _here = _m // 100000, province_of(_m) % 100000
            _nb = [_pl * 100000 + q for q in PORTAL_LINKS.get(_here, ())]
            if any(not province_owner(q) or same_side(province_owner(q), side_nation(s)) for q in _nb):
                log(f"   RETREAT refused: unit {uid} of {getattr(s, 'acc', '?')} at the gate to enemy province {target} "
                    f"(nation {_own})")
                _say_lang(s, "这个星门通往敌国省份，不能从这里撤退。请走到通往己方、同盟或中立省份的星门。",
                          "這個星門通往敵國省份，不能從這裡撤退。請走到通往己方、同盟或中立省份的星門。",
                          "This gate leads into an enemy province - you cannot retreat through it. Use a gate to a "
                          "province of your side, an ally or a neutral one.")
                return
            target, dest = cap, None                      # surrounded by enemy land: back to the capital
    except Exception as e:
        log(f"   retreat gate check error: {e!r}")
    # user 2026-10-25 14:35: in a battle, walking onto a gate is NOT a retreat.  The player is asked in a chat message and
    # must confirm with /撤退 (/retreat), or use the retreat button / Ctrl+F11 (confirmed=True) to leave.
    try:
        _m2 = getattr(s, "map", None) or 0
        if (not confirmed and getattr(s, "battle", None) and not getattr(s, "spectator", False)
                and 0 < _m2 < 100000000 and map_kind(_m2) == "province" and (uid in alive or not alive)):
            gp = s.__dict__.setdefault("gate_pending", {})
            now2 = time.time()
            old2 = gp.get(uid)
            gp[uid] = (target, dest, now2, old2[3] if old2 else 0)
            if not old2 or now2 - old2[3] > GATE_ASK_REPEAT:
                gp[uid] = (target, dest, now2, now2)
                log(f"   GATE ASK: unit {uid} of {getattr(s, 'acc', '?')} stands at the gate to {target} - waiting for /retreat")
                _say_lang(s, "单位到达了星门，但战斗中不会自动撤退。站在星门上不动 8 秒（或输入 /撤退）就会撤退，把单位移开则取消；按撤退键/Ctrl+F11 可整队撤退。",
                          "單位到達了星門，但戰鬥中不會自動撤退。站在星門上不動 8 秒（或輸入 /撤退）就會撤退，把單位移開則取消；按撤退鍵/Ctrl+F11 可整隊撤退。",
                          "A unit reached the gate. It retreats if it stands there for 8 s (or type /retreat); move it away to "
                          "cancel. Retreat button / Ctrl+F11 = whole division.")
            return
    except Exception as e:
        log(f"   gate ask error: {e!r}")
    if uid != getattr(s, "hero_uid", HERO_UID):
        if uid not in alive:
            if not alive and getattr(s, "battle", None):
                uid = getattr(s, "hero_uid", HERO_UID)     # nothing left on the field: the commander leaves
            else:
                return
        alive.discard(uid)
        stop_attack(s, uid)
        SHIELDS.pop(uid, None)
        CLOAKED.pop(uid, None)
        release_passengers(s, uid)          # a carrier leaving through the portal drops its passenger (client too)
        hp_store(s, [uid])
        s.send(bytes([0x19]) + struct.pack(">II", uid, 0))
        for o in map_peers(s):
            o.send(bytes([0x19]) + struct.pack(">II", uid, 0))
        log(f"   RETREAT: unit {uid} left the battle through the exit portal, {len(alive)} unit(s) still fighting")
        if alive:
            return
        if getattr(s, "battle", None) and not getattr(s, "spectator", False):
            squad_lost(s, "retreated")       # choose a new division and re-enter, or retreat (client 0x54)
            return
    import time as _rt
    if getattr(s, "retreating", False) and _rt.time() - getattr(s, "retreat_t", 0) < RESULT_SHOW_SECONDS + 15:
        log(f"   RETREAT of {getattr(s, 'acc', '?')} ignored: already leaving")
        return
    s.retreating, s.retreat_t = True, _rt.time()     # (2026-10-23 16:10: a stuck flag blocked every later retreat)
    for t in list(getattr(s, "attacks", {}).values()):
        t.cancel()
    s.attacks = {}
    hp_store(s, list(alive))
    s.unit_hp = {}
    log(f"   RETREAT: commander leaves {getattr(s, 'map', None)} for {target} "
        f"({'commander at the portal' if uid == getattr(s, 'hero_uid', HERO_UID) else 'all units retreated'})")
    in_battle = bool(getattr(s, "battle", None) or getattr(s, "battle_kind", ""))
    s.battle_kind = ""
    # (2026-10-25 audit H) the commander is out NOW, not after the result window: his units leave every client, stop
    # holding POCs / being targets, and the battle judges without him (attackers gone, POCs held, time up)
    _b = getattr(s, "battle", None)
    if _b is not None and not getattr(s, "spectator", False):
        for _u in list(alive):
            _pk = bytes([0x19]) + struct.pack(">II", _u, 0)
            for _o in map_peers(s):
                _o.send(_pk)
        alive.clear()
        if s in _b.get("members", ()) and len(_b["members"]) > 1:
            _b["members"].discard(s)
            if BATTLES.get(_b.get("map")) is _b and not _b.get("won"):
                if _b.get("owner") is s:
                    set_battle_owner(_b, battle_best_commander(_b, exclude=s), f"commander {s.acc} retreats")
                try:
                    battle_ctx_handoff(s, _b)
                except Exception as e:
                    log(f"   battle context hand-off error: {e!r}")
                check_attackers_gone(_b)
    # 0x2f carries the arrival point in the target map (portal record cells * 32 + 16, 004d17c0)
    dx, dy = dest if dest and dest[0] and dest[1] else (0x200, 0x200)
    dx, dy = min(max(dx, 0x40), 0xFC0), min(max(dy, 0x40), 0xFC0)     # keep inside a 128 x 128 tile map
    ret = getattr(s, "return_to", None)
    if ret and ((getattr(s, "map", 0) or 0) >= 100000000 or map_kind(getattr(s, "map", 0) or 0) == "hunt"):
        # leaving a CAVE through its exit: back to the province cave entrance the commander came from
        (target, (dx, dy), _rc) = ret
        s.return_to = None
    if not in_battle:
        enter_field(s, target, dx, dy, capital=(target in CAPITALS.values()))
        s.retreating = False
        return
    # 2026-10-21 23:35 (user): retreat / victory / annihilation all get the result window -> RETREAT (frame 2),
    # shown RESULT_SHOW_SECONDS, then the commander leaves.  A retreat is neither a win nor a loss.
    try:                    # (user 2026-10-24 21:57) the damage XP was only paid at victory / defeat, not on retreat
        pay_damage_xp(s)
    except Exception as e:
        log(f"   damage XP error: {e!r}")
    try:
        units_battle_end(s, False)                     # (10-31 14:36) a retreat counts as a battle fought
    except Exception as e:
        log(f"   units_battle_end error: {e!r}")
    battle_report(s, 2)
    try:
        s.send(build_battle_result(s, False, [0] * 5, result=2))
        log("   battle result window (0x25, RETREAT) sent")
        xp_summary(s, retreat=True)
    except Exception as e:
        log(f"   retreat result window failed: {e!r}")
    gen = getattr(s, "battle_gen", None)

    async def _leave():
        await asyncio.sleep(RESULT_SHOW_SECONDS)
        if s.w.is_closing():
            return
        try:
            enter_field(s, target, dx, dy, capital=(target in CAPITALS.values()))
        except Exception as e:
            log(f"   RETREAT to {target} failed: {e!r} - back to the capital")
            try:
                enter_field(s, cap, 0x200, 0x200, capital=True)
            except Exception as e2:
                log(f"   RETREAT to the capital failed too: {e2!r}")
        finally:
            s.retreating = False
    spawn(_leave())


def confirm_gate_retreat(s):
    """chat command /撤退 /retreat: the units that stood at a gate (retreat() asked) leave through it now."""
    gp = getattr(s, "gate_pending", None) or {}
    now = time.time()
    todo = [(uid, v) for uid, v in gp.items() if now - v[2] <= GATE_ASK_VALID
            and (uid in getattr(s, "alive_units", set()) or not getattr(s, "alive_units", None))]
    s.gate_pending = {}
    if not getattr(s, "battle", None) or not todo:
        return _say_lang(s, "现在没有站在星门上的单位。先把要撤退的单位移到星门。",
                         "現在沒有站在星門上的單位。先把要撤退的單位移到星門。",
                         "No unit is standing at a gate. Move the unit to a gate first.")
    for uid, (target, dest, _t, _a) in todo:
        log(f"   GATE CONFIRM: unit {uid} of {getattr(s, 'acc', '?')} retreats through the gate to {target}")
        retreat(s, uid, target, dest, confirmed=True)
