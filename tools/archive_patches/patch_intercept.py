"""NPC interception of reinforcements (user 2026-10-22: "看到對方在增援還會主動去找增援路線截斷", answers 1.B 2.B).
Applied to server/sgserver.py once (idempotent check on the marker)."""
import sys, re
P = sys.argv[1] if len(sys.argv) > 1 else "server/sgserver.py"
src = open(P, encoding="utf-8").read()
if "def npc_intercept_scan" in src:
    print("already patched"); sys.exit(0)

def rep(old, new, cnt=1):
    global src
    n = src.count(old)
    assert n == cnt, (n, old[:80])
    src = src.replace(old, new)

# 1. defence counts only support squads that ARRIVED
rep('''    sup = [n for n in npc_of(owner) if n["task"] and n["task"].get("kind") == "support" and n["task"].get("target") == pid]
    p = 40.0''', '''    sup = [n for n in npc_of(owner) if n["task"] and n["task"].get("kind") == "support" and n["task"].get("target") == pid
           and n["task"].get("phase", "support") == "support"]     # marching / ambushed squads do not defend yet
    p = 40.0''')

# 2. support squads march (route province = last one before the target)
rep('''        n = random.choice(idle)
        n["task"] = {"kind": "support", "target": pid, "since": now, "phase": "support"}
        log(f"   NPC: {n['name']} (nation {owner}) sorties to help {pid} (attacked by NPCs)")''',
'''        n = random.choice(idle)
        n["task"] = npc_reinf_task("support", owner, pid, now)
        log(f"   NPC: {n['name']} (nation {owner}) sorties to help {pid} (attacked by NPCs, via {n['task'].get('route')}, "
            f"arrives in {n['task']['arrive'] - now:.0f}s)")''')

