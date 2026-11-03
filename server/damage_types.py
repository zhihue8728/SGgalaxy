"""Damage type x armour class table (design: project doc claude/DAMAGE_ARMOR_DESIGN.md, 2026-10-21).

Client rule (004d0420 / 004cb080 / 005261b0, CONFIRMED):
    damage = max(1, weapon damage - armour * (100 + TABLE[target armour class][attacker damage class]) / 100)
    armour class  = PUT stats9[1]  (unit +0x130)
    damage class  = PUT stats9[2] // 100  (stats9[2] = damage CODE, unit +0x120; +0x124 = code // 100 also picks
                    the projectile / hit effect, code % 100 the projectile picture)
The table travels at the end of the item database (0x10): u8 columns, u8 rows, rows x columns s16.
"""
import re

# 2026-10-24 14:30 (user choice A): ARMOR PIERCING really pierces - most armour counts only 10-25 % against it
# (was 25-75 %, and 100 % for an unarmoured aircraft hull).  Rapid-fire AP guns (Falcon: 6-49 per shot every 0.3 s)
# lost almost everything to the per-hit armour subtraction.  Energy fields / demon armour still resist half.
# ---- damage classes (columns) ----------------------------------------------------------------------------------
NONE, BALLISTIC, MISSILE, FLAME, LASER, AP, EXPLOSIVE = range(7)
DAMAGE_NAMES = ["none", "ballistic", "missile", "flame", "laser", "armor piercing", "explosive"]

# 2026-10-24 14:44 armour ROLES (user): every branch has passive armour against each damage type -
#   Infantry (slot 5001): Kevlar = ballistic, Ablative = laser (+ some flame), Hybrid = missile, Morganan = flame + all.
#   Mobile / Aviation (5101): Steel = ballistic, Moly Steel = flame, Zirconium = missile, Impervious Steel / Phasic =
#   laser, Tantalum Carbide = flame (high tier), alien composites = missile + all.
# ---- armour classes (rows) -----------------------------------------------------------------------------------
ROWS = [
    # name                       none  ball  miss  flame laser AP   expl
    ("chassis",                  [0,    0,    0,    0,    0,  -90,    0]),   # 0
    ("ablative",                 [0,  -25,    0,   50,   75,  -90,    0]),   # 1  anti-LASER (+ heat)
    ("kevlar",                   [0,   75,   25,  -25,    0,  -90,    0]),   # 2  anti-BALLISTIC
    ("hybrid",                   [0,   25,   75,    0,   25,  -85,   50]),   # 3  anti-MISSILE
    ("morganan",                 [0,   40,   40,   75,   40,  -75,   40]),   # 4  anti-FLAME, all-round
    ("steel",                    [0,   75,  -25,    0,  -25,  -90,   25]),   # 5
    ("phasic",                   [0,    0,    0,    0,  100,  -85,    0]),   # 6
    ("tantalum carbide",         [0,   25,   25,  100,    0,  -85,    0]),   # 7
    ("alien composite",          [0,   40,   75,   40,   40,  -75,   50]),   # 8  anti-MISSILE, all-round
    ("derma",                    [0,   25,    0,  -50,    0,  -75,  -25]),   # 9
    ("sheathing",                [0,   50,    0,  -25,   25,  -90,    0]),   # 10
    ("husk",                     [0,    0,   75,  -25,    0,  -75,   75]),   # 11
    ("grafted",                  [0,   40,   40,    0,   40,  -75,   40]),   # 12
    ("mantlet defense",          [0,   75,    0,    0,  -25,  -85,   75]),   # 13
    ("mantlet field",            [0,  -25,   25,    0,  100,  -50,    0]),   # 14
    ("mantlet armor",            [0,   50,   50,    0,    0,  -85,   50]),   # 15
    ("aircraft hull",            [0,    0,  -25,    0,    0,  -90,  -25]),   # 16
    ("hafnium flame shield",     [0,    0,    0,  150,    0,  -75,    0]),   # 17
    ("hafnium laser shield",     [0,    0,    0,    0,  150,  -75,    0]),   # 18
    ("hafnium ballistic shield", [0,  150,    0,    0,    0,  -75,    0]),   # 19
    ("hafnium missile shield",   [0,    0,  150,    0,    0,  -75,    0]),   # 20
    ("azure dragon (demon)",     [0,   75,   75,   50,   75,  -50,   50]),   # 21
    ("white tiger (demon)",      [0,   75,   50,   75,   75,  -50,   50]),   # 22
    ("alien carapace",           [0,   25,    0,  -50,  -25,  -75,   25]),   # 23
    ("vermilion bird (demon)",   [0,   50,  150,    0,   50,  -50,  150]),   # 24
    ("black tortoise (demon)",   [0,   50,   50,  200,   50,  -50,   50]),   # 25
    # 2026-10-24 14:44 (user: Mobile / Aviation also need passive anti-flame / anti-missile / anti-laser armour that
    # works without being switched on): three steel families get their own role (mobile + aviation armour slot 5101)
    ("moly steel",               [0,   40,    0,   75,  -25,  -90,    0]),   # 26 anti-FLAME (molybdenum: heat)
    ("zirconium",                [0,   25,   75,  -25,    0,  -90,   25]),   # 27 anti-MISSILE (ceramic)
    ("impervious steel",         [0,    0,    0,    0,   75,  -90,    0]),   # 28 anti-LASER (reflective)
]
ROW_OF = {name: i for i, (name, _v) in enumerate(ROWS)}
CHASSIS, AIRCRAFT, ALIEN = ROW_OF["chassis"], ROW_OF["aircraft hull"], ROW_OF["alien carapace"]

