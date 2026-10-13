# Manx TT Super Bike (Sega Saturn, AM3 / Sega 1997) decompile notes
Research only, non-commercial. Never publish game files, bins, decompiles or the Ghidra db. No leaked source.
User 10-13: "can you now do manx tt for the saturn please". Same pipeline as Documents/SonicR (NOTES.md there).

## Setup (10-13)
- Source: your own disc image (Saturn zip, Europe, 18 tracks; Track 01 data 91944384 bytes). image/track01.bin + manxtt.cue.
- cd/ via Scorcher tools/isoextract.py <bin> cd 2352: 5 files. 0.AAA 497924 bytes (main program?), CDIMAGE.ELF 79204352
  bytes (NOT an ELF: a data archive, header 00000093 00000001 00000002 ...), SMP_ABS/BIB/CPY.TXT.
- IP.BIN: MK-81210 V1.000 1997-02-17, "MANX TT SUPER BIKE", area E.
- IP first read 0x06010000, size field 0x1000. 0.AAA starts with SH-2 code (df12 d113 ...) = main program at 0x06010000.
- Import: ghidra/mxrun.sh (forward-slash paths!) -import cd/0.AAA -processor SuperH:BE:32:SH-2 -loader BinaryLoader -loader-baseAddr 0x06010000 -postScript FindSh2FunctionsMem.java -> 978 fn. tools/srptrs.py (3rd arg base 06010000) pointer targets starting 2fx6/4f22/7ffx -> ghidra/ptrcode.txt 196, CreateAt (with analysis) -> 1204 fn.
- ExportFuncInfo -> ghidra/funcinfo_0.tsv (1204 fn, 5765 calls, 739 string refs). CsDumpAll -> ghidra/decomp_0.c (62761 lines; 1 pcode error at 06015216).
- tools/slice.py -> ghidra/naming/s1..s8.c (~7.8k lines each). Round 1 prompt ghidra/scripts/n1_prompt_mx.txt (from SonicR n1_prompt.txt), 8 Sonnet agents -> naming/h1..h8.txt.
- Round 1 DONE (10-13): naming/h1..h8 (78/112/84/166/169/155/262/178) -> ghidra/hand_0.txt 1204 lines, 373 provisional; 4 dup names got _2 (0x06040fe8 rect_Set, 0x06063018 gfs_PlanReadChunk, 0x06067c1c movie_OpenFile, 0x0606af3c strcmp). ApplyNames 1204 named; funcinfo re-exported (0 FUN_); decomp_0.c re-dumped (66610 lines). Backup naming/hand_0_r1.bak.
- Round 2 (10-13): tools/provctx.py patched (base '0' = 0x06010000, image .AAA); naming/prov_list.txt = provisional + _N names (398) -> naming/r2_1..8.txt; prompt naming/prompt_r2.txt; 8 Sonnet agents -> naming/v2_1..8.txt; apply with tools/srprovapply.py ghidra/hand_0.txt naming/v2_*.txt.
- Round 2 DONE (10-13): v2_1..8 (398 verdicts): confirmed 232, renamed 121, unsure 20 -> hand_0.txt 1204 lines, 20 provisional, no dups. ApplyNames 1204, Ghidra == hand file (0 diffs), 0 FUN_. Top prefixes: cdc 114, gfs 99, movie 66, snd 52, stub 41, softfp 40, car 37, GFS 35, math 31, bup 30, bike 29, hud 26.

## Log after publishing (10-13)
- Studies: handling, AI + ghost, chase camera, archive, models (study/*.md); each has "Resolved" sections from the trim, drill, models and guess-dig passes.
- Models: player bike = livery RBH (3 LOD), wheels from TYRES, PRIDERS per-livery rider skins + RIDER_M clips, ERIDERS rigid lean-step riders; tools rbh2obj.py, riderpose.py, objview.py.
- Guess dig: disc PAL, AI pace handicap, unreachable camera states and rider clips, unused decompressors.
- HANDOFF-scorcher.md: summary handed to the Scorcher modding project.
- Manx TT DONE.
