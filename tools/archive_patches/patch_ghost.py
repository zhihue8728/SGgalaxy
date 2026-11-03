"""GHOST BATTLES (user 2026-10-22 21:29 "全部NPC都保持真实战斗", answers: full server simulation, up to 30 min):
every NPC assault / hunt / NPC-vs-NPC ambush is a REAL battle in BATTLES from the moment the NPCs arrive.  While no player
is on the map a 'ghost' session stands in for the battle's creator and server/battlesim.py moves and fights the units once
per second; a player who enters JOINS that battle and sees every unit where it is with its HP; when the last player leaves
the server simulates on.  Applied once to server/sgserver.py (marker check)."""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else "server/sgserver.py"
src = open(P, encoding="utf-8").read()
def rep(old, new, cnt=1):
    global src
    if new in src:
        return                                  # already applied (the script can run again)
    n = src.count(old)
    assert n == cnt, (n, old[:90])
    src = src.replace(old, new)

rep('''import npc as NP
''', '''import npc as NP
import battlesim as BSIM
''')

# ---- 1. NPC assault arrives: open a real (ghost) battle instead of the abstract siege / raid window -------------------
rep('''    if owner and npc_humans(owner) > 0:
        RAIDS[pid] = {"nation": owner, "until": now + AL.RAID_DEFEND_SECONDS, "from": t.get("origin"), "npc": nid,
                      "force": [n["id"] for n in ns]}''', '''    if NPC_GHOST_BATTLES:
        if npc_open_battle(pid, ns, now):
            if owner and npc_humans(owner) > 0:
                _notify_side(owner, f"第 {nid} 国的 {', '.join(n['name'] for n in ns[:3])} 正在进攻 {province_label(pid)}！进入该省防守（战斗最长 30 分钟）。",
                             f"第 {nid} 國的 {', '.join(n['name'] for n in ns[:3])} 正在進攻 {province_label(pid)}！進入該省防守（戰鬥最長 30 分鐘）。",
                             f"Commanders of nation {nid} ({', '.join(n['name'] for n in ns[:3])}) are attacking "
                             f"{province_label(pid)}! Enter it to defend (the battle lasts up to 30 minutes).", (255, 120, 120))
        else:
            npc_finish(ns, None, now)
        return
    if owner and npc_humans(owner) > 0:
        RAIDS[pid] = {"nation": owner, "until": now + AL.RAID_DEFEND_SECONDS, "from": t.get("origin"), "npc": nid,
                      "force": [n["id"] for n in ns]}''')

