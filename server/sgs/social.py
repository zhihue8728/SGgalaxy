# sgserver part "social": FHQ, directory, user info, chat, regiments, mailbox.
# Loaded by sgserver.py into ONE shared namespace (exec, in the order of PARTS) - not an importable module;
# every name here is a sgserver global.  Checks: python tools/check_server.py
# ---- FHQ: ELECTIONS / DOMESTIC / FOREIGN POLICY (client 0x36 -> server 0x37, research_social.md) --------------------
# client 0x36 [u32 nation][u8 kind][u8 op][...]; kind 0 = Vote window, 1 = Domestic Policy, 2 = Foreign Policy.
#   kind 0 ops: 0 info, 1 campaign [s16 statement], 2 cancel campaign, 3 support [s8], 4 oppose [s8], 5 nominate [s8],
#               6 vote [s8], 7 statement [s16]          kind 2 op 2 = nation statement [s16]
# server 0x37 [kind][u32 nation]...:
#   kind 0: [sub 0][u32 nation][s8 name][s8 ?][u8][u8][s8 ?][u8][u32 votes][u8 x4][u16 support][u16 oppose][s8 statement]
#           sub 1/2 = list: [sub][u32 nation][u8 n] then n records without the leading u32
#   kind 1: u16 x3, u32 x5, u16 x4, u8, u16 x3, u8, u8 n {u16 slot, s8, s8, s8, u32}
#   kind 2: [sub 0][u8 n] {u32 nation, u16, u8, u16 x8, s16 text}   or [sub 1][s16 message]
# NOTE field meanings of the unknown u8/u16 are provisional (calibrate with in-game screenshots).
# PRESIDENTIAL ELECTION (user 2026-10-26 23:37; client F37 brings the FHQ hall's Vote button back):
#   one term = ELECTION_SECONDS (7 days): the first NOMINATION_SECONDS (3 days) candidates register (campaign /
#   nominate) and collect support / opposition, the last 4 days the citizens vote; at the end the most votes win
#   (ties: more support - opposition), no candidate = the president stays.
#   Only citizens of the nation; voting / support needs division level ELECT_VOTE_LEVEL, running ELECT_RUN_LEVEL;
#   one vote per public IP (against alt accounts) - a player may change his own vote.
ELECTION_SECONDS = 7 * 24 * 3600
NOMINATION_SECONDS = 3 * 24 * 3600
ELECT_VOTE_LEVEL = 10
ELECT_RUN_LEVEL = 30

def politics(nid):
    global WORLD
    if WORLD is None:
        WORLD = load_world()
    p = WORLD.setdefault("politics", {}).setdefault(str(nid), {})
    p.setdefault("president", ""); p.setdefault("candidates", {}); p.setdefault("statement", "")
    p.setdefault("election_end", time.time() + ELECTION_SECONDS)
    if p.get("cycle") != ELECTION_SECONDS:                 # old 24 h cycles: this term now runs the new length
        p["election_end"] = max(p["election_end"], time.time() + ELECTION_SECONDS)
        p["cycle"] = ELECTION_SECONDS
    p.setdefault("vote_ip", {})
    p.setdefault("tax", [10, 10, 10]); p.setdefault("treasury", [0, 0, 0, 0, 0]); p.setdefault("council", {})
    return p

def save_politics():
    save_world(WORLD)

def resolve_election(nid):
    p = politics(nid)
    if time.time() < p["election_end"]:
        return False
    c = p["candidates"]
    if c:
        win = max(c, key=lambda n: (len(c[n]["votes"]), len(c[n]["support"]) - len(c[n]["oppose"])))
        old = p.get("president")
        p["president"] = win; p["statement"] = c[win].get("statement", "")
        if (old or "").lower() != win.lower():
            p["pres_support"], p["pres_oppose"] = {}, {}            # the new Overlord starts with a clean record
        try:
            nation_say(nid, "{} is the new president of the faction ({} votes).".format(display_name(win), len(c[win]["votes"])),
                       (255, 220, 80))
        except Exception:
            pass
        try:
            refresh_hero_marks(*[x for x in (old, win) if x])          # gold mark moves to the new president
        except Exception:
            pass
        log(f"   nation {nid}: election won by {win} ({len(c[win]['votes'])} vote(s))")
    p["candidates"] = {}
    p["vote_ip"] = {}
    p["vote_announced"] = False
    p["election_end"] = time.time() + ELECTION_SECONDS
    save_politics()
    return True

# RECALL (user 2026-10-27 "可以"): the original FHQ text "too much opposition = an immediate election".
#   Same day opposition >= RECALL_MIN and >= RECALL_RATIO x same day support -> the Overlord is removed at once
#   (mark cleared, nation told) and a fresh term starts now: NOMINATION_SECONDS of registration, then voting.
#   Candidates already registered stay.  No candidate at the end -> the seat stays empty until a later term.
RECALL_MIN = 5
RECALL_RATIO = 2

def recall_check(nid, p):
    today = time.strftime("%Y-%m-%d")
    opp = sum(1 for d in p.get("pres_oppose", {}).values() if d == today)
    sup = sum(1 for d in p.get("pres_support", {}).values() if d == today)
    old = p.get("president")
    if not old or opp < RECALL_MIN or opp < RECALL_RATIO * sup:
        return False
    p["president"] = ""; p["statement"] = ""
    p["pres_support"], p["pres_oppose"] = {}, {}
    p["vote_ip"] = {}; p["vote_announced"] = False
    for c in p["candidates"].values():
        c["votes"] = []
    p["election_end"] = time.time() + ELECTION_SECONDS
    save_politics()
    log(f"   nation {nid}: president {old} recalled ({opp} oppose / {sup} support today)")
    try:
        nation_say(nid, "{} was recalled by the citizens ({} oppose, {} support). A new election starts now - register in the FHQ (Vote).".format(
            display_name(old), opp, sup), (255, 120, 80))
    except Exception:
        pass
    try:
        refresh_hero_marks(old)
    except Exception:
        pass
    return True

def election_voting(p):
    """True in the voting days of the term (after the nomination days)."""
    return time.time() >= p["election_end"] - (ELECTION_SECONDS - NOMINATION_SECONDS)

def nation_say(nid, text, rgb=(255, 220, 80)):
    for o in list(ONLINE):
        if getattr(o, "logged_in", False) and getattr(o, "cmd", {}).get("nation") == nid and not o.w.is_closing():
            o.send(chat_line(0x0A, text, rgb))

async def election_cycle():
    """every minute: end terms that are over, tell the citizens when voting begins."""
    while True:
        await asyncio.sleep(60)
        try:
            for n in NATIONS:
                nid = n[0]
                resolve_election(nid)
                p = politics(nid)
                if p["candidates"] and election_voting(p) and not p.get("vote_announced"):
                    p["vote_announced"] = True
                    save_politics()
                    nation_say(nid, "Voting for president has started - vote in the FHQ (Vote).")
        except Exception as e:
            log(f"   election cycle: {e!r}")

# VOTE WINDOW (server 0x37 kind 0; client parser 005e7770, reverse engineered 2026-10-26 23:50):
#   [u8 sub][u32 MINUTES remaining (window +0x59f4, "TIME REMAINING")] then
#   sub 0 = the Overlord in service (status "position occupied, no nominations"): ONE record
#   sub 1 = nomination period / sub 2 = voting period: [u8 n] n records (candidates)
#   record = s8 A, s8 B, u8, u8, s8 C, u8, u32, u8 x4, u16, u16, s16 STATEMENT  (005e74e0 keeps 15 values)
#   Field meanings below are the best reading of the window (NAME, TITLE, SPECIALTY, RANK, LEVEL, HONOR, PRESTIGE,
#   TACTICS, CLOUT, EDUCATION, MECH APT, support / oppose); GM /votedebug fills every field with a marker so one
#   screenshot shows the real mapping.  (Before: the statement went out as s8 -> the client read a u16 length.)
VOTE_DEBUG = False

def stmt_text(t):
    """(user 2026-10-26 23:55: Chinese statements came out as ???) statements are stored as real text now (decoded with
    the writer's code page); older ones were the raw GBK / Big5 bytes kept as latin-1 characters -> decoded here."""
    t = str(t or "")
    if t and all(ord(ch) < 0x100 for ch in t) and any(ord(ch) >= 0x80 for ch in t):
        raw = t.encode("latin-1")
        for enc in ("gbk", "cp950"):
            try:
                return raw.decode(enc)
            except UnicodeDecodeError:
                pass
    return t

