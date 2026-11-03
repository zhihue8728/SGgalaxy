import numpy as np, xcodec, xpf
from sheet import E
same=diff=bad=0; badn=[]
for nm,b in E.items():
    if not nm.lower().endswith('.xpf'): continue
    try:
        w,h,offs=xcodec.frames_meta(b)
        new={}
        for o in set(offs):
            if o+2>=len(b): continue
            p,a,nb=xcodec.decode(b,o,w,h); new[o]=xcodec.encode(p,a)
            if new[o]==b[o:o+nb]: same+=1
            else: diff+=1
        nb2=xcodec.rebuild(b,new)
        w2,h2,offs2=xcodec.frames_meta(nb2)
        for o,o2 in zip(offs,offs2):
            if o+2>=len(b): continue
            p,a,_=xcodec.decode(b,o,w,h); p2,a2,_=xcodec.decode(nb2,o2,w,h)
            assert (a==a2).all() and (p[a]==p2[a2]).all()
    except Exception as e:
        bad+=1; badn.append((nm,str(e)[:60]))
print(same,diff,bad,badn[:10])
