"""test88 (user 2026-10-27 22:12 "fewer NPC hunts - joining a surface battle comes first"): an idle NPC marches to a
running surface battle of its side (defence of its nation's province with players there / an attack of its nation)
before anything else; hunts are rare."""
import os, sys, time, random
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
for f in ('npcs.json', 'world.json'):
    if os.path.exists(f): os.remove(f)
import sgserver as S
S.LOG = open('/tmp/mp/server88.log', 'w', encoding='utf-8')
S.save_world = lambda w: None; S.npc_save = lambda force=False: None
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
random.seed(5)
now = time.time()
S.npc_tick(now)
nid = 1
act = [n for n in S.npc_of(nid) if n['state'] == 'active']
for n in act: n['task'] = None; n['rest_until'] = 0; n['think_at'] = 1e18; n['hl'] = None
S.NPC_SURFACE_JOIN = 1.0
class W:
    def is_closing(self): return False
class P:
    def __init__(s, nat):
        s.acc = 'p%d' % nat; s.cmd = {'nation': nat}; s.w = W(); s.lang = 'zh-cn'; s.enc = 'gbk'; s.spectator = False
        s.alive_units = {5001}; s.unit_pos = {5001: (1000, 1000)}; s.unit_hp = {5001: 500}
        s.put_args = {5001: {'st9': [5, 0, 100, 40, 200, 100, 0, 0, 100], 'hp': 500, 'kind': 1}}
        s.sent = []
    def send(s, d, **k): s.sent.append(d)
# 1. a defence: a province of nation 1 (not the capital) attacked by a player of nation 2
cap = S.CAPITALS[nid]
w = S.world_state()
for q in list(S.PORTAL_LINKS.get(cap % 100000, ()))[:2]:
    w['owners'][str((cap // 100000) * 100000 + q)] = nid      # two provinces next to the capital
own = [int(k) for k, o in w['owners'].items() if int(o) == nid and int(k) not in S.CAPITALS.values()]
chk('nation 1 has a province', bool(own), len(own))
pid = own[0]
defender, attacker = P(1), P(2)
S.side_nation = lambda o: o.cmd['nation']
S.ally_client_ok = lambda o: True
B = S.BF.new_battle(map=pid, t0=now, targets={}, pocs={}, members={defender, attacker}, owner=attacker, defender=nid, opened=now)
S.BATTLES[pid] = B
n = act[0]
S.npc_think(n, now)
t = n['task'] or {}
chk('idle NPC joins the defence of its province first', t.get('kind') == 'defend' and t.get('target') == pid, (t.get('kind'), t.get('target')))
chk('... its side is told when it arrives', any(b[:1] == b'*' for b in defender.sent))
del S.BATTLES[pid]
# 2. an attack of its nation's player on a neighbouring province
cand = S.npc_targets(nid, now)
chk('there is a province to attack', bool(cand))
tp = cand[0]['pid']
att, dfn = P(1), P(3)
B2 = S.BF.new_battle(map=tp, t0=now, targets={}, pocs={}, members={att, dfn}, owner=att, defender=S.province_owner(tp) or 0, opened=now)
S.BATTLES[tp] = B2
m = act[1]
S.npc_think(m, now)
t2 = m['task'] or {}
chk('idle NPC joins its player attacking next door (assist)', t2.get('kind') == 'attack' and t2.get('target') == tp and t2.get('assist'),
    (t2.get('kind'), t2.get('target'), t2.get('assist')))
# 3. per battle cap
S.NPC_SURFACE_JOIN_MAX = 2
S.NPC_JOIN_CHANCE = 0.0
for _p in S.NP.PERSONAS.values(): _p['follow'] = 0.0
S.npc_may_attack = lambda a, b: False; S.NPC_HUNT_CHANCE = 0.0; S.NPC_PATROL_CHANCE = 0.0
k = act[2]; S.npc_think(k, now)
k2 = act[3]; S.npc_think(k2, now)
same = [x for x in (k, k2) if x['task'] and x['task'].get('target') == tp and x['task'].get('assist')]
chk('at most NPC_SURFACE_JOIN_MAX NPCs per side and battle', len(same) <= 1, len(same))
del S.BATTLES[tp]
chk('hunts are rare', S.NPC_HUNT_MAX <= 3)
