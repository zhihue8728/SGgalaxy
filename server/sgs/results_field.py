# sgserver part "results_field": battle result, XP, income, national power, territory, medals, prestige, uranium, enter_field.
# Loaded by sgserver.py into ONE shared namespace (exec, in the order of PARTS) - not an importable module;
# every name here is a sgserver global.  Checks: python tools/check_server.py
# ---- BATTLE RESULT window (server class-B 0x25, client 004b0040 -> CBattleResultWnd 0040a430) --------------------
# u8 RESULT, u8 n {u32, u16, u16}, u16, u16, u16, u32,
# 4 x side {u8, u8, u32, u32, u32, u32, u8, s8 name}, 5 x u32 (resources gained?), 6 x u16 (bonuses: Faction /
# Army Strength / Participation / Mercenary / Battle Commander / Faction Controlled Battle, shown "%4.1f%%"),
# u8 n units {u32 uid, u8, u8, u32, u32, u32, u32, u32, u16, u8, u8, u8}.
# The window sends nothing when closed.  Field meanings are being identified: unknown fields carry DIAGNOSTIC
# values (RESULT_DIAG) so a screenshot shows where each lands.  PLACEHOLDER layout until confirmed.
RESULT_DIAG = True
# 2026-10-22 (user): the client only shows the 0x25 window once the battle screen is left -> leave almost at once
RESULT_SHOW_SECONDS = 0.8
PROVINCE_CAPTURE_REWARD = (1000, 200, 200, 20, 50)   # per planet tier (PLACEHOLDER)

# VICTORY XP (design 2026-10-20, PLACEHOLDER): every unit of the division that is still alive when the battle is
# won gets VICTORY_XP x average enemy level, +CAPTURE_XP x level when a province was captured (also for a win by
# POCs only, without kills).  Unit level ups feed the branches like kill XP (progression.add_unit_xp).
# VICTORY_XP -> battlefield.py (2026-10-24, the battle rules in one place)
# VICTORY_KILL_BONUS -> battlefield.py (2026-10-24, the battle rules in one place)
# CAPTURE_XP -> battlefield.py (2026-10-24, the battle rules in one place)

# JOIN_XP_BONUS -> battlefield.py (2026-10-24, the battle rules in one place)

# WOH_XP_BONUS -> battlefield.py (2026-10-24, the battle rules in one place)

# PROVINCE XP LEVEL CAP (client ksLevelLimit "[Level %d or over cannot gain XP here.]"): a unit whose level reaches the
# cap of the battle's planet tier earns no XP there (no farming of weak provinces).  Caps are PLACEHOLDERS.
# XP_LEVEL_CAP -> battlefield.py (2026-10-24, the battle rules in one place)

