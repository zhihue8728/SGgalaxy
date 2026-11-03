"""BATTLEFIELD (2026-10-24, claude/BATTLEFIELD_PLAN.md P1+P2): the battle RULES in one place - which kinds of battle
exist, how each one is won or lost, who may reinforce, and the battle constants.

Pure Python, no server imports (like battle_ai.py).  sgserver.py describes a battle with a plain VIEW dict and gets a
RESULT back; it only applies it (end_battle for every member + the side effects of the result tag).

    view = {
      "kind":     one of KINDS (battle_kind() in sgserver.py),
      "event":    "death" (a server unit died / left) | "leave" (a player left) | "poc" (POC owners changed) | "time"
                | "tick" (the NPC battle loop, every step),
      "same":     same_side(a, b) -> bool,
      "members":  [(key, side_nation, spectator)],     key = anything hashable (the session)
      "defender": nation that owns / defends the province (0 = none),
      "enemies":  server-owned enemy units still alive (aliens / NPCs, allies of the players not counted),
      "pocs":     [owner nation, ...],
      "hives":    hives still standing (none since 18:05), "budget": aliens still to appear (random-spawn caves),
      "waves":    alien waves still to come,
      "blocker":  nation of the ambushers (ambush / blockade),
      "npc_side": nation of the NPC raiders (npc raid),
      "npc_attacker": NPC nation attacking (kind "npc"), with
      "att_alive" / "def_alive": living units of the attackers / everybody else, "att_reserve" / "def_reserve": waves
      left, "att_loss" / "def_loss": share of the units lost (TIME UP without POCs),
    }
    judge(view) -> None (battle goes on) | {"tag": str, "won": {key: bool}, "why": str}
"""

# ------------------------------------------------------------------------------------------------ constants (P2)
# time
BATTLE_SECONDS = 30 * 60          # a battle lasts at most 30 min, then TIME UP (POC majority, ties to the defender)
REINFORCE_COOLDOWN = 60           # s between two F7 squads (players and NPC waves)
REDEPLOY_WAIT = 20                # the client's own default (004a6f20 re-arms 4a4fa0(0x14, 0x3c))
REDEPLOY_WINDOW = 60
# POC capture (server side, client 0048f340 rule)
POC_RADIUS = 48                   # px around the POC centre (the objective covers 3 x 3 tiles of 32 px, 00499350)
POC_RATE = 100                    # MEASURED 2026-10-21 15:03: capture progress per second (a 20000 POC took 200 s)
POC_TICK = 0.5
TAB_POINTS_PER_POC = 50           # TAB ranking points per POC captured
# deaths / anti-cheat
ALIEN_DEATH_FALLBACK = 6.0        # s without a client death report after the server model reached 0 -> server kill
TTK_SAFETY = 3.0                  # a reported death must be reachable by team DPS x time x this
KILL_RATE_WINDOW, KILL_RATE_MAX = 60, 40      # more than 40 rewarded kills per minute per account = no reward
GRENADE_SPLASH = 128              # px splash of Grenade (4e6190)
# stealth (00_LOCKED_SETTINGS: cloaked units are only attacked with a Detector switched on near them)
STEALTH_ACTIONS = (15, 32)        # Cloak / Camouflage toggles
NPC_DETECT_R = 480                # px a server-side Detector reveals cloaked enemy units in
NPC_CLOAK_NEAR = 1000             # px: an NPC unit switches its Cloak / Detector on when an enemy is this near
# server units' targeting
FUTILE_SECONDS = 12.0             # target HP unchanged this long while attacked -> retarget
FUTILE_IGNORE = 15.0
# world snapshots (client 0x1d): true positions / HP, dead NPC units found here
SNAP_ON, SNAP_PERIOD, SNAP_MAX_BAD, SNAP_FRESH = True, 2.5, 3, 4.0
# NPC sides in a battle
NPC_GIVEUP_RATIO = 0.3            # an NPC side regrouping at this force ratio or worse ...
NPC_GIVEUP_AFTER = 20.0           # ... for this long retreats out of the battle
NPC_GIVEUP_GRACE = 90.0           # (2026-10-24) a side that came onto the map fights at least this long before giving up;
                                  # never while a player of its side still fights there (it came to help him)
