"""test44: allied NPCs that answer a call for help really enter the running battle (user 2026-10-24 05:58: they said
"on my way" and then stood in the next province).  Enemy defenders on the map do not use up the allies' slots; a full
battle (NPC_JOIN_SIDE_MAX commanders of the SAME side with units) sends no helpers (10-31: no waiting outside)."""
import sys, os, time, random
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
for f in ('npcs.json', 'world.json'):
    if os.path.exists(f): os.remove(f)
import sgserver as S
S.LOG = open('/tmp/mp/server44.log', 'w', encoding='utf-8')
S.spawn = lambda c: (c.close() if hasattr(c, 'close') else None)
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
random.seed(1)
now = time.time()
S.npc_tick(now)
S.npc_sync = lambda *a, **k: None
SAID = []
_say = S.npc_say
S.npc_say = lambda nid, n, key, texts, now_, **k: SAID.append((key[0], n['name'], texts('zh-tw'))) or True
X = 1
PL = S.nation_planet(X)
Y = next(n for n, *_ in S.NATIONS if n != X and S.nation_planet(n) == PL and not S.same_side(n, X))
C = S.CAPITALS[X]
q1 = PL * 100000 + sorted(S.PORTAL_LINKS[C % 100000])[0]
S.set_province_owner(q1, X)
P = next(PL * 100000 + q for q in sorted(S.PORTAL_LINKS[q1 % 100000])
         if PL * 100000 + q != C and PL * 100000 + q not in S.CAPITALS.values())
S.set_province_owner(P, Y)
class W:
    def is_closing(self): return False
class Pl:
    def __init__(s):
        s.acc = 'SG001'; s.cmd = {'nation': X}; s.w = W(); s.battle_gen = 1; s.spectator = False
        s.client_hash = 'x'; s.client_release = '9.9.9'; s.targets = {}; s.logged_in = True
        s.alive_units = set(); s.unit_hp = {}; s.map = P
    def send(s, *a, **k): pass

def scenario(fill_nation, n_fill):
    for m in S.npc_all():
        m['state'] = 'active'; m['rest_until'] = 0; m['task'] = None
    S.BATTLES.clear(); SAID.clear()
    pl = Pl()
    B = S.BF.new_battle(map=P, t0=0, targets=pl.targets, members={pl}, owner=pl, defender=Y,
                        pocs={1: {'x': 500, 'y': 500, 'strength': 10, 'progress': 10, 'owner': Y, 'capturing': False}})
    pl.battle = B
    S.BATTLES[P] = B
    fill = [m for m in S.npc_of(fill_nation)][-n_fill:] if n_fill else []
    for k, m in enumerate(fill):                 # commanders already fighting there, each with one living unit
        m['task'] = {'kind': 'defend' if fill_nation == Y else 'attack', 'target': P, 'phase': 'battle', 'since': now}
        B.setdefault('npc_ids', []).append(m['id'])
        B['targets'][90000 + k] = {'npc': m['id'], 'nation': fill_nation, 'hp': 100}
        S.NPC_RT[m['id']] = {'B': B, 'dead': 0, 'units': 1, 'used': set()}   # really on the map
    before = {m['id'] for m in S.npc_all() if m.get('task')}
    S.npc_sos_answer(B, P, X, None, now)
    went = [m for m in S.npc_all() if m.get('task') and m['id'] not in before and m['nation'] == X]
    entered, first_back = set(), None
    for dt in range(10, 1200, 10):
        S.npc_tick(now + dt)
        for m in went:
            if m.get('task') and m['task'].get('phase') == 'battle' and m['task'].get('target') == P and m['id'] in B['npc_ids']:
                entered.add(m['name'])
        if first_back is None and any(not m.get('task') for m in went):
            first_back = dt
    return went, entered, first_back

went, entered, _ = scenario(Y, 8)
chk('helpers answer the call', len(went) >= 1, [m['name'] for m in went])
chk('8 ENEMY defenders on the map: the helpers still enter', entered == {m['name'] for m in went}, entered)
# (2026-10-31 11:48 / 12:36 "the NPCs only watch from outside", "full: open another battlefield"): cap 12, and a full
# side gets no helpers at all - nobody marches over to wait outside
went, entered, back = scenario(X, S.NPC_JOIN_SIDE_MAX)
chk('a full side (NPC_JOIN_SIDE_MAX commanders with units): no helper marches over to watch', not went and not entered,
    [m['name'] for m in went])
went, entered, back = scenario(X, S.NPC_JOIN_SIDE_MAX - 2)
chk('... 2 slots free: at most 2 helpers, and they enter', 1 <= len(went) <= 2 and entered == {m['name'] for m in went},
    ([m['name'] for m in went], entered))
went, entered, _ = scenario(X, 0)
chk('empty battle: helpers enter', entered == {m['name'] for m in went} and went, entered)
# (user 2026-10-24 07:16) helpers and defenders march at the same fixed pace: NPC_REINF_STEP s per province, and the
# ETA in the reply is exactly that
for m in S.npc_all():
    m['state'] = 'active'; m['rest_until'] = 0; m['task'] = None
S.BATTLES.clear()
pl = Pl()
B = S.BF.new_battle(map=P, t0=0, targets=pl.targets, members={pl}, owner=pl, defender=Y,
                    pocs={1: {'x': 500, 'y': 500, 'strength': 10, 'progress': 10, 'owner': Y, 'capturing': False}})
pl.battle = B
S.BATTLES[P] = B
before = {m['id'] for m in S.npc_all() if m.get('task')}
S.npc_sos_answer(B, P, X, None, now)
hs = [m for m in S.npc_all() if m.get('task') and m['id'] not in before]
chk('helper ETA = NPC_REINF_STEP x provinces x 0.85-1.3 (+0-25 s, 16:39 random)', hs and all(S.NPC_REINF_STEP * (len(m['task']['path']) - 1) * 0.84 <= m['task']['arrive'] - now <= S.NPC_REINF_STEP * (len(m['task']['path']) - 1) * 1.31 + 25.1
                                                         for m in hs), [(m['task']['arrive'] - now, len(m['task']['path'])) for m in hs])
d = next(m for m in S.npc_of(Y) if not m.get('task'))
tk = S.npc_reinf_task('defend', Y, P, now, d)
chk('defender reinforcement: the same pace', tk is None or abs(tk['arrive'] - now - S.NPC_REINF_STEP * (len(tk['path']) - 1)) < 0.01, tk)
# (user 2026-10-24 11:42) a call during the cool-down gets an answer instead of silence
S._HEAR_T.clear()
pl2 = Pl(); pl2.acc = 'hhhhhhhh'; pl2.sent = []; pl2.send = lambda d, *a, **k: pl2.sent.append(bytes(d)); pl2.battle = None
S.npc_hear(pl2, '幫')
n0 = len(pl2.sent)
S.npc_hear(pl2, '幫忙')
chk('call during the cool-down: the player is told when he can call again',
    len(pl2.sent) > n0 and any('可以再喊'.encode('utf-8') in d or b'call again' in d or b'\xa5i\xa5H' in d for d in pl2.sent[n0:]),
    [d[:60] for d in pl2.sent[n0:]])
