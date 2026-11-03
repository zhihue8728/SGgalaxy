# sgserver part "unit_orders": THE ONE PLACE that decides and sends the orders of SERVER UNITS (aliens + NPC units).
# Loaded by sgserver.py into ONE shared namespace (exec, in the order of PARTS) - not an importable module.
#
# Why one place (user 2026-10-27 "simplify the battle flow so this never happens again"): the alien AI, the NPC
# battle brain, the fight-back in damage_target and the join replay each built their own 0x2B attack lumps, and every
# one of them had to remember the same client rule - and twice it was forgotten (NPC 10-25, aliens 10-27):
#
#   CLIENT RULE.  Lump 0x2B AttackObj -> command 1 -> 004d6e30 puts the unit in fire state 5 AT ONCE, whatever the
#   distance.  A target out of range is then reached by client patch F6 (uids 50001..69999) INSIDE the attack state:
#   the attack sprite gNNNat.xpf slides over the ground, no legs, no footprints.  Only lump 0x1A (command 2, move
#   state 2, gNNNmo.xpf + gNNNmop.xpf footprints) walks.  Player units never hit this: their owner's client walks them
#   (0x16) before it sends 0x29 (004e32a0).
#
# So for a server unit:
#   order_attack()   in range -> 0x2B; out of range -> 0x1A toward it and a CHASE that sends the 0x2B on arrival;
#   chase_step()     every AI second for every server unit with a chase or an attack: arrive -> attack, target moved
#                    -> re-aim, attacking but the target ran away (snapshot) -> chase again;
#   dispatch_orders() the single exit for every AI order: ownership guard, ATTACK GUARD (any 0x2B that slipped past
#                    order_attack and is far out of range is turned into a chase - logged as "attack guard"),
#                    order gate, send.
# tools/mptest/test84 fails when code outside this file builds a 0x2B lump.
ORD_APPROACH = True          # False = old behaviour (0x2B at any distance, client F6 drags the unit)
ORD_SLACK = 24               # px beyond the weapon range still counted as in range (target radius)
ORD_REDO = 2.5               # s between re-aims at a target that moved
ORD_MOVED = 48               # px the target must have moved for a re-aim
ORD_RECHASE = 80             # px beyond range (snapshot position) before an attacking unit walks again
ORD_GUARD = 64               # px beyond range before the attack guard rewrites a raw 0x2B
ORD_SNAP_FRESH = 4.0         # s a 0x1d snapshot position is trusted

def attack_lump(tid, target):
    """the raw attack lump.  Use order_attack(); only the in-range branch, the join replay and GM /aatk call this."""
    return bytes([0x2B]) + struct.pack(">II", tid, int(target))

def unit_speed_px(tg):
    """map pixels per second of a server unit: speed x10 m/s, 20 px = 1 m -> speed * 2 px/s."""
    return max(1.0, float(tg.get("spd") or (tg.get("put") or {}).get("spd") or 10) * 2.0)

def walk_seconds(tg, a, b):
    """how long a server unit walks from a to b (client paths are ~30 % longer than the straight line) - the ONE
    estimate (was also written out twice in npc_battle)."""
    return AL.dist(a, b) * 1.3 / unit_speed_px(tg) + 0.5

def unit_range(tg):
    st9 = (tg.get("put") or {}).get("st9") or ()
    return max(st9[4] if len(st9) > 4 else 0, st9[7] if len(st9) > 7 else 0)

def snapshot_pos(tg, p, now):
    """true position of a server unit from the 0x1d world snapshot (battle_maps.apply_snapshot): position, a walk
    still under way re-based on it, and spos/snap_t for the run-away check of chase_step."""
    p = (float(p[0]), float(p[1]))
    tg["pos"], tg["x"], tg["y"] = p, int(p[0]), int(p[1])
    tg["spos"], tg["snap_t"] = p, now
    mv = tg.get("mv")
    if mv:
        tg["mv"] = (p, mv[1], now, now + walk_seconds(tg, p, mv[1]))

def _plain_move(tid, tg, dest, now, msgs):
    """default mover (aliens): one straight leg, the client finds the path.  NPCs pass their own (way points)."""
    a = _npc_est_pos(tg, now)
    tg["pos"] = tuple(a)
    tg["mv"] = (tuple(a), (float(dest[0]), float(dest[1])), now, now + walk_seconds(tg, a, dest))
    tg["arrive_t"] = tg["mv"][3]
    msgs.append(_alien_order_move(tid, *dest))

def _approach_point(a, tpos, r):
    """where to walk to shoot at tpos: on the line to it, 3/4 of the weapon range in front of it."""
    d = AL.dist(a, tpos)
    k = max(0.0, r * 0.75)
    if d < 1 or d <= k:
        return tuple(a)
    return (tpos[0] + (a[0] - tpos[0]) * k / d, tpos[1] + (a[1] - tpos[1]) * k / d)

def _stand_point(a, tpos, r):
    """where the client stops to shoot: on the line to the target at ~0.9 x range (or where it is, if closer)."""
    d = AL.dist(a, tpos)
    r = max(40, r * 0.9)
    if d <= r or d < 1:
        return tuple(a)
    return (tpos[0] + (a[0] - tpos[0]) * r / d, tpos[1] + (a[1] - tpos[1]) * r / d)