NPC_WITHDRAW_MAX = 45.0           # s: a withdrawing NPC unit that cannot reach its gate leaves anyway
NPC_WAVES_MAX = 99                # (the reserve decides)
NPC_WAVE_AT = 0.5                 # an NPC calls its next squad when its units fell to this share of one squad
# XP / result (00_LOCKED_SETTINGS: XP by damage dealt, paid on victory, defeat and retreat)
VICTORY_XP = 20
VICTORY_KILL_BONUS = 0.5          # won battle: +50 % of the kill XP each unit earned in it
CAPTURE_XP = 30
JOIN_XP_BONUS = 0.5               # joining the weakest faction = +50 % XP (ksJoinNationBonus)
WOH_XP_BONUS = 0.25               # Word of Honor: fighting with your Superior
XP_LEVEL_CAP = {1: 35, 2: 60, 3: 999}         # planet tier -> unit level that no longer gains XP
ARMY_BONUS_PER_RATIO, ARMY_BONUS_MAX = 25, 50
PARTICIPATION_BONUS, PARTICIPATION_MAX = 5, 25
COMMANDER_BONUS = 10
FACTION_CONTROLLED_BONUS = 5
MERCENARY_BONUS_PCT = 20

# ------------------------------------------------------------------------------------------------ kinds of battle
# win: how the battle ends.  reinforce: F7 / NPC waves allowed.  The order of the rules in judge() follows this table.
KINDS = {
    "hive":     {"zh": "隨機刷怪洞穴", "win": "the whole run has appeared (budget 0) and every alien is dead "
                                        "(18:05: no hive nests any more)", "reinforce": True},
    "waves":    {"zh": "波次洞穴", "win": "every wave destroyed", "reinforce": True},
    "ambush":   {"zh": "伏擊 / 封鎖", "win": "ambushed side: every ambusher dead or gone; ambushers: the time runs out "
                                          "(NPC ambush rules) or the ambushed players leave", "reinforce": True},
    "raid":     {"zh": "突襲（外星怪 / NPC）", "win": "defenders: every raider dead; NPC raiders: every POC held",
                 "reinforce": True},
    "province": {"zh": "省份攻防", "win": "attackers: hold every POC; defenders: no attacker left or TIME UP with the "
                                       "POC majority (ties to the defender); killing every enemy is not enough",
                 "reinforce": True},
    "field":    {"zh": "無 POC 戰場（外星怪領地）", "win": "every enemy destroyed", "reinforce": True},
    "npc":      {"zh": "NPC 攻省（有或沒有玩家）", "win": "attackers: hold every POC, or (no POC) every defender dead; "
                                              "lose: wiped out with no reserve, or a third side holds every POC; "
                                              "TIME UP: POC majority (no POC: smaller share of losses)", "reinforce": True},
}


# ------------------------------------------------------------------------------------------------ POC rulesets
# (user 2026-10-27 18:59 "实作", claude/BATTLE_TYPES.md; original rules from the monx007.com SG guide "POC rulesets")
# Every province battle (kind "province") has one ruleset, fixed per province (server: poc_rule(pid)).  Common rules
# stay: the attackers win at once when one attacking side holds every POC; TIME UP: POC majority, ties to the defender.
RULES = {
    "all_or_nothing": {"en": "All or Nothing", "cn": "全有或全无", "tw": "全有或全無",
                       "help_en": "Attackers must take and hold EVERY POC; the defenders win by keeping just one.",
                       "help_cn": "进攻方必须拿下并守住全部 POC；防守方只要保住一个就获胜。",
                       "help_tw": "進攻方必須拿下並守住全部 POC；防守方只要保住一個就獲勝。"},
    "standard":       {"en": "Standard", "cn": "标准", "tw": "標準",
                       "help_en": "Time up: the attackers need the POC majority, the defenders at least half.",
                       "help_cn": "时间到时，进攻方须占多数 POC，防守方占一半以上即获胜。",
                       "help_tw": "時間到時，進攻方須佔多數 POC，防守方佔一半以上即獲勝。"},
    "standard_enhanced": {"en": "Standard Enhanced", "cn": "标准强化", "tw": "標準強化",
                       "help_en": "Like Standard, and the attackers must hold a POC within 5 minutes - after that, "
                                  "holding none means they lose at once.",
                       "help_cn": "同标准规则；另外进攻方须在 5 分钟内占下一个 POC，之后只要一个都没有就立即判负。",
                       "help_tw": "同標準規則；另外進攻方須在 5 分鐘內佔下一個 POC，之後只要一個都沒有就立即判負。"},
    "victory":        {"en": "Victory", "cn": "胜利点数", "tw": "勝利點數",
                       "help_en": "Both sides start with 800 points: lost units and a POC minority cost points, "
                                  "joining players add points, a side with no units loses 50 per second. 0 points = defeat.",
                       "help_cn": "双方各 800 点：单位阵亡、POC 较少都会扣点，有玩家加入会加点，场上没有单位每秒扣 50。先到 0 的一方战败。",
                       "help_tw": "雙方各 800 點：單位陣亡、POC 較少都會扣點，有玩家加入會加點，場上沒有單位每秒扣 50。先到 0 的一方戰敗。"},
}
ENHANCED_DEADLINE = 5 * 60        # s: original "hold a POC by 10:00" of the 15-minute clock
VP_START = 800
VP_JOIN = 50                      # a player joins the side
VP_UNIT_LOSS = 8                  # per unit lost
VP_POC_DRAIN = 1.0                # per second and per POC the side is behind
VP_EMPTY_DRAIN = 50.0             # per second while the side has no unit on the field (original: after a retreat)
VP_ANNOUNCE = 30                  # s between two score lines in the chat
# Max Power Rating (original BATTLE tab "Max Power Rating : 160"): a side may only bring commanders into a battle while
# the sum of their power ratings (PRESTIGE, progression.power_rating, at least 1 each) stays within the province's cap.
MAX_PR_BY_TIER = {1: 40, 2: 100, 3: 160}

