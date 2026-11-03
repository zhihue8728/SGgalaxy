"""test96 (user 2026-10-28 13:05 "check every other mechanism with more than one logic and fix them"): the single
places that replaced copies - prices (shop list = charge, sale = half everywhere), resources (res_pay / res_add),
province capture (old owner told, ally rule, no 'lost' to the new owner), side notices, the hit formula, the walk
time estimate, the battle unit listing."""
import os, sys, struct, glob
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
S.LOG = open('/tmp/mp/server96.log', 'w', encoding='utf-8')
S.save_world = lambda w: None
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
src = {f: open(f, encoding='utf-8').read() for f in glob.glob('/tmp/mp/sgs/*.py') + ['/tmp/mp/battlesim.py']}
alls = ''.join(src.values())
# prices
name = sorted(S.SHOP_NAMES)[0]
code = S.CODE_OF.get(name, name)
rec = S.build_unit_shop(1, [], 0.8, {})
chk('Factory list price = charged price (with the centre discount)', struct.pack('>5I', *S.unit_buy_price(name, 0.8)) in rec)
chk('unit sale = half', S.unit_sell_price(code) == tuple(v // 2 for v in S.unit_price_of(code)))
iid = next(it['id'] for it in S.ITEMS if any(S.item_price(it['id'])))
chk('item sale = half', S.item_sell_price(iid) == tuple(v // 2 for v in S.item_price(iid)))
chk('no hand-written "half the price" left', alls.count('v // 2 for v in') == 0 and 'refund[k] += v // 2' not in alls
    and 'res[k] += v // 2' not in alls, alls.count('v // 2 for v in'))
a = {'resources': [10, 10, 10, 10, 10]}
chk('res_pay refuses without change', not S.res_pay(a, (11, 0, 0, 0, 0)) and a['resources'] == [10] * 5)
chk('res_pay pays', S.res_pay(a, (1, 2, 3, 4, 5)) and a['resources'] == [9, 8, 7, 6, 5])
S.res_add(a, (0.6, 0, 0, -1))
chk('res_add rounds to integers, shorter gains ok', a['resources'] == [10, 8, 7, 5, 5], a['resources'])
chk('no hand-written resource lists left', 'a["resources"] = [r - ' not in alls and 'a["resources"] = [r + ' not in alls)
# capture
told = []
S.notify_side = lambda nid, en, rgb=(0, 0, 0), zh_cn=None, zh_tw=None: told.append((nid, en))
w = S.world_state()
pid = next(int(k) for k in w['owners'] if int(k) not in S.CAPITALS.values())
w['owners'][str(pid)] = 2
S.set_province_owner = lambda p, n: w['owners'].__setitem__(str(p), n)
S.same_side = lambda x, y: bool(x) and bool(y) and (x == y or {x, y} == {2, 3})
told.clear()
chk('an ally\'s province is never taken', S.capture_province(pid, 3) is None and w['owners'][str(pid)] == 2)
old = S.capture_province(pid, 1)
chk('capture: owner changes, old owner returned', old == 2 and w['owners'][str(pid)] == 1, old)
chk('... the OLD side is told it was lost (not the new owner)', told and all(n == 2 for n, _t in told) and 'lost' in told[0][1], told)
chk('second winner of the same battle: no-op', S.capture_province(pid, 1) is None)
chk('every capture path uses capture_province', alls.count('capture_province(') >= 6
    and 'set_province_owner(pid, nat)' not in alls and 'set_province_owner(pid, A)' not in alls
    and 'set_province_owner(prov, side_nation(s))' not in alls)
chk('one side-notice loop', 'def notify_side' in alls and 'side_nation(o) == nation:' not in alls)
# hit formula
import damage_types as DT
chk('one hit formula', DT.hit_damage(100, 20, 2, 1) == max(1, int(100 - 20 * (100 + DT.ROWS[2][1][1]) / 100))
    and alls.count('(100 + t) / 100') == 0, alls.count('(100 + t) / 100'))
chk('walk time estimate in one place', alls.count('* 1.3 /') == 1)
B = {'members': [], 'targets': {1: {'hp': 50, 'npc': 1, 'nation': 4, 'put': {'st9': [0] * 9, 'kind': 1}},
                                2: {'hp': 0, 'put': {}}, 3: {'hp': 9, 'put': {'st9': [1] * 9, 'kind': 2}}}}
L = list(S.battle_units(B))
chk('battle_units lists the living server units (aliens: nation None)', len(L) == 2 and L[0][0] == 4 and L[1][0] is None, L)
chk('strength estimates use battle_units', src['/tmp/mp/sgs/npc_world.py'].count('in battle_units(B)') == 2)
