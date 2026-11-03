# sgserver part "battle_rules": unit skills, battle judge, deaths, skill timing, transport/shield, frames, alien raids.
# Loaded by sgserver.py into ONE shared namespace (exec, in the order of PARTS) - not an importable module;
# every name here is a sgserver global.  Checks: python tools/check_server.py
# ---- UNIT SKILLS (research_skills.md; CONFIRMED FUN_004d49a0: u64 ability bit -> command button) -----------------
# Skills come from EQUIPMENT: item 'Special' (items.json stats) -> ability bit.  Some chassis have innate skills
# (their default equipment in the original; hlp texts) -> CHASSIS_SKILLS.  Installed-only skills need bit 31.
SPECIAL_BITS = {"Anti-Grav Harness": 3, "Self Destruct": 4, "Disguise": 5, "EMP Grenade": 6, "Mind Warp": 7,
                "Grenade": 8, "After Burner": 9, "Neutron Shield": 10, "Sensor Evasion": 11, "EMP Attack": 12,
                "Charge EMP Mine": 13, "Cloak": 14, "Refuel": 15, "Mine Detector": 16, "Radar Jammer": 17,
                "Bombard": 21, "Charge Mine": 22, "Heal": 25, "Teleport Unit": 26, "Transport Unit": 28,
                "Identify": 29, "Radar": 30, "Short Circuit": 32, "IRBM": 33, "Camouflage": 34, "Air Bombard": 37,
                "Speed Boost": 38, "Allow Phase": 35, "Warp": 52, "Link Gate": 39, "Carpet Bomb": 40, "Flare": 42, "Shield": 43, "Altcharge": 36,
                "Detect": 45, "Snipe": 46, "Chemical Mine": 47, "Earthquake": 48, "IRBM Defense": 49, "Fusion Storm": 50}
INSTALL_ONLY = {16, 17, 29, 30, 39}
# chassis that HAVE installed-state art (*SG.xpf in tc.dat / tc2.dat, listed 2026-10-22); others never get Install (bit 31)
INSTALL_ART = {"a016", "a024", "g002", "g004", "g006", "g010", "g034", "g035", "g037", "g041", "g042", "g053", "g054",
               "g055", "g056", "g058"}
# user 2026-10-24 14:06: NO innate chassis skills - every skill comes from equipment (like the original: each of the
# old entries - Daeva Grenade, Sapper Charge Mine, Liche IRBM Defense, Gear-Doc Repair, Orbus Teleport, Leviathan
# Neutron Shield, Volte Refuel, Triage Heal/Repair - has items for that chassis' own slots).  The support chassis get
# their role item in the stock loadout instead (units_items_lab.STOCK_SKILL).
# user 2026-10-24 14:18: EXCEPT these two keep their innate skill - their role items are out of reach for a fresh unit
# (Gear-Doc: the lowest Repair item is tech level 45; Daeva: a grenade does not fit its 73 kg weight capacity).
CHASSIS_SKILLS = {"g023": [20], "g001": [8]}     # Gear-Doc Repair, Daeva Grenade
# (17:01, user) artillery (Arbalest g010, Ballista g034, Trebuchet g037) deploys through its WEAPON skill (bombArd /
# Flak Attack, bits 21 / 37 = command 6/7 and 35/36), not the generic Install; the Triage (g056) deploys with its own
# "Heal install mode" (bit 56).  No generic Install (bit 31) for them.
NO_GENERIC_INSTALL = {"g010", "g034", "g037", "g056",
                      # (17:07 audit) units whose deploy is their OWN command: Vulture bombArd (Bombard shells),
                      # Apparition sNipe / sNipe release (Snipe), Orbus sHield install (Shield)
                      "a024", "g042", "g035",
                      # (17:15) Volte "E Energy production mode" (bit 54)
                      "g055"}
# (18:25, user: the Mantlet had no R button) client 004d49a0 at 004d53a5: ability bit 57 does NOT give a button of its
# own - it puts command 63 "B Dispose bUnker" in the list of command 4 (Install), i.e. the commands of an INSTALLED
# unit.  So the Mantlet deploys with the generic Install (bit 31, I); installed with bit 57 it is a bunker (004cfe16
# sets +0x1e), "B Dispose bunker" appears, and Install release with bit 57 first ejects the units inside (004da079 ->
# 004d9530).  Mantlet therefore keeps Install.
CHASSIS_DEPLOY = {"g055": 54, "g058": 57}
# (17:15) Virus "V Virus attack" (bit 59) / "D Virus kill" (bit 58): infect an enemy unit and make it explode;
# energy / power = its Virus Decay weapon (the strongest equipped one)
VIRUS_ART = {"g057"}
HEAL_INSTALL_ART = {"g056"}

# PUT_UNIT skill entries (CONFIRMED 2026-10-20, client 004ac800 -> 004c4fa0): after the u64 abilities,
# u8 n + n x {u8 ABILITY BIT, u16 A, u16 B} -> unit +0x160[bit] = A, +0x258[bit] = B.
#   A = ENERGY: per use for one-shot skills (e.g. Grenade: 4e0acb 'energy >= A', then 4cb4b0 spends A),
#       per second while a toggle is on (Cloak, Camouflage, Afterburner, ... 004cfea0 adds A to the upkeep).
#   B = POWER (damage / heal amount, passed to the effect 4cb3d0); bit 20 Repair / 25 Heal -> heal rate (+0x374),
#       bit 18 -> 004c4b90, bit 55 -> overrides the sight value.
# Without entries every skill costs 0 energy and has 0 power.  Values = the item's 'Energy Use' / 'Effectiveness'.
UNIT_SKILLS = {}       # uid -> [(bit, energy, power)] filled by unit_abilities, used by build_put_unit
# Energy upkeep: PUT +8 s8 = energy change per second in battle (client 004cfea0; negative = regeneration, capped
# at max).  ORIGINAL data: it is the sum of the equipped items' 'Energy Drain' (s8-sized values: 0 for almost every
# item, -4/-5 for the Fallout reactors) -> in battle only reactors regenerate; everything else is a battery.
# ('Energy Recharge' of storage items, 15..363, is the refill outside battle: every battle entry starts full.)
UNIT_REGEN = {}        # uid -> regeneration per second (= -sum Energy Drain)

VIRUS_DMG_PER_PCT = 50        # Decay weapon damage -> % of max HP the infection takes (750 -> 15 %, 4500 -> 90 %)
VIRUS_KEEP_MIN = 10           # an infected unit keeps at least 10 % of its max HP
VIRUS_DRAIN_PER_SEC = 16      # client 004cbfe0: 16 HP per second while infected
VIRUS_KILL_TICKS = 700        # client 004e74c0: a marked unit dies 7 s later

def virus_keep_pct(decay_damage):
    """POWER of "Virus attack" = % of max HP the infected target keeps."""
    return int(max(VIRUS_KEEP_MIN, min(95, 100 - round(decay_damage / VIRUS_DMG_PER_PCT))))

def _skill_item_bits(it):
    """ability bits an item grants.  (2026-10-24 check) the HP-restoring items have no 'Special' text, only the
    description: Medic 'repair damaged mechanical units' (Tool Kit, Assembly Arm, Restoration Gear ... - before only
    the ones with 'repair' in the NAME counted) and Triage 'replenish the HP of both biological and mechanical allies'
    (Regen Pad / Pod / Foci / Aura / Field = Heal AND Repair - before they granted nothing)."""
    st = it.get("stats", {})
    sp = st.get("Special")
    if sp in SPECIAL_BITS:
        return [SPECIAL_BITS[sp]]
    d = (it.get("desc") or "").lower()
    if "decreases the cooldown" in d:
        return [60]       # (17:07) Wight Overloader M1 / M2 -> "O Overload" (ability bit 60, command 72); had no skill
    
    if "Effectiveness" in st:
        if "both biological and mechanical" in d:
            return [25, 20]
        if "repair damaged mechanical" in d or "repair" in (it.get("name") or "").lower():
            return [20]
        if "heal injured biological" in d:
            return [25]
    return []

def _skill_item_bit(it):
    b = _skill_item_bits(it)
    return b[0] if b else None

BOOST_DEFAULT_PCT = 45
SELF_DESTRUCT_DEFAULT = 930  # Incendiary Detonator value      # Speed Boost item without a % in its text (Angel Harness); value seen in hlp.dat

def _skill_vals(it):
    """(energy, POWER) of a skill item.  POWER is unit +0x258[bit] (PUT skill entry B).
    2026-10-21 (client 0x4e432d / 004df4d0): Booster (bit 38) moves at speed * (100 + POWER) / 100 and Radar Jammer
    (bit 17) sends POWER as its ON flag -> both did nothing with POWER 0 (no 'Effectiveness' in items.json)."""
    import re as _re
    st = it.get("stats", {})
    clamp = lambda v: max(0, min(65535, int(round(float(v or 0)))))
    e, pw = clamp(st.get("Energy Use", 0)), clamp(st.get("Effectiveness", 0))
    b = _skill_item_bit(it)
    if b == 38 and not pw:
        m = _re.search(r"(\d+)\s*%", it.get("desc") or "")
        pw = int(m.group(1)) if m else BOOST_DEFAULT_PCT
    elif b == 17 and not pw:
        pw = 1
    elif b == 4 and not pw:
        pw = SELF_DESTRUCT_DEFAULT      # Fallout reactors: no Effectiveness -> client did 0 damage, server 500
    return e, pw

SKILL_DEFAULT = {}     # bit -> (energy, power) of the lowest tech item granting it (chassis / GM skills)
for _it in sorted(ITEMS, key=lambda it: it.get("stats", {}).get("Tech Level", 0) or 0):
    for _b in _skill_item_bits(_it):
        if _b not in SKILL_DEFAULT:
            SKILL_DEFAULT[_b] = _skill_vals(_it)
SKILL_DEFAULT[38] = (SKILL_DEFAULT.get(38, (0, 0))[0], SKILL_DEFAULT.get(38, (0, 0))[1] or 25)
SKILL_DEFAULT[17] = (SKILL_DEFAULT.get(17, (0, 0))[0] or 1330, SKILL_DEFAULT.get(17, (0, 0))[1] or 1)

UNIT_SIGHT = {}            # uid -> original sight in px (unit_view_px)
RECHARGE = {}              # uid -> (energy per second, recharge type) = PUT skill entry of ability bit 2

def storage_recharge(it):
    """recharge TYPE of a storage item: 1 solar, 2 gamma / nuclear (both everywhere), 3 battery (pads),
    4 methane (vents), 0 none (Fallout reactors, cells)."""
    d = (it.get("desc") or "").lower()
    n = (it.get("name") or "").lower()
    rate = _i(it.get("stats", {}).get("Energy Recharge", 0))
    if "not replenish" in d or not rate:
        return 0, 0
    if "battery" in d:
        return 3, rate
    if "methane" in d:
        return 4, rate
    if "gamma" in n or "nuclear" in d or "gamma" in d:
        return 2, rate
    if "solar" in d or "constantly" in d:
        return 1, rate
    return 0, 0

