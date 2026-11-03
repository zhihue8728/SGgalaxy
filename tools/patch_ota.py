"""OTA hooks for server/sgserver.py (2026-10-22, claude/OTA_PLAN.md).  Run from the repo root."""
import shutil
p = "server/sgserver.py"
t = open(p, encoding="utf-8").read()
assert "import ota as OTA" not in t, "already patched"
shutil.copy(p, p + ".before_ota")


def rep(o, n, c=1):
    global t
    assert t.count(o) == c, (t.count(o), o[:90])
    t = t.replace(o, n)


rep("import acctstore as STORE\n", "import acctstore as STORE\nimport ota as OTA          # launcher downloads + version table (claude/OTA_PLAN.md)\n")

# ---- version table + policy -------------------------------------------------------------------------------------------
rep('''_ALLOWED_HASHES = {"t": 0, "v": set()}
''', '''_ALLOWED_HASHES = {"t": 0, "v": set()}

# ---- OTA (2026-10-22): which release a client runs (its code checksum -> updates/versions/*), old-version notice,
#      blocked after the deadline / below min_version, release broadcast, countdown restart (claude/OTA_PLAN.md)
UPDATE_DIR = os.environ.get("SG_UPDATE_DIR") or os.path.join(_SRV_DIR, "..", "updates")
OTA_V = OTA.Versions(UPDATE_DIR, client_code_hash)
RESTART_FILE = os.path.join(_SRV_DIR, "restart_request.json")    # written by deploy (-Countdown N)
RESTART = {"at": None, "why": "", "task": None}

def ota_say(o, key, rgb=(255, 220, 120), popup=True, **kw):
    try:
        txt = OTA.text(key, _mail_lang(o), **kw)
        if popup:
            o.send(chat_line(0x0A, txt, rgb, tr=False))
        o.send(chat_line(3, txt, rgb, tr=False))                       # kept in the chat history
    except Exception as e:
        log(f"   ota message error: {e!r}")

def ota_online():
    return [o for o in list(ONLINE) if getattr(o, "logged_in", False) and not o.w.is_closing()]

def ota_client_release(s):
    """release version the session runs (None = unknown / not reported yet)."""
    return getattr(s, "client_release", None)

async def ota_cycle():
    """every 15 s: new release published -> tell the players with an older client; restart request from deploy."""
    try:
        OTA_V.reload()
    except Exception as e:
        log(f"   OTA reload error: {e!r}")
    if OTA_V.current:
        log(f"   OTA: release {OTA_V.current}, {len(OTA_V.by_hash)} known client build(s)")
    while True:
        await asyncio.sleep(15)
        try:
            if OTA_V.reload():
                log(f"   OTA: new release {OTA_V.current}")
                _ALLOWED_HASHES["t"] = 0
                for o in ota_online():
                    r = ota_client_release(o)
                    if r is None or OTA.vtuple(r) < OTA.vtuple(OTA_V.current):
                        ota_say(o, "released", cur=OTA_V.current, notes=OTA_V.release.get("notes"))
            if os.path.exists(RESTART_FILE):
                try:
                    with open(RESTART_FILE, encoding="utf-8") as f:
                        req = json.load(f)
                finally:
                    os.remove(RESTART_FILE)
                restart_countdown(int(req.get("seconds", 300)), req.get("why") or "")
        except Exception as e:
            log(f"   OTA cycle error: {e!r}")

RESTART_MARKS = (1800, 900, 600, 300, 180, 120, 60, 30, 10)

def restart_countdown(seconds, why=""):
    """announce, wait, save everything, exit (systemd Restart=always starts the server again)."""
    if RESTART["task"]:
        RESTART["task"].cancel()
    RESTART.update(at=time.time() + seconds, why=why)
    log(f"   RESTART in {seconds} s ({why or 'update'})")
    async def run():
        try:
            while True:
                left = RESTART["at"] - time.time()
                if left <= 0.5:
                    break
                for o in ota_online():
                    ota_say(o, "restart", rgb=(255, 140, 80), t=OTA.fmt_left(left, _mail_lang(o)),
                            why=RESTART["why"] or OTA.text("why", _mail_lang(o)))
                nxt = [m for m in RESTART_MARKS if m < left - 1]
                await asyncio.sleep(left - (nxt[0] if nxt else 0))
            for o in ota_online():
                ota_say(o, "restart_now", rgb=(255, 140, 80))
            await asyncio.sleep(2)
            accounts_flush_now()
            npc_save(True)
            log("   RESTART now (saved)")
            if LOG:
                LOG.flush()
            import signal
            os.kill(os.getpid(), signal.SIGINT)
        except asyncio.CancelledError:
            pass
    RESTART["task"] = asyncio.get_event_loop().create_task(run())

def restart_cancel():
    if RESTART["task"]:
        RESTART["task"].cancel()
        RESTART.update(at=None, task=None)
        for o in ota_online():
            ota_say(o, "cancel", rgb=(120, 255, 120))
        return True
    return False

def version_command(s):
    r = ota_client_release(s) or "?"
    cur = OTA_V.current or "-"
    s.send(chat_line(0x0A, f"client {r} / release {cur} / checksum {getattr(s, 'client_hash', 0):08x}", (120, 220, 255), tr=False))
''')

