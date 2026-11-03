"""test63 (2026-10-25 audit): battle context hand-off, NPC-battle winners, join replay, NPC fallback removal."""
import sys, os, time, struct, asyncio
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
for f in ('npcs.json', 'world.json'):
    if os.path.exists(f): os.remove(f)
import sgserver as S
import battlefield as BF
S.LOG = open('/tmp/mp/server63.log', 'w', encoding='utf-8')
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
class W:
    def is_closing(self): return False
class P:
    def __init__(s, acc, nat):
        s.acc, s.cmd, s.w, s.sent, s.lang, s.enc = acc, {'nation': nat}, W(), [], 'en', 'latin-1'
        s.t0 = time.monotonic(); s.spectator = False
    def send(s, d): s.sent.append(d)
# 1. judge: NPC attackers (nation 2) lose against defender 1; a third-party player (3) is not a winner
same = lambda a, b: bool(a) and bool(b) and S.same_side(a, b)
view = {"npc_attacker": 2, "same": same, "members": [("d", 1, False), ("x", 3, False), ("a", 2, False)],
        "pocs": [1, 1], "defender": 1, "event": "time"}
r = BF._judge_npc(view)
chk('time up, defender holds the POCs: attackers lost', r and not r['att_won'], r and r['why'])
chk('... winner = defender player only (third party and attacker are not)', r and r['won'] == {'d': True, 'x': False, 'a': False}, r and r['won'])
view2 = dict(view, event="tick", pocs=[3, 3])
r2 = BF._judge_npc(view2)
chk('third side holds every POC -> it wins', r2 and r2['won'].get('x') and not r2['won'].get('d'), r2 and r2.get('won'))
# 2. context hand-off: the session the loop ran on leaves, the battle runs on a stand-in with the SAME state
async def t2():
    a, b_ = P('aa', 1), P('bb', 1)
    T, pocs = {60001: {'hp': 10, 'x': 1, 'y': 1}}, {}
    a.targets, a.pocs, a.alien_meta = T, pocs, {'raid': True}
    B = {'map': 600005, 'targets': T, 'pocs': pocs, 'members': {b_}, 't0': a.t0, 'owner': b_, '_loop_s': a}
    S.BATTLES[600005] = B
    S.battle_ctx_handoff(a, B)
    ctx = B.get('ctx')
    chk('stand-in created', ctx is not None and getattr(ctx, 'is_ghost', False))
    chk('... same targets / POCs objects, meta kept', ctx is not None and ctx.targets is T and ctx.pocs is pocs and ctx.alien_meta == {'raid': True})
    chk('battle meta read from the stand-in (joiner owner has none)', S._battle_meta(b_, B) == {'raid': True})
    chk('battle_ctx() returns it', S.battle_ctx(B) is ctx)
    S.battle_ctx_handoff(b_, B)
    chk('another member leaving does not hand over again', B.get('ctx') is ctx)
    S.BATTLES.pop(600005, None)
    await asyncio.sleep(0)
asyncio.run(t2())
# 3. join replay: a cloaked NPC that walks gets cloak + its move in one lump, and the POC state
s = P('jj', 1)
now = time.time()
B = {'targets': {60010: {'put': {'name': 'x'}, 'hp': 5, 'cloaked': True, 'mv': ((0, 0), (300, 400), now - 1, now + 9)},
                 60011: {'put': {'name': 'y'}, 'hp': 5, 'state': 'combat', 'target': 1022}},
     'pocs': {7: {'progress': 50, 'owner': 2, 'capturing': True}}, '_ord_last': {1: 2}}
S.join_replay(s, B)
lump = [p for p in s.sent if p[0] == 0x80]
body = b''.join(lump)
chk('one lump with cloak (0x30 .. 15 1)', lump and (bytes([0x30]) + struct.pack('>I', 60010) + bytes([15, 1])) in body)
chk('... the current move (0x1A to 300,400)', (bytes([0x1A]) + struct.pack('>IHH', 60010, 300, 400)) in body)
chk('... the current attack (0x2B)', (bytes([0x2B]) + struct.pack('>II', 60011, 1022)) in body)
chk('POC state 0x49 sent', any(p[0] == 0x49 for p in s.sent))
chk('order gate memory cleared', '_ord_last' not in B)
async def t4():
    # 4. a forged 0x1e for a healthy NPC unit is not believed; a worn-down one is; the snapshot confirms
    q = P('qq', 1); q.targets = {}; q.battle_gen = 1; q.alive_units = set(); q.unit_pos = {}
    Bq = {'map': 600009, 'targets': q.targets, 'members': {q}, 'pocs': {}, 'dead_aliens': set()}
    q.battle = Bq; q.map = 600009
    q.targets[60020] = {'npc': 5, 'hp': 100, 'max': 100, 'nation': 2, 'level': 3}
    r = S.alien_died(q, 60020)
    chk('forged death of a healthy, never-hit NPC unit: not believed', r is False and 60020 in q.targets)
    q.targets[60020]['hp'] = 30
    S.alien_died(q, 60020)
    chk('worn-down NPC unit (model 30 %): removed', 60020 not in q.targets)
    q.targets[60021] = {'npc': 5, 'hp': 100, 'max': 100, 'nation': 2, 'level': 3}
    S.alien_died(q, 60021, confirmed=True)
    chk('confirmed by the snapshot: removed', 60021 not in q.targets)
    # 5. snapshot accepted only from the client that was asked
    Bq['snap_who'], Bq['snap_req'] = None, time.time()
    S.apply_snapshot(q, b'\x00' * 40)
    chk('unrequested snapshot ignored (no snap_n)', 'snap_n' not in Bq)
    # 6. loss ratio: units that walked out are not counted
    S.NPC_RT[777] = {'B': Bq, 'nid': 2, 'dead': 2, 'units': 10, 'left': 6}
    Bq['npc_attacker'] = 2
    v = S.battle_view(None, Bq, 'time')
    chk('loss ratio = dead / (units - walked out)', abs(v.get('att_loss', 0) - 0.5) < 1e-6, v.get('att_loss'))
    S.NPC_RT.pop(777, None)
    # 7. join replay: switched-on modes
    s2 = P('j2', 1)
    B2 = {'targets': {60030: {'put': {'name': 'z'}, 'hp': 5, 'modes': {9: True, 40: False}}}, 'pocs': {}}
    S.join_replay(s2, B2)
    body2 = b''.join(p for p in s2.sent if p[0] == 0x80)
    chk('bombArd on replayed, shield off not', (bytes([0x30]) + struct.pack('>I', 60030) + bytes([9, 1])) in body2
        and (bytes([0x30]) + struct.pack('>I', 60030) + bytes([40, 1])) not in body2)
    await asyncio.sleep(0)
asyncio.run(t4())
