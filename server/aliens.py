"""Alien design (claude/ALIEN_PLAN.md, decisions 2026-10-21):
  * level = planet tier base + distance from the nearest capital + hunting-ground depth (+-2); on the NOVICE planet
    capped at the highest branch (division) level among the players in the battle (user: "L34 too high, set it by
    the branch max level");
  * squads of 3-5 with roles; air aliens (Oizys / Manta / Mamos) from the Advanced planet on;
  * a neutral province has a GARRISON (0-100 %): kills lower it, it recovers +10 %/hour, the number of aliens is
    garrison x base count x participants factor; a player joining a running battle brings one more squad;
  * hunting grounds (CAVE 1-3): waves every WAVE_SECONDS, the last one with a boss;
  * counter-attacks (raids): aliens attack owned provinces next to strong neutral ones; undefended -> lost.
Pure functions + the world dict; sgserver.py does the packets."""
import random, time, math

TIER_LEVEL = {   # tier: (level at distance 1, +per distance step, {cave k: +bonus}, boss level)
    1: (2, 3.5, {1: 3, 2: 8, 3: 14}, 30),
    2: (20, 5.0, {1: 4, 2: 9, 3: 15}, 60),
    3: (45, 5.0, {1: 5, 2: 12, 3: 20}, 95),
}
# role multipliers: hp, damage, range (x20 = metres*20), speed (x10), armor
# fx = weapon CODE sent as stats9[2] (client 004c4ba0, claude/ATTACK_FX.md): class * 100 + projectile picture.
#   2xx = missile class -> green acid blob m0xxk.xpf flies to the target and bursts (m0xxke.xpf).  With 0 the client
#   drew no projectile and no hit effect at all (user 2026-10-22: alien attack animation incomplete).
ROLES = {
    "Ubik":   dict(code="g011", hp=1.5, dmg=0.9, rng=120, spd=12, arm=1.5, air=False, fx=207, cd=80),
    "Slanth": dict(code="g015", hp=0.8, dmg=1.3, rng=200, spd=14, arm=0.8, air=False, fx=205, cd=160),
    "Poda":   dict(code="g024", hp=0.9, dmg=1.0, rng=120, spd=24, arm=1.0, air=False, fx=207, cd=80),
    "Larva":  dict(code="g025", hp=0.6, dmg=0.8, rng=140, spd=16, arm=0.6, air=False, fx=207, cd=80),
    "Oizys":  dict(code="a006", hp=0.7, dmg=1.0, rng=160, spd=26, arm=0.6, air=True, fx=207, cd=80),
    "Manta":  dict(code="a017", hp=1.0, dmg=1.1, rng=180, spd=20, arm=0.9, air=True, fx=230, cd=80),
    "Mamos":  dict(code="a010", hp=1.3, dmg=1.2, rng=200, spd=16, arm=1.2, air=True, fx=230, cd=80),
    # HIVE NEST (CAVE_DESIGN.md, 2026-10-21): static, no weapon, spawns hunter squads; destroying every hive of a
    # cave = victory.  ART CODE IS A PLACEHOLDER (g026: 25-frame stand animation, looks like a structure) - check
    # in game with GM /spawn g026 and change HIVE_CODE.
    # 2026-10-22 (user: the nest never died): hp 8.0 / arm 2.5 gave 25 000 HP at L24 - 8 normal aliens
    "Hive":   dict(code="g026", hp=3.0, dmg=0.0, rng=0, spd=1, arm=1.2, air=False, fx=0),
}
HIVE_CODE = "g026"
# ---- DEMON-STAR MONSTERS (user 2026-10-24 17:58): unused tc/tc2.dat art, ONLY on the demon star (social.STAR_MAP).
# g026 = long-range attacker, g031 = close-range attacker (user); g033 / g047 / g048 / g050 ground, a020 / a012 / a019
# air.  Manual names where the manual has them (Rayoks g050, Charnal a020, Miasmal a012, Miasam a019); the others
# carry working names.  Manual HP: Rayoks-Evo1 2520, Charnal 3300, Miasmal 4350 (Ubik line ~1000) -> hp multipliers.
ROLES.update({
    "Spitter":  dict(code="g026", hp=1.0, dmg=1.4, rng=240, spd=12, arm=1.0, air=False, fx=205, cd=160),  # long range
    "Ripper":   dict(code="g031", hp=1.4, dmg=1.3, rng=60,  spd=20, arm=1.3, air=False, fx=207, cd=80),   # close range
    "Stinger":  dict(code="g033", hp=1.0, dmg=1.1, rng=100, spd=22, arm=1.0, air=False, fx=207, cd=80),
    "Scorpid":  dict(code="g047", hp=1.5, dmg=1.2, rng=120, spd=16, arm=1.5, air=False, fx=207, cd=80),
    "Arachnid": dict(code="g048", hp=1.2, dmg=1.2, rng=160, spd=18, arm=1.1, air=False, fx=205, cd=160),
    "Rayoks":   dict(code="g050", hp=2.2, dmg=1.4, rng=80,  spd=14, arm=1.8, air=False, fx=207, cd=80),
    "Charnal":  dict(code="a020", hp=1.8, dmg=1.4, rng=180, spd=28, arm=1.2, air=True,  fx=230, cd=80),
    "Miasmal":  dict(code="a012", hp=2.6, dmg=1.6, rng=200, spd=18, arm=1.8, air=True,  fx=230, cd=160),
    "Miasam":   dict(code="a019", hp=3.2, dmg=1.8, rng=220, spd=14, arm=2.2, air=True,  fx=230, cd=160),  # star boss
})
STAR_SPECIES = {   # same layout as SPECIES: (size per tier), weight, air
    "Spitter":  (((5, 7), (6, 8), (6, 9)), 3, False),
    "Ripper":   (((5, 7), (6, 8), (6, 9)), 3, False),
    "Stinger":  (((7, 9), (8, 10), (8, 12)), 3, False),
    "Scorpid":  (((4, 6), (5, 6), (5, 7)), 2, False),
    "Arachnid": (((5, 6), (5, 7), (6, 8)), 2, False),
    "Rayoks":   (((3, 4), (3, 5), (4, 5)), 1, False),
    "Charnal":  (((4, 6), (5, 6), (5, 7)), 2, True),
    "Miasmal":  (((2, 3), (2, 4), (3, 4)), 1, True),
}
STAR_AIR_SHARE = 0.35          # share of air squads on the demon star (any planet tier)
STAR_BOSS = "Miasam"           # the last wave's boss on the demon star
SQUAD_TEMPLATES = {      # ground squads; tier >= 2 also gets air squads
    "ground": [["Ubik", "Slanth", "Slanth"], ["Ubik", "Poda", "Slanth", "Larva"], ["Larva", "Larva", "Larva", "Poda"],
               ["Ubik", "Ubik", "Slanth", "Poda", "Larva"]],
    "air": [["Oizys", "Oizys", "Manta"], ["Manta", "Mamos", "Oizys"], ["Mamos", "Manta", "Manta", "Oizys"]],
}
AIR_FROM_TIER = 2
AIR_SQUAD_SHARE = {2: 0.25, 3: 0.35}           # chance that a squad is an air squad
PROVINCE_SQUADS = {1: (1, 2), 2: (2, 3), 3: (2, 4)}   # (distance <= 2, distance >= 3) - squads are 5-12 now
# ---- SAME-SPECIES SQUADS (user 2026-10-22 12:49 + answers: 5-12 of ONE kind, sizes by the creature's nature and
# random - a battle may even be all Larva; total strength about the same as before -> each alien is scaled by
# sqrt(SQUAD_REF / squad size); claude/ALIEN_SQUADS_PLAN.md)
SPECIES = {   # name: (size range novice, advanced, elite), weight, air
    "Larva":  (((8, 10), (9, 12), (10, 12)), 3, False),     # swarm
    "Poda":   (((6, 8), (6, 9), (7, 10)), 3, False),        # fast raiders
    "Ubik":   (((5, 6), (5, 7), (6, 8)), 2, False),         # front line, tough
    "Slanth": (((5, 6), (5, 7), (6, 8)), 2, False),         # long range
    "Oizys":  (((6, 8), (6, 9), (7, 10)), 3, True),
    "Manta":  (((5, 7), (5, 8), (6, 8)), 2, True),
    "Mamos":  (((5, 6), (5, 7), (5, 8)), 1, True),
}
SQUAD_REF = 4.0                 # the old mixed squads had about 4 aliens
SINGLE_SPECIES_BATTLE = 0.25    # chance that every squad of a battle is the same creature
HUNTER_DELAY_PROVINCE = 60      # s: the province hunter squad sets out
PATROL_STEP_SECONDS = (18, 30)  # patrol squads walk to the next way point of their route this often

