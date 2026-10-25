import struct,sys
B=open('C:/Users/john/Documents/ManxTT/cd/0.AAA','rb').read()
BASE=0x06010000
base=int(sys.argv[1],16);stride=int(sys.argv[2],16);n=int(sys.argv[3])
for i in range(n):
    o=base+i*stride-BASE
    w=struct.unpack('>%di'%(stride//4),B[o:o+stride])
    print(i,hex(base+i*stride))
    print('  ',' '.join(f'[{k:02x}]{v/65536:.3f}' if abs(v)>=0x100 or v==0 else f'[{k:02x}]#{v}' for k,v in enumerate(w)))
