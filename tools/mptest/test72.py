"""test72 (user 2026-10-26 12:42): Simulation Center - two players of different nations pick the same province and
fight each other; they start apart.  FORCE OPEN from the sim board is ignored (no real map replaces the board)."""
import asyncio, struct, sys, os, time
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
from mpclient import Client
S.LOG = open('/tmp/mp/server72.log', 'w', encoding='utf-8')
PORT = 3972
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
async def main():
    S.ensure_unique_unit_ids()
    srv = await asyncio.start_server(S.handle, '127.0.0.1', PORT)
    A = Client('jjjjjjjj'); Bc = Client('hhhhhhhh')
    await A.connect(PORT); await A.login(); await Bc.connect(PORT); await Bc.login(); await asyncio.sleep(1.0)
    _a, a0 = S.get_account('jjjjjjjj'); _b, b0 = S.get_account('hhhhhhhh')
    # put B into another, non-allied nation
    nA = a0['commander']['nation']
    nB = next(n[0] for n in S.NATIONS if n[0] != nA and not S.same_side(n[0], nA) and S.nation_planet(n[0]) == S.nation_planet(nA))
    b0['commander']['nation'] = nB; _b['hhhhhhhh'] = b0; S.save_accounts(_b)
    for o in S.ONLINE:
        if o.acc == 'hhhhhhhh': o.cmd['nation'] = nB
    caps = set(S.CAPITALS.values())
    prov = next(p for p in S.planet_provinces(S.nation_planet(nA)) if p not in caps)
    A.send(bytes([0x2b, 1, 0])); Bc.send(bytes([0x2b, 1, 0])); await asyncio.sleep(0.6)
    A.send(bytes([0x20, 8]) + struct.pack('>I', prov)); await asyncio.sleep(1.5)
    t = time.monotonic(); Bc.send(bytes([0x20, 8]) + struct.pack('>I', prov)); await asyncio.sleep(1.5)
    Bt = S.BATTLES.get(S.SIM_BASE + prov)
    chk('both nations are in the same simulation', bool(Bt and Bt.get('sim') and len(Bt['members']) == 2), len(Bt['members']) if Bt else None)
    S.LOG.flush()
    log = open('/tmp/mp/server72.log', encoding='utf-8').read()
    chk('the second nation starts apart from the first', 'faces' in log and 'starts at' in log)
    srv.close()
asyncio.run(main())
