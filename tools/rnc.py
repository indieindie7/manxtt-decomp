# rnc.py: RNC ProPack method 2 unpacker (algorithm as in the game's rnc_Unpack2 0x0600a7e8),
# checked against the unpacked CRC-16 in the header.
# usage: py -3.13 -I rnc.py <in> [<out>]       (no out: just test)
#        py -3.13 -I rnc.py --dir <cd dir> <out dir>   (unpack every RNC file, report;
#        multi-image files become <name>.00, .01, ...)
import sys, os

def crc16(d):
    c = 0
    for b in d:
        c ^= b
        for _ in range(8):
            c = (c >> 1) ^ 0xA001 if c & 1 else c >> 1
    return c

def unpack(data):
    if data[:3] != b'RNC' or data[3] != 2:
        raise ValueError('not RNC method 2')
    size = int.from_bytes(data[4:8], 'big')
    psize = int.from_bytes(data[8:12], 'big')
    ucrc = int.from_bytes(data[12:14], 'big')
    src = data[18:18 + psize]
    st = {'p': 0, 'buf': 0, 'n': 0}
    def byte():
        v = src[st['p']]; st['p'] += 1; return v
    def bit():
        if st['n'] == 0:
            st['buf'] = byte(); st['n'] = 8
        v = (st['buf'] >> 7) & 1
        st['buf'] = (st['buf'] << 1) & 0xff; st['n'] -= 1
        return v
    def bits(k):
        v = 0
        for _ in range(k): v = (v << 1) | bit()
        return v
    def offset():
        o = 0
        if bit():
            o = bit()
            if bit():
                o = ((o << 1) | bit()) | 4
                if not bit(): o = (o << 1) | bit()
            elif o == 0:
                o = bit() + 2
        return ((o << 8) | byte()) + 1
    out = bytearray()
    bits(2)
    while len(out) < size:
        if not bit():
            out.append(byte()); continue
        if not bit():
            ln = 4 + bit()
            if bit():
                ln = ((ln - 1) << 1) + bit()
                if ln == 9:
                    ln = (bits(4) + 3) * 4
                    for _ in range(ln): out.append(byte())
                    continue
            off = offset()
        else:
            if not bit():
                ln = 2; off = byte() + 1
            elif not bit():
                ln = 3; off = offset()
            else:
                ln = byte()
                if ln == 0:
                    if bit(): continue
                    break
                ln += 8; off = offset()
        for _ in range(ln): out.append(out[-off])
    out = bytes(out[:size])
    return out, crc16(out) == ucrc

def chunks(d):
    # files like CREDITS.BIN are several RNC images back to back, sometimes padded (0-3 bytes)
    out, p = [], 0
    while True:
        q = next((p + k for k in range(4) if d[p + k:p + k + 4] == b'RNC'), None)
        if q is None: break
        out.append(q)
        p = q + 18 + int.from_bytes(d[q + 8:q + 12], 'big')
    return out, p

if __name__ == '__main__':
    if sys.argv[1] == '--dir':
        root, od = sys.argv[2], sys.argv[3]
        ok = bad = 0
        for dp, _, fs in os.walk(root):
            for f in fs:
                p = os.path.join(dp, f); d = open(p, 'rb').read()
                if d[:3] != b'RNC': continue
                rel = os.path.relpath(p, root)
                ch, end = chunks(d)
                if end < len(d):
                    t = os.path.join(od, rel + '.tail'); os.makedirs(os.path.dirname(t), exist_ok=True)
                    open(t, 'wb').write(d[end:]); print('TAIL', rel, '@%x' % end, len(d) - end)
                for k, c in enumerate(ch):
                    name = rel if len(ch) == 1 else '%s.%02d' % (rel, k)
                    try:
                        u, good = unpack(d[c:])
                    except Exception as e:
                        print('FAIL', name, e); bad += 1; continue
                    o = os.path.join(od, name); os.makedirs(os.path.dirname(o), exist_ok=True)
                    open(o, 'wb').write(u)
                    print('OK ' if good else 'CRC', name, '@%x' % c, '->', len(u))
                    ok += good; bad += not good
        print('crc ok', ok, 'bad', bad)
    else:
        u, good = unpack(open(sys.argv[1], 'rb').read())
        print(len(u), 'crc ok' if good else 'CRC MISMATCH')
        if len(sys.argv) > 2: open(sys.argv[2], 'wb').write(u)
