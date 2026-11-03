"""OCR (tesseract TSV, word boxes) of every distinct frame of every UI sprite -> out/ocr2.json
{name: [[frame, [[text, conf, x, y, w, h, line_id], ...]], ...]}"""
import io, json, os, subprocess, tempfile, sys
from multiprocessing import Pool
from PIL import Image, ImageOps
from sheet import E, frames


def ocr(im):
    bg = Image.new('RGB', im.size, (0, 0, 0)); bg.paste(im, (0, 0), im)
    g = ImageOps.autocontrast(ImageOps.grayscale(bg))
    s = 4 if im.width * im.height < 40000 else (3 if im.width * im.height < 120000 else 2)
    g = ImageOps.invert(g.resize((g.width * s, g.height * s), Image.LANCZOS))
    fd, fn = tempfile.mkstemp(suffix='.png'); os.close(fd); g.save(fn)
    r = subprocess.run(['tesseract', fn, '-', '--psm', '11', 'tsv'], capture_output=True, text=True,
                       env=dict(os.environ, OMP_THREAD_LIMIT='1')).stdout
    os.remove(fn); words = []
    for ln in r.splitlines()[1:]:
        c = ln.split('\t')
        if len(c) < 12 or not c[11].strip(): continue
        t = c[11].strip(); conf = float(c[10])
        if conf < 40 or sum(ch.isalpha() for ch in t) < 2: continue
        x, y, w, h = (int(v) // s for v in c[6:10])
        words.append([t, conf, x, y, w, h, f'{c[2]}.{c[3]}.{c[4]}'])
    return words


def job(nm):
    res = []
    try:
        if nm.lower().endswith('.jpg'):
            w = ocr(Image.open(io.BytesIO(E[nm])).convert('RGBA'))
            if w: res.append([0, w])
        else:
            for k, im in frames(nm, 64):
                if im.width < 12 or im.height < 6: continue
                w = ocr(im)
                if w: res.append([k, w])
    except Exception as e:
        res.append([-1, [['ERR ' + str(e), 0, 0, 0, 0, 0, '']]])
    return nm, res


if __name__ == '__main__':
    names = sorted(k for k in E if k.lower().endswith(('.xpf', '.jpg')))
    out = {}
    with Pool(2) as p:
        for i, (nm, res) in enumerate(p.imap_unordered(job, names, chunksize=4)):
            if res: out[nm] = res
            if i % 100 == 0:
                print(i, len(names), flush=True); json.dump(out, open('out/ocr2.json', 'w'))
    json.dump(out, open('out/ocr2.json', 'w')); print('done', len(out))
