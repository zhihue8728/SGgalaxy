# sgserver part "client_ota": client checksum, OTA, restart, backups.
# Loaded by sgserver.py into ONE shared namespace (exec, in the order of PARTS) - not an importable module;
# every name here is a sgserver global.  Checks: python tools/check_server.py
# ---- ANTI-CHEAT: client code checksum (2026-10-21, patch F16 tools/patch_sg_debug_f16.py) -----------------------
# After every keep-alive (0x58, every 5 s) the patched client sends 0xF6 [u32 checksum of its CODE IN MEMORY
# (.text + the .dbgmov patch section)][u32 patch version].  The server computes the same checksum from the official
# client file(s) below (+ server/client_hashes.json, a JSON list of extra allowed values).
#   CLIENT_HASH_MODE "log"     : only audit (first test: check audit.log says client_hash_ok)
#                    "enforce" : wrong checksum, or none CLIENT_HASH_GRACE s after login -> disconnected
# NOTE: this stops casual patching / memory editing of the code; a determined cheater who also patches the checksum
# routine can still fake it - it is a deterrent, the server-side checks (steps 1-5) are the real protection.
CLIENT_HASH_MODE = "enforce"   # 2026-10-21 22:45: client checksum e9a436bc matched the server value in game
CLIENT_HASH_GRACE = 30
_SRV_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_EXE_FILES = [os.path.join(_SRV_DIR, "..", "SG_debug.exe")]
CLIENT_HASH_FILE = os.path.join(_SRV_DIR, "client_hashes.json")

def client_code_hash(path):
    """same formula as the client patch F16: h = rol(h, 5) ^ dword over .text (virtual size) then .dbgmov."""
    d = open(path, "rb").read()
    pe = struct.unpack_from("<I", d, 0x3C)[0]
    n = struct.unpack_from("<H", d, pe + 6)[0]
    opt = struct.unpack_from("<H", d, pe + 20)[0]
    secs = {}
    for i in range(n):
        name, vs, va, rs, ra = struct.unpack_from("<8sIIII", d, pe + 24 + opt + 40 * i)
        secs[name.rstrip(b"\0")] = (vs, ra, rs)
    if b".text" not in secs or b".dbgmov" not in secs:
        return None
    h = 0
    for nm, size in ((b".text", 0x928EF * 4), (b".dbgmov", 0x800 * 4)):
        vs, ra, rs = secs[nm]
        blob = d[ra:ra + min(size, rs)].ljust(size, b"\0")
        for (w,) in struct.iter_unpack("<I", blob):
            h = (((h << 5) | (h >> 27)) & 0xFFFFFFFF) ^ w
    return h

_ALLOWED_HASHES = {"t": 0, "v": set()}

# ---- OTA (2026-10-22): which release a client runs (its code checksum -> updates/versions/*), old-version notice,
#      blocked after the deadline / below min_version, release broadcast, countdown restart (claude/OTA_PLAN.md)
UPDATE_DIR = os.environ.get("SG_UPDATE_DIR") or os.path.join(_SRV_DIR, "..", "updates")
_CODE_HASH_CACHE = os.path.join(UPDATE_DIR, "code_hash_cache.json")

def cached_code_hash(path):
    """client_code_hash of an update object, remembered by its file name (= sha256 of the content)."""
    key = os.path.basename(path)
    try:
        cache = json.load(open(_CODE_HASH_CACHE))
    except Exception:
        cache = {}
    if key in cache:
        return cache[key]
    h = client_code_hash(path)
    cache[key] = h
    try:
        tmp = _CODE_HASH_CACHE + ".tmp"
        json.dump(cache, open(tmp, "w"))
        os.replace(tmp, _CODE_HASH_CACHE)
    except Exception:
        pass
    return h

OTA_V = OTA.Versions(UPDATE_DIR, cached_code_hash)
RESTART_FILE = os.path.join(_SRV_DIR, "restart_request.json")    # written by deploy (-Countdown N)
RESTART = {"at": None, "why": "", "task": None}
UPDATE_SRV = None

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
        await asyncio.get_event_loop().run_in_executor(None, OTA_V.reload)     # not in the game loop (hashing)
    except Exception as e:
        log(f"   OTA reload error: {e!r}")
    if OTA_V.current:
        log(f"   OTA: release {OTA_V.current}, {len(OTA_V.by_hash)} known client build(s)")
    while True:
        await asyncio.sleep(15)
        try:
            if await asyncio.get_event_loop().run_in_executor(None, OTA_V.reload):
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
    RESTART["task"] = spawn(run())

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
    s.send(chat_line(0x0A, f"client {r} / release {cur}", (120, 220, 255)))   # (F34) the checksum is not shown; translated