# ---- 2. the ghost block -------------------------------------------------------------------------------------------------
if "def npc_open_battle" not in src: rep('''def npc_reinforce_enter(n, now):''', '''# ---- GHOST BATTLES -----------------------------------------------------------------------------------------------------
NPC_GHOST_BATTLES = True       # False = the old abstract sieges / raid windows
NPC_GHOST_DEPLOY = 12          # units one NPC brings onto the map at a time (its next squads follow like F7)
try:
    _WALK = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "walk_grids.json")))
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

def _npc_put_squad(s, nid, n, per, home, mode, poc=None, hp_mult=1.0):
    units = npc_battle_units(n, per, nid)
    if not units:
        return False
    NPC_RT[n["id"]] = {"B": s.battle, "dead": 0, "units": len(units), "used": set(), "waves": 0, "wave_t": 0, "per": per,
                       "home": home, "poc": poc, "mode": mode, "nid": nid, "hp_mult": hp_mult, "ally": False}
    npc_put_units(s, nid, n, units, home, mode, poc, hp_mult, False)
    return True

def npc_open_battle(pid, ns, now, ambush=None):
    """the NPCs ns arrive in province pid: a real battle starts there (BATTLES[pid], ghost creator).  Neutral: the alien
    garrison is on the map; owned: the owner's NPC defenders hold the POCs.  ambush = {"d": nation, "d_ns": [...]}: an
    NPC-vs-NPC ambush on the road (no POCs, the side that is wiped out loses)."""
    if pid in BATTLES:
        return False
    nid = ns[0]["nation"]
    owner = 0 if ambush else province_owner(pid)
    g = Ghost(pid, nid)
    tier, _dist, _cave, name = alien_context(g, pid)
    pocs = [] if ambush else province_pocs(pid)
    g.pocs = {p[0]: {"x": p[1], "y": p[2], "strength": p[3], "progress": p[3], "owner": p[5], "capturing": False} for p in pocs}
    x, y = sim_arrival(pid, g)
    spots = sorted((tuple(p) for p in SPAWN_SPOTS.get(name or "", [])), key=lambda p: (p[0] - x) ** 2 + (p[1] - y) ** 2) or [(x, y)]
    homes = [spots[i % min(len(spots), 4)] for i in range(len(ns))]
    budget = min(NPC_BATTLE_UNITS[1], NPC_GHOST_DEPLOY * len(ns))      # their next squads follow (F7-like waves)
    B = {"map": pid, "t0": g.t0, "targets": g.targets, "pocs": g.pocs, "members": set(), "owner": g, "ghost": g,
         "hive_marks": [], "won": False, "defender": owner, "sim": False, "npc_attacker": nid,
         "hunt": bool(ns[0]["task"].get("hunt")), "ambush": pid if ambush else None, "opened": now}
    g.battle = B
    if not owner and not ambush:
        g.pocs_pending = [(p[1], p[2]) for p in pocs]
        spawn_aliens_initial(g, pid, "province", x, y)
        npc_spawn(g, pid, nid, ns, budget, homes, "assault", x, y, True, keep_meta=True)
    else:
        npc_spawn(g, pid, nid, ns, budget, homes, "assault", x, y, True)
    if ambush:                                    # the ambushed reinforcement stands at the far side
        far = spots[-1] if spots else (x, y)
        for n in ambush["d_ns"]:
            _npc_put_squad(g, ambush["d"], n, NPC_GHOST_DEPLOY, far, "assault")
    elif owner:                                   # the owner's NPCs defend (like npc_spawn_defenders)
        cand = [n for n in npc_of(owner) if n["state"] == "active" and now >= n["rest_until"] and not n["task"]]
        cand.sort(key=lambda n: -NP.power_of(n))
        cl = npc_closeness(pid)
        picked = cand[:NPC_DEFENDERS_MAX + int(round(3 * cl))]
        per = max(4, int(NPC_BATTLE_UNITS[1] * (1 + cl)) // max(1, len(picked)))      # 36 .. 72 defenders in all
        for i, n in enumerate(picked):
            pc = pocs[i % len(pocs)] if pocs else None
            n["task"] = {"kind": "defend", "target": pid, "phase": "battle", "since": now}
            _npc_put_squad(g, owner, n, per, (pc[1], pc[2]) if pc else (x, y), "hold", pc, 1.0 + 0.5 * cl)
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
    log(f"   NPC: REAL battle on {pid} ({'ambush' if ambush else 'hunt' if B['hunt'] else 'assault'}) by nation {nid} "
        f"{[n['name'] for n in ns]} vs {'aliens' if not owner and not ambush else 'nation ' + str(ambush['d'] if ambush else owner)}: "
        f"{len(g.targets)} unit(s) on the map")
    return True

def _ghost_death(B, tid, tg):
    g = B["ghost"]
    B["targets"].pop(tid, None)
    dead_aliens(g).add(tid)
    alien_removed(g, tid, tg)

def ghost_step(B, now, dt=1.0):
    """one simulated second of a battle without players."""
    g = B["ghost"]
    pid = B["map"]
    tier = PLANET_TIER.get((pid // 100000) % 1000, 1)
    ctx = BSIM.Ctx()
    ctx.grid = _walk_grid(alien_context(g, pid)[3])
    ctx.now, ctx.aggro, ctx.leash, ctx.focus, ctx.poc_radius = now, AL.AGGRO[tier], AL.LEASH[tier], AL.FOCUS_MAX, POC_RADIUS
    ctx.hunt_from = (g.alien_meta or {}).get("hunt_from", 0)
    ctx.side_of = lambda tg: tg.get("nation") if tg.get("npc") is not None else ALIEN_NATION
    ctx.same_side = same_side
    ctx.damage = hit_damage
    ctx.on_death = lambda tid, tg: _ghost_death(B, tid, tg)
    BSIM.step(B["targets"], B["pocs"], ctx, dt)
    for tg in B["targets"].values():              # wounds are remembered (the NPC picks healthy units next time)
        if tg.get("npc") is not None and tg.get("idx") is not None:
            n_ = npc_state()["npcs"].get(str(tg["npc"]))
            if n_ is not None:
                NP.health(n_)[tg["idx"]] = max(0.0, min(1.0, tg["hp"] / max(1, tg["max"])))
    npc_fresh_wave(g, B, now)
    if B["pocs"] and not _live(B):                # poc_loop runs every 0.5 s; in a long sim step capture here too
        pass
    ghost_check_end(B, now)

def _side_alive(B, nat):
    return sum(1 for tg in B["targets"].values() if tg.get("hp", 0) > 0 and not tg.get("hive")
               and same_side(tg.get("nation") if tg.get("npc") is not None else ALIEN_NATION, nat))

def _reserve(B, nat, enemy=False):
    return any(rt.get("B") is B and rt.get("waves", 0) < NPC_WAVES_MAX and (not same_side(rt["nid"], nat) if enemy
                                                                            else same_side(rt["nid"], nat))
               for rt in NPC_RT.values())

def ghost_check_end(B, now):
    if B.get("won"):
        return
    A = B.get("npc_attacker")
    pocs = B["pocs"]
    if pocs and all(same_side(A, p["owner"]) for p in pocs.values()):
        return ghost_finish(B, True)
    att = _side_alive(B, A)
    dfn = sum(1 for tg in B["targets"].values() if tg.get("hp", 0) > 0 and not tg.get("hive")) - att
    if att == 0 and not _reserve(B, A) and not any(same_side(side_nation(o), A) for o in _live(B)):
        return ghost_finish(B, False)
    if not pocs and dfn == 0 and not _reserve(B, A, enemy=True) and not _live(B):
        return ghost_finish(B, True)

def ghost_time_up(B):
    A = B.get("npc_attacker")
    pocs = list(B["pocs"].values())
    if pocs:
        mine = sum(1 for p in pocs if same_side(A, p["owner"]))
        return ghost_finish(B, mine > len(pocs) - mine)
    def frac(enemy):
        ids = [i for i, rt in NPC_RT.items() if rt.get("B") is B and (not same_side(rt["nid"], A) if enemy else same_side(rt["nid"], A))]
        d = sum(NPC_RT[i].get("dead", 0) for i in ids)
        u = sum(NPC_RT[i].get("units", 0) for i in ids)
        return d / u if u else 1.0
    ghost_finish(B, frac(False) < frac(True))

def ghost_finish(B, att_won):
    """result of a battle an NPC nation started (with or without players on the map)."""
    if B.get("won"):
        return
    B["won"] = True
    pid, A = B["map"], B.get("npc_attacker")
    NPC_RESULT[pid] = bool(att_won)
    RAIDS.pop(pid, None)
    old = province_owner(pid)
    if att_won and A and not B.get("hunt") and not B.get("ambush") and old != A:
        set_province_owner(pid, A)
        if not old:
            AL.set_garrison(world_state(), pid, 0.0)
            save_world(world_state())
        else:
            _notify_side(old, f"{province_label(pid)} 失守了！", f"{province_label(pid)} 失守了！", f"{province_label(pid)} was lost!",
                         (255, 120, 120))
    live = _live(B)
    for o in list(live):
        asyncio.get_event_loop().create_task(end_battle(o, o.battle_gen, won=(not getattr(o, "spectator", False)
                                                                               and same_side(side_nation(o), A) == bool(att_won))))
    if not live and BATTLES.get(pid) is B:
        del BATTLES[pid]
    log(f"   NPC battle on {pid} over: attackers of nation {A} {'WON' if att_won else 'lost'} "
        f"({'with players' if live else 'simulated'}, {int(time.monotonic() - B['t0'])}s)")

def ghost_handover(B):
    """the first player enters a simulated battle: every unit is where the simulation left it; the AIs give new orders."""
    for tg in B["targets"].values():
        tg["state"], tg["target"], tg["mv"], tg["dest"], tg["on_poc"] = "idle", None, None, None, None
        if tg.get("pos"):
            tg["x"], tg["y"] = int(tg["pos"][0]), int(tg["pos"][1])
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
        for pid, B in todo:
            if BATTLES.get(pid) is not B or B.get("won") or _live(B):
                continue
            try:
                ghost_step(B, time.time(), dt=GHOST_TICK)
            except Exception as e:
                import traceback
                log(f"   ghost battle {pid} error: {e!r} {traceback.format_exc()[-300:]}")
            await asyncio.sleep(0)                       # let the network handlers run between two battles
        await asyncio.sleep(max(0.05, GHOST_TICK - (time.monotonic() - t0)))

def npc_reinforce_enter(n, now):''')

