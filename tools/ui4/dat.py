import struct
def entries(path):
    d=open(path,'rb').read(); n=struct.unpack_from('<I',d,0)[0]
    ent=[(struct.unpack_from('<I',d,4+17*i)[0], d[4+17*i+4:4+17*i+17].split(b'\0')[0].decode('latin1')) for i in range(n)]
    out={}
    for i,(o,nm) in enumerate(ent):
        if nm: out[nm]=d[o:(ent[i+1][0] if i+1<n else len(d))]
    return out
