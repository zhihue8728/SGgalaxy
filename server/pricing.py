"""Prices of units, Lab upgrades and items (design 2026-10-24: the original numbers are lost - user 14:03: "build them
from each unit's / item's characteristics and numbers, unique and reasonable").

Pure module (no server state): sgserver passes in the manual / item records.

Resources: (money, ore, silicon, uranium, sulfur).  Value of one unit of each, in money:
    money 1, ore 4, silicon 4, uranium 40, sulfur 8.
Rules from the original manual (www.sgalaxy.com/manual/s6.html):
  * higher-influence chassis cost more to buy and to repair;
  * high-tech items are made one by one -> their cost is mostly RESOURCES; low-tech items are sold off the shelf ->
    mostly MONEY.
Uniqueness: a unit's price comes from its own manual numbers (influence, health, armour, carrying capacity, speed);
an item's from its tech level, its kind and how strong it is compared with items of the same kind and tech level.
"""
import math, re

RATE = (1, 4, 4, 40, 8)          # money value of one money / ore / silicon / uranium / sulfur


def _split(value, money_share, weights):
    """value (in money) -> resource tuple: money_share in money, the rest by weights (ore, si, ura, sulfur)."""
    value = max(1.0, float(value))
    out = [value * money_share, 0.0, 0.0, 0.0, 0.0]
    rest = value - out[0]
    tot = sum(weights) or 1.0
    for k, w in enumerate(weights, start=1):
        out[k] = rest * w / tot / RATE[k]
    # round to friendly numbers: money to 5, resources to 1 (a resource below 1 unit is dropped)
    res = [int(round(out[0] / 5.0)) * 5] + [int(round(v)) for v in out[1:]]
    res[0] = max(res[0], 5)
    return tuple(res)


# ---- UNITS -----------------------------------------------------------------------------------------------------
# resource weights (ore, silicon, uranium, sulfur) by FRAME - what the chassis is built from
FRAME_MIX = {
    # infantry: cyborg / biological soldiers - cheap, money-heavy; science and stealth frames need electronics
    "Geo-frame": (3, 1, 0, 1), "Cyclo-frame": (3, 1, 0, 2), "Sci-frame": (1, 3, 0, 1), "Aero-frame": (2, 2, 0, 1),
    "Gaia-frame": (3, 1, 0, 1), "Ghost-frame": (1, 3, 1, 0), "Magna-frame": (2, 2, 1, 1),
    # mobile: vehicles - ore for hulls, silicon for electronics, sulfur for the artillery rigs
    "Aero-rig": (2, 2, 0, 0), "Gyro-rig": (1, 3, 0, 0), "Geo-rig": (4, 1, 0, 1), "Cyclo-rig": (3, 1, 0, 1),
    "Sci-rig": (1, 3, 1, 0), "Flak-rig": (2, 1, 0, 3),
    # aviation: airframes - silicon for avionics, uranium for the heavy / fast ones
    "Cyclo-raptor": (1, 3, 1, 0), "Geo-raptor": (2, 2, 0, 1), "Gaia-raptor": (2, 2, 1, 1), "Gyro-raptor": (2, 3, 1, 0),
}
BRANCH_MIX = {0: (3, 1, 0, 1), 1: (3, 2, 0, 1), 2: (1, 3, 1, 0), 3: (1, 1, 0, 2)}


def unit_value(influence, health=1500, armor=0, max_weight=80, speed=3.0):
    """money value of a chassis from its manual numbers."""
    return (18.0 * (max(1, influence) + 4) ** 1.3 + 0.05 * health + 8.0 * armor + 0.6 * max_weight
            + 15.0 * max(0.0, speed - 3.0))


def unit_price(influence, health=1500, armor=0, max_weight=80, speed=3.0, frame=None, branch=0):
    v = unit_value(influence, health, armor, max_weight, speed)
    share = min(0.8, max(0.35, 0.8 - influence / 200.0))
    return _split(v, share, FRAME_MIX.get(frame, BRANCH_MIX.get(branch, (3, 1, 0, 1))))


def upgrade_price(cur_value, tgt_value, influence, frame=None, branch=0):
    """Lab conversion: half of the value difference, at least a quarter of the target's value."""
    v = max(0.5 * (tgt_value - cur_value), 0.25 * tgt_value)
    share = min(0.8, max(0.35, 0.8 - influence / 200.0))
    return _split(v, share, FRAME_MIX.get(frame, BRANCH_MIX.get(branch, (3, 1, 0, 1))))


