import struct,sys
f=open(sys.argv[1],'rb');d=f.read(0x10000)
h=struct.unpack('>4I',d[:16]);print([hex(x) for x in h])
n=h[0]
for i in range(12):
    print(i,[hex(x) for x in struct.unpack('>4I',d[16+i*16:32+i*16])])
