"""BATTLE BRAIN (2026-10-23, claude/NPC_BATTLE_AI_ARCH.md): one decision module for every server-driven unit in a battle -
NPC squads of the NPC nations and the aliens - so they fight like people instead of each unit grabbing the nearest enemy.

Pure Python, no server imports: the caller builds a World (units, POCs, sides) and gets ORDERS back:
    ("attack", uid, target_uid) | ("move", uid, (x, y))
The caller turns them into lumps (0x2B / 0x1A).  The brain keeps its own memory per battle (Brain object).

Layers
  1. perception    every side only sees what it can see (stealth is filtered by the caller); threat grid (CELL px)
  2. commander     per controlled side, every PLAN_EVERY s: utility over plans (assault a POC / defend / hunt / regroup)
  3. squad         per squad: local force ratio -> fight / fall back; focus targets; formation by role
  4. unit          role behaviour (line, melee, artillery, support, anti-air, capturer), wounded units pull back
  5. human factor  reaction time, orders per second (APM), occasional second-best choice - from the difficulty profile
  6. order gate    an order is only sent when the intent changes (no slide, no order flood)
Aliens use the same squads / focus / formation with the ALIEN profile (no commander: territory, swarm, flee to the hive)."""
import math, random

CELL = 128                                    # threat grid cell (px)
PLAN_EVERY = 5.0                              # commander re-plans every 5 s
PLAN_STICK = 25.0                             # a new plan must beat the running one by this much (no flip-flop)
ENGAGE_PAD = 400                              # squad engages enemies this far beyond its longest weapon range
SQUAD_RADIUS = 700                            # local force ratio radius around a squad
GATHER_RATIO = 0.8                            # (2026-10-24) side weaker than this: a strung-out squad gathers first
GATHER_RADIUS = 260                           # ... until this share of its units stands within this many px
GATHER_SHARE = 0.8
GATHER_MAX = 30.0                             # ... but never longer than this (s)
SHIELD_R = 150                                # px around a raised shield that counts as inside (radius 160)
TP_GAP = 20.0                                 # s between two teleports of one support unit
SKILL_REACH = 110                             # px: a healer / repairer stands this close to its patient
SKILL_REPEAT = 6.0                            # s: heal / repair is (re)started this often on the same patient
OPPORTUNE = 1100                              # px: a free unit grabs an enemy / neutral POC this close
WOUNDED = 0.30                                # hp share under which a unit pulls back behind its squad
MOVE_MIN_GAP = 1.5                            # s between two move orders of one unit (unless the intent changed a lot)
TICK = 1.0                                    # the caller runs decide() about once per TICK s
MOVE_SAME = 72                                # px: a new destination this close to the old one is the same intent
OVERKILL = 1.25                               # damage already sent at a target (one volley each) / its HP -> next one
SPLIT_RATIO = 1.6                             # side force ratio above which squads take different POCs
MARCH_STEP = 400                              # px: on the march a unit this far ahead of its army's centre waits
KITE_GAP = 90                                 # px: a unit outranging a short-range enemy by this much keeps its distance

# difficulty: per planet tier (1 novice, 2 advanced, 3 elite).  react = s before a unit follows a NEW intent,
# apm = orders per second for one side, mistake = chance to pick the second best focus target, focus = units per target
PROFILES = {
    1: {"react": (0.8, 1.3), "apm": 8,  "mistake": 0.25, "focus": 4, "retreat": 0.45, "flank": 0.0, "kite": False},
    2: {"react": (0.5, 0.9), "apm": 16, "mistake": 0.12, "focus": 6, "retreat": 0.55, "flank": 0.3, "kite": True},
    3: {"react": (0.3, 0.6), "apm": 30, "mistake": 0.05, "focus": 8, "retreat": 0.65, "flank": 0.6, "kite": True},
}
# commander personality (npc.py PERSONAS) -> how early it falls back / how hard it pushes
PERSONA = {
    "warlike":  {"retreat": -0.20, "push": 1.3},
    "lone":     {"retreat": 0.00, "push": 1.0},
    "follower": {"retreat": 0.05, "push": 0.9},
    "cautious": {"retreat": 0.15, "push": 0.8},
    "guard":    {"retreat": 0.10, "push": 0.7},
}
ROLES = ("line", "melee", "artillery", "support", "antiair", "capturer")


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def centroid(pts):
    pts = list(pts)
    if not pts:
        return None
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


def toward(a, b, d):
    """the point d px from a in the direction of b (a itself if a == b)"""
    L = dist(a, b)
    if L < 1e-6:
        return a
    return (a[0] + (b[0] - a[0]) * d / L, a[1] + (b[1] - a[1]) * d / L)


GATE_CLEAR = 380                              # (2026-10-24) NPCs never park this close to a gate: an exit portal
MAP_MID = (2048, 2048)

def off_gate(p, gate):
    """user 2026-10-24 11:42: NPCs regrouped / gathered ON their gate (an exit portal); the player's units that chased
    them walked into the portal and left the battle ('my units move on their own').  A point near a gate is pushed
    GATE_CLEAR px into the map."""
    if p is None or gate is None or dist(p, gate) >= GATE_CLEAR:
        return p
    return toward(gate, MAP_MID, GATE_CLEAR)

def clamp_map(p, size=4096):
    return (max(64, min(size - 64, int(p[0]))), max(64, min(size - 64, int(p[1]))))


class U:
    """one unit as the brain sees it (filled by the caller)."""
    __slots__ = ("id", "side", "pos", "hp", "hpmax", "air", "dmg_g", "dmg_a", "rng_g", "rng_a", "cd", "spd", "role",
                 "squad", "ai", "home", "mode", "poc", "gate", "capt", "state", "target", "dest", "name",
                 "skills", "bio", "sight")

    def __init__(self, id, side, pos, hp, hpmax=None, air=False, dmg_g=0, dmg_a=0, rng_g=0, rng_a=0, cd=1.5, spd=10,
                 role="line", squad=None, ai=False, home=None, mode="assault", poc=None, gate=None, capt=False,
                 state="idle", target=None, dest=None, name="", skills=(), bio=False, sight=0):
        self.sight = sight or 0                    # own sight (px); 0 = unknown (aliens): the weapon range alone counts
        self.id, self.side, self.pos, self.hp = id, side, (float(pos[0]), float(pos[1])), max(0, hp)
        self.hpmax = max(1, hpmax or hp or 1)
        self.air, self.dmg_g, self.dmg_a, self.rng_g, self.rng_a = air, dmg_g, dmg_a, rng_g, rng_a
        self.cd, self.spd, self.role, self.squad, self.ai = max(0.2, cd), spd, role, squad, ai
        self.home, self.mode, self.poc, self.gate, self.capt = home or self.pos, mode, poc, gate, capt
        self.state, self.target, self.dest, self.name = state, target, dest, name
        self.skills, self.bio = frozenset(skills or ()), bio       # skills: "heal", "repair", "shield", "teleport",
        # (2026-10-24 19:45) + "grenade", "virus", "mine", "bombard", "flak", "booster", "energy", "refuel" (_tactics)

    def can_hit(self, o):
        return (self.dmg_a if o.air else self.dmg_g) > 0 and self.role != "support"

    def rng_vs(self, o):
        # (user 2026-10-25 13:31) a unit shoots only what is inside ITS OWN sight (allies' / radar vision does not count):
        # the real reach is min(weapon range, sight); a longer sight does not extend the weapon
        r = self.rng_a if o.air else self.rng_g
        return min(r, self.sight) if self.sight and r else r

    def dps(self):
        return max(self.dmg_g, self.dmg_a) / self.cd if self.role != "support" else 0.0

    def max_rng(self):
        r = max(self.rng_g, self.rng_a)
        return min(r, self.sight) if self.sight and r else r


