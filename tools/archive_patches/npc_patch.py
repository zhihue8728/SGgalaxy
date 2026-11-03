"""apply the NPC NATIONS patch to server/sgserver.py (backup sgserver.py.before_npc).  Run from the repo root."""
import os, shutil, sys

SRC = os.path.join("server", "sgserver.py")
BLOCK = os.path.join("tools", "npc_block.py")
txt = open(SRC, encoding="utf-8").read()
if "NPC NATIONS" in txt:
    sys.exit("already patched")
shutil.copyfile(SRC, SRC + ".before_npc")

def rep(old, new, count=1):
    global txt
    n = txt.count(old)
    assert n == count, f"expected {count} x, found {n}: {old[:70]!r}"
    txt = txt.replace(old, new)

rep('''def set_province_owner(pid, nid):
    global WORLD
    if WORLD is None:
        WORLD = load_world()
    WORLD["owners"][str(pid)] = nid
    save_world(WORLD)
''', '''def set_province_owner(pid, nid):
    global WORLD
    if WORLD is None:
        WORLD = load_world()
    old = int(WORLD["owners"].get(str(pid), 0))
    WORLD["owners"][str(pid)] = nid
    save_world(WORLD)
    try:
        npc_owner_changed(pid, old, nid)
    except Exception as e:
        log(f"   npc_owner_changed error: {e!r}")
''')

rep('''    rows = [(n, a["commander"]) for n, a in accs.items() if "commander" in a and (only is None or uid_of(n) == only)]
    return rows
''', '''    rows = [(n, a["commander"]) for n, a in accs.items() if "commander" in a and (only is None or uid_of(n) == only)]
    try:
        rows += npc_directory_rows(only)         # NPC commanders look like normal players (user 2026-10-22 13:13)
    except Exception as e:
        log(f"   npc directory error: {e!r}")
    return rows
''')

rep('''        if "commander" in a and uid_of(n) == uid:
            return n, a
    return None, None
''', '''        if "commander" in a and uid_of(n) == uid:
            return n, a
    for n in npc_all():
        if uid_of(n["name"]) == uid:
            return n["name"], npc_account(n)
    return None, None
''')

rep('''        if acc.lower() == n and "commander" in a:
            return acc, a
    return None, None
''', '''        if acc.lower() == n and "commander" in a:
            return acc, a
    _n = npc_by_name(n)
    if _n:
        return _n["name"], npc_account(_n)
    return None, None
''')

rep('''        if acc in accs:
            log(f"   register: account {acc!r} already exists -> fail")''',
    '''        if acc in accs or npc_name_taken(acc):
            log(f"   register: account {acc!r} already exists -> fail")''')

rep('''if now < r["until"] or pid in BATTLES:''', '''if now < r["until"] or pid in BATTLES or r.get("npc"):''')

# ---- enter_field: NPC attackers of a raid / NPC defenders of an owned province
rep('''        elif kind == "province" and province_owner(mapid) != 0 and mapid in RAIDS \\
                and side_nation(s) == province_owner(mapid):
            # ALIEN RAID''', '''        elif kind == "province" and province_owner(mapid) != 0 and mapid in RAIDS and RAIDS[mapid].get("npc") \\
                and side_nation(s) == province_owner(mapid):
            # NPC RAID (claude/NPC_NATIONS_PLAN.md): commanders of another nation attack; they fight and capture POCs
            s.pocs_pending = []
            npc_spawn_attackers(s, mapid, x, y, pocs, len(units))
            asyncio.get_event_loop().create_task(npc_ai(s, (getattr(s, "battle_gen", 0) or 0) + 1))
        elif kind == "province" and province_owner(mapid) != 0 and mapid in RAIDS \\
                and side_nation(s) == province_owner(mapid):
            # ALIEN RAID''')

rep('''            log(f"   PvP battle: {acc} attacks province {mapid} of nation {province_owner(mapid)} (no aliens)")
''', '''            log(f"   PvP battle: {acc} attacks province {mapid} of nation {province_owner(mapid)} (no aliens)")
            if npc_spawn_defenders(s, mapid, x, y, pocs, len(units)):       # NPC commanders defend their nation's province
                asyncio.get_event_loop().create_task(npc_ai(s, (getattr(s, "battle_gen", 0) or 0) + 1))
''')

rep('''            asyncio.get_event_loop().create_task(battle_timer(B))
''', '''            npc_battle_started(s, B)
            asyncio.get_event_loop().create_task(battle_timer(B))
''')

# ---- poc_loop
rep('''                        if abs(ux - p["x"]) <= POC_RADIUS and abs(uy - p["y"]) <= POC_RADIUS:
                            on.append((o, u))
                cap = [(o, u) for o, u in on if not same_side(side_nation(o), p["owner"])]
''', '''                        if abs(ux - p["x"]) <= POC_RADIUS and abs(uy - p["y"]) <= POC_RADIUS:
                            on.append((o, u))
                if b is not None:                      # NPC capturers standing on the POC (npc_ai sets on_poc)
                    for _tid, _tg in list(b["targets"].items()):
                        if _tg.get("npc") is not None and _tg.get("on_poc") == pid and _tg["hp"] > 0:
                            on.append((NpcSide(_tg), _tid))
                cap = [(o, u) for o, u in on if not same_side(side_nation(o), p["owner"])]
''')
rep('''                        if p["progress"] < -2 * p["strength"]:''',
    '''                        if p["progress"] < (-0.15 if getattr(who, "is_npc", False) else -2) * p["strength"]:''')
