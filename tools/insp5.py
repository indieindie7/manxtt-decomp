import re
d=open('cd/0.AAA','rb').read()
for m in re.finditer(rb'[ -~]{3,80}',d):
    s=m.group().decode()
    if 'MANXTT' in s.upper() or chr(92) in s or '.RBH' in s.upper() or '.VRI' in s.upper(): print(hex(0x06010000+m.start()),s)