# ---- ITEMS -----------------------------------------------------------------------------------------------------
TYPE_BASE = {1: 2.4, 2: 1.8, 3: 2.6, 4: 2.7, 5: 2.4, 6: 1.6, 7: 2.2, 8: 3.0, 9: 2.0}
TYPE_MIX = {   # (ore, silicon, uranium, sulfur)
    1: (3, 1, 1, 0),      # engines / biodrives
    2: (0, 3, 1, 0),      # energy storage
    3: (0, 4, 0, 0),      # computers
    5: (4, 1, 0, 0),      # armour
    6: (0, 4, 0, 0),      # sensors
    7: (1, 2, 0, 1),      # misc
    8: (0, 2, 2, 0),      # specials (cloak, teleport, shields ...)
    9: (1, 0, 0, 4),      # Trebuchet shells
}
WEAPON_MIX = {   # by damage class (damage_types: 1 ballistic, 2 missile, 3 flame, 4 laser, 5 AP, 6 explosive)
    0: (2, 1, 0, 1), 1: (4, 0, 0, 1), 2: (2, 1, 0, 3), 3: (1, 0, 0, 4), 4: (0, 3, 1, 0), 5: (3, 0, 1, 1),
    6: (1, 0, 0, 4),
}
ARMOR_TECH = re.compile(r"phasic|morganan|tantalum|hafnium|hybrid")


def _f(v):
    try:
        return float(v or 0)
    except Exception:
        return 0.0


def item_strength(it):
    """one number for how strong an item is, comparable within its type."""
    st = it.get("stats", {}) or {}
    t = 9 if it.get("ammo") else it.get("type")
    if t == 4 or t == 9:
        best = 0.0
        for side in ("Ground", "Air"):
            d = _f(st.get(side + " Damage"))
            if d:
                cd = _f(st.get(side + " Cooldown")) or 2.0
                rng = _f(st.get(side + " Range")) or 20.0
                best = max(best, d / cd * (rng / 30.0) ** 0.3)
        both = _f(st.get("Ground Damage")) and _f(st.get("Air Damage"))
        if not best:                                      # Trebuchet launchers: range only
            best = _f(st.get("Ground Range")) * 2.0
        return best * (1.3 if both else 1.0)
    if t == 1:
        return _f(st.get("Health")) + 3.0 * _f(st.get("Power"))
    if t == 2:
        return _f(st.get("Max Energy")) + 5.0 * _f(st.get("Energy Recharge"))
    if t == 3:
        return _f(st.get("Max Complexity")) + 20.0 * _f(st.get("XP Bonus"))
    if t == 5:
        return _f(st.get("Health")) + 30.0 * _f(st.get("Armor"))
    if t == 6:
        return _f(st.get("View Range")) + 3.0 * max(_f(st.get("Ground Range")), _f(st.get("Air Range")))
    return _f(st.get("Effectiveness")) or 1.0


def build_peer_table(items):
    """median strength per (type, special, tech bucket of 20) -> used to rate an item against its peers."""
    groups = {}
    for it in items:
        key = _peer_key(it)
        groups.setdefault(key, []).append(item_strength(it))
    return {k: sorted(v)[len(v) // 2] for k, v in groups.items()}


def _peer_key(it):
    st = it.get("stats", {}) or {}
    tl = int(_f(st.get("Tech Level")) or 1)
    return (9 if it.get("ammo") else it.get("type"), st.get("Special") if it.get("type") in (7, 8) else None, min(tl, 120) // 20)


def item_price(it, peers, damage_class=0):
    st = it.get("stats", {}) or {}
    t = 9 if it.get("ammo") else (it.get("type") or 7)
    tl = int(_f(st.get("Tech Level")) or 1)
    name = (it.get("name") or "")
    v = TYPE_BASE.get(t, 2.0) * (tl + 8) ** 1.35
    med = peers.get(_peer_key(it)) or 0
    s = item_strength(it)
    ratio = (s / med) if med > 0 and s > 0 else 1.0
    v *= min(1.8, max(0.6, ratio)) ** 0.7                 # stronger than its peers -> dearer (and the other way)
    if name.startswith(("H-", "AH-")):
        v *= 1.8
    share = min(0.85, max(0.25, 0.85 - tl / 160.0))
    if t == 4:
        mix = WEAPON_MIX.get(damage_class, WEAPON_MIX[0])
    elif t == 5 and ARMOR_TECH.search(name.lower()):
        mix = (2, 2, 1, 0)
    elif t == 1 and re.search(r"fallout|nuclear|reactor|gamma", name.lower()):
        mix = (1, 1, 3, 0)
    else:
        mix = TYPE_MIX.get(t, (1, 1, 0, 1))
    return _split(v, share, mix)


def premium(price, money_mult=1.0, add=(0, 0, 0, 0, 0)):
    """special shop items (Gold / Demon / Redcoat): a multiple of the normal price plus an extra charge."""
    return tuple(int(round(p * money_mult)) + a for p, a in zip(price, add))
