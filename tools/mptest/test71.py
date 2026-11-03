"""test71 (user 2026-10-26 12:42): national treasury shown in the FHQ Domestic Policy window grows each income cycle;
simulation: different nations start apart; force open ignored from the sim board."""
import sys, os
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
for f in ('npcs.json', 'world.json'):
    if os.path.exists(f): os.remove(f)
import sgserver as S
S.LOG = open('/tmp/mp/t_treasury.log', 'w', encoding='utf-8')
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
S.world_state()
nid = 1
p = S.politics(nid); p['treasury'] = [0] * 5
add = S.nation_revenue(nid)
chk('revenue is positive for a nation with provinces', add[0] > 0 and all(a >= 0 for a in add), add)
chk('treasury holds it', S.politics(nid)['treasury'] == add)
S.nation_revenue(nid)
chk('second cycle adds again', S.politics(nid)['treasury'][0] == 2 * add[0])
S.politics(nid)['tax'] = [0, 0, 0]
t0 = list(S.politics(nid)['treasury']); S.nation_revenue(nid)
chk('0 % tax adds nothing', S.politics(nid)['treasury'] == t0)
d = S.build_domestic(nid)
import struct
chk('Domestic Policy packet carries the treasury', struct.pack('>I', t0[0]) in d)
