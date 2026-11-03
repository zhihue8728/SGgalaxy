"""Side-by-side: original sprite direction views (x4) above the Blender renders of the same directions.
usage: python3 art3d/compare.py CODE D d1,d2,... RENDER_DIR OUT.png"""
import sys, os
from PIL import Image, ImageDraw
code, D, dirs, rdir, out = sys.argv[1], int(sys.argv[2]), [int(x) for x in sys.argv[3].split(',')], sys.argv[4], sys.argv[5]
base = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'units', code, 'views')
tiles = []
for d in dirs:
    v = Image.open(os.path.join(base, 'dir%02d.png' % d)).convert('RGBA'); v = v.resize((v.width * 4, v.height * 4), Image.NEAREST)
    r = Image.open(os.path.join(rdir, 'r_%s_d%02d.png' % (code, d))).convert('RGBA')
    tiles.append((d, v, r))
cw = max(max(v.width, r.width) for _, v, r in tiles) + 20
vh = max(v.height for _, v, _ in tiles); rh = max(r.height for _, _, r in tiles)
S = Image.new('RGBA', (cw * len(tiles), vh + rh + 50), (40, 44, 52, 255)); dr = ImageDraw.Draw(S)
for i, (d, v, r) in enumerate(tiles):
    x = i * cw + 10
    S.alpha_composite(v, (x + (cw - 20 - v.width) // 2, 20 + vh - v.height)); S.alpha_composite(r, (x + (cw - 20 - r.width) // 2, vh + 40))
    dr.text((x, 4), 'dir %d/%d' % (d, D), fill=(255, 255, 0))
S.save(out); print(S.size)
