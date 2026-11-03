"""(user 2026-10-22 22:15 / 22:17)
1. NPC commanders that the strategic map shows in a province now also stand and walk on that province's TOWN map (hero +
   minimap dot), like the idle NPCs on the capital map.
2. The BATTLE INFO dialog (class-B 0x1e) lists the NPC commanders fighting there (and 'Aliens' for an alien garrison) on
   the attacker / defender side, not only the players."""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else "server/sgserver.py"
src = open(P, encoding="utf-8").read()
def rep(old, new, cnt=1):
    global src
    if new in src:
        return
    n = src.count(old)
    assert n == cnt, (n, old[:90])
    src = src.replace(old, new)

rep('''    want = {}
    if nid is not None:
        for n in npc_of(nid):
            if n["state"] == "active" and not n.get("task") and len(want) < NPC_TOWN_MAX:
                want[n["id"]] = n
    spots, doors = _CAPS["spots"], _CAPS["doors"]''', '''    want = {}
    if nid is not None:
        for n in npc_of(nid):
            if n["state"] == "active" and not n.get("task") and len(want) < NPC_TOWN_MAX:
                want[n["id"]] = n
        spots, doors = _CAPS["spots"], _CAPS["doors"]
    else:
        # a province town map: every NPC the strategic map draws in this province (user 2026-10-22 22:15)
        pv = province_of(m) if m and m < 100000000 and map_kind(m) == "province" else None
        if pv is None or getattr(s, "battle_mode", 0):
            return
        for n in npc_active():
            if len(want) < NPC_TOWN_MAX and npc_location(n)[0] == pv \\
                    and (n.get("task") or {}).get("phase") not in ("battle", "siege", "raid"):
                want[n["id"]] = n
        if not want and not shown:
            return
        spots = [tuple(p) for p in SPAWN_SPOTS.get(alien_context(s, m)[3] or "", [])] or [(512, 512)]
        cx = sum(p[0] for p in spots) / len(spots)
        cy = sum(p[1] for p in spots) / len(spots)
        doors = sorted(spots, key=lambda p: -((p[0] - cx) ** 2 + (p[1] - cy) ** 2))[:6]     # near the map edges''')
rep('''    d += _s8(f"Battle for province {mapid % 100000:05d}") + bytes([len(parts)])
''', '''    d += _s8(f"Battle for province {mapid % 100000:05d}") + bytes([len(parts)])
    cnt_at = len(d) - 1
''')
rep('''    for o in parts:
        d += _s8(o.acc) + struct.pack(">II", hero_uid(o.acc), side_nation(o) or 0)
    full = len(parts) >= 10''', '''    for o in parts:
        d += _s8(o.acc) + struct.pack(">II", hero_uid(o.acc), side_nation(o) or 0)
    # NPC commanders with units on this battle field, and the alien garrison (user 2026-10-22 22:17: the lists were empty)
    extra = []
    alive_npc = {tg.get("npc") for tg in (b.get("targets") or {}).values() if tg.get("npc") is not None and tg.get("hp", 0) > 0}
    for i in sorted(alive_npc):
        n_ = npc_state()["npcs"].get(str(i))
        if n_ is not None:
            extra.append((n_["name"], NPC_TOWN_BASE + n_["id"], n_["nation"]))
    if any(tg.get("npc") is None and tg.get("hp", 0) > 0 and not tg.get("hive") for tg in (b.get("targets") or {}).values()):
        extra.append(("Aliens", 0, ALIEN_NATION))
    extra = extra[:max(0, 40 - len(parts))]
    if extra:
        d[cnt_at] = len(parts) + len(extra)              # the u8 participant count written above
        for name, cid, nat in extra:
            d += _s8(name) + struct.pack(">II", cid, nat)
    full = len(parts) >= 10''')
open(P, "w", encoding="utf-8").write(src)
print("patched")
