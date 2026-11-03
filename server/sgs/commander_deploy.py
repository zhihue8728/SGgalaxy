# sgserver part "commander_deploy": nicknames, commander, deployment, unit stats.
# Loaded by sgserver.py into ONE shared namespace (exec, in the order of PARTS) - not an importable module;
# every name here is a sgserver global.  Checks: python tools/check_server.py
# ---- NICKNAMES (user 2026-10-22 15:11: the login account stays English, the commander shows a Chinese nickname) ---------
# The account name stays the key everywhere on the server.  What the CLIENTS see is the nickname: in binary packets as its
# GBK bytes (wire form = those bytes as a latin-1 str, so every _s8 / .encode('latin-1') keeps working); a Big5 (cp950)
# receiver gets the same name re-encoded in Session.send (nick_swap, same byte length).  Chat lines (TextPkt) use the plain
# Unicode nickname and are encoded per receiver anyway.  Names that come back from a client (whisper target, profile by
# name, word of honor) are resolved by nick_account() in any of these forms.
NICK = {"wire": {}, "uni": {}, "acc": {}, "swap": []}
NICK_MAX_BYTES = 12           # the client's name fields (hero 0x20 name <= 12 chars)
NICK_CHANGE_URA = 100         # PLACEHOLDER: the first nickname is free, every change costs this much Uranium

def nick_rebuild(accs=None):
    accs = accs if accs is not None else load_accounts()
    w, u, a, sw = {}, {}, {}, []
    for acc, rec in accs.items():
        nk = rec.get("nick") if isinstance(rec, dict) else None
        if not nk:
            continue
        try:
            g = nk.encode("gbk")
        except UnicodeEncodeError:
            continue
        b5 = nk.encode("cp950", "replace")[:len(g)].ljust(len(g), b"?")
        w[acc.lower()] = g.decode("latin-1"); u[acc.lower()] = nk
        for form in (acc, nk, g.decode("latin-1"), b5.decode("latin-1")):
            a[form.lower()] = acc
        if b5 != g:
            sw.append((bytes([len(g)]) + g, bytes([len(b5)]) + b5))
    NICK.update(wire=w, uni=u, acc=a, swap=sw)

def wire_name(name):
    """client-side spelling of a commander name (nickname as GBK bytes in a latin-1 str); anything else unchanged."""
    if NICK["wire"] and isinstance(name, str):
        return NICK["wire"].get(name.lower(), name)
    return name

def display_name(acc):
    """Unicode name for chat lines (TextPkt)."""
    n = NICK["uni"].get((acc or "").lower())
    if n is not None:
        return n
    # user 2026-10-25 14:54: a Chinese account id is kept as the raw client bytes in a latin-1 str; chat lines are
    # re-encoded per receiver from Unicode, so decode it here (else every Chinese id showed as ????)
    if acc and any(ord(c) >= 0x80 for c in acc):
        for enc in ("gbk", "big5"):
            try:
                return acc.encode("latin-1").decode(enc)
            except Exception:
                pass
    return acc

def nick_account(name, enc=None):
    """account behind a name a client sent (account, nickname in GBK / Big5 bytes, or Unicode)."""
    if not name:
        return name
    acc = NICK["acc"].get(name.lower())
    if acc is None and enc and enc != "latin-1":
        try:
            acc = NICK["acc"].get(name.encode("latin-1").decode(enc).lower())
        except Exception:
            acc = None
    return acc or name

def nick_own(payload, acc):
    """the client knows ITSELF only by the login account (004ee140, set at login, not by 0x15): F4 shows it and PUT_UNIT
    marks a unit as OWN when its owner == that name (004acf0e _mbsicmp).  So in the packets that carry the commander /
    unit owner name (0x15, 0x18, 0x20) a player gets HIS OWN name as the account, everybody else the nickname
    (2026-10-22 16:09: with the nickname as owner the own battle units would not have been controllable)."""
    if not acc or not payload or payload[0] not in (0x15, 0x18, 0x20):
        return payload
    w = NICK["wire"].get(acc.lower())
    if not w:
        return payload
    g = w.encode("latin-1")
    pat = bytes([len(g)]) + g
    if pat in payload:
        a = acc.encode("latin-1", "replace")
        payload = payload.replace(pat, bytes([len(a)]) + a)
    return payload