# 3. NPC reinforcements of a player battle march in first (they can be intercepted on the way)
rep('''        first = not B.get("npc_side")
        n["task"] = {"kind": "defend", "target": mid, "phase": "battle", "since": now}
        B["npc_side"] = dfd
        homes = [(pocs[B.get("reinf", 0) % len(pocs)][1], pocs[B.get("reinf", 0) % len(pocs)][2])]
        npc_spawn(own, mid, dfd, [n], 6 + int(round(4 * cl)), homes, "hold", 0, 0, False, pocs, hp_mult=1.0 + 0.5 * cl)
        NPC_RT.setdefault(n["id"], {"dead": 0, "units": 0})["B"] = B
        B.setdefault("npc_ids", []).append(n["id"])
        B["reinf"] = B.get("reinf", 0) + 1
        if first:
            asyncio.get_event_loop().create_task(npc_ai(own, (getattr(own, "battle_gen", 0) or 0) + 1))
        log(f"   NPC: {n['name']} (nation {dfd}) reinforces the defence of {mid}")
        npc_dirty()''',
'''        n["task"] = npc_reinf_task("defend", dfd, mid, now)
        n["task"]["arrive"] = now + (n["task"]["arrive"] - now) * (1.0 - 0.5 * cl)      # near the capital: faster
        n["task"]["slot"] = B.get("reinf", 0)
        B["reinf"] = B.get("reinf", 0) + 1
        log(f"   NPC: {n['name']} (nation {dfd}) marches to reinforce the defence of {mid} (via {n['task'].get('route')}, "
            f"arrives in {n['task']['arrive'] - now:.0f}s)")
        npc_dirty()

def npc_reinforce_enter(n, now):
    """a marching NPC reinforcement reaches the battle: its squad enters the map at a POC of its nation."""
    t = n["task"]
    mid, dfd = t["target"], n["nation"]
    B = BATTLES.get(mid)
    own = B.get("owner") if B else None
    pocs = [(pid, p["x"], p["y"], p["strength"], POC_TYPE, p["owner"]) for pid, p in B["pocs"].items()] if B else []
    if B is None or B.get("won") or own is None or own.w.is_closing() or not pocs:
        npc_release(n, now, random.uniform(60, 300))
        log(f"   NPC: {n['name']} arrived at {mid} - the battle is over, goes home")
        return
    cl = npc_closeness(mid)
    first = not B.get("npc_side")
    t.update(phase="battle", since=now, entered=now)
    B["npc_side"] = dfd
    k = t.get("slot", 0)
    homes = [(pocs[k % len(pocs)][1], pocs[k % len(pocs)][2])]
    npc_spawn(own, mid, dfd, [n], 6 + int(round(4 * cl)), homes, "hold", 0, 0, False, pocs, hp_mult=1.0 + 0.5 * cl)
    NPC_RT.setdefault(n["id"], {"dead": 0, "units": 0})["B"] = B
    B.setdefault("npc_ids", []).append(n["id"])
    if first:
        asyncio.get_event_loop().create_task(npc_ai(own, (getattr(own, "battle_gen", 0) or 0) + 1))
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
NPC_AMBUSH_WAIT = 240          # s: a blockade waits this long for the player it was set up for
NPC_REINF_PACE = 0.75          # reinforcements march faster than an assault (march time x this)
NPC_INTERCEPT_PACE = 0.5       # interceptors are light, fast squads (march time x this)
NPC_AMBUSH_DEF = 1.25          # an ambushed squad fights back in formation (its power x this in the abstract ambush)
AMBUSH = {}                    # province -> {"R", "o", "o_ids", "d", "d_ids", "P", "acc", "B", "until"}   (runtime)
INTERCEPT_SEEN = {}            # (account, target province) -> time

def _route(a, b):
    """shortest portal path a -> b (full province ids, both ends included) on one planet, None if none."""
    if a is None or b is None or a // 100000 != b // 100000:
        return None
    base, s0, g = a // 100000 * 100000, a % 100000, b % 100000
    prev, q = {s0: None}, [s0]
    while q:
        x = q.pop(0)
        if x == g:
            break
        for y in PORTAL_LINKS.get(x, ()):
            if y not in prev:
                prev[y] = x
                q.append(y)
    if g not in prev:
        return None
    p, x = [], g
    while x is not None:
        p.append(base + x)
        x = prev[x]
    return p[::-1]

def npc_reinf_task(kind, nid, pid, now):
    """task of a reinforcement that marches from the capital to pid; route = the last province before pid."""
    cap = CAPITALS.get(nid)
    path = _route(cap, pid) if cap is not None else None
    route = path[-2] if path and len(path) >= 3 else None
    steps = min(2, len(path) - 1) if path else 1
    t = NP.march_seconds(max(1, steps)) * NPC_REINF_PACE
    return {"kind": kind, "target": pid, "since": now, "phase": "march", "depart": now, "arrive": now + t,
            "route": route, "origin": route or cap}

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
    for o in list(ONLINE):
        if getattr(o, "logged_in", False) and not o.w.is_closing() and same_side(side_nation(o), nid):
            try:
                _say_lang(o, zh_cn, zh_tw, en, rgb)
            except Exception:
                pass

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
        if not t or t.get("kind") not in ("support", "defend") or t.get("phase") != "march" or not t.get("route") \\
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
        if not mv or now - mv[2] > 120 or not getattr(o, "logged_in", False) or getattr(o, "battle", None) \\
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
    best = None                             # from the nearest province of O
    for p, ow in world_state()["owners"].items():
        p = int(p)
        if int(ow) != O or p // 100000 != R // 100000:
            continue
        path = _route(p, R)
        if path and (best is None or len(path) < len(best)):
            best = path
    if best is None:
        return False
    d = len(best) - 1
    if m.get("acc"):
        if d > 1:
            return False                    # players walk fast: only a nation right next to the road blocks it
        arrive = now + random.uniform(15, 40)
    else:
        if d > 3:
            return False
        arrive = now + NP.march_seconds(max(1, d)) * NPC_INTERCEPT_PACE
        if arrive > m["eta"] - 5:
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
    for n in team:
        n["task"] = {"kind": "intercept", "target": R, "origin": origin, "depart": now, "arrive": arrive,
                     "phase": "march", "since": now, "group": gid, "vs": N, "P": m["P"],
                     "ref": [m["npc"]["id"]] if m.get("npc") else [], "acc": m.get("acc"), "wait": 0}
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
            if mt and mt.get("kind") in ("support", "defend") and mt.get("phase") == "march" and mt.get("route") == R \\
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
        homes = [(x + 0x50 * (j + 1), y + 0x40 * (j % 2)) for j in range(len(ns))] if ally else \\
            spawn_homes(mapname, (x, y), len(ns), avoid=500)
        per = max(2, budget // max(1, len(ns)))
        for n, home in zip(ns, homes):
            units = npc_battle_units(n, per, nid)
            if not units:
                continue
            NPC_RT[n["id"]] = {"B": None, "dead": 0, "units": len(units), "used": set(), "waves": 0, "wave_t": 0,
                               "per": per, "home": home, "poc": None, "mode": "assault", "nid": nid, "hp_mult": 1.0,
                               "ally": ally}
            npc_put_units(s, nid, n, units, home, "assault", None, 1.0, ally)
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
    return True''')

