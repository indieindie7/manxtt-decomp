import struct,re
d=open('cd/0.AAA','rb').read()
a=open('cd/CDIMAGE.ELF','rb').read(16+147*16)
hs={struct.unpack('>I',a[16+i*16:20+i*16])[0]:i for i in range(147)}
def hh(s,w=1):
    h=0
    for c in s.encode():
        c=c-256 if c>127 else c
        h=(h+c+h*w)&0xffffffff
    return h
found={}
for m in re.finditer(rb'[ -~]{3,40}',d):
    s=m.group().decode()
    for cand in {s,s.upper(),s.lower()}:
        for w in (1,):
            if hh(cand,w) in hs: found[hs[hh(cand,w)]]=cand
print(len(found),sorted(found.items()))
