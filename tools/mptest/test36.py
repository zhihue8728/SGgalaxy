"""test36: NPCs the strategic map shows in a province stand on its town map (hero PUT); the BATTLE INFO dialog (0x1e)
lists the NPC commanders and the aliens of a battle."""
import asyncio, struct, sys, os, time, random
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
for f in ('npcs.json', 'world.json'):
    if os.path.exists(f): os.remove(f)
import sgserver as S
from mpclient import Client
S.LOG = open('/tmp/mp/server36.log', 'w', encoding='utf-8')
PORT = 3996
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
async def main():
    random.seed(4)
    S.ensure_unique_unit_ids()
    srv = await asyncio.start_server(S.handle, '127.0.0.1', PORT)
    S.npc_tick(time.time())
    A = Client('jjjjjjjj'); await A.connect(PORT); await A.login(); await asyncio.sleep(1.0)
    s = next(iter(S.ONLINE)); HN = s.cmd['nation']
    cap = S.CAPITALS[HN]
    pv = next(cap // 100000 * 100000 + q for q in S.PORTAL_LINKS[cap % 100000])
    S.set_province_owner(pv, HN)
    n = next(n for n in S.npc_of(HN) if not n['task'])
    n['state'] = 'active'
    n['task'] = {'kind': 'support', 'target': pv, 'since': time.time(), 'phase': 'support'}
    chk('the strategic map has the NPC in the province', S.npc_location(n)[0] == pv, S.npc_location(n))
    t = time.monotonic()
    S.enter_field(s, pv, 0x400, 0x400); await asyncio.sleep(0.5)
    chk('own province = town map', s.battle_mode == 0)
    S.npc_town_sync(s); await asyncio.sleep(0.5)
    chk('the NPC commander stands on the town map (PUT with his name)', any(p[1] in (n['name'], S.NP.name_zh(n['name']).encode('gbk').decode('latin-1')) for p in A.puts(t)),
        [p[1] for p in A.puts(t)][:5])
    n['task'] = None; n['rest_until'] = time.time() + 9999
    S.npc_town_sync(s)
    chk('a leaving NPC walks to the map edge first', s.npc_town.get(n['id'], {}).get('leave_at') is not None)
    # battle info lists NPCs + aliens
    NA = next(x[0] for x in S.NATIONS if S.nation_planet(x[0]) == S.nation_planet(HN) and x[0] != HN)
    cand = [c for c in S.npc_candidates(NA, time.time()) if c['kind'] == 'alien' and c['pid'] not in S.BATTLES]
    team = [m for m in S.npc_of(NA) if not m['task']][:2]
    for m in team: m['state'] = 'active'; m['rest_until'] = 0
    S.npc_send(team, cand[0], time.time(), group=True)
    for m in team: m['task']['arrive'] = time.time() - 1
    S.npc_tick(time.time())
    P = cand[0]['pid']
    chk('NPC battle running', P in S.BATTLES)
    t = time.monotonic()
    S.send_battle_control(s, P, 0x400, 0x400); await asyncio.sleep(0.5)
    body = A.got(0x1E, t)
    txt = body[-1] if body else b''
    # 2026-10-24: NPC commanders ARE listed like players - with their NATION id (a 0x0F table id: the attacker list
    # drawer 00408749 crashed on unknown ids; the 10-23 version sent NPC ids 40000+ there)
    o = 1 + 4 + 2 + 4; ln = txt[o]; o += 1 + ln
    n = txt[o]; o += 1
    rows = []
    for _ in range(n):
        L = txt[o]; nm = txt[o + 1:o + 1 + L]; o += 1 + L
        rows.append((nm, *struct.unpack_from('>II', txt, o))); o += 8
    ids = {x[0] for x in S.NATIONS} | {0}
    chk('BATTLE INFO lists the NPC commanders', any(r[0] in (m['name'].encode(), (S.NP.name_zh(m['name']) or '').encode('gbk')) for m in team for r in rows), rows)
    chk('... every listed nation is a 0x0F id (no client crash)', all(r[1] in ids for r in rows), rows)
    chk('... and ends with wait + can-enter', len(txt) - o == 2, len(txt) - o)
    srv.close()
asyncio.run(main())
