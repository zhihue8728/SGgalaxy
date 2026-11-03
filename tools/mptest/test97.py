"""test97 (user 2026-10-28 13:30 / 13:32 "units move in jerks and snap back out of sync"; F47 reports: rollbacks
~2400-2600 ms late): a 0x50 Delayed Put stamped 3 s ahead made the client's clock controller (0x548f00, d > 100)
JUMP forward ~2.5 s, so every later command came "late".  delayed_put (battle_rules) is the one way now: sent AFTER
the wait, stamped game_time(receiver) + RELAY_DELAY like any command; cancelled when the unit / battle is gone."""
import os, sys, struct, time, asyncio, glob
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
S.LOG = open('/tmp/mp/server97.log', 'w', encoding='utf-8')
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
class W:
    def is_closing(self): return False
class P:
    def __init__(s, t0):
        s.w = W(); s.sent = []; s.t0 = t0; s.acc = 'p'; s.targets = {}
    def send(s, d, **k): s.sent.append(d)
async def main():
    t0 = time.monotonic()
    a, b = P(t0), P(t0 - 5)                       # two clients with different game clocks
    B = {"members": {a, b}, "won": False}
    a.battle = b.battle = B
    body = bytes([0x18]) + b'\x01\x02\x03'
    a.targets[777] = {}
    t_app = S.delayed_put(a, body, still=lambda: 777 in a.targets, delay_s=0.2)
    chk('returns the appear time', abs(t_app - (time.time() + 0.2)) < 0.05)
    await asyncio.sleep(0.05)
    chk('nothing sent before the wait', not a.sent and not b.sent)
    await asyncio.sleep(0.3)
    ok = True
    for o in (a, b):
        pk = [p for p in o.sent if p[:1] == b'\x50']
        L = struct.unpack_from('>I', pk[0], 1)[0] if pk else None
        gt = S.game_time(o)
        ok = ok and pk and -15 <= L - gt <= S.RELAY_DELAY + 2 and pk[0][5:] == body[1:]
    chk('sent after the wait to every member, stamped game_time + RELAY_DELAY of EACH receiver (no 3 s lead)', ok)
    a.sent.clear(); b.sent.clear()
    S.delayed_put(a, body, still=lambda: 778 in a.targets, delay_s=0.1)
    await asyncio.sleep(0.2)
    chk('unit gone meanwhile -> nothing sent', not a.sent and not b.sent)
    S.delayed_put(a, body, delay_s=0.1); B["won"] = True
    await asyncio.sleep(0.2)
    chk('battle over meanwhile -> nothing sent', not a.sent)
asyncio.run(main())
src = ''.join(open(f, encoding='utf-8').read() for f in glob.glob('/tmp/mp/sgs/*.py'))
chk('no 0x50 stamped ahead by REINFORCE_DELAY anywhere', 'game_time(s) + REINFORCE_DELAY' not in src and src.count('bytes([0x50]) + struct.pack') == 1)
chk('join replay skips squads still on their way', 'its delayed_put reaches the joiner too' in src and 'still on its way' in src)
