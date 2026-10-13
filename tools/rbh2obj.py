#!/usr/bin/env python3
"""rbh2obj.py - export Manx TT (Sega Saturn) model RBH files to OBJ + MTL + PNG.

Run:  py -3.13 -I tools/rbh2obj.py <file.RBH> <outdir> [--vri A.VRI.chunks [--vri B...]] [--scale S] [--preview]

Formats are documented in ghidra/study/study_models.md.  Local use only: the output
contains game data and must not be copied outside C:/Users/john/Documents/ManxTT.

  * RBH = 'BIFF' container, blocks in BODY chunks, RELC chunks add block bases at pointer
    fields.  Here pointers are kept as (block offset) values; block 1 = object headers +
    command lists, block 2 = vertices (3 x s32), block 3 = per-object cells, block 0 = table
    of root pointers.
  * Object header (block 1): +0 cmd list, +4 vertices, +8 link, +0xC cell, +0x10 s16 vertex
    count, +0x14/+0x18 fixed 16.16 radii.
  * Command list: {u16 nfaces, u16 type|mode<<14, u16 ?, u16 size_in_u16}, payload = 4-byte
    prefix + nfaces * stride (12 flat, 16 textured); face = 4 u16 vertex byte offsets
    (index*12) + attrs.
  * VDP1 textures come from the VRI VRAM chunks (0x25C0xxxx), 4bpp LUT16 + RGB555 CLUT.
"""
import argparse
import os
import struct
import sys
import zlib


def u16(b, o): return struct.unpack_from('>H', b, o)[0]
def s16(b, o): return struct.unpack_from('>h', b, o)[0]
def u32(b, o): return struct.unpack_from('>I', b, o)[0]
def s32(b, o): return struct.unpack_from('>i', b, o)[0]


# ----------------------------------------------------------------------------- RBH
class Rbh:
    def __init__(self, path):
        d = open(path, 'rb').read()
        if d[:4] != b'BIFF' or d[8:12] != b'RBHF':
            raise SystemExit('not a BIFF/RBHF file: ' + path)
        pos = 12
        self.table = []
        self.blocks = []
        self.relocs = []   # (src block, dst block, [offsets])
        while pos + 8 <= len(d):
            tag = d[pos:pos + 4]
            size = u32(d, pos + 4)
            c = d[pos + 8:pos + 8 + size]
            pos += 8 + size
            if tag == b'RBHH':
                self.table = [struct.unpack('>IIHH', c[i:i + 12]) for i in range(0, len(c), 12)]
            elif tag == b'BODY':
                self.blocks.append(c)
            elif tag == b'RELC':
                a, b = struct.unpack('>II', c[:8])
                self.relocs.append((a, b, [u32(c, i) for i in range(8, len(c) - 3, 4)]))
        for (_, sz, _, _), blk in zip(self.table, self.blocks):
            assert sz == len(blk), 'block size mismatch'
        # pointer fields: (block, offset) -> target block (value stays a block-relative offset)
        self.ptr = {}
        for a, b, offs in self.relocs:
            for o in offs:
                self.ptr[(a, o)] = b


def find_objects(r):
    """Object headers: block-1 words at +4 that point into the vertex block (reloc 1->2)."""
    return sorted({o - 4 for (a, o), b in r.ptr.items() if a == 1 and b == 2})


FACE_STRIDE = {0: 12, 1: 16, 8: 16, 9: 20}   # type & 0xff ; 0x200 flag = double sided


