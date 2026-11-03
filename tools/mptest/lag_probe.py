"""where does the server block? times every NPC tick part and every ghost battle step (simulated world, 10-s ticks)."""
import sys, os, time, random, collections
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
t_start = time.monotonic()
import sgserver as S
S.LOG = open('/tmp/mp/lagprobe.log', 'w')
t_imp = time.monotonic() - t_start
T = [time.time()]
S.time.time = lambda: T[0]
pc = time.perf_counter
worst = collections.defaultdict(float); total = collections.defaultdict(float)
def timed(name, f, *a, **k):
    t = pc(); r = f(*a, **k); d = pc() - t
    worst[name] = max(worst[name], d); total[name] += d
    return r
# wrap the heavy server functions
for fn in ('npc_open_battle', 'npc_unit', 'spawn_aliens_initial', 'npc_save', 'npc_ensure_roster', 'npc_pool'):
    orig = getattr(S, fn)
    def w(*a, _o=orig, _n=fn, **k):
        return timed(_n, _o, *a, **k)
    setattr(S, fn, w)
t = pc(); S.npc_tick(T[0]); first = pc() - t
t = pc()
for n in S.npc_all():
    for name, lv in n['squad']: S.npc_unit(name, lv)
print(f'warm-up (background in the server) {pc() - t:.1f}s', flush=True)
worst.clear(); total.clear()
for n in S.npc_all():
    n["think_at"] = T[0] + random.uniform(*S.NPC_START_DELAY)
for step in range(int(float(sys.argv[1]) * 3600 / 10)):
    T[0] += 10
    timed('npc_tick', S.npc_tick, T[0]); timed('npc_react', S.npc_react, T[0]); timed('intercept_scan', S.npc_intercept_scan, T[0])
    S.BSIM.Grid.spent = 0
    for B in [B for B in S.BATTLES.values() if B.get('ghost') and not B.get('won')]:
        timed('ghost_step', S.ghost_step, B, T[0], dt=2.0)
print(f'import {t_imp:.2f}s  first npc_tick (rosters, doctrines) {first*1000:.0f} ms')
for k in sorted(worst, key=lambda k: -worst[k]):
    print(f'{k:16s} worst {worst[k]*1000:7.0f} ms   total {total[k]:6.1f} s')
