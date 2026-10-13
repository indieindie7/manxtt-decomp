# Manx TT Super Bike (Sega Saturn) reverse-engineering notes and symbols

Hand-named function map, notes and tools for the Sega Saturn port of **Manx TT Super Bike**
(Sega AM3 / Sega, 1997; Europe release MK-81210). Every function of the main SH-2 program is named.

Same method as [sonicr-decomp](https://github.com/indieindie7/sonicr-decomp) and
[cyberspeedway-decomp](https://github.com/indieindie7/cyberspeedway-decomp). Non-commercial, done for
study and preservation.

## What is here

| Path | Content |
|---|---|
| `ghidra/hand_0.txt` | 1204 named functions of `0.AAA` (`0x<addr> func <name> hand <comment>`); 20 marked `provisional` are weak |
| `ghidra/funcinfo_0.tsv` | per-function export: `F` address name source size, `C` callee lines (string lines removed) |
| `ghidra/scripts/` | `FindSh2FunctionsMem.java` (SH-2 prologue scan), `DumpLong.java`, the round-1 naming prompt |
| `ghidra/naming/` | the round-2 review prompt and the list of names it reviewed |
| `ghidra/mxrun.sh` | headless Ghidra runner used here (edit the paths for your machine) |
| `tools/` | `srptrs.py` (code-pointer discovery), `slice.py` (split the decompile for naming), `provctx.py` (caller context for the review round), `srprovapply.py` (apply verdicts by address), `rnc.py` |
| `NOTES.md` | project log: disc layout, import, discovery, naming rounds, counts |

`ApplyNames.java`, `ExportFuncInfo.java`, `CreateAt.java` and `CsDumpAll.java` are in
[amok-decomp](https://github.com/indieindie7/amok-decomp)'s `ghidra/scripts`.

## What is NOT here

No game files: no disc image, no program binary, no CDIMAGE.ELF data, no game strings, no decompiled C
output and no Ghidra project database (which embeds the binary). You need your own copy of the game.

## Reproducing

1. Extract `0.AAA` from your disc (an ISO9660 reader on the data track).
2. Ghidra 12.1.4: import it as `SuperH:BE:32:SH-2` with the BinaryLoader at base `0x06010000`,
   `-postScript FindSh2FunctionsMem.java`.
3. `ApplyNames.java ghidra/hand_0.txt hand` creates any missing functions and applies all names.
4. `CsDumpAll.java <out.c>` writes the whole decompile.

The largest groups: `cdc_` / `gfs_` / `GFS_` (CD block and the Sega file system library), `movie_`
(FMV playback), `snd_`, `softfp_` (GCC soft-float), `car_` / `bike_` (rider physics and handling),
`bup_` (backup RAM saves), `hud_`, `vdp2_`.

## License

The notes, names and scripts are MIT (see `LICENSE`). Manx TT Super Bike and Sega Saturn are trademarks
of Sega; this project has no affiliation with Sega and contains none of its code or data.