def rule_name(rule, lang="en"):
    r = RULES.get(rule)
    if not r:
        return ""
    return r["cn"] if lang == "zh-cn" else (r["tw"] if lang == "zh-tw" else r["en"])

def _is_def(view, s):
    dfd = view.get("defender") or 0
    return bool(dfd) and view["same"](s, dfd)

def _poc_split(view):
    """(POCs of the attackers, POCs of the defenders).  Defender = the province owner; 0 = the aliens."""
    dfd, same = view.get("defender") or 0, view["same"]
    pocs = view.get("pocs") or []
    d = sum(1 for o in pocs if (same(o, dfd) if dfd else not o))
    return len(pocs) - d, d

def _side_result(view, att_won, tag, why):
    return {"tag": tag, "why": why,
            "won": {k: (not sp) and (_is_def(view, s) != bool(att_won)) for k, s, sp in view["members"]}}

def _judge_rule(view):
    """ruleset checks of a province battle (None = the common rules decide)."""
    rule, ev = view.get("rule"), view.get("event")
    pocs = view.get("pocs") or []
    att, dfn = _poc_split(view)
    if rule == "victory" and ev in ("poc", "time"):
        vp = view.get("vp") or {}
        a, d = vp.get("att", VP_START), vp.get("def", VP_START)
        if a <= 0 or d <= 0 or ev == "time":
            att_won = d <= 0 < a if (a <= 0 or d <= 0) else a > d
            return _side_result(view, att_won, "victory_points",
                                f"Victory points: attackers {a:.0f} / defenders {d:.0f}")
        return None
    if rule == "standard_enhanced" and ev == "poc" and pocs and att == 0 \
            and view.get("elapsed", 0) >= ENHANCED_DEADLINE:
        return _side_result(view, False, "enhanced_forfeit",
                            f"Standard Enhanced: the attackers hold no POC after {ENHANCED_DEADLINE // 60} min")
    if rule == "all_or_nothing" and ev == "time" and pocs:
        return _side_result(view, dfn == 0 and att == len(pocs), "time_up",
                            f"All or Nothing, TIME UP: attackers {att} / defenders {dfn} of {len(pocs)} POC(s)")
    return None


def _all(view, flag=True):
    return {k: flag for k, _side, _spec in view["members"]}


