"""patch_netlag2 (user 2026-10-22 23:12: "frame interval adaptive first"): the battle frame interval follows the link of
each player (TCP_INFO, sampled once a second):
  congested (>4 KB queued or >20 segments unacked, 3 samples in a row)   -> FRAME_MAX 100 ms (never pile frames onto a clogged link)
  retransmits in the last 10 s, or rtt variance >40 ms -> FRAME_MIN 33 ms (denser packets: duplicate ACKs come sooner,
                                                          a lost packet is recovered faster, the clock cap is fresher)
  otherwise                                          -> FRAME_MS 50 ms (66 ms when more than 200 players are online)
Slowing down is immediate, speeding up needs 3 good samples in a row (no flapping).  /lag adapt on|off, /lag net shows it."""
import sys
P = sys.argv[1] if len(sys.argv) > 1 else "server/sgserver.py"
src = open(P, encoding="utf-8").read()


def rep(old, new, cnt=1):
    global src
    if new in src:
        return
    n = src.count(old)
    assert n == cnt, (n, old[:90])
    src = src.replace(old, new)


rep('''FRAME_BACKLOG = 16384       # a frame is skipped while this many bytes are already queued for the connection
''', '''FRAME_BACKLOG = 16384       # a frame is skipped while this many bytes are already queued for the connection
FRAME_ADAPT = True          # per player frame interval from the link quality (frame_interval)
FRAME_MIN, FRAME_MAX = 33, 100
''')

rep('''def quickack(s):''', '''def frame_interval(s, now):
    """battle frame interval in ms for this player (see patch_netlag2): re-evaluated once a second."""
    fa = s.__dict__.setdefault("fa", {"ms": FRAME_MS, "t": 0.0, "retr": None, "retr_t": -99.0, "good": 0})
    if not FRAME_ADAPT:
        return FRAME_MS
    if now - fa["t"] < 1.0:
        return fa["ms"]
    fa["t"] = now
    st = tcp_stats(s)
    if not st:
        return fa["ms"]
    if fa["retr"] is not None and st["total_retrans"] > fa["retr"]:
        fa["retr_t"] = now
    fa["retr"] = st["total_retrans"]
    # a burst (battle entry sends dozens of packets) is not congestion: it must last 3 samples in a row
    fa["cong"] = fa.get("cong", 0) + 1 if (st["queued"] > 4096 or st["unacked"] > 20) else 0
    if fa["cong"] >= 3:
        want = FRAME_MAX
    elif now - fa["retr_t"] < 10 or st["var"] > 40:
        want = FRAME_MIN
    else:
        want = FRAME_MS if len(ONLINE) <= 200 else 66
    if want >= fa["ms"]:
        fa["ms"], fa["good"] = want, 0
    else:
        fa["good"] += 1
        if fa["good"] >= 3:
            fa["ms"], fa["good"] = want, 0
    return fa["ms"]

def quickack(s):''')

rep('''            nxt += FRAME_MS / 1000.0                     # absolute schedule: no drift, no 100-115 ms jitter
            now = loop.time()''', '''            now = loop.time()
            nxt += frame_interval(s, now) / 1000.0       # absolute schedule: no drift, no 100-115 ms jitter''')

rep('''                    s.send(chat_line(0x0A, f"{getattr(o, 'acc', '?')}: " + (
                        f"rtt {st['rtt']:.0f}+-{st['var']:.0f} ms, retransmits {st['total_retrans']}, unacked {st['unacked']}, "
                        f"queued {st['queued']} B" if st else "no TCP_INFO (not Linux)"), (120, 255, 120)))''',
    '''                    s.send(chat_line(0x0A, f"{getattr(o, 'acc', '?')}: " + (
                        f"rtt {st['rtt']:.0f}+-{st['var']:.0f} ms, retransmits {st['total_retrans']}, unacked {st['unacked']}, "
                        f"queued {st['queued']} B, frame {(getattr(o, 'fa', None) or {}).get('ms', FRAME_MS)} ms"
                        if st else "no TCP_INFO (not Linux)"), (120, 255, 120)))''')

rep('''            if len(parts) > 1 and parts[1] == "net":''', '''            if len(parts) > 2 and parts[1] == "adapt":
                global FRAME_ADAPT
                FRAME_ADAPT = parts[2] == "on"
            if len(parts) > 1 and parts[1] in ("net", "adapt"):''')

rep('''s.send(chat_line(0x0A, f"frame {FRAME_MS} ms, gc pauses''', '''s.send(chat_line(0x0A, f"frame {FRAME_MS} ms (adaptive {'ON' if FRAME_ADAPT else 'off'} {FRAME_MIN}-{FRAME_MAX}), gc pauses''')

open(P, "w", encoding="utf-8").write(src)
print("patched", P)