_EXE_HASH = {}                 # path -> (mtime, size, hash)

def _exe_hash(f):
    """(2026-10-23 22:38: the stall every 65 s was this - hashing the 2.8 MB client exe in the game loop every
    minute, 110-160 ms) the code checksum of a client exe, recomputed only when the file changed."""
    st = os.stat(f)
    k = (st.st_mtime, st.st_size)
    hit = _EXE_HASH.get(f)
    if hit and hit[0] == k:
        return hit[1]
    h = client_code_hash(f)
    _EXE_HASH[f] = (k, h)
    return h

def allowed_client_hashes():
    if time.time() - _ALLOWED_HASHES["t"] > 60:            # re-read every minute (new client build / json edit)
        v = set()
        for f in CLIENT_EXE_FILES:
            try:
                h = _exe_hash(f)
                if h is not None:
                    v.add(h)
            except OSError:
                pass
        try:
            v |= {int(x, 16) if isinstance(x, str) else int(x) for x in json.load(open(CLIENT_HASH_FILE))}
        except Exception:
            pass
        _ALLOWED_HASHES.update(t=time.time(), v=v)
    return _ALLOWED_HASHES["v"]

LANG_NAMES = {"zh-tw": "繁體中文 (/lang en = English)", "zh-cn": "简体中文 (/lang en = English)", "en": "English (/lang zh = 中文)"}

def set_client_acp(s, acp):
    """the client's Windows code page decides the text encoding (950 Big5 / 936 GBK) and the default language;
    an account can override the language with /lang en|zh (a["lang"])."""
    if getattr(s, "acp", None) == acp:
        return
    s.acp = acp
    s.enc = I18N.codec(acp)
    try:
        LAST_ACP_BY_IP[(getattr(s, "peer", None) or ("",))[0]] = acp
    except Exception:
        pass
    want = None
    try:
        want = get_account(getattr(s, "acc", None))[1].get("lang")
    except Exception:
        pass
    auto = I18N.lang_of_acp(acp)
    s.lang = "en" if want == "en" else auto
    log(f"   client code page {acp} -> text encoding {s.enc}, language {s.lang}")
    try:                                   # remember it: the next login builds the item names in this language
        accs, a = get_account(getattr(s, "acc", None))
        if a is not None and a.get("acp") != acp:
            a["acp"] = acp; accs[s.acc] = a; save_accounts(accs)
    except Exception:
        pass
    if s.lang != "en":
        s.send(chat_line(0x0A, f"Language: {LANG_NAMES.get(s.lang, s.lang)}", (120, 220, 255)))
    if getattr(s, "logged_in", False) and getattr(s, "nations_lang", s.lang) != s.lang:
        log(f"   nation table resent in {s.lang} (sent in {s.nations_lang} before the code page was known)")
        try:                               # no commander yet = New-commander screen: no 'Neutral' entry there
            has_cmd = "commander" in (get_account(s.acc)[1] or {})
        except Exception:
            has_cmd = True
        s.send(build_nations(neutral=has_cmd, s=s))

def client_hash_kick(s, why):
    log(f"   ANTI-CHEAT: client check failed for {getattr(s, 'acc', s.peer)}: {why}")
    audit("client_hash_bad", getattr(s, "acc", None), peer=str(s.peer), why=why, mode=CLIENT_HASH_MODE)
    if CLIENT_HASH_MODE == "enforce":
        try:
            s.send(chat_line(0x0A, "Unsupported or modified game client - please reinstall the official client.", (255, 80, 80)))
        except Exception:
            pass
        asyncio.get_event_loop().call_later(1.0, s.w.close)

def client_hash_report(s, h, ver):
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
    if not ok:
        if getattr(s, "client_hash_warned", None) != h:
            s.client_hash_warned = h
            client_hash_kick(s, f"checksum {h:08x} (patch v{ver:#x}) not in {[f'{x:08x}' for x in allowed_client_hashes()]}")
    elif first:
        log(f"   client code checksum {h:08x} OK ({getattr(s, 'acc', s.peer)})")
        audit("client_hash_ok", getattr(s, "acc", None), hash=f"{h:08x}", ver=ver)
    if ok and getattr(s, "logged_in", False):
        try:
            challenge_start(s)                       # (F34) random code questions from now on
        except Exception as e:
            log(f"   challenge start error: {e!r}")

