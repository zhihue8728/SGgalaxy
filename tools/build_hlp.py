#!/usr/bin/env python3
"""Build out/hlp_fixed.dat = the client's hlp.dat + help texts the 1.8.5 client is missing (2026-10-21).
 * InfoTbl.txt gets '1<TAB>name<TAB>code' lines for every server item whose name it does not know
   (all armour, demon armour, the manual-only items of server/extra_items.json) and a text file <code> each.
 * Every item that grants a SKILL gets one line appended to its text: ability, energy cost, power.  The Lab item
   lists have no ability column for engines / weapons / armour (client 00457d80), so this is the only place where
   e.g. the Cloak of the Mutated Biocase engine is visible.
Archive format (tools/sgdat.py): u32 count, count x {u32 offset, char name[13]}, data; names sorted
case-insensitively (client bsearch 0048ba90), last entry = empty name with offset = file size.
usage: build_hlp.py [game hlp.dat] [out]"""
import os, sys, struct
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "server"))
os.chdir(os.path.join(ROOT, "server"))
import sgserver as S

_G = os.path.expanduser("~/mnt/Shattered Galaxy/")
SRC = sys.argv[1] if len(sys.argv) > 1 else (_G + "hlp.dat.orig" if os.path.exists(_G + "hlp.dat.orig") else _G + "hlp.dat")   # always the ORIGINAL
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "out", "hlp_fixed.dat")

def read(path):
    d = open(path, "rb").read()
    n = struct.unpack_from("<I", d, 0)[0]
    ents = [(d[4 + 17 * i + 4:4 + 17 * i + 17].split(b"\0")[0].decode("latin-1"), struct.unpack_from("<I", d, 4 + 17 * i)[0])
            for i in range(n)]
    files = {}
    for i, (nm, off) in enumerate(ents):
        if nm:
            files[nm] = d[off:ents[i + 1][1]]
    return files

def write(path, files):
    names = sorted(files, key=lambda x: x.lower())
    n = len(names) + 1
    off = 4 + 17 * n
    idx, data = bytearray(struct.pack("<I", n)), bytearray()
    for nm in names:
        idx += struct.pack("<I", off + len(data)) + nm.encode("latin-1").ljust(13, b"\0")
        data += files[nm]
    idx += struct.pack("<I", off + len(data)) + b"\0" * 13
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "wb").write(bytes(idx + data))

PASSIVE = {35: "can be moved by allied Teleport / Link Gate"}   # no button, no energy
PER_SECOND = {5, 10, 11, 14, 34, 45, 43, 39}      # toggles: energy per second while on
WHILE_MOVING = {3, 9, 38, 40}                      # per second while moving
BIT_NAME = {b: n for n, b in S.SPECIAL_BITS.items()}
BIT_NAME[20] = "Repair"

def skill_line(it):
    b = S._skill_item_bit(it)
    if b is None:
        return ""
    e, pw = S._skill_vals(it)
    nm = BIT_NAME.get(b, it["stats"].get("Special", "?"))
    if b in PASSIVE:
        return f" [Ability: {nm} (passive) - {PASSIVE[b]}]"
    if b in PER_SECOND:
        cost = f"{e} kJ/s while active"
    elif b in WHILE_MOVING:
        cost = f"{e} kJ/s while moving"
    elif b == 52:
        cost = f"{e} kJ x distance / 32"
    else:
        cost = f"{e} kJ per use"
    extra = ""
    if b == 38:
        extra = f", speed +{pw}%"
    elif pw and b not in (17,):
        extra = f", power {pw}"
    return f" [Ability: {nm} - {cost}{extra}]"