def armour_mod(row, col):
    """TABLE[armour class][damage class] in % (0 when out of range)."""
    try:
        return ROWS[row][1][col] if 0 <= row < len(ROWS) and 0 <= col < len(ROWS[row][1]) else 0
    except Exception:
        return 0

def hit_damage(dmg, armor, row, col):
    """THE hit formula (client 004d0420): max(1, damage - armour * (100 + TABLE[armour class][damage class]) / 100).
    (2026-10-28 "one logic": was written out in battle_rules.hit_damage, battlesim and npc_world.unit_effect.)"""
    return max(1, int(dmg - armor * (100 + armour_mod(row, col)) / 100))

def table_bytes():
    """item-database tail: u8 columns, u8 rows, rows x columns big-endian s16 (client 005266b0)."""
    import struct
    cols = len(ROWS[0][1])
    d = bytes([cols, len(ROWS)])
    for _n, vals in ROWS:
        d += struct.pack(">%dh" % cols, *vals)
    return d

# ---- which row an armour item gives ---------------------------------------------------------------------------
_FAMILY = [
    (r"\bablative\b", "ablative"), (r"\bkevlar\b", "kevlar"), (r"\bhybrid\b", "hybrid"), (r"\bmorganan\b", "morganan"),
    (r"phasic plating", "phasic"), (r"tantalum carbide", "tantalum carbide"),
    (r"kritskonium|tyraloid|lyssaic|haltyrium|podaictantalum", "alien composite"),
    (r"moly steel", "moly steel"), (r"zirconium", "zirconium"), (r"impervious steel", "impervious steel"),
    (r"steel", "steel"),
    (r"\bderma\b", "derma"), (r"\bsheathing\b", "sheathing"), (r"\bhusk\b", "husk"), (r"\bgrafted\b", "grafted"),
    (r"\bdefense\b", "mantlet defense"), (r"\bfield\b", "mantlet field"),
    (r"(parapet|tower|porticullis|rampart) armor", "mantlet armor"),
    (r"dragons hail", "azure dragon (demon)"), (r"tiger shroud", "white tiger (demon)"),
    (r"vermilion plume", "vermilion bird (demon)"), (r"demon fire", "black tortoise (demon)"),
]
_SHIELD = {"flame": "hafnium flame shield", "laser": "hafnium laser shield",
           "ballistic": "hafnium ballistic shield", "missile": "hafnium missile shield"}

