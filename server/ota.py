"""OTA updates for the SGalaxy server (2026-10-22, claude/OTA_PLAN.md).  Python standard library only.

1. A small HTTP/1.1 file server (GET / HEAD, Range, keep-alive) for the launcher downloads, with a GLOBAL bandwidth
   limit so updates never eat the game traffic (the cloud host has 20 Mbps).  It only serves files below the update
   folder; no listing, no other methods.
     updates/
       release.json                 {"version", "min_version", "deadline", "notes": {lang: text}}  (current release)
       manifest-<channel>.json      current manifest of a channel (cn / tw / en) + .sig (RSA signature)
       versions/<ver>/manifest-<channel>.json   every published release (rollback / version table)
       objects/<sha256>             file contents by hash (shared by all versions / channels)
       launcher/GOLauncher.exe      (also an object, named in the manifest; SGLauncher.exe before 2026-11-02)
2. The version table: game-client code checksum (the F16 0xF6 report) -> release version, computed from the client
   exes of every published release, so the server knows which version a player runs."""
import asyncio, json, os, re, time, urllib.parse, gzip, collections
_BOARD_SECRET_RE = re.compile(r"((?:f_)?passwd\d?)=[^&]*")

# ---- versions ---------------------------------------------------------------------------------------------------------
def vtuple(v):
    try:
        return tuple(int(x) for x in str(v).split("."))
    except Exception:
        return (0,)


class Versions:
    """release info + checksum -> version.  reload() is cheap when nothing changed (mtime check)."""

    def __init__(self, root, hash_fn):
        self.root, self.hash_fn = root, hash_fn
        self.release = {}
        self.by_hash = {}          # code checksum -> version
        self.path_by_hash = {}     # code checksum -> client exe object file (F34 challenge answers)
        self._hcache = {}          # object sha256 -> code checksum
        self._stamp = None

    def _stamp_now(self):
        st = []
        for p in (os.path.join(self.root, "release.json"), os.path.join(self.root, "versions")):
            try:
                st.append(os.stat(p).st_mtime_ns)
            except OSError:
                st.append(0)
        return tuple(st)

    def reload(self):
        """True when the release changed."""
        stamp = self._stamp_now()
        if stamp == self._stamp:
            return False
        self._stamp = stamp
        old = self.release.get("version")
        try:
            with open(os.path.join(self.root, "release.json"), encoding="utf-8") as f:
                self.release = json.load(f)
        except Exception:
            self.release = {}
        by, paths = {}, {}
        vdir = os.path.join(self.root, "versions")
        for ver in sorted(os.listdir(vdir) if os.path.isdir(vdir) else [], key=vtuple):
            for fn in os.listdir(os.path.join(vdir, ver)):
                if not (fn.startswith("manifest-") and fn.endswith(".json")):
                    continue
                try:
                    with open(os.path.join(vdir, ver, fn), encoding="utf-8") as f:
                        m = json.load(f)
                except Exception:
                    continue
                for e in m.get("files", []):
                    if not e.get("client"):
                        continue
                    sha = e["sha256"]
                    if sha not in self._hcache:
                        try:
                            self._hcache[sha] = self.hash_fn(os.path.join(self.root, "objects", sha))
                        except Exception:
                            self._hcache[sha] = None
                    if self._hcache[sha] is not None:
                        by[self._hcache[sha]] = ver
                        paths[self._hcache[sha]] = os.path.join(self.root, "objects", sha)
        self.by_hash = by
        self.path_by_hash = paths
        return self.release.get("version") != old

    @property
    def current(self):
        return self.release.get("version")

    def version_of(self, h):
        return self.by_hash.get(h)

    def deadline(self):
        d = self.release.get("deadline")
        return float(d) if d else None

    def policy(self, ver, now=None):
        """'ok' (current or newer) | 'old' (may still play, gets a notice) | 'blocked' (must update)."""
        cur = self.current
        if not cur or ver is None:
            return "ok"
        if vtuple(ver) >= vtuple(cur):
            return "ok"
        mn = self.release.get("min_version")
        if mn and vtuple(ver) < vtuple(mn):
            return "blocked"
        dl = self.deadline()
        if dl and (now or time.time()) >= dl:
            return "blocked"
        return "old"


