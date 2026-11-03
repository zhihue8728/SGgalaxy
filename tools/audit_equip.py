#!/usr/bin/env python3
"""Equipment / skill audit per chassis and planet tier (2026-10-21).  Writes out/equip_audit.tsv + prints a summary."""
import os, sys, collections, json
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "server")); os.chdir(os.path.join(ROOT, "server"))
import sgserver as S, progression as PG
EDU_MAX = 120
TIER_LV = {1: S.XP_LEVEL_CAP[1], 2: S.XP_LEVEL_CAP[2], 3: PG.UNIT_MAX_LEVEL}
REQUIRED = ("Engine", "Storage", "Computer")
SIM = {21: "server", 48: "server", 46: "server", 25: "server", 29: "server", 3: "server", 4: "server", 40: "server"}
names = {}
for ln in open(os.path.join(ROOT, "analysis/extract/infotbl.txt"), encoding="latin-1"):
    f = ln.rstrip("\r\n").split("\t")
    if len(f) >= 3: names[f[2]] = f[1]
units = json.load(open("units_manual.json"))["units"]
cat = {u["fields"]["chassis_code"]: u for u in units if "-mk" not in u["name"].lower()}
rows, issues = [], collections.defaultdict(list)
for code, slots in sorted(S.UNIT_SLOTS.items()):
    u = cat.get(code)
    if not u: continue
    nm, cls = u["name"], u["fields"]["category"]
    organic = cls == "Organic"
    for sid, kind in slots:
        its = [it for it in S.ITEMS if it.get("slot") == sid and not it.get("gold") and not S.never_sold(it)]
        tls = sorted(int(it["stats"].get("Tech Level", 1) or 1) for it in its)
        sk = sorted({S.SPECIAL_BITS.get(it["stats"].get("Special"), None) and it["stats"].get("Special") for it in its} - {None, False})
        line = {"code": code, "unit": nm, "class": cls, "slot": sid, "kind": kind, "items": len(its),
                "min_tl": tls[0] if tls else "", "max_tl": tls[-1] if tls else "", "skills": ",".join(sk)}
        for t, lv in TIER_LV.items():
            line[f"tier{t}"] = sum(1 for x in tls if x <= lv + EDU_MAX // 2)
        rows.append(line)
        if organic: continue
        if not its:
            issues["empty slot"].append(f"{nm} ({code}) {kind} {sid}")
        elif kind in REQUIRED and tls[0] > 1 + 0:
            issues[f"required {kind}: needs tech level {tls[0]}"].append(nm)
        for it in its:
            sp = it["stats"].get("Special")
            if sp and sp not in S.SPECIAL_BITS:
                issues["Special without ability bit"].append(f"{it['name']} ({sp})")
            tl = int(it["stats"].get("Tech Level", 1) or 1)
            if tl > TIER_LV[3] + EDU_MAX // 2:
                issues["tech level never reachable (> 120)"].append(f"{it['name']} TL {tl} [{nm}]")
            if "%05d" % it["id"] not in names and it["type"] != 5 and not it.get("manual_only") and not it.get("demon"):
                issues["not in client name table"].append(it["name"])
os.makedirs(os.path.join(ROOT, "out"), exist_ok=True)
with open(os.path.join(ROOT, "out", "equip_audit.tsv"), "w") as f:
    keys = list(rows[0])
    f.write("\t".join(keys) + "\n")
    for r in rows: f.write("\t".join(str(r[k]) for k in keys) + "\n")
for k, v in issues.items():
    v = sorted(set(v))
    print(f"## {k}: {len(v)}")
    for x in v[:40]: print("   ", x)
print("chassis checked:", len({r['code'] for r in rows}), "slot rows:", len(rows))