def unit_abilities(u):
    _c = u.get("chassis")
    # roster units are often stored by DISPLAY name ("Orbus") -> look the chassis skills up by art code
    bits = set(CHASSIS_SKILLS.get(CODE_OF.get(_c, _c), CHASSIS_SKILLS.get(_c, []))) | set(u.get("gm_skills", []))
    vals = {}
    for i in u.get("items", []):
        it = ITEM_BY_ID.get(i, {})
        for b in _skill_item_bits(it):
            bits.add(b)
            e, pw = _skill_vals(it)
            if b not in vals or (pw, -e) > (vals[b][1], -vals[b][0]):   # higher power, then cheaper
                vals[b] = (e, pw)
    # user 2026-10-24 14:34 (can the Triage deploy?): every chassis WITH installed-state art can Install (deploy),
    # as in the original (Triage, Mantlet "can deploy to shield allied infantry", Volte, Orbus, Red-Eye, SatCom,
    # Arbalest, Ballista, Trebuchet ...).  Before, Install was only given with an installed-only skill, so a Triage
    # never had the button.  Chassis without that art still never get it (they turned invisible and stuck).
    _art = str(CODE_OF.get(_c, _c)).lower()
    if _art in INSTALL_ART and _art not in NO_GENERIC_INSTALL:
        bits.add(31)
    if _art in CHASSIS_DEPLOY:
        _db = CHASSIS_DEPLOY[_art]
        bits.add(_db)
        # power: Volte = its Refuel item (energy it hands out), Mantlet = 0 (the bunker holds infantry)
        vals[_db] = vals.get(15) or SKILL_DEFAULT.get(15) or (0, 0) if _db == 54 else (0, 0)
    if _art in VIRUS_ART:
        # (user 2026-10-27 19:30: the Virus did no damage) CONFIRMED client rules:
        #  V "Virus attack" (bit 59, executor 004e7320): the target is INFECTED with threshold = POWER x its max HP / 100
        #    (004ca520); every second it loses 16 HP until its HP is down to the threshold (004cbfe0), then its HP is SET
        #    to the threshold.  POWER is the share of HP the target KEEPS (%) - the Decay weapon's damage (750..4500)
        #    as POWER made the threshold 7.5-45 x max HP: nothing happened (or the HP was raised).
        #  D "Virus kill" (bit 58, 004e74c0): the target is marked and dies 7 s later (004ca4e0 now + 700, 004cbfe0 ->
        #    004d9a70); only with full charge (180 s between two uses).  Energy / power = the Special item
        #    (Final Breath / Death Warrant / Rigor Mortis: 'mark an enemy unit to explode'), which granted nothing.
        _vw = unit_weapon(u)
        _ve = max(0, min(65535, int(float(_vw.get("Energy Use", 0) or 0))))
        bits.add(59)
        vals[59] = (_ve, virus_keep_pct(float(_vw.get("Ground Damage", 0) or 0)))
        _sp = [ITEM_BY_ID.get(i, {}) for i in u.get("items", []) if "mark an enemy unit to explode" in
               (ITEM_BY_ID.get(i, {}).get("desc") or "").lower()]
        if _sp:
            _st = max(_sp, key=lambda it: float(it.get("stats", {}).get("Effectiveness", 0) or 0)).get("stats", {})
            bits.add(58)
            vals[58] = (max(0, min(65535, int(float(_st.get("Energy Use", 0) or 0)))),
                        max(0, min(65535, int(float(_st.get("Effectiveness", 0) or 0)))))
        else:
            bits.discard(58)
    if _art in HEAL_INSTALL_ART:
        # (17:01) Triage: the original deploy is "U Heal install mode" (ability bit 56, command 60 / 61 in the
        # client's command table 0069b9a0, enabled by 004d49a0 from bit 32+24); while installed the client heals /
        # repairs the units on its pad itself.  Energy / power = its Heal / Repair item (the item decides which).
        bits.add(56)
        hv = vals.get(25) or vals.get(20) or SKILL_DEFAULT.get(25) or (0, 0)
        vals[56] = hv
    if bits & INSTALL_ONLY:
        if str(CODE_OF.get(_c, _c)).lower() in INSTALL_ART:
            bits.add(31)
        else:
            # no installed-state art (tc.dat *SG.xpf): installing made the unit INVISIBLE and stuck, and its
            # installed-only skills can never be used anyway (Sapper with a Mine Detector, user 2026-10-22 19:26)
            bits -= INSTALL_ONLY
    # bit 27 = TRANSPORTABLE (passive, 2026-10-21: the load lump 3 aborts unless the TARGET has it; Link Gate also
    # moves bit 27 / 35 units).  Every ground unit; aviation never.
    if str(CODE_OF.get(_c, _c))[:1] != "a":
        bits.add(27)
    v = ABILITY_ATTACK
    for b in bits:
        v |= 1 << b
    # PUT s8 +8 -> unit +0x10c: energy LOST per second (004cfea0).  Original: item Energy Drain costs, SOLAR storage
    # regenerates its Energy Recharge; battery / methane only on pads / vents (not on the maps), Fallout reactors
    # "do not replenish" (their negative drain ignored).
    drain = 0.0
    rtype, rate = 0, 0
    for i in u.get("items", []):
        it = ITEM_BY_ID.get(i, {})
        st = it.get("stats", {})
        drain += max(0.0, float(st.get("Energy Drain", 0) or 0))
        if it.get("type") == 2:
            rtype, rate = storage_recharge(it)
    UNIT_REGEN[u["uid"]] = max(-128, min(127, int(round(drain))))
    RECHARGE[u["uid"]] = (rate, rtype)
    UNIT_SIGHT[u["uid"]] = unit_view_px(u)
    UNIT_SKILLS[u["uid"]] = sorted((b,) + vals.get(b, SKILL_DEFAULT.get(b, (0, 0)))
                                   for b in bits if b < 0x3e and b != 31)
    _rt = RECHARGE.get(u["uid"], (0, 0))
    if _rt[1]:
        UNIT_SKILLS[u["uid"]] = sorted(UNIT_SKILLS[u["uid"]] + [(2, min(65535, _rt[0]), _rt[1])])
    # weapons cost ENERGY PER SHOT (004e55b0 -> 004cb4b0(unit +0x164) = skill entry of ability bit 1 'attack')
    _we = _i(unit_weapon(u).get("Energy Use", 0))
    if _we:
        UNIT_SKILLS[u["uid"]] = sorted(UNIT_SKILLS[u["uid"]] + [(1, _we, 0)])
    return v

# Skill effects the SERVER must simulate: server-owned aliens only die when the server says so (0x23).
# Client lump 0x30 [u32 uid][u8 ACTION][args] (relayed unchanged).
# CONFIRMED 2026-10-20 (client senders 004dd860..004e1a90: each checks energy at +0x160[bit] and pushes its ACTION):
ACTION_BIT = {3: 28, 6: 25, 8: 22, 10: 20, 12: 15, 13: 30, 14: 17, 16: 13, 17: 12, 21: 8, 22: 7, 23: 6, 25: 4,
              28: 32, 29: 33, 33: 36, 38: 41, 41: 44, 45: 47, 46: 48, 48: 50, 59: 59, 60: 58,
              # TOGGLES (2026-10-21, executor 004d8bb0 / upkeep 004cfea0): relayed only, mapped for logs / power
              15: 14, 32: 34, 18: 11, 24: 5, 19: 10, 43: 45, 20: 9, 35: 38, 27: 3, 37: 40, 52: 49,
              3: 28, 4: 28, 0x24: 28, 40: 43}     # transport load / unload / board order, sHield [u8 on]
# action names: 3 Transport-in, 6 Heal, 8 Mine, 10 Repair, 12 Refuel, 13 Radar, 14 Radar Jam, 16 EMP Mine,
# 17 EMP Attack, 21 Grenade, 22 Mind Warp, 23 EMP Grenade, 25 Self Destruct, 28 Short Circuit, 29 IRBM, 33 Air Mine,
# 38 Defensive Matrix, 41 Dynamite, 45 Chemical Mine, 46 Earthquake, 48 Fusion Storm.
# ORIGINAL effect rules (client executors; skill damage ignores armor, 004cb3d0 subtracts it straight from HP):
#   21 Grenade (4e6190): target -POWER, then EVERY unit within 128 px of the target (target included) -POWER/2.
#   46 Earthquake (4e6cf0): every unit except the caster within the caster's SIGHT radius -POWER.
#   25 Self Destruct (4d8c10): units within 280 px -POWER, the caster dies.
#   29 IRBM (4d78c0, at impact): every unit within 210 px of the point -POWER.
#   48 Fusion Storm (4cd9a0): target -POWER % of its MAX HP.
#   17 EMP Attack / 23 EMP Grenade: drain ENERGY only (no HP); 22 Mind Warp / 28 Short Circuit: disable for POWER.
# GRENADE_SPLASH -> battlefield.py (2026-10-24, the battle rules in one place)
SELF_DESTRUCT_RADIUS = 280
IRBM_RADIUS = 210
IRBM_IMPACT_DELAY = 10.0    # CONFIRMED 2026-10-21: the owner sends lump action 26 1000 ticks after the launch (29)
CAMO_ACTIONS = {32}         # u8 on/off: camouflaged units cannot capture a POC
# POC capture eligibility, CONFIRMED in the client (00496df0 / 0048e2c0, 2026-10-21): a unit counts for a POC only
# if its flag word has none of 0x126 (toggles set by unit commands 0x1e bit1, 0x1f bit2, 0x22 bit5 = damage immunity
# (004cb3d0 ignores hits), 0x25 bit8 - hover / invisible / invulnerable skills) and its HP > 0; it CAPTURES only if it
# is a ground unit (type 1, so no aviation) without ability bit 0x200000 of +0x15c (u64 ability bit 53).
# The client decides the capture (lump 0x5a); the server mirrors the rule so its own progress matches.
POC_BLOCK_ACTIONS = {15, 19, 27} | CAMO_ACTIONS     # LUMP actions (2026-10-21; were button ids 30/31/34/37)

