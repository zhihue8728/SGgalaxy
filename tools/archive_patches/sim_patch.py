"""Battle Simulation Center (user 2026-10-22: 'battle simulation沒有功能').
Client (reverse engineered 2026-10-22):
  HQ portal type 4 (004d0b30 case 4) -> 004a3d40(1) -> CBoardWnd in SIM mode (+0x129f5 = 1, 00422cb0:
  smc-titl.bik, map control mode 2 = smc-back.xpf).  On open (00421460) it sends 0x2b [01][00] (00565650)
  instead of 0x2b [00][same planet] + 0x2c.  In mode 2 a click on a province selects it (00466b50 -> 00466250,
  sends 0x2c [u32 province] -> province panel), the panel's ENTER button (0x11, 00435fa0) -> 00463a60 ->
  00463440: needs a BATTLE on the province record (0x2d rec +0x30), state != 3 (full), the join timer elapsed
  (u16 timer * 1 s, 00569490 -> +0x3c) and the player's nation in the record's nation list (+0x44);
  dialog -> JOIN = 0x20 [08][u32 province], WATCH = 0x20 [0d][u32 province].
Server: 0x2b [01] -> sim board (every province but the capitals carries an open battle), the join that follows
creates a SIMULATION battle on the province's own map: always aliens at a full garrison, POCs held by the
aliens, nothing is permanent (account snapshot restored when the player leaves the map), no capture, no
garrison change, no records."""
import io, re, sys
P = sys.argv[1]
src = open(P, encoding="utf-8").read()
n0 = len(src)

def rep(old, new, cnt=1):
    global src
    c = src.count(old)
    assert c == cnt, (c, old[:80])
    src = src.replace(old, new)

# ---- 1. 0x2b: sim board
rep('''    elif t == 0x2b:
        # client opens / refreshes the strategic map.''', '''    elif t == 0x2b and len(body) >= 2 and body[1] == 1:
        # Battle Simulation Center board (CBoardWnd sim mode, client 00565650 sends [01][00])
        s.sim_board = True
        s.send(build_sim_map(s))
    elif t == 0x2b:
        s.sim_board = False
        # client opens / refreshes the strategic map.''')

# ---- 2. join request from the sim board
rep('''        elif typ in (1, 7, 8, 13) and len(body) >= 6:
            m = struct.unpack_from(">I", body, 2)[0]
            log(f"   join request type {typ} for map {m}{' (WATCH)' if typ == 13 else ''}")''',
'''        elif typ in (8, 13) and len(body) >= 6 and getattr(s, "sim_board", False):
            m = struct.unpack_from(">I", body, 2)[0]
            log(f"   SIMULATION join request type {typ} for map {m}{' (WATCH)' if typ == 13 else ''}")
            sim_join(s, m, watch=(typ == 13))
        elif typ in (1, 7, 8, 13) and len(body) >= 6:
            m = struct.unpack_from(">I", body, 2)[0]
            log(f"   join request type {typ} for map {m}{' (WATCH)' if typ == 13 else ''}")''')

# ---- 3. enter_field: sim battles
rep('''def enter_field(s, mapid, x, y, capital=False, watch=False):''',
    '''def enter_field(s, mapid, x, y, capital=False, watch=False, sim=False):''')
rep('''    town = capital or map_kind(mapid) == "sst" or (map_kind(mapid) == "province"''',
    '''    _Bs = BATTLES.get(mapid)
    sim = bool(sim or (_Bs and _Bs.get("sim") and not capital))
    town = (not sim) and (capital or map_kind(mapid) == "sst") or (not sim) and (map_kind(mapid) == "province"''')
rep('''    if not town and s.cur_province and map_kind(mapid) == "province":
        s.battle_province = province_of(mapid)''',
    '''    if not town and s.cur_province and map_kind(mapid) == "province" and not sim:
        s.battle_province = province_of(mapid)''')