def judge(view):
    """the one place that decides whether a battle is over.  -> None | {"tag", "won": {key: bool}, "why"}"""
    kind, ev, same = view["kind"], view.get("event", "death"), view["same"]
    enemies, members = view.get("enemies", 0), view["members"]
    dfd = view.get("defender") or 0
    # user 2026-10-25 12:19: on the DEFENDER's map the battle is over as soon as the attackers have nothing left on the
    # field - the defender's own NPC units (which counted as 'enemies' of the leaving player) no longer keep it running.
    # "att_units" = server-owned units that are not the defender's side (aliens, a third NPC nation, NPC attackers).
    if kind in ("province", "field") and dfd and ev in ("leave", "death", "tick") and view.get("att_units", 1) == 0 \
            and not view.get("att_pending"):
        fighters = [(k, s) for k, s, spec in members if not spec]
        if all(same(s, dfd) for _k, s in fighters):
            return {"tag": "attackers_gone", "won": {k: same(s, dfd) for k, s, _sp in members},
                    "why": f"no attacker unit left on the defender's map -> the defenders (nation {dfd}) win"}
    if ev == "leave" or (ev == "death" and kind == "ambush"):
        # defenders win as soon as no attacker is left: no server-owned enemy and every fighter on the defender side
        fighters = [(k, s) for k, s, spec in members if not spec]
        if dfd and enemies == 0 and fighters and all(same(s, dfd) for _k, s in fighters):
            return {"tag": "attackers_gone", "won": {k: same(s, dfd) for k, s, _sp in members},
                    "why": f"no attacker left -> the defenders (nation {dfd}) win"}
        if ev == "leave":
            return None
    if kind == "npc":
        return _judge_npc(view)
    if kind == "hive" and ev == "death":            # (POCs still count in a hive cave: poc event below)
        if view.get("hives", 0) <= 0 and view.get("budget", 0) <= 0 and enemies == 0:
            return {"tag": "hive", "won": _all(view), "why": "every alien of the cave run destroyed -> cave victory"}
        return None
    if ev == "death" and enemies == 0 and view.get("waves", 0) > 0:
        return None                                   # the next wave is coming
    if kind == "ambush" and ev == "death" and enemies == 0:
        blk = view.get("blocker")
        return {"tag": "ambush_cleared", "won": {k: (not blk or not same(s, blk)) for k, s, _sp in members},
                "why": f"every ambusher (nation {blk}) destroyed or gone -> the ambushed side wins"}
    if kind == "raid" and ev == "death" and enemies == 0:
        return {"tag": "raid_repelled", "won": _all(view), "why": "every raider destroyed"}
    if kind == "province" and view.get("rule"):
        r = _judge_rule(view)
        if r is not None:
            return r
    if ev == "poc":
        owners = set(view.get("pocs") or [])
        pocs = view.get("pocs") or []
        if view.get("npc_side") and pocs and owners == {view["npc_side"]} and not (dfd and same(view["npc_side"], dfd)):
            # (2026-10-28 00:26) the DEFENDER's NPCs holding their own POCs is not a raid won
            nat = view["npc_side"]
            return {"tag": "npc_raid_won", "won": {k: same(s, nat) and not sp for k, s, sp in members},
                    "why": f"the raiders of nation {nat} hold every POC"}
        winners = {k for k, s, sp in members if pocs and not sp and all(same(s, w) for w in owners)
                   and not (dfd and same(s, dfd))}          # defenders win by time, not by POC
        if winners:
            return {"tag": "pocs_held", "won": {k: k in winners for k, _s, _sp in members},
                    "why": f"all {len(pocs)} POC(s) held"}
        return None
    if ev == "time":
        pocs = view.get("pocs") or []
        won = {}
        for k, s, _sp in members:
            # official rule: the side holding the MAJORITY of the POCs wins; equal counts go to the defender
            own = sum(1 for o in pocs if o and same(s, o))
            other = len(pocs) - own
            is_def = bool(dfd) and same(s, dfd)
            won[k] = is_def if not pocs else ((own >= other) if is_def else (own > other))
        return {"tag": "time_up", "won": won, "why": f"TIME UP, POC owners {list(pocs)}"}
    if ev == "death" and enemies == 0:
        if view.get("pocs"):
            return None                               # design 2026-10-20: POC battles are only won by capturing
        return {"tag": "field_cleared", "won": _all(view), "why": "every enemy destroyed"}
    return None


def _judge_npc(view):
    """a battle an NPC nation started (P3: was ghost_check_end / ghost_time_up), with or without players on the map.
    Events: "tick" / "death" / "poc" (the running checks) and "time".  -> tag "npc_battle" with att_won."""
    A, same, members = view["npc_attacker"], view["same"], view["members"]
    pocs, dfd = view.get("pocs") or [], view.get("defender") or 0
    def res(att_won, why, side=None):
        # (2026-10-25 audit C) attackers lost -> the DEFENDER's side wins (or the third side that holds every POC);
        # a third-party player on the map is not a winner just because he is not of the attackers
        if att_won:
            w = {k: (not sp) and bool(same(s, A)) for k, s, sp in members}
        else:
            win = side if side is not None else dfd
            w = {k: (not sp) and bool(win) and bool(same(s, win)) for k, s, sp in members}
        return {"tag": "npc_battle", "att_won": bool(att_won), "why": why, "won": w,
                "win_side": A if att_won else (side if side is not None else dfd)}
    if view.get("event") == "time":
        if pocs:
            mine = sum(1 for o in pocs if same(A, o))
            return res(mine > len(pocs) - mine, f"TIME UP: nation {A} holds {mine} of {len(pocs)} POC(s)")
        la, ld = view.get("att_loss", 1.0), view.get("def_loss", 1.0)
        return res(la < ld, f"TIME UP without POCs: losses attackers {la:.0%} / defenders {ld:.0%}")
    if pocs and all(same(A, o) for o in pocs):
        return res(True, f"nation {A} holds every POC")
    if pocs:
        # THIRD SIDE (user 2026-10-23 15:15): a player of another nation holds every POC -> the NPC attackers lost
        for _k, X, sp in members:
            if not sp and X and not same(X, A) and not (dfd and same(X, dfd)) and all(o and same(X, o) for o in pocs):
                return res(False, f"nation {X} (third side) holds every POC", side=X)
    live_att = any(not sp and same(s, A) for _k, s, sp in members)
    if view.get("att_alive", 1) == 0 and not view.get("att_reserve") and not live_att:
        return res(False, f"the attackers of nation {A} are wiped out")
    if not pocs and view.get("def_alive", 1) == 0 and not view.get("def_reserve") \
            and not any(not sp for _k, _s, sp in members):
        return res(True, "every defender destroyed")
    return None


