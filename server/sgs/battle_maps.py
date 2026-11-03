# sgserver part "battle_maps": shared maps / battles, F7, battle control, sim center, snapshots, POC, battle loop.
# Loaded by sgserver.py into ONE shared namespace (exec, in the order of PARTS) - not an importable module;
# every name here is a sgserver global.  Checks: python tools/check_server.py
# ---- SHARED MAPS AND BATTLES (research_multiplayer.md) ------------------------------------------------------------
# Every map id has a set of sessions on it.  On a town map players see each other's commanders; on a battle map
# the first player creates a BATTLE (one lock-step clock t0, one set of aliens and POCs); later players JOIN it
# (after the battle commander's permission: server 0x24 -> client 0x20 type+2 accept / type+1 reject, auto-accept
# after JOIN_TIMEOUT s).  Orders (client 0x80 lumps) are relayed to every participant with the same game time.
# Leaving: server 0x19 [u32 uid][u32 0] removes the units on the others' screens, 0xc5 [s8 name] "%s has left
# this battle."  When the battle time runs out the defender wins (attackers get a defeat).
MAP_PEERS = {}          # map id -> set(sessions)
BATTLES = {}            # map id -> battle dict
PENDING_JOIN = {}       # joiner account -> (session, map, x, y, commander session)
JOIN_PERMISSION = True
JOIN_TIMEOUT = 15.0
# BATTLE_SECONDS -> battlefield.py (2026-10-24, the battle rules in one place)

def map_peers(s):
    return [o for o in MAP_PEERS.get(getattr(s, "map", None), set()) if o is not s and not o.w.is_closing()]

def battle_unit_name(u):
    """unit NAME of a battle PUT (first label line, white): the unit's own label or its chassis name.  The second line
    (client 004c8fa0) is the OWNER = commander in his nation's colour.  Was the account name twice (19:38 screenshot)."""
    if not u:
        return ""
    lab = u.get("label")
    if lab and not is_default_name(lab):
        try:
            str(lab).encode("latin-1")                 # wire form (client bytes); a Unicode label -> chassis name
            return (PG.star_tag(u) + str(lab))[:40]
        except UnicodeEncodeError:
            pass
    return (PG.star_tag(u) + str(DISPLAY.get(u.get("chassis"), u.get("chassis")) or ""))[:40]   # (10-31) "*N " = stars

def battle_members(s):
    b = getattr(s, "battle", None)
    return [o for o in (b["members"] if b else {s}) if not o.w.is_closing()]

def put_for_others(s, viewer=None):
    """PUT packets that show s's commander (town) or units (battle) to other players."""
    out = []
    acc, nation = s.acc, side_nation(s)
    if getattr(s, "battle", None):
        _now = time.time()
        for uid in getattr(s, "alive_units", set()):
            args = getattr(s, "put_args", {}).get(uid)
            if args and args.get("enter_t", 0) <= _now:  # a squad still on its way comes with its delayed_put
                x, y = s.unit_pos.get(uid, (args["x"], args["y"]))
                out.append(build_put_unit(uid, args.get("label") or acc, acc, x, y, args["kind"], args["cls"], nation, hp=args["hp"],
                                          hp_max=args.get("hpmax"), energy=args["en"], stats9=args["st9"], slot=args["slot"],
                                          sight=args["sight"], speed=args["spd"], abilities=args["abil"]))
    elif getattr(s, "hero_uid", None):
        x, y = getattr(s, "hero_pos", (0x200, 0x200))
        look = max(1, min(getattr(s, "cmd", {}).get("look", 1), 11))
        out.append(build_put_unit(s.hero_uid, acc, acc, x, y, 0, look, nation, speed=town_speed(get_account(acc)[1])))
        out.append(build_hero(s.hero_uid, acc, x, y, 0, look, nation, 100, hero_mark(acc), hero_rank(acc), hero_title(acc, viewer)))
    return out

def shown_uids(s):
    if getattr(s, "battle", None):
        return list(getattr(s, "alive_units", set()))
    return [s.hero_uid] if getattr(s, "hero_uid", None) else []

# A hero who left a province battle (retreat, disconnect, all units lost) must wait REJOIN_WAIT seconds before he can
# attack that province again: the 0x1E dialog's WAIT byte -> "The dust is still settling ... after %d seconds".
REJOIN_WAIT = 30
LEFT_BATTLE = {}           # account -> (province, time left)

def rejoin_wait(s, mapid):
    rec = LEFT_BATTLE.get(getattr(s, "acc", None))
    if not rec or rec[0] != province_of(mapid):
        return 0
    return max(0, int(REJOIN_WAIT - (__import__("time").time() - rec[1]) + 0.999))

def leave_map(s, why=""):
    m = getattr(s, "map", None)
    if m is None:
        return
    if getattr(s, "sim_snap", None) is not None and getattr(s, "sim_map", None) == m:
        sim_restore(s)
    MAP_PEERS.get(m, set()).discard(s)
    b = getattr(s, "battle", None)
    for o in map_peers(s):
        for uid in shown_uids(s):
            o.send(bytes([0x19]) + struct.pack(">II", uid, 0))
        if b:
            o.send(bytes([0xC5]) + _s8(s.acc))
    if b:
        if not getattr(s, "spectator", False) and m < 100000000 and not b.get("sim"):
            LEFT_BATTLE[s.acc] = (province_of(m), __import__("time").time())   # re-join wait (REJOIN_WAIT)
        b["members"].discard(s)
        if b["members"] and BATTLES.get(m) is b:
            check_attackers_gone(b)
        if not b["members"] and BATTLES.get(m) is b and b.get("ghost") and not b.get("won"):
            ghost_resume(b)
        elif not b["members"] and BATTLES.get(m) is b:
            del BATTLES[m]
            log(f"   battle on {m} closed (no participants left)")
            npc_battle_closed(b)
        elif b.get("owner") is s and b["members"]:
            # new commander: the fighter with the highest rank (user 2026-10-22 13:39)
            set_battle_owner(b, battle_best_commander(b, exclude=s), f"commander {s.acc} left")
        if b["members"] and BATTLES.get(m) is b and not b.get("won"):
            try:
                battle_ctx_handoff(s, b)
            except Exception as e:
                log(f"   battle context hand-off error: {e!r}")
    if b:
        s.side_nation = None         # a mercenary's contract ends with the battle
        s.spectator = False
    s.battle = None
    log(f"   {getattr(s, 'acc', '?')} left map {m}{' (' + why + ')' if why else ''}")

_CTX_SKIP = {"w", "acc", "logged_in", "spectator", "battle", "map", "cmd", "side_nation", "battle_gen", "is_ghost",
             "alive_units", "unit_pos", "lost_units", "put_args", "attacks", "_loop", "retreating", "sim_snap"}

def battle_ctx(b):
    """the object a battle's server units are run with (battle_loop, npc_spawn, waves): the Ghost of an NPC battle, the
    stand-in that took over from the player who opened it, else its current owner."""
    if not b:
        return None
    return b.get("ctx") or b.get("ghost") or b.get("owner")

def battle_ctx_handoff(s, b):
    """(2026-10-25 audit A / C2) a player-opened battle ran its loop (aliens, NPC waves, POCs, judge) with the CREATOR's
    session: when he left while others fought on, NPC waves were PUT to him in town, ids came from his new battle, paths
    used his new map.  When the session the loop runs on leaves, a stand-in (npc_world.Ghost, sends go nowhere) takes over
    with the battle's own state (same targets / POCs / alien meta objects) and the loop restarts on it."""
    if b.get("ghost") is not None or b.get("_loop_s") is not s:
        return                                       # NPC battles run on their Ghost / the loop runs on someone else
    ctx = Ghost(b["map"], side_nation(s))
    for k, v in s.__dict__.items():
        if k not in _CTX_SKIP:
            setattr(ctx, k, v)
    ctx.targets = b["targets"]
    ctx.pocs = b["pocs"]
    ctx.battle, ctx.map, ctx.t0, ctx.battle_gen = b, b["map"], b["t0"], 1
    ctx.alive_units, ctx.unit_pos, ctx.attacks = set(), {}, {}
    b["ctx"] = ctx
    run = b.pop("_loop", None)
    if run is not None and not run.done():
        run.cancel()
    spawn(battle_loop(ctx, 1))
    log(f"   battle on {b['map']}: {getattr(s, 'acc', '?')} (who ran it) left - the battle runs on by itself")

def player_rank_level(o):
    """rank of a player = his highest branch level (the rank insignia follows it)."""
    try:
        _ac, a = get_account(getattr(o, "acc", None))
        br = PG.ensure_commander(a.setdefault("commander", {}))["branches"]
        return max(v["level"] for v in br.values())
    except Exception:
        return 0

def battle_best_commander(b, exclude=None):
    """battle commander = the fighting member with the highest rank; the current commander keeps the job on a tie."""
    fight = [o for o in b["members"] if o is not exclude and not getattr(o, "spectator", False) and not o.w.is_closing()]
    if not fight:
        fight = [o for o in b["members"] if o is not exclude]
    if not fight:
        return None
    cur = b.get("owner")
    return max(fight, key=lambda o: (player_rank_level(o), o is cur))

def set_battle_owner(b, new, why=""):
    old = b.get("owner")
    if new is None or new is old:
        return
    b["owner"] = new
    log(f"   battle on {b.get('map')}: commander {getattr(old, 'acc', '?')} -> {new.acc} ({why})")

