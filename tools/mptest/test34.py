"""test34: NPC doctrine (main kind + second kind + capturers, old rosters re-formed, renewal keeps it, battle units grouped
by kind) and F7-like squads (next squad when half a squad is left, cooldown, until the reserve is empty)."""
import asyncio, sys, os, time, random, collections
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
for f in ('npcs.json', 'world.json'):
    if os.path.exists(f): os.remove(f)
import sgserver as S
NP = S.NP
S.LOG = open('/tmp/mp/server34.log', 'w', encoding='utf-8')
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
random.seed(3)
pool = S.npc_pool()
n = NP.new_npc(11, 2, 99999, set(), pool)
d = n['doctrine']; c = collections.Counter(k for k, _l in n['squad'])
nf = NP.fast_count(len(n['squad']))
chk('new NPC has a doctrine', set(d) == {'main', 'second', 'fast'}, d)
chk('main kind is the biggest block', c[d['main']] >= (len(n['squad']) - nf) * 0.6, c)
chk('at most 3 kinds', len(c) <= 3, c)
chk('capturers first', all(k == d['fast'] for k, _l in n['squad'][:nf]))
old = {'level': 30, 'squad': [[random.choice(pool)['code'], 30] for _ in range(20)]}
lv = sorted(l for _c, l in old['squad'])
chk('old roster re-formed', NP.ensure_doctrine(old, 2, pool) and len(old['squad']) == 20 and
    sorted(l for _c, l in old['squad']) == lv and len({k for k, _l in old['squad']}) <= 3)
chk('only once', not NP.ensure_doctrine(old, 2, pool))
for _ in range(20): NP.refresh(n, 2, pool)
c2 = collections.Counter(k for k, _l in n['squad'])
chk('20 renewals keep the doctrine shape', c2[n['doctrine']['main']] >= (len(n['squad']) - NP.fast_count(len(n['squad']))) * 0.4
    and len(c2) <= 4, c2)
n['hl'] = None; n['squad'] = [[k, 30] for k, _l in n['squad']]
u = S.npc_battle_units(n, 12, 11)
kinds = [x[0] for x in u]
blocks = sum(1 for i in range(1, len(kinds)) if kinds[i] != kinds[i - 1]) + 1
chk('battle units come in blocks of one kind', blocks <= 3, kinds)
# F7 squads
class FakeS: pass
s = FakeS(); s.targets = {}
b = {'map': 200101}
n['squad'] = [[k, 30] for k, _l in n['squad']][:30] + [[n['doctrine']['main'], 30]] * max(0, 30 - len(n['squad']))
n['hl'] = None
S.npc_state()['npcs'][str(n['id'])] = n
sent = []
S.npc_put_units = lambda s_, nid, n_, units, *a, **k: [sent.append(x) or S.NPC_RT[n_['id']]['used'].add(x[6]) for x in units] or [s_.targets.__setitem__(len(s_.targets) + 1 + random.random(), {'npc': n_['id'], 'hp': 10}) for x in units]
S.NPC_RT[n['id']] = {'B': b, 'dead': 0, 'units': 6, 'used': set(range(6)), 'waves': 0, 'wave_t': 0, 'per': 6, 'home': (0, 0),
                     'mode': 'hold', 'poc': None, 'nid': 11}
for i in range(6): s.targets[i] = {'npc': n['id'], 'hp': 10}
t = 1000.0
S.npc_fresh_wave(s, b, t)
chk('no squad before the first cooldown', not sent)
S.npc_fresh_wave(s, b, t + 61)
chk('no squad while the units live', not sent)
for i in range(4): s.targets[i]['hp'] = 0
S.npc_fresh_wave(s, b, t + 62)
chk('half a squad left -> next squad (deploy size)', len(sent) == 6, len(sent))
for k in s.targets: s.targets[k]['hp'] = 0
S.npc_fresh_wave(s, b, t + 70)
chk('cooldown between squads', len(sent) == 6)
waves = 1
s.targets[0]['hp'] = 10                       # one unit stays alive (a wiped-out NPC gets no more squads, below)
for j in range(10):
    for k in list(s.targets)[1:]: s.targets[k]['hp'] = 0
    S.npc_fresh_wave(s, b, t + 140 + 70 * j)
chk('squads until the reserve is empty', len(sent) >= 20 and S.NPC_RT[n['id']]['waves'] == S.NPC_WAVES_MAX, (len(sent), S.NPC_RT[n['id']]['waves']))
# user 2026-10-24 04:30: a wiped-out NPC (no unit left) sends no more squads
S.NPC_RT[n['id']].update(waves=0, wave_t=1)
for k in s.targets: s.targets[k]['hp'] = 0
n0 = len(sent)
S.npc_fresh_wave(s, b, t + 5000)
chk('wiped out -> no more squads (the commander leaves the battle, 2026-10-24)', len(sent) == n0 and S.NPC_RT.get(n['id'], {}).get('waves', S.NPC_WAVES_MAX) == S.NPC_WAVES_MAX, (len(sent) - n0,))