def squad_scale(n):
    return math.sqrt(SQUAD_REF / max(1, n))

def species_squad(tier, name=None, rnd=random, star=False):
    """[name] * n for one squad; name None = random by weight (air kinds from the Advanced planet on).
    star = the demon star: only its own monsters (STAR_SPECIES), air squads on every tier."""
    pool = STAR_SPECIES if star else SPECIES
    if name is None:
        air = (rnd.random() < STAR_AIR_SHARE) if star else \
            (tier >= AIR_FROM_TIER and rnd.random() < AIR_SQUAD_SHARE.get(tier, 0))
        kinds = [(k, v[1]) for k, v in pool.items() if v[2] == air]
        name = rnd.choices([k for k, _w in kinds], [w for _k, w in kinds])[0]
    lo, hi = pool[name][0][max(1, min(3, tier)) - 1]
    return [name] * rnd.randint(lo, hi)
# (user 2026-10-27 14:05 "洞窟的外星怪物数量太少") x2, was {1: {1: 8, 2: 10, 3: 12}, 2: {1: 12, 2: 14, 3: 16}, 3: {1: 14, 2: 16, 3: 20}}
CAVE_UNITS = {1: {1: 16, 2: 20, 3: 24}, 2: {1: 24, 2: 28, 3: 32}, 3: {1: 28, 2: 32, 3: 40}}   # underground caves (wave mode)
# ---- CAVE 1/2/3 hive mode (user 2026-10-21 23:31: more aliens, hives in every cave, hives destroyed = victory,
# more aliens with more players).  mon1/2/3.nm are 256 x 256 (about 4 x a province map).
# (14:05) x1.5, was {1: {1: 30, 2: 38, 3: 45}, 2: {1: 45, 2: 52, 3: 60}, 3: {1: 52, 2: 60, 3: 75}}
CAVE_TOTAL = {1: {1: 45, 2: 57, 3: 68}, 2: {1: 68, 2: 78, 3: 90}, 3: {1: 78, 2: 90, 3: 113}}  # aliens per run, 1 player
CAVE_HIVES = {1: 2, 2: 3, 3: 4}            # hives per cave depth (+1 per 2 extra players, max +3)
CAVE_PLAYER_FACTOR = 0.75                  # +75 % aliens per extra player (provinces: +50 %)
CAVE_START_SHARE = 0.6                     # (14:05, was 0.5) share of the run placed at the start; the rest hatches from the hives
CAVE_ALIVE_CAP = 80                        # (14:05, was 60) aliens alive at once, +15 per extra player, at most CAVE_ALIVE_MAX
CAVE_ALIVE_STEP, CAVE_ALIVE_MAX = 15, 120
HIVE_SPAWN_SECONDS = 25                    # each hive hatches one squad this often while the run budget lasts
HIVE_SPAWN_SLOW = 2.0                      # budget used up: hives keep hatching, this many times slower
HUNTER_SHARE = {1: 1.0, 2: 1.0, 3: 1.0}    # (unused since 14:05) caves: every squad hunted the players (user 2026-10-22)
# (user 2026-10-27 14:05 "一部份主动攻击, 一部份巡逻") cave squads: this share HUNTS the players, the rest PATROL a
# route of spawn spots (and fight whoever comes within their aggro radius)
CAVE_HUNTER_SHARE = 0.5
CAVE_PATROL_POINTS = 4                     # way points of a cave patrol route (spawn spots near its start)
HUNT_GRACE = 20                            # seconds after the start before hunters move out
CAVE_LEASH = 60 * 32                       # guards in caves chase further (big maps)

