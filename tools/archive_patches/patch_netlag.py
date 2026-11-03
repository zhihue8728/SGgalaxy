"""patch_netlag (user 2026-10-22 22:47: "client stutters when controlling units, commands are not smooth, units pause a
little while moving").  Server side network latency work:

1. The game client (SG.exe) uses WSAAsyncSelect/send with Windows' default Nagle algorithm (no setsockopt in its import
   table).  A small packet is held until the previous one is ACKed, and a Linux server delays ACKs (up to 40 ms) ->
   every command sent while a position report is unacked waits RTT + 40 ms.  Fix: TCP_QUICKACK re-armed after every
   read (the server ACKs at once), TCP_THIN_LINEAR_TIMEOUTS (thin streams recover from a loss faster), keep-alive.
2. Battle lock-step frames: drift-free schedule every FRAME_MS (50 ms, was sleep(0.1) = 100-115 ms with jitter).
   The client clock is bounded by the newest frame it received, so the cap lags real time by half a frame interval plus
   jitter; and with frames 3x denser the duplicate-ACK loss recovery of TCP starts 3x sooner.  A frame is skipped while
   the connection already has FRAME_BACKLOG bytes queued (a stalled link must not receive a burst of stale frames).
3. Diagnostics: /lag net (per player RTT, RTT variance, retransmits, queued bytes from TCP_INFO), a 10 s monitor that
   logs bad links and GC pauses > 30 ms.  gc.freeze() after start-up keeps full collections short.
"""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else "server/sgserver.py"
src = open(P, encoding="utf-8").read()


def rep(old, new, cnt=1):
    global src
    if new in src:
        return
    n = src.count(old)
    assert n == cnt, (n, old[:90])
    src = src.replace(old, new)


# ---- 1. socket tuning ------------------------------------------------------------------------------------------
rep('''        self.r, self.w = reader, writer
        self.lang, self.enc = "en", "latin-1" ''', '''        self.r, self.w = reader, writer
        self.sock = writer.get_extra_info("socket") if writer is not None else None
        self.lang, self.enc = "en", "latin-1" ''')

rep('''ONLINE = set()        # all connected sessions (strategic map: who is where)
''', '''ONLINE = set()        # all connected sessions (strategic map: who is where)

# ---- NETWORK LATENCY (2026-10-22 22:47, see claude/NETWORK_LATENCY_EVAL.md) --------------------------------------
import socket as _socket
FRAME_MS = 50               # battle lock-step frame interval (was 100 ms)
FRAME_BACKLOG = 16384       # a frame is skipped while this many bytes are already queued for the connection
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
        d = sock.getsockopt(_socket.IPPROTO_TCP, ti, 192)
        u = struct.unpack_from("<23I", d, 8)
        total_retrans = struct.unpack_from("<I", d, 100)[0] if len(d) >= 104 else 0
        return {"rtt": u[15] / 1000.0, "var": u[16] / 1000.0, "unacked": u[4], "lost": u[6], "retrans": u[7],
                "total_retrans": total_retrans, "cwnd": u[18], "queued": s.w.transport.get_write_buffer_size()}
    except Exception:
        return None
''')

rep('''    s = Session(reader, writer)
    ONLINE.add(s)
    log(f"{s.peer} connected")''', '''    s = Session(reader, writer)
    ONLINE.add(s)
    tune_socket(s)
    log(f"{s.peer} connected")''')

rep('''            chunk = await reader.read(65536)
            if not chunk:
                break
''', '''            chunk = await reader.read(65536)
            if not chunk:
                break
            quickack(s)
''')

# ---- 2. battle frames -------------------------------------------------------------------------------------------
rep('''    n = 0
    log(f"   battle frames started (gen {gen})")
    try:
        while getattr(s, "battle_gen", None) == gen and not s.w.is_closing():
            s.send(bytes([0x80, 0, 0]) + struct.pack(">IH", game_time(s), 0), quiet=True)
            n += 1
            if n % 100 == 0:
                log(f"   battle frames: {n} sent, game time {game_time(s)}")
            await asyncio.sleep(0.1)
    except Exception as e:''', '''    n = 0
    log(f"   battle frames started (gen {gen}, every {FRAME_MS} ms)")
    loop = asyncio.get_event_loop()
    nxt = loop.time()
    try:
        while getattr(s, "battle_gen", None) == gen and not s.w.is_closing():
            try:
                backlog = s.w.transport.get_write_buffer_size()
            except Exception:
                backlog = 0
            if backlog <= FRAME_BACKLOG:                 # never queue stale frames behind a stalled link
                s.send(bytes([0x80, 0, 0]) + struct.pack(">IH", game_time(s), 0), quiet=True)
                n += 1
                if n % 500 == 0:
                    log(f"   battle frames: {n} sent, game time {game_time(s)}")
            nxt += FRAME_MS / 1000.0                     # absolute schedule: no drift, no 100-115 ms jitter
            now = loop.time()
            if nxt < now - 0.5:                          # long stall of the loop: do not fire a burst afterwards
                nxt = now
            await asyncio.sleep(max(0.0, nxt - now))
    except Exception as e:''')

# ---- 3. diagnostics ---------------------------------------------------------------------------------------------
rep('''def read_s8(b, off):
    n = b[off]''', '''async def net_monitor():
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
                    log(f"   net {getattr(s, 'acc', s.peer)}: rtt {st['rtt']:.0f}+-{st['var']:.0f} ms, "
                        f"retransmits +{st['total_retrans'] - prev} (total {st['total_retrans']}), unacked {st['unacked']}, "
                        f"queued {st['queued']} B{' (battle)' if getattr(s, 'battle', None) else ''}")
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

def read_s8(b, off):
    n = b[off]''')

rep('''            s.send(chat_line(0x0A, f"lag: max {LAG_STATS['max'] * 1000:.0f} ms, stalls>{LAG_WARN * 1000:.0f}ms: {LAG_STATS['n']}, "''',
    '''            if len(parts) > 1 and parts[1] == "net":
                for o in list(ONLINE):
                    if not getattr(o, "logged_in", False):
                        continue
                    st = tcp_stats(o)
                    s.send(chat_line(0x0A, f"{getattr(o, 'acc', '?')}: " + (
                        f"rtt {st['rtt']:.0f}+-{st['var']:.0f} ms, retransmits {st['total_retrans']}, unacked {st['unacked']}, "
                        f"queued {st['queued']} B" if st else "no TCP_INFO (not Linux)"), (120, 255, 120)))
                s.send(chat_line(0x0A, f"frame {FRAME_MS} ms, gc pauses>30ms {NET_STATS['gc_n']} (max {NET_STATS['gc_max'] * 1000:.0f} ms)",
                                 (120, 255, 120)))
                return
            s.send(chat_line(0x0A, f"lag: max {LAG_STATS['max'] * 1000:.0f} ms, stalls>{LAG_WARN * 1000:.0f}ms: {LAG_STATS['n']}, "''')

rep('''    asyncio.get_event_loop().create_task(lag_monitor())
    asyncio.get_event_loop().create_task(ota_cycle())''', '''    asyncio.get_event_loop().create_task(lag_monitor())
    asyncio.get_event_loop().create_task(net_monitor())
    asyncio.get_event_loop().create_task(ota_cycle())
    _install_gc_probe()''')

open(P, "w", encoding="utf-8").write(src)
print("patched", P)
