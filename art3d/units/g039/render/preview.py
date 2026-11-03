"""compose preview strips: python3 preview.py OUT.png "label|glob,glob,..." ...  (crop around pivot, x3)"""
import sys, glob
from PIL import Image, ImageDraw
SC=int(__import__("os").environ.get("SC","3")); CX,CY=89,109; HW=60; TOP=95; BOT=40
def crop(p, glow=False):
    im=Image.open(p).convert('RGBA'); c=im.crop((CX-HW,CY-TOP,CX+HW,CY+BOT))
    return c.resize((c.width*SC,c.height*SC),Image.NEAREST)
rows=[]
for spec in sys.argv[2:]:
    label,files=spec.split('|',1); fs=[]
    for g in files.split(','): fs+=sorted(glob.glob(g))
    ims=[crop(f) for f in fs]
    W=sum(i.width for i in ims)+4*len(ims); H=ims[0].height+16
    R=Image.new('RGBA',(W,H),(110,112,125,255)); d=ImageDraw.Draw(R); d.text((4,2),label,fill=(255,255,0,255)); x=0
    for i in ims: R.alpha_composite(i,(x,16)); x+=i.width+4
    rows.append(R)
W=max(r.width for r in rows); H=sum(r.height for r in rows)
S=Image.new('RGBA',(W,H),(50,50,50,255)); y=0
for r in rows: S.alpha_composite(r,(0,y)); y+=r.height
S.save(sys.argv[1]); print(S.size)