def may_reinforce(alive, who="npc", waves_used=0, reserve=1):
    """F7 / NPC waves (user 2026-10-24 04:30): a side with no unit left on the field is wiped out - an NPC cannot send
    new units any more (a player gets the re-deploy box of the original client instead, REDEPLOY_*)."""
    if who == "npc":
        return alive > 0 and waves_used < NPC_WAVES_MAX and reserve > 0
    return True


def rules_table():
    """human-readable list of the battle kinds (docs/10_BATTLEFIELD.md is generated from it)."""
    return [(k, v["zh"], v["win"], v["reinforce"]) for k, v in KINDS.items()]


# ------------------------------------------------------------------------------------------------ battle state (B2)
# A battle is a plain dict (BATTLES[map] = B; s.battle = B).  Every key it can carry is listed here once: the creation
# fields get their defaults from new_battle(); the RUNTIME fields are added while the battle runs (b.get / setdefault).
BATTLE_FIELDS = {
    # creation (new_battle fills the defaults; an unknown key is an error)
    "map":          (None,  "province / map id"),
    "t0":           (None,  "game clock origin (time.monotonic) shared by every member"),
    "targets":      (None,  "server-owned units {uid: tg} (aliens, NPC units, training targets)"),
    "pocs":         (None,  "{poc id: {x, y, owner, strength, progress, capturing}}"),
    "members":      (None,  "set of player sessions on the map"),
    "rule":         (None,  "POC ruleset (RULES key) of a province battle, None = common rules only"),
    "vp":           (None,  "Victory ruleset: {'att': points, 'def': points}"),
    "owner":        (None,  "session that commands the battle (Ctrl+F7, AI loop, snapshots)"),
    "ghost":        (None,  "the server's stand-in session of a simulated NPC battle (None = a player opened it)"),
    "hive_marks":   ([],    "hive minimap markers"),
    "won":          (False, "decided (battlefield.judge) - set only by finish_battle / ghost_finish / npc_won_battle"),
    "defender":     (0,     "nation that owns / defends the province (0 = none)"),
    "sim":          (False, "battle simulation center (no losses)"),
    "npc_attacker": (None,  "NPC nation that attacks (kind 'npc')"),
    "hunt":         (False, "NPC hunt of an alien province (never captures)"),
    "ambush":       (None,  "province id of an ambush / blockade"),
    "opened":       (None,  "time.time() the NPC battle was opened"),
}
BATTLE_RUNTIME = {
    "npc_side": "NPC nation of the raiders / defenders on a player's battle", "npc_raid": "the NPC side attacks",
    "npc_ally": "the NPC side is allied to the players", "npc_ids": "NPC commanders on the map", "npc_meta": "NPC meta",
    "reinf": "NPC reinforcement squads sent", "reinf_at": "next NPC reinforcement time", "sos": "NPC calls for help",
    "brains": "battle_ai.Brain per NPC side", "alien_brain": "battle_ai.Brain of the aliens", "giveup": "NPC give-up timers",
    "_loop": "the battle_loop task", "_bw": "brain_world cache of this AI second", "dead_aliens": "dead server unit ids",
    "snap_req": "last snapshot request", "snap_t": "last snapshot", "snap_n": "snapshots applied",
    "snap_bad": "unreadable snapshots", "faction_recorded": "faction record written",
}

def new_battle(**kw):
    """a battle dict with every creation field (defaults from BATTLE_FIELDS)."""
    bad = set(kw) - set(BATTLE_FIELDS)
    if bad:
        raise KeyError(f"new_battle: unknown battle field(s) {sorted(bad)} - add them to battlefield.BATTLE_FIELDS")
    b = {k: (list(d) if isinstance(d, list) else d) for k, (d, _doc) in BATTLE_FIELDS.items()}
    b.update(kw)
    return b
