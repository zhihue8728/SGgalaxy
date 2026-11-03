# sgserver part "world": world config, nations, province ownership, aliens config.
# Loaded by sgserver.py into ONE shared namespace (exec, in the order of PARTS) - not an importable module;
# every name here is a sgserver global.  Checks: python tools/check_server.py
# ---------------------------------------------------------------------------------------------------------------
# WORLD CONFIG.  One server = one star system of 8 planets (client file vinu.inf, pam2.dat; full province table in
# analysis/vinu_provinces.tsv).  Province id = planet*100000 + col*100 + row; planets are 8x8 grids, planet 2 is 9x9.
# Design: small planets are novice planets with 4 nations each (capitals in the four corner provinces, the faction
# page has exactly 4 slots); planet 2 (the big one) is the advanced planet, closed to new heroes.
# To open another novice planet: add it to PLANETS with OPEN=1 and give it 4 entries in NATIONS.
# check_world() refuses to start the server if this data would break the client (see docs/notes/FINDINGS.md).
#
# PLANETS: (id, name, cls, OPEN to new heroes, (x, y, z) orbit vector as signed bytes).
#   (2026-10-27 11:52 user: keep the different orbit tilts - the 11:37 shared vector was undone)
#   The orbit vector must not be (0,0,0): the client rotates it to place the planet (0045a4e0) and zooms the camera
#   there; at the origin the planet sits inside the central star and the planet page goes black.
#   If no planet is OPEN the client shows the GBK "planet full" dialog (garbled Hangul).
# class = planet art odv.dat pl-%03d.bik (frames checked 2026-10-27 11:28, analysis: _scratch/pl/planets.png):
#   000 Mars-like  001 Earth  002/004/012/013/014/016 asteroids  003 orange  005 Jupiter (bands)  006 grey moon
#   007 Saturn (rings)  008 Uranus blue  009 red rocky  010/011 green-blue  015 hazy  017 Neptune blue
PLANETS = [(6, "Earth", 1, 1, (6, 0, 2)),       # tier 1 (novice)    - names: user 2026-10-27 11:26
           (2, "Mars", 0, 0, (-8, 0, -3)),       # tier 2 (advanced)  pl-000 (was 2 = an asteroid)
           (3, "Jupiter", 5, 0, (2, 0, -9))]     # tier 3 (elite)     pl-005 (was 3 = an orange rock)          # class = planet art pl-%03d.bik (1 / 2 / 3: three different looks)
# orbit vectors were 10x larger: the Dimensional Matrix measures planet distance from them ("That planet is too far
# for you to reach") and the planets were outside the 3D view (only the star visible).
# PROGRESSION (design, 2026-10-20): planets have tiers  Novice -> Advanced -> Elite.  New commanders are born on the
# Novice planet; at a required commander level they can ADVANCE to the next tier planet or REINCARNATE (rebirth).
# Level thresholds and what carries over on rebirth are decided later (needs the level / XP system).
PLANET_TIER = {6: 1, 2: 2, 3: 3}          # planet id -> tier
TIER_MIN_LEVEL = {1: 0, 2: None, 3: None} # commander level needed to move to a tier (None = not decided yet)
BEGINNER_PLANET = 6
# terrain type sent in 0x17 for capital maps.  The capital path (flag 1) does not read vinu.inf, so with 0 the
# client remaps every ground tile with theme 0 -> buildings visible but the ground is black.  13 = city theme
# (the type vinu.inf gives the CornerA corners of planets 0 and 6).
CAPITAL_TERRAIN = 13

# LAYOUT: planet id -> vinu.inf planet whose province grid it uses (sent to the client in 0x43, which maps every
# province id through it).  The strategic map art (NTF2.dat nbCCRR/nsCCRR shapes) is a single 9-column grid
# (even columns rows 0-8, odd columns rows 0-9) = exactly vinu planet 2's grid.  The 8x8 planets only use part of
# it, so their "corners" are not the corners of the drawn map.  Every planet therefore uses layout 2.
LAYOUT = {p: 2 for p in range(8)}
GRID = {p: 9 for p in range(8)}            # columns 0-8 (rows 0-8, odd columns also row 9)
# corner provinces (CornerA in layout 2): order = nation slot 0..3 = top-left, top-right, bottom-left, bottom-right
CORNERS = {p: [p * 100000 + c for c in (0, 800, 8, 808)] for p in range(8)}