def order_attack(tid, tg, target, tpos, now, msgs, mover=None, stand=None):
    """attack order for a server unit.  True = 0x2B sent (in range); False = walking to it (chase).
    mover(tid, tg, dest, now, msgs): how the unit walks (default one straight leg; NPCs: way points).
    stand(tg, tpos): where the unit will stand while shooting (default 0.9 x range on the line)."""
    r = unit_range(tg)
    a = _npc_est_pos(tg, now)
    if ORD_APPROACH and r > 0 and tpos is not None and AL.dist(a, tpos) > r + ORD_SLACK:
        (mover or _plain_move)(tid, tg, _approach_point(a, tpos, r), now, msgs)
        if tg.get("npc") is None:                       # aliens: the AI loop keeps it in combat with this target
            tg["target"], tg["state"] = target, "combat"
        tg["chase"] = [target, now, tuple(tpos), now]
        return False
    tg.pop("chase", None)
    tg["target"], tg["state"] = target, "combat"
    tg["mv"], tg["dest"], tg["route"] = None, None, None
    tg.pop("on_poc", None)
    tg["pos"] = tuple(a)
    if tpos is not None:
        tg["pos"] = stand(tg, tpos) if stand else _stand_point(a, tpos, r)
    tg["atk_t"] = now
    msgs.append(attack_lump(tid, target))
    return True

def chase_step(tid, tg, tpos, now, msgs, mover=None, stand=None):
    """one AI second of a server unit that chases or attacks a live target at tpos.
    True = it is walking (the caller gives it no other order this second)."""
    ch = tg.get("chase")
    r = unit_range(tg)
    if ch:
        a = _npc_est_pos(tg, now)
        if AL.dist(a, tpos) <= r + ORD_SLACK:
            order_attack(tid, tg, ch[0], tpos, now, msgs, mover, stand)
            return False
        arrived = now >= tg.get("arrive_t", 0)
        if now - ch[3] >= ORD_REDO and (AL.dist(tpos, ch[2]) > ORD_MOVED or arrived):
            (mover or _plain_move)(tid, tg, _approach_point(a, tpos, r), now, msgs)
            if tg.get("npc") is None:
                tg["target"], tg["state"] = ch[0], "combat"
            tg["chase"] = [ch[0], ch[1], tuple(tpos), now]
        return True
    # attacking, the target walked away (true position from the 0x1d snapshot) -> walk after it
    sp, st = tg.get("spos"), tg.get("snap_t", 0)
    if (ORD_APPROACH and r > 0 and tg.get("state") == "combat" and sp and now - st <= ORD_SNAP_FRESH
            and st > tg.get("atk_t", 0) + 2 and AL.dist(sp, tpos) > r + ORD_SLACK + ORD_RECHASE):
        tg["pos"], tg["mv"] = tuple(sp), None
        log(f"   orders: {tg.get('name') or tid} {tid} - target {tg.get('target')} ran out of range, walks after it")
        order_attack(tid, tg, tg.get("target"), tpos, now, msgs, mover, stand)
        return True
    return False

def stop_chase(tg):
    tg.pop("chase", None)
    tg["mv"] = None

def _order_positions(s, members):
    """uid -> position of everything a server unit can attack: player units and server units."""
    pos = {}
    for o in members:
        pos.update(getattr(o, "unit_pos", None) or {})
    for t, tg in (getattr(s, "targets", None) or {}).items():
        if tg.get("pos") and tg.get("hp", 1) > 0:
            pos[t] = _npc_est_pos(tg, time.time()) if tg.get("mv") else tg["pos"]
    return pos

def attack_guard(s, members, msgs, now, who="AI"):
    """safety net: a 0x2B for a server unit far out of range that did not come through order_attack -> chase."""
    if not ORD_APPROACH:
        return msgs
    targets = getattr(s, "targets", None) or {}
    pos = None
    out = []
    for m in msgs:
        if m[:1] == b"\x2b" and len(m) >= 9:
            tid, target = struct.unpack_from(">II", m, 1)
            tg = targets.get(tid)
            if tg is not None and not tg.get("chase"):
                pos = _order_positions(s, members) if pos is None else pos
                tp = pos.get(target)
                r = unit_range(tg)
                if tp is not None and r > 0 and AL.dist(_npc_est_pos(tg, now), tp) > r + ORD_SLACK + ORD_GUARD:
                    log(f"   !! attack guard ({who}): {tg.get('name') or tid} {tid} -> {target} out of range, sent as a chase")
                    order_attack(tid, tg, target, tp, now, out)
                    continue
        out.append(m)
    return out

def dispatch_orders(s, b, members, msgs, now, who="AI"):
    """the single exit for orders of server units: ownership guard -> attack guard -> order gate -> one lump packet
    to every member, stamped game_time + RELAY_DELAY (lock-step: everybody executes it on the same tick)."""
    if not msgs:
        msgs = []
    msgs = server_orders_only(s, members, msgs, who) if msgs else msgs
    msgs = attack_guard(s, members, msgs, now, who) if msgs else msgs
    msgs = order_gate(s, b, msgs, now, who)
    if msgs:
        for o in members:
            pk = bytes([0x80, 0, 0]) + struct.pack(">IH", game_time(o) + RELAY_DELAY, len(msgs))
            for m in msgs:
                pk += struct.pack(">H", len(m)) + m
            o.send(pk)
    return msgs