def unit_role(name, st9, support_names, arty_range=500):
    """role from the chassis name and the stats9 [armor,row,code,gdmg,grng,gcd,admg,arng,acd]"""
    if name in support_names:
        return "support"
    gd, gr = (st9[3], st9[4]) if len(st9) > 4 else (0, 0)
    ad = st9[6] if len(st9) > 6 else 0
    if gd <= 0 and ad > 0:
        return "antiair"
    if gr >= arty_range:
        return "artillery"
    if 0 < gr <= 120:
        return "melee"
    return "line"


class Brain:
    """memory of one battle: plans per side, the last order of every unit, reaction delays, APM budget."""

    def __init__(self, tier=1, seed=None, persona=None, alien=False):
        self.p = dict(PROFILES.get(tier, PROFILES[1]))
        if persona in PERSONA:
            self.p["retreat"] = max(0.15, self.p["retreat"] + PERSONA[persona]["retreat"])
            self.p["push"] = PERSONA[persona]["push"]
        self.p.setdefault("push", 1.0)
        self.alien = alien
        self.rnd = random.Random(seed)
        self.plans = {}                  # side -> {"t", "kind", "poc", "point"}
        self.last = {}                   # uid -> (order tuple, time)
        self.intent = {}                 # uid -> (intent key, since)   (reaction time)
        self.budget = {}                 # side -> (second, used)
        self.log = []                    # recent decisions (for the battle log)
        # SQUAD ORDERS (user 2026-10-24 23:31: players talk to the NPCs - "佔點", "集合", "打 B3"; NPCs send the
        # platoon that counters what they spotted): squad key -> {"kind": attack | engage | move | capture | hold,
        # "point": (x, y), "target": unit id, "poc": id, "until": time, "why": text}
        self.orders = {}
        # (user 2026-10-31 10:16 "stronger strategy in the battle") side -> NPC helpers of that side marching here (set by
        # npc_battle each tick): a losing side with help on the way holds its POCs instead of falling back to its gate
        self.incoming = {}

    # ---------------------------------------------------------------- perception
    def threat_grid(self, enemies):
        """cell -> enemy dps that reaches the cell (weapon range + 64 px)"""
        g = {}
        for e in enemies:
            r = e.max_rng() + 64
            if e.dps() <= 0:
                continue
            c0x, c0y = int((e.pos[0] - r) // CELL), int((e.pos[1] - r) // CELL)
            c1x, c1y = int((e.pos[0] + r) // CELL), int((e.pos[1] + r) // CELL)
            for cx in range(c0x, c1x + 1):
                for cy in range(c0y, c1y + 1):
                    if dist(((cx + 0.5) * CELL, (cy + 0.5) * CELL), e.pos) <= r:
                        g[(cx, cy)] = g.get((cx, cy), 0.0) + e.dps()
        return g

    @staticmethod
    def power(units):
        return sum(u.dps() * (u.hp / u.hpmax) ** 0.5 * (1 + u.hpmax / 2000.0) for u in units)

    # ---------------------------------------------------------------- commander
    def plan(self, side, mine, enemies, pocs, same_side, now, default_mode, friends=None):
        # (user 2026-10-25 13:04) a defender that gets hurt hunts the attacker: remember when this side last lost HP
        hp0 = self.__dict__.setdefault("_hp0", {})
        for u in mine:
            if u.id in hp0 and u.hp < hp0[u.id] - 0.5:
                self.__dict__.setdefault("_hurt", {})[side] = now
                self.__dict__.setdefault("_hurt_u", {})[u.id] = now
            hp0[u.id] = u.hp
        pl = self.plans.get(side)
        if pl and now - pl["t"] < PLAN_EVERY:
            return pl
        ratio = self.power(friends or mine) / max(1e-6, self.power(enemies)) if enemies else 9.0
        my_c = centroid(u.pos for u in mine) or (2048, 2048)
        enemy_pocs = {i: p for i, p in pocs.items() if not same_side(side, p["owner"])}
        own_pocs = {i: p for i, p in pocs.items() if same_side(side, p["owner"])}
        tgrid = self.threat_grid(enemies)
        # only enemies this side can actually shoot decide where it goes: a ground army without anti-air does not
        # walk under aircraft it cannot hit (2026-10-23: NPC tanks marched at a Falcon wing and stood there)
        reach = [e for e in enemies if any(u.can_hit(e) for u in mine)]
        def poc_threat(p):
            return tgrid.get((int(p["x"] // CELL), int(p["y"] // CELL)), 0.0)
        opts = []
        push = self.p["push"]
        inc = self.incoming.get(side, 0)
        if enemy_pocs:
            # (10-31 strategy) the whole side goes for ONE POC (plan per side + PLAN_STICK): the least defended one, next to
            # a POC it already holds (a chain from its own ground), not the nearest one under the enemy's guns
            own_pts = [(q["x"], q["y"]) for q in own_pocs.values()]
            for i, p in enemy_pocs.items():
                d = dist(my_c, (p["x"], p["y"]))
                guard = sum(1 for e in enemies if dist(e.pos, (p["x"], p["y"])) < 450)
                chain = 25.0 if own_pts and min(dist(q, (p["x"], p["y"])) for q in own_pts) < 1400 else 0.0
                score = (100 * push - d / 40.0 - poc_threat(p) / 6.0 - 4.0 * guard + chain
                         + (30 if default_mode == "assault" else 0))
                if ratio < 1.0 and inc:
                    score -= 40.0                        # outnumbered with help on the way: no new POC yet, hold
                opts.append((score, {"kind": "assault", "poc": i, "point": (p["x"], p["y"])}))
        if own_pocs and reach:
            # defend the own POC the enemy is closest to
            i, p = min(own_pocs.items(), key=lambda kv: min(dist((kv[1]["x"], kv[1]["y"]), e.pos) for e in reach))
            dmin = min(dist((p["x"], p["y"]), e.pos) for e in reach)
            score = 90 - dmin / 30.0 + (40 if default_mode == "hold" else 0)
            opts.append((score, {"kind": "defend", "poc": i, "point": (p["x"], p["y"])}))
        contact = [e for e in reach if dist(e.pos, my_c) < 1000]
        if contact and ratio >= self.p["retreat"]:
            # the armies are in contact: fight it out where it is (never walk away from a fight we can win)
            opts.append((150 * push * min(ratio, 2.0), {"kind": "engage", "poc": None, "point": centroid(e.pos for e in contact)}))
        # (user 2026-10-24 21:59: NPCs in a battle with players hardly attacked and kept following the player's units)
        # ALLIES IN A FIGHT: when an allied unit (a player's, another NPC's) is in contact, go and fight beside it
        ids = {u.id for u in mine}
        # (user 2026-10-25 13:40) ... and own-side units too: when ANY friendly unit (another squad of this side, an ally, a
        # player) meets an enemy, the rest of the side goes to support it - the enemy list is shared by the whole side
        allies_f = [f for f in (friends or ()) if f.hp > 0]
        a_contact = [e for e in reach if any(dist(e.pos, f.pos) < 700 for f in allies_f)]
        if a_contact and ratio >= self.p["retreat"] * 0.7:
            opts.append((165 * push * min(max(ratio, 0.8), 2.0),
                         {"kind": "engage", "poc": None, "point": centroid(e.pos for e in a_contact)}))
        if reach:
            # hunt the weakest visible enemy group (enemies near their centroid)
            ec = centroid(e.pos for e in reach)
            near = [e for e in reach if dist(e.pos, ec) < 600]
            score = 70 * push + 25 * min(2.0, ratio) - dist(my_c, ec) / 50.0
            opts.append((score, {"kind": "hunt", "poc": None, "point": ec}))
        if ratio < self.p["retreat"] and enemies:
            # outnumbered: regroup where the threat is lowest near the own side (gates / own POCs / home)
            anchors = [(p["x"], p["y"]) for p in own_pocs.values()] + [off_gate(u.gate or u.home, u.gate) for u in mine]
            safe = min(anchors, key=lambda q: tgrid.get((int(q[0] // CELL), int(q[1] // CELL)), 0.0)) if anchors else my_c
            ids = {u.id for u in mine}
            allies = [f for f in (friends or ()) if f.id not in ids]
            if allies:                                   # (2026-10-24) with allies on the map: close up on them, not the gate
                safe = centroid(f.pos for f in allies)
            opts.append((200 * (self.p["retreat"] - ratio) + 60, {"kind": "regroup", "poc": None, "point": safe}))
            if own_pocs and (inc or len(own_pocs) >= len(enemy_pocs)):
                # (10-31) losing but holding POCs (or help coming): dig in on the own POC under the least fire and wait for
                # the reinforcements instead of giving the POCs up and walking back to the gate
                i, p = min(own_pocs.items(), key=lambda kv: tgrid.get((int(kv[1]["x"] // CELL), int(kv[1]["y"] // CELL)), 0.0))
                opts.append((200 * (self.p["retreat"] - ratio) + 75 + 15 * min(inc, 3),
                             {"kind": "defend", "poc": i, "point": (p["x"], p["y"])}))
        hurt = now - self.__dict__.get("_hurt", {}).get(side, -999) < 25.0
        if hurt and enemies and not self.alien:
            # DEFENCE: knows it holds the province; once hit it goes after the nearest attacker (even one it cannot shoot yet:
            # artillery / cloaked / out of sight range) instead of standing on its POC
            tgt = min(enemies, key=lambda e: dist(my_c, e.pos))
            opts.append((145 * push, {"kind": "hunt", "poc": None, "point": tgt.pos}))
        if not reach and not enemy_pocs and not self.alien:
            # (user 2026-10-25 12:17) a defence with no enemy in sight only marched to its POC and stood there: it now SEARCHES -
            # first where an enemy was last seen, else it sweeps a ring of waypoints around the own POCs (never far from them)
            ls = self.__dict__.setdefault("_last_seen", {})
            if enemies:
                ls[side] = (centroid(e.pos for e in enemies), now)
            sr = self.__dict__.setdefault("_search", {}).setdefault(side, {"i": 0, "t": now, "pt": None})
            seen = ls.get(side)
            if seen and now - seen[1] < 90:
                pt = seen[0]
            else:
                if sr["pt"] is None or now - sr["t"] > 45 or dist(my_c, sr["pt"]) < 220:
                    base = centroid([(p["x"], p["y"]) for p in own_pocs.values()]) or my_c
                    sr["i"] += 1
                    ang = sr["i"] * 2.4
                    r = 500 + 250 * (sr["i"] % 3)
                    sr["pt"] = clamp_map((base[0] + r * math.cos(ang), base[1] + r * math.sin(ang)))
                    sr["t"] = now
                pt = sr["pt"]
            opts.append((60, {"kind": "search", "poc": None, "point": pt}))
        if not opts:
            opts.append((0, {"kind": "hold", "poc": None, "point": my_c}))
        sc, best = max(opts, key=lambda x: x[0])
        if pl:                                           # keep the running plan unless a clearly better one appears
            cur = [o for o in opts if o[1]["kind"] == pl["kind"] and o[1].get("poc") == pl.get("poc")]
            if cur and cur[0][0] + PLAN_STICK >= sc:
                sc, best = cur[0]
        best.update(t=now, ratio=ratio)
        if not pl or pl["kind"] != best["kind"] or pl.get("poc") != best.get("poc"):
            self.log.append((now, side, best["kind"], best.get("poc"), round(ratio, 2)))
        self.plans[side] = best
        return best

    # ---------------------------------------------------------------- focus targets
    def focus(self, squad, enemies, now):
        """ranked enemy targets for one squad: dangerous + easy to kill first, artillery / support preferred"""
        c = centroid(u.pos for u in squad)
        reach = max((u.max_rng() for u in squad), default=200) + ENGAGE_PAD
        cand = []
        for e in enemies:
            d = dist(c, e.pos)
            if d > reach + 300:
                continue
            if not any(u.can_hit(e) for u in squad):
                continue
            value = (e.dps() + 5) / (e.hp + 50) * 1000
            if not any(e.can_hit(u) for u in squad):
                value *= 1.3                                  # it cannot shoot back at us: free damage

            if e.role == "artillery":
                value *= 1.6
            elif e.role == "support":
                value *= 1.4
            value *= 1.0 / (1.0 + d / 500.0)
            cand.append((value, e))
        cand.sort(key=lambda x: -x[0])
        ranked = [e for _v, e in cand]
        if len(ranked) > 1 and self.rnd.random() < self.p["mistake"]:
            ranked[0], ranked[1] = ranked[1], ranked[0]
        return ranked

    # ---------------------------------------------------------------- main step
    def decide(self, units, pocs, same_side, now, controlled=None, default_mode=None, stealth=frozenset()):
        """units: {uid: U}; controlled: set of sides the brain plays (None = every side with ai units).
        -> list of orders ('attack', uid, target) / ('move', uid, (x, y))"""
        orders = []
        self._claims = set()
        self._dload = {}
        self._load = {}
        ai_units = [u for u in units.values() if u.ai and u.hp > 0]
        sides = {u.side for u in ai_units} if controlled is None else set(controlled)
        for side in sides:
            mine = [u for u in ai_units if u.side == side]
            if not mine:
                continue
            enemies = [e for e in units.values() if e.hp > 0 and not same_side(side, e.side) and e.id not in stealth]
            # (user 2026-10-24 06:57) the force ratio counts EVERY friendly unit - players and allied NPCs too: an NPC
            # that came to help a player saw only its own squad against the whole enemy and retreated at once
            friends = [f for f in units.values() if f.hp > 0 and same_side(side, f.side)]
            dm = default_mode or ("hold" if sum(u.mode == "hold" for u in mine) * 2 > len(mine) else "assault")
            if self.alien:
                plan = {"kind": "territory", "poc": None, "point": None}
            else:
                plan = self.plan(side, mine, enemies, pocs, same_side, now, dm, friends=friends)
            tgrid = self.threat_grid(enemies)
            self._respond = self._poc_response(side, mine, enemies, pocs, same_side)
            squads = {}
            for u in mine:
                squads.setdefault(u.squad, []).append(u)
            for key, sq in squads.items():
                od = self.orders.get(key)
                if od is not None and now < od.get("until", 0):
                    orders += self._ordered(sq, od, enemies, pocs, now)
                    continue
                if od is not None:
                    self.orders.pop(key, None)
                orders += self._squad(sq, enemies, plan, pocs, same_side, now, tgrid, mine, friends=friends)
            orders = self._tactics(mine, enemies, friends, orders, pocs, same_side, now)
        return self._gate(orders, units, now)

    # ---- UNIT FUNCTIONS (user 2026-10-24 19:45: the NPC AI must use what its units can do).  Lump 0x30 formats
    # CONFIRMED from the client's senders (004dd860..004e1b36: u32 unit, u8 ACTION, then u8 / u16 / u32 writers):
    #   21 Grenade [u32 target]   59 Virus attack [u32]   60 Virus kill [u32]   12 Refuel [u32 friend]   8 Mine []
    #   9 bombArd mode [u8 on]    34 Flak Attack mode [u8 on]   35 Booster [u8 on]   55 Energy production [u8 on]
    def _tactics(self, mine, enemies, friends, orders, pocs, same_side, now):
        mem_all = self.__dict__.setdefault("_tac", {})
        by = {}
        for o in orders:
            by.setdefault(o[1], []).append(o)
        extra, drop = [], set()
        for u in mine:
            if not u.skills or u.hp <= 0:
                continue
            m = mem_all.setdefault(u.id, {})
            mine_o = [o for o in by.get(u.id, []) if o[0] != "skill"]
            mv = next((o for o in mine_o if o[0] == "move"), None)
            ground_e = [e for e in enemies if not e.air]
            near = lambda lst, r, p=u.pos: [e for e in lst if dist(e.pos, p) <= r]
            # -- artillery deploy modes: bombArd vs ground, Flak Attack vs air.  In the mode the client fires by itself
            #    at what is ONE RANGE AHEAD (fog circle 0048ea50), so the unit first turns toward the enemy.
            for sk, act, pool in (("bombard", 9, ground_e), ("flak", 34, [e for e in enemies if e.air])):
                if sk not in u.skills or u.air:
                    continue
                key = "m" + sk
                rng = max(u.rng_g, u.rng_a, 200)
                tgt = near(pool, rng + 60)
                if m.get(key):
                    if tgt:
                        m["seen"] = now
                    if now - m.get("seen", now) > 8 or (mv and dist(mv[2], u.pos) > rng * 1.5 and not tgt):
                        m[key] = False
                        extra.append(("skill", u.id, (act, 0), sk + " release"))
                    else:
                        drop.add(u.id)                      # deployed: no move / attack orders
                    continue
                if tgt and not (mv and mv[3] in ("fallback", "flee", "wounded")):
                    ec = centroid(e.pos for e in tgt)
                    if now - m.get("face_t", -99) > 6:
                        m["face_t"] = now                   # turn toward the enemy (a short step), deploy next tick
                        drop.add(u.id)
                        extra.append(("move", u.id, clamp_map(toward(u.pos, ec, 36)), "face for " + sk))
                    elif now - m["face_t"] >= 1.2:
                        m[key], m["seen"] = True, now
                        drop.add(u.id)
                        extra.append(("skill", u.id, (act, 1), sk))
                    else:
                        drop.add(u.id)
            if u.id in drop:
                continue
            # -- Volte: energy production mode next to its friends in a fight, then refuel them one by one
            if "energy" in u.skills:
                fr = [f for f in friends if f.id != u.id and f.role != "support" and dist(f.pos, u.pos) < 380]
                if m.get("energy"):
                    if near(enemies, 1100):
                        m["seen"] = now
                    if now - m.get("seen", now) > 10 or not fr:
                        m["energy"] = False
                        extra.append(("skill", u.id, (55, 0), "energy release"))
                    else:
                        drop.add(u.id)
                        if "refuel" in u.skills and now - m.get("rf", -99) > 6:
                            m["rf"] = now
                            k = m["rk"] = (m.get("rk", -1) + 1) % len(fr)
                            extra.append(("skill", u.id, (12, fr[k].id), "refuel"))
                    continue
                if len(fr) >= 2 and near(enemies, 1000):
                    m["energy"], m["seen"] = True, now
                    drop.add(u.id)
                    extra.append(("skill", u.id, (55, 1), "energy production"))
                    continue
            # -- Grenade: the enemy group with the most units inside the 128 px splash
            if "grenade" in u.skills and now - m.get("gr", -99) > 8:
                c = near(ground_e, 300)
                if c:
                    best = max(c, key=lambda e: (sum(dist(e.pos, o.pos) <= 128 for o in c), -e.hp))
                    if sum(dist(best.pos, o.pos) <= 128 for o in c) >= 2 or best.hp < best.hpmax * 0.3:
                        m["gr"] = now
                        extra.append(("skill", u.id, (21, best.id), "grenade"))
                        continue
            # -- Virus: infect the strongest enemy close by (attack), finish a wounded one (kill)
            if "virus" in u.skills and now - m.get("vi", -99) > 12:
                c = near(enemies, 320)
                if c:
                    m["vi"] = now
                    weak = [e for e in c if e.hp < e.hpmax * 0.35]
                    if weak:
                        extra.append(("skill", u.id, (60, min(weak, key=lambda e: e.hp).id), "virus kill"))
                    else:
                        extra.append(("skill", u.id, (59, max(c, key=lambda e: (e.dps(), e.hp)).id), "virus attack"))
                    continue
            # -- Sapper: mines where it holds (a POC of its side close by), never with the enemy on top of it
            if "mine" in u.skills and now - m.get("mn", -99) > 25 and m.get("mines", 0) < 4 and not near(enemies, 260):
                own = [p for p in (pocs or {}).values() if same_side(u.side, p.get("owner")) and dist(u.pos, (p["x"], p["y"])) < 260]
                if own or u.mode == "hold":
                    m["mn"], m["mines"] = now, m.get("mines", 0) + 1
                    extra.append(("skill", u.id, (8,), "mine"))
            # -- Booster: on for a long walk with no enemy close, off in the fight
            if "booster" in u.skills:
                far_walk = mv is not None and dist(mv[2], u.pos) > 700 and not near(enemies, 600)
                if far_walk and not m.get("boost"):
                    m["boost"] = True
                    extra.append(("skill", u.id, (35, 1), "booster on"))
                elif m.get("boost") and not far_walk and (near(enemies, 600) or mv is None):
                    m["boost"] = False
                    extra.append(("skill", u.id, (35, 0), "booster off"))
        if not extra and not drop:
            return orders
        return [o for o in orders if o[1] not in drop or o[0] == "skill"] + extra

    def _rally(self, sq):
        """gathering point of a squad: the centroid of its units nearest to the gate it came in by (the tail), so the
        head waits for the tail instead of the other way round."""
        g = sq[0].gate or sq[0].home or centroid(u.pos for u in sq)
        near = sorted(sq, key=lambda u: dist(u.pos, g))[:max(1, (len(sq) + 1) // 2)]
        return off_gate(centroid(u.pos for u in near), sq[0].gate)

    def _gathering(self, sq, plan, near_e, now):
        """True while this squad should close up before it attacks (weaker side, units spread out, no enemy on it)."""
        gs = self.__dict__.setdefault("_gather", {})
        key = sq[0].squad
        if self.alien or len(sq) < 3 or plan.get("kind") in ("regroup", "defend") or near_e \
                or plan.get("ratio", 9.0) >= GATHER_RATIO:
            gs.pop(key, None)
            return False
        rally = self._rally(sq)
        close = sum(1 for u in sq if dist(u.pos, rally) <= GATHER_RADIUS)
        if close >= GATHER_SHARE * len(sq):
            gs[key] = -1.0                                     # gathered: go (until it is strung out again)
            return False
        t0 = gs.get(key)
        if t0 == -1.0 and close >= 0.5 * len(sq):
            return False                                       # already on its way together
        if t0 is None or t0 == -1.0:
            gs[key] = t0 = now
        return now - t0 < GATHER_MAX

    def _poc_response(self, side, mine, enemies, pocs, same_side):
        """an enemy standing on a POC with none of ours there = it is being taken: the nearest free units (nothing in
        their own weapon range) go and kill the capturers.  -> {uid: enemy unit on that POC}"""
        out = {}
        for i, p in pocs.items():
            q = (p["x"], p["y"])
            on_e = [e for e in enemies if dist(e.pos, q) < 160]
            if not on_e or any(dist(u.pos, q) < 160 for u in mine):
                continue
            need = min(4, len(on_e) * 2)
            free = [u for u in mine if u.id not in out and u.role not in ("support",) and u.dps() > 0
                    and not any(dist(u.pos, e.pos) <= u.max_rng() for e in enemies)]
            free.sort(key=lambda u: dist(u.pos, q))
            for u in free[:need]:
                if dist(u.pos, q) < 2200:
                    out[u.id] = min(on_e, key=lambda e: dist(e.pos, u.pos))
        return out

    def _squad(self, sq, enemies, plan, pocs, same_side, now, tgrid, mine=(), friends=None):
        out = []
        side = sq[0].side
        c = centroid(u.pos for u in sq)
        near_e = [e for e in enemies if dist(e.pos, c) < SQUAD_RADIUS]
        near_f = [f for f in (friends or mine or sq) if dist(f.pos, c) < SQUAD_RADIUS]   # every friendly unit nearby
        ratio = self.power(near_f) / max(1e-6, self.power(near_e)) if near_e else 9.0
        ranked = self.focus(sq, enemies, now)
        fighters = [u for u in sq if u.role not in ("support",)]
        # ---- fall back when this squad is clearly losing (not aliens guarding a hive: they fight to the end)
        fallback = (ratio < self.p["retreat"] * 0.8 and near_e and not self.alien) or plan["kind"] == "regroup"
        if self.alien:
            # aliens: territorial - fight what comes close to home, chase up to the leash, wounded flee home
            for u in sq:
                tgt = self._pick(u, ranked, enemies, leash_from=u.home, leash=1400)
                if u.hp / u.hpmax < 0.2 and u.role != "boss" and near_e:
                    out.append(("move", u.id, clamp_map(u.home), "flee"))
                elif tgt is not None:
                    out.append(("attack", u.id, tgt.id, "fight"))
                elif dist(u.pos, u.home) > 300:
                    out.append(("move", u.id, clamp_map(u.home), "home"))
            return out
        # anchor of the squad: the plan's point; with no enemy near and the plan on the attack, each squad takes its
        # own enemy POC (nearest one no other squad has claimed) - spreading out to capture, regrouping to fight
        anchor = plan["point"] or c
        obj_poc = plan.get("poc")
        far = not any(dist(e.pos, c) < 1500 and any(x.can_hit(e) for x in sq) for e in enemies)
        # (2026-10-24) splitting up to take several POCs at once only when clearly stronger - otherwise the army
        # stays together (concentration wins fights: arena, the split army lost piece by piece)
        if far and plan["kind"] in ("assault", "hunt", "hold") and plan.get("ratio", 1.0) >= SPLIT_RATIO:
            claims = self.__dict__.setdefault("_claims", set())
            free = [(i, p) for i, p in pocs.items() if not same_side(side, p["owner"]) and i not in claims]
            if free:
                obj_poc, p = min(free, key=lambda kv: dist(c, (kv[1]["x"], kv[1]["y"])))
                claims.add(obj_poc)
                anchor = (p["x"], p["y"])
        if fallback:
            ec = centroid(e.pos for e in near_e) or anchor
            safe = off_gate(plan["point"] if plan["kind"] == "regroup" else toward(c, ec, -500), sq[0].gate)
            ids = {x.id for x in (mine or sq)}
            with_allies = any(f.id not in ids and dist(f.pos, safe) < 500 for f in (friends or ()))
            for u in sq:
                if u.role == "support" and u.skills and self._support_skills(u, mine or sq, enemies, now, out, True):
                    continue
                # shoot while falling back; once back beside the allies (regroup on them) hold there and fight with
                # them instead of only trailing after their units (user 2026-10-24 21:59)
                at_rally = with_allies and dist(u.pos, safe) < 300
                tgt = self._pick(u, ranked, enemies, max_d=u.max_rng() + (ENGAGE_PAD // 2 if at_rally else 40))
                if tgt is not None and u.role != "support" and (u.role == "artillery" or at_rally):
                    out.append(("attack", u.id, tgt.id, "cover"))
                elif at_rally:
                    continue                                                    # in place: no new order
                else:
                    out.append(("move", u.id, clamp_map(safe), "fallback"))
            return out
        # ---- GATHER (user 2026-10-24 07:06): against a stronger enemy a squad that is strung out (its units still
        # coming through the gate one by one) closes up first and goes in together; units already in range shoot
        if self._gathering(sq, plan, near_e, now):
            rally = self._rally(sq)
            for u in sq:
                tgt = self._pick(u, ranked, enemies, max_d=u.max_rng() + 20)
                if tgt is not None and u.role != "support":
                    out.append(("attack", u.id, tgt.id, "gather-fire"))
                elif dist(u.pos, rally) > GATHER_RADIUS * 0.6:
                    out.append(("move", u.id, clamp_map(rally), "gather"))
            return out
        front = centroid(e.pos for e in near_e) if near_e else None
        for u in sq:
            # ---- support: behind the fighters, away from the enemy
            if u.role == "support":
                if u.skills and self._support_skills(u, mine or sq, enemies, now, out, fallback):
                    continue
                fc = centroid(f.pos for f in fighters) or u.home
                away = front or (ranked[0].pos if ranked else None)
                p = toward(fc, away, -170) if away else fc
                out.append(("move", u.id, clamp_map(p), "support"))
                continue
            # ---- wounded: pull back behind the squad (others take its place)
            # (2026-10-24) only when somebody can mend it (healer for bio units, repairer for machines, a teleporter),
            # else pulling back just takes its guns out of the fight
            medic = any(("heal" if u.bio else "repair") in f.skills or "teleport" in f.skills
                        for f in (mine or sq) if f.id != u.id and f.hp > 0)
            if u.hp / u.hpmax < WOUNDED and len(fighters) > 2 and front is not None and medic:
                out.append(("move", u.id, clamp_map(toward(c, front, -260)), "wounded"))
                continue
            # ---- artillery: keep the stand-off distance from the nearest enemy, bombard the focus target
            if u.role == "artillery":
                # (user 2026-10-24 04:18: NPC self-propelled guns wandered about instead of shelling from range)
                # only enemies its gun can hit count: it never runs from aircraft it cannot shoot (they are faster
                # anyway) and never wanders off to POCs - it takes position at its range behind the army
                hit_e = [e for e in enemies if u.can_hit(e)]
                ne = min(hit_e, key=lambda e: dist(e.pos, u.pos)) if hit_e else None
                if ne is not None and not ne.air and dist(ne.pos, u.pos) < u.rng_vs(ne) * 0.45:
                    out.append(("move", u.id, clamp_map(toward(ne.pos, u.pos, u.rng_vs(ne) * 0.85)), "kite"))
                    continue
                tgt = self._pick(u, ranked, enemies, max_d=u.max_rng() + 900)
                if tgt is None and ne is not None and dist(ne.pos, c) < 1800:
                    tgt = ne
                if tgt is not None:
                    d = dist(u.pos, tgt.pos)
                    if d <= u.rng_vs(tgt) * 1.05:
                        out.append(("attack", u.id, tgt.id, "bombard"))
                    else:
                        out.append(("move", u.id, clamp_map(toward(tgt.pos, u.pos, u.rng_vs(tgt) * 0.85)), "standoff"))
                    continue
                if near_e or (plan["kind"] in ("engage", "defend", "hold") and fighters):
                    # nothing it can hit near: stay with the army, a little behind it
                    fc = centroid(f.pos for f in fighters if f.role != "artillery") or c
                    away = front or anchor
                    p = toward(fc, away, -200) if away and dist(fc, away) > 1 else fc
                    out.append(("move", u.id, clamp_map(p), "escort"))
                    continue
            # ---- KITE (2026-10-24, advanced / elite): a ranged unit that outranges the short-range enemy closing in
            # (melee, flamers ...) steps back to its own range and keeps shooting - the enemy walks into fire
            if self.p.get("kite") and u.role in ("line", "antiair") and u.spd > 0:
                cl = [e for e in enemies if u.can_hit(e) and e.can_hit(u) and not e.air
                      and u.rng_vs(e) - e.rng_vs(u) >= KITE_GAP and e.spd <= u.spd * 1.15
                      and dist(e.pos, u.pos) < e.rng_vs(u) + 70]
                if cl:
                    e = min(cl, key=lambda e: dist(e.pos, u.pos))
                    out.append(("move", u.id, clamp_map(toward(e.pos, u.pos, u.rng_vs(e) * 0.9)), "kite"))
                    continue
            # ---- a POC is being taken: go and kill the capturers
            rsp = getattr(self, "_respond", {}).get(u.id)
            if rsp is not None and u.can_hit(rsp):
                out.append(("attack", u.id, rsp.id, "contest"))
                continue
            # ---- capturers: take the plan's POC when the fight there is not hopeless
            # (2026-10-24) a capturer under fire far from its POC shoots back first (it cannot capture while
            # contested anyway); close to the POC it keeps walking onto it
            busy = [e for e in enemies if u.can_hit(e) and dist(u.pos, e.pos) <= u.rng_vs(e) + 10]
            if u.capt and busy and ratio < 2.5:
                tgt = self._pick(u, ranked, enemies, max_d=u.max_rng() + 20)
                if tgt is not None:
                    out.append(("attack", u.id, tgt.id, "capturer fights"))
                    continue
            if u.capt and plan["kind"] != "regroup":
                # capturers take POCs while the others fight: each its own POC (not ours, nobody else on the way),
                # the least defended first; one that is held by a strong enemy force is skipped
                claims = self.__dict__.setdefault("_claims", set())
                free = []
                for i, p in pocs.items():
                    if same_side(side, p["owner"]) or ("c", i) in claims:
                        continue
                    th = tgrid.get((int(p["x"] // CELL), int(p["y"] // CELL)), 0.0)
                    free.append((dist(u.pos, (p["x"], p["y"])) / 300.0 + th / 30.0, i, p))
                if free:
                    _s, i, p = min(free, key=lambda x: x[0])
                    if _s < 25:
                        claims.add(("c", i))
                        out.append(("move", u.id, clamp_map((p["x"], p["y"])), "capture"))
                        continue
            # ---- everyone else: focus fire, else go where the plan says
            tgt = self._pick(u, ranked, enemies, max_d=u.max_rng() + ENGAGE_PAD + (300 if plan["kind"] in ("hunt", "engage") else 0))
            if tgt is not None:
                out.append(("attack", u.id, tgt.id, "focus"))
                continue
            # RETALIATION (user 2026-10-25 13:31): a unit that was hit does not just stand there (except a capturer, handled
            # above): it walks at the nearest enemy it can hurt until that one is inside its own reach
            if now - self.__dict__.get("_hurt_u", {}).get(u.id, -999) < 20.0 and u.spd > 0:
                cl = [e for e in enemies if u.can_hit(e)]
                if cl:
                    e = min(cl, key=lambda e: dist(e.pos, u.pos))
                    out.append(("move", u.id, clamp_map(toward(e.pos, u.pos, max(40.0, u.rng_vs(e) * 0.8))), "retaliate"))
                    continue
            # nothing to shoot: an enemy / neutral POC close by and quiet -> stand on it (two units per POC)
            claims = self.__dict__.setdefault("_claims", set())
            opp = []
            for i, p in pocs.items():
                if same_side(side, p["owner"]):
                    continue
                q = (p["x"], p["y"])
                n_on = sum(1 for k in claims if k == ("o", i, 0) or k == ("o", i, 1))
                if n_on >= 2 or dist(u.pos, q) > OPPORTUNE:
                    continue
                if tgrid.get((int(q[0] // CELL), int(q[1] // CELL)), 0.0) > 60:
                    continue
                opp.append((dist(u.pos, q), i, q, n_on))
            if opp:
                _d, i, q, n_on = min(opp)
                claims.add(("o", i, n_on))
                out.append(("move", u.id, clamp_map(q), "opportune"))
                continue
            # flank: elite commanders approach through the cell with the least threat next to the anchor
            dest = anchor
            if plan["kind"] in ("engage", "hunt", "defend"):
                # walk only toward enemies this unit can shoot: ground-only weapons ignore aircraft (and the reverse)
                hit_e = [e for e in enemies if u.can_hit(e)]
                if hit_e:
                    close = [e for e in hit_e if dist(e.pos, anchor) < 900]
                    if close:
                        dest = centroid(e.pos for e in close)
                    elif plan["kind"] != "defend":
                        dest = min(hit_e, key=lambda e: dist(e.pos, u.pos)).pos
                else:
                    # nothing it can hit is here: take / hold a POC, else stay with the squad instead of
                    # standing under the aircraft as a free target
                    cand = [(p["x"], p["y"]) for p in pocs.values() if not same_side(side, p["owner"])]
                    if not cand:
                        cand = [(p["x"], p["y"]) for p in pocs.values()]
                    dest = min(cand, key=lambda q: dist(q, u.pos)) if cand else (c if dist(c, u.pos) > 200 else u.pos)
            if self.p["flank"] and front is None and (sum(map(ord, f"{u.squad}{plan['kind']}{plan.get('poc')}")) % 100) < self.p["flank"] * 100:
                best = None
                for dx in (-2, -1, 0, 1, 2):
                    for dy in (-2, -1, 0, 1, 2):
                        q = (anchor[0] + dx * CELL, anchor[1] + dy * CELL)
                        t = tgrid.get((int(q[0] // CELL), int(q[1] // CELL)), 0.0)
                        if best is None or t < best[0]:
                            best = (t, q)
                dest = best[1]
            # MARCH TOGETHER (2026-10-24, arena: the fast units arrived first and died one by one): far from the enemy
            # the army walks to a waypoint MARCH_STEP ahead of its own centre - the fast ones wait, the slow catch up
            if far and plan["kind"] in ("assault", "hunt", "engage", "defend", "search"):
                army = [f for f in (mine or sq) if f.role != "support" and f.hp > 0 and dist(f.pos, c) < 1600] or sq
                ac = centroid(f.pos for f in army)
                L = dist(ac, dest)
                if L > MARCH_STEP:
                    lead = ((u.pos[0] - ac[0]) * (dest[0] - ac[0]) + (u.pos[1] - ac[1]) * (dest[1] - ac[1])) / L
                    if lead > MARCH_STEP:
                        # too far ahead: wait where it stands (a stable order, no new intent every tick)
                        out.append(("move", u.id, clamp_map(u.pos), "wait for the army"))
                        continue
            spread = 26 * (hash(u.id) % 7 - 3) if not near_e and obj_poc is None else 12 * (hash(u.id) % 5 - 2)
            out.append(("move", u.id, clamp_map((dest[0] + spread, dest[1] - spread)), plan["kind"]))
        return out

    def _support_skills(self, u, allies, enemies, now, out, under_pressure):
        """support skills (user 2026-10-23 14:51).  -> True when this unit got its order for this tick.
          shield   : raise the bubble where it stands when >= 2 friends are inside and enemies are close (the fight is
                     going badly / friends are wounded / falling back); lower it when the enemy is gone.  It blocks
                     ground fire both ways, so it is a defensive tool: the support stays put while it is up.
          teleport : pull a badly wounded friend out of the fight to just behind the support (every TP_GAP s)
          heal     : bio units (infantry / organic)   repair: machines - the most wounded friend first; walk next to it,
                     then (re)start the skill every SKILL_REPEAT s"""
        mem = self.__dict__.setdefault("_sk", {}).setdefault(u.id, {})
        friends = [f for f in allies if f.id != u.id and f.hp > 0 and dist(f.pos, u.pos) < 900]
        if "shield" in u.skills:
            inside = [f for f in friends if dist(f.pos, u.pos) < SHIELD_R]
            threat = [e for e in enemies if dist(e.pos, u.pos) < 480]
            hurt = any(f.hp / f.hpmax < 0.5 for f in inside)
            shields = self.__dict__.setdefault("_shields", {})          # uid -> where a shield of this side is up
            near_sh = any(k != u.id and dist(p, u.pos) < 320 for k, p in shields.items())
            if not mem.get("shield") and threat and len(inside) >= 2 and (under_pressure or hurt) and not near_sh:
                shields[u.id] = u.pos
                mem["shield"], mem["sh_t"] = True, now
                out.append(("skill", u.id, (40, 1), "shield up"))
                return True
            if mem.get("shield"):
                if threat:
                    mem["sh_t"] = now
                elif now - mem["sh_t"] > 6:
                    mem["shield"] = False
                    self.__dict__.setdefault("_shields", {}).pop(u.id, None)
                    out.append(("skill", u.id, (40, 0), "shield down"))
                return True                                   # under its own shield: stay where it is
        if "teleport" in u.skills and now - mem.get("tp", -99.0) > TP_GAP:
            hurt = [f for f in friends if f.role != "support" and f.hp / f.hpmax < 0.35
                    and any(dist(e.pos, f.pos) < e.max_rng() + 80 for e in enemies)]
            if hurt:
                f = min(hurt, key=lambda f: f.hp / f.hpmax)
                ne = min(enemies, key=lambda e: dist(e.pos, u.pos)) if enemies else None
                dest = clamp_map(toward(u.pos, ne.pos, -140) if ne else u.pos)
                mem["tp"] = now
                out.append(("skill", u.id, (5, f.id, dest), "teleport out"))
                return True
        kinds = [k for k in ("heal", "repair") if k in u.skills]
        if kinds:
            cand = [f for f in friends if f.hp < f.hpmax * 0.75 and f.role != "support" or f.hp < f.hpmax * 0.5]
            cand = [f for f in cand if ("heal" in kinds and f.bio) or ("repair" in kinds and not f.bio)]
            if cand:
                f = min(cand, key=lambda f: (f.hp / f.hpmax, dist(f.pos, u.pos)))
                if dist(f.pos, u.pos) > SKILL_REACH:
                    out.append(("move", u.id, clamp_map(toward(f.pos, u.pos, SKILL_REACH * 0.6)), "to patient"))
                    return True
                if now - mem.get(("h", f.id), -99.0) > SKILL_REPEAT:
                    mem[("h", f.id)] = now
                    out.append(("skill", u.id, (6 if f.bio else 10, f.id), "heal" if f.bio else "repair"))
                return True
        return False

    def _ordered(self, sq, od, enemies, pocs, now):
        """a squad under an order: attack one unit (everyone who can hit it), or go to a point (engage / capture / hold /
        move) shooting what comes into range on the way; at the point it fights what is near."""
        out = []
        kind = od.get("kind")
        tgt = next((e for e in enemies if e.id == od.get("target") and e.hp > 0), None) if od.get("target") is not None else None
        point = tgt.pos if tgt is not None else od.get("point")
        if kind == "capture" and od.get("poc") in pocs:
            p = pocs[od["poc"]]
            point = (p["x"], p["y"])
        if point is None:
            return out
        ranked = self.focus(sq, enemies, now)
        for k, u in enumerate(sq):
            if tgt is not None and u.can_hit(tgt):
                out.append(("attack", u.id, tgt.id, "ordered: " + od.get("why", kind)))
                continue
            far = dist(u.pos, point) > 220
            pad = 20 if (far and kind in ("capture", "move")) else ENGAGE_PAD // 2
            e = self._pick(u, ranked, enemies, max_d=u.max_rng() + pad)
            if e is not None and (kind != "capture" or not u.capt or dist(u.pos, point) > 600):
                out.append(("attack", u.id, e.id, "ordered fight"))
                continue
            if far or (kind == "capture" and u.capt):
                spread = 20 * (k % 5 - 2), 20 * ((k // 5) % 3 - 1)
                q = point if (kind == "capture" and u.capt) else (point[0] + spread[0], point[1] + spread[1])
                out.append(("move", u.id, clamp_map(q), "ordered: " + od.get("why", kind)))
        return out

    def _pick(self, u, ranked, enemies, max_d=None, leash_from=None, leash=None):
        """the best focus target this unit can hit, spreading the squad (at most `focus` units per target, no overkill).
        2026-10-24: something already in weapon range is always shot before anything that must be walked to (arena:
        the brain spent 4x the time of the greedy AI walking to 'better' targets while being shot)."""
        if max_d is None:
            max_d = u.max_rng() + ENGAGE_PAD
        load = self.__dict__.setdefault("_load", {})
        dmg = self.__dict__.setdefault("_dload", {})
        def ok(e):
            return (e.hp > 0 and u.can_hit(e) and dist(u.pos, e.pos) <= max_d
                    and (leash_from is None or dist(leash_from, e.pos) <= leash))
        def inr(e):
            return dist(u.pos, e.pos) <= u.rng_vs(e) + 10
        def take(e):
            load[e.id] = load.get(e.id, 0) + 1
            dmg[e.id] = dmg.get(e.id, 0) + (u.dmg_a if e.air else u.dmg_g)
            return e
        def free(e):
            return load.get(e.id, 0) < self.p["focus"] and dmg.get(e.id, 0) < e.hp * OVERKILL
        in_range = [e for e in ranked if ok(e) and inr(e)]
        in_range += sorted((e for e in enemies if e not in in_range and ok(e) and inr(e)), key=lambda e: e.hp)
        # keep shooting the current target while it lives and stays reachable (no target flip-flop) - unless it
        # walked out of range and something else is in range
        last = self.last.get(u.id)
        if last is not None and last[0][0] == "attack":
            cur = next((e for e in enemies if e.id == last[0][1]), None)
            if cur is not None and ok(cur) and (inr(cur) or not in_range):
                return take(cur)
        for e in in_range:
            if free(e):
                return take(e)
        if in_range:
            return take(in_range[0])                      # all busy: still better than walking under fire
        for e in ranked:
            if ok(e) and free(e):
                return take(e)
        if self.alien:
            close = [e for e in enemies if ok(e)]
            if close:
                return min(close, key=lambda e: dist(u.pos, e.pos))
        return None

    # ---------------------------------------------------------------- reaction time / APM / order gate
    def _gate(self, orders, units, now):
        self._load = {}
        out = []
        by_side = {}
        for o in orders:
            kind, uid, arg, why = o
            u = units.get(uid)
            if u is None:
                continue
            if kind == "skill":
                by_side.setdefault(u.side, []).append((uid, ("skill",) + tuple(arg[:1]), (kind, uid, arg), why))
                continue
            key = (kind, arg if kind == "attack" else (int(arg[0] // MOVE_SAME), int(arg[1] // MOVE_SAME)))
            last = self.last.get(uid)
            if last is not None:
                lk, lt = last
                if lk == key:
                    continue                                  # same intent: nothing to send
                if kind == "move" and lk[0] == "move" and now - lt < MOVE_MIN_GAP:
                    continue
            # reaction time: a NEW intent is only acted on after the profile's reaction delay
            it = self.intent.get(uid)
            if it is not None and it[0] != key and kind == "move" and it[0][0] == "move" \
                    and abs(it[0][1][0] - key[1][0]) + abs(it[0][1][1] - key[1][1]) <= 4:
                it = (key, it[1])                             # same general direction: the pending reaction still counts
                self.intent[uid] = it
            if it is None or it[0] != key:
                rt = self.rnd.uniform(*self.p["react"])
                if kind == "attack" and last is not None and last[0][0] == "attack":
                    rt *= 0.3                                 # next target in the same fight: a quick click
                # the AI thinks once per TICK s: a reaction time shorter than a tick is a CHANCE to act right away
                # (average delay = rt), a longer one waits
                if rt < TICK and self.rnd.random() >= rt / TICK:
                    rt = 0.0
                it = (key, now + rt)
                self.intent[uid] = it
                if last is None:                              # the very first order goes out at once
                    it = (key, now)
            if now < it[1]:
                continue
            by_side.setdefault(u.side, []).append((uid, key, (kind, uid, arg), why))
        for side, lst in by_side.items():
            sec, used = self.budget.get(side, (int(now), 0))
            if sec != int(now):
                sec, used = int(now), 0
            room = max(1, int(self.p["apm"])) - used
            # attacks before moves (a human clicks the target first)
            lst.sort(key=lambda x: {"skill": 0, "attack": 1}.get(x[2][0], 2))
            for uid, key, order, why in lst[:max(0, room)]:
                if order[0] != "skill":
                    self.last[uid] = (key, now)
                out.append(order)
            self.budget[side] = (sec, used + min(len(lst), max(0, room)))
        return out
