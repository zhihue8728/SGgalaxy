"""Fit the 3D rig to the original sprite frames (2026-11-04, user: "the character already has a skeleton; adjust the
skeleton to each pose in the xpf").  For one action, every frame f has the same 3D pose seen from 8 directions, so the
8 original silhouettes (xpf body layer) + the blade pixels (b / glow layer) constrain the pose well.

Input: the rig export (Blender: bones' rest matrices, mesh vertices + weights + triangles, and for each direction the
affine armature-space -> pixel map of the sprite camera, canvas = the xpf canvas) and the original .xpf files.
Model: Blender's pose math (M_b = M_parent @ inv(Rest_parent) @ Rest_b @ Basis_b, linear blend skinning), surface
points splatted into each view.  Loss per view: 1 - IoU(body) + blade chamfer distance; + small regularisers (rotation
size, closeness to the previous frame).  Optimiser: adaptive coordinate / random search, frame by frame, previous
frame as the start, then a smoothing pass over the loop.
Output JSON: per frame {bone: quaternion (w, x, y, z)}, root location -> applied in Blender as action keys."""
import json, math, sys, os
import numpy as np
import cv2

FIT_BONES = {   # bone: number of rotation dofs (local axis-angle; 1 = about the bone's local x axis)
    'Bone_000': 3, 'Bone_004': 3, 'Bone_002': 3,
    'Bone_021': 3, 'Bone_020': 3,                        # left arm (free)
    'Bone_026': 3, 'Bone_025': 3, 'Bone_024': 3,         # right arm (sword)
    'Bone_009': 3, 'Bone_008': 3, 'Bone_014': 3, 'Bone_013': 3,
}
BLADE = ('Bone_044', 'Bone_043')


def rotvec_to_mat(v):
    th = float(np.linalg.norm(v))
    if th < 1e-9: return np.eye(3)
    k = v / th; K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + math.sin(th) * K + (1 - math.cos(th)) * K @ K


def rotvec_to_quat(v):
    th = float(np.linalg.norm(v))
    if th < 1e-9: return [1.0, 0.0, 0.0, 0.0]
    k = v / th; s = math.sin(th / 2)
    return [math.cos(th / 2), k[0] * s, k[1] * s, k[2] * s]


class Rig:
    def __init__(self, path, npts=16000, seed=1):
        d = json.load(open(path))
        self.proj = {int(k): np.array(v, np.float64) for k, v in d['proj'].items()}
        bones = d['bones']; self.names = [b['name'] for b in bones]; self.idx = {n: i for i, n in enumerate(self.names)}
        self.parent = [self.idx[b['parent']] if b['parent'] else -1 for b in bones]
        self.rest = np.array([b['m'] for b in bones], np.float64)
        self.rest_inv = np.linalg.inv(self.rest)
        order, seen = [], set()
        def visit(i):
            if i in seen: return
            if self.parent[i] >= 0: visit(self.parent[i])
            seen.add(i); order.append(i)
        for i in range(len(bones)): visit(i)
        self.order = order
        self.rel = [self.rest_inv[p] @ self.rest[i] if p >= 0 else self.rest[i] for i, p in enumerate(self.parent)]
        V = np.array(d['verts'], np.float64); T = np.array(d['tris'], np.int64)
        W = np.zeros((len(V), 4)); B = np.zeros((len(V), 4), np.int64)
        for i, ws in enumerate(d['w']):
            ws = sorted(ws, key=lambda x: -x[1])[:4]
            for j, (n, w) in enumerate(ws): W[i, j] = w; B[i, j] = self.idx[n]
        W /= np.maximum(W.sum(1, keepdims=True), 1e-9)
        # area-weighted surface samples (vertex attributes from the nearest corner: weights stay per-vertex)
        rng = np.random.default_rng(seed)
        a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
        area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
        ti = rng.choice(len(T), npts, p=area / area.sum())
        r1, r2 = rng.random(npts), rng.random(npts); s = np.sqrt(r1)
        bc = np.stack([1 - s, s * (1 - r2), s * r2], 1)
        self.P = (bc[:, :1] * a[ti] + bc[:, 1:2] * b[ti] + bc[:, 2:3] * c[ti])
        corner = T[ti, np.argmax(bc, 1)]
        self.PW, self.PB = W[corner], B[corner]
        self.Ph = np.c_[self.P, np.ones(npts)]
        self.tail_blade = np.array(d.get('blade_tail', [-0.681, 0.296, 1.843]))

    def pose(self, rot, loc=None):
        """rot: {bone: rotvec (local)} -> bone matrices (armature space)"""
        M = [None] * len(self.names)
        for i in self.order:
            basis = np.eye(4)
            v = rot.get(self.names[i])
            if v is not None: basis[:3, :3] = rotvec_to_mat(np.asarray(v, np.float64))
            if loc is not None and self.parent[i] < 0: basis[:3, 3] = loc
            p = self.parent[i]
            M[i] = (M[p] @ self.rel[i] if p >= 0 else self.rel[i]) @ basis
        return np.array(M)

    def skin(self, M):
        S = M @ self.rest_inv                                   # (nb, 4, 4)
        out = np.zeros((len(self.P), 3))
        for j in range(4):
            Sj = S[self.PB[:, j]]
            out += self.PW[:, j:j + 1] * np.einsum('nij,nj->ni', Sj[:, :3, :], self.Ph)
        return out

    def project(self, X, d):
        A = self.proj[d]; return X @ A[:, :3].T + A[:, 3]

    def blade(self, M):
        h = self.rest[self.idx[BLADE[0]]][:3, 3]
        Mh = M[self.idx[BLADE[0]]] @ self.rest_inv[self.idx[BLADE[0]]]
        Mt = M[self.idx[BLADE[1]]] @ self.rest_inv[self.idx[BLADE[1]]]
        return (Mh @ np.r_[h, 1])[:3], (Mt @ np.r_[self.tail_blade, 1])[:3]


