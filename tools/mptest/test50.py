"""test50 (user 2026-10-24 13:19-13:22): units follow the official manual.
Factory sells every Mk1 chassis (Chimera too) with the manual influence; the 0x2f '@' record carries the commander's
influence and the required influence (client greys out / refuses below it); Lab routes go UP only."""
import sys, os, struct
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
for f in ('npcs.json', 'world.json'):
    if os.path.exists(f): os.remove(f)
import sgserver as S
S.LOG = open('/tmp/mp/server50.log', 'w', encoding='utf-8')
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)

BASE = {"Imp", "Wraith", "Sapper", "Shade", "Ghast", "Spirit", "Pegasus", "Red-Eye", "Behemoth", "Manticore",
        "Triage", "Arbalest", "Hawk", "Pelican", "Eagle", "Roc"}
chk("Factory (13:41): only the base unit of each frame (+ Organic / paid)", BASE <= S.SHOP_NAMES and
    not ({"Chimera", "Hydra", "Leviathan", "Medic", "Daeva"} & S.SHOP_NAMES), sorted(S.SHOP_NAMES))
reach = set(S.SHOP_NAMES); grow = True
while grow:
    grow = False
    for a in list(reach):
        for b, _q in S.UPGRADES.get(a, []):
            if b not in reach: reach.add(b); grow = True
chk("every other chassis is reachable in the Lab", {n for _c, n, _t, _p in S.UNIT_CATALOG} <= reach)
chk("manual influence: Behemoth 2, Chimera 25, Hydra 47", (S._INFL["Behemoth"], S._INFL["Chimera"], S._INFL["Hydra"]) == (2, 25, 47))
tabs = {}
for cid, n, t, p in S.UNIT_CATALOG:
    tabs.setdefault(t, set()).add(cid)
