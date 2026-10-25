import sys,struct,collections
sys.path.insert(0,'C:/Users/john/Documents/ManxTT/tools')
import elfarc
f=open('C:/Users/john/Documents/ManxTT/cd/CDIMAGE.ELF','rb')
hdr,toc=elfarc.read_toc(f)
comp=0;raw=0;tot=collections.Counter();bytesrc=0
for i,(h,s,sz,c) in enumerate(toc):
    f.seek(s*2048);b=f.read(sz)
    if elfarc.classify(b)!='CHUNKS': continue
    p=0
    while True:
        d,w=struct.unpack_from('>II',b,p)
        if d==0: break
        p+=8;cm=bool(w&0x80000000);n=w&0x7fffffff
        if cm: comp+=1;tot['c']+=n;p+=n+((4-(n&3))&3)
        else: raw+=1;tot['r']+=n;p+=n
    if p+8>sz or sz-(p+8)>=2048: print('entry',i,'ends',p+8,'of',sz)
print(comp,raw,tot)
# entry 4 raw as chunk list?
f.seek(toc[4][1]*2048);b=f.read(toc[4][2]);print(struct.unpack_from('>IIII',b,0),b[16:32].hex(),b[-16:].hex())
