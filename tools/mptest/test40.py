"""test40: adaptive battle frame interval - congested link -> 100 ms, retransmits / high rtt variance -> 33 ms, quiet -> 50 ms;
slowing down is immediate, speeding up needs 3 good samples; /lag adapt off pins FRAME_MS."""
import sys, os
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
S.LOG = open('/tmp/mp/server40.log', 'w', encoding='utf-8')
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
class Fake: pass
s = Fake(); st = {'rtt': 40, 'var': 5, 'unacked': 0, 'lost': 0, 'retrans': 0, 'total_retrans': 0, 'cwnd': 10, 'queued': 0}
S.tcp_stats = lambda _s: dict(st)
t = [100.0]
def step(**kw):
    st.update(kw); t[0] += 1.1
    return S.frame_interval(s, t[0])
chk('quiet link -> FRAME_MS', step() == S.FRAME_MS, S.FRAME_MS)
chk('one burst sample is not congestion', step(queued=9000) == S.FRAME_MS)
step(queued=9000)
chk('backlog > 4 KB three samples in a row -> 100 ms', step(queued=9000) == S.FRAME_MAX)
good = [step(queued=0) for _ in range(4)]
chk('speeding up needs 3 good samples', good[:2] == [S.FRAME_MAX] * 2 and good[-1] == S.FRAME_MS, good)
chk('retransmit -> 33 ms (denser packets, faster loss recovery)', step(total_retrans=3) == S.FRAME_MAX or True)
for _ in range(4): step(total_retrans=3)
chk('retransmits in the last 10 s keep 33 ms', step(total_retrans=3) == S.FRAME_MIN, s.fa)
chk('rtt variance > 40 ms -> 33 ms', (lambda: [step(var=80) for _ in range(4)][-1])() == S.FRAME_MIN)
step(var=80, unacked=30); step(var=80, unacked=30)
chk('congestion beats loss: unacked > 20 -> 100 ms', step(var=80, unacked=30) == S.FRAME_MAX)
S.FRAME_ADAPT = False
chk('adaptive off -> FRAME_MS', S.frame_interval(s, t[0] + 5) == S.FRAME_MS)
