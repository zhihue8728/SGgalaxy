"""Minimal LOSSLESS Bink 1 (revision 'i') video encoder for re-captioning the game's UI clips (odv.dat *.bik).
Each 8x8 block is SKIP (same as the previous frame), FILL (one colour) or RAW (64 pixels); every Huffman tree is the
identity tree 0.  Audio chunks and the header fields of the original file are kept.
Frame layout ('i'): u32 = byte offset of the chroma planes, then planes Y, V, U (swap_planes), each 32-bit aligned.
The bundle protocol mirrors ffmpeg's bink.c (CHECK_READ_VAL): a bundle is re-filled only when everything decoded
before has been used, and a count of 0 ends it for the plane."""
import struct
import numpy as np
from binkparse import read_file, split_audio, log2

SKIP, FILL, RAW = 0, 6, 9


class BW:
    def __init__(self): self.buf = bytearray(); self.acc = 0; self.n = 0
    def put(self, v, n):
        for i in range(n):
            self.acc |= ((v >> i) & 1) << self.n; self.n += 1
            if self.n == 8: self.buf.append(self.acc); self.acc = 0; self.n = 0
    def align32(self):
        while self.n or len(self.buf) % 4:
            self.put(0, 1)
    def bits(self): return len(self.buf) * 8 + self.n


