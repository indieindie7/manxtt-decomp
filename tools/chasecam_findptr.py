import sys,bisect
B=open('C:/Users/john/Documents/ManxTT/cd/0.AAA','rb').read()
BASE=0x06010000
fs=[]
for l in open('C:/Users/john/Documents/ManxTT/ghidra/funcinfo_0.tsv'):
    p=l.split()
    if p and p[0]=='F': fs.append((int(p[1],16),p[2]))
fs.sort()
def fn(a):
    i=bisect.bisect_right([x[0] for x in fs],a)-1
    return f"{fs[i][1]}@{fs[i][0]:08x}"
for t in sys.argv[1:]:
    v=int(t,16).to_bytes(4,'big');o=0;res=[]
    while True:
        o=B.find(v,o)
        if o<0:break
        if o%4==0 or True: res.append(fn(BASE+o)+f"(lit {BASE+o:08x})")
        o+=1
    print(t,len(res),sorted(set(res))[:40])