# 4. tick: support / defend marches, interceptions
rep('''        elif t.get("kind") == "defend":
            npc_defend_step(n, now)
        elif t.get("kind") == "support":
            pid = t["target"]
            if now''', '''        elif t.get("kind") == "intercept":
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
        elif t.get("kind") == "support":
            pid = t["target"]
            if t.get("phase") == "march" and now >= t.get("arrive", 0):
                t.update(phase="support", entered=now)
                log(f"   NPC: {n['name']} arrived to support {pid}")
            if now''')
rep('''    forces = {}
    for n in npc_all():
        t = n["task"]''', '''    forces, icpt = {}, {}
    for n in npc_all():
        t = n["task"]''')
rep('''    for ns in forces.values():
        if ns[0]["task"]:
            npc_force_step(ns, now)''', '''    for ns in forces.values():
        if ns[0]["task"]:
            npc_force_step(ns, now)
    for ns in icpt.values():
        if ns[0]["task"]:
            npc_intercept_step(ns, now)''')
rep('''            npc_react(time.time())
''', '''            npc_react(time.time())
            npc_intercept_scan(time.time())
''')

# 5. strategic-map presence of the new tasks
rep('''    if t and t.get("kind") in ("attack", "defend"):
        if t.get("phase") == "march":''', '''    if t and t.get("kind") in ("attack", "defend", "intercept", "support"):
        if t.get("phase") in ("march", "ambushed"):''')
rep('''    if tk.get("kind") in ("attack", "defend") and tk.get("phase") == "march":''',
    '''    if tk.get("kind") in ("attack", "defend", "intercept", "support") and tk.get("phase") == "march":''')
rep('''    if tk.get("kind") in ("attack", "defend") and tk.get("phase") in ("siege", "raid", "battle") and tk.get("origin"):''',
    '''    if tk.get("kind") in ("attack", "defend", "intercept", "support") and tk.get("phase") in ("siege", "raid", "battle", "ambush", "support") \\
            and tk.get("origin"):''')

# 6. defenders of a province: not the marching / ambushed / blocking commanders
rep('''            and not (n["task"] and n["task"].get("kind") in ("defend", "attack") and n["task"].get("phase") != "march")]''',
    '''            and not (n["task"] and (n["task"].get("kind") in ("defend", "intercept") or n["task"].get("phase") == "ambushed"
                                    or n["task"].get("kind") == "attack" and n["task"].get("phase") != "march"))]''')

# 7. battle entry: a blockade makes the province a battle field; spawn the NPC squads of both sides
rep('''                                                   and mapid not in RAIDS)        # raided: defend it (battle)''',
    '''                                                   and mapid not in RAIDS        # raided: defend it (battle)
                                                   and mapid not in AMBUSH)      # blockade on the road (battle)''')
