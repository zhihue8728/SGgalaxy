import sys, numpy as np, xcodec, relabel
from sheet import E
def runs(v):
    out=[];s=None
    for i,x in enumerate(v):
        if x and s is None: s=i
        if not x and s is not None: out.append((s,i-1)); s=None
    if s is not None: out.append((s,len(v)-1))
    return out
def measure(nm,k,region=None,thr=60):
    b=E[nm]; w,h,offs=xcodec.frames_meta(b); p,a,_=xcodec.decode(b,offs[k],w,h)
    rgb=relabel.rgb_of(p).astype(int); g=rgb.max(-1)
    x0,y0,x1,y1=region or (0,0,w,h)
    sub=g[y0:y1,x0:x1]; bg=np.median(sub)
    t=(sub>bg+thr)&a[y0:y1,x0:x1]
    rows=runs(t.sum(1)>0); 
    res=[]
    for r0,r1 in rows:
        cols=np.where(t[r0:r1+1].any(0))[0]
        res.append(((x0+cols.min(), y0+r0, cols.max()-cols.min()+1, r1-r0+1)))
    return (w,h),res
if __name__=='__main__':
    for a in sys.argv[1:]:
        nm,_,rest=a.partition('#'); k,_,reg=rest.partition('@')
        reg=tuple(int(v) for v in reg.split(',')) if reg else None
        print(a, measure(nm,int(k or 0),reg))
