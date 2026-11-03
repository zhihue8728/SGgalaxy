"""test90 (user 2026-10-27 22:54 "a wounded unit came into the battle with full HP, back home it was wounded again"):
PUT_UNIT +4 = MAX HP, the u16 near the end = CURRENT HP; a wounded unit gets its real max and its wounded current HP.
(22:56) a blockade opens a real battle at once (NPC_BLOCKADE_BATTLE); an NPC walks home only over own / allied land."""
import os, sys, struct
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
S.LOG = open('/tmp/mp/server90.log', 'w', encoding='utf-8')
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
b = S.build_put_unit(1234, 'Imp', 'acc', 100, 200, 1, 4, 1, hp=300, hp_max=1200, energy=500)
mx = struct.unpack_from('>H', b, 5 + 1 + len('Imp') + 1 + len('acc'))[0]
cur = struct.unpack_from('>H', b, len(b) - 10)[0]
chk('PUT max HP = the full HP', mx == 1200, mx)
chk('PUT current HP = the wounded HP', cur == 300, cur)
b2 = S.build_put_unit(1234, 'Imp', 'acc', 100, 200, 1, 4, 1, hp=300, energy=500)
chk('no hp_max: both the same (old behaviour for server units without one)', struct.unpack_from('>H', b2, 5 + 4 + 4)[0] == 300)
chk('player PUTs carry hpmax (enter_field / reinforcement / replay)', 'hp_max=s.put_args[uid]["hpmax"]' in open('/tmp/mp/sgs/results_field.py', encoding='utf-8').read()
    and 'hp_max=args.get("hpmax")' in open('/tmp/mp/sgs/battle_maps.py', encoding='utf-8').read())
chk('blockades open a real battle at once', S.NPC_BLOCKADE_BATTLE)
src = open('/tmp/mp/sgs/npc_world.py', encoding='utf-8').read()
chk('no walk home through enemy land', 'or _route(here, cap) or [here, cap]' not in src)
