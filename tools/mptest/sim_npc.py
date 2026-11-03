import sys, os, time, random, collections
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
S.LOG = open('/tmp/mp/simnpc.log', 'w')
T = [time.time()]
HOURS = float(sys.argv[1]) if len(sys.argv) > 1 else 3
real = time.time
S.time.time = lambda: T[0]
st = S.npc_state()
# server start
for n in S.npc_all():
    n["think_at"] = T[0] + random.uniform(*S.NPC_START_DELAY)
marches = collections.Counter(); owned0 = {n: S.npc_owned(n) for n in (1, 2, 3, 4)}
for step in range(int(HOURS * 3600 / 10)):
    T[0] += 10
    S.npc_tick(T[0]); S.npc_react(T[0]); S.npc_intercept_scan(T[0])
    if step % 360 == 0:
        busy = sum(1 for n in S.npc_all() if n["task"])
        print(f"t+{step*10//60:4d}min busy NPC tasks {busy}  owned {[S.npc_owned(n) for n in (1,2,3,4)]}")
S.LOG.flush()
txt = open('/tmp/mp/simnpc.log').read()
print('marches', txt.count('march on'), 'won', txt.count('WON'), 'took', txt.count(' took '), 'stays home', txt.count('stays home'))