# ---- F34 CHALLENGE (user 2026-10-25 20:35): the 0xF6 checksum above is a constant a modified client can simply
# replay.  The server now asks: class 0xF7 [u32 nonce][u32 start dword][u32 count] -> the client (patch F34, hook at
# 0054a1d0) answers 0xF8 [u32 nonce][u32 h]: h = nonce, then rol5/xor over its .text dwords [start, start+count)
# (clamped to the .text size, count 0 = to the end) and over the whole .dbgmov.  The server computes the same from the
# exe file of the release the client claims (by its 0xF6 checksum).  Nonce and range are random each time, so the
# answer cannot be recorded and replayed - a cheater has to keep an untouched copy of the code and hash it himself.
# Builds with the F34 stub carry the marker "SGCH34" (the server asks them); an older build is only asked when
# CHALLENGE_ALL (or it is blocked by the OTA minimum version anyway - publish 1.0.27 with -Min 1.0.27).
CHALLENGE_MODE = "enforce"          # "log" = only audit, "enforce" = wrong / missing answer -> disconnected
CHALLENGE_ALL = False               # True: every client must answer, whatever release it claims
CHALLENGE_FIRST = (8, 20)           # s after the first 0xF6 report: first question
CHALLENGE_EVERY = (45, 150)         # s between two questions
CHALLENGE_TIMEOUT = 25              # s to answer
CHALLENGE_COUNT = (0x4000, 0x20000) # dwords hashed per question (the .text has 0x928EF)
_TEXT_DW, _DBG_DW = 0x928EF, 0x800
_EXE_IMG = {}                       # path -> (mtime, text bytes, dbgmov bytes, capable)

def _exe_image(path):
    st = os.stat(path)
    hit = _EXE_IMG.get(path)
    if hit and hit[0] == st.st_mtime:
        return hit
    d = open(path, "rb").read()
    pe = struct.unpack_from("<I", d, 0x3C)[0]
    n = struct.unpack_from("<H", d, pe + 6)[0]
    opt = struct.unpack_from("<H", d, pe + 20)[0]
    secs = {}
    for i in range(n):
        name, vs, va, rs, ra = struct.unpack_from("<8sIIII", d, pe + 24 + opt + 40 * i)
        secs[name.rstrip(b"\0")] = (ra, rs)
    ra, rs = secs[b".text"]
    text = d[ra:ra + min(_TEXT_DW * 4, rs)].ljust(_TEXT_DW * 4, b"\0")
    ra, rs = secs[b".dbgmov"]
    dbg = d[ra:ra + min(_DBG_DW * 4, rs)].ljust(_DBG_DW * 4, b"\0")
    hit = (st.st_mtime, text, dbg, b"SGCH34" in dbg)
    _EXE_IMG[path] = hit
    return hit

def challenge_answer(path, nonce, start, count):
    """the answer a genuine client of exe `path` gives to 0xF7 (same clamping as the client stub)."""
    _m, text, dbg, _cap = _exe_image(path)
    if start >= _TEXT_DW:
        start = 0
    room = _TEXT_DW - start
    if count == 0 or count > room:
        count = room
    h = nonce & 0xFFFFFFFF
    for (w,) in struct.iter_unpack("<I", text[start * 4:(start + count) * 4]):
        h = (((h << 5) | (h >> 27)) & 0xFFFFFFFF) ^ w
    for (w,) in struct.iter_unpack("<I", dbg):
        h = (((h << 5) | (h >> 27)) & 0xFFFFFFFF) ^ w
    return h

def client_exe_for(h):
    """the exe file of the client build with static checksum h (a published release, or the server's own build)."""
    p = OTA_V.path_by_hash.get(h) if hasattr(OTA_V, "path_by_hash") else None
    if p and os.path.exists(p):
        return p
    for f in CLIENT_EXE_FILES:
        try:
            if _exe_hash(f) == h:
                return f
        except OSError:
            pass
    return None

