"""Export every unit's sprites (tc.dat / tc2.dat) and data (server/units_manual.json, unitnames, aliens) for the
3D pipeline.  usage: python3 art3d/export_units.py GAME_DIR [OUT_DIR=art3d/units]
Per art code (g004, a004, h001 ...) it writes OUT/<code>/:
  info.json         names, Mk table, manual fields, every sprite layer with size / pivot / directions / frames / muzzle points
  sheets/<layer>.png  one sheet per sprite file: a row per direction, a column per animation frame (cells cropped to
                      the union of all frames; info.json gives the crop and the pivot inside it).  Mask layers
                      (shadows) are not drawn as sheets.
  views/dirNN.png   standing frame 0 for every direction, cropped (3D reference views)
  turnaround.png    the views side by side, x4 nearest neighbour
  picture*.jpg      the unit pictures stored in the dats (<code>.jpg / <code>s.jpg) when present
and OUT/../units.json (index) and OUT/../contact_sheet.png (every unit, direction 0)."""
import sys, os, re, json, io, shutil
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools')); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, 'server'))
import numpy as np
from PIL import Image, ImageDraw
import sgdat, xpfx

LAYER_DOC = {
    '': 'body (colour)', 's': 'shadow (mask only)', 'b': 'second colour layer (purpose not confirmed)',
    'd': 'glow / effect layer (type flag 0x08; purpose not confirmed)', 'p': 'footprints / ground marks',
    'c': 'extra layer (purpose not confirmed)', 'l': 'extra layer (purpose not confirmed)',
}
ACTION_DOC = {
    'st': 'stand', 'mo': 'move', 'at': 'attack', 'da': 'death / wreck', 'sg': 'siege / deployed (not confirmed)',
    'em': 'hero emote (not confirmed)', 'dt': 'not confirmed', 'db': 'not confirmed', 'he': 'not confirmed',
    'sa': 'not confirmed', 'sf': 'not confirmed', 'sk': 'not confirmed', 'm': 'not confirmed', 'ex': 'not confirmed',
    'pr': 'not confirmed',
}
SPLIT = re.compile(r'^([gahd]\d{3})([a-z]*?)(s|b|d|p|c|l)?(\d?)\.xpf$')
VERSION = 3
DIR_DOC = ('Sheets: one row per direction, one column per frame.  Direction 0 faces screen-right; the index turns '
           'clockwise on screen (D/4 = facing screen-down, D/2 = left, 3D/4 = up), D = 8, 16 or 32.  Checked by '
           'attack muzzle points (Behemoth, Chimera, Imp, Daeva, Wraith, Shade, Mephit, Spirit) and left/right mirror pairs; layers with '
           'layout_confident false need a visual check.')
ACTIONS = ['st', 'mo', 'at', 'da', 'sg', 'em', 'dt', 'db', 'he', 'sa', 'sf', 'sk', 'm', 'ex', 'pr']

def split_name(n):
    m = re.match(r'^([gahd]\d{3})([a-z]*)(\d?)\.xpf$', n)
    if not m: return None
    code, rest, num = m.groups()
    for a in sorted(ACTIONS, key=len, reverse=True):
        if rest.startswith(a) and len(rest) - len(a) <= 1:
            lay = rest[len(a):]
            if lay in LAYER_DOC: return code, a, lay + num
    return code, rest, num

def load_dats(game):
    files = {}
    for f in ['tc2.dat', 'tc.dat']:                       # the client maps tc2 before tc (later entries win? first wins)
        d = open(os.path.join(game, f), 'rb').read()
        for n, o, l in sgdat.read_index(d):
            n = n.lower()
            if n and n not in files: files[n] = (f, d[o:o + l])
    return files

def manual():
    um = json.load(open(os.path.join(ROOT, 'server', 'units_manual.json'), encoding='utf-8'))
    by = defaultdict(list)
    for u in um['units']:
        f = u.get('fields') or {}
        if f.get('chassis_code'): by[f['chassis_code'].lower()].append(u)
    return by

def names():
    try:
        import unitnames
        return unitnames.CN, unitnames.TW
    except Exception as e:
        print('unitnames:', e); return {}, {}

