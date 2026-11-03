# Builds server/items.json from the OFFICIAL manual tables (www.sgalaxy.com/manual_oml, crawled into
# analysis/manual/weapons.json + items_other.json) and the game's InfoTbl.txt (item name -> id).
# Run from the SGgalaxy folder:  python analysis/build_items2.py
#
# Each manual page is one equip slot (file I-G4004.txt = slot 4004 = Imp weapons), so the slot of every listed
# item is known exactly.  Item type sent to the client = slot // 1000 (1 engine, 2 power supply, 3 computer,
# 4 weapon, 5 armor, 6 sensor, 7 misc, 8 special).
import json, os, re, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = lambda *p: os.path.join(ROOT, *p)
rows_desc = json.load(open(A("analysis/extract/hlp_desc.json"), encoding="utf-8"))

ids = {}
for line in open(A("analysis/extract/infotbl.txt"), encoding="utf-8").read().split("\n"):
    p = line.strip("\r").split("\t")
    if len(p) == 3 and p[0] == "1" and int(p[2]) <= 65535:
        ids.setdefault(p[1].strip().lower(), int(p[2]))

def norm(row):
    out = {}
    for k, v in row.items():
        k2 = re.sub(r"\s*\(.*?\)\s*$", "", k).strip()
        if isinstance(v, str):
            m = re.match(r"^\s*([-\d.]+)", v)
            if m and k2 not in ("Item", "Special"):
                v = float(m.group(1))
        out[k2] = v
    return out

pages = json.load(open(A("analysis/manual/weapons.json"), encoding="utf-8"))["pages"] + \
        json.load(open(A("analysis/manual/items_other.json"), encoding="utf-8"))["pages"]

items, missing, seen = [], [], set()
for pg in pages:
    slot = pg.get("slot")
    if not slot:
        continue
    for r in pg["rows"]:
        r = norm(r)
        name = str(r.get("Item", "")).strip()
        iid = ids.get(name.lower())
        if iid is None:
            missing.append((pg["file"], name))
            continue
        if iid in seen:
            continue
        seen.add(iid)
        items.append({"id": iid, "code": "%05d" % iid, "name": name[:60], "slot": int(slot), "type": int(slot) // 1000,
                      "page": pg.get("title"), "stats": {k: v for k, v in r.items() if k != "Item"},
                      "desc": rows_desc.get("%05d" % iid, "")[:200]})

# Armor is NOT in the client's InfoTbl at all (no names / ids).  Give armor rows unused ids below 1000 (their
# Item-%03d.xpf art exists; which picture shows is unknown).
used = set(ids.values()) | {i["id"] for i in items}
free = (n for n in range(1, 1000) if n not in used)
for f, name in list(missing):
    pg = next(p for p in pages if p["file"] == f)
    if int(pg.get("slot") or 0) // 1000 != 5:
        continue
    r = next(norm(x) for x in pg["rows"] if str(x.get("Item")).strip() == name)
    iid = next(free)
    items.append({"id": iid, "code": "%05d" % iid, "name": name[:60], "slot": int(pg["slot"]), "type": 5,
                  "page": pg.get("title"), "stats": {k: v for k, v in r.items() if k != "Item"}, "desc": "", "new_id": True})
    missing.remove((f, name))

json.dump(items, open(A("server/items.json"), "w", encoding="utf-8"), indent=0, ensure_ascii=False)
print(len(items), "items with manual stats;", len(missing), "manual rows not found in InfoTbl")
print("types:", dict(collections.Counter(i["type"] for i in items)))
if missing:
    print("missing (first 30):", missing[:30])