MSG = {
    "old": {"zh-cn": "有新版本 {cur}（你是 {ver}）。请关闭游戏，重新打开启动器 GOLauncher 自动更新。{dl}",
            "zh-tw": "有新版本 {cur}（你是 {ver}）。請關閉遊戲，重新開啟啟動器 GOLauncher 自動更新。{dl}",
            "en": "New version {cur} is out (you have {ver}). Close the game and start GOLauncher to update. {dl}"},
    "deadline": {"zh-cn": "{t} 之后旧版将无法登录。", "zh-tw": "{t} 之後舊版將無法登入。",
                 "en": "Old versions cannot log in after {t}."},
    "blocked": {"zh-cn": "客户端版本 {ver} 过旧，请用启动器 GOLauncher 更新到 {cur} 后再登录。",
                "zh-tw": "客戶端版本 {ver} 過舊，請用啟動器 GOLauncher 更新到 {cur} 後再登入。",
                "en": "Your client {ver} is too old. Update to {cur} with GOLauncher, then log in again."},
    "released": {"zh-cn": "新版本 {cur} 已发布：{notes}  请在方便时关闭游戏，用启动器更新。",
                 "zh-tw": "新版本 {cur} 已發佈：{notes}  請在方便時關閉遊戲，用啟動器更新。",
                 "en": "Version {cur} released: {notes}  Close the game and update with GOLauncher when convenient."},
    "restart": {"zh-cn": "服务器将在 {t} 后重启维护（{why}），请尽快结束战斗。",
                "zh-tw": "伺服器將在 {t} 後重啟維護（{why}），請盡快結束戰鬥。",
                "en": "The server restarts in {t} ({why}). Please finish your battle."},
    "restart_now": {"zh-cn": "服务器正在重启，约 1 分钟后可重新登录。", "zh-tw": "伺服器正在重啟，約 1 分鐘後可重新登入。",
                    "en": "The server is restarting - log in again in about a minute."},
    "cancel": {"zh-cn": "服务器重启已取消。", "zh-tw": "伺服器重啟已取消。", "en": "Server restart cancelled."},
    "why": {"zh-cn": "版本更新", "zh-tw": "版本更新", "en": "update"},
}


def lang3(lang):
    return lang if lang in ("zh-cn", "zh-tw") else "en"


def fmt_left(sec, lang):
    sec = int(round(sec))
    if sec >= 60:
        m = (sec + 30) // 60
        return {"zh-cn": f"{m} 分钟", "zh-tw": f"{m} 分鐘"}.get(lang, f"{m} min")
    return {"zh-cn": f"{sec} 秒", "zh-tw": f"{sec} 秒"}.get(lang, f"{sec} s")


def text(key, lang, **kw):
    lang = lang3(lang)
    t = MSG[key][lang]
    if key == "old":
        dl = kw.pop("deadline_ts", None)
        kw["dl"] = text("deadline", lang, t=time.strftime("%m-%d %H:%M", time.localtime(dl))) if dl else ""
    if key == "released":
        n = kw.get("notes") or {}
        if isinstance(n, dict):
            kw["notes"] = n.get(lang) or n.get("zh-cn") or n.get("en") or ""
        else:
            kw["notes"] = str(n)
    return t.format(**kw).strip()


# ---- HTTP file server ---------------------------------------------------------------------------------------------------
class Bucket:
    """global token bucket (bytes / s) shared by all downloads."""

    def __init__(self, rate):
        self.rate = max(1, int(rate))
        self.tokens = float(self.rate)
        self.t = time.monotonic()

    async def take(self, n):
        while True:
            now = time.monotonic()
            self.tokens = min(self.rate, self.tokens + (now - self.t) * self.rate)
            self.t = now
            if self.tokens >= n:
                self.tokens -= n
                return
            await asyncio.sleep(max(0.01, (n - self.tokens) / self.rate))


SAFE = re.compile(r"^/[A-Za-z0-9._\-/]{1,200}$")
CHUNK = 32 * 1024
# (2026-11-01) gzip on the wire: a launcher that sends "Accept-Encoding: gzip" (from 1.0.80 on) gets every answer up to
# GZ_MAX bytes compressed when that saves at least 5 %.  The launcher checks the sha256 of the decompressed bytes, so a
# wrong answer cannot be installed.  Older launchers do not ask and get the plain bytes as before.  Compressed ranges are
# kept in a small LRU (many players fetch the same ranges of a new release).
GZ_MAX = 8 << 20
GZ_CACHE_MAX = 96 << 20


class GzCache:
    def __init__(self, cap):
        self.cap, self.size, self.d = cap, 0, collections.OrderedDict()

    def get(self, k):
        v = self.d.get(k)
        if v is not None:
            self.d.move_to_end(k)
        return v

    def put(self, k, v):
        if len(v) > self.cap // 4:
            return
        self.d[k] = v; self.size += len(v)
        while self.size > self.cap and self.d:
            _, o = self.d.popitem(last=False); self.size -= len(o)


