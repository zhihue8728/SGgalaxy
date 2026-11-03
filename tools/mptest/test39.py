"""test39: network latency work - battle lock-step frames every FRAME_MS on a drift-free schedule, frames are skipped
(not queued) behind a stalled link, the socket is tuned (NODELAY, QUICKACK, keep-alive), /lag net reports the link."""
import asyncio, struct, sys, os, time, random
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
for f in ('npcs.json', 'world.json'):
    if os.path.exists(f): os.remove(f)
import sgserver as S
from mpclient import Client
S.LOG = open('/tmp/mp/server39.log', 'w', encoding='utf-8')
PORT = 3991
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
async def main():
    random.seed(5)
    S.ensure_unique_unit_ids()
    srv = await asyncio.start_server(S.handle, '127.0.0.1', PORT)
    S.npc_tick(time.time())
    A = Client('jjjjjjjj'); await A.connect(PORT); await A.login(); await asyncio.sleep(1.0)
    s = next(iter(S.ONLINE))
    # ---- socket tuning
    import socket
    nd = s.sock.getsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY)
    ka = s.sock.getsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE)
    chk('TCP_NODELAY + keep-alive set on the player connection', bool(nd) and bool(ka), (nd, ka))
    st = S.tcp_stats(s)
    if sys.platform.startswith('linux'):
        chk('tcp_stats reads TCP_INFO (rtt, retransmits, queued)', st is not None and st['rtt'] >= 0 and st['queued'] >= 0, st)
    # ---- frames
    P = next(c['pid'] for c in S.npc_candidates(11, time.time()) if c['kind'] == 'alien')
    S.enter_field(s, P, 0x400, 0x400); await asyncio.sleep(0.5)
    t0 = time.monotonic()
    await asyncio.sleep(4.0)
    fr = [ts for ts, b in A.inbox if b[0] == 0x80 and len(b) == 9 and ts >= t0]
    gaps = [(b - a) * 1000 for a, b in zip(fr, fr[1:])]
    mean = sum(gaps) / max(1, len(gaps))
    chk(f'battle frames come every {S.FRAME_MS} ms (mean gap)', abs(mean - S.FRAME_MS) < 6, round(mean, 1))
    chk('no gap above 3 frame intervals on a quiet loop', max(gaps, default=999) < 3 * S.FRAME_MS, round(max(gaps, default=0)))
    ticks = [struct.unpack_from('>I', b, 3)[0] for ts, b in A.inbox if b[0] == 0x80 and len(b) == 9 and ts >= t0]
    chk('frame game time is monotonic and tracks the clock', all(y >= x for x, y in zip(ticks, ticks[1:])) and
        abs((ticks[-1] - ticks[0]) / 100 - (fr[-1] - fr[0])) < 0.15, (ticks[0], ticks[-1]))
    # ---- a stalled link gets no frame burst: pretend 1 MB is queued
    class FakeTr:
        def __init__(self, tr): self.tr = tr
        def get_write_buffer_size(self): return 10 ** 6
        def __getattr__(self, k): return getattr(self.tr, k)
    n_before = sum(1 for _ in A.inbox)
    real_w = s.w
    class W2:
        def __init__(self, w): self.w = w; self.transport = FakeTr(w.transport)
        def __getattr__(self, k): return getattr(self.w, k)
    s.w = W2(real_w)
    await asyncio.sleep(1.0)
    n_stalled = sum(1 for ts, b in A.inbox[n_before:] if b[0] == 0x80 and len(b) == 9)
    s.w = real_w
    chk('frames are skipped while the connection has a big backlog', n_stalled <= 1, n_stalled)
    await asyncio.sleep(0.5)
    n_after = sum(1 for ts, b in A.inbox[n_before:] if b[0] == 0x80 and len(b) == 9)
    chk('frames resume when the backlog is gone', n_after >= 5, n_after)
    # ---- /lag net (jjjjjjjj is a GM account)
    n0 = len(A.inbox)
    S.gm_command(s, '/lag net'); await asyncio.sleep(0.4)
    txt = b' '.join(b for ts, b in A.inbox[n0:] if b[0] == 0x2A)
    chk('/lag net lists the player link and the frame interval', b'jjjjjjjj' in txt and b'frame' in txt, txt[:120])
    S.gm_command(s, '/lag'); await asyncio.sleep(0.3)
    A.close(); await asyncio.sleep(0.3)
    srv.close()
asyncio.run(main())
