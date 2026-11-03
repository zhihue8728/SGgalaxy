"""F36 (2026-10-26, user: "controlling units, the picture freezes, then units teleport"): no clock freeze after a late order.

CLIENT BATTLE CLOCK (reverse engineered 2026-10-26, see claude/CLIENT_CLOCK.md):
  * T = timer_ms/10 - base  (base = [g+0x1c54], g = [0x6ba7c8]); the simulation tick [g+0x25a0] runs in 5-tick steps and
    004ad690 runs EVERY missed step at once until tick > T (catch-up loop 004ad710..004ade9d).
  * Empty 0x80 frames do not touch the clock (their time is stored at +0x29be4, which nothing reads).
  * Every ORDER lump (move / stop / attack / skill / death, 004dcc90 / 4dcd70 / 4dcec0 / 4dd6f0 / 4dd7b0) calls the clock
    controller 00548f00(L = order time):
      - L <  tick (the order came LATE): rollback 004a6160(L-5) (units restored from their history, lumps re-queued),
        tick = L rounded to 5, AND base += (tick - L + 5) - the clock is pushed back by the whole lateness, so the
        rolled-back battle stands still until real time has caught up (FREEZE), units first jump back (TELEPORT),
        and the slack w [0x6a5394] += 10 (max 50: the client then stays further behind = more order latency).
      - then: L - T < 10 -> base += 5 (brake); L - T > 100 -> jump; L - T > w -> base -= 5 (catch up).
  * TCP loss on the user's link (~1.5 stalls/s of ~1 rtt = 200+ ms in battle) delivers orders late again and again.
THE PATCH: at 00548f29 'sub eax, edi' (2B C7) -> 'xor eax, eax' (33 C0): the late branch now pushes the clock back only
5 ticks (the following 'add eax, 5'), the rollback stays, and the update loop re-simulates from L up to the present in the
same frame.  Result: no standing still, no backwards jump; only the units the late order touches are corrected (they
move on from where the order really started them).  Everything else (rollback, w, brake / catch-up) is unchanged.
usage: python patch_sg_debug_f36.py SG_debug.exe [more exes]   (idempotent)"""
import sys, struct, shutil
VA = 0x548f29
OLD = bytes.fromhex("2bc783c00550e8")          # sub eax,edi ; add eax,5 ; push eax ; call 005451e0
NEW = bytes.fromhex("33c083c00550e8")          # xor eax,eax ; add eax,5 ; push eax ; call 005451e0

def off(d, va):
    pe = struct.unpack_from("<I", d, 0x3c)[0]
    n = struct.unpack_from("<H", d, pe + 6)[0]
    opt = struct.unpack_from("<H", d, pe + 20)[0]
    for i in range(n):
        _nm, vs, sva, rs, ro = struct.unpack_from("<8sIIII", d, pe + 24 + opt + 40 * i)
        if 0x400000 + sva <= va < 0x400000 + sva + max(vs, rs):
            return va - 0x400000 - sva + ro
    raise SystemExit("VA not in any section")

for fn in sys.argv[1:]:
    d = bytearray(open(fn, "rb").read())
    o = off(d, VA)
    cur = bytes(d[o:o + len(OLD)])
    if cur == NEW:
        print(f"{fn}: F36 already applied"); continue
    if cur != OLD:
        raise SystemExit(f"{fn}: unexpected bytes at {VA:#x}: {cur.hex()}")
    shutil.copy(fn, fn + ".before_f36")
    d[o:o + 2] = NEW[:2]
    open(fn, "wb").write(d)
    print(f"{fn}: F36 applied at {VA:#x} (file {o:#x})")