# ALIEN_CLIENT_CONTROL (2026-10-20): the client simulates every unit (lock-step) - movement with path finding and
# collisions, weapon timing, projectiles, splash - and the HP bars it draws come from THAT simulation.  The server
# cannot reproduce it exactly, so a server-side HP model kills aliens too early or too late.  In the client the
# CONTROLLER of a unit (owner name == own commander, unit +0x69; 004ac800) reports its death itself: the unit's
# think function 004cc220 sends lump 0x1e [uid] the moment its simulated HP reaches 0.  So the aliens are put with
# the battle creator as owner: his client reports their deaths exactly when the animation/HP shows them dead,
# and the server relays it (0x1e -> 0x23) to everybody.  Player commands for aliens (move/stop/skill) are dropped
# by the relay, so they still cannot be controlled.  False = old server-side HP model.
ALIEN_CLIENT_CONTROL = False   # (2026-10-24: its code paths were removed - the server drives every alien)
# ALIEN_DEATH_FROM_CLIENT (2026-10-21): with the patched client (tools/patch_sg_debug.py, F4) EVERY client reports
# lump 0x1e [uid] when a server alien's SIMULATED HP reaches 0 (the aliens stay owned by "Alien", so they are not in
# anybody's unit list).  The first report kills it (relayed as 0x23), later duplicates are dropped.  The server HP
# model no longer kills aliens; it only credits the kill and, as a safety net for unpatched clients, kills an alien
# whose model HP stayed <= 0 for ALIEN_DEATH_FALLBACK seconds without any report.
ALIEN_DEATH_FROM_CLIENT = True
# ALIEN_DEATH_FALLBACK -> battlefield.py (2026-10-24, the battle rules in one place)

def dead_aliens(s):
    b = getattr(s, "battle", None)
    if isinstance(b, dict):
        return b.setdefault("dead_aliens", set())
    if not hasattr(s, "dead_aliens_set"):
        s.dead_aliens_set = set()
    return s.dead_aliens_set

def alien_owner(s):
    return "Alien"

def _all_dead_check(s):
    """a server unit died / left: battlefield.judge() decides whether the battle is over."""
    battle_judge(s, "death")

# ---- BATTLE JUDGE (2026-10-24, claude/BATTLEFIELD_PLAN.md P1): every end of a battle goes through battlefield.judge()
# (the rules, one table of battle kinds) and finish_battle() (the only place that sets b["won"] for a battle-wide
# result and starts end_battle for the members).  Personal ends stay where they are: a player's division destroyed
# (squad_lost / redeploy / forced retreat) only ends HIS battle.
def battle_kind(b, meta):
    if meta and meta.get("hive"):
        return "hive"
    if b and b.get("ambush"):
        return "ambush"
    # user 2026-10-25 11:50 (province 57 = 600509): an NPC battle on an OWNED province has alien_meta["raid"] set, so it was
    # judged as a 'raid' and never ended after the POC was taken.  A battle an NPC nation opened (npc_attacker) is 'npc'.
    if b and b.get("npc_attacker") is not None:
        return "npc"
    if meta and meta.get("raid"):
        return "raid"
    pocs = (b or {}).get("pocs") if b else None
    return "province" if pocs else "field"

def _closing(o):
    w = getattr(o, "w", None)
    return bool(w is not None and w.is_closing())

def battle_members_of(s):
    b = getattr(s, "battle", None)
    return list(b["members"]) if b else [s]

def _battle_meta(s, b):
    # (2026-10-25 audit B) the battle's own context first (Ghost / stand-in): a joiner has no meta and the owner may be
    # a player who joined later
    m = getattr(battle_ctx(b), "alien_meta", None) if b else None
    if not m and s is not None:
        m = getattr(s, "alien_meta", None)
    if not m and b:
        m = getattr(b.get("owner"), "alien_meta", None)
    return m

def battle_view(s, b, event):
    meta = _battle_meta(s, b)
    T = (b.get("targets") if b and b.get("targets") is not None else getattr(s, "targets", None)) or {}
    pocs = (b or {}).get("pocs") if b else getattr(s, "pocs", None)
    kind = battle_kind(b, meta)
    if kind == "npc":
        mem = list(_live(b))                          # NPC battles: the players still on the map (none = simulated)
    else:
        mem = list(b["members"]) if b else [o for o in battle_members_of(s) if not _closing(o)]
    extra = {}
    if kind == "npc":
        A = b.get("npc_attacker")
        att = _side_alive(b, A)
        def frac(enemy):
            ids = [i for i, rt in NPC_RT.items() if rt.get("B") is b and rt.get("nid") is not None
                   and (not same_side(rt["nid"], A) if enemy else same_side(rt["nid"], A))]
            d = sum(NPC_RT[i].get("dead", 0) for i in ids)
            u = sum(max(0, NPC_RT[i].get("units", 0) - NPC_RT[i].get("left", 0)) for i in ids)   # (audit S3)
            return d / u if u else 1.0
        extra = {"att_alive": att,
                 "def_alive": sum(1 for tg in b["targets"].values() if tg.get("hp", 0) > 0 and not tg.get("hive")) - att,
                 "att_reserve": _reserve(b, A), "def_reserve": _reserve(b, A, enemy=True)}
        if event == "time":
            extra.update(att_loss=frac(False), def_loss=frac(True))
    return {
        **extra,
        "kind": kind, "event": event, "same": same_side,
        "members": [(o, side_nation(o), bool(getattr(o, "spectator", False)) or _closing(o)) for o in mem],
        "defender": (b or {}).get("defender", 0) or 0,
        "enemies": sum(1 for g in T.values() if not g.get("ally")),
        "att_units": sum(1 for g in T.values() if not g.get("ally") and g.get("hp", 1) > 0
                         and not ((b or {}).get("defender") and g.get("nation") is not None
                                  and same_side(g.get("nation"), (b or {}).get("defender")))),
        "att_pending": any(getattr(o, "redeploy_pending", False) and not getattr(o, "spectator", False)
                           and not same_side(side_nation(o), (b or {}).get("defender") or 0) for o in mem),
        "hives": sum(1 for g in T.values() if g.get("hive")),
        "budget": (meta or {}).get("budget", 0) or 0,            # random-spawn caves: aliens still to appear
        "waves": (meta or {}).get("waves_left", 0) or 0,
        "pocs": [p["owner"] for p in (pocs or {}).values()],
        "blocker": ((AMBUSH.get(b["ambush"]) or {}).get("o") or b.get("npc_side")) if b and b.get("ambush") else None,
        # (00:26) the raiding NPC side is never the defender of the province
        "npc_side": b.get("npc_side") if b and b.get("npc_raid") and not (
            b.get("defender") and same_side(b.get("npc_side"), b.get("defender"))) else None,
        "npc_attacker": (b or {}).get("npc_attacker"),
        "rule": (b or {}).get("rule") if b and not (meta or {}).get("raid") and not b.get("ambush") else None,
        "elapsed": (time.monotonic() - b["t0"]) if b and b.get("t0") is not None else 0,
        "vp": (b or {}).get("vp"),
        "_meta": meta, "_mem": mem,
    }

def battle_judge(s, event, b=None):
    """-> the result applied (or None when the battle goes on)."""
    if b is None:
        b = getattr(s, "battle", None)
    if b is not None and b.get("won"):
        return None
    if s is None:
        s = (b or {}).get("owner")
    try:
        v = battle_view(s, b, event)
        res = BF.judge(v)
    except Exception as e:
        # user 2026-10-24 06:36: an error in the end check (KeyError 'nid') made leave_map fail - the player could not
        # retreat out of the battle.  A broken check means "the battle goes on", never a stuck player.
        import traceback
        log(f"   battle_judge error ({event}) on {(b or {}).get('map')}: {e!r} {traceback.format_exc()[-300:]}")
        return None
    if res is None:
        if event == "death" and v["enemies"] == 0:
            if v["waves"] > 0 and v["kind"] != "hive":
                log("   wave cleared - the next wave is coming")
            elif v["pocs"] and v["kind"] in ("province", "npc"):
                log("   all enemies destroyed - capture the POC(s) to win")
        return None
    if res["tag"] == "hive" and (v["_meta"] or {}).get("won_hives"):
        return None
    finish_battle(s, b, res, v)
    return res

def finish_battle(s, b, res, v):
    """apply a battlefield.judge() result: side effects of its tag, b["won"], end_battle for every member."""
    tag, meta = res["tag"], v["_meta"] or {}
    if tag == "npc_raid_won":
        npc_won_battle(b)                     # NPC raiders hold every POC: the province changes hands (own code path)
        return
    if tag == "npc_battle":
        log(f"   battle on {b.get('map')} [npc] decided: {res['why']}")
        ghost_finish(b, res["att_won"], res.get("win_side"))       # province change, NPC result, end_battle for the players on the map
        return
    if b is not None:
        b["won"] = True
    log(f"   battle on {(b or {}).get('map', getattr(s, 'map', '?'))} [{v['kind']}] over: {res['why']} ({tag})")
    if tag == "hive":
        meta["won_hives"] = True
    elif tag == "raid_repelled":
        r = RAIDS.pop(meta.get("mapid"), None)
        if meta.get("npc"):
            npc_battle_result(meta.get("mapid"), False)
        if r:
            raid_notify(r["nation"], f"The {'raid' if meta.get('npc') else 'alien raid'} on "
                                     f"{province_label(meta.get('mapid'))} was repelled!", (120, 255, 120))
    elif tag == "time_up":
        npc_time_up(b)
    elif tag == "pocs_held" and s is not None:
        s.poc_won = True
    for o in v["_mem"]:
        spawn(end_battle(o, o.battle_gen, won=bool(res["won"].get(o, False))))

# ---- ANTI-CHEAT: alien deaths (2026-10-21) ----------------------------------------------------------------------
# The client simulates combat and reports deaths (0x1e).  The server model (attack_loop / skills) misses part of the
# damage (log: aliens died with up to 70 % model HP left), so a death is NOT refused on HP alone.  A death with model
# HP > 0 is credited only if the battle's units COULD have dealt the missing HP since the first hit:
#   model hp left  <=  team max DPS (all deployed units, armour ignored) * seconds since the first hit * TTK_SAFETY
# Otherwise the alien is still removed (it is dead on the client), but nobody gets XP / resources (audit log).
# TTK_SAFETY -> battlefield.py (2026-10-24, the battle rules in one place)
# KILL_RATE_WINDOW, KILL_RATE_MAX -> battlefield.py (2026-10-24, the battle rules in one place)

def team_dps(s):
    tot = 0.0
    for o in battle_members(s):
        alive = getattr(o, "alive_units", None)
        for uid, (st9, _spd) in getattr(o, "unit_cmb", {}).items():
            if alive is not None and uid not in alive:
                continue
            g = st9[3] * 100 / max(20, st9[5]) if st9[3] > 0 else 0
            a = st9[6] * 100 / max(20, st9[8]) if st9[6] > 0 else 0
            tot += max(g, a)
    return tot

def alien_death_plausible(s, tg):
    if tg.get("hp", 0) <= 0:
        return True, ""
    if "first_hit" not in tg:
        return False, "never hit by any unit (server model)"
    dt = max(0.5, time.time() - tg["first_hit"])
    can = team_dps(s) * dt * TTK_SAFETY
    if tg["hp"] > can:
        return False, f"model hp {tg['hp']} left, team can deal {int(can)} in {dt:.1f}s"
    return True, ""

