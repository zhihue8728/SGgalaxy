"""NPC battle simulation in worker PROCESSES (user 2026-10-22 22:26: "NPC的线程够多 ... 不会造成正常玩家卡顿").
Python threads cannot run Python code in parallel (one interpreter lock), so the heavy part - battlesim.step for every
battle without players - runs in a ProcessPoolExecutor (NPC_WORKERS processes).  The game loop packs each battle (~1 ms),
awaits all steps together and applies the results only if the battle is still simulated (no player entered meanwhile).
NPC decisions (npc_tick, 10-30 ms) stay in the game loop: they change shared state and are already short."""
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

rep('''def ghost_step(B, now, dt=1.0):
    """one simulated second of a battle without players."""
    g = B["ghost"]
    pid = B["map"]
    tier = PLANET_TIER.get((pid // 100000) % 1000, 1)''', '''NPC_WORKERS = max(1, min(4, (os.cpu_count() or 2) - 1))     # simulation worker processes
_POOL = [None]

def ghost_pool():
    """the worker processes (created on first use; None = simulate in the game loop, e.g. in tests)."""
    if _POOL[0] is None and NPC_WORKERS > 0:
        try:
            import concurrent.futures, multiprocessing
            _POOL[0] = concurrent.futures.ProcessPoolExecutor(max_workers=NPC_WORKERS,
                                                              mp_context=multiprocessing.get_context(
                "fork" if "fork" in multiprocessing.get_all_start_methods() else "spawn"))
            log(f"   NPC simulation: {NPC_WORKERS} worker process(es)")
        except Exception as e:
            log(f"   NPC simulation workers unavailable ({e!r}) - simulating in the game loop")
            _POOL[0] = False
    return _POOL[0] or None

def ghost_payload(B, now, dt):
    g = B["ghost"]
    pid = B["map"]
    tier = PLANET_TIER.get((pid // 100000) % 1000, 1)
    params = {"map": alien_context(g, pid)[3], "walk_path": os.path.join(os.path.dirname(os.path.abspath(__file__)), "walk_grids.json"),
              "now": now, "dt": dt, "aggro": AL.AGGRO[tier], "leash": AL.LEASH[tier], "focus": AL.FOCUS_MAX,
              "poc_radius": POC_RADIUS, "hunt_from": (g.alien_meta or {}).get("hunt_from", 0),
              "allies": [list(x) for x in NATION_ALLIES], "damage_types": bool(DAMAGE_TYPES)}
    return BSIM.pack(B["targets"], B["pocs"], lambda tg: tg.get("nation") if tg.get("npc") is not None else ALIEN_NATION,
                     params)

def ghost_apply(B, res):
    """results of a worker step -> the battle (units that died or vanished meanwhile are skipped)."""
    for tid, f in res["units"].items():
        tg = B["targets"].get(tid)
        if tg is None or tg.get("hp", 0) <= 0:
            continue
        tg.update(f)                                  # nothing else changes a simulated battle while no player is there
    for tid in res["dead"]:
        tg = B["targets"].get(tid)
        if tg is not None:
            tg["hp"] = min(tg.get("hp", 0), 0)
            _ghost_death(B, tid, tg)

def ghost_step(B, now, dt=1.0, result=None):
    """one simulated step of a battle without players (result = a worker's step, else simulated here)."""
    g = B["ghost"]
    pid = B["map"]
    if result is not None:
        ghost_apply(B, result)
        return _ghost_after(B, now, dt)
    tier = PLANET_TIER.get((pid // 100000) % 1000, 1)''')
rep('''    BSIM.step(B["targets"], B["pocs"], ctx, dt)
    for tg in B["targets"].values():              # wounds are remembered (the NPC picks healthy units next time)''', '''    BSIM.step(B["targets"], B["pocs"], ctx, dt)
    _ghost_after(B, now, dt)

def _ghost_after(B, now, dt):
    g = B["ghost"]
    for tg in B["targets"].values():              # wounds are remembered (the NPC picks healthy units next time)''')
rep('''        todo = [(pid, B) for pid, B in list(BATTLES.items()) if B.get("ghost") and not B.get("won") and not _live(B)]
        for pid, B in todo:''', '''        todo = [(pid, B) for pid, B in list(BATTLES.items()) if B.get("ghost") and not B.get("won") and not _live(B)]
        pool = ghost_pool() if todo else None
        if pool is not None:
            # every battle steps in parallel in the worker processes; the game loop only packs and applies
            loop = asyncio.get_event_loop()
            futs = []
            for pid, B in todo:
                try:
                    futs.append((pid, B, loop.run_in_executor(pool, BSIM.step_remote, ghost_payload(B, time.time(), GHOST_TICK))))
                except Exception as e:
                    log(f"   ghost battle {pid}: worker submit failed {e!r}")
            for pid, B, fu in futs:
                try:
                    res = await fu
                except Exception as e:
                    log(f"   ghost battle {pid}: worker step failed {e!r}")
                    continue
                if BATTLES.get(pid) is not B or B.get("won") or _live(B):
                    continue                             # a player entered meanwhile: the clients simulate now
                try:
                    ghost_step(B, time.time(), dt=GHOST_TICK, result=res)
                except Exception as e:
                    import traceback
                    log(f"   ghost battle {pid} error: {e!r} {traceback.format_exc()[-300:]}")
                await asyncio.sleep(0)
            todo = []
        for pid, B in todo:''')
open(P, "w", encoding="utf-8").write(src)
print("patched")