rep('''def client_hash_report(s, h, ver):
    ok = h in allowed_client_hashes()
    first = not hasattr(s, "client_hash")
    s.client_hash, s.client_ver = h, ver
    if not ok:''', '''def client_hash_report(s, h, ver):
    known = OTA_V.version_of(h)                    # a published release (current or older)
    official = h in allowed_client_hashes()        # the server's own SG_debug.exe build / client_hashes.json
    ok = official or known is not None
    first = not hasattr(s, "client_hash")
    s.client_hash, s.client_ver = h, ver
    s.client_release = known or (OTA_V.current if official else None)
    if ok and first and known is not None:
        pol = OTA_V.policy(known)
        if pol == "blocked":
            log(f"   OTA: {getattr(s, 'acc', s.peer)} runs old release {known} (current {OTA_V.current}) -> must update")
            audit("client_old_blocked", getattr(s, "acc", None), release=known)
            ota_say(s, "blocked", rgb=(255, 80, 80), ver=known, cur=OTA_V.current)
            asyncio.get_event_loop().call_later(3.0, s.w.close)
            return
        if pol == "old":
            asyncio.get_event_loop().call_later(8.0, lambda: ota_say(s, "old", ver=known, cur=OTA_V.current,
                                                                       deadline_ts=OTA_V.deadline()))
    if not ok:''')

# ---- commands --------------------------------------------------------------------------------------------------------------
rep('''    if text.lower() == "/speed" and sub in (0, 3):
        speed_command(s)
        return
''', '''    if text.lower() == "/speed" and sub in (0, 3):
        speed_command(s)
        return
    if text.lower() == "/version" and sub in (0, 3):
        version_command(s)
        return
''')
rep('''        elif parts[0] == "/lag":
            global LOG_PACKETS''', '''        elif parts[0] == "/shutdown":
            # /shutdown MIN [reason] : announce, save, restart (systemd starts it again) ; /shutdown cancel
            if len(parts) > 1 and parts[1] == "cancel":
                ok = restart_cancel()
                s.send(chat_line(0x0A, "restart cancelled" if ok else "no restart pending", (120, 255, 120), tr=False))
                return
            mins = float(parts[1]) if len(parts) > 1 else 5
            restart_countdown(int(mins * 60), " ".join(parts[2:]))
            return
        elif parts[0] == "/lag":
            global LOG_PACKETS''')

# ---- main: update HTTP server + cycle ---------------------------------------------------------------------------------------
rep('''    ap.add_argument("--server-name", default=os.environ.get("SG_SERVER_NAME", ""))
    a = ap.parse_args()''', '''    ap.add_argument("--server-name", default=os.environ.get("SG_SERVER_NAME", ""))
    # OTA (2026-10-22): launcher downloads (0 = off) with a global bandwidth limit in KB/s
    ap.add_argument("--update-port", type=int, default=int(os.environ.get("SG_UPDATE_PORT", "0")))
    ap.add_argument("--update-rate", type=int, default=int(os.environ.get("SG_UPDATE_RATE", "1500")))
    a = ap.parse_args()''')
rep('''    srv = await asyncio.start_server(handle, a.host, a.port)
''', '''    srv = await asyncio.start_server(handle, a.host, a.port)
    if a.update_port:
        global UPDATE_SRV
        UPDATE_SRV = OTA.UpdateServer(UPDATE_DIR, rate_kb=a.update_rate, log=log)
        await UPDATE_SRV.start(a.host, a.update_port)
        log(f"update downloads on {a.host}:{a.update_port} from {os.path.realpath(UPDATE_DIR)} (max {a.update_rate} KB/s)")
''')
rep('''    asyncio.get_event_loop().create_task(lag_monitor())
''', '''    asyncio.get_event_loop().create_task(lag_monitor())
    asyncio.get_event_loop().create_task(ota_cycle())
''')
rep('''RESTART = {"at": None, "why": "", "task": None}
''', '''RESTART = {"at": None, "why": "", "task": None}
UPDATE_SRV = None
''')

open(p, "w", encoding="utf-8").write(t)
print("patched")