def kill_rate_ok_peek(s):
    now = time.time()
    return len([t for t in getattr(s, "kill_times", []) if now - t < KILL_RATE_WINDOW]) < KILL_RATE_MAX

def kill_rate_ok(s):
    now = time.time()
    q = [t for t in getattr(s, "kill_times", []) if now - t < KILL_RATE_WINDOW]
    ok = len(q) < KILL_RATE_MAX
    if ok:
        q.append(now)
    s.kill_times = q
    return ok

NPC_CORPSE_SECONDS = 3.0       # after its death animation a dead NPC unit is removed from every client (0x19)

def remove_unit_from_clients(s, uid, delay=0.0):
    """server 0x19 [u32 uid][u32 0] (client 004a5ee0 -> 004dcbf0 plain remove; an unknown id is skipped at 004a5f49).
    user 2026-10-24 11:16: dead NPC units stayed on the client as HP-0 'zombies' (only ALIEN deaths are finished by
    the client patch F4/F7): the client re-reported them every 3 s, the snapshot held 6 units the server no longer
    had, and the players' own units kept going for them - 'my units move and attack on their own'."""
    pk = bytes([0x19]) + struct.pack(">II", uid, 0)
    members = [o for o in battle_members(s) if not o.w.is_closing()]
    if delay <= 0:
        for o in members:
            o.send(pk)
        return
    async def later():
        await asyncio.sleep(delay)
        for o in members:
            if not o.w.is_closing():
                o.send(pk)
    spawn(later())

NPC_DEATH_HP_OK = 0.5        # (audit G) 0x1e for an NPC unit is believed when the model has it at <= this share of HP ...
NPC_DEATH_HIT_S = 60         # ... or it was hit within this many seconds; anything else waits for the requested snapshot

def npc_death_report_ok(s, tg):
    """(2026-10-25 audit G) a forged 0x1e removed any NPC unit for everybody.  Clients do not report NPC deaths in
    normal play (no client owns them - the snapshot finds them, apply_snapshot), so a report is accepted only when the
    server saw the unit being worn down; otherwise it is logged and the next snapshot (from the client the server asked)
    decides."""
    if tg.get("hp", 0) <= NPC_DEATH_HP_OK * max(1, tg.get("max", 1)):
        return True
    if time.time() - tg.get("first_hit", 0) <= NPC_DEATH_HIT_S or tg.get("hp_c", 1) <= 0:
        return True
    return False

def alien_died(s, tid, confirmed=False):
    """the controlling client reported 0x1e for an alien (its simulated HP reached 0); the relay sends 0x23."""
    _tg0 = s.targets.get(tid)
    if _tg0 is not None and _tg0.get("npc") is not None and not confirmed and not npc_death_report_ok(s, _tg0):
        log(f"   ANTI-CHEAT: death of NPC unit {tid} reported by {getattr(s, 'acc', '?')} not believed "
            f"(model hp {_tg0.get('hp')}/{_tg0.get('max')}, never hit lately) - the snapshot decides")
        audit("npc_death_unconfirmed", getattr(s, "acc", None), tid=tid, hp=_tg0.get("hp"), map=getattr(s, "map", None))
        return False
    tg = s.targets.pop(tid, None)
    if tg is None:
        return
    if tg.get("npc") is not None:
        dead_aliens(s).add(tid)                       # never reused for a new unit
        remove_unit_from_clients(s, tid, NPC_CORPSE_SECONDS)
    ok, why = alien_death_plausible(s, tg)
    if not ok and not kill_rate_ok_peek(s):
        pass
    elif not ok:
        # 2026-10-22 12:57 (user: a player unit that kills always gets XP): the server model misses many hits (units
        # firing on their own, splash, mines, skills), so "never hit / too fast" no longer cancels the reward - it is
        # only logged; the kill goes to the last hitter, else the nearest player unit.  The kill-RATE limit stays.
        audit("alien_death_unseen", getattr(s, "acc", None), tid=tid, why=why, level=tg.get("level"),
              map=getattr(s, "map", None))
        if not (tg.get("last_hitter") or getattr(s, "last_hitter", {}).get(tid)):
            near = None
            for o in battle_members(s):
                for u in getattr(o, "alive_units", set()):
                    d = AL.dist(o.unit_pos.get(u, (-99999, -99999)), tg.get("pos") or (tg.get("x", 0), tg.get("y", 0)))
                    if near is None or d < near[0]:
                        near = (d, u)
            if near:
                tg["last_hitter"] = near[1]
        ok = True
    if not ok:
        dead_aliens(s).add(tid)
        alien_removed(s, tid, tg)
        log(f"   ANTI-CHEAT: alien {tid} death reported by {s.acc} refused for rewards: {why}")
        audit("alien_death_implausible", getattr(s, "acc", None), tid=tid, why=why, level=tg.get("level"),
              map=getattr(s, "map", None))
        _all_dead_check(s)
        return
    dead_aliens(s).add(tid)
    alien_removed(s, tid, tg)
    s.last_kill_level = tg.get("level", 1)
    killer = tg.get("last_hitter") or getattr(s, "last_hitter", {}).get(tid)
    log(f"   alien {tid} died in the client simulation (server model hp {tg['hp']}), credited to {killer}")
    if killer is not None and npc_score_kill(s, killer, s.last_kill_level):
        killer = None                                        # an NPC unit's kill: its commander's TAB score only
    # (user 2026-10-24 21:57: kills gave no XP) the player's credit below sat INSIDE the NPC branch -> never ran
    if killer is not None:
        ks = next((o for o in battle_members(s) if killer in getattr(o, "put_args", {}) or killer in getattr(o, "alive_units", set())), s)
        ks.last_kill_level = s.last_kill_level
        ks.last_kill_share = kill_share(tg)
        on_kill(ks, killer, tid)
    _all_dead_check(s)

async def _alien_death_fallback(s, tid, tg):
    await asyncio.sleep(ALIEN_DEATH_FALLBACK)
    if s.targets.get(tid) is tg and tg["hp"] <= 0:
        log(f"   alien {tid}: no client death report {ALIEN_DEATH_FALLBACK}s after the server model reached 0 -> server kill")
        dead_aliens(s).add(tid)
        s.targets.pop(tid, None)
        alien_removed(s, tid, tg)
        s.last_kill_level = tg.get("level", 1)
        send_lumps(s, [bytes([0x23]) + struct.pack(">I", tid)])
        if tg.get("npc") is not None:                 # (2026-10-25 audit C3) NPC corpses are not finished by the client
            remove_unit_from_clients(s, tid, NPC_CORPSE_SECONDS)
        killer = tg.get("last_hitter")
        if killer is not None and npc_score_kill(s, killer, s.last_kill_level):
            killer = None
        if killer is not None:
            ks = next((o for o in battle_members(s) if killer in getattr(o, "put_args", {})), s)
            ks.last_kill_level = s.last_kill_level
            ks.last_kill_share = kill_share(tg)
            on_kill(ks, killer, tid)
        _all_dead_check(s)

def damage_target(s, uid, tid, amount, why="hit", delay=10):
    tg = s.targets.get(tid)
    if not tg:
        return
    s.last_hitter = getattr(s, "last_hitter", {})
    s.last_hitter[tid] = uid
    tg["last_hitter"] = uid                  # shared by every participant (the battle's target dict)
    tg.setdefault("first_hit", time.time())  # anti-cheat: time-to-kill check in alien_died
    _before = tg["hp"]
    tg["hp"] -= max(1, amount)
    note_damage_xp(s, uid, tg, max(0, min(max(1, amount), _before)))
    if LOG_COMBAT:
        log(f"   {why}: unit {uid} -> target {tid} for {max(1, amount)}, hp left {tg['hp']}")
    if tg.get("state") in ("idle", "return") and "home" in tg and tid >= 60001 and not tg.get("hive") \
            and not hidden(uid, getattr(s, "unit_pos", {}).get(uid, (0, 0)), detectors(s.targets)):
        # (00_LOCKED_SETTINGS stealth: a cloaked attacker that no switched-on Detector sees gets no answer)
        tg["state"], tg["target"] = "combat", uid       # hit from outside the aggro radius: fight back (AI loop)
        _fb, _now = [], time.time()                     # out of range: walk to it first (unit_orders)
        order_attack(tid, tg, uid, getattr(s, "unit_pos", {}).get(uid), _now, _fb)
        dispatch_orders(s, getattr(s, "battle", None), battle_members(s), _fb, _now, "fight back")
    if ALIEN_DEATH_FROM_CLIENT and tid >= 60001:
        if tg["hp"] <= 0 and not tg.get("fallback"):
            tg["fallback"] = True
            spawn(_alien_death_fallback(s, tid, tg))
        return                                    # the clients report the death (0x1e) at the simulated tick
    if tg["hp"] <= 0:
        s.last_kill_level = tg.get("level", 1)
        del s.targets[tid]
        send_lumps(s, [bytes([0x23]) + struct.pack(">I", tid)], delay)
        log(f"   target {tid} destroyed -> lump 0x23 Death")
        s.last_kill_share = kill_share(tg)
        on_kill(s, uid, tid)
        _all_dead_check(s)

# DAMAGE XP (user 2026-10-23 23:33: "every unit hit the enemy, why does only one get XP"): a unit earns XP for the
# damage it deals, not only for the killing blow.  One enemy is worth KILL_XP x its level, shared by the damage each
# unit did (damage / enemy max HP); the killer also gets the part nobody was seen dealing (hits the server model
# missed), so a kill is worth the same total as before.  Damage XP is paid when the battle ends - victory, defeat
# or retreat alike - and also counts for the victory kill bonus and the result-window bonuses (xp_gain).
def note_damage_xp(s, uid, tg, dealt):
    if dealt <= 0 or not owns_unit(s, uid):
        return
    mx = max(1, tg.get("max", tg["hp"] + dealt))
    tg["dmg_seen"] = tg.get("dmg_seen", 0) + dealt
    st = getattr(s, "battle_stats", None)
    if st is None:
        return
    dx = st.setdefault("dmg_xp", {})
    dx[uid] = dx.get(uid, 0.0) + PG.KILL_XP * max(1, tg.get("level", 1)) * dealt / mx

def kill_share(tg):
    """the part of a kill's XP the killer gets on top of his damage XP: what nobody was seen dealing."""
    mx = max(1, tg.get("max", 1))
    return max(0.0, 1.0 - tg.get("dmg_seen", 0) / mx)

