import sys, os, numpy as np
from PIL import Image, ImageDraw
import bikui, binkenc
from bik_labels import CLIPS
import dp_labels
for _st in ('bn', 'bh'):
    for _k in dp_labels.CLIP_POS:
        CLIPS[f'dp-{_st}-{_k}.bik'] = dict(mode='rot', dpkey=_k)
def preview(names, fn, lang='tw', every=1):
    tiles=[]; cache={}
    for nm in names:
        yuv,new=bikui.process_clip('bik/'+nm, CLIPS[nm], lang, cache)
        for i in range(0,len(new),every): tiles.append((nm[:-4]+'#%d'%i, Image.fromarray(new[i])))
    x=y=rh=0;pos=[]
    for n,im in tiles:
        if x+im.width>1500 and x>0: x=0;y+=rh+13;rh=0
        pos.append((x,y+12)); x+=im.width+4; rh=max(rh,im.height)
    S=Image.new('RGB',(1500,y+rh+13),(60,0,60)); d=ImageDraw.Draw(S)
    for (n,im),p in zip(tiles,pos): S.paste(im,p); d.text((p[0],p[1]-11),n,fill=(255,255,0))
    S.save(fn); print(fn,S.size)
def build(names, outdir):
    import io
    from sheet import E
    for lang in ('tw','cn'):
        os.makedirs(f'{outdir}/{lang}',exist_ok=True); cache={}
        for nm in names:
            if nm=='dp-bk-ts.bik':
                orig, rg, new = bikui.marquee('bik/'+nm, '單位部署' if lang=='tw' else '单位部署', lang)
                yuv = bikui.rgb_frames_to_yuv(orig, new, rg)
            else:
                yuv,_=bikui.process_clip('bik/'+nm, CLIPS[nm], lang, cache)
            binkenc.encode_file('bik/'+nm, yuv, f'{outdir}/{lang}/{nm}')
        # deploy background (NTF2.dat)
        rgb=np.asarray(Image.open(io.BytesIO(E['dp-st-bk.jpg'])).convert('RGB')).copy()
        out=bikui.apply_rot_labels(rgb,[dp_labels.DP[k] for k in dp_labels.JPG],lang)
        b=io.BytesIO(); Image.fromarray(out).save(b,'JPEG',quality=93); os.makedirs(f'out/{lang}',exist_ok=True)
        open(f'out/{lang}/dp-st-bk.jpg','wb').write(b.getvalue())
        rgb=np.asarray(Image.open(io.BytesIO(E['ft_back.jpg'])).convert('RGB')).copy()
        out=bikui.apply_rot_labels(rgb,dp_labels.FT_JPG,lang)
        b=io.BytesIO(); Image.fromarray(out).save(b,'JPEG',quality=93)
        open(f'out/{lang}/ft_back.jpg','wb').write(b.getvalue())
        print(lang,len(names))
if __name__=='__main__':
    if sys.argv[1]=='preview': preview(sys.argv[4:] or list(CLIPS), sys.argv[2], every=int(sys.argv[3]))
    else: build(sys.argv[2:] or list(CLIPS), 'out/bik')
