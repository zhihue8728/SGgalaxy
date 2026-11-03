# sgserver part "npc_battle": NPC squads on battle maps, battle brain step, /npc GM.
# Loaded by sgserver.py into ONE shared namespace (exec, in the order of PARTS) - not an importable module;
# every name here is a sgserver global.  Checks: python tools/check_server.py
# ---- hooks called from the rest of the server ------------------------------------------------------------------------
def npc_owner_changed(pid, old, new):
    """a nation that just lost a province is left alone by the NPCs for a while."""
    if old and old != new and pid not in set(CAPITALS.values()):
        npc_state()["protect"][str(old)] = time.time() + random.uniform(*NP.PROTECT_SECONDS)
        npc_dirty()
    if old and old != new:
        NPC_LOST[pid] = (old, time.time())      # (11-02) the old owner's NPCs want it back (npc_candidates "retake")

def npc_unit_died(tg):
    n = npc_state()["npcs"].get(str(tg.get("npc")))
    if n is not None and tg.get("idx") is not None:
        NP.health(n)[tg["idx"]] = 0.0
    rt = NPC_RT.get(tg.get("npc"))
    if rt is not None:
        rt["dead"] = rt.get("dead", 0) + 1

def npc_unit_left(tg):
    """(2026-10-25 audit S3) an NPC unit walked out (withdrawn / swapped out): not a loss, and no longer part of the
    side's strength -> 'left' (the loss ratio at time-up uses units - left)."""
    rt = NPC_RT.get(tg.get("npc"))
    if rt is not None:
        rt["left"] = rt.get("left", 0) + 1
    tid = tg.get("_tid")
    if tid is not None:
        CLOAKED.pop(tid, None)
        SHIELDS.pop(tid, None)

def npc_left_notice(b, name):
    """(audit C8) '%s has left this battle.' (0xC5, the participant list drops him) for an NPC commander, like a player."""
    if not b or not name:
        return
    pk = bytes([0xC5]) + _s8(name)
    for o in list(b.get("members") or ()):
        try:
            if not o.w.is_closing():
                o.send(pk)
        except Exception:
            pass

def npc_stats(b, npc_id):
    """per-battle score of an NPC commander for the COMBAT RANKING window (TAB): kills, kill levels, POCs, waves."""
    if not b or npc_id is None:
        return None
    return b.setdefault("npc_stats", {}).setdefault(npc_id, {"kills": 0, "kill_lv": 0, "pocs": 0, "reins": 0})

def npc_score_kill(s, killer, level):
    """killer = a server unit id: if it is an NPC unit, the kill counts for its commander (TAB window)."""
    tg = (getattr(s, "targets", None) or {}).get(killer)
    if not tg or tg.get("npc") is None:
        return False
    st = npc_stats(getattr(s, "battle", None), tg["npc"])
    if st is None:
        return False
    st["kills"] += 1
    st["kill_lv"] += max(1, int(level or 1))
    return True

def npc_killer_of(s, uid):
    """the NPC unit that killed player unit uid: the nearest living NPC unit whose current target it was."""
    pos = (getattr(s, "unit_pos", None) or {}).get(uid)
    best = None
    for tid, tg in (getattr(s, "targets", None) or {}).items():
        if tg.get("npc") is None or tg.get("target") != uid or tg.get("hp", 0) <= 0:
            continue
        d = AL.dist(tg.get("pos") or (0, 0), pos) if pos else 0
        if best is None or d < best[0]:
            best = (d, tid)
    return best[1] if best else None

def npc_battle_result(pid, npc_won):
    NPC_RESULT[pid] = bool(npc_won)

def npc_rt_attach(i, B, nid=None):
    """NPC_RT entry of NPC commander i -> battle B.  user 2026-10-24 06:16: entries made here without "nid" (NPCs that
    got no unit on the map) crashed the end-of-battle check (KeyError 'nid'): the battle loop stopped, the NPC units
    stood still and the battle never ended.  An NPC without units on the map has no reserve either (waves = max)."""
    if nid is None:
        nid = (npc_state()["npcs"].get(str(i)) or {}).get("nation")
    rt = NPC_RT.setdefault(i, {"dead": 0, "units": 0, "waves": NPC_WAVES_MAX})
    rt["B"] = B
    if rt.get("nid") is None:
        rt["nid"] = nid
    return rt

