"""test43: carry weight sent with the unit records follows the account's Mech even when several accounts are online
(was 60 instead of 120 on build_units calls without mech= once MECH_APT held 2 accounts)."""
import os, sys, struct
os.chdir('/tmp/mp'); sys.path.insert(0, '/tmp/mp')
import sgserver as S
def chk(n, ok, i=''): print(('PASS ' if ok else 'FAIL ') + n, i, flush=True)
cmd = S.PG.ensure_commander({})
cmd['attrs'] = [0, 0, 0, 120]
S.get_account = lambda acc: ({}, {"commander": cmd, "units": []})
class Sess: acc = "x"
S.MECH_APT.clear(); S.MECH_APT.update({"x": 120, "y": 0})
chassis = "Imp"
base = int(S.UNIT_MANUAL[chassis.lower()]["max_weight_kg"])
chk('mech_for reads the account Mech', S.mech_for(Sess()) == S.PG.attr(cmd, 3), S.mech_for(Sess()))
def wcap(pk):
    # record: u32 id, u8, u8, u16, then 3 x u32: max weight first
    return struct.unpack_from('>I', pk, 2 + 4 + 2 + 2)[0] if pk[1] != 1 else struct.unpack_from('>I', pk, 3 + 4 + 2 + 2)[0]
rec = [(1, chassis, chassis)]
w_with = wcap(S.build_units(rec, sub=2, mech=S.mech_for(Sess())))
w_old = wcap(S.build_units(rec, sub=2))
chk('with mech_for: base x (1 + Mech/120)', w_with == int(base * (1 + S.PG.attr(cmd, 3) / 120)), (base, w_with))
chk('the old default (2 accounts online) gave the wrong value - reason of the bug', w_old != w_with, w_old)
