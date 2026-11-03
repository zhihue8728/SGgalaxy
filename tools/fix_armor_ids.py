#!/usr/bin/env python3
"""Armor is not in the client's InfoTbl, so analysis/build_items2.py gave armor rows arbitrary unused ids - and the
client draws an item's icon from its id (004526fb0: id % 2000 -> Item-%03d.xpf / Item%04d.xpf), so several armors
showed WEAPON pictures (2026-10-21, Mobile Armor = minigun icons 264..299).  This re-numbers armor to the ids of the
armor pictures that exist in tc.dat/tc2.dat and are used by no InfoTbl item (contact sheets out/icons/free_*.png),
H- variant = base + 2000, L- variant = base + 4000 (same picture, like the original H-/A- items), and migrates the
item ids stored in server/accounts.json.  Exact picture per armor is a best guess by look and tech-level order."""
import json, os, shutil
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "server")
ICONS = {
    "Infantry Armor": {"Ablative": [24, 25, 26, 27, 28], "Kevlar": [29, 30, 31, 32, 33], "Hybrid": [34, 35, 36, 37, 38],
                       "Morganan": [308, 309, 310]},
    "Super Armors": {"Derma": [987, 988, 989, 990, 991], "Sheathing": [992, 993, 994, 995, 996],
                     "Husk": [1037, 1038, 1039, 1040, 1041], "Grafted": [1033, 1034, 1035]},
    "Mobile Armor": [39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 318, 319, 320, 321, 322],
    "Mantlet Armor": [802, 803, 804, 806, 807, 808, 809, 810, 812, 813, 815, 816],
}
GRADES = ["Minimal", "Minimum", "Light", "Standard", "Heavy", "Ultimate"]
items = json.load(open(os.path.join(R, "items.json"), encoding="utf-8"))
armor = [x for x in items if x.get("new_id") or "old_id" in x]
for x in armor:
    x.setdefault("old_id", x["id"])
def base_name(n):
    return n[2:] if n[:2] in ("H-", "L-") else n
def variant(n):
    return {"H-": 2000, "L-": 4000}.get(n[:2], 0)
newid = {}
for page, spec in ICONS.items():
    rows = [x for x in armor if x["page"] == page]
    bases = sorted({base_name(x["name"]) for x in rows},
                   key=lambda n: min(x["stats"].get("Tech Level", 0) for x in rows if base_name(x["name"]) == n))
    if isinstance(spec, list):
        icon = dict(zip(bases, spec))
    else:
        icon = {}
        for fam, nums in spec.items():
            fb = [b for b in bases if fam in b.split()]
            fb.sort(key=lambda b: next((GRADES.index(w) for w in b.split() if w in GRADES), 9))
            icon.update(zip(fb, nums))
    for x in rows:
        b = base_name(x["name"])
        assert b in icon, (page, b)
        newid[x["old_id"]] = icon[b] + variant(x["name"])
others = {x["id"] for x in items if x not in armor}
clash = [v for v in newid.values() if v in others]
assert not clash, clash
assert len(set(newid.values())) == len(newid), "duplicate new ids"
for x in armor:
    x["id"] = newid[x["old_id"]]; x["code"] = "%05d" % x["id"]
shutil.copy(os.path.join(R, "items.json"), os.path.join(R, "items.json.before_armor_ids"))
json.dump(items, open(os.path.join(R, "items.json"), "w", encoding="utf-8"), indent=0, ensure_ascii=False)
# accounts: unit item lists / any int list under "items" or "inventory"
ap = os.path.join(R, "accounts.json")
acc = json.load(open(ap, encoding="utf-8"))
shutil.copy(ap, ap + ".before_armor_ids")
n = 0
def fix(o):
    global n
    if isinstance(o, dict):
        for k, v in o.items():
            if k in ("items", "inventory", "hero_items", "stash") and isinstance(v, list):
                new = []
                for i in v:
                    if isinstance(i, int) and i in newid:
                        new.append(newid[i]); n += 1
                    else:
                        new.append(i)
                o[k] = new
            else:
                fix(v)
    elif isinstance(o, list):
        for v in o:
            fix(v)
fix(acc)
json.dump(acc, open(ap, "w", encoding="utf-8"), ensure_ascii=False)
print(len(newid), "armor ids renumbered;", n, "stored item ids migrated")
for o, v in list(newid.items())[:8]:
    print(o, "->", v)