rep('''        s.battle_kind = kind
''', '''        if not joining and not sim and not watch and kind == "province" and mapid in AMBUSH:
            try:
                if npc_spawn_ambush(s, mapid, x, y, pocs, len(units)):
                    asyncio.get_event_loop().create_task(npc_ai(s, (getattr(s, "battle_gen", 0) or 0) + 1))
            except Exception as e:
                log(f"   ambush spawn error: {e!r}")
        s.battle_kind = kind
''')
rep('''    prev = getattr(s, "cur_province", None)
    s.cur_province = mapid if mapid < 100000000 else None''', '''    prev = getattr(s, "cur_province", None)
    s.cur_province = mapid if mapid < 100000000 else None
    if prev and s.cur_province and province_of(prev) != province_of(mapid) and map_kind(mapid) == "province":
        s.moved = (province_of(prev), province_of(mapid), __import__("time").time())   # NPC interception watch''')

# 8. battle start links the ambush
rep('''def npc_battle_started(s, B):
    meta = getattr(s, "alien_meta", None) or {}''', '''def npc_battle_started(s, B):
    am = getattr(s, "ambush_meta", None)
    if am:
        s.ambush_meta = None
        A = AMBUSH.get(am["R"])
        if A is not None:
            A["B"] = B
        B["ambush"] = am["R"]
        for i in am["ids"]:
            NPC_RT.setdefault(i, {"dead": 0, "units": 0})["B"] = B
    meta = getattr(s, "alien_meta", None) or {}''')

# 9. ambush battle in the own province: over when every blocker is dead
rep('''    if not s.targets and meta and meta.get("raid"):''', '''    if b and b.get("ambush") and not b.get("won"):
        check_attackers_gone(b)               # blockade in an own province: the defenders win when no blocker is left
        if b.get("won"):
            return
    if not s.targets and meta and meta.get("raid"):''')

# 10. npc_ai: every NPC unit picks its enemies by ITS nation (two NPC nations on one map)
rep('''            nat = meta.get("npc_nation")
            tier = meta.get("tier", 1)
            members = [o for o in b["members"] if not o.w.is_closing()] if b is not None else battle_members(s)
            pos, hp = {}, {}
            for o in members:
                if getattr(o, "spectator", False) or same_side(side_nation(o), nat):
                    continue
                for u in getattr(o, "alive_units", set()):
                    pos[u] = o.unit_pos.get(u, (0, 0))
                    hp[u] = getattr(o, "unit_hp", {}).get(u, 9999)
            if meta.get("npc_ally"):                    # allied NPCs: the enemies are the province's aliens
                for _tid, _tg in s.targets.items():
                    if _tg.get("npc") is None and _tg.get("hp", 0) > 0 and _tg.get("pos"):
                        pos[_tid] = _tg["pos"]; hp[_tid] = _tg["hp"]
            pocs = b["pocs"] if b is not None else s.pocs
            enemy_pocs = {pid: p for pid, p in pocs.items() if not same_side(nat, p["owner"])}''',
'''            tier = meta.get("tier") or PLANET_TIER.get((mapid // 100000) % 1000, 1) if mapid and mapid < 100000000 else meta.get("tier", 1)
            members = [o for o in b["members"] if not o.w.is_closing()] if b is not None else battle_members(s)
            _pl = []
            for o in members:
                if getattr(o, "spectator", False):
                    continue
                _sn = side_nation(o)
                for u in getattr(o, "alive_units", set()):
                    _pl.append((u, o.unit_pos.get(u, (0, 0)), getattr(o, "unit_hp", {}).get(u, 9999), _sn))
            _nt = [(tid, tg) for tid, tg in s.targets.items() if tg.get("hp", 0) > 0 and tg.get("pos")]
            _cache = {}
            def enemies_of(nat, ally):
                """(pos, hp) of everything an NPC unit of nation nat fights: other sides' players and NPC units,
                plus the aliens for NPCs allied to the players (user 2026-10-22: two NPC nations on one map)."""
                k = (nat, bool(ally))
                if k not in _cache:
                    ps, hs = {}, {}
                    for u, p, h, sn in _pl:
                        if not same_side(sn, nat):
                            ps[u], hs[u] = p, h
                    for tid, tg in _nt:
                        if tg.get("npc") is not None:
                            if not same_side(tg.get("nation"), nat):
                                ps[tid], hs[tid] = _npc_est_pos(tg, now), tg["hp"]
                        elif ally:
                            ps[tid], hs[tid] = tg["pos"], tg["hp"]
                    _cache[k] = (ps, hs)
                return _cache[k]
            pocs = b["pocs"] if b is not None else s.pocs''')