def npc_battle_started(s, B):
    am = getattr(s, "ambush_meta", None)
    if am:
        s.ambush_meta = None
        A = AMBUSH.get(am["R"])
        if A is not None:
            A["B"] = B
        B["ambush"] = am["R"]
        for i in am["ids"]:
            npc_rt_attach(i, B)
    meta = getattr(s, "alien_meta", None) or {}
    if not meta.get("npc"):
        meta = getattr(s, "npc_extra", None) or {}
        s.npc_extra = None
        if meta:
            B["npc_meta"] = meta
    if not meta.get("npc"):
        return
    B["npc_side"], B["npc_raid"] = meta["npc_nation"], bool(meta.get("raid")) and not meta.get("npc_ally")
    B["npc_ally"] = bool(meta.get("npc_ally"))
    B["npc_ids"] = list(meta.get("npc_ids", []))
    now = time.time()
    for i in B["npc_ids"]:
        npc_rt_attach(i, B)
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
    if b.get("npc_attacker") is not None:
        return ghost_finish(b, True)
    if b.get("won"):
        return
    b["won"] = True
    nat, pid = b["npc_side"], b["map"]
    RAIDS.pop(pid, None)
    capture_province(pid, nat)                       # (one logic: battle_rules.capture_province)
    NPC_RESULT[pid] = True
    log(f"   NPC: the raiders of nation {nat} captured every POC of {pid}")
    for o in list(b["members"]):
        spawn(
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
    if won:
        capture_province(pid, nat)
    NPC_RESULT[pid] = won

# ---- NPC squads on a battle map (server-owned units, like the aliens) ---------------------------------------------------
def npc_spawn(s, mapid, nid, npcs, budget, homes, mode, x, y, raid, pocs=(), keep_meta=False, hp_mult=1.0, ally=False, starts=None):
    tier, dist, _cave, mapname = alien_context(s, mapid)
    s.targets = s.targets if isinstance(getattr(s, "targets", None), dict) else {}
    _meta = {"npc": True, "npc_nation": nid, "tier": tier, "dist": dist, "cave": None, "map": mapname, "branch": 0,
                    "players": 1, "mapid": mapid, "full": 0, "waves_left": 0, "next_wave": 0, "squad_n": 0,
                    "arrival": (x, y), "raid": raid, "sim": False, "npc_ids": [], "npc_ally": ally}
    if keep_meta:                  # NPCs besieging a neutral province next to its aliens: the alien meta stays
        s.npc_extra = _meta
    else:
        s.alien_meta = _meta
    if starts is not None and len(starts) == 0:   # (10-31 11:45) no gate to a province of its side: it does not enter
        log(f"   NPC: nation {nid} has no gate of its side on {mapid} - {[n['name'] for n in npcs]} do not enter")
        return
    per = max(2, budget // max(1, len(npcs)))
    npcs = npcs[:max(1, budget // per)]
    for qi, (n, home) in enumerate(zip(npcs, homes)):
        # (22:48) platoon NPCs bring 3..4 whole platoons (fewer when the side would get too big)
        units = npc_battle_units(n, per, nid, ctx=s, platoons=npc_field_platoons(n, len(npcs) - qi, s)
                                 if (n.get("doctrine") or {}).get("pp") else None)
        if not units:
            continue
        poc = pocs[qi % len(pocs)] if pocs else None
        NPC_RT[n["id"]] = {"B": None, "dead": 0, "units": len(units), "used": set(), "waves": 0, "wave_t": 0,
                           "per": max(per, len(units)),
                           "home": home, "poc": poc, "mode": mode, "nid": nid, "hp_mult": hp_mult, "ally": ally,
                           "start": starts[qi % len(starts)] if starts else None}
        npc_put_units(s, nid, n, units, home, mode, poc, hp_mult, ally, start=starts[qi % len(starts)] if starts else None)
        _meta["npc_ids"].append(n["id"])
    log(f"   NPC: {len(s.targets)} unit(s) of nation {nid} ({[n['name'] for n in npcs]}) on {mapid}, mode {mode}")

# 2026-10-23 12:31 / 13:36: the 1.8.5 client CRASHES a few seconds after it gets units of its OWN side that belong to a
# commander who is not in the battle (NPC allies: nation-1 NPCs joined SG001's nation-1 battle -> crash, twice).  Until
# the client is patched, no NPC unit of a player's side is ever put on a map where that player fights.
# Client F30 (release 1.0.11, tools/patch_sg_debug_f30.py) survives NPC allies (the crash was the CRT invalid-parameter
# handler, 00609e0f): only OLDER clients need the block.
ALLY_CLIENT_RELEASE = "1.0.11"

def ally_client_ok(o):
    h = getattr(o, "client_hash", None)
    if h is None:
        return False
    rel = getattr(o, "client_release", None)
    if rel and OTA.vtuple(rel) >= OTA.vtuple(ALLY_CLIENT_RELEASE):
        return True
    try:
        f = CLIENT_EXE_FILES[0]
        mt = os.path.getmtime(f)
        if _ALLY_HASH.get("mt") != mt:
            _ALLY_HASH.update(mt=mt, h=client_code_hash(f))
        return h == _ALLY_HASH["h"]                                # the server's own (current) client build
    except Exception:
        return False
_ALLY_HASH = {}

def npc_side_blocked(s, nid):
    b = getattr(s, "battle", None)
    members = set((b or {}).get("members") or ()) | {s}
    return any(not isinstance(o, Ghost) and not getattr(o, "spectator", False) and getattr(o, "acc", None)
               and not o.w.is_closing() and same_side(side_nation(o), nid) and not ally_client_ok(o) for o in members)

def npc_map_grid(s):
    """the 32-px walk grid of the battle map of s (None without one)."""
    try:
        mid = getattr(s, "map", None) or (getattr(s, "alien_meta", None) or {}).get("mapid")
        b = getattr(s, "battle", None) or {}
        mid = mid or b.get("map")
        return _walk_grid(alien_context(s, mid)[3]) if mid else None
    except Exception:
        return None

def npc_put_units(s, nid, n, units, home, mode, poc, hp_mult, ally=False, start=None):
    """put these units of NPC n on the battle map (server-owned targets + PUT_UNIT for every member)."""
    if npc_side_blocked(s, nid):
        log(f"   NPC: {n['name']} (nation {nid}) not put on the map - a player of that side is in the battle (client crash)")
        return
    # (22:48) each platoon in its own block (platoon blocks in a ring of 110 px, the units of a block 26 px apart);
    # every position on walkable ground (big platoon groups spilled onto rocks / water)
    _pp = (n.get("doctrine") or {}).get("pp")
    _grp = {}
    for k_, u_ in enumerate(units):
        _grp.setdefault(npc_platoon_of(n, u_[6]) if _pp else 0, []).append(k_)
    _ctr = AL.formation(len(_grp), 110)
    off = [(0, 0)] * len(units)
    for g_, (_pk, ks) in enumerate(sorted(_grp.items())):
        inner = AL.formation(len(ks), 26)
        for j_, k_ in enumerate(ks):
            off[k_] = (_ctr[g_][0] + inner[j_][0], _ctr[g_][1] + inner[j_][1])
    _grid = npc_map_grid(s)
    def _on_ground(p_, air_):
        if _grid is None or air_:
            return int(p_[0]), int(p_[1])
        q_ = _grid.snap(p_, 8)
        return (int(q_[0]), int(q_[1])) if q_ else (int(p_[0]), int(p_[1]))
    rt = NPC_RT.setdefault(n["id"], {"B": None, "dead": 0, "units": 0, "used": set()})
    for k, (name, lv, st9, hp, en, spd, idx, capt) in enumerate(units):
        hp = int(hp * hp_mult)
        tid = next_alien_id(s)
        _air = unit_kind(name)[1] == 2
        hx, hy = _on_ground((home[0] + off[k][0], home[1] + off[k][1]), _air)   # where it goes / stands (a POC for the holders)
        px, py = _on_ground((start[0] + off[k][0], start[1] + off[k][1]), _air) if start else (hx, hy)   # where it ENTERS (a gate)
        _t, akind, anum = unit_kind(name)
        sight = unit_sight(st9)
        _rsight = sight
        if NPC_REAL_SIGHT:
            try:
                _rsight = unit_view_px(npc_unit(name, lv))     # the unit's ORIGINAL sight (chassis + sensors), like a player's
            except Exception:
                _rsight = sight
        urole = npc_unit_role(name, st9)
        capt = capt and urole != "support"
        abil = 0 if urole == "support" else ABILITY_ATTACK
        sbits = npc_skill_bits(name)
        # user 2026-10-23 22:49: equipment functions for NPC units too - a Cloak item hides the unit (the NPC switches
        # it on near the enemy), a Detector item reveals cloaked enemy units around it (server-side targeting)
        try:
            _ib = unit_abilities(npc_unit(name, lv))
        except Exception:
            _ib = 0
        _eq = tuple(b_ for b_ in (NPC_CLOAK_BIT, NPC_DETECT_BIT) if _ib & (1 << b_)
                    and (b_ == NPC_DETECT_BIT or urole != "support"))
        _eq += tuple(b_ for b_ in sorted(NPC_ITEM_SKILLS) if _ib & (1 << b_))
        sbits = tuple(sbits) + tuple(b_ for b_ in _eq if b_ not in sbits)
        if sbits:
            UNIT_SKILLS[tid] = sorted((b_,) + tuple(SKILL_DEFAULT.get(b_, (0, 0))) for b_ in sbits)
            for b_ in sbits:
                abil |= 1 << b_
            if str(CODE_OF.get(DISPLAY.get(name, name), name))[:1] != "a":
                abil |= 1 << 27                                  # (transportable / teleportable, like player units)
        foff = AL.formation(NP.SQUAD_FAST, 16)[k % NP.SQUAD_FAST] if capt else (off[k][0] * 2, off[k][1] * 2)
        rt.setdefault("used", set()).add(idx)
        _plt = npc_platoon_of(n, idx) if (n.get("doctrine") or {}).get("pp") else 0     # (22:48) its platoon
        _fl = rt.setdefault("fielded", {})
        _fl[_plt] = _fl.get(_plt, 0) + 1
        s.targets[tid] = {"hp": hp, "max": hp, "x": px, "y": py, "armor": st9[0], "arow": st9[1], "level": lv,
                          "aggressive": True, "target": None, "name": name, "home": (hx, hy), "pos": (px, py),
                          "squad": n["id"], "state": "idle", "boss": False, "next_patrol": 0, "idx": idx,
                          "npc": n["id"], "plt": _plt, "nation": nid, "mode": mode, "role": "capturer" if capt else "fighter",
                          "off": foff, "spd": spd, "poc": poc[0] if poc else None, "ally": ally,
                          "gate": (px, py) if start else None, "urole": urole, "skills": list(sbits),
                          "can_cloak": NPC_CLOAK_BIT in sbits, "detect": NPC_DETECT_BIT in sbits,
                          "detect_r": max(NPC_DETECT_R, sight or 0) if NPC_DETECT_BIT in sbits else 0,
                          "bio": unit_branch(name) in ("inf", "org"),
                          "put": {"name": name, "owner": n["name"], "kind": akind, "num": anum, "nation": nid,
                                  "st9": st9, "sight": _rsight, "spd": spd, "abil": abil}}
        s.targets[tid]["put"]["en"] = max(1, en)
        try:                                     # (22:54) wounded NPC units: real max HP, so the bar shows the wound
            _hpmax = max(hp, int(unit_battle_stats(npc_unit(name, lv))[0] * npc_stand_mult(nid)))
        except Exception:
            _hpmax = hp
        s.targets[tid]["put"]["hpmax"] = _hpmax
        _pk = put_server_unit(tid, name, n["name"], px, py, akind, anum, nid, hp=hp, hp_max=_hpmax, energy=max(1, en), stats9=st9,
                             sight=_rsight, speed=spd, abilities=abil)
        _b = getattr(s, "battle", None) or {}
        _mem = [o for o in (_b.get("members") or ()) if not o.w.is_closing()]
        if _mem and time.monotonic() - _b.get("t0", time.monotonic()) > 5:
            # (2026-10-25 audit C6) a running lock-step battle: like players' F7 squads and alien waves, the NPC squad
            # is put with 0x50 "Delayed Put" at ONE game time, so every client adds it on the same frame; the brain
            # gives it no order before then (enter_t)
            s.targets[tid]["enter_t"] = delayed_put(s, _pk, still=lambda _t=tid: _t in s.targets) + 0.3
        else:
            for _o in (_mem or [s]):
                _o.send(_pk)

# ---- HOW THE NPCs USE THEIR UNITS (user 2026-10-23 14:01 / 14:04) -------------------------------------------------------
# support : never attacks (PUT without the attack ability, no 0x2B), stays behind its squad's fighters, gets away from
#           enemies.  Medics / repair / sensor / field-hospital / energy / shield / support-aircraft chassis.
# artillery: long-range guns (ground range >= NPC_ARTY_RANGE px: Arbalest, Trebuchet, Liche, Apparition, Spirit ...):
#           stops at NPC_ARTY_STANDOFF x range from the target and bombards, falls back when an enemy comes closer than
#           NPC_ARTY_MIN x range.
# line    : everything else (the old behaviour).
NPC_SUPPORT_UNITS = {"Medic", "Gear-Doc", "Orbus", "Red-Eye", "Red-Eye-MK2", "Triage", "Triage-MK2", "Volte", "Mantlet",
                     "Roc", "Roc-MK2", "Albatross"}
NPC_ARTY_RANGE, NPC_ARTY_STANDOFF, NPC_ARTY_MIN = 500, 0.85, 0.45
# support skills NPC units get with their chassis (user 2026-10-23 14:51: the AI must USE heal / repair / shield / teleport):
# ability bits 25 Heal, 20 Repair, 43 Shield, 26 Teleport Unit; energy / power = the lowest-tech item (SKILL_DEFAULT)
NPC_SKILL_BITS = {"g016": (25,), "g023": (20, 25), "g056": (25, 20), "g035": (26, 43), "g002": (43,)}
SKILL_NAME = {25: "heal", 20: "repair", 43: "shield", 26: "teleport",
              # (2026-10-24 19:45) unit functions the battle brain uses (battle_ai._tactics) - from the unit's items /
              # chassis abilities: Daeva grenade, Sapper mines, artillery bombArd / Flak, Booster, Volte, Virus
              8: "grenade", 22: "mine", 21: "bombard", 37: "flak", 38: "booster", 54: "energy", 15: "refuel",
              59: "virus", 58: "virus"}
NPC_ITEM_SKILLS = {8, 22, 21, 37, 38, 54, 15, 59, 58}

def npc_skill_bits(name):
    return NPC_SKILL_BITS.get(CODE_OF.get(DISPLAY.get(name, name), name), ())

def npc_unit_role(name, st9):
    if name in NPC_SUPPORT_UNITS:
        return "support"
    if len(st9) > 4 and st9[4] >= NPC_ARTY_RANGE:
        return "artillery"
    return "line"

# APPROACH BEFORE ATTACK (user 2026-10-25 21:27 Ghasts, 2026-10-27 aliens): sgs/unit_orders.py, one rule for every
# server unit (order_attack / chase_step).  npc_weapon_range = the unit's longest weapon range in px.
def npc_weapon_range(tg):
    return unit_range(tg)

# ---- BATTLE BRAIN (battle_ai.py, claude/NPC_BATTLE_AI_ARCH.md) ------------------------------------------------------
import battle_ai as BAI
USE_BRAIN = True              # False = the old per-unit NPC AI
ALIEN_BRAIN = True            # aliens: focus fire / spread / wounded flee from the brain (the rest of alien_ai stays)

def _brain_side_same(a, b):
    if a == ALIEN_NATION or b == ALIEN_NATION:
        return a == b
    return same_side(a, b)

def _st9_unit(uid, side, pos, hp, hpmax, st9, spd, name, air=False, **kw):
    kw.setdefault("sight", 0)
    st9 = list(st9 or ()) + [0] * (9 - len(st9 or ()))
    role = BAI.unit_role(name, st9, NPC_SUPPORT_UNITS, NPC_ARTY_RANGE)
    return BAI.U(uid, side, pos, hp, hpmax, air=air, dmg_g=st9[3], dmg_a=st9[6], rng_g=st9[4], rng_a=st9[7],
                 cd=max(st9[5], st9[8], 20) / 100.0, spd=spd or 10, role=role, name=name, **kw)

def brain_world(s, members, now, pocs):
    """the battle as the brain sees it: every unit (NPC, alien, players) as battle_ai.U, POCs as plain dicts.
    (ARCH_REVIEW A4) built once per AI second and shared by the alien and the NPC step of battle_loop."""
    holder = getattr(s, "battle", None) or s.__dict__
    key = (now, len(s.targets), len(members))
    hit = holder.get("_bw")
    if hit is not None and hit[0] == key:
        units, stealth = hit[1], hit[2]
        return units, {i: {"x": p["x"], "y": p["y"], "owner": p["owner"]} for i, p in (pocs or {}).items()}, stealth
    units, P, stealth = _brain_world(s, members, now, pocs)
    holder["_bw"] = (key, units, stealth)
    return units, P, stealth

def _brain_world(s, members, now, pocs):
    units = {}
    for tid, tg in s.targets.items():
        if tg.get("hp", 0) <= 0 or not tg.get("pos") or tg.get("hive"):
            continue
        pa = tg.get("put") or {}
        if tg.get("npc") is not None:
            p = _npc_est_pos(tg, now) if tg.get("state", "idle") != "combat" else tg["pos"]
            u = _st9_unit(tid, tg.get("nation"), p, tg.get("hp_c", tg["hp"]), tg.get("max", tg["hp"]), pa.get("st9"),
                          pa.get("spd"), tg.get("name", ""), air=pa.get("kind") == 2, squad=("n", tg["npc"], tg.get("plt", 0)), ai=True,
                          home=tg.get("home"), mode=tg.get("mode", "assault"), poc=tg.get("poc"), gate=tg.get("gate"),
                          capt=tg.get("role") == "capturer", state=tg.get("state", "idle"), target=tg.get("target"),
                          skills=[SKILL_NAME[b_] for b_ in tg.get("skills", ()) if b_ in SKILL_NAME], bio=tg.get("bio", False),
                          sight=pa.get("sight") or 0)
            if tg.get("urole") == "support":
                u.role = "support"
        else:
            u = _st9_unit(tid, ALIEN_NATION, tg["pos"], tg.get("hp_c", tg["hp"]), tg.get("max", tg["hp"]), pa.get("st9"),
                          pa.get("spd"), tg.get("name", ""), squad=("a", tg.get("squad")), ai=False, home=tg.get("home"))
        units[tid] = u
    stealth = set()
    _dets = detectors(s.targets)
    for o in members:
        if getattr(o, "spectator", False):
            continue
        sn = side_nation(o)
        for uid in getattr(o, "alive_units", set()):
            if hidden(uid, o.unit_pos.get(uid, (0, 0)), _dets):
                stealth.add(uid)
            pa = getattr(o, "put_args", {}).get(uid) or {}
            hpv = getattr(o, "unit_hp", {}).get(uid) or pa.get("hp") or 1000
            units[uid] = _st9_unit(uid, sn, o.unit_pos.get(uid, (0, 0)), hpv, max(hpv, pa.get("hp") or hpv), pa.get("st9"),
                                   pa.get("spd"), pa.get("label", ""), air=pa.get("kind") == 2, squad=("p", o.acc),
                                   bio=pa.get("kind") != 2 and unit_branch(pa.get("label", "")) in ("inf", "org"),
                                   sight=pa.get("sight") or 0)
    P = {i: {"x": p["x"], "y": p["y"], "owner": p["owner"]} for i, p in (pocs or {}).items()}
    return units, P, stealth

import math
NPC_DODGE_WINDOW, NPC_DODGE_STEP, NPC_DODGE_PAUSE = 4.0, 130, 2.2

NPC_REAL_SIGHT = True       # user 2026-10-25 13:31: NPC units get their original sight (not weapon range + 80): they only fire inside it
NPC_ZONE_AIM_S = 30.0       # s a player's last order still counts as the aim of a stationary artillery piece
NPC_ZONE_REST_S = 2.0       # s an artillery piece has to stand still (installed) before its zone counts

def npc_arty_zones(s, members, mine, now):
    """user 2026-10-25 11:05: bombArd mode.  The client (004c5500, CONFIRMED) puts the shell area at
    unit position + facing direction x GROUND range, radius = the unit's sight.  The server does not know the facing,
    so the direction is that of the player's last order (move / attack) given to the stationary gun - an approximation:
    NPC units inside that circle are marked 'shelled' with the zone so that npc_dodge walks them out of it."""
    for o in members:
        if getattr(o, "spectator", False):
            continue
        rest = o.__dict__.setdefault("arty_rest", {})
        for uid in list(getattr(o, "alive_units", ())):
            pos = (getattr(o, "unit_pos", {}) or {}).get(uid)
            cmb = (getattr(o, "unit_cmb", {}) or {}).get(uid)
            if not pos or not cmb:
                continue
            st9 = cmb[0]
            if len(st9) < 9 or st9[3] <= 0 or st9[4] < NPC_ARTY_RANGE:
                continue                                   # not a ground artillery piece
            old = rest.get(uid)
            if old is None or AL.dist(old[0], pos) > 24:
                rest[uid] = (pos, now)
                continue
            if now - old[1] < NPC_ZONE_REST_S:
                continue
            md = (getattr(o, "move_dest", {}) or {}).get(uid)
            aim = md[0] if md and now - md[1] <= NPC_ZONE_AIM_S else None
            if aim is None or AL.dist(aim, pos) < 30:
                continue
            d = AL.dist(aim, pos)
            rng = st9[4]
            cx, cy = pos[0] + (aim[0] - pos[0]) / d * rng, pos[1] + (aim[1] - pos[1]) / d * rng
            rad = (getattr(o, "put_args", {}).get(uid) or {}).get("sight") or unit_sight(st9)
            rad = max(100, min(rad, 400))
            for tg in mine.values():
                if tg.get("hp", 0) <= 0 or tg.get("withdraw") or same_side(tg.get("nation"), side_nation(o)):
                    continue
                if AL.dist(tg["pos"], (cx, cy)) <= rad * 1.1:
                    tg["shelled"] = (now, pos)
                    tg["shell_zone"] = ((cx, cy), rad, now)

def npc_dodge(s, side, mine, now, move_to):
    """user 2026-10-25: a unit under artillery fire (the shell takes seconds to land) steps sideways out of the impact
    area instead of standing still - except a capturer that is taking / walking to a POC.  The side step is
    perpendicular to the line from the gun, on walkable ground."""
    grid = None
    for tid, tg in mine.items():
        sh = tg.get("shelled")
        if not sh or tg.get("nation") != side or tg.get("hp", 0) <= 0 or tg.get("withdraw"):
            continue
        if now - sh[0] > NPC_DODGE_WINDOW or now < tg.get("dodge_t", 0):
            continue
        d_ = tg.get("dest")
        if tg.get("role") == "capturer" and d_ and d_[0] is not None:
            continue                                        # capturing: stays on the point
        if (tg.get("put") or {}).get("kind") == 2:
            continue                                        # aircraft are not hit by ground shells
        a = _npc_est_pos(tg, now) if tg.get("mv") else tg["pos"]
        if grid is None:
            grid = npc_map_grid(s)
        dest = None
        zn = tg.get("shell_zone")
        if zn and now - zn[2] <= NPC_DODGE_WINDOW:
            # bombArd shells land in a circle (centre, radius): walk straight out of it, 70 px past its edge
            (cx, cy), rad = zn[0], zn[1]
            vx, vy = a[0] - cx, a[1] - cy
            n = max(1.0, (vx * vx + vy * vy) ** 0.5)
            for k in (1, -1):
                ang = 0.0 if k == 1 else 0.9
                ux, uy = vx / n, vy / n
                ux, uy = ux * math.cos(ang) - uy * math.sin(ang), ux * math.sin(ang) + uy * math.cos(ang)
                q = (cx + ux * (rad + 70), cy + uy * (rad + 70))
                if grid is not None:
                    q = grid.snap(q, 6)
                if q and AL.dist(q, a) > 20:
                    dest = (q[0], q[1])
                    break
        else:
            vx, vy = a[0] - sh[1][0], a[1] - sh[1][1]
            n = max(1.0, (vx * vx + vy * vy) ** 0.5)
            px, py = -vy / n, vx / n
            sg = tg.setdefault("dodge_sign", 1 if (tid & 1) else -1)
            for k in (sg, -sg):
                q = (a[0] + px * k * NPC_DODGE_STEP, a[1] + py * k * NPC_DODGE_STEP)
                if grid is not None:
                    q = grid.snap(q, 6)
                if q and AL.dist(q, a) > NPC_DODGE_STEP * 0.5:
                    dest = (q[0], q[1])
                    tg["dodge_sign"] = k
                    break
        if dest is None:
            continue
        move_to(tid, tg, dest)
        tg["route"] = None
        tg["dodge_until"], tg["dodge_t"] = now + 1.6, now + NPC_DODGE_PAUSE
        log(f"   NPC dodge: {tg.get('name')} {tid} steps out of artillery fire to {tuple(int(v) for v in dest)}")

def brain_npc_step(s, b, mine, members, pocs, tier, now, msgs, move_to, stand):
    _mover = lambda t_, g_, d_, _n, _m: move_to(t_, g_, d_)       # NPC walks: way points (unit_orders mover)
    holder = b if b is not None else s.__dict__
    brains = holder.setdefault("brains", {})
    units, P, stealth = brain_world(s, members, now, pocs)
    st = npc_state()["npcs"]
    for tid, tg in mine.items():
        if tg.get("can_cloak") and not tg.get("cloaked") and tg.get("pos") and tg.get("hp", 0) > 0:
            near = any(u.hp > 0 and not _brain_side_same(u.side, tg.get("nation")) and
                       (u.pos[0] - tg["pos"][0]) ** 2 + (u.pos[1] - tg["pos"][1]) ** 2 <= NPC_CLOAK_NEAR ** 2
                       for u in units.values())
            if near:
                tg["cloaked"] = True
                CLOAKED[tid] = {15}
                msgs.append(bytes([0x30]) + struct.pack(">I", tid) + bytes([15, 1]))
                log(f"   battle brain: {tg.get('name')} {tid} cloaks")
        if tg.get("detect") and tg.get("pos") and tg.get("hp", 0) > 0:
            # a Detector only works switched on (Detect toggle, action 43 [u8 on]), like a player's.  user 2026-10-25: the
            # client draws a detection ring while it is on -> it ran on EVERY detector all battle.  Now it is on only while
            # a cloaked enemy is near, off again 8 s after the last one went away.
            _r = max(tg.get("detect_r") or NPC_DETECT_R, NPC_CLOAK_NEAR) * 1.3
            need = any(u.hp > 0 and CLOAKED.get(u.id) and not _brain_side_same(u.side, tg.get("nation")) and
                       (u.pos[0] - tg["pos"][0]) ** 2 + (u.pos[1] - tg["pos"][1]) ** 2 <= _r * _r
                       for u in units.values())
            if need:
                tg["detect_need_t"] = now
                if not tg.get("detect_on"):
                    tg["detect_on"] = True
                    msgs.append(bytes([0x30]) + struct.pack(">I", tid) + bytes([43, 1]))
                    log(f"   battle brain: {tg.get('name')} {tid} switches its Detector on")
            elif tg.get("detect_on") and now - tg.get("detect_need_t", 0) > 8 and not tg.get("detect_hold", 0) > now:
                tg["detect_on"] = False
                msgs.append(bytes([0x30]) + struct.pack(">I", tid) + bytes([43, 0]))
                log(f"   battle brain: {tg.get('name')} {tid} switches its Detector off")
    _left = False
    for tid, tg in list(mine.items()):
        if not tg.get("withdraw"):
            continue
        gate = tg.get("gate") or tg.get("home")
        # (2026-10-24) a unit that cannot reach its gate (blocked / stuck) still leaves after NPC_WITHDRAW_MAX s
        # (11:42) gone before it stands on the portal: player units chasing it must not follow it into the exit
        if gate is None or AL.dist(tg.get("pos") or gate, gate) < BAI.GATE_CLEAR or now - tg.get("wd_t", now) > NPC_WITHDRAW_MAX:
            _left = True
            s.targets.pop(tid, None)
            dead_aliens(s).add(tid)                         # (11:16) its id is never given to a new unit
            mine.pop(tid, None)
            pk = bytes([0x19]) + struct.pack(">II", tid, 0)
            for o in members:
                try:
                    o.send(pk)
                except Exception:
                    pass
            tg["_tid"] = tid
            npc_unit_left(tg)
            log(f"   NPC: {tg.get('name')} {tid} left {getattr(s, 'map', '?')} through its gate (swapped out)")
        elif not tg.get("wd_sent"):
            tg["wd_sent"], tg["wd_t"] = True, now
            move_to(tid, tg, gate)
    if _left:
        _all_dead_check(s)                          # the last enemy walked out: the battle may be over
    for side in sorted({tg.get("nation") for tg in mine.values()}):
        br = brains.get(side)
        if br is None:
            lead = next((st.get(str(tg["npc"])) for tg in mine.values() if tg.get("nation") == side), None) or {}
            br = brains[side] = BAI.Brain(tier=tier, seed=hash((side, getattr(s, "map", 0))) & 0xffff,
                                          persona=lead.get("persona"))
            log(f"   battle brain: nation {side} on {getattr(s, 'map', '?')} - tier {tier}, persona {lead.get('persona')}")
        try:                                              # (10-31) helpers of this side on the way here
            _mp = getattr(s, "map", None)
            br.incoming[side] = sum(1 for m in npc_state()["npcs"].values()
                                    if m.get("state") == "active" and m.get("task") and m["task"].get("target") == _mp
                                    and m["task"].get("phase") == "march" and same_side(m.get("nation"), side))
        except Exception:
            br.incoming[side] = 0
        _ow = (holder.get("_orders_wait") or {}).pop(side, None)
        if _ow:
            br.orders.update(_ow)                         # orders given before this side's brain existed
        nlog = len(br.log)
        for kind, uid, arg in br.decide(units, P, _brain_side_same, now, controlled={side}, stealth=stealth):
            tg = s.targets.get(uid)
            if tg is None or tg.get("withdraw"):
                continue
            if tg.get("dodge_until", 0) > now:
                continue                                   # stepping out of artillery fire
            if kind == "skill":
                act = arg[0]
                if act in (6, 10, 21, 59, 60, 12):            # heal / repair / grenade / virus / refuel [u32 unit]
                    body = struct.pack(">I", arg[1])
                elif act in (9, 34, 35, 55):                  # bombArd / Flak / Booster / Energy production [u8 on]
                    body = bytes([arg[1]])
                    tg["mv"], tg["dest"] = (None, None) if arg[1] and act in (9, 34, 55) else (tg.get("mv"), tg.get("dest"))
                elif act == 8:                                # deploy mine [] - where it stands
                    body = b""
                    note_mine(s, tg["pos"], tg.get("nation"))
                elif act == 40:                               # shield [u8 on] - fixed where it is raised
                    body = bytes([arg[1]])
                    if arg[1]:
                        SHIELDS[uid] = (int(tg["pos"][0]), int(tg["pos"][1]), skill_power(uid, 40) or 160)
                        tg["mv"], tg["dest"] = None, None
                    else:
                        SHIELDS.pop(uid, None)
                elif act == 5:                                # teleport [u32 unit][u16 x][u16 y]
                    body = struct.pack(">IHH", arg[1], int(arg[2][0]), int(arg[2][1]))
                    _t2 = s.targets.get(arg[1])
                    if _t2 is not None:
                        _t2["pos"], _t2["mv"], _t2["state"], _t2["target"] = (float(arg[2][0]), float(arg[2][1])), None, "idle", None
                else:
                    continue
                if act in (9, 34, 35, 55, 40):              # (audit) on/off modes: kept for players who join later
                    tg.setdefault("modes", {})[act] = bool(arg[1])
                msgs.append(bytes([0x30]) + struct.pack(">I", uid) + bytes([act]) + body)
                log(f"   battle brain: {tg.get('name')} {uid} uses {({6: 'Heal', 10: 'Repair', 40: 'Shield', 5: 'Teleport', 21: 'Grenade', 59: 'Virus attack', 60: 'Virus kill', 12: 'Refuel', 9: 'bombArd mode', 34: 'Flak mode', 35: 'Booster', 55: 'Energy production', 8: 'Mine'}).get(act, act)}"
                    f" {arg[1:]}")
                continue
            if kind == "attack":
                tu = units.get(arg)
                if tu is None:
                    continue
                ch = tg.get("chase")
                if ch and ch[0] == arg:
                    continue                               # already walking to it (chase_step below)
                order_attack(uid, tg, arg, tu.pos, now, msgs, _mover, stand)   # out of range: walks first (unit_orders)
            else:
                tg.pop("chase", None)
                move_to(uid, tg, arg)
                for i, p in (pocs or {}).items():           # a capturer standing on its POC counts for poc_loop
                    if tg.get("role") == "capturer" and AL.dist(arg, (p["x"], p["y"])) < 40:
                        tg["dest"] = (i, arg)
        # walking to the target / target ran out of range while attacking: one rule for all server units (unit_orders)
        for uid, tg in list(mine.items()):
            if tg.get("nation") != side or tg.get("withdraw"):
                continue
            ch = tg.get("chase")
            tgt = ch[0] if ch else (tg.get("target") if tg.get("state") == "combat" else None)
            if tgt is None:
                continue
            tu = units.get(tgt)
            if tu is None or tu.hp <= 0:
                tg.pop("chase", None)
                continue
            chase_step(uid, tg, tu.pos, now, msgs, _mover, stand)
        if stealth:
            release_hidden(s, stealth, msgs, "battle brain")
        npc_dodge(s, side, mine, now, move_to)
        # GIVE UP (2026-10-24): a beaten NPC side does not sit at its gate forever (the battle never ended) - like a
        # player it retreats: after NPC_GIVEUP_AFTER s of a hopeless regroup every unit of that side walks out
        _pl = br.plans.get(side) or {}
        _gu = holder.setdefault("giveup", {})
        _seen = holder.setdefault("side_since", {}).setdefault(side, now)
        # (user 2026-10-24 06:57) not right after coming in, and never while a player of this side still fights here
        _with_player = any(not getattr(o, "spectator", False) and getattr(o, "alive_units", None)
                           and _brain_side_same(side_nation(o), side) for o in members)
        if _pl.get("kind") == "regroup" and _pl.get("ratio", 1.0) < NPC_GIVEUP_RATIO \
                and now - _seen >= NPC_GIVEUP_GRACE and not _with_player \
                and (b is None or npc_side_may_giveup(b, side)):
            _gu.setdefault(side, now)
            if now - _gu[side] >= NPC_GIVEUP_AFTER:
                _out = [tg for tg in mine.values() if tg.get("nation") == side and not tg.get("withdraw")]
                for tg in _out:
                    tg["withdraw"] = True
                if _out:
                    log(f"   battle brain: nation {side} on {getattr(s, 'map', '?')} is beaten (force ratio "
                        f"{_pl.get('ratio', 0):.2f}) - {len(_out)} unit(s) retreat through their gate")
                    try:
                        _n0 = npc_state()["npcs"].get(str(_out[0].get("npc")))
                        if _n0:
                            _pm = getattr(s, "map", 0)
                            _tx = {"zh-cn": f"{province_label_lang(_pm, 'zh-cn')}顶不住了，全军撤退！",
                                   "zh-tw": f"{province_label_lang(_pm, 'zh-tw')}頂不住了，全軍撤退！"}
                            npc_say(side, _n0, ("giveup", _pm, side),
                                    lambda lg, _tx=_tx, _pm=_pm: _tx.get(lg, f"We can't hold {province_label(_pm)} - fall back!"),
                                    now, gap=600, urgent=True)
                    except Exception:
                        pass
        else:
            _gu.pop(side, None)
        for e in br.log[nlog:]:
            log(f"   battle brain: nation {e[1]} on {getattr(s, 'map', '?')} plans {e[2]}"
                f"{'' if e[3] is None else ' POC %s' % e[3]} (force ratio {e[4]})")
        del br.log[:-20]
    # capturers standing on their POC (poc_loop counts tg["on_poc"])
    for tid, tg in mine.items():
        d = tg.get("dest")
        tg["on_poc"] = d[0] if (d and d[0] is not None and tg.get("role") == "capturer" and now >= tg.get("arrive_t", 0)) else None

# NPC_GIVEUP_RATIO -> battlefield.py (2026-10-24, the battle rules in one place)
# NPC_GIVEUP_AFTER -> battlefield.py (2026-10-24, the battle rules in one place)
# NPC_WITHDRAW_MAX -> battlefield.py (2026-10-24, the battle rules in one place)
# NPC_WAVES_MAX -> battlefield.py (2026-10-24, the battle rules in one place)
# NPC_WAVE_AT -> battlefield.py (2026-10-24, the battle rules in one place)

def npc_exit_check(s, b, now):
    """user 2026-10-24 06:37: an NPC commander whose units are all dead (or who has only non-fighting support units
    left and no reserve) leaves the battle like a player: the support units walk out through their gate, then the
    commander goes home (strategic map: off the province, battle list: off the dialog).  -> NPC ids that left."""
    left = []
    tg_all = list((s.targets or {}).items())
    for nid_, rt in list(NPC_RT.items()):
        if rt.get("B") is not b:
            continue
        mine_ = [(tid, tg) for tid, tg in tg_all if tg.get("npc") == nid_ and tg.get("hp", 0) > 0]
        fighting = [tg for _t, tg in mine_ if not tg.get("withdraw") and tg.get("urole") != "support"]
        reserve = rt.get("units", 0) > 0 and rt.get("waves", 0) < NPC_WAVES_MAX
        n = npc_state()["npcs"].get(str(nid_))
        if mine_ and not fighting and not reserve:
            _out = [tg for _t, tg in mine_ if not tg.get("withdraw")]
            for tg in _out:
                tg["withdraw"] = True
            if _out:
                log(f"   NPC: {(n or {}).get('name', nid_)} has no fighting unit left on {b['map']} - "
                    f"{len(_out)} support unit(s) walk out")
            continue
        if mine_ or (reserve and rt.get("wave_t", 0) and now < rt["wave_t"]):
            continue                                  # still there, or its next squad is about to come in
        if rt.get("units", 0) <= 0 and not rt.get("nid"):
            continue
        rt["waves"] = NPC_WAVES_MAX
        tk = (n or {}).get("task") or {}
        if b.get("ambush") or tk.get("kind") not in ("attack", "defend") or tk.get("phase") != "battle":
            continue                                  # ambushes / interceptions end through their own flow (AMBUSH)
        if nid_ in (b.get("npc_ids") or []):
            b["npc_ids"].remove(nid_)
        if n is not None:
            npc_left_notice(b, n.get("name"))
        if n is not None and tk.get("target") == b.get("map"):
            dead = rt.get("dead", 0) / max(1, rt.get("units", 1))
            npc_release(n, now, NP.rest_seconds(False), False)
            log(f"   NPC: {n['name']} (nation {n['nation']}) has no unit left on {b['map']} - leaves the battle "
                f"({dead:.0%} lost)")
        else:
            NPC_RT.pop(nid_, None)
        left.append(nid_)
    if left:
        npc_dirty()
    return left

def npc_fresh_wave(s, b, now):
    """F7 like a player (user 2026-10-22 21:25): when an NPC's units on the map fell to half of a squad, its next squad
    (the deploy size, healthy reserve units not used yet) comes in - at most every REINFORCE_COOLDOWN s, until the
    reserve is empty."""
    try:
        if npc_exit_check(s, b, now):
            _all_dead_check(s)
    except Exception as e:
        log(f"   npc_exit_check error: {e!r}")
    for nid_, rt in list(NPC_RT.items()):
        if rt.get("B") is not b or rt.get("units", 0) <= 0 or rt.get("waves", 0) >= NPC_WAVES_MAX:
            continue
        if not rt.get("wave_t"):
            rt["wave_t"] = now + REINFORCE_COOLDOWN          # like a player: F7 is ready one cooldown after the start
            continue
        if now < rt["wave_t"]:
            continue
        mine_ = [(tid, tg) for tid, tg in s.targets.items() if tg.get("npc") == nid_ and tg.get("hp", 0) > 0]
        alive = len(mine_)
        if not BF.may_reinforce(alive, "npc"):
            # (user 2026-10-24 04:30) wiped out: like a player whose whole division is dead it cannot call F7 any
            # more - no fresh units walk in, the battle is decided
            rt["waves"] = NPC_WAVES_MAX
            log(f"   NPC: {(npc_state()['npcs'].get(str(nid_)) or {}).get('name', nid_)} is wiped out on {b['map']} - "
                f"no more waves")
            _all_dead_check(s)
            continue
        th = battle_threat(b, rt["nid"])
        _n = npc_state()["npcs"].get(str(nid_))
        if _n is not None and (_n.get("doctrine") or {}).get("pp"):
            _platoon_wave(s, b, now, nid_, rt, _n, mine_, th)
            continue
        useless = [(tid, tg) for tid, tg in mine_ if th and th["n"] > 0 and tg.get("urole") != "support" and not tg.get("withdraw")
                   and unit_effect((tg.get("put") or {}).get("st9") or (), th) <= 0.0]
        swap = th is not None and alive and len(useless) >= max(2, alive // 2) and npc_side_company(s, b, nid_, rt["nid"])
        if alive > max(1, rt.get("per", 6)) * NPC_WAVE_AT and not swap:
            continue
        n = npc_state()["npcs"].get(str(nid_))
        if n is None:
            continue
        if swap:
            # user 2026-10-23 21:09: units that cannot hurt this enemy (e.g. ground-only guns against aircraft) walk back
            # to their gate and leave; units that fit the battle come in instead
            for tid, tg in useless:
                tg["withdraw"] = True
                if b.get("ghost") and not _live(b):
                    s.targets.pop(tid, None)
                    dead_aliens(s).add(tid)
            rt.setdefault("used", set()).difference_update({tg.get("idx") for _t, tg in useless})
            log(f"   NPC: {n['name']} pulls back {len(useless)} unit(s) that cannot hurt the enemy on {b['map']} "
                f"(enemy air share {th['air']:.0%})")
        if npc_deploy(n) - alive < 2:                     # (10-31) at its deploy limit (walking-out units count)
            continue
        units = npc_battle_units(n, max(2, rt.get("per", 6)), rt["nid"], exclude=rt.get("used", set()) |
                                 {tg.get("idx") for _t, tg in mine_}, ctx=b)
        units = [u for u in units if NP.health(n)[u[6]] >= 0.5]
        rt["wave_t"] = now + REINFORCE_COOLDOWN
        if len(units) < 2:
            rt["waves"] = NPC_WAVES_MAX                        # reserve used up
            continue
        rt["waves"] += 1
        rt["units"] += len(units)
        _st = npc_stats(b, nid_)
        if _st is not None:
            _st["reins"] += 1                               # TAB window: REINS
        npc_put_units(s, rt["nid"], n, units, rt["home"], rt["mode"], rt["poc"], rt.get("hp_mult", 1.0), rt.get("ally", False),
                      start=rt.get("start"))
        log(f"   NPC: {n['name']} sends {len(units)} fresh unit(s) into {b['map']} (wave {rt['waves']})")

# ---- PLAYERS <-> NPCs IN BATTLE (user 2026-10-24 23:31) -----------------------------------------------------------------
# 1. Players give the allied NPC platoons of their battle orders in the chat (ally or battle channel):
#      "佔點" / "抢点" / "capture" [B3]  -> the capturer platoons take the nearest POCs not ours (or the one in B3)
#      "集合" / "跟我" / "rally"          -> every allied platoon closes up on the player's units
#      "打 B3" / "攻擊 C2" / "attack D4"  -> every allied platoon fights in that grid cell
#      "守 B3" / "防守" / "hold" [B3]     -> hold that cell (or the player's position)
#    The grid is the minimap's: columns A..E left to right, rows 1..5 top to bottom (NPC_GRID_N).
# 2. NPCs report in the ally channel what their units see - enemy self-propelled artillery, cloaked units, mines -
#    with the grid cell, and send the platoon that counters it: a fast / line platoon onto the artillery, a platoon with a
#    Detector to the cloaked units / mines (else they ask the players for one).
NPC_GRID_N = 5
NPC_ORDER_S = 60              # s an order from a player lasts
NPC_COUNTER_S = 45            # s a counter-strike order lasts
NPC_SPOT = True
NPC_SPOT_EVERY = 3            # s between two looks
NPC_SPOT_RANGE = 700          # px: what an NPC unit notices around it
NPC_SPOT_CLOAK = 450          # px: a cloaked unit this close is noticed (shimmer, shots from nowhere)
NPC_SPOT_GAP = 90             # s between two reports of the same thing in the same cell / of the same enemy unit
NPC_SPOT_SAY_GAP = 45         # s between two chat lines of one side about the same kind of thing
NPC_SPOT_GROUP = 4            # (20:16) enemy ground units in one cell near us that make a "N enemies in A2" report
NPC_TALK_GAP = 4              # s between two orders of one player
_TALK_T = {}

_W_CAPTURE = ("佔點", "占点", "佔領", "占领", "搶點", "抢点", "拿點", "拿点", "佔據點", "占据点", "capture", "take poc", "poc")
_W_RALLY = ("集合", "跟我", "靠攏", "靠拢", "過來", "过来", "rally", "follow me", "on me")
_W_ATTACK = ("攻擊", "攻击", "進攻", "进攻", "打", "attack", "push")
_W_HOLD = ("防守", "守住", "守", "hold", "defend")
# (user 2026-10-25 20:16) more talk with a grid cell, both ways
_W_SCOUT = ("侦察", "偵察", "侦查", "偵查", "探路", "去看", "看看", "scout", "recon")
_W_AIR = ("飞机", "飛機", "空军", "空軍", "空中", "直升机", "直升機", "air", "plane", "aircraft", "flyer")
_W_ENEMY = ("有敌", "有敵", "敌人", "敵人", "敌军", "敵軍", "发现", "發現", "enemy", "enemies", "contact", "hostile")
_W_HELP = ("救", "支援", "帮", "幫", "顶不住", "頂不住", "help", "sos", "backup")
NPC_SCOUT_S = 45              # s a scout platoon has to reach its cell before it reports what it sees anyway
NPC_SCOUT_NEAR = 380          # px from the cell centre that counts as "there"

def battle_side_players(b, side):
    """the players of side `side` in battle b (receivers of the battle reports with grid cells)."""
    return [o for o in ((b or {}).get("members") or ()) if not o.w.is_closing() and same_side(side_nation(o), side)]

def _enemies_in(s, b, side, now):
    """[(uid, pos, st9, name, kind)] of the units fighting side `side` on this map (players' and other NPC sides')."""
    out = []
    for o in ((b or {}).get("members") or ()):
        if getattr(o, "spectator", False) or same_side(side_nation(o), side):
            continue
        for u in getattr(o, "alive_units", set()) or ():
            pa = (getattr(o, "put_args", {}) or {}).get(u) or {}
            out.append((u, o.unit_pos.get(u, (0, 0)), pa.get("st9") or (), pa.get("label", ""), pa.get("kind")))
    for tid, tg in ((b or {}).get("targets") or getattr(s, "targets", None) or {}).items():
        if tg.get("hp", 0) <= 0:
            continue
        nat = tg.get("nation") if tg.get("npc") is not None else ALIEN_NATION
        if same_side(nat, side):
            continue
        pu = tg.get("put") or {}
        pos = _npc_est_pos(tg, now) if tg.get("npc") is not None else (tg.get("pos") or (tg.get("x", 0), tg.get("y", 0)))
        out.append((tid, pos, pu.get("st9") or (), tg.get("name", ""), pu.get("kind")))
    return out

def _aa_platoons(plts):
    return [(k, g) for k, g in plts.items()
            if any(len((tg.get("put") or {}).get("st9") or ()) > 6 and (tg.get("put") or {}).get("st9")[6] > 0 for _t, tg in g["units"])]

def map_px_size(s):
    try:
        mid = getattr(s, "map", None) or (getattr(s, "battle", None) or {}).get("map")
        sz = MAP_SIZES.get(alien_context(s, mid)[3] or "")
        if sz:
            return sz[0] * 32, sz[1] * 32
    except Exception:
        pass
    return 4096, 4096

def grid_label(s, pos):
    w, h = map_px_size(s)
    c = max(0, min(NPC_GRID_N - 1, int(pos[0] * NPC_GRID_N // max(1, w))))
    r = max(0, min(NPC_GRID_N - 1, int(pos[1] * NPC_GRID_N // max(1, h))))
    return f"{chr(65 + c)}{r + 1}"

def grid_point(s, label):
    w, h = map_px_size(s)
    c, r = ord(label[0].upper()) - 65, int(label[1]) - 1
    return ((c + 0.5) * w / NPC_GRID_N, (r + 0.5) * h / NPC_GRID_N)

def _grid_in(text):
    import re as _re
    m = _re.search(r"(?<![A-Za-z])([A-Ea-e])\s*([1-5])(?![0-9])", text or "")
    return (m.group(1).upper() + m.group(2)) if m else None

def _side_platoons(s, side):
    """allied NPC platoons on this map: {(npc id, platoon): {"role", "units": [tg], "npc": n}}"""
    out = {}
    for tid, tg in (getattr(s, "targets", None) or {}).items():
        if tg.get("npc") is None or tg.get("hp", 0) <= 0 or tg.get("withdraw") or not same_side(tg.get("nation"), side):
            continue
        n = npc_state()["npcs"].get(str(tg["npc"]))
        if n is None:
            continue
        key = ("n", tg["npc"], tg.get("plt", 0))
        g = out.setdefault(key, {"units": [], "npc": n, "nation": tg.get("nation"),
                                 "role": (npc_platoons(n)[tg.get("plt", 0)][0] if (n.get("doctrine") or {}).get("pp")
                                          and tg.get("plt", 0) < len(npc_platoons(n)) else "main")})
        g["units"].append((tid, tg))
    return out

def _give_order(s, side, key, od):
    holder = getattr(s, "battle", None) or s.__dict__
    br = (holder.get("brains") or {}).get(side)
    if br is not None:
        br.orders[key] = od
    else:
        holder.setdefault("_orders_wait", {}).setdefault(side, {})[key] = od

def _centre(pts):
    pts = list(pts)
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)) if pts else None

def npc_battle_hear(s, text):
    """a player in a battle talks to the allied NPC platoons there (see above).  True = it was an order for them."""
    B = getattr(s, "battle", None)
    if not B or B.get("won") or getattr(s, "spectator", False):
        return False
    low = (text or "").lower()
    cell = _grid_in(text)
    kind = ("scout" if cell and any(w in low for w in _W_SCOUT)
            else "air" if cell and any(w in low for w in _W_AIR)
            else "enemy" if cell and any(w in low for w in _W_ENEMY)
            else "help" if cell and any(w in low for w in _W_HELP)
            else "capture" if any(w in low for w in _W_CAPTURE) else "rally" if any(w in low for w in _W_RALLY)
            else "hold" if any(w in low for w in _W_HOLD) else "attack" if cell and any(w in low for w in _W_ATTACK)
            else None)
    if kind is None:
        return False
    if kind in ("scout", "air", "enemy", "help"):
        return npc_battle_hear_cell(s, B, kind, cell, text)
    me = side_nation(s)
    plts = _side_platoons(s, me)
    if not plts:
        return False
    now = time.time()
    if now < _TALK_T.get(s.acc, 0):
        return True
    _TALK_T[s.acc] = now + NPC_TALK_GAP
    mine_pos = [s.unit_pos[u] for u in (getattr(s, "alive_units", ()) or ()) if u in (getattr(s, "unit_pos", {}) or {})]
    point = grid_point(s, cell) if cell else _centre(mine_pos)
    lb = cell or (grid_label(s, point) if point else "")
    used = []
    if kind == "capture":
        pocs = {i: p for i, p in (B.get("pocs") or {}).items() if not same_side(p.get("owner"), me)}
        if cell:
            pc = grid_point(s, cell)
            pocs = {i: p for i, p in pocs.items() if grid_label(s, (p["x"], p["y"])) == cell} or pocs
        if not pocs:
            spk = next(iter(plts.values()))["npc"]
            npc_say(spk["nation"], spk, ("talk", s.acc, "nopoc"), lambda lang: {"zh-cn": "附近没有可以占的据点了。",
                    "zh-tw": "附近沒有可以佔的據點了。"}.get(lang, "No POC left to take here."), now, gap=20, urgent=True,
                    to=battle_side_players(B, me))
            return True
        # capturer platoons first, then the fastest others; each takes the nearest free POC
        order = sorted(plts.items(), key=lambda kv: (kv[1]["role"] != "fast", -max((tg.get("spd") or 0) for _t, tg in kv[1]["units"])))
        free = dict(pocs)
        for key, g in order[:max(1, min(len(pocs), 3))]:
            c = _centre(tg["pos"] for _t, tg in g["units"])
            i, p = min(free.items(), key=lambda kv: (kv[1]["x"] - c[0]) ** 2 + (kv[1]["y"] - c[1]) ** 2)
            for _t, tg in g["units"][:NP.SQUAD_FAST]:
                tg["role"] = "capturer"                       # these stand on the POC (poc_loop counts them)
            _give_order(s, g["nation"], key, {"kind": "capture", "poc": i, "point": (p["x"], p["y"]),
                                                "until": now + NPC_ORDER_S, "why": "player: capture"})
            used.append((g, grid_label(s, (p["x"], p["y"]))))
            if len(free) > 1:
                free.pop(i, None)
    else:
        if point is None:
            return False
        for key, g in plts.items():
            _give_order(s, g["nation"], key, {"kind": {"rally": "move", "hold": "hold", "attack": "engage"}[kind],
                                              "point": point, "until": now + NPC_ORDER_S, "why": f"player: {kind}"})
            used.append((g, lb))
    who = {}
    for g, l in used:
        who.setdefault(g["npc"]["id"], (g["npc"], []))[1].append(l)
    for n, ls in list(who.values())[:3]:
        def reply(lang, _k=kind, _l=sorted(set(ls)), _p=display_name(s.acc), _n=sum(1 for g, _x in used if g["npc"] is n)):
            ll = "、".join(_l)
            if lang in ("zh-cn", "zh-tw"):
                tw = lang == "zh-tw"
                act = {"capture": ("抢点队前往" if not tw else "搶點隊前往") + ll + ("据点" if not tw else "據點"),
                       "rally": ("全队向你靠拢" if not tw else "全隊向你靠攏") + f"（{ll}）",
                       "hold": ("守住" if not tw else "守住") + ll,
                       "attack": ("全队压上" if not tw else "全隊壓上") + ll}[_k]
                return f"{_p}，收到！{act}。"
            act = {"capture": f"capturers heading for the POC in {ll}", "rally": f"closing up on you ({ll})",
                   "hold": f"holding {ll}", "attack": f"pushing into {ll}"}[_k]
            return f"{_p}, roger - {act}."
        npc_say(n["nation"], n, ("talk", s.acc, kind, n["id"]), reply, now, gap=10, urgent=True,
                to=battle_side_players(B, me))
    log(f"   NPC talk: {s.acc} '{text}' -> {kind} {lb}: {len(used)} platoon(s)")
    return True

def npc_battle_hear_cell(s, B, kind, cell, text):
    """(user 2026-10-25 20:16) "侦察 D2" / "E3 有飞机" / "A2 有敌人" / "救 C3": the allied NPC platoons of this battle
    act on a grid cell and answer like a team mate.  Orders go into the battle's brains (one per side, shared by every
    client of the battle - the units' moves reach all of them as ordinary NPC orders); the answers go to the players of
    this side in this battle.  -> True = handled (help: False, so the off-map SOS runs too)."""
    me = side_nation(s)
    plts = _side_platoons(s, me)
    now = time.time()
    to = battle_side_players(B, me)
    if not plts:
        return False
    if now < _TALK_T.get(s.acc, 0):
        return kind != "help"
    _TALK_T[s.acc] = now + NPC_TALK_GAP
    point = grid_point(s, cell)
    def dist_g(g):
        c = _centre(_npc_est_pos(tg, now) for _t, tg in g["units"])
        return (c[0] - point[0]) ** 2 + (c[1] - point[1]) ** 2 if c else 1e18
    picked, note = [], ""
    if kind == "scout":
        # the fastest small platoon goes and reports what it finds
        k, g = max(plts.items(), key=lambda kv: (kv[1]["role"] == "fast",
                                                 max((tg.get("spd") or 0) for _t, tg in kv[1]["units"]), -len(kv[1]["units"])))
        _give_order(s, g["nation"], k, {"kind": "move", "point": point, "until": now + NPC_SCOUT_S + 15,
                                        "why": f"player: scout {cell}"})
        B.setdefault("_scouts", []).append({"side": me, "key": k, "cell": cell, "point": point, "npc": g["npc"]["id"],
                                            "until": now + NPC_SCOUT_S, "by": s.acc})
        picked = [g]
    elif kind == "air":
        aa = _aa_platoons(plts)
        if aa:
            for k, g in sorted(aa, key=lambda kv: dist_g(kv[1]))[:2]:
                _give_order(s, g["nation"], k, {"kind": "engage", "point": point, "until": now + NPC_ORDER_S,
                                                "why": f"player: aircraft in {cell}"})
                picked.append(g)
        else:
            note = "noaa"
    else:                                          # enemy / help: the nearest platoons (help: up to 3)
        n_ = 3 if kind == "help" else 2
        for k, g in sorted(plts.items(), key=lambda kv: dist_g(kv[1]))[:n_]:
            _give_order(s, g["nation"], k, {"kind": "engage", "point": point, "until": now + NPC_ORDER_S,
                                            "why": f"player: {kind} {cell}"})
            picked.append(g)
    spk = (picked[0] if picked else next(iter(plts.values())))["npc"]
    def reply(lang, _k=kind, _c=cell, _p=display_name(s.acc), _n=len(picked), _note=note, _v=random.randrange(3)):
        if lang in ("zh-cn", "zh-tw"):
            tw = lang == "zh-tw"
            if _note == "noaa":
                return (f"{_p}，我们这边没有防空单位，谁能打{_c}的飞机？" if not tw else f"{_p}，我們這邊沒有防空單位，誰能打{_c}的飛機？")
            t = {"scout": [("收到，我去{c}看看。", "收到，我去{c}看看。"), ("快速队前往{c}侦察，有消息马上报。", "快速隊前往{c}偵察，有消息馬上報。"),
                           ("我去探{c}，等我回报。", "我去探{c}，等我回報。")],
                 "air": [("防空单位前往{c}，交给我们！", "防空單位前往{c}，交給我們！"), ("收到，防空过去{c}打飞机。", "收到，防空過去{c}打飛機。"),
                         ("{c}的飞机交给我的防空。", "{c}的飛機交給我的防空。")],
                 "enemy": [("收到，{c}我们压过去。", "收到，{c}我們壓過去。"), ("往{c}移动，准备接敌。", "往{c}移動，準備接敵。"),
                           ("{c}是吧？马上到。", "{c}是吧？馬上到。")],
                 "help": [("撑住！{n} 队往{c}支援。", "撐住！{n} 隊往{c}支援。"), ("马上到{c}，再顶一下！", "馬上到{c}，再頂一下！"),
                          ("{c}收到，全速支援中。", "{c}收到，全速支援中。")]}[_k][_v][1 if tw else 0]
            return f"{_p}，" + t.format(c=_c, n=_n)
        if _note == "noaa":
            return f"{_p}, we have no anti-air - who can hit the aircraft in {_c}?"
        return f"{_p}, " + {"scout": f"scouting {_c}, will report.", "air": f"anti-air heading to {_c}.",
                            "enemy": f"moving on {_c}.", "help": f"{_n} platoon(s) coming to {_c} - hold on!"}[_k]
    npc_say(spk["nation"], spk, ("talk", B.get("map"), s.acc, kind), reply, now, gap=8, urgent=True, to=to)
    log(f"   NPC talk: {s.acc} '{text}' -> {kind} {cell}: {len(picked)} platoon(s)")
    return kind != "help"

def npc_scout_reports(s, b, now):
    """a scout platoon that reached its cell (or ran out of time) says what is there."""
    sc = (b or {}).get("_scouts") or []
    if not sc:
        return
    keep = []
    for job in sc:
        plts = _side_platoons(s, job["side"])
        g = plts.get(job["key"])
        c = _centre(_npc_est_pos(tg, now) for _t, tg in g["units"]) if g else None
        there = c is not None and AL.dist(c, job["point"]) <= NPC_SCOUT_NEAR
        if not there and now < job["until"] and g:
            keep.append(job)
            continue
        cell = job["cell"]
        en = [e for e in _enemies_in(s, b, job["side"], now) if grid_label(s, e[1]) == cell]
        air = sum(1 for e in en if e[4] == 2)
        arty = sum(1 for e in en if e[4] != 2 and len(e[2]) > 4 and e[2][3] > 0 and e[2][4] >= NPC_ARTY_RANGE)
        n = npc_state()["npcs"].get(str(job["npc"])) or (g or {}).get("npc")
        if n is None:
            continue
        lost = g is None
        def rep(lang, _c=cell, _k=len(en), _a=air, _r=arty, _lost=lost):
            if lang in ("zh-cn", "zh-tw"):
                tw = lang == "zh-tw"
                if _lost:
                    return f"侦察队在{_c}失去联络！" if not tw else f"偵察隊在{_c}失去聯絡！"
                if not _k:
                    return f"{_c}侦察完毕：没看到敌人。" if not tw else f"{_c}偵察完畢：沒看到敵人。"
                extra = "".join([(f"，其中飞机 {_a}" if not tw else f"，其中飛機 {_a}") if _a else "",
                                 (f"，自走炮 {_r}" if not tw else f"，自走砲 {_r}") if _r else ""])
                return (f"{_c}侦察完毕：敌人约 {_k} 个{extra}。" if not tw else f"{_c}偵察完畢：敵人約 {_k} 個{extra}。")
            if _lost:
                return f"Lost contact with the scouts in {_c}!"
            if not _k:
                return f"{_c} scouted: no enemy seen."
            return f"{_c} scouted: about {_k} enemies" + (f", {_a} aircraft" if _a else "") + (f", {_r} artillery" if _r else "") + "."
        npc_say(n["nation"], n, ("scout", b.get("map"), cell, job["by"]), rep, now, gap=10, urgent=True,
                to=battle_side_players(b, job["side"]))
        log(f"   NPC scout {cell}: {len(en)} enemies ({air} air, {arty} arty){' - scouts lost' if lost else ''}")
    b["_scouts"] = keep

def npc_spot_reports(s, b, members, now):
    """NPC units spot enemy self-propelled artillery, cloaked units and mines near them: a report with the grid cell in
    the ally channel (when a player of that side is in this battle) and the counter platoon is sent."""
    tg_all = getattr(s, "targets", None) or {}
    sides = {tg.get("nation") for tg in tg_all.values() if tg.get("npc") is not None and tg.get("hp", 0) > 0}
    holder = b if b is not None else s.__dict__
    seen = holder.setdefault("_spotted", {})
    for side in sides:
        plts = _side_platoons(s, side)
        if not plts:
            continue
        own = [(tid, tg) for g in plts.values() for tid, tg in g["units"]]
        opos = [_npc_est_pos(tg, now) for _t, tg in own]
        def near(p, r):
            return any((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 <= r * r for q in opos)
        # enemy units: players' units and NPC units of the other sides
        enemies = []
        for o in members:
            if getattr(o, "spectator", False) or same_side(side_nation(o), side):
                continue
            for u in getattr(o, "alive_units", set()) or ():
                pa = (getattr(o, "put_args", {}) or {}).get(u) or {}
                enemies.append((u, o.unit_pos.get(u, (0, 0)), pa.get("st9") or (), pa.get("label", ""), pa.get("kind")))
        for tid, tg in tg_all.items():
            if tg.get("npc") is not None and tg.get("hp", 0) > 0 and not same_side(tg.get("nation"), side):
                pu = tg.get("put") or {}
                enemies.append((tid, _npc_est_pos(tg, now), pu.get("st9") or (), tg.get("name", ""), pu.get("kind")))
        found = []
        dets = detectors(tg_all)
        for uid, pos, st9, name, kind in enemies:
            if stealthed(uid):
                if near(pos, NPC_SPOT_CLOAK):
                    found.append(("cloak", uid, pos, name))
                continue
            if kind != 2 and len(st9) > 4 and st9[3] > 0 and st9[4] >= NPC_ARTY_RANGE and near(pos, NPC_SPOT_RANGE):
                found.append(("arty", uid, pos, name))
            elif kind == 2 and near(pos, NPC_SPOT_RANGE):
                found.append(("air", uid, pos, name))              # (20:16) "E3 有敌机"
        # (20:16) a bunch of enemy ground units in one cell near us: "A2 发现敌人约 N 个"
        import collections as _col2
        _gc = _col2.Counter(grid_label(s, pos) for uid, pos, st9, name, kind in enemies
                            if kind != 2 and not stealthed(uid) and near(pos, NPC_SPOT_RANGE))
        for _cell, _k in _gc.items():
            if _k >= NPC_SPOT_GROUP:
                found.append(("group", None, grid_point(s, _cell), str(_k)))
        for mx, my, mside, mt in list(holder.get("mines") or ()):
            if now - mt < MINE_MEMORY and not same_side(mside, side) and near((mx, my), 500):
                found.append(("mine", None, (mx, my), ""))
        if not found:
            continue
        player_here = any(not getattr(o, "spectator", False) and same_side(side_nation(o), side) for o in members)
        def _own_in(cell_, _opos=opos):
            return sum(1 for q in _opos if grid_label(s, q) == cell_) + sum(
                1 for o in members if same_side(side_nation(o), side) and not getattr(o, "spectator", False)
                for u in getattr(o, "alive_units", set()) or () if grid_label(s, o.unit_pos.get(u, (-1e6, -1e6))) == cell_)
        done = set()
        # (user 2026-10-24 23:51: the same Arbalests were reported again in B4, C3, B3 as they moved) one report per
        # enemy unit (NPC_SPOT_GAP), and the cell report counts the units of that kind there ("x 3")
        import collections as _col
        cnt = _col.Counter((w_, grid_label(s, p_)) for w_, _u, p_, _n in found)
        for what, uid, pos, name in found:
            cell = grid_label(s, pos)
            if (what, cell) in done or now < seen.get((side, what, cell), 0) \
                    or (uid is not None and now < seen.get((side, what, uid), 0)):
                continue
            done.add((what, cell))
            seen[(side, what, cell)] = now + NPC_SPOT_GAP
            for _w, _u, _p, _n in found:                       # every unit of this report counts as reported
                if _w == what and _u is not None and grid_label(s, _p) == cell:
                    seen[(side, what, _u)] = now + NPC_SPOT_GAP * 2
            if len(seen) > 500:
                for k_ in [k_ for k_, v_ in seen.items() if v_ < now]:
                    seen.pop(k_, None)
            # the counter platoon
            sent = None
            if what == "air":
                aa = _aa_platoons(plts)
                if aa:
                    k, g = min(aa, key=lambda kv: AL.dist(_centre(_npc_est_pos(tg, now) for _t, tg in kv[1]["units"]), pos))
                    _give_order(s, g["nation"], k, {"kind": "engage", "point": pos, "until": now + NPC_COUNTER_S,
                                                    "why": "counter aircraft"})
                    sent = g
            elif what == "group":
                pass                                          # the brain fights it; this is a report (and a call)
            elif what == "arty":
                cand = [(k, g) for k, g in plts.items() if g["role"] in ("fast", "main", "second")
                        and any((tg.get("put") or {}).get("st9", [0] * 9)[3] > 0 for _t, tg in g["units"])]
                if cand:
                    k, g = max(cand, key=lambda kv: (kv[1]["role"] == "fast",
                                                     max((tg.get("spd") or 0) for _t, tg in kv[1]["units"])))
                    _give_order(s, g["nation"], k, {"kind": "attack", "target": uid, "point": pos,
                                                    "until": now + NPC_COUNTER_S, "why": "counter artillery"})
                    sent = g
            else:
                cand = [(k, g) for k, g in plts.items() if any(tg.get("detect") for _t, tg in g["units"])]
                if cand:
                    k, g = cand[0]
                    for _t, tg in g["units"]:
                        if tg.get("detect"):
                            tg["detect_on"] = True
                            tg["detect_hold"] = now + NPC_COUNTER_S
                            tg["detect_need_t"] = now
                    _give_order(s, g["nation"], k, {"kind": "engage", "point": pos, "until": now + NPC_COUNTER_S,
                                                    "why": f"detect {what}"})
                    sent = g
            spk = (sent or next(iter(plts.values())))["npc"]
            log(f"   NPC spot: {spk['name']} (nation {side}) sees {what} {name} in {cell}"
                f"{' -> sends platoon ' + str(sent['role']) if sent else ''}")
            if not player_here:
                continue
            _k = cnt[(what, cell)]
            def say(lang, _w=what, _c=cell, _nm=(name if what == "group" else name + (f" x{_k}" if _k > 1 else "")),
                    _sent=sent, _own_in=_own_in):
                tw = lang == "zh-tw"
                if _w == "group":
                    _ours = _own_in(_c)
                    if lang in ("zh-cn", "zh-tw"):
                        if _ours < int(_nm or 0):
                            return (f"{_c} 敌人很多（约 {_nm} 个），我们人少，请求支援！" if not tw
                                    else f"{_c} 敵人很多（約 {_nm} 個），我們人少，請求支援！")
                        return (f"{_c} 发现敌人约 {_nm} 个，正在交战。" if not tw else f"{_c} 發現敵人約 {_nm} 個，正在交戰。")
                    return (f"Lots of enemies in {_c} (~{_nm}), we are outnumbered - need support!" if _ours < int(_nm or 0)
                            else f"About {_nm} enemies in {_c}, engaging.")
                if _w == "air":
                    if lang in ("zh-cn", "zh-tw"):
                        return (f"{_c} 有敌方飞机" if not tw else f"{_c} 有敵方飛機") + (f"（{_nm}）" if _nm else "") + \
                            (("，我的防空过去了。" if not tw else "，我的防空過去了。") if _sent else
                             ("，谁有防空？" if not tw else "，誰有防空？"))
                    return f"Enemy aircraft in {_c}" + (f" ({_nm})" if _nm else "") + \
                        (" - my anti-air is on it." if _sent else " - who has anti-air?")
                if lang in ("zh-cn", "zh-tw"):
                    base = {"arty": (f"{_c} 发现敌方自走炮" if not tw else f"{_c} 發現敵方自走砲") + (f"（{_nm}），" if _nm else "，"),
                            "cloak": f"{_c} 有隐形单位！" if not tw else f"{_c} 有隱形單位！",
                            "mine": f"{_c} 有地雷，小心！" if not tw else f"{_c} 有地雷，小心！"}[_w]
                    if _sent:
                        tail = {"arty": "我派快速部队去端掉它。" if not tw else "我派快速部隊去端掉它。",
                                "cloak": "我的侦测单位过去了。" if not tw else "我的偵測單位過去了。",
                                "mine": "我的侦测单位去扫。" if not tw else "我的偵測單位去掃。"}[_w]
                    else:
                        tail = {"arty": "谁的快速单位能去处理？" if not tw else "誰的快速單位能去處理？",
                                "cloak": "需要侦测单位支援！" if not tw else "需要偵測單位支援！",
                                "mine": "需要侦测单位，先绕开。" if not tw else "需要偵測單位，先繞開。"}[_w]
                    return base + tail
                base = {"arty": f"Enemy artillery in {_c}" + (f" ({_nm})" if _nm else ""), "cloak": f"Cloaked units in {_c}!",
                        "mine": f"Mines in {_c}, careful!"}[_w]
                tail = {"arty": " Sending fast units at it." if _sent else " Any fast units to deal with it?",
                        "cloak": " My detector is on the way." if _sent else " Need a detector here!",
                        "mine": " My detector will sweep." if _sent else " Need a detector - go around."}[_w]
                return base + tail
            npc_say(spk["nation"], spk, ("spot", (b or {}).get("map"), side, what), say, now, gap=NPC_SPOT_SAY_GAP,
                    urgent=True, to=battle_side_players(b, side) if b is not None else None)

NPC_PATHS = True             # way points for ground NPC units in live battles (npc_step.move_to)
NPC_PATHS_PER_STEP = 6       # new A* paths per battle and second
NPC_ROUTE_CACHE = 15         # s a path is reused (same 128 px start area, same 64 px goal)
NPC_PLATOON_SPENT = 0.34      # a platoon with this share of its units left (or less) is replaced by a fresh one

def npc_side_company(s, b, npc_id, nation):
    """(user 2026-10-31 13:23 "an NPC may pull units back to swap them as the battle needs - not when it is alone on the
    field"): another commander of its side has living units on this map (a player, or another NPC)."""
    for o in ((b or {}).get("members") or ()):
        if not getattr(o, "spectator", False) and same_side(side_nation(o), nation) and (getattr(o, "alive_units", None) or ()):
            return True
    for tg in ((b or {}).get("targets") or getattr(s, "targets", None) or {}).values():
        if tg.get("npc") is not None and tg.get("npc") != npc_id and tg.get("hp", 0) > 0 and not tg.get("withdraw") \
                and same_side(tg.get("nation"), nation):
            return True
    return False

def _platoon_wave(s, b, now, nid_, rt, n, mine_, th):
    """(user 2026-10-24 22:48) platoon NPCs: keep rt["n_pl"] platoons fighting.  A platoon that is worn down (<=
    NPC_PLATOON_SPENT of the units it brought) or that cannot hurt the enemy on the map (all its guns useless against
    it: ground-only guns vs aircraft) is replaced by the platoon of the reserve that suits the battle best (anti-air
    against aircraft, artillery against ground armies ...).  Useless platoons walk back to their gate and leave."""
    fielded = rt.get("fielded") or {}
    alive = {}
    for _tid, tg in mine_:
        if not tg.get("withdraw"):
            alive.setdefault(tg.get("plt", 0), []).append((_tid, tg))
    rt.setdefault("n_pl", max(1, len(fielded)))
    active, gone = [], []
    company = npc_side_company(s, b, nid_, rt["nid"])     # (10-31) alone on the field: no swapping
    for k, cnt in fielded.items():
        us = alive.get(k, [])
        # (23:20 log) the capturer platoon stays while there are POCs to take, even if its guns cannot hurt the enemy
        _capt = npc_platoons(n)[k][0] == "fast" if k < len(npc_platoons(n)) else False
        _to_take = any(not same_side(p_.get("owner"), rt["nid"]) for p_ in (b.get("pocs") or {}).values())
        useless = company and th is not None and th["n"] > 0 and us and not (_capt and _to_take) and all(
            tg.get("urole") == "support" or unit_effect((tg.get("put") or {}).get("st9") or (), th) <= 0.0 for _t, tg in us)
        if useless:
            for _t, tg in us:
                tg["withdraw"] = True
                if b.get("ghost") and not _live(b):
                    s.targets.pop(_t, None)
                    dead_aliens(s).add(_t)
            rt.setdefault("used", set()).difference_update({tg.get("idx") for _t, tg in us})   # they may come back
            gone.append(k)
            log(f"   NPC: {n['name']} pulls platoon {k} ({len(us)} unit(s)) out of {b['map']}: it cannot hurt the enemy "
                f"(enemy air share {th['air']:.0%})")
        elif len(us) > max(1, int(cnt * NPC_PLATOON_SPENT)):
            active.append(k)
    for k in gone:
        fielded.pop(k, None)
    if len(active) >= rt["n_pl"]:
        return
    if npc_deploy(n) - len(mine_) < 2:                  # (10-31) at its deploy limit: the next platoon waits for room
        return
    rt["wave_t"] = now + REINFORCE_COOLDOWN
    on_map = {tg.get("idx") for _t, tg in mine_}
    units = npc_battle_units(n, 0, rt["nid"], exclude=rt.get("used", set()) | on_map, ctx=b,
                             platoons=rt["n_pl"] - len(active),
                             capture=bool(b.get("pocs")) and not any(fielded.get(k) and (n.get("doctrine") or {}).get("pp")
                                                                     and npc_platoons(n)[k][0] == "fast" for k in active))
    units = [u for u in units if NP.health(n)[u[6]] >= 0.5]
    if len(units) < 2:
        if not active:
            rt["waves"] = NPC_WAVES_MAX                          # reserve used up
        return
    rt["waves"] += 1
    rt["units"] += len(units)
    _st = npc_stats(b, nid_)
    if _st is not None:
        _st["reins"] += 1
    for k in [k for k in fielded if k not in active]:
        fielded.pop(k, None)                                     # spent platoons: their survivors fight on, uncounted
    npc_put_units(s, rt["nid"], n, units, rt["home"], rt["mode"], rt["poc"], rt.get("hp_mult", 1.0), rt.get("ally", False),
                  start=rt.get("start"))
    _new = sorted({npc_platoon_of(n, u[6]) for u in units})
    log(f"   NPC: {n['name']} sends platoon(s) {_new} ({len(units)} unit(s): "
        f"{', '.join(sorted({u[0] for u in units}))}) into {b['map']} (wave {rt['waves']})")

def npc_closeness(pid):
    """1.0 at the capital .. 0 six portal steps away: the nearer to the capital, the stronger and more numerous the defenders
    (user 2026-10-22 14:03)."""
    return max(0.0, min(1.0, 1.0 - province_distance(pid) / 6.0))

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
    npc_spawn(s, mapid, r["npc"], npcs, npc_budget(n_units), homes, "assault", x, y, True,
              starts=gate_starts(mapid, len(npcs), r["npc"], (x, y)))

def npc_spawn_siege(s, mapid, x, y, pocs, n_units):
    """a player enters a neutral province while NPC commanders besiege it: their squads are really there (assault mode)
    next to the aliens and fight the player / take the POCs (user 2026-10-22 13:53: NPC dots missing in the battle)."""
    if not pocs or getattr(s, "spectator", False):
        return False
    force = [n for n in npc_all() if n["state"] == "active" and n["task"] and n["task"].get("kind") == "attack"
             and n["task"].get("target") == mapid and n["task"].get("phase") == "siege"]
    if not force:
        return False
    # a player of the SAME side joins his nation's NPC siege: the NPC squads are ALLIES there and fight the aliens with him
    # (user 2026-10-22 15:16: the NPC units were missing when the besiegers were of the player's own nation)
    mine = [n for n in force if same_side(n["nation"], side_nation(s))]
    if mine:
        force, ally = mine, True
    else:
        force, ally = [n for n in force if n["nation"] == force[0]["nation"]], False
    nid = force[0]["nation"]
    _t, _d, _c, mapname = alien_context(s, mapid)
    homes = spawn_homes(mapname, (x, y), len(force))
    npc_spawn(s, mapid, nid, force, npc_budget(n_units), homes, "assault", x, y, True, keep_meta=True, ally=ally,
              starts=gate_starts(mapid, len(force), nid, (x, y)))
    return True

def npc_spawn_defenders(s, mapid, x, y, pocs, n_units):
    owner = province_owner(mapid)
    if not owner or not pocs or same_side(owner, side_nation(s)) or getattr(s, "spectator", False):
        return False
    now = time.time()
    me = side_nation(s)
    # user 2026-10-23 16:08: three NPCs stood in the province on the strategic map, but after entering the battle there
    # was no NPC unit - they were sent back to march in from the capital.  NPCs that are DRAWN in this province (support,
    # a finished defence, walking through) are already here: they enter through the gates a few seconds after the start.
    present = []
    for n in npc_all():
        tk = n["task"]
        if n["state"] != "active" or not same_side(n["nation"], owner) or same_side(n["nation"], me):
            continue
        if tk and (tk.get("kind") == "intercept" or tk.get("phase") == "ambushed"):
            continue
        try:
            # user 2026-10-25 10:36: ten NPCs of the owner were drawn in the province (log: "took 600205 from 1" 8 s after
            # the player came in) but none entered: they were on a left-over assault / support task of THIS province (the
            # battle it belonged to is gone, a new one starts for the player) - npc_here() does not count them.  They
            # are in the province, so they defend it.
            _stale = bool(tk and tk.get("target") == mapid and tk.get("kind") in ("attack", "support", "defend")
                          and tk.get("phase") in ("battle", "support", "fight", "siege"))
            if npc_here(n, now) != mapid and not _stale:
                continue
        except Exception:
            continue
        present.append(n)
    present.sort(key=lambda n: -NP.power_of(n))
    present = present[:NPC_DEFENDERS_MAX + 3]
    pids = {n["id"] for n in present}
    cand = [n for n in npc_of(owner) if n["state"] == "active" and now >= n["rest_until"] and n["id"] not in pids
            and not (n["task"] and (n["task"].get("kind") in ("defend", "intercept") or n["task"].get("phase") == "ambushed"
                                    or n["task"].get("kind") == "attack" and n["task"].get("phase") != "march"))]
    if not cand and not present:
        # user 2026-10-25 10:43: nobody of the owner was free (all resting) and the province was attacked with no defender
        # at all.  A nation always has a garrison: the strongest active commanders that are not busy defending / ambushed
        # march in even if they are still resting (at most 2).
        cand = [n for n in npc_of(owner) if n["state"] == "active" and n["id"] not in pids
                and not (n["task"] and (n["task"].get("kind") in ("defend", "intercept") or n["task"].get("phase") == "ambushed"
                                        or n["task"].get("kind") == "attack" and n["task"].get("phase") != "march"))]
        cand.sort(key=lambda n: -NP.power_of(n))
        cand = cand[:2]
        if cand:
            log(f"   NPC: province {mapid} has no free defender - emergency garrison {[n['name'] for n in cand]}")
    if not cand and not present:
        return False
    cl = npc_closeness(mapid)
    per = max(4, int(npc_budget(n_units) * (1 + cl)) // max(1, min(len(present) + len(cand), NPC_DEFENDERS_MAX + 3)))
    for i, n in enumerate(present):
        if n["task"]:
            NPC_RT.pop(n["id"], None)
        n.pop("walk", None)
        n["task"] = {"kind": "defend", "target": mapid, "since": now, "phase": "march", "depart": now,
                     "arrive": now + 4.0 + 3.0 * i, "route": None, "origin": mapid, "path": [mapid],
                     "slot": i, "budget": per, "present": True}
        log(f"   NPC: {n['name']} (nation {n['nation']}) is in {mapid} - enters the battle through a gate")
        def _go(n=n, tk=n["task"]):
            try:
                if n.get("task") is tk and tk.get("phase") == "march":
                    npc_reinforce_enter(n, time.time())
            except Exception as e:
                log(f"   NPC: {n['name']} could not enter {mapid}: {e!r}")
        try:
            asyncio.get_event_loop().call_later(n["task"]["arrive"] - now, _go)   # (not up to NPC_TICK later)
        except Exception:
            pass
    if present:
        npc_dirty()
    if not cand:
        return False
    cand.sort(key=lambda n: (bool(n["task"]), -NP.power_of(n)))
    picked = cand[:max(0, NPC_DEFENDERS_MAX + int(round(3 * cl)) - len(present))]
    if not picked:
        return False
    # user 2026-10-23 13:00: no enemy was there before the battle and 4 appeared the moment the player entered.  The
    # defenders now MARCH in from their capital (strategic map: in the province they come from, white line), reach the
    # battle after the march time and enter through the gate on their road (npc_reinforce_enter), then go to the POCs.
    for i, n in enumerate(picked, start=len(present)):
        here = None
        try:
            here = npc_here(n, now)
        except Exception:
            pass
        # the march starts where the NPC is drawn now (not always the capital), through friendly provinces only
        path, secs = npc_march_path(n, mapid, now, NPC_REINF_PACE, start=here)
        if not path:
            log(f"   NPC: {n['name']} cannot reach {mapid} (cut off from {here})")
            continue
        if n["task"]:
            npc_release(n, now, 0)                 # (a marching attacker turns back to defend)
        n.pop("walk", None)
        route = path[-2] if len(path) >= 2 else None
        n["task"] = {"kind": "defend", "target": mapid, "since": now, "phase": "march", "depart": now,
                     "arrive": now + reinf_seconds(len(path) - 1),     # (07:16) same pace as every reinforcement
                     "route": route, "origin": route or here, "path": path}
        n["task"].update(slot=i, budget=per)
        log(f"   NPC: {n['name']} (nation {owner}) marches to defend {mapid} (via {n['task'].get('route')}, "
            f"arrives in {n['task']['arrive'] - now:.0f}s)")
    npc_dirty()
    return False                                   # (npc_ai starts with the first squad that arrives)

def _npc_est_pos(tg, now):
    mv = tg.get("mv")
    if not mv:
        return tg["pos"]
    (x0, y0), (x1, y1), t0, t1 = mv
    f = 1.0 if t1 <= t0 else max(0.0, min(1.0, (now - t0) / (t1 - t0)))
    return (x0 + (x1 - x0) * f, y0 + (y1 - y0) * f)

def npc_step(s, b, now):
    """one second of the NPC sides of a battle (battle_loop): wounds, fresh squads, the battle brain's orders.
    (2026-10-24 ARCH_REVIEW B1: the old per-unit NPC AI - only a fallback when the brain failed - is gone; a brain
    error now means no new NPC orders for that second.)"""
    mapid = getattr(s, "map", None)
    if b is not None and b.get("ghost"):
        ghost_check_end(b, now)                  # (players on the map: the end rules still apply, third side too)
    meta = getattr(s, "alien_meta", None) or {}
    if not meta.get("npc"):
        meta = dict(meta, **(getattr(s, "npc_extra", None) or (b or {}).get("npc_meta") or {}))
    tier = meta.get("tier") or PLANET_TIER.get((mapid // 100000) % 1000, 1) if mapid and mapid < 100000000 else meta.get("tier", 1)
    members = [o for o in b["members"] if not o.w.is_closing()] if b is not None else battle_members(s)
    pocs = b["pocs"] if b is not None else s.pocs
    msgs = []
    mine = {tid: tg for tid, tg in s.targets.items() if tg.get("npc") is not None and tg["hp"] > 0}
    for tg in mine.values():                    # remember the wounds (the NPC picks healthy units next time)
        n_ = npc_state()["npcs"].get(str(tg["npc"]))
        if n_ is not None and tg.get("idx") is not None:
            NP.health(n_)[tg["idx"]] = max(0.0, min(1.0, tg["hp"] / max(1, tg["max"])))
    if b is not None:
        npc_fresh_wave(s, b, now)
        mine = {tid: tg for tid, tg in s.targets.items() if tg.get("npc") is not None and tg["hp"] > 0}
    mine = {tid: tg for tid, tg in mine.items() if tg.get("enter_t", 0) <= now}   # (audit C6) not on the clients yet
    def _stand(tg, tp):
        """where the unit stands to shoot at tp: on the line to it at ~its weapon range (the client stops there)"""
        d = AL.dist(tg["pos"], tp)
        r = max(40, npc_weapon_range(tg) * (NPC_ARTY_STANDOFF if tg.get("urole") == "artillery" else 0.9))
        if d <= r or d < 1:
            return tg["pos"]
        return (tp[0] + (tg["pos"][0] - tp[0]) * r / d, tp[1] + (tg["pos"][1] - tp[1]) * r / d)
    # ---- PATH FINDING (user 2026-10-24 22:48): ground NPC units get WAY POINTS from the map's walk grid (battlesim
    # Grid.path, A* on 64 px cells, smoothed) instead of one far destination: the client walks short open legs (no
    # units stuck at water / cliffs, less path search on every client), the server knows where they really are, and
    # destinations are moved onto walkable ground.  NPC_PATHS_PER_STEP new paths per battle and second (CPU guard,
    # ~6 ms each), shared by the units of a platoon (cache NPC_ROUTE_CACHE s); without a path: the old straight order.
    grid = npc_map_grid(s) if NPC_PATHS else None
    _np = [0]
    holder_ = b if b is not None else s.__dict__
    rcache = holder_.setdefault("_routes", {})
    def _leg(tid, tg, a, q):
        d = AL.dist(a, q)
        if d > 20:
            msgs.append(_alien_order_move(tid, *q))
        dur = walk_seconds(tg, a, q)                       # (unit_orders: the one estimate)
        tg["mv"] = (tuple(a), tuple(q), now, now + dur)
        tg["leg_t"] = now + dur
        return dur
    def move_to(tid, tg, dest, poc_id=None):
        a = _npc_est_pos(tg, now) if tg.get("mv") else tg["pos"]
        route = None
        if grid is not None and (tg.get("put") or {}).get("kind") != 2 and AL.dist(a, dest) > 160:
            q = grid.snap(dest, 6)
            dest = (q[0], q[1]) if q else dest
            key = (int(a[0]) // 128, int(a[1]) // 128, int(dest[0]) // 64, int(dest[1]) // 64)
            hit = rcache.get(key)
            if hit and now - hit[0] < NPC_ROUTE_CACHE:
                route = hit[1]
            elif _np[0] < NPC_PATHS_PER_STEP:
                _np[0] += 1
                try:
                    route = grid.path(a, dest)
                except Exception as e:
                    log(f"   NPC path error: {e!r}")
                    route = None
                rcache[key] = (now, route)
                if len(rcache) > 400:
                    for k_ in [k_ for k_, v_ in rcache.items() if now - v_[0] >= NPC_ROUTE_CACHE]:
                        rcache.pop(k_, None)
        if route and len(route) > 1:
            fo = tg.get("off") or (0, 0)
            legs = []
            for wp in route[:-1]:                          # platoon mates do not all queue on the same point
                w2 = (wp[0] + fo[0] * 0.5, wp[1] + fo[1] * 0.5)
                legs.append((grid.snap(w2, 2) or wp) if grid is not None else w2)
            legs.append(tuple(dest))
            dur = _leg(tid, tg, a, legs[0])
            total = dur + sum(walk_seconds(tg, legs[i], legs[i + 1]) for i in range(len(legs) - 1))
            tg["route"] = legs[1:]
        else:
            tg["route"] = None
            total = _leg(tid, tg, a, dest)
        tg["arrive_t"] = now + total
        tg["dest"] = (poc_id, dest)
        tg["state"], tg["target"] = "idle", None
    # next leg of the units on a route (the brain's orders below may replace the route)
    for tid, tg in mine.items():
        r_ = tg.get("route")
        if r_ and tg.get("state", "idle") == "idle" and now >= tg.get("leg_t", 0) - 0.4:
            a_ = tg["mv"][1] if tg.get("mv") else tg["pos"]
            tg["pos"] = a_
            _leg(tid, tg, a_, r_.pop(0))
            if not r_:
                tg["route"] = None
    if mine and NPC_SPOT and now >= holder_.get("_spot_t", 0):
        holder_["_spot_t"] = now + NPC_SPOT_EVERY
        try:
            npc_spot_reports(s, b, members, now)
        except Exception as e:
            log(f"   npc spot report error: {e!r}")
        try:
            npc_scout_reports(s, b, now)
        except Exception as e:
            log(f"   npc scout report error: {e!r}")
    if mine:
        try:
            npc_arty_zones(s, members, mine, now)
        except Exception as e:
            log(f"   artillery zone error: {e!r}")
        try:
            brain_npc_step(s, b, mine, members, pocs, tier, now, msgs, move_to, _stand)
        except Exception as e:
            import traceback
            log(f"   battle brain error (no NPC orders this second): {e!r} {traceback.format_exc()[-400:]}")
    dispatch_orders(s, b, members, msgs, now, "NPC AI")

# ---- GM: /npc ------------------------------------------------------------------------------------------------------------
def npc_gm(s, parts):
    """/npc status | /npc go PID [N] | /npc stand [HOURS] | /npc fill | /npc clear | /npc reset |
    /npc ambush PID [NATION] (blockade for a test) | /npc ambushes"""
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
    elif sub == "where":
        # /npc where [PID]: every NPC that is IN this province (strategic map icon) or heading for it (user 2026-10-23 15:58)
        pid = int(parts[2]) if len(parts) > 2 else (province_of(getattr(s, "map", 0) or 0) or 0)
        rows = 0
        for n in npc_active():
            loc, _tg = npc_location(n, now)
            t = n.get("task") or {}
            if loc != pid and t.get("target") != pid:
                continue
            rows += 1
            eta = f", arrives in {t['arrive'] - now:.0f}s" if t.get("arrive") and t["arrive"] > now else ""
            say(f"{n['name']} (nation {n['nation']}): shown in {loc}, task {t.get('kind')}/{t.get('phase')} -> "
                f"{t.get('target')}{eta}, path {t.get('path')}")
        say(f"{rows} NPC(s) in / heading for {pid}")
    elif sub == "ambushes":
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
    elif sub == "clear":
        # give every province except the capitals back to the aliens (undo of an NPC land grab on a test server)
        w = world_state()
        caps = set(CAPITALS.values())
        n_ = 0
        for k in list(w["owners"]):
            if int(k) not in caps and int(w["owners"][k]):
                set_province_owner(int(k), 0)
                n_ += 1
        npc_state()["protect"].clear()
        say(f"{n_} provinces given back to the aliens")
    elif sub == "reset":
        npc_state()["npcs"].clear()
        for n_, _nm, _c in NATIONS:
            npc_ensure_roster(n_)
        say("NPC rosters recreated")
    npc_save(True)