# ---- 3. hooks -----------------------------------------------------------------------------------------------------------
rep('''    asyncio.get_event_loop().create_task(npc_cycle())
''', '''    asyncio.get_event_loop().create_task(npc_cycle())
    asyncio.get_event_loop().create_task(ghost_cycle())
''')
# entering: a simulated battle is JOINED
rep('''    joining = bool(B and B["members"])''', '''    joining = bool(B and (B["members"] or B.get("ghost")) and not B.get("won"))
    if joining and B.get("ghost") and not _live(B):
        ghost_handover(B)''')
# last player leaves a simulated battle: it goes on
rep('''        if not b["members"] and BATTLES.get(m) is b:
            del BATTLES[m]''', '''        if not b["members"] and BATTLES.get(m) is b and b.get("ghost") and not b.get("won"):
            ghost_resume(b)
        elif not b["members"] and BATTLES.get(m) is b:
            del BATTLES[m]''')
# results of NPC-started battles go through ghost_finish
rep('''def npc_won_battle(b):
    if b.get("won"):
        return''', '''def npc_won_battle(b):
    if b.get("npc_attacker") is not None:
        return ghost_finish(b, True)
    if b.get("won"):
        return''')
rep('''async def battle_timer(b):
    await asyncio.sleep(BATTLE_SECONDS)
    if BATTLES.get(b["map"]) is b and not b.get("won"):''', '''async def battle_timer(b):
    await asyncio.sleep(BATTLE_SECONDS)
    if BATTLES.get(b["map"]) is b and not b.get("won") and b.get("npc_attacker") is not None:
        ghost_time_up(b)                 # NPC battle (simulated or with players): POC majority, else the losses
        return
    if BATTLES.get(b["map"]) is b and not b.get("won"):''')
