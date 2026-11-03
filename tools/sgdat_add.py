#!/usr/bin/env python3
"""Add/replace files in a Shattered Galaxy .dat (writes a NEW file, the source is untouched).
usage: sgdat_add.py SRC.dat OUT.dat file1 [file2 ...]   (entry name = file basename).  Keeps the index order
(sorted if the source is sorted, new names are inserted in order, otherwise appended)."""
import struct, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sgdat
def add(src, out, files):
    d = open(src, 'rb').read()
    ents = [(n, d[o:o + s]) for n, o, s in sgdat.read_index(d)]
    # the index ends with an EMPTY-NAME sentinel (2026-10-22: it was counted in the sort check -> 'not sorted' ->
    # new files were appended AFTER the sentinel and the client's (case-insensitive binary) search never found them)
    tail = [e for e in ents if not e[0]]
    ents = [e for e in ents if e[0]]
    names = [n.lower() for n, _ in ents]
    srt = names == sorted(names)
    for f in files:
        n = os.path.basename(f); data = open(f, 'rb').read()
        for i, (en, _) in enumerate(ents):
            if en.lower() == n.lower(): ents[i] = (en, data); break
        else:
            ents.append((n, data))
            if srt: ents.sort(key=lambda e: e[0].lower())
    ents += tail
    off = 4 + 17 * len(ents); idx = b''; body = b''
    for n, data in ents:
        idx += struct.pack('<I', off + len(body)) + n.encode('latin-1').ljust(13, b'\0'); body += data
    open(out, 'wb').write(struct.pack('<I', len(ents)) + idx + body)
    return srt, len(ents)
if __name__ == '__main__':
    print(add(sys.argv[1], sys.argv[2], sys.argv[3:]))
