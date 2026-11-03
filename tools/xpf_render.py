import sys,os,struct,zlib
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import xpf_probe as X
def frame(b,offs,i,W,H):
    f=b[offs[i]:offs[i+1]]; img=[[(255,0,255)]*W for _ in range(H)]
    p=1;y=0
    while p+3<=len(f) and y<H:
        x=struct.unpack('<H',f[p:p+2])[0]; n=f[p+2]; p+=3
        for k in range(n):
            if p+2>len(f): break
            v=struct.unpack('<H',f[p:p+2])[0];p+=2
            if x+k<W: img[y][x+k]=(((v>>11)&31)*255//31,((v>>5)&63)*255//63,(v&31)*255//31)
        y+=1
    return img
def png(rows,fn):
    H=len(rows);W=len(rows[0])
    raw=b''.join(b'\0'+bytes(c for px in r for c in px) for r in rows)
    def ch(t,d): c=struct.pack('>I',len(d))+t+d; return c+struct.pack('>I',zlib.crc32(t+d))
    open(fn,'wb').write(b'\x89PNG\r\n\x1a\n'+ch(b'IHDR',struct.pack('>IIBBBBB',W,H,8,2,0,0,0))+ch(b'IDAT',zlib.compress(raw))+ch(b'IEND',b''))
if __name__=='__main__':
    b=X.load(os.path.expanduser('~/mnt/Shattered Galaxy/NTF2.dat'),'ui-insg.xpf')
    offs=struct.unpack('<169I',b[14:14+676])
    frs=[0,1,2,3,8,9,10,11,16,17,18,19]
    rows=[]
    for r in range(0,12,2):
        a=frame(b,offs,frs[r],158,53);c=frame(b,offs,frs[r+1],158,53)
        rows+=[a[y]+[(0,0,0)]*4+c[y] for y in range(53)]+[[(0,0,0)]*320]*4
    png(rows,'/tmp/xp/insg0.png')
