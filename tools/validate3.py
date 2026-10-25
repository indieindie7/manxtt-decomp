import sys,collections
sys.path.insert(0,'C:/Users/john/Documents/ManxTT/tools')
import elfarc
f=open('C:/Users/john/Documents/ManxTT/cd/CDIMAGE.ELF','rb')
h,toc=elfarc.read_toc(f)
names=elfarc.find_names('C:/Users/john/Documents/ManxTT/cd/0.AAA',{t[0] for t in toc},1)
cat=collections.Counter();by=collections.Counter()
for i,(hh,s,sz,c) in enumerate(toc):
    f.seek(s*2048);b=f.read(sz);k=elfarc.classify(b);nm=names.get(hh,'')
    ext=nm.rsplit('.',1)[-1] if '.' in nm else '?'
    cat[(k,ext)]+=1;by[(k,ext)]+=sz
for k in sorted(cat): print(k,cat[k],by[k])
for i in (0,5,6,8):
    f.seek(toc[i][1]*2048);b=f.read(toc[i][2]);t,ch=elfarc.parse_biff(b)
    print(i,[(hex(a),c,d,e) for a,c,d,e in t][:8],[(x,len(d)) for x,d,_ in ch][:10])
f.seek(toc[1][1]*2048);b=f.read(toc[1][2]);print([(hex(d),len(c)) for d,c in elfarc.parse_chunks(b)])
f.seek(toc[7][1]*2048);b=f.read(toc[7][2]);print([(hex(d),len(c)) for d,c in elfarc.parse_chunks(b)])
