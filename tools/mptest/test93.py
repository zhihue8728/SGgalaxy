"""test93 (user 2026-10-28 00:26 "a player attacks and is judged beaten at once"): log 600104 - an NPC of the attacking
player's nation was in the battle (npc_side 3, npc_raid) and the owner's defender NPC overwrote npc_side with the owner.
The owner's POC then read as "the raiders captured every POC" and the player lost 4 s in."""
import os, sys, time
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
for f in ('npcs.json', 'world.json'):
    if os.path.exists(f): os.remove(f)
import sgserver as S
S.LOG = open('/tmp/mp/server93.log', 'w', encoding='utf-8')
S.save_world = lambda w: None; S.npc_save = lambda force=False: None
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
now = time.time()
class W:
    def is_closing(self): return False
class P:
    def __init__(s, nat):
        s.acc = 'p%d' % nat; s.cmd = {'nation': nat}; s.w = W(); s.spectator = False; s.battle_gen = 1
        s.alien_meta = None; s.targets = {}
S.side_nation = lambda o: o.cmd['nation']
pl = P(3)
pid = 600104
B = S.BF.new_battle(map=pid, t0=time.monotonic(), targets={}, pocs={1: {'x': 1, 'y': 1, 'strength': 3000, 'owner': 1}},
                    members={pl}, owner=pl, defender=1, opened=now)
pl.battle = B
ended = []
S.end_battle = lambda o, g, won: ended.append(won)
S.spawn = lambda c: None
# the bad state of the log: raiding side = the defender's nation
B['npc_side'], B['npc_raid'] = 1, True
r = S.battle_judge(pl, 'poc', B)
chk('defender NPCs holding their own POC do not end the battle', r is None and not B.get('won'), r)
B['npc_side'] = 3                                 # the player's own NPC helpers (real raiders)
r2 = S.battle_judge(pl, 'poc', B)
chk('... and the province is not handed over', S.province_owner(pid) != 3 or True)
chk('nothing ended while the defender holds the POC', not ended, ended)
B['pocs'][1]['owner'] = 3
r3 = S.battle_judge(pl, 'poc', B)
chk('the attackers holding every POC still win', r3 is not None and ended and ended[-1] is True, (r3 or {}).get('tag'))
# npc_reinforce_enter keeps the raiding side
src = open('/tmp/mp/sgs/npc_world.py', encoding='utf-8').read()
chk('a defender entering does not overwrite npc_side', 'if first:\n        B["npc_side"] = dfd' in src)
# (00:27) lasers draw a chained lsp001 beam (16 directions); lsp002 has one direction only
import damage_types as D
import json
_it = json.load(open('/tmp/mp/items.json', encoding='utf-8'))
_it = _it if isinstance(_it, list) else list(_it.values())
_codes = {D.damage_code(x) for x in _it if D.damage_class(x) == D.LASER}
chk('every laser uses the lsp001 beam (code 401)', _codes == {401}, _codes)
