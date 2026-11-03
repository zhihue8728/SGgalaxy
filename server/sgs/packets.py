# sgserver part "packets": order ownership checks, packet handlers (PACKET_HANDLERS).
# Loaded by sgserver.py into ONE shared namespace (exec, in the order of PARTS) - not an importable module;
# every name here is a sgserver global.  Checks: python tools/check_server.py
# ---- ANTI-CHEAT: lump order ownership / skills (2026-10-21) ------------------------------------------------------
# Battle is lock-step: the server relays every order to every client and they all execute it.  Before, the relay did
# not check WHO owns the unit: a forged lump could move / stop / fire skills with an enemy player's units or the
# aliens, and a forged 0x1e (-> 0x23 Death) killed ANY unit on every client.  Now:
#   - orders (0x16 / 0x17 / 0x29 / 0x30 / 0x18 / 0x21) only for the sender's own units (put / alive / hero)
#   - 0x1e death reports: own units or aliens only
#   - 0x30 active skills only if the unit really has that skill (UNIT_SKILLS from its items)
#   - an id nobody on the map owns is still relayed (unknown cases, logged) so nothing legitimate breaks.
SKILL_CHECK_ACTIONS = {6, 8, 10, 12, 13, 14, 16, 17, 21, 22, 23, 25, 28, 29, 33, 38, 41, 45, 46, 48, 59, 60}

def owns_unit(s, uid):
    return (uid in getattr(s, "put_args", {}) or uid in (getattr(s, "alive_units", None) or ())
            or uid == getattr(s, "hero_uid", None))

def order_owner_refused(s, m):
    try:
        if m[0] not in (0x16, 0x17, 0x1E, 0x29, 0x30, 0x18, 0x21) or len(m) < 5:
            return None
        uid = struct.unpack_from(">I", m, 2 if m[0] == 0x18 else 1)[0]
        if m[0] == 0x18 and len(m) < 9:
            return None
        if owns_unit(s, uid):
            if m[0] == 0x30 and len(m) >= 6 and m[5] in SKILL_CHECK_ACTIONS and uid in UNIT_SKILLS:
                bit = ACTION_BIT.get(m[5])
                if bit is not None and bit not in {sk[0] for sk in UNIT_SKILLS[uid]}:
                    return f"unit {uid} has no skill for action {m[5]} (bit {bit})"
            return None
        alien = uid in getattr(s, "targets", {}) or uid in dead_aliens(s)
        if m[0] == 0x1E and alien:
            return None                              # alien death reports (dedup / plausibility elsewhere)
        other = next((o for o in map_peers(s) if owns_unit(o, uid)), None)
        if alien:
            return f"order 0x{m[0]:02x} for alien {uid}"
        if other is not None:
            return f"order 0x{m[0]:02x} for unit {uid} of {other.acc}"
    except Exception:
        pass
    return None

def ally_order_refused(s, m):
    try:
        if m[0] == 0x29 and len(m) >= 9:
            tid = struct.unpack_from(">I", m, 5)[0]
            o = owner_peer(s, tid)
            # TK (user rule 2026-10-21): only players of the SAME nation, and only when BOTH have TK on (Ctrl+F6);
            # allied nations can never attack each other.
            if o and side_nation(s) == side_nation(o):
                if not (getattr(o, "allow_tk", False) and getattr(s, "allow_tk", False)):
                    return f"TK: {s.acc} -> {o.acc} refused (both players need TK on)"
            elif o and same_side(side_nation(s), side_nation(o)):
                return f"{o.acc} is an allied nation (allies never attack each other)"
        elif m[0] == 0x30 and len(m) >= 10 and m[5] in (3, 5, 0x24):   # load / teleport / board order (10 = Repair)
            tid = struct.unpack_from(">I", m, 6)[0]
            o = owner_peer(s, tid)
            if o and same_side(side_nation(s), side_nation(o)) and not getattr(o, "allow_tp", True):
                return f"{o.acc} has TP off (units not transportable by allies)"
    except Exception:
        pass
    return None

def handle_packet(s, body):
    """one client packet -> its handler.  (ARCH_REVIEW B3, 2026-10-24: was one 950-line if/elif chain; the branches
    are now one function per packet type, _pkt_XX, found through PACKET_HANDLERS; same tests, same order.)"""
    body = NP.en_bytes(body, getattr(s, "lang", "en"))      # a Chinese NPC name the client sends back = the real English name
    t = body[0]
    if getattr(s, "gate_pushing", False) and t not in GATE_IDLE_TYPES:
        # (2026-10-27) the client sends nothing when the Dimensional Matrix closes; the first other packet (walking,
        # chat, ...) means it is closed -> stop resending 0x38, which could reopen it
        s.gate_pushing = False
        s.gate_push_id = getattr(s, "gate_push_id", 0) + 1
        log(f"   orbit push stopped by client packet 0x{t:02x}")
    if star_center_blocked(s, body, t):
        return
    PACKET_HANDLERS.get(t, _pkt_default)(s, body, t)