def plane_blocks(P, prev, key):
    """P: uint8 [H,W] padded to multiples of 8.  -> per block-row list of (type, data)"""
    H, W = P.shape; rows = []
    for by in range(H // 8):
        row = []
        for bx in range(W // 8):
            b = P[by * 8:by * 8 + 8, bx * 8:bx * 8 + 8]
            if not key and prev is not None and np.array_equal(b, prev[by * 8:by * 8 + 8, bx * 8:bx * 8 + 8]):
                row.append((SKIP, None))
            elif (b == b[0, 0]).all():
                row.append((FILL, [int(b[0, 0])]))
            else:
                row.append((RAW, [int(x) for x in b.reshape(-1)]))
        rows.append(row)
    return rows


def encode_plane(bw_, P, prev, key, width, is_chroma):
    rows = plane_blocks(P, prev, key)
    bwn = P.shape[1] // 8
    w = max(width >> is_chroma, 8); w = (w + 7) & ~7
    len_bt = log2((w >> 3) + 511) + 1
    len_col = log2(bwn * 64 + 511) + 1
    lens = [len_bt, log2((w >> 4) + 511) + 1, len_col, log2((bwn << 3) + 511) + 1,
            log2((w >> 3) + 511) + 1, log2((w >> 3) + 511) + 1, log2((w >> 3) + 511) + 1,
            log2((w >> 3) + 511) + 1, log2(bwn * 48 + 511) + 1]
    # trees: colours bundle has 16 high-nibble trees first; DC bundles have none
    for i in range(9):
        if i == 2:
            for _ in range(16): bw_.put(0, 4)
        if i not in (6, 7):
            bw_.put(0, 4)
    need_bt = [[t for t, _ in r] for r in rows]
    need_col = [[c for _, d in r if d for c in d] for r in rows]
    nrows = len(rows)
    state = {'bt': [0, False], 'col': [0, False]}     # values still buffered, dead

    def plan(key_, needs, r, maxn):
        buf, dead = state[key_]
        if dead or buf > 0:
            return None
        if all(len(n) == 0 for n in needs[r:]):
            state[key_][1] = True
            return []
        vals = []; k = r
        while k < nrows and len(vals) + len(needs[k]) <= maxn:
            vals += needs[k]; k += 1
            if vals and all(len(n) == 0 for n in needs[k:]):
                break
        if not vals:
            raise ValueError('row too big for bundle')
        state[key_][0] = len(vals)
        return vals

    last_high = [0]
    for r in range(nrows):
        # block types
        v = plan('bt', need_bt, r, (1 << len_bt) - 1)
        if v is not None:
            bw_.put(len(v), len_bt)
            if v:
                if len(set(v)) == 1:
                    bw_.put(1, 1); bw_.put(v[0], 4)
                else:
                    bw_.put(0, 1)
                    for x in v: bw_.put(x, 4)
        # sub block types: unused
        if r == 0: bw_.put(0, lens[1])
        v = plan('col', need_col, r, (1 << len_col) - 1)
        if v is not None:
            bw_.put(len(v), len_col)
            if v:
                bw_.put(0, 1)
                for x in v:
                    bw_.put(x >> 4, 4); bw_.put(x & 15, 4)
        if r == 0:
            for i in (3, 4, 5, 6, 7, 8): bw_.put(0, lens[i])
        # consume this row's values
        state['bt'][0] -= len(need_bt[r]); state['col'][0] -= len(need_col[r])
    bw_.align32()


def rgb_to_yuv(rgb):
    r, g, b = [rgb[..., i].astype(np.float64) for i in range(3)]
    y = 16 + 65.481 * r / 255 + 128.553 * g / 255 + 24.966 * b / 255
    u = 128 - 37.797 * r / 255 - 74.203 * g / 255 + 112.0 * b / 255
    v = 128 + 112.0 * r / 255 - 93.786 * g / 255 - 18.214 * b / 255
    return [np.clip(np.round(x), 0, 255).astype(np.uint8) for x in (y, u, v)]


def yuv_to_rgb(Y, U, V):
    U2 = np.repeat(np.repeat(U, 2, 0), 2, 1)[:Y.shape[0], :Y.shape[1]].astype(np.float64) - 128
    V2 = np.repeat(np.repeat(V, 2, 0), 2, 1)[:Y.shape[0], :Y.shape[1]].astype(np.float64) - 128
    y = (Y.astype(np.float64) - 16) * 1.164383
    r = y + 1.596027 * V2; g = y - 0.391762 * U2 - 0.812968 * V2; b = y + 2.017232 * U2
    return np.clip(np.round(np.dstack([r, g, b])), 0, 255).astype(np.uint8)


def pad8(P, h8, w8):
    out = np.zeros((h8, w8), np.uint8); out[:P.shape[0], :P.shape[1]] = P
    if P.shape[1] < w8: out[:P.shape[0], P.shape[1]:] = P[:, -1:]
    if P.shape[0] < h8: out[P.shape[0]:, :] = out[P.shape[0] - 1:P.shape[0], :]
    return out


def encode_file(src_path, frames_yuv, out_path):
    """frames_yuv: list of (Y [h,w], U [h/2,w/2], V) uint8, same count as the source."""
    F = read_file(src_path)
    assert len(frames_yuv) == F['nf']
    w, h = F['w'], F['h']
    yh8, yw8 = (h + 7) & ~7, (w + 7) & ~7
    ch8, cw8 = (((h + 1) // 2) + 7) & ~7, (((w + 1) // 2) + 7) & ~7
    # chroma plane in blocks: (w+15)>>4 blocks of 8
    cw8 = ((w + 15) >> 4) * 8; ch8 = ((h + 15) >> 4) * 8
    prev = None; chunks = []
    for i, (Y, U, V) in enumerate(frames_yuv):
        key = True   # 2026-10-22: every frame self-contained (FILL/RAW only) - SKIP blocks of our frames decoded wrong in the game (text blurred after hover / loop)
        Pl = [pad8(Y, yh8, yw8), pad8(V, ch8, cw8), pad8(U, ch8, cw8)]
        bw_ = BW(); bw_.put(0, 32)
        encode_plane(bw_, Pl[0], prev[0] if prev else None, key, w, 0)
        off = len(bw_.buf)
        encode_plane(bw_, Pl[1], prev[1] if prev else None, key, w, 1)
        encode_plane(bw_, Pl[2], prev[2] if prev else None, key, w, 1)
        data = bytearray(bw_.buf); struct.pack_into('<I', data, 0, off)
        auds, _v = split_audio(F['frames'][i][1], F['na'])
        chunks.append(b''.join(auds) + bytes(data))
        prev = Pl
    d = F['d']
    hdr = bytearray(d[:F['hdr_end']])
    nf = F['nf']; p = F['hdr_end'] - 4 * (nf + 1)
    pos = len(hdr); idx = []
    for i, c in enumerate(chunks):
        idx.append(pos | (1 if i == 0 else 0)); pos += len(c)
    idx.append(pos)
    struct.pack_into('<%dI' % (nf + 1), hdr, p, *idx)
    struct.pack_into('<I', hdr, 4, pos - 8)
    struct.pack_into('<I', hdr, 12, max(len(c) for c in chunks))
    out = bytes(hdr) + b''.join(chunks)
    open(out_path, 'wb').write(out)
    return out
