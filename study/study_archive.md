# CDIMAGE.ELF archive format (Manx TT Super Bike, Saturn) - study 10-13

Sources: ghidra/study/archive.c, decomp_0.c, funcinfo_0.tsv, strings in cd/0.AAA (load base 0x06010000), and byte inspection of cd/CDIMAGE.ELF (79204352 bytes = 38674 sectors). Tool: tools/elfarc.py (`list`, `extract`). Checks: tools/validate_elfarc.py, validate2.py, validate3.py. Items marked [guess] are not proven by code.

## 1. Header and TOC (cd_LoadElfToc 0x06047fa8)
All values big endian. The file is not an ELF; the name is only a label.
- Header, 16 bytes: u32 NumFiles (=147), u32 HashWeight (=1), u32 unused (=2, never read by the loader), u32 VolumeID (=0, printed only).
- TOC at file offset 0x10: NumFiles*16 bytes (malloc NumFiles<<4, read once, kept in RAM).
- TOC entry, 16 bytes: u32 hash, u32 start_sector, u32 size_bytes, u32 sector_count. Sectors are 2048 bytes. File offset = start_sector*0x800. Verified for all 147 entries: sector_count = ceil(size/2048).

## 2. Sector alignment
Entries are contiguous and sector aligned with no gaps. Data starts at sector 17. The last entry ends at sector 38610; the file is 38674 sectors, so 64 trailing sectors are not in the TOC [guess: padding].

## 3. How the game finds an entry
By name hash, never by index.
- cd_OpenFileByName 0x06048148 hashes the path: h = 0; for each signed char c: h = h + c + h*HashWeight (32 bit; weight 1 gives 2h+c, so only the last ~32 characters affect the result). It then scans the TOC linearly for entry.hash == h, GFS_Seek(start_sector), and reads sector_count sectors with GFS_NwCdReadSimple. Not found prints "was not found in the TOC".
- Mode 1 (PC file) reads the same path from the development PC through the SN debugger (bios Vbr call 8c).
- stream_HandleMsg 0x0604a4c4 (movie streamer "TLSTREAM", ring buffer): finds the entry by name hash, or, when bit 16 of its flag argument is set, takes an explicit {hash, sector, count} triple. stream_SeekCd 0x0604a2c8 seeks inside the entry.
- file_Read 0x060485c8 reads whole sectors straight to the destination plus a bounce sector for the tail.
- Names are build paths such as W:\MANXTT\SRC\ART\GAME\1PLAYER\L1UNIQUE.RBH stored as plain strings in 0.AAA. elfarc.py hashes those strings and recovers 141 of 147 names.

## 4. Entry formats (all 147 classified)
### 4a. BIFF container, 75 entries (73 named *.RBH + 2 unnamed: 0, 6). Loader res_LoadChunkedFile 0x06041e1c
'BIFF', u32 size (file length = size+8), 'RBHF', then chunks {char tag[4], u32 size, data}:
- RBHH: table of 12-byte records {u32 ptr, u32 size, u16, u16}. ptr==0 means the loader allocates the block; ptr!=0 loads at that absolute address (entry 5 MANXSNDS uses 0x25A1xxxx = sound RAM [guess: sample/sequence banks]).
- BODY: raw bytes for the next block.
- PACK: LZ-compressed blocks (see section 6). None present in this archive.
- RELC: fixups: two block indices, then u32 offsets; the base of the second block is added at each offset in the first (pointer relocation).
Verified for all 75: sum of table sizes equals sum of BODY sizes.

### 4b. VDP chunk list, 65 entries (64 named *.VRI + 1 unnamed: 1). Loader res_UnpackChunkListFile 0x0604898c (memory form res_UnpackChunkListMem 0x060488c0, no callers)
Repeat {u32 dest, u32 size (bit 31 = compressed), data}; dest==0 ends the list. Compressed form: u32 unpacked length + LZ stream, padded to 4. 108 chunks in total, none compressed. dest ranges: 0x25C0xxxx VDP1 VRAM, 0x25E0xxxx VDP2 VRAM, 0x25F0xxxx VDP2 colour RAM (the loader writes this range into a RAM shadow and sets flag |= 4 instead of the hardware address). All 65 lists parse exactly to the end of the entry.

