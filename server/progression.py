"""Commander / unit progression (F4 window): branch levels, XP, attribute points and the derived values.

Rules (from the player guide the user supplied, 2026-10-20):
  * Four branches (兵科): 0 Infantry INF, 1 Mobile MOB, 2 Aviation AVI, 3 Organic ORG.  Separate from unit levels.
  * A unit gains XP in battle; when the UNIT levels up, its branch gains XP.  Enough branch XP -> branch level up.
  * Every branch level up gives 1 POINT to spend on the four attributes:
      Tactics   : units per battle            = tactics // 20 + 6
      Clout     : unit quality (UQ) and influence:
                    UQ of a unit            = unit level + clout // 2      (Lab upgrades need UQ)
                    influence in a branch   = branch level + clout // 2    (Factory: buy higher units)
      Education : tech level (TL) of a unit = unit level + education // 2 (max item tech level it can carry)
      Mech apt  : carry weight              = base weight * (1 + mech / 120)
  * Novice planet: once ANY branch reaches 20 the commander may go to the Advanced planet (StarPortal, not
    automatic).  Staying on Novice caps every branch at 35.
The XP amounts below are PLACEHOLDERS (the real tables are not known yet) - tune them here.
"""
BRANCHES = ("inf", "mob", "avi", "org")
BRANCH_NAMES = {"inf": "Infantry", "mob": "Mobile", "avi": "Aviation", "org": "Organic"}

KILL_XP = 25                 # unit XP for destroying one enemy unit (x enemy level)
UNIT_MAX_LEVEL = 60          # placeholder cap (original design, restored)
# Power rating (PR) by total attribute points (guide table, lower bounds); beyond 226 it is +1 per 15 points.
PR_TABLE = ((40, 1), (61, 2), (101, 3), (111, 4), (121, 5), (151, 6), (171, 7), (191, 8), (211, 9), (226, 10))
PR_MAX = 26
ATTR_MAX = 120              # each attribute (Tactics/Clout/Education/Mech) tops out at 120 points
REINC_POINTS = 2             # every reincarnation grants 2 bonus attribute points
NOVICE_BRANCH_CAP = 35
ADVANCE_BRANCH_LEVEL = 20
DIVISION_MAX_LEVEL = 100
TIER_NAMES = {1: "Novice", 2: "Advanced", 3: "Elite"}

# UNIT XP CURVE = THE CLIENT'S (user 2026-11-01 17:00 "make the server's unit XP table the same as the client's").
# The client computes a unit's level from its TOTAL XP (unit +0x30, the first u32 of the 0x16 record) with 00550b30:
#   total XP needed to leave level L = W * L * (L + 1) * (2L + 1) / 60   (= W * sum(k^2, k = 1..L) / 10, integer)
# where W is a u16 of the chassis' 0x44 record (+0x38 = G1 of build_unit_catalog).  The Assign XP window predicts with it
# ("level 1 -> 19") and shows the level the XP is worth in brackets.  The server sends W = UNIT_XP_W for every chassis and
# levels units with the same formula, so the client's prediction and the server's result are the same.
# (Before: the server used 100 x level per level, sent W = 11 as a diagnostic number and the chassis WEIGHT as the XP.)
UNIT_XP_W = 11

def unit_xp_cum(level):      # TOTAL XP that ends `level` (client 00550b30)
    level = max(0, int(level))
    return UNIT_XP_W * level * (level + 1) * (2 * level + 1) // 60

def unit_xp_need(level):     # XP from `level` to `level + 1`
    return max(1, unit_xp_cum(level) - unit_xp_cum(level - 1))

def _old_unit_xp_need(level):    # the curve before 2026-11-01 (only to convert old units once)
    return 100 * max(1, int(level))

def unit_xp_total(u):
    """the unit's TOTAL XP as the client counts it (0x16 record, first u32 -> unit +0x30)"""
    ensure_unit(u)
    return unit_xp_cum(u["level"] - 1) + max(0, int(u.get("xp", 0) or 0))

def branch_xp_per_unit_level(new_unit_level):
    return 10 * new_unit_level

def branch_xp_need(level):
    return 40 * level

# ---- data ---------------------------------------------------------------------------------------------------
def ensure_commander(cmd):
    cmd.setdefault("attrs", [0, 0, 0, 0])               # tactics, clout, education, mech (from the create screen)
    cmd.setdefault("points", 0)
    cmd.setdefault("tier", 1)                           # planet tier: 1 Novice, 2 Advanced, 3 Elite
    br = cmd.setdefault("branches", {})
    for b in BRANCHES:
        br.setdefault(b, {"level": 1, "xp": 0})
    return cmd

