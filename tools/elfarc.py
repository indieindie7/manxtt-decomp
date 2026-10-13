#!/usr/bin/env python3
"""elfarc.py - Manx TT Super Bike (Saturn) CDIMAGE.ELF archive tool (research, read-only on the input).

  py -3.13 -I elfarc.py list    <CDIMAGE.ELF> [--exe 0.AAA]
  py -3.13 -I elfarc.py extract <CDIMAGE.ELF> <outdir> [--exe 0.AAA]

Archive layout (see ghidra/study/study_archive.md):
  header 16 bytes, big endian: u32 NumFiles, u32 HashWeight(=1), u32 (=2, unused by loader), u32 VolumeID(=0)
  TOC at 0x10: NumFiles * 16 bytes {u32 hash, u32 start_sector(2048), u32 size_bytes, u32 sector_count}
  hash(name): h=0; for each char c (signed): h = h + c + h*HashWeight   (32 bit)  -> only the last ~32 chars matter
  file data at start_sector*2048, entries are contiguous and sector aligned.
Entry formats (all stored data is big endian):
  BIFF  : 'BIFF' u32 size, 'RBHF', then chunks {tag,u32 size,data}: RBHH (table of 12-byte {ptr,size,flags}),
          PACK (LZ blocks: u16 outlen, u16 inlen, stream; ends with outlen==0), BODY (raw), RELC (fixups)
  CHUNKS: list of {u32 dest, u32 size|0x80000000 if compressed, data} ending with dest==0 (VDP1/VDP2/sound RAM loads)
  RIFF  : movie (AVI/Cinepak style), streamed, not decoded here.
Extract: BIFF is written with every PACK decompressed into a BODY chunk (same container otherwise);
CHUNKS is written as decoded concatenation of [u32 dest][u32 len][data] records (".chunks");
RIFF and unknown are written raw.
"""
import struct, sys, os, re


def u32(b, o):
    return struct.unpack_from('>I', b, o)[0]


def name_hash(s, w=1):
    h = 0
    for c in s.encode('latin1'):
        if c > 127:
            c -= 256
        h = (h + c + h * w) & 0xFFFFFFFF
    return h


def find_names(exe_path, hashes, w):
    """hash -> name by hashing every 'W:\\...' style string found in the game executable (0.AAA)."""
    names = {}
    try:
        d = open(exe_path, 'rb').read()
    except OSError:
        return names
    for m in re.finditer(rb'[ -~]{4,100}', d):
        s = m.group().decode('latin1')
        starts = [i for i in range(len(s)) if s[i:i + 3] == 'W:\\']
        for i in starts or [0]:
            for cand in (s[i:], s[i:].upper()):
                h = name_hash(cand, w)
                if h in hashes and h not in names:
                    names[h] = cand
    return names


# ---- decompression ---------------------------------------------------------------------------
def _varint(b, p):
    """stream_ReadVarInt 0x06042498: bit7 continue, bit6 sign (first byte), 6 low bits, then 7-bit groups."""
    x = b[p]; p += 1
    sign = -1 if x & 0x40 else 1
    v = x & 0x3F
    sh = 6
    if x & 0x80:
        while True:
            x = b[p]; p += 1
            v |= (x & 0x7F) << sh
            sh += 7
            if not x & 0x80:
                break
    return v * sign, p


def lz_decode(src, outlen):
    """stream_DecodeLz 0x06042568 / lz_DecodeVarintBackref 0x060487b4.
    token>0: copy token literal bytes; token<0: copy -token bytes from absolute output offset (next varint)."""
    out = bytearray()
    p = 0
    while len(out) < outlen:
        n, p = _varint(src, p)
        if n < 0:
            n = -n
            off, p = _varint(src, p)
            for k in range(n):
                out.append(out[off + k])
        elif n == 0:
            raise ValueError('zero-length token')
        else:
            out += src[p:p + n]
            p += n
    return bytes(out), p


def parse_chunks(b):
    """returns list of (dest, data) or None if not a plausible chunk list."""
    p = 0
    res = []
    while p + 8 <= len(b):
        dest = u32(b, p)
        sz = u32(b, p + 4)
        if dest == 0:
            return res if p + 8 <= len(b) else None
        p += 8
        comp = bool(sz & 0x80000000)
        sz &= 0x7FFFFFFF
        if p + sz > len(b):
            return None
        if comp:
            ulen = u32(b, p)
            try:
                data, _ = lz_decode(b[p + 4:p + sz], ulen)
            except Exception:
                return None
            p += sz
            if sz & 3:
                p += 4 - (sz & 3)
        else:
            data = b[p:p + sz]
            p += sz
        res.append((dest, data))
    return None