def pay_damage_xp(s):
    """end of the battle: every unit gets the XP of the damage it dealt (x account / item multipliers)."""
    st = getattr(s, "battle_stats", None)
    if not st or not st.get("dmg_xp"):
        return
    accs, a = get_account(getattr(s, "acc", None))
    if a is None:
        return
    cmd = PG.ensure_commander(a.setdefault("commander", {}))
    cap = xp_level_cap(s)
    paid, events = {}, []
    for u in a.get("units", []):
        x = st["dmg_xp"].get(u["uid"], 0.0)
        if x <= 0 or u.get("level", 1) >= cap:
            continue
        g = int(round(x * xp_multiplier(a, s) * unit_xp_bonus(u)))
        if g <= 0:
            continue
        events += PG.add_unit_xp(cmd, u, unit_branch(u["chassis"]), g) or []
        st.setdefault("xp_gain", {})[u["uid"]] = st.setdefault("xp_gain", {}).get(u["uid"], 0) + g
        paid[u["uid"]] = g
    st["dmg_xp"] = {}
    accs[s.acc] = a
    save_accounts(accs)
    star_notify(s)
    log(f"   damage XP: {paid}" + "".join(f"\n      * {e}" for e in events))

def skill_power(uid, act, default=0):
    b = ACTION_BIT.get(act)
    pw = next((p for bb, _e, p in UNIT_SKILLS.get(uid, []) if bb == b), 0) if b is not None else 0
    return pw or default

# ---- skill timing (CONFIRMED 2026-10-20) ---------------------------------------------------------------------
# Battle is lock-step: the client sends 0x30 at every click and executes NOTHING itself; the order runs on every
# client when the relayed lump's game time comes (server echo: game_time + RELAY_DELAY).  At that tick the unit's
# order becomes 'use skill X' and the executor tries it every frame:
#   Grenade 4e6190 / EMP Grenade 4e6400 / Mind Warp 4e6800 / Short Circuit 4e69b0 / EMP Attack 4e6b60 share ONE
#   per-unit timer (unit +0xb876 table, set by 004cd3f0(now)): fire only when last_use + 200 < now, and only with
#   energy >= cost.  A newer order of the unit (another click, a move, an attack) replaces a pending one.
# The server mirrors this in GAME TICKS (1/100 s, the same clock as game_time) and stamps the resulting 0x23 deaths
# with the exact tick of the throw, so a target dies on the same frame the client shows the grenade hit.
# LOCK-STEP ORDER DELAY (ticks of 1/100 s): every relayed order / server lump executes at game_time + RELAY_DELAY.
# The client clock only advances to the time of the last 0x80 frame it received, and orders + frames share one ordered
# TCP stream, so in theory a few ticks are enough (ARCH_REVIEW A2: 10 -> 2..3 saves 70-80 ms per action).  Not yet
# verified with real clients -> GM /lag delay N (1..20) changes it at run time for an A/B test; default unchanged.
# (user 2026-10-24 20:02: controlling units feels sluggish; the link has rtt ~220 ms).  Order -> action = rtt +
# RELAY_DELAY.  The client stores the time of EVERY 0x80 it receives as its clock limit (0x80 handler 004a1e14: plain
# store, not max) and frames / lumps share one ordered TCP stream: a lump stamped game_time + D is always received before
# any frame stamped later, so any D > FRAME_LEAD keeps every client in step.  10 -> 4 ticks: 60 ms less per order.
# FRAME_LEAD: frames are stamped this many ticks AHEAD, so the client keeps simulating smoothly through 20 ms of
# frame jitter instead of stopping at the last frame time (must stay below RELAY_DELAY).  GM: /lag delay N, /lag lead N.
# (user 2026-10-24 22:20: units MOVE choppily) the client clock runs in real time but stops at the last frame's time.
# It trails the server clock by ~rtt/2, so right after a frame arrives it is only FRAME_LEAD ticks short of the limit:
# with frames every 50 ms and a lead of 2 ticks it ran 20 ms and then STOOD 30 ms - every 50 ms (the stutter).
# The lead must exceed the frame interval + jitter: frames every 33 ms (core_net.FRAME_MS), lead 6 ticks = 60 ms
# (27 ms of jitter margin), order delay 7 (> lead).  Costs +30 ms per order against 4 / 2 - small next to the rtt.
# >>> 2026-10-28: THE CLOCK RULES ARE IN claude/CLIENT_CLOCK.md (project doc).  Parts of the notes above are OUTDATED:
# the 0x80 frame time does NOT limit the client clock (only stored at battle+0x29be4, never read); the clock follows
# the time stamps L of commands and 0x50 puts (controller 0x548f00).  Rules: stamp L = game_time(receiver) +
# RELAY_DELAY at SEND time (delay the sending, never the stamp: d > 100 makes the client jump its clock forward),
# never a stamp in the past (rollback), use send_lumps / delayed_put / dispatch_orders.
RELAY_DELAY = 7
FRAME_LEAD = 6
SKILL_SHARED_CD = 200                # ticks
SKILL_SHARED_CD_ACTIONS = {21, 22, 23, 28, 17}

def _skill_cost(uid, act):
    b = ACTION_BIT.get(act)
    return next((e for bb, e, _p in UNIT_SKILLS.get(uid, []) if bb == b), 0)

def _unit_energy(s, uid, tick):
    """server estimate of a unit's energy at game tick `tick` (PUT energy, + regeneration per second, capped).
    Toggle upkeep (Cloak ...) is not simulated."""
    s.unit_energy = getattr(s, "unit_energy", {})
    pa = (getattr(s, "put_args", {}) or {}).get(uid) or {}
    full = pa.get("en") or 1000
    en, t = s.unit_energy.get(uid, (full, tick))
    en = min(full, en + UNIT_REGEN.get(uid, 0) * max(0, tick - t) / 100)
    s.unit_energy[uid] = (en, tick)
    return en

def cancel_pending_skill(s, uid):
    getattr(s, "skill_pending", {}).pop(uid, None)

async def _run_skill(s, uid, order):
    """execute a relayed skill order at the tick the clients execute it (see above)."""
    act, exec_t = order["act"], order["exec_t"]
    s.skill_last = getattr(s, "skill_last", {})
    fire_t = exec_t
    if act in SKILL_SHARED_CD_ACTIONS:
        fire_t = max(exec_t, s.skill_last.get(uid, -10**9) + SKILL_SHARED_CD + 1)
    # commit RELAY_DELAY ticks before the fire tick: a newer order received after that executes later anyway
    wait = (fire_t - RELAY_DELAY - game_time(s)) / 100
    if wait > 0:
        await asyncio.sleep(wait)
    if getattr(s, "skill_pending", {}).get(uid) is not order:
        return                                          # replaced by a newer order before it could fire
    del s.skill_pending[uid]
    if getattr(s, "targets", None) is None:
        return
    cost = _skill_cost(uid, act)
    en = _unit_energy(s, uid, fire_t)
    if en < cost:
        log(f"   skill {act} by {uid}: not enough energy ({int(en)} < {cost}) - the client does not fire either")
        return
    s.unit_energy[uid] = (en - cost, fire_t)
    if act in SKILL_SHARED_CD_ACTIONS:
        s.skill_last[uid] = fire_t
    delay = max(1, fire_t - game_time(s))               # 0x23 deaths stamped with the fire tick
    order["effect"](delay)
    log(f"   skill {act} by {uid} fired at tick {fire_t} (ordered for {exec_t}), energy {int(en)} -> {int(en - cost)}")

# ---- TRANSPORT + SHIELD state (2026-10-21) ----------------------------------------------------------------------
# Transport (bit 28): lump 0x30 [carrier][0x24][target] = fly to it, [carrier][03][target] = LOAD (target needs
# ability bit 27, one passenger), [carrier][04] = UNLOAD next to the carrier.  The passenger is hidden on the
# clients; if the carrier dies the passenger dies too, if the carrier leaves (0x19) it is dropped.
# Shield (bit 43): lump 0x30 [uid][0x28][u8 on]; while on, a ground hit whose attacker and target are not inside the
# same shield (octagonal distance <= radius = POWER of bit 43) does 0 damage (004d0420 / 004d01a0).
CARRIED = {}               # passenger uid -> carrier uid
SHIELDS = {}               # shielding unit uid -> (x, y, radius)
# STEALTH (user 2026-10-23 12:08): a unit with Cloak (action 15) or Camouflage (32) switched on cannot be targeted by the
# server-owned enemies (aliens, NPC units): they neither pick it as a target nor keep shooting at it.  Area / skill damage
# (grenades, IRBM, earthquake ... applied by position) still reaches it; nothing server-side has a Detect skill.
# STEALTH_ACTIONS -> battlefield.py (2026-10-24, the battle rules in one place)
CLOAKED = {}               # uid -> set of stealth actions that are on
def stealthed(uid):
    return bool(CLOAKED.get(uid))

NPC_CLOAK_BIT, NPC_DETECT_BIT = 14, 45      # ability bits: Cloak (lump action 15 [u8 on]), Detector
# NPC_DETECT_R -> battlefield.py (2026-10-24, the battle rules in one place)
# NPC_CLOAK_NEAR -> battlefield.py (2026-10-24, the battle rules in one place)

MINE_ACTS = (8, 16, 33, 45)   # lump 0x30 actions that lay a mine: Mine, EMP Mine, Air Mine, Chemical Mine
MINE_MEMORY = 900             # s a mine is remembered (the server does not see it go off)

def note_mine(s, pos, side):
    holder = getattr(s, "battle", None) or s.__dict__
    mines = holder.setdefault("mines", [])
    mines.append((float(pos[0]), float(pos[1]), side, time.time()))
    del mines[:-80]

def detectors(targets):
    """(pos, radius) of every living server-owned unit (NPC / alien) that carries a Detector."""
    return [(tg["pos"], tg.get("detect_r") or NPC_DETECT_R) for tg in (targets or {}).values()
            if tg.get("detect") and tg.get("detect_on") and tg.get("hp", 0) > 0 and tg.get("pos")]

def release_hidden(s, hid, msgs, why):
    """(user 2026-10-23 23:06) a server-owned unit whose target became invisible to it (cloaked, no Detector of its side
    switched on near it) drops that target AT ONCE: the client keeps executing an attack order until a new order
    arrives, so it gets a halt (move to where it stands).  Without a Detector an NPC cannot shoot back at a cloaked
    attacker either - it never gets an order against it (the item text: cloaked units must be targeted manually)."""
    for tid, tg in list((getattr(s, "targets", None) or {}).items()):
        if tg.get("state") == "combat" and tg.get("target") in hid and tg.get("hp", 0) > 0 and tg.get("pos"):
            log(f"   {why}: {tg.get('name') or tid} {tid} loses its target {tg['target']} (cloaked, not detected) - halt")
            tg["state"], tg["target"], tg["dest"] = "idle", None, None
            stop_chase(tg)
            msgs.append(_alien_order_move(tid, *tg["pos"]))

def hidden(uid, pos, dets):
    """a cloaked unit stays invisible to the server's AIs unless a Detector of theirs is close enough (user 22:49)."""
    if not stealthed(uid):
        return False
    return not any((pos[0] - d[0][0]) ** 2 + (pos[1] - d[0][1]) ** 2 <= d[1] * d[1] for d in dets)

