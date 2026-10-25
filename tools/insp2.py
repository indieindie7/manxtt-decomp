import struct,sys,collections
d=open(sys.argv[1],'rb').read()
n=struct.unpack('>I',d[:4])[0]
E=[struct.unpack('>4I',d[16+i*16:32+i*16]) for i in range(n)]
print(len(d),len(d)/2048)
prev=0
for i,(h,s,sz,x) in enumerate(E):
    exp=(sz+2047)//2048
    off=s*2048
    magic=d[off:off+8].hex() if off<len(d) else 'OOR'
    if i<40 or i>n-10 or x!=exp: print(i,hex(h),s,sz,x,exp,'gap',s-prev,magic)
    prev=s+x
print('end',prev,len(d)//2048)
print(set(e[3]-(e[2]+2047)//2048 for e in E))