rep('''                            _bst = getattr(who, "battle_stats", None)
                            if _bst is not None:
                                _bst["pocs"] = _bst.get("pocs", 0) + 1
                            _ac, _a = get_account(who.acc)
                            _st = _a.setdefault("commander", {}).setdefault("stats", {})
                            _st["pocs"] = _st.get("pocs", 0) + 1
                            check_medals(who, _a, _ac)
                            _ac[who.acc] = _a
                            save_accounts(_ac)
''', '''                            if not getattr(who, "is_npc", False):
                                _bst = getattr(who, "battle_stats", None)
                                if _bst is not None:
                                    _bst["pocs"] = _bst.get("pocs", 0) + 1
                                _ac, _a = get_account(who.acc)
                                _st = _a.setdefault("commander", {}).setdefault("stats", {})
                                _st["pocs"] = _st.get("pocs", 0) + 1
                                check_medals(who, _a, _ac)
                                _ac[who.acc] = _a
                                save_accounts(_ac)
''')
rep('''            if winners:
                s.poc_won = True
''', '''            if b is not None and b.get("npc_raid") and pocs and owners == {b.get("npc_side")} and not b.get("won"):
                npc_won_battle(b)          # NPC raiders hold every POC: the defenders lose the province
                break
            if winners:
                s.poc_won = True
''')

rep('''    if BATTLES.get(b["map"]) is b and not b.get("won"):
        b["won"] = True
        dfd = b.get("defender", 0)
''', '''    if BATTLES.get(b["map"]) is b and not b.get("won"):
        b["won"] = True
        npc_time_up(b)
        dfd = b.get("defender", 0)
''')

rep('''        if r:
            raid_notify(r["nation"], f"The alien raid on {province_label(meta.get('mapid'))} was repelled!", (120, 255, 120))
''', '''        if meta.get("npc"):
            npc_battle_result(meta.get("mapid"), False)
        if r:
            raid_notify(r["nation"], f"The {'raid' if meta.get('npc') else 'alien raid'} on "
                                     f"{province_label(meta.get('mapid'))} was repelled!", (120, 255, 120))
''')

rep('''            del BATTLES[m]
            log(f"   battle on {m} closed (no participants left)")
''', '''            del BATTLES[m]
            log(f"   battle on {m} closed (no participants left)")
            npc_battle_closed(b)
''')

rep('''    dfd = b.get("defender", 0)
    if not dfd or b.get("won"):
        return
''', '''    dfd = b.get("defender", 0)
    if not dfd or b.get("won") or b.get("targets"):       # server-owned enemies (aliens / NPCs) still alive: not over
        return
''')

rep('''    """bookkeeping when an alien dies: province garrison goes down."""
''', '''    """bookkeeping when an alien dies: province garrison goes down."""
    if tg.get("npc") is not None:
        npc_unit_died(tg)
''')

rep('''def honor_hp(cmd, hp):
    """unit max HP including the honor bonus (see HONOR_HP_MODE)."""
''', '''def honor_hp(cmd, hp):
    """unit max HP including the honor bonus and the 'last stand' bonus of a nation in trouble (NPC plan)."""
    return int(_honor_hp0(cmd, hp) * npc_stand_mult(cmd.get("nation", 0)))

def _honor_hp0(cmd, hp):
''')

rep('''    # every running province battle (BATTLES) gets the Legend icon''', '''    for _n in npc_active():                  # NPC commanders are drawn like players
        _loc, _tg = npc_location(_n)
        if _loc:
            counts.setdefault(_loc, {}).setdefault(_n["nation"], 0)
            counts[_loc][_n["nation"]] += 1
    # every running province battle (BATTLES) gets the Legend icon''')

rep('''    # +0x48 = terrain THEME of the province map for the preview minimap''', '''    for _n in npc_active():
        _loc, _tg = npc_location(_n)
        if pid in (_loc, _tg):
            users.append((_n["name"], _n["nation"], min(_n["level"], 255), _tg))
    # +0x48 = terrain THEME of the province map for the preview minimap''')

rep('''    asyncio.get_event_loop().create_task(map_push_cycle())
    async with srv:''', '''    asyncio.get_event_loop().create_task(map_push_cycle())
    asyncio.get_event_loop().create_task(npc_cycle())
    async with srv:''')

rep('''        elif parts[0] == "/raidnow":''', '''        elif parts[0] == "/npc":
            npc_gm(s, parts)
            return
        elif parts[0] == "/raidnow":''')

block = open(BLOCK, encoding="utf-8").read()
rep("async def main():\n", block + "\n\nasync def main():\n")
open(SRC, "w", encoding="utf-8").write(txt)
print("patched", SRC)
