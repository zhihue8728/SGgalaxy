"""test53 (user 2026-10-24 22:04): ORDER GATE - server orders of the AIs are coalesced per unit, repeats dropped, at
most ORDER_BUDGET per battle and second (skills, attacks, then moves; the rest waits)."""
import sys, os, struct
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
S.LOG = open('/tmp/mp/server53.log', 'w', encoding='utf-8')
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
class P: pass
s = P(); s.targets = {60001 + i: {} for i in range(200)}; s.map = 600001
b = {}
mv = lambda u, x: bytes([0x1A]) + struct.pack(">IHH", u, x, 100) + b"\0\0\0"
at = lambda u, t: bytes([0x2B]) + struct.pack(">II", u, t)
sk = lambda u: bytes([0x30]) + struct.pack(">I", u) + bytes([9, 1])
out = S.order_gate(s, b, [mv(60001, 10), mv(60001, 500), at(60002, 7)], 100.0)
chk("latest intent per unit only", mv(60001, 10) not in out and mv(60001, 500) in out and at(60002, 7) in out, len(out))
out = S.order_gate(s, b, [mv(60001, 500)], 101.0)
chk("same order again within ORDER_REPEAT_S dropped", out == [], out)
out = S.order_gate(s, b, [mv(60001, 500)], 106.0)
chk("... sent again after it", out == [mv(60001, 500)], out)
many = [mv(60010 + i, 50 + i) for i in range(60)] + [at(60100, 1), sk(60101)]
out = S.order_gate(s, b, many, 200.0)
chk("budget per second", len(out) == S.ORDER_BUDGET, len(out))
chk("skills and attacks first", out[0] == sk(60101) and out[1] == at(60100, 1), out[:2])
out2 = S.order_gate(s, b, [], 201.0)
chk("the rest goes next second", len(out2) == 62 - S.ORDER_BUDGET, len(out2))
s.targets.pop(60005)
S.order_gate(s, b, [], 300.0)
out = S.order_gate(s, b, [mv(60005, 9)], 300.0)
chk("orders of units that are gone are dropped", out == [], out)
chk("other lumps pass", S.order_gate(s, b, [bytes([0x23, 0, 0, 0, 1])], 400.0) == [bytes([0x23, 0, 0, 0, 1])])
