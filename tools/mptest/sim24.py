import sys, os, time, random
os.chdir('/tmp/mp'); sys.path.insert(0,'/tmp/mp')
import sgserver as S
S.LOG = open('/tmp/mp/sim.log','w')
S.save_world = lambda w: None
S.npc_save = lambda force=False: None
base = time.time(); sim = [base]
real = time.time
time.time = lambda: sim[0]
random.seed(3)
caps = set(S.CAPITALS.values())
def owned():
    c = {}
    for k, v in S.world_state()['owners'].items():
        if int(v) and int(k) not in caps: c[int(v)] = c.get(int(v), 0) + 1
    return c
for step in range(0, 24*360+1):
    sim[0] = base + step*10
    S.npc_tick(sim[0])
    if step % (360*2) == 0: print(f"{step//360:2d}h", dict(sorted(owned().items())), flush=True)