def aliens():
    try:
        import aliens as A
        return {r['code']: n for n, r in A.ROLES.items()}
    except Exception as e:
        print('aliens:', e); return {}

def sheet(frames, lay):
    ks = sorted(frames); imgs = [frames[k] for k in ks]
    al = np.zeros(imgs[0].shape[:2], bool)
    for a in imgs: al |= a[:, :, 3] > 0
    ys, xs = np.nonzero(al); x0, y0, x1, y1 = int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1
    D = lay['dirs'] or 1; F = lay['frames'] if lay['dirs'] else len(imgs)
    cw, ch = x1 - x0, y1 - y0
    S = Image.new('RGBA', (cw * F, ch * D), (0, 0, 0, 0))
    for i, a in enumerate(imgs):
        if lay['dirs']: f, d = divmod(i, D)
        else: f, d = i, 0
        S.paste(Image.fromarray(a[y0:y1, x0:x1]), (f * cw, d * ch))
    return S, [x0, y0, x1, y1], cw, ch

def entry(info):
    body = {l['action']: l for l in info['layers'] if l.get('layer') == '' and not l.get('empty')}
    m0 = info['manual'][0] if info['manual'] else {}
    return dict(code=info['code'], kind=info['kind'], chassis=info['base_chassis'], cn=list(info['names_cn'].values()),
                frame=m0.get('group'), category=m0.get('category'), alien=info.get('alien_role'),
                used=bool(info['manual'] or info.get('alien_role') or info['code'].startswith('h')),
                actions={a: [l['dirs'], l['frames_per_dir'], l['frame_count']] for a, l in sorted(body.items())},
                views=len(info['views']), pictures=info['pictures'])

