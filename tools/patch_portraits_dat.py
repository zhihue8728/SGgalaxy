"""Write the new commander portraits (client/sgrender/art/SGHud-hero-NN / SGHud-heroport-NN, 1..9) into the game's own
image packs, so the game's own windows show the same faces as the HUD (user 2026-11-01 02:07 / 02:15):
  tc2.dat   Hero-01..09.xpf   80x67, 2 identical frames            (F4 window, result, who list)
  NTF2.dat  HeroPort.xpf      223x142, frame N-1                   (new commander: the big picture)
A backup <file>.before_portraits is written once.  usage: python tools/patch_portraits_dat.py  (from the repo root)"""
import os, sys, shutil
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import sgdat, xpf, xpf_write as W, sgdat_add
from PIL import Image
ART = 'client/sgrender/art'
def entry(path, name):
    d = open(path, 'rb').read()
    for n, o, l in sgdat.read_index(d):
        if n.lower() == name.lower(): return n, d[o:o + l]
    raise KeyError(name)
def backup(p):
    b = p + '.before_portraits'
    if not os.path.exists(b): shutil.copy2(p, b)
    return b
def patch_tc2(path):
    src = backup(path); tmp = []
    os.makedirs('out/_portraits_tmp', exist_ok=True)
    for h in range(1, 10):
        n, b = entry(src, 'hero-%02d.xpf' % h); i = xpf.info(b)
        im = Image.open('%s/SGHud-hero-%02d.png' % (ART, h)).convert('RGBA').resize((i['w'] - 1, i['h'] - 1), Image.LANCZOS)
        f = 'out/_portraits_tmp/' + n; open(f, 'wb').write(W.replace_frames(b, {0: im, 1: im})); tmp.append(f)
    print(path, sgdat_add.add(src, path, tmp))
def patch_ntf2(path):
    src = backup(path)
    os.makedirs('out/_portraits_tmp', exist_ok=True)
    n1, hp = entry(src, 'heroport.xpf')
    fr = {k: Image.open('%s/SGHud-heroport-%02d.png' % (ART, k + 1)).convert('RGBA').resize((223, 142), Image.LANCZOS) for k in range(9)}
    f1 = 'out/_portraits_tmp/' + n1; open(f1, 'wb').write(W.replace_frames(hp, fr))
    print(path, sgdat_add.add(src, path, [f1]))   # CmdBtn.xpf (the 9 strips) stays the original (user 02:17)
if __name__ == '__main__':
    patch_tc2('out/tc/tc2.dat')
    for p in ('out/NTF2_cn.dat', 'out/NTF2_tw.dat', 'out/NTF2_en.dat'):
        if os.path.exists(p): patch_ntf2(p)