def _gz(data):
    z = gzip.compress(data, compresslevel=6, mtime=0)
    return z if len(z) < len(data) * 0.95 else None


class UpdateServer:
    def __init__(self, root, rate_kb=1500, max_conn=64, per_ip=6, log=print, on_manifest=None, board=None):
        self._brate = {}                      # ip -> request times (board flood guard)
        self.board = board                   # (method, path below /b/, query, body, ip) -> (status, bytes)
        self.root = os.path.realpath(root)
        self.on_manifest = on_manifest       # (ip, channel): the launcher of this IP runs in that language
        self.bucket = Bucket(rate_kb * 1024)
        self.max_conn, self.per_ip, self.log = max_conn, per_ip, log
        self.conns = {}
        self.bytes_sent = 0
        self.bytes_saved = 0                 # gzip: bytes not sent
        self.requests = 0
        self.gz = GzCache(GZ_CACHE_MAX)

    async def start(self, host, port):
        os.makedirs(self.root, exist_ok=True)
        return await asyncio.start_server(self.handle, host, port)

    def _path(self, url):
        p = urllib.parse.unquote(urllib.parse.urlsplit(url).path)
        if not SAFE.match(p) or ".." in p or "//" in p:
            return None
        full = os.path.realpath(os.path.join(self.root, p.lstrip("/")))
        if not full.startswith(self.root + os.sep) or not os.path.isfile(full):
            return None
        return full

    async def handle(self, r, w):
        ip = (w.get_extra_info("peername") or ("?",))[0]
        if sum(self.conns.values()) >= self.max_conn or self.conns.get(ip, 0) >= self.per_ip:
            w.close()
            return
        self.conns[ip] = self.conns.get(ip, 0) + 1
        try:
            while True:
                try:
                    head = await asyncio.wait_for(r.readuntil(b"\r\n\r\n"), 20)
                except (asyncio.TimeoutError, asyncio.IncompleteReadError, asyncio.LimitOverrunError, ConnectionError):
                    return
                if len(head) > 8192:
                    return
                lines = head.decode("latin-1").split("\r\n")
                try:
                    method, url, ver = lines[0].split(" ", 2)
                except ValueError:
                    return
                hdr = {}
                for l in lines[1:]:
                    if ":" in l:
                        k, v = l.split(":", 1)
                        hdr[k.strip().lower()] = v.strip()
                keep = hdr.get("connection", "").lower() != "close" and ver == "HTTP/1.1"
                self.requests += 1
                sp = urllib.parse.urlsplit(url)
                if self.board and sp.path.startswith("/b/"):          # board + mail pages for the game client (sgs/board_mail.py)
                    now = time.time()                              # flood guard: 40 requests / 10 s per IP address
                    hist = [t for t in self._brate.get(ip, ()) if now - t < 10]
                    hist.append(now); self._brate[ip] = hist
                    if len(self._brate) > 2000:
                        for k in [k for k, v in self._brate.items() if not v or now - v[-1] > 10]:
                            self._brate.pop(k, None)
                    if len(hist) > 40 or len(url) > 4096:
                        await self._reply(w, 429 if len(hist) > 40 else 414, b"too many requests", keep=False)
                        return
                    body = b""
                    if method == "POST":
                        try:
                            cl = int(hdr.get("content-length", "0") or 0)
                            if not 0 <= cl <= 65536:
                                raise ValueError
                            body = await asyncio.wait_for(r.readexactly(cl), 20) if cl else b""
                        except (ValueError, asyncio.TimeoutError, asyncio.IncompleteReadError):
                            await self._reply(w, 400, b"bad request", keep=False)
                            return
                    elif method not in ("GET", "HEAD"):
                        await self._reply(w, 405, b"method not allowed", keep=False)
                        return
                    try:
                        code, data = self.board(method, sp.path[3:], sp.query, body, ip)
                    except Exception as e:
                        self.log(f"   board request error: {e!r}")
                        code, data = 500, b"error"
                    qlog = _BOARD_SECRET_RE.sub(r"\1=***", sp.query[:200])[:80]      # the client puts the login password in the URL: never log it
                    self.log(f"   board {method} {sp.path} q={qlog!r} body={len(body)}B ip={ip} -> {code} {len(data)}B")
                    w.write((f"HTTP/1.1 {code} {'OK' if code == 200 else 'Error'}\r\nContent-Type: text/html\r\n"
                             f"Content-Length: {len(data)}\r\nCache-Control: no-cache, no-store\r\nPragma: no-cache\r\nExpires: 0\r\n"
                             f"Connection: {'keep-alive' if keep else 'close'}\r\n\r\n").encode() + (data if method != "HEAD" else b""))
                    await w.drain()
                    if not keep:
                        return
                    continue
                if method not in ("GET", "HEAD"):
                    await self._reply(w, 405, b"method not allowed", keep=False)
                    return
                full = self._path(url)
                if full is None:
                    await self._reply(w, 404, b"not found", keep=keep)
                    if not keep:
                        return
                    continue
                mm = re.match(r"^/manifest-(cn|tw|en)\.json$", urllib.parse.urlsplit(url).path)
                if mm and self.on_manifest:
                    try:
                        self.on_manifest(ip, mm.group(1))
                    except Exception:
                        pass
                size = os.path.getsize(full)
                a, b, code = 0, size - 1, 200
                rg = hdr.get("range", "")
                m = re.match(r"bytes=(\d*)-(\d*)$", rg)
                if m and (m.group(1) or m.group(2)):
                    if m.group(1):
                        a = int(m.group(1)); b = int(m.group(2)) if m.group(2) else size - 1
                    else:
                        a = max(0, size - int(m.group(2)))
                    b = min(b, size - 1)
                    if a > b:
                        await self._reply(w, 416, b"", keep=keep, extra=f"Content-Range: bytes */{size}\r\n")
                        continue
                    code = 206
                name = os.path.basename(full)
                cache = "no-cache" if name.startswith(("manifest", "release")) else "public, max-age=31536000, immutable"
                extra = f"Accept-Ranges: bytes\r\nCache-Control: {cache}\r\n"
                if code == 206:
                    extra += f"Content-Range: bytes {a}-{b}/{size}\r\n"
                n = b - a + 1
                body = None
                if method == "GET" and n <= GZ_MAX and "gzip" in hdr.get("accept-encoding", "").lower():
                    key = (full, os.path.getmtime(full), a, b)
                    body = self.gz.get(key)
                    if body is None:
                        with open(full, "rb") as f:
                            f.seek(a)
                            raw = f.read(n)
                        body = await asyncio.get_running_loop().run_in_executor(None, _gz, raw) or b""
                        self.gz.put(key, body)
                    body = body or None              # b"" = not worth it (cached), send the plain bytes
                if body is not None:
                    w.write((f"HTTP/1.1 {code} {'OK' if code == 200 else 'Partial Content'}\r\nContent-Type: application/octet-stream\r\n"
                             f"Content-Encoding: gzip\r\nVary: Accept-Encoding\r\nContent-Length: {len(body)}\r\n{extra}"
                             f"Connection: {'keep-alive' if keep else 'close'}\r\n\r\n").encode())
                    for i in range(0, len(body), CHUNK):
                        part = body[i:i + CHUNK]
                        await self.bucket.take(len(part))
                        w.write(part)
                        await w.drain()
                    self.bytes_sent += len(body); self.bytes_saved += n - len(body)
                    if not keep:
                        return
                    continue
                w.write((f"HTTP/1.1 {code} {'OK' if code == 200 else 'Partial Content'}\r\nContent-Type: application/octet-stream\r\n"
                         f"Content-Length: {n}\r\n{extra}Connection: {'keep-alive' if keep else 'close'}\r\n\r\n").encode())
                if method == "GET":
                    with open(full, "rb") as f:
                        f.seek(a)
                        left = n
                        while left > 0:
                            buf = f.read(min(CHUNK, left))
                            if not buf:
                                break
                            await self.bucket.take(len(buf))
                            w.write(buf)
                            await w.drain()
                            left -= len(buf)
                            self.bytes_sent += len(buf)
                else:
                    await w.drain()
                if not keep:
                    return
        except (ConnectionError, OSError):
            pass
        finally:
            self.conns[ip] -= 1
            if not self.conns[ip]:
                del self.conns[ip]
            try:
                w.close()
            except Exception:
                pass

    async def _reply(self, w, code, body, keep=True, extra=""):
        reason = {400: "Bad Request", 404: "Not Found", 405: "Method Not Allowed", 414: "URI Too Long", 429: "Too Many Requests", 416: "Range Not Satisfiable"}.get(code, "Error")
        w.write((f"HTTP/1.1 {code} {reason}\r\nContent-Length: {len(body)}\r\n{extra}"
                 f"Connection: {'keep-alive' if keep else 'close'}\r\n\r\n").encode() + body)
        await w.drain()