def join_map(s):
    """after enter_field put s on its map: show the others to s and s to the others."""
    MAP_PEERS.setdefault(s.map, set()).add(s)
    for o in map_peers(s):
        for pk in put_for_others(o, s):              # titles in the viewer's code page
            s.send(pk)
        for pk in put_for_others(s, o):
            o.send(pk)
    try:
        npc_town_sync(s)
    except Exception as e:
        log(f"   npc town sync error: {e!r}")
    n = len(map_peers(s))
    if n:
        log(f"   {s.acc} sees {n} other player(s) on map {s.map}")

def broadcast_lumps(s, msgs, delay=10):
    """lump messages to everybody on s's map (battle: shared clock)."""
    for o in [s] + map_peers(s):
        pk = bytes([0x80, 0, 0]) + struct.pack(">IH", game_time(o) + delay, len(msgs))
        for m in msgs:
            pk += struct.pack(">H", len(m)) + m
        o.send(pk)

async def battle_timer(b):
    await asyncio.sleep(BATTLE_SECONDS)
    if BATTLES.get(b["map"]) is b and not b.get("won"):
        battle_judge(None, "time", b)        # TIME UP: POC majority, ties to the defender; NPC battles: NPC rules

def attack_notice(o, mapid, who=None, nat=None):
    """(19:27) the 'province under attack' notice in the player's language and code page: class-B 0x31 [01][s16]
    (message box) + a system chat line."""
    lang = _mail_lang(o)
    lb = province_label_lang(province_of(mapid), lang)
    by = display_name(who) if who else (nation_name(nat, lang) if nat else "")
    t = {"zh-cn": f"{lb}遭到{by + '的' if by else ''}进攻！在战略地图上右键点该省即可前往防守。",
         "zh-tw": f"{lb}遭到{by + '的' if by else ''}進攻！在戰略地圖上右鍵點該省即可前往防守。"}.get(
        lang, f"{lb} is under attack{' by ' + by if by else ''}! Right-click the province on the strategic map to defend it.")
    # (user 2026-10-25 20:31) NOT class-B 0x31: that is the StarCenter (space center) window's message - the client
    # opened the space center in the middle of a battle.  A red-orange system chat line instead.
    o.send(chat_line(0x0A, t, (255, 110, 90), tr=False))

def notify_defenders(b, attacker):
    """tell the online players of the defending side that their province is attacked (class-B 0x31 [01][s16]).
    attacker: a player session, or the Ghost of an NPC battle (then the attacking nation is named)."""
    dfd = b["defender"]
    ghost = getattr(attacker, "is_ghost", False)
    n = 0
    for o in list(ONLINE):
        if o is attacker or not getattr(o, "logged_in", False) or o.w.is_closing() or getattr(o, "is_ghost", False):
            continue
        if same_side(side_nation(o), dfd) and not (getattr(o, "battle", None) is b):
            try:
                attack_notice(o, b["map"], None if ghost else attacker.acc, b.get("npc_attacker") if ghost else None)
                n += 1
            except Exception as e:
                log(f"   attack notice {getattr(o, 'acc', '?')}: {e!r}")
    log(f"   defenders of nation {dfd} notified: {n} player(s)")

def pull_into_battle(b, mapid, starter=None):
    """user 2026-10-25 19:26 (an NPC attacked province 05 while the player stood in it - nothing happened): when a battle
    opens on a province - by an NPC or by a player - every player who stands on that province map in town mode (not in
    a battle, not leaving) is put into it at once, in battle mode, on his own side (defender of his province, or the
    attackers' side).  The defending side's players elsewhere get the usual notice (0x31)."""
    pulled = 0
    for o in list(ONLINE):
        try:
            if o is starter or not getattr(o, "logged_in", False) or o.w.is_closing() or getattr(o, "battle", None) \
                    or getattr(o, "retreating", False) or getattr(o, "spectator", False) or getattr(o, "is_ghost", False):
                continue
            m = getattr(o, "map", None) or 0
            if not (0 < m < 100000000) or map_kind(m) != "province" or province_of(m) != province_of(mapid):
                continue
            x, y = getattr(o, "hero_pos", None) or (0x200, 0x200)
            log(f"   {o.acc} stands in {mapid} where a battle opened -> enters it (nation {side_nation(o)})")
            _say_lang(o, "你所在的省份开战了，你已进入战斗。", "你所在的省份開戰了，你已進入戰鬥。",
                      "A battle started in the province you are in - you are in it now.", (255, 200, 120))
            enter_field(o, mapid, x, y)
            pulled += 1
        except Exception as e:
            log(f"   pull into battle {getattr(o, 'acc', '?')}: {e!r}")
    if b and b.get("defender") and starter is not None and getattr(starter, "is_ghost", False):
        notify_defenders(b, starter)              # (19:27) NPC attacks are announced like player attacks
    return pulled

def check_attackers_gone(b):
    """a player left: defenders win as soon as no attacker is left on the battle field (battlefield.judge 'leave')."""
    if b and b.get("defender"):
        battle_judge(None, "leave", b)

# TAB_POINTS_PER_POC -> battlefield.py (2026-10-24, the battle rules in one place)

def battle_attacker_nation(b, members=()):
    """the attacking nation of battle b (0 = none / aliens only)."""
    if not b:
        return 0
    dfd = b.get("defender") or 0
    if b.get("npc_attacker"):
        return int(b["npc_attacker"])
    cands = [side_nation(o) for o in members]
    cands += [tg.get("nation") for tg in (b.get("targets") or {}).values() if tg.get("npc") is not None]
    for c in cands:
        if c and not (dfd and same_side(c, dfd)):
            return int(c)
    return 0