# AIs pause while the server simulates
rep('''            meta = getattr(s, "alien_meta", None) or {"tier": 1}''', '''            if b is not None and b.get("ghost") and not _live(b):
                await asyncio.sleep(1.0)
                continue                         # no player: battlesim moves the units (ghost_cycle)
            meta = getattr(s, "alien_meta", None) or {"tier": 1}''')
rep('''            now = time.time()
            meta = getattr(s, "alien_meta", None) or {}
            if not meta.get("npc"):''', '''            now = time.time()
            if b is not None and b.get("ghost") and not _live(b):
                await asyncio.sleep(1.0)
                continue
            meta = getattr(s, "alien_meta", None) or {}
            if not meta.get("npc"):''')
# aliens and NPC units always fight each other (one rule with and without players)
rep('''                if _tg.get("ally") and _tg.get("npc") is not None and _tg.get("hp", 0) > 0 and _tg.get("pos"):''',
    '''                if _tg.get("npc") is not None and _tg.get("hp", 0) > 0 and _tg.get("pos"):''')
rep('''                        elif ally:''', '''                        else:                     # aliens fight every NPC (2026-10-22 21:29)''')
# support squads join a running NPC battle as defenders
rep('''            if t.get("phase") == "march" and now >= t.get("arrive", 0):
                t.update(phase="support", entered=now)
                log(f"   NPC: {n['name']} arrived to support {pid}")''', '''            if t.get("phase") == "march" and now >= t.get("arrive", 0):
                t.update(phase="support", entered=now)
                log(f"   NPC: {n['name']} arrived to support {pid}")
                _B = BATTLES.get(pid)
                if _B is not None and _B.get("npc_attacker") is not None and not _B.get("won"):
                    own = _B["owner"]
                    pocs_ = list(_B["pocs"].items())
                    pc = pocs_[0] if pocs_ else None
                    home = (pc[1]["x"], pc[1]["y"]) if pc else next(iter(_B["targets"].values()), {}).get("home", (512, 512))
                    if _npc_put_squad(own, n["nation"], n, NPC_GHOST_DEPLOY, home, "hold",
                                      (pc[0], pc[1]["x"], pc[1]["y"]) if pc else None):
                        NPC_RT[n["id"]]["B"] = _B
                        n["task"] = {"kind": "defend", "target": pid, "phase": "battle", "since": now}
                        log(f"   NPC: {n['name']} joins the battle on {pid} as a defender")
                        continue''')
# supports are also sent for attacks that are real battles now
rep('''            if owner and not same_side(owner, n["nation"]) and tk["target"] not in BATTLES:''',
    '''            if owner and not same_side(owner, n["nation"]) and (tk["target"] not in BATTLES
                                                                 or BATTLES[tk["target"]].get("npc_attacker") == n["nation"]):''')