rep('''            for tid, tg in list(mine.items()):
                tg["pos"] = _npc_est_pos(tg, now) if tg.get("state", "idle") != "combat" else tg["pos"]''',
'''            for tid, tg in list(mine.items()):
                nat = tg.get("nation")
                pos, hp = enemies_of(nat, tg.get("ally"))
                enemy_pocs = {pid: p for pid, p in pocs.items() if not same_side(nat, p["owner"])}
                tg["pos"] = _npc_est_pos(tg, now) if tg.get("state", "idle") != "combat" else tg["pos"]''')
# engage() uses pos of the CURRENT unit (closure over the loop variable) - fine.  One npc_ai per session and battle:
rep('''    await asyncio.sleep(2.0)
    b, mapid = getattr(s, "battle", None), getattr(s, "map", None)
    def alive():
        if b is not None:
            return BATTLES.get(mapid) is b and not b.get("won")
        return getattr(s, "battle_gen", None) == gen and not s.w.is_closing()
    try:
        while alive():
            now = time.time()
            meta = getattr(s, "alien_meta", None) or {}
            if not meta.get("npc"):''', '''    if getattr(s, "_npc_ai_gen", None) == gen:
        return                                  # already running for this battle (siege + ambush on one map)
    s._npc_ai_gen = gen
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
            if not meta.get("npc"):''')

# 11. hunts never "capture" (also after a real battle)
rep('''    if t.get("hunt") and not battle:                      # a hunt never takes the province
        w = world_state()
        AL.set_garrison(w, pid, AL.garrison(w, pid) * (NPC_HUNT_GARRISON if won else 0.85))
        save_world(w)''', '''    if t.get("hunt"):                                     # a hunt never takes the province
        if not battle:
            w = world_state()
            AL.set_garrison(w, pid, AL.garrison(w, pid) * (NPC_HUNT_GARRISON if won else 0.85))
            save_world(w)''')

# 12. GM: /npc ambush [PID] [NATION] (blockade in a province for testing) and /npc ambushes (list)
rep('''    elif sub == "stand":
        st = npc_state()''', '''    elif sub == "ambushes":
        for R, A in AMBUSH.items():
            left = "BATTLE" if A.get("B") else "%.0fs left" % (A["until"] - now)
            say(f"{R}: nation {A['o']} {A['o_ids']} vs nation {A['d']} {A['d_ids'] or A.get('acc')}, {left}")
        if not AMBUSH:
            say("no blockade")
    elif sub == "ambush" and len(parts) > 2:
        R = int(parts[2])
        me = side_nation(s)
        O = int(parts[3]) if len(parts) > 3 else next((n_ for n_, _nm, _c in NATIONS if not same_side(n_, me)
                                                       and _npc_idle_of(n_, now)), None)
        team = _npc_idle_of(O, now)[:2] if O else []
        if not team or R in AMBUSH or R in BATTLES:
            say("no idle NPC of an enemy nation / the province is busy")
            return
        for n in team:
            n["task"] = {"kind": "intercept", "target": R, "origin": R, "depart": now, "arrive": now, "phase": "ambush",
                         "since": now, "entered": now, "group": None, "vs": me, "P": R, "ref": [], "acc": s.acc}
        AMBUSH[R] = {"R": R, "o": O, "o_ids": [n["id"] for n in team], "d": me, "d_ids": [], "P": R, "acc": s.acc,
                     "B": None, "t0": now, "until": now + 600}
        say(f"blockade of nation {O} ({', '.join(n['name'] for n in team)}) in {R} for 10 min - enter it")
    elif sub == "stand":
        st = npc_state()''')
rep('''    """/npc status | /npc go PID [N] | /npc stand [HOURS] | /npc fill | /npc clear | /npc reset"""''',
    '''    """/npc status | /npc go PID [N] | /npc stand [HOURS] | /npc fill | /npc clear | /npc reset |
    /npc ambush PID [NATION] (blockade for a test) | /npc ambushes"""''')

open(P, "w", encoding="utf-8").write(src)
print("patched")