def parse_biff(b):
    """returns (table, chunks) ; chunks = list of (tag, payload) with PACK decoded."""
    assert b[:4] == b'BIFF' and b[8:12] == b'RBHF'
    total = u32(b, 4) + 8
    p = 12
    chunks = []
    while p + 8 <= total:
        tag = b[p:p + 4]
        sz = u32(b, p + 4)
        data = b[p + 8:p + 8 + sz]
        p += 8 + sz
        if tag == b'PACK':
            out = bytearray()
            q = 0
            while q + 2 <= len(data):
                ol = struct.unpack_from('>H', data, q)[0]; q += 2
                if ol == 0:
                    break
                il = struct.unpack_from('>H', data, q)[0]; q += 2
                d, _ = lz_decode(data[q:q + il], ol)
                out += d
                q += il
            chunks.append((b'BODY', bytes(out), True))
        else:
            chunks.append((tag, data, False))
    table = []
    for tag, data, _ in chunks:
        if tag == b'RBHH':
            for i in range(len(data) // 12):
                table.append(struct.unpack_from('>IIHH', data, i * 12))
    return table, chunks


def classify(b):
    if b[:4] == b'BIFF':
        return 'BIFF'
    if b[:4] == b'RIFF':
        return 'RIFF'
    c = parse_chunks(b) if len(b) >= 8 else None
    if c:
        return 'CHUNKS'
    return 'RAW'


def read_toc(f):
    f.seek(0)
    n, w, x, vol = struct.unpack('>4I', f.read(16))
    toc = [struct.unpack('>4I', f.read(16)) for _ in range(n)]
    return (n, w, x, vol), toc


def main(argv):
    if len(argv) < 3 or argv[1] not in ('list', 'extract'):
        print(__doc__)
        return 1
    exe = None
    args = argv[2:]
    if '--exe' in args:
        i = args.index('--exe'); exe = args[i + 1]; del args[i:i + 2]
    path = args[0]
    if exe is None:
        exe = os.path.join(os.path.dirname(os.path.abspath(path)), '0.AAA')
    f = open(path, 'rb')
    (n, w, x, vol), toc = read_toc(f)
    names = find_names(exe, {t[0] for t in toc}, w)
    outdir = args[1] if argv[1] == 'extract' else None
    if outdir:
        os.makedirs(outdir, exist_ok=True)
    if argv[1] == 'list':
        print('NumFiles=%d HashWeight=%d hdr3=%d VolumeID=%d' % (n, w, x, vol))
    for i, (h, sec, size, cnt) in enumerate(toc):
        f.seek(sec * 2048)
        b = f.read(size) if (outdir or size < 0x200000) else f.read(0x1000)
        kind = classify(b) if len(b) == size else ('RIFF' if b[:4] == b'RIFF' else '?')
        nm = names.get(h, '')
        if argv[1] == 'list':
            print('%3d  off=0x%08x size=%9d sec=%5d n=%5d hash=%08x %-6s %s  %s' %
                  (i, sec * 2048, size, sec, cnt, h, kind, b[:4].hex(), nm))
            continue
        base = os.path.basename(nm.replace('\\', '/')) if nm else 'h%08x' % h
        fn = '%03d_%s' % (i, base)
        if kind == 'BIFF':
            table, chunks = parse_biff(b)
            outb = bytearray(b'BIFF\0\0\0\0RBHF')
            for tag, data, _ in chunks:
                outb += tag + struct.pack('>I', len(data)) + data
            outb[4:8] = struct.pack('>I', len(outb) - 8)
            data = bytes(outb)
        elif kind == 'CHUNKS':
            data = b''.join(struct.pack('>II', d, len(c)) + c for d, c in parse_chunks(b))
            fn += '.chunks'
        else:
            data = b
        with open(os.path.join(outdir, fn), 'wb') as o:
            o.write(data)
        print('%3d %-6s %9d -> %9d %s' % (i, kind, size, len(data), fn))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
