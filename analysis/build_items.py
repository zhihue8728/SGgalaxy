# Builds server/items.json (item database for class-A 0x10) from the game's own help data.
# Run from the SGgalaxy folder:  python analysis/build_items.py
#
# Sources: analysis/extract/infotbl.txt (InfoTbl.txt from hlp.dat: item names + 5-digit codes = item ids),
#          analysis/extract/hlp_desc.json (help text per code), server/unit_slots.json (equip.txt slots per chassis).
# The game data does NOT say which unit an item belongs to.  The WEAPONS table below groups the base weapons
# (in InfoTbl order the weapons come in families) by the unit whose help text matches them.  It is a best guess:
# edit it when the real assignment is known.  H-/A-/AH- variants (codes 02xxx/04xxx/06xxx) follow their base item.
import json, os, re, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rows = json.load(open(os.path.join(ROOT, "analysis/extract/hlp_desc.json"), encoding="utf-8"))
slots = json.load(open(os.path.join(ROOT, "server/unit_slots.json")))

def slot_of(code, kind):
    for sid, k in slots.get(code, []):
        if k == kind:
            return sid
    return 0

# unit art code -> base weapon ids (InfoTbl families)
WEAPONS = {
    "g004": [507, 458, 456, 508, 457, 454, 509, 455, 523, 520, 510, 521, 511, 524, 522],     # Imp: flamethrowers
    "g001": [75, 78, 74, 79, 73, 80, 77, 81, 76, 573, 575, 576, 578, 577],                   # Daeva: grenade launchers
    "g019": [391, 54, 2, 4, 392, 446, 19, 450, 442, 443, 451, 449, 452, 445],                # Shade: rifles / lasers
    "g018": [396, 1, 398, 60, 393, 447, 394, 61, 448, 397, 17, 399, 395, 444],               # Wraith: long range ballistic
    "g006": [82, 461, 459, 466, 464, 467, 460, 532, 525, 468, 465, 528, 64, 58],             # Spectre: missiles
    "g021": [868, 867, 882, 891, 881, 898, 904, 890, 909, 897, 912, 903, 908, 915],          # Liche: anti-air / anti-IRBM
    "g005": [7, 20, 8, 21, 481, 469, 482, 22, 470, 483, 471, 484, 472, 485, 473],            # Banshee: rapid fire
    "g039": [622, 794, 623, 625, 624, 795, 798, 796, 626, 800, 797, 801, 627],               # Ghast: blades
    "g003": [53, 133, 413, 328, 330, 737, 329, 768, 415, 703, 414, 720, 134],                # Revenant: fists
    "g041": [390, 16, 52, 512, 757, 513, 546],                                               # Spirit
    "g040": [697, 611, 705, 714, 722, 731, 783, 748, 615, 779, 770, 789, 707, 724, 756],     # Phantom: armor piercing
    "g042": [696, 701, 713, 718, 730, 706, 747, 752, 735, 764, 723, 740, 765, 766, 784],     # Apparition: sniper
    "g044": [857, 860, 874, 886, 871, 57, 553, 554, 563, 584, 556, 555, 986],                # Mephit: long range
    "g020": [59, 9, 11, 55, 382, 383, 12, 543, 545, 384, 6, 13, 388, 547],                   # Behemoth: cannons
    "g045": [3, 135, 389, 381, 380, 385],                                                    # Leviathan: lasers
    "g032": [10, 5, 407, 462, 405, 463, 540, 538, 537, 535],                                 # Manticore: AA missiles
    "g010": [62, 514, 136, 495, 515, 137, 493, 516, 496, 519, 494, 518, 517, 497],           # Arbalest: mortars
    "g038": [403, 23, 404, 63, 108, 408, 401, 402, 406, 410, 561, 409, 562],                 # Hydra: AA volleys
    "g008": [708, 710, 725, 727, 742, 744, 759, 761, 773, 775, 786, 788, 790, 792],          # Chimera: air + ground
    "g043": [865, 879, 888, 895, 632, 633, 901, 634, 635],                                   # Gryphon: missiles
    "g009": [99, 559, 560, 631],                                                             # Pegasus
    "g037": [661, 662, 663, 664, 665, 666, 386, 387, 695, 712, 729, 763, 777],               # Trebuchet
    "a004": [66, 56, 367, 100, 368, 486, 86, 487, 87, 488, 529, 539, 533, 531, 65, 18, 369], # Hawk: missiles
    "a008": [138, 544, 113, 370, 139, 569, 564, 570, 571, 583, 572],                         # Eagle: beams
    "a015": [502, 489, 503, 490, 506, 491, 504, 492, 505, 565, 566, 567, 568],               # Phoenix: fire
    "a002": [526, 530, 534, 640, 643, 656, 642, 657, 641, 667, 655, 654, 668, 104],          # Owl: AA missiles
    "a014": [670, 669, 675, 677, 671, 674, 678, 672, 676, 673, 684, 679, 680, 681],          # Falcon: electrical
    "a016": [866, 880, 889, 896, 902, 709, 787, 907, 726, 793, 743, 774, 760, 791],          # Condor
}
WEAPON_OWNER = {i: c for c, lst in WEAPONS.items() for i in lst}

