"""Robust .xpf frame reader for the 3D art pipeline (wraps the format in tools/xpf.py).
- type & 0x10 = mask-only frames (shadows / footprints): runs carry no pixel data.
- the offset table may be shorter than rows*24+1 dwords; frames past the table are ignored.
- type & 0x04 = each frame starts with muzzle points: u8 n, n x (u16 x, u16 y) in sprite pixels.
- frames that fail to decode or have no pixels are reported as empty."""
import struct
import numpy as np
COLS = 24
def info(b):
    t, w, h, cx, cy = struct.unpack('<5H', b[:10])
    return dict(type=t, w=w, h=h, cx=cx, cy=cy, rows=b[13], flags=list(b[10:13]))
def offsets(b):
    """Frame offsets.  The table starts at byte 14 and ends at the entry equal to the file size
    (the header's 'rows' byte only bounds it: rows*24+1 dwords at most)."""
    rows = b[13]; mx = min(rows * COLS + 1, (len(b) - 14) // 4)
    offs = []
    for i in range(mx):
        v = struct.unpack_from('<I', b, 14 + 4 * i)[0]
        if offs and (v < offs[-1] or v > len(b)): break
        offs.append(v)
        if v == len(b): break
    return offs
def frame(b, k, offs=None, inf=None, want_pts=False):
    inf = inf or info(b); offs = offs or offsets(b)
    w, h = inf['w'], inf['h']; mask = bool(inf['type'] & 0x10)
    if k + 1 >= len(offs): return None
    s, e = offs[k], offs[k + 1]
    if not (0 <= s < e <= len(b)) or e - s < 3: return None
    f = b[s:e]; a = np.zeros((h, w, 4), np.uint8)
    p = 0; pts = []
    if inf['type'] & 0x04:                      # muzzle points: u8 n, n x (u16 x, u16 y)
        n = f[0]; p = 1
        for i in range(n):
            pts.append(struct.unpack_from('<2H', f, p)); p += 4
    top, bot = f[p], f[p + 1]; p += 2
    if top + bot > h: return None
    try:
        for y in range(top, h - bot):
            x = 0
            while x < w and p < len(f):
                x += f[p]; p += 1
                if x >= w: break
                n = f[p]; p += 1
                if mask:
                    a[y, x:min(w, x + n)] = (0, 0, 0, 128)
                else:
                    if p + 2 * n > len(f): return None
                    v = np.frombuffer(f[p:p + 2 * n], '<u2').astype(np.uint32); p += 2 * n
                    m = min(n, w - x)
                    v = v[:m]
                    a[y, x:x + m, 0] = ((v >> 11) & 31) * 255 // 31
                    a[y, x:x + m, 1] = ((v >> 5) & 63) * 255 // 63
                    a[y, x:x + m, 2] = (v & 31) * 255 // 31
                    a[y, x:x + m, 3] = 255
                x += n
    except Exception:
        return None
    if not a[:, :, 3].any(): return None
    return (a, pts) if want_pts else a
def frames(b, want_pts=False):
    inf = info(b); offs = offsets(b); out = {}
    for k in range(len(offs) - 1):
        r = frame(b, k, offs, inf, want_pts)
        if r is not None: out[k] = r
    return inf, out

def _iou(a, b):
    a = a[:, :, 3] > 0; b = b[:, :, 3] > 0
    return float((a & b).sum()) / max(1, int((a | b).sum()))
def layout(frs):
    """Guess the frame layout from the decoded frames (list in index order).
    Frames are stored frame-major: index = f * dirs + d (same direction repeats every `dirs`).
    Returns dict(dirs, frames, order, score) where score = mean IoU at lag dirs vs lag 1."""
    n = len(frs)
    if n <= 1: return dict(dirs=1, frames=n, order='single', confident=True)
    lag = {L: sum(_iou(frs[i], frs[i + L]) for i in range(n - L)) / (n - L) for L in (1, 2, 4, 8, 16, 32) if n > L}
    cands = []
    for D in (8, 16, 32):
        if n % D == 0 and n // D >= 2 and D in lag:
            cands.append((lag[D], D))
    if cands:
        s, D = max(cands)
        # prefer 8 when 8 and 16 tie (same direction 2 frames apart also overlaps)
        if D == 16 and 8 in lag and n % 8 == 0 and lag[8] >= s - 0.03: D, s = 8, lag[8]
        if s > lag.get(1, 0) + 0.02:
            return dict(dirs=D, frames=n // D, order='frame-major', confident=True, iou_lag=round(s, 2), iou_lag1=round(lag[1], 2))
    if n in (8, 16, 32):
        return dict(dirs=n, frames=1, order='one-frame-per-direction', confident=True, iou_lag1=round(lag[1], 2))
    return dict(dirs=None, frames=n, order='unknown', confident=False, iou=dict((k, round(v, 2)) for k, v in lag.items()))

def _mirror_partner_frac(views):
    """views: one RGBA frame per direction (dir 0..D-1).  Fraction of directions whose horizontal mirror best matches
    direction (D/2 - d) mod D, i.e. dir 0 and D/2 face sideways (right / left) and the sequence turns one way round."""
    D = len(views)
    def crop(a):
        c = a[:, :, 3] > 0; ys, xs = np.nonzero(c); return c[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    def iou(a, b):
        h = max(a.shape[0], b.shape[0]); w = max(a.shape[1], b.shape[1])
        A = np.zeros((h, w), bool); B = np.zeros((h, w), bool)
        A[h - a.shape[0]:, (w - a.shape[1]) // 2:(w - a.shape[1]) // 2 + a.shape[1]] = a
        B[h - b.shape[0]:, (w - b.shape[1]) // 2:(w - b.shape[1]) // 2 + b.shape[1]] = b
        return (A & B).sum() / max(1, (A | B).sum())
    v = [crop(a) for a in views]; hit = 0
    for d in range(D):
        m = v[d][:, ::-1]
        p = max(range(D), key=lambda q: iou(m, v[q]))
        hit += p == (D // 2 - d) % D
    return hit / D

def layout2(frs):
    """Pick the layout (dirs x frames, frame-major) whose direction-0 views mirror the way real turnarounds do,
    breaking ties with the lag-IoU rule of layout().  Adds 'mirror' (0..1) to the result."""
    n = len(frs); base = layout(frs)
    if n < 8: return dict(base, mirror=None)
    best = None
    for D in (8, 16, 32):
        if n % D: continue
        mf = _mirror_partner_frac(frs[:D])
        lag = (sum(_iou(frs[i], frs[i + D]) for i in range(n - D)) / (n - D)) if n > D else 0.0
        sc = mf + 0.5 * lag
        if best is None or sc > best[0] + 0.05 or (abs(sc - best[0]) <= 0.05 and D < best[1]):
            best = (sc, D, mf)
    if best is None: return dict(base, mirror=None)
    sc, D, mf = best
    if mf < 0.5:                                   # mirror test inconclusive (e.g. asymmetric infantry): lag rule
        return dict(base, mirror=round(mf, 2))
    return dict(dirs=D, frames=n // D, order='frame-major' if n > D else 'one-frame-per-direction',
                confident=mf >= 0.5, mirror=round(mf, 2))