rep('''    if joining:
        pocs = [(pid, p["x"], p["y"], p["strength"], POC_TYPE, p["owner"]) for pid, p in B["pocs"].items()]   # pads added below''',
    '''    if sim and pocs and not joining:
        pocs = [p[:5] + (ALIEN_NATION,) + tuple(p[6:]) for p in pocs]     # simulation: the aliens hold every POC
    if joining:
        pocs = [(pid, p["x"], p["y"], p["strength"], POC_TYPE, p["owner"]) for pid, p in B["pocs"].items()]   # pads added below''')
rep('''    owner = province_owner(mapid) if mapid < 100000000 else 0
    # battery pads''', '''    owner = province_owner(mapid) if mapid < 100000000 and not sim else 0
    if sim and not watch and getattr(s, "sim_snap", None) is None:
        sim_snapshot(s, mapid)
    # battery pads''')
rep('''        elif kind == "ctf" or kind == "other":
            # training targets''', '''        elif sim:
            # BATTLE SIMULATION: always a full alien garrison, whoever owns the province
            s.pocs_pending = [(p[1], p[2]) for p in pocs] if pocs else []
            spawn_aliens_initial(s, mapid, "province", x, y, sim=True)
            asyncio.get_event_loop().create_task(alien_ai(s, (getattr(s, "battle_gen", 0) or 0) + 1))
            try:
                s.send(chat_line(0x0A, "BATTLE SIMULATION: units are not lost and no experience or resources are gained.",
                                 (120, 220, 255)))
            except Exception:
                pass
        elif kind == "ctf" or kind == "other":
            # training targets''')
rep('''                 "won": False, "defender": province_owner(mapid) if mapid < 100000000 else 0}
            BATTLES[mapid] = B''', '''                 "won": False, "defender": province_owner(mapid) if mapid < 100000000 and not sim else 0,
                 "sim": sim}
            BATTLES[mapid] = B''')
rep('''            if B["defender"] and not (getattr(s, "alien_meta", None) or {}).get("raid"):''',
    '''            if B["defender"] and not sim and not (getattr(s, "alien_meta", None) or {}).get("raid"):''')

# ---- 4. aliens
rep('''def spawn_aliens_initial(s, mapid, kind, x, y, raid=False):''',
    '''def spawn_aliens_initial(s, mapid, kind, x, y, raid=False, sim=False):''')
rep('''    s.alien_meta["raid"] = raid
    if kind == "province":''', '''    s.alien_meta["raid"] = raid
    s.alien_meta["sim"] = sim
    if kind == "province":''')
rep('''        g = 100.0 if raid else AL.garrison(WORLD, mapid)''', '''        g = 100.0 if (raid or sim) else AL.garrison(WORLD, mapid)''')
rep('''        if not raid:
            try:
                s.send(chat_line(0x0A, f"Alien garrison of this province: {g:.0f}%."''',
    '''        if not raid and not sim:
            try:
                s.send(chat_line(0x0A, f"Alien garrison of this province: {g:.0f}%."''')
rep('''    if meta and (meta.get("cave") == 0 or meta.get("hive")) and meta.get("mapid", 0) < 100000000 and not tg.get("raid"):''',
    '''    if meta and (meta.get("cave") == 0 or meta.get("hive")) and meta.get("mapid", 0) < 100000000 and not tg.get("raid") \\
            and not meta.get("sim"):''')

# ---- 5. strategic map / signature: sim battles are invisible
rep('''    for mid, B in list(BATTLES.items()):
        if mid >= 100000000 or not B.get("members"):
            continue
        pv = province_of(mid)''', '''    for mid, B in list(BATTLES.items()):
        if mid >= 100000000 or not B.get("members") or B.get("sim"):
            continue
        pv = province_of(mid)''')
rep('''    for mid, B in list(BATTLES.items()):
        if mid >= 100000000 or not B.get("members"):
            continue
        bat.append(''', '''    for mid, B in list(BATTLES.items()):
        if mid >= 100000000 or not B.get("members") or B.get("sim"):
            continue
        bat.append(''')

