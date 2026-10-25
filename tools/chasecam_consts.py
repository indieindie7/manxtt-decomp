import re,struct,sys
B=open('C:/Users/john/Documents/ManxTT/cd/0.AAA','rb').read()
BASE=0x06010000
def rd(a,n):
    o=a-BASE
    return B[o:o+n] if 0<=o<len(B)-n else None
def s16(a):
    d=rd(a,2); return struct.unpack('>h',d)[0] if d else None
def s32(a):
    d=rd(a,4); return struct.unpack('>i',d)[0] if d else None
def f16(v): return v/65536.0
src=open('C:/Users/john/Documents/ManxTT/ghidra/decomp_0.c').read().split('\n')
a,b=int(sys.argv[1]),int(sys.argv[2])
seen={}
for l in src[a-1:b]:
    for m in re.finditer(r'\b(PTR_DAT|DAT)_([0-9a-f]{8})\b',l):
        seen[m.group(0)]=(m.group(1),int(m.group(2),16))
for k,(t,ad) in sorted(seen.items(),key=lambda x:x[1][1]):
    if t=='DAT':
        v16=s16(ad);v32=s32(ad)
        print(f"{k}: s16={v16} ({v16:#x}) s32={v32} ({v32 & 0xffffffff:#010x}) fx16.16={f16(v32):.4f}")
    else:
        p=s32(ad)&0xffffffff
        extra=''
        v=s32(p) if p else None
        v8=rd(p,8)
        extra=f" -> mem32={v if v is None else hex(v&0xffffffff)}" if v is not None else ''
        if v8 and len(v8)==8: extra+=f" dbl={struct.unpack('>d',v8)[0]}"
        print(f"{k}: ptr={p:#010x}{extra}")
