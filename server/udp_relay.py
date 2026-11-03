"""UDP RELAY (2026-10-26, claude/UDP_RELAY.md): the game's TCP stream carried over UDP between the player's PC
(launcher/SGRelay.exe, listens on 127.0.0.1:3000) and this server (UDP RELAY_PORT -> TCP 127.0.0.1:<game port>).

Why: TCP waits for every lost segment (~1.25 rtt) and everything behind it waits too; the battle client then gets
orders late and rolls the battle back ("freeze + snap back", claude/CLIENT_CLOCK.md).  Here every datagram with new
bytes is sent TWICE (again after DUP_DELAY), a gap the receiver sees is re-sent at once (duplicate ACKs), and only when
both copies are lost the RTO (about 1.2 rtt) applies.  With 5 % independent loss a byte is late only with ~0.25 %.

Datagram  = [ 'S' 'R' ][u8 ver=1][u8 type][u64 session id]  + body          (big-endian)
  HELLO 1 (c->s)   body []                -> HELLO_OK 2 once the server's TCP to the game is open
  DATA  3          body [u32 ack][u32 seq][u16 n][n bytes]   seq = stream offset of the first byte, ack = next byte wanted
  ACK   4          body [u32 ack][u8 gap]  gap = 1 while the receiver holds bytes beyond a hole (sender re-sends at once)
  FIN   5          body [u32 final offset]  the sender's TCP side closed after this many bytes
  PING  6 / PONG 7 body [u32 echo]          keep-alive (NAT mapping) + probe of the launcher
  RST   8          body []                  unknown / dropped session
The session id (random 64 bit, chosen by the client) is the only identifier: the client's address may change
(NAT rebinding, carrier NAT) - the server follows the latest address of a valid session.
The server's TCP connection to the game first sends one line  b"SGRELAY <client ip> <client port>\\n"  so the game
server sees the player's real address (core_net.handle accepts it from 127.0.0.1 only)."""
import asyncio, os, random, struct, time

MAGIC, VER = b"SR", 1
T_HELLO, T_HELLO_OK, T_DATA, T_ACK, T_FIN, T_PING, T_PONG, T_RST = 1, 2, 3, 4, 5, 6, 7, 8
HDR = struct.Struct(">2sBBQ")
DATA_H = struct.Struct(">IIH")
U32 = struct.Struct(">I")
MAX_CHUNK = 1150            # payload bytes per datagram (stays below a 1280-byte path MTU)
DUP_DELAY = 0.020           # the second copy of new bytes
DUP3_DELAY = 0.060          # a third copy of SMALL new data (< DUP3_MAX bytes): frames / orders, cheap
DUP3_MAX = 300
RTO_MIN, RTO_MAX = 0.08, 1.5
TICK = 0.010
RESEND_BURST = 16           # datagrams per retransmission round
WIN_SECONDS, WIN_LOG_ACK = 10.0, 0.35   # relay stats line when an ACK took longer than this (network / player relay late)
MOD = 1 << 32


def pack(t, sid, body=b""):
    return HDR.pack(MAGIC, VER, t, sid) + body


def unpack(d):
    if len(d) < HDR.size:
        return None
    m, v, t, sid = HDR.unpack_from(d)
    if m != MAGIC or v != VER:
        return None
    return t, sid, d[HDR.size:]


