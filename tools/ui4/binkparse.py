"""Bink 1 (revision 'i') bitstream PARSER (bit consumption only) - port of ffmpeg libavcodec/bink.c, used to learn the
layout of RAD's frames (what the 32-bit words before the planes mean) and to check our encoder's output."""
import struct
from binktab import TREE_BITS, TREE_LENS

VLC = []
for t in range(16):
    VLC.append({(TREE_LENS[t][s], TREE_BITS[t][s]): s for s in range(16)})


class BR:
    def __init__(self, data):
        self.d = data; self.p = 0; self.n = len(data) * 8
    def bit(self):
        b = (self.d[self.p >> 3] >> (self.p & 7)) & 1; self.p += 1; return b
    def bits(self, n):
        v = 0
        for i in range(n): v |= self.bit() << i
        return v
    def huff(self, tree):
        vnum, syms = tree
        code = 0
        for ln in range(1, 8):
            code |= self.bit() << (ln - 1)
            s = VLC[vnum].get((ln, code))
            if s is not None: return syms[s]
        raise ValueError('bad vlc')


def log2(x):
    return x.bit_length() - 1


def read_tree(br):
    vnum = br.bits(4)
    if not vnum: return (0, list(range(16)))
    if br.bit():
        ln = br.bits(3); syms = []; used = [0] * 16
        for i in range(ln + 1):
            s = br.bits(4); syms.append(s); used[s] = 1
        for i in range(16):
            if len(syms) >= 16: break
            if not used[i]: syms.append(i)
        return (vnum, syms)
    ln = br.bits(2); inn = list(range(16))
    for i in range(ln + 1):
        size = 1 << i; out = [0] * 16
        for t in range(0, 16, size << 1):
            a = inn[t:t + size]; b = inn[t + size:t + 2 * size]; o = []
            while a and b:
                o.append(b.pop(0) if br.bit() else a.pop(0))
            o += a + b; out[t:t + 2 * size] = o
        inn = out
    return (vnum, inn)


BT, SBT, COL, PAT, XO, YO, IDC, DDC, RUN = range(9)


class Bundle:
    def __init__(self, ln): self.len = ln; self.vals = []; self.ptr = 0; self.dead = False
    def need(self): return (not self.dead) and self.ptr >= len(self.vals)
    def get(self):
        v = self.vals[self.ptr]; self.ptr += 1; return v