chk("class ids stay inside their tab (<= 99 per tab, Mk6+ share)", all(all(c // 100 == t for c in ids) for t, ids in tabs.items()))
chk("unit table packet fits one frame (< 65535 bytes)", len(S.build_unit_catalog()) < 65000, len(S.build_unit_catalog()))
names = {n for _c, n, _t, _p in S.UNIT_CATALOG}
bad = [(a, b, q) for a, opts in S.UPGRADES.items() for b, q in opts
       if b not in names or q <= S.chassis_influence(a) or q != S._INFL.get(b)]
chk("every Lab route goes UP to a catalogue chassis", not bad, bad[:5])
chk("Manticore -> Manticore-MK2 / Chimera / Hydra", [b for b, _q in S.UPGRADES["Manticore"]] == ["Manticore-MK2", "Chimera", "Hydra"],
    S.UPGRADES["Manticore"])
chk("no way back down (Chimera cannot become Manticore)", all(b != "Manticore" for b, _q in S.UPGRADES.get("Chimera", [])))

def shop_rows(d):
    n = d[6]; o = 7; rows = {}
    for _ in range(n):
        b0, mine, need, L = d[o], d[o + 1], d[o + 2], d[o + 3]
        nm = d[o + 4:o + 4 + L].decode('latin-1'); o += 4 + L + 20
        rows[nm] = (b0, mine, need)
    return rows
cmd = {"attrs": [0, 20, 0, 0]}
S.PG.ensure_commander(cmd)
cmd["branches"]["mob"]["level"] = 12
rows = shop_rows(S.build_unit_shop(1, [], 1.0, cmd))
chk("Chimera not in the Factory", "Chimera" not in rows)
chk("shop record: your influence (12 + 20//2 = 22) and required 3 for Manticore", rows["Manticore"] == (1, 22, 3), rows["Manticore"])
chk("shop record: Behemoth required 2", rows["Behemoth"][2] == 2, rows["Behemoth"])
chk("infantry uses the infantry influence", rows["Imp"][1] == S.PG.influence(cmd, "inf"), rows["Imp"])
# 14:03 / 14:06: designed prices, Trebuchet shells, no innate skills, organic evolution from the manual
chk("unit prices rise with influence (Imp < Chimera < Hydra)",
    sum(S._PRICE_BY_NAME["Imp"]) < sum(S._PRICE_BY_NAME["Chimera"]) < sum(S._PRICE_BY_NAME["Hydra"]))
chk("every catalogue unit has a price and a Lab form is sold back for something", all(sum(p) > 0 for _c, _n, _t, p in S.UNIT_CATALOG)
    and sum(S.unit_price_of("Chimera")) > 0)
chk("Lab conversion costs resources", sum(S.upgrade_cost("Manticore", "Chimera")) > 0)
hi = next(i for i in S.ITEMS if i["name"] == "Maxus Mauler-X"); lo = next(i for i in S.ITEMS if i["name"] == "Terminus Marauder")
ph, pl = S.item_price(hi["id"]), S.item_price(lo["id"])
chk("high-tech items are paid mostly in resources, low-tech mostly in money",
    ph[0] / sum(a * b for a, b in zip(ph, (1, 4, 4, 40, 8))) < 0.5 < pl[0] / sum(a * b for a, b in zip(pl, (1, 4, 4, 40, 8))), (ph, pl))
shells = [i for i in S.ITEMS if i.get("page") == "Trebuchet Shells"]
chk("Trebuchet shells designed (no placeholder, distinct damage)", len(shells) == 26 and not any(i.get("placeholder") for i in shells)
    and len({(i["slot"], i["stats"].get("Ground Damage") or i["stats"].get("Air Damage")) for i in shells}) == 26)
u = {"uid": 9, "chassis": "Trebuchet", "level": 10, "items": [985, 884]}
chk("Astral Toss (flak) adds 8 m to the launcher's AIR range", S.unit_weapon(u).get("Air Range") == 51.5 + 8, S.unit_weapon(u))
chk("innate skills only for Gear-Doc (Repair) and Daeva (Grenade)", S.CHASSIS_SKILLS == {"g023": [20], "g001": [8]})
cmd2 = S.PG.ensure_commander({"attrs": [0, 20, 10, 0]})
st = S.stock_loadout({"uid": 1, "chassis": "g056", "level": 5}, cmd2)
chk("a new Triage still heals and repairs (Regen item in its stock loadout)",
    {25, 20} <= {b for i in st for b in S._skill_item_bits(S.ITEM_BY_ID[i])})
chk("organic evolution: Ubik -> Ubik-Amplus (UQ 10), Ubik-Maximus -> Tyr-Primus (UQ 40)",
    S.UPGRADES["Ubik"] == [("Ubik-Amplus", 10)] and S.UPGRADES["Ubik-Maximus"] == [("Tyr-Primus", 40)])
chk("Mamos needs UQ 80 (Momas-Primus)", S._INFL["Mamos"] == 80)
chk("Mk6..Mk9 open, sharing their chassis' Mk5 class id", S.unit_class_id("Behemoth-MK9") == S.unit_class_id("Behemoth-MK5")
    and S.UPGRADES["Behemoth-MK8"] == [("Behemoth-MK9", 114)])
chk("Surge AK256 Cap ground range fixed (0.1 m typo -> 14 m)", S.unit_stats9({"uid": 7, "chassis": "Falcon", "level": 50, "items": [678]})[4] == 280)
_u = {"uid": 77, "chassis": "g056", "level": 5, "items": st}
chk("Triage deploys with its own Heal install mode (bit 56, 17:01), no generic Install",
    (S.unit_abilities(_u) >> 56) & 1 and not (S.unit_abilities(_u) >> 31) & 1)
_u2 = {"uid": 78, "chassis": "g004", "level": 5, "items": []}
_u3 = {"uid": 79, "chassis": "g017", "level": 5, "items": []}
chk("Sapper (no installed art) still never gets Install", not (S.unit_abilities(_u3) & (1 << 31)))
import damage_types as _D
_rows = dict(_D.ROWS)
chk("passive role armour: Mobile/Aviation have anti-flame (Moly), anti-missile (Zirconium), anti-laser (Impervious)",
    _rows["moly steel"][3] >= 75 and _rows["zirconium"][2] >= 75 and _rows["impervious steel"][4] >= 75)
chk("Infantry: Kevlar ballistic, Ablative laser, Hybrid missile, Morganan flame",
    _rows["kevlar"][1] >= 75 and _rows["ablative"][4] >= 75 and _rows["hybrid"][2] >= 75 and _rows["morganan"][3] >= 75)

chk("SatCom removed (14:53): not sold, not in the Lab, not in the catalogue",
    "SatCom" not in S.SHOP_NAMES and not any(n.startswith("SatCom") for _c, n, _t, _p in S.UNIT_CATALOG)
    and all(not t.startswith("SatCom") for o in S.UPGRADES.values() for t, _q in o))
_sc = {"uid": 80, "chassis": "SatCom-MK3", "level": 5, "items": []}
_sc2 = {"uid": 81, "chassis": "g054", "level": 5, "items": []}
chk("owned SatCom units become Red-Eye of the same Mk", S.migrate_removed_chassis(_sc) and _sc["chassis"] == "Red-Eye-MK3"
    and S.migrate_removed_chassis(_sc2) and _sc2["chassis"] == "Red-Eye")
_r = S.upgrade_reach("Hawk")
chk("Hawk reaches Hawk-MK9, Owl-MK7, Falcon-MK5 (manual Mk tops, 14:54)", {"Hawk-MK9", "Owl-MK7", "Falcon-MK5"} <= set(_r), sorted(_r)[:8])
chk("Pelican -> Pelican-MK2 / War Pigeon / Vulture (manual Geo-raptor frame)",
    [b for b, _q in S.UPGRADES["Pelican"]] == ["Pelican-MK2", "War Pigeon", "Vulture"])
_cat = S.build_unit_catalog()
_i = _cat.rfind(b"\x0aWar Pigeon") + 1
_g4 = struct.unpack_from(">H", _cat, _i + len(b"War Pigeon") + 6 + 8 + 6)[0]
chk("catalogue G4 = speed x10 (War Pigeon 3 m/s -> 30)", _g4 == 30, _g4)
# a fresh account owning only a Hawk: the Lab list now carries the whole reachable tree
S.ACCOUNTS_CACHE = None if hasattr(S, "ACCOUNTS_CACHE") else None
_cmd = S.PG.ensure_commander({"attrs": [0, 20, 10, 0]})
_hk = {"uid": 90, "chassis": "Hawk", "level": 60, "items": S.stock_loadout({"uid": 90, "chassis": "a004", "level": 60}, _cmd)}
_hk["chassis"] = "Falcon"
_acc = {"resources": [0, 0, 0, 0, 0], "commander": _cmd}
_mv, _rm, _ad = S.fit_after_upgrade(_hk, _acc, _cmd)
chk("after an upgrade the unit is valid on the new chassis (slots / weight / engine)",
    not [p for p in S.equip_problems(_hk, _cmd) if not p.startswith("tech")], (S.equip_problems(_hk, _cmd), _mv, _rm, _ad))
# organic natural weapons / hides (14:58, manual W-3xx / A-3xx tiers)
def _o(nm, lv):
    u = {"uid": 95, "chassis": nm, "level": lv}; u["items"] = S.stock_loadout(u, _cmd); return u
_s = S.unit_stats9(_o("Oizys", 1))
chk("Oizys L1: magma breath 90 dmg, 10 m, 1 s, flame", _s[2:6] == [301, 90, 200, 100], _s)
_s = S.unit_stats9(_o("Ubik", 60))
chk("Ubik L60: acid spit ground AND air 645, 16.5 m", _s[3] == 645 and _s[6] == 645 and _s[4] == 330, _s)
_s = S.unit_stats9(_o("Mamos", 1))
chk("Mamos (UQ 80 -> tier 8): air-only 195 dmg, 30 m", _s[3] == 0 and _s[6] == 195 and _s[7] == 600, _s)
chk("Slanth L1 hide: 1650 + 1020 HP (+150 biodrive), carapace row", S.unit_battle_stats(_o("Slanth", 1))[0] == 2820
    and S.unit_stats9(_o("Slanth", 1))[1] == S.DT.ALIEN)
_q = _o("Quorg", 30)
chk("Quorg gets Razor claws (slot 4049, manual)", any(S.ITEM_BY_ID[i]["name"].startswith("Razor") for i in _q["items"])
    and S.unit_stats9(_q)[3] == 266)
_wp = {"uid": 96, "chassis": "War Pigeon", "level": 1}
_wp["items"] = S.add_stock_skill(_wp, _cmd, S.stock_loadout(_wp, _cmd))
chk("War Pigeon is a bomber: stock Carpet Bomb (bit 40), no gun slot items", any(40 in S._skill_item_bits(S.ITEM_BY_ID[i]) for i in _wp["items"]),
    [S.ITEM_BY_ID[i]["name"] for i in _wp["items"]])
_pe = {"uid": 97, "chassis": "Pelican", "level": 5}
_pe["items"] = S.stock_loadout(_pe, _cmd); _pe["chassis"] = "War Pigeon"
S.fit_after_upgrade(_pe, {"resources": [0] * 5, "commander": _cmd}, _cmd)
chk("Pelican -> War Pigeon upgrade fits a Carpet Bomb", any(40 in S._skill_item_bits(S.ITEM_BY_ID[i]) for i in _pe["items"]))
chk("no NPC War Pigeons", "War Pigeon" in S.NPC_NO_UNITS and "War Pigeon-MK3" in S.NPC_NO_UNITS)
_ar = {"uid": 98, "chassis": "Arbalest", "level": 30, "items": [91, 2127]}   # Terminus Marauder 30 m + TACS M1 (+5 m)
chk("artillery sensor TACS M1 adds 5 m to the Arbalest's range (30 -> 35 m)", S.unit_stats9(_ar)[4] == 700, S.unit_stats9(_ar))
_nc = [it["name"] for it in S.ITEMS if it.get("type") == 4 and (S._ist(it, "Ground Damage") + S._ist(it, "Air Damage")) > 0
       and not S.DT.damage_class(it) and it["name"] != "Surge EMP Facilitator"]
chk("every damaging weapon has a damage class (manual-only weapons, Alien Flame Tongue)", not _nc, _nc[:6])
chk("H-Repair Machine uses the Repair Machine icon (id 2186)", 2186 in S.ITEM_BY_ID and S.ITEM_BY_ID[2186]["name"] == "H-Repair Machine"
    and 4187 not in S.ITEM_BY_ID)
_ac = {"units": [{"uid": 1, "chassis": "g016", "level": 5, "items": [4187]}], "hero_items": [4187], "commander": {}}
S.ensure_loadouts(_ac)
chk("old H-Repair Machine id 4187 is rewritten in saved accounts", 4187 not in _ac["hero_items"] and 4187 not in _ac["units"][0]["items"])
chk("Trebuchet shells are Misc (type 7) / Special (type 8) items so the Lab lists them",
    S.ITEM_BY_ID[694]["type"] == 7 and S.ITEM_BY_ID[719]["type"] == 8 and S.ITEM_BY_ID[694].get("ammo"))
_tu = {"uid": 99, "chassis": "Trebuchet", "level": 30, "items": [977, 694, 719]}
_t9 = S.unit_stats9(_tu)
chk("Trebuchet: launcher + Cougar M1 (ground 170) + Astral Ram flak (air 140)", _t9[3] == 170 and _t9[6] == 140, _t9)
chk("original split: 7 Cougar mortar shells (Misc 7137) + 6 Astral flak rounds (Special 8137), each with H-",
    sum(1 for it in S.ITEMS if it.get("ammo") and it["slot"] == 7137) == 14
    and sum(1 for it in S.ITEMS if it.get("ammo") and it["slot"] == 8137) == 12
    and all(S.ITEM_BY_ID[i]["slot"] == 8137 for i in (719, 736, 870, 884, 892, 899)))
_old = {"units": [{"uid": 5, "chassis": "g037", "level": 30, "items": [154, 160, 140, 4039, 977, 719, 870]}], "commander": {"attrs": [0, 20, 10, 0]}}
S.ensure_loadouts(_old)
_oi = _old["units"][0]["items"]
chk("old Trebuchet (two Astral rounds) -> at most one flak round + a Cougar mortar shell, still valid",
    sum(1 for i in _oi if S.ITEM_BY_ID[i]["slot"] == 8137) <= 1 and any(S.ITEM_BY_ID[i]["slot"] == 7137 for i in _oi)
    and not S.equip_problems(_old["units"][0], S.PG.ensure_commander(_old["commander"])), _oi)
_tr = dict(S.lab_tree(["War Pigeon", "War Pigeon-MK2"]))
chk("every owned form keeps ALL its options (16:41: a 2nd War Pigeon lost its MK2 option -> 'cannot upgrade')",
    "War Pigeon-MK2" in [t for t, _q in _tr["War Pigeon"]] and _tr["War Pigeon-MK2"], _tr)
_tp = dict(S.lab_tree(["Pelican", "Pelican-MK2"]))
chk("Pelican (root) -> Pelican-MK2 / War Pigeon / Vulture even when a Pelican-MK2 is owned",
    [t for t, _q in _tp["Pelican"]] == ["Pelican-MK2", "War Pigeon", "Vulture"], _tp)
_h = S.lab_tree(["Hawk", "War Pigeon"])
chk("Lab list (16:10): only owned forms are entries (no Roc / Owl categories)", [n for n, _o in _h] == ["Hawk", "War Pigeon"]
    and [t for t, _q in _h[0][1]] == ["Hawk-MK2", "Owl", "Falcon"], _h)
_cids = {n: c for c, n, _t, _p in S.UNIT_CATALOG}
chk("class ids line by line (16:18): War Pigeon-MK2 right after War Pigeon, Ubik-Amplus after Ubik",
    _cids["War Pigeon-MK2"] == _cids["War Pigeon"] + 1 and _cids["Ubik-Amplus"] == _cids["Ubik"] + 1
    and _cids["Arbalest-MK4"] == _cids["Arbalest"] + 3, (_cids["War Pigeon"], _cids["War Pigeon-MK2"]))
import struct as _st
_c = S.build_unit_catalog({"Hawk", "War Pigeon-MK2"})
_n1 = _st.unpack_from(">H", _c, 1)[0]
_o = 3; _l1 = []
for _ in range(_n1):
    _cid = _st.unpack_from(">H", _c, _o)[0]; _ln = _c[_o + 2]; _l1.append(_c[_o + 3:_o + 3 + _ln].decode()); _o += 3 + _ln
_n2 = _st.unpack_from(">H", _c, _o)[0]
chk("0x44 Lab list = owned forms only (Hawk, War Pigeon-MK2), records stay complete (16:32)",
    sorted(_l1) == ["Hawk", "War Pigeon-MK2"] and _n2 == len(S.UNIT_CATALOG), (_l1, _n2))
chk("tree (16:48): only the frame root branches - Arbalest -> MK2/Ballista/Trebuchet, Ballista -> MK2 only, War Pigeon -> MK2 only",
    [t for t, _q in S.UPGRADES["Arbalest"]] == ["Arbalest-MK2", "Ballista", "Trebuchet"]
    and [t for t, _q in S.UPGRADES["Ballista"]] == ["Ballista-MK2"]
    and [t for t, _q in S.UPGRADES["War Pigeon"]] == ["War Pigeon-MK2"]
    and [t for t, _q in S.UPGRADES["War Pigeon-MK2"]] == ["War Pigeon-MK3"])

_ba = {"uid": 120, "chassis": "Ballista", "level": 30, "items": [114]}
_a9 = S.unit_stats9(_ba)
chk("artillery: no generic Install; Ballista Flak Attack reach = its 50 m (ground range was 0)",
    not (S.unit_abilities(_ba) >> 31) & 1 and (S.unit_abilities(_ba) >> 37) & 1 and _a9[4] == 1000 and _a9[3] == 0, _a9)
_w = {"uid": 130, "chassis": "Wight", "level": 5}
_w["items"] = S.add_stock_skill(_w, _cmd, S.stock_loadout(_w, _cmd))
chk("Wight gets Overload (bit 60) from Overloader M1 (17:07)", (S.unit_abilities(_w) >> 60) & 1, [S.ITEM_BY_ID[i]["name"] for i in _w["items"]])
chk("own deploy commands, no generic Install: Vulture / Apparition / Orbus; Red-Eye / Condor keep it (install-only skills)",
    not any((S.unit_abilities({"uid": 131, "chassis": n, "level": 9, "items": []}) >> 31) & 1 for n in ("Vulture", "Apparition", "Orbus"))
    and all((S.unit_abilities({"uid": 132, "chassis": n, "level": 9, "items": []}) >> 31) & 1 for n in ("Red-Eye", "Condor")))
_ab = lambda n, it=(): S.unit_abilities({"uid": 140, "chassis": n, "level": 30, "items": list(it)})
chk("own deploy commands (17:15): Volte Energy production 54, Mantlet Bunker 57, Virus attack/kill 59/58, no generic Install",
    (_ab("Volte") >> 54) & 1 and (_ab("Mantlet") >> 57) & 1 and (_ab("Virus", [5175]) >> 59) & 1 and (_ab("Virus", [5175]) >> 58) & 1
    and not (_ab("Volte") >> 31) & 1)      # (18:25) the Mantlet keeps Install: bit 57 = its installed bunker
chk("Manta detection eyes (manual I-G8317) on sale for the Manta line", any(it["name"] == "Super Detector" for it in S.items_for_unit("Manta"))
    and (_ab("Manta", [6924]) >> 45) & 1)
# (17:27) Triage -> Volte: the Volte was missing from the Lab - the upgrade (op 5) did not resend the 0x44 Lab list
_src = open(os.path.join(os.path.dirname(os.path.abspath(S.__file__)), "sgs", "packets.py"), encoding="utf-8").read()
_op5 = _src[_src.index("COMPLETE UPGRADE"):]
_op5 = _op5[:_op5.index("LAB_OK")]
chk("Lab upgrade resends the owned-forms list before the success result (new form shows in the Lab)",
    "send_unit_catalog(s)" in _op5)
# (17:35) Volte: Energy production mode (bit 54) + a Refuel item (bit 15) - the client refuels allies only in that mode
_vo = {"uid": 9901, "chassis": "Volte", "level": 30, "items": []}   # Volte needs UQ 25
_vcmd = S.PG.ensure_commander({})
_vo["items"] = S.stock_loadout(_vo, _vcmd)
_vb = S.unit_abilities(_vo) if hasattr(S, "unit_abilities") else 0
_vbits = _vb[0] if isinstance(_vb, tuple) else _vb
chk("a Volte gets a Refuel item (Surge Coupler) and the Energy production command",
    any(15 in S._skill_item_bits(S.ITEM_BY_ID[i]) for i in _vo["items"]) and bool(int(_vbits) >> 54 & 1) and bool(int(_vbits) >> 15 & 1),
    (_vo["items"], hex(int(_vbits))))
# (17:36) bombArd / Flak Attack mode reveals a circle of SIGHT radius one ground range ahead (0048ea50): artillery
# must have a sight like the Arbalest's (Trebuchet view 0 -> its shelled area stayed in the fog) and a ground range
_tr = {"uid": 9902, "chassis": "Trebuchet", "level": 50, "items": []}
_tr["items"] = S.stock_loadout(_tr, _vcmd)
_tr_flak = {"uid": 9903, "chassis": "Trebuchet", "level": 50,
            "items": [i for i in _tr["items"] if not S.ITEM_BY_ID[i]["name"].startswith("Cougar")]}
chk("Trebuchet reveals its target area like an Arbalest (sight >= 7 m, ground range for both shell kinds)",
    S.unit_view_px(_tr) >= 140 and S.unit_stats9(_tr)[4] > 0 and S.unit_stats9(_tr_flak)[4] > 0,
    (S.unit_view_px(_tr), S.unit_stats9(_tr), S.unit_stats9(_tr_flak), [S.ITEM_BY_ID[i]["name"] for i in _tr_flak["items"]]))
# (17:58) demon-star monsters: only on the demon star, the last wave ends with the Miasam boss
import random as _rnd
_AL = S.AL
_star = [n for w in (1, 2, 3) for q in _AL.cave_wave(2, 3, 1, w, _rnd.Random(w), star=True) for n in q]
_norm = [n for k in range(200) for q in (_AL.cave_wave(3, 3, 2, 3, _rnd.Random(k)) + _AL.province_units(3, 4, 100, 2, _rnd.Random(k))) for n in q]
chk("demon star spawns only its own monsters (+ Miasam boss); they never appear elsewhere",
    _star and set(_star) <= set(_AL.STAR_SPECIES) | {_AL.STAR_BOSS} and _star[-1] == _AL.STAR_BOSS
    and not (set(_norm) & (set(_AL.STAR_SPECIES) | {_AL.STAR_BOSS}))
    and all(_AL.ROLES[n]["code"] in ("g026", "g031", "g033", "g047", "g048", "g050", "a020", "a012", "a019") for n in set(_star)),
    (sorted(set(_star)), _star[-1:]))
# (18:25) Mantlet: Install (bit 31) deploys it, bit 57 makes the installed unit a bunker ("B Dispose bunker")
_ml = {"uid": 9904, "chassis": "Mantlet", "level": 60, "items": []}
_ml["items"] = S.stock_loadout(_ml, _vcmd)
_mb = S.unit_abilities(_ml); _mb = int(_mb[0] if isinstance(_mb, tuple) else _mb)
chk("Mantlet has Install (31) and Bunker (57)", bool(_mb >> 31 & 1) and bool(_mb >> 57 & 1), hex(_mb))
# (19:16, original) Wight / Quorg: unlocked once with /wight /quorg (Uranium), then bought with normal resources
_shop = lambda acc: S.build_unit_shop(1, acc["units"], 1.0, acc["commander"])
_a0 = {"commander": S.PG.ensure_commander({}), "units": []}
_a1 = {"commander": dict(S.PG.ensure_commander({}), unlocked=["Wight"]), "units": []}
chk("Wight / Quorg: hidden in the Factory until unlocked, then sold for resources (no Uranium)",
    b"Wight" not in _shop(_a0) and b"Quorg" not in _shop(_a0) and b"Wight" in _shop(_a1) and b"Quorg" not in _shop(_a1)
    and S.PRICE.get(S.CODE_OF["Wight"])[3] < 250 and sum(S.PRICE.get(S.CODE_OF["Wight"])) > 0,
    S.PRICE.get(S.CODE_OF["Wight"]))