class Stream:
    """reliable, ordered bytes in both directions over an unreliable datagram path.
    out(datagram_body_type, body) sends one datagram; deliver(bytes) hands received bytes on."""

    def __init__(self, out, deliver, clock=time.monotonic):
        self.out, self.deliver, self.clock = out, deliver, clock
        self.tx = bytearray()          # unacknowledged + unsent bytes, starting at offset una
        self.una = 0                   # oldest unacknowledged offset
        self.nxt = 0                   # next offset to be written
        self.rcv = 0                   # next offset expected from the peer
        self.ooo = {}                  # offset -> bytes received beyond a gap
        self.srtt, self.rttvar, self.rto = None, 0.0, 0.25
        self.sent = []                 # [end offset, first send time, retransmitted?]
        self.dup = None                # [from, to, when] second copy of new bytes
        self.dup3 = []                 # third copies of small writes
        self.last_tx = 0.0
        self.rto_at = None
        self.dupacks = 0
        self.fast_at = 0.0
        self.peer_fin = None
        self.st = {"tx": 0, "rx": 0, "re": 0, "dup_rx": 0, "gap": 0}
        # (2026-10-28, rollbacks with commands 0.3-1.6 s late) per-10-s window: the longest time from the FIRST send of
        # bytes until their ACK (re-sends included, unlike the rtt sample) = how late the player's relay got them
        self.win = {"ack_max": 0.0, "slow": 0, "rto": 0, "fast": 0, "acked": 0}

    # ---- sending -------------------------------------------------------------------------------------------------
    def write(self, data):
        if not data:
            return
        now = self.clock()
        a = self.nxt
        self.tx += data
        self.nxt += len(data)
        self.sent.append([self.nxt, now, False])
        self._send(a, self.nxt)
        if self.dup and self.dup[1] == a:
            self.dup[1] = self.nxt                          # writes within DUP_DELAY share one second copy
        else:
            self.dup = [a, self.nxt, now + DUP_DELAY]
        if DUP3_DELAY and len(data) <= DUP3_MAX:
            self.dup3.append([a, self.nxt, now + DUP3_DELAY])
        if self.rto_at is None:
            self.rto_at = now + self.rto

    def _send(self, a, b, limit=None):
        a = max(a, self.una)
        n = 0
        while a < b and (limit is None or n < limit):
            e = min(b, a + MAX_CHUNK)
            chunk = bytes(self.tx[a - self.una:e - self.una])
            self.out(T_DATA, DATA_H.pack(self.rcv % MOD, a % MOD, len(chunk)) + chunk)
            self.st["tx"] += 1
            a = e
            n += 1
        self.last_tx = self.clock()
        return a

    def _resend_from_una(self, why):
        for s in self.sent:
            s[2] = True                                       # Karn: no rtt sample from re-sent data
        self.st["re"] += 1
        self._send(self.una, self.nxt, RESEND_BURST)

    def on_ack(self, ack, gap=False):
        ack = self._unwrap(ack, self.una)
        now = self.clock()
        if ack > self.nxt:
            return
        if ack > self.una:
            sample = None
            while self.sent and self.sent[0][0] <= ack:
                end, t, re = self.sent.pop(0)
                _d = now - t
                self.win["acked"] += 1
                if _d > self.win["ack_max"]:
                    self.win["ack_max"] = _d
                if _d > 0.4:
                    self.win["slow"] += 1
                if not re:
                    sample = now - t
            if sample is not None:
                if self.srtt is None:
                    self.srtt, self.rttvar = sample, sample / 2
                else:
                    self.rttvar = 0.75 * self.rttvar + 0.25 * abs(self.srtt - sample)
                    self.srtt = 0.875 * self.srtt + 0.125 * sample
                self.rto = min(RTO_MAX, max(RTO_MIN, self.srtt * 1.2 + 2 * self.rttvar + 0.02))
            del self.tx[:ack - self.una]
            self.una = ack
            self.dupacks = 0
            self.rto_at = (now + self.rto) if self.una < self.nxt else None
        elif gap and ack == self.una and self.una < self.nxt:
            self.dupacks += 1                                 # the peer holds bytes beyond a hole
            if now >= self.fast_at:
                self.win["fast"] += 1
                self._resend_from_una("fast")
                self.fast_at = now + (self.srtt or 0.2) * 0.8
                self.dupacks = 0

    def tick(self):
        now = self.clock()
        if self.dup and now >= self.dup[2]:
            a, b, _ = self.dup
            self.dup = None
            if b > self.una:
                self._send(a, b)
        while self.dup3 and now >= self.dup3[0][2]:
            a, b, _ = self.dup3.pop(0)
            if b > self.una:
                self._send(a, b)
        if self.rto_at is not None and now >= self.rto_at:
            if self.una < self.nxt:
                self.win["rto"] += 1
                self._resend_from_una("rto")
                self.rto = min(RTO_MAX, self.rto * 1.5)
                self.rto_at = now + self.rto
            else:
                self.rto_at = None

    # ---- receiving -----------------------------------------------------------------------------------------------
    @staticmethod
    def _unwrap(v, ref):
        """32-bit offset on the wire -> full offset nearest to ref"""
        base = ref - (ref % MOD)
        c = base + v
        if c - ref > MOD // 2:
            c -= MOD
        elif ref - c > MOD // 2:
            c += MOD
        return c

    def on_data(self, body):
        if len(body) < DATA_H.size:
            return
        ack, seq, n = DATA_H.unpack_from(body)
        data = body[DATA_H.size:DATA_H.size + n]
        self.st["rx"] += 1
        self.on_ack(ack)
        seq = self._unwrap(seq, self.rcv)
        end = seq + len(data)
        if end <= self.rcv:
            self.st["dup_rx"] += 1
        elif seq <= self.rcv:
            self._take(data[self.rcv - seq:])
        else:
            self.st["gap"] += 1
            if len(self.ooo) < 4096:
                self.ooo[seq] = data
        # every datagram is acknowledged (17 bytes); the gap flag asks for an immediate re-send of the hole
        self.out(T_ACK, U32.pack(self.rcv % MOD) + (b"\x01" if self.ooo else b"\x00"))

    def _take(self, data):
        self.rcv += len(data)
        out = [data]
        while self.ooo:
            k = min(self.ooo)
            if k > self.rcv:
                break
            d = self.ooo.pop(k)
            if k + len(d) > self.rcv:
                out.append(d[self.rcv - k:])
                self.rcv = k + len(d)
        self.deliver(b"".join(out))

    def idle(self):
        return self.una == self.nxt