def _oct_dist(dx, dy):
    a, b = abs(dx), abs(dy)
    hi, lo = max(a, b), min(a, b)
    return hi - lo + lo * 0x5a8 // 1024

def shield_at(x, y):
    for sid, (sx, sy, r) in list(SHIELDS.items()):
        if _oct_dist(x - sx, y - sy) <= r:
            return sid
    return None

def release_passengers(s, carrier, kill=False):
    for pid in [p for p, c in CARRIED.items() if c == carrier]:
        CARRIED.pop(pid, None)
        o = s if pid in getattr(s, "alive_units", set()) else (owner_peer(s, pid) or s)
        if pid in getattr(o, "alive_units", set()):
            if kill:
                on_unit_lost(o, pid)
            else:
                cx, cy = s.unit_pos.get(carrier, o.unit_pos.get(pid, (0, 0)))
                o.unit_pos[pid] = (cx, cy)
        log(f"   transport: passenger {pid} {'killed with' if kill else 'unloaded from'} carrier {carrier}")

def on_skill(s, m):
    """server-side effect of a relayed 0x30 skill action on server-owned aliens (original rules, see above)."""
    import math
    uid, act = struct.unpack_from(">IB", m, 1)
    pw = skill_power(uid, act)
    if act in STEALTH_ACTIONS and len(m) >= 7:
        _on = CLOAKED.setdefault(uid, set())
        (_on.add if m[6] else _on.discard)(act)
        if not _on:
            CLOAKED.pop(uid, None)
    if act in MINE_ACTS:                       # (23:31) mines laid: the NPCs may spot them (npc_spot_reports)
        try:
            _p = (getattr(s, "unit_pos", {}) or {}).get(uid)
            if _p:
                note_mine(s, _p, side_nation(s))
        except Exception:
            pass
    near = lambda x, y, r: [t for t, tg in list(s.targets.items()) if math.hypot(tg["x"] - x, tg["y"] - y) <= r]
    effect = None
    if act == 21 and len(m) >= 10 and pw:                            # Grenade
        tid = struct.unpack_from(">I", m, 6)[0]
        def effect(delay, tid=tid):
            tg = s.targets.get(tid)
            if not tg:
                return
            # CONFIRMED (4e6190): the splash loop does NOT skip the target, so the target takes POWER + POWER/2
            # (Concussion Grenade 90 -> 135) and every other unit within 128 px POWER/2.
            splash = near(tg["x"], tg["y"], GRENADE_SPLASH)
            damage_target(s, uid, tid, pw, "Grenade", delay)
            for t in splash:
                damage_target(s, uid, t, pw // 2, "Grenade splash", delay)
    elif act == 48 and len(m) >= 10 and pw:                          # Fusion Storm: % of max HP
        tid = struct.unpack_from(">I", m, 6)[0]
        def effect(delay, tid=tid):
            tg = s.targets.get(tid)
            if tg:
                damage_target(s, uid, tid, tg.get("max", tg["hp"]) * pw // 100, "Fusion Storm", delay)
    elif act == 46:                                                  # Earthquake: caster's sight radius
        def effect(delay):
            ux, uy = s.unit_pos.get(uid, (-9999, -9999))
            r = (getattr(s, "put_args", {}).get(uid) or {}).get("sight") or 160
            for t in near(ux, uy, r):
                damage_target(s, uid, t, pw, "Earthquake", delay)
    elif act == 25:                                                  # Self Destruct
        def effect(delay):
            ux, uy = s.unit_pos.get(uid, (-9999, -9999))
            dmg = pw or SELF_DESTRUCT_DEFAULT        # must equal the POWER the clients use
            for t in near(ux, uy, SELF_DESTRUCT_RADIUS):
                damage_target(s, uid, t, dmg, "Self Destruct", delay)
    elif act == 29 and len(m) >= 10 and pw:                          # IRBM
        px, py = struct.unpack_from(">HH", m, 6)
        def effect(delay):
            async def impact():
                await asyncio.sleep(IRBM_IMPACT_DELAY)
                for t in near(px, py, IRBM_RADIUS):
                    damage_target(s, uid, t, pw, "IRBM")
            spawn(impact())
    elif act == 59 and len(m) >= 10 and pw:                          # Virus attack: infection (see VIRUS_ART)
        tid = struct.unpack_from(">I", m, 6)[0]
        def effect(delay, tid=tid):
            tg = s.targets.get(tid)
            if not tg or tg.get("infected"):
                return
            keep = int(tg.get("max", tg["hp"]) * pw / 100)
            tg["infected"] = True
            async def drain():
                try:
                    while True:
                        await asyncio.sleep(1.0)
                        t2 = s.targets.get(tid)
                        if t2 is None or t2["hp"] <= keep:
                            break
                        damage_target(s, uid, tid, min(VIRUS_DRAIN_PER_SEC, t2["hp"] - keep), "Virus infection")
                finally:
                    if s.targets.get(tid) is not None:
                        s.targets[tid].pop("infected", None)
            spawn(drain())
    elif act == 60 and len(m) >= 10:                                 # Virus kill: the marked unit dies 7 s later
        tid = struct.unpack_from(">I", m, 6)[0]
        def effect(delay, tid=tid):
            async def kill():
                await asyncio.sleep(VIRUS_KILL_TICKS / 100)
                tg = s.targets.get(tid)
                if tg is not None and tg["hp"] > 0:
                    damage_target(s, uid, tid, tg["hp"], "Virus kill")
            spawn(kill())
    elif act in SKILL_SHARED_CD_ACTIONS:                             # EMP / Mind Warp / Short Circuit: no HP,
        def effect(delay):                                           # but they use the shared timer and energy
            pass
    elif act == 3 and len(m) >= 10:                                  # transport IN (load) [u32 passenger]
        pid = struct.unpack_from(">I", m, 6)[0]
        if not any(c == uid for c in CARRIED.values()):             # capacity: one unit (ksTransportIn)
            CARRIED[pid] = uid
    elif act == 4:                                                   # transport OUT (unload at the carrier)
        release_passengers(s, uid)
    elif act == 40 and len(m) >= 7:                                  # sHield [u8 on]: fixed where it is raised
        if m[6]:
            x, y = s.unit_pos.get(uid, (-9999, -9999))
            SHIELDS[uid] = (x, y, skill_power(uid, 40) or 160)
        else:
            SHIELDS.pop(uid, None)
    elif act in POC_BLOCK_ACTIONS and len(m) >= 7:
        s.camo = getattr(s, "camo", set())             # units that may not capture a POC (toggle skills on)
        s.poc_block = getattr(s, "poc_block", {})
        on = s.poc_block.setdefault(uid, set())
        (on.add if m[6] else on.discard)(act)
        (s.camo.add if on else s.camo.discard)(uid)
    if effect is not None:
        s.skill_pending = getattr(s, "skill_pending", {})
        order = {"act": act, "exec_t": getattr(s, "lump_exec_t", game_time(s) + RELAY_DELAY), "effect": effect}
        s.skill_pending[uid] = order                    # replaces an older pending order of this unit
        spawn(_run_skill(s, uid, order))
    log(f"   skill action {act} (bit {ACTION_BIT.get(act)}, power {pw}) by unit {uid} ({m[6:].hex()})")

TRAINING_TARGETS = 3       # dummy enemy units put on battle maps so attacks can be tested

# PUT_UNIT +0x21 -> unit +0x150 = the unit's behaviour mode (client 004ad04b; values 1..6 are handled in the unit
# think 004cc491 / 004cf5b4 / 004cf775; the client itself resets it to 2 at 004d2ebc).  The server always sent 0.
# user 2026-10-24 12:18: players' units ran off on their own when attacked -> players' units get the client's own
# default 2 (test).  Server-owned units (NPC / aliens / targets) keep 0: no client runs their think.
UNIT_MODE_PLAYER = 2
UNIT_MODE_SERVER = 0

def build_put_unit(uid, name, owner, x, y, kind=0, cls=1, nation=1, stat=100, ptype=0x18, hp=None, energy=None, stats9=None, slot=0, sight=None, speed=None, abilities=0, mode=None, hp_max=None):
    """server type 0x18 PUT_UNIT (client parser FUN_004ac800; 0x50 = same with a u32 prefix, 'delayed put').
    Layout from the decompile; the two s8 strings come right after the 4 header bytes."""
    d = bytearray([ptype, kind, cls, slot + 1, 0])        # kind, art number, slot+1 (division slot: own units need
                                                          # distinct slots, else the selection panel shows only one), [+0x70]
    for t in (name, owner):
        tb = wire_name(t).encode('latin-1'); d += bytes([len(tb)]) + tb      # unit name, owner name (own unit = owner == commander name)
    # +4 max HP (unit +0x110, spec panel "HP cur/max"), +6 max energy (+0x108, also the current energy;
    #    a unit with 0 energy accepts orders but stops at once - FUN_004cb4b0 -> FUN_004dc010),
    # +8 s8 (+0x10c) = energy UPKEEP per second (client FUN_004cfea0, every 100 ticks for kind != 0/3:
    #    energy -= upkeep; negative = regeneration).  0 = moving/standing costs nothing.
    hp = stat if hp is None else max(1, min(65535, int(hp)))
    # (user 2026-10-27 22:54 "a wounded unit came into the battle with its HP restored, back home it was wounded
    # again"): +4 is the MAX HP and the u16 near the end the CURRENT HP.  Both got the current value, so a wounded
    # unit showed a full bar (current = max).  hp_max = the unit's full HP; hp = what it has now.
    hpm = hp if hp_max is None else max(hp, min(65535, int(hp_max)))
    energy = stat if energy is None else max(1, min(65535, int(energy)))
    regen = UNIT_REGEN.get(uid, 0)
    d += struct.pack(">HHb", hpm, energy, -regen)
    d += struct.pack(">HH", stat if speed is None else speed, stat if sight is None else sight) + bytes([0])      # +9 (+0x14), +0xb (+0x114 = sight), +0xd u8 (+0x118) - back to 0 (bisect: 10 here + 10 at +8 = unit moves but HP drains)
    # +0xe .. +0x1e: 9 x u16 battle stats, see unit_stats9 (speed, move type, armor type, ground/air dmg-range-cooldown)
    d += struct.pack(">9H", *(stats9 if stats9 else [stat] * 9))
    # +0x22 u64 ABILITY bits (unit +0x158 low / +0x15c high), FUN_004d49a0 builds the command panel from them:
    #   bit 1 (0x2) = ATTACK command (only with damage > 0); without it right-click on an enemy just walks there.
    #   Other bits add skill buttons (deploy, mine, heal, cloak ...); bits 0x15/0x25/0x35/0x36/0x38 forbid attacking.
    d += bytes([0, UNIT_MODE_PLAYER if mode is None else mode]) + struct.pack(">Q", abilities)   # +0x20, +0x21 mode, +0x22 abilities
    skills = UNIT_SKILLS.get(uid, []) if abilities else []   # +0x2a: u8 n + n x {u8 bit, u16 energy, u16 power}
    d += bytes([len(skills)]) + b"".join(struct.pack(">BHH", b, e, pw) for b, e, pw in skills)
    d += struct.pack(">III", uid, nation, nation)         # unit id, nation, nation
    d += struct.pack(">HHH", hp, x, y) + struct.pack(">I", 0)   # current HP (must be non-zero or the client kills the unit), x, y, then u32 at +0x12
    return bytes(d)

def put_server_unit(*a, **k):
    """PUT_UNIT for a server-owned unit (NPC / alien / training target): behaviour mode 0 as before."""
    k.setdefault("mode", UNIT_MODE_SERVER)
    return build_put_unit(*a, **k)

def game_time(s):
    """Game clock in 1/100 s, aligned with the 0x0E/4 sync (1000 at field entry)."""
    import time
    return 1000 + int((time.monotonic() - getattr(s, "t0", time.monotonic())) * 100)

async def battle_frames(s, gen):
    """Lock-step frames for battle mode.  In battle the client only advances its game clock up to the time of the
    last 0x80 lump it received from the server (0x80 handler stores it at +0x29be4), so without a steady stream
    of (even empty) frames nothing ever executes: units can be selected but never move.  Empty frame:
    [80][00 flag][00][u32 time][u16 0]."""
    n = 0
    log(f"   battle frames started (gen {gen}, every {FRAME_MS} ms)")
    loop = asyncio.get_event_loop()
    nxt = loop.time()
    try:
        while getattr(s, "battle_gen", None) == gen and not s.w.is_closing():
            try:
                backlog = s.w.transport.get_write_buffer_size() + s.pending_out()
            except Exception:
                backlog = 0
            fi = frame_interval(s, loop.time()) / 1000.0
            if s.__dict__.get("no_frames"):
                pass                                     # GM /lag frames off: A/B test, no empty frames
            elif time.monotonic() - getattr(s, "last80", -99.0) < fi * 0.8:
                TRAFFIC["frames_skipped"] += 1           # a lump packet just carried the clock forward
            elif backlog <= FRAME_BACKLOG:               # never queue stale frames behind a stalled link
                s.send(bytes([0x80, 0, 0]) + struct.pack(">IH", game_time(s) + min(FRAME_LEAD, RELAY_DELAY - 1), 0), quiet=True)
                n += 1
                if n % 500 == 0:
                    log(f"   battle frames: {n} sent, game time {game_time(s)}")
            now = loop.time()
            nxt += frame_interval(s, now) / 1000.0       # absolute schedule: no drift, no 100-115 ms jitter
            if nxt < now - 0.5:                          # long stall of the loop: do not fire a burst afterwards
                nxt = now
            await asyncio.sleep(max(0.0, nxt - now))
    except Exception as e:
        log(f"   battle frame loop stopped: {e!r}")

# ---- server-side combat for server-owned units (training targets) -------------------------------------------
# Battle is lock-step and every client simulates damage itself, but a unit only DIES when its owner reports it:
# the server lump 0x23 [u32 uid] (client FUN_004a60c0 -> FUN_004dd7b0 sets the "Death" command at the lump time).
# The training targets have no owning client, so the server simulates the hits on them from the attack orders
# (0x29 attacker -> target) and sends 0x23 when their HP reaches 0.  Distances are map pixels (20 px = 1 m:
# range x20), speed x10 m/s -> speed*2 px/s.
SERVER_ORDER_TYPES = (0x1A, 0x1B, 0x2B, 0x30)        # move / stop / attack / skill: the acting unit is the u32 at +1

def server_orders_only(s, members, msgs, who="AI"):
    """(user 2026-10-24 10:53: 'the NPC AI controls the player's units') hard guard for every order the server's AIs
    send: the acting unit must be a server unit of this battle (NPC / alien target), never a unit a player owns.
    Anything else is dropped and logged, so the server can never steer a player's unit."""
    targets = getattr(s, "targets", None) or {}
    owned = set()
    for o in members:
        owned |= set(getattr(o, "alive_units", ()) or ())
        hu = getattr(o, "hero_uid", None)
        if hu is not None:
            owned.add(hu)
    out = []
    for m in msgs:
        if len(m) >= 5 and m[0] in SERVER_ORDER_TYPES:
            uid = struct.unpack_from(">I", m, 1)[0]
            if uid in owned:
                log(f"   !! blocked server order for a player unit ({who}): {m.hex()}")
                continue
            if uid not in targets:
                continue                                  # the unit died / left meanwhile: nothing to steer
        out.append(m)
    return out

# ---- ORDER GATE (user 2026-10-24 22:04: big battles - lighten the clients) ----------------------------------------------
# Every server order (move / stop / attack / skill of an NPC or alien unit) is simulated by EVERY client of the battle,
# and each move / attack order makes the client compute a path.  With many squads this is where the clients spend
# their time, so the server sends fewer and better orders:
#   * coalescing: per unit only its LATEST move / attack intent is kept (an order superseded in the same second is
#     never sent);
#   * repeats: the same order bytes for a unit inside ORDER_REPEAT_S are dropped;
#   * budget: at most ORDER_BUDGET orders per battle and second (skills first, then attacks, then moves; the rest
#     waits for the next second, oldest first - only its newest intent survives meanwhile).
ORDER_GATE = True
ORDER_BUDGET = 40            # server orders per battle and second (all AIs together)
ORDER_REPEAT_S = 4.0         # identical order for the same unit within this many seconds: dropped
ORDER_STATS_S = 30           # log line with the order counts every this many seconds (big battles only)

def order_gate(s, b, msgs, now, who="AI"):
    if not ORDER_GATE:
        return msgs
    holder = b if b is not None else s.__dict__
    pend = holder.setdefault("_ord_pend", {})        # key -> (first_t, msg)
    last = holder.setdefault("_ord_last", {})        # uid -> (msg, t)
    st = holder.setdefault("_ord_stats", {"t0": now, "in": 0, "out": 0, "dup": 0, "late": 0})
    passthru = []
    for m in msgs:
        if len(m) < 5 or m[0] not in SERVER_ORDER_TYPES:
            passthru.append(m)
            continue
        uid = struct.unpack_from(">I", m, 1)[0]
        st["in"] += 1
        key = (uid, m[0], m[5]) if m[0] == 0x30 and len(m) > 5 else (uid, "go")    # skills each on their own
        lm = last.get(key)
        if lm is not None and lm[0] == m and now - lm[1] < ORDER_REPEAT_S:
            st["dup"] += 1
            pend.pop(key, None)
            continue
        old = pend.get(key)
        pend[key] = ((old[0] if old else now), m)
    win = holder.get("_ord_win")
    if not win or int(now) != win[0]:
        win = holder["_ord_win"] = [int(now), 0]
    room = max(0, ORDER_BUDGET - win[1])
    tg_ = getattr(s, "targets", None) or {}
    for k in [k for k in pend if k[0] not in tg_]:
        pend.pop(k, None)                             # the unit died / left while its order waited
    rank = {0x30: 0, 0x1B: 1, 0x2B: 1, 0x1A: 2}
    order = sorted(pend.items(), key=lambda kv: (rank.get(kv[1][1][0], 3), kv[1][0]))
    out = []
    for key, (t0, m) in order[:room]:
        out.append(m)
        pend.pop(key, None)
        last[key] = (m, now)
        if now - t0 >= 0.5:
            st["late"] += 1
    win[1] += len(out)
    st["out"] += len(out)
    if now - st["t0"] >= ORDER_STATS_S:
        if st["in"] >= ORDER_STATS_S * 5:
            log(f"   order gate ({who}, map {getattr(s, 'map', '?')}): {st['in']} orders in {now - st['t0']:.0f} s -> "
                f"{st['out']} sent, {st['dup']} repeats dropped, {st['late']} delayed, {len(pend)} waiting")
        holder["_ord_stats"] = {"t0": now, "in": 0, "out": 0, "dup": 0, "late": 0}
        for k in [k for k, v in last.items() if now - v[1] > 60]:
            last.pop(k, None)                         # units long gone
    return passthru + out

# ---- DELAYED PUT (0x50): the ONE way a unit joins a RUNNING lock-step battle (user 2026-10-28 13:30/13:32 "units
# move in jerks and snap back out of sync").  Measured with F47: about one rollback every 10 s, 200-500 ms late, and
# bursts of ~2400-2600 ms late.  Cause: the client's clock controller 0x548f00 also runs for 0x50 (004ad4e0) - its time
# was game_time + REINFORCE_DELAY (300 ticks = 3 s AHEAD), so d = L - T > 100 and the client JUMPED its clock forward
# by d - 50 (~2.5 s): every command after that was ~2.5 s "late" -> rollback storm.  NPC reinforcements now come
# often (npc_auto_reinforce), so it got worse.  Now the PUT is SENT after the wait and stamped like every other
# command (game time of the receiver + RELAY_DELAY): every client still adds the unit on the same frame, the squad still
# appears REINFORCE_DELAY later, and the clock never jumps.  Was written out in 5 places (aliens, players' squads, NPC
# squads, GM spawn, join replay).
def delayed_put(s, body, still=None, delay_s=None):
    """send PUT_UNIT body (0x18 packet) to every member of s's battle as 0x50 after delay_s (default REINFORCE_DELAY);
    still() -> False cancels (unit died / left).  -> the wall time it appears (for enter_t)."""
    d = REINFORCE_DELAY / 100.0 if delay_s is None else float(delay_s)
    B = getattr(s, "battle", None)
    def go():
        try:
            if getattr(s, "battle", None) is not B or (B is not None and B.get("won")) or s.w.is_closing():
                return
            if still is not None and not still():
                return
            for o in battle_members(s):
                o.send(bytes([0x50]) + struct.pack(">I", game_time(o) + RELAY_DELAY) + body[1:])
        except Exception as e:
            log(f"   delayed put error: {e!r}")
    try:
        asyncio.get_event_loop().call_later(d, go)
    except Exception:
        go()
    return time.time() + d

def send_lumps(s, msgs, delay=None):
    if delay is None:
        delay = RELAY_DELAY
    for o in battle_members(s):
        pk = bytes([0x80, 0, 0]) + struct.pack(">IH", game_time(o) + delay, len(msgs))
        for m in msgs:
            pk += struct.pack(">H", len(m)) + m
        o.send(pk)

def stop_attack(s, uid):
    cancel_pending_skill(s, uid)                         # a newer order replaces a pending skill (lock-step)
    t = getattr(s, "attacks", {}).pop(uid, None)
    if t:
        t.cancel()

def hit_damage(dmg, armor, row, col):
    """client 004d0420: max(1, damage - armour * (100 + TABLE[armour class][damage class]) / 100)."""
    return DT.hit_damage(dmg, armor, row, col if DAMAGE_TYPES else -1)      # (damage_types: the one formula)

async def attack_loop(s, uid, tid):
    try:
        st9, speed = s.unit_cmb.get(uid, ([100] * 9, 100))
        tg = s.targets.get(tid)
        air = bool(tg and tg.get("air"))
        dmg, rng, cd = (st9[6], st9[7], max(20, st9[8])) if air or not st9[3] else (st9[3], st9[4], max(20, st9[5]))
        if not tg or dmg <= 0:
            return
        # The client only sends 0x29 once the attacker is already IN RANGE (FUN_004db110 walks first with 0x16
        # and the unit AI sends 0x29 on arrival), so the first shot follows the relayed order (game time + 10).
        await asyncio.sleep(0.1)
        while tid in s.targets:
            ax, ay = s.unit_pos.get(uid, (-9999, -9999))
            blocked = SHIELDS and not air and shield_at(ax, ay) != shield_at(tg["x"], tg["y"])
            if tg.get("npc") is not None and not air and st9[3] > 0 and st9[4] >= NPC_ARTY_RANGE:
                tg["shelled"] = (time.time(), (ax, ay))      # user 2026-10-25: NPCs step out of artillery fire
            damage_target(s, uid, tid, 0 if blocked else hit_damage(dmg, tg["armor"], tg.get("arow", 0), st9[2] // 100))
            if tid not in s.targets:
                break
            await asyncio.sleep(cd / 100)
    except asyncio.CancelledError:
        pass
    finally:
        if s.attacks.get(uid) is asyncio.current_task():
            s.attacks.pop(uid, None)

KILL_REWARD = (50, 10, 5, 0, 0)   # money, ore, silicon, uranium, sulfur per kill (PLACEHOLDER)
BATTLE_END_DELAY = 5.0

# ---- ALIEN RAIDS (counter-attacks, user decision 2026-10-21) --------------------------------------------------
RAIDS = {}                 # province id -> {"nation", "until", "from"}
def province_label(pid):
    """(user 2026-10-23 21:39) players know a province by the NUMBER the strategic map draws on it (01..85), not its id."""
    if pid in CAPITALS.values():
        return next((n[1] for n in NATIONS if CAPITALS.get(n[0]) == pid), str(pid))
    return f"#{province_number(pid):02d}"

def province_label_lang(pid, lang):
    """the province as the player sees it on the strategic map: "24号省" / "24號省" / "province #24"; capitals by name."""
    for nid, cap in CAPITALS.items():
        if cap == pid:
            nm = nation_name(nid, lang)
            return {"zh-cn": f"{nm}首都", "zh-tw": f"{nm}首都"}.get(lang, f"capital of {nm}")
    k = province_number(pid)
    return {"zh-cn": f"{k:02d}号省", "zh-tw": f"{k:02d}號省"}.get(lang, f"province #{k:02d}")

def battle_units(B):
    """every living unit on the map of battle B as (nation, stats9, art kind, hp): the players' units (newest HP from
    sgs/unit_hp, else the PUT HP) and the server-owned ones (NPC / aliens, nation None for aliens).  The ONE listing the
    strength estimates use (was written out separately in battle_threat and side_strength)."""
    for o in list(B.get("members", ()) or ()):
        if getattr(o, "spectator", False) or o.w.is_closing():
            continue
        sn = side_nation(o)
        hp_ = getattr(o, "unit_hp", {}) or {}
        pa_ = getattr(o, "put_args", {}) or {}
        for u in getattr(o, "alive_units", set()) or ():
            pa = pa_.get(u) or {}
            yield sn, pa.get("st9"), pa.get("kind"), hp_.get(u, pa.get("hp", 100))
    for tg in list((B.get("targets") or {}).values()):
        if tg.get("hp", 0) <= 0:
            continue
        pu = tg.get("put") or {}
        yield (tg.get("nation") if tg.get("npc") is not None else None), pu.get("st9"), pu.get("kind"), tg.get("hp", 100)

def capture_province(pid, nid):
    """THE way a province changes hands after a fight (user 2026-10-28 13:05 "one logic per mechanism").  Was written
    out in 5 places (player capture, NPC raid won, NPC raid time-up, NPC battle won, abstract NPC assault) with
    different side effects: two of them told the NEW owner "<province> was lost!" (the owner was read after the change),
    one ignored the "an ally's province is never taken" rule, the player capture never told the old side.
    -> the old owner (0 = was neutral) when the province changed hands, None when nothing changed."""
    nid = int(nid or 0)
    old = int(province_owner(pid) or 0)
    if not nid or old == nid:
        return None
    if old and same_side(old, nid):
        log(f"   capture of {pid} by nation {nid}: owner {old} is an ally - no capture")
        return None
    set_province_owner(pid, nid)
    RAIDS.pop(pid, None)
    if not old:
        AL.set_garrison(world_state(), pid, 0.0)
        save_world(world_state())
    else:
        _lb = province_label(pid)
        _notify_side(old, f"{_lb} 失守了！", f"{_lb} 失守了！", f"{_lb} was lost!", (255, 120, 120))
    return old

def notify_side(nid, en, rgb=(255, 200, 120), zh_cn=None, zh_tw=None):
    """a chat line to every online player of side nid (its allies too) - the ONE side notice (raid_notify sent to the
    exact nation only, npc_world._notify_side to the side: the same "province lost" news reached allies or not
    depending on the code path).  Without Chinese texts the English one is translated per player (i18n catalogue)."""
    for o in list(ONLINE):
        if getattr(o, "logged_in", False) and not o.w.is_closing() and same_side(side_nation(o), nid):
            try:
                if zh_cn or zh_tw:
                    _say_lang(o, zh_cn or zh_tw, zh_tw or zh_cn, en, rgb)
                else:
                    o.send(chat_line(0x0A, en, rgb))
            except Exception:
                pass

def raid_notify(nation, text, rgb=(255, 120, 120)):
    notify_side(nation, text, rgb)

async def raid_cycle():
    """every RAID_CHECK_SECONDS: per planet, maybe one owned (non-capital) province next to a strong neutral
    garrison is attacked; its nation has RAID_DEFEND_SECONDS to enter it and kill the aliens, else it becomes
    neutral again (garrison GARRISON_AFTER_LOSS)."""
    global WORLD
    while True:
        try:
            now = time.time()
            if WORLD is None:
                WORLD = load_world()
            for pid, r in list(RAIDS.items()):
                if now < r["until"] or pid in BATTLES or r.get("npc"):
                    continue
                RAIDS.pop(pid, None)
                if province_owner(pid) == r["nation"]:
                    set_province_owner(pid, 0)
                    if r.get("star"):
                        raid_notify(r["nation"], f"Demon star: {province_label(pid)} was retaken by the demon-star monsters.")
                        log(f"   STAR RAID: {pid} not defended -> lost by nation {r['nation']}")
                        continue
                    AL.set_garrison(WORLD, pid, AL.GARRISON_AFTER_LOSS)
                    save_world(WORLD)
                    raid_notify(r["nation"], f"{province_label(pid)} was lost to the aliens.")
                    log(f"   RAID: {pid} not defended -> lost by nation {r['nation']}")
            if now >= getattr(raid_cycle, "next_check", 0):
                raid_cycle.next_check = now + AL.RAID_CHECK_SECONDS
                caps = set(CAPITALS.values())
                for pl in [p[0] for p in PLANETS]:
                    if random.random() >= AL.RAID_CHANCE:
                        continue
                    cands = []
                    for pid in planet_provinces(pl):
                        own = province_owner(pid)
                        if not own or pid in caps or pid in RAIDS or pid in BATTLES:
                            continue
                        for q in PORTAL_LINKS.get(pid % 100000, ()):
                            qid = pl * 100000 + q
                            if province_owner(qid) == 0 and AL.garrison(WORLD, qid) >= AL.RAID_MIN_GARRISON:
                                cands.append((pid, qid, own)); break
                    if cands:
                        pid, qid, own = random.choice(cands)
                        RAIDS[pid] = {"nation": own, "until": now + AL.RAID_DEFEND_SECONDS, "from": qid}
                        raid_notify(own, f"Aliens are attacking {province_label(pid)}! Defend it within "
                                         f"{AL.RAID_DEFEND_SECONDS // 60} minutes or it is lost.")
                        log(f"   RAID: aliens from {qid} attack {pid} (nation {own})")
            if now >= getattr(raid_cycle, "next_star", 0):
                raid_cycle.next_star = now + STAR_RAID_CHECK_SECONDS
                star_raid_tick(now)
        except Exception as e:
            log(f"   raid cycle error: {e!r}")
        await asyncio.sleep(30)

# DEMON-STAR COUNTER-ATTACKS (user 2026-10-27 12:30 "魔星的外星怪物会反扑将占领的省抢回来"): during a window the
# demon-star monsters strike back at the provinces taken from them - a held province next to monster land (owner 0)
# is attacked; its side has STAR_RAID_DEFEND_SECONDS to enter it and win, else the monsters take it back.  The landing
# corner is never attacked (the way in); the centre may be.
STAR_RAID_CHECK_SECONDS = 3 * 60
STAR_RAID_CHANCE = 0.5            # per star planet with held provinces, per check
STAR_RAID_DEFEND_SECONDS = 5 * 60
STAR_RAID_MAX = 2                 # running counter-attacks per star planet at once

def star_raid_tick(now=None, rnd=random):
    now = now or time.time()
    if not star_window_open(now):
        return []
    started = []
    for pl in sorted(STAR_PLANET_IDS):
        if sum(1 for p in RAIDS if is_star_province(p) and (p // 100000) % 1000 == pl) >= STAR_RAID_MAX:
            continue
        if rnd.random() >= STAR_RAID_CHANCE:
            continue
        corners = {star_corner(n, pl) for n in CAPITALS}
        cands = []
        for pid in planet_provinces(pl):
            own = province_owner(pid)
            if not own or pid in corners or pid in RAIDS or pid in BATTLES:
                continue
            q = [pl * 100000 + q for q in PORTAL_LINKS.get(pid % 100000, ()) if province_owner(pl * 100000 + q) == 0]
            if q:
                cands.append((pid, rnd.choice(q), own))
        if not cands:
            continue
        pid, qid, own = rnd.choice(cands)
        RAIDS[pid] = {"nation": own, "until": now + STAR_RAID_DEFEND_SECONDS, "from": qid, "star": True}
        raid_notify(own, f"Demon star: the monsters strike back at {province_label(pid)}! Defend it within "
                         f"{STAR_RAID_DEFEND_SECONDS // 60} minutes or it is lost.")
        log(f"   STAR RAID: monsters from {qid} attack {pid} (nation {own})")
        started.append(pid)
    return started
