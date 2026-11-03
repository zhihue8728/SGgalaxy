import subprocess, tempfile, os, sys, numpy as np
from PIL import Image, ImageOps, ImageFilter
from sheet import E, frames
def run(g, psm=11):
    fn=tempfile.mktemp(suffix='.png'); g.save(fn)
    r=subprocess.run(['tesseract',fn,'-','--psm',str(psm)],capture_output=True,text=True).stdout; os.remove(fn)
    return ' '.join(r.split())
def prep(im, mode):
    bg=Image.new('RGB',im.size,(0,0,0)); bg.paste(im,(0,0),im)
    a=np.asarray(bg).astype(int)
    if mode=='max': g=a.max(-1)
    else: g=a.sum(-1)//3
    g=Image.fromarray(g.astype(np.uint8))
    g=ImageOps.autocontrast(g)
    g=g.resize((g.width*4,g.height*4),Image.NEAREST if 'n' in mode else Image.LANCZOS)
    if 't' in mode: g=g.point(lambda v:255 if v>110 else 0)
    if 'b' in mode: g=g.filter(ImageFilter.GaussianBlur(1.5))
    return ImageOps.invert(g)
for nm,k in [('iu-weit.xpf',0),('uu-res.xpf',0),('uew-but0.xpf',0),('uu-com.xpf',0),('iu-rs-bk.xpf',0)]:
    im=dict(frames(nm))[k]
    for mode in ['max','maxn','maxt','maxnb','maxtb']:
        print(nm,mode,'|',run(prep(im,mode)))
