#!/usr/bin/env python3
"""Walk grids for the server-side battle simulation (server/battlesim.py, user 2026-10-22 21:29: NPC battles always real).
For every map in server/spawn_spots.json: the 32-px cells where a 2x2 unit fits (flag 0x01 = blocked) AND that are
connected to the map's spawn spots.  Output server/walk_grids.json {map: [w, h, base64 bitmap row-major, bit = walkable]}.
usage: gen_walk_grids.py PAM.dat PAM3.dat SPAWN_SPOTS.json OUT.json"""
import sys, os, struct, json, base64
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sgdat
def main():
    pam, pam3, spots_f, out = sys.argv[1:5]
    files = {}
    for p in (pam, pam3):
        d = open(p, "rb").read()
        for n, o, s in sgdat.read_index(d):
            if n.lower().endswith(".nm"): files[n.lower()[:-3]] = d[o:o + s]
    spots = json.load(open(spots_f))
    res = {}
    for name, pts in sorted(spots.items()):
        b = files.get(name)
        if b is None: print("missing", name); continue
        w, h = struct.unpack_from("<HH", b, 1)
        blk = [b[5 + 3 * i + 2] & 1 for i in range(w * h)]
        free = lambda x, y: 0 <= x < w - 1 and 0 <= y < h - 1 and not (blk[y*w+x] | blk[y*w+x+1] | blk[(y+1)*w+x] | blk[(y+1)*w+x+1])
        seen = set(); st = [(px // 32, py // 32) for px, py in pts if free(px // 32, py // 32)]
        seen.update(st)
        while st:
            x, y = st.pop()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                q = (x + dx, y + dy)
                if q not in seen and free(*q): seen.add(q); st.append(q)
        bits = bytearray((w * h + 7) // 8)
        for x, y in seen: i = y * w + x; bits[i >> 3] |= 1 << (i & 7)
        res[name] = [w, h, base64.b64encode(bytes(bits)).decode()]
        print(f"{name}: {w}x{h} walkable {len(seen)}")
    json.dump(res, open(out, "w"))
if __name__ == "__main__":
    main()
