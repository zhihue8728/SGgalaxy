#!/usr/bin/env python3
"""i18n phase 4: put the Chinese-captioned UI sprites (out/ui_tw, out/ui_cn, made by tools/ui4/build_ui.py) into
copies of NTF2.dat / NTFB.dat -> out/NTF2_tw.dat, out/NTF2_cn.dat, out/NTFB_tw.dat, out/NTFB_cn.dat.
usage: build_ntf2.py "<game folder>"   (reads NTF2.dat.orig / NTFB.dat.orig when they exist)"""
import os, struct, sys

def read(path):
    d = open(path, 'rb').read(); n = struct.unpack_from('<I', d, 0)[0]
    ent = [(struct.unpack_from('<I', d, 4 + 17 * i)[0], d[4 + 17 * i + 4:4 + 17 * i + 17]) for i in range(n)]
    return d, ent

def replace(src, dst, files):
    d, ent = read(src)
    n = len(ent)
    order = sorted(range(n), key=lambda i: ent[i][0])          # data blocks in file order
    blocks = {}
    for j, i in enumerate(order):
        o = ent[i][0]; e = ent[order[j + 1]][0] if j + 1 < n else len(d)
        blocks[i] = d[o:e]
    names = {i: ent[i][1].split(b'\0')[0].decode('latin1') for i in range(n)}
    low = {k.lower(): v for k, v in files.items()}
    hit = 0
    out = bytearray(d[:4 + 17 * n]); pos = len(out); newoff = {}
    for i in order:
        nm = names[i].lower()
        data = low[nm] if nm and nm in low else blocks[i]
        hit += bool(nm and nm in low)
        newoff[i] = pos; out += data; pos += len(data)
    for i in range(n):
        struct.pack_into('<I', out, 4 + 17 * i, newoff[i])
    open(dst, 'wb').write(out)
    return hit

def main():
    gd = sys.argv[1]; here = os.path.dirname(os.path.abspath(__file__)); outd = os.path.join(here, '..', 'out')
    for dat in ("NTF2",):
        src = os.path.join(gd, dat + '.dat.orig')
        if not os.path.exists(src): src = os.path.join(gd, dat + '.dat')
        for lang in ('tw', 'cn'):
            fd = os.path.join(outd, 'ui_' + lang)
            files = {f: open(os.path.join(fd, f), 'rb').read() for f in os.listdir(fd)}
            dst = os.path.join(outd, f'{dat}_{lang}.dat')
            print(dat, lang, 'replaced', replace(src, dst, files), '->', dst)
if __name__ == '__main__':
    main()
