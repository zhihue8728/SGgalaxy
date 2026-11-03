# sgserver part "gm_starcenter": tutorial, GM commands, star center, reincarnation, TP/TK.
# Loaded by sgserver.py into ONE shared namespace (exec, in the order of PARTS) - not an importable module;
# every name here is a sgserver global.  Checks: python tools/check_server.py
# ---- TUTORIAL ONLY ON THE FIRST LOGIN (user 2026-10-22 15:30) -----------------------------------------------------------
# The interactive tutorial (CInteractiveHelpMan) is client-only and reports nothing (its 'done' set filled by 0x7d is never
# read).  Its opening step is type 1, which the client skips when the commander's WIN count (0x15 -> +0x474, 0051d2fe) is
# not 0.  So: the first login of a commander gets his real 0 -> tutorial; every later login a win count of at least 1.
TUTORIAL_FIRST = set()      # accounts in their first session (tutorial may run until they log out)

def tutorial_login(acc, accs, a):
    if a.get("tutorial_seen"):
        TUTORIAL_FIRST.discard(acc)
        return
    a["tutorial_seen"] = time.time()
    TUTORIAL_FIRST.add(acc)
    accs[acc] = a
    save_accounts(accs)

def wins_for_client(name):
    a = load_accounts().get(name) or {}
    w = int((a.get("commander") or {}).get("wins", 0) or 0)
    if w == 0 and a.get("tutorial_seen") and name not in TUTORIAL_FIRST:
        w = 1                                   # hides the tutorial (only the client's gate reads it)
    return min(w, 65535)

def help_command(s, text):
    parts = text.split()
    topic = parts[1].lower() if len(parts) > 1 else ""
    # (user 2026-10-25 20:49: /help came out in English) the help is written per language (HELP_TEXT, social.py)
    lang = _mail_lang(s)
    texts = _help_text()
    book = texts.get(lang) or texts["en"]
    lines = book.get(topic) or book[""]
    for l in lines:
        s.send(chat_line(3, l, (120, 220, 255), tr=False))     # chat window: several lines (0x0A = one-line box)

