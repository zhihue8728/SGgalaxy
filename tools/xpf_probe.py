import sys,os,struct
sys.path.insert(0,os.path.join(os.path.dirname(__file__)))
import sgdat
def load(dat,name):
    d=open(dat,'rb').read()
    for a,o,s in sgdat.read_index(d):
        if a.lower()==name.lower(): return d[o:o+s]
def parse(f,w,h):
    p=1;lines=[]
    while p<len(f):
        x=struct.unpack('<H',f[p:p+2])[0]; n=f[p+2]; p+=3
        lines.append((x,n,p)); p+=n*2
    return lines,p
if __name__=='__main__':
    b=load(os.path.expanduser('~/mnt/Shattered Galaxy/NTF2.dat'),'ui-insg.xpf')
    offs=struct.unpack('<169I',b[14:14+676])
    for fr in (0,1,8):
        f=b[offs[fr]:offs[fr+1]]
        L,p=parse(f,158,53); print(fr,len(f),p,len(L),L[:4],L[-3:])