def _vote_record(name, c, s=None):
    _sx = s if s is not None else type("_S", (), {"lang": "en", "enc": "latin-1"})()
    sup, opp = len(c.get("support", [])), len(c.get("oppose", []))
    st = stmt_text(c.get("statement", "")).encode(getattr(_sx, "enc", "latin-1"), "replace")[:1000]
    if VOTE_DEBUG:
        st = b"STATEMENT_S"
        return (_s8("NAME_A") + _s8("TITLE_B") + bytes([1, 7]) + _s8("PRES_C") + bytes([33]) + struct.pack(">I", 444444)
                + bytes([55, 66, 77, 88]) + struct.pack(">HH", 999, 1010) + struct.pack(">H", len(st)) + st)
    a = load_accounts().get(name) if name else None
    cmd = (a or {}).get("commander", {}) if isinstance(a, dict) else {}
    br = cmd.get("branches") or {}
    keys = list(PG.BRANCHES)
    lv = {k: int((br.get(k) or {}).get("level", 1) or 1) for k in keys}
    top_k = max(keys, key=lambda k: lv[k]) if name and br else keys[0]
    top = lv[top_k] if name and br else 0
    attrs = list(cmd.get("attrs", [0, 0, 0, 0]) or [0, 0, 0, 0]) + [0, 0, 0, 0]
    title = rank_for(_sx, top, cmd.get("reincarnations", 0)) if name and br else ""
    try:
        prest = str(pr_of(cmd)) if name and cmd else ""
    except Exception:
        prest = ""
    # 1st u8 = PORTRAIT number (005e3a60: sprintf "Hero-%02d.xpf"), like the F4 window - it was the branch index 0 (no picture)
    look = max(1, min(int(cmd.get("look", 1) or 1), 11)) if name else 0
    return (_s8(name or "") + _s8e(_sx, title) + bytes([look, min(rank_index(top), 255) if name else 0])
            + _s8(prest) + bytes([min(top, 255)]) + struct.pack(">I", int(cmd.get("honor", 0) or 0) // 100)
            + bytes([min(int(x or 0), 255) for x in attrs[:4]]) + struct.pack(">HH", min(sup, 65535), min(opp, 65535))
            + struct.pack(">H", len(st)) + st)

def build_vote_info(nid, s=None):
    """sub 0 (Overlord in service) or sub 1 (nominations) / sub 2 (voting) with the candidates."""
    p = politics(nid)
    now = time.time()
    vote_from = p["election_end"] - (ELECTION_SECONDS - NOMINATION_SECONDS)
    cl = p["candidates"]
    if not election_voting(p):
        sub, mins = 1, (vote_from - now) / 60                 # nominations are open: candidates may register
    elif cl:
        sub, mins = 2, (p["election_end"] - now) / 60
    else:
        sub, mins = 0, (p["election_end"] - now) / 60          # voting days without a candidate: the Overlord stays
    mins = max(0, min(int(mins), 0xFFFFFFFF))
    pres = p["president"]
    pc = {"support": list(p.get("pres_support", {})), "oppose": list(p.get("pres_oppose", {})),
          "statement": p.get("statement", "")}
    d = bytes([0x37, 0]) + struct.pack(">I", nid) + bytes([0]) + struct.pack(">I", mins) + _vote_record(pres, pc, s)
    if sub == 0:
        return [d]
    d2 = bytes([0x37, 0]) + struct.pack(">I", nid) + bytes([sub]) + struct.pack(">I", mins) + bytes([min(len(cl), 255)])
    for n, c in list(cl.items())[:255]:
        d2 += _vote_record(n, c, s)
    return [d, d2]

def nation_stats(nid):
    """real numbers for the FHQ windows: members, online, provinces, wins, losses."""
    accs = load_accounts()
    members = [n for n, a in accs.items() if a.get("commander", {}).get("nation") == nid]
    wins = sum(accs[n]["commander"].get("wins", 0) for n in members)
    losses = sum(accs[n]["commander"].get("losses", 0) for n in members)
    online = sum(1 for o in ONLINE if getattr(o, "logged_in", False) and not o.w.is_closing()
                 and getattr(o, "cmd", {}).get("nation") == nid)
    global WORLD
    if WORLD is None:
        WORLD = load_world()
    return {"members": len(members), "online": online, "provinces": owned_provinces(nid),
            "wins": wins, "losses": losses}

COUNCIL_SEATS = 13              # (old) lines the window shows at once; the client keeps COUNCIL_ROWS records
# COUNCIL = the faction's REGIMENTS (user 2026-11-03 00:01: assigning a power gave "无效！请检查是否重复指派同一军团或
# 议会成员"; 00:02 "議員名稱不應該能被刪除").  Client facts (SG.exe 1.8.5):
#   - 0047c860: the window always keeps 100 records: the n the server sent, then 100 - n fillers "空字段 (%d)" with an
#     EMPTY title and name;
#   - 0047b7e0 (OK): every one of the 100 records' edit lines is trimmed (00550700: ASCII space / tab / CR / LF) and must
#     have a regiment, a title and a name, regiments and names each unique - else ksInvalidCouncil.  So an empty seat (or
#     a blank " " record, what the server sent until now) always made it invalid.
# Now: one record per regiment of the faction (name, leader title, leader), the powers the president gave it, and the
# other seats up to 100 are INVISIBLE but valid fillers (full-width spaces, not trimmed by the client, each different).
# The president can only change the POWERS: what he types into the regiment / title / name columns is ignored and
# the next answer shows the server's names again.
COUNCIL_ROWS = 100
COUNCIL_POWER_BITS = 0x0F       # SHOUT, MARTIAL LAW, PUNISH, HEALTH BONUS

def _council_filler(k, enc):
    """an invisible, untrimmable, unique text for filler seat k (0..127)"""
    fw = "\u3000" if enc in ("gbk", "cp936", "cp950", "big5") else "\xa0"
    inner = "".join(fw if (k >> b) & 1 else " " for b in range(7))
    return (fw + inner + fw).encode(enc, "replace")

def _council_regiments(nid):
    return sorted(((n, g) for n, g in load_regiments().items() if int(g.get("nation", 0) or 0) == nid),
                  key=lambda kv: (-len(kv[1].get("members", [])), kv[0]))[:COUNCIL_ROWS]

def _council_powers(nid):
    """{regiment: power bits}; (11-03) an older president-made council (p["council"]) gives its powers once"""
    p = politics(nid)
    pw = p.setdefault("council_powers", {})
    if p.get("council"):
        regs = {n for n, _g in _council_regiments(nid)}
        for r in p["council"].values():
            if isinstance(r, list) and len(r) >= 4 and str(r[0]) in regs and str(r[0]) not in pw:
                pw[str(r[0])] = int(r[3]) & COUNCIL_POWER_BITS
        p["council"] = {}
        save_politics()
    return pw

def _council_rows(nid, s=None):
    lang = getattr(s, "lang", "en") if s is not None else "en"
    enc = getattr(s, "enc", "latin-1") if s is not None else "latin-1"
    title = {"zh-cn": "团长", "zh-tw": "團長"}.get(lang, "Leader").encode(enc, "replace")
    pw = _council_powers(nid)
    out, used_names = b"", set()
    regs = _council_regiments(nid)
    for k, (n, g) in enumerate(regs, 1):
        a = str(n).encode(enc, "replace")[:30]
        c = str(display_name(str(g.get("leader", ""))) or "?").encode(enc, "replace")[:26]
        while c in used_names:                       # one commander leading two regiments: names must differ
            c += _council_filler(len(used_names), enc)[:2]
        used_names.add(c)
        out += struct.pack(">H", k) + b"".join(bytes([len(x)]) + x for x in (a, title, c)) \
            + struct.pack(">I", int(pw.get(n, 0)) & COUNCIL_POWER_BITS)
    for k in range(len(regs) + 1, COUNCIL_ROWS + 1):
        f = _council_filler(k, enc)
        out += struct.pack(">H", k) + (bytes([len(f)]) + f) * 3 + struct.pack(">I", 0)
    return COUNCIL_ROWS, out

def council_save(nid, rows):
    """the president's OK: only the powers of the faction's regiments are taken (names / titles are the server's)"""
    pw = _council_powers(nid)
    regs = {n for n, _g in _council_regiments(nid)}
    seen = 0
    for _slot, a, _b, _c, v in rows:
        a = str(a).strip().strip("\u3000\xa0")
        if a in regs:
            pw[a] = int(v) & COUNCIL_POWER_BITS
            seen += 1
    save_politics()
    return seen

def build_domestic(nid, s=None):
    p = politics(nid)
    st = nation_stats(nid)
    tr = p["treasury"]
    # u16 x3 (first unused by the screen), the two numbers on the left, 5 treasury resources, then the record block
    b = struct.pack(">HHH", 0, min(st["members"], 65535), min(st["provinces"], 65535))
    b += b"".join(struct.pack(">I", int(x)) for x in tr)
    b += struct.pack(">HH", min(st["wins"], 65535), min(st["losses"], 65535))        # record row 1 (and 2)
    b += struct.pack(">HH", 0, 0)                                                      # row 3
    b += bytes([0]) + struct.pack(">HHH", 0, 0, 0) + bytes([0])                        # row 4, minutes
    n_, rows = _council_rows(nid, s)
    b += bytes([n_]) + rows
    return bytes([0x37, 1]) + struct.pack(">I", nid) + b

def _faction_desc(n, nid, s=None):
    """(21:24) default FACTION DESCRIPTION when the president wrote none: capital, provinces, relation to the viewer."""
    lang = getattr(s, "lang", "en") if s is not None else "en"
    st = nation_stats(n)
    cap = province_number(CAPITALS.get(n, 0)) if CAPITALS.get(n) else 0
    allies = [nation_name(x, lang) for x, *_r in NATIONS if x != n and same_side(x, n) and nation_planet(x) == nation_planet(n)]
    rel = "own" if n == nid else ("ally" if same_side(n, nid) else "enemy")
    if lang in ("zh-cn", "zh-tw"):
        relz = {"own": ("本国", "本國"), "ally": ("同盟", "同盟"), "enemy": ("敌对", "敵對")}[rel][lang == "zh-tw"]
        al = "、".join(allies) or ("无" if lang == "zh-cn" else "無")
        return (f"{nation_name(n, lang)}（{relz}）首都：{cap}号省，领土 {st['provinces']} 省，成员 {st['members']} 人，同盟：{al}。"
                if lang == "zh-cn" else
                f"{nation_name(n, lang)}（{relz}）首都：{cap}號省，領土 {st['provinces']} 省，成員 {st['members']} 人，同盟：{al}。")
    return (f"{nation_name(n, lang)} ({rel}): capital #{cap}, {st['provinces']} provinces, {st['members']} members, "
            f"allies: {', '.join(allies) or 'none'}.")

def build_foreign(nid, s=None):
    # (21:24) every faction of the planet, the viewer's own first (the 4th column stayed empty)
    rows = sorted((n for n in NATIONS if nation_planet(n[0]) == nation_planet(nid)), key=lambda n: (n[0] != nid, n[0]))
    d = bytes([0x37, 2]) + struct.pack(">I", nid) + bytes([0, len(rows)])
    for n in rows:
        st = nation_stats(n[0])
        # u32 nation, u16 MEMBERS, u8 PLANET, then u16: PROVINCES, MOBILITY now, MOBILITY max, INVASION minutes,
        # RECORD win, RECORD lose, (2 unused), s16 faction description
        d += struct.pack(">IHB", n[0], min(st["members"], 65535), nation_planet(n[0]) & 0xFF)
        d += struct.pack(">8H", min(st["provinces"], 65535), min(st["online"], 65535), min(st["members"], 65535), 0,
                         min(st["wins"], 65535), min(st["losses"], 65535), 0, 0)
        _txt = stmt_text(politics(n[0]).get("statement", "")) or _faction_desc(n[0], nid, s)
        _tb = str(_txt).encode(getattr(s, "enc", "latin-1") if s is not None else "latin-1", "replace")[:1000]
        d += struct.pack(">H", len(_tb)) + _tb
    return d

def fhq_request(s, body):
    nid, kind, op = struct.unpack_from(">IBB", body, 1)
    mine = getattr(s, "cmd", {}).get("nation", 1)
    resolve_election(nid)
    p = politics(nid)
    me = s.acc
    log(f"   FHQ request nation {nid} kind {kind} op {op} by {me}")
    def say(t):
        s.send(chat_line(0x0A, t, (255, 200, 0)))
    if kind == 0:
        if op in (1, 2, 3, 4, 5, 6, 7) and nid != mine:          # (2026-10-26) allies do not vote either
            say("Only citizens of this nation can take part in its election."); return
        _lv = _cmd_level(getattr(s, "cmd", {}) or get_account(me)[1].get("commander", {}))
        try:
            _lv = max(_lv, _cmd_level(get_account(me)[1].get("commander", {})))
        except Exception:
            pass
        voting = election_voting(p)
        refuse = None
        if op in (1, 5) and voting:
            refuse = "Registration is closed: the vote has started."
        elif op == 1 and _lv < ELECT_RUN_LEVEL:
            refuse = "You need division level {} to run for president.".format(ELECT_RUN_LEVEL)
        elif op in (3, 4, 6) and _lv < ELECT_VOTE_LEVEL:
            refuse = "You need division level {} to vote.".format(ELECT_VOTE_LEVEL)
        elif op == 6 and not voting:
            refuse = "Voting has not started yet."
        elif op == 6:
            ip = (getattr(s, "peer", None) or ("?",))[0]
            prev = p["vote_ip"].get(ip)
            if prev and prev.lower() != me.lower():
                refuse = "Someone from your network has already voted."
        if op == 5 and not refuse:
            _n5, _o5 = read_s8(body, 7)
            _acc5 = nick_account(_n5) if _n5 else ""
            _a5 = load_accounts().get(_acc5) or {}
            _c5 = _a5.get("commander", {}) if isinstance(_a5, dict) else {}
            if not _c5 or _c5.get("nation") != nid or _cmd_level(_c5) < ELECT_RUN_LEVEL:
                refuse = "{} is not a citizen of this faction or below division level {}.".format(_n5, ELECT_RUN_LEVEL)
        if refuse:
            say(refuse)
            for pk in build_vote_info(nid, s):
                s.send(pk)
            return
        arg8 = arg16 = ""
        if op in (3, 4, 5, 6):
            arg8, _o = read_s8(body, 7)
        elif op in (1, 7) and len(body) >= 9:
            ln = struct.unpack_from(">H", body, 7)[0]; arg16 = body[9:9 + ln].decode(getattr(s, "enc", "latin-1"), "replace")
        c = p["candidates"]
        if op == 1:
            if me in c:                                          # re-register = new statement, keep the record
                c[me]["statement"] = arg16[:250]
            else:
                c[me] = {"statement": arg16[:250], "support": [], "oppose": [], "votes": []}
        elif op == 2:
            c.pop(me, None)
        elif op in (3, 4) and arg8 and p["president"] and arg8.lower() == p["president"].lower():
            today = time.strftime("%Y-%m-%d")
            ps, po = p.setdefault("pres_support", {}), p.setdefault("pres_oppose", {})
            if ps.get(me) == today or po.get(me) == today:
                say("You can only support or oppose the Overlord once per day.")
            else:
                ps.pop(me, None); po.pop(me, None)
                (ps if op == 3 else po)[me] = today
                if op == 4:
                    recall_check(nid, p)
        elif op in (3, 4) and arg8 in c:
            for k in ("support", "oppose"):
                if me in c[arg8][k]: c[arg8][k].remove(me)
            c[arg8]["support" if op == 3 else "oppose"].append(me)
        elif op == 5:
            if arg8 and arg8 not in c:
                c[arg8] = {"statement": "", "support": [], "oppose": [], "votes": []}
        elif op == 6 and arg8 in c:
            for cc in c.values():
                if me in cc["votes"]: cc["votes"].remove(me)
            c[arg8]["votes"].append(me)
            p["vote_ip"][(getattr(s, "peer", None) or ("?",))[0]] = me
        elif op == 7:
            # (user 2026-10-27 00:06 "Statement 點擊 done 後，輸入的內容沒有保存") STATEMENT -> DONE sends op 7 for
            # whoever types it: a candidate's statement is shown from his candidate record, so save it there too
            # (before only the Overlord's own field was written and a candidate's text was dropped).
            if me in c:
                c[me]["statement"] = arg16[:250]
            if (p["president"] or "").lower() == me.lower():
                p["statement"] = arg16[:250]
            log(f"   FHQ statement by {me}: {arg16[:60]!r}")
        save_politics()
        for pk in build_vote_info(nid, s):
            s.send(pk)
    elif kind == 1:
        if op == 1 and p["president"] == me and len(body) >= 8:
            try:
                n = body[7]; o = 8; cs = []
                for _ in range(n):
                    slot = struct.unpack_from(">H", body, o)[0]; o += 2
                    a, o = read_s8(body, o); b2, o = read_s8(body, o); c2, o = read_s8(body, o)
                    v = struct.unpack_from(">I", body, o)[0]; o += 4
                    a = a.encode("latin-1").decode(getattr(s, "enc", "latin-1"), "replace")   # (11-03) Chinese names
                    cs.append((slot, a, b2, c2, v))
                k = council_save(nid, cs)
                log(f"   council of nation {nid} saved: powers of {k} regiment(s)")
            except Exception as e:
                log(f"   council: bad packet {body.hex()} ({e})")
        elif op == 1:
            say("Only the president can change the council.")
        s.send(build_domestic(nid, s))
    elif kind == 2:
        if op == 2 and len(body) >= 9 and p["president"] == me:
            ln = struct.unpack_from(">H", body, 7)[0]
            p["statement"] = body[9:9 + ln].decode(getattr(s, "enc", "latin-1"), "replace")[:250]; save_politics()
        s.send(build_foreign(nid, s))

# ---- PLAYER DIRECTORY + HALL OF FAME (research_social.md) -------------------------------------------------------
# Player directory (client cache keyed by (u32 uid, u16 k), filled by FUN_0057e400 / FUN_0057e5e0):
#   server 0x3b = one entry   [u32 uid][u16 k][u8 a][s8 name][u16 b][s8 c]      (answer to client 0x3c [u32 uid][u16 k])
#   server 0x3a = many        [u16 n] n x (same entry)                         (answer to client 0x3b [])
# Hall of fame (client 0x12 [u8 kind] -> server 0x12 [kind][u16 n] rows; FUN_004f8820):
#   kinds 1-4 row: [u32 uid][u16 k][u8 p5][u8 p6][u8 p7][u32 p8][u32 p9][u8 p10][u16 win][u16 lose] (+ [u16] for kind 1),
#     kind 1 is followed by a trailing [u16 total].  The row draw (FUN_004f5a50) shows p5 and p7 as "%d", p6 as a short
#     text, p8 as a number, p9/100 as a number, p10 (<5) as an icon index, win/lose as "%5d /%5d" and a win-rate %.
#   kinds 5/6 are sent empty (layouts known, meaning not).
HOF_DEBUG = False       # /hofdebug: fill every field with a recognisable marker so a screenshot reveals the mapping

def uid_of(name):
    return zlib.crc32(name.lower().encode("latin-1", "replace")) & 0x7FFFFFFF

def player_entry(name, cmd, k=0):
    return (struct.pack(">IHB", uid_of(name), k, cmd.get("nation", 1) & 0xFF) + _s8(name)
            + struct.pack(">H", min(pr_of(dict(cmd)), 65535)) + _s8(""))

def build_directory(only=None, k=0):
    accs = load_accounts()
    rows = [(n, a["commander"]) for n, a in accs.items() if "commander" in a and (only is None or uid_of(n) == only)]
    try:
        rows += npc_directory_rows(only)         # NPC commanders look like normal players (user 2026-10-22 13:13)
    except Exception as e:
        log(f"   npc directory error: {e!r}")
    return rows

def handle_directory(s, body):
    t = body[0]
    # the directory is the REGIMENT list (see regiment_entry)
    if t == 0x3C and len(body) >= 7:
        _uid, k = struct.unpack_from(">IH", body, 1)
        for n, g in load_regiments().items():
            if g.get("id") == k:
                s.send(bytes([0x3B]) + regiment_entry(n, g, getattr(s, "enc", "latin-1")))
    elif t == 0x3B:
        s.send(build_regiment_list(getattr(s, "enc", "latin-1")))

def hof_row(kind, name, cmd):
    w, l = int(cmd.get("wins", 0)), int(cmd.get("losses", 0))
    # the client reads an s8 NAME (limit 20) first (its error report "string packet error1: len 82, limit 20" showed it
    # reading the first uid byte as a length), then the fixed part
    nm = _s8(name[:19])
    # user 2026-10-24 12:48 (F6 who-list: FACTION empty, LEVEL 0).  Row draw 004f5a50 (row record from 004f8770):
    #   u32 -> row+0x40 = NATION id: FACTION column = nation table 00551ec0(it) (name + colour +0x10a) - we sent the
    #          name's crc, which no nation has -> empty;
    #   u16 -> row+0x44 = REGIMENT key: directory cache 0057e310 (compares only the u16, like the F4 window);
    #   p5 -> +0x48 = LEVEL ("%d"), p7 -> +0x4d = branch 0..3: with the window flag +0x764 set the LEVEL column shows
    #          the rank name 0057a550(branch, level) in the branch colour 0057a520 instead;
    #   p8 -> +0x50 PR, p9 -> +0x54 PRE (shown /100), p6 -> +0x4c icon (0 / 9 checked), p10 -> +0x58 icon (< 5).
    try:
        _br = (PG.ensure_commander(dict(cmd)) if not cmd.get("branches") else cmd)["branches"]
        _bk = max(PG.BRANCHES, key=lambda k: (_br.get(k) or {}).get("level", 0))
        _lv, _bi = int((_br.get(_bk) or {}).get("level", 1)), PG.BRANCHES.index(_bk)
    except Exception:
        _lv, _bi = 1, 0
    _nat = int(cmd.get("nation", 1) or 1)
    _rid = NO_REGIMENT if cmd.get("npc") else regiment_id_of(name)
    if HOF_DEBUG:
        r = struct.pack(">IHBBBIIBHH", _nat, _rid, 11, 2, 13, 100001, 20000200, 3, 7777, 8888)
    else:
        r = struct.pack(">IHBBBIIBHH", _nat, _rid & 0xFFFF, min(_lv, 255), 0, _bi,
                        int(pr_of(dict(cmd))), int(cmd.get("honor", 0)) // 100 * 100,
                        (_nat - 1) % 5, min(w, 65535), min(l, 65535))
    if kind == 1:
        r += struct.pack(">H", 0)
    return nm + r

def build_regiment_rows(s=None):
    """(user 2026-10-25 21:02: F6 REGIMENT tab empty, 'ACTIVE REGIMENTS 0') the tab asks 0x12 [6] (004f3cd0); the answer
    (004f8820 kind 6): [u16 n] n x {u32 uid, u16 key, s8 name (<= 20), u16, u16, u16, u16}.  The key is looked up in the
    directory cache (0x3a / 0x3b regiment entries -> NAME / FACTION columns; a missing key makes the client ask 0x3c).
    The s8 = the regiment leader (COMMANDER column); the four u16: member count first, the others not known yet (0)."""
    enc = getattr(s, "enc", "latin-1") if s is not None else "latin-1"
    rows = []
    regs = sorted(load_regiments().items(), key=lambda kv: (-len(kv[1].get("members", [])), kv[0]))
    for n, g in regs[:500]:
        lb = str(display_name(str(g.get("leader", "")))).encode(enc, "replace")[:20]
        rows.append(struct.pack(">IH", g["id"], g["id"]) + bytes([len(lb)]) + lb
                    + struct.pack(">HHHH", min(len(g.get("members", [])), 65535), 0, 0, 0))
    return bytes([0x12, 6]) + struct.pack(">H", len(rows)) + b"".join(rows)

def build_hof(kind, s=None):
    if kind == 6:
        return build_regiment_rows(s)
    if kind not in (1, 2, 3, 4):
        return bytes([0x12, kind]) + struct.pack(">H", 0)
    rows = build_directory()
    # user 2026-10-24 13:13 (F6 Hall of Fame: Novice / Advanced / Elite showed only the player himself): the HOF tab's
    # three pages request kinds 2 / 3 / 4 (client 004f3cd0: view 1 -> 2, 2 -> 3, 3 -> 4) = planet tiers 1 / 2 / 3.
    # Before, every kind got the same mixed top 100 (sorted by wins / honor / nation).  Now each page lists the
    # commanders - players and NPCs - whose nation is on that tier's planet, best PR first.
    if kind in (2, 3, 4):
        tier = kind - 1
        rows = [r for r in rows if PLANET_TIER.get(nation_planet(int(r[1].get("nation", 1) or 1)), 1) == tier]
    if kind == 1:
        # (user 2026-10-25 20:54: a new regiment did not show in the F6 WHO-LIST) the who-list was the top 100 by PR of
        # ALL commanders (NPCs mostly) - an online player with a low PR was not in it at all.  WHO = who is online:
        # the online players first (best PR first), then the others.
        on = {getattr(o, "acc", "").lower() for o in ONLINE if getattr(o, "logged_in", False) and not o.w.is_closing()}
        rows.sort(key=lambda r: (str(r[0]).lower() not in on, -pr_of(dict(r[1]))))
    else:
        rows.sort(key=lambda r: -pr_of(dict(r[1])))
    rows = rows[:100]
    d = bytes([0x12, kind]) + struct.pack(">H", len(rows)) + b"".join(hof_row(kind, n, c) for n, c in rows)
    if kind == 1:
        d += struct.pack(">H", len(rows))
    return d

# ---- USER INFO / WORD OF HONOR / RESOURCE EXCHANGE / PLAYER SEARCH (reverse engineered 2026-10-20, UNVERIFIED in game) --
# USER INFO (F4 window of ANOTHER player): client 0x23 [02][s8 name] (Hall of Fame / who-list click) or [01][u32 id]
#   -> server 0x27 sub 1 (client FUN_004b4980): [01][s8 name][u8 nation][u32 uid][u16 k] then the same body as sub 0 up to
#   the medals (s8 title, u8, 4 x branch, u8 reinc, 3 x u32, medals), then [u16 wins][u16 losses][s8 superior][u16 n][n bytes text].
# WORD OF HONOR (superior / subordinate; F4 window buttons 0x1a / 0x1b):
#   client 0x55 [00][00][s8 target] = give my word to target  -> server asks the target: 0x54 [05][u8][s8 asker]
#   target answers 0x55 [03][u8 code][s8 asker] (1 yes, 0 no, 2..10 busy) -> asker gets 0x54 [06][code] (+[s8 target] if 1)
#   client waits 30 s ("They do not respond...") so a reply must always come.  client 0x5c [00][s8 name] = release.
#   0x54 sub 0 [u8][u8][s8 name] adds a friend-list row, sub 1 [s8] removes it (client 004f32c0 / 004f2120).
# PLAYER SEARCH: client 0x57 [s8 name] (who window search box) -> we answer with a directory entry (0x3b) + 0x54 sub 0.
# RESOURCE EXCHANGE (building "ExchangeShop", client 0x34 [u32 shop][01] to enter):
#   server 0x34 [00][u32 shop] 4 x {u16 max amount, u32 rate} for ore / silicon / uranium / sulfur (rate = money per unit)
#   client 0x34 [u32 shop][02] 4 x i32 amount (+ buy / - sell); the window computes
#     S = sum(amount*rate), fee = sum(|amount*rate|)/3, money left = money - S - fee must be >= 0
#   server 0x34 [01][u8 ok]: 0 = failure text, 1 = success text (window closes).
EXCHANGE_RATE = [4, 6, 12, 8]
EXCHANGE_MAX = 9999

def find_account_by_uid(uid):
    for n, a in load_accounts().items():
        if "commander" in a and uid_of(n) == uid:
            return n, a
    for n, a in load_accounts().items():          # a clicked hero sends the unit id of the hero, not the account id
        if "commander" in a and uid < 1000 and a.get("hero_uid") == uid:
            return n, a
    for n in npc_all():
        if uid_of(n["name"]) == uid or NPC_TOWN_BASE + n["id"] == uid:
            return n["name"], npc_account(n)
    return None, None

def find_account_by_name(name):
    n = nick_account((name or "").strip()).lower()
    for acc, a in load_accounts().items():
        if acc.lower() == n and "commander" in a:
            return acc, a
    _n = npc_by_name(n)
    if _n:
        return _n["name"], npc_account(_n)
    return None, None

def build_user_info(name, a, s=None):
    cmd = PG.ensure_commander(a.setdefault("commander", {}))
    br = cmd["branches"]
    top = max(v["level"] for v in br.values())
    # header u8 = PORTRAIT number, not the nation (window +0x90d -> "Hero-%02d.xpf", client 005e0778).  Sending the nation
    # (14) made the client load Hero-14.xpf.  The u32 is the NATION ID (window +0x910): 005e2331 looks it up in the nation
    # table (00551ec0 returns NULL for an unknown id) and reads the nation name from it -> with the player uid there the
    # client did strlen(NULL + 4) and crashed (EIP 0060F6C0, EAX = 4; 2026-10-22 14:56).  u16 = 0 (sub 0: +0x44c).
    look = max(1, min(int(cmd.get("look", 1) or 1), 11))
    # u16 = key of the client's directory cache (0057e310 compares ONLY this u16; window 005e2346 shows the entry's
    # name as REGIMENT).  Our directory entries all use 0, so 0 showed a random commander as regiment -> use a key no
    # entry has (0xFFFF = no regiment shown).
    _rid = NO_REGIMENT if a.get("npc") else regiment_id_of(name)
    d = bytearray([0x27, 1]) + _s8(name) + bytes([look]) + struct.pack(">IH", int(cmd.get("nation", 1) or 1), _rid)
    _sx = s if s is not None else type("_S", (), {"lang": "en", "enc": "latin-1"})()
    d += _s8e(_sx, rank_for(_sx, top, cmd.get("reincarnations", 0))) + bytes([0])      # rank in the viewer's language
    for key in PG.BRANCHES:
        v = br[key]
        d += bytes([min(v["level"], 255)]) + _s8e(_sx, rank_for(_sx, v["level"], short=True)) + bytes([rank_icon(v["level"])] * 2) \
            + struct.pack(">II", v["xp"], PG.branch_xp_need(v["level"]))
    d += bytes([min(cmd.get("reincarnations", 0), 255)])
    d += struct.pack(">III", pr_of(cmd), cmd.get("honor", 0), 0)
    medals = cmd.get("medals", [])[:255]
    d += bytes([len(medals)]) + b"".join(
        struct.pack(">I", mid) + (_s8e(s, medal_text(txt, getattr(s, "lang", "en"))) if s is not None else _s8(txt))
        for mid, txt in medals)
    d += struct.pack(">HH", cmd.get("wins", 0), cmd.get("losses", 0))
    d += _s8(cmd.get("superior", ""))
    text = str(cmd.get("bio", "")).encode("latin-1", "replace")[:1000]
    d += struct.pack(">H", len(text)) + text
    # the client reads ONE MORE s8 after the biography (disassembly 004b4e4a: FUN_005a9ff0 right after the text copy, then the
    # window is built by 005e1630).  Without it the client read past the end of the packet and crashed (2026-10-22 14:45).
    try:
        reg = "" if a.get("npc") else (regiment_of(name)[0] or "")
    except Exception:
        reg = ""
    d += _s8e(_sx, reg)
    return bytes(d)

def handle_user_info(s, body):
    if body[1] == 2:
        name, _o = read_s8(body, 2)
        acc, a = find_account_by_name(name)
    else:
        uid = struct.unpack_from(">I", body, 2)[0]
        acc, a = find_account_by_uid(uid)
    if not acc:
        log(f"   user info request {body.hex()}: nobody found")
        if body[1] == 1:
            s.send(build_hero_info(s))
        return
    log(f"   user info request -> 0x27 sub 1 for {acc}")
    s.send(build_user_info(acc, a, s))

def refresh_hero_info(s):
    s.send(build_hero_info(s))

def handle_word_of_honor(s, body):
    """0x55 [op]...: op 0 [00][s8 target] give my word; op 3 [u8 code][s8 asker] answer; 2 = (menu, ignored)."""
    op = body[1]
    if op == 0 and len(body) >= 4:
        target, _o = read_s8(body, 3)
        o = find_online(target)
        if (not target) or target.lower() == s.acc.lower() or not o:
            log(f"   word of honor: {s.acc} -> {target!r}: target missing/offline -> busy")
            s.send(bytes([0x54, 6, 2]))
            return
        o.word_asker = s.acc
        o.send(bytes([0x54, 5, 0]) + _s8(s.acc))
        log(f"   word of honor: {s.acc} asks {o.acc} to be his superior")
    elif op == 3 and len(body) >= 4:
        code = body[2]
        asker, _o = read_s8(body, 3)
        a_s = find_online(asker)
        if not a_s:
            return
        if code == 1:
            _accs, a = get_account(a_s.acc)
            _c = PG.ensure_commander(a.setdefault("commander", {}))
            if _c.get("superior", "").lower() != s.acc.lower():
                _c["tribute"] = 0                      # a new Superior: the pending tribute starts again
                _c["tribute_up"] = 0
            _c["superior"] = s.acc
            save_accounts(_accs)
            a_s.send(bytes([0x54, 6, 1]) + _s8(s.acc))
            refresh_hero_info(a_s)
            log(f"   word of honor: {a_s.acc} is now a subordinate of {s.acc}")
        else:
            a_s.send(bytes([0x54, 6, code if 0 <= code <= 10 else 0]))
            log(f"   word of honor: {s.acc} answered {code} to {a_s.acc}")
    elif op == 2:
        send_exp_window(s)                              # Quick Menu "Assign XP"
    elif op == 4:
        assign_exp_packet(s, body)                      # the Assign XP window's answer (format not confirmed)
    else:
        log(f"   0x55 request {body.hex()} (not handled)")

def release_word(s, body):
    if body[1] == 0 and len(body) >= 3:
        name, _o = read_s8(body, 2)
        _accs, a = get_account(s.acc)
        cmd = PG.ensure_commander(a.setdefault("commander", {}))
        if cmd.get("superior", "").lower() == name.lower():
            cmd["superior"] = ""
            cmd["tribute"] = 0
            cmd["tribute_up"] = 0
            save_accounts(_accs)
            log(f"   word of honor: {s.acc} left his superior {name}")
        refresh_hero_info(s)
    else:
        log(f"   0x5c request {body.hex()} (not handled)")

# ---- WORD OF HONOR "PYRAMID": Subordinate list + Assign XP (client UseExpWnd; texts in ntt.dat pyramid) -----------------
# Rules (client texts): the Superior receives bonus XP from his Subordinates' adventures (progression.WOH_TRIBUTE of every
# XP they earn, kept in the Subordinate's cmd["tribute"]) and hands it out to his OWN units in the Assign XP window.
#   * a Subordinate who outranks the Superior (higher division level) cannot be used  (kPyramidStudentLevelOver)
#   * a unit that is too high cannot receive                                            (ksLevelLimit)
# Server 0x54 sub 3 opens the window (client 004ac000 case 3 -> 004a3520 builds CUseExpWnd, 005dfea0 parses; disassembly
# 2026-11-01 16:30): [03][u8 n] n x {u8 level, u32 A, u32 B, s8 name (<= 255)}.  The u32 are BIG-ENDIAN (005a86b0) - the
# server sent them little-endian before.  A = DIRECT XP (直接经验, the Subordinate's own tribute), B = INDIRECT XP (间接经验, from his Subordinates) - the columns
# of the window (seen in game 11-01 16:35; B was a name hash before and showed as a 10-digit number).
# The window keeps each row (0x58 bytes: name, level +0x1c, A +0x20, B +0x24, and XOR-scrambled copies of A, B and the
# name - the client's anti-tamper copy) in two lists (+0x430, +0x440).
# The window's answer (OK button, 005de820): client 0x55 [04][u8 n] n x {
#     u32 unit id (the unit record's +4 = the uid of 0x16), u8 m, m x { s8 student name, u32 A, u32 B, u16 0x6300, u8 0x11,
#     s8 scrambled name, u16, u16, u8 0x8c, u16, u16 } }  - one entry per unit that was given students: the player drops a
# Subordinate's XP on a unit, the whole amount goes to it (no amount is typed).  A student the window cannot find in its
# list is sent with zeros (and a "(Wrong Exp Info)" line in the client's log); the server checks every name itself.
def _cmd_level(cmd):
    return max([int(v.get("level", 1) or 1) for v in (cmd.get("branches") or {}).values()] or [1])

def my_subordinates(acc):
    """[(account name, account dict)] of everybody who gave his Word to `acc`."""
    low = acc.lower()
    out = []
    for nm, a in load_accounts().items():
        if isinstance(a, dict) and (a.get("commander") or {}).get("superior", "").lower() == low:
            out.append((nm, a))
    return sorted(out, key=lambda x: x[0].lower())

def _row_pools(nm, a):
    """the XP pools behind the Superior's row for Subordinate nm: [(commander dict, key)] - his own DIRECT tribute, then
    the INDIRECT share (progression.WOH_TRIBUTE2) of each of his own Subordinates."""
    out = [(a.setdefault("commander", {}), "tribute")]
    for _xn, xa in my_subordinates(nm):
        out.append((xa.setdefault("commander", {}), "tribute_up"))
    return out

def tribute_rows(acc):
    """per Subordinate: (name, level, direct XP, indirect XP, usable).  usable = 0 when he outranks the Superior
    (kPyramidStudentLevelOver: "You cannot use XP gained from higher ranking Subordinates")."""
    _a, me = get_account(acc)
    mylv = _cmd_level(me.get("commander", {}))
    rows = []
    for nm, a in my_subordinates(acc):
        lv = _cmd_level(a.get("commander", {}))
        pools = _row_pools(nm, a)
        d = int(pools[0][0].get("tribute", 0) or 0)
        i = sum(int(c.get(k, 0) or 0) for c, k in pools[1:])
        rows.append((nm, lv, d, i, d + i if lv <= mylv else 0))
    return rows

def send_exp_window(s):
    rows = tribute_rows(s.acc)[:255]
    d = bytes([0x54, 3, len(rows)])
    for nm, lv, dx, ix, use in rows:
        if not use:                                   # (outranks me: the window shows nothing to use)
            dx = ix = 0
        d += bytes([min(lv, 255)]) + struct.pack(">II", min(dx, 0x7FFFFFFF), min(ix, 0x7FFFFFFF)) + _s8(nm)
    s.send(d)
    log(f"   assign XP window for {s.acc}: {[(r[0], r[1], r[2], r[3], r[4]) for r in rows]}")

def parse_assign_exp(body):
    """client 0x55 [04] (format above) -> [(unit id, [student name, ...])].  Raises on a short / bad packet."""
    o = 2
    n = body[o]; o += 1
    out = []
    for _ in range(n):
        uid = struct.unpack_from(">I", body, o)[0]; o += 4
        m = body[o]; o += 1
        names = []
        for _ in range(m):
            nm, o = read_s8(body, o)
            o += 4 + 4 + 2 + 1
            _x, o = read_s8(body, o)
            o += 2 + 2 + 1 + 2 + 2
            if o > len(body):
                raise ValueError("short packet")
            names.append(nm)
        out.append((uid, names))
    return out

def assign_exp(s, unit_no, amount=None, only=None):
    """give tribute XP to my unit number `unit_no` (1 = first).  Returns (given, message)."""
    accs, me = get_account(s.acc)
    cmd = PG.ensure_commander(me.setdefault("commander", {}))
    units = me.get("units", [])
    if not 1 <= unit_no <= len(units):
        return 0, "No such unit."
    u = units[unit_no - 1]
    if u.get("level", 1) >= PG.UNIT_MAX_LEVEL:
        return 0, "This unit's level is too high for you to distribute XP to it."
    if u.get("level", 1) > _cmd_level(cmd):
        return 0, "This unit's level is too high for you to distribute XP to it."
    left = amount if amount is not None else 10 ** 9
    given = 0
    all_accs = load_accounts()
    mylv = _cmd_level(cmd)
    for nm, a in my_subordinates(s.acc):
        if left <= 0:
            break
        if only and nm.lower() != only.lower():
            continue
        if _cmd_level(a.get("commander", {})) > mylv:
            continue
        for c, k in _row_pools(nm, a):                 # direct first, then the indirect shares
            t = int(c.get(k, 0) or 0)
            if t <= 0 or left <= 0:
                continue
            take = min(t, left)
            c[k] = t - take
            given += take
            left -= take
    if given <= 0:
        return 0, "No XP received from your Subordinates"
    all_accs[s.acc] = me
    events = PG.add_unit_xp(cmd, u, unit_branch(u["chassis"]), given, tribute=False) or []
    me["commander"] = cmd
    all_accs[s.acc] = me
    save_accounts(all_accs)
    star_notify(s)
    log(f"   assign XP: {s.acc} gave {given} tribute XP to unit #{u['uid']} " + "".join(f"\n      * {e}" for e in events))
    return given, f"+{given} XP -> {u.get('label') or u['chassis']} (level {u.get('level', 1)})" + "".join(f"; {e}" for e in events)

def assign_exp_packet(s, body):
    """the Assign XP window's OK: every listed Subordinate's whole usable XP goes to the unit it was dropped on."""
    try:
        plan = parse_assign_exp(body)
    except Exception as e:
        log(f"   assign XP packet from {s.acc}: {body.hex()} - bad ({e!r})")
        send_exp_window(s)
        return
    log(f"   assign XP packet from {s.acc}: {plan}")
    say = lambda m: s.send(chat_line(0x0A, m, (120, 220, 255)))
    total = 0
    for uid, names in plan:
        _a, me = get_account(s.acc)
        no = next((i + 1 for i, u in enumerate(me.get("units", [])) if u.get("uid") == uid or u.get("hid") == uid), 0)
        if not no:
            log(f"   assign XP: {s.acc} has no unit {uid}")
            continue
        # the client shows (and sends back) a Subordinate's NICKNAME in place of his account name (zhihue -> 口合口合 in GBK
        # bytes, seen 11-01 16:38) -> back to the account, as for chat names
        for nm in dict.fromkeys(nick_account(x, getattr(s, "enc", None)) for x in names):   # (a name twice = once)
            g, m = assign_exp(s, no, None, only=nm)
            total += g
            say(m)
    refresh_after_exp(s)
    if total:
        log(f"   assign XP: {s.acc} distributed {total} XP")

def refresh_after_exp(s):
    """the units' XP / levels and the commander (branch levels) changed -> the client's roster and F4 data again.
    0x16 sub 1 clears the client's roster: every unit's equipment (0x1F) must follow (11-01 13:07)."""
    try:
        _a, me = get_account(s.acc)
        cmd = me.get("commander", {})
        s.send(build_commander(s.acc, cmd.get("nation", 1), cmd.get("attrs", (0, 0, 0, 0)), resources=me["resources"]))
        s.send(build_units([roster_rec(u) for u in me["units"]], mech=MECH_APT.get(s.acc)))
        for u in me["units"]:
            if u.get("items"):
                s.send(build_set_inventory(u["uid"], u["items"]))
    except Exception as e:
        log(f"   assign XP refresh: {e!r}")

def xp_command(s, text):
    say = lambda m: s.send(chat_line(0x0A, m, (120, 220, 255)))
    parts = text.split()[1:]
    rows = tribute_rows(s.acc)
    if not rows:
        return say("You have no Subordinates (a player gives you his Word of Honor from your F4 window).")
    if not parts:
        for nm, lv, dx, ix, use in rows:
            say(f"{display_name(nm)} lv{lv}: {dx} + {ix} XP" + ("" if use or not dx + ix else "  (outranks you - not usable)"))
        _a, me = get_account(s.acc)
        say("Units: " + ", ".join(f"#{i + 1} {u.get('label') or u['chassis']} L{u.get('level', 1)}" for i, u in enumerate(me.get("units", []))))
        return say("/xp UNIT# [AMOUNT]  - give to one unit;  /xp auto  - spread over all units")
    if parts[0].lower() == "auto":
        _a, me = get_account(s.acc)
        n = len(me.get("units", []))
        total = sum(r[4] for r in rows)
        if n == 0 or total <= 0:
            return say("No XP received from your Subordinates")
        each = max(1, total // n)
        done = 0
        for i in range(1, n + 1):
            g, m = assign_exp(s, i, each)
            done += g
        say(f"Distributed {done} XP.")
    else:
        try:
            no = int(parts[0])
            amt = int(parts[1]) if len(parts) > 1 else None
        except ValueError:
            return say("/xp UNIT# [AMOUNT]")
        g, m = assign_exp(s, no, amt)
        say(m)
    try:
        _a, _me = get_account(s.acc)
        _c = _me.get("commander", {})
        s.send(build_commander(s.acc, _c.get("nation", 1), _c.get("attrs", (0, 0, 0, 0)), resources=_me["resources"]))
    except Exception as e:
        log(f"   /xp refresh: {e!r}")

def handle_player_search(s, body):
    name, _o = read_s8(body, 1)
    if not getattr(s, "field_sent", False):
        # (user 2026-10-27 11:35: FRIEND ID on the New-commander screen hung at "Processing") the New-commander window
        # (CNewSelectFriendNationWnd, client 005a5c50) sends this same 0x57 [s8 name] and waits for server 0x55:
        # [55][u8 found][u32 nation] (005a55b0: found -> that nation is selected, 0 -> ksFriendFoundFail).
        try:
            raw = name.strip()
            acc = (nick_account(raw, getattr(s, "enc", None)) or "").lower()
            c = (load_accounts().get(acc) or {}).get("commander") or {}
            nid = c.get("nation")
            open_pl = {p[0] for p in PLANETS if p[3]}
            ok = bool(nid) and nid in CAPITALS and (CAPITALS[nid] // 100000) % 1000 in open_pl
        except Exception as e:
            log(f"   friend lookup error: {e!r}")
            ok, nid = False, 0
        log(f"   New commander: friend {name!r} -> {'nation ' + str(nid) if ok else 'not found'}")
        s.send(bytes([0x55, 1]) + struct.pack(">I", nid) if ok else bytes([0x55, 0]))
        return
    q = name.strip().lower()
    hits = [(n, a["commander"]) for n, a in load_accounts().items() if "commander" in a and q and q in n.lower()][:20]
    log(f"   player search {name!r}: {len(hits)} hit(s)")
    for n, c in hits:          # (no 0x3b here any more: that cache holds regiments)
        s.send(bytes([0x54, 0, 1, c.get("nation", 1) & 0xFF]) + _s8(n))

def build_exchange(shop):
    d = bytes([0x34, 0]) + struct.pack(">I", shop)
    for r in EXCHANGE_RATE:
        d += struct.pack(">HI", EXCHANGE_MAX, r)
    return d

def handle_exchange(s, body):
    shop = struct.unpack_from(">I", body, 1)[0]
    op = body[5]
    if op == 1:
        s.send(build_exchange(shop))
        log(f"   exchange shop {shop}: rates {EXCHANGE_RATE}")
    elif op == 2 and len(body) >= 22:
        amt = struct.unpack_from(">4i", body, 6)
        accs, a = get_account(s.acc)
        res = a["resources"]
        cost = sum(x * r for x, r in zip(amt, EXCHANGE_RATE))
        fee = sum(abs(x * r) for x, r in zip(amt, EXCHANGE_RATE)) // 3
        ok = res[0] - cost - fee >= 0 and all(res[i + 1] + amt[i] >= 0 for i in range(4)) \
            and all(x <= EXCHANGE_MAX for x in amt)
        log(f"   exchange {amt}: cost {cost} fee {fee} money {res[0]} -> {'OK' if ok else 'REFUSED'}")
        if ok:
            a["resources"] = [res[0] - cost - fee] + [res[i + 1] + amt[i] for i in range(4)] + list(res[5:])
            save_accounts(accs)
            s.send(build_commander(s.acc, s.cmd.get("nation", 1), s.cmd.get("attrs", (0, 0, 0, 0)), resources=a["resources"]))
        s.send(bytes([0x34, 1, 1 if ok else 0]))

# ---- CHAT (client 0x2a, server 0x2a '*' -> CCtrlChatting 00439bb0, research_social.md) -------------------------
# client -> server: [2a][sub][...][rgb]   sub 0/3 = public (3 = on a battle map), 2 = allies/nation,
#                   1/4 = whisper [s8 target][s8 text], 5 = group [u8 n][n x s8 name][s8 text]
# server -> client: [2a][03][s8 text][rgb] plain line, [2a][01][s8 "Sender>text"][rgb] whisper,
#                   [2a][0a][s8 text][rgb] system line ("chatss").
CHAT_MAX = 200

class TextPkt(bytes):
    """a 0x2A chat line that is re-encoded for every receiver (2026-10-21, Chinese client phase 1): system lines
    (sub 0x0A) are translated into the receiver's language (i18n.py), every line is encoded in the receiver's
    Windows code page (cp950 / gbk / latin-1).  Session.send renders it."""
    def render(self, sess):
        lang = getattr(sess, "lang", "en")
        text = I18N.translate_checked(self.text, lang) if self.tr else self.text
        text = NP.zh_text(text, lang)                      # NPC commanders: Chinese name for Chinese clients (npc.py)
        tb = text.encode(getattr(sess, "enc", "latin-1"), "replace")[:250]
        while tb and len(tb) == 250 and tb[-1] >= 0x80 and getattr(sess, "enc", "latin-1") != "latin-1":
            tb = tb[:-1]                                   # never cut a 2-byte character in half
        return bytes([0x2A, self.sub, len(tb)]) + tb + bytes(self.rgb)

def chat_line(sub, text, rgb=(255, 255, 255), tr=None):
    tb = text.encode("latin-1", "replace")[:250]
    p = TextPkt(bytes([0x2A, sub, len(tb)]) + tb + bytes(rgb))
    p.sub, p.text, p.rgb = sub, text, tuple(rgb)
    p.tr = (sub == 0x0A) if tr is None else tr          # player chat (1 / 3) is never translated
    return p

def find_online(name):
    n = nick_account((name or "").strip()).lower()
    for o in ONLINE:
        if getattr(o, "logged_in", False) and not o.w.is_closing() and getattr(o, "acc", "").lower() == n:
            return o
    return None

def handle_chat(s, body):
    sub = body[1]
    try:
        o = 2
        if sub in (1, 4):
            target, o = read_s8(body, o)
            text, o = read_s8(body, o)
            names = [target]
        elif sub == 5:
            n = body[o]; o += 1
            names = []
            for _ in range(n):
                nm, o = read_s8(body, o); names.append(nm)
            text, o = read_s8(body, o)
        else:
            text, o = read_s8(body, o)
            names = []
        rgb = tuple(body[o:o + 3]) if len(body) >= o + 3 else (255, 255, 255)
    except Exception:
        log(f"   chat: bad packet {body.hex()}")
        return
    # the client typed in its Windows code page (Big5 / GBK for Chinese): decode it, every receiver gets it
    # re-encoded in his own code page (TextPkt)
    try:
        _raw = text.encode("latin-1")
        # (2026-10-25 20:58 "A級" arrived as 'A?') the raw bytes of every non-ASCII / '?' chat line, to tell a client-side
        # loss from a decoding problem
        if any(c >= 0x80 for c in _raw) or b"?" in _raw:
            log(f"   chat raw bytes from {getattr(s, 'acc', '?')!r}: {_raw.hex(' ')}")
        text = _raw.decode(getattr(s, "enc", "latin-1"), "replace")
    except Exception:
        pass
    text = text.replace("\n", " ").strip()[:CHAT_MAX]
    if not text or text.startswith("!KILL!"):
        return
    log(f"   chat sub{sub}: {text!r}" + (f" -> {names}" if names else ""))
    if text.lower().split()[0] == "/lang" and sub in (0, 2, 3):
        # /lang en | zh : language of the server messages (Chinese needs a Chinese Windows code page 950 / 936)
        arg = (text.split() + [""])[1].lower()
        accs, a = get_account(s.acc)
        if arg in ("en", "zh", "auto"):
            a["lang"] = None if arg in ("zh", "auto") else "en"
            accs[s.acc] = a; save_accounts(accs)
            s.lang = "en" if arg == "en" else I18N.lang_of_acp(getattr(s, "acp", 0))
        s.send(chat_line(0x0A, f"Language: {LANG_NAMES.get(getattr(s, 'lang', 'en'), 'en')}", (120, 220, 255)))
        return
    if text.lower().split()[0] == "/help" and sub in (0, 2, 3):
        help_command(s, text)
        return
    if text.lower() == "/star" and sub in (0, 2, 3):
        enter_star(s)
        return
    if text.lower().split(" ")[0] == "/nick" and sub in (0, 2, 3):
        nick_command(s, text[5:].strip())
        return
    if text.lower().split(" ")[0] == "/mail" and sub in (0, 2, 3):
        mail_command(s, text[5:].strip())
        return
    if text.lower() == "/speed" and sub in (0, 2, 3):
        speed_command(s)
        return
    if text.lower() == "/version" and sub in (0, 2, 3):
        version_command(s)
        return
    if text.lower().split()[0] in ("/wight", "/quorg") and sub in (0, 2, 3):
        unlock_unit_command(s, text)
        return
    if text.lower().strip() in ("/retreat", "/撤退", "/撤退!", "/yes") and sub in (0, 2, 3):
        confirm_gate_retreat(s)
        return
    if text.lower() == "/reset" and sub in (0, 2, 3):
        reset_points(s)
        return
    if text.lower().split()[0] == "/xp" and sub in (0, 2, 3):
        xp_command(s, text)
        return
    if text.lower().startswith("/regiment") and sub in (0, 2, 3):
        regiment_command(s, text)
        return
    if text.startswith("/") and sub in (0, 2, 3):
        if GM_COMMANDS and is_gm(getattr(s, "acc", None)):
            log(f"   GM {s.acc}: {text!r}")
            audit("gm", s.acc, text=text)
            gm_command(s, text)
        else:
            log(f"   ANTI-CHEAT: non-GM {getattr(s, 'acc', None)} tried command {text!r}")
            audit("gm_denied", getattr(s, "acc", None), text=text)
            s.send(chat_line(0x0A, "Unknown command. Type /help.", (255, 120, 120)))
        return
    me = display_name(s.acc)                     # nickname (Unicode; TextPkt encodes it for every receiver)
    if sub in (1, 4, 5):
        delivered = []
        _enc = getattr(s, "enc", "latin-1")
        names = [nick_account(nm, _enc) for nm in names]       # typed / clicked nickname -> account
        for nm in names:
            t = find_online(nm)
            if not t or t is s:
                continue
            t.send(chat_line(1, f"{me}>{text}", rgb)); delivered.append(t.acc)
        for nm in names:
            if nm.lower() not in [d.lower() for d in delivered]:
                try:
                    _nm = nm.encode("latin-1").decode(_enc)
                except Exception:
                    _nm = nm
                s.send(chat_line(0x0A, f"{display_name(_nm)} is not online.", (255, 200, 0)))
        if delivered:
            s.send(chat_line(3, f"(to {', '.join(display_name(d) for d in delivered)}) {text}", rgb))
    elif sub == 2:
        mine = side_nation(s)
        for t in list(ONLINE):
            if getattr(t, "logged_in", False) and not t.w.is_closing() and same_side(side_nation(t), mine):
                t.send(chat_line(3, f"{ally_tag(t)} {me}: {text}", rgb))
        try:
            _txt = text.encode("latin-1").decode(getattr(s, "enc", "latin-1"))
        except Exception:
            _txt = text
        try:
            if npc_battle_hear(s, _txt):              # (23:31) orders to the allied NPC platoons of this battle
                return
        except Exception as e:
            log(f"   npc_battle_hear: {e!r}")
        try:
            npc_hear(s, _txt)                         # idle NPCs answer calls for help (2026-10-23 21:57)
        except Exception as e:
            log(f"   npc_hear: {e!r}")
    else:
        if getattr(s, "battle", None):
            group = [t for t in battle_members(s)]
        else:
            group = [s] + map_peers(s)
        for t in group:
            t.send(chat_line(3, f"{me}: {text}", rgb))
        if getattr(s, "battle", None):
            try:
                _txt = text.encode("latin-1").decode(getattr(s, "enc", "latin-1"))
            except Exception:
                _txt = text
            try:
                npc_battle_hear(s, _txt)              # (23:31) battle channel: orders to the allied NPC platoons
            except Exception as e:
                log(f"   npc_battle_hear: {e!r}")

# ---- REGIMENTS (guilds): chat-command implementation (the original client uses embedded ASP pages, not served) ----
REGIMENT_CREATE_COST = (10000, 1000, 1000, 0, 0)   # money, ore, silicon, uranium, sulfur (PLACEHOLDER amounts)
REGIMENT_RENAME_URA = 250
REGIMENT_MAX_PER_NATION = 13                       # at most 13 regiments per faction (anyone with the resources may found one)                           # renaming costs Uranium
REGIMENT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "regiments.json")

_REGS = None

def load_regiments():
    global _REGS
    if _REGS is None:
        try:
            _REGS = STORE.kv_get(db(), "regiments") or {}
        except Exception:
            _REGS = {}
    regs = _REGS
    # every regiment has a fixed small id (the key of the client's directory cache, see regiment_entry); old files get them now
    if any(not g.get("id") for g in regs.values()):
        used = {g.get("id") for g in regs.values()}
        for g in regs.values():
            if not g.get("id"):
                g["id"] = next(i for i in range(1, 65000) if i not in used); used.add(g["id"])
        save_regiments(regs)
    return regs

# ---- REGIMENT DIRECTORY (2026-10-22 15:06) ------------------------------------------------------------------------------
# The client's directory cache (0x3a list / 0x3b one entry, FUN_0057e400 / 0057e5e0) is keyed ONLY by the u16 (0057d560),
# and the F4 windows show the NAME of the entry whose key = the commander's regiment id (own: 0x15 +0x44c; other player:
# 0x27 sub 1 header u16) as "Regiment".  So the entries are regiments: [u32 id][u16 id][u8 nation][s8 name][u16 members]
# [s8 leader].  NO_REGIMENT = a key no entry has (empty regiment field).
NO_REGIMENT = 0xFFFF

def regiment_id_of(acc):
    name, r = regiment_of(acc) if acc else (None, None)
    return int(r.get("id") or NO_REGIMENT) if r else NO_REGIMENT

def regiment_entry(name, g, enc="latin-1"):
    nb = str(name).encode(enc, "replace")[:19]                       # Chinese regiment names (user 2026-10-22 15:11)
    lb = wire_name(str(g.get("leader", ""))).encode("latin-1", "replace")[:19]
    return (struct.pack(">IHB", g["id"], g["id"], int(g.get("nation", 1)) & 0xFF) + bytes([len(nb)]) + nb
            + struct.pack(">H", min(len(g.get("members", [])), 65535)) + bytes([len(lb)]) + lb)

def build_regiment_list(enc="latin-1"):
    regs = load_regiments()
    rows = [regiment_entry(n, g, enc) for n, g in regs.items()][:2000]
    return bytes([0x3A]) + struct.pack(">H", len(rows)) + b"".join(rows)

def regiments_changed(*accs):
    """after create / join / leave / kick / rename: every client gets the new list, the commanders concerned a new 0x15."""
    for o in list(ONLINE):
        if not getattr(o, "logged_in", False) or o.w.is_closing():
            continue
        o.send(build_regiment_list(getattr(o, "enc", "latin-1")))
        if getattr(o, "acc", None) in accs:
            try:
                _a = get_account(o.acc)[1]; _c = _a.get("commander", {})
                o.send(build_commander(o.acc, _c.get("nation", 1), _c.get("attrs", (0, 0, 0, 0)), resources=_a["resources"]))
            except Exception as e:
                log(f"   regiments_changed: {e!r}")
    try:
        refresh_hero_marks(*accs)
    except Exception as e:
        log(f"   regiments_changed marks: {e!r}")

def save_regiments(r):
    global _REGS
    _REGS = r
    STORE.kv_put(db(), "regiments", r)          # game.db (was regiments.json)

def regiment_of(acc):
    for name, r in load_regiments().items():
        if acc in r["members"]:
            return name, r
    return None, None

# MARK ABOVE THE COMMANDER'S HEAD (user 2026-10-26 23:33: "a regiment leader needs a mark over his head").  The client
# draws hero PUT 0x20 byte +0x368 (004ce920): 1 = ui-pres1/2.xpf (gold, animated - the faction PRESIDENT),
# 2 = ui-cabi.xpf (silver winged emblem, "cabinet" in the original) -> used for REGIMENT LEADERS; the president's mark wins.
def hero_mark(acc):
    if not acc:
        return 0
    try:
        nat = get_account(acc)[1].get("commander", {}).get("nation", 1)
        if str(politics(nat).get("president", "")).lower() == str(acc).lower():
            return 1
    except Exception:
        pass
    try:
        _n, r = regiment_of(acc)
        if r and str(r.get("leader", "")).lower() == str(acc).lower():
            return 2
    except Exception:
        pass
    return 0

# NAME LINE (user 2026-10-27 00:46/00:54, like the original Chinese servers):
#   rank badges left/right of the name (ui-rtl1/rtr1 frame 1..30, 0 = none) = PRESTIGE (PR, the number the client shows
#   as PRESTIGE: 0..26 from the attribute points, progression.power_rating) - original help: "Prestige ranks battle
#   prowess against other heroes"; 1-5 coloured wings, 6-10 jewelled, 11-15 gold, 16-20 silver, 21-25 stone, 26 fangs.
#   a line of stars over it (the 0x20 title, client F41/F42) = reincarnations in copper / silver / gold.
HERO_STAR = "★"

def hero_rank(acc):
    try:
        return max(0, min(int(pr_of(dict(get_account(acc)[1].get("commander", {})))), 30))
    except Exception:
        return 0

def hero_title(acc, viewer=None):
    """title bytes over the name (user 2026-10-27 00:55): stars by reincarnations in copper / silver / gold -
    1-5 rebirths = 1-5 copper stars, 6-10 = 1-5 silver, 11-15 = 1-5 gold (more = 5 gold).  The first byte 1/2/3 picks
    the colour in the client (F42) and is not printed.  Stars in the VIEWER's code page (GBK A1EF / Big5 A1B9;
    the English client gets GBK too - client F43 shows GBK text on any non-Chinese Windows)."""
    try:
        n = int(get_account(acc)[1].get("commander", {}).get("reincarnations", 0) or 0)
    except Exception:
        n = 0
    if n <= 0:
        return b""
    n = min(n, 15)
    tier, cnt = (n - 1) // 5 + 1, (n - 1) % 5 + 1
    enc = getattr(viewer, "enc", None) or "gbk"
    if enc.lower().replace("-", "") in ("latin1", "iso88591", "cp1252", "ascii"):
        enc = "gbk"            # English client: F43 decodes DBCS text as GBK (user 00:58 "英文版也要保持星星")
    try:
        stars = (HERO_STAR * cnt).encode(enc)
    except (UnicodeEncodeError, LookupError):
        stars = b"*" * cnt
    return bytes([tier]) + stars

def refresh_hero_marks(*accs):
    """resend the commander PUT 0x20 (mark / rank) of these players in town to themselves and to everyone on their map."""
    for o in list(ONLINE):
        if getattr(o, "acc", None) not in accs or getattr(o, "battle", None) or not getattr(o, "hero_uid", None):
            continue
        try:
            look = max(1, min(getattr(o, "cmd", {}).get("look", 1), 11))
            x, y = getattr(o, "hero_pos", (0x200, 0x200))
            for t in [o] + list(map_peers(o)):
                if not t.w.is_closing():
                    t.send(build_hero(o.hero_uid, o.acc, x, y, 0, look, side_nation(o), 100, hero_mark(o.acc),
                                      hero_rank(o.acc), hero_title(o.acc, t)))
        except Exception as e:
            log(f"   refresh_hero_marks {o.acc}: {e!r}")

def regiment_name_ok(name):
    """letters / digits / Chinese (the client shows the name with the viewer's code page): 3-16 letters or 2-8 Chinese."""
    try:
        b = name.encode("gbk")
    except UnicodeEncodeError:
        return False
    return 3 <= len(b) <= 16 and (len(b) >= 4 or name.isascii()) and len(name) >= 2 and name.replace(" ", "").isalnum()

def regiment_command(s, text):
    """/regiment create NAME | join NAME | leave | open | close | list | who | kick HERO | info"""
    say = lambda m: s.send(chat_line(0x0A, m, (120, 220, 255)))
    parts = text.split(None, 2)
    sub = parts[1].lower() if len(parts) > 1 else "info"
    arg = parts[2].strip() if len(parts) > 2 else ""
    regs = load_regiments()
    mine, r = regiment_of(s.acc)
    accs, a = get_account(s.acc)
    cmd = a.setdefault("commander", {})
    if sub == "create":
        if mine:
            return say(f"You already belong to regiment {mine}.")
        if not regiment_name_ok(arg):
            return say("Regiment name: 2-8 Chinese characters or 3-16 letters/digits.")
        if any(n.lower() == arg.lower() for n in regs):
            return say("That regiment name is taken.")
        if sum(1 for g in regs.values() if g["nation"] == cmd.get("nation", 1)) >= REGIMENT_MAX_PER_NATION:
            return say(f"Your faction already has {REGIMENT_MAX_PER_NATION} regiments.")
        if not res_can_pay(a, REGIMENT_CREATE_COST):
            return say("Founding a regiment costs %d money, %d ore and %d silicon." % REGIMENT_CREATE_COST[:3])
        res_add(a, [-_v for _v in REGIMENT_CREATE_COST])
        _used = {g.get("id") for g in regs.values()}
        regs[arg] = {"leader": s.acc, "members": [s.acc], "open": True, "nation": cmd.get("nation", 1),
                     "id": next(i for i in range(1, 65000) if i not in _used)}
        accs[s.acc] = a; save_accounts(accs); save_regiments(regs)
        regiments_changed(s.acc)                 # list + 0x15 with the new regiment id (F4 shows the name)
        return say(f"Regiment {arg} founded.")
    if sub == "join":
        name = next((n for n in regs if n.lower() == arg.lower()), None)
        if mine:
            return say(f"You already belong to regiment {mine}. /regiment leave first.")
        if not name:
            return say("No such regiment.")
        g = regs[name]
        if not g["open"]:
            return say("That regiment is closed to new members.")
        if g["nation"] != cmd.get("nation", 1):
            return say("That regiment belongs to another faction.")
        g["members"].append(s.acc); save_regiments(regs)
        regiments_changed(s.acc)
        return say(f"You joined regiment {name}.")
    if sub == "list":
        if not regs:
            return say("No regiments yet.")
        for n, g in list(regs.items())[:15]:
            say(f"{n}: {len(g['members'])} member(s), leader {g['leader']}, {'open' if g['open'] else 'closed'}")
        return
    if not mine:
        return say("You are not in a regiment. /regiment create NAME  or  /regiment join NAME  or  /regiment list")
    if sub in ("who", "info"):
        say(f"Regiment {mine} (leader {display_name(r['leader'])}, {'open' if r['open'] else 'closed'}): "
            + ", ".join(display_name(m) for m in r["members"]))
    elif sub == "leave":
        r["members"].remove(s.acc)
        heir = None
        if not r["members"]:
            del regs[mine]
        elif r["leader"] == s.acc:
            r["leader"] = heir = r["members"][0]
        save_regiments(regs)
        regiments_changed(*([s.acc] + ([heir] if heir else [])))      # the new leader gets the mark
        say(f"You left regiment {mine}.")
    elif sub == "rename":
        if r["leader"] != s.acc:
            return say("Only the regiment leader can do that.")
        if not regiment_name_ok(arg) or any(n.lower() == arg.lower() for n in regs):
            return say("Invalid or taken name (2-8 Chinese characters or 3-16 letters/digits).")
        if not res_can_pay(a, (0, 0, 0, REGIMENT_RENAME_URA)):
            return say(f"Renaming costs {REGIMENT_RENAME_URA} Uranium.")
        res_add(a, (0, 0, 0, -REGIMENT_RENAME_URA))
        regs[arg] = regs.pop(mine)
        accs[s.acc] = a; save_accounts(accs); save_regiments(regs)
        regiments_changed(*regs[arg]["members"])
        say(f"Regiment renamed to {arg} (-{REGIMENT_RENAME_URA} Uranium).")
    elif sub in ("open", "close", "kick"):
        if r["leader"] != s.acc:
            return say("Only the regiment leader can do that.")
        if sub == "kick":
            who = next((m for m in r["members"] if m.lower() == arg.lower()), None)
            if not who or who == s.acc:
                return say("No such member.")
            r["members"].remove(who)
        else:
            r["open"] = (sub == "open")
        save_regiments(regs)
        regiments_changed(*([who] if sub == "kick" else []))
        say(f"Done ({sub}).")
    else:
        say("/regiment create|join|leave|rename|open|close|kick|list|who")

def nick_command(s, want):
    """/nick NAME : the name other players see (Chinese allowed; the login account does not change).  First one free,
    then NICK_CHANGE_URA Uranium.  /nick alone shows the current one."""
    say = lambda m: s.send(chat_line(0x0A, m, (120, 220, 255)))
    accs, a = get_account(s.acc)
    if not want:
        return say(f"Your name: {a.get('nick') or s.acc}.  /nick NAME to change it (letters, digits or Chinese).")
    try:
        nb = want.encode("gbk")
    except UnicodeEncodeError:
        return say("That name has characters the game cannot show.")
    if not (2 <= len(nb) <= NICK_MAX_BYTES) or not all(c.isalnum() for c in want):
        return say(f"Name: letters, digits or Chinese, at most {NICK_MAX_BYTES // 2} Chinese characters or {NICK_MAX_BYTES} letters.")
    low = want.lower()
    if any(low in (acc.lower(), (r.get("nick") or "").lower()) for acc, r in accs.items() if acc != s.acc and isinstance(r, dict)) \
            or npc_name_taken(want) or (low != s.acc.lower() and low in {x.lower() for x in accs}):
        return say("That name is taken.")
    if a.get("nick") and a["nick"] != want:
        if not res_can_pay(a, (0, 0, 0, NICK_CHANGE_URA)):
            return say(f"Changing your name costs {NICK_CHANGE_URA} Uranium.")
        res_add(a, (0, 0, 0, -NICK_CHANGE_URA))
    a["nick"] = want
    accs[s.acc] = a
    save_accounts(accs); accounts_flush_now()
    nick_rebuild(accs)
    cmd = a.get("commander", {})
    s.send(build_commander(s.acc, cmd.get("nation", 1), cmd.get("attrs", (0, 0, 0, 0)), resources=a["resources"]))
    log(f"   nick: {s.acc} -> {want!r}")
    say(f"Your name is now {want}.  Other players see it the next time you enter a map.")

def speed_command(s):
    """/speed : fast walking on town maps for SPEED_BOOST_HOURS hours, costs SPEED_BOOST_URA Uranium (paid accounts always walk fast)."""
    say = lambda m: s.send(chat_line(0x0A, m, (255, 200, 80)))
    accs, a = get_account(s.acc)
    if a.get("paid"):
        return say("Paid account: you always walk at the fast speed.")
    left = a.get("speed_boost_until", 0) - time.time()
    if left > 0:
        return say(f"Fast walking is active for another {left / 60:.0f} minute(s).")
    if not res_can_pay(a, (0, 0, 0, SPEED_BOOST_URA)):
        return say(f"Fast walking ({SPEED_BOOST_HOURS} h) costs {SPEED_BOOST_URA} Uranium.")
    res_add(a, (0, 0, 0, -SPEED_BOOST_URA))
    a["speed_boost_until"] = time.time() + SPEED_BOOST_HOURS * 3600
    accs[s.acc] = a
    save_accounts(accs)
    s.send(build_commander(s.acc, a.get("commander", {}).get("nation", 1), a["commander"]["attrs"], resources=a["resources"]))
    say(f"Fast walking for {SPEED_BOOST_HOURS} hours (-{SPEED_BOOST_URA} Uranium). It applies the next time you enter a map.")

def unlock_unit_command(s, text):
    """(19:16, original) /wight, /quorg: unlock the chassis in the Factory for URA_PRICE Uranium, once per commander.
    The original asked before paying -> /wight shows the price, /wight yes pays."""
    words = text.lower().split()
    name = {"/wight": "Wight", "/quorg": "Quorg"}[words[0]]
    cost = URA_PRICE[name]
    say = lambda m: s.send(chat_line(0x0A, m, (255, 200, 80)))
    accs, a = get_account(s.acc)
    cmd = PG.ensure_commander(a.setdefault("commander", {}))
    if unit_unlocked(a, name):
        return say(f"The {name} is already unlocked - buy it in the Factory.")
    if len(words) < 2 or words[1] not in ("yes", "y", "ok"):
        return say(f"Unlock the {name} in the Factory for {cost} Uranium? Type /{name.lower()} yes to confirm.")
    if not res_can_pay(a, (0, 0, 0, cost)):
        return say(f"Unlocking the {name} costs {cost} Uranium (you have {a['resources'][3]}).")
    res_add(a, (0, 0, 0, -cost))
    cmd.setdefault("unlocked", []).append(name)
    accs[s.acc] = a; save_accounts(accs)
    s.cmd = cmd
    s.send(build_commander(s.acc, cmd.get("nation", 1), cmd["attrs"], resources=a["resources"]))
    audit("unit_unlock", s.acc, unit=name, cost=cost)
    log(f"   {s.acc} unlocked {name} (-{cost} Uranium)")
    say(f"The {name} is unlocked (-{cost} Uranium). You can now buy it in the Factory.")

def reset_points(s):
    """/reset : all spent attribute points back to the point pool, costs ATTR_RESET_URA"""
    accs, a = get_account(s.acc)
    cmd = PG.ensure_commander(a.setdefault("commander", {}))
    sp = cmd.get("spent_attrs") or [0, 0, 0, 0]
    spent = sum(sp)
    say = lambda m: s.send(chat_line(0x0A, m, (120, 220, 255)))
    if spent <= 0:
        return say("You have no spent attribute points to reset.")
    if not res_can_pay(a, (0, 0, 0, ATTR_RESET_URA)):
        return say(f"Resetting attribute points costs {ATTR_RESET_URA} Uranium.")
    res_add(a, (0, 0, 0, -ATTR_RESET_URA))
    cmd["points"] = cmd.get("points", 0) + spent
    cmd["attrs"] = [max(0, x - y) for x, y in zip(cmd["attrs"], sp)]
    cmd["spent_attrs"] = [0, 0, 0, 0]
    accs[s.acc] = a; save_accounts(accs)
    s.cmd = cmd
    s.send(build_commander(s.acc, cmd.get("nation", 1), cmd["attrs"], resources=a["resources"]))
    s.send(build_hero_info(s))
    say(f"Attribute points reset: {spent} point(s) returned (-{ATTR_RESET_URA} Uranium).")
    refresh_hero_marks(s.acc)

STAR_MAP = 400000004               # Black Tortoise: reuses an alien-cave map (original star maps are not in the client)
STAR_REWARD_MULT = 5              # kill rewards on the star

def enter_star(s):
    accs, a = get_account(s.acc)
    nid = a.get("commander", {}).get("nation", 1)
    say = lambda m: s.send(chat_line(0x0A, m, (120, 220, 255)))
    if star_time_left(nid) <= 0:
        return say("Your faction has no demon-star time. Fill the national power bar first.")
    if not star_window_open():
        return say("The demon stars are open 12:00-13:00 and 19:00-20:00 (server time).")
    if getattr(s, "battle", None):
        return say("Leave your current battle first.")
    _why = star_travel(s, star_planet(nation_star(nid)))      # (2026-10-27) the nation's demon-star planet
    if _why:
        say(_why)

def _help_text():
    """/help, /help regiment, /help uranium, /help star in the player's language (prices from the server constants)."""
    rc = REGIMENT_CREATE_COST
    return {
        "zh-cn": {
            "": ["聊天指令：/nick 名字　/mail 信件　/speed 快速移动　/reset 重置属性点　/lang zh|en 语言　/star 魔星　/regiment 军团",
                 "/help regiment 军团指令；/help uranium 铀的用途；/help star 魔星说明",
                 "战斗中（同盟或战场频道）：占点、集合、打 B3、守 B3、侦察 D2、E3有飞机、A2有敌人、救 C3；走到星门按 OK 撤退该单位"],
            "star": ["/star - 进入本阵营这次轮到的魔星（需要魔星时间，12:00 / 19:00 各开放 1 小时；也可从星门进入）",
                     "从角落打到中心省（第 4 列第 4 行）并占领，中心省研究所贩售该魔星的专属装备；怪物会反扑，时段结束全部重置"],
            "uranium": [f"/reset - 重置已分配的属性点（{ATTR_RESET_URA} 铀）",
                        f"F8 - 每天 {HOME_FREE_PER_DAY} 次免费传送回首都，之后每次 {HOME_TELEPORT_URA} 铀",
                        f"太空中心 - 换阵营 {NATION_CHANGE_URA} 铀，转生 {REINC_URA} 铀",
                        f"/wight、/quorg - 在工厂解锁 Wight（{URA_PRICE.get('Wight', 250)}）/ Quorg（{URA_PRICE.get('Quorg', 800)} 铀）",
                        f"/regiment rename - {REGIMENT_RENAME_URA} 铀",
                        f"/speed - 城镇快速移动 3 小时（{SPEED_BOOST_URA} 铀）",
                        f"/nick - 改名（第一次免费，之后 {NICK_CHANGE_URA} 铀）"],
            "regiment": [f"/regiment create 名字 - 建立军团（金钱 {rc[0]}、矿 {rc[1]}、硅 {rc[2]}）；每个阵营最多 {REGIMENT_MAX_PER_NATION} 个",
                         f"/regiment rename 名字 - 团长：改名（{REGIMENT_RENAME_URA} 铀）",
                         "/regiment join 名字 - 加入本阵营开放中的军团",
                         "/regiment leave - 离开军团",
                         "/regiment open|close - 团长：开放／停止招收新成员",
                         "/regiment kick 指挥官 - 团长：踢出成员",
                         "/regiment list - 全部军团",
                         "/regiment who - 本军团成员"]},
        "zh-tw": {
            "": ["聊天指令：/nick 名字　/mail 信件　/speed 快速移動　/reset 重置屬性點　/lang zh|en 語言　/star 魔星　/regiment 軍團",
                 "/help regiment 軍團指令；/help uranium 鈾的用途；/help star 魔星說明",
                 "戰鬥中（同盟或戰場頻道）：佔點、集合、打 B3、守 B3、偵察 D2、E3有飛機、A2有敵人、救 C3；走到星門按 OK 撤退該單位"],
            "star": ["/star - 進入本陣營這次輪到的魔星（需要魔星時間，12:00 / 19:00 各開放 1 小時；也可從星門進入）",
                     "從角落打到中心省（第 4 列第 4 行）並佔領，中心省研究所販售該魔星的專屬裝備；怪物會反撲，時段結束全部重置"],
            "uranium": [f"/reset - 重置已分配的屬性點（{ATTR_RESET_URA} 鈾）",
                        f"F8 - 每天 {HOME_FREE_PER_DAY} 次免費傳送回首都，之後每次 {HOME_TELEPORT_URA} 鈾",
                        f"太空中心 - 換陣營 {NATION_CHANGE_URA} 鈾，轉生 {REINC_URA} 鈾",
                        f"/wight、/quorg - 在工廠解鎖 Wight（{URA_PRICE.get('Wight', 250)}）/ Quorg（{URA_PRICE.get('Quorg', 800)} 鈾）",
                        f"/regiment rename - {REGIMENT_RENAME_URA} 鈾",
                        f"/speed - 城鎮快速移動 3 小時（{SPEED_BOOST_URA} 鈾）",
                        f"/nick - 改名（第一次免費，之後 {NICK_CHANGE_URA} 鈾）"],
            "regiment": [f"/regiment create 名字 - 建立軍團（金錢 {rc[0]}、礦 {rc[1]}、矽 {rc[2]}）；每個陣營最多 {REGIMENT_MAX_PER_NATION} 個",
                         f"/regiment rename 名字 - 團長：改名（{REGIMENT_RENAME_URA} 鈾）",
                         "/regiment join 名字 - 加入本陣營開放中的軍團",
                         "/regiment leave - 離開軍團",
                         "/regiment open|close - 團長：開放／停止招收新成員",
                         "/regiment kick 指揮官 - 團長：踢出成員",
                         "/regiment list - 全部軍團",
                         "/regiment who - 本軍團成員"]},
        "en": dict(HELP_LINES, **{"": [
            "Chat commands:  /nick NAME  /mail  /speed  /reset  /lang zh|en  /star  /regiment ...",
            "/help regiment  - regiment commands;  /help uranium  - what Uranium buys;  /help star  - demon stars",
            "In battle (ally / battle channel): capture, rally, attack B3, hold B3, scout D2, air E3, enemy A2, help C3"]}),
    }

HELP_LINES = {
    "star": ["/star    - enter your faction's current demon star (needs demon-star time, 12:00 / 19:00 for 1 h; or use the Dimensional Matrix)",
             "/power   - GM: national power and star status",
             "Fight from your corner to the centre (col 4 row 4); its Lab sells that star's own gear. Monsters strike back; all resets at the window's end"],
    "uranium": ["/reset              - return spent attribute points (15 Uranium)",
                "F8                  - 5 free teleports home per day, then 5 Uranium each",
                "StarCenter          - switch faction 150 Uranium, reincarnation 30 Uranium",
                "/wight, /quorg      - unlock the Wight (250) / Quorg (800 Uranium) in the Factory",
                "/regiment rename    - 250 Uranium"],
    "regiment": ["/regiment create NAME  - found a regiment (money + ore + silicon); max 13 per faction",
                 "/regiment rename NAME  - leader: rename (250 Uranium)",
                 "/regiment join NAME    - join an open regiment of your faction",
                 "/regiment leave        - leave your regiment",
                 "/regiment open|close   - leader: allow / stop new members",
                 "/regiment kick HERO    - leader: remove a member",
                 "/regiment list         - all regiments",
                 "/regiment who          - members of your regiment"],
}

# ---- SERVER MAILBOX (user 2026-10-22 15:30) ------------------------------------------------------------------------------
# The client's own mail is a set of ASP web pages (lsbbs01_t.asp ...) that this server does not serve, so letters live in
# the account (a["mail"]) and are read with chat commands: /mail (list), /mail N (read), /mail del N.  A new commander gets
# the WELCOME letter (player commands); unread letters are announced at every login.  Letter texts are built when read,
# in the reader's language, so prices always match the server constants.
MAIL_MAX = 30

def mail_add(a, kind, **kw):
    box = a.setdefault("mail", [])
    nid = max([m.get("id", 0) for m in box] + [0]) + 1
    box.append(dict(kw, id=nid, kind=kind, t=time.time(), read=False))
    del box[:-MAIL_MAX]
    return nid

def _mail_lang(s):
    lang = getattr(s, "lang", "en")
    return lang if lang in ("zh-cn", "zh-tw") else "en"

def mail_text(m, lang):
    """(subject, [lines]) of a letter in this language."""
    if m.get("kind") == "welcome":
        rc = REGIMENT_CREATE_COST
        T = {
            "zh-cn": ("欢迎来到银河霸主 - 玩家指令", [
                "指挥官你好！以下是可以在聊天框输入的指令：",
                f"1. /nick 名字 - 设定中文昵称（最多 6 个中文字或 12 个字母；第一次免费，之后每次改名 {NICK_CHANGE_URA} 铀）。登入帐号不变。",
                f"2. /regiment create 名字 - 建立军团（金钱 {rc[0]}、矿 {rc[1]}、硅 {rc[2]}；每个阵营最多 {REGIMENT_MAX_PER_NATION} 个；名字 2-8 个中文字或 3-16 个字母）。",
                "   /regiment join 名字 加入、/regiment leave 离开、/regiment list 全部军团、/regiment who 成员、/help regiment 全部军团指令。",
                f"3. /speed - 城镇快速移动 3 小时（{SPEED_BOOST_URA} 铀；付费帐号永久快速）。",
                f"4. /reset - 重置属性点（{ATTR_RESET_URA} 铀）。",
                "5. /lang zh 或 /lang en - 切换伺服器讯息的语言。",
                "6. /star - 进入魔星（所属阵营的魔星时间内）。",
                f"7. F8 - 回首都（每天 {HOME_FREE_PER_DAY} 次免费）。",
                "8. /mail - 信件列表；/mail 编号 阅读；/mail del 编号 删除。/help - 指令说明。"]),
            "zh-tw": ("歡迎來到銀河霸主 - 玩家指令", [
                "指揮官你好！以下是可以在聊天框輸入的指令：",
                f"1. /nick 名字 - 設定中文暱稱（最多 6 個中文字或 12 個字母；第一次免費，之後每次改名 {NICK_CHANGE_URA} 鈾）。登入帳號不變。",
                f"2. /regiment create 名字 - 建立軍團（金錢 {rc[0]}、礦 {rc[1]}、矽 {rc[2]}；每個陣營最多 {REGIMENT_MAX_PER_NATION} 個；名字 2-8 個中文字或 3-16 個字母）。",
                "   /regiment join 名字 加入、/regiment leave 離開、/regiment list 全部軍團、/regiment who 成員、/help regiment 全部軍團指令。",
                f"3. /speed - 城鎮快速移動 3 小時（{SPEED_BOOST_URA} 鈾；付費帳號永久快速）。",
                f"4. /reset - 重置屬性點（{ATTR_RESET_URA} 鈾）。",
                "5. /lang zh 或 /lang en - 切換伺服器訊息的語言。",
                "6. /star - 進入魔星（所屬陣營的魔星時間內）。",
                f"7. F8 - 回首都（每天 {HOME_FREE_PER_DAY} 次免費）。",
                "8. /mail - 信件列表；/mail 編號 閱讀；/mail del 編號 刪除。/help - 指令說明。"]),
            "en": ("Welcome to Galactic Overlord - player commands", [
                "Welcome, Commander!  Commands you can type in the chat box:",
                f"1. /nick NAME - your display name (Chinese allowed, up to 6 Chinese characters or 12 letters; first one free, then {NICK_CHANGE_URA} Uranium). Your login does not change.",
                f"2. /regiment create NAME - found a regiment ({rc[0]} money, {rc[1]} ore, {rc[2]} silicon; at most {REGIMENT_MAX_PER_NATION} per faction).",
                "   /regiment join NAME, /regiment leave, /regiment list, /regiment who, /help regiment for all regiment commands.",
                f"3. /speed - fast walking in town for 3 hours ({SPEED_BOOST_URA} Uranium; paid accounts always walk fast).",
                f"4. /reset - return your spent attribute points ({ATTR_RESET_URA} Uranium).",
                "5. /lang zh or /lang en - language of the server messages.",
                "6. /star - enter the demon star (during your faction's demon-star time).",
                f"7. F8 - back to the capital ({HOME_FREE_PER_DAY} free per day).",
                "8. /mail - your letters; /mail N to read, /mail del N to delete.  /help - command help."]),
        }
        return T[lang]
    sub = m.get("subject") or {}
    body = m.get("body") or {}
    return sub.get(lang) or sub.get("en") or "?", body.get(lang) or body.get("en") or []

def mail_say(s, text, rgb=(255, 230, 140), popup=False):
    # sub 0x0A opens the one-line MESSAGE box (each line replaces the last - 15:50 screenshot), so letters go to the
    # chat window (sub 3 = plain line, kept in the chat history); only the unread notice uses the box
    s.send(chat_line(0x0A if popup else 3, text, rgb, tr=False))

MAIL_UI = {"zh-cn": ("你有 {n} 封未读信件，输入 /mail 阅读。", "信箱是空的。", "#{id} {new}{subj}", "[未读] ", "没有这封信。", "已删除。", "系统"),
           "zh-tw": ("你有 {n} 封未讀信件，輸入 /mail 閱讀。", "信箱是空的。", "#{id} {new}{subj}", "[未讀] ", "沒有這封信。", "已刪除。", "系統"),
           "en": ("You have {n} unread letter(s). Type /mail to read.", "Your mailbox is empty.", "#{id} {new}{subj}", "[new] ",
                  "No such letter.", "Deleted.", "System")}

def mail_command(s, arg):
    lang = _mail_lang(s); ui = MAIL_UI[lang]
    accs, a = get_account(s.acc)
    box = a.get("mail", [])
    parts = arg.split()
    if not parts:
        if not box:
            return mail_say(s, ui[1], popup=True)
        for m in box[-15:]:
            mail_say(s, ui[2].format(id=m["id"], new=("" if m.get("read") else ui[3]), subj=mail_text(m, lang)[0]))
        unread = [m for m in box if not m.get("read")]
        if unread:                                   # /mail opens the newest unread letter right away
            parts = [str(unread[-1]["id"])]
        else:
            return
    if parts[0].lower() in ("del", "delete") and len(parts) > 1 and parts[1].isdigit():
        n = int(parts[1]); keep = [m for m in box if m.get("id") != n]
        if len(keep) == len(box):
            return mail_say(s, ui[4])
        a["mail"] = keep; accs[s.acc] = a; save_accounts(accs)
        return mail_say(s, ui[5])
    if parts[0].isdigit():
        m = next((m for m in box if m.get("id") == int(parts[0])), None)
        if not m:
            return mail_say(s, ui[4])
        subj, lines = mail_text(m, lang)
        mail_say(s, f"== {subj} ({ui[6]}) ==", (255, 200, 80))
        for l in lines:
            mail_say(s, l)
        if not m.get("read"):
            m["read"] = True; accs[s.acc] = a; save_accounts(accs)
        return
    mail_say(s, "/mail  |  /mail N  |  /mail del N")

def mail_login_notice(s):
    try:
        if not getattr(s, "logged_in", False) or s.w.is_closing():
            return
        # user 15:51: unread letters are printed in full in the chat window at login (no /mail, no MESSAGE box)
        accs, a = get_account(s.acc)
        unread = [m for m in a.get("mail", []) if not m.get("read")]
        lang = _mail_lang(s)
        for m in unread[-3:]:
            subj, lines = mail_text(m, lang)
            mail_say(s, f"== {subj} ({MAIL_UI[lang][6]}) ==", (255, 200, 80))
            for l in lines:
                mail_say(s, l)
            m["read"] = True
        if unread:
            accs[s.acc] = a; save_accounts(accs)
    except Exception as e:
        log(f"   mail notice error: {e!r}")

# ---- STRATEGIC MAP ASSEMBLE / AVOID ORDERS (user 2026-10-25 21:05) ---------------------------------------------------
# Strategic map, bottom panel: ASSEMBLE (All / AntiGround / AntiAir / Speciality) and AVOID (All / Ground / Air) put an
# order on a province.  Client side (reverse engineered from SG.exe 1.8.5):
#   0x3F (empty)            sent on entering the strategic map (004adf20 -> 0054ecb0): asks for the marker list
#   0x40 [u16 nDel][u16 id]*nDel [u16 nAdd] {u8 type, u32 province, u32 setter, u8 scope, u16 regiment}*nAdd
#                           (00463880: the window's pending edits; the client clears them after sending, so the
#                           server must echo the result back)
#   server 0x3E [u16 n] {u16 id, u8 type, u32 province, u32 setter, s8 setter name, u8 scope, u16 regiment}*n  full list
#               (0054fc10; the s8 is read through the stream cursor 005a8da0 - Ghidra shows it as a constant "mrkminf")
#   server 0x3F [u16 nDel][u16 id]*nDel [u16 nAdd] {same record}*nAdd                                     delta (0054fdb0)
#   The window (004669b0, on open) MOVES the markers whose setter name = the own commander name into its edit store and
#   lists their ids as deleted; on close (00463ee0) it sends 0x40 = "delete all my old ones, add this set".  So the s8
#   must be the commander's client-side name (wire_name), else the player could never move / remove his own orders.
#   type (index into the client's text table 006a54a4): 0 All Unit Assemble, 1 AntiGround Assemble, 2 AntiAir Assemble,
#        3 Artillery Assemble, 4 Specialist Assemble, 5 All Unit Avoid, 6 Ground Unit Avoid, 7 Air Unit Avoid (>= 8 ignored)
#   setter = a second province (target of the order) or -1, scope 1 = faction order, 2 = regiment order (the client only
#   shows it when the regiment = its own 0x15 +0x44c), regiment = regiment id.
# Rules (original game): faction orders are given by the president / ruling council, regiment orders by the regiment
# leader; everybody of the faction sees the faction orders, only the regiment sees its own.
MARKER_TTL = 12 * 3600          # an order is dropped after 12 hours
MARKER_MAX_PER_NATION = 80

def _markers():
    global WORLD
    if WORLD is None:
        WORLD = load_world()
    m = WORLD.setdefault("markers", {"next": 1, "list": {}})
    now = time.time()
    dead = [k for k, r in m["list"].items() if now - r.get("t", now) > MARKER_TTL]
    for k in dead:
        m["list"].pop(k, None)
    return m

def _marker_rec(mid, r):
    nb = str(wire_name(r.get("acc", ""))).encode("latin-1", "replace")[:30]
    return (struct.pack(">HBII", int(mid) & 0xFFFF, r["type"] & 0xFF, r["prov"] & 0xFFFFFFFF, r["setter"] & 0xFFFFFFFF)
            + bytes([len(nb)]) + nb + struct.pack(">BH", r["scope"] & 0xFF, r["reg"] & 0xFFFF))

def _marker_visible(o, r):
    cmd = getattr(o, "cmd", {}) or {}
    if int(cmd.get("nation", 0) or 0) != r["nation"]:
        return False
    if r["scope"] == 2:
        return regiment_id_of(getattr(o, "acc", None)) == r["reg"]
    if r["scope"] not in (1, 2):
        return getattr(o, "acc", None) == r["acc"]
    return True

def is_council_member(acc, nid):
    """president, a seat of the president's council, or (no council set: _council_rows) a regiment leader of the faction."""
    p = politics(nid)
    low = str(acc).lower()
    if str(p.get("president", "")).lower() == low:
        return True
    if p["council"]:
        for v in p["council"].values():
            vals = v if isinstance(v, list) else [v]
            if any(str(x).lower() == low for x in vals):
                return True
        return False
    return any(str(g.get("leader", "")).lower() == low and int(g.get("nation", 0) or 0) == nid
               for g in load_regiments().values())

def build_marker_list(s):
    m = _markers()
    rows = [_marker_rec(k, r) for k, r in sorted(m["list"].items(), key=lambda kv: int(kv[0])) if _marker_visible(s, r)]
    return bytes([0x3E]) + struct.pack(">H", len(rows)) + b"".join(rows)

def _marker_push(dels, adds):
    """dels: [(id, rec)], adds: [(id, rec)] -> 0x3F delta to every online player who may see them."""
    for o in list(ONLINE):
        if not getattr(o, "logged_in", False) or o.w.is_closing():
            continue
        dd = [k for k, r in dels if _marker_visible(o, r)]
        aa = [(k, r) for k, r in adds if _marker_visible(o, r)]
        if not dd and not aa:
            continue
        o.send(bytes([0x3F]) + struct.pack(">H", len(dd)) + b"".join(struct.pack(">H", int(k) & 0xFFFF) for k in dd)
               + struct.pack(">H", len(aa)) + b"".join(_marker_rec(k, r) for k, r in aa))

def marker_edit(s, body):
    """client 0x40: delete / add ASSEMBLE and AVOID orders."""
    cmd = getattr(s, "cmd", {}) or {}
    nid = int(cmd.get("nation", 0) or 0)
    m = _markers()
    try:
        o = 1
        nd = struct.unpack_from(">H", body, o)[0]; o += 2
        del_ids = [struct.unpack_from(">H", body, o + 2 * i)[0] for i in range(nd)]; o += 2 * nd
        na = struct.unpack_from(">H", body, o)[0]; o += 2
        adds = []
        for i in range(na):
            typ, prov, setter, scope, reg = struct.unpack_from(">BIIBH", body, o); o += 12
            adds.append((typ, prov, setter, scope, reg))
    except struct.error as e:
        log(f"   marker edit by {s.acc}: bad packet {body.hex()} ({e})")
        return
    log(f"   marker edit by {s.acc}: delete {del_ids} add {adds}")
    council = is_council_member(s.acc, nid)
    my_reg = regiment_id_of(s.acc)
    _rn, _rg = regiment_of(s.acc)
    reg_leader = bool(_rg) and str(_rg.get("leader", "")).lower() == str(s.acc).lower()

    def may(scope, reg, owner_acc=None):
        if owner_acc is not None and owner_acc == s.acc:
            return True
        if scope == 1:
            return council
        if scope == 2:
            return reg == my_reg and (reg_leader or council)
        return owner_acc in (None, s.acc)

    gone, new, refused = [], [], 0
    for mid in del_ids:
        r = m["list"].get(str(mid))
        if r is None or r["nation"] != nid:
            continue
        if not may(r["scope"], r["reg"], r["acc"]):
            refused += 1; continue
        gone.append((mid, m["list"].pop(str(mid))))
    mine = sum(1 for r in m["list"].values() if r["nation"] == nid)
    for typ, prov, target, scope, reg in adds:
        if typ >= 8 or not prov or prov >= 0x80000000:   # (10-31) -1 = no province chosen yet (button pressed first)
            continue
        if scope == 2:
            reg = my_reg
        if not may(scope, reg):
            refused += 1; continue
        if mine >= MARKER_MAX_PER_NATION:
            refused += 1; continue
        # one order of a kind (assemble / avoid) per province and scope: a new one replaces the old one
        kind = typ >= 5
        for k, r in list(m["list"].items()):
            if (r["nation"] == nid and r["prov"] == prov and r["scope"] == scope and r["reg"] == (reg if scope == 2 else r["reg"])
                    and (r["type"] >= 5) == kind):
                gone.append((int(k), m["list"].pop(k))); mine -= 1
        mid = m["next"]
        for _ in range(65535):
            if str(mid) not in m["list"] and mid != 0:
                break
            mid = mid % 65535 + 1
        m["next"] = mid % 65535 + 1
        # "setter" (the u32 after the province) is NOT a user id: the window fills it with a second province (00462450 /
        # 004663e0: [+0x1c18] / [+0x1c1c]) or -1 (004624e0), and the tooltip looks it up in the province cache (00565ce0)
        rec = {"type": typ, "prov": prov, "setter": target, "scope": scope, "reg": reg if scope == 2 else 0,
               "nation": nid, "acc": s.acc, "t": time.time()}
        m["list"][str(mid)] = rec
        new.append((mid, rec)); mine += 1
    if gone or new:
        save_world(WORLD)
        _marker_push(gone, new)
        log(f"   markers of nation {nid}: -{[k for k, _ in gone]} +{[(k, r['type'], r['prov'], r['scope']) for k, r in new]}")
    if refused:
        if council or reg_leader:
            _say_lang(s, "部分指令无法设置（权限不足或数量已达上限）。", "部分指令無法設定（權限不足或數量已達上限）。",
                      "Some orders could not be set (no permission or too many orders).")
        else:
            _say_lang(s, "只有议会成员（国家指令）或军团长（军团指令）可以下达集结 / 回避指令。",
                      "只有議會成員（國家指令）或軍團長（軍團指令）可以下達集結 / 迴避指令。",
                      "Only council members (faction orders) or regiment leaders (regiment orders) can give assemble / avoid orders.")
        # the client already dropped its pending edits: resend the true list so its map matches the server
        s.send(build_marker_list(s))
