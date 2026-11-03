"""test91 (user 2026-10-27 23:14 "NPCs should reinforce on their own, not only after an SOS; after an SOS faster"):
without any call idle NPCs come to a player's battle (more when the side is losing, one every NPC_AUTO_GAP s);
a player's call makes helpers already on the way hurry and new helpers march at NPC_SOS_RUSH x the time."""
import os, sys, time, random
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
for f in ('npcs.json', 'world.json'):
    if os.path.exists(f): os.remove(f)
import sgserver as S
S.LOG = open('/tmp/mp/server91.log', 'w', encoding='utf-8')
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
cap = S.CAPITALS[nid]
w = S.world_state()
for q in list(S.PORTAL_LINKS.get(cap % 100000, ()))[:2]:
    w['owners'][str((cap // 100000) * 100000 + q)] = nid
own = [int(k) for k, o in w['owners'].items() if int(o) == nid and int(k) not in S.CAPITALS.values()]
pid = own[0]
S.side_nation = lambda o: o.cmd['nation']
S.ally_client_ok = lambda o: True
defender, attacker = P(1), P(2)
attacker.put_args = {5002: {'st9': [5, 0, 100, 60, 200, 100, 0, 0, 100], 'hp': 3000, 'kind': 1}}
attacker.alive_units = {5002}; attacker.unit_hp = {5002: 3000}
B = S.BF.new_battle(map=pid, t0=now, targets={}, pocs={}, members={defender, attacker}, owner=attacker, defender=nid, opened=now)
S.BATTLES[pid] = B
going = lambda: [m for m in S.npc_all() if m['task'] and m['task'].get('target') == pid and m['nation'] == nid]
S.npc_auto_reinforce(now)
chk('without any call an NPC comes to help the losing side', len(going()) == 1, len(going()))
S.npc_auto_reinforce(now + 1)
chk('... the next one only after NPC_AUTO_GAP', len(going()) == 1)
for k in range(1, 8):
    S.npc_auto_reinforce(now + k * S.NPC_AUTO_GAP + 1)
chk('a losing side gets up to NPC_SURFACE_JOIN_MAX helpers', len(going()) == S.NPC_SURFACE_JOIN_MAX, len(going()))
g = going()[0]
left = g['task']['arrive'] - now
n_ = S.npc_rush_incoming(pid, nid, now)
chk('a call makes the helpers on the way hurry', n_ >= 1 and g['task']['arrive'] - now <= max(S.NPC_SOS_RUSH_MIN, left * S.NPC_SOS_RUSH) + 0.01,
    (left, g['task']['arrive'] - now))
chk('... only once', S.npc_rush_incoming(pid, nid, now) == 0)
for m in going(): m['task'] = None
before = {m['id'] for m in S.npc_all() if m['task']}
S.npc_sos_answer(B, pid, nid, None, now, helpers=2, rush=True)
new = [m for m in S.npc_all() if m['task'] and m['id'] not in before]
chk('a call brings helpers (one more than asked)', len(new) >= 3, len(new))
ok = all(m['task']['arrive'] - now <= S.reinf_seconds(len(m['task'].get('path') or [0, 0]) - 1) * S.NPC_SOS_RUSH * 1.1 + 1 for m in new)
chk('called helpers march at NPC_SOS_RUSH x the reinforcement time', ok,
    [(round(m['task']['arrive'] - now), len(m['task'].get('path') or ())) for m in new])