def parse_plane(br, width, height, is_chroma, stats):
    bw = ((width + 15) >> 4) if is_chroma else ((width + 7) >> 3)
    bh = ((height + 15) >> 4) if is_chroma else ((height + 7) >> 3)
    w = max(width >> is_chroma, 8); w = (w + 7) & ~7
    lens = {BT: log2((w >> 3) + 511) + 1, SBT: log2((w >> 4) + 511) + 1, COL: log2(bw * 64 + 511) + 1,
            IDC: log2((w >> 3) + 511) + 1, DDC: log2((w >> 3) + 511) + 1, XO: log2((w >> 3) + 511) + 1,
            YO: log2((w >> 3) + 511) + 1, PAT: log2((bw << 3) + 511) + 1, RUN: log2(bw * 48 + 511) + 1}
    B = {k: Bundle(v) for k, v in lens.items()}
    trees = {}; col_high = []
    for i in range(9):
        if i == COL:
            col_high = [read_tree(br) for _ in range(16)]
        if i not in (IDC, DDC):
            trees[i] = read_tree(br)
    state = {'last': 0}

    def cnt(b):
        if not b.need(): return None
        t = br.bits(b.len)
        if not t: b.dead = True; return None
        b.vals = []; b.ptr = 0
        return t

    def rd_bt(b):
        t = cnt(b)
        if t is None: return
        if br.bit():
            v = br.bits(4); b.vals = [v] * t
        else:
            last = 0
            while len(b.vals) < t:
                v = br.huff(trees_b)
                if v < 12: last = v; b.vals.append(v)
                else: b.vals += [last] * [4, 8, 12, 32][v - 12]

    for by in range(bh):
        for k in (BT, SBT):
            trees_b = trees[k]; rd_bt(B[k])
        t = cnt(B[COL])
        if t is not None:
            if br.bit():
                state['last'] = br.huff(col_high[state['last']]); v = (state['last'] << 4) | br.huff(trees[COL])
                B[COL].vals = [v] * t
            else:
                for _ in range(t):
                    state['last'] = br.huff(col_high[state['last']]); B[COL].vals.append((state['last'] << 4) | br.huff(trees[COL]))
        t = cnt(B[PAT])
        if t is not None:
            for _ in range(t): B[PAT].vals.append(br.huff(trees[PAT]) | (br.huff(trees[PAT]) << 4))
        for k in (XO, YO):
            t = cnt(B[k])
            if t is not None:
                if br.bit():
                    v = br.bits(4)
                    if v and br.bit(): v = -v
                    B[k].vals = [v] * t
                else:
                    for _ in range(t):
                        v = br.huff(trees[k])
                        if v and br.bit(): v = -v
                        B[k].vals.append(v)
        for k, sb in ((IDC, 0), (DDC, 1)):
            t = cnt(B[k])
            if t is not None:
                v = br.bits(11 - sb)
                if v and sb and br.bit(): v = -v
                B[k].vals = [v]; t -= 1; i = 0
                while i < t:
                    l2 = min(t - i, 8); bs = br.bits(4)
                    for j in range(l2):
                        if bs:
                            v2 = br.bits(bs)
                            if v2 and br.bit(): v2 = -v2
                            v += v2
                        B[k].vals.append(v)
                    i += 8
        t = cnt(B[RUN])
        if t is not None:
            if br.bit(): B[RUN].vals = [br.bits(4)] * t
            else:
                for _ in range(t): B[RUN].vals.append(br.huff(trees[RUN]))
        bx = 0
        while bx < bw:
            blk = B[BT].get()
            stats[blk] = stats.get(blk, 0) + 1
            if ((by & 1) or (bx & 1)) and blk == 1:
                bx += 2; continue
            if blk == 0: pass
            elif blk == 1:
                sb = B[SBT].get(); stats['s%d' % sb] = stats.get('s%d' % sb, 0) + 1
                if sb == 3: run_block(br, B)
                elif sb == 5: B[IDC].get(); dct(br)
                elif sb == 6: B[COL].get()
                elif sb == 8:
                    B[COL].get(); B[COL].get()
                    for _ in range(8): B[PAT].get()
                elif sb == 9:
                    for _ in range(64): B[COL].get()
                else: raise ValueError('sub %d' % sb)
                bx += 1
            elif blk == 2: B[XO].get(); B[YO].get()
            elif blk == 3: run_block(br, B)
            elif blk == 4: B[XO].get(); B[YO].get(); residue(br, br.bits(7))
            elif blk == 5: B[IDC].get(); dct(br)
            elif blk == 6: B[COL].get()
            elif blk == 7: B[XO].get(); B[YO].get(); B[DDC].get(); dct(br)
            elif blk == 8:
                B[COL].get(); B[COL].get()
                for _ in range(8): B[PAT].get()
            elif blk == 9:
                for _ in range(64): B[COL].get()
            else: raise ValueError('blk %d' % blk)
            bx += 1
    if br.p & 31: br.p += 32 - (br.p & 31)


def run_block(br, B):
    br.bits(4); i = 0
    while True:
        run = B[RUN].get() + 1; i += run
        if br.bit(): B[COL].get()
        else:
            for _ in range(run): B[COL].get()
        if i >= 63: break
    if i == 63: B[COL].get()