# NATIONS: (id, name, (r, g, b), planet, corner slot 0..3).  Ids are stored in accounts, do not renumber.
NATION_DEFS = [(1, "Nation1", (255, 64, 64), 6, 0), (2, "Nation2", (64, 255, 64), 6, 1),
               (3, "Nation3", (64, 64, 255), 6, 2), (4, "Nation4", (255, 255, 64), 6, 3),
               # Advanced planet (tier 2) and Elite planet (tier 3) factions, joined through the StarCenter.
               # Ids 11-14 / 21-24 (NOT 5: the client's star-gate range check special-cases nation 5).
               (11, "Adv-Nation1", (255, 64, 64), 2, 0), (12, "Adv-Nation2", (64, 255, 64), 2, 1),
               (13, "Adv-Nation3", (64, 64, 255), 2, 2), (14, "Adv-Nation4", (255, 255, 64), 2, 3),
               (21, "Elite-Nation1", (255, 64, 64), 3, 0), (22, "Elite-Nation2", (64, 255, 64), 3, 1),
               (23, "Elite-Nation3", (64, 64, 255), 3, 2), (24, "Elite-Nation4", (255, 255, 64), 3, 3)]
NATION_SLOT = {n[0]: n[4] for n in NATION_DEFS}

# CHINESE NATION NAMES (user 2026-10-22 15:46): one name per COLOUR, the same on every planet with the tier in front
# (Novice: X國, Advanced: 進階X國, Elite: 精英X國).  English clients keep the English names above.
NATION_COLOUR_ZH = {0: ("赤焰國", "赤焰国"), 1: ("翠林國", "翠林国"), 2: ("蒼海國", "苍海国"), 3: ("金陽國", "金阳国")}   # slot = colour
NATION_TIER_ZH = {1: ("", ""), 2: ("進階", "进阶"), 3: ("精英", "精英")}
NEUTRAL_ZH = ("中立", "中立")

def nation_name(nid, lang="en"):
    """display name of a nation in this language (zh-tw / zh-cn: Chinese, otherwise the English name)."""
    if lang in ("zh-tw", "zh-cn"):
        k = 0 if lang == "zh-tw" else 1
        if nid == 0:
            return NEUTRAL_ZH[k]
        d = next((n for n in NATION_DEFS if n[0] == nid), None)
        if d:
            return NATION_TIER_ZH[PLANET_TIER.get(d[3], 1)][k] + NATION_COLOUR_ZH[d[4]][k]
    if nid == 0:
        return "Neutral"
    return next((n[1] for n in NATION_DEFS if n[0] == nid), str(nid))

LAST_ACP_BY_IP = {}       # peer IP -> code page of the last session from there (the nation table comes before 0xF6)

def session_lang_enc(s, acc=None):
    """(lang, enc) for text sent to s - also before its 0xF6 arrived: remembered code page of the account or of the IP."""
    if getattr(s, "acp", None):
        return getattr(s, "lang", "en"), getattr(s, "enc", "latin-1")
    acp = None
    try:
        acp = (load_accounts().get(acc or getattr(s, "acc", None) or "") or {}).get("acp")
    except Exception:
        pass
    if not acp:
        try:
            acp = LAST_ACP_BY_IP.get((getattr(s, "peer", None) or ("",))[0])
        except Exception:
            acp = None
    if acp:
        return I18N.lang_of_acp(int(acp)), I18N.codec(int(acp))
    return "en", "latin-1"