# item text -> (unit art code, slot kind) for special equipment
SPECIAL_RULES = [
    ("arbalest mortar", "g010", "Ammo"), ("ballista flak", "g034", "Ammo"), ("trebuchet mortar", "g037", "Ammo"),
    ("trebuchet flak", "g037", "Ammo"), ("vulture mortar", "a024", "Ammo"), ("astral launcher", "g037", "Misc"),
    ("land mine", "g017", "Special"), ("emp mine", "g017", "Special"), ("heal injured", "g016", "Special"),
    ("repair damaged", "g023", "Special"), ("triage to replenish", "g056", "Special"),
    ("volte to replenish", "g055", "Special"), ("phase allied", "g035", "Special"),
    ("albatross to deploy", "a013", "Special"), ("transport an all", "a001", "Special"),
    ("interregional", "g021", "Special"), ("bombs allow", "a011", "Special"), ("cloak", "g042", "Special"),
    ("camouflage", "g041", "Special"), ("infect an enemy", "g057", "Special"), ("overload", "g059", "Special"),
    ("afterburner", "a004", "Misc"),
]

items = []
for line in open(os.path.join(ROOT, "analysis/extract/infotbl.txt"), encoding="utf-8").read().split("\n"):
    p = line.strip("\r").split("\t")
    if len(p) != 3 or p[0] != "1":
        continue
    code, name = p[2].strip(), p[1]
    iid = int(code)
    if iid > 65535:
        continue
    d = rows.get(code, "")
    dl = d.lower()
    base = iid % 2000 if iid < 8000 else iid
    if "weapon" in dl[:40] and "astral" not in dl:
        t, owner = 4, WEAPON_OWNER.get(base)
        slot = slot_of(owner, "Weapon") if owner else 0
    elif "air engine" in dl:
        t, slot = 1, 1201
    elif "mutant biodrive" in dl or "heart" in name.lower() or "nucleoid" in name.lower() or "biocore" in name.lower():
        t, slot = 1, 1000
    elif "biodrive" in dl:
        t, slot = 1, 1001
    elif "engine" in dl[:30]:
        t, slot = 1, 1101
    elif "storage" in dl:
        t, slot = 2, 2001
    elif "computer" in dl:
        t, slot = 3, 3001
    else:
        t, slot = 7, 0
        for key, unit, kind in SPECIAL_RULES:
            if key in dl:
                t = {"Ammo": 6, "Misc": 7, "Special": 7}[kind]
                slot = slot_of(unit, kind)
                break
        else:
            if "infantry sensor" in dl or "helmet" in dl or "infantry add on" in dl:
                slot = 7000
            elif "mobile sensor" in dl or "artillery sensor" in dl:
                slot = 7100
            elif "armor" in dl or "shield" in dl or "protection" in dl:
                t, slot = 5, (5001 if "infantry" in dl else 5101)
    items.append({"id": iid, "code": code, "name": name[:60], "type": t, "slot": slot, "desc": d[:200]})

seen, out = set(), []
for it in items:
    if it["id"] not in seen:
        seen.add(it["id"]); out.append(it)
json.dump(out, open(os.path.join(ROOT, "server/items.json"), "w", encoding="utf-8"), indent=0, ensure_ascii=False)
c = collections.Counter(it["slot"] for it in out)
print(len(out), "items;", sum(1 for it in out if it["slot"]), "with a slot;", len(c), "different slots")