# ---------------------------------------------------------------------------------------------------------------------
# SERVER SIDE (inside sgserver: start_relay_server(port, game_port, log))
RELAY_MAX_SESSIONS = 400
RELAY_PER_IP = 6
RELAY_IDLE = 30.0
RELAY_HELLO_PER_IP_MIN = 30


class _ServerSession:
    def __init__(self, srv, sid, addr):
        self.srv, self.sid, self.addr = srv, sid, addr
        self.writer = None
        self.ready = False
        self.last_rx = time.monotonic()
        self.closed = False
        self.local_fin = False
        self.fin_sent = 0
        self.stream = Stream(self._out, self._deliver)
        self.t0 = time.monotonic()
        self.pending = []

    def _out(self, t, body):
        self.srv.sendto(pack(t, self.sid, body), self.addr)

    def _deliver(self, data):
        if self.writer is not None and not self.writer.is_closing():
            self.writer.write(data)
        else:
            self.pending.append(data)

    async def open(self, game_host, game_port):
        try:
            r, w = await asyncio.wait_for(asyncio.open_connection(game_host, game_port), 5)
        except Exception as e:
            self.srv.log(f"   relay {self.addr}: game connection failed: {e!r}")
            self.close(rst=True)
            return
        self.writer = w
        w.write(b"SGRELAY %s %d\n" % (self.addr[0].encode(), self.addr[1]))
        for d in self.pending:
            w.write(d)
        self.pending = []
        self.ready = True
        self._out(T_HELLO_OK, b"")
        try:
            while True:
                d = await r.read(65536)
                if not d:
                    break
                self.stream.write(d)
        except Exception:
            pass
        self.local_fin = True

    def close(self, rst=False):
        if self.closed:
            return
        self.closed = True
        if rst:
            self._out(T_RST, b"")
        if self.writer is not None:
            try:
                self.writer.close()
            except Exception:
                pass
        self.srv.drop(self)


class RelayServer(asyncio.DatagramProtocol):
    def __init__(self, game_host, game_port, log=print):
        self.game_host, self.game_port, self.log = game_host, game_port, log
        self.sessions = {}
        self.hello_ip = {}
        self.tr = None

    def connection_made(self, tr):
        self.tr = tr

    def sendto(self, d, addr):
        if self.tr is not None:
            self.tr.sendto(d, addr)

    def drop(self, sess):
        if self.sessions.get(sess.sid) is sess:
            del self.sessions[sess.sid]
            st, s = sess.stream.st, sess.stream
            self.log(f"   relay {sess.addr[0]}:{sess.addr[1]} closed after {time.monotonic() - sess.t0:.0f} s: "
                     f"rtt {(s.srtt or 0) * 1000:.0f} ms, sent {st['tx']} dgrams ({st['re']} resend rounds), "
                     f"received {st['rx']} ({st['dup_rx']} duplicates, {st['gap']} after a gap)")

    def datagram_received(self, d, addr):
        p = unpack(d)
        if p is None:
            return
        t, sid, body = p
        s = self.sessions.get(sid)
        if t == T_HELLO:
            if s is None:
                now = time.monotonic()
                h = [x for x in self.hello_ip.get(addr[0], []) if now - x < 60]
                h.append(now)
                self.hello_ip[addr[0]] = h
                if (len(h) > RELAY_HELLO_PER_IP_MIN or len(self.sessions) >= RELAY_MAX_SESSIONS
                        or sum(1 for x in self.sessions.values() if x.addr[0] == addr[0]) >= RELAY_PER_IP):
                    return
                s = _ServerSession(self, sid, addr)
                self.sessions[sid] = s
                self.log(f"   relay session from {addr[0]}:{addr[1]}")
                asyncio.get_event_loop().create_task(s.open(self.game_host, self.game_port))
            elif s.ready:
                s.addr = addr
                s._out(T_HELLO_OK, b"")
            return
        if t == T_PING:
            if s is not None:
                s.addr, s.last_rx = addr, time.monotonic()
            self.sendto(pack(T_PONG, sid, body[:4]), addr)    # also the launcher's probe (unknown sid)
            return
        if s is None:
            if t in (T_DATA, T_FIN):
                self.sendto(pack(T_RST, sid), addr)
            return
        s.addr, s.last_rx = addr, time.monotonic()
        if t == T_DATA:
            s.stream.on_data(body)
        elif t == T_ACK and len(body) >= 4:
            s.stream.on_ack(U32.unpack_from(body)[0], body[4:5] == b"\x01")
        elif t == T_FIN and len(body) >= 4:
            s.stream.peer_fin = Stream._unwrap(U32.unpack_from(body)[0], s.stream.rcv)
        elif t == T_RST:
            s.close()

    async def ticker(self):
        last_win = time.monotonic()
        while True:
            await asyncio.sleep(TICK)
            now = time.monotonic()
            if now - last_win >= WIN_SECONDS:
                last_win = now
                for s in list(self.sessions.values()):
                    w = s.stream.win
                    if w["ack_max"] > WIN_LOG_ACK or w["rto"]:
                        self.log(f"   relay {s.addr[0]}:{s.addr[1]} last {WIN_SECONDS:.0f} s: slowest ACK {w['ack_max'] * 1000:.0f} ms "
                                 f"({w['slow']} of {w['acked']} > 400 ms), {w['fast']} fast + {w['rto']} timeout re-sends, "
                                 f"rtt {(s.stream.srtt or 0) * 1000:.0f} ms")
                    s.stream.win = {"ack_max": 0.0, "slow": 0, "rto": 0, "fast": 0, "acked": 0}
            for s in list(self.sessions.values()):
                try:
                    s.stream.tick()
                    if s.stream.peer_fin is not None and s.stream.rcv >= s.stream.peer_fin:
                        s.close()
                    elif s.local_fin and s.stream.idle():
                        if s.fin_sent < 3:
                            s._out(T_FIN, U32.pack(s.stream.nxt % MOD))
                            s.fin_sent += 1
                        else:
                            s.close()
                    elif now - s.last_rx > RELAY_IDLE:
                        s.close(rst=True)
                except Exception as e:
                    self.log(f"   relay tick error: {e!r}")