# ---- 6. real players never walk into a simulation (and the other way round)
rep('''def arrive_battle(s, mapid, watch=False, side=None):
    """the player chose to take part (or to watch / offer his service): ask the battle commander."""''',
    '''def arrive_battle(s, mapid, watch=False, side=None):
    """the player chose to take part (or to watch / offer his service): ask the battle commander."""
    if BATTLES.get(mapid, {}).get("sim"):
        s.send(chat_line(0x0A, "A battle simulation is running on this province. Try again later.", (255, 200, 80)))
        log(f"   {s.acc}: real join of {mapid} refused, a simulation runs there")
        return''')
rep('''        if mapid in BATTLES and BATTLES[mapid].get("owner") is not s and province_owner(mapid) != cmd.get("nation"):
            if BATTLE_CTRL_DIALOG''', '''        if mapid in BATTLES and BATTLES[mapid].get("sim"):
            s.send(chat_line(0x0A, "A battle simulation is running on this province. Try again later.", (255, 200, 80)))
            _cur = getattr(s, "map", None) or CAPITALS.get(cmd["nation"])
            enter_field(s, _cur, x, y, capital=(_cur == CAPITALS.get(cmd["nation"])))
            return
        if mapid in BATTLES and BATTLES[mapid].get("owner") is not s and province_owner(mapid) != cmd.get("nation"):
            if BATTLE_CTRL_DIALOG''')

# ---- 7. leaving the map restores the account
rep('''def leave_map(s, why=""):
    m = getattr(s, "map", None)
    if m is None:
        return''', '''def leave_map(s, why=""):
    m = getattr(s, "map", None)
    if m is None:
        return
    if getattr(s, "sim_snap", None) is not None and getattr(s, "sim_map", None) == m:
        sim_restore(s)''')

rep('''        if not getattr(s, "spectator", False) and m < 100000000:
            LEFT_BATTLE[s.acc]''', '''        if not getattr(s, "spectator", False) and m < 100000000 and not b.get("sim"):
            LEFT_BATTLE[s.acc]''')

# ---- 8. end of a simulation battle
rep('''    for t in list(getattr(s, "attacks", {}).values()):
        t.cancel()
    s.attacks = {}
    hpmap = getattr(s, "unit_hp", {})
    if hpmap:''', '''    for t in list(getattr(s, "attacks", {}).values()):
        t.cancel()
    s.attacks = {}
    if getattr(s, "sim_snap", None) is not None:
        await sim_finish(s, gen, won)
        return
    hpmap = getattr(s, "unit_hp", {})
    if hpmap:''')