def ammo_texts(it):
    """(15:58) Trebuchet shells (designed, "ammo"): the client's own help for all twelve ids said "Flak rounds ... air
    units" (also on the mortar shells) and was English only -> own text with the target, damage and range, + zh."""
    st = it.get("stats", {})
    air = bool(st.get("Air Damage"))
    dmg = int(st.get("Air Damage") or st.get("Ground Damage") or 0)
    rb = st.get("Range Bonus")
    en = (f"Trebuchet {'flak round' if air else 'mortar shell'}: attacks {'AIR' if air else 'GROUND'} units only. "
          f"Damage {dmg} per hit, area effect.{f' Launcher range +{rb:g} m.' if rb else ''} "
          f"Equip it together with an Astral Launcher (weapon slot); the launcher sets range and cooldown.")
    tw = (f"投石車{'防空彈' if air else '迫擊砲彈'}：只攻擊{'空中' if air else '地面'}單位。每發傷害 {dmg}，範圍傷害。"
          f"{f'發射器射程 +{rb:g} 公尺。' if rb else ''}必須和星界發射器（武器欄）一起裝備，射程與冷卻由發射器決定。")
    cn = (f"投石车{'防空弹' if air else '迫击炮弹'}：只攻击{'空中' if air else '地面'}单位。每发伤害 {dmg}，范围伤害。"
          f"{f'发射器射程 +{rb:g} 米。' if rb else ''}必须和星界发射器（武器栏）一起装备，射程与冷却由发射器决定。")
    return en, tw, cn

ARMOR_KIND = {"Infantry": "infantry", "Mobile": "vehicle", "Aviation": "aircraft", "Organic": "organic"}

def new_text(it):
    st, t = it.get("stats", {}), it["type"]
    if it.get("desc") and not it.get("manual_only"):
        return it["desc"]
    if t == 5:
        kind = next((v for k, v in ARMOR_KIND.items() if k.lower() in (it.get("page") or "").lower()), "unit")
        if any(w in it["name"] for w in ("Derma", "Sheathing", "Husk", "Grafted")):
            kind = "organic"
        return (f"{it['name']} is {kind} armor. It adds {int(st.get('Health', 0) or 0)} health and "
                f"{int(st.get('Armor', 0) or 0)} armor to the chassis.")
    if t == 4:
        g, a = st.get("Ground Damage"), st.get("Air Damage")
        what = "ground and air" if g and a else ("air" if a else "ground")
        if st.get("Special") == "Snipe":
            return (f"Apparition sniper rifle: long range {what} attack ({st.get('Ground Range')} m). "
                    "Snipers need a sensor or allied sight to see their targets.")
        return f"This weapon attacks {what} targets."
    if "Repair" in it["name"]:
        return "This item allows the unit to repair damaged mechanical units."
    return it["name"]

AMMO_ZH = {}

def main():
    files = read(SRC)
    tbl = files["infotbl.txt"].decode("latin-1")
    known = {}
    for ln in tbl.splitlines():
        f = ln.split("\t")
        if len(f) >= 3:
            known[f[1]] = f[2]
    added, appended = [], 0
    for it in S.ITEMS:
        code = known.get(it["name"])
        if code is None:
            code = "%05d" % it["id"]
            if code in files:
                print("code clash, skipped:", it["name"], code)
                continue
            tbl += f"1\t{it['name']}\t{code}\r\n"
            known[it["name"]] = code
            files[code] = new_text(it).encode("latin-1", "replace")
            added.append(it["name"])
        line = skill_line(it)
        if it.get("own_help") and it.get("desc"):
            files[code] = (it["desc"] + (line or "")).encode("latin-1", "replace")
            continue
        if it.get("ammo"):
            en, tw, cn = ammo_texts(it)
            m = __import__("re").match(r" \[Ability: (.*?) - (\d+) kJ per use\]", line or "")
            zl = (f" [技能：{m.group(1)} - 每次 {m.group(2)} kJ]" if m else "")
            files[code] = (en + (line or "")).encode("latin-1", "replace")
            AMMO_ZH[en + (line or "")] = [tw + zl, cn + zl]
            continue
        if line and code in files and b"[Ability:" not in files[code]:
            files[code] = files[code].rstrip() + line.encode("latin-1")
            appended += 1
    files["infotbl.txt"] = tbl.encode("latin-1")
    if AMMO_ZH:                                   # translations for build_i18n_dat.py
        import json
        ip = os.path.join(ROOT, "tools", "i18n_ui.json")
        T = json.load(open(ip, encoding="utf-8"))
        T["hlp"].update(AMMO_ZH)
        json.dump(T, open(ip, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    write(OUT, files)
    print(f"{OUT}: {len(added)} new item texts, {appended} ability lines")

if __name__ == "__main__":
    main()