def parse_object(r, off):
    B, V = r.blocks[1], r.blocks[2]
    cmd, vp, n = u32(B, off), u32(B, off + 4), s16(B, off + 0x10)
    verts = [(s32(V, vp + 12 * i), s32(V, vp + 12 * i + 4), s32(V, vp + 12 * i + 8)) for i in range(n)]
    faces = []
    c = cmd
    while True:
        cnt = u16(B, c)
        if cnt == 0:
            break
        w1 = u16(B, c + 2)
        ty, mode = w1 & 0x3fff, w1 >> 14
        two = bool(ty & 0x200)
        base = ty & 0xff
        size = u16(B, c + 6) * 2
        stride = FACE_STRIDE[base]
        assert 4 + stride * cnt == size, (hex(off), hex(c))
        for k in range(cnt):
            p = c + 8 + 4 + stride * k
            idx = [u16(B, p + 2 * j) // 12 for j in range(4)]
            a = [u16(B, p + 8 + 2 * j) for j in range((stride - 8) // 2)]
            f = dict(idx=idx, mode=mode, two=two, kind=base)
            if stride == 12:
                f.update(pmod=a[0], colr=a[1], srca=None, size=None)
            else:
                f.update(srca=a[0], size=a[1], pmod=a[2], colr=a[3])
            faces.append(f)
        c += 8 + size
    return dict(off=off, verts=verts, faces=faces, radius=u32(B, off + 0x14) / 65536.0)


# ----------------------------------------------------------------------------- VRAM / textures
class Vram:
    def __init__(self, vri_paths):
        self.mem = bytearray(0x80000)
        for p in vri_paths:
            d = open(p, 'rb').read()
            pos = 0
            while pos + 8 <= len(d):
                dest, sz = struct.unpack_from('>II', d, pos)
                if dest == 0:
                    break
                data = d[pos + 8:pos + 8 + sz]
                pos += 8 + sz
                if 0x25C00000 <= dest < 0x25C80000:
                    o = dest - 0x25C00000
                    self.mem[o:o + len(data)] = data

    def clut(self, colr):
        a = colr * 8
        return [rgb555(u16(self.mem, a + 2 * i)) for i in range(16)]

    def tex16(self, srca, size, colr):
        w, h = ((size >> 8) & 0x3f) * 8, size & 0xff
        a = srca * 8
        pal = self.clut(colr)
        rows = []
        for y in range(h):
            row = []
            for x in range(w):
                byte = self.mem[a + (y * w + x) // 2]
                nib = (byte >> 4) if x % 2 == 0 else (byte & 15)
                row.append(pal[nib] if nib else (0, 0, 0, 0))   # colour 0 = transparent
            rows.append(row)
        return w, h, rows


def rgb555(v):
    return ((v & 31) << 3 | (v & 31) >> 2, (v >> 5 & 31) << 3 | (v >> 5 & 31) >> 2,
            (v >> 10 & 31) << 3 | (v >> 10 & 31) >> 2, 255)


def write_png(path, w, h, rows):
    raw = b''.join(b'\x00' + b''.join(bytes(px) for px in row) for row in rows)

    def chunk(t, d):
        c = struct.pack('>I', len(d)) + t + d
        return c + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    open(path, 'wb').write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0))
                           + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))


# ----------------------------------------------------------------------------- OBJ writer
class Writer:
    def __init__(self, outdir, name, vram, scale):
        self.dir, self.name, self.vram, self.scale = outdir, name, vram, scale
        self.mats = {}     # key -> material name
        os.makedirs(outdir, exist_ok=True)

    def material(self, f):
        pm = f['pmod']
        cm = (pm >> 3) & 7
        if f['srca'] is None or cm != 1:
            if f['srca'] is None:
                if cm == 5:
                    r, g, b, _ = rgb555(f['colr'])
                    key = ('flat', f['colr'])
                    return key, 'flat_%04x' % f['colr'], (r, g, b), None
                return ('flatidx', f['colr']), 'flatidx_%04x' % f['colr'], (160, 160, 160), None
            return ('tex', f['srca'], f['size'], pm, f['colr']), 'tex_%04x_%04x_cm%d' % (f['srca'], f['colr'], cm), (160, 160, 160), None
        key = ('tex', f['srca'], f['size'], f['colr'])
        name = 'tex_%04x_%04x_%04x' % (f['srca'], f['size'], f['colr'])
        return key, name, (255, 255, 255), (f['srca'], f['size'], f['colr'])

    def write(self, fname, groups):
        """groups: list of (groupname, obj dict).  Writes fname.obj + fname.mtl + PNGs."""
        s = self.scale
        lines = ['# Manx TT model export (local use only)', 'mtllib %s.mtl' % fname]
        mats = {}
        vbase = 0
        vtbase = 0
        uvs = [(0, 1), (1, 1), (1, 0), (0, 0)]   # A top-left, B top-right, C bottom-right, D bottom-left (v up)
        for gname, ob in groups:
            lines.append('g %s' % gname)
            for x, y, z in ob['verts']:
                lines.append('v %.5f %.5f %.5f' % (x * s, -y * s, z * s))     # game y is down
            if any(f['srca'] is not None for f in ob['faces']):
                for u, v in uvs:
                    lines.append('vt %d %d' % (u, v))
            cur = None
            have_uv = any(f['srca'] is not None for f in ob['faces'])
            for f in ob['faces']:
                key, mname, col, tex = self.material(f)
                if key not in mats:
                    mats[key] = (mname, col, tex)
                if cur != mname:
                    lines.append('usemtl %s' % mname)
                    cur = mname
                i = f['idx']
                quad = [i[0], i[1], i[2], i[3]]
                corners = [0, 1, 2, 3]
                if i[3] == i[2] or i[3] == i[0]:   # triangle: last index repeats
                    quad = [i[0], i[1], i[2]]
                    corners = [0, 1, 2]
                # axis flip (y -> -y) mirrors the winding: emit reversed order so normals face out
                order = list(range(len(quad)))[::-1]
                vt_here = f['srca'] is not None and have_uv
                def ref(k):
                    vi = quad[k] + 1 + vbase
                    if vt_here:
                        return '%d/%d' % (vi, vtbase + corners[k] + 1)
                    return '%d' % vi
                lines.append('f ' + ' '.join(ref(k) for k in order))
                if f['two']:
                    lines.append('f ' + ' '.join(ref(k) for k in order[::-1]))
            vbase += len(ob['verts'])
            if any(f['srca'] is not None for f in ob['faces']):
                vtbase += 4
        open(os.path.join(self.dir, fname + '.obj'), 'w').write('\n'.join(lines) + '\n')
        ml = []
        for key, (mname, col, tex) in mats.items():
            ml.append('newmtl %s' % mname)
            ml.append('Kd %.3f %.3f %.3f' % tuple(c / 255.0 for c in col))
            if tex and self.vram:
                pn = '%s.png' % mname
                pp = os.path.join(self.dir, pn)
                if not os.path.exists(pp):
                    w, h, rows = self.vram.tex16(*tex)
                    write_png(pp, w, h, rows)
                ml.append('map_Kd %s' % pn)
                ml.append('map_d %s' % pn)
            ml.append('')
        open(os.path.join(self.dir, fname + '.mtl'), 'w').write('\n'.join(ml))


