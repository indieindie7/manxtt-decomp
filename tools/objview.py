"""objview.py - quick textured software render of the OBJ files rbh2obj.py writes (local check only).

Run: py -3.13 -I tools/objview.py <out.png> <a.obj>[@dx,dy,dz] [b.obj ...] [--size 320]
Draws each OBJ from four sides (left, 3/4 front, front, top) with painter's sort and per-face texture
lookup (map_Kd from the MTL, colour 0 = transparent), so UV corner order and part placement can be checked.
"""
import sys, os, math
import numpy as np
from PIL import Image


def load_obj(path):
    d = os.path.dirname(path)
    V, T, faces, mats, cur = [], [], [], {}, None
    for line in open(path):
        p = line.split()
        if not p:
            continue
        if p[0] == 'mtllib':
            name = None
            for ml in open(os.path.join(d, p[1])):
                q = ml.split()
                if not q:
                    continue
                if q[0] == 'newmtl':
                    name = q[1]; mats[name] = {'kd': (1, 1, 1), 'tex': None}
                elif q[0] == 'Kd':
                    mats[name]['kd'] = tuple(float(x) for x in q[1:4])
                elif q[0] == 'map_Kd':
                    mats[name]['tex'] = np.asarray(Image.open(os.path.join(d, q[1])).convert('RGBA'))
        elif p[0] == 'v':
            V.append([float(x) for x in p[1:4]])
        elif p[0] == 'vt':
            T.append([float(x) for x in p[1:3]])
        elif p[0] == 'usemtl':
            cur = p[1]
        elif p[0] == 'f':
            vi, ti = [], []
            for c in p[1:]:
                s = c.split('/')
                vi.append(int(s[0]) - 1)
                ti.append(int(s[1]) - 1 if len(s) > 1 and s[1] else None)
            faces.append((vi, ti, cur))
    return np.array(V), np.array(T) if T else np.zeros((0, 2)), faces, mats


def rot(yaw, pitch):
    cy, sy, cp, sp = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch)
    ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
    return rx @ ry


def render(models, size, yaw, pitch):
    img = np.zeros((size, size, 3), np.uint8); img[:] = (40, 44, 52)
    allv = np.concatenate([m[0] for m in models])
    R = rot(yaw, pitch)
    P = allv @ R.T
    lo, hi = P.min(0), P.max(0)
    sc = 0.9 * size / max(hi[0] - lo[0], hi[1] - lo[1], 1e-6)
    cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
    tris = []
    for V, T, faces, mats in models:
        Q = V @ R.T
        for vi, ti, m in faces:
            for k in range(1, len(vi) - 1):
                idx = [0, k, k + 1]
                pts = Q[[vi[i] for i in idx]]
                uv = [T[ti[i]] if ti[i] is not None else None for i in idx]
                tris.append((pts[:, 2].mean(), pts, uv, mats.get(m)))
    tris.sort(key=lambda t: t[0])  # far (small z) first; camera looks down -z
    ys, xs = np.mgrid[0:size, 0:size]
    for _, pts, uv, mat in tris:
        sx = (pts[:, 0] - cx) * sc + size / 2
        sy = size / 2 - (pts[:, 1] - cy) * sc
        x0, x1 = int(max(0, sx.min())), int(min(size - 1, sx.max())) + 1
        y0, y1 = int(max(0, sy.min())), int(min(size - 1, sy.max())) + 1
        if x1 <= x0 or y1 <= y0:
            continue
        X, Y = xs[y0:y1, x0:x1] + 0.5, ys[y0:y1, x0:x1] + 0.5
        den = (sy[1] - sy[2]) * (sx[0] - sx[2]) + (sx[2] - sx[1]) * (sy[0] - sy[2])
        if abs(den) < 1e-9:
            continue
        a = ((sy[1] - sy[2]) * (X - sx[2]) + (sx[2] - sx[1]) * (Y - sy[2])) / den
        b = ((sy[2] - sy[0]) * (X - sx[2]) + (sx[0] - sx[2]) * (Y - sy[2])) / den
        c = 1 - a - b
        inside = (a >= 0) & (b >= 0) & (c >= 0)
        if not inside.any():
            continue
        kd = np.array(mat['kd'] if mat else (1, 0, 1))
        if mat and mat['tex'] is not None and uv[0] is not None:
            tex = mat['tex']; h, w = tex.shape[:2]
            u = a * uv[0][0] + b * uv[1][0] + c * uv[2][0]
            v = a * uv[0][1] + b * uv[1][1] + c * uv[2][1]
            tx = np.clip((u * w).astype(int), 0, w - 1)
            ty = np.clip(((1 - v) * h).astype(int), 0, h - 1)
            px = tex[ty, tx]
            ok = inside & (px[..., 3] > 0)
            img[y0:y1, x0:x1][ok] = px[..., :3][ok]
        else:
            img[y0:y1, x0:x1][inside] = (kd * 255).astype(np.uint8)
    return img


def main():
    a = sys.argv[1:]
    size = 320
    if '--size' in a:
        i = a.index('--size'); size = int(a[i + 1]); del a[i:i + 2]
    out, objs = a[0], a[1:]
    models = []
    for o in objs:  # optional placement: file.obj@dx,dy,dz (OBJ units)
        path, _, off = o.partition('@')
        V, T, F, M = load_obj(path)
        if off:
            V = V + np.array([float(x) for x in off.split(',')])
        models.append((V, T, F, M))
    # OBJ is y-up, +z forward (game z): left side, 3/4 front, front, top
    views = [(math.pi / 2, 0), (math.pi * 0.75, 0.35), (math.pi, 0), (math.pi, -math.pi / 2 + 0.01)]
    tiles = [render(models, size, y, p) for y, p in views]
    Image.fromarray(np.concatenate(tiles, 1)).save(out)
    print('wrote', out)


if __name__ == '__main__':
    main()