def xp_level_cap(s):
    m = getattr(s, "map", None) or 0
    if m >= 100000000:                      # caves / CTF / exercise: no cap
        return 999
    return XP_LEVEL_CAP.get(PLANET_TIER.get((m // 100000) % 1000, 1), 999)

def _same_battle(s, o):
    """o and s fight in the same battle right now"""
    b = getattr(s, "battle", None)
    if not (o and b and getattr(o, "battle", None)):
        return False
    return o.battle is b or getattr(o, "map", None) == getattr(s, "map", 0)

def woh_partner(s, a):
    """(user 2026-11-01 16:20) Word of Honor XP bonus (WOH_XP_BONUS): the client's texts - a Subordinate fights with his
    Superior ("fight with your Superior"), and the Superior "also gain(s) an XP bonus when fighting alongside them"
    (ksPyramidWelcomeMailContents).  -> the name of the partner in this battle (Superior first), or "" """
    if s is None or not getattr(s, "battle", None) or not isinstance(a, dict):
        return ""
    sup = (a.get("commander") or {}).get("superior", "")
    if sup and _same_battle(s, find_online(sup)):
        return sup
    me = (getattr(s, "acc", "") or "").lower()
    for o in ONLINE:
        if o is s or not _same_battle(s, o) or not getattr(o, "logged_in", False):
            continue
        oa = load_accounts().get(getattr(o, "acc", None)) or {}
        if me and ((oa.get("commander") or {}).get("superior", "") or "").lower() == me:
            return o.acc
    return ""

def with_superior(s, a):
    return bool(woh_partner(s, a))

STAR_MARK_NAMES = {"mvp": ("本场最佳", "本場最佳", "Best of the battle"),
                   "bronze": ("铜质战功", "銅質戰功", "Bronze record"), "silver": ("银质战功", "銀質戰功", "Silver record"),
                   "gold": ("金质战功", "金質戰功", "Gold record"), "legend": ("传奇战功", "傳奇戰功", "Legendary record"),
                   "ace": ("一骑当千", "一騎當千", "One against a thousand"), "vet30": ("沙场老兵", "沙場老兵", "Veteran"),
                   "vet100": ("百战之魂", "百戰之魂", "Soul of a hundred battles"), "survivor": ("不死鸟", "不死鳥", "Phoenix"),
                   "conqueror": ("开疆拓土", "開疆拓土", "Conqueror"), "guardian": ("守护之盾", "守護之盾", "Shield of the realm"),
                   "star3": ("三星精锐", "三星精銳", "Three-star elite"), "fivestar": ("五星传奇", "五星傳奇", "Five-star legend")}

def battle_rec0(a):
    """uid -> (star, {medal: times}) of every unit before a battle (the battle report shows what changed)."""
    hall = ((a or {}).get("commander") or {}).get("unit_hall") or {}
    out = {}
    for u in (a or {}).get("units", []):
        r = hall.get(str(u.get("hid", u.get("uid")))) or {}
        out[u["uid"]] = (PG.unit_star(u), dict(r.get("mcount") or {}))
    return out

# BATTLE REPORT (user 2026-10-31 15:01 "the result screen must be better - units should not only show XP"): what each unit
# did in this battle, kept on the account (a["last_report"]) for the HUD's result panel (board_mail.report_page).
BATTLE_REPORT_ID = [0]

def battle_report(s, result, reward=None):
    """result: 1 victory, 0 defeat, 2 retreat; reward: the province capture / mercenary resources on top."""
    try:
        st = getattr(s, "battle_stats", None) or {}
        ids = list(dict.fromkeys(st.get("units") or ()))
        if not ids or getattr(s, "sim_snap", None) is not None:
            return
        accs, a = get_account(getattr(s, "acc", None))
        if a is None:
            return
        cmd = a.get("commander") or {}
        hall = cmd.get("unit_hall") or {}
        lost = set(getattr(s, "lost_units", set()) or ())
        kills, xg, xb = st.get("kills") or {}, st.get("xp_gain") or {}, st.get("xp_bonus") or {}
        rec0, xp0 = st.get("rec0") or {}, st.get("xp0") or {}
        top = max([kills.get(i, 0) for i in ids] or [0])
        by = {u["uid"]: u for u in a.get("units", [])}
        units = []
        for uid in ids:
            u = by.get(uid)
            if u is None:
                continue
            r = hall.get(str(u.get("hid", uid))) or {}
            s0, m0 = rec0.get(uid, (PG.unit_star(u), {}))
            got = {k: n - m0.get(k, 0) for k, n in (r.get("mcount") or {}).items() if n - m0.get(k, 0) > 0}
            units.append({"hid": str(u.get("hid", uid)), "name": PG.strip_star_tag(u.get("label") or ""), "chassis": u.get("chassis"),
                          "star": PG.unit_star(u), "star0": s0, "kills": int(kills.get(uid, 0)), "alive": uid not in lost,
                          "lv0": int(xp0.get(uid, (u.get("level", 1), 0))[0]), "lv": int(u.get("level", 1)),
                          "xp": int(xg.get(uid, 0) + xb.get(uid, 0)), "medals": got,
                          "mvp": top > 0 and kills.get(uid, 0) == top,
                          "uxp": int(u.get("xp", 0)), "need": PG.unit_xp_need(int(u.get("level", 1))), "peak": PG.unit_peak(u)})
        BATTLE_REPORT_ID[0] += 1
        # (15:27) the left half: the growth - commander honor, the four branches, the resources in one line
        c = PG.ensure_commander(a.setdefault("commander", {}))
        br0 = st.get("br0") or {}
        br = {k: [int(br0.get(k, (v.get("level", 1), 0))[0]), int(v.get("level", 1)), int(v.get("xp", 0)),
                  PG.branch_xp_need(int(v.get("level", 1)))] for k, v in c["branches"].items()}
        res = [int(g) + int(r) for g, r in zip(st.get("gain") or [0] * 5, reward or [0] * 5)]
        a["last_report"] = {"id": int(time.time() * 1000) % 2000000000, "t": time.time(), "res": int(result),
                            "map": getattr(s, "map", 0) or 0, "bon": list(st.get("bonuses") or [0] * 6), "units": units,
                            "cmd": {"name": wire_name(s.acc) if "wire_name" in globals() else s.acc,
                                    "honor0": int(st.get("honor0", c.get("honor", 0)) or 0), "honor": int(c.get("honor", 0) or 0)},
                            "br": br, "gain": res}
        accs[s.acc] = a
        save_accounts(accs)
    except Exception as e:
        log(f"   battle_report error: {e!r}")

def units_battle_end(s, won, captured=False, defended=False):
    """(user 2026-10-31 14:36) every unit that fought: battles, wins, best battle, survival run, captures, defences -> its
    honor record (PG.unit_battle_end); new medals are announced."""
    st = getattr(s, "battle_stats", None) or {}
    ids = set(st.get("units") or ())
    if not ids or getattr(s, "sim_snap", None) is not None:
        return
    accs, a = get_account(getattr(s, "acc", None))
    if a is None:
        return
    cmd = PG.ensure_commander(a.setdefault("commander", {}))
    lost = set(getattr(s, "lost_units", set()) or ())
    kills = st.get("kills") or {}
    top = max([kills.get(i, 0) for i in ids] or [0])             # (14:44) MVP: the most kills of his units
    heavy = len(lost & ids) * 2 >= len(ids)                       # half of his units were destroyed
    for u in a.get("units", []):
        if u.get("uid") in ids:
            k = kills.get(u["uid"], 0)
            PG.unit_battle_end(cmd, u, won, u["uid"] not in lost and u.get("hp", 1) != 0, k, captured, defended,
                               mvp=k > 0 and k == top, heavy_loss=heavy)
    accs[s.acc] = a
    save_accounts(accs)
    star_notify(s)

def star_notify(s):
    """(user 2026-10-31 14:07 / 14:10) tell the player about unit stars and new record marks (PG.star_news)."""
    try:
        accs, a = get_account(getattr(s, "acc", None))
        if a is None:
            return
        cmd = a.get("commander") or {}
        news = cmd.pop("star_news", None)
        if not news:
            return
        accs[s.acc] = a
        save_accounts(accs)
        for n in news:
            if n[0] == "star":
                _say_lang(s, f"★ {n[1]} 升到 {n[2]} 星！回到 1 级继续成长，装备能力保留，生命与伤害 +{n[2] * 3}%。",
                          f"★ {n[1]} 升到 {n[2]} 星！回到 1 級繼續成長，裝備能力保留，生命與傷害 +{n[2] * 3}%。",
                          f"* {n[1]} rises to star {n[2]}! Back to level 1, equipment kept, HP and damage +{n[2] * 3}%.",
                          rgb=(255, 220, 90))
            else:
                cn, tw, en = STAR_MARK_NAMES.get(n[2], (n[2], n[2], n[2]))
                cnt = n[5] if len(n) > 5 else 1
                xn = f" ×{cnt}" if cnt > 1 else ""
                _say_lang(s, f"【战功】{n[1]} 获得「{cn}」{xn} - 荣誉 +{n[4] / 100:g}", f"【戰功】{n[1]} 獲得「{tw}」{xn} - 榮譽 +{n[4] / 100:g}",
                          f"{n[1]} earns '{en}'{' x%d' % cnt if cnt > 1 else ''} - honor +{n[4] / 100:g}", rgb=(255, 220, 90))
    except Exception as e:
        log(f"   star_notify error: {e!r}")

def unit_xp_bonus(u):
    """computer / biodrive 'XP Bonus' (Lab only on the client; applied by the server): XP x (1 + sum/100)."""
    return 1.0 + sum(float(ITEM_BY_ID.get(i, {}).get("stats", {}).get("XP Bonus", 0) or 0) for i in u.get("items", [])) / 100

def xp_multiplier(a, s=None):
    """total XP multiplier of an account: join-faction bonus (while he is still in that faction) and, later,
    timed boosters (a['xp_boost_until'] = unix time, a['xp_boost_mult'])."""
    import time
    cmd = a.get("commander", {})
    m = 1.0
    if with_superior(s, a):
        m += WOH_XP_BONUS
    if a.get("xp_boost_until", 0) > time.time():
        m += float(a.get("xp_boost_mult", 1.0)) - 1.0
    return m

def weakest_nation(nats):
    """nation with the fewest members among the joinable factions (None when all are equal)."""
    accs = load_accounts()
    cnt = {n[0]: sum(1 for x in accs.values() if isinstance(x, dict) and x.get("commander", {}).get("nation") == n[0])
           for n in nats}
    lo, hi = min(cnt.values()), max(cnt.values())
    return None if lo == hi else min(cnt, key=cnt.get)

def award_victory_xp(s, captured):
    st = getattr(s, "battle_stats", None)
    if not st:
        return
    lv = st.get("enemy_avg", 1)
    accs, a = get_account(getattr(s, "acc", None))
    cmd = PG.ensure_commander(a.setdefault("commander", {}))
    xp = int((VICTORY_XP + (CAPTURE_XP if captured else 0)) * lv * xp_multiplier(a, s))
    alive = getattr(s, "alive_units", set())
    lost = getattr(s, "lost_units", set())
    events = []
    kill_bonus = {}
    for u in a.get("units", []):
        if u["uid"] not in st["units"] or u.get("level", 1) >= xp_level_cap(s):
            continue
        # VICTORY KILL BONUS (user 2026-10-21 23:41): a won battle adds VICTORY_KILL_BONUS of the XP each unit
        # earned by its kills in this battle - every unit that fought and was not destroyed (also units that
        # left through the exit portal earlier).  A retreat or a defeat only keeps the kill XP itself.
        kb = int(st.get("xp_gain", {}).get(u["uid"], 0) * VICTORY_KILL_BONUS) if u["uid"] not in lost else 0
        add = (xp if u["uid"] in alive else 0) + kb
        if add <= 0:
            continue
        kill_bonus[u["uid"]] = kb
        events += PG.add_unit_xp(cmd, u, unit_branch(u["chassis"]), add) or []
        st.setdefault("xp_gain", {})[u["uid"]] = st.setdefault("xp_gain", {}).get(u["uid"], 0) + add
    accs[s.acc] = a
    save_accounts(accs)
    star_notify(s)
    log(f"   victory XP: +{xp} to {len([u for u in st['units'] if u in alive])} unit(s) (enemy avg level {lv}), "
        f"kill bonus {int(VICTORY_KILL_BONUS * 100)}% {kill_bonus}"
        + "".join(f"\n      * {e}" for e in events))

# ---- BATTLE RESULT BONUSES (6 x u16 in 1/100 %, CBattleResultWnd 0040a950: "%+4.1f%%" when != 0) ----------------
# The client only displays them; the formulas are OUR design (the original server rules are not known):
#   Faction Bonus            : JOIN_XP_BONUS while you fight for the weakest faction you joined (client text 50 %)
#   Army Strength Bonus      : fighting a stronger enemy: (enemy unit levels / own side unit levels - 1) x 25 %, max 50 %
#   Participation Bonus      : +5 % per allied commander in the battle, max 25 %
#   Mercenary Bonus          : MERCENARY_BONUS_PCT extra RESOURCES on victory (not XP)
#   Battle Commander Bonus   : +10 % when you command the battle (first in / Ctrl+F7 owner)
#   Faction Controlled Battle: +5 % when the battle is commanded by an ally of your faction
# The XP bonuses (all but Mercenary) are paid at the end of the battle on the XP each unit earned in it; the unit
# tooltip ksXpDesc shows them as "Territorial bonus".
# ARMY_BONUS_PER_RATIO, ARMY_BONUS_MAX -> battlefield.py (2026-10-24, the battle rules in one place)
# PARTICIPATION_BONUS, PARTICIPATION_MAX -> battlefield.py (2026-10-24, the battle rules in one place)
# COMMANDER_BONUS -> battlefield.py (2026-10-24, the battle rules in one place)
# FACTION_CONTROLLED_BONUS -> battlefield.py (2026-10-24, the battle rules in one place)

def battle_bonuses(s):
    """6 percentages (float) in the window's order."""
    _accs, a = get_account(getattr(s, "acc", None))
    cmd = a.get("commander", {})
    st = getattr(s, "battle_stats", None) or {}
    b = getattr(s, "battle", None)
    mine = side_nation(s)
    allies, foes = [], []
    if b:
        for o in b.get("members", ()):
            if o is s or getattr(o, "spectator", False):
                continue
            (allies if same_side(side_nation(o), mine) else foes).append(o)
    own = st.get("lv_sum", 0) + sum((getattr(o, "battle_stats", None) or {}).get("lv_sum", 0) for o in allies)
    enemy = sum((getattr(o, "battle_stats", None) or {}).get("lv_sum", 0) for o in foes) or st.get("enemy_sum", 0)
    faction = JOIN_XP_BONUS * 100 if cmd.get("xp_bonus_nation") and cmd.get("xp_bonus_nation") == cmd.get("nation") else 0
    army = min(ARMY_BONUS_MAX, max(0.0, (enemy / own - 1) * ARMY_BONUS_PER_RATIO)) if own and enemy else 0
    part = min(PARTICIPATION_MAX, PARTICIPATION_BONUS * len(allies))
    merc = MERCENARY_BONUS_PCT if getattr(s, "side_nation", None) else 0
    owner = b.get("owner") if b else None
    is_cmdr = owner is s
    fcb = FACTION_CONTROLLED_BONUS if (owner is not None and not is_cmdr and same_side(side_nation(owner), mine)) else 0
    return [faction, round(army, 1), part, merc, COMMANDER_BONUS if is_cmdr else 0, fcb]

def award_bonus_xp(s):
    """pay the XP bonuses on every unit's battle XP; remembers each unit's XP before the bonus (tooltip)."""
    st = getattr(s, "battle_stats", None)
    if not st:
        return
    bon = battle_bonuses(s)
    st["bonuses"] = bon
    pct = sum(bon) - bon[3]                       # Mercenary is paid in resources
    accs, a = get_account(getattr(s, "acc", None))
    cmd = PG.ensure_commander(a.setdefault("commander", {}))
    mid, events = {}, []
    cap = xp_level_cap(s)
    for u in a.get("units", []):
        if u["uid"] not in st["units"]:
            continue
        mid[u["uid"]] = (u.get("level", 1), u.get("xp", 0))
        g = int(st.get("xp_gain", {}).get(u["uid"], 0) * pct / 100)
        if g > 0 and u.get("level", 1) < cap:
            events += PG.add_unit_xp(cmd, u, unit_branch(u["chassis"]), g) or []
            st.setdefault("xp_bonus", {})[u["uid"]] = st.setdefault("xp_bonus", {}).get(u["uid"], 0) + g
    st["xp_mid"] = mid
    accs[s.acc] = a
    save_accounts(accs)
    star_notify(s)
    log(f"   battle bonuses {bon} -> +{pct:.1f} % XP" + "".join(f"\n      * {e}" for e in events))

def xp_summary(s, retreat=False):
    """user 2026-10-25: the result window only shows bars - say in the chat what the XP was made of."""
    st = getattr(s, "battle_stats", None) or {}
    ids = st.get("units") or []
    base = sum(int(st.get("xp_gain", {}).get(u, 0)) for u in ids)
    bon = [0] * 6 if retreat else (st.get("bonuses") or [0] * 6)
    pct = 0 if retreat else sum(bon) - bon[3]
    extra = int(base * pct / 100)
    kills = sum(st.get("kills", {}).get(u, 0) for u in ids)
    names = ("阵营", "兵力差距", "参战", "佣兵", "指挥官", "阵营主导")
    det = "、".join(f"{n}{b:+.0f}%" for n, b in zip(names, bon) if b and n != "佣兵")
    _say_lang(s, f"经验结算：击杀 {kills}，战斗经验 {base}，加成 {pct:.0f}%（+{extra}）{('：' + det) if det else ''}，合计 {base + extra}。",
              f"經驗結算：擊殺 {kills}，戰鬥經驗 {base}，加成 {pct:.0f}%（+{extra}）{('：' + det) if det else ''}，合計 {base + extra}。",
              f"XP: kills {kills}, battle XP {base}, bonus {pct:.0f}% (+{extra}), total {base + extra}.", (160, 255, 160))

def record_faction(s, won):
    """FACTION record shown by the result window (ksRecord / ksRecordV / ksRecordD / ksRecordTO): victories and
    defeats of the player's faction, overall and against every enemy faction.  Counted once per battle and side."""
    b = getattr(s, "battle", None)
    mine = side_nation(s)
    if not mine:
        return
    if b is not None:
        done = b.setdefault("faction_recorded", set())
        if mine in done:
            return
        done.add(mine)
    w = world_state()
    r = w.setdefault("faction_record", {}).setdefault(str(mine), {"w": 0, "l": 0, "vs": {}})
    r["w" if won else "l"] += 1
    opp = set()
    if b:
        opp = {side_nation(o) for o in b.get("members", ()) if not getattr(o, "spectator", False)
               and not same_side(side_nation(o), mine)}
    o0 = getattr(s, "prov_owner0", 0)
    if o0 and not same_side(o0, mine):
        opp.add(o0)
    for n in opp:
        if n:
            v = r["vs"].setdefault(str(n), [0, 0])
            v[0 if won else 1] += 1
    save_world(w)

def faction_record(nid):
    return world_state().get("faction_record", {}).get(str(nid), {"w": 0, "l": 0, "vs": {}})

def can_upgrade_now(cmd, u):
    opts = UPGRADES.get(DISPLAY.get(u["chassis"], u["chassis"]), [])
    return bool(opts) and PG.unit_quality(cmd, u) >= min(q for _t, q in opts)

def battle_enemy_nation(s, nid):
    """the nation this commander fought in his (last) battle, None for aliens only."""
    try:
        B = getattr(s, "battle", None) or BATTLES.get(getattr(s, "map", None)) or getattr(s, "last_battle", None) or {}
        cands = [B.get("defender"), B.get("npc_attacker"), B.get("npc_side")]
        cands += [side_nation(o) for o in B.get("members", ()) if not getattr(o, "spectator", False)]
        cands += [tg.get("nation") for tg in (B.get("targets") or getattr(s, "targets", {}) or {}).values()
                  if tg.get("npc") is not None]
        cands.append(getattr(s, "prov_owner0", None))
        for c in cands:
            if c and c in CAPITALS.keys() and not same_side(c, nid):
                return int(c)
    except Exception as e:
        log(f"   battle_enemy_nation: {e!r}")
    return None

def build_battle_result(s, won, reward, result=None):
    """class-B 0x25, client parser 004b0040, window CBattleResultWnd (draw 0040a950).  CONFIRMED 2026-10-21:
      u8 RESULT (0 VICTORY, 1 DEFEAT, 2 RETREAT - the three frames of brw-titl.xpf)
      u8 n x {u32 enemy nation, u16 victories, u16 defeats}  -> "Record Against %s :" lines (ksRecordTO)
      u16 faction victories, u16 faction DEFEATS, u16 faction provinces, u32 PRESTIGE
      4 x division {u8 level BEFORE (!= level -> highlighted = level up), u8 LEVEL, u32 xp floor, u32 next level,
                    u32 xp before, u32 xp now (bar animates before -> now), u8, s8 rank}
      5 x u32 resources gained
      6 x u16 bonuses in 1/100 %
      u8 n x unit {u32 uid, u8 level before, u8 level, u32 floor, u32 next, u32 xp before, u32 xp now,
                   u32 xp after BASE gain (before the bonuses; tooltip ksXpDesc base / territorial / total),
                   u16, u8 kills, u8 avg enemy level, u8 CAN UPGRADE (icon + "You can now upgrade this unit in the Lab.")}"""
    st = getattr(s, "battle_stats", None) or {"gain": [0] * 5, "kills": {}, "units": [], "xp0": {}, "honor0": 0}
    gain = [g + r for g, r in zip(st["gain"], reward)]
    accs, a = get_account(getattr(s, "acc", None))
    cmd = PG.ensure_commander(a.setdefault("commander", {}))
    nid = side_nation(s) or getattr(s, "cmd", {"nation": 1}).get("nation", 1)
    rec = faction_record(nid)
    # user 2026-10-23 16:48: the faction panel overflowed with one "Record Against" line per nation.  The client
    # (CBattleResultWnd 0040a950, loop 0040ce40) draws every record 30 px lower (label y 107, value y 122, ...) and the
    # panel only has room for ONE: the original shows the record against the nation fought in THIS battle.
    vs_all = {int(k): v for k, v in rec.get("vs", {}).items() if int(k) in CAPITALS}
    en = battle_enemy_nation(s, nid)
    vs = [(en, vs_all.get(en, (0, 0)))] if en else []
    # RESULT byte = frame of brw-titl.xpf (rendered 2026-10-21): 0 VICTORY, 1 DEFEAT, 2 RETREAT
    d = bytearray([0x25, result if result is not None else (0 if won else 1), len(vs)])
    for n, (vw, vl) in vs:
        d += struct.pack(">IHH", n, min(vw, 65535), min(vl, 65535))
    d += struct.pack(">HHHI", min(rec["w"], 65535), min(rec["l"], 65535), min(owned_provinces(nid), 65535), pr_of(cmd))
    br0 = st.get("br0", {})
    for br in PG.BRANCHES:
        b = cmd["branches"][br]
        lv0, xp0 = br0.get(br, (b["level"], b["xp"]))
        need = PG.branch_xp_need(b["level"])
        d += bytes([min(lv0, 255), min(b["level"], 255)]) + struct.pack(">IIII", 0, need, xp0 if lv0 == b["level"] else 0, b["xp"])
        d += bytes([0]) + _s8e(s, rank_for(s, b["level"], short=True))
    d += struct.pack(">5I", *gain)
    bon = [0] * 6 if result == 2 else (st.get("bonuses") or battle_bonuses(s))   # retreat: no battle bonuses
    d += struct.pack(">6H", *[max(0, min(65535, int(round(x * 100)))) for x in bon])
    units = [u for u in a.get("units", []) if u["uid"] in st["units"]]
    avg = st.get("enemy_avg", getattr(s, "last_kill_level", 1))
    d += bytes([len(units)])
    for u in units:
        lv0, xp0 = st["xp0"].get(u["uid"], (u.get("level", 1), u.get("xp", 0)))
        lvm, xpm = st.get("xp_mid", {}).get(u["uid"], (u.get("level", 1), u.get("xp", 0)))
        lv = u.get("level", 1)
        before = xp0 if lv0 == lv else 0
        mid = xpm if lvm == lv else before
        upg = 1 if can_upgrade_now(cmd, u) and not can_upgrade_now(cmd, dict(u, level=lv0)) else 0
        d += struct.pack(">IBB5IHBBB", u["uid"], min(lv0, 255), min(lv, 255), 0, PG.unit_xp_need(lv),
                         before, u.get("xp", 0), mid, 0, min(st["kills"].get(u["uid"], 0), 255),
                         min(avg, 255), upg)
    return bytes(d)

# ---- PROVINCE INCOME CYCLE (design 2026-10-20, PLACEHOLDER amounts) -----------------------------------------------
# Every CYCLE_SECONDS each online commander earns PROVINCE_INCOME x (provinces his nation owns) x planet tier.
# ---- NATIONAL POWER (国力值) and DEMON STAR TIME (魔星时间) -- design by the user, 2026-10-20 ------------------------
# Holding land earns the nation power.  At POWER_FULL the nation gets 24 h of demon-star time; the stars (Azure Dragon,
# White Tiger, Vermilion Bird, Black Tortoise) are only open during STAR_WINDOWS (server local time) for one hour each.
# The original accrual rule is unknown -> PLACEHOLDER: every income cycle each owned province adds POWER_PER_PROVINCE.
POWER_FULL = 40000                # user 2026-10-27 00:26 (was 30000); also the WAR tab bar maximum
POWER_PER_PROVINCE = 10           # per income cycle (30 min) and owned province
STAR_TIME_SECONDS = 24 * 3600
STAR_WINDOWS = ((12, 0), (19, 0))  # (hour, minute) start; each lasts STAR_WINDOW_MINUTES
STAR_WINDOW_MINUTES = 60
STARS = {"Azure Dragon": "mechanical armour", "White Tiger": "infantry armour", "Vermilion Bird": "flying armour",
         "Black Tortoise": "special equipment (later: fire armour)"}

# FOUR DEMON STARS (claude/DEMON_STAR_PLANETS.md).  User 2026-10-27 11:05 "國家輪流切換，不用固定一顆": every time a
# nation fills its bar it gets the NEXT star of its own rotation (start = its slot on the planet), skipping stars that
# another nation's running demon-star time already holds, so nations take turns on the four stars.
DEMON_STARS = [  # (key, English, zh-tw, zh-cn, star planet id, armour sold in its centre Lab)
    ("azure",     "Azure Dragon",   "青龍", "青龙", 7, "mechanical armour"),   # planet 7 (was 0: its corner = map id 0 = "no map", user 12:41)
    ("tiger",     "White Tiger",    "白虎", "白虎", 1, "infantry armour"),
    ("vermilion", "Vermilion Bird", "朱雀", "朱雀", 5, "flying armour"),
    ("tortoise",  "Black Tortoise", "玄武", "玄武", 4, "fire armour"),
]

def assign_star(nid):
    """called when nid's bar fills: next star in its rotation that no other running demon-star time holds."""
    w = world_state()
    rot = w.setdefault("star_rot", {})
    asg = w.setdefault("star_assign", {})
    busy = {asg.get(str(n)) for n in CAPITALS if n != nid and star_time_left(n) > 0}
    start = rot.get(str(nid), NATION_SLOT.get(nid, 0) if "NATION_SLOT" in globals() else 0)
    pick = None
    for k in range(len(DEMON_STARS)):
        i = (start + k) % len(DEMON_STARS)
        if i not in busy:
            pick = i
            break
    if pick is None:                      # all four held (5+ nations at once): share the next one
        pick = start % len(DEMON_STARS)
    asg[str(nid)] = pick
    rot[str(nid)] = (pick + 1) % len(DEMON_STARS)
    log(f"   demon star of nation {nid}: {DEMON_STARS[pick][1]} (busy {sorted(x for x in busy if x is not None)})")
    return pick

def nation_star(nid):
    """index into DEMON_STARS of the nation's current demon-star time, or None."""
    if star_time_left(nid) <= 0:
        return None
    i = world_state().get("star_assign", {}).get(str(nid))
    if not (isinstance(i, int) and 0 <= i < len(DEMON_STARS)):
        i = assign_star(nid)              # demon-star time from before the rotation existed
        save_world(world_state())
    return i

def star_label(i, lang="en"):
    st = DEMON_STARS[i]
    return {"zh-tw": st[2], "zh-cn": st[3]}.get(lang, st[1])

# ---- DEMON-STAR PLANETS: gameplay (user 2026-10-27, claude/DEMON_STAR_PLANETS.md) --------------------------------
# * during a window the nation enters ITS star (nation_star) through the Dimensional Matrix (or /star) and lands in
#   the corner matching its home capital (capital id % 100000 on the star planet);
# * the provinces are held by demon-star monsters; a province may only be entered if the side holds it or one next
#   to it; a won battle takes it (world["star_owners"] via world.set_province_owner);
# * the centre (col 4 row 4) has the boss; whoever holds it walks into a capital-type map there and its Lab sells the
#   demon-star equipment (the home Lab no longer does);
# * at the end of the window everybody on a star is sent home and the star is reset (progress is not kept).
STAR_CENTER = 404
STAR_CENTER_CAPITAL = True       # held centre = capital-type map (Capital.nm, Lab); False = normal province map

def star_planet(i):
    return DEMON_STARS[i][4]

def star_index_of_planet(planet):
    return next((i for i, d in enumerate(DEMON_STARS) if d[4] == planet), None)

def star_corner(nid, planet):
    return planet * 100000 + CAPITALS.get(nid, 0) % 100000

def star_center(planet):
    return planet * 100000 + STAR_CENTER

def star_reset(planet, nids=()):
    """clear a star planet (owners, garrisons); the given nations hold their landing corner."""
    w = world_state()
    so = w.setdefault("star_owners", {})
    for k in [k for k in so if (int(k) // 100000) % 1000 == planet]:
        del so[k]
    gar = w.get("garrison")
    if isinstance(gar, dict):
        for k in [k for k in gar if str(k).isdigit() and int(k) < 100000000 and (int(k) // 100000) % 1000 == planet]:
            del gar[k]
    for p in [p for p in RAIDS if is_star_province(p) and (p // 100000) % 1000 == planet]:
        RAIDS.pop(p, None)                # running counter-attacks end with the reset
    for nid in nids:
        so[str(star_corner(nid, planet))] = nid
    w.setdefault("star_reset_at", {})[str(planet)] = time.time()
    save_world(w)
    log(f"   demon star planet {planet} reset, corners for {list(nids)}")

def star_nations(planet):
    """nations whose demon star this planet is and which have demon-star time now."""
    return [n for n in CAPITALS if star_time_left(n) > 0 and nation_star(n) is not None and star_planet(nation_star(n)) == planet]

def star_access(s, planet):
    """None when the player's nation may be on this star planet now, else the refusal text (English, tr'd by caller)."""
    nid = getattr(s, "cmd", {}).get("nation", 1)
    if star_time_left(nid) <= 0:
        return "Your faction has no demon-star time. Fill the national power bar first."
    i = nation_star(nid)
    if i is None or star_planet(i) != planet:
        return "This planet is not open yet."
    if not star_window_open():
        return "The demon stars are open 12:00-13:00 and 19:00-20:00 (server time)."
    return None

def star_ensure_open(planet):
    """the window's first visitor resets the planet: corners for every nation that has this star now."""
    now = time.time()
    win = next(((a_, b_) for a_, b_ in star_windows(now) if a_ <= now < b_), None)
    if win and world_state().get("star_reset_at", {}).get(str(planet), 0) < win[0]:
        star_reset(planet, star_nations(planet))

def star_travel(s, planet):
    """Dimensional Matrix TRANSPORT / /star: land in the nation's corner of its demon star. None = done."""
    why = star_access(s, planet)
    if why:
        return why
    star_ensure_open(planet)
    nid = s.cmd.get("nation", 1)
    corner = star_corner(nid, planet)
    if province_owner(corner) is None or not same_side(province_owner(corner), nid):
        set_province_owner(corner, nid)
    log(f"   {getattr(s, 'acc', '?')} travels to demon star planet {planet} -> corner {corner}")
    try:
        s.send(chat_line(0x0A, "Demon star: fight from your corner to the centre province - whoever holds the centre "
                               "can buy demon-star equipment in its Lab.", (255, 200, 60)))
    except Exception:
        pass
    enter_field(s, corner, 0x200, 0x200)
    return None

def star_enter_ok(s, mapid):
    """walking into a star province: held by the player's side, or next to one it holds."""
    nid = side_nation(s)
    if same_side(province_owner(mapid), nid):
        return True
    pl = (mapid // 100000) % 1000
    return any(same_side(province_owner(pl * 100000 + q), nid) for q in PORTAL_LINKS.get(mapid % 100000, ()))

def star_lab_ok(s):
    """Lab at the centre of a demon star held by the player's side: demon-star equipment for sale."""
    m = getattr(s, "map", None)
    return bool(m and is_star_province(m) and m % 100000 == STAR_CENTER and same_side(province_owner(m), side_nation(s)))

def star_lab_key(s):
    """DEMON_STARS key of the star whose held centre Lab the player is in (its own armour + the shared demon items),
    else False.  Holding the centre also opens the H- versions there."""
    if not star_lab_ok(s):
        return False
    i = star_index_of_planet((s.map // 100000) % 1000)
    return DEMON_STARS[i][0] if i is not None else False

def star_evict_all(planet=None):
    """end of a window: everybody on a demon star goes home; the stars are reset (progress is not kept)."""
    for o in list(ONLINE):
        m = getattr(o, "map", None)
        if getattr(o, "logged_in", True) and m and is_star_province(m) and (planet is None or (m // 100000) % 1000 == planet):
            try:
                o.send(chat_line(0x0A, "The demon star has closed. You are back in your capital.", (255, 200, 60)))
                enter_field(o, CAPITALS[o.cmd.get("nation", 1)], 0x200, 0x200, capital=True)
            except Exception as e:
                log(f"   star evict {getattr(o, 'acc', '?')}: {e!r}")
    for pl in ([planet] if planet is not None else sorted(STAR_PLANET_IDS)):
        star_reset(pl)

def world_state():
    global WORLD
    if WORLD is None:
        WORLD = load_world()
    return WORLD

def nation_power(nid):
    return int(world_state().setdefault("power", {}).get(str(nid), 0))

def add_nation_power(nid, amount):
    """returns True when this addition filled the bar (24 h demon-star time starts, bar restarts)"""
    w = world_state()
    p = w.setdefault("power", {})
    p[str(nid)] = int(p.get(str(nid), 0)) + int(amount)
    full = p[str(nid)] >= POWER_FULL
    if full:
        p[str(nid)] -= POWER_FULL
        now = time.time()
        w.setdefault("star_until", {})[str(nid)] = now + STAR_TIME_SECONDS
        w.setdefault("power_full_at", {})[str(nid)] = now      # Ura bonus claimed at login within 24 h
        try:
            assign_star(nid)
        except Exception as e:
            log(f"   assign star error: {e!r}")
        log(f"   NATION POWER FULL: nation {nid} -> demon-star time until {time.strftime('%m-%d %H:%M', time.localtime(now + STAR_TIME_SECONDS))}")
    save_world(w)
    return full

def star_time_left(nid):
    return max(0, int(world_state().get("star_until", {}).get(str(nid), 0) - time.time()))

STAR_FORCE = [0, 0]               # GM /startest: an extra window [start, end] (epoch)

def star_window_open(now=None):
    if STAR_FORCE[0] <= (now or time.time()) < STAR_FORCE[1]:
        return True
    t = time.gmtime((now or time.time()) + 8 * 3600)           # windows are UTC+8 (players), whatever the server TZ
    mins = t.tm_hour * 60 + t.tm_min
    return any(h * 60 + m <= mins < h * 60 + m + STAR_WINDOW_MINUTES for h, m in STAR_WINDOWS)

# DEMON-STAR NOTICES (user 2026-10-27 10:43 "魔星时间没有提示"): the nation is told when its bar fills (online members
# also get the Uranium bonus at once, not only at their next login), when a window opens / is about to close while it
# has demon-star time, and at login.  During demon-star time the WAR tab shows the bar FULL (user: option A).
STAR_CLOSE_WARN_MINUTES = 10

def star_windows(now=None):
    """(start, end) epochs of today's and tomorrow's windows (UTC+8), sorted."""
    now = now or time.time()
    day0 = (now + TZ_OFFSET) // 86400 * 86400 - TZ_OFFSET
    return sorted([(day0 + d * 86400 + h * 3600 + m * 60, day0 + d * 86400 + h * 3600 + m * 60 + STAR_WINDOW_MINUTES * 60)
                   for d in (0, 1) for h, m in STAR_WINDOWS] + ([tuple(STAR_FORCE)] if STAR_FORCE[1] > now - 86400 else []))

def _hm(t):
    return time.strftime("%H:%M", time.gmtime(t + TZ_OFFSET))

def star_status_text(nid, now=None):
    now = now or time.time()
    left = star_time_left(nid)
    if left <= 0:
        return None
    for a_, b_ in star_windows(now):
        if a_ <= now < b_:
            return "Your faction has demon-star time ({}h{:02d}m left). The demon star is OPEN until {} - type /star to enter.".format(
                left // 3600, left % 3600 // 60, _hm(b_))
        if a_ > now and a_ < now + left:
            return "Your faction has demon-star time ({}h{:02d}m left). The demon star opens at {} for 1 hour - type /star then.".format(
                left // 3600, left % 3600 // 60, _hm(a_))
    return "Your faction has demon-star time ({}h{:02d}m left), but no demon-star window falls inside it.".format(
        left // 3600, left % 3600 // 60)

def star_announce(nid):
    until = world_state().get("star_until", {}).get(str(nid), 0)
    nation_say(nid, "National power is FULL! Your faction has demon-star time for 24 hours (until {}).".format(
        time.strftime("%m-%d %H:%M", time.gmtime(until + TZ_OFFSET))), (255, 200, 60))
    i = nation_star(nid)
    if i is not None:
        for o in list(ONLINE):
            if getattr(o, "logged_in", False) and getattr(o, "cmd", {}).get("nation") == nid and not o.w.is_closing():
                o.send(chat_line(0x0A, "This time your faction's demon star is {}.".format(star_label(i, getattr(o, "lang", "en"))),
                                 (255, 200, 60), tr=True))
    for o in list(ONLINE):
        if getattr(o, "logged_in", False) and getattr(o, "cmd", {}).get("nation") == nid and not o.w.is_closing():
            try:
                ura_on_login(o)
                t = star_status_text(nid)
                if t:
                    o.send(chat_line(0x0A, t, (255, 200, 60)))
            except Exception as e:
                log(f"   star announce {getattr(o, 'acc', '?')}: {e!r}")

async def star_notice_cycle():
    """window open / closing soon -> every nation with demon-star time is told."""
    done = set()
    while True:
        await asyncio.sleep(20)
        try:
            now = time.time()
            for a_, b_ in star_windows(now - 86400) + star_windows(now):
                if b_ <= now < b_ + 120 and ("end", b_) not in done:
                    done.add(("end", b_))
                    if star_window_open(now):
                        # (13:18) another window still runs (e.g. GM /startest across 13:00): nobody is sent home
                        log("   demon star window end at %s ignored: another window is still open" % _hm(b_))
                    else:
                        star_evict_all()
                for key, at, text in (("open", a_, "The demon star is OPEN now until {} - use the Dimensional Matrix or type /star."),
                                      ("close", b_ - STAR_CLOSE_WARN_MINUTES * 60,
                                       "The demon star closes in {} minutes ({}).")):
                    if not (at <= now < at + 120) or (key, at) in done:
                        continue
                    done.add((key, at))
                    for nid in list(CAPITALS):
                        if star_time_left(nid) > 0:
                            nation_say(nid, text.format(_hm(b_)) if key == "open"
                                       else text.format(STAR_CLOSE_WARN_MINUTES, _hm(b_)), (255, 200, 60))
                            log(f"   demon star {key} notice -> nation {nid}")
            done = {k for k in done if k[1] > now - 86400}
        except Exception as e:
            log(f"   star notice error: {e!r}")

def star_open(nid):
    """True when the nation's demon-star time is running AND we are inside one of the daily one-hour windows."""
    return star_time_left(nid) > 0 and star_window_open()

# ---- TERRITORY / WAR TAB / SETTLEMENT (user 2026-10-22 19:06) ----------------------------------------------------------
# Strategic map WAR tab (client 00435030, reversed 19:10):
#   CURRENT FIELDS OWNED = own nation +0x160, CURRENT FIELDS VALUE = +0x164, TIME TO NEXT CYCLE = map +0x94 (seconds),
#   OVERALL WAR STATUS = every nation of the commander's planet, sorted by +0x150, text "%d/%d" = +0x150 / +0x154 and
#   the bar = +0x150 / +0x154 (green part).  The client only shows the numbers the server sends: here = FIELDS (provinces
#   occupied, capital not counted) / all provinces of the planet without the capitals -> a territory count, not power.
# Field value: each occupied province is worth FIELD_VALUE_BASE + FIELD_VALUE_PER_HOUR per full hour held, max
# FIELD_VALUE_MAX.  SETTLEMENT just before each demon-star window (STAR_WINDOWS, UTC+8): every nation gains national
# power = its field value x POWER_PER_FIELD_VALUE (so the demon-star time can start right at the window).
FIELD_VALUE_BASE = 10
FIELD_VALUE_PER_HOUR = 1
FIELD_VALUE_MAX = 50
POWER_PER_FIELD_VALUE = 8          # PLACEHOLDER: ~ the old 10 power per province per 30 min over a day
SETTLE_BEFORE_MINUTES = 5          # settlement time = window start - 5 min
TZ_OFFSET = 8 * 3600               # the players' time zone (UTC+8) for windows / settlement, whatever the server's TZ

def province_held_hours(pid):
    w = world_state()
    since = w.setdefault("since", {})
    if str(pid) not in since:
        since[str(pid)] = time.time()          # held before ownership times were recorded: count from now
    return max(0.0, (time.time() - float(since[str(pid)])) / 3600)

def province_field_value(pid):
    return int(min(FIELD_VALUE_MAX, FIELD_VALUE_BASE + FIELD_VALUE_PER_HOUR * int(province_held_hours(pid))))

def nation_fields(nid):
    """(provinces occupied by the nation without its capital, their total field value)"""
    caps = {str(c) for c in CAPITALS.values()}
    pids = [int(k) for k, v in world_state()["owners"].items() if int(v) == nid and k not in caps]
    return len(pids), sum(province_field_value(p) for p in pids)

def planet_field_total(planet):
    caps = set(CAPITALS.values())
    return sum(1 for p in planet_provinces(planet) if p not in caps)

def next_settlement(now=None):
    """epoch of the next settlement (SETTLE_BEFORE_MINUTES before a STAR_WINDOWS start, UTC+8)."""
    now = now or time.time()
    local = now + TZ_OFFSET
    day0 = local - local % 86400
    cands = []
    for dd in (0, 1):
        for h, m in STAR_WINDOWS:
            ts = day0 + dd * 86400 + h * 3600 + m * 60 - SETTLE_BEFORE_MINUTES * 60 - TZ_OFFSET
            if ts > now + 1:
                cands.append(ts)
    return min(cands)

def settle_territory():
    lines = []
    for nid in list(CAPITALS):
        n, val = nation_fields(nid)
        if val and add_nation_power(nid, val * POWER_PER_FIELD_VALUE):
            try:
                star_announce(nid)
            except Exception as e:
                log(f"   star announce error: {e!r}")
        lines.append((nid, n, val))
    log(f"   TERRITORY SETTLEMENT: " + ", ".join(f"nation {nid}: {n} fields value {v} -> +{v * POWER_PER_FIELD_VALUE} power" for nid, n, v in lines))
    for o in list(ONLINE):
        if getattr(o, "logged_in", False) and not o.w.is_closing():
            try:
                nid = getattr(o, "cmd", {}).get("nation", 1)
                n, val = next(((a, b) for x, a, b in lines if x == nid), (0, 0))
                lang = _mail_lang(o)
                txt = {"zh-cn": f"领地结算：{n} 块领地，价值 {val}，国力 +{val * POWER_PER_FIELD_VALUE}（{nation_power(nid)}/{POWER_FULL}）",
                       "zh-tw": f"領地結算：{n} 塊領地，價值 {val}，國力 +{val * POWER_PER_FIELD_VALUE}（{nation_power(nid)}/{POWER_FULL}）"
                       }.get(lang, f"Territory settlement: {n} fields, value {val}, national power +{val * POWER_PER_FIELD_VALUE} ({nation_power(nid)}/{POWER_FULL})")
                o.send(chat_line(0x0A, txt, (255, 220, 120), tr=False))
            except Exception as e:
                log(f"   settlement notice error: {e!r}")

async def settlement_cycle():
    while True:
        wait = next_settlement() - time.time()
        await asyncio.sleep(max(1.0, wait))
        try:
            settle_territory()
        except Exception as e:
            log(f"   settlement error: {e!r}")
        await asyncio.sleep(2)

MAP_WAR_TALLY = True    # send the WAR tab numbers as class-B 0x2c sub 1 right after the 0x2d map (/mapopt war 0|1)

def war_power(nid):
    """WAR tab bar: the national power, shown FULL while the nation's demon-star time runs (user 2026-10-27 option A)."""
    return POWER_FULL if star_time_left(nid) > 0 else min(nation_power(nid), POWER_FULL)

def map_title(s, planet):
    """s8 -> map object +0x78: the text box at the top of the strategic map (client 004229b3 draws it at 189,6 297x18).
    (user 2026-10-27 00:26: the map must say which planet it is)"""
    lang, enc = session_lang_enc(s)
    pl = next((p for p in PLANETS if p[0] == planet), None)
    if pl:
        nm = planet_name(planet, pl[1], s)
    else:                                   # demon-star / closed planets (2026-10-27): star name, not the id
        st = next((i for i, d in enumerate(DEMON_STARS) if d[4] == planet), None)
        if st is not None:
            # user 11:20: on a demon star only "魔星 玄武" (no "当前星球：")
            b = ({"zh-tw": "魔星 ", "zh-cn": "魔星 "}.get(lang, "Demon star ") + star_label(st, lang)).encode(enc, "replace")[:60]
            return bytes([len(b)]) + b
        elif planet in GATE_CLOSED_PLANETS:
            g = GATE_CLOSED_PLANETS[planet]
            nm = {"zh-tw": g[1], "zh-cn": g[2]}.get(lang, g[0]).encode(enc, "replace")
        else:
            nm = str(planet).encode()
    b = nm[:60]                          # user 11:26: just the planet name, no "当前星球：" prefix
    return bytes([len(b)]) + b

def build_war_tally(s, planet, secB):
    """class-B 0x2c sub 1 (client 00569cf0): province DELTA list (00569080: u16 planet, u16 n, u16, n records) - here
    empty - then the cave section B, s8 text, the per-nation tally (00565410: u8 n {u32 nation, u16 +0x150,
    u16 +0x160 FIELDS OWNED, u16 +0x164 FIELDS VALUE}) and u16 seconds to the next settlement (+0x94)."""
    tally = []
    for nid, _n, _c in NATIONS:
        if nation_planet(nid) != planet:
            continue
        n, val = nation_fields(nid)
        # +0x150 = OVERALL WAR STATUS "x/y" + bar: national power (user 2026-10-27 00:26), y = POWER_FULL (0x0F +0x154)
        tally.append(struct.pack(">IHHH", nid, min(war_power(nid), 65535), min(n, 65535), min(val, 65535)))
    # the client prints +0x94 as "%d:%02d" of value/60, value%60 and never counts it down -> send MINUTES, so the
    # tab reads hours:minutes (19:15 screenshot showed 1001:16 = minutes:seconds)
    left = int(max(0, next_settlement() - time.time()) + 59) // 60
    return (bytes([0x2C, 1]) + struct.pack(">HHH", planet, 0, 0) + secB + map_title(s, planet) + bytes([len(tally)])
            + b"".join(tally) + struct.pack(">H", min(left, 65535)))

def send_strategic_map(o):
    o.send(build_strategic_map(o))
    if MAP_WAR_TALLY and getattr(o, "_war_tally", None):
        o.send(o._war_tally)

CYCLE_SECONDS = 30 * 60
PROVINCE_INCOME = (100, 20, 20, 2, 5)
_cycle_start = None

def owned_provinces(nid):
    return sum(1 for v in WORLD["owners"].values() if int(v) == nid)

async def income_cycle():
    global _cycle_start
    import time
    while True:
        _cycle_start = time.time()
        await asyncio.sleep(CYCLE_SECONDS)
        # national power is now gained at the territory settlement before each demon-star window (settle_territory)
        try:
            for _n in NATIONS:                               # the national treasury (FHQ Domestic Policy window)
                if owned_provinces(_n[0]):
                    nation_revenue(_n[0])
            save_world(WORLD)
        except Exception as e:
            log(f"   national revenue error: {e!r}")
        for o in list(ONLINE):
            try:
                if not getattr(o, "logged_in", False) or o.w.is_closing():
                    continue
                nid = getattr(o, "cmd", {}).get("nation", 1)
                n = owned_provinces(nid)
                inc = [0] * 5
                for _pid, _own in WORLD["owners"].items():       # per owned province: tier x its abundance
                    if int(_own) == nid:
                        _pid = int(_pid)
                        _t = PLANET_TIER.get((_pid // 100000) % 1000, 1)
                        inc = [x + y for x, y in zip(inc, apply_abundance([v * _t for v in PROVINCE_INCOME], _pid))]
                accs, a = get_account(o.acc)
                res_add(a, inc)
                accs[o.acc] = a
                save_accounts(accs)
                o.send(build_commander(o.acc, nid, a.get("commander", {}).get("attrs", (0, 0, 0, 0)),
                                       resources=a["resources"]))
                log(f"   income cycle: {o.acc} nation {nid} owns {n} province(s) -> +{inc}")
            except Exception as e:
                log(f"   income cycle error: {e!r}")

def nation_revenue(nid, cycles=1):
    """(user 2026-10-26 12:42: the FHQ Domestic Policy window showed 0 for every national resource) the national
    treasury (world politics[nid]['treasury'] = money, ore, silicon, uranium, sulfur): every income cycle the nation
    collects TAX % (the president's rates, default 10 %) of what its provinces yield.  PLACEHOLDER rule - the players'
    own income is not reduced.  Returns the amounts added."""
    p = politics(nid)
    tax = p.get("tax") or [10, 10, 10]
    inc = [0] * 5
    for _pid, _own in WORLD["owners"].items():
        if int(_own) == nid:
            _pid = int(_pid)
            _t = PLANET_TIER.get((_pid // 100000) % 1000, 1)
            inc = [x + y for x, y in zip(inc, apply_abundance([v * _t for v in PROVINCE_INCOME], _pid))]
    rate = [tax[0], tax[1] if len(tax) > 1 else tax[0], tax[2] if len(tax) > 2 else tax[0], tax[2] if len(tax) > 2 else tax[0],
            tax[2] if len(tax) > 2 else tax[0]]
    add = [int(x * r / 100.0 * cycles) for x, r in zip(inc, rate)]
    p["treasury"] = [int(a_) + b_ for a_, b_ in zip(p.get("treasury") or [0] * 5, add)]
    return add

HONOR_MAX_SHOWN = 2000        # honor counts as "full" at this SHOWN value (also where the +20 % HP bonus ends)
HONOR_DRAIN_SECONDS = 60      # honor upkeep: 1 shown honor per minute (rules below)
def honor_is_full(cmd):
    return cmd.get("honor", 0) >= HONOR_MAX_SHOWN * 100

def alien_battle(s):
    """battle against aliens: alien cave, hunting ground or an unowned province ("territory")."""
    k = getattr(s, "battle_kind", "")
    if k in ("cave", "hunt"):
        return True
    b = getattr(s, "battle", None)
    return k == "province" and bool(b) and not b.get("defender", 0)

def honor_drain_due(a, s):
    """upkeep rules (user, 2026-10-20) - kept deliberately:
       PAID account   : entering an alien CAVE costs 1 honor per minute.
       FREE account   : honor not full -> every battle costs 1 honor per minute;
                        honor full     -> only alien battles (caves and territory) cost 1 honor per minute."""
    cmd = a.get("commander", {})
    if a.get("paid"):
        return getattr(s, "battle_kind", "") == "cave"
    if not honor_is_full(cmd):
        return True
    return alien_battle(s)

async def honor_tick():
    """every minute for each fighting (non-spectating) player: upkeep per honor_drain_due, and +1 shown honor every
    2 minutes spent in a battle (HONOR_BATTLE_SECONDS)."""
    n = 0
    while True:
        await asyncio.sleep(HONOR_DRAIN_SECONDS)
        n += 1
        try:
            accs = None
            for o in list(ONLINE):
                if not getattr(o, "logged_in", False) or o.w.is_closing():
                    continue
                if not getattr(o, "battle", None) or getattr(o, "spectator", False):
                    continue
                accs, a = get_account(o.acc)
                cmd = a.setdefault("commander", {})
                delta = 0
                if n % max(1, HONOR_BATTLE_SECONDS // HONOR_DRAIN_SECONDS) == 0:
                    delta += HONOR_BATTLE_GAIN
                if honor_drain_due(a, o):
                    delta -= HONOR_BATTLE_GAIN
                if delta:
                    cmd["honor"] = max(0, cmd.get("honor", 0) + delta)
                    accs[o.acc] = a
                    log(f"   honor tick: {o.acc} {delta // 100:+d} -> {cmd['honor'] // 100}")
            if accs is not None:
                save_accounts(accs)
        except Exception as e:
            log(f"   honor tick error: {e!r}")

# HONOR (design 2026-10-20, PLACEHOLDER amounts): honor measures service to the faction.  It is shown in the F4
# window as honor // 100 with a progress bar.  Gained by fighting for the faction, lost on defeat and (later)
# when leaving the faction ("YOU WILL LOSE URANIUM AND HONOR IF YOU JOIN THIS FACTION").
# The client shows honor / 100 (F4 0x27 u32, bar f4-st-hn.xpf); amounts below are in those 1/100 units.
# Its only stated effect (khiUserInfoHonor): "Your units will earn extra health for every 100 honor" -> applied
# when units are put on a battle map: +HONOR_HP_PCT % max HP per 100 shown honor, capped at HONOR_HP_CAP %.
HONOR_GAIN = {"province": 500, "hunt": 100, "cave": 100, "ctf": 10, "other": 10}   # per victory (PLACEHOLDER)
HONOR_CAPTURE = 1000      # extra for conquering a province
HONOR_LOSS = 200          # per defeat
HONOR_PER_KILL = 10       # x enemy level
# The client never states the amount.  "extra health for every 100 honor" reads most naturally as a FLAT bonus:
# HONOR_HP_MODE "flat": +HONOR_HP_PER_100 HP per 100 shown honor (cap HONOR_HP_FLAT_CAP HP);
#               "pct" : +HONOR_HP_PCT % max HP per 100 shown honor (cap HONOR_HP_CAP %) - the old, much faster rule.
HONOR_HP_MODE = "pct"
HONOR_HP_PER_100 = 1
HONOR_HP_FLAT_CAP = 100
HONOR_HP_PCT = 1          # +1 % max HP ...
HONOR_PER_PCT = 100       # ... per 100 SHOWN honor (= 10000 internal), user rule 2026-10-20; analysis 2026-10-20: an active player earns
                          # ~100 (lv 10) .. ~600 (lv 100) shown honor per hour -> +50 % after roughly 250 h of play
HONOR_HP_CAP = 20         # user rule: +20 % at 2000 shown honor
HONOR_BATTLE_SECONDS = 120   # user rule: +1 shown honor for every 2 minutes spent in a battle
HONOR_BATTLE_GAIN = 100      # internal units (= 1 shown)
FACTION_PENALTY_HONOR = 0.5     # joining the strongest faction of a planet: lose 50 % honor and uranium
PRESTIGE_PER_KILL = 1

def honor_hp_mult(cmd):
    return 1.0 + min(HONOR_HP_CAP, HONOR_HP_PCT * (max(0, cmd.get("honor", 0)) // (HONOR_PER_PCT * 100))) / 100.0

# unit_full_hp -> sgs/unit_hp.py (2026-10-28)

def honor_hp(cmd, hp):
    """unit max HP including the honor bonus and the 'last stand' bonus of a nation in trouble (NPC plan)."""
    return int(_honor_hp0(cmd, hp) * npc_stand_mult(cmd.get("nation", 0)))

def _honor_hp0(cmd, hp):
    steps = max(0, cmd.get("honor", 0)) // 10000          # number of 'shown 100 honor'
    if HONOR_HP_MODE == "pct":
        return int(hp * honor_hp_mult(cmd))
    return int(hp + min(HONOR_HP_FLAT_CAP, HONOR_HP_PER_100 * steps))

# ---- MEDALS (0x27 u8 n {u32 id, s8 text}; art dcr-%03d.xpf (id // 1000), group (id % 1000) >> 5, frame id & 31.
# CONFIRMED 2026-10-20 (NTF2.dat + in-game): FRAME 0 OF EVERY dcr FILE IS EMPTY (2 bytes) -> ids N*1000 draw nothing;
# use N*1000 + f, f >= 1.  dcr-000..020: frames 1-2 unique ribbons, 3-4 generic placeholders; dcr-021/022: 4 each;
# dcr-023: 8, 024: 20, 025: 14, 026: 24, 027: 16, 028: 16, 029: 8 (sheet: analysis/medals/medal_sheet.png).
# The client has no names/conditions -> design table.  Art chosen to fit the name.
MEDALS = {"first_kill": (13001, "First Blood"), "kills_100": (14001, "Veteran: 100 kills"),
          "first_capture": (2002, "Conqueror: first province"), "captures_10": (4002, "Warlord: 10 provinces"),
          "flawless": (8001, "Survivor: victory without losses"), "advanced": (3002, "Explorer: Advanced planet"),
          "elite": (23008, "Elite: Elite planet"), "reincarnation": (22004, "Reborn"),
          "honor_1000": (21003, "Honor Guard: 1000 honor"), "caves_10": (18002, "Cave Raider: 10 cave wins"),
          "pocs_50": (7002, "POC Master: 50 POCs"), "level_100": (27004, "Centurion: division level 100")}
_MEDAL_BY_TEXT = {txt: mid for mid, txt in MEDALS.values()}
# (user 2026-10-24 21:43) medal names in Chinese (F4 window): stored in English in the account, translated when sent.
# (user 2026-11-01 13:36) every medal has its own name: shown as "name：condition" (the HUD tip: name = title, condition
# below; the game's own windows show the line as it is).  The stored English texts stay the keys (awards, migrations).
MEDAL_SHOW = {   # stored text -> (en, zh-tw, zh-cn)
    "First Blood": ("First Blood Medal: destroyed the first enemy unit", "初陣勳章：首次擊毀敵方單位", "初阵勋章：首次击毁敌方单位"),
    "Veteran: 100 kills": ("Hundred Battles Medal: destroyed 100 enemy units", "百戰勳章：累計擊毀 100 個敵方單位", "百战勋章：累计击毁 100 个敌方单位"),
    "Conqueror: first province": ("Pioneer Medal: captured the first province", "開疆勳章：首次佔領省份", "开疆勋章：首次占领省份"),
    "Warlord: 10 provinces": ("Expansion Medal: captured 10 provinces", "拓土勳章：累計佔領 10 個省份", "拓土勋章：累计占领 10 个省份"),
    "Survivor: victory without losses": ("Flawless Victory Medal: won a battle without losing a unit", "完勝勳章：戰鬥獲勝且沒有損失任何單位", "完胜勋章：战斗获胜且没有损失任何单位"),
    "Explorer: Advanced planet": ("Mars Expedition Medal: advanced to Mars (Advanced planet)", "火星遠征勳章：晉升到火星（進階星球）", "火星远征勋章：晋升到火星（进阶星球）"),
    "Elite: Elite planet": ("Jupiter Expedition Medal: advanced to Jupiter (Elite planet)", "木星遠征勳章：晉升到木星（精英星球）", "木星远征勋章：晋升到木星（精英星球）"),
    "Reborn": ("Rebirth Medal: completed a reincarnation", "重生勳章：完成轉生", "重生勋章：完成转生"),
    "Honor Guard: 1000 honor": ("Honor Guard Medal: reached 1000 honor", "榮譽衛士勳章：榮譽達到 1000", "荣誉卫士勋章：荣誉达到 1000"),
    "Cave Raider: 10 cave wins": ("Cave Assault Medal: won 10 cave battles", "洞穴突擊勳章：洞穴戰勝利 10 次", "洞穴突击勋章：洞穴战胜利 10 次"),
    "POC Master: 50 POCs": ("POC Master Medal: captured 50 POCs", "奪點大師勳章：佔領據點 50 次", "夺点大师勋章：占领据点 50 次"),
    "Centurion: division level 100": ("Centurion Medal: a division reached level 100", "百夫長勳章：任一兵科達到 100 級", "百夫长勋章：任一兵科达到 100 级"),
}

def medal_text(txt, lang):
    sh = MEDAL_SHOW.get(txt)
    if not sh:
        return txt
    return sh[1] if lang == "zh-tw" else sh[2] if lang == "zh-cn" else sh[0]

def fix_medal_ids(cmd):
    """migrate medals saved with the old (invisible) N*1000 ids to the current art ids."""
    for m in cmd.get("medals", []):
        if m[1] in _MEDAL_BY_TEXT:
            m[0] = _MEDAL_BY_TEXT[m[1]]

def award_medal(s, key, a=None, accs=None):
    """Give a medal once.  When a/accs are passed the caller saves the account."""
    own = a is None
    if own:
        accs, a = get_account(getattr(s, "acc", None))
    cmd = a.setdefault("commander", {})
    have = cmd.setdefault("medals", [])
    mid, txt = MEDALS[key]
    if any(m[0] == mid or m[1] == txt for m in have):
        return False
    have.append([mid, txt])
    if own:
        accs[s.acc] = a
        save_accounts(accs)
    log(f"   MEDAL awarded to {getattr(s, 'acc', '?')}: {txt}")
    return True

def check_medals(s, a, accs):
    cmd = a.get("commander", {})
    st = cmd.setdefault("stats", {})
    if st.get("kills", 0) >= 1: award_medal(s, "first_kill", a, accs)
    if st.get("kills", 0) >= 100: award_medal(s, "kills_100", a, accs)
    if st.get("captures", 0) >= 1: award_medal(s, "first_capture", a, accs)
    if st.get("captures", 0) >= 10: award_medal(s, "captures_10", a, accs)
    if st.get("cave_wins", 0) >= 10: award_medal(s, "caves_10", a, accs)
    if st.get("pocs", 0) >= 50: award_medal(s, "pocs_50", a, accs)
    if cmd.get("honor", 0) >= 100000: award_medal(s, "honor_1000", a, accs)
    if cmd.get("tier", 1) >= 2 or cmd.get("reincarnations", 0): award_medal(s, "advanced", a, accs)
    if cmd.get("tier", 1) >= 3 or cmd.get("reincarnations", 0): award_medal(s, "elite", a, accs)
    if any(v.get("level", 1) >= 100 for v in cmd.get("branches", {}).values()): award_medal(s, "level_100", a, accs)

# ---- PRESTIGE RATING (PR): Elo / USCF-like (hlp design notes: "Prestige ... USCF-like ranking") -------------------
# Shown by the client as PRESTIGE (F4 0x27, battle result 0x25, user info).  Every decided battle (not retreats,
# not spectators): expected = 1 / (1 + 10^((opp - PR) / 400)), PR += K x (score - expected), score 1 win / 0 loss.
# Opponent rating: the average PR of enemy players in the battle, else ALIEN_PR_BASE + ALIEN_PR_PER_LEVEL x the
# aliens' average level.  Old counter values are reset to PR_START once (cmd["pr_elo"]).  Values PLACEHOLDER.
PR_START = 1000
PR_K = 32
ALIEN_PR_BASE = 800
ALIEN_PR_PER_LEVEL = 25

def elo_of(cmd):
    if not cmd.get("pr_elo"):
        cmd["pr_elo"] = True
        cmd["prestige"] = PR_START
    return cmd["prestige"]

def pr_of(cmd):
    """PR shown by the client (PRESTIGE field): power rating from the total attribute points (guide table)."""
    return PG.power_rating(PG.ensure_commander(cmd))

def update_pr(s, cmd, won):
    pr = elo_of(cmd)
    b = getattr(s, "battle", None)
    foes = []
    if b:
        for o in b["members"]:
            if o is not s and not getattr(o, "spectator", False) and not same_side(side_nation(o), side_nation(s)):
                foes.append(elo_of(get_account(o.acc)[1].setdefault("commander", {})))
    if foes:
        opp = sum(foes) / len(foes)
    else:
        lv = (getattr(s, "battle_stats", None) or {}).get("enemy_avg", 1)
        opp = ALIEN_PR_BASE + ALIEN_PR_PER_LEVEL * lv
    exp = 1.0 / (1.0 + 10 ** ((opp - pr) / 400.0))
    new = max(0, round(pr + PR_K * ((1 if won else 0) - exp)))
    cmd["prestige"] = new
    log(f"   PR {pr} -> {new} ({'win' if won else 'loss'} vs rating {int(opp)}, expected {exp:.2f})")

# ---- URANIUM (Ura) INCOME (user design 2026-10-20) ------------------------------------------------------------------
# paid account that fights once per 24 h : + PR/3
# faction power bar full (30000)         : + PR*3 for every member (paid and free) who logs in within 24 h
# stored Ura > 600                       : both incomes are halved
URA_DAILY_DIV = 3
URA_FULL_MULT = 3
URA_HALVE_ABOVE = 600
URA_PERIOD = 24 * 3600

def ura_grant(a, amount):
    """add (possibly fractional) Ura to an account dict, halved above URA_HALVE_ABOVE; returns the integer Ura added"""
    if a["resources"][3] > URA_HALVE_ABOVE:
        amount *= 0.5
    tot = a.get("ura_frac", 0.0) + amount
    whole = int(tot)
    a["ura_frac"] = round(tot - whole, 4)
    a["resources"][3] += whole
    return whole

def ura_refresh(s, a, note):
    cmd = a.get("commander", {})
    s.send(build_commander(s.acc, cmd.get("nation", 1), cmd.get("attrs", (0, 0, 0, 0)), resources=a["resources"]))
    s.send(chat_line(0x0A, note, (120, 220, 255)))

def ura_on_battle(s, a):
    """called after a battle result: paid accounts get PR/3 once per 24 h"""
    if not a.get("paid") or getattr(s, "spectator", False):
        return
    now = time.time()
    if now - a.get("ura_daily_at", 0) < URA_PERIOD:
        return
    a["ura_daily_at"] = now
    pr = pr_of(a.get("commander", {}))
    got = ura_grant(a, pr / URA_DAILY_DIV)
    log(f"   Ura daily: {s.acc} PR {pr} -> +{pr / URA_DAILY_DIV:.2f} (whole {got}), Ura {a['resources'][3]}")
    ura_refresh(s, a, f"Daily Uranium reward: +{pr / URA_DAILY_DIV:.1f} (stored {a['resources'][3]}).")

def ura_on_login(s):
    """faction power bar filled within the last 24 h and not yet claimed -> PR*3 (paid and free)"""
    accs, a = get_account(s.acc)
    cmd = a.setdefault("commander", {})
    t = world_state().get("power_full_at", {}).get(str(cmd.get("nation", 1)), 0)
    if not t or time.time() - t > URA_PERIOD or a.get("ura_full_claim", 0) >= t:
        return
    a["ura_full_claim"] = t
    pr = pr_of(cmd)
    ura_grant(a, pr * URA_FULL_MULT)
    accs[s.acc] = a
    save_accounts(accs)
    log(f"   Ura full-power bonus: {s.acc} PR {pr} -> +{pr * URA_FULL_MULT}, Ura {a['resources'][3]}")
    ura_refresh(s, a, f"Your faction filled its power bar! Uranium +{pr * URA_FULL_MULT} (stored {a['resources'][3]}).")

def record_battle(s, won, kind, captured=False):
    accs, a = get_account(getattr(s, "acc", None))
    cmd = PG.ensure_commander(a.setdefault("commander", {}))
    if won:
        cmd["wins"] = cmd.get("wins", 0) + 1
        gain = HONOR_GAIN.get(kind, 1) + (HONOR_CAPTURE if captured else 0)
        cmd["honor"] = cmd.get("honor", 0) + gain
    else:
        cmd["losses"] = cmd.get("losses", 0) + 1
        gain = -min(HONOR_LOSS, cmd.get("honor", 0))
        cmd["honor"] = cmd.get("honor", 0) + gain
    update_pr(s, cmd, won)
    st = cmd.setdefault("stats", {})
    if captured:
        st["captures"] = st.get("captures", 0) + 1
    if won and kind == "cave":
        st["cave_wins"] = st.get("cave_wins", 0) + 1
    bs = getattr(s, "battle_stats", None)
    if won and bs and not getattr(s, "lost_units", set()) and not getattr(s, "spectator", False):
        award_medal(s, "flawless", a, accs)
    check_medals(s, a, accs)
    ura_on_battle(s, a)
    accs[s.acc] = a
    save_accounts(accs)
    log(f"   record: {cmd.get('wins', 0)} wins / {cmd.get('losses', 0)} losses, honor {gain:+d} -> {cmd['honor']}")

def on_kill(s, uid, tid):
    """Unit XP for the kill; unit level ups feed the unit's branch (progression.py)."""
    acc = getattr(s, "acc", None)
    if not acc:
        return
    if not kill_rate_ok(s):
        log(f"   ANTI-CHEAT: {acc} over {KILL_RATE_MAX} kills / {KILL_RATE_WINDOW}s - kill by {uid} not rewarded")
        audit("kill_rate", acc, uid=uid, tid=tid, map=getattr(s, "map", None))
        return
    accs, a = get_account(acc)
    u = next((x for x in a["units"] if x["uid"] == uid), None)
    if u is None:
        return
    cmd = PG.ensure_commander(a.setdefault("commander", {}))
    br = unit_branch(u["chassis"])
    lv = getattr(s, "last_kill_level", 1)
    share = getattr(s, "last_kill_share", 1.0)      # the rest of the kill's XP came as damage XP
    s.last_kill_share = 1.0
    cap = xp_level_cap(s)
    if u.get("level", 1) >= cap:
        if not getattr(s, "cap_warned", False):
            s.cap_warned = True
            s.send(chat_line(0x0A, f"[Level {cap} or over cannot gain XP here.]"))
        events = PG.award_kill(cmd, u, br, lv, 0.0)
    else:
        _m = xp_multiplier(a, s) * unit_xp_bonus(u) * share
        events = PG.award_kill(cmd, u, br, lv, _m)
        _bs = getattr(s, "battle_stats", None)
        if _bs is not None:
            _xg = _bs.setdefault("xp_gain", {})
            _xg[uid] = _xg.get(uid, 0) + int(PG.KILL_XP * max(1, lv) * _m)
    # (PRESTIGE is now an Elo-type rating updated once per battle, see update_pr)
    cmd["honor"] = cmd.get("honor", 0) + HONOR_PER_KILL * lv
    cmd.setdefault("stats", {})["kills"] = cmd.get("stats", {}).get("kills", 0) + 1
    check_medals(s, a, accs)
    gain = [g * lv * (STAR_REWARD_MULT if getattr(s, "map", None) == STAR_MAP or is_star_province(getattr(s, "map", None)) else 1) for g in KILL_REWARD]
    gain = apply_abundance(gain, province_of(s.map) if (getattr(s, "map", 0) or 0) < 100000000 else getattr(s, "map", 0))
    a.setdefault("resources", list(START_RESOURCES))
    res_add(a, gain)
    st = getattr(s, "battle_stats", None)
    if st is not None:
        st["gain"] = [x + g for x, g in zip(st["gain"], gain)]
        st["kills"][uid] = st["kills"].get(uid, 0) + 1
        st["kill_lv"] = st.get("kill_lv", 0) + lv          # TAB: Avg Kill Lvl / POINT
    events.append(f"reward {gain} -> resources {a['resources']}")
    accs[acc] = a
    save_accounts(accs)
    star_notify(s)
    log(f"   XP: unit {uid} ({br}) lv {u['level']} xp {u['xp']}/{PG.unit_xp_need(u['level'])}, kills {u['kills']}"
        + "".join(f"\n      * {e}" for e in events))

def side_nation(s):
    """the nation a player fights for: his own, or for a MERCENARY the side he offered his service to."""
    return getattr(s, "side_nation", None) or getattr(s, "cmd", {}).get("nation", 1)

def enter_field(s, mapid, x, y, capital=False, watch=False, sim=False):
    """Put the player's commander on a field (map).
    0x17: u32 map id, u8 CAPITAL flag (client 004adf20 -> 00498b20: 1 = base "Capital.nm" + per-province overlay
    "%08d.nm"; 0 = the vinu.inf map of the province / special ranges like 2xxxxxxxx exercise.nm),
    u32, u8 online, u8, u32, u32, u8 kind, u8 terrain type (0 = from vinu.inf; capitals need CAPITAL_TERRAIN),
    u8 n + n x 15-byte records.  Then unit list 0x16, 0x18 + 0x20 commander put, 0x0E/4 order sync."""
    cmd = getattr(s, "cmd", {"nation": 1, "look": 1})
    acc = getattr(s, "acc", "zhihue")
    look = max(1, min(cmd["look"], 11))
    # byte +9 = BATTLE mode (client +0x29bdc): 0 = town (left click = info, right click = hero walks),
    # 1 = battle (RTS control: box/click select of combat units, unit orders 0x30).  Without it combat units on a
    # battle map cannot be selected (client 0049b110).
    # own / allied province = town, unless a battle is running there (defenders then enter in battle mode)
    _Bs = BATTLES.get(mapid)
    if is_sim_map(mapid):
        sim = True                        # (19:59) simulation map id: always a simulation of its province
    _real = real_map(mapid)
    # MAX POWER RATING (user 2026-10-27 18:59): a commander may only join a running province battle while his side's
    # power ratings stay within the province's cap (strategic_map BATTLE tab "Max Power Rating")
    if (_Bs is not None and not watch and not sim and not capital and not _Bs.get("won") and not _Bs.get("sim")
            and mapid < 100000000 and s not in (_Bs.get("members") or ())
            and getattr(s, "battle", None) is not _Bs and (_Bs.get("members") or _Bs.get("ghost"))):
        _cap = province_max_pr(mapid)
        _side = side_nation(s)
        _have = side_pr(_Bs, _side)
        _mine = commander_pr(s)
        if _have and _have + _mine > _cap:
            log(f"   {getattr(s, 'acc', '?')} refused on {mapid}: power rating {_have} + {_mine} > max {_cap}")
            _say_lang(s, f"你这一方在这场战斗的战力总和已达上限（{_have} + {_mine} > {_cap}），无法加入。",
                      f"你這一方在這場戰鬥的戰力總和已達上限（{_have} + {_mine} > {_cap}），無法加入。",
                      f"Your side's power rating in this battle is at its limit ({_have} + {_mine} > {_cap}).",
                      (255, 150, 120))
            _back = getattr(s, "map", None)
            if _back and _back != mapid:
                return enter_field(s, _back, *(getattr(s, "hero_pos", None) or (0x200, 0x200)),
                                   capital=(_back in CAPITALS.values()))
            return enter_field(s, CAPITALS.get(cmd.get("nation"), 600000), 0x200, 0x200, capital=True)
    if (STAR_CENTER_CAPITAL and not sim and not watch and is_star_province(mapid) and mapid % 100000 == STAR_CENTER
            and mapid not in BATTLES and mapid not in RAIDS and same_side(province_owner(mapid), side_nation(s))):
        capital = True                    # demon-star centre held by the side: capital map with its Lab
    sim = bool(sim or (_Bs and _Bs.get("sim") and not capital))
    town = (not sim) and (capital or map_kind(mapid) == "sst") or (not sim) and (map_kind(mapid) == "province"
                                                   and same_side(province_owner(mapid), cmd.get("nation"))
                                                   and mapid not in BATTLES and not watch
                                                   and mapid not in RAIDS)       # raided: defend it (battle)
    battle = 0 if town else 1
    s.battle_mode = battle
    old = getattr(s, "map", None)
    if (mapid >= 100000000 or map_kind(mapid) == "hunt") and old is not None and old < 100000000 and map_kind(old) != "hunt":
        # entering a cave / CTF / exercise from a province or capital: remember where to come back to
        s.return_to = (old, getattr(s, "hero_pos", None) or (x, y), old in CAPITALS.values())
    leave_map(s, "changing map")
    B = BATTLES.get(mapid) if battle else None
    joining = bool(B and (B["members"] or B.get("ghost")) and not B.get("won"))
    if joining and B.get("ghost") and not _live(B):
        ghost_handover(B)
    prev = getattr(s, "cur_province", None)
    s.cur_province = mapid if mapid < 100000000 else None
    if prev and s.cur_province and province_of(prev) != province_of(mapid) and map_kind(mapid) == "province":
        s.moved = (province_of(prev), province_of(mapid), __import__("time").time())   # NPC interception watch
    s.prov_owner0 = province_owner(mapid) if mapid < 100000000 else 0     # owner when this player arrived
    # strategic map: a player fighting in a province is shown in the province he came from with a white route
    # line to the battle province (user record travel target); others see the battle flag on that province.
    if not town and s.cur_province and map_kind(mapid) == "province" and not sim:
        s.battle_province = province_of(mapid)
        s.came_from = province_of(prev) if prev else CAPITALS.get(cmd.get("nation"))
        s.battle_until = __import__("time").time() + 30 * 60
        if not watch:
            try:
                _frm = province_of(prev) if prev and (province_of(prev) % 100000) in PORTAL_LINKS.get(province_of(mapid) % 100000, ()) else None
                _g = entry_gate(mapid, side_nation(s), _frm)
                if _g:
                    if (x, y) != _g:
                        log(f"   {getattr(s, 'acc', '?')} enters {mapid} at the gate from {_frm or 'own land'} {_g} (asked {x},{y})")
                    x, y = _g
            except Exception as e:
                log(f"   entry gate error: {e!r}")
    else:
        s.battle_province = None
    # u32 battle start / end time in game ticks (1/100 s, same clock as the 0x0E/4 sync = 1000).  The battle
    # timer divides by (end - start) (client 00429490) -> 0/0 crashed with "integer divide by zero".
    start, end = (1000, 1000 + 30 * 60 * 100) if battle else (0, 0)
    pocs = province_pocs(_real) if (battle and map_kind(_real) == "province") else []
    if sim and pocs and not joining:
        pocs = [p[:5] + (ALIEN_NATION,) + tuple(p[6:]) for p in pocs]     # simulation: the aliens hold every POC
    if joining:
        pocs = [(pid, p["x"], p["y"], p["strength"], POC_TYPE, p["owner"]) for pid, p in B["pocs"].items()]   # pads added below
    if pocs:
        log(f"   POC(s) for {mapid}: {pocs}")
    # u32 after the CAPITAL flag = MAP OWNER nation (client +0x29bd4, CONFIRMED 004adf20): the Faction HQ portal
    # (Portals.por type 7, 004d0b30) refuses "Faction %s denies you access to their headquarters" unless owner and
    # player are the same/allied nation, and owner group == player group marks the map as friendly territory.
    owner = province_owner(mapid) if mapid < 100000000 and not sim else 0
    if sim and not watch and getattr(s, "sim_snap", None) is None:
        sim_snapshot(s, mapid)
    # battery pads / methane vents ride in the same objective list (types 6 / 7), never in s.pocs
    objs = pocs + province_pads(_real, pocs) if pocs else pocs
    # HIVE MARKERS (user 2026-10-22 12:55: the hives must show on the minimap like the POCs): every hive is also an
    # objective type 0 with STRENGTH 0 (= nothing to capture, client 0048f340) owned by the aliens (red); a
    # destroyed hive turns to the player's colour (0x49).  Hive places are chosen here, before 0x17.
    hive_marks = hive_markers(s, mapid, x, y, joining and B, battle, watch)
    objs = objs + [(m["id"], m["x"], m["y"], 0, POC_TYPE, m["owner"]) for m in hive_marks]
    pkt = bytes([0x17]) + struct.pack(">I", mapid) + bytes([1 if capital else 0]) + struct.pack(">I", owner) \
        + bytes([battle, 0]) + struct.pack(">II", start, end) + bytes([POC_BATTLE_KIND if objs else 0,
                                                                    map_terrain(_real, capital), len(objs)]) \
        + b"".join(struct.pack(">IHHHBI", *p) for p in objs)
    s.send(pkt)
    _accs, a = get_account(acc)
    roster = a["units"]
    MECH_APT[acc] = PG.attr(PG.ensure_commander(a.setdefault("commander", {})), 3)
    if ensure_loadouts(a) or not a.get("deploy_init"):
        ensure_deploy(a)
        _accs[acc] = a
        save_accounts(_accs)
    s.send(build_units([roster_rec(u) for u in roster], mech=MECH_APT[acc]))
    for u in roster:                     # equipped items of every unit (class-A 0x1F)
        if u.get("items"):
            s.send(build_set_inventory(u["uid"], u["items"]))
    s.send(build_set_inventory(hero_uid(acc), a.get("hero_items", [])))   # hero item stock (Lab INVENTORY)
    if town:
        # town map: the commander walks around himself (hero, kind 0, art H<look>)
        s.hero_uid = hero_uid(acc)
        s.hero_pos = (x, y)
        s.send(build_put_unit(s.hero_uid, acc, acc, x, y, 0, look, cmd["nation"], speed=town_speed(a)))
        # 0x20 right after 0x18: sets the rank insignia / prestige mark (otherwise uninitialised in the client)
        s.send(build_hero(s.hero_uid, acc, x, y, 0, look, cmd["nation"], 100, hero_mark(acc), hero_rank(acc), hero_title(acc, s)))
    else:
        # battle map: the commander fights with his combat units (kind 1 = 'g' chassis art), not with the avatar.
        # the account's roster (bought at the Factory); a lone g001 when the roster is still empty.
        _cmd_hp = get_account(acc)[1].get("commander", {})
        _cur = lambda u: hp_battle_en(_cmd_hp, u)          # (sgs/unit_hp.py)
        units = [(u["uid"],) + unit_kind(u["chassis"])[1:] + _cur(u) + (unit_stats9(u), unit_speed(u))
                 for u in roster if hp_alive(u)] \
            or [(1, 1, 1, 1000, 1000, None, None)]
        _abil = {u["uid"]: unit_abilities(u) for u in roster}
        s.camo = set()
        s.poc_block = {}
        # never capture: aviation (art kind 2) or ability bit 53 (client +0x15c & 0x200000)
        s.no_capture = {u[0] for u in units if u[1] == 2} | {k for k, v in _abil.items() if (v >> 53) & 1}
        deploy = PG.deploy_limit(PG.ensure_commander(a.setdefault("commander", {})))   # Tactics // 20 + 6
        # the division chosen in the deploy window (unit["deploy"] 1..12) enters first, in slot order
        _slot = {u["uid"]: int(u.get("deploy", 0) or 0) for u in roster}
        if any(_slot.values()):
            units.sort(key=lambda r: (0, _slot.get(r[0])) if _slot.get(r[0]) else (1, 0))
            deploy = min(deploy, sum(1 for r in units if _slot.get(r[0]))) or deploy
        s.reserve = [u for u in units[deploy:] if u[0] != 1]      # F7 reinforcement squads (deploy limit each)
        _by_uid = {u["uid"]: u for u in roster}
        units = [] if watch else units[:deploy]
        s.spectator = bool(watch)
        s.last_reinforce = __import__("time").time()
        s.put_args = {}
        for i, (uid, kind, cls, hp, en, st9, spd) in enumerate(units):
            s.put_args[uid] = {"x": x + 0x30 * (i % 4), "y": y + 0x30 * (i // 4), "kind": kind, "cls": cls, "hp": hp,
                               "hpmax": unit_full_hp(s, _by_uid.get(uid)) or hp,
                               "en": en, "st9": st9, "slot": i, "sight": UNIT_SIGHT.get(uid) or (unit_sight(st9) if st9 else None),
                               "spd": spd, "abil": _abil.get(uid, ABILITY_ATTACK), "label": battle_unit_name(_by_uid.get(uid))}
            s.send(build_put_unit(uid, s.put_args[uid]["label"], acc, x + 0x30 * (i % 4), y + 0x30 * (i // 4), kind, cls, side_nation(s),
                                  hp=hp, hp_max=s.put_args[uid]["hpmax"], energy=en, stats9=st9, slot=i, sight=UNIT_SIGHT.get(uid) or (unit_sight(st9) if st9 else None), speed=spd,
                                  abilities=_abil.get(uid, ABILITY_ATTACK)))
        s.unit_pos = {u[0]: (x + 0x30 * (i % 4), y + 0x30 * (i // 4)) for i, u in enumerate(units)}
        s.entry_pos = (x, y)                  # re-deploy / reinforcement squads enter here
        for _u in [u[0] for u in units]:      # stale transport / shield state of these units from older battles
            CARRIED.pop(_u, None); SHIELDS.pop(_u, None); CLOAKED.pop(_u, None)
            for _p in [p for p, c in CARRIED.items() if c == _u]:
                CARRIED.pop(_p, None)
        s.redeploy_pending = False
        s.unit_cmb = {u[0]: (u[5] or [100] * 9, u[6] or 100) for u in units}
        s.alive_units = {u[0] for u in units}
        s.purged_dead = set()
        s.lost_units = set()                    # destroyed this battle (retreats are not losses) -> Survivor medal
        _a0 = get_account(acc)[1]
        s.cap_warned = False
        s.reinforce_count = 0
        s.battle_stats = {"gain": [0] * 5, "kills": {}, "units": [u[0] for u in units],
                          "xp0": {u["uid"]: (u.get("level", 1), u.get("xp", 0)) for u in _a0.get("units", [])},
                          "rec0": battle_rec0(_a0),      # (10-31 15:01) stars / medal counts before the battle
                          "honor0": _a0.get("commander", {}).get("honor", 0),
                          "br0": {k: (v.get("level", 1), v.get("xp", 0)) for k, v in
                                  PG.ensure_commander(_a0.setdefault("commander", {}))["branches"].items()},
                          "lv_sum": sum(u.get("level", 1) for u in _a0.get("units", [])
                                        if u["uid"] in {q[0] for q in units})}
        s.attacks = {}
        s.targets = {}
        s.alien_meta = None
        kind = map_kind(mapid)
        if joining:
            # join the running battle: same aliens (current HP / position), no new spawn, no second AI
            s.targets = B["targets"]
            # (see npc_side_blocked) NPC units of the joiner's own side leave the battle before he sees it
            _me = side_nation(s)
            _gone = [] if ally_client_ok(s) else \
                [tid for tid, tg in s.targets.items() if tg.get("npc") is not None and same_side(tg.get("nation"), _me)]
            _rel = set()
            for tid in _gone:
                _tg = s.targets.pop(tid, None)
                # (2026-10-25 audit C4) the members already there must drop them too, and the id is never reused
                B.setdefault("dead_aliens", set()).add(tid)
                _pk = bytes([0x19]) + struct.pack(">II", tid, 0)
                for _o in list(B["members"]):
                    if not _o.w.is_closing():
                        _o.send(_pk)
                if _tg is not None and _tg.get("npc") is not None:
                    _rel.add(_tg["npc"])
            if _gone:
                for _i in _rel | {g for g in B.get("npc_ids", [])}:
                    _n = npc_state()["npcs"].get(str(_i))
                    if _n is not None and same_side(_n["nation"], _me):
                        if _i in B.get("npc_ids", []):
                            B["npc_ids"].remove(_i)
                        NPC_RT.pop(_i, None)
                        npc_release(_n, time.time(), 120)
                log(f"   {acc} joins: {len(_gone)} NPC unit(s) of his own side withdrawn (client cannot show NPC allies)")
            _now = time.time()
            for tid, tg in s.targets.items():
                pa = tg.get("put")
                if pa and tg.get("enter_t", 0) > _now:
                    continue                          # still on its way: its delayed_put reaches the joiner too
                if pa:
                    # (2026-10-25 audit C1) where the unit is NOW (mid-leg) and the HP the clients have, not the model's
                    _px, _py = tg["x"], tg["y"]
                    if tg.get("npc") is not None and tg.get("mv"):
                        try:
                            _px, _py = (int(v) for v in _npc_est_pos(tg, _now))
                        except Exception:
                            pass
                    _hp = tg.get("hp_c") if tg.get("hp_c") else tg["hp"]
                    _pk = put_server_unit(tid, pa["name"], pa["owner"], _px, _py, pa["kind"], pa["num"],
                                          pa["nation"], hp=max(1, int(_hp)), hp_max=pa.get("hpmax"), energy=pa.get("en", 1000), stats9=pa["st9"],
                                          sight=pa["sight"], speed=pa["spd"], abilities=pa["abil"])
                    s.send(_pk)
            log(f"   {acc} JOINS the battle on {mapid} ({len(B['members'])} participant(s) already there)")
        elif sim:
            # BATTLE SIMULATION: always a full alien garrison, whoever owns the province
            s.pocs_pending = [(p[1], p[2]) for p in pocs] if pocs else []
            spawn_aliens_initial(s, mapid, "province", x, y, sim=True)
            spawn(alien_ai(s, (getattr(s, "battle_gen", 0) or 0) + 1))
            try:
                s.send(chat_line(0x0A, "BATTLE SIMULATION: units are not lost and no experience or resources are gained.",
                                 (120, 220, 255)))
            except Exception:
                pass
        elif kind == "ctf" or kind == "other":
            # training targets: passive units of another nation a bit further away
            enemy_nation = 1 if cmd["nation"] != 1 else 2
            for k in range(TRAINING_TARGETS):
                tid = 50001 + k
                s.targets[tid] = {"hp": 1500, "x": x + 0x40 * k, "y": y - 0x180, "armor": TARGET_STATS9[0],
                                  "level": 1, "aggressive": False,
                                  "put": {"name": "Target", "owner": "Trainer", "kind": 1, "num": 4,
                                          "nation": enemy_nation, "st9": TARGET_STATS9, "sight": None, "spd": 5,
                                          "abil": 0}}
                s.send(put_server_unit(tid, "Target", "Trainer", x + 0x40 * k, y - 0x180, 1, 4, enemy_nation,
                                      hp=1500, energy=1000, stats9=TARGET_STATS9, speed=5, abilities=0))
        elif kind == "province" and province_owner(mapid) != 0 and mapid in RAIDS and RAIDS[mapid].get("npc") \
                and side_nation(s) == province_owner(mapid):
            # NPC RAID (claude/NPC_NATIONS_PLAN.md): commanders of another nation attack; they fight and capture POCs
            s.pocs_pending = []
            npc_spawn_attackers(s, mapid, x, y, pocs, len(units))
            spawn(npc_ai(s, (getattr(s, "battle_gen", 0) or 0) + 1))
        elif kind == "province" and province_owner(mapid) != 0 and mapid in RAIDS \
                and side_nation(s) == province_owner(mapid):
            # ALIEN RAID: the owner's player defends against the attacking aliens (kill them all to win)
            s.pocs_pending = []
            spawn_aliens_initial(s, mapid, "province", x, y, raid=True)
            spawn(alien_ai(s, (getattr(s, "battle_gen", 0) or 0) + 1))
        elif kind == "province" and province_owner(mapid) != 0:
            # ORIGINAL RULE (user, 2026-10-20): a province that has an owner has no aliens.  The attackers must
            # capture the owner's POC; the defenders hold it until the battle time runs out (kStep_27bb).
            log(f"   PvP battle: {acc} attacks province {mapid} of nation {province_owner(mapid)} (no aliens)")
            if npc_spawn_defenders(s, mapid, x, y, pocs, len(units)):       # NPC commanders defend their nation's province
                spawn(npc_ai(s, (getattr(s, "battle_gen", 0) or 0) + 1))
        else:
            # aliens that fight back: caves (repeatable XP / resources) and unowned provinces (conquest)
            s.pocs_pending = [(p[1], p[2]) for p in pocs] if pocs else []
            spawn_aliens_initial(s, mapid, kind, x, y)
            spawn(alien_ai(s, (getattr(s, "battle_gen", 0) or 0) + 1))
            if kind == "province" and mapid < 100000000:
                try:
                    if npc_spawn_siege(s, mapid, x, y, pocs, len(units)):
                        spawn(npc_ai(s, (getattr(s, "battle_gen", 0) or 0) + 1))
                except Exception as e:
                    log(f"   npc siege spawn error: {e!r}")
        if not joining and not sim and not watch and kind == "province" and mapid in AMBUSH:
            try:
                if npc_spawn_ambush(s, mapid, x, y, pocs, len(units)):
                    spawn(npc_ai(s, (getattr(s, "battle_gen", 0) or 0) + 1))
            except Exception as e:
                log(f"   ambush spawn error: {e!r}")
        s.battle_kind = kind
        log(f"   battle ({kind}) units (deploy limit {deploy}): {[(u[0], u[3], u[4]) for u in units]} + "
            f"{len(s.targets)} enemies {[(t, v['hp'], v['level']) for t, v in s.targets.items()]}")
    if getattr(s, "battle_stats", None) is not None and getattr(s, "targets", None):
        lvs = [t.get("level", 1) for t in s.targets.values()]
        s.battle_stats["enemy_avg"] = max(1, round(sum(lvs) / len(lvs)))
        s.battle_stats["enemy_sum"] = sum(lvs)
    s.t0 = B["t0"] if joining else time.monotonic()
    s.send(bytes([0x0E, 4, 1]) + struct.pack(">I", game_time(s)))
    s.map = mapid
    s.map_since = __import__("time").time()
    s.battle_gen = (getattr(s, "battle_gen", 0) or 0) + 1
    s.poc_won = False
    if joining:
        s.pocs = B["pocs"]
        s.battle = B
        B["members"].add(s)
        try:
            join_replay(s, B)                 # (2026-10-25 audit C1) current orders, cloak / Detector, POC progress
        except Exception as e:
            log(f"   join replay error: {e!r}")
        try:
            spawn_join_squad(B, s)            # (audit C5) after the add: the joiner gets the PUT of his extra squad too
        except Exception as e:
            log(f"   join squad error: {e!r}")
        if B.get("ambush") or (not B["pocs"] and map_kind(mapid) == "province"):
            # user 2026-10-23 16:32: an ambush map has no POC (wipe-out rules) - say so when a player joins
            try:
                _say_lang(s, "这是伏击战：没有据点，消灭全部敌军即胜利。", "這是伏擊戰：沒有據點，消滅全部敵軍即勝利。",
                          "This is an ambush: there are no POCs - destroy every enemy unit to win.")
            except Exception as e:
                log(f"   ambush notice failed: {e!r}")
        try:
            battle_rule_notice(s, B)
        except Exception as e:
            log(f"   rule notice error: {e!r}")
        try:
            set_battle_owner(B, battle_best_commander(B), f"{acc} joined")     # highest rank commands the battle
        except Exception as e:
            log(f"   commander pick error: {e!r}")
    else:
        s.pocs = {p[0]: {"x": p[1], "y": p[2], "strength": p[3], "progress": p[3], "owner": p[5], "capturing": False}
                  for p in pocs}
        s.battle = None
        if battle:
            B = BF.new_battle(map=mapid, t0=s.t0, targets=s.targets, pocs=s.pocs, members={s}, owner=s,
                              hive_marks=hive_marks, defender=province_owner(mapid) if mapid < 100000000 and not sim else 0,
                              sim=sim)
            BATTLES[mapid] = B
            s.battle = B
            if map_kind(mapid) == "province" and B["pocs"] and not (getattr(s, "alien_meta", None) or {}).get("raid") \
                    and not B.get("ambush"):
                B["rule"] = poc_rule(mapid)
                if B["rule"] == "victory":
                    B["vp"] = {"att": float(BF.VP_START), "def": float(BF.VP_START)}
                try:
                    battle_rule_notice(s, B)
                except Exception as e:
                    log(f"   rule notice error: {e!r}")
            npc_battle_started(s, B)
            spawn(battle_timer(B))
            if B["defender"] and not sim and not (getattr(s, "alien_meta", None) or {}).get("raid"):
                notify_defenders(B, s)
            if not sim and map_kind(mapid) == "province":
                asyncio.get_event_loop().call_soon(lambda: pull_into_battle(B, mapid, s))   # (19:26) players standing here
    if battle:
        spawn(battle_frames(s, s.battle_gen))
        if pocs and not joining:
            spawn(poc_loop(s, s.battle_gen))
    join_map(s)
    log(f"   enter field map {mapid} ({'capital' if capital else 'normal'}) at ({x},{y}) look={look} nation={cmd['nation']}")
