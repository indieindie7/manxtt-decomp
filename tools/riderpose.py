"""riderpose.py - pose a Manx TT rider (PRIDERS row OBJ from rbh2obj.py) with a RIDER_M clip key (local use only).

Run: py -3.13 -I tools/riderpose.py <PRIDERS_NN.obj> <RIDER_M.RBH> <clip> <key> <out.obj> [--bike]
  clip 1 = lean (15 keys, key 7 upright), 2 = stopped/idle, 3 = race finish, 4 = state 5 (see study_models.md).
  --bike also applies the bike-frame offsets (rider root T(0,-22,0), RotY 180 deg, key translation x4) so the
  result lines up with the livery body OBJ (rbh2obj default scale 1/32).
Skeleton and conventions: ghidra/study/study_models.md section 5 and "Resolved (models pass, 10-13)".
"""
import sys, struct, math
import numpy as np

SCALE = 1 / 32  # rbh2obj default
# (parent, translate (game units), full rotation or Z only, pose angle base index)
SKEL = [
    (None, (0, 2.16, 0), 'zyx', 0),
    (0, (5.63, -0.21, -6.08), 'zyx', 3),
    (1, (16.58, 0, 0), 'z', 6),
    (0, (5.60, -0.21, 6.09), 'zyx', 9),
    (3, (16.63, 0, 0), 'z', 12),
    (None, (0, 2.18, 0), 'zyx', 15),
    (5, (14.60, 0.18, 7.38), 'zyx', 18),
    (6, (11.32, 0, 0), 'z', 21),
    (5, (16.20, 0.018, 0.016), 'zyx', 24),
    (5, (14.66, 0.21, -7.37), 'zyx', 27),
    (9, (11.42, 0, 0), 'z', 30),
]


def ang(a):
    return (a & 0xfff) * 2 * math.pi / 4096


def rx(a):
    c, s = math.cos(ang(a)), math.sin(ang(a)); return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def ry(a):
    c, s = math.cos(ang(a)), math.sin(ang(a)); return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def rz(a):
    c, s = math.cos(ang(a)), math.sin(ang(a)); return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def mat(R=None, t=(0, 0, 0)):
    M = np.eye(4)
    if R is not None:
        M[:3, :3] = R
    M[:3, 3] = t
    return M


def rbh_block0(path):
    r = open(path, 'rb').read()
    p = 12
    while p < len(r):
        t, n = r[p:p + 4], struct.unpack('>I', r[p + 4:p + 8])[0]
        if t == b'BODY':
            return r[p + 8:p + 8 + n]
        p += 8 + n + (n & 1)


def clip_key(b, clip, key):
    c = struct.unpack_from('>I', b, clip * 4)[0]
    n = struct.unpack_from('>h', b, c)[0]
    key = max(0, min(key, n - 1))
    k = c + 4 + key * 16
    pp, x, y, z = struct.unpack_from('>Iiii', b, k)
    pose = struct.unpack_from('>33h', b, pp)
    return n, pose, (x / 65536, y / 65536, z / 65536)


def part_mats(pose):
    out = []
    for parent, t, kind, i in SKEL:
        M = mat(t=t)
        if kind == 'zyx':
            M = M @ mat(rz(pose[i + 2])) @ mat(ry(pose[i + 1])) @ mat(rx(pose[i]))
        else:
            M = M @ mat(rz(pose[i + 2]))
        out.append((out[parent] if parent is not None else np.eye(4)) @ M)
    return out


def main():
    a = sys.argv[1:]
    bike = '--bike' in a
    a = [x for x in a if x != '--bike']
    src, rbh, clip, key, dst = a[0], a[1], int(a[2]), int(a[3]), a[4]
    n, pose, kxyz = clip_key(rbh_block0(rbh), clip, key)
    mats = part_mats(pose)
    root = np.eye(4)
    if bike:
        root = mat(t=(0, -22.0, 0)) @ mat(ry(-2048)) @ mat(t=tuple(4 * v for v in kxyz))
    out, part = [], -1
    for line in open(src):
        if line.startswith('g part'):
            part = int(line[6:8])
        if line.startswith('v ') and part >= 0:
            x, y, z = (float(v) for v in line.split()[1:4])
            g = np.array([x / SCALE, -y / SCALE, z / SCALE, 1.0])
            w = root @ mats[part] @ g
            line = 'v %.5f %.5f %.5f\n' % (w[0] * SCALE, -w[1] * SCALE, w[2] * SCALE)
        out.append(line)
    open(dst, 'w').writelines(out)
    print('clip %d key %d of %d, key xyz %s -> %s' % (clip, key, n, kxyz, dst))


if __name__ == '__main__':
    main()
