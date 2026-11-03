# sgserver part "core_net": network, sessions, logging, accounts cache, rate limits.
# Loaded by sgserver.py into ONE shared namespace (exec, in the order of PARTS) - not an importable module;
# every name here is a sgserver global.  Checks: python tools/check_server.py
import argparse, asyncio, datetime, math, os, random, struct, sys, time, zlib
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from sgproto import Cipher, frame, CLIENT_PLAIN, KEYS, OLD_KEY   # noqa: E402
import sgnet   # noqa: E402  (2026-11-02) the encrypted connection: AES-128-CTR under the game's own packets
import battlefield as BF   # noqa: E402  battle rules: kinds, judge(), constants (claude/BATTLEFIELD_PLAN.md)
from battlefield import (  # noqa: E402
    KILL_RATE_WINDOW, KILL_RATE_MAX, ARMY_BONUS_PER_RATIO, ARMY_BONUS_MAX, PARTICIPATION_BONUS,
    PARTICIPATION_MAX, SNAP_ON, SNAP_PERIOD, SNAP_MAX_BAD, SNAP_FRESH,
    GRENADE_SPLASH, ALIEN_DEATH_FALLBACK, TTK_SAFETY, STEALTH_ACTIONS, NPC_DETECT_R,
    NPC_CLOAK_NEAR, FUTILE_SECONDS, FUTILE_IGNORE, REDEPLOY_WAIT, REDEPLOY_WINDOW,
    VICTORY_XP, VICTORY_KILL_BONUS, CAPTURE_XP, JOIN_XP_BONUS, WOH_XP_BONUS,
    XP_LEVEL_CAP, COMMANDER_BONUS, FACTION_CONTROLLED_BONUS, BATTLE_SECONDS, TAB_POINTS_PER_POC,
    REINFORCE_COOLDOWN, MERCENARY_BONUS_PCT, POC_RADIUS, POC_RATE, POC_TICK,
    NPC_GIVEUP_RATIO, NPC_GIVEUP_AFTER, NPC_GIVEUP_GRACE, NPC_WITHDRAW_MAX, NPC_WAVES_MAX, NPC_WAVE_AT)

LOG = None


LOG_PACKETS = False       # per-packet in/out lines (very slow: console + disk on the single event loop); /logpkt toggles
LAG_WARN = 0.10           # event-loop stalls above this many seconds are logged
LAG_STATS = {"max": 0.0, "n": 0, "last": 0.0, "last_at": 0.0}

def log(msg):
    line = f"{datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]} {msg}"
    print(line)
    if LOG:
        LOG.write(line + "\n")           # buffered; log_flusher() flushes about once a second

def spawn(coro):
    """start a background task on the running loop (one place instead of asyncio.get_event_loop().create_task)."""
    return asyncio.get_event_loop().create_task(coro)

def data_json(name):
    """a data file next to this script (server/NAME), parsed."""
    import json as _j
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), name), encoding="utf-8") as f:
        return _j.load(f)

def plog(msg):
    if LOG_PACKETS:
        log(msg)

LOG_COMBAT = False        # every hit / every relayed lump (hundreds of lines a second in a big battle); /lag combat

def clog(msg):
    if LOG_COMBAT:
        log(msg)


