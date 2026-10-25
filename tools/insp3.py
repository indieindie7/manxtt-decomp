import struct,sys
d=open('cd/0.AAA','rb').read()
def w(a):
    o=a-0x06010000; return d[o:o+4]
def h(a):
    o=a-0x06010000; return d[o:o+2]
for a in (0x0604204c,0x06042050,0x06042054,0x06042058,0x0604205c,0x06042060): print(hex(a),w(a).hex(),w(a))
print(h(0x06042042).hex(),h(0x06048aae).hex(),h(0x06048962).hex(), h(0x0604a5c2).hex())
for a in (0x06048ac0,0x06048ac4,0x06048ac8,0x06048acc,0x06048970,0x0604896c,0x06048974,0x06048978):print(hex(a),w(a).hex())
for a in (0x06042684,0x06042686,0x06042688): print(hex(a),h(a).hex())
