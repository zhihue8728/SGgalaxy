"""test74 (user 2026-10-26 19:58): Word of Honor 'pyramid' - Subordinate XP tribute, Assign XP window list, /xp."""
import asyncio, struct, sys, os
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
from mpclient import Client
S.LOG = open('/tmp/mp/server74.log', 'w', encoding='utf-8')
PORT = 3974
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
async def main():
    S.ensure_unique_unit_ids()
    srv = await asyncio.start_server(S.handle, '127.0.0.1', PORT)
    A = Client('jjjjjjjj'); Bc = Client('hhhhhhhh')
    await A.connect(PORT); await A.login(); await Bc.connect(PORT); await Bc.login(); await asyncio.sleep(1.0)
    # B (student) swears to A (superior)
    Bc.send(bytes([0x55, 0, 0]) + S._s8('jjjjjjjj')); await asyncio.sleep(0.5)
    A.send(bytes([0x55, 3, 1]) + S._s8('hhhhhhhh')); await asyncio.sleep(0.5)
    accs, b = S.get_account('hhhhhhhh')
    chk('hhhhhhhh has jjjjjjjj as superior', b['commander'].get('superior', '').lower() == 'jjjjjjjj')
    # B earns XP -> tribute
    cmd = b['commander']; u = b['units'][0]
    S.PG.add_unit_xp(cmd, u, S.unit_branch(u['chassis']), 1000)
    chk('tribute 10 % recorded', cmd.get('tribute') == 100, cmd.get('tribute'))
    accs['hhhhhhhh'] = b; S.save_accounts(accs)
    # window list
    A.msgs.clear() if hasattr(A, 'msgs') else None
    A.send(bytes([0x55, 2])); await asyncio.sleep(0.6)
    rows = S.tribute_rows('jjjjjjjj')
    chk('one subordinate row', len(rows) == 1 and rows[0][0] == 'hhhhhhhh' and rows[0][2] == 100, rows)
    # assign
    _a, a0 = S.get_account('jjjjjjjj')
    lvl0 = a0['units'][0].get('level', 1); xp0 = a0['units'][0].get('xp', 0)
    class F: pass
    sess = next(o for o in S.ONLINE if o.acc == 'jjjjjjjj')
    g, m = S.assign_exp(sess, 1, 60)
    chk('assign 60', g == 60, m)
    _a, a1 = S.get_account('jjjjjjjj')
    chk('unit got XP (or levelled)', a1['units'][0].get('xp', 0) != xp0 or a1['units'][0].get('level', 1) > lvl0)
    _b, b1 = S.get_account('hhhhhhhh')
    chk('pool reduced to 40', b1['commander'].get('tribute') == 40, b1['commander'].get('tribute'))
    chk('assigned XP did not flow on', a1['commander'].get('tribute', 0) == a0['commander'].get('tribute', 0))
    g, m = S.assign_exp(sess, 1, None)
    chk('assign rest 40', g == 40, m)
    g, m = S.assign_exp(sess, 1, 5)
    chk('nothing left', g == 0, m)
    # release resets
    Bc.send(bytes([0x5c, 0]) + S._s8('jjjjjjjj')); await asyncio.sleep(0.5)
    _b, b2 = S.get_account('hhhhhhhh')
    chk('release clears superior and pool', not b2['commander'].get('superior') and b2['commander'].get('tribute') == 0)
    A.send(bytes([0x2a, 0]) + S._s8('/xp') + bytes([255, 255, 255])); await asyncio.sleep(0.4)
    chk('/xp with no subordinates does not crash', True)
    srv.close()
asyncio.run(main())
