"""test95 (user 2026-10-28 12:53 / 12:56 "damaged in battle, full again in the Factory - solve it for real, one logic"):
sgs/unit_hp.py is the only HP rule.  Roster HP is kept in equipment units; the battle full HP carries the honor /
last-stand bonus; a wound keeps its SHARE across both; the client's 0x21 kind 2 is not an HP; repair = full."""
import os, sys, struct
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
S.LOG = open('/tmp/mp/server95.log', 'w', encoding='utf-8')
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
ACC = {'p': {'units': [{'uid': 5001, 'chassis': 'g004', 'items': []}, {'uid': 5002, 'chassis': 'g004', 'items': []}],
             'commander': {'nation': 1, 'honor': 500000}, 'resources': [10 ** 6] * 5}}
S.get_account = lambda acc: (ACC, ACC.get(acc, {}))
saved = []
S.save_accounts = lambda accs: saved.append(1)
S.npc_stand_mult = lambda nid: 1.0
u = ACC['p']['units'][0]
base = S.hp_base_full(u)
cur, full = S.hp_battle(ACC['p']['commander'], u)
chk('battle full HP carries the honor bonus', full > base, (base, full))
chk('an undamaged unit enters with its battle full HP', cur == full)
class Sx: pass
s = Sx(); s.acc = 'p'; s.put_args = {5001: {'hpmax': full}, 5002: {'hpmax': full}}
# the unit loses a little less than the bonus (the old bug: Factory showed it FULL)
wound = (full - base) // 2
S.hp_note(s, 5001, full - wound)
S.hp_store(s)
f = S.hp_frac(u)
chk('a small wound is kept in the roster (Factory not full)', 0 < f < 1 and 'hp' in u, (f, u.get('hp')))
chk('... the share is the battle share', abs(f - (full - wound) / full) < 0.002, (f, (full - wound) / full))
rec = S.build_units([S.roster_rec(u)])
a0, a1 = struct.unpack_from('>HH', rec, 3 + 4 + 2 + 2 + 12 + 3)
chk('Factory record: current < max', a1 < a0 and a0 == base, (a0, a1, base))
cur2, full2 = S.hp_battle(ACC['p']['commander'], u)
chk('next battle: same share of the battle full HP', abs(cur2 / full2 - f) < 0.002, (cur2, full2))
# honor grows: the wound share stays
ACC['p']['commander']['honor'] = 900000
cur3, full3 = S.hp_battle(ACC['p']['commander'], u)
chk('bonus changes, the wound share stays', full3 >= full2 and abs(cur3 / full3 - f) < 0.002, (cur3, full3))
ACC['p']['commander']['honor'] = 500000
# 0x21 kind 2 is not an HP
s2 = Sx(); s2.acc = 'p'; s2.targets = {}; s2.unit_hp = {}
m1 = bytes([0x21]) + struct.pack('>I', 5002) + bytes([2]) + struct.pack('>5H', 7, 7, 7, 7, 7)
src = open('/tmp/mp/sgs/packets.py', encoding='utf-8').read()
chk('0x21 kind 2 is ignored as HP (only kind 1)', 'len(m) >= 8 and m[5] == 1' in src)
# undamaged report clears the key; repair = full
S.hp_note(s, 5001, full); S.hp_store(s, [5001])
chk('full again -> no hp key', 'hp' not in u, u.get('hp'))
u['hp'] = base // 3
S.hp_repair(u)
cur4, full4 = S.hp_battle(ACC['p']['commander'], u)
chk('repair -> next battle at the battle full HP (not wounded by the bonus)', cur4 == full4 and S.hp_frac(u) == 1.0)
# dead stays dead
u2 = ACC['p']['units'][1]; u2['hp'] = 0
S.hp_note(s, 5002, 500); S.hp_store(s)
chk('a dead unit is not revived by a late report', u2['hp'] == 0)
# snapshot HP goes through the same writer
chk('snapshot HP uses hp_note', 'hp_note(o, uid, r["hp"])' in open('/tmp/mp/sgs/battle_maps.py', encoding='utf-8').read())
# one place: no other copies left
allsrc = ''.join(open(os.path.join('/tmp/mp/sgs', fn), encoding='utf-8').read() for fn in os.listdir('/tmp/mp/sgs') if fn.endswith('.py') and fn != 'unit_hp.py')
chk('no other HP rule copies', 'def hp_frac' not in allsrc and 'def unit_full_hp' not in allsrc and 'def _keep_hp' not in allsrc
    and 'unit_hp_c' not in allsrc and 'min(hp, u["hp"])' not in allsrc)
