import sys, numpy as np
from PIL import Image, ImageDraw
import binkrt, binkenc
def grid(img, s=4):
    H,W=img.shape[:2]
    im=Image.fromarray(img).resize((W*s,H*s),Image.NEAREST)
    T=Image.new('RGB',(W*s+22,H*s+14),(40,0,40)); T.paste(im,(22,14)); d=ImageDraw.Draw(T)
    for x in range(0,W,5):
        d.line([(22+x*s,14),(22+x*s,14+H*s)],fill=(255,255,0) if x%10==0 else (80,80,0))
        if x%10==0: d.text((22+x*s,1),str(x),fill=(255,255,0))
    for y in range(0,H,5):
        d.line([(22,14+y*s),(22+W*s,14+y*s)],fill=(255,255,0) if y%10==0 else (80,80,0))
        if y%10==0: d.text((1,14+y*s),str(y),fill=(255,255,0))
    return T
if __name__=='__main__':
    out=sys.argv[1]; tiles=[]
    for a in sys.argv[2:]:
        p,_,k=a.partition('#'); fr=binkrt.decode(p); k=int(k) if k else len(fr)-1
        tiles.append(grid(binkenc.yuv_to_rgb(*fr[k]), int(__import__('os').environ.get('S','4'))))
    Wt=max(t.width for t in tiles); Ht=sum(t.height+6 for t in tiles)
    S=Image.new('RGB',(Wt,Ht),(20,20,20)); y=0
    for t in tiles: S.paste(t,(0,y)); y+=t.height+6
    S.save(out); print(S.size)