NATIONS = [(n[0], n[1], n[2]) for n in NATION_DEFS]
# capital = map id of the nation's corner province (nation +0x110; client planet = (v/100000)%1000).
# Entering it uses 0x17 with the CAPITAL flag = 1: base map Capital.nm + overlay "%08d.nm" (fallback "000"+5 digits).
CAPITALS = {n[0]: CORNERS[n[3]][n[4]] for n in NATION_DEFS}

# ---- PROVINCE OWNERSHIP (persisted in world.json) --------------------------------------------------------------
# Province ids of a planet in layout 2: col 0-8, rows 0-8, odd columns also row 9 (see LAYOUT / GRID above).
# Owner 0 = no nation (aliens, the 'Neutral' entry of the 0x0F table).  Capitals belong to their nation.
WORLD_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "world.json")

def planet_provinces(planet):
    return [planet * 100000 + c * 100 + r for c in range(GRID.get(planet, 9)) for r in range(10 if c % 2 else 9)]

def load_world():
    try:
        w = STORE.kv_get(db(), "world") or {}
    except Exception:
        w = {}
    own = w.setdefault("owners", {})
    for p in PLANETS:
        for pid in planet_provinces(p[0]):
            own.setdefault(str(pid), 0)
    for nid, cap in CAPITALS.items():
        own[str(cap)] = nid
    return w

def save_world(w):
    STORE.kv_put(db(), "world", w)              # game.db (was world.json)

WORLD = None
# DEMON-STAR PLANETS (claude/DEMON_STAR_PLANETS.md, 2026-10-27): planets 0 / 1 / 5 / 4 = Azure Dragon / White Tiger /
# Vermilion Bird / Black Tortoise (results_field.DEMON_STARS).  Their provinces keep their owners in a SEPARATE table
# world["star_owners"], reset every demon-star window, so nothing that walks world["owners"] (settlement, income,
# NPCs, raids, 0x0F) ever sees them.
STAR_PLANET_IDS = {7, 1, 4, 5}       # (12:48) never planet 0: map id 0 of its corner reads as "no map"