# ---- 9. new functions (before arrive_battle)
SIM_FUNCS = r'''
# ---- BATTLE SIMULATION CENTER (2026-10-22, see tools/../claude/SIM_CENTER.md) --------------------------------
SIM_KEYS = ("units", "resources", "commander", "hero_items", "next_uid")

def build_sim_map(s):
    """0x2d for the sim board: every province of the hero's planet, an OPEN battle on all but the capitals (join timer
    0, the player's nation in the nation list = the client offers JOIN / WATCH).  Real battles are not shown."""
    cmd = getattr(s, "cmd", {"nation": 1})
    nat = side_nation(s) or cmd.get("nation", 1)
    planet = current_planet(s)
    provs = planet_provinces(planet)
    caps = set(CAPITALS.values())
    rec = b""
    for pid in provs:
        name = next((n[1] for n in NATIONS if CAPITALS.get(n[0]) == pid), f"P{(pid % 10000) // 100}-{pid % 100}")
        nb = name.encode("latin-1", "replace")[:30]
        busy = BATTLES.get(pid)
        nsim = len(busy["members"]) if busy and busy.get("sim") else 0
        if pid in caps or (busy and not busy.get("sim")):
            fight = bytes([0])                                       # capital / real battle: no simulation
        else:
            fight = bytes([1, 3 if nsim >= 10 else 1]) + struct.pack(">H", 0) + bytes([0])
        rec += struct.pack(">I", pid) + bytes([1 if pid in caps else 0, len(nb)]) + nb + bytes([99]) \
            + struct.pack(">I", province_owner(pid)) + bytes([0]) + fight \
            + bytes([1]) + struct.pack(">I", nat) + bytes([min(nsim, 255), 0])
    log(f"   SIM board -> 0x2d with {len(provs)} provinces of planet {planet}")
    return bytes([0x2D]) + struct.pack(">HH", len(provs), 0) + rec + struct.pack(">H", 0)

def sim_arrival(mapid, s):
    """arrival point of a simulation: the walkable spawn spot farthest from the map's first POC."""
    try:
        name = alien_context(s, mapid)[3]
        spots = [tuple(p) for p in SPAWN_SPOTS.get(name or "", [])]
        pocs = province_pocs(mapid)
        if spots and pocs:
            px, py = pocs[0][1], pocs[0][2]
            return max(spots, key=lambda p: (p[0] - px) ** 2 + (p[1] - py) ** 2)
        if spots:
            return spots[0]
    except Exception as e:
        log(f"   sim arrival error: {e!r}")
    return (0x800, 0x800)

def sim_join(s, mapid, watch=False):
    pid = province_of(mapid) if mapid < 100000000 else None
    if not pid or pid in CAPITALS.values() or map_kind(mapid) != "province":
        s.send(chat_line(0x0A, "Simulations cannot be held in a capital.", (255, 200, 80)))
        return
    B = BATTLES.get(mapid)
    if B and not B.get("sim"):
        s.send(chat_line(0x0A, "A real battle is running on this province. Try again later.", (255, 200, 80)))
        return
    s.sim_board = False
    if B:
        x, y = getattr(B.get("owner"), "entry_pos", None) or sim_arrival(mapid, s)
    else:
        x, y = sim_arrival(mapid, s)
    log(f"   SIMULATION {'watch' if watch else ('join' if B else 'start')} on {mapid} at ({x},{y}) by {s.acc}")
    enter_field(s, mapid, x, y, watch=watch, sim=True)

def sim_snapshot(s, mapid):
    import copy
    _accs, a = get_account(s.acc)
    s.sim_snap = {k: copy.deepcopy(a.get(k)) for k in SIM_KEYS}
    s.sim_map = mapid
    log(f"   SIMULATION snapshot of {s.acc} taken ({len(a.get('units', []))} unit(s))")

def sim_restore(s):
    import copy
    snap = getattr(s, "sim_snap", None)
    if snap is None:
        return
    accs, a = get_account(s.acc)
    for k, v in snap.items():
        if v is None:
            a.pop(k, None)
        else:
            a[k] = copy.deepcopy(v)
    accs[s.acc] = a
    save_accounts(accs)
    s.sim_snap = None
    s.unit_hp = {}
    log(f"   SIMULATION over for {s.acc}: account restored (units, resources, XP)")

async def sim_finish(s, gen, won):
    sim_restore(s)
    st = getattr(s, "battle_stats", None)
    if st is not None:
        st["gain"] = [0] * 5
    try:
        s.send(build_battle_result(s, won, [0] * 5))
    except Exception as e:
        log(f"   sim result window failed: {e!r}")
    s.send(chat_line(0x0A, "Battle simulation over: everything is back as it was.", (120, 220, 255)))
    await asyncio.sleep(RESULT_SHOW_SECONDS)
    if getattr(s, "battle_gen", None) != gen or s.w.is_closing():
        return
    cmd = getattr(s, "cmd", {"nation": 1})
    _accs, a = get_account(s.acc)
    s.send(build_commander(s.acc, cmd["nation"], cmd.get("attrs", (0, 0, 0, 0)), resources=a["resources"]))
    s.battle_kind = ""
    log(f"   simulation over ({'victory' if won else 'defeat'}) -> back to capital")
    enter_field(s, CAPITALS.get(cmd["nation"], 200000000), 0x200, 0x200, capital=True)
'''
rep('''def arrive_battle(s, mapid, watch=False, side=None):''', SIM_FUNCS + '''
def arrive_battle(s, mapid, watch=False, side=None):''')

open(P, "w", encoding="utf-8").write(src)
print("patched", n0, "->", len(src))
