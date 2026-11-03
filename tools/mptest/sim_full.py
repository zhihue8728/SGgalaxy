"""NPC world simulation with REAL (server-simulated) battles: 10-s ticks, every open NPC battle is stepped with dt=10 s,
time-up after 30 min."""
import sys, os, time, random, collections
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
S.LOG = open('/tmp/mp/simnpc.log', 'w')
HOURS = float(sys.argv[1]) if len(sys.argv) > 1 else 3
T = [time.time()]
S.time.time = lambda: T[0]
# (11-02) a FULL world like the live server: every alien province of a planet goes to the nation whose capital is nearest
w = S.world_state(); own = w["owners"]
for pid in list(own):
    p = int(pid)
    if p >= 100000000 or int(own[pid]) or p in set(S.CAPITALS.values()): continue
    pl = p // 100000
    best = None
    for nid, cap in S.CAPITALS.items():
        if cap // 100000 != pl: continue
        d = S.npc_dist_from(cap).get(p % 100000, 99)
        if best is None or d < best[0]: best = (d, nid)
    if best: own[pid] = best[1]
for n in S.npc_all():
    n["think_at"] = T[0] + random.uniform(*S.NPC_START_DELAY)
real0 = time.monotonic(); maxb = 0; steps = 0
for step in range(int(HOURS * 3600 / 10)):
    T[0] += 10
    S.npc_tick(T[0]); S.npc_react(T[0]); S.npc_intercept_scan(T[0])
    S.BSIM.Grid.spent = 0
    open_ = [B for B in S.BATTLES.values() if B.get('ghost') and not B.get('won')]
    maxb = max(maxb, len(open_))
    for B in open_:
        S.ghost_step(B, T[0], dt=10.0); steps += 1
        if not B.get('won') and T[0] - B.get('opened', T[0]) >= S.BATTLE_SECONDS:
            S.ghost_time_up(B)
    if step % 360 == 0:
        print(f"t+{step*10//60:4d}min tasks {sum(1 for n in S.npc_all() if n['task'])} battles {len(open_)} owned "
              f"{[S.npc_owned(n) for n in (1,2,3,4)]} real {time.monotonic()-real0:.0f}s", flush=True)
S.LOG.flush()
txt = open('/tmp/mp/simnpc.log').read()
print('battles opened', txt.count('REAL battle on'), 'over', txt.count('NPC battle on') - txt.count('NPC battle on ') + txt.count(' over: '),
      'won', txt.count('WON ('), 'lost', txt.count('lost ('), 'max simultaneous', maxb, 'steps', steps,
      'took', txt.count(' took '), 'captured POCs', txt.count('CAPTURED by nation'), 'errors', txt.count('error'))
