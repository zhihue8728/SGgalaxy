"""test75 (user 2026-10-26 21:08: freeze then teleport): adaptive jitter buffer / lossy-link frame interval."""
import sys, os
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
S.LOG = open('/tmp/mp/server75.log', 'w', encoding='utf-8')
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
G = S.__dict__ if hasattr(S, '__dict__') else {}
class W:
    def is_closing(self): return False
    class transport:
        @staticmethod
        def get_write_buffer_size(): return 0
class F:
    def __init__(s, acc): s.acc = acc; s.logged_in = True; s.battle_mode = 1; s.w = W(); s.st = None
stats = {}
real_tcp = S.tcp_stats
S.tcp_stats = lambda o: stats.get(o.acc)
g = sys.modules['sgserver'].__dict__
a = F('good'); b = F('lossy')
S.ONLINE.clear(); S.ONLINE.add(a)
g['FRAME_LEAD'], g['RELAY_DELAY'], g['JB_AUTO'] = 6, 7, True
def st(var, retr, segs, dsack=0): return {"rtt": 215, "var": var, "unacked": 2, "lost": 0, "retrans": 0, "total_retrans": retr,
                                          "cwnd": 10, "queued": 0, "segs": segs, "dsack": dsack, "rto": 300}
# good link: var 20 -> 33 + 50 = 83 ms -> 9 ticks
t = 1000.0
for i in range(12):
    stats['good'] = st(20, 0, 30 * i); S.jb_update(t + i)
chk('good link: lead from jitter (9)', g['FRAME_LEAD'] == 9 and g['RELAY_DELAY'] == 10, (g['FRAME_LEAD'], g['RELAY_DELAY']))
# lossy link joins: 1.6 real retransmits/s -> lossy -> capped
S.ONLINE.add(b)
for i in range(12, 24):
    stats['good'] = st(20, 0, 30 * i)
    stats['lossy'] = st(20, int(1.6 * (i - 12)), 30 * (i - 12)); S.jb_update(t + i)
chk('lossy link detected', S.jb_lossy(b) and not S.jb_lossy(a), (b.jb, a.jb))
chk('lead raised to the cap', g['FRAME_LEAD'] == g['JB_LEAD_MAX'] and g['RELAY_DELAY'] == g['FRAME_LEAD'] + 1, (g['FRAME_LEAD'], g['RELAY_DELAY']))
chk('order delay always > lead', g['RELAY_DELAY'] > g['FRAME_LEAD'])
# spurious retransmissions (DSACK) do not count
c = F('spur'); S.ONLINE.discard(b); S.ONLINE.add(c)
leads, delays = [], []
for i in range(24, 36):
    stats['good'] = st(20, 0, 30 * i)
    stats['spur'] = st(20, 2 * (i - 24), 30 * (i - 24), dsack=2 * (i - 24)); S.jb_update(t + i)
    leads.append(g['FRAME_LEAD']); delays.append(g['RELAY_DELAY'])
chk('spurious retransmissions are not loss', not S.jb_lossy(c), c.jb)
# lowering: one tick per second, order delay follows later, stamps never go back
for i in range(36, 50):
    stats['good'] = st(20, 0, 30 * i); stats['spur'] = st(20, 0, 30 * i, 0); S.jb_update(t + i)
    leads.append(g['FRAME_LEAD']); delays.append(g['RELAY_DELAY'])
chk('lead goes down 1 tick per second', all(x - y in (0, 1) for x, y in zip(leads, leads[1:])), leads)
chk('order delay > every lead of the last 2 s', all(delays[k] > max(leads[max(0, k - 2):k + 1]) for k in range(len(leads))), (leads, delays))
chk('settles at the good-link value', leads[-1] == 9, leads)
# manual override
g['JB_AUTO'] = False; g['FRAME_LEAD'], g['RELAY_DELAY'] = 6, 7
stats['spur'] = st(80, 0, 0); S.jb_update(t + 60)
chk('manual mode leaves the values alone', g['FRAME_LEAD'] == 6 and g['RELAY_DELAY'] == 7)
S.tcp_stats = real_tcp
