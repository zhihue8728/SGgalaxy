# sgserver part "units_items_lab": factory units, lab upgrades, item database, equipment, purchases, lab.
# Loaded by sgserver.py into ONE shared namespace (exec, in the order of PARTS) - not an importable module;
# every name here is a sgserver global.  Checks: python tools/check_server.py
import re
# ---- Factory unit catalogue -------------------------------------------------------------------
# Chassis name = client art code (hlp.dat InfoTbl.txt: Imp=g004, Pegasus=g009, Hawk=a004, ...).
# tab: 0 Infantry, 1 Mobile, 2 Aviation, 3 Organic.  class id sent to the client = tab*100 + n
# (CUnitInfoMan record +8; the Factory files a unit under tab = classid/100).
# infl = influence needed to buy (Bahamut wiki: buy level = branch level + Clout/2). Organic values unknown -> 1.
# price = (money, ore, silicon, uranium, sulfur) -- placeholders until real prices are known.
# user 2026-10-24 13:19-13:22: the unit setup must follow the ORIGINAL game; the Chimera (light tank) was neither
# visible nor buyable at the Factory; upgrade routes must be clear and go UP only (base -> advanced -> Mk).
# Source = the official manual (units_manual.json, www.sgalaxy.com/manual_oml U-*.txt): every Infantry / Mobile /
# Aviation chassis with its influence per Mk level and its FRAME (the group of chassis it belongs to, e.g. Cyclo-rig
# = Manticore 3 / Chimera 25 / Hydra 47).
#   Factory : sells every Mk1 chassis of the three branches; the client greys out the ones whose influence the
#             commander does not have (0x2f '@' record bytes: your influence / required influence, see build_unit_shop).
#   Lab     : one step UP at a time - the next Mk of the same chassis, or a chassis of the SAME frame whose Mk1 needs
#             more influence than the unit's current form.  Needed: unit quality UQ >= the target's manual influence.
# Mk forms are named "<Chassis>-MK<n>" (as before, the manual tables are keyed case-insensitively).
# MK_MAX: how many Mk levels are in the 0x44 unit table.
#   Packet size is NOT a limit (verified 2026-10-24): the client receives into a 256 KB buffer (005a8a80, 0x40000)
#   and allocates each frame's decrypt buffer from its own length (005a9424: malloc(len*2 + 10)); the 0x44 parser
#   (005c8ff0) grows a vector of 0x68-byte records.  Frames are at most 65535 bytes (u16 length).
#   The limit is the Factory tab = class_id // 100 (0048b218): at most 99 class ids per tab.  Mk1..Mk5 of every
#   chassis = 85 per tab (Infantry, Mobile) -> MK_MAX 5.  Mk6..Mk9 (up to 125 per tab) need another scheme.
MK_MAX = 9
# (user 2026-10-24 14:20: open Mk6..Mk9 - reincarnated heroes have the Clout for them.)  No client patch: Mk6..Mk9 SHARE
# the class id of their chassis' Mk5.  The client only uses the class id for the tab (class_id // 100: Factory
# 0048b218, Lab tree 00447f96 / 00449e63, 00481a37); units, shop entries, upgrade lists and the 0x44 records are all
# matched by NAME, and the 0x44 id list is a plain vector (005c8e20), so duplicate ids are accepted.
MK_UNIQUE = 5
_CAT_TAB = {"Infantry": 0, "Mobile": 1, "Aviation": 2}
try:
    _MAN_ROWS = data_json("units_manual.json")["units"]
except Exception as _e:
    _MAN_ROWS = []
    print("units_manual.json:", _e)
_MK_INFL = {}        # chassis -> {mk: influence}
# user 2026-10-24 14:53: SatCom removed (same Gyro-rig frame and influence as Red-Eye -> a duplicate base unit).
# Owned SatCom units become the Red-Eye of the same Mk (ensure_loadouts).
REMOVED_CHASSIS = {"SatCom": "Red-Eye"}
_REMOVED_CODES = {"g054": "Red-Eye"}
_BASE_INFO = {}      # chassis -> (art code, tab, Mk1 influence, frame)
for _r in _MAN_ROWS:
    _f = _r.get("fields") or {}
    _t = _CAT_TAB.get(_f.get("category"))
    if _t is None or _f.get("influence") is None:
        continue
    _m = re.match(r"^(.*?)(?:-Mk(\d+))?$", _r["name"])
    _b, _k = _m.group(1), int(_m.group(2) or 1)
    if _b in REMOVED_CHASSIS:
        continue
    _MK_INFL.setdefault(_b, {})[_k] = int(_f["influence"])
    if _k == 1:
        _BASE_INFO[_b] = (_f.get("chassis_code"), _t, int(_f["influence"]), _f.get("group"))
UNITS = [(code, tab, infl, name) for name, (code, tab, infl, _g) in
         sorted(_BASE_INFO.items(), key=lambda kv: (kv[1][1], kv[1][2], kv[0]))]
UNITS += [
    ("a006", 3, 1,  "Oizys"),      # 小梟鷹
    ("g011", 3, 1,  "Ubik"),       # 小龍
    ("a017", 3, 1,  "Manta"),      # 飛天蛇雁
    ("g015", 3, 1,  "Slanth"),     # 修羅蟹
    ("a010", 3, 1,  "Mamos"),      # 六翼漁鷹
    ("g024", 3, 1,  "Poda"),       # 尖魔獸
    ("g025", 3, 1,  "Larva"),      # 金剛蠕蟲
    ("g051", 3, 1,  "Quorg"),      # 鬼面暴龍 -- paid unit, priced in Uranium
]
URA_PRICE = {"Wight": 250, "Quorg": 800}      # special units: UNLOCK cost in Uranium (see unit_unlocked)
# (user 2026-10-24 19:16, "as in the original" - wiki: "can be unlocked for the Price of 250 Uranium, just type /wight in
# the chatbox"; /quorg 800): /wight and /quorg unlock the chassis in the Factory ONCE per commander; after that it is
# bought like every other unit (resource price, no limit).  Before: every Wight / Quorg cost 250 / 800 Uranium.
def unit_unlocked(a, name):
    """a = account.  Unlocked by /wight /quorg (commander "unlocked"), or already owning one (bought before 19:16)."""
    cmd = (a or {}).get("commander", {}) or {}
    if name in (cmd.get("unlocked") or []):
        return True
    return any(DISPLAY.get(u.get("chassis"), u.get("chassis")) == name or split_mk(DISPLAY.get(u.get("chassis"), u.get("chassis")))[0] == name
               for u in (a or {}).get("units", []))

# ORGANIC evolution (user 2026-10-24 14:06: check the original for alien upgrades).  The official manual lists every
# organic stage with its UNIT QUALITY (UQ, in place of influence) - e.g. Xeno-ventus: Ubik-Primus 0, -Amplus 10,
# -Magnus 20, -Maximus 30, Tyr-Primus 40 ... Haltyr-Extremus 120.  No demon-star condition is mentioned: the stages
# work like the mechanical Mk line (UQ = unit level + Clout // 2).  Lab: one stage up at a time inside the line.
# The first stage keeps our Factory name (Oizys = Oizys-Prima ...).  Not included: Xeno-frame Abomination (not sold)
# and the Evo lines (Jorias, Vytyr, Charise, Dythe, Miasmal, Miasam, Charnal, Rayoks: no known way to get them; tab 3
# would also go over 99 class ids).
_ORG_FIRST = {"Xeno-ignus": "Oizys", "Xeno-ventus": "Ubik", "Xeno-humus": "Slanth", "Xeno-motus": "Poda",
              "Xeno-frigus": "Manta", "Xeno-hoverus": "Mamos", "Xeno-scavus": "Larva", "Xeno-collisi": "Quorg"}
_ORG_LINES = {}      # line -> [(name, art code, UQ)] in UQ order
for _r in _MAN_ROWS:
    _f = _r.get("fields") or {}
    if _f.get("category") == "Organic" and _f.get("group") in _ORG_FIRST:
        _ORG_LINES.setdefault(_f["group"], []).append((_r["name"], _f.get("chassis_code"), int(_f.get("unit_quality") or 0)))
_ORG_REQ, _ORG_NEXT, _ORG_CODE = {}, {}, {}
for _g, _st in _ORG_LINES.items():
    _st.sort(key=lambda x: x[2])
    _names = [_ORG_FIRST[_g]] + [x[0] for x in _st[1:]]
    for _i, (_nm, (_mn, _cd, _uq)) in enumerate(zip(_names, _st)):
        _ORG_REQ[_nm] = max(1, _uq)
        _ORG_CODE[_nm] = _cd
        if _i + 1 < len(_names):
            _ORG_NEXT[_nm] = (_names[_i + 1], max(1, _st[_i + 1][2]))
UNITS = [(c, t, (_ORG_REQ.get(n, i) if t == 3 else i), n) for c, t, i, n in UNITS]   # Mamos = Momas-Primus: UQ 80

import pricing as PRC
_MAN_F = {r["name"].lower(): (r.get("fields") or {}) for r in _MAN_ROWS}
for _g, _st in _ORG_LINES.items():                  # "Oizys" = Oizys-Prima, "Mamos" = Momas-Primus ...
    _MAN_F.setdefault(_ORG_FIRST[_g].lower(), _MAN_F.get(_st[0][0].lower(), {}))

def _man_fields(name):
    b, k = split_mk(name) if "split_mk" in globals() else (name, 1)
    return _MAN_F.get(str(name).lower().replace("-mk", "-mk")) or _MAN_F.get(f"{b}-mk{k}".lower()) or _MAN_F.get(str(b).lower()) or {}

def unit_value_of(name):
    """money value of a chassis (any Mk) from its manual numbers (pricing.unit_value)."""
    f = _man_fields(name)
    return PRC.unit_value(int(f.get("influence") or f.get("unit_quality") or 1), float(f.get("base_health") or 1500),
                          float(f.get("base_armor") or 0), float(f.get("max_weight_kg") or 80),
                          float(f.get("speed_m_s") or 3))

def _price(infl, name=None):
    """(2026-10-24 14:03, user: no original prices -> build them from each unit's characteristics) see pricing.py."""
    f = _man_fields(name) if name else {}
    b = split_mk(name)[0] if name and "split_mk" in globals() else name
    info = _BASE_INFO.get(b) if name else None
    return PRC.unit_price(int(f.get("influence") or f.get("unit_quality") or infl or 1), float(f.get("base_health") or 1500),
                          float(f.get("base_armor") or 0), float(f.get("max_weight_kg") or 80),
                          float(f.get("speed_m_s") or 3), frame=info[3] if info else None,
                          branch=info[1] if info else 3)

def mk_name(chassis, k):
    return chassis if k <= 1 else f"{chassis}-MK{k}"

def split_mk(name):
    """'Behemoth-MK3' -> ('Behemoth', 3); 'Behemoth' -> ('Behemoth', 1)."""
    m = re.match(r"^(.*?)-MK(\d+)$", str(name or ""), re.I)
    return (m.group(1), int(m.group(2))) if m else (str(name or ""), 1)

def chassis_influence(name):
    """manual influence of a catalogue name (any Mk); organic stages: their UQ."""
    if name in _ORG_REQ:
        return _ORG_REQ[name]
    b, k = split_mk(name)
    return (_MK_INFL.get(b) or {}).get(k, 1)

# ADVANCED (kept for the NPC pool / other users): the Mk2..MK_MAX forms (name, art code, Mk1 chassis, influence, zh)
ADVANCED = [(mk_name(b, k), info[0], b, infl, "")
            for b, info in sorted(_BASE_INFO.items(), key=lambda kv: (kv[1][1], kv[1][2], kv[0]))
            for k, infl in sorted(_MK_INFL[b].items()) if 2 <= k <= MK_MAX]

# The client has NO code->name table of its own for shops/units: the name it shows is the "chassis name" the server
# sends (0x44 catalogue, 0x2f shop, 0x16 roster).  Real names exist only in hlp.dat (InfoTbl.txt, used by the help).
# The art is chosen by the separate type/number bytes, so the chassis name can be the real name.
USE_REAL_NAMES = True
CODE_OF = {(u[3] if USE_REAL_NAMES else u[0]): u[0] for u in UNITS}   # display name -> art code
CODE_OF.update({x[0]: x[1] for x in ADVANCED})
DISPLAY = {u[0]: (u[3] if USE_REAL_NAMES else u[0]) for u in UNITS}   # art code -> display name
_seq = {}
UNIT_CATALOG = []          # (class id, name, tab, price) -- same shape build_unit_shop expects
for _n, _t, _i, _e in UNITS:
    _seq[_t] = _seq.get(_t, 0) + 1
    UNIT_CATALOG.append((_t * 100 + _seq[_t], (_e if USE_REAL_NAMES else _n), _t, _price(_i, _e)))
# user 2026-10-24 13:41: the Factory sells only the BASE unit of each frame (the lowest-influence Mk1 chassis of
# the frame: Imp, Wraith, Sapper, Shade, Ghast, Spirit, Pegasus, Red-Eye/SatCom, Behemoth, Manticore, Triage, Arbalest,
# Hawk, Pelican, Eagle, Roc) plus the Organic / paid units; everything else is reached in the Lab (upgrade_options).
_FRAME_MIN = {}
for _b, (_c, _t, _i, _g) in _BASE_INFO.items():
    _FRAME_MIN[_g] = min(_i, _FRAME_MIN.get(_g, 999))
BASE_UNITS = {_b for _b, (_c, _t, _i, _g) in _BASE_INFO.items() if _i == _FRAME_MIN[_g]}
SHOP_NAMES = {x[1] for x in UNIT_CATALOG if x[1] in BASE_UNITS or x[1] not in _BASE_INFO or x[1] in URA_PRICE}
_TAB = {u[3]: u[1] for u in UNITS}
_INFL = {u[3]: u[2] for u in UNITS}
if USE_REAL_NAMES:                                  # Mk forms must also be in the 0x44 table (Lab results)
    _MK5_ID = {}
    for _a, _c, _b, _uq, _zh in ADVANCED:
        _t = _TAB[_b]
        _k = split_mk(_a)[1]
        if _k > MK_UNIQUE and _b in _MK5_ID:
            _cid = _MK5_ID[_b]                          # Mk6..Mk9: shared id (see MK_UNIQUE)
        else:
            _seq[_t] = _seq.get(_t, 0) + 1
            _cid = _t * 100 + _seq[_t]
            if _k == MK_UNIQUE:
                _MK5_ID[_b] = _cid
        UNIT_CATALOG.append((_cid, _a, _t, _price(_uq, _a)))
        _INFL[_a] = _uq
