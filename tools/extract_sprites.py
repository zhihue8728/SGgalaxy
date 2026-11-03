"""Extract Shattered Galaxy sprites (.xpf inside the .dat archives) to PNG for upscaling tests (Real-ESRGAN).
usage: python extract_sprites.py GAME_DIR OUT_DIR name.xpf [name.xpf ...] [--frames 0,6]
Unit bodies are G###MO.XPF (tc/tc2.dat), heroes H###MO.XPF, portraits Hero-##.xpf.  Output: <name>_<frame>.png (RGBA,
cropped to the visible pixels).  Needs tools/sgdat.py and tools/xpf.py next to it, and Pillow."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sgdat, xpf
def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    frames = [0, 6]
    if '--frames' in sys.argv:
        frames = [int(x) for x in sys.argv[sys.argv.index('--frames') + 1].split(',')]
        args = [a for a in args if a != sys.argv[sys.argv.index('--frames') + 1]]
    game, out, names = args[0], args[1], [n.lower() for n in args[2:]]
    os.makedirs(out, exist_ok=True)
    idx = {}
    for f in os.listdir(game):
        if f.lower().endswith('.dat'):
            d = open(os.path.join(game, f), 'rb').read()
            try:
                for name, off, ln in sgdat.read_index(d):
                    idx.setdefault(name.lower(), (f, off, ln))
            except Exception:
                pass
    for n in names:
        if n not in idx:
            print('missing', n); continue
        f, off, ln = idx[n]
        with open(os.path.join(game, f), 'rb') as fh:
            fh.seek(off); b = fh.read(ln)
        for fr in frames:
            im = xpf.frame(b, fr); bb = im.getbbox()
            if bb:
                im.crop(bb).save(os.path.join(out, '%s_%d.png' % (n[:-4], fr)))
if __name__ == '__main__':
    main()