def ensure_unit(u):
    u.setdefault("level", 1)
    u.setdefault("xp", 0)
    u.setdefault("kills", 0)
    if u.get("xpv", 1) < 2:                  # (11-01) XP into the client's curve once: the same share of the level
        lv = max(1, int(u.get("level", 1) or 1))
        x = max(0, int(u.get("xp", 0) or 0))
        if x:
            need = unit_xp_need(lv)
            u["xp"] = min(need - 1, x * need // _old_unit_xp_need(lv))
        u["xpv"] = 2
    return u

# ---- UNIT STARS (user 2026-10-31 14:07 / 14:10) --------------------------------------------------------------------
# A unit stops at UNIT_MAX_LEVEL while the division goes to 100 and the division XP comes from unit level-ups, so a
# maxed unit had to be sold.  Now a unit that reaches UNIT_MAX_LEVEL rises one STAR: back to level 1 (XP 0), but its
# PEAK level is kept for what the level allows - the tech level of its equipment, its unit quality (Lab chassis), an
# organic unit's organ stage - and every level it climbs again gives division XP again.  Each star: +STAR_BONUS HP and
# damage.  Free and automatic.  Its name shows "*N " in front (the HUD draws it as a star).
STAR_MAX = 5
STAR_BONUS = 0.03

def unit_peak(u):
    """the level that counts for equipment / unit quality / organs: the highest level the unit ever had."""
    return max(int(u.get("level", 1) or 1), int(u.get("peak", 0) or 0))

def unit_star(u):
    return max(0, min(STAR_MAX, int((u or {}).get("star", 0) or 0)))

def star_mult(u):
    return 1.0 + STAR_BONUS * unit_star(u)

def star_tag(u):
    n = unit_star(u)
    return f"*{n} " if n else ""

def strip_star_tag(name):
    import re as _re
    return _re.sub(r"^\*[1-9] ", "", name or "")

# UNIT HONOR RECORD (user 14:10 "a page that keeps the highest-star units and the lifetime kills; past a number a
# special mark and honor"): cmd["unit_hall"][hall id] = the unit's best stars / lifetime kills, kept when the unit is
# sold or dies.  The hall id stays with the unit through Lab upgrades (they give it a new uid).
# Medals of a unit (user 14:10 / 14:36 / 14:44).  Two kinds:
#   "once"   - a milestone of the record: (code, "once", field, threshold, honor x100) - earned one time;
#   "battle" - judged at every battle's settlement, at most once per battle and COUNTED (user 14:44 "every settlement can
#              give it once; the unit's history lists how many times in all"): (code, "battle", test, 0, honor each time).
# Record fields: kills lifetime kills, star, bt battles fought, bk most kills in one battle, sv longest survival run,
# cap provinces taken, dw defences won.  Battle tests: ace 15+ kills in the battle, mvp the most kills of the
# commander's units in the battle (3+), survivor alive although half the commander's units in it were destroyed,
# conqueror in a won battle that took the province, guardian in a won defence of the province.
MEDALS = (("bronze", "once", "kills", 100, 1000), ("silver", "once", "kills", 500, 5000),
          ("gold", "once", "kills", 1000, 10000), ("legend", "once", "kills", 3000, 30000),
          ("vet30", "once", "bt", 30, 1000), ("vet100", "once", "bt", 100, 3000),
          ("star3", "once", "star", 3, 3000), ("fivestar", "once", "star", STAR_MAX, 10000),
          ("ace", "battle", "ace", 0, 300), ("mvp", "battle", "mvp", 0, 100), ("survivor", "battle", "survivor", 0, 200),
          ("conqueror", "battle", "conqueror", 0, 200), ("guardian", "battle", "guardian", 0, 200))
ACE_KILLS = 15
MVP_MIN_KILLS = 3
HALL_KILL_MARKS = tuple((t, c, h) for c, k, f, t, h in MEDALS if f == "kills")   # (older code / tests)
HALL_STAR_MARK = ("fivestar", 10000)
HALL_MAX = 200                            # records kept per commander (the weakest dropped)
HALL_HIST = 30                            # history lines kept per unit
REC_FIELDS = ("bt", "bw", "bk", "sv", "cs", "cap", "dw")

def unit_rec(u):
    r = u.setdefault("rec", {})
    for k in REC_FIELDS:
        r.setdefault(k, 0)
    return r

def _hist(r, kind, val):
    h = r.setdefault("hist", [])
    h.append([int(__import__("time").time()), kind, val])
    del h[:-HALL_HIST]

def _award(cmd, r, code, thr, hon, events=None):
    """one medal to the record: counted, first time on the wall, history, honor, news for the player."""
    mc = r.setdefault("mcount", {})
    mc[code] = int(mc.get(code, 0)) + 1
    if code not in r["marks"]:
        r["marks"].append(code)
    _hist(r, "medal", code)
    cmd["honor"] = int(cmd.get("honor", 0) or 0) + hon
    cmd.setdefault("star_news", []).append(("mark", r["name"] or str(r["chassis"]), code, thr, hon, mc[code]))
    if events is not None:
        events.append(f"unit record: medal {code} x{mc[code]} (+{hon} honor)")

def hall_note(cmd, u, events=None, star_up=False):
    """update the unit's record; new medals add honor (cmd["honor"], shown / 100) and go to cmd["star_news"]."""
    if not isinstance(cmd, dict) or not isinstance(u, dict):
        return
    hid = str(u.setdefault("hid", u.get("uid", 0)))
    hall = cmd.setdefault("unit_hall", {})
    r = hall.setdefault(hid, {"marks": [], "t0": int(__import__("time").time())})
    ur = unit_rec(u)
    r.update(name=strip_star_tag(u.get("label") or ""), chassis=u.get("chassis"), star=max(r.get("star", 0), unit_star(u)),
             kills=max(r.get("kills", 0), int(u.get("kills", 0) or 0)), peak=max(r.get("peak", 0), unit_peak(u)),
             uid=u.get("uid"), t=int(__import__("time").time()))
    for k in REC_FIELDS:
        r[k] = max(int(r.get(k, 0) or 0), int(ur.get(k, 0) or 0)) if k != "cs" else int(ur.get(k, 0) or 0)
    if star_up:
        _hist(r, "star", r["star"])
    for code, kind, f, thr, hon in MEDALS:
        if kind == "once" and int(r.get(f, 0) or 0) >= thr and code not in r["marks"]:
            _award(cmd, r, code, thr, hon, events)
    if len(hall) > HALL_MAX:
        worst = min(hall, key=lambda k: (hall[k].get("star", 0), hall[k].get("kills", 0), hall[k].get("bt", 0)))
        hall.pop(worst, None)

def unit_battle_end(cmd, u, won, survived, kills, captured=False, defended=False, mvp=False, heavy_loss=False):
    """(14:36 / 14:44) one battle of this unit is over: battles, wins, best battle, survival run, captures, defences;
    the battle medals of this settlement (each at most once)."""
    r = unit_rec(u)
    r["bt"] += 1
    if won:
        r["bw"] += 1
    r["bk"] = max(r["bk"], int(kills or 0))
    r["cs"] = r["cs"] + 1 if survived else 0
    r["sv"] = max(r["sv"], r["cs"])
    if won and captured:
        r["cap"] += 1
    if won and defended:
        r["dw"] += 1
    hall_note(cmd, u)
    hr = cmd["unit_hall"][str(u["hid"])]
    got = {"ace": int(kills or 0) >= ACE_KILLS, "mvp": bool(mvp) and int(kills or 0) >= MVP_MIN_KILLS,
           "survivor": bool(survived and heavy_loss), "conqueror": bool(won and captured), "guardian": bool(won and defended)}
    for code, kind, test, thr, hon in MEDALS:
        if kind == "battle" and got.get(test):
            _award(cmd, hr, code, thr, hon)

# ---- derived values -----------------------------------------------------------------------------------------
def attr(cmd, i):
    return int((cmd.get("attrs") or [0, 0, 0, 0])[i])

def deploy_limit(cmd):
    return min(12, attr(cmd, 0) // 20 + 6)      # at most 12 units per battle

def total_points(cmd):
    """all attribute points of the hero (spent; the unspent POINT counter is not counted)."""
    return sum(int(x) for x in (cmd.get("attrs") or [0, 0, 0, 0]))

def power_rating(cmd):
    pts = total_points(cmd)
    if pts < 40:
        return 0
    if pts >= 226:
        return min(PR_MAX, 10 + (pts - 226) // 15)
    pr = 0
    for lo, v in PR_TABLE:
        if pts >= lo:
            pr = v
    return pr

def influence(cmd, branch):
    return ensure_commander(cmd)["branches"][branch]["level"] + attr(cmd, 1) // 2

def unit_quality(cmd, u):
    return unit_peak(ensure_unit(u)) + attr(cmd, 1) // 2

def tech_level(cmd, u):
    return unit_peak(ensure_unit(u)) + attr(cmd, 2) // 2

def carry_weight(cmd, base):
    return int(base * (1 + attr(cmd, 3) / 120))

def branch_cap(cmd):
    # division (branch) level: max 100, +1 per reincarnation (ntf2/rtn-desc.txt: "reach max level, restart at level 1,
    # next time you may go one level higher"; reincarnated heroes rank above non-reincarnated level-100 heroes).
    # The "Maximum is 60" in the F4 help text is stale; unit levels stay at UNIT_MAX_LEVEL (user decision).
    if cmd.get("tier", 1) == 1:
        return NOVICE_BRANCH_CAP
    return DIVISION_MAX_LEVEL + int(cmd.get("reincarnations", 0))

def can_advance(cmd):
    return cmd.get("tier", 1) == 1 and any(v["level"] >= ADVANCE_BRANCH_LEVEL
                                           for v in ensure_commander(cmd)["branches"].values())

# ---- events -------------------------------------------------------------------------------------------------
def add_branch_xp(cmd, branch, xp, events):
    b = ensure_commander(cmd)["branches"][branch]
    b["xp"] += xp
    while b["level"] < branch_cap(cmd) and b["xp"] >= branch_xp_need(b["level"]):
        b["xp"] -= branch_xp_need(b["level"])
        b["level"] += 1
        cmd["points"] = cmd.get("points", 0) + 1
        events.append(f"branch {BRANCH_NAMES[branch]} -> level {b['level']} (+1 point, {cmd['points']} unspent)")
        if b["level"] == ADVANCE_BRANCH_LEVEL and cmd.get("tier", 1) == 1:
            events.append("may now travel to the Advanced planet (StarPortal)")
    if b["level"] >= branch_cap(cmd):
        b["xp"] = 0

# WORD OF HONOR "Pyramid" (client texts ntt.dat pyramid / HELPWND khiPyramid*): a Subordinate's adventures give the Superior
# bonus XP that he distributes himself (Assign XP window).  The amount is not in the client: PLACEHOLDER 10 % of the XP
# every unit of the Subordinate earns, kept on the Subordinate's own commander record (cmd["tribute"]).
WOH_TRIBUTE = 0.10
# (user 2026-11-01 16:20) the Assign XP window has two columns per Subordinate, DIRECT and INDIRECT XP (005dfea0: two u32).
# Indirect = what the Subordinate's own Subordinates earn for the Superior one step higher.  PLACEHOLDER 5 %, kept on the
# lower commander's record (cmd["tribute_up"]); the Superior's row for the middle commander shows the sum of them.
WOH_TRIBUTE2 = 0.05

def add_unit_xp(cmd, u, branch, xp, tribute=True):
    """Give a unit XP; returns a list of human-readable events (level ups).  tribute=False: XP that is itself a
    distributed tribute (does not flow on to the next Superior)."""
    events = []
    ensure_unit(u)
    u["xp"] += xp
    if tribute and xp > 0 and isinstance(cmd, dict) and cmd.get("superior"):
        cmd["tribute"] = int(cmd.get("tribute", 0)) + int(xp * WOH_TRIBUTE)
        cmd["tribute_up"] = int(cmd.get("tribute_up", 0) or 0) + int(xp * WOH_TRIBUTE2)
    while u["level"] < UNIT_MAX_LEVEL and u["xp"] >= unit_xp_need(u["level"]):
        u["xp"] -= unit_xp_need(u["level"])
        u["level"] += 1
        events.append(f"unit {u.get('label') or u['chassis']} #{u['uid']} -> level {u['level']}")
        add_branch_xp(cmd, branch, branch_xp_per_unit_level(u["level"]), events)
        if u["level"] >= UNIT_MAX_LEVEL and unit_star(u) < STAR_MAX:      # (10-31) STAR: back to level 1, peak kept
            u["peak"] = max(int(u.get("peak", 0) or 0), u["level"])
            u["star"] = unit_star(u) + 1
            u["level"], u["xp"] = 1, 0
            events.append(f"unit {u.get('label') or u['chassis']} #{u['uid']} rises to star {u['star']} - back to level 1")
            if isinstance(cmd, dict):
                cmd.setdefault("star_news", []).append(("star", strip_star_tag(u.get("label") or "") or u.get("chassis"), u["star"]))
                hall_note(cmd, u, events, star_up=True)
            break
    return events

def award_kill(cmd, u, branch, enemy_level=1, mult=1.0):
    ensure_unit(u)["kills"] += 1
    ev = add_unit_xp(ensure_commander(cmd), u, branch, int(KILL_XP * max(1, enemy_level) * mult))
    hall_note(cmd, u, ev)                                 # (10-31) lifetime kills on the unit's record
    return ev

def spend_point(cmd, index):
    """F4: put one point into attribute 0..3. Returns True if done."""
    ensure_commander(cmd)
    if cmd.get("points", 0) <= 0 or not 0 <= index < 4 or cmd["attrs"][index] >= ATTR_MAX:
        return False
    cmd["attrs"][index] += 1
    cmd["points"] -= 1
    sp = cmd.setdefault("spent_attrs", [0, 0, 0, 0])      # points the player put in himself (for /reset)
    sp[index] += 1
    return True
