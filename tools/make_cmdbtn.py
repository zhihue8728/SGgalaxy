import sys; sys.path.insert(0,'.')
import sgdat, xpf
from PIL import Image, ImageOps
ART = 'n3'
EYES={1:(170,95),2:(152,95),3:(165,90),4:(160,104),5:(205,86),6:(170,95),7:(175,93),8:(168,94),9:(190,82)}
FX0,FY0,FX1,FY1=6,4,86,33         # face window in a 147x37 strip
def band(h):
    im=Image.open(f'{ART}/SGHud-hero-{h:02d}.png').convert('RGB').resize((320,268),Image.LANCZOS)
    ex,ey=EYES[h]; sw=118; sh=int(sw*(FY1-FY0)/(FX1-FX0))
    x0=ex-int(sw*0.55); y0=ey-int(sh*0.52)
    return im.crop((x0,y0,x0+sw,y0+sh)).resize((FX1-FX0,FY1-FY0),Image.LANCZOS)
def tint(face,state):
    if state==1:  # selected: warm
        return Image.blend(face, Image.new('RGB',face.size,(255,150,60)), 0.22)
    if state==2:  # disabled: grey-blue
        g=ImageOps.grayscale(face).convert('RGB')
        return Image.blend(g, Image.new('RGB',face.size,(110,120,200)), 0.35)
    # normal: a cold wash on the left fading out (like the original art)
    cold=Image.blend(face, Image.new('RGB',face.size,(120,125,210)), 0.45)
    m=Image.linear_gradient('L').rotate(90).resize(face.size)   # left white -> right black
    m=m.point(lambda v: int(v*0.85))
    return Image.composite(cold, face, m)
def build(b):
    out={}
    for h in range(1,10):
        f=band(h)
        for st in range(3):
            k=(h-1)*3+st
            orig=xpf.frame(b,k)
            fr=orig.copy()
            t=tint(f,st).convert('RGBA')
            # fade into the original strip on the right side of the window
            w=FX1-FX0; mask=Image.new('L',(w,FY1-FY0),255)
            px=mask.load()
            for x in range(w):
                a=255 if x<w-22 else int(255*(w-x)/22)
                for y in range(FY1-FY0): px[x,y]=a
            region=orig.crop((FX0,FY0,FX1,FY1))
            region.paste(t,(0,0),mask)
            # keep the original frame pixels (the border) where the original is near-white/orange border
            fr.paste(region,(FX0,FY0))
            out[k]=fr
    return out
