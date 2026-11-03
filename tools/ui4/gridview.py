import sys, numpy as np
from PIL import Image, ImageDraw
import xcodec, relabel
from sheet import E, frames
def grid_tile(nm, k, scale=2):
    b=E[nm]; w,h,offs=xcodec.frames_meta(b); p,a,_=xcodec.decode(b,offs[k],w,h)
    rgb=relabel.rgb_of(p).astype(np.uint8)
    im=Image.fromarray(np.dstack([rgb,a.astype(np.uint8)*255]),'RGBA').resize((w*scale,h*scale),Image.NEAREST)
    T=Image.new('RGBA',(w*scale+24,h*scale+24),(60,0,60,255)); T.alpha_composite(im,(24,24)); d=ImageDraw.Draw(T)
    for x in range(0,w,10):
        d.line([(24+x*scale,24),(24+x*scale,24+h*scale)],fill=(255,255,255,40) if x%50 else (255,255,0,90))
        if x%20==0: d.text((24+x*scale,2 if (x//20)%2==0 else 12),str(x),fill=(255,255,0))
    for y in range(0,h,10):
        d.line([(24,24+y*scale),(24+w*scale,24+y*scale)],fill=(255,255,255,40) if y%50 else (255,255,0,90))
        if y%20==0: d.text((0,24+y*scale),str(y),fill=(255,255,0))
    return T
def sheet(specs, fn, maxw=1500):
    tiles=[(f'{nm}#{k}',grid_tile(nm,k)) for nm,k in specs]
    x=y=rowh=0; pos=[]
    for t,im in tiles:
        if x+im.width>maxw and x>0: x=0;y+=rowh+16;rowh=0
        pos.append((x,y+14)); x+=im.width+10; rowh=max(rowh,im.height)
    S=Image.new('RGB',(maxw,y+rowh+18),(25,25,25)); d=ImageDraw.Draw(S)
    for (t,im),(px,py) in zip(tiles,pos): S.paste(im,(px,py)); d.text((px,py-13),t,fill=(0,255,255))
    S.save(fn); print(fn,S.size)
if __name__=='__main__':
    specs=[]
    for a in sys.argv[2:]:
        nm,_,k=a.partition('#'); specs.append((nm,int(k) if k else frames(nm)[0][0]))
    sheet(specs,sys.argv[1])
