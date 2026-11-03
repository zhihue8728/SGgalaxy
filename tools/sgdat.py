#!/usr/bin/env python3
"""Shattered Galaxy .dat archive tool.
Format (verified on pam/tc/hlp/ntt/oml): u32 LE count; then count entries of 17 bytes = u32 LE start offset + name[13] (NUL padded);
file i spans [off_i, off_{i+1}) and the last one runs to EOF. First offset == 4 + 17*count.
usage: sgdat.py list FILE | sgdat.py extract FILE OUTDIR [pattern] | sgdat.py cat FILE NAME"""
import struct, sys, os, fnmatch

def read_index(d):
    n = struct.unpack_from("<I", d, 0)[0]
    ents = []
    for i in range(n):
        o = 4 + 17 * i
        off = struct.unpack_from("<I", d, o)[0]
        name = d[o + 4:o + 17].split(b"\0")[0].decode("latin-1")
        ents.append((name, off))
    out = []
    for i, (name, off) in enumerate(ents):
        end = ents[i + 1][1] if i + 1 < n else len(d)
        out.append((name, off, end - off))
    return out

def main():
    cmd, path = sys.argv[1], sys.argv[2]
    d = open(path, "rb").read()
    idx = read_index(d)
    if cmd == "list":
        for name, off, size in idx:
            print(f"{name}\t{off}\t{size}\t{d[off:off+4].hex()}")
    elif cmd == "extract":
        out = sys.argv[3]; pat = sys.argv[4] if len(sys.argv) > 4 else "*"
        os.makedirs(out, exist_ok=True)
        for name, off, size in idx:
            if name and fnmatch.fnmatch(name.lower(), pat.lower()):
                open(os.path.join(out, name), "wb").write(d[off:off + size])
    elif cmd == "cat":
        for name, off, size in idx:
            if name.lower() == sys.argv[3].lower():
                sys.stdout.buffer.write(d[off:off + size])

if __name__ == "__main__":
    main()