def main():
    game = sys.argv[1]; out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, 'units')
    os.makedirs(out, exist_ok=True)
    files = load_dats(game); man = manual(); CN, TW = names(); AL = aliens()
    groups = defaultdict(list)
    for n in files:
        if n.endswith('.xpf'):
            s = split_name(n)
            if s: groups[s[0]].append((n, s[1], s[2]))
    index = []; import time; t0 = time.time()
    budget = float(os.environ.get('ART3D_BUDGET', '1e9'))      # seconds; rerun to resume (done codes are skipped)
    for code in sorted(groups):
        cdir = os.path.join(out, code)
        ip = os.path.join(cdir, 'info.json')
        if os.path.exists(ip):
            info = json.load(open(ip, encoding='utf-8'))
            if info.get('version') == VERSION:
                index.append(entry(info)); continue
        if time.time() - t0 > budget:
            print('PARTIAL: time budget reached, run again to continue'); return
        os.makedirs(os.path.join(cdir, 'sheets'), exist_ok=True)
        layers = []; stand = None
        for n, act, lay in sorted(groups[code]):
            dat, b = files[n]
            inf, fr = xpfx.frames(b, want_pts=True)
            if not fr: layers.append(dict(file=n, dat=dat, action=act, layer=lay, empty=True)); continue
            imgs = {k: v[0] for k, v in fr.items()}; pts = {k: v[1] for k, v in fr.items()}
            L = xpfx.layout2([imgs[k] for k in sorted(imgs)])
            e = dict(file=n, dat=dat, action=act, action_doc=ACTION_DOC.get(act, 'not confirmed'), layer=lay,
                     layer_doc=LAYER_DOC.get(lay[:1], 'not confirmed'), type=inf['type'] & 0xff, type_raw=inf['type'],
                     canvas=[inf['w'], inf['h']], pivot=[inf['cx'], inf['cy']], frame_count=len(imgs),
                     dirs=L['dirs'], frames_per_dir=L['frames'] if L['dirs'] else None, layout=L['order'],
                     layout_confident=L['confident'], mirror_check=L.get('mirror'), mask_only=bool(inf['type'] & 0x10))
            if any(pts.values()):
                e['muzzle_points'] = {str(k): [list(p) for p in v] for k, v in sorted(pts.items()) if v}
            if not e['mask_only']:
                S, crop, cw, ch = sheet(imgs, L)
                sp = os.path.join('sheets', n[:-4] + '.png'); S.save(os.path.join(cdir, sp), optimize=True)
                e.update(sheet=sp, sheet_crop=crop, cell=[cw, ch], pivot_in_cell=[inf['cx'] - crop[0], inf['cy'] - crop[1]])
            layers.append(e)
            if act == 'st' and lay == '' and L['dirs']: stand = (imgs, L)
            elif act == 'mo' and lay == '' and L['dirs'] and stand is None: stand = (imgs, L)
        views = []
        if stand:
            imgs, L = stand; ks = sorted(imgs); os.makedirs(os.path.join(cdir, 'views'), exist_ok=True)
            tiles = []
            for d in range(L['dirs']):
                a = imgs[ks[d]]; bb = Image.fromarray(a).getbbox(); im = Image.fromarray(a).crop(bb)
                p = os.path.join('views', 'dir%02d.png' % d); im.save(os.path.join(cdir, p)); views.append(p); tiles.append(im)
            W = sum(t.width for t in tiles) + 8 * (len(tiles) - 1); H = max(t.height for t in tiles)
            T = Image.new('RGBA', (W, H), (0, 0, 0, 0)); x = 0
            for t in tiles: T.paste(t, (x, H - t.height)); x += t.width + 8
            T = T.resize((T.width * 4, T.height * 4), Image.NEAREST); T.save(os.path.join(cdir, 'turnaround.png'), optimize=True)
        pics = []
        for suf in ('', 's'):
            j = f'{code}{suf}.jpg'
            if j in files:
                p = f'picture{suf}.jpg'; open(os.path.join(cdir, p), 'wb').write(files[j][1]); pics.append(p)
        rows = sorted(man.get(code, []), key=lambda u: u['name'])
        chassis = [u['name'] for u in rows]
        bases = sorted({re.sub(r'-Mk\d+$', '', c) for c in chassis})
        info = dict(version=VERSION, directions=DIR_DOC, code=code, kind={'g': 'ground', 'a': 'air', 'h': 'hero', 'd': 'other'}[code[0]],
                    chassis=chassis, base_chassis=bases,
                    names_cn={b: CN.get(b) for b in bases if CN.get(b)}, names_tw={b: TW.get(b) for b in bases if TW.get(b)},
                    alien_role=AL.get(code), manual=[dict(name=u['name'], **(u.get('fields') or {})) for u in rows],
                    layers=layers, views=views, pictures=pics,
                    turnaround='turnaround.png' if views else None)
        if code.startswith('h'): info['note'] = 'commander body (look %d)' % int(code[1:])
        json.dump(info, open(os.path.join(cdir, 'info.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        index.append(entry(info))
        print(code, len(layers), 'layers', len(views), 'views', bases, flush=True)
    json.dump(index, open(os.path.join(os.path.dirname(out), 'units.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    # contact sheet: every unit, direction 0 of its standing frame
    cells = []
    for e in index:
        p = os.path.join(out, e['code'], 'views', 'dir00.png')
        if os.path.exists(p): cells.append((e, Image.open(p)))
    C, CW, CH = 10, 150, 150
    R = (len(cells) + C - 1) // C
    S = Image.new('RGB', (C * CW, R * CH), (40, 44, 52)); dr = ImageDraw.Draw(S)
    for i, (e, im) in enumerate(cells):
        x, y = (i % C) * CW, (i // C) * CH
        sc = min(2.0, (CW - 10) / im.width, (CH - 34) / im.height)
        t = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.NEAREST)
        S.paste(t, (x + (CW - t.width) // 2, y + 4 + (CH - 34 - t.height) // 2), t)
        lab = e['code'] + ' ' + (e['chassis'][0] if e['chassis'] else (e['alien'] or ''))
        dr.text((x + 4, y + CH - 26), lab[:22], fill=(255, 255, 255))
        dr.text((x + 4, y + CH - 14), ('' if e['used'] else 'unused ') + (e['frame'] or e['kind']), fill=(150, 200, 255))
    S.save(os.path.join(os.path.dirname(out), 'contact_sheet.png'), optimize=True)
    print('done', len(index), 'codes')

if __name__ == '__main__':
    main()
