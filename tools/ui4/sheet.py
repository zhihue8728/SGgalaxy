import dat,xpf,io,sys
from PIL import Image, ImageDraw
E={}
for f in ['NTF2.dat','NTFB.dat']:
    for k,v in dat.entries('game/'+f).items(): E[k]=v
def frames(nm,maxf=48):
    b=E[nm]; offs=xpf.offsets(b); seen=set(); out=[]
    for k in range(min(len(offs)-1,maxf)):
        if offs[k] in seen or offs[k]+2>=len(b): continue
        seen.add(offs[k]); im=xpf.frame(b,k)
        if im.getbbox() is None: continue
        out.append((k,im))
    return out
def sheet(names,fn,maxw=1400,maxf=12):
    tiles=[]
    for nm in names:
        if nm.lower().endswith('.jpg'): tiles.append((nm,Image.open(io.BytesIO(E[nm])).convert('RGBA')));continue
        try:
            for k,im in frames(nm)[:maxf]: tiles.append((f'{nm}#{k}',im))
        except Exception as e: print(nm,e)
    x=y=rowh=0; pos=[]
    for nm,im in tiles:
        w,h=im.size
        if x+w>maxw: x=0;y+=rowh+14;rowh=0
        pos.append((x,y+12)); x+=w+6; rowh=max(rowh,h)
    S=Image.new('RGB',(maxw,y+rowh+14),(60,0,60)); d=ImageDraw.Draw(S)
    for (nm,im),(px,py) in zip(tiles,pos):
        S.paste(im,(px,py),im); d.text((px,py-11),nm,fill=(255,255,0))
    S.save(fn); print(fn,S.size)
if __name__=='__main__':
    pre=sys.argv[2:]
    sheet(sorted(k for k in E if k.lower().endswith('.xpf') and k.lower().startswith(tuple(pre))),sys.argv[1])