### 4c. Raw, 1 entry: entry 4 SDDRVS.TSK (25488 bytes)
Sega sound driver (starts 0000a000 00001000, ends "SEGA"), loaded by sound_LoadDriverAndInit 0x0604a0e8.

### 4d. Movies, 6 entries (141-146): RIFF AVI with the DUCK (TrueMotion) video codec
Streamed from disc by the TLSTREAM layer, not loaded whole. Names: 144 HONDA25.AVI, 145 SUZUKI25.AVI, 146 CAMA.AVI; 141-143 unnamed. They hold most of the 79 MB.

## 5. Entry counts by guessed type
| kind | count |
|---|---|
| BIFF / RBH (models, sound banks, HUD text, tables with fixups) | 73 named + 2 unnamed = 75 |
| VDP chunk list / VRI (textures, backgrounds, palettes) | 64 named + 1 unnamed = 65 |
| TSK sound driver | 1 |
| AVI movies | 6 |
| total | 147 |
Content groups by index (names from the path strings): 0-1 unnamed small pair; 2-3 BUP (backup screen); 4-6 sound (SDDRVS.TSK, MANXSNDS.RBH, unnamed sibling bank with 8 table entries [guess]); 7-22 course data, 8 pairs of VRI+RBH named L1UNIQUE, L1RMUNI, T1UNIQUE, T1RMUNI, L2UNIQUE, L2RMUNI, T2UNIQUE, T2RMUNI [guess: L=Laxey course, T=TT course, RM = reverse/mirror, 1/2 = player count]; 23-24 OPTIONS; 25-101 bike, tyre, sheep, rider and HUD art; 102-108 attract and title; 109-140 misc, credits, logos; 141-146 movies.

## 6. Compression (code present, unused on this archive)
- stream_DecodeLz 0x06042568 and lz_DecodeVarintBackref 0x060487b4: token = varint (bit 7 continue, bit 6 sign on the first byte, 6 low bits, then 7-bit groups at shift 6, 13, ...). Token > 0: copy that many literal bytes. Token < 0: copy -token bytes from an absolute output offset given by the next varint. Shift direction and sign handling are implemented in elfarc.py lz_decode() but untested on real data since no compressed block exists.
- BIFF PACK stream: repeat {u16 outlen (0 ends), u16 inlen, inlen bytes}.
- rle_Decode 0x06042114 and lz_Decompress 0x06042208 (bit-stream LZ) have no callers in the decompile [guess: unused leftovers].

## 7. Unnamed entries
0 (BIFF), 1 (chunk list), 6 (BIFF, sound sibling), 141, 142, 143 (movies). Entry 143 might be W:\MANXTT\MAKECD\PROJECT\MOVIES\BEAC.AVI [weak guess, 32-bit hash, not added to the tool].

## 8. Which code reads which kinds
| code | address | reads |
|---|---|---|
| cd_LoadElfToc | 0x06047fa8 | header + TOC |
| cd_OpenFileByName | 0x06048148 | lookup by hash and CD read, used by all loaders below |
| res_LoadChunkedFile | 0x06041e1c | BIFF *.RBH (game-screen task handlers: title, options, bup, congrats, gamestart, hud art, loading screen, logo, attract movie handler, sound streamer for MANXSNDS) |
| res_UnpackChunkListFile | 0x0604898c | VRI chunk lists (same task handlers) |
| sound_LoadDriverAndInit | 0x0604a0e8 | SDDRVS.TSK |
| stream_HandleMsg, stream_SeekCd | 0x0604a4c4, 0x0604a2c8 | AVI movies (ring buffer) |
| movie_OpenFile | 0x0603eb68 | DUCK AVI open ("DUCK ERROR: Could not open %s") |
Loads are by constant path strings; no code was found that indexes the TOC by number.

## 9. Extraction
`py -3.13 -I tools/elfarc.py extract cd/CDIMAGE.ELF extracted/` wrote all 147 entries (76 MB) without error. BIFF written as BIFF (any PACK turned into BODY), VRI as `.chunks` ([u32 dest][u32 len][data] records), AVI and TSK raw.