rep('''        if tk and tk.get("kind") == "attack" and tk.get("phase") in ("march", "siege", "raid"):''',
    '''        if tk and tk.get("kind") == "attack" and tk.get("phase") in ("march", "siege", "raid", "battle"):''')
# NPC-vs-NPC ambush = real battle on the road
rep('''        acc = t.get("acc")
        AMBUSH[R] = {"R": R, "o": O, "o_ids": [n["id"] for n in ns], "d": t["vs"], "d_ids": d_ids, "P": t["P"],
                     "acc": acc, "B": None, "t0": now,
                     "until": now + (NPC_AMBUSH_WAIT if acc else random.uniform(*NP.SIEGE))}''', '''        acc = t.get("acc")
        AMBUSH[R] = {"R": R, "o": O, "o_ids": [n["id"] for n in ns], "d": t["vs"], "d_ids": d_ids, "P": t["P"],
                     "acc": acc, "B": None, "t0": now,
                     "until": now + (NPC_AMBUSH_WAIT if acc else random.uniform(*NP.SIEGE))}
        if d_ids and NPC_GHOST_BATTLES:
            d_ns = [npc_state()["npcs"][str(i)] for i in d_ids]
            if npc_open_battle(R, ns, now, ambush={"d": t["vs"], "d_ns": d_ns}):
                AMBUSH[R]["B"] = BATTLES[R]
                AMBUSH[R]["until"] = now + BATTLE_SECONDS + 60''')
open(P, "w", encoding="utf-8").write(src)
print("patched")

# ---- second part (2026-10-22 21:50): POC capture inside the simulation step; poc_loop pauses while no player is there --
if "def _ghost_pocs" not in src:
    rep('''            members = battle_members(s) if b is None else [o for o in b["members"] if not o.w.is_closing()]
            for pid, p in pocs.items():''', '''            members = battle_members(s) if b is None else [o for o in b["members"] if not o.w.is_closing()]
            if b is not None and b.get("ghost") and not members:
                await asyncio.sleep(POC_TICK)
                continue                         # no player: ghost_step captures (_ghost_pocs)
            for pid, p in pocs.items():''')
    rep('''    npc_fresh_wave(g, B, now)
    if B["pocs"] and not _live(B):                # poc_loop runs every 0.5 s; in a long sim step capture here too
        pass
    ghost_check_end(B, now)''', '''    npc_fresh_wave(g, B, now)
    _ghost_pocs(B, dt)
    ghost_check_end(B, now)

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
            p["capturing"] = False''')
    open(P, "w", encoding="utf-8").write(src)
    print("patched part 2")

# ---- third part: anti-air-only unit kinds never become the main kind of an NPC doctrine (npc.pick_doctrine uses it) ----
rep('''    med = sorted(p["spd"] for p in pool)[len(pool) // 2]
    for p in pool:
        p["fast"] = p["spd"] >= med''', '''    med = sorted(p["spd"] for p in pool)[len(pool) // 2]
    for p in pool:
        p["fast"] = p["spd"] >= med
        try:                      # can it hit GROUND units? (anti-air only kinds are never the main kind of a doctrine)
            p["ground"] = unit_stats9(npc_unit(p["code"], max(1, int(p["min"]))))[3] > 0
        except Exception:
            p["ground"] = True''')
open(P, "w", encoding="utf-8").write(src)

# ---- fourth part: simulated NPC battles show the battle icon on the strategic map (open to all) --------------------------
rep('''        if mid >= 100000000 or not B.get("members") or B.get("sim"):
            continue
        bat.append((province_of(mid), len(B["members"]), getattr(B.get("owner"), "join_mode", 0)))''', '''        if mid >= 100000000 or not (B.get("members") or B.get("ghost")) or B.get("sim") or B.get("won"):
            continue
        bat.append((province_of(mid), len(B["members"]), getattr(B.get("owner"), "join_mode", 0)))''')
rep('''        if mid >= 100000000 or not B.get("members") or B.get("sim"):
            continue
        pv = province_of(mid)''', '''        if mid >= 100000000 or not (B.get("members") or B.get("ghost")) or B.get("sim") or B.get("won"):
            continue
        pv = province_of(mid)''')
open(P, "w", encoding="utf-8").write(src)