def build_score_table(s):
    """server 0xFC = COMBAT RANKING window (TAB, parser 004b4720, rows 004b46a0).
    u8 ATTACKER NATION, u8 DEFENDER NATION, u8 n rows {s8 HERO, u8 FACTION (nation id), u16 POINT, u16 KILL,
    u8 Avg Kill Lvl, u8 POC, u8 REINS}.
    user 2026-10-24 12:46 (TOTAL ATTACKER 0 / DEFENDER 0, no NPC): the two header bytes are NOT point totals - the
    client stores them at window +0x2e4 / +0x2e8 and for every row whose FACTION equals one of them adds 1 to
    +0x2ec / +0x2f0, the TOTAL ATTACKER / DEFENDER numbers (= how many commanders fight on each side).  We sent the point
    totals (no nation id) -> always 0.  Rows of allied nations are not counted by the client (it compares one id).
    NPC commanders of the battle get rows like players (points = levels of their kills, REINS = waves sent).
    POINT = sum of the killed enemies' levels + TAB_POINTS_PER_POC per POC captured (our rule)."""
    b = getattr(s, "battle", None)
    members = [o for o in b["members"] if not o.w.is_closing() and not getattr(o, "spectator", False)] if b else [s]
    dfd = int((b or {}).get("defender", 0) or 0)
    att = battle_attacker_nation(b, members)
    rows = []
    for o in members[:40]:
        st = getattr(o, "battle_stats", None) or {}
        kills = sum((st.get("kills") or {}).values())
        rows.append((_s8(o.acc), side_nation(o), st.get("kill_lv", 0), kills, st.get("pocs", 0),
                     getattr(o, "reinforce_count", 0)))
    if b:
        seen = {}
        for tg in (b.get("targets") or {}).values():
            if tg.get("npc") is not None:
                seen.setdefault(tg["npc"], tg.get("nation"))
        # (audit C8) NPC commanders whose units are all gone keep their row (kills / REINS), like players who are wiped out
        for i in list(b.get("npc_ids") or []) + list((b.get("npc_stats") or {}).keys()):
            seen.setdefault(i, None)
        for i, nat in list(seen.items())[:max(0, 40 - len(rows))]:
            n_ = npc_state()["npcs"].get(str(i))
            if n_ is None:
                continue
            st = (b.get("npc_stats") or {}).get(i) or {}
            rows.append((_s8(n_["name"]), nat or n_["nation"], st.get("kill_lv", 0), st.get("kills", 0),
                         st.get("pocs", 0), st.get("reins", 0)))
    d = bytes([0xFC, att & 0xFF, dfd & 0xFF, len(rows)])
    for nm, nat, klv, kills, pocs, reins in rows:
        pts = klv + TAB_POINTS_PER_POC * pocs
        d += nm + bytes([int(nat or 0) & 0xFF]) + struct.pack(">HH", min(pts, 65535), min(kills, 65535)) \
            + bytes([min(klv // kills if kills else 0, 255), min(pocs, 255), min(reins, 255)])
    return d

def request_join(s, mapid, x, y, watch=False, side=None):
    """s wants to enter a map with a running battle commanded by someone else -> ask him (0x24).
    Only players of the commander's side need his permission; the enemy side (defenders) enters directly."""
    b = BATTLES.get(mapid)
    cmdr = b and b.get("owner")
    if not JOIN_PERMISSION or not cmdr or cmdr is s or cmdr.w.is_closing():
        return False
    mine = side if side else getattr(s, "cmd", {}).get("nation", 0)
    if not watch and not same_side(mine, side_nation(cmdr)):
        log(f"   {s.acc} (nation {mine}) joins the battle on {mapid} on the other side - no permission needed")
        return False
    typ = 13 if watch else (4 if side else 1)
    # FORCE OPEN (client 0x56, a council member): the commander's permission is not needed any more
    # (client text ksForceOpen: "This battle has been Forced Opened by a council member. You can automatically join")
    if b.get("force_open") and not watch:
        log(f"   join request: {s.acc} -> battle on {mapid}: FORCE OPENED by {b['force_open']} -> enters directly")
        return False
    PENDING_JOIN[s.acc] = (s, mapid, x, y, cmdr, watch, side)
    # Ctrl+F7 battle permission (client 0x44 [u8 mode], window radio buttons 005a68a0): 1 = allow everybody,
    # 2 = refuse everybody, 0 = ask me (manual, the 0x24 dialog below)
    mode = getattr(cmdr, "join_mode", 0)
    if mode in (1, 2):
        log(f"   join request: {s.acc} -> battle on {mapid}: commander {cmdr.acc} has Ctrl+F7 mode {mode} "
            f"-> {'allowed' if mode == 1 else 'refused'} automatically")
        answer_join(cmdr, typ + (2 if mode == 1 else 1), s.acc)
        return True
    cmdr.send(bytes([0x24, typ]) + _s8(s.acc) + _s8(""))
    log(f"   join request: {s.acc} -> battle on {mapid} (commander {cmdr.acc}), waiting for permission")
    async def timeout(acc=s.acc):
        await asyncio.sleep(JOIN_TIMEOUT)
        if acc in PENDING_JOIN:
            js, m, jx, jy, _c, w, sd = PENDING_JOIN.pop(acc)
            log(f"   join request of {acc}: no answer -> accepted")
            if not js.w.is_closing():
                js.side_nation = sd
                enter_field(js, m, jx, jy, watch=w)
    spawn(timeout())
    return True

def answer_join(cmdr, typ, name):
    """client 0x20 [type][s8 name]: type+2 accept (3,6,10,15) / type+1 reject (2,5,9,14)."""
    p = PENDING_JOIN.pop(name, None)
    if not p:
        return
    js, m, jx, jy, _c, w, sd = p
    if typ in (3, 6, 10, 15):
        log(f"   join request of {name}: ACCEPTED by {cmdr.acc}")
        js.side_nation = sd
        enter_field(js, m, jx, jy, watch=w)
    else:
        log(f"   join request of {name}: REJECTED by {cmdr.acc}")
        _say_lang(js, "战场指挥官拒绝了你的加入。", "戰場指揮官拒絕了你的加入。",
                  "The Battlefield Commander rejected your entrance.", (255, 150, 120))   # (20:31) not 0x31 = StarCenter

# ---- REINFORCEMENT SQUADS (F7) ----------------------------------------------------------------------------------
# Units beyond the deploy limit (Tactics // 20 + 6) stay in RESERVE.  F7 in battle = client 0x19 [00] (005b4cb0):
# after REINFORCE_COOLDOWN s the next squad (up to the deploy limit of free slots) enters with class-B 0x50
# "Delayed Put" [u32 lock-step time][PUT body] (004ad4e0) on every participant at the same frame.  Otherwise the
# client is told the wait: class-B 0x5b [02][00][u16 s] "You can reinforce after %d seconds" (00524400).
# REINFORCE_COOLDOWN -> battlefield.py (2026-10-24, the battle rules in one place)
REINFORCE_DELAY = 300            # lock-step frames (1/100 s) until the squad appears

def arrival_notice():
    """'Your units will enter the battle in %d seconds.' (ntt.dat ksUnitArriveTime) as a system chat line.
    The client's own box for it (class-B 0x52 -> mode 1) shows the HERO'S route time (005e94f0), which is 0 for a
    squad that is put directly, so the server tells the real delay instead."""
    return chat_line(0x0A, f"Your units will enter the battle in {max(1, round(REINFORCE_DELAY / 100))} seconds.")

def reinforce(s):
    import time
    if not getattr(s, "battle", None) or getattr(s, "spectator", False):
        return
    wait = int(REINFORCE_COOLDOWN - (time.time() - getattr(s, "last_reinforce", 0)))
    # (user 2026-10-24 20:18: after units retreated through a portal, F7 could not pick the units to send in again)
    # F7 now opens the DEPLOY WINDOW: the player chooses; after OK (client 0x19 [01], set_deploy) the chosen units that
    # are not on the field - retreated or still in reserve, alive - enter like a reinforcement squad (reinforce_chosen).
    if wait > 0:
        s.send(bytes([0x5B, 2, 0]) + struct.pack(">H", wait))
        log(f"   F7 reinforcement: wait {wait} s")
        return
    if F7_CHOOSE and reinforce_candidates(s):
        s.f7_choose = True
        s.send(bytes([0x1C, 0]))
        log(f"   F7 reinforcement: deploy window ({len(reinforce_candidates(s))} unit(s) off the field)")
        return
    if not getattr(s, "reserve", None):
        s.send(bytes([0x5B, 2, 0]) + struct.pack(">H", 0))
        log("   F7 reinforcement: no units in reserve")
        return
    if wait > 0:
        s.send(bytes([0x5B, 2, 0]) + struct.pack(">H", wait))
        log(f"   F7 reinforcement: wait {wait} s")
        return
    cmd = PG.ensure_commander(get_account(s.acc)[1].setdefault("commander", {}))
    room = max(0, PG.deploy_limit(cmd) - len(s.alive_units))
    squad, s.reserve = s.reserve[:room], s.reserve[room:]
    if not squad:
        s.send(bytes([0x5B, 2, 0]) + struct.pack(">H", int(REINFORCE_COOLDOWN)))
        log("   F7 reinforcement: division at the deploy limit")
        return
    s.last_reinforce = time.time()
    s.reinforce_count = getattr(s, "reinforce_count", 0) + 1         # TAB: REINS
    put_squad(s, squad)
    s.send(arrival_notice())
    s.send(bytes([0x5B, 2, 0]) + struct.pack(">H", int(REINFORCE_COOLDOWN)))
    log(f"   F7 reinforcement: squad {[u[0] for u in squad]} enters, {len(s.reserve)} left in reserve")

F7_CHOOSE = True

def reinforce_candidates(s):
    """living units of the account that are not on the battle map (retreated through a portal or in reserve)."""
    _accs, a = get_account(s.acc)
    on = set(getattr(s, "alive_units", set()) or ())
    lost = getattr(s, "lost_units", set()) or set()
    return [u for u in a["units"] if hp_alive(u) and u["uid"] not in on and u["uid"] not in lost]

def reinforce_chosen(s):
    """after the F7 deploy window: the chosen (slot > 0) off-field units enter, up to the free deploy places."""
    import time
    s.f7_choose = False
    if not getattr(s, "battle", None) or getattr(s, "spectator", False):
        return
    accs, a = get_account(s.acc)
    cmd = PG.ensure_commander(a.setdefault("commander", {}))
    room = max(0, PG.deploy_limit(cmd) - len(getattr(s, "alive_units", ()) or ()))
    cand = {u["uid"]: u for u in reinforce_candidates(s)}
    pick = sorted((u for u in cand.values() if int(u.get("deploy", 0) or 0)), key=lambda u: int(u["deploy"]))[:room]
    if not pick:
        _say_lang(s, "没有选到可以进场的单位（已在战场上或已阵亡的不算），或部队已满。",
                  "沒有選到可以進場的單位（已在戰場上或已陣亡的不算），或部隊已滿。",
                  "No unit to send in (units on the field or destroyed do not count), or the division is full.",
                  (255, 200, 120))
        log(f"   F7 chosen reinforcement: nothing to send (room {room})")
        return

    _cur = lambda u: hp_battle_en(cmd, u)               # (sgs/unit_hp.py)
    squad = [(u["uid"],) + unit_kind(u["chassis"])[1:] + _cur(u) + (unit_stats9(u), unit_speed(u)) for u in pick]
    s.reserve = [r for r in getattr(s, "reserve", []) if r[0] not in {q[0] for q in squad}]
    s.last_reinforce = time.time()
    s.reinforce_count = getattr(s, "reinforce_count", 0) + 1
    put_squad(s, squad)
    s.send(arrival_notice())
    s.send(bytes([0x5B, 2, 0]) + struct.pack(">H", int(REINFORCE_COOLDOWN)))
    log(f"   F7 chosen reinforcement: {[q[0] for q in squad]} enter (room {room})")

def purge_dead(s):
    """user 2026-10-25 11:21: a player's destroyed unit stays on every client as a corpse / green minimap dot.  When new units
    enter (F7, Reinforce, 0x53) the corpses of this player's destroyed units are removed (server 0x19 [uid][0]) from
    his own screen and from the other members'."""
    done = s.__dict__.setdefault("purged_dead", set())
    alive = getattr(s, "alive_units", set())
    n = 0
    for uid in list(getattr(s, "lost_units", set()) or ()):
        if uid in done or uid in alive:
            continue
        done.add(uid)
        pk = bytes([0x19]) + struct.pack(">II", uid, 0)
        s.send(pk)
        for o in map_peers(s):
            o.send(pk)
        n += 1
    if n:
        log(f"   {n} destroyed unit(s) of {getattr(s, 'acc', '?')} removed from the clients (new units enter)")

def put_squad(s, squad):
    try:
        purge_dead(s)
    except Exception as e:
        log(f"   purge_dead error: {e!r}")
    # (the squad is stamped at send time: delayed_put)
    x0, y0 = getattr(s, "entry_pos", None) or next(iter(s.unit_pos.values()), (0x400, 0x400))
    _accs, a = get_account(s.acc)
    by = {u["uid"]: u for u in a["units"]}
    # (user 2026-10-24 23:51: after a retreat and a new division the selected units showed no status in the side panels)
    # the slot is the unit's place in the client's division panels (0..11): it was len(put_args) + i, and put_args
    # keeps the units that left -> slots 12, 13 ... had no panel.  Now: the lowest slots no unit on the field uses.
    taken = {(s.put_args.get(u_) or {}).get("slot") for u_ in (s.alive_units or ()) if u_ not in {q[0] for q in squad}}
    free_slots = [k for k in range(64) if k not in taken]
    for i, (uid, kind, cls, hp, en, st9, spd) in enumerate(squad):
        x, y = x0 + 0x30 * (i % 4), y0 + 0x30 * (i // 4)
        abil = unit_abilities(by[uid]) if uid in by else ABILITY_ATTACK
        slot = free_slots[i] if i < len(free_slots) else len(s.put_args) + i
        s.put_args[uid] = {"x": x, "y": y, "kind": kind, "cls": cls, "hp": hp, "en": en, "st9": st9, "slot": slot,
                           "hpmax": unit_full_hp(s, by.get(uid)) or hp,
                           "sight": UNIT_SIGHT.get(uid) or (unit_sight(st9) if st9 else None), "spd": spd, "abil": abil,
                           "label": battle_unit_name(by.get(uid))}
        body = build_put_unit(uid, s.put_args[uid]["label"], s.acc, x, y, kind, cls, side_nation(s), hp=hp, energy=en, stats9=st9,
                              hp_max=s.put_args[uid]["hpmax"],
                              slot=slot, sight=UNIT_SIGHT.get(uid) or (unit_sight(st9) if st9 else None), speed=spd, abilities=abil)
        s.put_args[uid]["enter_t"] = delayed_put(s, body, still=lambda _u=uid: _u in s.alive_units)
        s.unit_pos[uid] = (x, y)
        s.unit_cmb[uid] = (st9 or [100] * 9, spd or 100)
        s.alive_units.add(uid)
        s.__dict__.setdefault('purged_dead', set()).discard(uid)
        if uid not in s.battle_stats["units"]:
            s.battle_stats["units"].append(uid)

# ---- BATTLE CONTROL dialog (class-B 0x1e, 004af1e0 'fldbctrl') ---------------------------------------------------
# Sent to a hero arriving at a province where a battle is running.  LAYOUT (CONFIRMED 2026-10-24 from 004af1e0,
# list drawer 00408630, nation table 00551ec0, commander nation setter 004ee830):
#   u32 map, u8, u8, u32 DEFENDER nation, s8 title (<= 0x100),
#   u8 n x { s8 name (<= 0x40, the list shows 18 chars), u32 NATION of the participant, u32 SIDE nation },
#   u8 WAIT seconds, u8 CAN ENTER (0 = "This battle is full"), ...
# - SIDE: group(side) == group(defender) in the alliance groups of the 0x0F table -> DEFENDER list, else ATTACKER.
# - NATION: looked up in the 0x0F nation table (00551ec0) for the name colour (record +0x10a).  The DEFENDER drawer
#   skips an id it cannot find, the ATTACKER drawer does not check (00408749) -> access violation.  This was the
#   10-23 crash: the server sent the commander's hero uid / NPC ids 40000+ here instead of a nation id.
# - NATION == the client's own nation (commander +0x3ac, set from 0x15) -> "my nation already fights here": after the
#   button the client sends 0x20 [01][u32 map] instead of 0x1b [01][u32 map][x][y] (same join, server side).
# - Own nation 5 (mercenary) gets the side-choice buttons (0x20 [04][map][side]).
# The client answers ATTACK / ASSIST = client 0x1b [01|02][u32 map][u16 x][u16 y] (+ 0x48 [u16 0]).
BATTLE_CTRL_DIALOG = True
BATTLE_DIALOG_EXTRA = True        # (2026-10-24) NPC commanders + the alien garrison in the lists (valid nation ids now)
BATTLE_CTRL_TIMEOUT = 30
PENDING_ARRIVAL = {}             # account -> (map, x, y)

def _npc_row_name(s, name):
    """an NPC in the battle dialog lists: Chinese clients see '杨星辰' (bytes in their code page)."""
    lg, en = session_lang_enc(s)
    t = NP.disp(name, lg)
    if t == name:
        return name
    try:
        return t.encode(en)
    except Exception:
        return name

def send_battle_control(s, mapid, x, y):
    b = BATTLES.get(mapid)
    if not b:
        return False
    parts = [o for o in b["members"] if not o.w.is_closing()]
    d = bytearray([0x1E]) + struct.pack(">I", mapid) + bytes([0, 0]) + struct.pack(">I", b.get("defender", 0))
    # (user 2026-10-26 12:28) FIELD ID showed the raw id ("Battle for province 00006"), not the number the strategic map
    # draws on the province -> the same label as everywhere else, in the player's language and code page
    _lg, _en = session_lang_enc(s)
    try:
        _lb = province_label_lang(mapid, _lg) if (province_number(mapid) or mapid in CAPITALS.values()) \
            else f"{mapid % 100000:05d}"
    except Exception:
        _lb = f"{mapid % 100000:05d}"
    _ttl = {"zh-cn": f"{_lb}的战斗", "zh-tw": f"{_lb}的戰鬥"}.get(_lg, f"Battle for {_lb}")
    _tb = _ttl.encode(_en, "replace")[:250]
    d += bytes([len(_tb)]) + _tb + bytes([len(parts)])
    cnt_at = len(d) - 1
    # CONFIRMED 2026-10-21 (004af1e0 + dialog 004089f0 / 004082b0 / 004081e0):
    #   participant = s8 name, u32 commander ID (== own id -> "already in this battle"), u32 SIDE nation (same
    #   alliance group as the defender -> DEFENDER list, else ATTACKER list);
    #   then u8 WAIT seconds ("The dust is still settling ... after %d seconds", dialog +0x328 = now + s*100)
    #   and u8 CAN ENTER (0 -> "This battle is full ...", dialog +0x324).  Before: side/0, wait 30, can-enter 0.
    for o in parts:
        d += _s8(o.acc) + struct.pack(">II", (getattr(o, "cmd", {}) or {}).get("nation", 0) or 0, side_nation(o) or 0)
    # NPC commanders with units on this battle field, and the alien garrison (user 2026-10-22 22:17: the lists were empty)
    extra = []
    # (2026-10-24) NPC commanders are listed like players: their own nation (a 0x0F entry -> coloured name) and their
    # side.  Only commanders that still have units on the field; the alien garrison as one line of nation 0 (the
    # 'Neutral' entry, sent after login).  A participant whose nation the client would not find is never sent.
    known = {n[0] for n in NATIONS} | {0}
    tgs = (b.get("targets") or {}).values()
    alive_npc = {tg.get("npc") for tg in tgs if tg.get("npc") is not None and tg.get("hp", 0) > 0
                 and not tg.get("withdraw")} if BATTLE_DIALOG_EXTRA else set()
    for i in sorted(alive_npc, key=lambda i: str(i)):
        n_ = npc_state()["npcs"].get(str(i))
        if n_ is not None and n_["nation"] in known:
            extra.append((_npc_row_name(s, n_["name"]), n_["nation"], n_["nation"]))
    if BATTLE_DIALOG_EXTRA and any(tg.get("npc") is None and tg.get("hp", 0) > 0 and not tg.get("hive") for tg in tgs):
        lang, enc = session_lang_enc(s)
        extra.append(({"zh-cn": "外星驻军", "zh-tw": "外星駐軍"}.get(lang, "Aliens").encode(enc, "replace"), ALIEN_NATION,
                      ALIEN_NATION))                     # bytes: already in the receiver's code page
    # (user 2026-10-24 22:28: DEFENDER was empty) the defender's NPCs were not on the field yet (marching in / held in
    # the province) -> list the defending NPC commanders of that province, else the defending nation itself
    _dn = b.get("defender", 0) or 0
    if BATTLE_DIALOG_EXTRA and _dn and _dn in known and _dn != ALIEN_NATION \
            and not any(same_side(side_nation(o) or 0, _dn) for o in parts) \
            and not any(same_side(e[2], _dn) for e in extra if e[2] != ALIEN_NATION):
        _pv = province_of(mapid) if mapid < 100000000 else None
        _dl = []
        for _n in npc_active():
            if _n.get("nation") != _dn:
                continue
            _loc, _tg = npc_location(_n)
            _tk = _n.get("task") or {}
            if _pv and (_loc == _pv or (_tk.get("target") and province_of(_tk["target"]) == _pv)):
                _dl.append((_npc_row_name(s, _n["name"]), _dn, _dn))
        extra[:0] = _dl[:8]
    extra = extra[:max(0, 40 - len(parts))]
    if extra:
        d[cnt_at] = len(parts) + len(extra)              # the u8 participant count written above
        for name, cid, nat in extra:
            d += (bytes([len(name[:60])]) + name[:60] if isinstance(name, bytes) else _s8(name)) + struct.pack(">II", cid, nat)
    full = len(parts) >= 10
    wait = min(255, rejoin_wait(s, mapid))
    d += bytes([wait, 0 if full else 1])
    PENDING_ARRIVAL[s.acc] = (mapid, x, y)
    s.send(bytes(d))
    log(f"   battle control dialog (0x1e) for {mapid} -> {s.acc} ({len(parts)} participant(s)"
        f"{' + ' + ', '.join(f'{e[0]!s}/{e[1]}' for e in extra) if extra else ''})")
    return True


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
        _lang, _enc = session_lang_enc(s)
        name = next((nation_name(n[0], _lang) for n in NATIONS if CAPITALS.get(n[0]) == pid), f"P{(pid % 10000) // 100}-{pid % 100}")
        nb = name.encode(_enc, "replace")[:26] + b" %02d" % province_number(pid)       # last 2 chars = map number
        busy = BATTLES.get(SIM_BASE + pid)                           # (19:59) simulations run on their own map ids
        nsim = len(busy["members"]) if busy and busy.get("sim") else 0
        if pid in caps:
            fight = bytes([0])                                       # capital: no simulation
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
    """mapid = the province (or its simulation id).  The simulation runs on SIM_BASE + province: apart from any real
    battle there, invisible on the strategic map (user 2026-10-27 19:59)."""
    pid = province_of(real_map(mapid)) if real_map(mapid) < 100000000 else None
    if not pid or pid in CAPITALS.values() or map_kind(pid) != "province":
        s.send(chat_line(0x0A, "Simulations cannot be held in a capital.", (255, 200, 80)))
        return
    mapid = SIM_BASE + pid
    B = BATTLES.get(mapid)
    s.sim_board = False
    if B:
        x, y = getattr(B.get("owner"), "entry_pos", None) or sim_arrival(mapid, s)
        # (user 2026-10-26 12:42) players of different (not allied) nations pick the same province and fight each
        # other: the newcomer starts at the spawn spot farthest from the other side's arrival, not on top of it
        try:
            _me = side_nation(s)
            _foes = [o for o in B["members"] if not getattr(o, "spectator", False) and not o.w.is_closing()
                     and not same_side(side_nation(o), _me)]
            if _foes and not watch:
                _spots = [tuple(p) for p in SPAWN_SPOTS.get(alien_context(s, mapid)[3] or "", [])]
                _ref = getattr(B.get("owner"), "entry_pos", None) or (x, y)
                if _spots:
                    x, y = max(_spots, key=lambda p: (p[0] - _ref[0]) ** 2 + (p[1] - _ref[1]) ** 2)
                    log(f"   SIMULATION: {s.acc} (nation {_me}) faces {[o.acc for o in _foes]} - starts at ({x},{y})")
        except Exception as e:
            log(f"   sim versus start error: {e!r}")
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

def arrive_battle(s, mapid, watch=False, side=None):
    """the player chose to take part (or to watch / offer his service): ask the battle commander."""
    x, y = PENDING_ARRIVAL.pop(s.acc, (mapid, 0x800, 0x800))[1:] if s.acc in PENDING_ARRIVAL else (0x800, 0x800)
    if mapid not in BATTLES:
        enter_field(s, mapid, x, y, watch=watch)
        return
    if not request_join(s, mapid, x, y, watch=watch, side=side):
        s.side_nation = side
        enter_field(s, mapid, x, y, watch=watch)

# ---- MERCENARIES (nation 5 is special-cased by the client; client 0xd6 [u8 on] = become / retire, 005e0d80) ----
# A mercenary keeps his faction but may offer his service to ANY battle (client 0x20 [04][u32 map][u32 side]); he
# then fights for that side (PUT nation, POC capture) and earns MERCENARY_BONUS_PCT extra resources on victory.
# MERCENARY_BONUS_PCT -> battlefield.py (2026-10-24, the battle rules in one place)

# ---- LATE-JOIN SNAPSHOT (EXPERIMENTAL) ---------------------------------------------------------------------------
# server 0x0E [06][u32 T] asks a participant for its world state -> client 0x1d [u16 zlen][zlib(...)] (004a9890);
# class-B 0x22 [u16 zlen][zlib] rebuilds it on a joiner (004b0a20).  Whether the leading u32 T must be stripped is
# not known, so the relay is OFF: joiners get the aliens / players re-PUT instead (works).  Snapshots are logged.

# ---- BATTLE SNAPSHOTS FOR THE AI (claude/NPC_BATTLE_AI_ARCH.md P1, battle_snap.py) ---------------------------------------
# Every SNAP_PERIOD s one live participant of a battle with server-owned units (NPCs / aliens) is asked for its world
# dump (0x0E [06][u32 0]: T = 0 does not touch its clock).  The answer gives the TRUE positions / HP of every unit: the
# AI stops guessing.  A dump that does not match the battle (layout doubt) is only logged; after SNAP_MAX_BAD such
# dumps the battle stops asking.
import battle_snap as BSNAP
# SNAP_ON, SNAP_PERIOD, SNAP_MAX_BAD, SNAP_FRESH -> battlefield.py (2026-10-24, the battle rules in one place)

def snap_requester(B):
    own = B.get("owner")
    live = [o for o in _live(B) if not getattr(o, "spectator", False)]
    if own in live:
        return own
    if not live:
        # (2026-10-25 audit E) only watchers on the map: the simulation pauses for them (their clients run the battle),
        # so a watcher's client must report the deaths, or nothing ever dies on the server
        live = [o for o in _live(B) if not getattr(o, "is_ghost", False)]
    return live[0] if live else None

SNAP_ACCEPT = 10.0          # s after the request a snapshot is accepted (from the client that was asked)

async def snapshot_cycle():
    await asyncio.sleep(5)
    while True:
        try:
            now = time.time()
            if SNAP_ON:
                for pid, B in list(BATTLES.items()):
                    if B.get("won") or B.get("snap_bad", 0) >= SNAP_MAX_BAD or now - B.get("snap_req", 0) < SNAP_PERIOD:
                        continue
                    if not any(t >= 50001 for t in (B.get("targets") or {})):
                        continue                         # players only: nothing for the AI
                    o = snap_requester(B)
                    if o is None or not getattr(o, "battle_mode", 0):
                        continue
                    B["snap_req"], B["snap_who"] = now, o
                    o.send(bytes([0x0E, 6]) + struct.pack(">I", 0), quiet=True)
        except Exception as e:
            log(f"   snapshot cycle error: {e!r}")
        await asyncio.sleep(0.5)

def apply_snapshot(s, body):
    """client 0x1d: true positions / HP of the units -> the battle's server-owned units and the players' unit positions."""
    B = getattr(s, "battle", None)
    snap = BSNAP.parse(body)
    if B is None:
        return
    if snap is None:
        B["snap_bad"] = B.get("snap_bad", 0) + 1
        log(f"   snapshot from {s.acc}: unreadable ({len(body)} B, bad {B['snap_bad']})")
        return
    # (2026-10-25 audit F) only the answer of the client that was asked, within SNAP_ACCEPT s, once
    if B.get("snap_who") is not s or time.time() - B.get("snap_req", 0) > SNAP_ACCEPT:
        log(f"   ANTI-CHEAT: snapshot from {getattr(s, 'acc', '?')} not requested - ignored")
        audit("snapshot_unrequested", getattr(s, "acc", None), map=B.get("map"))
        return
    B["snap_who"] = None
    U = snap["units"]
    targets = B.get("targets") or {}
    players = {u: o for o in _live(B) for u in getattr(o, "alive_units", set())}
    known = set(targets) | set(players)
    hit = [u for u in U if u in known]
    if U and len(hit) < 0.6 * len(U):
        B["snap_bad"] = B.get("snap_bad", 0) + 1
        log(f"   snapshot from {s.acc}: {len(U)} unit(s), only {len(hit)} known - layout doubt, not applied (bad {B['snap_bad']})")
        return
    now = time.time()
    err, nerr = 0.0, 0
    for uid in hit:
        r = U[uid]
        p = (float(r["x"]), float(r["y"]))
        tg = targets.get(uid)
        if tg is not None:
            if tg.get("pos"):
                old = _npc_est_pos(tg, now)
                err += AL.dist(old, p); nerr += 1
            snapshot_pos(tg, p, now)                          # (unit_orders: walk re-based, run-away check)
            tg["hp_c"] = r["hp"]
        else:
            o = players[uid]
            o.unit_pos[uid] = (r["x"], r["y"])
            hp_note(o, uid, r["hp"])                         # (sgs/unit_hp.py) newest battle HP
    # DEAD ON THE CLIENT (user 2026-10-24 04:30: dead NPC units stayed as red dots on the minimap and the battle did
    # not end): nobody reports the death of an NPC unit when no client owns it.  The world dump is the truth: a
    # server unit with HP 0 in it, or missing from two dumps in a row, is dead -> removed here, 0x23 to everybody
    # (clears the dot), kill credited to its last hitter, then the usual end-of-battle check.
    gone = []
    for uid, tg in list(targets.items()):
        r = U.get(uid)
        first = tg.setdefault("snap_first", now)
        if r is not None:
            tg.pop("snap_miss", None)
            if r["hp"] <= 0:
                gone.append((uid, "HP 0 in the client"))
        elif tg.get("npc") is not None and not tg.get("withdraw") and now - first > SNAP_FRESH * 2:
            tg["snap_miss"] = tg.get("snap_miss", 0) + 1
            if tg["snap_miss"] >= 2:
                gone.append((uid, "gone from the client"))
    for uid, why in gone:
        if uid not in targets:
            continue
        log(f"   snapshot: {targets[uid].get('name') or 'unit'} {uid} is dead on the client ({why}) - removed")
        send_lumps(s, [bytes([0x23]) + struct.pack(">I", uid)])
        alien_died(s, uid, confirmed=True)
    B["snap_t"], B["snap_n"] = now, B.get("snap_n", 0) + 1
    if B["snap_n"] <= 3 or B["snap_n"] % 40 == 0:
        log(f"   snapshot #{B['snap_n']} from {s.acc} on {B.get('map')}: {len(U)} unit(s), {len(hit)} known, "
            f"estimate error {err / max(1, nerr):.0f} px over {nerr} server unit(s)")

# ---- POC capture (server side) ---------------------------------------------------------------------------------
# The client simulates the capture itself (0048f340) but never reports it, so the server runs the same rule on the
# unit positions the client reports (lumps 0x18 / 0x16) and is authoritative: it sends 0x49 on every state change
# and ends the battle as a VICTORY (province captured) once every POC belongs to the player's alliance.
# POC_RADIUS -> battlefield.py (2026-10-24, the battle rules in one place)
# POC_RATE -> battlefield.py (2026-10-24, the battle rules in one place)
                           # drops 5 per simulation step, steps advance the game clock by 5 at 100 units/s ->
                           # 100 per second (a 20000 POC took 200 s; the old 500/s assumption made the server's
                           # 3x fallback fire first, at 120 s).
# POC_TICK -> battlefield.py (2026-10-24, the battle rules in one place)
POC_MIN_FRACTION = 0.8     # anti-cheat: a client POC report needs >= 80 % of the capture time seen by the server

def same_side(a, b):
    return a == b or (a, b) in NATION_ALLIES or (b, a) in NATION_ALLIES

def join_replay(s, B):
    """(2026-10-25 audit C1/S2) a player who joins a running battle got only a bare PUT of every server unit: no current
    order, no cloak / Detector state, no POC capture progress - his client simulated those units differently from the
    others' (desync).  After the PUTs (and the clock 0x0E) he gets ONE lump, stamped like every relayed order
    (game_time + RELAY_DELAY), with what each unit is doing now, and the state of every POC."""
    now = time.time()
    T = B.get("targets") or {}
    msgs = []
    for tid, tg in T.items():
        if not tg.get("put") or tg.get("hp", 1) <= 0:
            continue
        if tg.get("cloaked"):
            msgs.append(bytes([0x30]) + struct.pack(">I", tid) + bytes([15, 1]))
        if tg.get("detect_on"):
            msgs.append(bytes([0x30]) + struct.pack(">I", tid) + bytes([43, 1]))
        for act, on in (tg.get("modes") or {}).items():     # bombArd / Flak / Booster / Energy / Shield switched on
            if on:
                msgs.append(bytes([0x30]) + struct.pack(">I", tid) + bytes([act, 1]))
        tgt = tg.get("target")
        if tg.get("state") == "combat" and tgt is not None and not tg.get("chase"):
            msgs.append(attack_lump(tid, tgt))            # (chasing units: their walk below)
        elif tg.get("mv") and now < tg["mv"][3]:
            q = tg["mv"][1]
            msgs.append(_alien_order_move(tid, q[0], q[1]))
    if msgs:
        for i in range(0, len(msgs), 60):
            part = msgs[i:i + 60]
            pk = bytes([0x80, 0, 0]) + struct.pack(">IH", game_time(s) + RELAY_DELAY, len(part))
            for m in part:
                pk += struct.pack(">H", len(m)) + m
            s.send(pk)
    for pid, p in (B.get("pocs") or {}).items():
        send_poc_state(s, pid, p)
    # repeats of these orders must not be dropped by the order gate for the others' sake: forget what was last sent
    B.pop("_ord_last", None)
    log(f"   join replay for {getattr(s, 'acc', '?')}: {len(msgs)} order(s)/state(s), {len(B.get('pocs') or {})} POC(s)")

def send_poc_state(s, pid, p):
    s.send(bytes([0x49]) + struct.pack(">IHIB", pid, max(0, int(p["progress"])) & 0xFFFF, p["owner"],
                                       1 if p["capturing"] else 0))

def poc_step(s, b):
    """one POC_TICK of the server-side POC capture (battle_loop).  -> True when the battle got decided."""
    pocs = b["pocs"] if b is not None else s.pocs      # the creator may leave: keep the battle's own POCs
    members = battle_members(s) if b is None else [o for o in b["members"] if not o.w.is_closing()]
    for pid, p in pocs.items():
        on = []          # (session, uid) of units standing on the POC
        for o in members:
            for u in getattr(o, "alive_units", set()):
                if u in getattr(o, "camo", set()) or u in getattr(o, "no_capture", set()) or u in CARRIED:
                    continue
                ux, uy = o.unit_pos.get(u, (-999, -999))
                if abs(ux - p["x"]) <= POC_RADIUS and abs(uy - p["y"]) <= POC_RADIUS:
                    on.append((o, u))
        if b is not None:                      # NPC capturers standing on the POC (npc_ai sets on_poc)
            for _tid, _tg in list(b["targets"].items()):
                if _tg.get("npc") is not None and _tg.get("on_poc") == pid and _tg["hp"] > 0:
                    on.append((NpcSide(_tg), _tid))
        cap = [(o, u) for o, u in on if not same_side(side_nation(o), p["owner"])]
        if cap:
            who = cap[0][0]
            nat = side_nation(who)
            if p["capturing"] and p.get("cap_nat") is not None and not same_side(p.get("cap_nat"), nat):
                p["capturing"] = False               # (audit I) another nation took over the capture: it starts anew
            if not p["capturing"]:
                p["capturing"], p["progress"] = True, p["strength"]   # client does the same itself
                p["cap_t"], p["cap_nat"] = time.time(), nat               # anti-cheat: 0x5a time check
                log(f"   POC {pid}: capture started by {[u for _o, u in cap]} (strength {p['strength']})")
            else:
                p["progress"] -= POC_RATE * POC_TICK
                # the CLIENT decides when its capture animation is complete and reports it (0x5a);
                # the server only takes over if no report came after 3x the expected time
                if p["progress"] < (-0.15 if getattr(who, "is_npc", False) else -2) * p["strength"]:
                    p["owner"], p["progress"], p["capturing"] = nat, 0, False
                    for o in members:
                        send_poc_state(o, pid, p)
                    log(f"   POC {pid}: CAPTURED by nation {nat} ({who.acc})")
                    if not getattr(who, "is_npc", False):
                        _bst = getattr(who, "battle_stats", None)
                        if _bst is not None:
                            _bst["pocs"] = _bst.get("pocs", 0) + 1
                        _ac, _a = get_account(who.acc)
                        _st = _a.setdefault("commander", {}).setdefault("stats", {})
                        _st["pocs"] = _st.get("pocs", 0) + 1
                        check_medals(who, _a, _ac)
                        _ac[who.acc] = _a
                        save_accounts(_ac)
        elif p["capturing"]:
            p["capturing"] = False
            p.pop("cap_t", None)
            log(f"   POC {pid}: capture interrupted at {int(p['progress'])}")
    if b is not None and b.get("rule") == "victory" and not b.get("won"):
        try:
            victory_points_step(b, members)
        except Exception as e:
            log(f"   victory points error: {e!r}")
    return battle_judge(s, "poc", b) is not None     # every POC held (or NPC raiders hold them all)

def _vp_say(members, b):
    a, d = b["vp"]["att"], b["vp"]["def"]
    for o in members:
        try:
            _say_lang(o, f"胜利点数：进攻 {a:.0f} / 防守 {d:.0f}", f"勝利點數：進攻 {a:.0f} / 防守 {d:.0f}",
                      f"Victory points: attackers {a:.0f} / defenders {d:.0f}", (255, 220, 120))
        except Exception:
            pass

def victory_points_step(b, members):
    """VICTORY ruleset (battlefield.RULES): 800 points per side; joining players add, lost units / a POC minority /
    an empty side cost points (one POC_TICK)."""
    vp = b.setdefault("vp", {"att": float(BF.VP_START), "def": float(BF.VP_START)})
    dfd = b.get("defender") or 0
    is_def = lambda nat: (same_side(nat, dfd) if dfd else (nat is None or nat == 0 or nat == ALIEN_NATION))
    side = lambda o: "def" if (dfd and same_side(side_nation(o), dfd)) else "att"
    fighters = [o for o in members if not getattr(o, "spectator", False)]
    seen = b.setdefault("_vp_seen", set())
    for o in fighters:                                   # a player joins his side
        if o.acc not in seen:
            seen.add(o.acc)
            if len(seen) > 1:                            # the opener does not count
                vp[side(o)] += BF.VP_JOIN
    lost = {"att": 0, "def": 0}
    prev = b.setdefault("_vp_units", {})
    now_units = {}
    for o in fighters:
        cur = set(getattr(o, "alive_units", set()) or ())
        old = prev.get(o.acc)
        if old is not None:
            lost[side(o)] += len(old - cur)
        now_units[o.acc] = cur
    T = {t: g for t, g in (b.get("targets") or {}).items() if g.get("hp", 0) > 0 and not g.get("hive") and not g.get("ally")}
    old_t = prev.get("_targets")
    if old_t is not None:
        for t, nat in old_t.items():
            if t not in T:
                lost["def" if is_def(nat) else "att"] += 1
    now_units["_targets"] = {t: g.get("nation") for t, g in T.items()}
    b["_vp_units"] = now_units
    for k in ("att", "def"):
        vp[k] -= BF.VP_UNIT_LOSS * lost[k]
    pocs = [p["owner"] for p in (b.get("pocs") or {}).values()]
    d_own = sum(1 for o in pocs if (same_side(o, dfd) if dfd else not o))
    a_own = len(pocs) - d_own
    if a_own != d_own:
        vp["att" if a_own < d_own else "def"] -= BF.VP_POC_DRAIN * abs(a_own - d_own) * POC_TICK
    have = {"att": any(side(o) == "att" and getattr(o, "alive_units", None) for o in fighters)
                   or any(not is_def(n) for n in now_units["_targets"].values()),
            "def": any(side(o) == "def" and getattr(o, "alive_units", None) for o in fighters)
                   or any(is_def(n) for n in now_units["_targets"].values())}
    for k in ("att", "def"):
        if not have[k] and time.monotonic() - (b.get("t0") or 0) > 20:
            vp[k] -= BF.VP_EMPTY_DRAIN * POC_TICK
    for k in ("att", "def"):
        vp[k] = max(0.0, vp[k])
    nowt = time.time()
    if nowt - b.get("_vp_said", 0) >= BF.VP_ANNOUNCE or min(vp.values()) <= 0:
        b["_vp_said"] = nowt
        _vp_say(members, b)

def battle_rule_notice(o, b):
    """tell a player the ruleset of the battle he enters (and its Max Power Rating)."""
    r = BF.RULES.get(b.get("rule") or "")
    if not r:
        return
    cap = province_max_pr(b["map"])
    _say_lang(o, f"战斗类型：{r['cn']}。{r['help_cn']}（每方最高战力总和 {cap}，双方各自计算）",
              f"戰鬥類型：{r['tw']}。{r['help_tw']}（每方最高戰力總和 {cap}，雙方各自計算）",
              f"Battle type: {r['en']}. {r['help_en']} (Max Power Rating {cap} per side, each side counted separately)", (255, 220, 120))


# ---- ONE LOOP PER BATTLE (2026-10-24 ARCH_REVIEW A4): POCs every POC_TICK, aliens + NPC sides every second, in this
# order, one task per battle (was: alien_ai, npc_ai and poc_loop as three tasks, each with its own view of the field).
# alien_ai / npc_ai / poc_loop are kept as names: they only make sure the battle's loop runs.
AI_EVERY = 1.0

async def battle_loop(s, gen):
    await asyncio.sleep(1.0)
    b, mapid = getattr(s, "battle", None), getattr(s, "map", None)
    holder = b if b is not None else s.__dict__
    run = holder.get("_loop")
    if run is not None and not run.done() and run is not asyncio.current_task():
        return                                   # this battle has its loop already
    holder["_loop"] = asyncio.current_task()
    holder["_loop_s"] = s                        # (audit A) the session this loop runs on (battle_ctx_handoff)
    def alive():
        if b is not None:
            return BATTLES.get(mapid) is b and not b.get("won")
        return getattr(s, "battle_gen", None) == gen and not s.w.is_closing() and not getattr(s, "poc_won", False)
    ai_at = time.monotonic() + 1.0
    errs = 0
    try:
        while alive():
            if b is not None and b.get("ghost") and not _live(b):
                await asyncio.sleep(POC_TICK)
                continue                         # no player on the map: the simulation (ghost_cycle) runs it
            try:
                done = poc_step(s, b)
                errs = 0
            except Exception as e:
                # user 2026-10-24 06:16: one exception here stopped the whole battle (NPCs froze, no end) - log it and
                # go on; only an error that repeats for a minute stops the loop
                import traceback
                errs += 1
                if errs in (1, 10) or errs % 60 == 0:
                    log(f"   battle loop error #{errs} on {mapid}: {e!r} {traceback.format_exc()[-300:]}")
                if errs >= 120:
                    raise
                done = False
            if done:
                break
            if time.monotonic() >= ai_at:
                ai_at += AI_EVERY
                now = time.time()
                for step in (alien_step, npc_step):
                    try:
                        step(s, b, now)
                    except Exception as e:
                        import traceback
                        log(f"   {step.__name__} error: {e!r} {traceback.format_exc()[-300:]}")
            await asyncio.sleep(POC_TICK)
    except Exception as e:
        import traceback
        log(f"   battle loop stopped: {e!r} {traceback.format_exc()[-300:]}")
    finally:
        if holder.get("_loop") is asyncio.current_task():
            holder.pop("_loop", None)

async def alien_ai(s, gen):
    await battle_loop(s, gen)

async def npc_ai(s, gen):
    await battle_loop(s, gen)

async def poc_loop(s, gen):
    await battle_loop(s, gen)

BATTLE_STATE_FORCE_OPEN = 4    # (2026-10-25) province battle force-opened by a council member
BATTLE_STATE_IN_PROGRESS = 0   # u8 after the battle flag (legend: in progress / open / closed / full - order TBD)
PROVINCE_VALUE = 10        # "fields value" per owned province (PLACEHOLDER)
# vinu.inf terrain type per province (analysis/vinu_provinces.tsv copied to server/): 12 / 13
VINU_TYPE = {}
VINU_NAME = {}
# Map files whose abstract ground tiles (0x4000 bit) only use indices 0..413 = the "city" tile family of FieldMap.mp
# theme 13 (like Capital.nm; the client itself forces theme 13 for rr1.nm / nbattle.nm, 00495e30).  Drawn with
# theme 12 (what vinu.inf says for e.g. A1-L) they become a mosaic of grass/water/sand squares (2026-10-20 14:28,
# 600001 broken / 600101 fine).  Computed from pam3.dat (max abstract tile index <= 413).
LOW_FAMILY_MAPS = {"a1-dl", "a1-dl2", "a1-dr", "a1-dr2", "a1-l", "a1-l2", "a1-r", "a1-r2", "capital", "capitale",
                   "e4-1", "free", "nbattle", "rm01", "rm2", "rr1", "sst", "z1", "z3", "z4"}
try:
    for _ln in open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "vinu_provinces.tsv"), encoding="utf-8"):
        _f = _ln.rstrip("\n").split("\t")
        if _f[0].isdigit():
            VINU_TYPE[int(_f[0])] = int(_f[4])
            VINU_NAME[int(_f[0])] = _f[5].lower().replace(".nm", "")
except OSError:
    pass

# POINTS OF CONTENTION (CONFIRMED 004adf20 / 00499350 "Mission Objective"): 0x17 ends with
#   u8 battle kind (+0x29bf0; 4/5/7 make the objectives 'flag' 1), u8 THEME, u8 n, n x {u32 id, u16 x, u16 y
#   (pixels, /32 = tile, must be inside the map), u16 (p6), u8 TYPE, u32 (p7)}.
# The .nm map files hold no POC positions -> the server places them.  TYPE / p6 / p7 / kind meanings are not
# known yet (GM /poc TYPE [KIND] to experiment).  PLACEHOLDER: one POC in the middle of a 128x128 map.
# Record fields CONFIRMED (00499350 -> objective +0x38 = p6, owner = p7; client lock-step logic 0048f340, type 0):
#   p6 = STRENGTH: capture starts at p6 and drops by 5 per update while a unit of another alliance group stands on
#        the POC; below 0 the POC changes owner to that unit's nation.  p6 = 0 = nothing to capture (no counting).
#   p7 = OWNER nation of the POC (0 = aliens / Neutral).
#   server 0x49 [u32 id][u16 progress][u32 owner][u8 capturing] overwrites the three values (004a1f80).
POC_TYPE = 0
POC_BATTLE_KIND = 0
POC_STRENGTH = None        # GM /poc ... STRENGTH: force one strength for every POC (None = use POC_PLAN)
# POC PLAN (official rules, 2011-12 patch "POC time / number"): capture time depends on how many POCs the battlefield has:
#   1 POC 50 s, 2 POC 40 s, 3 POC 30 s, 4 POC 25 s, 5 POC 20 s - applied to Advanced .. Triton planets (tier >= 2);
#   the novice planet keeps the old rule (1 POC, 30 s).  The client takes 100 strength per second (POC_RATE, measured).
# The number of POCs of a province (tier >= 2) is 2..5, derived from the province id so it is always the same.
POC_SECONDS = {1: 50, 2: 40, 3: 30, 4: 25, 5: 20}
POC_NOVICE_SECONDS = 30
POC_FORCE = None           # GM /pocs N [SECONDS] (applies to the next province battle)
try:
    POC_SPOTS = data_json("poc_spots.json")
except (OSError, ValueError):
    POC_SPOTS = {}         # tools/gen_poc_spots.py builds it from pam.dat (walkable, connected, away from the borders/exits)

# POC RULESET of a province (user 2026-10-27 18:59, battlefield.RULES): fixed per province.  The novice planet (1 POC)
# plays Standard; elsewhere the four rulesets are spread over the provinces (crc of the id).  POC_RULE_FORCE = GM /rule.
POC_RULE_ORDER = ("all_or_nothing", "standard", "standard_enhanced", "victory")
POC_RULE_FORCE = None

def poc_rule(pid):
    base = province_of(pid) if pid < 100000000 else pid
    if base >= 100000000 or (pid // 10000) % 10 or base in CAPITALS.values():
        return None
    if POC_RULE_FORCE:
        return POC_RULE_FORCE
    if PLANET_TIER.get((base // 100000) % 1000, 1) <= 1 and not is_star_province(base):
        return "standard"
    return POC_RULE_ORDER[(zlib.crc32(b"rule%d" % base) >> 3) % 4]

def province_max_pr(pid):
    """Max Power Rating of a province's battles: the sum of the power ratings one side may bring (BF.MAX_PR_BY_TIER)."""
    base = province_of(pid) if pid < 100000000 else pid
    tier = 3 if is_star_province(base) else PLANET_TIER.get((base // 100000) % 1000, 1)
    return BF.MAX_PR_BY_TIER.get(tier, 160)

def commander_pr(o):
    """power rating counted against the Max Power Rating (at least 1 per commander)."""
    try:
        return max(1, PG.power_rating(PG.ensure_commander(get_account(o.acc)[1].setdefault("commander", {}))))
    except Exception:
        return 1

def side_pr(B, nid, exclude=None):
    return sum(commander_pr(o) for o in list(B.get("members") or []) if o is not exclude
               and not getattr(o, "spectator", False) and same_side(side_nation(o), nid))

def poc_count(pid):
    if POC_FORCE:
        return POC_FORCE[0]
    if PLANET_TIER.get((pid // 100000) % 1000, 1) <= 1:
        return 1
    if poc_rule(pid) == "all_or_nothing":
        return 3                          # original: All or Nothing maps have 3 POCs (clustered)
    return 2 + (zlib.crc32(str(pid).encode()) % 4)

def poc_seconds(pid, n):
    if POC_FORCE and POC_FORCE[1]:
        return POC_FORCE[1]
    return POC_NOVICE_SECONDS if PLANET_TIER.get((pid // 100000) % 1000, 1) <= 1 else POC_SECONDS.get(n, 30)

def poc_positions(pid, n):
    """pixel positions of the n POCs of a province map (precomputed on walkable ground), centre template as fallback."""
    # 2026-10-21: a province is drawn with the NAMED map of its vinu layout (0x66: every planet -> layout 2, e.g.
    # 200807 = a1-dr.nm); the old keys "000CCRR" were the 8x8 maps of planet 0 -> POCs on the wrong map's ground
    keys = []
    if pid < 100000000 and (pid // 10000) % 10 == 0:
        vk = LAYOUT.get((pid // 100000) % 1000, 2) * 100000 + pid % 100000
        if VINU_NAME.get(vk):
            keys.append(VINU_NAME[vk])
    for key in keys + ["%08d" % (pid % 100000000), "000%05d" % (pid % 100000)]:
        sp = POC_SPOTS.get(key)
        if sp and str(n) in sp:
            # never two POCs in one minimap grid square (5 x 5 over 128 tiles; user 2026-10-21): a cramped map
            # with fewer open squares than POCs gets fewer POCs
            out, used = [], set()
            for x, y in sp[str(n)]:
                c = (x // 32 * 5 // 128, y // 32 * 5 // 128)
                if c not in used:
                    used.add(c); out.append((x, y))
            return out
    tmpl = {1: [(0, 0)], 2: [(28, 0), (-28, 0)], 3: [(0, -28), (24, 14), (-24, 14)],
            4: [(28, 0), (-28, 0), (0, 28), (0, -28)], 5: [(0, 0), (28, 28), (-28, 28), (28, -28), (-28, -28)]}[n]
    return [((64 + dx) * 32, (64 + dy) * 32) for dx, dy in tmpl]

# ---- BATTERY PADS / METHANE VENTS (CONFIRMED 2026-10-21, client 0048f340 objective tick) -----------------------
# The 0x17 objective record's TYPE byte: 0 = POC, 6 = BATTERY PAD, 7 = METHANE VENT.  Every tick the client lets a
# unit within 64 px of a type-6 object recharge if its storage recharge TYPE (unit +0x260 = PUT skill entry of
# ability bit 2, value B) is 3 (battery); type 7 does the same for TYPE 4 (methane).  The amount per second is
# +0x168 (bit-2 entry, value A).  TYPE 1 / 2 (solar, gamma / nuclear) recharge everywhere (004cfea0 ->
# 004c68d0 / 004cbc60).  Original pad positions are not in the client data -> placed on walkable POC candidates.
PAD_TYPE, VENT_TYPE = 6, 7
PADS_PER_MAP = (1, 1)          # battery pads, methane vents per province battle map
PAD_MIN_DIST = 320             # px from every POC and from each other

def province_pads(mapid, pocs):
    keys = []
    if mapid < 100000000 and (mapid // 10000) % 10 == 0:
        vk = LAYOUT.get((mapid // 100000) % 1000, 2) * 100000 + mapid % 100000
        if VINU_NAME.get(vk):
            keys.append(VINU_NAME[vk])
    cand = []
    for key in keys + ["%08d" % (mapid % 100000000), "000%05d" % (mapid % 100000)]:
        sp = POC_SPOTS.get(key)
        if sp:
            for n in sorted(sp, key=lambda k: -int(k)):
                cand += [tuple(p) for p in sp[n]]
            break
    if not cand:
        cand = [(40 * 32, 40 * 32), (88 * 32, 88 * 32), (40 * 32, 88 * 32), (88 * 32, 40 * 32)]
    taken = [(p[1], p[2]) for p in pocs]
    out = []
    want = [PAD_TYPE] * PADS_PER_MAP[0] + [VENT_TYPE] * PADS_PER_MAP[1]
    nid = max([p[0] for p in pocs] or [0]) + 1
    for x, y in cand:
        if len(out) == len(want):
            break
        if all((x - tx) ** 2 + (y - ty) ** 2 >= PAD_MIN_DIST ** 2 for tx, ty in taken):
            out.append((nid + len(out), x, y, 0, want[len(out)], 0))
            taken.append((x, y))
    return out

def province_pocs(mapid):
    owner = province_owner(mapid)
    n = poc_count(mapid)
    strength = POC_STRENGTH if POC_STRENGTH else poc_seconds(mapid, n) * POC_RATE
    return [(i + 1, x, y, min(strength, 65535), POC_TYPE, owner) for i, (x, y) in enumerate(poc_positions(mapid, n))]

THEME_OVERRIDE = None   # GM /theme N (test): force the province-map terrain theme (FieldMap.mp has 9..13)
def map_terrain(mapid, capital=False):
    """terrain THEME byte of 0x17.  0 ('take vinu.inf's') kept the PREVIOUS map's theme: an Elite province entered
    from the capital (theme 13) was drawn with desert tiles + its own water/grass tiles = broken map (2026-10-20
    14:28).  Send the province's vinu.inf type explicitly, looked up in the layout the planet uses (0x43)."""
    if capital:
        return CAPITAL_TERRAIN
    if THEME_OVERRIDE is not None and mapid < 100000000 and (mapid // 10000) % 10 == 0:
        return THEME_OVERRIDE
    if mapid >= 100000000 or (mapid // 10000) % 10 != 0:
        return 0                                  # exercise / caves / hunting grounds / sst: unchanged (worked)
    planet = (mapid // 100000) % 1000
    key = LAYOUT.get(planet, planet) * 100000 + mapid % 100000
    if VINU_NAME.get(key) in LOW_FAMILY_MAPS:
        return CAPITAL_TERRAIN          # 13
    return VINU_TYPE.get(key, 12)

def current_planet(s):
    """planet the hero is on: current province-family map, else the province he came from, else the capital's."""
    for m in (getattr(s, "map", None), getattr(s, "cur_province", None)):
        if m and m < 100000000:
            return (m // 100000) % 1000
    return (CAPITALS.get(getattr(s, "cmd", {}).get("nation"), 600000) // 100000) % 1000


# ---- FORCE OPEN (user 2026-10-25 21:06 "照原版規則做") ---------------------------------------------------------------
# Strategic map, USERS tab: the FORCE OPEN button (shown by the client to the president / council (cmd +0x47f) and to
# regiment leaders, 00434760) sends 0x56 [u32 province][u8 1 open | 0 undo] (004347d0; only when a battle of the
# player's side runs there).  Original rule (ntt ksForceOpen): a council member forces a battle open - everybody of
# the faction may then join WITHOUT the battlefield commander's permission (his Ctrl+F7 "refuse all" included).
def force_open(s, body):
    if len(body) < 6:
        return
    if getattr(s, "sim_board", False):
        # (user 2026-10-26 12:42) the Simulation Center board has the same panel: a real map pushed here replaced the
        # sim records and the board's ENTER did nothing -> no force open from the simulation board
        log(f"   FORCE OPEN from the simulation board by {s.acc} ignored")
        return
    pid, on = struct.unpack_from(">I", body, 1)[0], body[5]
    nid = int((getattr(s, "cmd", {}) or {}).get("nation", 0) or 0)
    _rn, _rg = regiment_of(s.acc)
    leader = bool(_rg) and str(_rg.get("leader", "")).lower() == str(s.acc).lower()
    if not (is_council_member(s.acc, nid) or leader):
        log(f"   FORCE OPEN {pid} by {s.acc} refused: not a council member")
        _say_lang(s, "只有议会成员可以强制开放战斗。", "只有議會成員可以強制開放戰鬥。",
                  "Only council members can force a battle open.", (255, 150, 120))
        return
    hit = [(m, B) for m, B in list(BATTLES.items()) if m < 100000000 and province_of(m) == province_of(pid)
           and not B.get("sim") and not B.get("won")]
    if not hit:
        log(f"   FORCE OPEN {pid} by {s.acc}: no battle there")
        _say_lang(s, "该省目前没有战斗。", "該省目前沒有戰鬥。", "There is no battle in that province.", (255, 150, 120))
        return
    pnum = province_number(province_of(pid))
    for m, B in hit:
        if on:
            B["force_open"] = s.acc
            # players already waiting for the commander's answer get in now
            for acc, p in list(PENDING_JOIN.items()):
                js, jm, jx, jy, _c, w, sd = p
                if jm == m and not w:
                    PENDING_JOIN.pop(acc, None)
                    if not js.w.is_closing():
                        js.side_nation = sd
                        enter_field(js, jm, jx, jy, watch=False)
        else:
            B.pop("force_open", None)
    log(f"   FORCE OPEN {'ON' if on else 'OFF'}: province {pid} by {s.acc} (battles {[m for m, _ in hit]})")
    who = display_name(s.acc)
    for o in list(ONLINE):
        if not getattr(o, "logged_in", False) or o.w.is_closing():
            continue
        if int((getattr(o, "cmd", {}) or {}).get("nation", 0) or 0) != nid:
            continue
        if on:
            _say_lang(o, f"议会成员 {who} 已强制开放 {pnum} 号省的战斗，所有人可直接加入。",
                      f"議會成員 {who} 已強制開放 {pnum} 號省的戰鬥，所有人可直接加入。",
                      f"Council member {who} forced the battle in province {pnum} open: everybody can join directly.",
                      (120, 220, 255))
        else:
            _say_lang(o, f"{who} 取消了 {pnum} 号省战斗的强制开放。", f"{who} 取消了 {pnum} 號省戰鬥的強制開放。",
                      f"{who} cancelled the forced opening of the battle in province {pnum}.", (120, 220, 255))
    # the button / Legend read the battle state from the strategic map -> send the requester a fresh one
    try:
        s.send(build_strategic_map(s))
    except Exception as e:
        log(f"   force open: map refresh failed {e!r}")