def load_targets(dat_paths, body, glow, dirs=8):
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import sgdat, xpfx
    files = {}
    for p in dat_paths:
        b = open(p, 'rb').read()
        for n, o, l in sgdat.read_index(b): files.setdefault(n.lower(), b[o:o + l])
    ib, fb = xpfx.frames(files[body]); ig, fg = xpfx.frames(files[glow])
    fpd = len(fb) // dirs
    T = {}
    for f in range(fpd):
        for d in range(dirs):
            k = f * dirs + d
            m = fb[k][..., 3] > 0 if k in fb else np.zeros((ib['h'], ib['w']), bool)
            g = fg.get(k); gm = (g[..., :3].max(2) > 40) & (g[..., 3] > 0) if g is not None else np.zeros_like(m)
            dist = cv2.distanceTransform((~gm).astype(np.uint8), cv2.DIST_L2, 3) if gm.any() else None
            T[(f, d)] = dict(body=m, glow=gm, gdist=dist)
    return T, fpd, (ib['w'], ib['h'])


class Fitter:
    def __init__(self, rig, T, size, dirs=8, blade_w=0.04):
        self.rig, self.T, self.size, self.dirs, self.blade_w = rig, T, size, dirs, blade_w
        self.keys = [(b, n) for b, n in FIT_BONES.items()]
        self.nx = sum(n for _, n in self.keys) + 1              # + root height

    def unpack(self, x):
        rot, i = {}, 0
        for b, n in self.keys:
            rot[b] = x[i:i + 3] if n == 3 else np.array([x[i], 0, 0]); i += n
        return rot, np.array([0, 0, x[i]])

    def render(self, X, d):
        W, H = self.size; uv = self.rig.project(X, d)
        u = np.round(uv[:, 0]).astype(int); v = np.round(uv[:, 1]).astype(int)
        ok = (u >= 0) & (u < W) & (v >= 0) & (v < H)
        m = np.zeros((H, W), np.uint8); m[v[ok], u[ok]] = 1
        return cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8)).astype(bool)

    def loss(self, x, f, prev=None, detail=False):
        rot, loc = self.unpack(x)
        M = self.rig.pose(rot, loc); X = self.rig.skin(M)
        bh, bt = self.rig.blade(M)
        L = 0.0; ious = []
        for d in range(self.dirs):
            t = self.T[(f, d)]; m = self.render(X, d)
            inter = (m & t['body']).sum(); uni = (m | t['body']).sum()
            iou = inter / max(uni, 1); ious.append(iou); L += 1 - iou
            if t['gdist'] is not None:
                p = self.rig.project(np.linspace(bh, bt, 16), d)
                W, H = self.size
                u = np.clip(p[:, 0], 0, W - 1).astype(int); v = np.clip(p[:, 1], 0, H - 1).astype(int)
                fwd = t['gdist'][v, u].mean()
                gy, gx = np.nonzero(t['glow'])
                seg = p[-1] - p[0]; l2 = max(seg @ seg, 1e-6)
                q = np.stack([gx, gy], 1) - p[0]; tt = np.clip(q @ seg / l2, 0, 1)
                back = np.linalg.norm(q - tt[:, None] * seg, axis=1).mean()
                L += self.blade_w * (fwd + back)
        L += 0.02 * float(np.sum(x[:-1] ** 2))
        if prev is not None: L += 0.15 * float(np.sum((x - prev) ** 2))
        return (L, ious) if detail else L

    def fit(self, f, x0, prev=None, iters=1500, seed=0, step=0.25):
        rng = np.random.default_rng(seed)
        x = x0.copy(); best = self.loss(x, f, prev); sig = np.full(self.nx, step); sig[-1] = 0.03
        for it in range(iters):
            y = x.copy()
            if rng.random() < 0.5:
                j = rng.integers(self.nx); y[j] += rng.normal() * sig[j]
            else:
                mask = rng.random(self.nx) < 0.25; y[mask] += rng.normal(size=mask.sum()) * sig[mask] * 0.6
            ly = self.loss(y, f, prev)
            if ly < best:
                x, best = y, ly; sig = np.minimum(sig * 1.15, 0.6)
            else:
                sig *= 0.995
            sig = np.maximum(sig, 0.01)
        return x, best


