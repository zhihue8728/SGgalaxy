"""test84 (user 2026-10-27 "simplify the battle flow so this never happens again"): every attack order of a server
unit is built in sgs/unit_orders.py; both AIs leave through dispatch_orders; the attack guard turns a raw far-away
0x2B into a walk; the same chase rule serves aliens and NPC units."""
import os, re, sys, struct, glob
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
S.LOG = open('/tmp/mp/server84.log', 'w', encoding='utf-8')
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
# 1. source rules
pat = re.compile(r'bytes\(\[\s*0x2[bB]\s*\]\)|b"\\x2[bB]|0x2[bB]\]\)\s*\+\s*struct')
bad = []
for f in glob.glob('/tmp/mp/sgs/*.py') + glob.glob('/tmp/mp/*.py'):
    b = os.path.basename(f)
    if b in ('unit_orders.py',) or b.startswith('test') or b in ('mpclient.py', 'sgproto.py'):
        continue
    for i, l in enumerate(open(f, encoding='utf-8', errors='replace')):
        code = l.split('#', 1)[0]
        if pat.search(code) and 'm[:1] ==' not in code and '== b"\\x2b"' not in code:
            bad.append(f'{b}:{i + 1}: {l.strip()[:90]}')
chk('no attack lump 0x2B is built outside unit_orders.py', not bad, bad)
src = {os.path.basename(f): open(f, encoding='utf-8').read() for f in glob.glob('/tmp/mp/sgs/*.py')}
chk('alien AI and NPC AI leave through dispatch_orders', 'dispatch_orders(s, b, members, msgs, now, "alien AI")' in src['battle_flow.py']
    and 'dispatch_orders(s, b, members, msgs, now, "NPC AI")' in src['npc_battle.py'])
chk('no second order tail (server_orders_only + order_gate) outside unit_orders',
    all('order_gate(s, b, msgs' not in t for n, t in src.items() if n != 'unit_orders.py' and n != 'battle_rules.py'))
# 2. attack guard
class O:
    def __init__(s_): s_.sent = []; s_.unit_pos = {5001: (3000.0, 1000.0)}; s_.alive_units = {5001}; s_.hero_uid = None
    def send(s_, d, **k): s_.sent.append(d)
class Sess: pass
s = Sess(); s.targets = {}
o = O()
st9 = [10, 0, 100, 50, 200, 100, 0, 0, 100]
s.targets[60010] = {"hp": 500, "pos": (1000.0, 1000.0), "home": (1000.0, 1000.0), "state": "combat", "target": 5001,
                    "put": {"st9": st9, "spd": 20}, "name": "Ubik"}
s.targets[60011] = {"hp": 500, "pos": (2900.0, 1000.0), "home": (2900.0, 1000.0), "state": "combat", "target": 5001,
                    "put": {"st9": st9, "spd": 20}, "name": "Ubik"}
S.game_time = lambda x: 1000
out = S.dispatch_orders(s, None, [o], [S.attack_lump(60010, 5001), S.attack_lump(60011, 5001)], 100.0, "test")
kinds = {struct.unpack_from('>I', m, 1)[0]: m[0] for m in out}
chk('attack guard: a raw far 0x2B goes out as a MOVE (walk animation)', kinds.get(60010) == 0x1A and s.targets[60010].get("chase"), kinds)
chk('attack guard: an in-range 0x2B passes unchanged', kinds.get(60011) == 0x2B, kinds)
chk('the orders reached the member in one lump packet', len(o.sent) == 1 and o.sent[0][0] == 0x80)
# 3. one rule for aliens and NPC units
for name, extra in (('alien', {}), ('NPC unit', {"npc": 7})):
    tg = dict({"hp": 500, "pos": (0.0, 0.0), "state": "idle", "target": None, "put": {"st9": st9, "spd": 20}}, **extra)
    m = []
    walked = []
    mover = (lambda t_, g_, d_, n_, m_: (walked.append(d_), S._plain_move(t_, g_, d_, n_, m_))) if extra else None
    r = S.order_attack(60020, tg, 5001, (2000.0, 0.0), 50.0, m, mover)
    chk(f'{name}: out of range -> walks first', r is False and m and m[0][0] == 0x1A and tg.get("chase") and (walked or not extra))
    S.snapshot_pos(tg, (1900.0, 0.0), 80.0)
    m = []
    S.chase_step(60020, tg, (2000.0, 0.0), 80.5, m, mover)
    chk(f'{name}: in range after the walk -> 0x2B', len(m) == 1 and m[0][0] == 0x2B and not tg.get("chase"))