def gm_command(s, text):
    """/points N  /res N  /level BRANCH N  /unitlevel N  /help  -- results go to the server log; the client is
    refreshed with 0x15 (resources, attributes) and 0x27 (F4 window)."""
    parts = text.split()
    accs, a = get_account(getattr(s, "acc", None))
    cmd = PG.ensure_commander(a.setdefault("commander", {}))
    try:
        if parts[0] == "/i18nmiss":
            # (2026-10-27) system lines that reached a Chinese client in English since the start (logs/i18n_missing.log)
            items = sorted(I18N.MISSING.items(), key=lambda kv: -kv[1])
            s.send(chat_line(0x0A, f"i18n missing: {len(items)} line(s) (logs/i18n_missing.log)", (120, 255, 120), tr=False))
            for t, n in items[:12]:
                s.send(chat_line(3, f"{n}x {t[:180]}", (200, 220, 255), tr=False))
            return
        if parts[0] == "/spawn":
            # /spawn CODE [LEVEL] [N]: put N passive aliens with art code CODE (e.g. g026, a018) near your units in
            # the current battle - to identify the unnamed unit art of tc/tc2.dat (claude/ALIEN_PLAN.md section 9)
            code = parts[1].lower(); lv = int(parts[2]) if len(parts) > 2 else 10; n = int(parts[3]) if len(parts) > 3 else 1
            if not getattr(s, "battle", None):
                s.send(chat_line(0x0A, "/spawn works inside a battle.", (255, 120, 120))); return
            members = battle_members(s)
            x0, y0 = next(iter(s.unit_pos.values()), (0x400, 0x400))
            for k in range(n):
                tid = next_alien_id(s)
                _t, akind, anum = unit_kind(code)
                hp, st9, spd = AL.stats("Ubik", lv)
                x, y = x0 + 0x60 + 0x40 * k, y0 - 0x60
                s.targets[tid] = {"hp": hp, "max": hp, "x": x, "y": y, "armor": st9[0], "arow": st9[1], "level": lv, "aggressive": False,
                                  "target": None, "name": code,
                                  "put": {"name": f"{code} L{lv}", "owner": alien_owner(s), "kind": akind, "num": anum,
                                          "nation": ALIEN_NATION, "st9": st9, "sight": unit_sight(st9), "spd": spd, "abil": 0}}
                body = put_server_unit(tid, f"{code} L{lv}", alien_owner(s), x, y, akind, anum, ALIEN_NATION, hp=hp,
                                      energy=1000, stats9=st9, sight=unit_sight(st9), speed=spd, abilities=0)
                s.targets[tid]["enter_t"] = delayed_put(s, body, still=lambda _t=tid: _t in s.targets)
            log(f"   GM spawn {n} x {code} L{lv}")
            return
        elif parts[0] in ("/amove", "/aatk"):
            # walking-animation test (user 2026-10-22 23:51 "aliens float, no walk animation"): /amove = every alien of
            # this battle gets a plain MOVE order (lump 0x1A, like a player's right click) to your first unit,
            # /aatk = an ATTACK order (lump 0x2B, what the alien AI sends when it engages).  Compare the two.
            if not getattr(s, "battle", None) or not getattr(s, "targets", None):
                s.send(chat_line(0x0A, "/amove /aatk: needs a battle with aliens.", (255, 120, 120))); return
            me = next(iter(getattr(s, "alive_units", set()) or s.unit_pos), None)
            px, py = s.unit_pos.get(me, (0x400, 0x400))
            msgs = []
            for tid in list(s.targets):
                msgs.append(_alien_order_move(tid, px, py) if parts[0] == "/amove" else attack_lump(tid, me))   # raw on purpose (A/B test)
            send_lumps(s, msgs)
            s.send(chat_line(0x0A, f"{parts[0]}: {len(msgs)} aliens -> unit {me} at ({px},{py})", (120, 255, 120)))
            log(f"   GM {parts[0]}: {len(msgs)} aliens -> {me} ({px},{py})")
            return
        elif parts[0] == "/npc":
            npc_gm(s, parts)
            return
        elif parts[0] == "/mapopt":
            # /mapopt tally|text|numbers 0|1 : switch the new strategic-map data on / off (crash hunt 2026-10-22 16:04)
            global MAP_TALLY, PROVINCE_TEXT, MAP_NUMBERS
            if len(parts) >= 3 and parts[1] == "war":
                global MAP_WAR_TALLY
                MAP_WAR_TALLY = parts[2] not in ("0", "off")
                s.send(chat_line(0x0A, f"mapopt: war tally (0x2c sub 1) = {int(MAP_WAR_TALLY)}", (120, 255, 120), tr=False))
                return
            if len(parts) >= 3 and parts[1] == "battle":
                global BATTLE_INFO_TEXT                 # (18:44) BATTLE tab text like the original server
                BATTLE_INFO_TEXT = parts[2] not in ("0", "off")
                s.send(chat_line(0x0A, f"mapopt: battle info text = {int(BATTLE_INFO_TEXT)}", (120, 255, 120), tr=False))
                return
            if len(parts) >= 3 and parts[1] in ("tally", "text", "numbers"):
                v = parts[2] not in ("0", "off")
                if parts[1] == "tally": MAP_TALLY = v
                elif parts[1] == "text": PROVINCE_TEXT = v
                else: MAP_NUMBERS = v
            s.send(chat_line(0x0A, f"mapopt: tally={int(MAP_TALLY)} text={int(PROVINCE_TEXT)} numbers={int(MAP_NUMBERS)}",
                             (120, 255, 120), tr=False))
            return
        elif parts[0] == "/shutdown":
            # /shutdown MIN [reason] : announce, save, restart (systemd starts it again) ; /shutdown cancel
            if len(parts) > 1 and parts[1] == "cancel":
                ok = restart_cancel()
                s.send(chat_line(0x0A, "restart cancelled" if ok else "no restart pending", (120, 255, 120), tr=False))
                return
            mins = float(parts[1]) if len(parts) > 1 else 5
            restart_countdown(int(mins * 60), " ".join(parts[2:]))
            return
        elif parts[0] == "/worldreset":
            # /worldreset CONFIRM : the ONLY way to put the map back to its initial state (user 2026-10-22 19:18):
            # every province except the capitals neutral again, full alien garrisons, holding times / raids cleared.
            # A backup of game.db is made first.  Deploys and restarts never touch the map.
            if len(parts) < 2 or parts[1] != "CONFIRM":
                s.send(chat_line(0x0A, "Map reset: type /worldreset CONFIRM (backup first; all provinces neutral).", (255, 160, 80), tr=False))
                return
            make_backup("worldreset")
            w = world_state(); caps = set(CAPITALS.values()); n_ = 0
            for k in list(w["owners"]):
                if int(k) not in caps and int(w["owners"][k]):
                    set_province_owner(int(k), 0); n_ += 1
            w["garrison"] = {}; w["since"] = {}
            RAIDS.clear()
            try:
                npc_state()["protect"].clear(); npc_dirty()
            except Exception:
                pass
            save_world(w)
            log(f"   GM {s.acc}: WORLD RESET ({n_} provinces back to the aliens)")
            audit("world_reset", s.acc, provinces=n_)
            s.send(chat_line(0x0A, f"Map reset done: {n_} provinces back to the aliens (backup made).", (120, 255, 120), tr=False))
            return
        elif parts[0] == "/ownerlog":
            # /ownerlog [N]: the last N province ownership changes (game.db), newest first
            lg = (STORE.kv_get(db(), "owner_log") or [])[-int(parts[1]) if len(parts) > 1 else -10:]
            for ts, pid_, old_, new_, why_ in reversed(lg):
                s.send(chat_line(3, f"{time.strftime('%m-%d %H:%M', time.gmtime(ts + 8 * 3600))} {province_label(pid_)} "
                                    f"{nation_name(old_, _mail_lang(s))} -> {nation_name(new_, _mail_lang(s))} ({why_})",
                                 (200, 220, 255), tr=False))
            if not lg:
                s.send(chat_line(3, "no ownership changes recorded yet", (200, 220, 255), tr=False))
            return
        elif parts[0] == "/traffic":
            for ln in traffic_report(12):
                s.send(chat_line(0x0A, ln, (120, 255, 120), tr=False))
            return
        elif parts[0] == "/lag":
            global LOG_PACKETS, LOG_COMBAT, FRAME_LEAD, RELAY_DELAY, JB_AUTO
            if len(parts) > 1 and parts[1] == "pkt":
                LOG_PACKETS = not LOG_PACKETS
            if len(parts) > 1 and parts[1] == "combat":            # every hit / relayed lump in the log (debugging)
                LOG_COMBAT = not LOG_COMBAT
            if len(parts) > 1 and parts[1] == "reset":
                LAG_STATS.update(max=0.0, n=0)
            if len(parts) > 2 and parts[1] == "adapt":
                global FRAME_ADAPT
                FRAME_ADAPT = parts[2] == "on"
            if len(parts) > 2 and parts[1] == "orders":             # /lag orders 40 (0 = gate off): AI orders / battle / s
                global ORDER_BUDGET, ORDER_GATE
                ORDER_GATE = int(parts[2]) > 0
                ORDER_BUDGET = max(1, min(500, int(parts[2]))) if ORDER_GATE else ORDER_BUDGET
                log(f"   GM {s.acc}: order gate {'on, ' + str(ORDER_BUDGET) + '/s' if ORDER_GATE else 'off'}")
                s.send(chat_line(0x0A, f"AI order gate: {str(ORDER_BUDGET) + ' orders / battle / s' if ORDER_GATE else 'off'}",
                                 (120, 255, 120)))
                return
            if len(parts) > 2 and parts[1] == "auto":               # /lag auto on|off: adaptive jitter buffer (core_net jb_*)
                global JB_AUTO
                JB_AUTO = parts[2] == "on"
            if len(parts) > 2 and parts[1] == "leadmax":            # /lag leadmax 15: cap of the adaptive lead (ticks)
                global JB_LEAD_MAX
                JB_LEAD_MAX = max(JB_LEAD_MIN, min(30, int(parts[2])))
            if len(parts) > 2 and parts[1] in ("lead", "delay"):    # manual values switch the adaptive buffer off
                JB_AUTO = False
            if len(parts) > 2 and parts[1] == "lead":               # /lag lead 2: frames stamped N ticks ahead (< delay)
                FRAME_LEAD = max(0, min(RELAY_DELAY - 1, int(parts[2])))
                s.send(chat_line(0x0A, f"frame lead {FRAME_LEAD} ticks (order delay {RELAY_DELAY})", (120, 255, 120)))
            if len(parts) > 2 and parts[1] == "delay":              # /lag delay 3: lock-step order delay in ticks (A/B test)
                RELAY_DELAY = max(1, min(40, int(parts[2])))
                FRAME_LEAD = min(FRAME_LEAD, RELAY_DELAY - 1)
                log(f"   GM {s.acc}: RELAY_DELAY -> {RELAY_DELAY} ticks")
                s.send(chat_line(0x0A, f"order delay {RELAY_DELAY} ticks = {RELAY_DELAY * 10} ms (default 4)", (120, 255, 120)))
                return
            if len(parts) > 2 and parts[1] == "frames":             # /lag frames off|on: A/B test (claude/CLIENT_CLOCK.md s.10)
                s.__dict__["no_frames"] = parts[2] == "off"       # only YOUR session: do units still move without frames?
                log(f"   GM {s.acc}: empty battle frames {'OFF' if s.no_frames else 'on'} for this session")
                s.send(chat_line(0x0A, f"empty battle frames {'OFF' if s.no_frames else 'on'} (your session only)", (120, 255, 120)))
                return
            if len(parts) > 2 and parts[1] == "frame":              # /lag frame 100: fixed frame interval in ms (turns adaptive off) - A/B test
                global FRAME_MS
                FRAME_MS, FRAME_ADAPT = max(20, min(200, int(parts[2]))), False
            if len(parts) > 1 and parts[1] in ("auto", "leadmax"):
                s.send(chat_line(0x0A, f"jitter buffer {'AUTO' if JB_AUTO else 'manual'}: lead {FRAME_LEAD} ticks "
                                       f"(max {JB_LEAD_MAX}, wanted {JB_STATE['want']} by {JB_STATE['who']}), "
                                       f"order delay {RELAY_DELAY}", (120, 255, 120)))
                return
            if len(parts) > 1 and parts[1] in ("net", "adapt", "frame"):
                for o in list(ONLINE):
                    if not getattr(o, "logged_in", False):
                        continue
                    st = tcp_stats(o)
                    s.send(chat_line(0x0A, f"{getattr(o, 'acc', '?')}: " + (
                        f"rtt {st['rtt']:.0f}+-{st['var']:.0f} ms, retransmits {st['total_retrans']}, unacked {st['unacked']}, "
                        f"queued {st['queued']} B, frame {(getattr(o, 'fa', None) or {}).get('ms', FRAME_MS)} ms, "
                        f"loss {(o.__dict__.get('jb') or {}).get('loss', 0) * 100:.1f}%, spurious {st.get('dsack', 0)}"
                        if st else "no TCP_INFO (not Linux)"), (120, 255, 120)))
                s.send(chat_line(0x0A, f"frame {FRAME_MS} ms (adaptive {'ON' if FRAME_ADAPT else 'off'} {FRAME_MIN}-{FRAME_MAX}), gc pauses>30ms {NET_STATS['gc_n']} (max {NET_STATS['gc_max'] * 1000:.0f} ms)",
                                 (120, 255, 120)))
                return
            s.send(chat_line(0x0A, f"lag: max {LAG_STATS['max'] * 1000:.0f} ms, stalls>{LAG_WARN * 1000:.0f}ms: {LAG_STATS['n']}, "
                                   f"last {LAG_STATS['last'] * 1000:.0f} ms; packet log {'ON' if LOG_PACKETS else 'off'}; "
                                   f"combat log {'ON' if LOG_COMBAT else 'off'}; "
                                   f"order delay {RELAY_DELAY * 10} ms, lead {FRAME_LEAD * 10} ms "
                                   f"({'auto' if JB_AUTO else 'manual'}); "
                                   f"online {len(ONLINE)}; accounts {len(load_accounts())}", (120, 255, 120)))
            return
        elif parts[0] == "/raidnow":
            # /raidnow: run the alien raid check now (every planet gets a raid if it has a candidate province)
            raid_cycle.next_check = 0
            _old = AL.RAID_CHANCE; AL.RAID_CHANCE = 1.0
            asyncio.get_event_loop().call_later(40, lambda: setattr(AL, "RAID_CHANCE", _old))
            s.send(chat_line(0x0A, "Raid check in <= 30 s.", (200, 200, 255))); return
        elif parts[0] == "/garrison":
            # /garrison [PID] [VALUE]: show / set the alien garrison of a neutral province (default: current map)
            pid = int(parts[1]) if len(parts) > 1 else getattr(s, "map", 0)
            global WORLD
            if WORLD is None:
                WORLD = load_world()
            if len(parts) > 2:
                AL.set_garrison(WORLD, pid, float(parts[2])); save_world(WORLD)
            s.send(chat_line(0x0A, f"garrison {pid}: {AL.garrison(WORLD, pid):.0f}%", (200, 200, 255))); return
        elif parts[0] == "/points":
            cmd["points"] = cmd.get("points", 0) + int(parts[1])
        elif parts[0] == "/res":
            n = int(parts[1]); res_add(a, [n] * 5)
        elif parts[0] == "/dmgtest":                   # /dmgtest CODE | off : damage code for the next battle
            global DMG_TEST_CODE
            DMG_TEST_CODE = None if parts[1] == "off" else int(parts[1])
            log(f"   GM damage-code test = {DMG_TEST_CODE} (player units of the next battle)")
        elif parts[0] == "/dmgtypes":                  # /dmgtypes on|off : armour classes + damage codes
            global DAMAGE_TYPES
            DAMAGE_TYPES = parts[1] == "on"
            log(f"   GM damage types = {DAMAGE_TYPES}")
        elif parts[0] == "/event" and len(parts) >= 3 and parts[1] == "redcoat":   # /event redcoat on|off|auto
            global REDCOAT_EVENT
            REDCOAT_EVENT = {"on": True, "off": False}.get(parts[2])
            log(f"   GM Redcoat event = {REDCOAT_EVENT} (active now: {redcoat_event_active()})")
        elif parts[0] == "/money":                     # /money N : money only
            res_add(a, (int(parts[1]),))
        elif parts[0] == "/level":
            br, n = parts[1].lower(), int(parts[2])
            cmd["branches"][br]["level"] = max(1, n); cmd["branches"][br]["xp"] = 0
        elif parts[0] == "/theme":
            global THEME_OVERRIDE
            THEME_OVERRIDE = None if parts[1] == "off" else int(parts[1])
            cur = getattr(s, "map", None)
            log(f"   GM theme override = {THEME_OVERRIDE}, re-entering map {cur}")
            if cur:
                enter_field(s, cur, 0x200, 0x200, capital=(cur == CAPITALS.get(cmd.get("nation"))))
            return
        elif parts[0] == "/tk":
            # /tk [on|off]: my units targetable by allies (test; the real Ctrl+F6 toggle sends no packet)
            s.allow_tk = (len(parts) < 2 or parts[1].lower() != "off")
            log(f"   GM tk = {s.allow_tk}")
        elif parts[0] == "/ura":
            a["resources"][3] = int(parts[1]) if len(parts) > 1 else a["resources"][3]
            a.pop("ura_daily_at", None); a.pop("ura_full_claim", None)
            s.send(chat_line(0x0A, f"Uranium {a['resources'][3]} (daily/full claims reset)", (120, 220, 255)))
        elif parts[0] == "/power":
            nid_ = cmd.get("nation", 1)
            if len(parts) > 1:
                add_nation_power(nid_, int(parts[1]))
            left = star_time_left(nid_)
            s.send(chat_line(0x0A, f"National power {nation_power(nid_)}/{POWER_FULL}; demon-star time left "
                                   f"{left // 3600}h{left % 3600 // 60:02d}m; star gate "
                                   f"{'OPEN' if star_open(nid_) else 'closed'} (opens 12:00 and 19:00 for 1 h)", (120, 220, 255)))
        elif parts[0] == "/powerall":
            # (2026-10-27) every nation: power, fields, field value, demon-star time, + settlement times (Cang Hai check)
            for nid_, nm_, _c in NATIONS:
                n_, v_ = nation_fields(nid_)
                left = star_time_left(nid_)
                full_at = world_state().get("power_full_at", {}).get(str(nid_))
                line = (f"{nation_name(nid_, getattr(s, 'lang', 'en'))} ({nid_}): power {nation_power(nid_)}/{POWER_FULL}, "
                        f"{n_} fields value {v_} (+{v_ * POWER_PER_FIELD_VALUE}/settlement), star {left // 3600}h"
                        f"{left % 3600 // 60:02d}m"
                        f"{(' (' + DEMON_STARS[nation_star(nid_)][1] + ')') if nation_star(nid_) is not None else ''}, last full "
                        f"{time.strftime('%m-%d %H:%M', time.localtime(full_at)) if full_at else '-'}")
                s.send(chat_line(0x0A, line, (120, 220, 255), tr=False))
                log("   /powerall " + line)
            s.send(chat_line(0x0A, f"next settlement {time.strftime('%m-%d %H:%M', time.localtime(next_settlement()))}",
                             (120, 220, 255), tr=False))
        elif parts[0] == "/home":
            go_home(s, free_pass=True)
            return
        elif parts[0] == "/own":
            # /own COL ROW [NATION] | /own PROVINCE_ID [NATION] | /own around: give the hero's nation a province (or all
            # neighbours of its capital) -- test aid for the strategic-map "You cannot reach this province!" problem.
            nid_ = cmd.get("nation", 1)
            cur = getattr(s, "map", None) or CAPITALS.get(nid_, 600000)
            planet = (cur // 100000) % 1000 if cur < 100000000 else (CAPITALS.get(nid_, 600000) // 100000) % 1000
            if parts[1] == "around":
                cap = CAPITALS.get(nid_)
                col, row = (cap % 100000) // 100, cap % 100
                near = [planet * 100000 + c * 100 + r for c in range(col - 1, col + 2) for r in range(row - 1, row + 2)]
                targets = [p_ for p_ in near if p_ in planet_provinces(planet) and p_ != cap]
            elif len(parts) >= 3 and int(parts[2]) < 10:
                targets = [planet * 100000 + int(parts[1]) * 100 + int(parts[2])]
                nid_ = int(parts[3]) if len(parts) > 3 else nid_
            else:
                targets = [planet * 100000 + int(parts[1]) % 100000]
                nid_ = int(parts[2]) if len(parts) > 2 else nid_
            for p_ in targets:
                set_province_owner(p_, nid_)
            log(f"   GM own {targets} -> nation {nid_}")
            s.send(chat_line(0x0A, f"Province(s) {targets} now belong to nation {nid_}; reopen the strategic map.", (120, 220, 255)))
            return
        elif parts[0] == "/orbitpush":
            # /orbitpush SECONDS: resend the Dimensional Matrix every SECONDS while it is open (fast demo orbits); 0 = off
            global ORBIT_PUSH, ORBIT_DEMO_EARTH_SECONDS
            # /orbitpush SECONDS [EARTH_ORBIT_SECONDS]  (11:58 user: it moves but not smoothly -> smaller, more frequent
            # steps: e.g. /orbitpush 0.2 120 = 5 updates a second, Earth 0.6 degrees per update)
            ORBIT_PUSH = float(parts[1]) if len(parts) > 1 else 0.0
            ORBIT_DEMO_EARTH_SECONDS = (float(parts[2]) if len(parts) > 2 else 120.0) if ORBIT_PUSH > 0 else 0
            s.send(chat_line(0x0A, f"orbit push every {ORBIT_PUSH}s (Earth orbit {ORBIT_DEMO_EARTH_SECONDS:.0f} s); "
                                   f"open the Dimensional Matrix", (120, 220, 255), tr=False))
            return
        elif parts[0] == "/orbit16":
            # (2026-10-27) /orbit16 N: put N (Kepler-scaled) into the unknown u16 of the planet records, then open the
            # Dimensional Matrix again to see whether the client turns the planets itself.  /orbit16 0 = off.
            global ORBIT_U16
            ORBIT_U16 = int(parts[1]) if len(parts) > 1 else 0
            s.send(chat_line(0x0A, f"orbit u16 = {ORBIT_U16} (Earth); open the Dimensional Matrix again", (120, 220, 255), tr=False))
            return
        elif parts[0] == "/rule":
            # /rule all_or_nothing|standard|standard_enhanced|victory|off : POC ruleset of every new province battle (test)
            global POC_RULE_FORCE
            v = parts[1] if len(parts) > 1 else "off"
            POC_RULE_FORCE = v if v in BF.RULES else None
            s.send(chat_line(0x0A, f"POC ruleset of new battles: {POC_RULE_FORCE or 'per province'}", (120, 220, 255), tr=False))
            return
        elif parts[0] == "/startest":
            # /startest MIN: test the demon star now - own nation gets demon-star time, a window opens for MIN minutes
            # (0 = close it now: everybody on a star goes home, the stars reset)
            mins = float(parts[1]) if len(parts) > 1 else 30
            nid_ = cmd.get("nation", 1)
            if mins <= 0:
                STAR_FORCE[:] = [0, 0]
                star_evict_all()
                s.send(chat_line(0x0A, "Demon-star test window closed.", (255, 200, 60)))
                return
            w_ = world_state()
            if star_time_left(nid_) <= 0:
                w_.setdefault("star_until", {})[str(nid_)] = time.time() + STAR_TIME_SECONDS
            STAR_FORCE[:] = [time.time(), time.time() + mins * 60]
            save_world(w_)
            s.send(chat_line(0x0A, f"Demon-star test window open for {mins:g} min; your star: {star_label(nation_star(nid_), getattr(s, 'lang', 'en'))}.", (255, 200, 60)))
            return
        elif parts[0] == "/visit":
            # (2026-10-27 demon-star planets) /visit MAPID: enter ANY map id, other planets included, e.g. /visit 400404
            # (planet 4 col 4 row 4) - test whether the client shows provinces of the unused planets 0 / 1 / 4 / 5 / 7
            m = int(parts[1])
            log(f"   GM visit {m} ({map_kind(m)})")
            enter_field(s, m, 0x200, 0x200, capital=(m in CAPITALS.values()))
            return
        elif parts[0] == "/goto":
            # /goto COL ROW (e.g. /goto 8 7) or /goto PROVINCE_ID: jump to a province of the current planet
            # (test aid while walking through the field portals does not work on every capital corner).
            cur = getattr(s, "map", None) or CAPITALS.get(cmd.get("nation"), 600000)
            planet = (cur // 100000) % 1000 if cur < 100000000 else (CAPITALS.get(cmd.get("nation"), 600000) // 100000) % 1000
            if len(parts) >= 3:
                target = planet * 100000 + int(parts[1]) * 100 + int(parts[2])
            else:
                target = planet * 100000 + int(parts[1]) % 100000
            if target not in planet_provinces(planet):
                s.send(chat_line(0x0A, f"/goto: province {target} does not exist on planet {planet}", (255, 120, 120)))
                return
            log(f"   GM goto {target}")
            enter_field(s, target, 0x200, 0x200, capital=(target == CAPITALS.get(cmd.get("nation"))))
            return
        elif parts[0] == "/paid":
            # /paid [on|off]: mark this account as paying (honor upkeep rules differ, see honor_drain_due)
            a["paid"] = (len(parts) < 2 or parts[1].lower() != "off")
            log(f"   GM paid = {a['paid']}")
        elif parts[0] == "/honor":
            # /honor N = set the honor SHOWN in F4 (internal value = N x 100)
            cmd["honor"] = int(parts[1]) * 100
        elif parts[0] == "/medal":
            # /medal all | /medal clear | /medal KEY (first_kill, kills_100, first_capture, captures_10, flawless,
            # advanced, elite, reincarnation, honor_1000, caves_10, pocs_50, level_100)
            if parts[1] == "clear":
                cmd["medals"] = []
            elif parts[1] == "id":
                # diagnostic: /medal id 0 1 23000 26005 ... -> exactly these raw ids (file id//1000, frame id%1000)
                cmd["medals"] = [[int(x), f"medal {x}"] for x in parts[2:]]
            else:
                for key in (MEDALS if parts[1] == "all" else [parts[1]]):
                    mid, txt = MEDALS[key]
                    if not any(m[0] == mid for m in cmd.setdefault("medals", [])):
                        cmd["medals"].append([mid, txt])
            log(f"   medals now: {[m[1] for m in cmd.get('medals', [])]}")
        elif parts[0] == "/poc":
            global POC_TYPE, POC_BATTLE_KIND
            global POC_STRENGTH
            POC_TYPE = int(parts[1]); POC_BATTLE_KIND = int(parts[2]) if len(parts) > 2 else POC_BATTLE_KIND
            POC_STRENGTH = int(parts[3]) if len(parts) > 3 else POC_STRENGTH
            log(f"   GM POC type = {POC_TYPE}, battle kind = {POC_BATTLE_KIND} (applies to the next province battle)")
            return
        elif parts[0] == "/pocs":
            global POC_FORCE
            POC_FORCE = (max(1, min(5, int(parts[1]))), int(parts[2]) if len(parts) > 2 else 0) if len(parts) > 1 and parts[1] != "off" else None
            log(f"   GM POC plan = {POC_FORCE or 'by province'} (applies to the next province battle)")
            return
        elif parts[0] == "/goto":
            # test: enter any map id, e.g. /goto 600001 (Novice province, same A1-L.nm map file as 300001)
            m = int(parts[1])
            log(f"   GM goto {m} ({map_kind(m)})")
            enter_field(s, m, 0x200, 0x200, capital=(m in CAPITALS.values()))
            return
        elif parts[0] == "/hofdebug":
            global HOF_DEBUG
            HOF_DEBUG = not HOF_DEBUG; log(f"   GM: hall of fame debug markers {'on' if HOF_DEBUG else 'off'}")
        elif parts[0] == "/votedebug":                  # /votedebug: markers in every Vote window field (calibration)
            global VOTE_DEBUG
            VOTE_DEBUG = not VOTE_DEBUG
            s.send(chat_line(0x0A, f"vote window debug markers {'ON' if VOTE_DEBUG else 'off'} - reopen the Vote window",
                             (120, 255, 120)))
            return
        elif parts[0] == "/president":
            nid0 = cmd.get("nation", 1)
            pp = politics(nid0)
            _old = pp.get("president")
            pp["president"] = parts[1] if len(parts) > 1 else s.acc
            pp["candidates"] = {}; pp["election_end"] = time.time() + ELECTION_SECONDS; save_politics()
            refresh_hero_marks(*[x for x in (_old, pp["president"]) if x])
            log(f"   GM: president of nation {nid0} = {pp['president']!r}")
        elif parts[0] == "/ally":
            a0 = cmd.get("nation", 1); b0 = int(parts[1])
            if b0 not in CAPITALS or b0 == a0:
                raise ValueError("unknown nation")
            pr = (min(a0, b0), max(a0, b0))
            if pr in [(min(x, y), max(x, y)) for x, y in NATION_ALLIES]:
                NATION_ALLIES[:] = [(x, y) for x, y in NATION_ALLIES if (min(x, y), max(x, y)) != pr]
                log(f"   GM: nations {a0} and {b0} are no longer allied")
            else:
                NATION_ALLIES.append(pr); log(f"   GM: nations {a0} and {b0} are now allied")
            WORLD_allies_save()
            for t in list(ONLINE):
                if getattr(t, "logged_in", False) and not t.w.is_closing():
                    t.send(build_relations())
        elif parts[0] == "/nation":
            n = int(parts[1])
            if n not in CAPITALS:
                raise ValueError("unknown nation")
            cmd["nation"] = n; cmd["tier"] = PLANET_TIER.get(nation_planet(n), 1); s.cmd = cmd
        elif parts[0] == "/stats":
            # /stats -> show; /stats KEY N -> set a medal counter (kills, captures, cave_wins, pocs); /stats reset
            st = cmd.setdefault("stats", {})
            if len(parts) > 1 and parts[1] == "reset":
                st.clear()
            elif len(parts) > 2:
                st[parts[1]] = int(parts[2])
            log(f"   stats {st}, honor {cmd.get('honor', 0) // 100}, tier {cmd.get('tier', 1)}, "
                f"reincarnations {cmd.get('reincarnations', 0)}")
        elif parts[0] == "/skill":
            # test: /skill NAME|BIT [UNIT#|all]  (e.g. /skill Heal 1, /skill 25 all, /skill all all) | /skill clear
            #       | /skill list.  Bits are added on top of chassis/equipment; effective from the NEXT battle entry.
            byname = {k.lower().replace(" ", ""): v for k, v in SPECIAL_BITS.items()}
            byname.update({"repair": 20, "defensivematrix": 41, "snipe": 46, "frenzy": 52, "airmine": 36})
            if parts[1] == "list":
                for i, u in enumerate(a["units"], 1):
                    bits = [b for b in range(64) if unit_abilities(u) >> b & 1 and b not in (1, 31)]
                    log(f"   unit #{i} uid {u['uid']} {u['chassis']}: "
                        f"{[n for n, b in SPECIAL_BITS.items() if b in bits] or bits}")
                return
            if parts[1] == "clear":
                for u in a["units"]:
                    u.pop("gm_skills", None)
            else:
                if parts[1] == "all":
                    want = sorted(set(SPECIAL_BITS.values()))
                elif parts[1].isdigit():
                    want = [int(parts[1])]
                else:
                    want = [byname[parts[1].lower().replace("_", "")]]
                sel = parts[2] if len(parts) > 2 else "1"
                us = a["units"] if sel == "all" else [a["units"][int(sel) - 1]]
                for u in us:
                    u["gm_skills"] = sorted(set(u.get("gm_skills", [])) | set(want))
                    log(f"   unit uid {u['uid']} {u['chassis']} gm skills {u['gm_skills']}")
        elif parts[0] == "/unitlevel":
            n = int(parts[1])
            for u in a["units"]:
                PG.ensure_unit(u)["level"] = max(1, n)
        else:
            log("   GM commands: /points N, /res N, /money N, /dmgtest CODE|off, /dmgtypes on|off, /level inf|mob|avi|org N, /unitlevel N, /nation ID, /theme 9..13|off, /goto MAPID, /poc TYPE [KIND] [STRENGTH], /honor N, /medal all|clear|KEY|id N.., /skill NAME|BIT|all [UNIT#|all] | clear | list")
            return
    except (IndexError, ValueError, KeyError) as e:
        log(f"   GM command {text!r} failed: {e!r}")
        return
    accs[s.acc] = a
    save_accounts(accs)
    s.send(build_commander(s.acc, cmd.get("nation", getattr(s, "cmd", {}).get("nation", 1)), cmd["attrs"], resources=a["resources"]))
    s.send(build_hero_info(s))
    if parts[0] == "/nation":
        enter_field(s, CAPITALS[cmd["nation"]], 0x200, 0x200, capital=True)
    log(f"   GM {text!r} done: points {cmd['points']}, resources {a['resources']}, "
        f"branches {dict((k, v['level']) for k, v in cmd['branches'].items())}")

# planet names (user 2026-10-27 11:26: "新手星定义为地球", real planet names instead of novice / advanced / elite)
PLANET_ZH = {6: ("地球", "地球"), 2: ("火星", "火星"), 3: ("木星", "木星")}   # (zh-tw, zh-cn)
# CLOSED PLANETS (user 2026-10-27 10:59 "8 颗星球都做出来，但显示未开放"): vinu.inf has 8 planets (0..7, 64-85 provinces
# each, maps present); the game uses 6 / 2 / 3.  The other five are listed in the Dimensional Matrix with their own
# planet art (odv.dat pl-000..017.bik, class byte) and "(not open)" in the name; TRAVEL to them is refused.
# OPEN flag stays 1 (0 = the window does not draw the planet at all).  Planet 4 = the future demon star (STAR_MAP is
# one of its provinces).   pid: (English, zh-tw, zh-cn, art class, orbit vector, (A, B, phase, size))
GATE_CLOSED_PLANETS = {
    # (user 2026-10-27 11:32) the demon stars use the asteroid art 002 / 004 / 012 / 013 and sit in the asteroid belt
    # between Mars and Jupiter; the other planets of the solar system are listed too (all nine).
    # ids 1 / 4 / 5 / 7 have maps in vinu.inf (0 too, but its corner would be map id 0 = "no map" for the server);
    # 8..13 are shown in the Dimensional Matrix only (no maps, never open).
    7:  ("Azure Dragon demon star",   "青龍魔星", "青龙魔星", 2,  (3, 0, 4),   (135, 128, 20000, 6)),   # DEMON_STARS
    1:  ("White Tiger demon star",    "白虎魔星", "白虎魔星", 4,  (-4, 0, 5),  (140, 132, 110000, 6)),
    5:  ("Vermilion Bird demon star", "朱雀魔星", "朱雀魔星", 12, (-10, 0, 6), (138, 130, 200000, 6)),
    4:  ("Black Tortoise demon star", "玄武魔星", "玄武魔星", 13, (9, 0, -6),  (142, 134, 290000, 6)),
    8:  ("Mercury", "水星",   "水星",   6,  (2, 0, 1),   (40, 38, 250000, 5)),
    9:  ("Venus",   "金星",   "金星",   3,  (-3, 0, 2),  (65, 62, 120000, 7)),
    13: ("Saturn",  "土星",   "土星",   7,  (11, 0, 8),  (200, 190, 330000, 13)),
    10: ("Uranus",  "天王星", "天王星", 8,  (-12, 0, 9), (228, 216, 60000, 10)),
    11: ("Neptune", "海王星", "海王星", 17, (13, 0, -10), (256, 242, 170000, 10)),
    12: ("Pluto",   "冥王星", "冥王星", 15, (-14, 0, -11), (285, 270, 280000, 5)),
}
CLOSED_SUFFIX = {"zh-tw": "（未開放）", "zh-cn": "（未开放）"}

def planet_name(pid, name, s=None):
    """planet name in the session's language (bytes in its encoding)."""
    lang, enc = session_lang_enc(s) if s is not None else ("en", "latin-1")
    if pid in GATE_CLOSED_PLANETS and not any(p[0] == pid for p in PLANETS):
        en, tw, cn = GATE_CLOSED_PLANETS[pid][:3]
        _open = s is not None and pid in STAR_PLANET_IDS and star_access(s, pid) is None
        t = {"zh-tw": tw, "zh-cn": cn}.get(lang, en) + ("" if _open else CLOSED_SUFFIX.get(lang, " (not open)"))
        try:
            return t.encode(enc)
        except (UnicodeEncodeError, LookupError):
            return (en + " (not open)").encode("latin-1", "replace")
    if lang in ("zh-tw", "zh-cn") and pid in PLANET_ZH:
        return PLANET_ZH[pid][0 if lang == "zh-tw" else 1].encode(enc, "replace")
    return name.encode("latin-1", "replace")

def _planet_rec(pid, name, cls, opn, pos, detail=False, s=None):
    """planet record shared by 0x40 (New commander) and 0x38 (Dimensional Matrix): u16 id, s8 name, u8 class,
    u8 size, u32 angle (1/1000 deg), 3 x s8 orbit vector, u16, u16, u32, u16, u8 DETAIL flag, u8 OPEN."""
    nb = planet_name(pid, name, s)
    a, b, phase, size = PLANET_ORBIT.get(pid) or (GATE_CLOSED_PLANETS[pid][5] if pid in GATE_CLOSED_PLANETS else (150, 140, 0, 10))
    # (user 2026-10-27 11:40: planets move along their orbits, each at its own speed) the orbital position follows
    # real time: one Earth orbit = ORBIT_EARTH_MINUTES, others by Kepler (period ~ A^1.5) -> inner planets are faster.
    period = (ORBIT_DEMO_EARTH_SECONDS or ORBIT_EARTH_MINUTES * 60.0) * (max(a, 1) / 90.0) ** 1.5
    phase = int(phase + 360000.0 * ((time.time() % (period * 1000)) / period)) % 360000
    # u16 after the position: meaning unknown.  11:52 user test with GM /orbit16 N: the client does NOT turn the
    # planets by itself (the matrix is a still picture) -> stays 0; only the opening position follows real time.
    u16 = min(65535, int(ORBIT_U16 * (90.0 / max(a, 1)) ** 1.5)) if ORBIT_U16 else 0
    return (struct.pack(">H", pid) + bytes([len(nb)]) + nb + bytes([cls, size]) + struct.pack(">I", 0)
            + struct.pack(">bbb", *pos) + struct.pack(">HH", a, b) + struct.pack(">I", phase) + struct.pack(">H", u16)
            + bytes([1 if detail else 0, opn]))

ORBIT_EARTH_MINUTES = 60          # real minutes for one Earth orbit in the Dimensional Matrix
ORBIT_U16 = 0                     # GM /orbit16 N (test of the unknown u16)
# ANIMATION TEST (user 2026-10-27 11:53 "從這裡下手"): the client draws the matrix as a still picture and has no orbit
# clock of its own (0045a6d0 only turns the CAMERA by time).  Test: resend 0x38 sub 0 every ORBIT_PUSH s while the
# window is open (ORBIT_PUSH_FOR s at most) with a fast demo clock.  Open question: what the client does with a 0x38
# that arrives after the window was closed (it might reopen it) -> GM only (/orbitpush SECONDS, 0 = off).
ORBIT_PUSH = 0.0
ORBIT_PUSH_FOR = 180
ORBIT_DEMO_EARTH_SECONDS = 0      # while > 0: one Earth orbit in this many seconds (GM /orbitpush sets 60)

async def orbit_push(s, pid):
    t0 = time.time()
    while ORBIT_PUSH > 0 and time.time() - t0 < ORBIT_PUSH_FOR and getattr(s, "gate_push_id", 0) == pid \
            and not s.w.is_closing():
        await asyncio.sleep(ORBIT_PUSH)
        try:
            s.send(build_star_gate(s))
        except Exception as e:
            log(f"   orbit push: {e!r}")
            return

# CONFIRMED (00460d00 / 00459d30 / 00401270 / 00401560): the two u16 after the orbit vector are the orbit ELLIPSE
# semi-major A and semi-minor B (focus = sqrt(A^2-B^2), so A >= B > 0), the u32 is the orbital position in 1/1000 deg.
# A = B = 0 put every planet at infinity: nothing drawn and always "too far".  Sun is size 20 at the origin.
# pid: (A, B, phase millideg, size)  -- PLACEHOLDER layout: inner novice, middle advanced, outer elite.
PLANET_ORBIT = {6: (90, 85, 30000, 8),          # Earth   (solar order, user 2026-10-27 11:32)
                2: (112, 106, 150000, 7),         # Mars
                3: (170, 160, 260000, 14)}        # Jupiter   (Saturn ... Pluto: GATE_CLOSED_PLANETS)

# planet detail shown in the Dimensional Matrix INFORMATION panel (CONFIRMED order, 0 = lowest word):
#   terrain, gravity, atmosphere, cloud cover, radiation, ORE, SILICON, URANIUM, SULFUR abundance (0 = "Scarce")
# Higher tiers are richer (design: resources differ per planet).  Values are levels, PLACEHOLDERS.
PLANET_ENV = {6: [1, 2, 2, 1, 1, 1, 1, 0, 2],
              2: [2, 2, 1, 2, 2, 2, 2, 1, 2],
              3: [3, 3, 1, 2, 3, 3, 3, 2, 3]}
STAR_GATE_RANGE = 1000    # Dimensional Matrix range, same units as PLANET_ORBIT (orbits <= 240 -> all in range)
# ---- STAR CENTER (Faction Pledge Center, Portals.por type 10): move to a more advanced planet -------------------
# client 0x37 [00] (walk in) -> server 0x31 sub 0 window (client 005afa50) or 0x31 sub 1 [s16] message box (005ae400)
#   sub 0: u8 n planets {planet record = star-gate record WITHOUT detail block},
#          u8 n nations {u32 nation, u16 (+4), u8 (+8), u16 WAIT (+0xc, !=0 -> "not accepting new members"),
#                        u8 PENALTY (+0x10, 0 = none, else "you will lose uranium and honor"), s8 (+0x14), u8 (+0x30),
#                        s16 description (+0x34), u8 MODE (+0x50: 0 join, 1 reincarnate)}
# client 0x37 [05][u32 nation][u8 penalty] = pledge/join, [0a][u32 nation] = visit,
#        0x37 [0b][u32 nation][u8 penalty][u8 hero picture] = reincarnate.
# Rules (design): Novice -> Advanced needs a division at level 20 (progression.can_advance), Advanced -> Elite needs
# STARCENTER_ELITE_LEVEL; one tier at a time; no way back.  Joining keeps units and resources (PENALTY 0).
STARCENTER_ELITE_LEVEL = 50          # PLACEHOLDER: division level needed on the Advanced planet to go to Elite
def nation_planet(nid):
    return (CAPITALS.get(nid, 600000) // 100000) % 1000

def starcenter_targets(cmd):
    """(nations the commander may join now, refusal message or None)"""
    tier = cmd.get("tier", 1)
    if tier == 1 and not PG.can_advance(cmd):
        return [], (f"A division must reach level {PG.ADVANCE_BRANCH_LEVEL} before you can move to the "
                    f"Advanced planet.")
    if tier == 2 and not any(v["level"] >= STARCENTER_ELITE_LEVEL for v in cmd["branches"].values()):
        return [], f"A division must reach level {STARCENTER_ELITE_LEVEL} before you can move to the Elite planet."
    if tier >= 3:
        n = cmd.get("reincarnations", 0)
        if n >= REINC_MAX:
            return [], f"You cannot reincarnate more than {REINC_MAX} times."
        need = reinc_level(cmd)
        if not any(v["level"] >= need for v in cmd["branches"].values()):
            return [], f"A division must reach level {need} before you can reincarnate."
        return [n_ for n_ in NATION_DEFS if PLANET_TIER.get(n_[3], 1) == 1], None
    nats = [n for n in NATION_DEFS if PLANET_TIER.get(n[3], 1) == tier + 1]
    if not nats:
        return [], "There are currently no factions open at this time."
    return nats, None

def switch_targets(cmd):
    """factions on the hero's own planet tier he may switch to (costs NATION_CHANGE_URA); none on the Elite planet,
    where the StarCenter rows are reincarnation offers"""
    tier = cmd.get("tier", 1)
    if tier >= 3:
        return []
    return [n for n in NATION_DEFS if PLANET_TIER.get(n[3], 1) == tier and n[0] != cmd.get("nation")]

def faction_penalty(nats, nid):
    """1 = joining the strongest faction of its planet (most provinces) -> 'YOU WILL LOSE URANIUM AND HONOR'
    (client shows ksSCJoinNationPenalty for PENALTY != 0).  Equal factions: no penalty."""
    counts = {n[0]: owned_provinces(n[0]) for n in nats}
    return 1 if counts and max(counts.values()) > min(counts.values()) and counts.get(nid) == max(counts.values()) else 0

def _s16_tr(s, text):
    """u16-length text of a Star Center message box (0x31 sub 1) in the player's language and code page (i18n.py)."""
    lang, enc = session_lang_enc(s)
    b = I18N.translate_checked(str(text), lang).encode(enc, "replace")[:1000]
    return struct.pack(">H", len(b)) + b

def build_starcenter(s, cmd):
    nats, err = starcenter_targets(cmd)
    if err and not switch_targets(cmd):
        return bytes([0x31, 1]) + _s16_tr(s, err)
    if err:                      # cannot advance yet, but can still switch faction on this planet (Uranium)
        nats = []
    accs = load_accounts() if "load_accounts" in globals() else {}
    a_me = accs.get(getattr(s, "acc", None)) or {}
    d = bytearray([0x31, 0, len(PLANETS)])
    for p in PLANETS:
        d += _planet_rec(p[0], p[1], p[2], 1, p[4], detail=False, s=s)
    sw = switch_targets(cmd)
    d += bytes([len(nats) + len(sw)])
    lang = getattr(s, "lang", "en")
    zh = lang in ("zh-tw", "zh-cn")
    tw = lang == "zh-tw"
    for n in nats + sw:
        members = sum(1 for a in accs.values() if isinstance(a, dict) and a.get("commander", {}).get("nation") == n[0])
        # (user 2026-10-24 21:44: the text showed the internal name "Adv-Nation4" in English) everything in the viewer's
        # language: faction name, planet name, capital, provinces, members, leader, what joining costs
        nm = nation_name(n[0], lang)
        pl = planet_name(n[3], next((p[1] for p in PLANETS if p[0] == n[3]), "?"), s).decode(getattr(s, "enc", "latin-1"), "replace")
        cap = province_number(CAPITALS.get(n[0], 0)) if CAPITALS.get(n[0]) else 0
        try:
            prov = owned_provinces(n[0])
        except Exception:
            prov = 0
        try:
            lead = politics(n[0]).get("president") or ""
        except Exception:
            lead = ""
        nolead = "無" if tw else ("无" if zh else "none")
        mode = 1 if cmd.get("tier", 1) >= 3 else 0                  # MODE 1 = reincarnate (opens the rtn dialog)
        _ura = int((a_me.get("resources") or [0] * 5)[3]) if a_me else 0
        if n in sw:
            pen = NATION_CHANGE_URA
        else:
            pen = 0 if mode or not faction_penalty(nats, n[0]) else max(1, int(_ura * FACTION_PENALTY_HONOR))
        if zh:
            base = (f"{nm}：位於{pl}，首都 {cap} 號省，領土 {prov} 省，成員 {members} 人，領主：{lead or nolead}。" if tw else
                    f"{nm}：位于{pl}，首都 {cap} 号省，领土 {prov} 省，成员 {members} 人，领主：{lead or nolead}。")
            if mode:
                extra = (f"轉生加入此國：回到 1 級，單位上限 +{REINC_UNIT_BONUS}，並獲得一隻外星生物。" if tw else
                         f"转生加入此国：回到 1 级，单位上限 +{REINC_UNIT_BONUS}，并获得一只外星生物。")
            elif n in sw:
                extra = (f"轉換到此國需要 {NATION_CHANGE_URA} 鈾。" if tw else f"转换到此国需要 {NATION_CHANGE_URA} 铀。")
            elif pen:
                extra = ("這是本星領土最多的國家，加入會損失部分鈾與榮譽。" if tw else "这是本星领土最多的国家，加入会损失部分铀与荣誉。")
            else:
                extra = ("加入此國不會有懲罰，單位與資源全部保留。" if tw else "加入此国不会有惩罚，单位与资源全部保留。")
        else:
            base = (f"{nm}: on the {pl} planet, capital #{cap}, {prov} provinces, {members} members, "
                    f"leader: {lead or nolead}.")
            if mode:
                extra = (f"Reincarnate into this faction: back to level 1, +{REINC_UNIT_BONUS} unit capacity and a gift "
                         f"alien unit.")
            elif n in sw:
                extra = f"Switching to this faction costs {NATION_CHANGE_URA} Uranium."
            elif pen:
                extra = "The strongest faction of its planet: joining costs part of your Uranium and honor."
            else:
                extra = "No penalty: you keep all your units and resources."
        desc = base + ("\n" if not zh else "") + " " + extra
        _db = desc.encode(getattr(s, "enc", "latin-1"), "replace")[:1000]
        # (user 2026-10-24 21:24) client 005ad8a0: +4 u16 PLANET id, +8 u8 PLANET TYPE ("%d" = tier),
        # +0xc TIME TO JOIN (0 = now), +0x10 PENALTY in Uranium ("%3d Uranium", 0 = none); s8 +0x14 = OVERLORD (21:44:
        # it showed the faction name) -> the faction's leader
        d += struct.pack(">IHBHB", n[0], n[3] & 0xFFFF, PLANET_TIER.get(n[3], 1) & 0xFF, 0, min(255, pen)) \
            + _s8e(s, lead or nolead) + bytes([0]) + struct.pack(">H", len(_db)) + _db + bytes([mode])
    return bytes(d)

HOME_FREE_PER_DAY = 5         # F8 return to capital: 5 free uses per day, then HOME_TELEPORT_URA each
HOME_TELEPORT_URA = 5         # PLACEHOLDER price per extra use

def go_home(s, free_pass=False):
    """F8 / ksBackToCapital: instantly back to the capital (outside battle).  5 free uses a day (server date),
    further uses cost Uranium."""
    accs, a = get_account(getattr(s, "acc", None))
    cmd = a.setdefault("commander", {})
    cap = CAPITALS.get(cmd.get("nation"))
    if cap is None:
        return False
    if getattr(s, "battle", None) and not getattr(s, "spectator", False):
        _say_lang(s, "战斗中不能传送回首都。", "戰鬥中不能傳送回首都。", "You cannot teleport home during a battle.",
                  (255, 150, 120))                 # (20:31) 0x31 is the StarCenter window: it opened in the battle
        return False
    if getattr(s, "map", None) == cap:
        return False
    if not free_pass:
        today = time.strftime("%Y-%m-%d")
        if a.get("home_day") != today:
            a["home_day"], a["home_used"] = today, 0
        if a["home_used"] >= HOME_FREE_PER_DAY:
            if not res_can_pay(a, (0, 0, 0, HOME_TELEPORT_URA)):
                _say_lang(s, f"今天的 {HOME_FREE_PER_DAY} 次免费传送已用完，之后每次 {HOME_TELEPORT_URA} 铀。",
                          f"今天的 {HOME_FREE_PER_DAY} 次免費傳送已用完，之後每次 {HOME_TELEPORT_URA} 鈾。",
                          f"You used your {HOME_FREE_PER_DAY} free teleports today. Each extra one costs {HOME_TELEPORT_URA} Uranium.",
                          (255, 150, 120))         # (20:31) not 0x31 (StarCenter window)
                return False
            res_add(a, (0, 0, 0, -HOME_TELEPORT_URA))
            s.send(build_commander(s.acc, cmd.get("nation", 1), cmd.get("attrs", (0, 0, 0, 0)), resources=a["resources"]))
        a["home_used"] += 1
        accs[s.acc] = a
        save_accounts(accs)
        left = max(0, HOME_FREE_PER_DAY - a["home_used"])
        s.send(chat_line(0x0A, f"Teleport home: {left} free use(s) left today.", (120, 220, 255)))
    log(f"   go home: {s.acc} -> capital {cap}")
    enter_field(s, cap, 0x200, 0x200, capital=True)
    return True

def starcenter_request(s, body):
    accs, a = get_account(getattr(s, "acc", None))
    cmd = PG.ensure_commander(a.setdefault("commander", {}))
    cmd.setdefault("nation", getattr(s, "cmd", {}).get("nation", 1))
    sub = body[1] if len(body) > 1 else 0
    if sub == 0:
        s.send(build_starcenter(s, cmd))
        log(f"   StarCenter window (tier {cmd.get('tier', 1)}): {starcenter_targets(cmd)[1] or 'faction list'}")
        return
    nid = struct.unpack_from(">I", body, 2)[0] if len(body) >= 6 else 0
    if sub == 0x0a:                                   # visit: go to that faction's capital without joining
        if nid not in CAPITALS:
            s.send(bytes([0x31, 1]) + _s16_tr(s, "Unknown faction.")); return
        log(f"   StarCenter: visit nation {nid} capital {CAPITALS[nid]}")
        enter_field(s, CAPITALS[nid], 0x200, 0x200, capital=True)
        return
    if sub == 0x05:                                   # pledge / join
        nats, err = starcenter_targets(cmd)
        switching = nid in [n[0] for n in switch_targets(cmd)] and (err or nid not in [n[0] for n in nats])
        if switching:
            nats = switch_targets(cmd)
            err = None
            if not res_can_pay(a, (0, 0, 0, NATION_CHANGE_URA)):
                s.send(bytes([0x31, 1]) + _s16_tr(s, f"Switching faction costs {NATION_CHANGE_URA} Uranium."))
                log(f"   StarCenter: switch to {nid} refused (Uranium {a['resources'][3]})")
                return
            res_add(a, (0, 0, 0, -NATION_CHANGE_URA))
        if err or nid not in [n[0] for n in nats]:
            s.send(bytes([0x31, 1]) + _s16_tr(s, err or "You cannot join this faction."))
            log(f"   StarCenter: join {nid} refused ({err or 'not a next-tier faction'})")
            return
        old = cmd["nation"]
        if a.get("paid"):                       # paid accounts: changing nation resets honor to 0 (user rule)
            cmd["honor"] = 0
            log("   StarCenter: paid account changed nation -> honor reset to 0")
        if faction_penalty(nats, nid):
            lost_h = int(cmd.get("honor", 0) * FACTION_PENALTY_HONOR)
            cmd["honor"] = cmd.get("honor", 0) - lost_h
            a["resources"][3] = int(a["resources"][3] * (1 - FACTION_PENALTY_HONOR))
            log(f"   StarCenter: faction penalty -> honor -{lost_h}, uranium now {a['resources'][3]}")
        cmd["xp_bonus_nation"] = nid if weakest_nation(nats) == nid else 0
        if cmd["xp_bonus_nation"]:
            log(f"   StarCenter: {s.acc} joined the weakest faction -> +{int(JOIN_XP_BONUS * 100)}% XP while he stays")
        cmd["nation"] = nid
        cmd["tier"] = PLANET_TIER.get(nation_planet(nid), 1)
        a["commander"] = cmd
        check_medals(s, a, accs)
        accs[s.acc] = a
        save_accounts(accs)
        s.cmd = cmd
        s.send(build_commander(s.acc, nid, cmd.get("attrs", (0, 0, 0, 0)), resources=a["resources"]))
        s.send(build_relations())
        log(f"   StarCenter: {s.acc} left nation {old} and joined {nid} (planet {nation_planet(nid)}, tier {cmd['tier']})")
        # entering a map on another planet makes the client show "Welcome Commander! ... claim your destiny"
        enter_field(s, CAPITALS[nid], 0x200, 0x200, capital=True)
        return
    if sub == 0x0b:
        reincarnate(s, accs, a, cmd, nid, body[7] if len(body) > 7 else cmd.get("look", 1))
        return
    log(f"   StarCenter: unknown request {body.hex()}")

# ---- REINCARNATION (ntf2/rtn-desc.txt; client 005ae640 / rtn dialog 00586940) ----------------------------------
# After max level: restart at level 1 (cap +1 per reincarnation), gift alien unit not sold in shops, +2 base unit
# capacity, a mark beside the name (0x20 rank byte = count -> ui-rtl1/ui-rtr1), a new appearance.  Client checks:
# units <= 25 + 2 x count, count < 11 (message says 10).  Offered on the Elite planet as StarCenter MODE 1 rows.
REINC_BASE_LEVEL = 100     # PLACEHOLDER: max level that allows reincarnation (rtn-desc implies level 100)
REINC_MAX = 10
REINC_URA = 30           # Uranium price of a reincarnation ("return to a lower planet")
NATION_CHANGE_URA = 150  # Uranium price of switching to another faction of the same planet
ATTR_RESET_URA = 15      # Uranium price of /reset (all attribute points back to the point pool)
REINC_UNIT_BONUS = 2
REINC_KEEP_UNITS = 25      # client (005ae640): reincarnation is refused while you own more than 25 + 2 x (current reincarnations) units
REINC_GIFT_UNIT = "g011"   # gift alien: Ubik (small dragon, evolves into Tyr/Haltyr = the dinosaur line) - was Slanth (crab) placeholder

def reinc_level(cmd):
    return REINC_BASE_LEVEL + cmd.get("reincarnations", 0)

def reincarnate(s, accs, a, cmd, nid, pic):
    nats, err = starcenter_targets(cmd)
    if err or cmd.get("tier", 1) < 3 or nid not in [n[0] for n in nats]:
        s.send(bytes([0x31, 1]) + _s16_tr(s, err or "You cannot reincarnate into this faction."))
        log(f"   StarCenter: reincarnation refused ({err or 'bad faction'})")
        return
    keep = REINC_KEEP_UNITS + REINC_UNIT_BONUS * cmd.get("reincarnations", 0)
    if len(a["units"]) > keep:                                  # the client already blocks this; keep the server in line
        s.send(bytes([0x31, 1]) + _s16_tr(s, f"Your new incarnation will not be able to own more than {keep} units."))
        log(f"   StarCenter: reincarnation refused ({len(a['units'])} units > {keep})")
        return
    if not res_can_pay(a, (0, 0, 0, REINC_URA)):
        s.send(bytes([0x31, 1]) + _s16_tr(s, f"Reincarnation costs {REINC_URA} Uranium."))
        log(f"   StarCenter: reincarnation refused (Uranium {a['resources'][3]} < {REINC_URA})")
        return
    res_add(a, (0, 0, 0, -REINC_URA))
    n = cmd.get("reincarnations", 0) + 1
    cmd["reincarnations"] = n
    cmd["points"] = cmd.get("points", 0) + PG.REINC_POINTS      # guide: +2 bonus attribute points per reincarnation
    for b in cmd["branches"].values():
        b["level"], b["xp"] = 1, 0
    cmd["nation"], cmd["tier"] = nid, PLANET_TIER.get(nation_planet(nid), 1)
    if pic:
        cmd["look"] = pic
    uid = new_unit_uid({**accs, s.acc: a})
    a["next_uid"] = uid + 1
    a["units"].append({"uid": uid, "chassis": REINC_GIFT_UNIT, "label": "Gift"})
    a["commander"] = cmd
    award_medal(s, "reincarnation", a, accs)
    accs[s.acc] = a
    save_accounts(accs)
    s.cmd = cmd
    s.send(build_commander(s.acc, nid, cmd.get("attrs", (0, 0, 0, 0)), resources=a["resources"]))
    s.send(build_relations())
    s.send(build_hero_info(s))
    s.send(build_units([roster_rec(u) for u in a["units"]], mech=mech_for(s)))
    log(f"   StarCenter: {s.acc} REINCARNATED (#{n}) into nation {nid}, look {pic}, gift unit {uid}")
    enter_field(s, CAPITALS[nid], 0x200, 0x200, capital=True)

def build_star_gate(s):
    """server 0x38 sub 0 (client 005b2470): u8 ?, u8 n planets {_planet_rec, [detail: 9 x u8, u32, u32,
    u8 m {u32, u8}]}, u16 current planet (+0x23544), u16 (+0x23548)."""
    cmd = getattr(s, "cmd", {"nation": 1})
    here = (CAPITALS.get(cmd.get("nation"), 600000) // 100000) % 1000
    # u8 after the sub = gate ENABLED (+0x2354c): 0 greys out TRANSPORT whatever planet is selected (005b1bd0).
    shown = list(PLANETS) + [(pid, v[0], v[3], 0, v[4]) for pid, v in sorted(GATE_CLOSED_PLANETS.items())
                             if not any(p[0] == pid for p in PLANETS)]
    d = bytearray([0x38, 0, 1, len(shown)])
    for p in shown:
        # OPEN flag = 1 for every planet here: with 0 the window greys the planet out ("Disable") and draws
        # nothing.  Whether the commander may really go there is decided on TRAVEL (star_gate_travel).
        d += _planet_rec(p[0], p[1], p[2], 1, p[4], detail=True, s=s)
        # detail block (planet object +200..+0xf4): 9 x u8, u32, u32, u8 m {u32, u8}.  Meaning unknown -> zeros.
        d += bytes(PLANET_ENV.get(p[0], [0] * 9)) + struct.pack(">II", 0, 0) + bytes([0])
    # u16 current planet, u16 TRAVEL RANGE (+0x23548): the Travel button (005b1bd0 case 0x1f) refuses planets whose
    # distance is above it ("not within range" - faction technology).  0 disabled every other planet.
    d += struct.pack(">HH", here, STAR_GATE_RANGE)
    return bytes(d)

def star_gate_travel(s, planet):
    """Travel request.  Rules (design): only to an OPEN planet, and from the Novice planet only after any branch
    reached level 20 (progression.can_advance).  Refusals use 0x38 sub 1 [s16 message] (client 005b1fa0)."""
    cmd_full = PG.ensure_commander(get_account(getattr(s, "acc", None))[1].setdefault("commander", {}))
    here = (CAPITALS.get(getattr(s, "cmd", {}).get("nation"), 600000) // 100000) % 1000
    info = next((p for p in PLANETS if p[0] == planet), None)
    if planet in STAR_PLANET_IDS:
        # demon star: the nation's own star during its window (results_field.star_travel); a success needs no reply
        msg = star_travel(s, planet)
        if msg is None:
            return b""
    elif info is None and planet in GATE_CLOSED_PLANETS:
        msg = "This planet is not open yet."
    elif info is None:
        msg = "Unknown planet."
    elif planet == here:
        msg = "You are already on this planet."
    elif PLANET_TIER.get(planet, 1) < PLANET_TIER.get(here, 1):
        msg = f"Veteran commanders cannot return to the {info[1]} planet."
    elif PLANET_TIER.get(planet, 1) > PLANET_TIER.get(here, 1):
        msg = "To move to a more advanced planet, pledge to one of its factions at the StarCenter."
    elif PLANET_TIER.get(planet, 1) > PLANET_TIER.get(here, 1) and not PG.can_advance(cmd_full):
        msg = f"A division must reach level {PG.ADVANCE_BRANCH_LEVEL} before you can travel to {info[1]}."
    else:
        msg = f"Travel to {info[1]} is not implemented yet."
    log(f"   star gate travel to planet {planet}: {msg}")
    lang, enc = session_lang_enc(s)
    try:
        mb = I18N.translate_checked(msg, lang).encode(enc, "replace")[:1000]          # (2026-10-27) message box in the player's language
    except Exception:
        mb = msg.encode("latin-1", "replace")
    return bytes([0x38, 1]) + struct.pack(">H", len(mb)) + mb

# ---- TP / TK between allies (Ctrl+F5 / Ctrl+F6; client hotkeys in FUN_004b3680) ---------------------------------------
# TP OFF (default ON until the client reports): allies cannot Teleport (action 5 [u32 unit][pt]) or load (action 10
# [u32 unit]) your units.  TK OFF (default): allies cannot attack your units (0x29 [attacker][u32 target]).
def owner_peer(s, uid):
    """the OTHER player on this map who owns unit uid (None for own units, aliens, unknown)."""
    for o in map_peers(s):
        if uid in getattr(o, "put_args", {}) or uid in getattr(o, "unit_pos", {}) or uid == getattr(o, "hero_uid", None):
            return o
    return None