class Session:
    def __init__(self, reader, writer):
        self.r, self.w = reader, writer
        self.sock = writer.get_extra_info("socket") if writer is not None else None
        self.lang, self.enc = "en", "latin-1"        # set from the client's code page (0xF6, set_client_acp)
        self.peer = writer.get_extra_info('peername')
        self.cipher = Cipher()
        self.encrypted_rx = False      # the client encrypts non-plain types always (decided by type), see below
        self.ckey = None               # (11-02) this client's packet key, found from its first encrypted packet
        self.tx = None                 # (11-02) SGX1 stream cipher server -> client (None until the hello: nothing is sent)

    def rx_decode(self, payload):
        """(user 2026-11-02 13:42, packet key @iloveyou) decode a client packet with this connection's key.  Until the key
        is known, sgproto.KEYS are tried in order (new key first); the one whose plain-text checksum matches becomes the
        connection's key, for what the server sends too.  A client switching keys is followed (an old client's packet
        that happens to pass with the new key's checksum - 1 in 256 - is corrected by its next packet)."""
        order = ((self.ckey,) if self.ckey else ()) + tuple(k for k in KEYS if k != self.ckey)
        err = None
        for k in order:
            try:
                body = Cipher.decode(payload, k)
            except ValueError as e:
                err = e
                continue
            if k != self.ckey:
                if self.ckey is not None or k == OLD_KEY:
                    log(f"{self.peer} packet key: {'OLD (client built before F53)' if k == OLD_KEY else 'new'}"
                        + (f" (was {self.ckey!r})" if self.ckey else ""))
                self.ckey = k
                self.cipher.set_key(k)
            return body
        raise err or ValueError("decode")

    # ---- OUTGOING TRAFFIC (user 2026-10-23 14:54: the CVM has a monthly traffic package) ------------------------------
    # Every packet of one event-loop turn goes out in ONE write (TCP_NODELAY would otherwise send one segment of
    # ~54 B TCP/IP header per packet: a battle frame is 9 B of payload).  Same order, same turn, no added delay.
    def _q(self, data, ptype):
        t = TRAFFIC["by"].setdefault(ptype, [0, 0])
        if not (COALESCE and getattr(self, "battle_mode", 0) and getattr(self, "logged_in", False)):
            # 2026-10-23 15:27: the client crashed before the login screen once packets were merged - outside a
            # battle (handshake, server list, login, towns) every packet keeps its own write, as before
            if self.__dict__.get("_ob"):
                self._flush()
            t[0] += 1
            t[1] += len(data)
            self.w.write(self.tx(data) if self.tx else data)
            TRAFFIC["writes"] += 1
            TRAFFIC["wire"] += len(data) + TCP_OVERHEAD
            return
        ob = self.__dict__.setdefault("_ob", [])
        ob.append(data)
        t[0] += 1
        t[1] += len(data)
        if not getattr(self, "_ob_sched", False):
            self._ob_sched = True
            asyncio.get_event_loop().call_soon(self._flush)

    def _flush(self):
        self._ob_sched = False
        ob = self.__dict__.get("_ob")
        if not ob:
            return
        data = b"".join(ob)
        ob.clear()
        if self.w.is_closing():
            return
        self.w.write(self.tx(data) if self.tx else data)
        TRAFFIC["writes"] += 1
        TRAFFIC["wire"] += len(data) + TCP_OVERHEAD * (1 + len(data) // 1400)

    def pending_out(self):
        return sum(len(x) for x in self.__dict__.get("_ob") or ())

    def send_plain(self, payload: bytes):
        self._q(frame(payload), payload[0] if payload else -1)
        if LOG_PACKETS:
            log(f"{self.peer} <- plain  {payload[:48].hex()} ({len(payload)}B)")

    def send(self, payload: bytes, quiet=False):
        """Server->client: types 0,3,0xB,0xC,0xD plain; others encrypted (once the client enabled it)."""
        from sgproto import SERVER_PLAIN
        if self.w.is_closing():
            return                      # disconnected: battle loops may still try to send
        if type(payload) is TextPkt:
            payload = payload.render(self)
        if getattr(self, "lang", "en") != "en":
            payload = UN.localize(payload, self.lang, self.enc)       # Chinese chassis names (unitnames.py)
            payload = NP.zh_bytes(payload, self.lang, self.enc)       # Chinese NPC commander names (npc.py, 2026-10-26)
        if len(payload) == 1 and payload[0] not in SERVER_PLAIN:
            payload = payload + b"\0"   # the client cannot decode a 1-byte encrypted packet (CheckSumError + exit)
        payload = nick_own(payload, getattr(self, "acc", None))
        payload = nick_swap(payload, getattr(self, "enc", "latin-1"))
        if payload[0] not in SERVER_PLAIN and self.ckey is None and not self.__dict__.get("_key_warned"):
            self._key_warned = True            # (11-02) should not happen: the client always encrypts first
            log(f"{self.peer} !! encrypted packet {payload[0]:#04x} before the client's key is known - sent with the new key")
        data = payload if payload[0] in SERVER_PLAIN else self.cipher.encode(payload)
        if payload[0] == 0x80 and len(payload) > 9:
            self.last80 = time.monotonic()      # a lump packet also moves the client's clock: no empty frame needed
        self._q(frame(data), payload[0])
        if not quiet and LOG_PACKETS:
            log(f"{self.peer} <- type={payload[0]:#04x} {payload[:48].hex()} ({len(payload)}B)")


ONLINE = set()        # all connected sessions (strategic map: who is where)
TCP_OVERHEAD = 54     # IPv4 + TCP (timestamps) header bytes per segment
COALESCE = True       # merge the packets of one loop turn into one write - battles only (see Session._q)
TRAFFIC = {"t0": time.time(), "by": {}, "writes": 0, "wire": 0, "frames_skipped": 0}

def traffic_report(top=8):
    el = max(1.0, time.time() - TRAFFIC["t0"])
    by = sorted(TRAFFIC["by"].items(), key=lambda kv: -kv[1][1])
    mb_h = TRAFFIC["wire"] / el * 3600 / 1e6
    lines = [f"out {TRAFFIC['wire'] / 1e6:.1f} MB in {el / 3600:.1f} h = {mb_h:.1f} MB/h "
             f"(~{mb_h * 24 * 30 / 1000:.0f} GB/month), {TRAFFIC['writes']} writes, "
             f"{TRAFFIC['frames_skipped']} empty frames saved, {len(ONLINE)} online"]
    lines.append("top: " + ", ".join(f"{t:#04x} {b / 1e6:.2f}MB/{n}" for t, (n, b) in by[:top]))
    return lines

async def traffic_logger():
    while True:
        await asyncio.sleep(3600)
        for ln in traffic_report():
            log("   TRAFFIC " + ln)

# ---- NETWORK LATENCY (2026-10-22 22:47, see claude/NETWORK_LATENCY_EVAL.md) --------------------------------------
import socket as _socket
FRAME_MS = 33               # battle lock-step frame interval (was 100, then 50 ms; 22:20 -> 33 ms, see FRAME_LEAD)
FRAME_BACKLOG = 16384       # a frame is skipped while this many bytes are already queued for the connection
FRAME_ADAPT = True          # per player frame interval from the link quality (frame_interval)
FRAME_MIN, FRAME_MAX = 33, 100
# (user 2026-10-26 21:08 "the picture freezes, then units teleport") FRAME_MAX was 100 ms - longer than the frame lead
# (60 ms): in "congested" mode every frame came after the client clock had already stopped -> a stop every frame.  The
# frame interval must ALWAYS stay below FRAME_LEAD * 10 ms (the jitter buffer below keeps that true).
_TCP_QUICKACK = getattr(_socket, "TCP_QUICKACK", 12 if sys.platform.startswith("linux") else None)
_TCP_THIN_LINEAR = 16       # Linux TCP_THIN_LINEAR_TIMEOUTS
NET_STATS = {"gc_max": 0.0, "gc_n": 0}

def tune_socket(s):
    """per connection: no Nagle, immediate ACKs, linear retransmit timeouts for thin streams, keep-alive."""
    sock = getattr(s, "sock", None)
    if sock is None:
        return
    def opt(level, name, val):
        try:
            sock.setsockopt(level, name, val)
        except Exception:
            pass
    opt(_socket.IPPROTO_TCP, _socket.TCP_NODELAY, 1)
    opt(_socket.SOL_SOCKET, _socket.SO_KEEPALIVE, 1)
    if sys.platform.startswith("linux"):
        for nm, v in (("TCP_KEEPIDLE", 30), ("TCP_KEEPINTVL", 10), ("TCP_KEEPCNT", 4)):
            if hasattr(_socket, nm):
                opt(_socket.IPPROTO_TCP, getattr(_socket, nm), v)
        opt(_socket.IPPROTO_TCP, _TCP_THIN_LINEAR, 1)
        if hasattr(_socket, "TCP_USER_TIMEOUT"):
            opt(_socket.IPPROTO_TCP, _socket.TCP_USER_TIMEOUT, 30000)
    if _TCP_QUICKACK:
        opt(_socket.IPPROTO_TCP, _TCP_QUICKACK, 1)

def frame_interval(s, now):
    """battle frame interval in ms for this player (see patch_netlag2): re-evaluated once a second."""
    fa = s.__dict__.setdefault("fa", {"ms": FRAME_MS, "t": 0.0, "retr": None, "retr_t": -99.0, "good": 0})
    if not FRAME_ADAPT:
        fa["ms"] = FRAME_MS                      # (/lag net then shows the interval really used)
        return FRAME_MS
    if now - fa["t"] < 1.0:
        return fa["ms"]
    fa["t"] = now
    st = tcp_stats(s)
    if not st:
        return fa["ms"]
    if fa["retr"] is not None and st["total_retrans"] > fa["retr"]:
        fa["retr_t"] = now
    fa["retr"] = st["total_retrans"]
    # a burst (battle entry sends dozens of packets) is not congestion: it must last 3 samples in a row
    # (2026-10-26 21:41 user: "moving and attacking stutter MORE") back to the frame rules that were live before today -
    # the 21:08 experiment (congestion by backlog only, 50 ms frames on lossy links, adaptive lead) is withdrawn.
    fa["cong"] = fa.get("cong", 0) + 1 if (st["queued"] > 4096 or st["unacked"] > 20) else 0
    if fa["cong"] >= 3:
        want = FRAME_MAX
    elif now - fa["retr_t"] < 10 or st["var"] > 40:
        want = FRAME_MIN
    else:
        want = FRAME_MS if len(ONLINE) <= 200 else 50          # (22:20) must stay below FRAME_LEAD ticks
    if want >= fa["ms"]:
        fa["ms"], fa["good"] = want, 0
    else:
        fa["good"] += 1
        if fa["good"] >= 3:
            fa["ms"], fa["good"] = want, 0
    return fa["ms"]

def quickack(s):
    """the kernel leaves quick-ack mode again by itself; asking after each read also sends the ACK that is pending."""
    sock = getattr(s, "sock", None)
    if sock is not None and _TCP_QUICKACK:
        try:
            sock.setsockopt(_socket.IPPROTO_TCP, _TCP_QUICKACK, 1)
        except Exception:
            pass

def tcp_stats(s):
    """Linux TCP_INFO of the player's connection: rtt / rttvar in ms, retransmitted segments, unacked, queued bytes."""
    sock = getattr(s, "sock", None)
    ti = getattr(_socket, "TCP_INFO", None)
    if sock is None or ti is None:
        return None
    try:
        d = sock.getsockopt(_socket.IPPROTO_TCP, ti, 232)
        u = struct.unpack_from("<23I", d, 8)
        total_retrans = struct.unpack_from("<I", d, 100)[0] if len(d) >= 104 else 0
        # (2026-10-26) data segments sent (156) and DSACK duplicates (216 = retransmissions the client already had,
        # i.e. SPURIOUS ones that never stalled anything) - Linux >= 5.x; 0 when the kernel is older
        segs = struct.unpack_from("<I", d, 156)[0] if len(d) >= 160 else 0
        dsack = struct.unpack_from("<I", d, 216)[0] if len(d) >= 220 else 0
        return {"rtt": u[15] / 1000.0, "var": u[16] / 1000.0, "unacked": u[4], "lost": u[6], "retrans": u[7],
                "total_retrans": total_retrans, "cwnd": u[18], "queued": s.w.transport.get_write_buffer_size(),
                "segs": segs, "dsack": dsack, "rto": u[0] / 1000.0}
    except Exception:
        return None

# ---- ANTI-CHEAT: packet rate limits (2026-10-21) -----------------------------------------------------------------
# Measured in sgserver.log: a normal client peaks at ~125 packets in one second (login burst) and ~3.3 KB/s.
RATE_PER_SEC = 400          # packets in one second above this are DROPPED (logged once per second)
RATE_PER_10S = 1500         # packets in 10 s above this -> the connection is CLOSED (flood / bot)
CHAT_PER_10S = 8            # chat lines (0x0a) per 10 s; more are dropped (spam)
RECV_BUF_MAX = 256 * 1024   # an unfinished frame can never be larger than 64 KB + 3
LOGIN_FAIL_MAX, LOGIN_FAIL_WINDOW = 5, 300      # failed logins per IP in 5 minutes -> further attempts refused
LOGIN_FAILS = {}            # ip -> [times]

def rate_check(s, t):
    """returns 'ok', 'drop' or 'kick' for one incoming packet of type t."""
    now = time.time()
    sec = int(now)
    if getattr(s, "rl_sec", None) != sec:
        s.rl_sec, s.rl_n, s.rl_warned = sec, 0, False
    s.rl_n += 1
    w = getattr(s, "rl_win", None)
    if w is None or now - w[0] >= 10:
        w = s.rl_win = [now, 0, 0]
    w[1] += 1
    if t == 0x0A:
        w[2] += 1
    if w[1] > RATE_PER_10S:
        return "kick"
    if s.rl_n > RATE_PER_SEC or (t == 0x0A and w[2] > CHAT_PER_10S):
        if not s.rl_warned:
            s.rl_warned = True
            log(f"   ANTI-CHEAT: rate limit {getattr(s, 'acc', s.peer)}: {s.rl_n}/s, chat {w[2]}/10s -> dropping")
            audit("rate_limit", getattr(s, "acc", None), peer=str(s.peer), per_sec=s.rl_n, chat=w[2], type=t)
        return "drop"
    return "ok"

def login_blocked(ip):
    now = time.time()
    q = [x for x in LOGIN_FAILS.get(ip, []) if now - x < LOGIN_FAIL_WINDOW]
    LOGIN_FAILS[ip] = q
    return len(q) >= LOGIN_FAIL_MAX

# ---- ENCRYPTED CONNECTION (2026-11-02, user "1/2/3都要加密" + "立即只接受加密连线"; protocol in tools/sgnet.py) ------------
# Every connection starts with HELLO = b"SGX1" + the client's X25519 key (the game folder's ddraw.dll sends it right after
# connect); from then on both directions are AES-128-CTR.  Connections without it (old clients) are closed.
# The server's secret key: /opt/sgserver/.netkey (deploy.ps1 copies %USERPROFILE%\.sgota\net_key.json), env SG_NETKEY_FILE.
HELLO_WAIT = 20.0            # seconds a new connection has for its hello
NET_KEY, NET_KEY_FILE = None, None

def net_key():
    global NET_KEY, NET_KEY_FILE
    if NET_KEY is None:
        NET_KEY, NET_KEY_FILE = sgnet.load_server_key()
    return NET_KEY

async def sgx_hello(s, reader):
    """read the relay line (UDP relay on this host) and the SGX1 hello -> (decrypt function, already received bytes,
    decrypted) or None (not an encrypted client: the caller closes it)."""
    buf = b""
    loop = asyncio.get_event_loop()
    end = loop.time() + HELLO_WAIT
    local = (s.peer or ("",))[0] in ("127.0.0.1", "::1")
    while True:
        # UDP RELAY (2026-10-26, server/udp_relay.py): a connection from the relay on this host starts with one line
        # "SGRELAY <player ip> <port>\n" - the player's real address (login limits, board identity, logs); plain text,
        # the player's encrypted stream follows it unchanged
        if local and not getattr(s, "_rly", False) and len(buf) >= 4 and buf[:4] == b"SGRE":
            nl = buf.find(b"\n")
            if nl >= 0 or len(buf) >= 100:
                parts = buf[:nl].split() if nl >= 0 else []
                if len(parts) == 3 and parts[0] == b"SGRELAY":
                    s.peer = (parts[1].decode("ascii", "replace"), int(parts[2]))
                    s.relayed = True
                    log(f"{s.peer} connected through the UDP relay")
                    buf = buf[nl + 1:]
                s._rly = True
                continue
        elif len(buf) >= 4 or (buf and not sgnet.MAGIC.startswith(buf)):
            if buf[:4] != sgnet.MAGIC[:len(buf[:4])]:
                break                                        # not a hello: decided without waiting
            if len(buf) >= sgnet.HELLO_LEN:
                break
        left = end - loop.time()
        if left <= 0:
            log(f"{s.peer} no SGX1 hello in {HELLO_WAIT:.0f} s ({len(buf)} B) -> closed")
            return None
        try:
            chunk = await asyncio.wait_for(reader.read(4096), left)
        except asyncio.TimeoutError:
            continue
        if not chunk:
            return None
        buf += chunk
    hello, rest = buf[:sgnet.HELLO_LEN], buf[sgnet.HELLO_LEN:]
    key = net_key()
    if key is None:
        log(f"!! {s.peer}: no connection key (SG_NETKEY_FILE / /opt/sgserver/.netkey) -> closed")
        return None
    try:
        rx, s.tx = sgnet.server_accept(key, hello)
    except Exception as e:
        log(f"{s.peer} not an encrypted client (first bytes {buf[:16].hex()}: {e}) -> closed")
        audit("plain_client", None, peer=str(s.peer), head=buf[:16].hex())
        return None
    return rx, rx(rest)

async def handle(reader, writer):
    s = Session(reader, writer)
    ONLINE.add(s)
    tune_socket(s)
    log(f"{s.peer} connected")
    buf = b""
    try:
        hs = await sgx_hello(s, reader)
        if hs is None:
            return
        rx, early = hs
        s.send_plain(b"SERVER CONNECTED")
        while True:
            if early is not None:
                chunk, early = early, None               # (what came with the hello, already decrypted)
            else:
                chunk = await reader.read(65536)
                if not chunk:
                    break
                chunk = rx(chunk)
                quickack(s)
                plog(f"{s.peer} -> raw {len(chunk)}B {chunk[:64].hex()}")
            buf += chunk
            if len(buf) > RECV_BUF_MAX:
                log(f"   ANTI-CHEAT: {s.peer} receive buffer {len(buf)} B -> closed")
                audit("buffer_overflow", getattr(s, "acc", None), peer=str(s.peer), size=len(buf))
                break
            while len(buf) >= 3:
                if buf[0] != 0xAA:
                    log(f"{s.peer} !! no 0xAA magic, first bytes {buf[:16].hex()} (text? {buf[:32]!r})")
                    buf = b""; break
                ln = struct.unpack_from(">H", buf, 1)[0]
                if len(buf) < 3 + ln:
                    break
                payload, buf = buf[3:3 + ln], buf[3 + ln:]
                t = payload[0]
                if t in CLIENT_PLAIN:
                    body = payload
                    how = "plain"
                else:
                    try:
                        body = s.rx_decode(payload); how = "decoded"
                    except Exception as e:
                        log(f"{s.peer} !! type={t:#04x} decode failed: {e} raw={payload.hex()}")
                        continue
                plog(f"{s.peer} -> type={body[0]:#04x} ({how}, {len(body)}B) {body.hex()}")
                rc = rate_check(s, body[0])
                if rc == "kick":
                    log(f"   ANTI-CHEAT: {getattr(s, 'acc', s.peer)} sent > {RATE_PER_10S} packets in 10 s -> closed")
                    audit("flood_kick", getattr(s, "acc", None), peer=str(s.peer))
                    raise ConnectionError("flood")
                if rc == "drop":
                    continue
                try:
                    handle_packet(s, body)
                except Exception as e:          # a bad packet must not drop the player's connection
                    import traceback
                    log(f"   !! handler error for type {body[0]:#04x}: {e!r}\n{traceback.format_exc()[-600:]}")
    except (ConnectionError, asyncio.IncompleteReadError):
        pass
    finally:
        ONLINE.discard(s)
        try:
            leave_map(s, "disconnected")
        except Exception as e:
            log(f"   leave_map error: {e!r}")
        s.battle_gen = -1                      # stops battle frame / alien AI loops of this session
        for _t in list(getattr(s, "attacks", {}).values()):      # attack loops / pending skills of this session
            try:
                _t.cancel()
            except Exception:
                pass
        getattr(s, "skill_pending", {}).clear()
        try:
            drop_pending_account(s)
        except Exception as e:
            log(f"   pending account cleanup error: {e!r}")
        log(f"{s.peer} closed")
        writer.close()


def build_server_list(entries):
    """Type 0x46 payload.  entries: [(id, 'a.b.c.d', 'name', 'desc')]
    Decompressed layout (FUN_005A5C50): u8 count, then per entry
      b0 id | b1..b4 = IP bytes d,c,b,a (reversed) | b5 unused | b6 | b7 nation(0 ok when client nation==1) | 'name;desc:' \0
    """
    d = bytearray([len(entries)])
    for eid, ip, name, desc in entries:
        a, b, c, dd = (int(x) for x in ip.split('.'))
        d += bytes([eid, dd, c, b, a, 0, 0, 1]) + f"{name}:".encode('latin-1') + b"\0"   # NO ';' - the client's ';' branch has a null-pointer bug (crash)
    comp = zlib.compress(bytes(d))
    return bytes([0x46]) + struct.pack(">H", len(comp)) + comp


SERVERS = [(1, "127.0.0.1", "Local", "Private test server")]
PUBLIC_IP, PUBLIC_PORT = "127.0.0.1", 3000


def build_redirect(ip, port, name=b""):
    """Server->client type 3 (FUN_00548c50): u32 IP (bytes reversed d,c,b,a), u16 port, u8 n, n bytes."""
    a, b, c, d = (int(x) for x in ip.split('.'))
    return bytes([3, d, c, b, a]) + struct.pack(">H", port) + bytes([len(name)]) + name



import json
import time
ACCOUNTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "accounts.json")