for _nm, _cd in _ORG_CODE.items():                # organic evolution stages (Lab only, tab 3)
    if _nm not in CODE_OF:
        CODE_OF[_nm] = _cd
        _seq[3] = _seq.get(3, 0) + 1
        UNIT_CATALOG.append((300 + _seq[3], _nm, 3, _price(_ORG_REQ[_nm], _nm)))
        _INFL[_nm] = _ORG_REQ[_nm]
assert all(n <= 99 for n in _seq.values()), f"Factory tab over 99 class ids: {_seq}"

# (16:18) CLASS ID ORDER.  The Lab chassis list has ONE entry per class id, sorted by class id (00449cc0 map per tab):
# the Mk / evolved forms used to get their ids after ALL base chassis (War Pigeon 205, War Pigeon-MK2 228), so an
# upgraded War Pigeon-MK2 sat far below the list and looked lost.  Ids are now given LINE BY LINE: each base, then its
# own Mk forms (Mk6..Mk9 still share the Mk5 id), then the next base; organic lines stage after stage.  Nothing stores
# class ids (accounts keep names; unit_class_id looks them up), the 0x44 table is sent fresh on every request.
def _line_key(name):
    if name in _ORG_CODE or name in _ORG_REQ:
        first = next((f for f in _ORG_FIRST.values() if f == name), None)
        for g, st in _ORG_LINES.items():
            names = [_ORG_FIRST[g]] + [x[0] for x in st[1:]]
            if name in names:
                return (names[0], names.index(name))
        return (name, 0)
    b, k = split_mk(name)
    return (b, k)
_base_order = {}
for _i, (_cid, _nm, _t, _p) in enumerate(UNIT_CATALOG):
    _b = _line_key(_nm)[0]
    _base_order.setdefault(_b, _i)
_new, _seq2, _mk5 = [], {}, {}
for _cid, _nm, _t, _p in sorted(UNIT_CATALOG, key=lambda r: (r[2], _base_order[_line_key(r[1])[0]], _line_key(r[1])[1])):
    _b, _k = _line_key(_nm)
    if _nm not in _ORG_REQ and _k > MK_UNIQUE and _b in _mk5:
        _c2 = _mk5[_b]
    else:
        _seq2[_t] = _seq2.get(_t, 0) + 1
        _c2 = _t * 100 + _seq2[_t]
        if _nm not in _ORG_REQ and _k == MK_UNIQUE:
            _mk5[_b] = _c2
    _new.append((_c2, _nm, _t, _p))
UNIT_CATALOG[:] = _new
assert all(n <= 99 for n in _seq2.values()), f"Factory tab over 99 class ids: {_seq2}"

_FRAME_ROOTS = {_b for _b, (_c, _t, _i, _g) in _BASE_INFO.items() if _i == _FRAME_MIN[_g]}

def upgrade_options(name):
    """one step UP from a unit's current form: the next Mk of its chassis, and the Mk1 of every chassis of the same
    frame that needs more influence.  -> [(target name, influence needed)]"""
    if name in _ORG_NEXT:
        return [_ORG_NEXT[name]]
    b, k = split_mk(name)
    info = _BASE_INFO.get(b)
    if not info:
        return []
    cur = chassis_influence(name)
    out = []
    nxt = (_MK_INFL.get(b) or {}).get(k + 1)
    if nxt is not None and k + 1 <= MK_MAX:
        out.append((mk_name(b, k + 1), nxt))
    # (16:46 / 16:48, user: upgrades follow the branches of a TREE) the frame's base chassis (the one the Factory
    # sells, Mk1) is the root: it may go up its own Mk line OR become any other chassis of the frame; every other
    # chassis and every Mk2+ form only goes up its own Mk line.  Arbalest -> Arbalest-MK2 / Ballista / Trebuchet,
    # Ballista -> Ballista-MK2 only (no Ballista -> Trebuchet), War Pigeon-MK2 -> War Pigeon-MK3 only.
    if k > 1 or b not in _FRAME_ROOTS:
        return out
    for ob, (oc, ot, oi, og) in sorted(_BASE_INFO.items(), key=lambda kv: kv[1][2]):
        if ob != b and og == info[3] and oi > cur and ob not in URA_PRICE:
            out.append((ob, oi))
    return out

UPGRADES = {}                                       # current form -> [(target name, UQ required)]
for _cid, _nm, _t, _p in UNIT_CATALOG:
    _o = upgrade_options(_nm)
    if _o:
        UPGRADES[_nm] = _o


def upgrade_reach(name):
    """every form reachable from `name` by repeated Lab upgrades -> {form: [steps from name]} (BFS, shortest)."""
    seen, todo = {name: []}, [name]
    while todo:
        cur = todo.pop(0)
        for tgt, _uq in UPGRADES.get(cur, []):
            if tgt not in seen:
                seen[tgt] = seen[cur] + [tgt]
                todo.append(tgt)
    return seen


def upgrade_path_cost(cur, path):
    """total resources of a multi-step Lab upgrade cur -> path[0] -> ... -> path[-1]."""
    tot, prev = [0, 0, 0, 0, 0], cur
    for nxt in path:
        tot = [x + y for x, y in zip(tot, upgrade_cost(prev, nxt))]
        prev = nxt
    return tuple(tot)


def migrate_removed_chassis(u):
    """SatCom (removed) -> Red-Eye of the same Mk.  True when the unit changed."""
    ch = u.get("chassis") or ""
    if ch in _REMOVED_CODES:
        u["chassis"] = _REMOVED_CODES[ch]
        return True
    b, k = split_mk(ch)
    if b in REMOVED_CHASSIS:
        u["chassis"] = mk_name(REMOVED_CHASSIS[b], k)
        return True
    return False
MAX_UNITS = 48          # commander [0x471]: unit slots in the division (base; +REINC_UNIT_BONUS per reincarnation)
HERO_UNIT_HARD_CAP = 100   # a hero never owns more than 100 units (user, 2026-10-20)
BATTLE_UNITS_MAX = 12      # units controlled in one battle (Tactics 120 // 20 + 6)
ROSTER_MIN_BASE = 25       # units a hero can own right after (re)birth; client reincarnation check uses 25 + 2 x reincarnations
def roster_cap(cmd):
    """units the hero may OWN: grows linearly with the best branch level from 25 (level 1) to MAX_UNITS (level 60);
    every reincarnation adds REINC_UNIT_BONUS to both ends (branches restart at level 1, so the cap restarts low)."""
    cmd = cmd or {}
    bonus = REINC_UNIT_BONUS * int(cmd.get("reincarnations", 0))
    lv = max([v.get("level", 1) for v in (cmd.get("branches") or {}).values()] or [1])
    lv = max(1, min(PG.UNIT_MAX_LEVEL, lv))
    base = ROSTER_MIN_BASE + (MAX_UNITS - ROSTER_MIN_BASE) * (lv - 1) // (PG.UNIT_MAX_LEVEL - 1)
    return min(HERO_UNIT_HARD_CAP, base + bonus)
# 0x33 sub 1 [u8] = Lab result.  CONFIRMED 2026-10-21 (00573820 case 1: `cmp al,bl(0) ; sete` -> handler arg):
# the client calls its SUCCESS path when the byte is 0 and its FAILURE path otherwise.  Success paths refresh the
# page: unit upgrade 005d5d40(1) (message +0x33c, tree refresh), equip 0052d5e0(1) (inventory refresh).  Before
# this the server sent 1 for success, so every upgrade/equip showed the failure text and nothing was refreshed.
LAB_OK, LAB_FAIL = 0, 1
LAB_TEST_MODE = False   # True = every upgrade needs UQ 1 and costs little (testing); False = real UQ rule
MECH_APT = {}           # account -> Mech Apt, used for the carry weight sent with the unit records
import progression as PG
_NAME_TAB = {name: tab for _cid, name, tab, _p in UNIT_CATALOG}
def unit_branch(chassis):
    """branch key (inf/mob/avi/org) of a roster unit = its Factory tab (class id // 100)."""
    name = DISPLAY.get(chassis, chassis)
    if name not in _NAME_TAB:
        name = next((n for n, c in CODE_OF.items() if c == chassis and n in _NAME_TAB), name)
    return PG.BRANCHES[_NAME_TAB.get(name, 0)]
START_RESOURCES = (5000, 500, 500, 100, 100)   # money, ore, silicon, uranium, sulfur = 0x15 u32 slots 2..6

# official manual unit pages (www.sgalaxy.com/manual_oml U-*.txt, crawled into units_manual.json):
# influence, max weight / space, unit weight, health, armor, speed, view range per unit and Mk level.
try:
    _um = data_json("units_manual.json")
    UNIT_MANUAL = {u["name"].lower(): u["fields"] for u in _um["units"]}
    for _k in list(UNIT_MANUAL):                       # "Imp-Mk2" -> also "imp-mk2" (our ADVANCED names use MK2)
        UNIT_MANUAL.setdefault(_k.replace("-mk", "-mk"), UNIT_MANUAL[_k])
    for _n in ("oizys", "ubik", "manta", "slanth", "poda", "larva"):
        for _suf in ("-prima", "-primus"):
            if _n + _suf in UNIT_MANUAL:
                UNIT_MANUAL.setdefault(_n, UNIT_MANUAL[_n + _suf])
    if "momas-primus" in UNIT_MANUAL:
        UNIT_MANUAL.setdefault("mamos", UNIT_MANUAL["momas-primus"])
except Exception as _e:
    UNIT_MANUAL = {}
    print("units_manual.json:", _e)

def owned_forms(acc):
    """display names of the chassis forms the account owns (Lab chassis list, 16:32)."""
    try:
        _accs, a = get_account(acc)
    except Exception:
        return set()
    return {DISPLAY.get(u.get("chassis"), u.get("chassis")) for u in (a or {}).get("units", [])}

def send_unit_catalog(s, force=False):
    """(16:32, user: the Lab must list only the chassis the player owns) the client builds the Lab's chassis list
    ONLY from the FIRST list of 0x44 (class id + name; read by 00449cc0 / 0044a560 / name->id 005c6390, nothing
    else uses it - the Factory and the units use the 0x68 records of the second list).  So the first list carries only
    the player's own forms; the records stay complete.  Re-sent when the set of owned forms changed: on Lab entry
    (0x33 op 1) and after a Lab upgrade (before the result, so the refreshed tree finds the new form).  Not while the
    Factory is open (a purchase shows up in the Lab at the next Lab visit)."""
    acc = getattr(s, "acc", None)
    own = owned_forms(acc) if acc else None
    if not force and own is not None and getattr(s, "cat_owned", None) == own:
        return False
    s.cat_owned = own
    s.send(build_unit_catalog(own))
    return True

def build_unit_catalog(owned=None):
    """class-A 0x44 (client FUN_005c8ff0 -> CUnitInfoMan), answer to client 0x46 [u16 cached version]:
      u16 n {u16 class id, s8 chassis name}
      u16 n {u8 a, u8 b, u16 class id (+8; /100 = factory tab), s8 chassis name, u16 F1, u16 F2, u16 F3,
             u64, 5 x u16 G1..G5, u8 H, u16 J1, u16 J2}   -> 0x68-byte records looked up by name.
    DIAGNOSTIC values: every unknown field gets a distinct number so the Factory info text
    (influence / weight / space) shows which field is which:
      F1 = Weight, F2 = Space (confirmed), F3 = 103   G1 = XP factor W (11-01), G2..G5 = 12..15   H = 21   J1,J2 = 31,32"""
    first = [r for r in UNIT_CATALOG if owned is None or r[1] in owned]
    d = bytearray([0x44]) + struct.pack(">H", len(first))
    for cid, name, tab, _p in first:
        nb = name.encode('latin-1'); d += struct.pack(">H", cid) + bytes([len(nb)]) + nb
    d += struct.pack(">H", len(UNIT_CATALOG))
    for cid, name, tab, _p in UNIT_CATALOG:
        nb = name.encode('latin-1')
        code = CODE_OF.get(name, name)
        art_type = {'h': 0, 'g': 1, 'a': 2, 'd': 3}[code[0]]
        d += bytes([art_type, int(code[1:]) & 0xff]) + struct.pack(">H", cid) + bytes([len(nb)]) + nb
        # byte a = art TYPE (0 h,1 g,2 a,3 d), byte b = art NUMBER -> "%c%03dst.xpf"/"mo.xpf" (FUN_004c66e0 / FUN_004c4d90)
        mu = UNIT_MANUAL.get(name.lower(), {})
        d += struct.pack(">HHH", int(mu.get("max_weight_kg", 100)), int(mu.get("max_space_l", 100)), 103)
        # G4 = SPEED x10 (14:56: the Lab "upgrade info" showed every target at 1.4 m/s = the diagnostic 14 of G4)
        # G1 = the chassis' XP factor W (record +0x38, client 00550b30: total XP ending level L = W*L(L+1)(2L+1)/60) -
        # the same number the server levels with (progression.UNIT_XP_W; was the diagnostic 11, kept as the value)
        d += struct.pack(">Q", 0) + struct.pack(">5H", PG.UNIT_XP_W, 12, 13, int(round(float(mu.get("speed_m_s") or 1.4) * 10)), 15)
        d += bytes([21]) + struct.pack(">HH", 31, 32)
    return bytes(d)

PRICE = {CODE_OF.get(name, name): price for cid, name, tab, price in UNIT_CATALOG if name in SHOP_NAMES}   # by art code
_PRICE_BY_NAME = {name: price for cid, name, tab, price in UNIT_CATALOG}

def unit_price_of(chassis):
    """price of ANY roster unit (base by art code, Lab forms by name) - repair and sale use it (before, Lab forms
    such as Chimera were sold back for nothing and repaired at a flat placeholder)."""
    return _PRICE_BY_NAME.get(DISPLAY.get(chassis, chassis)) or PRICE.get(CODE_OF.get(chassis, chassis)) or (100, 20, 10, 0, 0)

def upgrade_cost(cur, target):
    """Lab conversion cost (pricing.upgrade_price): half the value difference, at least a quarter of the target."""
    b, _k = split_mk(target)
    info = _BASE_INFO.get(b)
    return PRC.upgrade_price(unit_value_of(cur), unit_value_of(target), chassis_influence(target),
                             frame=info[3] if info else None, branch=info[1] if info else 3)
UNIT_NAME = {u[0]: u[3] for u in UNITS}