def fit_action(F, fpd, restarts=3, log=print):
    """frame 0 from the rest pose (best of a few restarts), then each frame from the previous one, then two
    smoothing passes that pull every frame towards the mean of its neighbours (the action loops)"""
    best = None
    for seed in range(restarts):
        x, L = F.fit(0, np.zeros(F.nx), iters=2500, seed=seed)
        if best is None or L < best[1]: best = (x, L)
    xs = [best[0]]; log(f'frame 0: {best[1]:.3f}')
    for f in range(1, fpd):
        x, L = F.fit(f, xs[-1], prev=xs[-1], iters=1800, seed=f, step=0.15); xs.append(x); log(f'frame {f}: {L:.3f}')
    for p in range(2):
        for f in range(fpd):
            nb = (xs[(f - 1) % fpd] + xs[(f + 1) % fpd]) / 2
            xs[f], _ = F.fit(f, xs[f], prev=nb, iters=700, seed=100 + f + p * 20, step=0.08)
    return xs


def to_frames(F, xs):
    out = []
    for x in xs:
        rot, loc = F.unpack(x)
        out.append({'rot': {b: rotvec_to_quat(np.asarray(v)) for b, v in rot.items()}, 'loc': [float(c) for c in loc]})
    return out


if __name__ == '__main__':
    # python art3d/rigfit.py RIG.json BODY.xpf GLOW.xpf OUT.json DAT[,DAT]    (g039: g039mo.xpf g039mob.xpf)
    rigp, body, glow, outp, dats = sys.argv[1:6]
    rig = Rig(rigp)
    T, fpd, size = load_targets(dats.split(','), body.lower(), glow.lower())
    F = Fitter(rig, T, size)
    xs = fit_action(F, fpd)
    for f, x in enumerate(xs):
        L, ious = F.loss(x, f, detail=True); print(f'frame {f}: loss {L:.2f}, mean IoU {np.mean(ious):.3f}')
    json.dump(to_frames(F, xs), open(outp, 'w'))
    print(f'{outp}: {fpd} frames (Blender: g039_pipeline.apply_fit(act, path))')
