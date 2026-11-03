"""event-loop stalls (user 2026-10-22 22:12: "!! event loop stalled 1798 ms"): the NPC tick opened several real battles at
once and every new (unit kind, level) needed an equipment search (~20 ms each).  Fixes: at most NPC_OPEN_PER_TICK battles
are opened per NPC tick (the others arrive a few seconds later), the NPC unit loadouts are computed in the background at
start-up (one per event-loop turn), and the tick reports its own duration when it is slow."""
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

rep('''    if NPC_GHOST_BATTLES:
        if npc_open_battle(pid, ns, now):''', '''    if NPC_GHOST_BATTLES:
        if _OPEN_BUDGET[0] <= 0:                  # enough battles opened in this tick: a few seconds later
            for n in ns:
                n["task"]["arrive"] = now + random.uniform(3, 9)
            return
        _OPEN_BUDGET[0] -= 1
        if npc_open_battle(pid, ns, now):''')
rep('''NPC_GHOST_DEPLOY = 12          # units one NPC brings onto the map at a time (its next squads follow like F7)''',
    '''NPC_GHOST_DEPLOY = 12          # units one NPC brings onto the map at a time (its next squads follow like F7)
NPC_OPEN_PER_TICK = 2          # real battles opened per NPC tick at most (CPU: ~50-180 ms each before the warm-up)
_OPEN_BUDGET = [NPC_OPEN_PER_TICK]

async def npc_warm_units():
    """compute the battle loadout of every (unit kind, level) the NPC armies use, one per event-loop turn, so opening
    a battle later does not stall the server (each new one costs an equipment search of ~20 ms)."""
    await asyncio.sleep(20)
    n_new, t0 = 0, time.monotonic()
    for n in list(npc_all()):
        for name, lv in list(n["squad"]):
            if (name, int(lv)) in _NPC_UNITS:
                continue
            try:
                npc_unit(name, lv)
                n_new += 1
            except Exception:
                pass
            await asyncio.sleep(0)
    log(f"   NPC: {n_new} unit loadouts prepared in the background ({time.monotonic() - t0:.0f}s)")''')
rep('''def npc_tick(now=None):
    now = now or time.time()''', '''def npc_tick(now=None):
    now = now or time.time()
    _OPEN_BUDGET[0] = NPC_OPEN_PER_TICK''')
rep('''            npc_tick()
            npc_react(time.time())
            npc_intercept_scan(time.time())''', '''            _t0 = time.monotonic()
            npc_tick()
            npc_react(time.time())
            npc_intercept_scan(time.time())
            if time.monotonic() - _t0 > 0.15:
                log(f"   NPC tick took {(time.monotonic() - _t0) * 1000:.0f} ms")''')
rep('''    asyncio.get_event_loop().create_task(ghost_cycle())
''', '''    asyncio.get_event_loop().create_task(ghost_cycle())
    asyncio.get_event_loop().create_task(npc_warm_units())
''')
# a slow simulated battle step is reported too
rep('''            try:
                ghost_step(B, time.time(), dt=GHOST_TICK)
            except Exception as e:''', '''            try:
                _t1 = time.monotonic()
                ghost_step(B, time.time(), dt=GHOST_TICK)
                if time.monotonic() - _t1 > 0.1:
                    log(f"   ghost battle {pid}: step took {(time.monotonic() - _t1) * 1000:.0f} ms ({len(B['targets'])} units)")
            except Exception as e:''')
open(P, "w", encoding="utf-8").write(src)
print("patched")