def armour_row(items, is_air=False):
    """armour class of a unit from its equipped items (dicts from items.json)."""
    row = None
    for it in items:
        n = it.get("name", "").lower()
        m = re.match(r"(?:h-)?hafnium (flame|laser|ballistic|missile) shield", n)
        if m:
            return ROW_OF[_SHIELD[m.group(1)]]        # a Hafnium shield decides the class
        if it.get("type") == 5 and row is None:
            base = n[2:] if n[:2] in ("h-", "l-") else n
            for pat, fam in _FAMILY:
                if re.search(pat, base):
                    row = ROW_OF[fam]
                    break
    if row is not None:
        return row
    return AIRCRAFT if is_air else CHASSIS

# ---- which column a weapon has ---------------------------------------------------------------------------------
def damage_class(item):
    d = (item.get("desc") or "").lower()
    m = re.search(r"this is an? (ballistic|missile|flame|laser) weapon", d)
    if m:
        return {"ballistic": BALLISTIC, "missile": MISSILE, "flame": FLAME, "laser": LASER}[m.group(1)]
    if "armor piercing" in d:
        return AP
    if "area effect" in d or "mortar" in d or "flak" in d:
        return EXPLOSIVE
    return NONE

# 2026-10-22 12:46 (user: are all attack animations right?): every weapon used picture 1 -> all missiles looked
# alike and every gun drew the same thin grey tracer.  The client (claude/ATTACK_FX.md) draws, per class:
#   1 ballistic: a tracer LINE, code 1 T W: T = colour (0 grey, 1 red/orange, 2 green, 3 blue), W = width 1-9
#   2 missile / 5 armour piercing / 6 explosive: projectile m%03dk.xpf (+ trail m%03df, burst m%03dke)
#   3 flame: ft%03d.xpf;  4 laser: beam + lsp%03d.xpf sparks
# The original per-weapon pictures are unknown -> a stable choice per weapon FAMILY (H- / L- / Gold variants share
# the look), from the pictures that exist in the game data.
# 2026-10-28 00:27 (user: "a laser must be one straight line - the Eagle's Lynx effect is wrong"): the client draws a
# laser (004ce480 -> beam object, mode 0 = 004ec870) as a CHAIN of lsp%03d segments, each segment picked by its
# direction to the target and placed at the end point of the one before.  lsp001.xpf has 16 directions x 8 frames
# (130x129) and makes a straight beam; lsp002.xpf has ONE direction x 13 frames (60x60 spark) - every segment then
# steps the same fixed way and the "beam" runs off at an angle.  Lasers use lsp001 only (was [1, 2]: Lynx Pl / Ph /
# CNuB / AMB ... got 402).
_PICS = {MISSILE: [1, 2, 3, 15, 16, 17, 18, 21, 22, 23, 24, 25, 36], FLAME: [1, 2, 3], LASER: [1],
         AP: [10, 12, 14], EXPLOSIVE: [4, 8, 11]}

def _family(name):
    n = (name or "").lower()
    for pre in ("gold ", "h-", "l-", "a-", "ah-", "e-", "i-"):
        if n.startswith(pre):
            n = n[len(pre):]
    return n

def _stable(n):
    h = 0
    for ch in n:
        h = (h * 131 + ord(ch)) & 0xFFFFFF
    return h

def damage_code(item, picture=None):
    """stats9[2]: class * 100 + picture (see above)."""
    c = damage_class(item) if item else NONE
    if not c:
        return 0
    if picture is not None:
        return c * 100 + picture
    st = item.get("stats", {})
    if c == BALLISTIC:
        dmg = max(float(st.get("Ground Damage", 0) or 0), float(st.get("Air Damage", 0) or 0))
        width = 1 if dmg < 150 else (2 if dmg < 450 else 3)
        colour = 0 if dmg < 150 else 1            # light arms: grey tracer; heavy guns: orange beam
        return 100 + colour * 10 + width
    pics = _PICS.get(c, [1])
    return c * 100 + pics[_stable(_family(item.get("name"))) % len(pics)]