import acctstore as STORE
import ota as OTA          # launcher downloads + version table (claude/OTA_PLAN.md)
DB_FILE = os.environ.get("SG_DB") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "game.db")
_DB = None

def db():
    """the game database (accounts + world / npcs / regiments).  First start: the old JSON files are imported."""
    global _DB
    if _DB is None:
        _DB = STORE.connect(DB_FILE)        # (11-02) encrypted rows; no key -> RuntimeError, the server does not start
        if STORE.CONVERTED.get(DB_FILE):
            print(f"{DB_FILE}: {STORE.CONVERTED[DB_FILE]} plain row(s) encrypted")
        try:
            n = STORE.migrate_json(_DB, ACCOUNTS_FILE)
            if n:
                print(f"accounts.json -> {DB_FILE}: {n} account(s) imported")
            for key, path in (("world", WORLD_FILE), ("npcs", NPC_FILE), ("regiments", REGIMENT_FILE)):
                if STORE.migrate_kv(_DB, key, path):
                    print(f"{os.path.basename(path)} -> {DB_FILE} [{key}]")
        except Exception as e:
            print(f"!! migration error: {e!r}")
    return _DB

_ACC = None            # shared in-memory account table (all code mutates this dict, then calls save_accounts)
_ACC_DIRTY = False
_ACC_FLUSHER = False   # True while accounts_flusher() runs: saves are then written behind, not on the event loop
_ACC_SNAP = {}         # account name -> (marshal bytes, json text) of what is in the database now
_ACC_DV = None         # PRAGMA data_version after our own writes (another program wrote -> reload)

