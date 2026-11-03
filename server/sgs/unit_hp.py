"""PLAYER UNIT HP - the one place (user 2026-10-28 12:56: "damaged in battle, full again in the Factory - solve it for
real, one logic, no several places computing / syncing it").

What was wrong (before this module, five copies of the rule):
  * the roster stored the BATTLE HP the client reported (0x21), which includes the honor / last-stand bonus
    (honor_hp), but the Factory / Lab / repair measured it against the bonus-less equipment HP
    (unit_battle_stats) -> any wound smaller than the bonus showed as FULL, a bigger one as too small;
  * a repair stored the bonus-less HP, so the next battle started below its battle full HP (looked wounded);
  * the client's lump 0x21 has two kinds ([uid][01][u16 hp] and [uid][02][5 x u16] (the other 5 values)) - the
    server read the first u16 of BOTH as the HP;
  * three _cur() copies (enter, F7, re-deploy), unit_full_hp, hp_frac, _keep_hp, the end_battle block, the snapshot
    HP kept apart (unit_hp_c).

THE RULE
  roster  u["hp"]  = HP in EQUIPMENT units: 0 .. hp_base_full(u) = unit_battle_stats(u)[0]; no key = full.
  battle  full     = honor_hp(commander, base full)  (honor / last-stand bonus; can change between battles)
          current  = the roster FRACTION x battle full  -> the wound is kept whatever the bonus is now.
  live    s.unit_hp[uid] = the newest battle HP of a unit on the field (client 0x21 kind 1 every ~5 s when it
          changed, or a 0x1d world snapshot) - hp_note() is the only writer.
  store   hp_store(s, uids): battle HP / the max HP the client was given (put_args "hpmax") x base full -> roster.
          The only writer of u["hp"] besides death (0) and repair (hp_repair)."""

def hp_base_full(u):
    """full HP of a roster unit with its equipment, no battle bonus (Factory / Lab / repair scale)."""
    try:
        return max(1, int(unit_battle_stats(u)[0] or 1))
    except Exception:
        return 1

def hp_frac(u):
    """0..1 share of its full HP a roster unit has (no 'hp' key = undamaged)."""
    if not u or "hp" not in u:
        return 1.0
    return max(0.0, min(1.0, float(u["hp"]) / hp_base_full(u)))

def hp_battle(cmd, u):
    """(current, full) battle HP of a roster unit for its PUT: full with the commander's bonus, current = the stored
    share of it (a wounded unit stays wounded by the same share)."""
    full = max(1, int(honor_hp(cmd or {}, hp_base_full(u)) * PG.star_mult(u)))   # (10-31) +3 % HP per star
    f = hp_frac(u)
    cur = int(round(full * f))
    if f > 0 and cur < 1:
        cur = 1
    return min(full, cur), full

def hp_battle_en(cmd, u):
    """(current battle HP, energy) - the squad tuples of enter / F7 / re-deploy."""
    return hp_battle(cmd, u)[0], unit_battle_stats(u)[1]

def unit_full_hp(s, u):
    """battle full HP of a player's roster unit (= PUT max HP); None if unknown."""
    if not u:
        return None
    try:
        return hp_battle(get_account(getattr(s, "acc", None))[1].get("commander", {}), u)[1]
    except Exception:
        return None

def hp_note(s, uid, hp):
    """the newest battle HP of an own unit on the field (client 0x21 kind 1 / 0x1d snapshot)."""
    try:
        hp = int(hp)
    except Exception:
        return
    s.__dict__.setdefault("unit_hp", {})[uid] = max(0, hp)

def hp_store(s, uids=None):
    """write the live battle HP of these units (None = all noted) back to the roster, in equipment units, and forget
    them.  Dead units (roster hp 0) stay dead.  -> {uid: stored hp}"""
    live = s.__dict__.get("unit_hp") or {}
    todo = [u for u in (live if uids is None else uids) if u in live]
    if not todo:
        return {}
    pa = getattr(s, "put_args", {}) or {}
    accs, a = get_account(getattr(s, "acc", None))
    cmd = a.get("commander", {})
    by = {u["uid"]: u for u in a.get("units", [])}
    done = {}
    for uid in todo:
        hp = live.pop(uid)
        u = by.get(uid)
        if u is None or u.get("hp", 1) <= 0:
            continue
        full_b = (pa.get(uid) or {}).get("hpmax") or hp_battle(cmd, u)[1]
        base = hp_base_full(u)
        v = int(round(base * max(0.0, min(1.0, hp / max(1, full_b)))))
        if hp > 0 and v < 1:
            v = 1
        if v >= base:
            u.pop("hp", None)                       # undamaged: no key (= full whatever the equipment becomes)
        else:
            u["hp"] = v
        done[uid] = v
    if done and getattr(s, "acc", None) in accs:
        accs[s.acc] = a
        save_accounts(accs)
    return done

def hp_alive(u):
    """a roster unit that is not destroyed (hp 0 = destroyed until repaired)."""
    return bool(u) and u.get("hp", 1) > 0

def hp_repair(u):
    """Factory repair: back to full."""
    u.pop("hp", None)