def is_star_province(pid):
    return isinstance(pid, int) and pid < 100000000 and (pid // 100000) % 1000 in STAR_PLANET_IDS

def _owner_table(pid):
    return WORLD.setdefault("star_owners", {}) if is_star_province(pid) else WORLD["owners"]

def province_owner(pid):
    global WORLD
    if WORLD is None:
        WORLD = load_world()
    return int(_owner_table(pid).get(str(pid), 0))

def set_province_owner(pid, nid):
    global WORLD
    if WORLD is None:
        WORLD = load_world()
    tab = _owner_table(pid)
    old = int(tab.get(str(pid), 0))
    tab[str(pid)] = nid
    if is_star_province(pid):                 # demon-star land: no field value / owner log / NPC reaction
        save_world(WORLD)
        log(f"   demon star province {pid}: {old} -> {nid}")
        return
    if old != nid:
        WORLD.setdefault("since", {})[str(pid)] = time.time()     # field value grows with the holding time
        try:                                  # every ownership change is kept in game.db (kv "owner_log")
            import inspect
            why = inspect.stack()[1].function
            lg = STORE.kv_get(db(), "owner_log") or []
            lg.append([int(time.time()), pid, old, nid, why])
            STORE.kv_put(db(), "owner_log", lg[-5000:])
        except Exception as e:
            log(f"   owner log error: {e!r}")
    save_world(WORLD)
    try:
        npc_owner_changed(pid, old, nid)
    except Exception as e:
        log(f"   npc_owner_changed error: {e!r}")
    if old != nid and pid < 100000000:
        try:
            asyncio.get_event_loop().call_later(RESULT_SHOW_SECONDS + 5, evict_province, pid)
        except Exception:
            pass

def evict_sweep(now):
    """user 2026-10-23 21:47: after a battle's settlement nobody of another nation stays in a province that is not his
    side's - every NPC tick, a commander standing on such a province map (no battle running there, not just arrived)
    is moved out like evict_province."""
    for o in list(ONLINE):
        try:
            if not getattr(o, "logged_in", False) or o.w.is_closing() or getattr(o, "battle", None) \
                    or getattr(o, "retreating", False) or getattr(o, "spectator", False):
                continue
            m = getattr(o, "map", None)
            if not m or m >= 100000000 or map_kind(m) != "province" or now - getattr(o, "map_since", now) < 15:
                continue
            pid = province_of(m)
            own = province_owner(pid)
            B = BATTLES.get(pid)
            # user 2026-10-25 14:40: strictly nobody stays in a province that is not his side's - unowned land too
            # (the only reason to be there is a running battle)
            if (own and same_side(own, side_nation(o))) or (B is not None and not B.get("won")) or pid in RAIDS:
                continue
            evict_province(pid)
        except Exception as e:
            log(f"   evict sweep {getattr(o, 'acc', '?')}: {e!r}")

def evict_province(pid):
    """user 2026-10-23 17:09: once the battle is over and the province taken, commanders that do not belong to its new
    owner's side leave the province (to a neighbouring one of their side, else their capital); they can come back
    only by entering a battle again from a neighbouring province.  NPCs: npc_tick (npc_leave_lost)."""
    nid = province_owner(pid)
    B = BATTLES.get(pid)
    if B is not None and not B.get("won"):
        return                                         # a new battle is already running there
    for o in list(ONLINE):
        try:
            if not getattr(o, "logged_in", False) or o.w.is_closing() or getattr(o, "battle", None) \
                    or getattr(o, "retreating", False) or getattr(o, "spectator", False):
                continue
            here = getattr(o, "map", None)
            if not here or here >= 100000000 or province_of(here) != pid or map_kind(here) != "province":
                continue
            me = side_nation(o)
            if nid and same_side(me, nid):
                continue
            cap = CAPITALS.get((getattr(o, "cmd", {}) or {}).get("nation"))
            # user 2026-10-25 13:51/14:32: one step back towards the capital over own / allied / unowned land; no such
            # neighbour at all -> straight to the capital
            tgt, dest = capital_fallback(o, pid)
            if not tgt:
                tgt, dest = retreat_target(o)
            if not tgt or tgt == pid or (province_owner(tgt) and not same_side(province_owner(tgt), me)):
                tgt, dest = cap, None
            dx, dy = dest if dest else (0x200, 0x200)
            log(f"   {o.acc} leaves {pid} (taken by nation {nid}) -> {tgt}")
            _say_lang(o, "此省已被敌方占领，你已撤到相邻的己方省份。要再进攻请从相邻省份进入战斗。",
                      "此省已被敵方佔領，你已撤到相鄰的己方省份。要再進攻請從相鄰省份進入戰鬥。",
                      "This province was taken by the enemy - you withdrew to a neighbouring province of your side.")
            o.battle_province = None
            enter_field(o, tgt, dx, dy, capital=(tgt in CAPITALS.values()))
        except Exception as e:
            log(f"   evict {getattr(o, 'acc', '?')} from {pid} failed: {e!r}")

def map_kind(mapid):
    """client map-id ranges (00495e30): 2xxxxxxxx exercise.nm (CTF / training), 4xxxxxxxx Cave1.nm (alien cave),
    5xxxxxxxx rr1.nm, 6xxxxxxxx nbattle.nm (Cadet Combat Field); below 100000000 = a province of a planet."""
    top = mapid // 100000000
    if mapid < 100000000:
        # Portals.por / Capital.por field portals use RELATIVE targets added to the current map id:
        # +-100 / +-1 = neighbouring province, +10000..+80000 = mon1..mon8.nm (hunting grounds around a province),
        # +90000 = sst.nm.  So digit (id // 10000) % 10 tells the map type (client 00495e30).
        digit = (mapid // 10000) % 10
        if digit == 0:
            return "province"
        return "sst" if digit == 9 else "hunt"
    return {2: "ctf", 4: "cave", 5: "cave", 6: "cave"}.get(top, "other")

# SIMULATION MAPS (user 2026-10-27 19:59 "Sim的戰鬥地圖跟大地圖要分開"): a simulation runs on map id SIM_BASE + province
# id, the id the Battle Simulation board itself uses (its ENTER sends 0x32 [00][u32 that id]).  The client loads the
# same province map for it (005dc190: key = id/1e9 + (layout - id/100000) * 100000 + id -> the same vinu entry), but
# every server table keyed by map id (BATTLES, owners, strategic map, NPCs) keeps it apart from the real province.
SIM_BASE = 100000000

def is_sim_map(mapid):
    return isinstance(mapid, int) and SIM_BASE <= mapid < 2 * SIM_BASE

def real_map(mapid):
    """the province map behind a simulation map id (other ids unchanged)."""
    return mapid - SIM_BASE if is_sim_map(mapid) else mapid

def province_of(mapid):
    """the province a province-family map belongs to (digit stripped)."""
    return mapid - ((mapid // 10000) % 10) * 10000 if mapid < 100000000 else None

# ---- ALIENS (caves, unowned provinces) ----------------------------------------------------------------------
# Ground organic chassis only (aviation aliens would be unhittable for ground-only weapons).  Stats per level are
# PLACEHOLDERS: hp, damage, armor grow with the level; range 8 m, cooldown 1.6 s, speed 1.5 m/s.
ALIEN_TYPES = [("Ubik", "g011"), ("Slanth", "g015"), ("Poda", "g024"), ("Larva", "g025")]
import i18n as I18N
import unitnames as UN
import aliens as AL          # level / squads / garrison / raids design (claude/ALIEN_PLAN.md)
try:      # map name -> [width, height, walkable cells] (from pam.dat / pam3.dat .nm headers, 2026-10-22)
    MAP_SIZES = data_json("map_sizes.json")
except Exception:
    MAP_SIZES = {}
try:
    SPAWN_SPOTS = data_json("spawn_spots.json")
except Exception:
    SPAWN_SPOTS = {}         # tools/gen_spawn_spots.py
ALIEN_NATION = 0
CAVE_ALIENS = 6
PROVINCE_ALIENS = 5

def alien_stats(level):
    hp = 250 + 120 * level
    st9 = [2 * level, 0, 0, 25 + 8 * level, 8 * 20, 160, 0, 0, 160]
    return hp, st9, 15

def check_world():
    """Start-up sanity check of the New-commander data.  Every rule here was learned from a client failure:
      1. at least one planet must have OPEN=1, otherwise the client (005a43b0) shows the GBK message
         "此星球人数已满，不能注册，请换其他星球" (planet full, cannot register) which the Korean font renders as
         garbled Hangul (e.g. "늪☒헷홍☒☒찮...").
      2. every OPEN planet needs >= 1 selectable nation whose capital is on it (planet = (capital/100000)%1000),
         otherwise the planet arrows (0055b730/0055b850) loop forever looking for a usable planet = client freeze.
      3. capital % 10000 must be a province code < 809 (client 00435030)."""
    errors = []
    open_planets = [p for p in PLANETS if p[3]]
    if not open_planets:
        errors.append("no planet has OPEN=1 -> New commander shows the garbled 'planet full' dialog")
    for p in open_planets:
        if not any((CAPITALS.get(n[0], 0) // 100000) % 1000 == p[0] for n in NATIONS):
            errors.append(f"open planet {p[0]} {p[1]!r} has no nation capital on it -> planet arrows freeze the client")
    for nid, cap in CAPITALS.items():
        pl, col, row = (cap // 100000) % 1000, (cap % 100000) // 100, cap % 100
        if pl not in GRID or not (0 <= col < GRID[pl] and 0 <= row < (10 if col % 2 else 9)):
            errors.append(f"nation {nid} capital {cap}: not a province of vinu.inf (planet {pl} col {col} row {row}) -> client crash")
    for p in PLANETS:
        if tuple(p[4]) == (0, 0, 0):
            errors.append(f"planet {p[0]} {p[1]!r} orbit vector is (0,0,0) -> planet page goes black when zooming to it")
    if not any(p[0] == BEGINNER_PLANET and p[3] for p in PLANETS):
        errors.append(f"BEGINNER_PLANET {BEGINNER_PLANET} is not an OPEN planet")
    return errors

# Nation relations (class-A 0x05, client FUN_00547bb0 -> CNationInfo map (a,b)->state, then FUN_005521d0):
#   [05][u8 0 = full list][u8 n]{u32 nation a, u8 m, m x {u32 nation b, u8 state}}   or   [05][u8 1][u32 a][u32 b][u8 state]
# FUN_005521d0 builds the alliance groups: group[i] = i for every nation of the 0x0F table, then nations with
# state 1 (= Ally) are merged.  Units take group(nation) at PUT time (+0x358/+0x35c) and the client treats two units
# as friends when their groups are equal (FUN_004c52b0).  Without this packet the group table is empty, every
# nation maps to group 0 -> everything is friendly: no red units, right-click never attacks.
NATION_ALLIES = []          # [(a, b)] pairs of allied nation ids (persisted in world.json "allies")
def WORLD_allies_save():
    global WORLD
    if WORLD is None:
        WORLD = load_world()
    WORLD["allies"] = [list(x) for x in NATION_ALLIES]
    save_world(WORLD)
def build_relations(allies=None):
    allies = NATION_ALLIES if allies is None else allies
    by = {}
    for a, b in allies:
        by.setdefault(a, []).append(b)
    d = bytearray([0x05, 0, len(by)])
    for a, bs in by.items():
        d += struct.pack(">I", a) + bytes([len(bs)])
        for b in bs:
            d += struct.pack(">I", b) + bytes([1])
    return bytes(d)

try:
    PORTAL_LINKS = {int(k): set(v) for k, v in data_json("portal_links.json").items()}
except Exception:
    PORTAL_LINKS = {}          # file missing: no neighbour check

def build_universe_layout():
    """class-A 0x66 (client 005460a0 -> FUN_005dc1f0): [u8 n] n x {u8 planet, u8 vinu.inf layout planet} into the
    CUniverseMan planet->layout map (+0x24).  THIS map (not 0x43, which only feeds CPlanetInfoMan for drawing) is what
    the client uses for (a) the province map file of a province / its preview (FUN_005dc190) and (b) which planet's
    records of portals.por it loads as the portal network (FUN_0056c440 -> FUN_005dc2b0).  Never sent before
    2026-10-21: every planet fell back to layout 0 (the 8x8 grid), so only the top-left capital had portals, the
    other three capitals could not find a path ("You cannot reach this province!") and column-8 / row-8 provinces
    had no preview.  Must arrive before the first map is entered (the portal list is only rebuilt on a planet change)."""
    items = sorted(LAYOUT.items())
    return bytes([0x66, len(items)]) + b"".join(bytes([p & 0xFF, l & 0xFF]) for p, l in items)

# New-commander FACTION page text (one per colour slot; tier prefix comes with the name)
NATION_INTRO = {
    0: ("以烈焰為旗的軍事國家，崇尚正面強攻與鋼鐵紀律，裝甲與重火力部隊是他們的驕傲。",
        "以烈焰为旗的军事国家，崇尚正面强攻与钢铁纪律，装甲与重火力部队是他们的骄傲。",
        "A martial nation under the flame banner: frontal assault, iron discipline, armour and heavy guns."),
    1: ("生於密林的國度，擅長機動與伏擊，善用地形以少勝多，是最難捉摸的對手。",
        "生于密林的国度，擅长机动与伏击，善用地形以少胜多，是最难捉摸的对手。",
        "Born in the deep forests: masters of mobility and ambush who use the terrain to beat larger armies."),
    2: ("掌握海洋與天空的科技強國，重視研究與空中力量，以精密戰術見長。",
        "掌握海洋与天空的科技强国，重视研究与空中力量，以精密战术见长。",
        "A technocracy of sea and sky that values research and air power and wins with precise tactics."),
    3: ("富饒的黃金之國，資源與貿易最為發達，能以雄厚國力支撐長期戰爭。",
        "富饶的黄金之国，资源与贸易最为发达，能以雄厚国力支撑长期战争。",
        "The wealthy golden nation, strongest in resources and trade, built to outlast any war."),
}

def nation_intro(nid, name, lang):
    d = next((n for n in NATION_DEFS if n[0] == nid), None)
    k = {"zh-tw": 0, "zh-cn": 1}.get(lang, 2)
    if d is None or d[4] not in NATION_INTRO:
        return name if nid else ("中立" if k < 2 else "Neutral")
    return f"{name}：{NATION_INTRO[d[4]][k]}" if k < 2 else f"{name}: {NATION_INTRO[d[4]][k]}"

def build_nations(neutral=False, s=None, acc=None):
    """server type 0x0F (client parser FUN_00547f80). The New-commander screen crashes when the table holds the
    id-0 'Neutral' entry, the field screen needs it (nation lookup of id 0), so it is only sent after login."""
    open_pl = {p[0] for p in PLANETS if p[3]}
    allnat = ([(0, "Neutral", (128, 128, 128), 0)] if neutral else []) + \
             [(n[0], n[1], n[2], 1 if (CAPITALS[n[0]] // 100000) % 1000 in open_pl else 0) for n in NATIONS]
    lang, enc = session_lang_enc(s, acc) if s is not None else ("en", "latin-1")
    if s is not None:
        s.nations_lang = lang
    allnat = [(nid, nation_name(nid, lang), c, sel) for nid, _nm, c, sel in allnat]     # Chinese names (15:46)
    d = bytearray([0x0F, len(allnat)])
    for nid, name, (r, g, b), sel in allnat:
        nb = name.encode(enc, 'replace')[:30]
        d += struct.pack(">I", nid) + bytes([len(nb)]) + nb
        d += bytes([0, sel, r, g, b])          # +0x104, +0x105 (selectable at New commander), colour RGB
        d += struct.pack(">I", CAPITALS.get(nid, 0)) + bytes([NATION_SLOT[nid] + 1 if nid in NATION_SLOT else 0]) # +0x110, +0x10c = emblem frame in Flag-L.xpf (selected per nation)
        # +0x150 / +0x154 = WAR tab "x/y" + bar (00435030): national power / POWER_FULL (user 2026-10-27 00:26; was fields)
        _f, _tot = (war_power(nid), POWER_FULL) if nid in CAPITALS else (0, 0)
        d += struct.pack(">HH", min(_f, 65535), min(_tot, 65535))
    # per-nation extra records (client FUN_00547f80): u32 nation id, s8 short text (+0x114), u8 (+0x130), s16 long text (+0x134).
    # Without them those strings are uninitialised and the New-commander screen shows a garbled dialog once a nation is shown.
    d += struct.pack(">H", len(allnat))
    for nid, name, _c, _s in allnat:
        short = name.encode(enc, 'replace')[:27]
        long_ = nation_intro(nid, name, lang).encode(enc, 'replace')
        d += struct.pack(">I", nid) + bytes([len(short)]) + short + bytes([0]) + struct.pack(">H", len(long_)) + long_
    # province ownership (client FUN_00547f80 tail, stored at DAT_006ba80c+0x14, 12-byte records):
    # u32 province id, u32 owner nation, u8 value (added to nation +0x158; +0x15c counts the provinces).
    # The galaxy/planet map colours provinces by owner; every nation starts owning its capital.
    owned = [(cap, nid) for nid, cap in CAPITALS.items() if any(n[0] == nid for n in NATIONS)]
    d += struct.pack(">H", len(owned))
    for prov, nid in owned:
        d += struct.pack(">II", prov, nid) + bytes([1])
    return bytes(d)

# ---------------------------------------------------------------------------------------------------------------
# UNIT CATALOGUE (server-side game data; the client has none locally).  EXPERIMENTAL first version.
# (class id, chassis name, factory tab 0=Infantry 1=Mobile 2=Aviation 3=Organic, price money/ore/silicon/uranium/sulfur)
