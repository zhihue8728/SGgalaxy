"""OCR every frame of the UI sprites (NTF2/NTFB .xpf + .jpg) to find images that carry English text (i18n phase 4)."""
import sys,struct,io,os,json,subprocess,tempfile
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import xpf
from PIL import Image, ImageOps
G=os.path.expanduser('~/mnt/Shattered Galaxy/')
def entries(f):
    d=open(G+f,'rb').read(); n=struct.unpack_from('<I',d,0)[0]
    ent=[(struct.unpack_from('<I',d,4+17*i)[0], d[4+17*i+4:4+17*i+17].split(b'\0')[0].decode('latin1')) for i in range(n)]
    for i,(o,nm) in enumerate(ent):
        if nm: yield nm, d[o:(ent[i+1][0] if i+1<n else len(d))]
def ocr(im):
    bg=Image.new('RGB',im.size,(0,0,0)); bg.paste(im,(0,0),im if im.mode=='RGBA' else None)
    g=ImageOps.grayscale(bg); g=ImageOps.autocontrast(g)
    s=3 if g.width*g.height<60000 else (2 if g.width*g.height<250000 else 1)
    g=g.resize((g.width*s,g.height*s)); g=ImageOps.invert(g)
    fn=tempfile.mktemp(suffix='.png'); g.save(fn)
    r=subprocess.run(['tesseract',fn,'-','--psm','11'],capture_output=True,text=True).stdout
    os.remove(fn)
    return ' '.join(w for w in r.split() if sum(c.isalpha() for c in w)>=3)
import time
OUT=os.path.expanduser('~/mnt/SGgalaxy/out/ui_ocr.json')
out=json.load(open(OUT)) if os.path.exists(OUT) else {}
done=set(out.get('_done',[])); T0=time.time()
for f in ['NTF2.dat','NTFB.dat']:
    for nm,b in entries(f):
        key=f+':'+nm
        if key in done: continue
        if time.time()-T0>140: break
        done.add(key)
        try:
            if nm.lower().endswith('.xpf'):
                offs=xpf.offsets(b); seen=set(); res=[]
                for k in range(min(len(offs)-1,48)):
                    if time.time()-T0>150: raise TimeoutError
                    fb=b[offs[k]:offs[k+1]]
                    if len(fb)<=2 or fb in seen: continue
                    seen.add(fb); im=xpf.frame(b,k)
                    if im.width<16 or im.height<8: continue
                    t=ocr(im)
                    if t: res.append((k,t))
            elif nm.lower().endswith('.jpg'):
                t=ocr(Image.open(io.BytesIO(b)).convert('RGBA')); res=[(0,t)] if t else []
            else: continue
            if res: out[key]=res
        except TimeoutError:
            done.discard(key); break
        except Exception as e:
            out[f+':'+nm]=[(-1,'ERR '+str(e))]
out['_done']=sorted(done)
json.dump(out,open(OUT,'w'),indent=0)
print('done',len(done),'hits',len(out)-1)
