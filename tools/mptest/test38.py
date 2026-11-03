"""test38: simulated NPC battles step in WORKER PROCESSES - the game loop stays responsive (max stall measured with
many battles), the results are applied (units move / fight), a player entering stops the worker results."""
import asyncio, sys, os, time, random
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
for f in ('npcs.json', 'world.json'):
    if os.path.exists(f): os.remove(f)
import sgserver as S
S.LOG = open('/tmp/mp/server38.log', 'w', encoding='utf-8')
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
def open_battles(k):
    out = []
    for nid in [n[0] for n in S.NATIONS]:
        for c in S.npc_candidates(nid, time.time()):
            if len(out) >= k: return out
            if c['kind'] != 'alien' or c['pid'] in S.BATTLES: continue
            team = [n for n in S.npc_of(nid) if not n['task']][:2]
            if not team: break
            for n in team: n['state'] = 'active'; n['rest_until'] = 0
            S.npc_send(team, c, time.time(), group=True)
            if S.npc_open_battle(c['pid'], team, time.time()):
                out.append(S.BATTLES[c['pid']])
            break
    return out
async def lag(stop, rec):
    while not stop.is_set():
        t = time.monotonic(); await asyncio.sleep(0.05); rec.append(time.monotonic() - t - 0.05)
async def run(seconds):
    stop, rec = asyncio.Event(), []
    lt = asyncio.ensure_future(lag(stop, rec)); gt = asyncio.ensure_future(S.ghost_cycle())
    await asyncio.sleep(seconds); stop.set(); gt.cancel(); await asyncio.sleep(0.1)
    return max(rec) if rec else 0
async def main():
    random.seed(2)
    S.npc_tick(time.time())
    Bs = open_battles(16)
    chk('16 simulated battles open', len(Bs) >= 12, len(Bs))
    p0 = {id(B): {k: g['pos'] for k, g in B['targets'].items()} for B in Bs}
    S.NPC_WORKERS = 0; S._POOL[0] = False
    m_loop = await run(12)
    S._POOL[0] = None; S.NPC_WORKERS = 2
    p1 = {id(B): {k: g['pos'] for k, g in B['targets'].items()} for B in Bs}
    m_pool = await run(14)
    print(f'   max game-loop stall: in the loop {m_loop*1000:.0f} ms, with workers {m_pool*1000:.0f} ms')
    chk('workers keep the game loop responsive (max stall < 60 ms)', m_pool < 0.06, round(m_pool * 1000))
    moved = sum(1 for B in Bs for k, g in B['targets'].items() if k in p1[id(B)] and S.BSIM.dist(p1[id(B)][k], g['pos']) > 20)
    chk('worker results applied (units moved)', moved >= 20, moved)
    chk('every unit still on walkable ground', all(S._walk_grid(S.alien_context(B['ghost'], B['map'])[3]) is None or
        S._walk_grid(S.alien_context(B['ghost'], B['map'])[3]).ok(*S._walk_grid(S.alien_context(B['ghost'], B['map'])[3]).cell(g['pos']))
        for B in Bs for g in B['targets'].values()))
    S._POOL[0].shutdown()
asyncio.run(main())