def star_center_blocked(s, body, t):
    """(user 2026-10-27 13:02 "魔星 4 4 地圖應該只有 lab") the held demon-star centre loads as a capital-type map; only
    its Lab and Factory are open (user 13:21).  StarCenter, Dimensional Matrix / Observatory, exchange, FHQ, simulation board, CTF /
    caves / space station are refused and the hero is put back on the centre map (closes the building screen)."""
    m = getattr(s, "map", None)
    if not (m and is_star_province(m) and m % 100000 == STAR_CENTER):
        return False
    n = len(body)
    blocked = ((t == 0x34 and n >= 6) or t in (0x36, 0x37)
               or (t == 0x39 and n >= 3 and body[1] == 0) or (t == 0x2b and n >= 2 and body[1] == 1)
               or (t == 0x2e and n >= 9 and (struct.unpack_from(">I", body, 1)[0] >= 100000000
                                              or (struct.unpack_from(">I", body, 1)[0] // 10000) % 10 == 9)))
    if not blocked:
        return False
    log(f"   demon-star centre: building packet 0x{t:02x} refused ({body[:10].hex()})")
    s.send(chat_line(0x0A, "Only the Lab and the Factory are open in the centre of a demon star.", (255, 200, 60)))
    x, y = getattr(s, "hero_pos", None) or (0x200, 0x200)
    enter_field(s, m, x, y)
    return True

GATE_IDLE_TYPES = {0x58, 0x39}     # keep-alive / the matrix's own requests do not close it

def _pkt_default(s, body, t):
    """a packet type without a handler (or a sub-case nobody handles)."""
    if t not in (0x60,):
        log(f"   UNHANDLED client packet 0x{t:02x}: {body.hex()}")

def _pkt_00(s, body, t):
    if t == 0 and len(body) >= 6:
        ver = struct.unpack_from(">H", body, 1)[0]
        log(f"   handshake: version={ver:#06x} (0xB9=1.8.5) flags={body[3]:#04x},{body[4]:#04x} nation={chr(body[5])!r}")
        # sub-code 0 + checksum that never matches the client's cache -> client asks for the list (type 0x0B)
        s.send(bytes([0, 0]) + struct.pack(">I", 0xFFFFFFFF))
    else:
        _pkt_default(s, body, t)          # (no sub-case matched: like the old if-chain, the default)

def acc_id_ok(acc):
    """user 2026-10-25 14:15: account IDs may be English letters, digits, '_' and Chinese characters (a character = 2 bytes,
    GBK / Big5: lead 0x81..0xFE, trail 0x40..0xFE except 0x7F).  The account name is the raw client bytes read as latin-1
    (read_s8), so the same ID typed on a GBK and a Big5 client is two different IDs.  3..16 BYTES, first character a letter or
    a Chinese character."""
    if not acc:
        return False
    try:
        b = acc.encode("latin-1")
    except UnicodeEncodeError:
        return False
    if not 3 <= len(b) <= 16:
        return False
    i, first = 0, True
    while i < len(b):
        c = b[i]
        if c < 0x80:
            ch = chr(c)
            if not (ch.isascii() and (ch.isalpha() or (not first and (ch.isdigit() or ch == "_")))):
                return False
            i += 1
        elif 0x81 <= c <= 0xFE and i + 1 < len(b) and 0x40 <= b[i + 1] <= 0xFE and b[i + 1] != 0x7F:
            i += 2
        else:
            return False
        first = False
    return True

def _pkt_02(s, body, t):
    if t == 0x02:
        acc, o = read_s8(body, 1); pw, o = read_s8(body, o); mail, o = read_s8(body, o)
        s.reg_acc = acc
        accs = load_accounts()
        import re as _re
        if not acc_id_ok(acc):
            # user 2026-10-25 14:15: an ID may be Chinese (GBK / Big5 double bytes) as well as letters / digits / _
            log(f"   register: account {acc!r} rejected (letters, digits, _ or Chinese; 3-16 bytes, no digit / _ first)")
            msg = b"ID: 3-16 bytes, letters / digits / Chinese, first not a digit."
            s.send(bytes([2, 1, len(msg)]) + msg)
        elif acc in accs or any(k.lower() == acc.lower() for k in accs) or npc_name_taken(acc) or nick_account(acc).lower() != acc.lower():   # also not someone's nickname
            log(f"   register: account {acc!r} already exists -> fail")
            msg = b"This ID already exists."
            s.send(bytes([2, 1, len(msg)]) + msg)   # client reads an s8 error text after a non-zero code
        else:
            # PENDING until the New-commander screen is confirmed (0x04): quitting before that deletes the account
            # again (drop_pending_account), so the ID can be registered anew (user 2026-10-22 18:53)
            accs[acc] = {"email": mail, "pending": time.time()}
            STORE.pw_set(accs[acc], pw)                            # salted hash, never the plain password
            save_accounts(accs); accounts_flush_now()          # new accounts hit the disk at once
            log(f"   register: new account {acc!r} email={mail!r} -> ok")
            s.send(bytes([2, 0]))
    else:
        _pkt_default(s, body, t)          # (no sub-case matched: like the old if-chain, the default)

def _pkt_03(s, body, t):
    if t == 0x03:
        acc, o = read_s8(body, 1); pw, o = read_s8(body, o)
        accs = load_accounts()
        ip = s.peer[0] if isinstance(s.peer, tuple) else str(s.peer)
        if login_blocked(ip):
            log(f"   ANTI-CHEAT: login {acc!r} from {ip} refused: {LOGIN_FAIL_MAX} failed logins in {LOGIN_FAIL_WINDOW}s")
            audit("login_blocked", acc, ip=ip)
            msg = b"Too many failed logins. Try again in 5 minutes."
            s.send(bytes([2, 1, len(msg)]) + msg)
            return
        if acc in accs and accs[acc].get("pending") and getattr(s, "reg_acc", None) != acc:
            log(f"   login {acc!r}: account still in the New-commander screen of another session -> refused")
            msg = b"Wrong ID or password."
            s.send(bytes([2, 1, len(msg)]) + msg)
        elif acc in accs and STORE.pw_check(accs[acc], pw):
            if STORE.pw_upgrade(accs[acc], pw):                    # old plain-text password -> hash
                save_accounts(accs)
            # one session per account: two logged-in sessions of the same account both load / save accounts.json
            # (item / resource duplication races) -> the OLD session is closed
            for o2 in list(ONLINE):
                if o2 is not s and getattr(o2, "logged_in", False) and getattr(o2, "acc", None) == acc:
                    log(f"   {acc!r} logged in again from {s.peer} -> closing the old session {o2.peer}")
                    audit("double_login", acc, old=str(o2.peer), new=str(s.peer))
                    o2.logged_in = False
                    try:
                        o2.w.close()
                    except Exception:
                        pass
            log(f"   login: {acc!r} OK -> 02 00, then 0x06 (mode 1) + 0x15 (commander)")
            s.logged_in = True
            client_hash_watch(s)
            s.acc = acc
            s.send(bytes([2, 0]))
            s.send(build_nations(neutral=True, s=s, acc=acc))
            s.send(build_relations())         # builds the nation group table -> other nations are enemies
            s.send(bytes([6, 1]))
            s.cmd = accs[acc].get("commander", {"nation": 1, "look": 1})
            s.cmd.setdefault("nation", 1); s.cmd.setdefault("look", 1)
            _a2, a = get_account(acc)
            try:
                tutorial_login(acc, _a2, a)          # before 0x15: decides whether the tutorial may start
            except Exception as e:
                log(f"   tutorial flag error: {e!r}")
            s.send(build_commander(acc, s.cmd["nation"], s.cmd.get("attrs", (0, 0, 0, 0)), resources=a["resources"]))
            asyncio.get_event_loop().call_later(6.0, mail_login_notice, s)
            try:
                ura_on_login(s)
            except Exception as e:
                log(f"   ura login error: {e!r}")
            try:                              # demon-star reminder (user 2026-10-27 "魔星时间没有提示")
                _st = star_status_text(s.cmd.get("nation", 1))
                if _st:
                    asyncio.get_event_loop().call_later(4.0, lambda: s.send(chat_line(0x0A, _st, (255, 200, 60))))
            except Exception as e:
                log(f"   star login notice error: {e!r}")
            try:                              # language of the last session (0xF6 arrives only after login)
                if a.get("acp"):
                    set_client_acp(s, int(a["acp"]))
            except Exception as e:
                log(f"   remembered code page error: {e!r}")
            pk = build_item_db_packets(s=s)
            for x in pk:
                s.send(x, quiet=True)
            log(f"   sent item database: {len(ITEMS)} items in {len(pk)} class-A 0x10 parts")
        else:
            log(f"   login: {acc!r} FAILED")
            LOGIN_FAILS.setdefault(ip, []).append(time.time())
            audit("login_failed", acc, ip=ip)
            msg = b"Wrong ID or password."
            s.send(bytes([2, 1, len(msg)]) + msg)   # client handler FUN_00431c30: 02 <code> [s8 text]
    else:
        _pkt_default(s, body, t)          # (no sub-case matched: like the old if-chain, the default)

def _pkt_04(s, body, t):
    if t == 0x04 and len(body) >= 12:
        # final create (client FUN_00558360): u32 nation, u8 look, u8 look(dup), 4 x u8 attributes (tactics, clout, education, mech)
        nation = struct.unpack_from(">I", body, 1)[0]
        look = body[5]
        attrs = list(body[7:11])
        acc = getattr(s, "reg_acc", None)
        log(f"   create commander: acc={acc!r} nation={nation} look={look} attrs={attrs}")
        if acc:
            accs = load_accounts()
            if acc in accs:
                accs[acc].pop("pending", None)                     # confirmed: the account is kept from now on
                accs[acc]["commander"] = {"nation": nation, "look": look, "attrs": attrs}
                if not any(m.get("kind") == "welcome" for m in accs[acc].get("mail", [])):
                    mail_add(accs[acc], "welcome")       # player commands letter (user 2026-10-22 15:30)
                save_accounts(accs)
    else:
        _pkt_default(s, body, t)          # (no sub-case matched: like the old if-chain, the default)

def _pkt_07(s, body, t):
    if t == 0x07 and len(body) >= 4:
        # change password from the login screen (FUN_004323a0): [s8 account][s8 old password][s8 new password];
        # answer 02 00 = "Successfully changed", 02 <code> = failure (FUN_00432570)
        acc, o = read_s8(body, 1); old, o = read_s8(body, o); new, o = read_s8(body, o)
        accs = load_accounts()
        if acc in accs and STORE.pw_check(accs[acc], old) and new:
            STORE.pw_set(accs[acc], new); save_accounts(accs); accounts_flush_now()
            log(f"   password of {acc!r} changed")
            s.send(bytes([2, 0]))
        else:
            log(f"   password change for {acc!r} refused")
            msg = b"Wrong ID or password."
            s.send(bytes([2, 1, len(msg)]) + msg)
    else:
        _pkt_default(s, body, t)          # (no sub-case matched: like the old if-chain, the default)

def _pkt_0a(s, body, t):
    if t == 0x0A:
        # CLIENT ERROR REPORT (0047e540): [u16 len][text] e.g. "S_24026296 O_0 CheckSumError at packet No : 28".
        # Kept in its own file so client-side failures are easy to find (2026-10-21).
        try:
            n = struct.unpack_from(">H", body, 1)[0] if len(body) >= 3 else 0
            text = body[3:3 + n].decode("latin-1", "replace").strip()
        except Exception:
            text = body[1:].hex()
        log(f"   CLIENT ERROR REPORT from {getattr(s, 'acc', '?')}: {text}")
        try:
            import datetime as _dt
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "client_errors.log"), "a",
                      encoding="utf-8") as f:
                f.write(f"{_dt.datetime.now():%Y-%m-%d %H:%M:%S}\t{getattr(s, 'acc', '?')}\t{s.peer}\t"
                        f"map {getattr(s, 'map', None)}\t{text}\n")
        except Exception as e:
            log(f"   client_errors.log write failed: {e!r}")
    else:
        _pkt_default(s, body, t)          # (no sub-case matched: like the old if-chain, the default)

def _pkt_0b(s, body, t):
    if t == 0x0B and len(body) >= 2 and body[1] == 1:
        log("   client requests server list -> sending 0x46")
        s.send(build_server_list(SERVERS))
    elif t == 0x0B and len(body) >= 3 and body[1] == 0:
        idx = body[2]
        log(f"   client selected server index {idx} -> redirect (type 3) to {PUBLIC_IP}:{PUBLIC_PORT}")
        s.send(build_redirect("127.0.0.1" if getattr(s, "relayed", False) else PUBLIC_IP, PUBLIC_PORT))   # relayed: stay on the relay
    else:
        _pkt_default(s, body, t)          # (no sub-case matched: like the old if-chain, the default)

def _pkt_0e(s, body, t):
    if t == 0x0E and len(body) >= 6 and body[1] == 1:
        # lock-step time sync (00547130): echo the client's ms and add our game time (1/100 s)
        s.send(bytes([0x0E, 1]) + body[2:6] + struct.pack(">I", game_time(s)))
    else:
        _pkt_default(s, body, t)          # (no sub-case matched: like the old if-chain, the default)

def _pkt_0f(s, body, t):
    if t == 0x0F:
        # New-commander screen.  The client's code page (0xF6) only arrives once in the game: the language comes from
        # the account (acp of an earlier session) or from the launcher's manifest download of this IP (ota_lang).
        log(f"   client requests nation table -> sending 0x0F ({session_lang_enc(s)[0]})")
        s.send(build_nations(s=s))
        s.send(build_relations())
    else:
        _pkt_default(s, body, t)          # (no sub-case matched: like the old if-chain, the default)

def _pkt_12(s, body, t):
    if t == 0x12 and len(body) >= 2:
        s.send(build_hof(body[1], s))
    else:
        _pkt_default(s, body, t)          # (no sub-case matched: like the old if-chain, the default)

def _pkt_19(s, body, t):
    if t == 0x19 and len(body) >= 2:
        if body[1] == 1:                       # deploy window OK: [01][u8 n] n x {u32 uid, u8 slot}
            set_deploy(s, body)
        elif getattr(s, "battle_mode", 0) and getattr(s, "alive_units", None) \
                and not getattr(s, "redeploy_pending", False):
            log(f"   F7 reinforcement request {body.hex()}")
            reinforce(s)
        else:                                  # ASSIGN / DEPLOY TROOPS, F7 outside a battle -> open the deploy window
            log("   0x19 [00] outside a battle -> class-B 0x1C (open the deploy window)")
            s.send(bytes([0x1C, 0]))   # 1-byte packets cannot be decoded by the client (CheckSumError) -> pad
    else:
        _pkt_default(s, body, t)          # (no sub-case matched: like the old if-chain, the default)

def _pkt_1b(s, body, t):
    if t == 0x1b and len(body) >= 6:
        # battle control dialog answer: [01 ATTACK | 02 ASSIST][u32 map][u16 x][u16 y]
        m = struct.unpack_from(">I", body, 2)[0]
        log(f"   battle control: {'ATTACK' if body[1] == 1 else 'ASSIST'} on {m}")
        s.side_nation = None
        w = rejoin_wait(s, m)
        if w > 0:
            log(f"   re-join refused: {s.acc} left {province_of(m)} recently, {w} s to wait")
            send_battle_control(s, m, *(PENDING_ARRIVAL.get(s.acc, (m, 0x800, 0x800))[1:]))
            return
        arrive_battle(s, m)
    else:
        _pkt_default(s, body, t)          # (no sub-case matched: like the old if-chain, the default)

def _pkt_1d(s, body, t):
    if t == 0x1d:
        apply_snapshot(s, body)
    else:
        _pkt_default(s, body, t)          # (no sub-case matched: like the old if-chain, the default)

def _pkt_1f(s, body, t):
    if t == 0x1f:
        log(f"   client: battle objectives complete / idle timer ({body.hex()})")
    else:
        _pkt_default(s, body, t)          # (no sub-case matched: like the old if-chain, the default)

def _pkt_20(s, body, t):
    if t == 0x20 and len(body) >= 2:
        # battle join codes (research_multiplayer.md): commander's answer [type+1 reject | type+2 accept][s8 name],
        # or a join request [1|7|8|13][u32 map]
        typ = body[1]
        if typ in (2, 3, 5, 6, 9, 10, 14, 15) and len(body) >= 3:
            name = body[3:3 + body[2]].decode("latin-1", "replace")
            answer_join(s, typ, name)
        elif typ in (8, 13) and len(body) >= 6 and getattr(s, "sim_board", False):
            m = struct.unpack_from(">I", body, 2)[0]
            log(f"   SIMULATION join request type {typ} for map {m}{' (WATCH)' if typ == 13 else ''}")
            sim_join(s, m, watch=(typ == 13))
        elif typ in (1, 7, 8, 13) and len(body) >= 6:
            m = struct.unpack_from(">I", body, 2)[0]
            log(f"   join request type {typ} for map {m}{' (WATCH)' if typ == 13 else ''}")
            s.side_nation = None
            # (2026-10-24) 0x20 [01] is the battle-control answer when the player's own nation is already listed in
            # the battle (004af1e0) - same rules as 0x1b, including the re-join wait
            if typ == 1 and PENDING_ARRIVAL.get(getattr(s, "acc", None), (None,))[0] == m:
                w = rejoin_wait(s, m)
                if w > 0:
                    log(f"   re-join refused: {s.acc} left {province_of(m)} recently, {w} s to wait")
                    send_battle_control(s, m, *(PENDING_ARRIVAL.get(s.acc, (m, 0x800, 0x800))[1:]))
                    return
            arrive_battle(s, m, watch=(typ == 13))
        elif typ == 4 and len(body) >= 10:
            m, side = struct.unpack_from(">II", body, 2)
            if not getattr(s, "cmd", {}).get("mercenary"):
                log(f"   mercenary offer from {s.acc} refused: not a mercenary")
            else:
                log(f"   MERCENARY {s.acc} offers his service to nation {side} in battle {m}")
                arrive_battle(s, m, side=side)
        else:
            log(f"   0x20 {body.hex()} (not handled)")
    else:
        _pkt_default(s, body, t)          # (no sub-case matched: like the old if-chain, the default)

def _pkt_23(s, body, t):
    if t == 0x23 and len(body) >= 3 and body[1] == 2:
        handle_user_info(s, body)
    elif t == 0x23 and len(body) >= 6 and body[1] == 1 and find_account_by_uid(struct.unpack_from(">I", body, 2)[0])[0] not in (None, getattr(s, "acc", None)):
        handle_user_info(s, body)
    elif t == 0x23 and len(body) >= 6 and body[1] == 1:
        # F4 / commander info: client sends [23][01][u32 commander id][00] and waits for server 0x27.
        cid = struct.unpack_from(">I", body, 2)[0]
        s.send(build_hero_info(s))
        log(f"   F4 commander info request id={cid} -> 0x27 sub 0")
    elif t == 0x23:
        log(f"   select/info request {body.hex()} (no reply yet)")
    else:
        _pkt_default(s, body, t)          # (no sub-case matched: like the old if-chain, the default)

def _pkt_25(s, body, t):
    if t == 0x25 and len(body) >= 5:
        # F4 attribute points: client FUN_005e0cf0 sends [25][+tactics][+clout][+education][+mech] (points added
        # with the arrows).  Spend them (never more than the unspent points), save, refresh 0x15 (NOT the F4 window).
        accs, a = get_account(getattr(s, "acc", None))
        cmd = PG.ensure_commander(a.setdefault("commander", {}))
        want = list(body[1:5])
        spent = [0, 0, 0, 0]
        for i, n in enumerate(want):
            for _ in range(n):
                if PG.spend_point(cmd, i):
                    spent[i] += 1
        accs[s.acc] = a
        save_accounts(accs)
        s.cmd = cmd if "nation" in cmd else getattr(s, "cmd", cmd)
        # 2026-10-21 23:14: the client sends 0x25 when the F4 window is CLOSED; answering with 0x27 (the F4 window
        # data) OPENED it again -> F4 could not be closed.  Only the commander record (+ the roster when Mech Apt /
        # caps changed) is refreshed now; the window is rebuilt from 0x27 the next time F4 is opened.
        s.send(build_commander(s.acc, cmd.get("nation", 1), cmd["attrs"], resources=a["resources"]))
        if any(spent):
            MECH_APT[s.acc] = PG.attr(cmd, 3)
            s.send(build_units([roster_rec(u) for u in a["units"]], mech=MECH_APT[s.acc]))
            # (user 2026-11-01 13:07 "the units' equipment is gone"): 0x16 sub 1 CLEARS the client's roster and
            # rebuilds the units without items - their equipment (class-A 0x1F) must follow, as on entering a map
            for u in a["units"]:
                if u.get("items"):
                    s.send(build_set_inventory(u["uid"], u["items"]))
        log(f"   F4 attribute points {want} -> spent {spent}, attrs now {cmd['attrs']}, {cmd['points']} points left")
        if any(spent):
            try:
                refresh_hero_marks(s.acc)          # PRESTIGE may have changed -> name badges (2026-10-27)
            except Exception as e:
                log(f"   badge refresh: {e!r}")
    else:
        _pkt_default(s, body, t)          # (no sub-case matched: like the old if-chain, the default)

def _pkt_2a(s, body, t):
    if t == 0x2a and len(body) >= 3:
        handle_chat(s, body)
    else:
        _pkt_default(s, body, t)          # (no sub-case matched: like the old if-chain, the default)

def _pkt_32(s, body, t):
    """(user 2026-10-27 19:51: Simulation board ENTER did nothing) the BATTLE SIMULATION board keeps its provinces as
    100000000 + province id; its ENTER (panel control 0x10, client 00435fa0 -> 0049e460) sends 0x32 [00][u32 sim id]
    for such an id (log: 'UNHANDLED client packet 0x32: 320005ff0b1d00' = 100600605).  -> the simulation starts."""
    if t == 0x32 and len(body) >= 6 and body[1] == 0:
        mid = struct.unpack_from(">I", body, 2)[0]
        if 100000000 <= mid < 200000000:
            log(f"   SIMULATION ENTER (0x32) on sim province {mid} by {getattr(s, 'acc', '?')}")
            sim_join(s, mid - 100000000)
            return
    _pkt_default(s, body, t)

def _pkt_2b(s, body, t):
    if t == 0x2b and len(body) >= 2 and body[1] == 1:
        # Battle Simulation Center board (CBoardWnd sim mode, client 00565650 sends [01][00])
        s.sim_board = True
        s.send(build_sim_map(s))
    elif t == 0x2b:
        s.sim_board = False
        # client opens / refreshes the strategic map.  Reply 0x2d (client 00569d90 -> 00569490 + 00569830):
        #   section A: u16 n, u16 ?, n x {u32 province, u8, s8 name, u8, u32 owner nation,
        #              u8 ?, u8 battle (if !=0: u8, u16 timer, u8), u8 k, k x {u32 nation, u8 heroes, u8 ?}}
        #   section B: u16 n, n x {u32 province, s8 name, u8, u16, u8, u8 k, k x {u32, u8, u8}}   (battles; none)
        # Field meanings are inferred from the parser (section B fills owner=0xff, battle=1 as constants).  EXPERIMENTAL.
        _now = time.monotonic()
        if _now - getattr(s, "map_reply_t", -9.0) < MAP_REFRESH_MIN:
            log("   strategic map: REFRESH ignored (< 1 s since the last one)")
            return
        s.map_reply_t = _now
        send_strategic_map(s)
        s.map_seen = True; s.info_t = time.time()
        s.map_sig = _map_signature(current_planet(s))
        # The preview minimap's tile table (object +0x10) is only built by the first 0x2e handled; a normal province as
        # FIRST preview crashed at SG.exe+0x8d533 (EAX=0, 2026-10-21 00:27/00:31/00:35).  Worked when the client had
        # previously been answered for the player's own (capital) province -> push that one right after the map.
        try:
            here = getattr(s, "cur_province", None) or CAPITALS.get(getattr(s, "cmd", {}).get("nation"))
            if here:
                s.send(build_province_info(s, province_of(here)))
            # REFRESH also renews the province the player is looking at (cave counts / recovery time, user 16:14)
            _ip = getattr(s, "info_pid", None)
            if _ip and _ip != (province_of(here) if here else None) and time.time() - getattr(s, "info_t", 0) < 600:
                s.send(build_province_info(s, _ip))
        except Exception as e:
            log(f"   preview prime failed: {e!r}")
    else:
        _pkt_default(s, body, t)          # (no sub-case matched: like the old if-chain, the default)

def _pkt_2c(s, body, t):
    if t == 0x2c and len(body) >= 5:
        pid = struct.unpack_from(">I", body, 1)[0]
        s.send(build_province_info(s, pid))
        s.info_pid, s.info_t = pid, time.time()
    else:
        _pkt_default(s, body, t)          # (no sub-case matched: like the old if-chain, the default)

def _pkt_2d(s, body, t):
    if t == 0x2d and len(body) >= 6:
        # client walks into a unit shop building (Factory): u32 shop id, u8, u8.
        # Reply 0x2f '@' (client 004a63d0 -> opens "Shop Wnd", data parsed by 0048ade0):
        #   u32 shop id, u8 N merchant chassis {u8, u8, u8, s8 chassis name (must exist in the client's unit table
        #   CUnitInfoMan, sent by the server in class-A 0x44), 5 x u32}, u8 M own units {u32 unit id, 5 x u32, 5 x u32}
        # FIRST STEP: empty shop (no unit catalogue yet).
        # sub (body[5]): 1 = enter, 2 = PURCHASE [u8 ?][s8 chassis][u8] (confirmed), others unknown yet.
        shop = struct.unpack_from(">I", body, 1)[0]
        sub = body[5]
        acc = getattr(s, "acc", None)
        accs, a = get_account(acc)
        if sub == 1:
            s.send(build_unit_shop(shop, a["units"], center_price_mult(s), a.setdefault("commander", {})))
            log(f"   enter unit shop {shop} -> 0x2f '@' with {len(UNIT_CATALOG)} chassis, {len(a['units'])} own")
        elif sub == 2 and len(body) >= 8:
            chassis, _o = read_s8(body, 7)
            chassis = UN.to_english(chassis, s.lang, s.enc)
            chassis = CODE_OF.get(chassis, chassis)        # stored by art code
            price = unit_buy_price(chassis, center_price_mult(s))     # the same price the shop list shows
            res = a["resources"]
            if price is None:
                log(f"   BUY {chassis!r}: not in catalogue")
            elif DISPLAY.get(chassis, chassis) in URA_PRICE and not unit_unlocked(a, DISPLAY.get(chassis, chassis)):
                _nm = DISPLAY.get(chassis, chassis)
                log(f"   BUY {chassis!r}: not unlocked (/{_nm.lower()})")
                s.send(chat_line(0x0A, f"Unlock the {_nm} first: type /{_nm.lower()} ({URA_PRICE[_nm]} Uranium).", (255, 200, 80)))
            elif len(a["units"]) >= roster_cap(a.get("commander", {})):
                log(f"   BUY {chassis!r}: division full ({roster_cap(a.get('commander', {}))})")
            elif PG.influence(PG.ensure_commander(a.setdefault("commander", {})), unit_branch(chassis)) < _INFL.get(DISPLAY.get(chassis, chassis), 1):
                log(f"   BUY {chassis!r}: influence {PG.influence(a['commander'], unit_branch(chassis))} < required "
                    f"{_INFL.get(DISPLAY.get(chassis, chassis), 1)} (influence = branch level + Clout // 2)")
            elif not res_pay(a, price):
                log(f"   BUY {chassis!r}: not enough resources {res} < {price}")
            else:
                # never reuse an id of a sold unit (the client may still know it)
                uid = new_unit_uid({**accs, acc: a})
                a["next_uid"] = uid + 1
                a["units"].append({"uid": uid, "chassis": chassis})
                ensure_loadouts(a)                   # stock equipment, else the deploy window refuses the unit
                if acc in accs:
                    accs[acc] = a; save_accounts(accs)
                s.send(build_units([(uid, DISPLAY.get(chassis, chassis), DISPLAY.get(chassis, chassis))], sub=2, mech=mech_for(s)))
                if a["units"][-1].get("items"):
                    s.send(build_set_inventory(uid, a["units"][-1]["items"]))
                _c = a.get("commander", {})
                s.send(build_commander(acc, _c.get("nation", 1), _c.get("attrs", (0, 0, 0, 0)), resources=a["resources"]))
                log(f"   BUY {chassis!r} -> unit {uid}, resources now {a['resources']}, roster {len(a['units'])}")
        elif sub == 3 and len(body) >= 10:
            # SELL (confirmed: [u32 shop][03][u32 unit id][u8]) -> refund half the price, remove from roster,
            # tell the client with 0x16 sub 3 [u32 id] (client FUN_00483820 removes it from YOUR UNITS too).
            uid = struct.unpack_from(">I", body, 6)[0]
            unit = next((u for u in a["units"] if u["uid"] == uid), None)
            if unit is None:
                log(f"   SELL unit {uid}: not in roster")
            else:
                refund = list(unit_sell_price(unit["chassis"]))
                a["units"].remove(unit)
                res_add(a, refund)
                if acc in accs:
                    accs[acc] = a; save_accounts(accs)
                s.send(bytes([0x16, 3]) + struct.pack(">I", uid))
                # the client does not add the refund itself: send the new resources (0x15), else the Factory kept
                # showing the old amounts (user 2026-10-22 19:23)
                _c = a.get("commander", {})
                s.send(build_commander(acc, _c.get("nation", 1), _c.get("attrs", (0, 0, 0, 0)), resources=a["resources"]))
                s.send(chat_line(0x0A, {"zh-cn": "卖出回收：", "zh-tw": "賣出回收："}.get(_mail_lang(s), "Sold for: ")
                                 + ", ".join(f"{n} {v}" for n, v in zip(_res_names(s), refund) if v), (120, 220, 255), tr=False))
                log(f"   SELL unit {uid} ({unit['chassis']}) refund {refund} -> resources {a['resources']}")
        elif sub == 4 and len(body) >= 10:
            # REPAIR (REPAIR ALL sends one per unit): [u32 shop][04][u32 unit id][u8].  Units are not damaged on the
            # server yet, so repair is free: answer with 0x2f 'B' (client 00484040: u32 id, 5 x u32 repair cost)
            # = 0 and re-send the unit record (0x16 sub 4).
            uid = struct.unpack_from(">I", body, 6)[0]
            unit = next((u for u in a["units"] if u["uid"] == uid), None)
            if unit is None:
                log(f"   REPAIR unit {uid}: not in roster")
            else:
                cost = repair_cost(unit)
                if not res_pay(a, cost):
                    log(f"   REPAIR unit {uid}: not enough resources {a['resources']} < {cost}")
                    return
                hp_repair(unit)
                s.send(build_commander(acc, getattr(s, "cmd", {}).get("nation", 1),
                                       getattr(s, "cmd", {}).get("attrs", (0, 0, 0, 0)), resources=a["resources"]))
                if acc in accs:
                    accs[acc] = a; save_accounts(accs)
                s.send(bytes([0x2F, 0x42]) + struct.pack(">I", uid) + struct.pack(">5I", 0, 0, 0, 0, 0))
                disp = DISPLAY.get(unit["chassis"], unit["chassis"])
                s.send(build_units([roster_rec(unit)], sub=4, mech=mech_for(s)))
                if unit.get("items"):                      # (11-01) the record update: its equipment again too
                    s.send(build_set_inventory(uid, unit["items"]))
                log(f"   REPAIR unit {uid} -> full hp {hp_base_full(unit)}, cost {cost}, resources {a['resources']}")
        else:
            log(f"   unit shop sub {sub} (unhandled) {body.hex()}")
    else:
        _pkt_default(s, body, t)          # (no sub-case matched: like the old if-chain, the default)

def _pkt_2e(s, body, t):
    if t == 0x2e and len(body) >= 9:
        # client asks to change map (entering a building such as the CTF, a portal, ...):
        # u32 target map id, u16 x, u16 y, u8, u8.  Answer by entering that field.
        mapid = struct.unpack_from(">I", body, 1)[0]
        x, y = struct.unpack_from(">HH", body, 5)
        cmd = getattr(s, "cmd", {"nation": 1})
        # FIELD PORTAL (Portals.por type 1, client FUN_004d0b30): the target is a fixed neighbouring province from
        # the portal table, written with the portal file's own planet digit (e.g. 100701 = col 7 row 1).  Map it
        # onto the commander's planet.  x, y = arrival point (portal cell * 32), last u8 = route distance.
        if mapid < 100000000:
            # planet of the map the hero is on (a visitor on another planet uses that planet's portals),
            # falling back to the nation's capital planet
            cur = getattr(s, "map", None)
            planet = ((cur if cur and cur < 100000000 else CAPITALS.get(cmd.get("nation"), 600000)) // 100000) % 1000
            mapid = planet * 100000 + mapid % 100000
            if province_of(mapid) not in planet_provinces(planet):
                log(f"   change-map request {body.hex()} -> map {mapid}: province {province_of(mapid)} does not exist "
                    f"on planet {planet}, staying at {getattr(s, 'map', None)}")
                back = getattr(s, "map", None) or CAPITALS.get(cmd["nation"])
                enter_field(s, back, x, y, capital=(back == CAPITALS.get(cmd["nation"])))
                return
        # only NEIGHBOURING provinces (portal_links.json = province graph of the patched portals.por, layout 2,
        # keyed by id % 100000): no capital <-> capital teleport, no jumping across the map.  Refused silently:
        # the hero is put back where he is.
        _cur = getattr(s, "map", None)
        if (_cur and _cur < 100000000 and (_cur // 10000) % 10 == 0 and mapid < 100000000 and (mapid // 10000) % 10 == 0
                and mapid != _cur and PORTAL_LINKS
                and mapid % 100000 not in PORTAL_LINKS.get(_cur % 100000, ())):
            log(f"   change-map request {body.hex()} -> {mapid} from {_cur}: not a neighbour, refused")
            enter_field(s, _cur, x, y, capital=(_cur in CAPITALS.values()))
            return
        # hunting grounds (CAVE 1-3 = province id + k*10000): only the province's own caves, and from a cave only
        # back to that province
        if (_cur and _cur < 100000000 and mapid < 100000000 and mapid != _cur
                and ((mapid // 10000) % 10 in (1, 2, 3) or (_cur // 10000) % 10 in (1, 2, 3))
                and (mapid % 10000 != _cur % 10000 or mapid // 100000 != _cur // 100000)):
            log(f"   change-map request {body.hex()} -> {mapid} from {_cur}: not this province's cave, refused")
            enter_field(s, _cur, x, y, capital=(_cur in CAPITALS.values()))
            return
        # DEMON STAR (claude/DEMON_STAR_PLANETS.md): only during the nation's window, and only into a province the
        # side holds or one next to it (the march goes corner -> centre)
        if is_star_province(mapid) and mapid != _cur:
            _why = star_access(s, (mapid // 100000) % 1000)
            if _why or not star_enter_ok(s, mapid):
                _why = _why or "On a demon star you can only attack a province next to one your side holds."
                s.send(chat_line(0x0A, _why, (255, 200, 60)))
                log(f"   change-map -> {mapid}: demon star refused ({_why})")
                if _cur and is_star_province(_cur) and not star_access(s, (_cur // 100000) % 1000):
                    enter_field(s, _cur, x, y)
                else:
                    enter_field(s, CAPITALS[cmd["nation"]], 0x200, 0x200, capital=True)
                return
        if is_sim_map(_cur) and mapid != _cur:
            # (19:59) a simulation map is closed: its field portals do not lead onto the real provinces
            s.send(chat_line(0x0A, "This is a battle simulation: leave it through your exit portal.", (255, 200, 80)))
            enter_field(s, _cur, x, y)
            return
        if mapid in BATTLES and BATTLES[mapid].get("owner") is not s and province_owner(mapid) != cmd.get("nation"):
            if BATTLE_CTRL_DIALOG and send_battle_control(s, mapid, x, y):
                return
            if JOIN_PERMISSION and request_join(s, mapid, x, y):
                return
        log(f"   change-map request {body.hex()} -> map {mapid} ({map_kind(mapid)}"
            f"{', owner %d' % province_owner(mapid) if mapid < 100000000 else ''}) at ({x},{y})")
        enter_field(s, mapid, x, y, capital=(mapid == CAPITALS.get(cmd["nation"])))
    else:
        _pkt_default(s, body, t)          # (no sub-case matched: like the old if-chain, the default)

def _pkt_2f(s, body, t):
    if t == 0x2f and len(body) >= 15:
        # exit portal reached in a battle map -> retreat (client FUN_004e1990)
        uid, _w, flag, target = struct.unpack_from(">IHIi", body, 1)
        dest = struct.unpack_from(">HH", body, 15) if len(body) >= 19 else None   # arrival x, y in the target map
        log(f"   0x2f raw {body.hex()}")       # (10-24) to tell the exit-portal and the after-death variants apart
        retreat(s, uid, target, dest, confirmed=GATE_CLIENT_CONFIRMS)   # the client asked the player already (004d17c0)
    else:
        _pkt_default(s, body, t)          # (no sub-case matched: like the old if-chain, the default)

def _pkt_33(s, body, t):
    if t == 0x33 and len(body) >= 6:
        # client walks into the Lab / item shop: u32 shop id, u8, u8.  Reply 0x33 (client 004a6290 -> opens
        # "IntegratedShop", data parsed by 00573820): u8 sub=0, u32 shop id, u16 n items {...}.  FIRST STEP: no items.
        # client requests (u32 shop, u8 op, ...): op 1 = enter, 6 = UNIT UPGRADE page, 7 [s8 unit name] = EQUIP ITEM
        # page for that unit.  Server 0x33 subs (client 00573820):
        #   0 = item list   u32 shop, u16 n {u8 0, u8, u8, u8, u8, s8 item name, 3 x u16, 5 x u32 price}
        #   2 = upgrade list u32 shop, u16 n {u8, u8, s8 unit, u8 m {u8, u8, s8 target, u8, 5 x u32 price, u8}}
        #   3 = equipped    u32 shop, s8, u16 n {u16, u8, 9 x u32}
        shop = struct.unpack_from(">I", body, 1)[0]
        op = body[5]
        if op == 1:
            s.lab_notices_seen = set()            # new Lab visit: upgrade notices may be shown again (once each)
            if send_unit_catalog(s):              # Lab chassis list = owned forms only (bought since the last visit)
                log(f"   lab: unit table re-sent, Lab list = {sorted(s.cat_owned or [])}")
        if op == 6:
            s.send(build_lab_upgrades(shop, getattr(s, "acc", None)))
            log(f"   lab: unit upgrade page -> 0x33 sub 2 (experimental) {build_lab_upgrades(shop, getattr(s, 'acc', None)).hex()[:120]}")
        elif op == 7 and len(body) >= 7:
            unit, _o = read_s8(body, 6)
            unit = UN.to_english(unit, s.lang, s.enc)
            _accs, _a = get_account(getattr(s, "acc", None))
            _cmd = PG.ensure_commander(_a.setdefault("commander", {}))
            _mine = [u for u in _a["units"] if DISPLAY.get(u["chassis"], u["chassis"]) == unit or u.get("label") == unit]
            s.lab_tl = max([PG.tech_level(_cmd, u) for u in _mine] or [1 + PG.attr(_cmd, 2) // 2])
            s.send(build_lab_item_sale(shop, unit, s.lab_tl, star=star_lab_key(s),
                                     hgear=hgear_open(s.cmd.get("nation", 1)) or star_lab_ok(s)))
            log(f"   lab: tech level limit {s.lab_tl} (unit level + Education // 2)")
            log(f"   lab: equip page for {unit!r} -> 0x33 sub 3 with {len(items_for_unit(unit))} items for its slots {[x[0] for x in UNIT_SLOTS.get(CODE_OF.get(unit, unit), [])]}")
        elif op == 3 and len(body) >= 12:
            # EQUIP DONE (CONFIRMED 2026-10-21, client 00530510): [u32 shop][03][u32 unit id]
            #   [u8 n1][n1 x u16 REMOVED (sold)][u8 n2][n2 x u16 lab list +0x106b0 (items placed from the
            #   inventory, already owned -> free)][u8 n3][n3 x u16 ADDED (bought)][s8 unit name][u8]
            # Before: n2 was read as a u16 -> "04 00 81 .." = 1024 items -> struct.error -> connection lost.
            uid = struct.unpack_from(">I", body, 6)[0]
            o = 10
            lists = []
            for _k in range(3):
                n = body[o] if o < len(body) else 0; o += 1
                n = max(0, min(n, (len(body) - o) // 2))
                lists.append(list(struct.unpack_from(">%dH" % n, body, o))); o += 2 * n
            # CONFIRMED 2026-10-21 21:43 (SELL engine + UNEQUIP two items + buy an engine -> [6177] [374, 641] [4148]):
            # list 1 = SOLD, list 2 = UNEQUIPPED into the hero's stock, list 3 = ADDED (bought, or taken back
            # from the stock - then free).  Before, list 2 was read as 'placed from the inventory' and re-added.
            sold, unequipped, added = lists
            log(f"   lab op 3 lists: sold {sold} unequipped {unequipped} added {added}")
            newname, _o = read_s8(body, o) if o < len(body) else ("", o)
            newname = PG.strip_star_tag(UN.to_english(newname, s.lang, s.enc))   # (10-31) the shown "*N " is not a name
            acc = getattr(s, "acc", None)
            accs, a = get_account(acc)
            unit = next((u for u in a["units"] if u["uid"] == uid), None)
            if unit is None:
                log(f"   EQUIP unit {uid}: not in roster")
                s.send(bytes([0x33, 1, LAB_FAIL]))
            else:
                old = list(unit.get("items", []))
                ids = list(old)
                stock = list(a.get("hero_items", []))
                refund = [0, 0, 0, 0, 0]
                for i in sold:                                   # sold to the shop: half the buy price back
                    if i in ids:
                        ids.remove(i)
                        for k, v in enumerate(item_sell_price(i)):
                            refund[k] += v
                for i in unequipped:                             # into the hero's stock
                    if i in ids:
                        ids.remove(i)
                        stock.append(i)
                bought = []
                for i in added:
                    if i in ORGAN_IDS or i == ALIEN_ENGINE_ID:   # (21:24) organs: fitted by the server, never bought
                        continue
                    if i in stock:                               # taken back from the stock: free
                        stock.remove(i)
                    else:
                        bought.append(i)
                    ids.append(i)
                # one item per slot: a newer item replaces the old one in the same slot (also repairs rosters that
                # piled up duplicates under the old parser)
                ids = dedupe_slots(ids)
                cost = [0, 0, 0, 0, 0]
                for i in bought:
                    for k, v in enumerate(item_price(i)):
                        cost[k] += v
                net = [c - r for c, r in zip(cost, refund)]       # the refund pays for the new items
                cost = [max(0, x) for x in net]
                _cmd3 = PG.ensure_commander(a.setdefault("commander", {}))
                _bad = (["op 3 list too long"] if any(len(l) > LAB_LIST_MAX for l in lists) else []) + \
                    lab_design_problems(unit, _cmd3, old, ids, bought,
                                        star=star_lab_key(s),
                                        hgear=hgear_open(_cmd3.get("nation", 1)) or star_lab_ok(s))
                if _bad and any("not on sale" in b for b in _bad) and any(h_item(ITEM_BY_ID.get(i, {})) for i in bought) \
                        and not hgear_open(_cmd3.get("nation", 1)) and not star_lab_ok(s):
                    _bad = ["H- equipment is only sold once your side has captured the centre province of the planet"] + _bad
                if _bad:
                    log(f"   ANTI-CHEAT: {acc} EQUIP unit {uid} refused: {'; '.join(_bad)} "
                        f"(sold {sold} unequipped {unequipped} added {added} raw {body.hex()})")
                    audit("lab_design_refused", acc, uid=uid, reasons=_bad, sold=sold, unequipped=unequipped, added=added)
                    s.send(bytes([0x33, 1, LAB_FAIL]))
                    lab_notice(s, "This design was refused by the server: " + _bad[0] + ".", a)
                demon_locked = (any(ITEM_BY_ID.get(i, {}).get("demon") for i in bought)
                                and not star_lab_ok(s)) \
                    or any(never_sold(ITEM_BY_ID.get(i, {})) for i in bought) \
                    or (any(redcoat_item(ITEM_BY_ID.get(i, {})) for i in bought) and not redcoat_event_active())
                if _bad:
                    pass
                elif demon_locked or not res_can_pay(a, cost):
                    log(f"   EQUIP unit {uid}: not enough resources for {cost}")
                    s.send(bytes([0x33, 1, LAB_FAIL]))
                    if demon_locked:
                        lab_notice(s, "Some of these items are not on sale right now.")
                    else:
                        _need = ", ".join(f"{n} {c} (you have {r})" for n, c, r in zip(("Money", "Ore", "Silicon", "Uranium", "Sulfur"), cost, a["resources"]) if r < c)
                        lab_notice(s, f"Not enough resources for this design (need {_need}).", a)
                else:
                    res_add(a, [-_v for _v in net])
                    ids = with_alien_engine(unit, ids)
                    unit["items"] = ids
                    a["hero_items"] = [i for i in stock if i not in ORGAN_IDS and i != ALIEN_ENGINE_ID][:HERO_STOCK_MAX]   # (21:24) organs never go to the stock
                    if newname:
                        # the client always sends the shown name: the chassis' default name is NOT a custom label
                        # (it stuck to the unit and an upgraded Red-Eye -> Orbus kept showing as "Red-Eye")
                        unit["label"] = None if is_default_name(newname) else newname
                    if acc in accs:
                        accs[acc] = a; save_accounts(accs)
                    if newname:        # rename: update the unit record (second name string = the label)
                        disp = DISPLAY.get(unit["chassis"], unit["chassis"])
                        s.send(build_units([(uid, disp, PG.star_tag(unit) + newname[:12], hp_frac(unit), unit.get("level", 1), unit.get("deploy", 0),
                                                 unit_battle_stats(unit)[0], PG.unit_xp_total(unit))], sub=4, mech=mech_for(s)))
                    s.send(build_set_inventory(uid, ids))
                    s.send(build_set_inventory(hero_uid(acc), a["hero_items"]))     # hero stock
                    send_unit_catalog(s)               # the new form must be in the Lab list before the refresh
                    s.send(bytes([0x33, 1, LAB_OK]))
                    send_resources(s, a)
                    if any(refund):
                        s.send(chat_line(0x0A, "Sold: + " + ", ".join(f"{n} {v}" for n, v in zip(("Money", "Ore", "Silicon", "Uranium", "Sulfur"), refund) if v)))
                    log(f"   EQUIP unit {uid}: items {ids} ({[ITEM_BY_ID.get(i, {}).get('name') for i in ids]}), "
                        f"cost {cost}, sold for {refund}, stock {a['hero_items']}, resources {a['resources']}")
        elif op == 4 and len(body) >= 7:
            # STOCK SALE (client 0052e760, never seen yet): [u32 shop][04][u8 n][n x u16][u8 m][m x u16][s8 name].
            # Assumed: list 1 = items sold from the hero's stock.  Only items really in the stock are refunded.
            o = 6
            lists = []
            for _k in range(2):
                n = body[o] if o < len(body) else 0; o += 1
                n = max(0, min(n, (len(body) - o) // 2))
                lists.append(list(struct.unpack_from(">%dH" % n, body, o))); o += 2 * n
            log(f"   lab op 4 (stock) lists: {lists[0]} / {lists[1]} raw {body.hex()}")
            accs, a = get_account(s.acc)
            stock = a.setdefault("hero_items", [])
            refund = [0, 0, 0, 0, 0]
            # CONFIRMED 2026-10-21 21:56: [u32 shop][04][u8 n][n x u16 SOLD from the stock][u8 m][..][s8 hero name][u8]
            missing = []
            for i in lists[0][:LAB_LIST_MAX * 4]:
                if i in stock:
                    stock.remove(i)
                    for k, v in enumerate(item_sell_price(i)):
                        refund[k] += v
                else:
                    missing.append(i)
            if missing:
                log(f"   ANTI-CHEAT: {s.acc} sold stock items he does not own: {missing}")
                audit("stock_sale_not_owned", s.acc, items=missing, raw=body.hex())
            if any(refund):
                res_add(a, refund)
                accs[s.acc] = a; save_accounts(accs)
                s.send(chat_line(0x0A, "Sold: + " + ", ".join(f"{n} {v}" for n, v in zip(("Money", "Ore", "Silicon", "Uranium", "Sulfur"), refund) if v)))
            s.send(build_set_inventory(hero_uid(s.acc), stock))
            s.send(bytes([0x33, 1, LAB_OK]))       # the client waits for it ("The server is verifying your design...")
            send_resources(s, a)
        elif op == 5 and len(body) >= 11:
            # COMPLETE UPGRADE (confirmed): [u32 shop][05][u32 unit id][s8 target][s8 target][u8]
            uid = struct.unpack_from(">I", body, 6)[0]
            target, _o = read_s8(body, 10)
            target = UN.to_english(target, s.lang, s.enc)
            acc = getattr(s, "acc", None)
            accs, a = get_account(acc)
            unit = next((u for u in a["units"] if u["uid"] == uid), None)
            cur = DISPLAY.get(unit["chassis"], unit["chassis"]) if unit else None
            opts = dict(UPGRADES.get(cur, []))
            _path = [target]
            if unit is not None and target not in opts:      # a deeper node of the tree: go there in several steps
                _path = upgrade_reach(cur).get(target) or []
                if _path:
                    opts[target] = max(chassis_influence(f) for f in _path)
            if unit is None or target not in opts:
                log(f"   UPGRADE unit {uid} ({cur}) -> {target!r}: not allowed (options {list(opts)})")
                s.send(bytes([0x33, 1, LAB_FAIL]))
            else:
                uq = 1 if LAB_TEST_MODE else opts[target]
                cost = (1, 0, 0, 0, 0) if LAB_TEST_MODE else upgrade_path_cost(cur, _path)
                my_uq = PG.unit_quality(PG.ensure_commander(a.setdefault("commander", {})), unit)
                if not LAB_TEST_MODE and my_uq < opts[target]:
                    log(f"   UPGRADE unit {uid} -> {target}: unit quality {my_uq} < required {opts[target]} "
                        f"(UQ = unit level + Clout // 2)")
                    s.send(bytes([0x33, 1, LAB_FAIL]))
                    lab_notice(s, f"Upgrade to {target} failed: Unit Quality {my_uq} is below the required {opts[target]}.")
                elif not res_can_pay(a, cost):
                    log(f"   UPGRADE unit {uid} -> {target}: not enough resources")
                    s.send(bytes([0x33, 1, LAB_FAIL]))
                    _need = ", ".join(f"{n} {c} (you have {r})" for n, c, r in zip(("Money", "Ore", "Silicon", "Uranium", "Sulfur"), cost, a["resources"]) if r < c)
                    lab_notice(s, f"Upgrade to {target} failed: not enough resources (need {_need}).", a)
                else:
                    res_add(a, [-_v for _v in cost])
                    unit["chassis"] = target          # stored by NAME (MK2 forms share the base art code)
                    # items whose slot the NEW chassis does not have (Red-Eye radar / sensors on an Orbus) made the
                    # unit invalid in the deploy window -> unequipped and refunded at the sell price (half)
                    _moved, _dropped, _added = fit_after_upgrade(unit, a, PG.ensure_commander(a.setdefault("commander", {})))
                    if _moved or _dropped or _added:
                        log(f"   UPGRADE unit {uid}: moved {_moved}, removed {_dropped} (refunded half), added stock {_added}")
                    # 14:18: remove + re-add with the SAME id still left it under the old chassis in the Lab tree
                    # (the tree keeps its per-chassis id lists; a known id is never moved).  The upgraded unit gets
                    # a NEW id: the old entry no longer resolves (004482a0 skips it) and the refresh files the new
                    # id under the new chassis.
                    if is_default_name(unit.get("label")):
                        unit["label"] = None             # default chassis name -> follows the new chassis
                    old_uid = uid
                    uid = new_unit_uid({**accs, acc: a})
                    a["next_uid"] = uid + 1
                    unit["uid"] = uid
                    if acc in accs:
                        accs[acc] = a; save_accounts(accs)
                    # 0x16 sub 4 = update one unit (same record as sub 2), then 0x33 sub 1 (result) and a
                    # refreshed upgrade page + commander (resources)
                    # Round 1 crashed after: 0x16 sub 4 + 0x33 01 00 + 0x15 + a re-sent upgrade list (0x33 sub 2).
                    # Most likely culprit: rebuilding the upgrade list while the UI still points at the upgraded
                    # Imp entry (which disappears from the list).  Now only the unit update + the result.
                    # 0x33 sub 1 [u8]: 0 = success (005d5d40(1): message + tree refresh), non-zero = failure.
                    # 2026-10-21 13:49: with sub 4 (update) the Lab tree kept the unit under its OLD chassis
                    # (the refresh 00449cc0 only adds units to categories, it never moves one out).  Remove the
                    # unit (sub 3) and add it again with the new chassis (sub 2), then the success result, whose
                    # handler 005d5d40 rebuilds the tree (00449cc0).
                    s.send(bytes([0x16, 3]) + struct.pack(">I", old_uid))
                    s.send(build_units([(uid, target, PG.star_tag(unit) + (unit.get("label") or target), hp_frac(unit), unit.get("level", 1), unit.get("deploy", 0),
                                             unit_battle_stats(unit)[0], PG.unit_xp_total(unit))], sub=2, mech=mech_for(s)))
                    s.send(build_set_inventory(uid, unit.get("items", [])))     # the new id's equipment
                    # (17:27, user: Triage -> Volte, the Volte was not in the Lab) the Lab tree only lists forms
                    # of the 0x44 FIRST list; a form the player did not own before must be added before the
                    # success result (005d5d40 rebuilds the tree) - the equip path did this, the upgrade did not.
                    send_unit_catalog(s)
                    s.send(bytes([0x33, 1, LAB_OK]))
                    send_resources(s, a)
                    # 2026-10-21 22:08: 5 Eagles upgraded to Condor lost their Genus Splash (Eagle weapon slot 4208,
                    # Condor 4216) and silently had NO weapon -> the client never sent attack orders for them.
                    # ONE message box per upgrade kind and Lab visit (22:42: 9 upgrades = 18 boxes was too many).
                    _nowpn = not any(ITEM_BY_ID.get(i, {}).get("type") == 4 for i in unit.get("items", []))
                    if _dropped or _nowpn:
                        _key = (cur, target, tuple(map(str, _dropped)), _nowpn)
                        _seen = s.__dict__.setdefault("lab_notices_seen", set())
                        if _key not in _seen:
                            _seen.add(_key)
                            _txt = f"{cur} -> {target}: "
                            if _dropped:
                                _txt += f"{', '.join(map(str, _dropped))} removed (no slot / too heavy), sold for half price. "
                            if _nowpn:
                                _txt += f"Upgraded {target}s have NO WEAPON - equip one in EQUIP ITEM."
                            lab_notice(s, _txt.strip())
                    log(f"   UPGRADE unit {old_uid} -> new id {uid}: {cur} -> {target}, cost {cost}, resources {a['resources']}")
        else:
            s.send(bytes([0x33, 0]) + struct.pack(">IH", shop, 0))
            log(f"   lab op {op} -> 0x33 empty item list")
    else:
        _pkt_default(s, body, t)          # (no sub-case matched: like the old if-chain, the default)

def _pkt_34(s, body, t):
    if t == 0x34 and len(body) >= 6:
        handle_exchange(s, body)
    else:
        _pkt_default(s, body, t)          # (no sub-case matched: like the old if-chain, the default)

def _pkt_36(s, body, t):
    if t == 0x36 and len(body) >= 7:
        fhq_request(s, body)
    else:
        _pkt_default(s, body, t)          # (no sub-case matched: like the old if-chain, the default)

def _pkt_37(s, body, t):
    if t == 0x37:
        # StarCenter / Faction Pledge Center (Portals.por type 10, client FUN_0049eaf0 / window 005aed30)
        starcenter_request(s, body)
    else:
        _pkt_default(s, body, t)          # (no sub-case matched: like the old if-chain, the default)

def _pkt_39(s, body, t):
    if t == 0x39 and len(body) >= 3 and body[1] == 0:
        # walking into the Dimensional Matrix (portal type 11 -> [39][00][01]) or the Observatory (type 12 ->
        # [39][00][00]): answer with the star-gate window, server 0x38 sub 0 (client 005b2b70 -> 005b2470).
        s.send(build_star_gate(s))
        log(f"   {'Dimensional Matrix' if body[2] else 'Observatory'} -> 0x38 sub 0 with {len(PLANETS)} planets")
        if ORBIT_PUSH > 0:                          # (2026-10-27 test, GM /orbitpush) resend so the planets move
            s.gate_push_id = getattr(s, "gate_push_id", 0) + 1
            s.gate_pushing = True
            spawn(orbit_push(s, s.gate_push_id))
    elif t == 0x39 and len(body) >= 4 and body[1] == 1:
        # TRAVEL button (client 005b0710): [39][01][u16 planet]
        planet = struct.unpack_from(">H", body, 2)[0]
        _r = star_gate_travel(s, planet)
        if _r:                            # demon-star travel done: nothing to answer (an empty packet confused the client)
            s.send(_r)
    else:
        _pkt_default(s, body, t)          # (no sub-case matched: like the old if-chain, the default)

def _pkt_3a(s, body, t):
    if t == 0x3a:
        # F8 / "Do you want to instantly transport back to your capital?" (client 004b3680 VK_F8 -> 004a5be0:
        # only outside battle and when not already at the capital; Yes -> 0049e110 sends 0x3a [u8 0]).
        # Also used by the "no Shop/Lab here, go back to your capital?" prompts (00576ab0 / 005769d0).
        go_home(s)
    else:
        _pkt_default(s, body, t)          # (no sub-case matched: like the old if-chain, the default)

def _pkt_3b_3c(s, body, t):
    if t in (0x3B, 0x3C):
        handle_directory(s, body)
    else:
        _pkt_default(s, body, t)          # (no sub-case matched: like the old if-chain, the default)

def _pkt_3f(s, body, t):
    if t == 0x3F:
        # (2026-10-25) not a market list: the strategic map's ASSEMBLE / AVOID orders (social.marker_edit)
        pkt = build_marker_list(s)
        log(f"   client requests strategic orders -> 0x3e with {struct.unpack_from('>H', pkt, 1)[0]} order(s)")
        s.send(pkt)
    else:
        _pkt_default(s, body, t)          # (no sub-case matched: like the old if-chain, the default)

def _pkt_40(s, body, t):
    if t == 0x40:
        marker_edit(s, body)
    else:
        _pkt_default(s, body, t)

def _pkt_56(s, body, t):
    if t == 0x56:
        force_open(s, body)
    else:
        _pkt_default(s, body, t)

def _pkt_42(s, body, t):
    if t == 0x42:
        # NewUser screen: start-planet list (client parser FUN_0055bea0): the Dimensional Matrix record (_planet_rec:
        # orbit ellipse A/B, phase, size - the old inline record had A = B = 0 = planets at infinity, so the PLANET
        # page showed nothing, 2026-10-22 18:32 screenshot) + u32 (class) + u8 n x u32 (none).
        # OPEN (u8) must be set on at least one planet, else the client shows the "planet full" dialog (005a43b0).
        if True:
            # only the planets a NEW commander may start on (OPEN) - today only 新手星.  With all three the 3D page
            # showed the Novice planet but its mouse-over said "Advanced" (18:49 screenshot); 进阶星 / 精英星 are
            # reached later through the Star Center and seen in the Dimensional Matrix.
            start = [p for p in PLANETS if p[3]]
            pl = bytes([len(start)]) + b"".join(_planet_rec(p[0], p[1], p[2], p[3], p[4], s=s) + struct.pack(">I", p[2]) + bytes([0])
                                                for p in start) + struct.pack(">H", BEGINNER_PLANET)
            log("   client requests start-planet list -> sending 0x40")
            s.send(bytes([0x40]) + pl)
    else:
        _pkt_default(s, body, t)          # (no sub-case matched: like the old if-chain, the default)

def _pkt_44(s, body, t):
    if t == 0x44 and len(body) >= 2:
        # Ctrl+F7 BATTLE PERMISSION window (client 005a68f0, sent whenever the window is toggled):
        # [u8 mode] 1 = allow all joiners, 2 = refuse all, 0 = manual (ask me)
        s.join_mode = body[1]
        log(f"   Ctrl+F7 battle permission mode = {body[1]} ({ {1: 'allow all', 2: 'refuse all', 0: 'manual'}.get(body[1], '?') })")
    else:
        _pkt_default(s, body, t)          # (no sub-case matched: like the old if-chain, the default)

def _pkt_46(s, body, t):
    if t == 0x46 and getattr(s, "logged_in", False):
        # CUnitInfoMan asks for the unit table (u16 cached version) -> class-A 0x44
        send_unit_catalog(s, force=True)
        log(f"   unit table request {body.hex()} -> 0x44 with {len(UNIT_CATALOG)} chassis (Lab list: {len(s.cat_owned or [])} owned forms)")
    else:
        _pkt_default(s, body, t)          # (no sub-case matched: like the old if-chain, the default)

def _pkt_47(s, body, t):
    if t == 0x47 and len(body) >= 3:
        # client 00547a60 (sent on Ctrl+F5 and again whenever the option struct is pushed in a battle):
        # [u8 option byte (struct+0xd of the options record, meaning unknown)][u8 TP: 1 = my units may be teleported /
        # loaded by allies].  Ctrl+F6 (TK) is toggled in a client-local flag (+0x459) that nothing else reads and sends
        # no packet of its own; if the option byte changes when you press Ctrl+F6 it is the TK flag (see /tk).
        s.allow_tp = bool(body[2])
        s.opt_byte = body[1]
        log(f"   option 0x47: opt byte {body[1]}, units transportable by allies (TP) = {body[2]}")
    else:
        _pkt_default(s, body, t)          # (no sub-case matched: like the old if-chain, the default)

def _pkt_48(s, body, t):
    if t == 0x48:
        log(f"   0x48 {body.hex()} (deploy troops ack)")
    else:
        _pkt_default(s, body, t)          # (no sub-case matched: like the old if-chain, the default)

def _pkt_4b(s, body, t):
    if t == 0x4B and len(body) >= 7:
        # Alt + click on the minimap (client 0049aa40 -> 0049e090): [u16 x][u16 y][u16 colour] map marker.
        # Relayed to the sender's side in the same battle as server 0x4B (client 004a19b0 -> 004a1960 draws it).
        # Original rule: only the battle commander / regiment leaders may mark -> here: the battle's commander or
        # anyone on his side when he is not on the map.
        b = getattr(s, "battle", None)
        if b:
            cmdr = b.get("owner")
            mine = side_nation(s)
            if cmdr is s or cmdr is None or cmdr.w.is_closing() or not same_side(side_nation(cmdr), mine) \
                    or getattr(s, "regiment_leader", False):
                for o in b["members"]:
                    if not o.w.is_closing() and same_side(side_nation(o), mine):
                        o.send(bytes([0x4B]) + body[1:7])
                log(f"   map marker by {s.acc}: {body[1:7].hex()}")
            else:
                log(f"   map marker by {s.acc} refused (not the battle commander)")
        else:
            # (user 2026-10-24 19:22: alone in an underground cave the minimap marker did not show) no battle record:
            # the marker goes back to the sender and to the players of his side on the same map
            mine = side_nation(s)
            for o in [s] + [p for p in map_peers(s) if same_side(side_nation(p), mine)]:
                if not o.w.is_closing():
                    o.send(bytes([0x4B]) + body[1:7])
            log(f"   map marker by {s.acc} (no battle record on map {getattr(s, 'map', None)}): {body[1:7].hex()}")
    else:
        _pkt_default(s, body, t)          # (no sub-case matched: like the old if-chain, the default)

def _pkt_53(s, body, t):
    if t == 0x53:
        log("   client 0x53: re-enter the battle with the current division")
        redeploy(s)
    else:
        _pkt_default(s, body, t)          # (no sub-case matched: like the old if-chain, the default)

def _pkt_54(s, body, t):
    if t == 0x54:
        s.redeploy_pending = False
        # Ctrl+F11 FORCED RETREAT (004a4f30): the whole division leaves the battle
        log("   FORCED RETREAT (Ctrl+F11)")
        if (getattr(s, "battle", None) and getattr(s, "redeploy_why", "") == "destroyed"
                and not getattr(s, "alive_units", None)):
            # every unit destroyed and the player gives up (RETREAT in the re-deploy box) -> DEFEAT result
            log("   whole division destroyed -> defeat")
            spawn(end_battle(s, getattr(s, "battle_gen", None), won=False))
        elif getattr(s, "battle", None) or getattr(s, "battle_province", None):
            retreat(s, getattr(s, "hero_uid", HERO_UID), *retreat_target(s), confirmed=True)
    else:
        _pkt_default(s, body, t)          # (no sub-case matched: like the old if-chain, the default)

def _pkt_55(s, body, t):
    if t == 0x55 and len(body) >= 2:
        handle_word_of_honor(s, body)
    else:
        _pkt_default(s, body, t)          # (no sub-case matched: like the old if-chain, the default)

def _pkt_57(s, body, t):
    if t == 0x57 and len(body) >= 2:
        handle_player_search(s, body)
    else:
        _pkt_default(s, body, t)          # (no sub-case matched: like the old if-chain, the default)

def _pkt_58(s, body, t):
    if t == 0x58:
        # keep-alive carrying a tick counter; the client is now on the field screen -> enter the capital once
        if getattr(s, "logged_in", False) and not getattr(s, "field_sent", False):
            s.field_sent = True
            # 0x43 (client 00567300): u16 n, n x (u32 planet id, u32 vinu.inf planet layout).  The client maps every
            # province id through this table (FUN_005dc190) before looking up its map / drawing the planet map; an
            # unknown planet maps to layout 0.  Identity mapping = each planet uses its own vinu.inf grid.
            s.send(build_universe_layout())
            log(f"   sent 0x66 universe layout table {LAYOUT}")
            s.send(bytes([0x43]) + struct.pack(">H", len(LAYOUT)) + b"".join(struct.pack(">II", p, l) for p, l in LAYOUT.items()))
            log(f"   sent 0x43 planet layout table {LAYOUT}")
            cmd = getattr(s, "cmd", {"nation": 1, "look": 1})
            enter_field(s, CAPITALS.get(cmd["nation"], 200000000), 0x200, 0x200, capital=True)
    else:
        _pkt_default(s, body, t)          # (no sub-case matched: like the old if-chain, the default)

def _pkt_5a(s, body, t):
    if t == 0x5a and len(body) >= 11:
        # client report: POC owner changed [u32 id][u8 nation][u32 map][u8 1] (004a41b0).  AUTHORITATIVE: the client
        # sends it when its own capture animation is complete (the server's countdown ran ahead of the animation,
        # 2026-10-20 17:23).  The POC loop then sees the new owner and declares the victory.
        pid, nat = struct.unpack_from(">IB", body, 1)
        p = getattr(s, "pocs", {}).get(pid)
        log(f"   client POC report: POC {pid} -> nation {nat} (server state: {p and p['owner']})")
        if p is not None and p["owner"] != nat:
            if nat == side_nation(s) & 0xFF:
                nat = side_nation(s)
            # ANTI-CHEAT (2026-10-21): the report is accepted only if the server's own model saw a unit of the
            # reporter's side standing on the POC for (almost) the whole capture time (strength / POC_RATE s; the
            # server starts counting when the move ORDER arrives, i.e. earlier than the client, so honest reports
            # always pass).  Otherwise the reporter gets the real POC state back (the 3x fallback still applies).
            need = p.get("strength", 0) / POC_RATE * POC_MIN_FRACTION
            have = time.time() - p["cap_t"] if p.get("capturing") and p.get("cap_t") else -1
            why = None
            if not same_side(nat, side_nation(s)):
                why = f"nation {nat} is not the reporter's side {side_nation(s)}"
            elif not same_side(p.get("cap_nat"), side_nation(s)) or have < need:
                why = f"server saw {have:.0f}s of capture by {p.get('cap_nat')}, needs {need:.0f}s"
            if why:
                log(f"   ANTI-CHEAT: POC {pid} report from {s.acc} refused: {why}")
                audit("poc_refused", s.acc, pid=pid, why=why, map=getattr(s, "map", None))
                send_poc_state(s, pid, p)
                return
            p["owner"], p["progress"], p["capturing"] = nat, 0, False
            for o in battle_members(s):
                if o is not s:
                    send_poc_state(o, pid, p)
            _ac, _a = get_account(s.acc)
            _st = _a.setdefault("commander", {}).setdefault("stats", {})
            _st["pocs"] = _st.get("pocs", 0) + 1
            check_medals(s, _a, _ac)
            _ac[s.acc] = _a
            save_accounts(_ac)
            log(f"   POC {pid}: CAPTURED by nation {nat} ({s.acc}, client report)")
            _bst = getattr(s, "battle_stats", None)
            if _bst is not None:
                _bst["pocs"] = _bst.get("pocs", 0) + 1
    else:
        _pkt_default(s, body, t)          # (no sub-case matched: like the old if-chain, the default)

def _pkt_5c(s, body, t):
    if t == 0x5C and len(body) >= 2:
        release_word(s, body)
    else:
        _pkt_default(s, body, t)          # (no sub-case matched: like the old if-chain, the default)

def _pkt_7b(s, body, t):
    if t == 0x7b:
        log(f"   0x7b {body.hex()} (sent together with map change; ignored)")
    else:
        _pkt_default(s, body, t)          # (no sub-case matched: like the old if-chain, the default)

def _pkt_80(s, body, t):
    if t == 0x80:
        # client lump: [0x80][flag][b2][u16 count]{u16 len, msg}*   (flag 1 = zlib of [b2][count][msgs])
        try:
            if body[1] == 0:
                cnt = struct.unpack(">H", body[3:5])[0]; off = 5; raw = body
            else:
                import zlib
                raw = zlib.decompress(body[4:]); cnt = struct.unpack(">H", raw[1:3])[0]; off = 3
            echo = []
            s.lump_exec_t = game_time(s) + RELAY_DELAY      # the tick at which the clients execute these orders
            for _ in range(cnt):
                ln = struct.unpack(">H", raw[off:off + 2])[0]; m = raw[off + 2:off + 2 + ln]; off += 2 + ln
                if LOG_COMBAT:
                    log(f"   lump msg type={m[0]:#04x} {m.hex()}")
                why = order_owner_refused(s, m)
                if why:
                    log(f"   ANTI-CHEAT: dropped lump from {s.acc}: {why} ({m.hex()})")
                    audit("order_refused", getattr(s, "acc", None), why=why, msg=m.hex(), map=getattr(s, "map", None))
                    continue
                why = ally_order_refused(s, m)
                if why:
                    log(f"   dropped ally order 0x{m[0]:02x}: {why}")
                    continue
                # Battle is LOCK-STEP: every client simulates the fight itself; the server only relays the orders
                # back (to everyone in the field) with a game time.  Client order -> server lump type (client
                # 004de840 / 004de930 / 004e1be0 send these and queue the same command locally):
                #   0x16 move [uid,x,y,p,flag]      -> 0x1a
                #   0x17 [uid][u8][u8]              -> 0x1b (command type 0)
                #   0x1e [uid]                      -> 0x23 ("Death" / stop, command type 5)
                #   0x29 [uid][u32 target]          -> 0x2b ("AttackObj", command type 1)
                #   0x30 [uid][u8 action]...        -> 0x30 ("Action", skills)
                RELAY = {0x16: 0x1A, 0x17: 0x1B, 0x1E: 0x23, 0x29: 0x2B, 0x30: 0x30}
                if len(m) >= 5 and m[0] in (0x16, 0x17, 0x1E, 0x29, 0x30, 0x18, 0x21) and hasattr(s, "targets"):
                    uid = struct.unpack_from(">I", m, 1)[0]
                    if m[0] == 0x18 and len(m) >= 9:          # periodic report: [u8][u32 uid][u16 x][u16 y]...
                        uid = struct.unpack_from(">I", m, 2)[0]
                        s.unit_pos[uid] = struct.unpack_from(">HH", m, 6)
                        try:
                            gate_assist(s, uid, s.unit_pos[uid])
                        except Exception as e:
                            log(f"   gate assist error: {e!r}")
                    elif m[0] == 0x16 and len(m) >= 9:
                        stop_attack(s, uid)
                        s.unit_pos[uid] = struct.unpack_from(">HH", m, 5)   # destination (approximation)
                        s.__dict__.setdefault("move_dest", {})[uid] = (s.unit_pos[uid], time.time())
                    elif m[0] == 0x29 and len(m) >= 9:
                        stop_attack(s, uid)
                        tid = struct.unpack_from(">I", m, 5)[0]
                        if tid in s.targets:
                            s.attacks[uid] = spawn(attack_loop(s, uid, tid))
                    elif m[0] == 0x21 and len(m) >= 8 and m[5] == 1:
                        # own unit HP report (client 004e1f60 kind 1, every ~5 s when it changed); kind 2 carries 5
                        # other values and is NOT the HP (it was read as the HP before 2026-10-28)
                        hp_note(s, uid, struct.unpack_from(">H", m, 6)[0])
                    elif m[0] == 0x17:
                        stop_attack(s, uid)
                    elif m[0] == 0x30 and len(m) >= 6:
                        on_skill(s, m)
                    elif m[0] == 0x1E:
                        if uid in s.targets:
                            if alien_died(s, uid) is False:
                                continue                   # (audit G) NPC death not believed: no 0x23 relay
                        elif uid in dead_aliens(s):
                            # (2026-10-24 11:16) the client keeps a dead unit it was never told to remove and re-reports
                            # it every 3 s: tell it once more to remove it (0x19), quietly
                            _ack = s.__dict__.setdefault("dead_acked", {})
                            if time.time() - _ack.get(uid, 0) > 10:
                                _ack[uid] = time.time()
                                s.send(bytes([0x19]) + struct.pack(">II", uid, 0))
                                log(f"   duplicate death report for {uid} from {s.acc} - told the client to remove it")
                            continue                       # another client reported it first: no second 0x23
                        else:
                            if uid in getattr(s, "alive_units", set()) and acid_bura_death(s, uid):
                                echo.append(bytes([0x30]) + struct.pack(">IB", uid, 25))   # burst BEFORE the 0x23
                            on_unit_lost(s, uid)
                if m[0] == 0x21:
                    continue                                       # HP report: not a command, no relay
                if m[0] == 0x16 and len(m) >= 12:
                    echo.append(bytes([0x1A]) + m[1:12])
                elif m[0] in RELAY and m[0] != 0x16:
                    echo.append(bytes([RELAY[m[0]]]) + m[1:])
            if echo:
                pk = bytes([0x80, 0, 0]) + struct.pack(">IH", s.lump_exec_t, len(echo))
                for m in echo:
                    pk += struct.pack(">H", len(m)) + m
                s.send(pk)
                # multiplayer: the same orders to everybody else on this map (battle = shared clock)
                for o in map_peers(s):
                    po = bytes([0x80, 0, 0]) + struct.pack(">IH", game_time(o) + RELAY_DELAY, len(echo))
                    for m in echo:
                        po += struct.pack(">H", len(m)) + m
                    o.send(po)
                if not getattr(s, "battle", None):
                    for m in echo:
                        if m[0] == 0x1A and len(m) >= 9 and struct.unpack_from(">I", m, 1)[0] == getattr(s, "hero_uid", -1):
                            s.hero_pos = struct.unpack_from(">HH", m, 5)
                if LOG_COMBAT:
                    log(f"   echoed {len(echo)} lump msg(s) back" + (f" (+{len(map_peers(s))} player(s))" if map_peers(s) else ""))
        except Exception as e:
            log(f"   lump parse error: {e!r}")
    else:
        _pkt_default(s, body, t)          # (no sub-case matched: like the old if-chain, the default)

def _pkt_d6(s, body, t):
    if t == 0xd6 and len(body) >= 2:
        accs, a = get_account(s.acc)
        c = a.setdefault("commander", {})
        c["mercenary"] = bool(body[1])
        accs[s.acc] = a
        save_accounts(accs)
        s.cmd["mercenary"] = c["mercenary"]
        log(f"   {s.acc} {'BECOMES a mercenary' if c['mercenary'] else 'retires from mercenary'}")
    else:
        _pkt_default(s, body, t)          # (no sub-case matched: like the old if-chain, the default)

def _pkt_f1_f2_f3_f4(s, body, t):
    if t in (0xF1, 0xF2, 0xF3, 0xF4):
        # SG_debug.exe (tools/patch_sg_debug.py) movement diagnostics
        try:
            if t == 0xF1:
                tg, st, fo, cm, nl, nf, fs_, ls_ = struct.unpack_from(">IIBIIIII", body, 1)
                log(f"   CLIENT DEBUG path search: target {tg} start {st} found={fo} ctx-map {cm} | planet portal list "
                    f"{nl} records, {nf} type-1 from start, sources {fs_}..{ls_}")
            elif t == 0xF2:
                ix, ty, so, tg, fl, cm = struct.unpack_from(">IIIIBI", body, 1)
                log(f"   CLIENT DEBUG on portal #{ix}: type {ty} {so} -> {tg} flag={fl} ctx-map {cm}")
            elif t == 0xF4:
                pid_, ty, prog, own, capf, non, ncap, first, stren, tx, ty_ = struct.unpack_from(">IIIIBIIIIII", body, 1)
                log(f"   CLIENT DEBUG POC {pid_} type {ty}: progress {prog}/{stren} owner {own} capturing={capf} "
                    f"on-POC {non} capturers {ncap} (first {first}) tile ({tx},{ty_})")
            else:
                ok, cm = struct.unpack_from(">BI", body, 1)
                log(f"   CLIENT DEBUG portal accepted, hero-has-units check={ok} ctx-map {cm}")
        except struct.error:
            log(f"   CLIENT DEBUG 0x{t:02x} (short) {body.hex()}")
    else:
        _pkt_default(s, body, t)          # (no sub-case matched: like the old if-chain, the default)

def _pkt_f5(s, body, t):
    if t == 0xF5 and len(body) >= 2:
        # SG_debug.exe F10: Ctrl+F6 TK toggle [u8 on] -> allies may / may not attack my units (ally_order_refused)
        s.allow_tk = bool(body[1])
        log(f"   Ctrl+F6 TK {'ON (allies may attack my units)' if body[1] else 'OFF'}")
    else:
        _pkt_default(s, body, t)          # (no sub-case matched: like the old if-chain, the default)

def _pkt_f6(s, body, t):
    if t == 0xF6 and len(body) >= 9:          # F16 code checksum (0xF5 is the F10 Ctrl+F6 TK toggle)
        client_hash_report(s, struct.unpack_from(">I", body, 1)[0], struct.unpack_from(">I", body, 5)[0])
        if len(body) >= 13:                     # F18: + u32 Windows ANSI code page (GetACP)
            set_client_acp(s, struct.unpack_from(">I", body, 9)[0])
    else:
        _pkt_default(s, body, t)          # (no sub-case matched: like the old if-chain, the default)

def _pkt_f9(s, body, t):
    if t == 0xF9 and len(body) >= 13:
        # F47 (2026-10-28): the client got a LATE command (its time L below the simulation tick) and rolled back -
        # the "teleport and snap back".  [u32 L][u32 tick][u32 w]; ticks = 1/100 s.
        L, tick, w = struct.unpack_from(">III", body, 1)
        late = max(0, tick - L) * 10
        st = s.__dict__.setdefault("late", {"n": 0, "max": 0, "sum": 0, "logged": 0.0, "rep_n": 0})
        st["n"] += 1; st["sum"] += late; st["max"] = max(st["max"], late)
        now = time.time()
        if now - st["logged"] >= 2.0:
            st["logged"] = now
            b = getattr(s, "battle", None)
            # srv = how long after its stamp L the SERVER got this report (~ one rtt when the command reached the client
            # in time and its clock was simply ahead; much more = the command / the client was held up)
            try:
                srv = (game_time(s) - L) * 10
            except Exception:
                srv = None
            log(f"   LATE command on {getattr(s, 'acc', '?')}'s client: {late} ms late (L {L}, tick {tick}, buffer w {w}, "
                f"report {srv} ms after L) - rollback #{st['n']}{' on ' + str(b.get('map')) if b else ''}")
    else:
        _pkt_default(s, body, t)

def _pkt_fa(s, body, t):
    if t == 0xFA and len(body) >= 9:
        # F47 v3 (2026-10-28): the client drew no frame for N ms during a battle (busy: sprite loading, a long
        # re-simulation ...) - commands that arrive meanwhile are handled late -> rollback.  [u32 ms][u32 tick]
        ms, tick = struct.unpack_from(">II", body, 1)
        st = s.__dict__.setdefault("freeze", {"n": 0, "max": 0, "rep_n": 0})
        st["n"] += 1; st["max"] = max(st["max"], ms)
        b = getattr(s, "battle", None)
        log(f"   CLIENT FREEZE on {getattr(s, 'acc', '?')}'s client: no frame for {ms} ms (tick {tick})"
            f"{' on ' + str(b.get('map')) if b else ''}")
    else:
        _pkt_default(s, body, t)

def _pkt_f8(s, body, t):
    if t == 0xF8 and len(body) >= 9:          # F34 answer to the code challenge 0xF7: [u32 nonce][u32 answer]
        challenge_reply(s, struct.unpack_from(">I", body, 1)[0], struct.unpack_from(">I", body, 5)[0])
    else:
        _pkt_default(s, body, t)

def _pkt_fc(s, body, t):
    if t == 0xFC:
        # TAB = battle score table (client 0049e560 sends 0xFC [], answer parsed by 004b4720):
        # u8 A, u8 B, u8 n {s8 name, u8, u16, u16, u8, u8, u8}.  Field meanings PROVISIONAL (see SCORE_FIELDS).
        s.send(build_score_table(s))
    else:
        _pkt_default(s, body, t)          # (no sub-case matched: like the old if-chain, the default)

PACKET_HANDLERS = {
    0x00: _pkt_00,
    0x02: _pkt_02,
    0x03: _pkt_03,
    0x04: _pkt_04,
    0x07: _pkt_07,
    0x0a: _pkt_0a,
    0x0b: _pkt_0b,
    0x0e: _pkt_0e,
    0x0f: _pkt_0f,
    0x12: _pkt_12,
    0x19: _pkt_19,
    0x1b: _pkt_1b,
    0x1d: _pkt_1d,
    0x1f: _pkt_1f,
    0x20: _pkt_20,
    0x23: _pkt_23,
    0x25: _pkt_25,
    0x2a: _pkt_2a,
    0x2b: _pkt_2b,
    0x32: _pkt_32,
    0x2c: _pkt_2c,
    0x2d: _pkt_2d,
    0x2e: _pkt_2e,
    0x2f: _pkt_2f,
    0x33: _pkt_33,
    0x34: _pkt_34,
    0x36: _pkt_36,
    0x37: _pkt_37,
    0x39: _pkt_39,
    0x3a: _pkt_3a,
    0x3b: _pkt_3b_3c,
    0x3c: _pkt_3b_3c,
    0x3f: _pkt_3f,
    0x40: _pkt_40,
    0x42: _pkt_42,
    0x44: _pkt_44,
    0x46: _pkt_46,
    0x47: _pkt_47,
    0x48: _pkt_48,
    0x4b: _pkt_4b,
    0x53: _pkt_53,
    0x54: _pkt_54,
    0x55: _pkt_55,
    0x56: _pkt_56,
    0x57: _pkt_57,
    0x58: _pkt_58,
    0x5a: _pkt_5a,
    0x5c: _pkt_5c,
    0x7b: _pkt_7b,
    0x80: _pkt_80,
    0xd6: _pkt_d6,
    0xf1: _pkt_f1_f2_f3_f4,
    0xf2: _pkt_f1_f2_f3_f4,
    0xf3: _pkt_f1_f2_f3_f4,
    0xf4: _pkt_f1_f2_f3_f4,
    0xf5: _pkt_f5,
    0xf6: _pkt_f6,
    0xf8: _pkt_f8,
    0xf9: _pkt_f9,
    0xfa: _pkt_fa,
    0xfc: _pkt_fc,
}

    # TODO: login (type 3 / 0xD4), ...
