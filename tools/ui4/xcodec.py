"""Lossless .xpf frame codec on RGB565 arrays (for re-drawing UI labels).
frame = u8 top, u8 bottom, then rows top..h-bottom-1: repeat {u8 skip; if x+skip < w: u8 n, n x u16} while x < w."""
import struct
import numpy as np
import xpf


def decode(b, off, w, h):
    """-> (pix uint16 [h,w], alpha bool [h,w], nbytes)"""
    pix = np.zeros((h, w), np.uint16); a = np.zeros((h, w), bool)
    top, bot = b[off], b[off + 1]; p = off + 2
    for y in range(top, h - bot):
        x = 0
        while x < w:
            x += b[p]; p += 1
            if x >= w: break
            n = b[p]; p += 1
            v = np.frombuffer(b, '<u2', n, p); p += 2 * n
            k = min(n, w - x)
            pix[y, x:x + k] = v[:k]; a[y, x:x + k] = True
            x += n
    return pix, a, p - off


def encode(pix, a):
    h, w = a.shape
    rows = np.where(a.any(1))[0]
    if len(rows) == 0:
        return bytes([h if h < 256 else 255, 0])[:2]
    top, bot = min(255, int(rows[0])), min(255, int(h - 1 - rows[-1]))
    out = bytearray([top, bot])
    for y in range(top, h - bot):
        x = 0; r = a[y]
        while x < w:
            # skip transparent
            s = x
            while s < w and not r[s]: s += 1
            skip = s - x
            if s >= w:
                # trailing skip to the end of the row
                while skip > 255:
                    out += bytes([255, 0]); skip -= 255
                out.append(skip if skip > 0 else 0)
                if skip == 0:
                    pass
                break
            while skip > 255:
                out += bytes([255, 0]); skip -= 255
            e = s
            while e < w and r[e] and e - s < 255: e += 1
            out += bytes([skip, e - s]); out += pix[y, s:e].astype('<u2').tobytes()
            x = e
    return bytes(out)


def frames_meta(b):
    i = xpf.info(b); offs = list(xpf.offsets(b))
    return i['w'], i['h'], offs


def rebuild(b, new_frames):
    """new_frames: {original offset: encoded bytes}.  Keeps header + the bytes between the table and the first frame,
    re-lays every distinct frame (shared offsets stay shared)."""
    w, h, offs = frames_meta(b)
    n = len(offs); tab_end = 14 + 4 * n
    uniq = sorted(set(o for o in offs if o < len(b)))
    first = min(uniq) if uniq else len(b)
    pre = bytearray(b[:first])
    body = bytearray(); newpos = {}
    for o in uniq:
        if o in new_frames:
            data = new_frames[o]
        else:
            if o + 2 > len(b):
                data = b[o:]
            else:
                try:
                    _, _, nb = decode(b, o, w, h); data = b[o:o + nb]
                except Exception:
                    nxt = [u for u in uniq if u > o]; data = b[o:(nxt[0] if nxt else len(b))]
        newpos[o] = first + len(body); body += data
    end_old = offs[-1]
    newoffs = [newpos.get(o, first + len(body)) for o in offs]
    struct.pack_into('<%dI' % n, pre, 14, *newoffs)
    return bytes(pre + body)