def cave_plan(tier, cave, players):
    """(total aliens, hives, alive cap) of a hive-mode cave run for this number of players."""
    extra = max(0, players - 1)
    total = int(round(CAVE_TOTAL[tier][cave] * (1 + CAVE_PLAYER_FACTOR * extra)))
    hives = CAVE_HIVES[cave] + min(3, extra // 2)
    cap = min(CAVE_ALIVE_MAX, CAVE_ALIVE_CAP + CAVE_ALIVE_STEP * extra)
    return total, hives, cap

def squads_for(n_units, tier, rnd=random):
    out, total = [], 0
    while total < n_units:
        sq = squads(tier, rnd); out.append(sq); total += len(sq)
    return out
CAVE_WAVES = 3
WAVE_SECONDS = 240
PARTICIPANT_FACTOR = 0.5                         # +50 % per extra player at the start
MAX_ALIENS = 60
GARRISON_REGEN_PER_HOUR = 10.0
GARRISON_AFTER_LOSS = 30.0
AGGRO = {1: 8 * 32, 2: 10 * 32, 3: 12 * 32}      # pixels
HELP_RADIUS = 12 * 32
LEASH = {1: 30 * 32, 2: 30 * 32, 3: 45 * 32}
PATROL_RADIUS = 6 * 32
RAID_CHECK_SECONDS = 15 * 60
RAID_CHANCE = 0.2
RAID_MIN_GARRISON = 70.0
RAID_DEFEND_SECONDS = 10 * 60

def level_for(tier, dist, cave=0, rnd=random):
    base, step, cb, _boss = TIER_LEVEL[tier]
    lv = base + step * max(0, dist - 1) + (cb.get(cave, 0) if cave else 0)
    return max(1, int(round(lv)) + rnd.randint(-2, 2))

def cap_level(tier, lv, branch_max):
    if tier == 1 and branch_max:
        return max(1, min(lv, branch_max))
    return lv

def stats(name, lv, boss=False, scale=1.0):
    """hp, stats9, speed for a unit of this role/level (PLACEHOLDER curve, see plan section 8).
    scale: squad-size factor (squad_scale) for hp and damage."""
    r = ROLES[name]
    hp = (250 + 120 * lv) * r["hp"] * (4 if boss else 1) * scale
    dmg = (25 + 8 * lv) * r["dmg"] * (1.5 if boss else 1) * scale
    arm = 2 * lv * r["arm"]
    # cd = weapon cooldown (1/100 s).  2026-10-22 12:43 (user reference: streams of small green shots): the small acid
    # dot (m007k) shooters fire every 0.8 s; each shot does 60 % (armour is subtracted per hit, so halving the shot
    # would weaken them against armour: 60 % x 2 shots = +20 % raw, about even after armour).
    cd = r.get("cd", 160)
    if cd < 160:
        dmg = dmg * 0.6
    st9 = [int(arm), 0, r.get("fx", 0), int(dmg), r["rng"], cd, 0, 0, cd]
    return int(hp), st9, r["spd"]

def squads(tier, rnd=random, name=None, star=False):
    """one squad = 5-12 aliens of the same kind (old mixed templates: SQUAD_TEMPLATES, unused)."""
    return species_squad(tier, name, rnd, star)

MAP_REF_FREE = 14583            # walkable cells of a median 128 x 128 province map (server/map_sizes.json)
MAX_ALIENS_BIG = 80             # 256 x 256 maps

def map_factor(free_cells):
    """2026-10-22 12:55 (user: bigger maps more aliens): squads x sqrt(walkable area / median), 0.8 .. 2.0
    (a 256 x 256 province = about 2 x the squads)."""
    if not free_cells:
        return 1.0
    return max(0.8, min(2.0, math.sqrt(free_cells / MAP_REF_FREE)))

def province_units(tier, dist, garrison, players, rnd=random, size=1.0, star=False):
    """list of squads (lists of role names) for a neutral province battle; size = map_factor of the map."""
    near, far = PROVINCE_SQUADS[tier]
    n = near if dist <= 2 else far
    n = n * size * (garrison / 100.0) * (1 + PARTICIPANT_FACTOR * max(0, players - 1))
    n = max(1, int(round(n)))
    cap = MAX_ALIENS_BIG if size > 1.4 else MAX_ALIENS
    out, total = [], 0
    one = species_squad(tier, None, rnd, star)[0] if rnd.random() < SINGLE_SPECIES_BATTLE else None
    for _ in range(n):
        sq = squads(tier, rnd, one, star)
        if total + len(sq) > cap: break
        out.append(sq); total += len(sq)
    return out

def cave_wave(tier, cave, players, wave, rnd=random, star=False):
    units = CAVE_UNITS[tier][cave] * (1 + PARTICIPANT_FACTOR * max(0, players - 1)) / CAVE_WAVES
    out, total = [], 0
    while total < units:
        sq = squads(tier, rnd, star=star); out.append(sq); total += len(sq)
    if star and wave >= CAVE_WAVES:
        out.append([STAR_BOSS])          # demon star: the last wave ends with a Miasam boss
    return out

# ---- garrison (world["garrison"][pid] = [value, unix time]) -------------------------------------------------
def garrison(world, pid, now=None):
    now = now or time.time()
    g = world.setdefault("garrison", {}).get(str(pid))
    if not g:
        return 100.0
    v, t = g
    return min(100.0, v + GARRISON_REGEN_PER_HOUR * max(0.0, now - t) / 3600.0)

def set_garrison(world, pid, value, now=None):
    world.setdefault("garrison", {})[str(pid)] = [max(0.0, min(100.0, value)), now or time.time()]

def garrison_kill(world, pid, full_count):
    """one alien of a province garrison killed: -100/full_count %."""
    set_garrison(world, pid, garrison(world, pid) - 100.0 / max(1, full_count))

def formation(n, spacing=28):
    """offsets of n squad members around their point: rings of 1, 6, 12 ..."""
    out = [(0, 0)]
    ring = 1
    while len(out) < n:
        k = 6 * ring
        for i in range(k):
            a = 2 * math.pi * i / k
            out.append((int(spacing * ring * math.cos(a)), int(spacing * ring * math.sin(a))))
            if len(out) >= n:
                break
        ring += 1
    return out[:n]

# ---- AI helpers -----------------------------------------------------------------------------------------------
def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])

FOCUS_MAX = 3                   # at most this many aliens pick the same player unit (the rest take the next one)

def pick_target(tier, apos, cands, hp_of, radius, busy=None):
    """cands: {uid: (x, y)}; tier 3 focuses the weakest unit in reach, others the nearest.
    busy: {uid: aliens already on it} -> prefer units with fewer than FOCUS_MAX attackers."""
    inr = {u: p for u, p in cands.items() if dist(apos, p) <= radius}
    if not inr:
        return None
    if busy:
        free = {u: p for u, p in inr.items() if busy.get(u, 0) < FOCUS_MAX}
        if free:
            inr = free
    if tier >= 3:
        return min(inr, key=lambda u: (hp_of(u), dist(apos, inr[u])))
    return min(inr, key=lambda u: dist(apos, inr[u]))
