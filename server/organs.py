"""ORGANIC units' natural weapons and hides (user 2026-10-24 14:58: check organic influence and equipment).

Source: the official manual (www.sgalaxy.com/manual_oml I-G43x1.txt weapons, I-G53x1.txt armour, read 2026-10-24).
Every organic line has ONE weapon page and one armour page with 19 "(rare)" tiers named W-3LL-000 .. W-3LL-180 /
A-3LL-000 .. 180 (LL = line).  They are never sold; the 1.8.5 client has no item records for them -> here they are
the creature's own body parts: the server picks the tier (organ_tier) and adds it to the unit's combat values.
Tier rule (design - the original rule is not in the manual): tier = unit level 1..60 mapped onto 0..18, at least the
evolution stage's UQ // 10 (an evolved Tyr-Primus, UQ 40, starts at tier 4).
"""
TL = [1, 1, 1, 1, 1, 1, 1, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120]

# weapon slot -> (line, ground damage x19 or None, ground range m, ground cooldown s, air damage x19 or None, air range, air cd)
WEAPONS = {
    4311: ("Xeno-ignus (Oizys)",
           [90, 92, 95, 99, 102, 105, 110, 114, 120, 126, 132, 140, 147, 159, 176, 195, 222, 249, 273], 10, 1.0, None, 0, 0),
    4321: ("Xeno-ventus (Ubik)",
           [121, 126, 135, 141, 153, 168, 180, 199, 222, 243, 273, 301, 334, 375, 418, 465, 522, 582, 645], 16.5, 2.5,
           [123, 126, 135, 141, 153, 168, 180, 199, 222, 243, 273, 301, 334, 375, 418, 465, 522, 582, 645], 16.5, 2.5),
    4331: ("Xeno-humus (Slanth)",
           [139, 145, 153, 162, 173, 186, 200, 216, 233, 252, 273, 295, 320, 345, 373, 402, 433, 466, 500], 35, 2.3, None, 0, 0),
    4341: ("Xeno-motus (Poda)",
           [153, 159, 168, 179, 191, 206, 222, 240, 261, 282, 306, 332, 360, 390, 423, 456, 492, 531, 570], 4.5, 2.0, None, 0, 0),
    4351: ("Xeno-frigus (Manta)",
           [75, 76, 78, 79, 80, 82, 84, 85, 87, 89, 91, 93, 94, 96, 98, 99, 101, 102, 104], 15, 3.0, None, 0, 0),
    4361: ("Xeno-hoverus (Mamos)", None, 0, 0,
           [123, 126, 132, 140, 149, 158, 170, 182, 195, 210, 225, 243, 263, 282, 305, 327, 351, 377, 402], 30, 3.5),
    4371: ("Xeno-scavus (Larva)",
           [111, 115, 120, 126, 133, 141, 150, 161, 172, 185, 198, 213, 228, 245, 263, 282, 302, 323, 345], 4.2, 1.5, None, 0, 0),
}
_ARM = [0, 0, 2, 3, 3, 5, 6, 6, 8, 9, 9, 11, 12, 12, 14, 15, 15, 17, 18]          # same armour column on every page
_HP_A = [816, 1128, 1464, 1800, 2160, 2496, 2832, 3192, 3528, 3888, 4224, 4560, 4896, 5232, 5568, 5904, 6216, 6528, 6864]
HIDES = {   # weapon slot of the line -> health x19 (armour = _ARM)
    4311: [408, 564, 732, 900, 1080, 1248, 1416, 1596, 1764, 1944, 2112, 2280, 2448, 2616, 2784, 2952, 3108, 3264, 3432],  # A-301
    4321: _HP_A,                                                                                                         # A-302
    4331: [1020, 1410, 1830, 2250, 2700, 3120, 3540, 3990, 4410, 4860, 5280, 5700, 6120, 6540, 6960, 7380, 7770, 8160, 8580],  # A-303
    4341: [1060, 1466, 1903, 2340, 2808, 3244, 3681, 4149, 4586, 5054, 5491, 5928, 6364, 6801, 7238, 7675, 8080, 8486, 8923],  # A-304
    4351: [918, 1269, 1647, 2025, 2430, 2808, 3186, 3591, 3969, 4374, 4752, 5130, 5508, 5886, 6264, 6642, 6993, 7344, 7722],  # A-306
    4361: _HP_A,                                                                                                         # A-308
    4371: _HP_A,                                                                                                         # A-309
}
# Specials of the lines (manual I-G83xx, TL 2 unless noted) - for reference, not wired yet:
#   8306 Oizys: Angel Harness (Speed Boost), Bulwark Wing (+600 HP), Acid Burn (Alien Acid 15), Alien Flame Tongue
#   8315 Slanth: Air Lob, Org Range Extender (60);  8324 Poda: Acid Pod (15), Corrosive Burn (25, -900 HP)
#   8317 Manta: Camo / Infil / Cloak Eye (Detect), the TL 30 pairs, Super Detector (TL 60), Manta Cloak
#   storage 2000: Alien Power (TL 0, 10000 kJ, +50);  computer 3000: Alien Mark III (TL 1, max complexity 25)


def organ_tier(level, stage_uq=0):
    lv = max(1, min(60, int(level or 1)))
    return max(0, min(18, max((lv - 1) * 18 // 59, int(stage_uq or 0) // 10)))


def organ_weapon(weapon_slot, tier):
    """manual stats of the creature's natural weapon (items.json stat names), or None."""
    w = WEAPONS.get(weapon_slot)
    if not w:
        return None
    _n, gd, gr, gc, ad, ar, ac = w
    st = {"Tech Level": TL[tier]}
    if gd:
        st.update({"Ground Damage": gd[tier], "Ground Range": gr, "Ground Cooldown": gc})
    if ad:
        st.update({"Air Damage": ad[tier], "Air Range": ar, "Air Cooldown": ac})
    return st


def organ_hide(weapon_slot, tier):
    """(health, armour) of the creature's natural hide."""
    hp = HIDES.get(weapon_slot)
    return (hp[tier], _ARM[tier]) if hp else (0, 0)