def nick_swap(payload, enc):
    if enc == "cp950" and NICK["swap"]:
        for g, b5 in NICK["swap"]:
            if g in payload:
                payload = payload.replace(g, b5)
    return payload

# RANKS (2026-10-21 23:05, user: rank icons looked wrong).  ui-insg.xpf holds 21 insignia per division colour
# (frame = index * 8 + branch, rendered out/insg/all.png): 0-5 chevrons x1..6, 6-11 bars x1..6, 12-17 round badges
# x1..6, 18-20 large emblems x1..3.  Before, 12 titles were spread over the 21 icons (Captain = 6 bars) and General was
# reached at level 56 although divisions now go to 100.  Now one title per insignia, spread evenly over levels 1..100
# (about 5 levels per rank); levels above 100 keep the top rank.  Reincarnation: see rank_title (R<n> mark).  Titles are server-defined (the client
# data has no rank names).
RANK_TITLES = ["Recruit", "Private", "Pvt 1st Cl.", "Corporal", "Sergeant", "Staff Sgt",          # chevrons
               "Warrant Off.", "2nd Lieut.", "1st Lieut.", "Captain", "Sr. Captain", "Major",  # bars
               "Lt. Colonel", "Colonel", "Sr. Colonel", "Commodore", "Brigadier", "Maj. General",      # badges
               "Lt. General", "General", "Supreme Gen."]                                              # emblems
RANK_LEVELS = 100
RANK_SHORT = ["Recruit", "Private", "PFC", "Corporal", "Sergeant", "StaffSgt", "W.Officer", "2nd Lt.", "1st Lt.",
              "Captain", "Sr.Capt.", "Major", "Lt.Col.", "Colonel", "Sr.Col.", "Commodore", "Brigadier", "Maj.Gen.",
              "Lt.Gen.", "General", "Sup.Gen."]          # with the reincarnation mark (R<n> + short title <= 12)