async def start_relay_server(port, game_port, log=print, host="0.0.0.0", game_host="127.0.0.1"):
    loop = asyncio.get_event_loop()
    srv = RelayServer(game_host, game_port, log)
    await loop.create_datagram_endpoint(lambda: srv, local_addr=(host, port))
    loop.create_task(srv.ticker())
    log(f"UDP relay on {host}:{port} -> game {game_host}:{game_port}")
    return srv


# ---------------------------------------------------------------------------------------------------------------------
# CLIENT SIDE in Python (tests; the players use launcher/SGRelay.exe, same protocol)
class RelayClient(asyncio.DatagramProtocol):
    def __init__(self, server_addr):
        self.server = server_addr
        self.sessions = {}
        self.tr = None

    def connection_made(self, tr):
        self.tr = tr

    def datagram_received(self, d, addr):
        p = unpack(d)
        if p is None:
            return
        t, sid, body = p
        s = self.sessions.get(sid)
        if s is None:
            return
        s["last_rx"] = time.monotonic()
        st = s["stream"]
        if t == T_HELLO_OK:
            s["ok"].set()
        elif t == T_DATA:
            st.on_data(body)
        elif t == T_ACK and len(body) >= 4:
            st.on_ack(U32.unpack_from(body)[0], body[4:5] == b"\x01")
        elif t == T_FIN and len(body) >= 4:
            st.peer_fin = Stream._unwrap(U32.unpack_from(body)[0], st.rcv)
        elif t == T_RST:
            s["writer"].close()

    async def serve_tcp(self, reader, writer):
        sid = random.getrandbits(64)
        s = {"writer": writer, "ok": asyncio.Event(), "last_rx": time.monotonic()}
        s["stream"] = Stream(lambda t, b: self.tr.sendto(pack(t, sid, b), self.server),
                             lambda d: writer.write(d))
        self.sessions[sid] = s
        for _ in range(15):
            self.tr.sendto(pack(T_HELLO, sid), self.server)
            try:
                await asyncio.wait_for(s["ok"].wait(), 0.2)
                break
            except asyncio.TimeoutError:
                pass
        if not s["ok"].is_set():
            writer.close()
            self.sessions.pop(sid, None)
            return
        try:
            while True:
                d = await reader.read(65536)
                if not d:
                    break
                s["stream"].write(d)
        except Exception:
            pass
        for _ in range(3):
            self.tr.sendto(pack(T_FIN, sid, U32.pack(s["stream"].nxt % MOD)), self.server)
        self.sessions.pop(sid, None)

    async def ticker(self):
        while True:
            await asyncio.sleep(TICK)
            now = time.monotonic()
            for sid, s in list(self.sessions.items()):
                st = s["stream"]
                st.tick()
                if st.peer_fin is not None and st.rcv >= st.peer_fin:
                    s["writer"].close()
                    self.sessions.pop(sid, None)
                elif now - st.last_tx > 1.0 and s["ok"].is_set():
                    self.tr.sendto(pack(T_PING, sid, U32.pack(0)), self.server)
                    st.last_tx = now