def dct(br):
    cl = [0] * 128; ml = [0] * 128; ls = le = 64
    for c, m in ((4, 0), (24, 0), (44, 0), (1, 3), (2, 3), (3, 3)):
        cl[le] = c; ml[le] = m; le += 1
    bits = br.bits(4) - 1
    while bits >= 0:
        lp = ls
        while lp < le:
            if not (ml[lp] | cl[lp]) or not br.bit(): lp += 1; continue
            cc = cl[lp]; mode = ml[lp]
            if mode in (0, 2):
                if mode == 0: cl[lp] = cc + 4; ml[lp] = 1
                else: cl[lp] = 0; ml[lp] = 0; lp += 1
                for i in range(4):
                    if br.bit(): ls -= 1; cl[ls] = cc + i; ml[ls] = 3
                    else:
                        if not bits: br.bit()
                        else: br.bits(bits); br.bit()
            elif mode == 1:
                ml[lp] = 2
                for i in range(3): cc += 4; cl[le] = cc; ml[le] = 2; le += 1
            elif mode == 3:
                if not bits: br.bit()
                else: br.bits(bits); br.bit()
                cl[lp] = 0; ml[lp] = 0; lp += 1
        bits -= 1
    br.bits(4)


def residue(br, masks):
    cl = [0] * 128; ml = [0] * 128; ls = le = 64
    for c, m in ((4, 0), (24, 0), (44, 0), (0, 2)):
        cl[le] = c; ml[le] = m; le += 1
    nz = 0
    mask = 1 << br.bits(3)
    while mask:
        for i in range(nz):
            if not br.bit(): continue
            masks -= 1
            if masks < 0: return
        lp = ls
        while lp < le:
            if not (cl[lp] | ml[lp]) or not br.bit(): lp += 1; continue
            cc = cl[lp]; mode = ml[lp]
            if mode in (0, 2):
                if mode == 0: cl[lp] = cc + 4; ml[lp] = 1
                else: cl[lp] = 0; ml[lp] = 0; lp += 1
                for i in range(4):
                    if br.bit(): ls -= 1; cl[ls] = cc + i; ml[ls] = 3
                    else:
                        nz += 1; br.bit(); masks -= 1
                        if masks < 0: return
            elif mode == 1:
                ml[lp] = 2
                for i in range(3): cc += 4; cl[le] = cc; ml[le] = 2; le += 1
            elif mode == 3:
                nz += 1; br.bit(); cl[lp] = 0; ml[lp] = 0; lp += 1; masks -= 1
                if masks < 0: return
        mask >>= 1


def read_file(path):
    d = open(path, 'rb').read()
    nf = struct.unpack_from('<I', d, 8)[0]; w, h = struct.unpack_from('<II', d, 20)
    flags = struct.unpack_from('<I', d, 36)[0]; na = struct.unpack_from('<I', d, 40)[0]
    p = 44 + 4 * na + 4 * na + 4 * na          # max sizes, (rate,flags), ids
    idx = list(struct.unpack_from('<%dI' % (nf + 1), d, p))
    frames = []
    for i in range(nf):
        a = idx[i] & ~1; b = (idx[i + 1] & ~1) if i + 1 < nf else len(d)
        if i + 1 == nf: b = struct.unpack_from('<I', d, 4)[0] + 8
        frames.append((idx[i] & 1, d[a:b]))
    return dict(d=d, nf=nf, w=w, h=h, flags=flags, na=na, idx=idx, hdr_end=p + 4 * (nf + 1), frames=frames)


def split_audio(fr, na):
    p = 0; auds = []
    for _ in range(na):
        n = struct.unpack_from('<I', fr, p)[0]; auds.append(fr[p:p + 4 + n]); p += 4 + n
    return auds, fr[p:]


if __name__ == '__main__':
    import sys
    for path in sys.argv[1:]:
        F = read_file(path)
        for i, (key, fr) in enumerate(F['frames'][:4]):
            auds, v = split_audio(fr, F['na'])
            br = BR(v); w0 = br.bits(32); st = {}
            pos = [br.p]
            parse_plane(br, F['w'], F['h'], 0, st); pos.append(br.p)
            for pl in (1, 2):
                parse_plane(br, F['w'], F['h'], 1, st); pos.append(br.p)
            print(path.split('/')[-1], i, 'key', key, 'len', len(v), 'word0', w0, 'plane ends (bytes)', [x // 8 for x in pos], st)