def load_accounts():
    """cached table (game.db).  tools/acct.py may edit the database while the server runs: the flusher notices it
    (data_version) and reloads when no unsaved change waits."""
    global _ACC, _ACC_SNAP, _ACC_DV
    if _ACC is not None:
        return _ACC
    try:
        _ACC = STORE.load_all(db())
    except RuntimeError:
        raise                              # (11-02) cannot decrypt: never run (and save) with an empty table
    except Exception as e:
        print(f"!! load_accounts: {e!r}")
        _ACC = {}
    _ACC_SNAP = {}
    _ACC_DV = STORE.data_version(db())
    try:
        nick_rebuild(_ACC)
    except NameError:
        pass
    return _ACC

def _atomic_json(path, data, indent):
    """write to path.tmp, then rename: a crash / full disk while writing can no longer leave a half-written file."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)

def _acc_changes(snap, old):
    """(changed {name: json}, deleted [names], new snapshot) - only accounts whose content changed are serialized."""
    import marshal
    out, changed = {}, {}
    for k, b in snap.items():
        if k in old and old[k][0] == b:
            out[k] = old[k]
        else:
            out[k] = (b, json.dumps(marshal.loads(b), separators=(",", ":")))
            changed[k] = out[k][1]
    return changed, [k for k in old if k not in snap], out

def _acc_flush_sync():
    global _ACC_DIRTY, _ACC_SNAP, _ACC_DV
    import marshal
    if _ACC is None:
        return
    _ACC_DIRTY = False
    changed, deleted, _ACC_SNAP = _acc_changes({k: marshal.dumps(v) for k, v in _ACC.items()}, dict(_ACC_SNAP))
    STORE.write(db(), changed, deleted)
    _ACC_DV = STORE.data_version(db())

def save_accounts(a):
    global _ACC, _ACC_DIRTY
    if not a and STORE.count_accounts(db()) > 0:
        log("   !! save_accounts: refusing to overwrite the accounts with an EMPTY account table")
        return
    _ACC = a
    _ACC_DIRTY = True
    if not _ACC_FLUSHER:
        _acc_flush_sync()                  # no background task (tests / tools): write through

def accounts_flush_now():
    if _ACC_DIRTY:
        _acc_flush_sync()

async def accounts_flusher():
    """write-behind: every ~2 s, if something changed, snapshot with marshal (fast) and write only the changed accounts
    (one SQLite transaction) in a worker thread, so the event loop (= every player's battle) never waits for the disk."""
    global _ACC_FLUSHER, _ACC_DIRTY, _ACC_SNAP, _ACC, _ACC_DV
    import marshal
    _ACC_FLUSHER = True
    loop = asyncio.get_event_loop()
    while True:
        await asyncio.sleep(2.0)
        try:
            if not _ACC_DIRTY and _ACC is not None and STORE.data_version(db()) != _ACC_DV:
                _ACC = None                        # changed by tools/acct.py -> reload
                load_accounts()
                log("   accounts reloaded (changed outside the server)")
                continue
        except Exception as e:
            log(f"   !! account reload check: {e!r}")
        if not _ACC_DIRTY or _ACC is None:
            continue
        try:
            _ACC_DIRTY = False
            snap = {k: marshal.dumps(v) for k, v in _ACC.items()}
            old = dict(_ACC_SNAP)
            def work():
                changed, deleted, out = _acc_changes(snap, old)
                STORE.write(db(), changed, deleted)
                return out
            _ACC_SNAP = await loop.run_in_executor(None, work)
            _ACC_DV = STORE.data_version(db())
        except Exception as e:
            _ACC_DIRTY = True
            log(f"   !! accounts_flusher error: {e!r}")

async def log_flusher():
    while True:
        await asyncio.sleep(1.0)
        try:
            if LOG:
                LOG.flush()
        except Exception:
            pass

_BEAT = [0.0]

def start_stall_probe():
    """(2026-10-23 22:16) a watchdog THREAD: when the game loop has not beaten for STALL_PROBE_MS, it logs where the
    main thread is (the 3 innermost frames of the server's own code) - once per stall - so the cause of a stall shows
    in the log ("stall at ...")."""
    import threading, traceback
    main_id = threading.main_thread().ident
    def run():
        reported = 0.0
        while True:
            time.sleep(0.02)
            beat = _BEAT[0]
            if not beat or time.monotonic() - beat < 0.15 or reported == beat:
                continue
            reported = beat
            fr = sys._current_frames().get(main_id)
            if fr is None:
                continue
            st = [f for f in traceback.extract_stack(fr)
                  if not any(x in f.filename.replace("\\", "/") for x in ("/asyncio/", "selectors.py", "threading.py"))]
            where = " <- ".join(f"{os.path.basename(f.filename)}:{f.lineno} {f.name}" for f in reversed(st[-4:]))
            try:
                log(f"   !! stall at {where}")
            except Exception:
                pass
    threading.Thread(target=run, daemon=True, name="stall-probe").start()

# ---- ADAPTIVE JITTER BUFFER (user 2026-10-26 21:08: "controlling units, the picture freezes and then they teleport") ----
# The client's battle clock runs in real time but never past the time of the last 0x80 frame it received; when frames
# arrive late it STOPS, and when the late frames come it runs the missed ticks at once (units jump).  Frames are stamped
# FRAME_LEAD ticks ahead, so a delay shorter than the lead is invisible.  Log of the user's link (21:05-21:08): rtt
# 210-230 ms +-20, and in battle 12-18 TCP retransmissions per 10 s (~5 % of the 30 segments/s); outside battles 1-3.
# Every lost segment holds back everything behind it until the copy arrives (~1 rtt later) - with a 60 ms lead that is a
# freeze of ~200 ms, about 1.5 times a second.  The server event loop was fine (4 stalls > 100 ms in 7 hours).
# So the lead now follows the worst link in a battle, once a second:
#   lead = frame interval + 2.5 x rtt variance (+ JB_LOSS_MS when the link really loses segments), JB_LEAD_MIN..MAX ticks
#   RELAY_DELAY (order delay) = lead + 1 - every order still executes after every frame already sent (lock-step rule)
# A larger lead costs reaction time (order -> action = rtt + RELAY_DELAY): the cap JB_LEAD_MAX keeps it at most +80 ms
# over the old fixed 7.  Raising takes effect at once; lowering goes 1 tick per second (frame times never go back), and
# the order delay follows 2 s later.  GM: /lag auto on|off, /lag leadmax N; /lag lead N or /lag delay N = manual (auto off).
# !! (2026-10-26 21:40, client clock reverse engineered - claude/CLIENT_CLOCK.md) the premise above is WRONG for this
# client: empty 0x80 frames never touch its clock (the frame time is stored at +0x29be4 and never read); the clock is
# steered only by ORDER lumps (00548f00), relative to their own time.  Raising lead and order delay together only shifts
# every time stamp and the client re-centres on it, so the "jitter buffer" changes nothing but adds transients -> OFF by
# default.  The sampling (loss / spurious statistics for the net log, lossy-link frame interval) keeps running.
# The freeze + teleport itself is fixed in the client (F36: a late order no longer pushes the clock back).
JB_AUTO = False
JB_LEAD_MIN, JB_LEAD_MAX = 6, 15           # ticks (1/100 s)
JB_LOSSY_RATE = 0.4                        # real (not spurious) retransmissions per second that make a link "lossy"
JB_LOSS_MS = 100                           # extra buffer on a lossy link
JB_STATE = {"hist": [], "want": 0, "who": None, "changes": 0}

def jb_sample(s, st, now):
    """remember (time, retransmissions, data segments, spurious) of this link for 10 s; returns (rate/s, loss share)"""
    jb = s.__dict__.setdefault("jb", {"r": [], "rate": 0.0, "loss": 0.0})
    r = jb["r"]
    r.append((now, st["total_retrans"], st.get("segs", 0), st.get("dsack", 0)))
    while len(r) > 2 and now - r[0][0] > 10.5:
        r.pop(0)
    if len(r) >= 2:
        dt = max(1.0, r[-1][0] - r[0][0])
        real = max(0, (r[-1][1] - r[0][1]) - (r[-1][3] - r[0][3]))
        segs = max(1, r[-1][2] - r[0][2])
        jb["rate"], jb["loss"] = real / dt, real / segs
    return jb["rate"], jb["loss"]

def jb_lossy(s):
    return (s.__dict__.get("jb") or {}).get("rate", 0.0) >= JB_LOSSY_RATE

def jb_want(s, st):
    fi = (s.__dict__.get("fa") or {}).get("ms", FRAME_MS)
    ms = fi + 2.5 * st["var"] + (JB_LOSS_MS if jb_lossy(s) else 0)
    return max(JB_LEAD_MIN, min(JB_LEAD_MAX, int(math.ceil(ms / 10.0))))

def jb_update(now=None):
    """one step of the jitter buffer (every second): sets FRAME_LEAD / RELAY_DELAY for all battles."""
    global FRAME_LEAD, RELAY_DELAY
    now = time.monotonic() if now is None else now
    want, who = JB_LEAD_MIN, None
    for o in list(ONLINE):
        if not (getattr(o, "logged_in", False) and getattr(o, "battle_mode", 0)):
            continue
        st = tcp_stats(o)
        if not st:
            continue
        jb_sample(o, st, now)
        w = jb_want(o, st)
        if w > want:
            want, who = w, getattr(o, "acc", None)
    JB_STATE["want"], JB_STATE["who"] = want, who
    if not JB_AUTO:
        return
    old = FRAME_LEAD
    new = want if want > FRAME_LEAD else max(want, FRAME_LEAD - 1)
    hist = JB_STATE["hist"]
    hist.append(new)
    del hist[:-3]
    RELAY_DELAY = max(max(hist), new) + 1          # set before the lead: an order is always stamped after any frame
    FRAME_LEAD = new
    if new != old:
        JB_STATE["changes"] += 1
        log(f"   jitter buffer: lead {old} -> {new} ticks, order delay {RELAY_DELAY} (worst link {who})")

async def jitter_buffer_loop():
    while True:
        await asyncio.sleep(1.0)
        try:
            jb_update()
        except Exception as e:
            log(f"   jitter buffer error: {e!r}")

async def lag_monitor():
    """event-loop stall detector: sleeps 50 ms and measures how late it wakes up."""
    try:
        start_stall_probe()
    except Exception as e:
        log(f"   stall probe unavailable: {e!r}")
    while True:
        _BEAT[0] = time.monotonic()
        t0 = time.monotonic()
        await asyncio.sleep(0.05)
        d = time.monotonic() - t0 - 0.05
        if d > LAG_STATS["max"]:
            LAG_STATS["max"] = d
        if d > LAG_WARN:
            LAG_STATS["n"] += 1; LAG_STATS["last"] = d; LAG_STATS["last_at"] = time.time()
            log(f"   !! event loop stalled {d * 1000:.0f} ms")

async def net_monitor():
    """every 10 s: log players whose link is bad (rtt variance, retransmits, queued bytes) and GC pauses."""
    last_retr = {}
    while True:
        await asyncio.sleep(10.0)
        try:
            for s in list(ONLINE):
                if not getattr(s, "logged_in", False):
                    continue
                st = tcp_stats(s)
                if not st:
                    continue
                prev = last_retr.get(id(s), st["total_retrans"])
                last_retr[id(s)] = st["total_retrans"]
                if st["total_retrans"] > prev or st["var"] > 60 or st["queued"] > 32768:
                    jb = s.__dict__.get("jb") or {}
                    log(f"   net {getattr(s, 'acc', s.peer)}: rtt {st['rtt']:.0f}+-{st['var']:.0f} ms, "
                        f"retransmits +{st['total_retrans'] - prev} (total {st['total_retrans']}, spurious {st.get('dsack', 0)}), "
                        f"loss {jb.get('loss', 0) * 100:.1f}% {jb.get('rate', 0):.1f}/s, unacked {st['unacked']}, "
                        f"queued {st['queued']} B, frame {(s.__dict__.get('fa') or {}).get('ms', FRAME_MS)} ms, "
                        f"lead {FRAME_LEAD}{' (battle)' if getattr(s, 'battle', None) else ''}")
                lt = s.__dict__.get("late")             # F47 late-command reports (rollbacks) since the last line
                if lt and lt["n"] > lt.get("rep_n", 0):
                    dn = lt["n"] - lt.get("rep_n", 0)
                    log(f"   net {getattr(s, 'acc', s.peer)}: {dn} late command(s) / rollback(s) in 10 s "
                        f"(total {lt['n']}, avg {lt['sum'] / max(1, lt['n']):.0f} ms, max {lt['max']} ms)")
                    lt["rep_n"] = lt["n"]
            alive = {id(s) for s in ONLINE}
            for k in [k for k in last_retr if k not in alive]:
                last_retr.pop(k, None)
        except Exception as e:
            log(f"   net monitor error: {e!r}")

def _install_gc_probe():
    import gc
    t0 = [0.0]
    def cb(phase, info):
        if phase == "start":
            t0[0] = time.perf_counter()
        else:
            d = time.perf_counter() - t0[0]
            if d > NET_STATS["gc_max"]:
                NET_STATS["gc_max"] = d
            if d > 0.03:
                NET_STATS["gc_n"] += 1
                log(f"   !! GC pause {d * 1000:.0f} ms (generation {info.get('generation')})")
    gc.callbacks.append(cb)
    gc.collect()
    gc.freeze()                       # everything loaded so far is never scanned again by full collections
    gc.set_threshold(20000, 20, 50)

def gc_idle():
    """(ARCH_REVIEW A3) collect the young generations right after the NPC tick, every NPC_TICK s: they stay small, so
    the automatic collection does not hit in the middle of a battle frame (06:21 log: a 114 ms generation-1 pause)."""
    import gc
    gc.collect(1)

def read_s8(b, off):
    n = b[off]
    return b[off + 1:off + 1 + n].decode("latin-1"), off + 1 + n
