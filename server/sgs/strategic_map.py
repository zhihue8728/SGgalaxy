# sgserver part "strategic_map": strategic map and province info.
# Loaded by sgserver.py into ONE shared namespace (exec, in the order of PARTS) - not an importable module;
# every name here is a sgserver global.  Checks: python tools/check_server.py
# ---- strategic map AUTO-REFRESH (2026-10-21) -------------------------------------------------------------------
# 0x2d is a pure data replace on the client (00569d90 -> 00569490 / 00569830 -> 00565500 redraw), so it can be
# pushed at any time.  Every MAP_PUSH_SECONDS the server compares what the map shows (owners, battles + their
# open/closed/full state, where the heroes are) and re-sends 0x2d to every player who has opened the map once
# and whose planet changed.  The battle countdown alone does not trigger a push.  REFRESH still works (0x2b).
MAP_PUSH_SECONDS = 2
MAP_PUSH_RANGE = (5.0, 10.0)
MAP_PUSH = True           # 2026-10-21 user: no periodic push; the map refreshes when it is opened (client 0x2b)
MAP_REFRESH_MIN = 1.0      # and REFRESH is answered at most once per second per player

def _map_signature(planet):
    _tab = (WORLD or {}).get("star_owners" if planet in STAR_PLANET_IDS else "owners", {})   # demon stars: own table
    owners = tuple(sorted((k, v) for k, v in _tab.items() if (int(k) // 100000) % 1000 == planet)
                   + [("raid", p) for p in RAIDS if (p // 100000) % 1000 == planet])
    heroes = []
    for o in list(ONLINE):
        if not getattr(o, "logged_in", False):
            continue
        oc = getattr(o, "cmd", {}) or {}
        loc = getattr(o, "battle_province", None) or (province_of(o.cur_province) if getattr(o, "cur_province", None)
                                                      else CAPITALS.get(oc.get("nation")))
        heroes.append((str(getattr(o, "acc", "")), loc, oc.get("nation", 0)))
    bat = []
    for mid, B in list(BATTLES.items()):
        if mid >= 100000000 or not (B.get("members") or B.get("ghost")) or B.get("sim") or B.get("won"):
            continue
        bat.append((province_of(mid), len(B["members"]), getattr(B.get("owner"), "join_mode", 0)))
    for _n in npc_active():
        _loc, _tg = npc_location(_n)
        _ph = (_n.get("task") or {}).get("phase")
        heroes.append(("npc", _loc, _n["nation"], _ph in ("siege", "raid", "battle")))
        if _ph in ("siege", "raid", "battle"):
            bat.append((province_of(_loc), 0, 0))
    return (owners, tuple(sorted(heroes, key=str)), tuple(sorted(bat)))

async def map_push_cycle():
    while MAP_PUSH:
        await asyncio.sleep(random.uniform(*MAP_PUSH_RANGE))      # 5-10 s (user 2026-10-22 14:07)
        try:
            sigs = {}
            for o in list(ONLINE):
                if not getattr(o, "logged_in", False) or not getattr(o, "map_seen", False) or getattr(o, "battle", None):
                    continue
                if getattr(o, "sim_board", False):
                    # (user 2026-10-24 21:46: ENTER on the Simulation Center did nothing) the normal map pushed here
                    # replaced the sim board's records (no open battle, own nation not listed) -> client ENTER ignored
                    continue
                try:
                    if o.w.is_closing():
                        continue
                except Exception:
                    pass
                pl = current_planet(o)
                if pl not in sigs:
                    sigs[pl] = _map_signature(pl)
                if getattr(o, "map_sig", None) != sigs[pl]:
                    o.map_sig = sigs[pl]
                    send_strategic_map(o)
                elif MAP_WAR_TALLY and getattr(o, "_war_secB", None) is not None and time.time() - getattr(o, "_war_t", 0) >= 60 \
                        and time.time() - getattr(o, "info_t", 0) < 600:
                    # WAR tab: settlement countdown (minutes) / fields / value refreshed every minute while the map is used
                    o._war_t = time.time()
                    o.send(build_war_tally(o, o._war_planet, o._war_secB))
        except Exception as e:
            log(f"   map_push_cycle error: {e!r}")

def planet_of_map(mid):
    return (mid // 100000) % 1000

MAP_TALLY = False         # strategic map as 0x2c sub 0 with the per-nation tally (WAR tab numbers); False = plain 0x2d
                          # 2026-10-22 16:04: client crashed after entering the capital with it on -> off until tested
PROVINCE_TEXT = False     # cave / garrison status text in 0x2e (same crash report; GM /mapopt text 1 to test)
MAP_NUMBERS = True        # province number as the last two characters of the strategic-map names

def province_number(pid):
    """1..85: number of a province on its planet (column by column, the order of planet_provinces); the same on every
    planet.  Shown by the client as the last two characters of the province name."""
    try:
        return planet_provinces((pid // 100000) % 1000).index(pid % 100000 + (pid // 100000) % 1000 * 100000) + 1
    except ValueError:
        return 0

def build_strategic_map(s):
    """strategic map (sent as class-B 0x2c sub 0, a superset of 0x2d): every province of the commander's planet with its owner (0 = aliens) and the commander's position.
    record: u32 province, u8, s8 name, u8, u32 OWNER nation, u8, u8 battle (0), u8 k, k x {u32 nation, u8 heroes, u8}"""
    cmd = getattr(s, "cmd", {"nation": 1})
    if getattr(s, "sim_board", False):
        import traceback as _tb                    # (user 2026-10-26 12:42) who replaces the sim board with the real map?
        log("   WARNING: real strategic map built for " + str(getattr(s, "acc", "?")) + " while its Simulation Center board is open: "
            + " <- ".join(f.name for f in _tb.extract_stack(limit=6)[:-1][::-1]))
    # the client draws the planet the hero is ON (not the nation's planet): build the records for that planet,
    # otherwise province ids do not match and no emblem / hero icon is drawn (2026-10-20 14:05, /nation switch).
    planet = current_planet(s)
    here = getattr(s, "cur_province", None) or CAPITALS.get(cmd.get("nation"))
    here = province_of(here) if here else here
    provs = planet_provinces(planet)
    import time as _t
    counts, battles = {}, {}
    for o in list(ONLINE):
        if not getattr(o, "logged_in", False):
            continue
        oc = getattr(o, "cmd", {}) or {}
        # 2026-10-21: a player in a province battle is drawn IN the battle province (the attacker's figure moves
        # onto the province he attacks), not in the province he came from.
        loc = getattr(o, "battle_province", None)
        if loc and not getattr(o, "battle", None) and not any(province_of(m) == loc and not B.get("won")
                                                              for m, B in list(BATTLES.items()) if m < 100000000):
            loc = None                       # (16:55) the battle is over: not drawn in that province any more
        loc = loc or (province_of(o.cur_province) if getattr(o, "cur_province", None) else CAPITALS.get(oc.get("nation")))
        if loc:
            counts.setdefault(loc, {}).setdefault(oc.get("nation", 0), 0)
            counts[loc][oc.get("nation", 0)] += 1
        bp = getattr(o, "battle_province", None)
        if bp:
            battles[bp] = max(battles.get(bp, 0), int(max(0, getattr(o, "battle_until", 0) - _t.time())))
    for _n in npc_active():                  # NPC commanders are drawn like players
        _loc, _tg = npc_location(_n)
        if _loc:
            counts.setdefault(_loc, {}).setdefault(_n["nation"], 0)
            counts[_loc][_n["nation"]] += 1
    # NPC commanders fighting an abstract battle (siege / raid window) in a province: Legend "battle in progress" there
    _now = _t.time()
    for _n in npc_active():
        _tk = _n.get("task") or {}
        if _tk.get("phase") in ("siege", "raid", "battle") and _tk.get("target"):
            _left = int(max(1, (_tk.get("resolve_at") or _tk.get("until") or _now + 60) - _now))
            _pv = province_of(_tk["target"])
            battles[_pv] = max(battles.get(_pv, 0), _left)
    # every running province battle (BATTLES) gets the Legend icon, even when nobody of this planet is "travelling" there
    bstate = {}
    cave_recs = []
    import time as _tm
    for mid, B in list(BATTLES.items()):
        if mid >= 100000000 or not (B.get("members") or B.get("ghost")) or B.get("sim") or B.get("won"):
            continue
        pv = province_of(mid)
        left = int(BATTLE_SECONDS - (_tm.monotonic() - B.get("t0", _tm.monotonic())))
        battles[pv] = max(battles.get(pv, 0), left, 1)
        # legend: 0 in progress, 1 open to all, 2 closed to all, 3 full.  Open / closed = the battle commander's
        # Ctrl+F7 mode (1 allow all / 2 refuse all); manual (0) shows "in progress".
        _jm = getattr(B.get("owner"), "join_mode", 0)
        _st = 3 if len(B["members"]) >= 10 else {1: 1, 2: 2}.get(_jm, BATTLE_STATE_IN_PROGRESS)
        # 4 = FORCE OPENED by a council member (client 004347d0: the FORCE OPEN button sends 0x56 [prov][0] = undo
        # when the province's battle state is 4, else [prov][1])
        if B.get("force_open") and _st != 3:
            _st = BATTLE_STATE_FORCE_OPEN
        bstate[pv] = _st
        # 2026-10-21 23:22 (user): a CAVE battle (map id = province + k * 10000, k = 1..3) must also show the Legend
        # on the CAVE k layer of the map.  Section B (client 00569830: u32 id, s8 name, u8 state, u16 timer, u8,
        # u8 n {u32, u8, u8}; owner forced to 0xff, battle flag 1) carries battle records by map id -> one record
        # per cave battle with the CAVE map id (EXPERIMENTAL: which layer draws it is decided by the client).
        if (mid // 10000) % 10 in (1, 2, 3) and planet_of_map(mid) == planet:
            _nm = f"Cave {(mid // 10000) % 10}".encode("latin-1")
            cave_recs.append(struct.pack(">I", mid) + bytes([len(_nm)]) + _nm + bytes([_st])
                             + struct.pack(">H", min(max(left, 1), 65535)) + bytes([0, 0]))
    rec = b""
    for pid in provs:
        owner = province_owner(pid)
        _lang, _enc = session_lang_enc(s)
        name = next((nation_name(n[0], _lang) for n in NATIONS if CAPITALS.get(n[0]) == pid), f"P{(pid % 10000) // 100}-{pid % 100}")
        if pid not in CAPITALS.values():
            # 2026-10-21 23:32 (user): players must SEE the alien garrison: surface (neutral provinces only) and
            # CAVE 1/2/3, e.g. "P8-7 A85% C90/70/100"
            _w = WORLD if WORLD is not None else load_world()
            _cg = "/".join(f"{AL.garrison(_w, pid + k * 10000):.0f}" for k in (1, 2, 3))
            name = (f"{name} A{AL.garrison(_w, pid):.0f}% C{_cg}" if not owner else f"{name} C{_cg}")
        # the client draws the LAST TWO CHARACTERS of this name as the province NUMBER on the map and in the hover label
        # ("%2s" of name + len - 2, 00462e21).  It ended with the cave garrison "100" -> every province showed "00"
        # (user 2026-10-22 15:52) -> the name now ends with the province number 01..85 of its planet.
        nb = (name.encode(_enc, "replace")[:26] + b" %02d" % province_number(pid)) if MAP_NUMBERS \
            else name.encode(_enc, "replace")[:30]
        heroes = sorted(counts.get(pid, {}).items())
        fight = battles.get(pid)
        if fight is not None and fight < 1: fight = 1
        # user 2026-10-23 15:15: a THIRD nation may join a battle between two others.  The client's ENTER (00463440) only
        # offers JOIN when a nation of the record's list is on the player's side (00407e80) -> the player's own nation
        # is listed with 0 heroes in every province with a running battle
        if fight and pid in BATTLES and not any(same_side(n, side_nation(s)) for n, _h in heroes):
            heroes.append((side_nation(s), 0))
        # (user 2026-10-24 19:38: on the strategic map the DEFENDER of an enemy province / NPC battle had no name) the
        # client names the sides from this nation list; a defender with nobody of his in the province (NPC defenders
        # not there yet, players absent) was missing -> the owner is always listed during a battle (neutral: not shown)
        if fight and owner and not any(n == owner for n, _h in heroes):
            heroes.insert(0, (owner, 0))
        # rec+8 (u8 after the id) = MARKER: 1 draws the owner's emblem (gray box when the owner has none) -> capitals only.
        # rec+0x28 (u8 after the name) = XP level cap shown in the tooltip "[Level N or over cannot gain XP here.]"
        #   (0 -> "Level 0 ...", 99 -> line hidden).  Novice planet cap = 35.
        marker = 1 if pid in CAPITALS.values() else 0
        # 0 showed "[Level 0 or over cannot gain XP here.]" on Advanced/Elite; 99 hides the line (no cap there)
        xpcap = PG.NOVICE_BRANCH_CAP if PLANET_TIER.get(planet, 1) == 1 and any(p[0] == planet for p in PLANETS) else 99
        rec += struct.pack(">I", pid) + bytes([marker, len(nb)]) + nb + bytes([xpcap]) + struct.pack(">I", owner) \
            + bytes([0]) + (bytes([1, bstate.get(pid, BATTLE_STATE_IN_PROGRESS)]) + struct.pack(">H", min(fight, 65535)) + bytes([0]) if fight else bytes([0])) \
            + bytes([len(heroes)]) + b"".join(struct.pack(">I", n) + bytes([min(h, 255), 0]) for n, h in heroes)
    log(f"   strategic map -> 0x2d with {len(provs)} provinces of planet {planet} "
        f"(owned: {sum(1 for p in provs if province_owner(p))}), you are at {here}")
    secA = struct.pack(">HH", len(provs), 0) + rec
    secB = struct.pack(">H", len(cave_recs)) + b"".join(cave_recs)
    # class-B 0x2c sub 0 (client 00569c20) = sections A + B like 0x2d, then s8 text (00566460), then per nation
    # u8 n {u32 nation, u16 -> +0x150 provinces owned (war status "x/64"), u16 -> +0x160 FIELDS OWNED,
    # u16 -> +0x164 FIELDS VALUE}, u16 -> +0x94 time to next cycle.  Without it those labels show garbage.
    tally = []
    for nid, _n, _c in NATIONS:
        owned = sum(1 for p in provs if province_owner(p) == nid)
        tally.append(struct.pack(">IHHH", nid, owned, owned, owned * PROVINCE_VALUE))
    # NOTE: sending this as 0x2c sub 0 ([2c][00] + A + B + s8 + tally + u16) made the client hang on entering the
    # capital (2026-10-20 11:46).  Re-checked 2026-10-22 16:00 against the client (00569c20: sub u8, 00569490 A,
    # 00569830 B, 00566460 s8 -> +0x78, 00565410: u8 n {u32 nation, u16 -> +0x150, u16 -> +0x160 FIELDS OWNED,
    # u16 -> +0x164 FIELDS VALUE}, u16 -> +0x94 seconds to the next cycle): the layout IS right; the 10-20 hang came
    # before the 0x66 layout table / open-planet fixes.  MAP_TALLY switches it on (False = the old plain 0x2d).
    try:
        s._war_secB, s._war_planet, s._war_t = secB, planet, time.time()
        s._war_tally = build_war_tally(s, planet, secB)
    except Exception as e:
        s._war_tally = None
        log(f"   war tally error: {e!r}")
    if MAP_TALLY:
        left = int(max(0, CYCLE_SECONDS - (_t.time() - (_cycle_start or _t.time()))))
        return (bytes([0x2C, 0]) + secA + secB + map_title(s, planet) + bytes([len(tally)]) + b"".join(tally)
                + struct.pack(">H", min(left, 65535)))
    return bytes([0x2D]) + secA + secB

def _s16(t):
    b = str(t).encode('latin-1', 'replace')[:1000]
    return struct.pack(">H", len(b)) + b

PROVINCE_INFO_USERS = True
# RESOURCE ABUNDANCE (strategic map RESOURCE page, 0x2E 5 x u32, client 00434a30 prints them with "%d").
# Each province has its own abundance in % per resource (money, ore, silicon, uranium, sulfur).  It is REAL data:
# kill rewards, capture rewards and the province income of that province are multiplied by it.  Values are fixed per
# province (derived from the province id, so they never change between restarts); higher planet tiers are richer in
# uranium / sulfur.  Capitals and special maps (caves, CTF, exercise) are 100 %.
ABUNDANCE_RANGE = ((60, 160), (50, 170), (50, 170), (20, 90), (30, 130))   # tier 1 range per resource (%)
ABUNDANCE_TIER_BONUS = (0, 0, 0, 25, 20)                                   # + per planet tier above 1

def province_abundance(pid):
    import hashlib
    if not pid or pid >= 100000000 or pid in CAPITALS.values():
        return (100, 100, 100, 100, 100)
    tier = PLANET_TIER.get((pid // 100000) % 1000, 1)
    h = hashlib.md5(f"abundance:{pid}".encode()).digest()
    out = []
    for i, (lo, hi) in enumerate(ABUNDANCE_RANGE):
        v = lo + h[i] * (hi - lo) // 255 + ABUNDANCE_TIER_BONUS[i] * (tier - 1)
        out.append(int(v))
    return tuple(out)

def apply_abundance(vals, pid):
    return [int(v * a / 100) for v, a in zip(vals, province_abundance(pid))]

CAVE_ROWS = True          # cave / garrison status as the first rows of the USERS tab (user 2026-10-22 16:07)
STATUS_NATION = 9999      # nation id of those rows: unknown to the client -> empty FACTION column and no minimap dot
                          # (00434b65 / 00434f42 skip a NULL nation)

def cave_status_rows(s, pid):
    """USERS-tab rows: 'Cave1 27/45 4:00' (left / full, time until full again), LEV = % left."""
    base = province_of(pid) if pid < 100000000 else pid
    if base >= 100000000 or base in CAPITALS.values():
        return []
    w = WORLD if WORLD is not None else load_world()
    tier = PLANET_TIER.get((base // 100000) % 1000, 1)
    lang, enc = getattr(s, "lang", "en"), getattr(s, "enc", "latin-1")
    zh, tw = lang in ("zh-cn", "zh-tw"), lang == "zh-tw"
    def eta(g):
        if g >= 99.95:
            return "滿" if tw else ("满" if zh else "full")
        hrs = (100.0 - g) / max(0.1, AL.GARRISON_REGEN_PER_HOUR)
        h, m = int(hrs), int(round((hrs - int(hrs)) * 60))
        if m == 60:
            h, m = h + 1, 0
        return f"{h}:{m:02d}"
    rows = []
    if not province_owner(base):
        g = AL.garrison(w, base)
        rows.append(((f"地表 {g:.0f}% {eta(g)}" if zh else f"Surface {g:.0f}% {eta(g)}"), g))
    for k in (1, 2, 3):
        g = AL.garrison(w, base + k * 10000)
        full = AL.CAVE_TOTAL.get(tier, AL.CAVE_TOTAL[1]).get(k, 30)
        left = int(round(full * g / 100.0))
        rows.append(((f"洞窟{k} {left}/{full} {eta(g)}" if zh else f"Cave{k} {left}/{full} {eta(g)}"), g))
    k = (pid // 10000) % 10 if pid != base else 0
    if 1 <= k <= 3:                              # the info of one cave: that cave first
        rows.insert(0, rows.pop(len(rows) - 4 + k))
    out = []
    for txt, g in rows:
        wire = txt.encode(enc, "replace").decode("latin-1")      # _s8 sends latin-1: bytes in the reader's code page
        out.append((wire, STATUS_NATION, int(round(g)), pid, (0, 0)))
    return out

def province_status_text(pid, lang="en"):
    """text of the province info packet (0x2e trailing s16 -> province info +0x2c): surface garrison and, per cave,
    how many aliens are left after the last fights and how long until they are back to full (user 2026-10-22 15:57)."""
    base = province_of(pid) if pid < 100000000 else pid
    if base >= 100000000 or base in CAPITALS.values():
        return ""
    w = WORLD if WORLD is not None else load_world()
    tier = PLANET_TIER.get((base // 100000) % 1000, 1)
    zh = lang in ("zh-cn", "zh-tw")
    tw = lang == "zh-tw"
    def rec(g):
        if g >= 99.95:
            return "已滿" if tw else ("已满" if zh else "full")
        hrs = (100.0 - g) / max(0.1, AL.GARRISON_REGEN_PER_HOUR)
        h, m = int(hrs), int(round((hrs - int(hrs)) * 60))
        if m == 60:
            h, m = h + 1, 0
        if zh:
            return (f"恢復中，{h}小時{m:02d}分後滿" if tw else f"恢复中，{h}小时{m:02d}分后满")
        return f"recovering, full in {h}h{m:02d}m"
    parts = []
    if not province_owner(base):
        g = AL.garrison(w, base)
        parts.append((f"地表 外星駐軍 {g:.0f}%（{rec(g)}）" if tw else f"地表 外星驻军 {g:.0f}%（{rec(g)}）") if zh
                     else f"Surface aliens {g:.0f}% ({rec(g)})")
    for k in (1, 2, 3):
        g = AL.garrison(w, base + k * 10000)
        full = AL.CAVE_TOTAL.get(tier, AL.CAVE_TOTAL[1]).get(k, 30)
        left = int(round(full * g / 100.0))
        if zh:
            parts.append((f"洞窟{k} 剩餘 {left}/{full} 隻（{rec(g)}）" if tw else f"洞窟{k} 剩余 {left}/{full} 只（{rec(g)}）"))
        else:
            parts.append(f"Cave {k}: {left}/{full} aliens ({rec(g)})")
    if 100000000 > pid != base:                  # the info of one cave: that cave first
        k = (pid // 10000) % 10
        if 1 <= k <= 3:
            parts.insert(0, parts.pop(len(parts) - 4 + k))
    return "\n".join(parts)

# BATTLE TAB TEXT (user 2026-10-27 18:44, screenshot of the original server):
#     --- [A00053] ---
#     Battle Type: Victory
#     Current Field Value  : 1
#     Max Power Rating     : 160
#     Number of POCs(Time) : 5(0:45)
# The text is the trailing s16 of 0x2e (province info +0x2c, drawn in the BATTLE tab); the client has no such strings,
# the original server sent them.  Province code = planet letter (A, B, C ... in PLANETS order, demon stars after) +
# the province number 01..85 of the strategic map.  Battle type by what a battle there is / would be:
#   Victory = capture the POCs (provinces of the aliens or of another nation), Defense = alien / NPC counter-attack
#   on a held province, Ambush, Hive = cave run (kill every alien), Capital = no battles.
# Max Power Rating = the highest power rating (progression.power_rating, PRESTIGE) of the commanders in that battle,
# "-" when nobody fights there.
BATTLE_INFO_TEXT = True

def province_code(pid):
    base = province_of(pid) if pid < 100000000 else pid
    order = [p[0] for p in PLANETS] + [d[4] for d in DEMON_STARS]
    pl = (base // 100000) % 1000
    letter = chr(ord("A") + order.index(pl)) if pl in order else "X"
    k = (pid // 10000) % 10 if pid < 100000000 else 0
    return f"{letter}{province_number(base):05d}" + (f"-C{k}" if 1 <= k <= 3 else "")

def battle_info_text(pid, lang="en"):
    pid = real_map(pid)                          # the Battle Simulation board asks with SIM_BASE + province
    base = province_of(pid) if pid < 100000000 else pid
    zh, tw = lang in ("zh-cn", "zh-tw"), lang == "zh-tw"
    B = BATTLES.get(pid) if pid in BATTLES else None
    k = (pid // 10000) % 10 if pid < 100000000 else 0
    if base in CAPITALS.values():
        typ = ("Capital", "首都（無戰鬥）", "首都（无战斗）")
    elif 1 <= k <= 3:
        typ = ("Hive", "洞窟（消滅全部外星生物）", "洞窟（消灭全部外星生物）")
    elif B is not None and B.get("ambush"):
        typ = ("Ambush", "伏擊", "伏击")
    elif pid in RAIDS or (B is not None and (getattr(B.get("owner"), "alien_meta", None) or {}).get("raid")):
        typ = ("Defense", "防守", "防守")
    else:
        _r = (B or {}).get("rule") or poc_rule(base)          # (18:59) the province's POC ruleset
        typ = (BF.rule_name(_r, "en"), BF.rule_name(_r, "zh-tw"), BF.rule_name(_r, "zh-cn")) if _r \
            else ("Victory", "勝利（佔領 POC）", "胜利（占领 POC）")
    fv = province_field_value(base) if province_owner(base) and base not in CAPITALS.values() else 0
    # Max Power Rating (18:59): the cap of the province; during a battle also what each side has brought
    if base in CAPITALS.values() or 1 <= k <= 3:
        mpr = "-"
    else:
        mpr = str(province_max_pr(base))
        if B is not None and B.get("members"):
            dfd = B.get("defender") or 0
            att = sum(commander_pr(o) for o in B["members"] if not getattr(o, "spectator", False)
                      and not (dfd and same_side(side_nation(o), dfd)))
            dfs = sum(commander_pr(o) for o in B["members"] if not getattr(o, "spectator", False)
                      and dfd and same_side(side_nation(o), dfd))
            mpr += (f"（進攻 {att} / 防守 {dfs}）" if tw else f"（进攻 {att} / 防守 {dfs}）") if zh else f" (att {att} / def {dfs})"
    _vp = (B or {}).get("vp") if B is not None and B.get("rule") == "victory" else None
    if base in CAPITALS.values() or 1 <= k <= 3:
        pocs = "-"
    else:
        n = poc_count(base)
        sec = poc_seconds(base, n)
        pocs = f"{n}({sec // 60}:{sec % 60:02d})"
    if zh:
        lab = (["戰鬥類型", "目前領地價值", "每方最高戰力總和", "POC 數量（時間）"] if tw
               else ["战斗类型", "目前领地价值", "每方最高战力总和", "POC 数量（时间）"])
        t = typ[1] if tw else typ[2]
        out = f"--- [{province_code(pid)}] ---\n{lab[0]}：{t}\n{lab[1]}：{fv}\n{lab[2]}：{mpr}\n{lab[3]}：{pocs}"
        if _vp:
            out += (f"\n勝利點數：進攻 {_vp['att']:.0f} / 防守 {_vp['def']:.0f}" if tw
                    else f"\n胜利点数：进攻 {_vp['att']:.0f} / 防守 {_vp['def']:.0f}")
        return out
    out = (f"--- [{province_code(pid)}] ---\nBattle Type: {typ[0]}\nCurrent Field Value  : {fv}\n"
           f"Max Power Rating     : {mpr}\nNumber of POCs(Time) : {pocs}")
    if _vp:
        out += f"\nVictory Points : {_vp['att']:.0f} / {_vp['def']:.0f}"
    return out

def build_province_info(s, pid):
    """answer to client 0x2c [u32 province] (strategic map: province selected) = class-B 0x2e, client 00567ea0:
      u32 province, u8 (+0x48), u8 (+0x28), u8 (+0x29),
      u16 n users {s8 name, u32 (+0x1c, nation?), u8 (+0x20, level?), u8 (+0x24), u8 (+0x28), u8 (+0x2c), u8 (+0x30),
                   u32 (+0x34), u16 (+0x38), s16 text},
      s16 text, 5 x u32 (+0x4c.., resource abundance?)
    The USERS tab lists the commanders in that province: only this player for now (no multi-player view yet)."""
    cmd = getattr(s, "cmd", {"nation": 1})
    here = getattr(s, "cur_province", None) or CAPITALS.get(cmd.get("nation"))
    here = province_of(here) if here else here
    users = []
    for o in list(ONLINE):
        if not PROVINCE_INFO_USERS or not getattr(o, "logged_in", False):
            continue
        oc = getattr(o, "cmd", {}) or {}
        bp = getattr(o, "battle_province", None)
        loc = bp if bp else (province_of(o.cur_province) if getattr(o, "cur_province", None) else CAPITALS.get(oc.get("nation")))
        if pid not in (loc, bp):
            continue
        _accs, a = get_account(getattr(o, "acc", None))
        br = PG.ensure_commander(a.setdefault("commander", {}))["branches"]
        lv = max(v["level"] for v in br.values())
        _hp = getattr(o, "hero_pos", None) if province_of(getattr(o, "map", 0) or 0) == pid else None
        _dot = (int(max(2, min(125, _hp[0] // 32))), int(max(2, min(125, _hp[1] // 32)))) if _hp else (16, 16)
        users.append((o.acc, oc.get("nation", 1), lv, bp or loc, _dot))
    try:
        if CAVE_ROWS:
            users[:0] = cave_status_rows(s, pid)
    except Exception as e:
        log(f"   cave rows error: {e!r}")
    for _n in npc_active():
        _loc, _tg = npc_location(_n)
        _tk = _n.get("task") or {}
        if pid == _loc:                          # listed where it IS (npc_location: marching = still in its own province)
            users.append((_n["name"], _n["nation"], min(_n["level"], 255), _tg, npc_dot(_n)))
    # +0x48 = terrain THEME of the province map for the preview minimap (vinu.inf type: 12 normal, 13 city/CornerA).
    # 0 made the minimap renderer index a missing tile table -> crash at SG.exe+0x8d533 (FUN_0048d4d0).
    # capital: 13 (city theme; 0 crashed).  Normal province: 0 = take vinu.inf's type like 0x17 does
    # (12 crashed at the same place for 600801, 2026-10-20 12:51).
    # CONFIRMED (00437370): the preview loads the province map with FUN_00498b20(pid, theme=+0x48, CAPITAL=+0x28, 1),
    # the same loader as 0x17.  A capital must be loaded with CAPITAL=1 (Capital.nm + overlay) like in 0x17; with 0
    # the Advanced-planet capital 200808 failed to load and the minimap crashed at SG.exe+0x8d533 (2026-10-20 13:54).
    is_cap = pid in CAPITALS.values()
    # 2026-10-21: theme 0 = take the vinu.inf type (12) - wrong for the 'low family' maps (a1-l, a1-dl, a1-dr ... need 13 like
    # 0x17 sends), their preview then did not change.  Use the same value as the field (map_terrain).  The 00:27 crash with 13
    # happened before the preview was primed with the hero's own province.
    theme = CAPITAL_TERRAIN if is_cap else map_terrain(pid)
    d = bytearray([0x2E]) + struct.pack(">I", pid) + bytes([theme, 1 if is_cap else 0, 0]) + struct.pack(">H", len(users))
    for name, nid, lv, target, (dx, dy) in users:
        # +0x1c nation (dot colour on the minimap, FUN_00434ac0), +0x20 level, +0x24 ?, +0x28 ?, +0x2c x, +0x30 y
        # +0x34 u32 = travel TARGET province, +0x38 u16 = progress: the strategic map draws a white route line
        # from the user's province to the target (0 -> line to province 0 = top-left corner).  Not travelling =
        # target is the province itself.
        d += _s8(name) + struct.pack(">I", nid) + bytes([min(lv, 255), 0, 0, dx, dy]) + struct.pack(">IH", target, 0) + _s16("")
    try:
        _txt = (battle_info_text(pid, getattr(s, "lang", "en")) if BATTLE_INFO_TEXT
                else province_status_text(pid, getattr(s, "lang", "en")) if PROVINCE_TEXT else "")
    except Exception as e:
        log(f"   province status text error: {e!r}")
        _txt = ""
    _tb = _txt.encode(getattr(s, "enc", "latin-1"), "replace")[:900]
    d += struct.pack(">H", len(_tb)) + _tb + struct.pack(">5I", *province_abundance(province_of(pid) if pid < 100000000 else pid))
    log(f"   province info {pid} (owner {province_owner(pid)}) -> 0x2e with {len(users)} user(s)")
    return bytes(d)

GM_COMMANDS = True   # test server: chat commands that change the account (turn off for real players)
# Only these accounts may use GM commands (/spawn, /res, /money, /level, ...). Edit server/gm_accounts.json
# (a JSON list of account names, case-insensitive) - it is re-read on every command, no restart needed.
GM_ACCOUNTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gm_accounts.json")
def is_gm(acc):
    if not acc:
        return False
    try:
        with open(GM_ACCOUNTS_FILE, encoding="utf-8") as f:
            names = json.load(f)
    except Exception:
        return False
    return str(acc).lower() in {str(n).lower() for n in names}
