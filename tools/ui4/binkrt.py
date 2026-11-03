import subprocess, numpy as np, sys
from binkparse import read_file
import binkenc
def decode(path):
    F=read_file(path); w,h=F['w'],F['h']
    raw=subprocess.run(['ffmpeg','-v','error','-i',path,'-f','rawvideo','-pix_fmt','yuv420p','-'],capture_output=True).stdout
    cw,ch=(w+1)//2,(h+1)//2; fs=w*h+2*cw*ch; out=[]
    for i in range(len(raw)//fs):
        b=np.frombuffer(raw,np.uint8,fs,i*fs)
        Y=b[:w*h].reshape(h,w); U=b[w*h:w*h+cw*ch].reshape(ch,cw); V=b[w*h+cw*ch:].reshape(ch,cw)
        out.append((Y.copy(),U.copy(),V.copy()))
    return out
if __name__=='__main__':
    for p in sys.argv[1:]:
        fr=decode(p); out='/tmp/rt.bik'
        binkenc.encode_file(p,fr,out)
        fr2=decode(out)
        ok=len(fr)==len(fr2) and all((a==b).all() for f1,f2 in zip(fr,fr2) for a,b in zip(f1,f2))
        import os
        print(p, len(fr), 'roundtrip', ok, os.path.getsize(p),'->',os.path.getsize(out))
