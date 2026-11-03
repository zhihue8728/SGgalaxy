#!/usr/bin/env python3
"""Render the missing organic unit portraits from the sprites and add them to the client's tc.dat / tc2.dat.
usage: python tools\\install_portraits.py "C:\\Program Files (x86)\\KRU\\Shattered Galaxy" [--out DIR]
Backs up tc.dat / tc2.dat once (tc.dat.orig / tc2.dat.orig) and then rewrites them with the extra jpg entries
(or writes them to DIR instead of the game folder when --out is given).  Needs Pillow.  Safe to run again."""
import sys, os, shutil, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_portraits as M, sgdat_add
def main():
    game = sys.argv[1]; out = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else game
    M.GD = game.rstrip('\\/') + os.sep
    tmp = tempfile.mkdtemp()
    big, small = [], []
    for u in M.UNITS:
        for suffix, (w, h), lst in (('', (276, 344), big), ('s', (80, 100), small)):
            p = os.path.join(tmp, u + suffix + '.jpg'); M.portrait(u, w, h).save(p, quality=88); lst.append(p)
    for dat, files in (('tc.dat', big), ('tc2.dat', small)):
        src = os.path.join(game, dat)
        if os.path.exists(src + '.orig'):
            src_pristine = src + '.orig'
        else:
            src_pristine = src
        if out != game:
            src = src_pristine             # 2026-10-22: never rebuild from an already patched dat
        if out == game:
            bak = src + '.orig'
            if not os.path.exists(bak): shutil.copy2(src, bak)
            src = bak                      # always rebuild from the pristine copy
        os.makedirs(out, exist_ok=True)
        print(dat, sgdat_add.add(src, os.path.join(out, dat), files))
if __name__ == '__main__':
    main()