# ----------------------------------------------------------------------------- preview
def preview(path, groups_list, title):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    fig, axes = plt.subplots(1, 3, figsize=(15, 6))
    views = [('side (z, up)', 2, 1), ('front (x, up)', 0, 1), ('top (x, z)', 0, 2)]
    for ax, (nm, ca, cb) in zip(axes, views):
        polys, cols = [], []
        for gi, (gname, ob) in enumerate(groups_list):
            for f in ob['faces']:
                idx = [i for k, i in enumerate(f['idx']) if k < 3 or i != f['idx'][2]]
                pts = [(ob['verts'][i][ca], -ob['verts'][i][cb] if cb == 1 else ob['verts'][i][cb]) for i in idx]
                polys.append(pts)
                cols.append(plt.cm.tab20(gi % 20))
        ax.add_collection(PolyCollection(polys, facecolors=cols, edgecolors='k', linewidths=0.2, alpha=0.7))
        ax.autoscale()
        ax.set_aspect('equal')
        ax.set_title(nm)
    fig.suptitle(title)
    fig.savefig(path, dpi=80)
    plt.close(fig)


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('rbh')
    ap.add_argument('outdir')
    ap.add_argument('--vri', action='append', default=[], help='VRI.chunks to load into VDP1 VRAM (in load order)')
    ap.add_argument('--scale', type=float, default=1 / 32.0, help='vertex scale (default 1/32) [guess]')
    ap.add_argument('--preview', action='store_true', help='write preview PNGs with matplotlib')
    a = ap.parse_args()
    r = Rbh(a.rbh)
    base = os.path.splitext(os.path.basename(a.rbh))[0]
    base = base.split('_', 1)[1] if base[:3].isdigit() else base
    vram = Vram(a.vri) if a.vri else None
    w = Writer(a.outdir, base, vram, a.scale)
    objs = find_objects(r)
    parsed = {o: parse_object(r, o) for o in objs}
    print('%s: %d blocks, %d objects' % (base, len(r.blocks), len(objs)))
    B = r.blocks[1]
    # root table (block 0): u32 pointers either to objects directly or to rows of object pointers
    roots = [u32(r.blocks[0], i) for i in range(0, len(r.blocks[0]), 4)] if r.blocks[0] else []
    rows = {}
    if roots and all(x in parsed for x in roots):
        for i, x in enumerate(roots):
            rows[i] = [x]
    elif roots:
        first_cmd = min(parsed[o]['off'] for o in objs)
        first_cmd = min(u32(B, o) for o in objs)
        rl = first_cmd // 4 // len(roots)           # table is root-rows * rowlen pointers [guess]
        for i, x in enumerate(roots):
            rows[i] = [u32(B, x + 4 * k) for k in range(rl)]
    # one OBJ per root entry (a bike model / a rider pose), parts as OBJ groups
    prev_groups = []
    for i, offs in rows.items():
        groups = [('part%02d_%x' % (k, o), parsed[o]) for k, o in enumerate(offs) if o in parsed]
        w.write('%s_%02d' % (base, i), groups)
        prev_groups.append(groups)
    # objects not reachable from the root table
    reach = {o for offs in rows.values() for o in offs}
    extra = [o for o in objs if o not in reach]
    for o in extra:
        w.write('%s_obj%05x' % (base, o), [('obj_%x' % o, parsed[o])])
    print('wrote %d root models + %d loose objects to %s' % (len(rows), len(extra), a.outdir))
    if a.preview:
        if rows:
            preview(os.path.join(a.outdir, base + '_preview.png'), prev_groups[0], base + ' root 0')
        # contact sheet: first object of several roots
        for i in sorted(rows)[:1]:
            pass


if __name__ == '__main__':
    main()