def challenge_start(s):
    """after the first accepted 0xF6: question the client now and then, for as long as it is connected."""
    if getattr(s, "chal_task", None) is not None:
        return
    path = client_exe_for(getattr(s, "client_hash", None))
    try:
        capable = bool(path) and _exe_image(path)[3]
    except Exception:
        capable = False
    if not capable and not CHALLENGE_ALL:
        return
    s.chal_exe = path

    async def loop():
        import random as _r
        await asyncio.sleep(_r.uniform(*CHALLENGE_FIRST))
        while not s.w.is_closing():
            nonce = _r.getrandbits(32)
            start = _r.randrange(0, _TEXT_DW - 0x100)
            count = _r.randint(*CHALLENGE_COUNT)
            exp = None
            if s.chal_exe:
                try:
                    exp = await asyncio.get_event_loop().run_in_executor(None, challenge_answer, s.chal_exe, nonce, start, count)
                except Exception as e:
                    log(f"   challenge: answer for {getattr(s, 'acc', '?')} not computable: {e!r}")
            s.chal = {"nonce": nonce, "exp": exp, "t": time.time()}
            s.send(bytes([0xF7]) + struct.pack(">III", nonce, start, count), quiet=True)
            await asyncio.sleep(CHALLENGE_TIMEOUT)
            if s.w.is_closing():
                return
            if getattr(s, "chal", None) and s.chal.get("nonce") == nonce:
                challenge_fail(s, f"no answer to the code challenge within {CHALLENGE_TIMEOUT}s")
                if CHALLENGE_MODE == "enforce":
                    return
            await asyncio.sleep(_r.uniform(*CHALLENGE_EVERY))
    s.chal_task = spawn(loop())

def challenge_fail(s, why):
    log(f"   ANTI-CHEAT: code challenge failed for {getattr(s, 'acc', s.peer)}: {why}")
    audit("client_challenge_bad", getattr(s, "acc", None), peer=str(s.peer), why=why, mode=CHALLENGE_MODE)
    if CHALLENGE_MODE == "enforce":
        try:
            s.send(chat_line(0x0A, "Unsupported or modified game client - please reinstall the official client.", (255, 80, 80)))
        except Exception:
            pass
        asyncio.get_event_loop().call_later(1.0, s.w.close)

def challenge_reply(s, nonce, h):
    """client 0xF8 [u32 nonce][u32 answer]."""
    c = getattr(s, "chal", None)
    if not c or c.get("nonce") != nonce:
        audit("client_challenge_stray", getattr(s, "acc", None), nonce=f"{nonce:08x}")
        return
    s.chal = None
    if c.get("exp") is None:
        return                                       # no exe to compare with (logged when asked)
    if h != c["exp"]:
        challenge_fail(s, f"wrong answer {h:08x} (expected {c['exp']:08x})")
        return
    s.chal_ok = getattr(s, "chal_ok", 0) + 1
    if s.chal_ok == 1:
        log(f"   code challenge passed ({getattr(s, 'acc', s.peer)}, {time.time() - c['t']:.1f}s)")

def client_hash_watch(s):
    """called at login: no checksum report within CLIENT_HASH_GRACE s = old / unpatched / modified client."""
    async def w():
        await asyncio.sleep(CLIENT_HASH_GRACE)
        if not s.w.is_closing() and getattr(s, "logged_in", False) and not hasattr(s, "client_hash"):
            client_hash_kick(s, f"no 0xF6 checksum within {CLIENT_HASH_GRACE}s (old or unpatched client)")
    spawn(w())

# ---- daily backups (2026-10-21) -----------------------------------------------------------------------------------
BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backups")
BACKUP_EVERY = 24 * 3600     # seconds (also one backup at every server start)
BACKUP_KEEP_DAYS = 14        # older backup folders are deleted

def make_backup(why="daily"):
    import shutil
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    d = os.path.join(BACKUP_DIR, stamp)
    os.makedirs(d, exist_ok=True)
    n = 0
    accounts_flush_now()
    try:
        STORE.backup_to(db(), os.path.join(d, "game.db")); n += 1      # consistent copy of the live database
    except Exception as e:
        log(f"   !! database backup failed: {e!r}")
    for f in (GM_ACCOUNTS_FILE,):
        if os.path.exists(f):
            shutil.copy2(f, d); n += 1
    cut = time.time() - BACKUP_KEEP_DAYS * 86400
    for old in os.listdir(BACKUP_DIR):
        p = os.path.join(BACKUP_DIR, old)
        if os.path.isdir(p) and os.path.getmtime(p) < cut:
            shutil.rmtree(p, ignore_errors=True)
    log(f"   backup ({why}): {n} file(s) -> {d}")

async def backup_cycle():
    while True:
        try:
            make_backup("server start" if not getattr(backup_cycle, "ran", False) else "daily")
        except Exception as e:
            log(f"   !! backup failed: {e!r}")
        backup_cycle.ran = True
        await asyncio.sleep(BACKUP_EVERY)
