"""NPC commanders (claude/NPC_NATIONS_PLAN.md, user decisions 2026-10-22 13:08 - 13:13).

Pure logic: names, rosters, personalities, random timers, target choice and the abstract battle.  Nothing here touches the
network or sgserver; the NPC NATIONS section of sgserver.py feeds it the world and applies the results.

Rules in short
  * every nation has a roster of NPC_CAP commanders; the number ACTIVE is NPC_CAP - (players of that nation online)
    (a player logging in retires one NPC, a player leaving brings one back after a random delay);
  * every active NPC thinks on its own random timer, has a personality and either sorties alone or with a random group;
  * a province without a player in it is fought out abstractly (power numbers + dice); with a player in it the NPC squads
    are put on the battle map as server-owned units (sgserver.npc_spawn_*).
"""
import math
import random
import re

NPC_CAP = 20                    # roster size and the cap of active NPC + players per nation
NPC_PER_PLAYER = 1.0            # one player online retires this many NPCs
NPC_MIN = 0                     # active NPCs kept even when many players are online
REFILL_DELAY = (120, 600)       # seconds before a missing NPC comes back after a player left
THINK = (15, 80)                # seconds between two decisions of one NPC, then +-30 %  (2026-10-31: was 20-120, 30-180)
SORTIE_EVERY = (420, 1200)      # a nation's random group sortie happens this often
SORTIE_SIZE = (4, 10)
MARCH_STEP = (30, 90)          # seconds per province step
SIEGE = (60, 180)               # length of an abstract battle
REST_WIN = (120, 300)           # conquest mode (2026-10-27): shorter rests (was 180-600 / 600-1500 / protect 900-1800)
REST_LOSS = (180, 480)          # (2026-10-31: was 300-900)
PROTECT_SECONDS = (300, 600)   # a nation that just lost a province is left alone by NPCs for this long
LAST_STAND_PROVINCES = 3        # nation with this many provinces or fewer (capital included) gets "last stand"
LAST_STAND_SECONDS = 6 * 3600
LAST_STAND_COOLDOWN = 12 * 3600
LAST_STAND_HP = 1.25            # unit HP multiplier of that nation while it lasts (players and NPCs)
LAST_STAND_EXTRA = 5            # extra active NPCs while it lasts
# CAPITAL ALARM (user 2026-10-30 22:30 "an enemy took a province next to our capital: NPCs up to 30 for a while, more
# eager to attack, for 12 hours"): an enemy (not of its side) holds a province within ALARM_RANGE portal steps of the
# capital -> for ALARM_SECONDS the nation fields up to ALARM_ACTIVE commanders (roster grows to that size; players online
# still take NPC places) and its NPCs think faster, accept worse odds, never stay home and go first for the enemy land
# next to the capital.  Still threatened when it ends: a new alarm starts.
ALARM_RANGE = 1
ALARM_SECONDS = 12 * 3600
ALARM_ACTIVE = 30
ALARM_THINK = 0.5               # decision timer x this
ALARM_MIN_WIN = 0.10            # accepted win chance this much lower
ALARM_ENEMY = 15.0              # score bonus for any enemy province ...
ALARM_NEAR = 25.0               # ... and this much more for one within 2 steps of the capital (retake it)
# BOREDOM (2026-10-31 10:10): an NPC idle at home longer than BORED_SECONDS accepts BORED_MIN_WIN worse odds and never
# stays home - so nobody stands around for long
BORED_SECONDS = 600
BORED_MIN_WIN = 0.10
MIN_WIN_GATE = False            # (user 2026-10-31 10:14) the personality's min_win no longer rejects a target
# FACTORY REPAIR (user 2026-10-31 10:13 "after a battle the NPC goes back to the capital's factory to repair, no 30 min
# wait"): a damaged NPC whose task ends walks home (no fallback post); at the capital its units are repaired at once
REPAIR_BELOW = 0.999            # readiness below this after a task = damaged
SQUAD_RANGE = (42, 42)          # units one NPC carries (user 2026-10-24 22:48: always 42; was 12..42 random)
# PLATOONS (user 2026-10-24 22:48): the 42 units form platoons of ONE kind each, 6..8 units (the commander's deploy
# rule), 3..4 platoons of different roles go into a battle together and are swapped by the battle situation.
PLATOON_RANGE = (6, 8)
# role of platoon k (k = 0, 1, ...): capturers first, then the main line, anti-air, artillery, more line / second kind
# (user 2026-10-27 22:06 "NPCs must use aircraft"): one AIR platoon (doctrine "air" = the best armed aircraft the NPC can
# field; without one it falls back to the main kind) - 42 units / 6-8 = 6-7 platoons: fast main aa arty air main (second)
PLATOON_ROLES = ("fast", "main", "aa", "arty", "air", "main", "second", "air")
SQUAD_SIZE = 8                  # units that count fully for the strength of an NPC (the rest = reserve, x RESERVE_WEIGHT)
RESERVE_WEIGHT = 0.3
SQUAD_FAST = 3                  # fast ground units sent as POC capturers (picked from the first fast_count(size) units)
HEAL_SECONDS = 1800             # a wounded / lost unit is back at full strength after this long
MIN_READY = 0.45                # an NPC whose best units are weaker than this stays home and recovers