# ---- PRICES and RESOURCES: the one place (user 2026-10-28 13:05 "every mechanism with more than one logic") ----------
# Before: the shown unit price (catalogue x mult) and the charged one (PRICE[code] x mult) were two lookups; "half the
# price" for a sale was written out in 6 places (unit sale + shop list, item sale in the Lab, the stock, the slot purge,
# the over-weight purge, the item list); resources were changed by hand in ~30 places.
SELL_DIV = 2                 # everything sells for half its buy price

def unit_buy_price(chassis, mult=1.0):
    """Factory price of a chassis (name or art code) incl. the centre-province discount mult; None = not for sale."""
    p = PRICE.get(CODE_OF.get(chassis, chassis))
    if p is None:
        return None
    return tuple(int(round(v * mult)) for v in p) if mult != 1.0 else tuple(p)

def unit_sell_price(chassis):
    return tuple(v // SELL_DIV for v in unit_price_of(chassis))

def item_sell_price(item_id):
    return tuple(v // SELL_DIV for v in item_price(item_id))

def res_can_pay(a, cost):
    return all(r >= c for r, c in zip(a.setdefault("resources", [0] * 5), cost))

def res_add(a, gain):
    """resources += gain (gain may be shorter; negative entries spend)."""
    res = a.setdefault("resources", [0] * 5)
    for k, v in enumerate(gain):
        if k < len(res):
            res[k] += int(round(v))
    return res

def res_pay(a, cost):
    """pay cost if every resource is enough -> True, else nothing changes -> False."""
    if not res_can_pay(a, cost):
        return False
    res_add(a, [-int(c) for c in cost])
    return True

def build_unit_shop(shop, roster=(), mult=1.0, cmd=None):
    """0x2f '@': u32 shop id, u8 N {u8, u8, u8, s8 chassis, 5 x u32 price}, u8 M own units {u32 id, 5 x u32, 5 x u32}
    The own-unit ids must already exist in the client's roster (0x16).  The two 5 x u32 groups of an own unit are
    guessed as (repair cost, sell price); 0x2f 'B' (client 00484040) updates them later: u32 id, 5 x u32."""
    _acc = {"commander": cmd or {}, "units": list(roster)}
    sale = [x for x in UNIT_CATALOG if x[1] in SHOP_NAMES and (x[1] not in URA_PRICE or unit_unlocked(_acc, x[1]))]
    d = bytearray([0x2F, 0x40]) + struct.pack(">I", shop) + bytes([len(sale)])
    for cid, name, tab, price in sale:
        nb = name.encode('latin-1')
        # (2026-10-24 13:19) record bytes: [u8 ?][u8 YOUR influence -> +0x2a][u8 REQUIRED influence -> +0x2b]
        # (client 00484239 greys the entry out and 00486238 refuses the purchase while +0x2a < +0x2b, message with
        # the required value).  All three were 1 -> every unit showed "influence 1 / required 1".
        try:
            _mine = PG.influence(PG.ensure_commander(cmd), PG.BRANCHES[tab]) if cmd is not None else 255
        except Exception:
            _mine = 255
        _need = _INFL.get(name, 1)
        d += bytes([1, max(0, min(int(_mine), 255)), max(1, min(int(_need), 255)), len(nb)]) + nb \
            + struct.pack(">5I", *(unit_buy_price(name, mult) or tuple(int(round(v * mult)) for v in price)))
    d += bytes([len(roster)])
    for u in roster:
        sell = unit_sell_price(u["chassis"])
        d += struct.pack(">I", u["uid"]) + struct.pack(">5I", *repair_cost(u)) + struct.pack(">5I", *sell)
    return bytes(d)

REPAIR_FACTOR = 0.4        # full repair of a destroyed unit = 40 % of its price (PLACEHOLDER)
def repair_cost(u):
    frac = 1.0 - hp_frac(u)                       # (sgs/unit_hp.py)
    price = unit_price_of(u["chassis"])
    return tuple(int(round(p * REPAIR_FACTOR * frac)) for p in price)

def unit_kind(chassis):
    chassis = CODE_OF.get(chassis, chassis)
    """0x16 unit type (client accepts 1..2) and 0x18 art kind/number from the chassis code."""
    return (2 if chassis[0] == 'a' else 1), {'h': 0, 'g': 1, 'a': 2, 'd': 3}[chassis[0]], int(chassis[1:])

def drop_pending_account(s):
    """the session that registered an account closed before confirming the New-commander screen -> delete it."""
    acc = getattr(s, "reg_acc", None)
    if not acc:
        return
    accs = load_accounts()
    if acc in accs and accs[acc].get("pending") and "commander" not in accs[acc]:
        del accs[acc]
        save_accounts(accs)
        log(f"   account {acc!r} removed: New commander not finished")
    elif acc in accs and accs[acc].get("pending"):
        del accs[acc]
        save_accounts(accs)
        log(f"   account {acc!r} removed: New commander not finished (stub record)")

def drop_all_pending():
    """server start: accounts whose New-commander screen was never confirmed (server stopped meanwhile)."""
    accs = load_accounts()
    gone = [k for k, v in accs.items() if isinstance(v, dict) and v.get("pending")]
    for k in gone:
        del accs[k]
    if gone:
        save_accounts(accs)
        log(f"   removed {len(gone)} unfinished account(s): {gone}")

def get_account(acc):
    accs = load_accounts()
    a = accs.get(acc, {})
    _c = a.get("commander")
    if isinstance(_c, dict) and "nation" not in _c:
        # a commander record made by a READ path (ensure_commander defaults) for an account that never finished the
        # New-commander screen: with the shared account cache it is kept, so give it the defaults the login always used
        # (nation 1, look 1) instead of failing with KeyError 'nation' (zhihue, 2026-10-22 15:37)
        _c.setdefault("nation", 1); _c.setdefault("look", 1)
    a.setdefault("units", [])
    a.setdefault("resources", list(START_RESOURCES))
    return accs, a

# ---- Item database (class-A 0x10, client FUN_00526ed0 -> parser FUN_005266b0, cached as IINF.udf) ----------
# Packet: [0x10][u8 parts total][u8 part index 1..total][u16 BE chunk length][chunk]; chunks are concatenated.
# Data: u16 n, n x item, then u8 a (<= 32), u8 b, b*a x u16 (a 32-wide table, meaning unknown -> 0x0).
# item: s8 name (<= 62), u16 id (+0x45; art = Item-%03d / Item%04d of id % 2000, Item%05d if id > 9999),
#       u16 (+0x47), u8 (+0x49), 5 x u16 (+0x4a..+0x52), u8 type, then by type:
#       1: u16,u16   2: u16,u8   3: u16,u16   4: u16,u16,u16,u8 flags   5: u16,u16   6: u8,u8 flags,u16
#       7 (8 is read as 7): u8,u16   9: u16
# items.json: 2702 items from hlp.dat (InfoTbl names, codes = ids, type guessed from the help text:
# 1 engine/biodrive, 2 storage, 3 computer, 4 weapon, 5 armor, 6 mines/bombs, 7 sensors/misc).
# CONFIRMED on screen: +0x49 u8 = TECH LEVEL, 5 x u16 = WEIGHT, SPACE, COMPLEXITY, ?, ? (Imp with 3 items: 3/6/9).
# Other numbers are DIAGNOSTIC placeholders until their meaning is known.
try:
    ITEMS = data_json("items.json")
except Exception:
    ITEMS = []
# DATA FIXES (2026-10-24 14:25, user: a Falcon weapon with 8 damage / 0.3 s cooldown could only hit when it was
# almost touching).  Surge AK256 Cap (+ Gold) carry Ground Range 0.1 m (= 2 px) in the source table while their Air
# Range and the H- version's Ground Range are 14 m -> obvious typo, ground range set to 14 m like the air range.
ITEM_DATA_FIXES = {678: {"Ground Range": 14}, 10678: {"Ground Range": 14}}
for _it in ITEMS:
    if _it.get("id") in ITEM_DATA_FIXES:
        _it.setdefault("stats", {}).update(ITEM_DATA_FIXES[_it["id"]])
# TREBUCHET SHELLS (2026-10-21).  Names / ids / text from hlp.dat InfoTbl (00719 Astral Ram ... 00870 Astral Flak);
# the original NUMBERS are lost -> PLACEHOLDER stats modelled on Arbalest mortars / Ballista flak.  Slot guess:
# mortar shell = Misc 7137, flak round = Special 8137 (g037's free slots).  Damage comes from the shell, range and
# cooldown from the Astral launcher (unit_weapon).
_TREB_TXT_M = ("Trebuchet Mortar Shells cause area effect damage to enemy ground forces.  This shell must be used "
               "in tandem with an Astral Launcher.")
_TREB_TXT_F = ("Trebuchet Flak rounds do area effect damage to enemy air units. This round must be used in tandem "
               "with an Astral Launcher.")
# (2026-10-24 14:03, user: no original numbers -> design them from the unit's role, unique and reasonable)
# The Trebuchet is the top Flak-rig artillery (influence 50, Arbalest 14 / Ballista 30): the Astral LAUNCHER sets range
# (35-66 m) and cooldown (2 s, X- 3 s); the SHELL sets the damage.  Design: about 1.3-1.6x the damage per second of an
# Arbalest mortar of the same tech level (slower 2 s launcher, bigger hit), paid with energy and weight; it can carry
# a mortar shell (ground) AND a flak round (air) at once - its unique trait.  Each shell has its own role:
#   Ram   TL 2   standard shell, balanced
#   Maul  TL 20  heavy hitter: big damage, heavy and hungry
#   Toss  TL 45  light long-lob shell: less damage, +6 m range, cheap on energy
#   Slam  TL 75  siege shell: the biggest hit, slow to haul (heaviest, most energy), -0 range
#   Jolt  TL 105 high-tech efficient shell: strong, +4 m range, moderate energy, complex
# H- versions: +30 % damage, twice the energy, ~1.8x weight, +4 complexity (like the other H- items).
# "Range Bonus" is added to the launcher's range (unit_weapon).
# (15:42) the Lab lists an item under a tab only if its TYPE fits the tab: as type 9 (ammo) in the Misc / Special
# slots 7137 / 8137 the shells were sent but appeared nowhere -> mortar shells = type 7 (Misc, skill Bombard),
# flak rounds = type 8 (Special, skill Air Bombard); "ammo": True marks them for the combat / price code.
# (16:01) ORIGINAL split, from the client's own help texts (hlp.dat): the seven COUGAR shells (M1 M2 M3 S1 S2 S3 T,
# ids 694 702 711 762 728 776 745) are "Trebuchet Mortar Shells ... enemy ground forces"; the six ASTRAL rounds (Ram
# Maul Flak Toss Slam Jolt, ids 719 736 870 884 892 899) are "Trebuchet Flak rounds ... enemy air units"; the
# launcher "must be used in conjunction with a Mortar Shell and Flak Round".  Before, the Astral rounds were made
# mortar shells and the Cougar shells were missing.  Numbers are still our design (none survive):
#   mortar M1-M3 standard line, S1-S3 siege line (bigger hit, heavy, hungry), T top shell (efficient, +5 m);
#   flak Ram/Maul/Flak/Slam rising damage, Toss long reach (+8 m), Jolt high-tech efficient.
_TREB_MORTAR = (  # id, name, TL, ground damage, energy, weight, space, complexity, range bonus
    (694, "Cougar M1 Shell", 2, 170, 40, 14, 5, 5, 0),
    (702, "Cougar M2 Shell", 20, 205, 50, 18, 6, 6, 0),
    (711, "Cougar M3 Shell", 40, 240, 55, 20, 6, 7, 0),
    (762, "Cougar S1 Shell", 55, 290, 80, 28, 9, 7, 0),
    (728, "Cougar S2 Shell", 70, 320, 90, 30, 9, 8, 0),
    (776, "Cougar S3 Shell", 90, 360, 100, 32, 10, 9, 0),
    (745, "Cougar T Shell", 110, 340, 60, 18, 7, 10, 5),
)
_TREB_FLAK = (    # id, name, TL, air damage, energy, weight, space, complexity, range bonus
    (719, "Astral Ram", 2, 140, 50, 14, 5, 5, 3),
    (736, "Astral Maul", 20, 170, 60, 18, 6, 6, 3),
    (870, "Astral Flak", 40, 195, 70, 20, 6, 6, 5),
    (884, "Astral Toss", 60, 210, 55, 14, 5, 7, 8),
    (892, "Astral Slam", 80, 260, 90, 26, 8, 8, 3),
    (899, "Astral Jolt", 105, 270, 65, 16, 6, 9, 6),
)
_TREB_SHELLS = _TREB_MORTAR        # (kept name: other code / docs refer to it)
for _rows, _slot, _typ, _side, _sp, _txt in ((_TREB_MORTAR, 7137, 7, "Ground", "Bombard", _TREB_TXT_M),
                                             (_TREB_FLAK, 8137, 8, "Air", "Air Bombard", _TREB_TXT_F)):
    for _id, _n, _tl, _dmg, _en, _w, _sp_, _cx, _rb in _rows:
        for _h in (0, 2000):
            _st = {"Tech Level": _tl + (1 if _h else 0), "Complexity": _cx + (4 if _h else 0),
                   "Weight": int(round(_w * (1.8 if _h else 1))), "Space": _sp_,
                   _side + " Damage": int(round(_dmg * (1.3 if _h else 1))), "Energy Use": _en * (2 if _h else 1),
                   "Special": _sp}
            if _rb:
                _st["Range Bonus"] = _rb
            ITEMS.append({"id": _id + _h, "code": "%05d" % (_id + _h), "name": ("H-" if _h else "") + _n,
                          "slot": _slot, "type": _typ, "ammo": True, "page": "Trebuchet Shells", "designed": True,
                          "stats": _st, "desc": _txt + " This is an explosive weapon."})
# DEMON-STAR equipment (Black Tortoise sells fire armour; art "Demon Fire" 5102 / "H-Demon Fire" 7102 exists in the
# client, stats are ours).  Sold by the Lab only while the nation has demon-star time.
# Tech level 119 / 120 (H-): was 125 / 126, above the highest reachable MAX TECH LEVEL (unit level 60 + Education 120/2 =
# 120), so nobody could ever equip them (audit 2026-10-21).
DEMON_ITEMS = [
    {"id": 5102, "code": "05102", "star": "tortoise", "name": "Demon Fire", "slot": 5101, "type": 5, "page": "Mobile Armor", "demon": True,
     "stats": {"Tech Level": 119, "Complexity": 0, "Weight": 28, "Space": 20, "Health": 3000, "Armor": 100},
     "desc": "Demon-star armour of the Black Tortoise (mobile). Armour bonus against: ballistic +50%, missile +50%, flame +200%, laser +50%, armour piercing -50%, explosive +50%. Sold only in the Lab at the centre of the Black Tortoise demon star while your side holds it.", "own_help": True},
    {"id": 7102, "code": "07102", "star": "tortoise", "name": "H-Demon Fire", "slot": 5101, "type": 5, "page": "Mobile Armor", "demon": True,
     "stats": {"Tech Level": 120, "Complexity": 0, "Weight": 60, "Space": 28, "Health": 5400, "Armor": 125},
     "desc": "Demon-star armour of the Black Tortoise (mobile, heavy). Armour bonus against: ballistic +50%, missile +50%, flame +200%, laser +50%, armour piercing -50%, explosive +50%. Sold only in the Lab at the centre of the Black Tortoise demon star while your side holds it.", "own_help": True},
]
# Black Tortoise special equipment (user list 2026-10-21).  Existing items just get the demon flag (sold only on the
# star); items whose art exists in the client but that have no data get placeholder stats.
# 2026-10-21 20:31 (user): Mutated Biodrive / Terminus Biodrive (+ H-) are NORMAL Lab items again (Apparition cloak
# engines); only Mutated Biocase stays demon-star equipment.
# 2026-10-21 20:34 (user): Minor Carpace / Phasic Implant / Tendon Enhancer are normal Lab items again - they are the
# whole manual table 'Organic General Misc', so as demon items the organic units' Misc slot was empty.
ACID_BURA_ID = 8943   # id % 2000 = 943 -> icon Item-943 (organic sac); codes 00943 / 02943 / 04943 are taken in InfoTbl
DEMON_FLAG_IDS = (352, 2352)          # Mutated Biocase / H-                           (TL 100/101)
DEMON_ITEMS += [
    {"id": 1133, "code": "01133", "name": "Alien Flame Tongue", "slot": 4321, "type": 4, "page": "Organic Weapons", "demon": True,
     "stats": {"Tech Level": 40, "Complexity": 0, "Weight": 0, "Air Damage": 90, "Air Range": 12, "Air Cooldown": 1.5},
     "desc": "Alien anti-air weapon: a tongue of flame. This is a flame weapon."},
    {"id": 2923, "code": "02923", "name": "Angel Harness", "slot": 7300, "type": 7, "page": "Organic General Misc", "demon": True,
     "stats": {"Tech Level": 40, "Complexity": 0, "Weight": 0, "Special": "Speed Boost"},
     "desc": "Press B to speed up."},
    # ACID BURA (user list 2026-10-22, "掛掉時爆炸"; not in the 1.8.5 client tables): bursts like Self Destruct when the
    # unit dies - 280 px (14 m), 930 HP.  Icon Item-943 (organic sac), id 8943.  Needs client F21 (004d8c10 HP check removed);
    # the server puts lump 0x30 [uid][25] in front of the unit's death (acid_bura_death).
    {"id": ACID_BURA_ID, "code": "08943", "name": "Acid Bura", "slot": 7300, "type": 7, "page": "Organic General Misc", "demon": True,
     "stats": {"Tech Level": 40, "Complexity": 0, "Weight": 0, "Energy Use": 0, "Special": "Self Destruct", "Effectiveness": 930},
     "desc": "The Acid Bura bursts when its unit dies: every unit within 14 meters loses 930 HP."},
    {"id": 30001, "code": "30001", "name": "Alien Power", "slot": 2000, "type": 2, "page": "Organic Power", "demon": True,
     "stats": {"Tech Level": 40, "Complexity": 0, "Weight": 0, "Max Energy": 8000, "Energy Drain": 0, "Energy Recharge": 60},
     "desc": "Solar powered alien energy store."},
    {"id": 30002, "code": "30002", "name": "Monster Power", "slot": 2000, "type": 2, "page": "Organic Power", "demon": True,
     "stats": {"Tech Level": 40, "Complexity": 0, "Weight": 0, "Max Energy": 12000, "Energy Drain": 0, "Energy Recharge": 20},
     "desc": "Non-solar alien energy store."},
]
# Demon-star armour of the other stars (design claude/DAMAGE_ARMOR_DESIGN.md): Azure Dragon = mechanical armour
# (client art "Dragons Hail" 5045/7045), White Tiger = infantry armour, Vermilion Bird = flying armour (aircraft
# only).  The last two have no client art of their own -> unused armour pictures (Item-830 power suit, Item-838 plate).
DEMON_ITEMS += [
    {"id": 5045, "code": "05045", "star": "azure", "name": "Dragons Hail", "slot": 5101, "type": 5, "page": "Mobile Armor", "demon": True,
     "stats": {"Tech Level": 119, "Complexity": 0, "Weight": 30, "Space": 20, "Health": 3200, "Armor": 110},
     "desc": "Demon-star armour of the Azure Dragon (mobile). Armour bonus against: ballistic +75%, missile +75%, flame +50%, laser +75%, armour piercing -50%, explosive +50%. Sold only in the Lab at the centre of the Azure Dragon demon star while your side holds it.", "own_help": True},
    {"id": 7045, "code": "07045", "star": "azure", "name": "H-Dragons Hail", "slot": 5101, "type": 5, "page": "Mobile Armor", "demon": True,
     "stats": {"Tech Level": 120, "Complexity": 0, "Weight": 62, "Space": 28, "Health": 5600, "Armor": 135},
     "desc": "Demon-star armour of the Azure Dragon (mobile, heavy). Armour bonus against: ballistic +75%, missile +75%, flame +50%, laser +75%, armour piercing -50%, explosive +50%. Sold only in the Lab at the centre of the Azure Dragon demon star while your side holds it.", "own_help": True},
    {"id": 830, "code": "00830", "star": "tiger", "name": "Tiger Shroud", "slot": 5001, "type": 5, "page": "Infantry Armor", "demon": True,
     "stats": {"Tech Level": 119, "Complexity": 0, "Weight": 14, "Space": 0, "Health": 2400, "Armor": 80},
     "desc": "Demon-star armour of the White Tiger (infantry). Armour bonus against: ballistic +75%, missile +50%, flame +75%, laser +75%, armour piercing -50%, explosive +50%. Sold only in the Lab at the centre of the White Tiger demon star while your side holds it.", "own_help": True},
    {"id": 2830, "code": "02830", "star": "tiger", "name": "H-Tiger Shroud", "slot": 5001, "type": 5, "page": "Infantry Armor", "demon": True,
     "stats": {"Tech Level": 120, "Complexity": 0, "Weight": 28, "Space": 0, "Health": 4200, "Armor": 100},
     "desc": "Demon-star armour of the White Tiger (infantry, heavy). Armour bonus against: ballistic +75%, missile +50%, flame +75%, laser +75%, armour piercing -50%, explosive +50%. Sold only in the Lab at the centre of the White Tiger demon star while your side holds it.", "own_help": True},
    {"id": 838, "code": "00838", "star": "vermilion", "name": "Vermilion Plume", "slot": 5101, "type": 5, "page": "Mobile Armor", "demon": True,
     "air_only": True, "stats": {"Tech Level": 119, "Complexity": 0, "Weight": 20, "Space": 16, "Health": 2800, "Armor": 90},
     "desc": "Demon-star armour of the Vermilion Bird (aircraft only). Armour bonus against: ballistic +50%, missile +150%, flame +0%, laser +50%, armour piercing -50%, explosive +150%. Sold only in the Lab at the centre of the Vermilion Bird demon star while your side holds it.", "own_help": True},
    {"id": 2838, "code": "02838", "star": "vermilion", "name": "H-Vermilion Plume", "slot": 5101, "type": 5, "page": "Mobile Armor", "demon": True,
     "air_only": True, "stats": {"Tech Level": 120, "Complexity": 0, "Weight": 42, "Space": 24, "Health": 4900, "Armor": 110},
     "desc": "Demon-star armour of the Vermilion Bird (aircraft only, heavy). Armour bonus against: ballistic +50%, missile +150%, flame +0%, laser +50%, armour piercing -50%, explosive +150%. Sold only in the Lab at the centre of the Vermilion Bird demon star while your side holds it.", "own_help": True},
]
DEMON_PRICE = (20000, 2000, 2000, 0, 500)      # money, ore, silicon, uranium, sulfur (PLACEHOLDER)
for _d in DEMON_ITEMS:
    if not any(i["id"] == _d["id"] for i in ITEMS):
        ITEMS.append(_d)
for _i in ITEMS:
    if _i["id"] == 25800:            # innate engine of the alien chassis (items.json had a weapon text, TL 2)
        _i["stats"].update({"Tech Level": 1, "Complexity": 0, "Weight": 0, "Space": 0, "Energy Drain": 0})
        _i["desc"] = "The innate biodrive of an alien creature.  It is part of the body: always fitted, free, cannot be bought or removed."
for _i in ITEMS:
    if _i["id"] in DEMON_FLAG_IDS:
        _i["demon"] = True
# MANUAL-ONLY ITEMS (2026-10-21): items of the official manual that the 1.8.5 client does not know (Apparition sniper
# rifles, Terminus weapons of Pegasus / Manticore / Owl / Hawk, H-Repair Machine).  Without them Apparition's weapon
# slot 4042 was EMPTY.  Ids are free ids whose id % 2000 picks an existing icon of a similar weapon (Item-NNN.xpf);
# names / help texts for the Lab come from the patched hlp.dat (tools/build_hlp.py).  server/extra_items.json.
try:
    for _x in data_json("extra_items.json"):
        if not any(i["id"] == _x["id"] or i["name"] == _x["name"] for i in ITEMS):
            ITEMS.append(_x)
except Exception as _e:
    print("extra_items.json:", _e)
# QUORG weapons (user 14:58, manual I-G4049 "Razor" claws, read 2026-10-24): the client knows the names / icons (ids
# 966-975, H- 2966-2975 in hlp.dat) but items.json had no slot for them -> Quorg's weapon slot 4049 was empty.
_RAZORS = """Razor Slicer,2,3,32,264,4,2.8,96,43|Razor Dicer,10,3,37,258,4,2.4,99,50|Razor Talon,22,3,27,266,4.5,2.7,99,37|Razor Claw,34,5,30,308,4.2,2.7,105,41|Razor Death Hook,47,4,42,332,4.2,2.2,110,57|Razor Ripper,60,10,33,353,4.5,2.3,113,49|Razor Cleaver,75,7,22,322,4,2,109,32|Razor Shredder,90,10,34,469,4.5,2.3,135,50|Razor Lacerator,105,8,34,570,4.5,2.5,153,49|Razor Sabre,120,10,28,546,4.5,2.2,148,42|H-Razor Slicer,3,15,59,295,4,2,103,89|H-Razor Dicer,11,26,36,328,4,2.4,110,79|H-Razor Talon,23,22,42,343,4.5,2.4,111,78|H-Razor Claw,35,22,51,397,4.2,2.2,123,90|H-Razor Death Hook,48,15,63,372,4.2,1.7,117,95|H-Razor Ripper,61,14,47,343,4.2,1.7,112,72|H-Razor Cleaver,76,24,37,372,4,1.5,118,76|H-Razor Shredder,91,19,50,565,4.5,2,151,83|H-Razor Lacerator,106,17,59,609,4.5,1.7,159,92|H-Razor Sabre,120,21,40,579,4.5,1.7,156,74"""
for _k, _row in enumerate(_RAZORS.split("|")):
    _n, _tl, _cx, _w, _gd, _gr, _gc, _ad, _en = _row.split(",")
    _id = (966 + _k) if _k < 10 else (2966 + _k - 10)
    if _id not in {i["id"] for i in ITEMS}:
        ITEMS.append({"id": _id, "code": "%05d" % _id, "name": _n, "slot": 4049, "type": 4, "page": "Quorg Weapons",
                      "stats": {"Tech Level": int(_tl), "Complexity": int(_cx), "Weight": int(_w), "Space": 0,
                                "Ground Damage": int(_gd), "Ground Range": float(_gr), "Ground Cooldown": float(_gc),
                                "Air Damage": int(_ad), "Air Range": float(_gr), "Air Cooldown": float(_gc),
                                "Energy Use": int(_en)},
                      "desc": "Quorg melee claws. This is a ballistic weapon."})
# (15:28 icon / text audit) every item the client knows (InfoTbl) has its own id = original icon + help; the 39
# manual-only items borrow the icon of a similar item (id % 2000).  Their weapons had NO text, so no damage class (no
# projectile type, no armour table): the class of their own unit's weapon family (manual siblings) is used.
_EXTRA_CLASS = {"Apparition Weapons": "ballistic", "Manticore Weapons": "missile", "Owl Weapons": "missile",
                "Hawk Weapons": "laser", "Pegasus Weapons": "missile"}
for _x in ITEMS:
    if _x.get("type") == 4 and not (_x.get("desc") or "").strip() and _x.get("page") in _EXTRA_CLASS:
        _x["desc"] = "%s (official manual). This is a %s weapon." % (_x["page"][:-1], _EXTRA_CLASS[_x["page"]])
# ids changed so that the icon matches the item -> old ids in saved accounts are rewritten (ensure_loadouts)
ITEM_ID_REMAP = {4187: 2186}     # H-Repair Machine: icon 187 = First-Aid Kit -> 186 = Repair Machine (H- = base + 2000)
# (17:15) ORGANIC SPECIALS of the manual (I-G8306 Oizys line, I-G8317 Manta line), with the client's own ids
# (InfoTbl names; their old help texts do not match -> own text, build_hlp "own_help").  Left out: Angel Harness /
# Alien Flame Tongue (already demon-star items), Acid Burn / Acid Pod / Corrosive Burn ("Alien Acid", effect unknown),
# Air Lob / Org Range Extender (no stats in the manual), Manta Cloak (no client id).
_ORG_SPECIALS = (
    (2976, "Bulwark Wing", 8306, 2, {"Health": 600}, "Oizys wing plating: +600 health."),
    (6924, "Camo Eye", 8317, 2, {"Energy Use": 150, "Special": "Detect", "Effectiveness": 100},
     "Manta eye: detects camouflaged enemy units nearby."),
    (6948, "Infil Eye", 8317, 2, {"Energy Use": 150, "Special": "Detect", "Effectiveness": 10},
     "Manta eye: detects disguised (infiltrating) enemy units nearby."),
    (6928, "Cloak Eye", 8317, 2, {"Energy Use": 150, "Special": "Detect", "Effectiveness": 1},
     "Manta eye: detects cloaked enemy units nearby."),
    (4924, "CamoInfil Eye", 8317, 30, {"Energy Use": 150, "Special": "Detect", "Effectiveness": 110},
     "Manta eye: detects camouflaged and disguised enemy units nearby."),
    (4948, "InfilCloak Eye", 8317, 30, {"Energy Use": 150, "Special": "Detect", "Effectiveness": 11},
     "Manta eye: detects disguised and cloaked enemy units nearby."),
    (4928, "CloakCamo Eye", 8317, 30, {"Energy Use": 150, "Special": "Detect", "Effectiveness": 101},
     "Manta eye: detects cloaked and camouflaged enemy units nearby."),
    (4862, "Super Detector", 8317, 60, {"Energy Use": 150, "Special": "Detect", "Effectiveness": 111},
     "Manta eye: detects all cloaked, camouflaged and disguised enemy units nearby."),
)
for _id, _n, _sl, _tl, _st, _d in _ORG_SPECIALS:
    if _id not in {i["id"] for i in ITEMS}:
        ITEMS.append({"id": _id, "code": "%05d" % _id, "name": _n, "slot": _sl, "type": 8, "page": "Organic Specials",
                      "own_help": True, "stats": dict({"Tech Level": _tl, "Complexity": 0, "Weight": 0}, **_st),
                      "desc": _d})
# GOLD weapons: the client has the names (hlp.dat infotbl: id = base id + 10000) and draws them with the base icon in a
# gold tint (FUN_0050e520), but no stats -> generated from the base weapon.  Only GOLD_ON_SALE ids are sold (test).
GOLD_DAMAGE_MULT = 1.3
GOLD_COOLDOWN_MULT = 0.9
GOLD_ON_SALE = {10054}                      # Gold Autorifle (TEST: shows the gold icon in the Lab)
GOLD_PRICE = (100, 0, 0, 0, 0)              # PLACEHOLDER (user: price varies)
try:
    _gold_base = set(data_json("gold_ids.json"))
except Exception:
    _gold_base = set()
_by = {i["id"]: i for i in ITEMS}
for _b in sorted(_gold_base):
    _it = _by.get(_b)
    if not _it or _it.get("type") != 4 or (_b + 10000) in _by:
        continue
    _st = dict(_it["stats"])
    for _k in ("Ground Damage", "Air Damage"):
        if _k in _st:
            _st[_k] = int(round(_st[_k] * GOLD_DAMAGE_MULT))
    for _k in ("Ground Cooldown", "Air Cooldown"):          # design 2026-10-21: gold = +30 % damage, -10 % cooldown
        if _k in _st:
            _st[_k] = round(_st[_k] * GOLD_COOLDOWN_MULT, 2)
    _g = dict(_it, id=_b + 10000, code="%05d" % (_b + 10000), name="Gold " + _it["name"], stats=_st, gold=True,
              desc=(_it.get("desc") or "") + " Gold edition.")
    ITEMS.append(_g)
# ---- ORGAN ITEMS (user 2026-10-24 21:24: an organic unit showed firepower / armour / range 0 in the Lab) ----------------
# The client computes the Lab values from the EQUIPPED items; the natural weapons / hides (organs.py, manual W-3LL-ttt /
# A-3LL-ttt, 19 tiers) were only added server-side.  Now they are real items fitted automatically (with_alien_engine):
# W-3LL-ttt = the client's own InfoTbl ids / help (W-301-000 = 30100 ... W-309-180 = 30718, ORGAN_BASE), hides A-3LL-ttt
# = the same + 1000 (no client record: own name, no help).  Never sold, never kept in the hero stock, the tier follows the unit level / stage.
import organs as _ORGI
ORGAN_LINE = {4311: 1, 4321: 2, 4331: 3, 4341: 4, 4351: 6, 4361: 8, 4371: 9}     # weapon slot -> page number 30LL
# client InfoTbl codes of the W-3LL-000 records (W-306 = 30500, W-308 = 30600, W-309 = 30700) and their help texts
ORGAN_BASE = {4311: 100, 4321: 200, 4331: 300, 4341: 400, 4351: 500, 4361: 600, 4371: 700}
_ORGAN_DESC = {4311: "This is a flame weapon.  It will do area effect damamge to units on the same plane.",
               4321: "This is a missile weapon.", 4331: "This is a missile weapon.", 4341: "This is a ballistic weapon.",
               4351: "This weapon does armor piercing damage.", 4361: "This is a missile weapon.",
               4371: "This weapon does armor piercing damage."}
ORGAN_IDS = set()
for _ws, _ll in ORGAN_LINE.items():
    for _t in range(19):
        _st = dict(_ORGI.organ_weapon(_ws, _t)); _st.update({"Complexity": 0, "Weight": 0})
        _wid = 30000 + ORGAN_BASE[_ws] + _t
        ITEMS.append({"id": _wid, "code": "%05d" % _wid, "name": "W-3%02d-%03d" % (_ll, _t * 10), "slot": _ws, "type": 4,
                      "stats": _st, "organ": True, "page": "Organic Weapons",
                      "desc": _ORGAN_DESC[_ws]})
        _hp, _ar = _ORGI.organ_hide(_ws, _t)
        _hid = 31000 + ORGAN_BASE[_ws] + _t
        ITEMS.append({"id": _hid, "code": "%05d" % _hid, "name": "A-3%02d-%03d" % (_ll, _t * 10), "slot": _ws + 1000,
                      "type": 5, "stats": {"Tech Level": _ORGI.TL[_t], "Complexity": 0, "Weight": 0, "Health": _hp,
                                           "Armor": _ar}, "organ": True, "page": "Organic Hides",
                      "desc": "The creature's natural hide (tier %d)." % _t})
        ORGAN_IDS.update((_wid, _hid))
ITEM_BY_ID = {i["id"]: i for i in ITEMS}
try:
    UNIT_SLOTS = data_json("unit_slots.json")
except Exception:
    UNIT_SLOTS = {}

CENTER_DISCOUNT = 0.8        # Factory in the captured centre province: units cost 80 %

def center_price_mult(s):
    """2026-10-23 (user option 3): the Factory of the centre province (43) sells units 20 % cheaper to the side that
    owns it - a reason to capture and then keep coming back to the centre."""
    try:
        nation = s.cmd.get("nation", 1)
        c = nation_planet(nation) * 100000 + H_GEAR_CENTER
        if int(getattr(s, "map", 0) or 0) == c and hgear_open(nation):
            return CENTER_DISCOUNT
    except Exception:
        pass
    return 1.0

H_GEAR_CENTER = 404          # col 4 row 4 of every planet = the middle province of the strategic map

def h_item(it):
    return (it.get("name") or "").startswith("H-")

def hgear_open(nation, here=None):
    """2026-10-23 (user: H- gear only after the map-centre province is captured, to give players a reason to go for
    the centre): the H- items are on sale only while the player's side owns the centre province of its planet."""
    try:
        c = nation_planet(nation) * 100000 + H_GEAR_CENTER
        o = province_owner(c)
        return o != 0 and same_side(nation, o)
    except Exception:
        return False

def demon_on_sale(it, star):
    """(2026-10-27 step 2) star = False: no demon-star items; True: all of them; a DEMON_STARS key ("azure" ...): the
    shared demon items plus THAT star's armour (each star's centre Lab sells its own armour)."""
    if not it.get("demon"):
        return True
    if star is True:
        return True
    return bool(star) and it.get("star") in (None, star)

def items_for_unit(unit_name, per_slot=60, star=False, hgear=True):
    """sale list for a unit: items whose slot id is one of the unit's equip.txt slots."""
    code = CODE_OF.get(unit_name, unit_name)
    sl = [sid for sid, _k in UNIT_SLOTS.get(code, [])]
    out = []
    for sid in sl:
        out += sorted([it for it in ITEMS if it.get("slot") == sid and demon_on_sale(it, star)
                     and not never_sold(it) and (hgear or not h_item(it))
                     and (not redcoat_item(it) or redcoat_event_active())
                     and (not it.get("air_only") or code[:1] == "a")
                     and (not it.get("gold") or it["id"] in GOLD_ON_SALE)],
                      key=lambda it: it.get("stats", {}).get("Tech Level", 0))[:per_slot]
    return out
_ITEM_EXTRA = {1: ">HH", 2: ">HB", 3: ">HH", 4: ">HHHB", 5: ">HH", 6: ">BBH", 7: ">BH", 9: ">H"}

ITEM_STATS = {}   # item id -> real stats from guides (server/item_stats.json, applied in family order)
try:
    _st = data_json("item_stats.json")
    for _code, _u in _st.get("units", {}).items():
        _wslot = next((sid for sid, k in UNIT_SLOTS.get(_code, []) if k == "Weapon"), None)
        _fam = [it for it in ITEMS if _wslot and it.get("slot") == _wslot and it["id"] < 2000]
        for _it, _row in zip(_fam, _u.get("weapons", [])):
            ITEM_STATS[_it["id"]] = _row
            for _v in (2000, 4000, 6000):           # H-/A-/AH- variants of the same base item
                if _it["id"] + _v in ITEM_BY_ID and not ITEM_BY_ID[_it["id"] + _v].get("manual_only"):
                    ITEM_STATS[_it["id"] + _v] = _row
except Exception as _e:
    print("item_stats.json:", _e)

def _i(v, mul=1, hi=65535):
    try:
        return max(0, min(hi, int(round(float(v) * mul))))
    except Exception:
        return 0

# ITEM NAMES IN CHINESE (2026-10-22, user): server/item_names_zh.json {"tw": {english: 繁體}, "cn": {...}}; the item
# database (0x10) is built per session language.  hlp_tw / hlp_cn InfoTbl.txt use the same names (the client finds an
# item's help text by its name).
try:
    ITEM_ZH = data_json("item_names_zh.json")
except Exception:
    ITEM_ZH = {"tw": {}, "cn": {}}

# DEMON-STAR ARMOUR TAG (user 2026-10-27 13:00 "魔星的科技裝備沒有顯示是防火還是防雷射"): the Lab list has no armour-type
# column -> the Chinese names in item_names_zh.json carry the tag ("恶魔之火（防火）"), the SAME names as the client's
# hlp InfoTbl (it finds the help text by name); the help texts (desc, own_help -> build_hlp) give the real numbers.
DEMON_ARMOR_TAG = {
    "azure":     ("all-round", "全防", "全防"),               # +75 ballistic / missile / laser, +50 flame / explosive
    "tiger":     ("all-round", "全防", "全防"),               # +75 ballistic / flame / laser, +50 missile / explosive
    "vermilion": ("vs missile+flak", "防飛彈/爆炸", "防飞弹/爆炸"),   # +150 missile / explosive
    "tortoise":  ("vs flame", "防火", "防火"),                 # +200 flame
}

def item_name_bytes(it, s=None):
    lang = getattr(s, "lang", "en") if s is not None else "en"
    enc = getattr(s, "enc", "latin-1") if s is not None else "latin-1"
    name = it["name"]
    if lang == "zh-tw":
        name = ITEM_ZH["tw"].get(name, name)
    elif lang == "zh-cn":
        name = ITEM_ZH["cn"].get(name, name)
    try:
        return name.encode(enc)[:62]
    except Exception:
        return it["name"].encode('latin-1', 'replace')[:62]

def _item_record(it, s=None):
    st = it.get("stats", {})
    nb = item_name_bytes(it, s)
    t = it["type"]
    # common part.  CONFIRMED: +0x49 tech level, 5 x u16 = weight, space, complexity, (4th, 5th unknown)
    # 4th u16 (+0x50) is used by the engine setter -> energy drain / energy use (guess); 5th = 0.
    # 2026-10-21 (Lab labels, item +0x50 / +0x52 SIGNED): 4th = energy use (engines: their Energy Drain - the skill
    # cost of a Booster / Cloak engine goes in the PUT skill list), 5th = ENERGY REGENERATION (storage recharge).
    def _s(v):
        try:
            return max(-32768, min(32767, int(round(float(v or 0)))))
        except Exception:
            return 0
    # CONFIRMED 2026-10-21 (Lab stat view 005281f0): +0x50 of every item except Misc/Special (type 7/8) is summed
    # as "Enrgy Drain kJ/s"; +0x52 is per type: weapon (4) "Weapon Enrgy kJ/use", storage (2) "Enrgy Regen kJ/s",
    # ammo (9) "Ammo Energy Cost kJ/use".  The weapon's per-shot Energy Use was sent in +0x50 -> it showed up as a
    # continuous drain and the per-shot cost as 0.
    drain = max(0.0, float(st.get("Energy Drain", 0) or 0))
    if t in (7, 8):
        energy = drain                                         # Misc/Special: +0x52 = skill "Energy Use" (0051bc10)
    elif t in (4, 9, 1, 2, 3, 6):
        energy = drain
    else:
        energy = st.get("Energy Use", 0) or drain               # armour upkeep (Mantlet)
    regen = {2: st.get("Energy Recharge", 0) if storage_recharge(it)[0] else 0,
             4: st.get("Energy Use", 0), 9: st.get("Energy Use", 0),
             7: st.get("Energy Use", 0), 8: st.get("Energy Use", 0),
             # engines: ABILITY BIT for the Lab 'Ability Icon' column added by SG_debug F12 (no client code reads an
             # engine's +0x52 otherwise; 2026-10-21)
             1: _skill_item_bit(it) or 0}.get(t, 0)
    d = bytes([len(nb)]) + nb + struct.pack(">HHB", it["id"], it["slot"], _i(st.get("Tech Level", 1), hi=255))
    d += struct.pack(">3H2h", _i(st.get("Weight")), _i(st.get("Space")), _i(st.get("Complexity")), _s(energy), _s(regen))
    d += bytes([t])
    # type-specific part (client FUN_005266b0); meanings are guesses from the manual columns
    if t == 1:      # engine / biodrive: health, power
        d += struct.pack(">HH", _i(st.get("Health")), _i(st.get("Power")))
    elif t == 2:    # power supply: max energy, recharge
        # u8 = recharge TYPE (1/2 = regenerates; inferred from the Lab code), not the amount (now the 5th u16)
        # u8 = recharge TYPE, same coding as unit +0x260: 1 solar, 2 gamma / nuclear, 3 battery (pads), 4 methane (vents)
        d += struct.pack(">HB", _i(st.get("Max Energy")), storage_recharge(it)[0])
    elif t == 3:    # computer: max complexity, xp bonus
        d += struct.pack(">HH", _i(st.get("Max Complexity")), _i(st.get("XP Bonus")))
    elif t == 4:    # weapon: damage, range (x10), cooldown (x10), flags bit0 ground / bit1 air
        g = bool(_i(st.get("Ground Damage"))) or ("Ground Range" in st and not _i(st.get("Air Damage")))
        a = bool(_i(st.get("Air Damage"))) or ("Air Range" in st and not _i(st.get("Ground Damage")) and not g)
        pre = "Ground " if _i(st.get("Ground Damage")) or not _i(st.get("Air Damage")) else "Air "
        # CONFIRMED scale from the Lab list: range is sent x20 (300 -> "15 m"), cooldown x100 (30 -> "0.3 s")
        d += struct.pack(">HHHB", _i(st.get(pre + "Damage")), _i(st.get(pre + "Range"), 20), _i(st.get(pre + "Cooldown"), 100),
                         (1 if g else 0) | (2 if a else 0))
    elif t == 5:    # armor: armor, health
        d += struct.pack(">HH", _i(st.get("Health")), _i(st.get("Armor")))     # Endurance, Armor (Lab labels)
    elif t == 6:    # sensor: u8 type (1 directional, 2 omni), u8 flags, u16 SENSOR RANGE (x20 like weapon range)
        omni = "omni" in (it.get("desc") or "").lower() or "omni" in (it.get("name") or "").lower()
        # (15:42) a bonus-slot item that is NOT a sensor (Trebuchet Advanced Cloak Module, Tachyon Scanner, Radar
        # Jammer: no view range) showed "Directional Sensor" -> sensor kind 0
        kind = (2 if omni else 1) if _ist(it, "View Range") > 0 else 0
        d += struct.pack(">BBH", kind, 0, _i(st.get("View Range"), 20))
    elif t in (7, 8):   # misc / special: u8 ABILITY BIT (skill icon, 00428590), u16 effectiveness
        # Trebuchet shells: the EFFECTIVENESS column shows their damage (15:58, was 0); display only
        eff = (st.get("Ground Damage") or st.get("Air Damage")) if it.get("ammo") else st.get("Effectiveness")
        d += struct.pack(">BH", _skill_item_bit(it) or 0, _i(eff))
    elif t == 9:        # AMMO (Trebuchet shells): u16 ammo damage (Lab "Ammo Damage")
        d += struct.pack(">H", _i(st.get("Ground Damage") or st.get("Air Damage")))
    return d

# ---- EQUIPMENT VALIDITY + STOCK LOADOUT (CONFIRMED 2026-10-21, client 005c5d10 / 005c54c0) ---------------------
# The deploy window refuses a unit whose equipment is invalid ("ksEquippingInvalidItem ... Go to the lab and equip it
# properly", unit +0xd4).  Invalid when: NO items at all; no ENGINE (type 1); an item's tech level > unit level +
# Education/2 (00550370); total weight > unit +0x24 / space > unit +0x28 (0x16 record: first two u32); total
# COMPLEXITY > the computer's (type 3) Max Complexity; an item in a slot the chassis does not have / two in one slot.
# Bought units had no items at all -> every unit was invalid.  Units without items now get a STOCK loadout.
# ---- PURCHASE SCENARIOS (2026-10-21) ----------------------------------------------------------------------------
# normal (base / H- / L- / A- / AH- / E- / I-, Trebuchet shells): every Lab, up to the unit's MAX TECH LEVEL
# GOLD: only the ids in GOLD_ON_SALE;  DEMON: only while the nation has demon-star time
# REDCOAT (RedcoatFlame / Shade / Peg / Hawk): the Independence-Day 'Redcoat' event of the US servers -> only while
#   the event runs (1-7 July, or GM /event redcoat on|off|auto)
# NEVER sold: Alien Biodrive (alien part)
REDCOAT_EVENT = None            # None = automatic (1-7 July), True / False = GM override
REDCOAT_PRICE = (5000, 500, 500, 0, 0)       # PLACEHOLDER

def redcoat_event_active():
    if REDCOAT_EVENT is not None:
        return REDCOAT_EVENT
    import datetime as _dt
    t = _dt.date.today()
    return t.month == 7 and t.day <= 7

def redcoat_item(it):
    return (it.get("name") or "").startswith("Redcoat")

def never_sold(it):
    # 2026-10-22 12:40 (user: a creature needs no engine, do not make players fit it): the Alien Biodrive is the
    # INNATE engine of the alien chassis (engine slot 1000: Oizys, Manta, Mamos, Ubik, Slanth, Poda, Larva).  The client
    # refuses a unit without a type-1 item (005c54c0), so it stays an item - but it is fitted automatically, free,
    # always (with_alien_engine), and never offered in the Lab.
    return it.get("id") == ALIEN_ENGINE_ID or bool(it.get("organ"))

ALIEN_ENGINE_ID = 25800

def alien_chassis(u):
    code = CODE_OF.get(DISPLAY.get(u["chassis"], u["chassis"]), u["chassis"])
    return any(sid == 1000 for sid, _k in UNIT_SLOTS.get(code, []))

def with_alien_engine(u, ids):
    """alien chassis: the innate Alien Biodrive is always fitted (whatever the Lab design sent), and (21:24) its natural
    weapon + hide as organ items of the tier of its level / stage (organs.organ_tier)."""
    if not alien_chassis(u):
        return ids
    out = [i for i in ids if ITEM_BY_ID.get(i, {}).get("slot") != 1000 and i not in ORGAN_IDS] + [ALIEN_ENGINE_ID]
    try:
        name = DISPLAY.get(u["chassis"], u["chassis"])
        code = CODE_OF.get(name, u["chassis"])
        ws = next((sid for sid, k in UNIT_SLOTS.get(code, []) if k == "Weapon"), None)
        if ws in ORGAN_LINE:
            t = _ORGI.organ_tier(PG.unit_peak(u), chassis_influence(name))
            out = [i for i in out if ITEM_BY_ID.get(i, {}).get("slot") not in (ws, ws + 1000)]
            out += [30000 + ORGAN_BASE[ws] + t, 31000 + ORGAN_BASE[ws] + t]
    except Exception:
        pass
    return out

def special_item(it):
    """not stock equipment and not in the normal Lab list (Redcoat event items, alien parts)."""
    return redcoat_item(it) or never_sold(it)

STOCK_KINDS = ("Engine", "Storage", "Computer", "Weapon", "Armor", "Ammo")   # Ammo slot = SENSOR

def _ist(it, k):
    return _i(it.get("stats", {}).get(k))

def _itl(it):
    return _i(it.get("stats", {}).get("Tech Level", 1)) or 1

def unit_caps(u, cmd):
    mu = UNIT_MANUAL.get(str(DISPLAY.get(u["chassis"], u["chassis"])).lower(), {})
    mech = PG.attr(cmd, 3)
    return int(int(mu.get("max_weight_kg", 100)) * (1 + mech / 120)), int(mu.get("max_space_l", 100))

def equip_problems(u, cmd, items=None):
    code = CODE_OF.get(DISPLAY.get(u["chassis"], u["chassis"]), u["chassis"])
    ids = u.get("items", []) if items is None else items
    its = [ITEM_BY_ID[i] for i in ids if i in ITEM_BY_ID]
    if not its:
        return ["no items"]
    out = []
    maxtl = PG.unit_peak(u) + PG.attr(cmd, 2) // 2
    wcap, scap = unit_caps(u, cmd)
    if not any(it["type"] == 1 for it in its):
        out.append("no engine")
    if any(_itl(it) > maxtl for it in its):
        out.append(f"tech level > {maxtl}")
    w, sp, cx = (sum(_ist(it, k) for it in its) for k in ("Weight", "Space", "Complexity"))
    comp = [it for it in its if it["type"] == 3]
    mc = _ist(comp[-1], "Max Complexity") if comp else 0
    if w > wcap: out.append(f"weight {w}/{wcap}")
    if sp > scap: out.append(f"space {sp}/{scap}")
    if cx > mc: out.append(f"complexity {cx}/{mc}")
    slots = [sid for sid, _k in UNIT_SLOTS.get(code, [])]
    used = [it["slot"] for it in its]
    if any(sl not in slots for sl in used) or len(used) != len(set(used)):
        out.append("slot")
    return out

def stock_loadout(u, cmd):
    """cheapest valid equipment: engine, storage, computer (+ weapon, armor if they still fit)."""
    code = CODE_OF.get(DISPLAY.get(u["chassis"], u["chassis"]), u["chassis"])
    maxtl = PG.unit_peak(u) + PG.attr(cmd, 2) // 2
    cand = {}
    for sid, kind in UNIT_SLOTS.get(code, []):
        if kind in STOCK_KINDS and kind not in cand:
            # alien chassis (engine slot 1000: Oizys, Manta, Mamos, Ubik ...) have exactly ONE engine, the Alien
            # Biodrive, which is never sold -> it is still their stock engine (user 2026-10-22 10:48: without it
            # the deploy window said "equipped an item it cannot equip" and the Lab "no engine")
            c = [it for it in ITEMS if it.get("slot") == sid and not it.get("gold") and not it.get("demon")
                 and not it.get("air_only") and not (special_item(it) and not (kind == "Engine" and never_sold(it)))
                 and _itl(it) <= maxtl
                 and (kind != "Weapon" or _ist(it, "Ground Damage") + _ist(it, "Air Damage") > 0)
                 and (kind != "Ammo" or (it.get("type") == 6 and _ist(it, "View Range") > 0))]
            c.sort(key=lambda it: (_ist(it, "Weight") + _ist(it, "Space"), _itl(it)))
            cand[kind] = [it["id"] for it in c[:8]]
    first = lambda k: cand.get(k, [None])[:1] if cand.get(k) else [None]
    best = None
    for comp in (cand.get("Computer") or [None]):
        for eng in (cand.get("Engine") or [None])[:4]:
            for sto in (cand.get("Storage") or [None])[:4]:
                base = [i for i in (eng, sto, comp) if i is not None]
                for extra in (("Weapon", "Armor", "Ammo"), ("Weapon", "Ammo"), ("Weapon", "Armor"), ("Weapon",),
                              ("Ammo",), ("Armor",), ()):
                    trial = base + [cand[k][0] for k in extra if cand.get(k)]
                    if not equip_problems(u, cmd, trial):
                        if best is None or len(trial) > len(best):
                            best = trial
                        break
                if best and len(best) >= len(base) + 3:
                    return best
    if best and code == "g037":
        # Trebuchet: the launcher only works with a shell -> cheapest launcher + mortar shell if they still fit
        L = sorted((it for it in ITEMS if it.get("slot") == 4137 and _itl(it) <= maxtl), key=_itl)
        M = sorted((it for it in ITEMS if it.get("slot") == 7137 and it.get("ammo") and _itl(it) <= maxtl), key=_itl)
        if L and M:
            trial = [i for i in best if ITEM_BY_ID[i].get("type") != 4 and not ITEM_BY_ID[i].get("ammo")
                     and ITEM_BY_ID[i].get("slot") != 7137] + [L[0]["id"], M[0]["id"]]
            if not equip_problems(u, cmd, trial):
                best = trial
    if best:
        best = add_stock_skill(u, cmd, best, maxtl)
    return best or []

# role item of the support / specialist chassis in a NEW unit's stock loadout (user 2026-10-24 14:06: skills only
# from equipment - a Triage without a Regen item could not heal any more).  bit -> lowest tech item that fits.
# a011 War Pigeon (15:11, original manual U-a011: "blankets the ground with bombs"; its weapon page I-G4211 does not
# exist, Misc = Afterburner, Specials = the Carpet Bomb series) -> it attacks ONLY with Carpet Bomb (bit 40).
STOCK_SKILL = {"g056": (25,), "g016": (25,), "g023": (20,), "g035": (26,), "g017": (22,), "g001": (8,), "a011": (40,),
               "g059": (60,),     # (17:07) Wight: "overpowers its opponents with its awesome overload ability"
               "g055": (15,)}     # (17:35) Volte: Refuel (Surge Coupler) - the client only lets it refuel allies
                                  # while in Energy production mode (state 55) or installed (00 4dca20)

def add_stock_skill(u, cmd, items, maxtl=None):
    code = CODE_OF.get(DISPLAY.get(u["chassis"], u["chassis"]), u["chassis"])
    if maxtl is None:
        maxtl = PG.unit_peak(u) + PG.attr(cmd, 2) // 2
    slots = {sid for sid, _k in UNIT_SLOTS.get(code, [])}
    for bit in STOCK_SKILL.get(code, ()):
        if any(bit in _skill_item_bits(ITEM_BY_ID.get(i, {})) for i in items):
            continue
        cands = sorted((it for it in ITEMS if it.get("slot") in slots and bit in _skill_item_bits(it)
                        and _itl(it) <= maxtl and not it.get("gold") and not it.get("demon")), key=_itl)
        _kind = {sid: k for sid, k in UNIT_SLOTS.get(code, [])}
        for it in cands[:6]:
            trial = [i for i in items if ITEM_BY_ID.get(i, {}).get("slot") != it["slot"]] + [it["id"]]
            # (17:35) the role item matters more than armour / sensor / misc: a stock Volte was too heavy for its
            # Surge Coupler (weight 109/100) -> drop those (heaviest first) until it fits
            spare = sorted((i for i in trial if _kind.get(ITEM_BY_ID.get(i, {}).get("slot")) in ("Armor", "Ammo", "Misc")
                            and i != it["id"]), key=lambda i: -float(ITEM_BY_ID.get(i, {}).get("stats", {}).get("Weight", 0) or 0))
            while equip_problems(u, cmd, trial) and spare:
                trial.remove(spare.pop(0))
            if any("complexity" in p for p in equip_problems(u, cmd, trial)):
                # a bigger computer (within the tech level) before giving up the weapon
                _cs = [c for c in ITEMS if _kind.get(c.get("slot")) == "Computer" and _itl(c) <= maxtl
                       and not c.get("gold") and not c.get("demon")]
                for c in sorted(_cs, key=lambda c: -float(c.get("stats", {}).get("Max Complexity", 0) or 0)):
                    t2 = [i for i in trial if _kind.get(ITEM_BY_ID.get(i, {}).get("slot")) != "Computer"] + [c["id"]]
                    if not equip_problems(u, cmd, t2):
                        trial = t2
                        break
            if equip_problems(u, cmd, trial):
                trial = [i for i in trial if _kind.get(ITEM_BY_ID.get(i, {}).get("slot")) != "Weapon"]
            if not equip_problems(u, cmd, trial):
                items = trial
                break
    return items

def _res_names(s):
    lang = _mail_lang(s)
    return {"zh-cn": ("金钱", "矿", "硅", "铀", "硫"), "zh-tw": ("金錢", "礦", "矽", "鈾", "硫")}.get(lang, ("Money", "Ore", "Silicon", "Uranium", "Sulfur"))

def drop_foreign_items(u, a, refund=True):
    """remove items whose slot the unit's chassis does not have; refund the sell price (half the buy price)."""
    code = CODE_OF.get(DISPLAY.get(u["chassis"], u["chassis"]), u["chassis"])
    slots = {sid for sid, _k in UNIT_SLOTS.get(code, [])}
    if not slots:
        return []
    keep, drop = [], []
    for i in u.get("items", []):
        (keep if ITEM_BY_ID.get(i, {}).get("slot") in slots else drop).append(i)
    if drop:
        u["items"] = keep
        if refund:
            for i in drop:
                res_add(a, item_sell_price(i))
    return [ITEM_BY_ID.get(i, {}).get("name", i) for i in drop]

def stock_weapons_missing(u, cmd):
    """(user 2026-10-24 23:42/23:44: Arbalest -> Trebuchet in the Lab, then the equipment shop CRASHED the client) the
    upgrade removed the Arbalest gun (no Trebuchet slot for it) and left the Trebuchet with no launcher and no shell.
    A unit without any weapon gets the stock weapon / ammo items of its chassis for its EMPTY slots (free).  -> ids"""
    have = [ITEM_BY_ID[i] for i in u.get("items", []) if i in ITEM_BY_ID]
    if any(it.get("type") == 4 for it in have):
        return []
    used = {it.get("slot") for it in have}
    out = []
    for i in stock_loadout(u, cmd):
        it = ITEM_BY_ID.get(i, {})
        if it.get("type") in (4, 6, 7, 8) and it.get("slot") not in used:
            out.append(i); used.add(it.get("slot"))
    return out

def fit_after_upgrade(u, a, cmd):
    """(user 14:56) a Lab upgrade must leave a valid unit.  Slots are per chassis (Eagle weapon 4208, Condor 4216):
    1. an item whose slot the new chassis lacks moves to the SAME-NAMED item of a free slot of the new chassis
       (no charge); only items with no such twin are removed and refunded half (drop_foreign_items);
    2. a missing engine / storage / computer is filled with the cheapest stock part;
    3. weight / space over the new chassis' limits (Hawk 60 kg -> Falcon 55 kg) -> the heaviest weapons / armour /
       extras come off first (refunded half) until it fits.
    -> (moved names, removed names, added names)"""
    code = CODE_OF.get(DISPLAY.get(u["chassis"], u["chassis"]), u["chassis"])
    slots = {sid for sid, _k in UNIT_SLOTS.get(code, [])}
    if not slots:
        return [], [], []
    moved, keep = [], []
    u["items"] = [i for i in u.get("items", []) if i not in ORGAN_IDS]     # (21:24) organs follow the new form below
    used = {ITEM_BY_ID.get(i, {}).get("slot") for i in u.get("items", []) if ITEM_BY_ID.get(i, {}).get("slot") in slots}
    for i in u.get("items", []):
        it = ITEM_BY_ID.get(i, {})
        if it.get("slot") in slots:
            keep.append(i)
            continue
        twin = next((x for x in ITEMS if x.get("name") == it.get("name") and x.get("slot") in slots
                     and x.get("slot") not in used), None)
        if twin:
            used.add(twin["slot"]); keep.append(twin["id"]); moved.append(it.get("name"))
        else:
            keep.append(i)                                   # dropped (with refund) just below
    u["items"] = keep
    removed = drop_foreign_items(u, a)
    added = []
    have = {ITEM_BY_ID[i].get("type") for i in u["items"] if i in ITEM_BY_ID}
    for i in stock_loadout(u, cmd):
        it = ITEM_BY_ID.get(i, {})
        if it.get("type") in (1, 2, 3) and it.get("type") not in have and it.get("slot") not in \
                {ITEM_BY_ID[k].get("slot") for k in u["items"] if k in ITEM_BY_ID}:
            u["items"].append(i); have.add(it.get("type")); added.append(it.get("name"))
    for i in stock_weapons_missing(u, cmd):             # (23:44) no weapon left -> the new chassis' stock weapon
        u["items"].append(i); added.append(ITEM_BY_ID.get(i, {}).get("name"))
    _sk = add_stock_skill(u, cmd, list(u["items"]))       # the new chassis' role item (War Pigeon: Carpet Bomb ...)
    added += [ITEM_BY_ID[i].get("name") for i in _sk if i not in u["items"]]
    u["items"] = _sk
    wcap, scap = unit_caps(u, cmd)
    res = a.setdefault("resources", [0, 0, 0, 0, 0])
    while True:
        its = [ITEM_BY_ID[i] for i in u["items"] if i in ITEM_BY_ID]
        w = sum(_ist(it, "Weight") for it in its); sp = sum(_ist(it, "Space") for it in its)
        if w <= wcap and sp <= scap:
            break
        cand = [it for it in its if it.get("type") not in (1, 2, 3)]
        if not cand:
            break
        big = max(cand, key=lambda it: (_ist(it, "Weight") if w > wcap else 0) + (_ist(it, "Space") if sp > scap else 0))
        u["items"].remove(big["id"]); removed.append(big.get("name"))
        for k, v in enumerate(item_sell_price(big["id"])):
            res[k] += v
    u["items"] = with_alien_engine(u, u["items"])          # organic: biodrive + the new form's weapon / hide
    return moved, removed, added

def is_default_name(name):
    """True for empty / a chassis' default name (Red-Eye, g002, Red-Eye-Mk2 ...), i.e. not a player's own label."""
    if not name:
        return True
    if not _DEFAULT_NAMES:
        _DEFAULT_NAMES.update(str(k).lower() for k in list(DISPLAY) + list(DISPLAY.values()) + list(CODE_OF)
                              + list(UNIT_MANUAL) + [c[1] for c in UNIT_CATALOG])
    n = str(name).strip().lower()
    return n in _DEFAULT_NAMES

_DEFAULT_NAMES = set()

def dedupe_slots(ids):
    """keep the LAST item of every slot (later = newer)."""
    out, seen = [], set()
    for i in reversed(ids):
        sl = ITEM_BY_ID.get(i, {}).get("slot", ("?", i))
        if sl in seen:
            continue
        seen.add(sl)
        out.append(i)
    return list(reversed(out))

AUDIT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audit.log")

def audit(event, acc, **kw):
    """ANTI-CHEAT audit trail: one JSON line per suspicious / important event in server/audit.log."""
    try:
        rec = {"t": datetime.datetime.now().isoformat(timespec="seconds"), "event": event, "acc": acc}
        rec.update(kw)
        with open(AUDIT_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
    except Exception as e:
        log(f"   audit write failed: {e}")

LAB_LIST_MAX = 16          # one unit has < 16 slots: longer op 3 lists are forged

def lab_design_problems(unit, cmd, old_ids, new_ids, bought, star, hgear=True):
    """ANTI-CHEAT (2026-10-21): server-side check of a Lab design (op 3).  The client checks all of this itself, so
    a failure here means a modified client / forged packet.  Returns a list of reasons (empty = OK).
      - every id must be a known item;  bought items must be on this unit's sale list (slot, gold, demon star,
        Redcoat event, air-only) and within its MAX TECH LEVEL (unit level + Education // 2)
      - the final design: every item in a slot of this chassis, one per slot, tech level <= max
      - weight / space / complexity over the limit -> refused only if the design got WORSE than before (old
        rosters with an over-limit stock loadout must still be editable)."""
    out = []
    disp = DISPLAY.get(unit["chassis"], unit["chassis"])
    unknown = [i for i in new_ids + bought if i not in ITEM_BY_ID]
    if unknown:
        out.append(f"unknown item ids {unknown}")
    sale = {it["id"] for it in items_for_unit(disp, per_slot=10 ** 6, star=star, hgear=hgear)}
    nosale = [i for i in bought if i in ITEM_BY_ID and i not in sale]
    if nosale:
        out.append(f"not on sale for {disp}: {nosale}")
    maxtl = PG.tech_level(cmd, unit)
    hitl = [i for i in new_ids if i in ITEM_BY_ID and _itl(ITEM_BY_ID[i]) > maxtl]
    if hitl:
        out.append(f"tech level > {maxtl}: {hitl}")
    probs = equip_problems(unit, cmd, new_ids) if new_ids else []
    if "slot" in probs:
        out.append("item in a slot this chassis does not have / two items in one slot")
    def tot(ids, k):
        return sum(_ist(ITEM_BY_ID[i], k) for i in ids if i in ITEM_BY_ID)
    wcap, scap = unit_caps(unit, cmd)
    for k, cap in (("Weight", wcap), ("Space", scap)):
        nv, ov = tot(new_ids, k), tot(old_ids, k)
        if nv > cap and nv > ov:
            out.append(f"{k.lower()} {nv}/{cap}")
    comp = [ITEM_BY_ID[i] for i in new_ids if i in ITEM_BY_ID and ITEM_BY_ID[i]["type"] == 3]
    mc = _ist(comp[-1], "Max Complexity") if comp else 0
    ncx = tot(new_ids, "Complexity")
    ocomp = [ITEM_BY_ID[i] for i in old_ids if i in ITEM_BY_ID and ITEM_BY_ID[i]["type"] == 3]
    ocx_over = tot(old_ids, "Complexity") - (_ist(ocomp[-1], "Max Complexity") if ocomp else 0)
    if new_ids and ncx > mc and ncx - mc > ocx_over:
        out.append(f"complexity {ncx}/{mc}")
    return out

def ensure_loadouts(a):
    """give every unit without equipment its stock loadout; returns the number of units changed."""
    cmd = PG.ensure_commander(a.setdefault("commander", {}))
    n = 0
    if any(i in ITEM_ID_REMAP for i in a.get("hero_items", [])):
        a["hero_items"] = [ITEM_ID_REMAP.get(i, i) for i in a["hero_items"]]
        n += 1
    for u in a.get("units", []):
        if migrate_removed_chassis(u):
            n += 1
        if any(i in ITEM_ID_REMAP for i in u.get("items", [])):
            u["items"] = [ITEM_ID_REMAP.get(i, i) for i in u["items"]]
            n += 1
        if u.get("label") and is_default_name(u["label"]) and u["label"] != DISPLAY.get(u["chassis"], u["chassis"]):
            u["label"] = None                       # stale default name from before an upgrade
            n += 1
        if any(redcoat_item(ITEM_BY_ID.get(i, {})) for i in u.get("items", [])):
            keep = [i for i in u["items"] if not redcoat_item(ITEM_BY_ID.get(i, {}))]
            stock = stock_loadout(u, cmd)
            weap = [i for i in stock if ITEM_BY_ID[i].get("type") == 4 and ITEM_BY_ID[i]["slot"] not in
                    {ITEM_BY_ID[k]["slot"] for k in keep if k in ITEM_BY_ID}]
            u["items"] = keep + weap if not equip_problems(u, cmd, keep + weap) else keep
            n += 1
        if u.get("items") and drop_foreign_items(u, a):
            n += 1
        if u.get("items"):
            fixed = dedupe_slots(u["items"])
            if fixed != u["items"]:
                u["items"] = fixed
                n += 1
        if u.get("chassis") in ("g037", "Trebuchet") or str(u.get("chassis", "")).startswith("Trebuchet"):
            # (16:01) Astral rounds moved from Misc 7137 to Special 8137 (they are FLAK) -> keep one flak round,
            # and give a Trebuchet without a mortar shell the cheapest Cougar shell that fits (once)
            if not u.get("shell_mig"):
                u["shell_mig"] = 1
                old = list(u.get("items", []))
                its = [i for i in old if ITEM_BY_ID.get(i, {}).get("slot") not in (7137, 8137)]
                mort = [i for i in old if ITEM_BY_ID.get(i, {}).get("slot") == 7137]
                flak = [i for i in old if ITEM_BY_ID.get(i, {}).get("slot") == 8137]
                cheap = lambda sl: sorted((it["id"] for it in ITEMS if it.get("slot") == sl and it.get("ammo")
                                           and not h_item(it)), key=lambda i: _itl(ITEM_BY_ID[i]))
                for cands in (mort + cheap(7137), flak + cheap(8137)):     # the player's own shell first
                    for c in cands:
                        if not equip_problems(u, cmd, its + [c]):
                            its.append(c); break
                u["items"] = its
                n += 1
        if u.get("items") and not u.get("weapon_mig"):
            u["weapon_mig"] = 1                     # (23:44) units an upgrade left without any weapon (Trebuchet)
            _w = stock_weapons_missing(u, cmd)
            if _w:
                u["items"] = list(u["items"]) + _w
                n += 1
        if u.get("items") and int(u.get("skill_mig") or 0) < 3:
            u["skill_mig"] = 3                      # (10-24) innate skills removed -> give the role item once
                                                    # (2 = 15:11 War Pigeon Carpet Bomb)
            _new = add_stock_skill(u, cmd, list(u["items"]))
            if _new != u["items"]:
                u["items"] = _new
            n += 1
        if not u.get("items"):
            ids = stock_loadout(u, cmd)
            if ids:
                u["items"] = ids
                n += 1
        if alien_chassis(u):
            fixed = with_alien_engine(u, u.get("items") or [])
            if fixed != u.get("items"):
                u["items"] = fixed
                n += 1
    return n

_ITEMDB_CACHE = {}

def build_item_db_packets(chunk=8000, s=None):
    """cached per (language, encoding) for 60 s: building it took ~75 ms per login and stalled the event loop for every
    player when many logged in at once (load test 2026-10-22: 60 logins -> 1.6 s stall)."""
    key = (getattr(s, "lang", "en") if s is not None else "en", getattr(s, "enc", "latin-1") if s is not None else "latin-1",
           chunk, len(ITEMS))
    hit = _ITEMDB_CACHE.get(key)
    if hit and time.time() - hit[0] < 60:
        return hit[1]
    pk = _build_item_db_packets(chunk, s)
    _ITEMDB_CACHE[key] = (time.time(), pk)
    return pk

def _build_item_db_packets(chunk=8000, s=None):
    d = bytearray(struct.pack(">H", len(ITEMS)))
    for it in ITEMS:
        d += _item_record(it, s)
    d += DT.table_bytes()                   # damage class x armour class table (damage_types.py, client 005266b0)
    parts = [bytes(d[i:i + chunk]) for i in range(0, len(d), chunk)]
    return [bytes([0x10, len(parts), k + 1]) + struct.pack(">H", len(c)) + c for k, c in enumerate(parts)]

# ---- Lab ---------------------------------------------------------------------------------------------------
# DIAGNOSTIC item list: real item names from hlp.dat InfoTbl.txt (category 1 = item, code = 5 digits).
# byte1 is set to 0..5 so the screen shows which equip tab (STOCK/CPU/WEAPON/ARMOR/BONUS/MISC) each value means;
# the three u16 are (item number, 102, 103) and the prices 10..50 so their meaning shows on screen.
def lab_sale_items(per_type=3):
    out, cnt = [], {}
    for it in ITEMS:
        if cnt.get(it["type"], 0) < per_type:
            cnt[it["type"]] = cnt.get(it["type"], 0) + 1
            out.append(it)
    return out

def build_lab_items(shop):
    """0x33 sub 0 items for sale: u8 0, u8 a (-> item+0, used as a key), u8, u8, u8, s8 name, 3 x u16, 5 x u32 price.
    Round 3 (item DB now sent): byte a = item type, the first u16 = item id."""
    items = lab_sale_items()
    d = bytearray([0x33, 0]) + struct.pack(">IH", shop, len(items))
    for it in items:
        nb = it["name"].encode('latin-1', 'replace')
        d += bytes([0, it["type"], 1, 1, 1, len(nb)]) + nb + struct.pack(">HHH", it["id"], 1, 1)
        d += struct.pack(">5I", 10, 20, 30, 40, 50)
    return bytes(d)

def item_price(item_id):
    it = ITEM_BY_ID.get(item_id, {})
    if it.get("organ") or item_id == ALIEN_ENGINE_ID:
        return (0, 0, 0, 0, 0)  # (21:24) a creature's own body parts: nothing to buy, sell or refund
    if it.get("gold"):          # Gold: premium version of the item, mostly money (user: price varies) -> 2.5x money
        return PRC.premium(_normal_item_price(it), 2.5)
    if it.get("demon"):         # Demon star: 3x plus sulfur and uranium (rare, only while the nation holds the star)
        return PRC.premium(_normal_item_price(it), 3.0, (0, 0, 0, 20, 100))
    if redcoat_item(it):        # Redcoat (event): 2x
        return PRC.premium(_normal_item_price(it), 2.0)
    return _normal_item_price(it)

_ITEM_PRICES = {}
def _normal_item_price(it):
    """(2026-10-24 14:03) pricing.item_price: tech level, kind, strength against items of the same kind and tech
    level; high tech is paid mostly in resources (manual s6).  Cached per item id."""
    p = _ITEM_PRICES.get(it.get("id"))
    if p is None:
        global _ITEM_PEERS
        if "_ITEM_PEERS" not in globals() or not _ITEM_PEERS:
            _ITEM_PEERS = PRC.build_peer_table(ITEMS)
        try:
            import damage_types as _DT
            dc = _DT.damage_class(it) if it.get("type") in (4, 9) or it.get("ammo") else 0
        except Exception:
            dc = 0
        p = PRC.item_price(it, _ITEM_PEERS, dc)
        _ITEM_PRICES[it.get("id")] = p
    return p

def send_resources(s, a):
    """commander record (0x15) with the account's CURRENT resources.  The Lab never got it after an equip / upgrade,
    so its MONEY / ORE ... column kept the values from when the Lab was opened (2026-10-21 21:09: showed 52513 money
    while the account had 3668 -> a later design was refused 'not enough resources').  Repair already did this."""
    cmd = a.get("commander", {}) or {}
    s.send(build_commander(s.acc, getattr(s, "cmd", {}).get("nation", cmd.get("nation", 1)),
                           cmd.get("attrs", (0, 0, 0, 0)), resources=a["resources"]))

def lab_notice(s, text, a=None):
    """Lab refusal shown to the player as a chat line.  (The Lab itself only puts its generic ksJobFail text in the
    small advisor box.)  NOT class-A 0x31 sub 1: that message box belongs to the STAR CENTER window - sending it in
    the Lab opened the Star Center (2026-10-21 21:08)."""
    s.send(chat_line(0x0A, text, (255, 80, 80)))
    if a is not None:
        send_resources(s, a)

def ITEM_PRICE(tl, heavy=False):
    """item price placeholder (the manual lists no prices): money only, 10 per tech level + 10.
    HEAVY (H- / AH-) versions (user 2026-10-21 20:57): about twice the weight / complexity / energy for +30..150 %
    stats, sold normally like in the original but at double money PLUS ore and silicon."""
    if heavy:
        return (20 * tl + 20, 2 * tl + 5, 2 * tl + 5, 0, 0)
    return (10 * tl + 10, 0, 0, 0, 0)

HERO_STOCK_MAX = 50       # client limit (Lab +0x106c4 = 0x32 - items); the manual mentions 24 slots

def build_set_inventory(uid, item_ids):
    """class-A 0x1F SET_INVENTORY (client FUN_00545d40): u32 unit id, u8 n, n x u16 item id.
    id == commander id -> the hero's own item inventory; otherwise the unit's equipped items (ids must be in the
    item DB).  Unknown unit id -> client logs "SET_INVENTORY on invalid ID"."""
    ids = [i for i in item_ids if i in ITEM_BY_ID][:255]
    return bytes([0x1F]) + struct.pack(">IB", uid, len(ids)) + struct.pack(">%dH" % len(ids), *ids)

def build_lab_item_sale(shop, unit_name, max_tl=255, star=False, hgear=True):
    items = [it for it in items_for_unit(unit_name, star=star, hgear=hgear) if it.get("stats", {}).get("Tech Level", 1) <= max_tl]
    """0x33 sub 3 = ITEMS FOR SALE for the unit on the EQUIP ITEM page (answer to op 7 [s8 unit name]).
    u32 shop, s8 unit name (must equal the unit the page shows), u16 n {u16 item id (looked up in the item
    database, FUN_00526150), u8, 10 x u32 (guess: 5 x buy price, 5 x sell price)}.
    (sub 0 is NOT items: client FUN_00517af0 draws its entries as UNITS with art type/number.)"""
    nb = unit_name.encode('latin-1')
    d = bytearray([0x33, 3]) + struct.pack(">I", shop) + bytes([len(nb)]) + nb + struct.pack(">H", len(items))
    for it in items:
        # u8 after the id must be 0: the page (FUN_0052e2c0) only lists entries with entry+2 == 0, an item that
        # exists in the DB, fits one of the unit's equip.txt slots (FUN_0047d110) and has item+0x49 (tech level)
        # <= the unit's MAX TECH LEVEL.
        buy = item_price(it["id"])                                  # manual has no prices -> placeholder by tech level
        d += struct.pack(">HB", it["id"], 0) + struct.pack(">5I", *buy) + struct.pack(">5I", *item_sell_price(it["id"]))
    return bytes(d)

def _next_mk(name):
    """the next form on the SAME line (Hawk -> Hawk-MK2, Ubik -> Ubik-Amplus), or None."""
    if name in _ORG_NEXT:
        return _ORG_NEXT[name]
    b, k = split_mk(name)
    return next(((t, q) for t, q in UPGRADES.get(name, []) if split_mk(t) == (b, k + 1)), None)

def lab_tree(owned):
    """(16:06, user: the Lab pictures overlapped - once a branch is chosen the others need not be shown) the upgrade
    graph is not a tree (Arbalest -> Ballista -> Trebuchet AND Arbalest -> Trebuchet; several owned forms of one
    frame), and the client drew every repeat on top of each other.  Now a TREE: every owned form lists its direct
    options (minus forms that are already shown elsewhere), and under each option only that option's own Mk line
    (Hawk -> Hawk-MK2 -> ... -> MK9, Owl -> Owl-MK2 ...); no form appears twice.  -> [(form, [(target, UQ)])]"""
    # (16:10, user: a War Pigeon upgraded to MK2 vanished from the Lab, and forms nobody owns - Roc, Owl ... - were
    # listed) -> entries ONLY for the forms the player owns (like before 14:54): every entry name becomes a category
    # of the Lab's chassis list.  Options that the player already owns as another unit are left out (that unit has
    # its own entry), so nothing is drawn twice.
    # (16:41) options are NOT filtered any more: leaving out forms the player already owns (16:06) left e.g. a second
    # War Pigeon without its War Pigeon-MK2 option, or with no option at all -> the client showed "this unit cannot
    # be upgraded on this planet".  Only the deeper chain entries caused overlapping pictures, and they are gone.
    return [(r, list(UPGRADES.get(r, []))) for r in owned]

def build_lab_upgrades(shop, acc):
    """0x33 sub 2: for every base unit the player owns, the advanced forms it can turn into (UPGRADES).
    Outer/inner u8,u8 guessed as art type/number; inner trailing u8 = UQ required (guess); last u8 = 0."""
    _accs, a = get_account(acc)
    owned = []
    for u in a["units"]:
        n = DISPLAY.get(u["chassis"], u["chassis"])
        if n in UPGRADES and n not in owned:
            owned.append(n)
    tree = lab_tree(owned)
    d = bytearray([0x33, 2]) + struct.pack(">IH", shop, len(tree))
    for n, opts in tree:
        _t, at, an = unit_kind(n)
        nb = n.encode('latin-1')
        d += bytes([at, an, len(nb)]) + nb + bytes([len(opts)])
        for tgt, uq in opts:
            _t2, tt, tn = unit_kind(tgt)
            tb = tgt.encode('latin-1')
            if LAB_TEST_MODE:      # let a fresh unit (UNIT QUALITY 3) upgrade so the COMPLETE UPGRADE packet shows
                uq = 1
            d += bytes([tt, tn, len(tb)]) + tb + bytes([uq]) + struct.pack(">5I", *upgrade_cost(n, tgt)) + bytes([0])
    return bytes(d)

def build_commander(name, nation=1, attrs=(0, 0, 0, 0), level=1, max_units=None, resources=START_RESOURCES):
    """server type 0x15: commander info (client parser FUN_00549d30; layout read from the call order, values are placeholders)."""
    try:
        _c = (load_accounts().get(name) or {}).get("commander", {})
    except Exception:
        _c = {}
    reinc = _c.get("reincarnations", 0)
    if max_units is None:
        max_units = roster_cap(_c)       # grows with the best branch level, +2 per reincarnation
    nb = wire_name(name).encode('latin-1')
    d = bytearray([0x15])
    # +8 commander id = the uid of his hero unit: the client recognises its OWN hero by it (with id 1 and hero uid 2
    # the hero was a yellow 'other player' dot that could not be moved, 2026-10-20 17:14)
    d += struct.pack(">III", hero_uid(name), nation, nation)  # +8 id, nation (FUN_004ee830), second faction (FUN_004ee8c0)
    # [0x450] = the commander's PORTRAIT: the client draws "Hero-%02d.xpf" with it (F4 0040e149, battle result, who
    # list).  It was a constant 1 -> every commander had portrait 1 while his body is art H<look> (user 10-31 17:14
    # "the person and the commander portrait do not match").  Same look, same clamp as the body (battle_maps / enter_field).
    try:
        _look = max(1, min(int(_c.get("look", 1) or 1), 11))
    except Exception:
        _look = 1
    d += bytes([_look])                           # [0x450]
    d += struct.pack(">6I", 0, *resources)   # slot1 ?, then money/ore/silicon/uranium/sulfur
    a4 = (list(attrs) + [0, 0, 0, 0])[:4]
    # +0x25 -> [0x470] = DEPLOY LIMIT (CONFIRMED 2026-10-21: read as a byte by the deploy window 005cd100 / 005cd510
    # "max %d units", 004ee300 first free division slot, 004ee680).  It was 1 -> only one unit could be deployed.
    try:
        level = PG.deploy_limit(_c)
    except Exception:
        level = 6
    d += bytes([level & 0xff] + [x & 0xff for x in a4] + [max_units & 0xff])
    # +0x25 -> [0x470] deploy limit, +0x26..+0x29 -> [0x46c..0x46f] (4 attributes?), +0x2a -> [0x471] = MAX UNITS
    # (Factory "UNITS (CUR/MAX)" = sprintf(.., shop[+0x85c], commander[+0x471]) in FUN_004894d0)
    # +0x2b -> [0x474] WINS, +0x2d -> [0x478] losses (parser 00549f95; shown as "%d/%d").  The tutorial's opening step is
    # skipped by the client when the wins are not 0 -> wins_for_client() (tutorial only on the first login)
    try:
        _w, _l = wins_for_client(name), min(int(_c.get("losses", 0) or 0), 65535)
    except Exception:
        _w, _l = 0, 0
    d += struct.pack(">HH", _w, _l)
    # +0x2f -> [0x47c] = COMMANDER LEVEL as the client sees it.  It was a constant 1, so the BOARD / MAIL windows refused
    # every post ("You cannot post ... until you reach level 15", client 00419f48 / 00543c64: level < 15 and
    # reincarnations < 1) even for a level-15 branch (2026-10-26).  Now the best branch level.  (>= 5 also runs 0049e8c0.)
    try:
        _lvl = max([int(v.get("level", 1) or 1) for v in (_c.get("branches") or {}).values()] or [1])
    except Exception:
        _lvl = 1
    d += bytes([max(1, min(_lvl, 255)), 0])       # +0x2f, +0x30
    d += struct.pack(">II", (CAPITALS.get(nation, 600000) // 100000) % 1000, 0)  # [0x480] founding planet, FUN_004edc80
    # [0x44c] = REGIMENT key of the client's directory cache (F4 shows that entry's name as regiment; 0 matched a random
    # commander, 2026-10-22 15:00) -> own regiment id, 0xFFFF = none.  [0x47f] (president flag, 004ee6a0), discarded,
    # [0x47d] = REINCARNATIONS
    try:
        _rid = regiment_id_of(name)
    except Exception:
        _rid = 0xFFFF
    # (2026-10-25) [0x47f] = 1 for the faction's president: the strategic map then lets him give FACTION orders
    # (ASSEMBLE / AVOID scope 1, 004663e0); regiment leaders give regiment orders (scope 2) without it
    try:
        _pres = 1 if str(politics(nation).get("president", "")).lower() == str(name).lower() else 0
    except Exception:
        _pres = 0
    d += struct.pack(">H", _rid) + bytes([_pres, 0, min(reinc, 255)])
    d += bytes([len(nb)]) + nb                    # s8: commander name
    d += bytes([0, 0])                            # [0x4a4], [0x4a5]
    return bytes(d)

def _s8(t):
    b = str(wire_name(t)).encode('latin-1', 'replace')[:250]
    return bytes([len(b)]) + b
