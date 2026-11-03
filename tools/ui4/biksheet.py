import sys, numpy as np
from PIL import Image, ImageDraw
import binkrt, binkenc
def sheet(paths, fn, maxw=1500, every=1, scale=1):
    tiles=[]
    for p in paths:
        fr=binkrt.decode(p)
        for i in range(0,len(fr),every):
            Y,U,V=fr[i]; im=Image.fromarray(binkenc.yuv_to_rgb(Y,U,V))
            if scale!=1: im=im.resize((im.width*scale,im.height*scale),Image.NEAREST)
            tiles.append((p.split('/')[-1][:-4]+f'#{i}',im))
    x=y=rh=0;pos=[]
    for n,im in tiles:
        if x+im.width>maxw and x>0: x=0;y+=rh+13;rh=0
        pos.append((x,y+12)); x+=im.width+4; rh=max(rh,im.height)
    S=Image.new('RGB',(maxw,y+rh+13),(60,0,60)); d=ImageDraw.Draw(S)
    for (n,im),p in zip(tiles,pos): S.paste(im,p); d.text((p[0],p[1]-11),n,fill=(255,255,0))
    S.save(fn); print(fn,S.size)
if __name__=='__main__':
    sheet(sys.argv[3:],sys.argv[1],every=int(sys.argv[2]))