def fast_count(size):
    return max(SQUAD_FAST, size // 4)

FIRST = ["Kael", "Mira", "Dax", "Lena", "Rook", "Sera", "Tarn", "Vex", "Nia", "Bron", "Ilya", "Zed", "Orin", "Tess",
         "Joss", "Kira", "Brandt", "Anya", "Cole", "Dara", "Egon", "Fenn", "Gale", "Hale", "Iris", "Jarl", "Kane",
         "Lux", "Mace", "Nox", "Odin", "Pike", "Quin", "Reva", "Sol", "Thorn", "Ugo", "Vale", "Wren", "Yara"]
LAST = ["Voss", "Hart", "Stone", "Reeve", "Crow", "Vane", "Frost", "Black", "Wolf", "Lane", "Cross", "Drake", "Flint",
        "Grey", "Holt", "Kerr", "Moss", "North", "Pryce", "Quill", "Rhodes", "Sharp", "Thorne", "Voight", "Ward",
        "York", "Ash", "Bane", "Cade", "Dunn", "Ember", "Fox", "Gray", "Hawk", "Ives", "Jett", "Knox", "Lowe"]

# w = weight when a roster is made; stay = chance to do nothing at a decision; enemy = score bonus for attacking another
# nation; min_win = lowest estimated win chance it accepts; follow = chance to join a departing comrade; think = timer factor
PERSONAS = {
    # (2026-10-27 22:03 "more eager to fight"): min_win -0.05..-0.10, stay lower, follow higher
    # (2026-10-31 10:10 "NPCs must attack more, many just stand"): min_win -0.10, stay halved, follow lower (fewer join an
    # existing campaign, more open their own)
    "lone":     {"w": 3.0, "stay": 0.01, "enemy": 10, "min_win": 0.15, "follow": 0.30, "think": 1.0},
    "follower": {"w": 2.0, "stay": 0.015, "enemy": 10, "min_win": 0.20, "follow": 0.70, "think": 1.0},
    "warlike":  {"w": 2.0, "stay": 0.0,  "enemy": 26, "min_win": 0.08, "follow": 0.40, "think": 0.6},
    "cautious": {"w": 2.0, "stay": 0.025, "enemy": 6, "min_win": 0.35, "follow": 0.50, "think": 1.0},
    "guard":    {"w": 1.5, "stay": 0.04, "enemy": 6,  "min_win": 0.30, "follow": 0.35, "think": 1.0},
}

# branch level range of a new NPC per planet tier.  Wide on purpose (user 2026-10-22 13:23: some high, some low): the level
# is drawn uniformly, so a roster has beginners and veterans side by side (novice planet is capped at 35 like players).
# User 2026-10-22 13:42: the level follows the planet - nobody below the planet's floor (advanced: 35, elite: 50).
TIER_LEVEL = {1: (3, 35), 2: (35, 85), 3: (50, 100)}
# unit level of the squad = branch level x UNIT_SCALE (+-3), never below the planet's floor and never above 60 (player max),
# so the squads match the strength of the planet they defend.
UNIT_SCALE = 0.65
TIER_UNIT_FLOOR = {1: 1, 2: 20, 3: 33}


def new_name(taken, rnd=random):
    for _ in range(200):
        n = rnd.choice(FIRST) + rnd.choice(LAST)
        if n.lower() not in taken:
            return n
    i = 1
    while f"Npc{i}" in taken:
        i += 1
    return f"Npc{i}"


def pick_persona(rnd=random):
    return rnd.choices(list(PERSONAS), [v["w"] for v in PERSONAS.values()])[0]


def unit_level(level, rnd=random, tier=1):
    base = level if tier == 1 else level * UNIT_SCALE
    return max(TIER_UNIT_FLOOR.get(tier, 1), min(35 if tier == 1 else 60, int(round(base)) + rnd.randint(-3, 3)))


# DOCTRINE (user 2026-10-22 21:25, screenshots of real players: a column of one tank kind, a blob of one infantry kind):
# every NPC has a MAIN unit kind (most of its army), a SECOND kind and one FAST kind for the POC capturers, instead of a
# random mix.  The daily renewal keeps the doctrine; now and then the second kind changes.
MAIN_SHARE = 0.7                # non-capturer units of the main kind (the rest = second kind)
DOCTRINE_DRIFT = 0.15           # chance per daily renewal that the second kind changes


def pick_doctrine(pool, level, rnd=random, main=None):
    use = [p for p in pool if p["min"] <= level] or pool[:1]
    gr = [p for p in use if p.get("ground", True) and not p.get("air")] or use   # main and capturers: ground units
    fast = [p for p in gr if p["fast"]] or gr                         # that hit ground (aircraft cannot take POCs)
    w = lambda lst: [1.0 + p["rank"] for p in lst]
    if main is None or not any(p["code"] == main for p in gr):
        main = rnd.choices(gr, w(gr))[0]["code"]
    rest = [p for p in use if p["code"] != main] or use
    second = rnd.choices(rest, w(rest))[0]["code"]
    if any(p["code"] == main for p in fast) and rnd.random() < 0.5:
        fastc = main                                # a fast main kind captures too: one big column
    else:
        fastc = rnd.choices(fast, w(fast))[0]["code"]
    return {"main": main, "second": second, "fast": fastc}


def platoon_sizes(size, p):
    """size units in platoons of at most p, as even as possible (42 / 8 -> 6 x 7)."""
    p = max(PLATOON_RANGE[0], min(PLATOON_RANGE[1], int(p or 7)))
    k = max(1, -(-size // p))
    out = [p] * k                       # full platoons first; the last ones give up units down to PLATOON_RANGE[0]
    extra = p * k - size                # (42 / 8 -> 8 8 8 6 6 6, 42 / 7 -> 6 x 7, 42 / 6 -> 7 x 6)
    for i in range(k - 1, -1, -1):
        cut = min(extra, out[i] - min(PLATOON_RANGE[0], out[i]))
        out[i] -= cut
        extra -= cut
    if extra > 0:                       # too few units for platoons of the minimum size: as even as possible
        return [size // k + (1 if i < size % k else 0) for i in range(k)]
    return out


def platoon_kinds(doc, size, p):
    """[(role, kind)] per platoon and the flat kind list of the roster (platoon after platoon)."""
    roles, flat = [], []
    for i, n in enumerate(platoon_sizes(size, p)):
        role = PLATOON_ROLES[i % len(PLATOON_ROLES)]
        kind = doc.get(role) or (doc.get("second") if role in ("arty", "air") else None) or doc["main"]
        roles.append((role, kind))
        flat += [kind] * n
    return roles, flat


def doctrine_kinds(doc, size, p=None):
    if p or doc.get("pp"):
        return platoon_kinds(doc, size, p or doc.get("pp"))[1]
    nf = fast_count(size)
    nmain = int(round((size - nf) * MAIN_SHARE))
    return [doc["fast"]] * nf + [doc["main"]] * nmain + [doc["second"]] * (size - nf - nmain)


def ensure_doctrine(npc, tier, pool, rnd=random):
    """an NPC made before the doctrines: give it one (main = its most common non-capturer kind) and re-form its army with
    the same number of units and the same levels.  True = changed."""
    if npc.get("doctrine"):
        return False
    sq = npc["squad"]
    nf = fast_count(len(sq))
    kinds = [c for c, _l in sq[nf:]] or [c for c, _l in sq]
    main = max(set(kinds), key=kinds.count) if kinds else None
    npc["doctrine"] = doc = pick_doctrine(pool, npc["level"], rnd, main)
    levels = sorted((l for _c, l in sq), reverse=True)
    npc["squad"] = [[c, l] for c, l in zip(doctrine_kinds(doc, len(sq)), levels)]
    npc["hl"] = None
    return True


def make_squad(pool, level, rnd=random, tier=1, size=None, doc=None):
    """pool = [{"code", "min", "fast", "rank"}].  Returns [[chassis code, unit level]] * SQUAD_SIZE: SQUAD_FAST fast ground
    units (the POC capturers) and the rest from everything the NPC may use; better (higher rank) kinds are likelier."""
    use = [p for p in pool if p["min"] <= level] or pool[:1]
    fast = [p for p in use if p["fast"] and not p.get("air")] or use
    w = lambda lst: [1.0 + p["rank"] for p in lst]
    size = size or rnd.randint(*SQUAD_RANGE)
    if doc:
        return [[c, unit_level(level, rnd, tier)] for c in doctrine_kinds(doc, size)]
    nf = fast_count(size)
    out = [rnd.choices(fast, w(fast))[0] for _ in range(nf)]
    out += [rnd.choices(use, w(use))[0] for _ in range(size - nf)]
    return [[p["code"], unit_level(level, rnd, tier)] for p in out]


REFRESH_EVERY = 86400           # each NPC renews part of its roster about once a day (own random phase)
REFRESH_SHARE = 0.25            # share of the units replaced per refresh
REFRESH_SIZE_STEP = 3           # the unit count drifts by up to +-this per refresh (inside SQUAD_RANGE)


def refresh(npc, tier, pool, rnd=random):
    """gradual daily renewal (user 2026-10-22 14:10): ~25 % of the units are replaced by new ones, the unit count drifts a
    little, the fast units stay in front.  Replaced / new units start at full health."""
    sq, hl = npc["squad"], health(npc)
    level = npc["level"]
    use = [p for p in pool if p["min"] <= level] or pool[:1]
    fast = [p for p in use if p.get("fast") and not p.get("air")] or use
    w = lambda lst: [1.0 + p["rank"] for p in lst]
    is_fast = {p["code"]: bool(p.get("fast")) and not p.get("air") for p in pool}
    doc = npc.get("doctrine")
    if doc and doc.get("pp"):
        # platoon roster (2026-10-24 22:48): the platoons keep their kind; ~25 % of the units are renewed (new level,
        # full health); now and then the second kind changes (all its units, so the platoons stay one kind)
        if rnd.random() < DOCTRINE_DRIFT:
            old2 = doc["second"]
            doc["second"] = pick_doctrine(pool, level, rnd, doc["main"])["second"]
            for u in sq:
                if u[0] == old2 and old2 not in (doc["main"], doc["fast"], doc.get("aa"), doc.get("arty")):
                    u[0] = doc["second"]
        for i in rnd.sample(range(len(sq)), max(1, int(round(len(sq) * REFRESH_SHARE)))):
            sq[i] = [sq[i][0], unit_level(level, rnd, tier)]
            hl[i] = 1.0
        return
    if doc and rnd.random() < DOCTRINE_DRIFT:
        doc["second"] = pick_doctrine(pool, level, rnd, doc["main"])["second"]
    def kind(fast_slot):
        if doc:
            return doc["fast"] if fast_slot else (doc["main"] if rnd.random() < MAIN_SHARE else doc["second"])
        return rnd.choices(fast if fast_slot else use, w(fast if fast_slot else use))[0]["code"]
    nf0 = fast_count(len(sq))
    for i in rnd.sample(range(len(sq)), max(1, int(round(len(sq) * REFRESH_SHARE)))):
        sq[i] = [kind(i < nf0 if doc else is_fast.get(sq[i][0])), unit_level(level, rnd, tier)]
        hl[i] = 1.0
    size = max(SQUAD_RANGE[0], min(SQUAD_RANGE[1], len(sq) + rnd.randint(-REFRESH_SIZE_STEP, REFRESH_SIZE_STEP)))
    while len(sq) > size:                      # drop the weakest
        j = min(range(len(sq)), key=lambda i: sq[i][1])
        sq.pop(j); hl.pop(j)
    while len(sq) < size:
        sq.append([kind(False), unit_level(level, rnd, tier)]); hl.append(1.0)
    # fast units first, and at least fast_count(size) of them
    order = sorted(range(len(sq)), key=lambda i: not is_fast.get(sq[i][0]))
    nf = fast_count(len(sq))
    nfast = sum(1 for i in order if is_fast.get(sq[i][0]))
    if doc:                                    # capturers first, then the main kind, then the second kind
        rank = {doc["fast"]: 0, doc["main"]: 1}
        order = sorted(range(len(sq)), key=lambda i: rank.get(sq[i][0], 2))
        for j in range(nf):
            if sq[order[j]][0] != doc["fast"]:
                sq[order[j]] = [doc["fast"], sq[order[j]][1]]
        npc["squad"] = [sq[i] for i in order]
        npc["hl"] = [hl[i] for i in order]
        return
    for j in range(nfast, nf):
        i = order[j]
        p = rnd.choices(fast, w(fast))[0]
        sq[i] = [p["code"], unit_level(level, rnd, tier)]; hl[i] = 1.0
    order = sorted(range(len(sq)), key=lambda i: not is_fast.get(sq[i][0]))
    npc["squad"] = [sq[i] for i in order]
    npc["hl"] = [hl[i] for i in order]


def new_npc(nid, tier, uid, taken, pool, rnd=random):
    lo, hi = TIER_LEVEL.get(tier, TIER_LEVEL[1])
    level = rnd.randint(lo, hi)
    doc = pick_doctrine(pool, level, rnd)
    return {"id": uid, "name": new_name(taken, rnd), "nation": nid, "persona": pick_persona(rnd), "level": level,
            "look": rnd.randint(1, 11), "doctrine": doc, "squad": make_squad(pool, level, rnd, tier, doc=doc), "hl": None, "state": "sleep", "task": None,
            "think_at": 0, "rest_until": 0, "wins": 0, "losses": 0, "honor": 0}


def conform(npc, tier, pool, rnd=random):
    """put an NPC made under older rules inside its planet's level range (new level + new squad).  True = changed."""
    lo, hi = TIER_LEVEL.get(tier, TIER_LEVEL[1])
    floor = TIER_UNIT_FLOOR.get(tier, 1)
    if lo <= npc["level"] <= hi and all(l >= floor for _c, l in npc["squad"]) \
            and SQUAD_RANGE[0] <= len(npc["squad"]) <= SQUAD_RANGE[1]:
        return False
    if not lo <= npc["level"] <= hi:
        npc["level"] = rnd.randint(lo, hi)
    npc["doctrine"] = pick_doctrine(pool, npc["level"], rnd)
    npc["squad"] = make_squad(pool, npc["level"], rnd, tier, doc=npc["doctrine"])
    npc["hl"] = None
    return True


def health(npc):
    """per-unit health 0..1 (parallel to the squad); lazily created."""
    sq = npc["squad"]
    hl = npc.get("hl")
    if not hl or len(hl) != len(sq):
        hl = npc["hl"] = [1.0] * len(sq)
    return hl


def power(squad, hl=None):
    """strength: the best SQUAD_SIZE units count fully (by level x health), the reserve RESERVE_WEIGHT."""
    v = sorted(((l + 10) * (hl[i] if hl else 1.0) for i, (_c, l) in enumerate(squad)), reverse=True)
    return float(sum(v[:SQUAD_SIZE]) + RESERVE_WEIGHT * sum(v[SQUAD_SIZE:]))


def power_of(npc):
    return power(npc["squad"], health(npc))


def readiness(npc):
    """mean health of the SQUAD_SIZE best units."""
    hl = health(npc)
    best = sorted(range(len(hl)), key=lambda i: -(npc["squad"][i][1] * hl[i]))[:SQUAD_SIZE]
    return sum(hl[i] for i in best) / max(1, len(best))


def heal(npc, now):
    last = npc.get("heal_t") or now
    npc["heal_t"] = now
    dt = max(0.0, now - last)
    if dt <= 0:
        return
    hl = health(npc)
    for i, h in enumerate(hl):
        if h < 1.0:
            hl[i] = min(1.0, h + dt / HEAL_SECONDS)


def win_prob(att, dfn):
    if dfn <= 0:
        return 1.0
    if att <= 0:
        return 0.0
    return 1.0 / (1.0 + math.exp(-(att - dfn) / (0.25 * max(att, dfn))))


def think_delay(npc, rnd=random):
    p = PERSONAS.get(npc.get("persona"), PERSONAS["lone"])
    return rnd.uniform(*THINK) * p["think"] * rnd.uniform(0.7, 1.3) * (ALARM_THINK if npc.get("alarm") else 1.0)


def march_seconds(steps, rnd=random):
    return sum(rnd.uniform(*MARCH_STEP) for _ in range(max(1, steps)))


def rest_seconds(won, rnd=random):
    return rnd.uniform(*(REST_WIN if won else REST_LOSS))


# SEEK THE FIGHT (user 2026-11-02 22:33 "为什么NPC AI不打呢？NPC一直找空的省打", 22:35 "改"): the win chance used to
# weigh 30 x (wp - 0.5) and the smallest nations were spared (-25), so an empty province beat a defended one ~6:1 and
# the armies of two nations passed each other taking each other's empty land.  Now the win chance counts a third, the
# small nations are not spared, and provinces where the enemy ARMY is (its squads stand / march there), that the enemy
# just took from us, or from which it is attacking us, score more.
WP_WEIGHT = 10.0               # was 30
SMALL_SPARE = 0.0              # was 25 (score - this for a nation with <= 2 provinces)
ARMY_BONUS = 15.0              # per enemy NPC squad in the province (up to ARMY_MAX)
ARMY_MAX = 3
RETAKE_BONUS = 30.0            # the province was ours until less than RETAKE_SECONDS ago
RETAKE_SECONDS = 1800
SOURCE_BONUS = 20.0            # enemy squads march on our land from this province

BRIDGE_BONUS = 40.0            # score bonus of a province that reconnects an own enclave (npc_world.npc_bridges)
BRIDGE_MIN_WIN = 0.15

def score(c, npc, att, rnd=random):
    """candidate c = {"pid", "owner", "kind": "alien"|"enemy", "garrison", "dist_cap", "def_power", "owner_big",
    "owner_small"}.  None = this NPC will not go there (too dangerous for its personality)."""
    p = PERSONAS.get(npc.get("persona"), PERSONAS["lone"])
    wp = win_prob(att, c["def_power"])
    alarm = bool(npc.get("alarm"))
    # (user 2026-10-31 10:14 "no more limit for a win chance below the personality's threshold"): every target is
    # acceptable - a low win chance only lowers the score (30 x (wp - 0.5) below), min_win is no longer a gate
    if MIN_WIN_GATE:
        mw = min(p["min_win"], BRIDGE_MIN_WIN) if c.get("bridge") else p["min_win"]
        mw -= (ALARM_MIN_WIN if alarm else 0.0) + (BORED_MIN_WIN if npc.get("bored") else 0.0)
        if wp < mw:
            return None
    s = 50.0 - 4.0 * c.get("dist_cap", 0)
    if alarm and c["kind"] != "alien":
        s += ALARM_ENEMY + (ALARM_NEAR if c.get("dist_cap", 9) <= 2 else 0.0)
    if c["kind"] == "alien":
        s += (100.0 - c.get("garrison", 100.0)) * 0.35
    else:
        s += 10.0 + p["enemy"]
        if c.get("owner_big"):
            s += 12.0                       # balance: the strongest nation is the preferred victim ...
        if c.get("owner_small"):
            s -= SMALL_SPARE                # ... (until 11-02) the weakest was left alone
        s += ARMY_BONUS * min(ARMY_MAX, c.get("army", 0))     # (11-02) go where the enemy army is
        if c.get("retake"):
            s += RETAKE_BONUS                                  # (11-02) take back what was just lost
        if c.get("source"):
            s += SOURCE_BONUS                                  # (11-02) hit where the attack on us comes from
    if c.get("bridge"):
        s += BRIDGE_BONUS                   # (2026-10-27 22:41) it joins a cut-off enclave to the home land again
    if npc.get("persona") == "lone":
        s += 10.0 * max(0.0, wp - 0.5)
    return s + WP_WEIGHT * (wp - 0.5) + rnd.uniform(-4, 4)


def choose(cands, npc, att, rnd=random):
    """weighted draw among the candidates the NPC accepts (high score likelier, low score possible); None = stay home."""
    p = PERSONAS.get(npc.get("persona"), PERSONAS["lone"])
    if not npc.get("alarm") and not npc.get("bored") and rnd.random() < p["stay"]:
        return None
    sc = [(c, score(c, npc, att, rnd)) for c in cands]
    sc = [(c, s) for c, s in sc if s is not None]
    if not sc:
        return None
    top = max(s for _c, s in sc)
    return rnd.choices([c for c, _s in sc], [math.exp((s - top) / 12.0) for _c, s in sc])[0]


def resolve(att, dfn, rnd=random):
    """abstract battle: (attacker won, attacker roll, defender roll)."""
    a = att * rnd.uniform(0.85, 1.15)
    d = dfn * rnd.uniform(0.9, 1.1)
    return a > d, a, d


def want_active(players, stand=False, alarm=False):
    """number of active NPCs of a nation with this many players online (capital alarm: up to ALARM_ACTIVE)."""
    cap = max(NPC_CAP, ALARM_ACTIVE) if alarm else NPC_CAP
    n = cap - int(math.ceil(NPC_PER_PLAYER * players))
    if stand:
        n += LAST_STAND_EXTRA
    return max(NPC_MIN, min(cap, n))


# ---- CHINESE FORM OF THE NAMES (user 2026-10-26 12:29: NPC names should show Chinese AND English) ------------------
# The NPC's real name (id on the wire, directory, owner of its units, uid) stays "BrandtVane"; places that only DISPLAY it
# (ally chat, battle dialog lists, notices) show a real CHINESE-STYLE name instead of it to Chinese clients - "李子轩"
# (2026-10-26, user: "NPC的名字改中文, 不要英文翻译成中文, 两个都显示").  NOT a transliteration: the FIRST part gives the
# given name, the LAST part the surname (Chinese order: surname + given); every combination exists and is unique.
FIRST_ZH = {"Kael": "暴躁", "Mira": "佛系", "Dax": "熬夜", "Lena": "摸鱼", "Rook": "失眠", "Sera": "迷路", "Tarn": "嘴硬", "Vex": "社恐", "Nia": "傲娇", "Bron": "爱哭", "Ilya": "肥宅", "Zed": "加班", "Orin": "断网", "Tess": "破产", "Joss": "单身", "Kira": "挑食", "Brandt": "放鸽", "Anya": "手残", "Cole": "赖床", "Dara": "路痴", "Egon": "嘴炮", "Fenn": "偷懒", "Gale": "忧郁", "Hale": "超凶", "Iris": "迷糊", "Jarl": "逃课", "Kane": "暴富", "Lux": "装睡", "Mace": "没带", "Nox": "爱吃", "Odin": "秒怂", "Pike": "无敌", "Quin": "欧皇", "Reva": "非酋", "Sol": "离线", "Thorn": "躺平", "Ugo": "内卷", "Vale": "狂暴", "Wren": "淡定", "Yara": "戏精"}
LAST_ZH = {"Voss": "小笼包", "Hart": "大白菜", "Stone": "臭豆腐", "Reeve": "咸鱼", "Crow": "烤鸭", "Vane": "土拨鼠", "Frost": "冰淇淋", "Black": "黑轮", "Wolf": "哈士奇", "Lane": "路灯", "Cross": "煎饼果子", "Drake": "皮皮虾", "Flint": "打火机", "Grey": "灰太狼", "Holt": "小馒头", "Kerr": "咖喱饭", "Moss": "青苔君", "North": "北极熊", "Pryce": "价格刺客", "Quill": "鹅毛笔", "Rhodes": "萝卜头", "Sharp": "尖叫鸡", "Thorne": "小刺猬", "Voight": "红烧肉", "Ward": "大衣柜", "York": "约会王", "Ash": "烟火", "Bane": "香蕉", "Cade": "蛋糕", "Dunn": "炖蛋", "Ember": "小火苗", "Fox": "狐狸", "Gray": "灰姑娘", "Hawk": "老鹰", "Ives": "椰子", "Jett": "喷射鸡", "Knox": "蛋挞", "Lowe": "乐高"}
_S2T = {"卜": "蔔", "乐": "樂", "产": "產", "价": "價", "会": "會", "内": "內", "凶": "兇", "单": "單", "吃": "喫", "咸": "鹹", "喷": "噴", "头": "頭", "娇": "嬌", "带": "帶", "忧": "憂", "怂": "慫", "懒": "懶", "戏": "戲", "拨": "撥", "挞": "撻", "敌": "敵", "断": "斷", "无": "無", "机": "機", "极": "極", "柜": "櫃", "欧": "歐", "残": "殘", "没": "沒", "灯": "燈", "炖": "燉", "烟": "煙", "烧": "燒", "爱": "愛", "猬": "蝟", "痴": "癡", "离": "離", "笔": "筆", "笼": "籠", "红": "紅", "约": "約", "线": "線", "网": "網", "萝": "蘿", "虾": "蝦", "装": "裝", "课": "課", "赖": "賴", "轮": "輪", "郁": "鬱", "饭": "飯", "饼": "餅", "馒": "饅", "鱼": "魚", "鸡": "雞", "鸭": "鴨", "鸽": "鴿", "鹅": "鵝", "鹰": "鷹"}

def name_zh(name, lang="zh-cn"):
    """Chinese-style name of a generated NPC name (2-char quirk + silly noun, 3-6 characters, see FIRST_ZH / LAST_ZH), None when it is not a
    FIRST+LAST name."""
    for f in sorted(FIRST_ZH, key=len, reverse=True):
        if name.startswith(f) and name[len(f):] in LAST_ZH:
            z = FIRST_ZH[f] + LAST_ZH[name[len(f):]]
            return "".join(_S2T.get(c, c) for c in z) if lang == "zh-tw" else z
    return None

def disp(name, lang):
    """what a client of this language is shown for an NPC: Chinese clients only the Chinese name '杨星辰' (user 2026-10-26 14:20:
    not together with the English name), others unchanged."""
    if lang in ("zh-cn", "zh-tw"):
        z = name_zh(name, lang)
        if z:
            return z
    return name


# ---- EVERY place that shows an NPC name (2026-10-26, user: "请确保所有地方都能正确显示") -------------------------------------
# Chinese clients get the Chinese name instead of the English one everywhere:
#  * zh_text()   - text lines (chat / notices, TextPkt.render) : "BrandtVane" -> "杨星辰"
#  * zh_bytes()  - binary packets (Session.send): every length-prefixed string [len]"BrandtVane" -> [len]<GBK/Big5 bytes>
#                  (owner names of units, commander lists, user lists, hall of fame ...; the Chinese name is SHORTER than
#                  the English one, so no client name buffer overflows)
#  * en_bytes()  - the way back: a Chinese name the client sends (click on a name, whisper ...) -> the real English name
_NAME_RE = r"(?:" + "|".join(sorted(FIRST, key=len, reverse=True)) + r")(?:" + "|".join(sorted(LAST, key=len, reverse=True)) + r")"
_RE_TXT = re.compile(r"(?<![A-Za-z])" + _NAME_RE + r"(?![a-z])")
_RE_BIN = re.compile(rb"[\x07-\x14]" + _NAME_RE.encode())
_REV = {}

def zh_text(text, lang):
    if lang not in ("zh-cn", "zh-tw") or not text or not isinstance(text, str):
        return text
    return _RE_TXT.sub(lambda m: name_zh(m.group(0), lang) or m.group(0), text)

def zh_bytes(payload, lang, enc):
    if lang not in ("zh-cn", "zh-tw") or len(payload) < 9:
        return payload
    def rep(m):
        b = m.group(0)
        if b[0] != len(b) - 1:
            return b
        z = name_zh(b[1:].decode("latin-1"), lang)
        if not z:
            return b
        zb = z.encode(enc, "replace")
        return bytes([len(zb)]) + zb
    return _RE_BIN.sub(rep, payload)

def _rev_build():
    for lang, enc in (("zh-cn", "gbk"), ("zh-tw", "cp950")):
        for f in FIRST:
            for l in LAST:
                en = f + l
                zb = name_zh(en, lang).encode(enc, "replace")
                _REV[bytes([len(zb)]) + zb] = bytes([len(en)]) + en.encode("latin-1")

_RE_ZH = re.compile(rb"[\x04-\x0c][\x81-\xfe][\x40-\xfe]{3,11}", re.S)

def en_bytes(payload, lang):
    """client -> server: Chinese NPC names (length-prefixed GBK / Big5) back to the English names"""
    if lang not in ("zh-cn", "zh-tw") or len(payload) < 7 or len(payload) > 2000:
        return payload
    if not _REV:
        _rev_build()
    def rep(m):
        b = m.group(0)
        for k in range(len(b), 5, -1):                    # the match may run on into following bytes: try the exact prefix
            r = _REV.get(b[:k])
            if r:
                return r + b[k:]
        return b
    return _RE_ZH.sub(rep, payload)
