"""test26: 0x27 sub 1 (another player's profile) is consumed EXACTLY by the client's reader order (FUN_004b4980 sub 1)."""
import os, sys, struct, time
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
def parse(d):
    o = 2
    def s8():
        nonlocal o
        n = d[o]; o += 1 + n
    def u(n):
        nonlocal o
        o += n
    s8(); u(1 + 4 + 2)            # name, nation, uid, k
    s8(); u(1)                    # title, u8
    for _ in range(4): u(1); s8(); u(2 + 8)
    u(1 + 12); n = d[o]; o += 1
    for _ in range(n): u(4); s8()
    u(4); s8(); ln = struct.unpack_from('>H', d, o)[0]; o += 2 + ln
    s8()                          # the extra string after the biography
    return o
for nm in ('jjjjjjjj',):
    acc, a = S.find_account_by_name(nm); d = S.build_user_info(acc, a)
    print(('PASS' if parse(d) == len(d) else 'FAIL'), 'player profile fully consumed', parse(d), len(d))
S.npc_tick(time.time())
n = S.npc_all()[5]
acc, a = S.find_account_by_uid(S.NPC_TOWN_BASE + n['id']); d = S.build_user_info(acc, a)
print(('PASS' if acc == n['name'] and parse(d) == len(d) else 'FAIL'), 'NPC profile fully consumed', parse(d), len(d))
