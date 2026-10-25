import sys,struct,collections
sys.path.insert(0,'C:/Users/john/Documents/ManxTT/tools')
import elfarc
f=open('C:/Users/john/Documents/ManxTT/cd/CDIMAGE.ELF','rb')
hdr,toc=elfarc.read_toc(f)
bad=0;tags=collections.Counter();stats=[]
for i,(h,s,sz,c) in enumerate(toc):
    f.seek(s*2048);b=f.read(sz)
    k=elfarc.classify(b)
    if k=='BIFF':
        try:
            table,ch=elfarc.parse_biff(b)
        except Exception as e:
            print(i,'BIFF ERR',e);bad+=1;continue
        for t,d,p in ch: tags[(t,p)]+=1
        tsz=sum(t[1] for t in table); body=sum(len(d) for t,d,p in ch if t==b'BODY')
        # per-entry: BODY chunks in order vs table entries
        stats.append((i,len(table),tsz,body,[t for t,_,_ in ch]))
    elif k=='CHUNKS':
        cs=elfarc.parse_chunks(b)
        for d,_ in cs: tags[('dest',d>>16)]+=1
print(bad,tags)
for s in stats[:12]: print(s[:4],s[4][:8])
print(sum(1 for s in stats if s[2]!=s[3]),'biff with table-size!=body-size of',len(stats))