def rank_index(level):
    return min(len(RANK_TITLES) - 1, max(0, int(level) - 1) * len(RANK_TITLES) // RANK_LEVELS)

def rank_icon(level):
    """insignia index 0..20 of ui-insg.xpf (the client adds the division colour)."""
    return rank_index(level)

def rank_name(level):
    """per-division RANK field of F4 / battle result: ~10 characters fit (2026-10-21 23:13 'R1 W.Officer' was cut)
    -> always the short title (<= 9), no rebirth mark (F4 HISTORY already shows REINCARNATION)."""
    return RANK_SHORT[rank_index(level)]

def rank_for(s, level, reinc=0, short=False):
    """rank text for THIS player's language (Chinese: 新兵 ... 元帥, rebirth mark 'R<n> ' kept)."""
    lang = getattr(s, "lang", "en")
    if lang not in ("zh-tw", "zh-cn"):
        return rank_name(level) if short else rank_title(level, reinc)
    t = I18N.rank(rank_index(level), lang)
    return f"R{min(int(reinc), 99)} {t}" if (reinc and not short) else t

def _s8e(s, t):
    """s8 string in the receiver's code page."""
    b = str(t).encode(getattr(s, "enc", "latin-1"), "replace")[:250]
    return bytes([len(b)]) + b

def rank_title(level, reinc=0):
    """rank title; a reincarnated hero keeps the mark 'R<n> ' in front (user 2026-10-21 23:08: after rebirth the rank
    starts again from Recruit - the branches restart at level 1 - but the rebirth must stay visible)."""
    if not reinc:
        return RANK_TITLES[rank_index(level)]
    # 2026-10-21 23:10 (user): shorter - "R<n>" + the SHORT title, at most 12 characters in all
    t = f"R{min(int(reinc), 99)} {RANK_SHORT[rank_index(level)]}"
    return t if len(t) <= 12 else t.replace(" ", "", 1)[:12]

def build_hero_info(s):
    """server 0x27 sub 0 = INTROSPECTION window (F4, client FUN_004b4980).  Field -> label CONFIRMED on screen
    with diagnostic values (2026-10-20):
      s8 TITLE, u8 B1 (?), 4 x branch {u8 LEVEL, s8 RANK, u8 ?, u8 ?, u32 XP, u32 next-level XP total
      (XP NEEDED = total - XP)} for INF/MOB/AVI/ORG, u8 REINCARNATION, u32 PRESTIGE, u32 HONOR points (shown
      /100 with a progress bar), u32 ?, u8 n {u32 medal id, s8 text} (MEDAL list), u16 RECORD wins, u16 losses,
      u8 TACTICS, u8 CLOUT, u8 EDUCATION, u8 MECH APT, u16 POINT,
      s8 SUPERIOR, u8 MERCENARY (11-01: client 004b537c -> 005e09f0 sets the F4 window's +0xe78, the 开/关 buttons)"""
    accs, a = get_account(getattr(s, "acc", None))
    cmd = PG.ensure_commander(a.setdefault("commander", {}))
    br = cmd["branches"]
    top = max(v["level"] for v in br.values())
    attrs = (list(cmd.get("attrs") or [0, 0, 0, 0]) + [0, 0, 0, 0])[:4]
    d = bytearray([0x27, 0]) + _s8e(s, rank_for(s, top, cmd.get("reincarnations", 0))) + bytes([0])
    for key in PG.BRANCHES:
        v = br[key]
        need = PG.branch_xp_need(v["level"])
        d += bytes([min(v["level"], 255)]) + _s8e(s, rank_for(s, v["level"], short=True)) + bytes([rank_icon(v["level"])] * 2) + struct.pack(">II", v["xp"], need)
    d += bytes([min(cmd.get("reincarnations", 0), 255)])
    d += struct.pack(">III", pr_of(cmd), cmd.get("honor", 0), 0)
    fix_medal_ids(cmd)
    medals = cmd.get("medals", [])[:255]
    d += bytes([len(medals)]) + b"".join(struct.pack(">I", mid) + _s8e(s, medal_text(txt, getattr(s, "lang", "en")))
                                         for mid, txt in medals)
    d += struct.pack(">HH", cmd.get("wins", 0), cmd.get("losses", 0))
    d += bytes([min(x, 255) for x in attrs]) + struct.pack(">H", cmd.get("points", 0))   # TACTICS..MECH, POINT
    d += _s8(cmd.get("superior", "")) + bytes([1 if cmd.get("mercenary") else 0])
    return bytes(d)

HP_DIAG = False    # diagnostic numbers in the roster record (found: block A[1] = current HP)
# hp_frac -> sgs/unit_hp.py (2026-10-28: the one place for unit HP)

def roster_rec(u):
    disp = DISPLAY.get(u["chassis"], u["chassis"])
    return (u["uid"], disp, PG.star_tag(u) + (u.get("label") or disp), hp_frac(u), u.get("level", 1), int(u.get("deploy", 0) or 0),
            unit_battle_stats(u)[0],                      # max HP incl. equipment (Lab / deploy window)
            PG.unit_xp_total(u))                          # (11-01) total XP (client unit +0x30)

# ---- DEPLOYMENT (division) -------------------------------------------------------------------------------------
# CONFIRMED 2026-10-21 (client CUnitManageWnd 005cc270, 0x16 parser 005461a0, 004ee510, 004a6f20):
#   commander +0x4a8 = 12 DIVISION slots (deployed units), +0x4d8 = 128 reserve slots.
#   0x16 record "hotkey flag" byte = 1 -> the unit goes into division slot (next byte - 1), 0 -> reserve.
#   Before ATTACK the client counts the division (004eda90); 0 -> "ksNoUnitActive ... Press <ASSIGN TROOPS>"
#   and it sends 0x19 [00].  Server class-B 0x1C [] opens the deploy window ("UnitManage Wnd", 004a3fb0).
#   OK in the window -> client 0x19 [01][u8 n] n x {u32 uid, u8 slot (1..12 = division, 0 = reserve)}.
#   The account stores the slot in unit["deploy"].
def ensure_deploy(a):
    """first time: deploy the first living units up to the deploy limit (slots 1..N)."""
    if a.get("deploy_init"):
        return
    lim = PG.deploy_limit(PG.ensure_commander(a.setdefault("commander", {})))
    n = 0
    for u in a.get("units", []):
        if n < lim and hp_alive(u):
            n += 1
            u["deploy"] = n
        else:
            u["deploy"] = 0
    a["deploy_init"] = True

def set_deploy(s, body):
    accs, a = get_account(s.acc)
    lim = PG.deploy_limit(PG.ensure_commander(a.setdefault("commander", {})))
    n = body[2] if len(body) > 2 else 0
    want, used = {}, set()
    for i in range(n):
        o = 3 + 5 * i
        if o + 5 > len(body):
            break
        uid = struct.unpack_from(">I", body, o)[0]
        slot = body[o + 4]
        if 1 <= slot <= min(12, lim) and slot not in used:
            used.add(slot)
            want[uid] = slot
        else:
            want[uid] = 0
    for u in a.get("units", []):
        if u["uid"] in want:
            u["deploy"] = want[u["uid"]]
    a["deploy_init"] = True
    accs[s.acc] = a
    save_accounts(accs)
    log(f"   deploy window OK: division {sorted((v, k) for k, v in want.items() if v)} (limit {lim})")
    if getattr(s, "redeploy_pending", False) and getattr(s, "battle", None) and not getattr(s, "alive_units", None):
        s.redeploy_chosen = True           # (21:56) chosen in the window opened by REINFORCE
        redeploy(s)                       # whole squad lost: the new division enters at once (2026-10-23)
    elif getattr(s, "f7_choose", False) and getattr(s, "battle", None):
        reinforce_chosen(s)               # (20:18) F7 in battle: the chosen off-field units enter

_NAME_CID = {name: cid for cid, name, _tab, _p in UNIT_CATALOG}
def unit_class_id(chassis):
    """Factory class id (tab*100 + n) of a roster unit, by display name or art code; 1 (Infantry) if unknown."""
    name = DISPLAY.get(chassis, chassis)
    if name not in _NAME_CID:
        name = next((n for n, c in CODE_OF.items() if (c == chassis or c == CODE_OF.get(name)) and n in _NAME_CID), name)
    return _NAME_CID.get(name, 1)

def mech_for(s):
    """Mech Apt of the account of session s (carry weight = base x (1 + Mech / 120)); every build_units call passes it,
    the old fallback (the only account in MECH_APT, else 0) showed 60 instead of 120 as soon as a 2nd account was online."""
    try:
        _accs, _a = get_account(getattr(s, "acc", None))
        return PG.attr(PG.ensure_commander(_a.setdefault("commander", {})), 3)
    except Exception:
        return MECH_APT.get(getattr(s, "acc", None), 0)

def build_units(units, sub=1, mech=None):
    """server type 0x16 (client parser FUN_005461a0, field order read from the call sequence):
    sub 1 = full unit list: u8 n + n records (clears the roster first);
    sub 2 = ADD ONE unit: exactly one record, no count byte; if the Factory is open the client also puts it
            into 'YOUR UNITS' (FUN_0048ab20);  sub 3 = REMOVE unit: u32 id.
    record: u32 id, u8 type (1..2, else "got invalid unit of type"), u8, u16, 3 x u32, u8, u8 hotkey flag,
            u8 hotkey+1, 9 x u16, u8, 9 x u16, u64, u16, s8, s8."""
    if mech is None:
        mech = next(iter(MECH_APT.values()), 0) if len(MECH_APT) == 1 else 0
    d = bytearray([0x16, sub]) + (bytes([len(units)]) if sub == 1 else b"")   # sub 2 add / 4 update: 1 record
    for rec in units:
        uid, chassis, name = rec[:3]
        frac = rec[3] if len(rec) > 3 else 1.0          # current HP as a fraction of full
        level = max(1, min(255, int(rec[4]))) if len(rec) > 4 else 1   # unit +0x3c LEVEL (Lab "Lev", UQ)
        slot = int(rec[5]) if len(rec) > 5 and 0 < int(rec[5]) <= 12 else 0   # division slot 1..12, 0 = reserve
        mu = UNIT_MANUAL.get(str(chassis).lower(), {})
        # CONFIRMED (Factory "2101/1680" diagnostic, 2026-10-20): block A[0] = MAX HP, block A[1] = CURRENT HP.
        # The u16 after the art bytes is NOT the HP (meaning unknown, kept at 1 as before).
        hp_max = int(rec[6]) if len(rec) > 6 else int(float(mu.get("base_health", 100) or 100))
        hp_max = max(1, min(65535, hp_max))
        cur = max(0, min(65535, int(round(hp_max * frac))))
        hp_cur = cur
        # u16 after the art bytes = CLASS ID -> unit +0x60 (CONFIRMED FUN_005461a0 -> FUN_005c5bb0).  The Lab/Factory
        # tree files the unit under tab = class id // 100 (FUN_00447e10) and a click only selects it (0x800 ->
        # Current/Required Unit Quality) when it is in that tab's list (FUN_00445250).  It was always 1 = Infantry,
        # so Mobile/Aviation/Organic units showed no Unit Quality in the Lab.
        cur = unit_class_id(chassis)
        if HP_DIAG:
            cur = 2500                                   # DIAGNOSTIC: is this the max (/N) or the current?
        d += struct.pack(">I", uid) + bytes([unit_kind(chassis)[0], unit_kind(chassis)[2]]) + struct.pack(">H", cur)
        # 3 x u32: the FIRST is the unit's TOTAL XP (unit +0x30, CONFIRMED 11-01: 005c5bb0 6th argument; the Assign XP
        # window and the Lab "经验" showed it - it was the chassis weight before, so every Apparition had "XP 56").
        # The level the client sees for it comes from progression.unit_xp_cum (W of the 0x44 record).
        # The second (max space?) and third (100) are still guesses.
        wcap = int(int(mu.get("max_weight_kg", 100)) * (1 + mech / 120))   # Mech Apt: base * (1 + mech/120) -> A[4]
        xpt = max(0, min(0xFFFFFFFF, int(rec[7]))) if len(rec) > 7 else 0
        d += struct.pack(">III", xpt, int(mu.get("max_space_l", 100)), 2600 if HP_DIAG else 100) + (bytes([level, 1, slot]) if slot else bytes([level, 0, 1]))   # u8 LEVEL (CONFIRMED 005c5bb0 -> +0x3c, was always 1), hotkey flag, hotkey+1
        # CONFIRMED with the Lab STAT VIEW (diagnostic 201..209 / 301..309):
        #   block A [0] = max Health, [1] = CURRENT health, [4] = max Weight, [5] = max Space, [7] = Speed x10
        #   block B [0] = Armor.  The other slots are still unknown -> 0.
        def _n(k, mul=1):
            try:
                return max(0, min(65535, int(round(float(mu.get(k, 0)) * mul))))
            except Exception:
                return 0
        # A[6] = CHASSIS WEIGHT (CONFIRMED 005c52d0: unit +0x2c + sum of item weights -> engine load FUN_00527020,
        # Lab "Eng. Usage").  Manual field unit_weight_kg.
        a = [hp_max, hp_cur, 0, 0, min(65535, wcap), _n("max_space_l"), _n("unit_weight_kg"), _n("speed_m_s", 10), 0]
        b = [_n("base_armor"), 0, 0, 0, 0, 0, 0, 0, 0]
        if HP_DIAG:     # DIAGNOSTIC: every unknown slot gets its own number to find CURRENT HP ("X/1680" in the Factory)
            for k in (1, 2, 3, 6, 8):
                a[k] = 2100 + k
            b = [b[0]] + [2200 + k for k in range(1, 9)]
        d += struct.pack(">9H", *a) + bytes([0])                              # 9 x u16 stats, u8
        d += struct.pack(">9H", *b) + struct.pack(">Q", 2300 if HP_DIAG else 0)   # 9 x u16, u64
        d += struct.pack(">H", 2400 if HP_DIAG else 0)
        # two s8 strings: CONFIRMED order = unit NAME (shown in the unit list), then CHASSIS (STAT VIEW "Chassis:")
        for t in (name, chassis):
            tb = t.encode('latin-1'); d += bytes([len(tb)]) + tb
    return bytes(d)

def build_hero(uid, name, x, y, kind=0, cls=1, nation=1, hp=100, mark=0, rank=0, title=b""):
    """server type 0x20 "S_HERO_PUT" (client parser FUN_004ac360).  Layout confirmed with the client's own
    packet dump (its string reader consumes bytes right after kind/cls):
      u8 kind(0..3: 0='h' hero art, 1='g', 2='a', 3='d'), u8 cls (art number: file h<cls:03d>*.xpf),
      s8 name (<=12 chars), s8 title, u32 unit id, u32 nation id, u16 x, u16 y, u16 hp,
      u8 (+0x360), u8 (+0x364), u8 mark (+0x368: 1 = prestige icon ui-pres*.xpf, 2 = cabinet ui-cabi.xpf),
      u8 rank (+0x36c: rank insignia frame 0..30 drawn left/right of the name with ui-rtl1/ui-rtr1.xpf, 0 = none).
    0x20 is the ONLY packet that sets mark/rank; a unit created by 0x18 alone keeps uninitialised memory there,
    which is why a random rank insignia showed up.  So the commander is put with 0x18 and then 0x20."""
    nb = wire_name(name).encode('latin-1')
    d = bytearray([0x20, kind, cls])
    tb = title[:40]                 # +0xc6 title line; client F41 prints it as "%s" in teal (was "<%s>" gray)
    d += bytes([len(nb)]) + nb + bytes([len(tb)]) + tb
    d += struct.pack(">II", uid, nation) + struct.pack(">HHH", x, y, hp) + bytes([0, 0, mark, rank])
    return bytes(d)

# PUT_UNIT 9 x u16 battle stats (+0xe..+0x1e), from the client (FUN_004ac800 and its readers):
#   [0] ARMOR (+0x11c; damage taken = attacker dmg - armor*(100+table[+0x130][dmg type])/100, FUN_004d0420/004cb080)
#   [1] armor class (+0x130, row of the damage-modifier table FUN_005261b0)   [2] damage type code 1xx..6xx (+0x120)
#   [3] GROUND damage (+0x134)  [4] ground range x20 (+0x138)  [5] ground cooldown x100 (+0x13c)
#   [6] AIR damage (+0x140)     [7] air range x20 (+0x144)     [8] air cooldown x100 (+0x148)
# Movement speed is NOT here: it is the header u16 at +9 (+0x14), speed x10 (100 = 10 m/s, what every unit had).
# A unit whose damage for the target's layer is 0 can not attack it (FUN_004c7d50): right-click only moves.
DEFAULT_WEAPON = {"Ground Damage": 60, "Ground Range": 10, "Ground Cooldown": 1.5}   # unit without a weapon item

import organs as ORG

def organ_of(u):
    """organic creature -> (weapon slot of its line, organ tier); None for everything else (organs.py).
    (21:24) None too when the organs are fitted as items (with_alien_engine): their stats then count like any item."""
    if not alien_chassis(u) or any(i in ORGAN_IDS for i in u.get("items", [])):
        return None
    name = DISPLAY.get(u["chassis"], u["chassis"])
    code = CODE_OF.get(name, u["chassis"])
    ws = next((sid for sid, k in UNIT_SLOTS.get(code, []) if k == "Weapon"), None)
    if ws not in ORG.WEAPONS:
        return None
    return ws, ORG.organ_tier(PG.unit_peak(u), chassis_influence(name))     # (10-31) a starred unit keeps its organs

def unit_weapon(u):
    """Combat values of a roster unit = its strongest equipped weapon (items.json, manual stats).
    Trebuchet: Astral LAUNCHER (range / cooldown, no damage) + mortar SHELL (ground damage) + flak ROUND (air)."""
    its = [ITEM_BY_ID.get(i, {}) for i in u.get("items", [])]
    launch = [it for it in its if it.get("type") == 4 and it.get("slot") == 4137]
    shells = [it for it in its if (it.get("ammo") or it.get("type") in (4, 9)) and it.get("slot") in (7137, 8137)]
    if launch and shells:
        ls = launch[0].get("stats", {})
        st = {"Energy Use": sum(float(it["stats"].get("Energy Use", 0) or 0) for it in shells)}
        for it in shells:
            for side in ("Ground", "Air"):
                if it["stats"].get(side + " Damage"):
                    st[side + " Damage"] = it["stats"][side + " Damage"]
                    st[side + " Range"] = float(ls.get(side + " Range", 0) or 0) + float(it["stats"].get("Range Bonus", 0) or 0)
                    st[side + " Cooldown"] = ls.get(side + " Cooldown", 0)
        return st
    best = None
    for i in u.get("items", []):
        it = ITEM_BY_ID.get(i, {})
        if it.get("type") != 4:
            continue
        st = it.get("stats", {})
        v = float(st.get("Ground Damage", 0) or 0) + float(st.get("Air Damage", 0) or 0)
        if v <= 0:
            continue        # Trebuchet launchers: range/cooldown only, the shells (not in items.json) do the damage
        if best is None or v > best[0]:
            best = (v, st)
    _org = organ_of(u)
    if _org:                    # (14:58) organic creature: its natural weapon (manual W-3xx tiers) unless an item is stronger
        ow = ORG.organ_weapon(*_org)
        ov = float(ow.get("Ground Damage", 0) or 0) + float(ow.get("Air Damage", 0) or 0)
        if best is None or ov > best[0]:
            return ow
    return best[1] if best else DEFAULT_WEAPON

import damage_types as DT
# Damage types (design claude/DAMAGE_ARMOR_DESIGN.md).  stats9[1] = armour class, stats9[2] = damage code (class*100 +
# projectile picture).  The damage code also changes the projectile / hit effect, so it stays off until the effects
# of classes 1..6 are checked in game: GM /dmgtest CODE puts that code on every player unit of the next battle.
DAMAGE_TYPES = True        # 2026-10-21 user: everything like the original
DMG_TEST_CODE = None

def unit_damage_classes(u):
    """(armour class row, damage code) of a roster unit."""
    items = [ITEM_BY_ID[i] for i in u.get("items", []) if i in ITEM_BY_ID]
    is_air = str(CODE_OF.get(DISPLAY.get(u["chassis"], u["chassis"]), u["chassis"]))[:1] == "a"
    row = DT.armour_row(items, is_air)
    best = None
    for it in items:
        if it.get("type") == 4:
            st = it.get("stats", {})
            v = float(st.get("Ground Damage", 0) or 0) + float(st.get("Air Damage", 0) or 0)
            if best is None or v > best[0]:
                best = (v, it)
    _org = organ_of(u)
    if _org and not any(it.get("type") == 5 for it in items):
        row = DT.ALIEN                       # natural hide = the wild aliens' carapace row
    _oi = [it for it in items if it.get("organ")]
    if any(it.get("type") == 5 for it in _oi) and not any(it.get("type") == 5 and not it.get("organ") for it in items):
        row = DT.ALIEN                       # (21:24) the hide fitted as an organ item: same carapace row
    if best and best[1].get("organ"):
        best = None                          # natural weapon item: the creature's own effect below (Oizys: flame)
        if any(it.get("slot") == 4311 for it in _oi):
            _org = (4311, 0)
    if _org and unit_weapon(u) is not (best[1].get("stats") if best else None):
        best = None                          # the natural weapon is the one used -> its effect below
    code = DT.damage_code(best[1]) if best else 0
    if not code and _org and _org[0] == 4311:
        code = 301                           # Oizys: "magma hot breath" -> flame
    if not code and alien_chassis(u):
        # 2026-10-22 12:41 (user: an alien attacks with a stream of green shots): a player's alien creature has no
        # weapon item -> code 0 drew no projectile.  Same acid projectile as the wild aliens (aliens.py ROLES fx).
        _art = CODE_OF.get(DISPLAY.get(u["chassis"], u["chassis"]), u["chassis"])
        code = next((r.get("fx", 0) for r in AL.ROLES.values() if r["code"] == _art), 0) \
            or (230 if str(_art)[:1] == "a" else 205)
    if DMG_TEST_CODE is not None:
        code = DMG_TEST_CODE
    elif not DAMAGE_TYPES:
        code = 0
    return (row if (DAMAGE_TYPES or DMG_TEST_CODE is not None) else 0), code

import re as _re
_TARGET_RANGE_RE = _re.compile(r"increases the target range by ([0-9.]+) met", _re.I)

def unit_stats9(u):
    mu = UNIT_MANUAL.get(str(DISPLAY.get(u["chassis"], u["chassis"])).lower(), {})
    w = unit_weapon(u)
    c = lambda v, m=1: max(0, min(65535, int(round(float(v or 0) * m))))
    armor = float(mu.get("base_armor", 0) or 0) + sum(float(ITEM_BY_ID.get(i, {}).get("stats", {}).get("Armor", 0) or 0)
                                                      for i in u.get("items", []))
    _org = organ_of(u)
    if _org:
        armor += ORG.organ_hide(*_org)[1]
    # sensors "add N meter weapon range" (their Ground/Air Range), Biostimulator +3 armor, +0.5 m range (desc)
    gb = ab = 0.0
    for i in u.get("items", []):
        it = ITEM_BY_ID.get(i, {})
        st = it.get("stats", {})
        if it.get("type") != 4:
            gb += float(st.get("Ground Range", 0) or 0)
            ab += float(st.get("Air Range", 0) or 0)
            # (15:17) artillery sensors TACS M1-M5 / RTS SG1-SG5 (Arbalest / Ballista bonus slot 6201): the manual gives
            # them range 0 and says "increases the target range by N meters" in the text -> that N is the range bonus
            _m = _TARGET_RANGE_RE.search(it.get("desc") or "")
            if _m:
                gb += float(_m.group(1)); ab += float(_m.group(1))
        if it.get("name") == "Biostimulator":
            armor += 3; gb += 0.5; ab += 0.5
    row, code = unit_damage_classes(u)
    # no damage on a side -> no range on that side (Ballista flak showed a 50 m ground weapon with 0 damage)
    gr = (float(w.get("Ground Range") or 0) + gb) if w.get("Ground Damage") else 0
    if not gr and w.get("Special") == "Air Bombard":
        # (17:01) Ballista "Flak Attack" fires at a POINT (the ground cell under the aircraft): the client checks the
        # distance with the GROUND range, which was 0 for flak-only weapons -> the attack had no reach
        gr = float(w.get("Air Range") or w.get("Ground Range") or 0) + ab
    ar = (float(w.get("Air Range") or 0) + ab) if w.get("Air Damage") else 0
    _sm = PG.star_mult(u)                       # (10-31) +3 % damage per star
    return [c(armor), row, code,
            c(w.get("Ground Damage"), _sm), c(gr, 20), c(w.get("Ground Cooldown"), 100),
            c(w.get("Air Damage"), _sm), c(ar, 20), c(w.get("Air Cooldown"), 100)]

def unit_view_px(u):
    """ORIGINAL sight (CONFIRMED 2026-10-21, 004cad50 / 004c71c0 / 0048dd30): 20 px per metre; a unit attacks only
    what is inside ITS OWN sight; chassis view + every item's View Range (sensors 'add' view) + 0.5 m Biostimulator."""
    mu = UNIT_MANUAL.get(str(DISPLAY.get(u["chassis"], u["chassis"])).lower(), {})
    m = float(mu.get("view_range_m", 0) or 0)
    for i in u.get("items", []):
        it = ITEM_BY_ID.get(i, {})
        m += float(it.get("stats", {}).get("View Range", 0) or 0)
        if it.get("name") == "Biostimulator":
            m += 0.5
    # (17:36, user) in bombArd (state 9) / Flak Attack (state 11) mode the client's fog painter (0048ea50, jump table
    # 0048ec10) reveals a circle of the unit's SIGHT radius (+0x114) centred one GROUND range (+0x138) ahead of it
    # (004c5500 / 004c7700).  Trebuchet has view 0 and no artillery-sensor slot -> radius 1 m, its target area stayed
    # in the fog.  Artillery gets at least the Arbalest's (2 m + TACS M1 5 m) so the shelled area opens like it does.
    if str(CODE_OF.get(DISPLAY.get(u["chassis"], u["chassis"]), u["chassis"])).lower() in ARTILLERY_ART:
        m = max(m, ARTILLERY_MIN_VIEW_M)
    return max(20, min(65535, int(round(m * 20))))

ARTILLERY_ART = {"g010", "g034", "g037"}      # Arbalest, Ballista, Trebuchet
ARTILLERY_MIN_VIEW_M = 7.0

def unit_speed(u):
    """PUT_UNIT header +9: movement speed x10 from the manual (Behemoth 1.2 m/s -> 12)."""
    mu = UNIT_MANUAL.get(str(DISPLAY.get(u["chassis"], u["chassis"])).lower(), {})
    return max(1, min(65535, int(round(float(mu.get("speed_m_s", 10) or 10) * 10))))

def unit_sight(st9):
    """+0xb sight (+0x114): the attack test also needs distance <= sight, so keep it above the weapon range."""
    return max(st9[4], st9[7], 240) + 80

# training targets: they stand still-ish and do not shoot back
TARGET_STATS9 = [0, 0, 0, 0, 0, 100, 0, 0, 100]

def unit_battle_stats(u):
    """HP / energy of a roster unit = official manual base + its equipped items (items.json stats)."""
    mu = UNIT_MANUAL.get(str(DISPLAY.get(u["chassis"], u["chassis"])).lower(), {})
    hp = float(mu.get("base_health", 1000))
    en = 0.0
    for i in u.get("items", []):
        st = ITEM_BY_ID.get(i, {}).get("stats", {})
        hp += float(st.get("Health", 0) or 0)
        en += float(st.get("Max Energy", 0) or 0)
    _org = organ_of(u)
    if _org:
        hp += ORG.organ_hide(*_org)[0]
    return int(hp), int(en or 1000)

ABILITY_ATTACK = 0x2       # PUT_UNIT ability bit 1 = can attack
