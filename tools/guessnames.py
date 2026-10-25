import re, sys
sys.path.insert(0, 'C:/Users/john/Documents/ManxTT/tools')
import elfarc
B = chr(92)
d = open('C:/Users/john/Documents/ManxTT/cd/0.AAA', 'rb').read()
words = set()
for m in re.finditer(rb'[A-Za-z_0-9]{3,12}', d):
    words.add(m.group().decode().upper())
words |= {'MANXSNDS', 'SNDS', 'MANXMUS', 'ENGINE', 'SFX', 'FONT', 'LOAD', 'LOADING', 'TITLE', 'LOGO', 'SEGA', 'AM3',
          'WARN', 'INTRO', 'OPTION', 'MENU', 'MAIN', 'CRED', 'BIKE', 'MISC', 'BUP', 'MANXTT', 'MANX', 'SOUND', 'MUSIC',
          'SAMPLES', 'SEQ', 'SEQS', 'DSP', 'PROG', 'MANXSEQ', 'MANXSND', 'MANXMIDI', 'MIDI', 'TONE', 'TONES'}
targets = {0x97d63044: 0, 0x97d63075: 1, 0xe94dec14: 6, 0xde193b19: 141, 0xbc331999: 142, 0x3bc31ff9: 143}
pre = 'W:' + B + 'MANXTT' + B
dirs = [pre + 'SRC' + B + 'ART' + B + x + B for x in
        ['COMMON', 'MISC', 'BUP', 'OPTIONS', 'ATTRACT', 'GAME' + B + 'COMMON', 'GAME' + B + '1PLAYER', 'GAME' + B + '2PLAYER',
         'GAME', 'LOADING', 'FONT', 'SYSTEM', 'TITLE', 'SEGA', 'LOGO']]
dirs += [pre + 'SRC' + B + 'SOUND' + B, pre + 'MAKECD' + B + 'PROJECT' + B + 'MOVIES' + B, pre + 'SRC' + B + 'ART' + B]
n = 0
for base in dirs:
    for w in words:
        for e in ('.RBH', '.VRI', '.AVI', '.TSK', '.BIN'):
            n += 1
            s = base + w + e
            h = elfarc.name_hash(s)
            if h in targets:
                print(targets[h], s)
print('tried', n)
