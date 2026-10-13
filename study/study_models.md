# Manx TT Super Bike (Saturn): bike / rider mesh, pose animation, texture formats

Status 2026-10-13. Program SH-2 BE, base 0x06010000 (file offset = addr - 0x06010000 in cd/0.AAA).
Exporter: tools/rbh2obj.py. Items marked [guess] are unverified. Local use only.

## 1. Container (RBH)
- 'BIFF', u32 size, 'RBHF', then chunks. RBHH = 12-byte block table. BODY chunks = raw blocks in table order.
  RELC chunks = fixups: u32 srcblock, u32 dstblock, u32 offsets...; at each offset the dst block base is added.
  The exporter keeps pointers block-relative; the target block comes from the RELC pair. Loader: res_LoadChunkedFile 0x06041e1c.
- Model RBHs (PRIDERS, EBIKES) have 4 blocks: 0 root table, 1 object headers + command lists (self relocs 1->1),
  2 vertices, 3 per-object cells (u32; 0 = no texture transfer). Pointer fields = 1->2 relocs (obj+4), 1->3 relocs (obj+0xC).
- RIDER_M.RBH (080) has a single block, RELC 0->0 (section 5).
- Path strings (W:\MANXTT\SRC\ART\GAME\COMMON\PRIDERS.RBH etc.) sit at 0x06027072-0x06027146; livery paths at 0x06026aaa+, 0x06026eba+.
  The code xref that loads them was NOT traced.

## 2. Mesh format (verified on PRIDERS, EBIKES, BHONDA1; all face indices valid)
Object header, 0x20 bytes, in block 1 (read by obj_QueueDrawGroup 0x06045ae0):
- +0x00 ptr command list (block 1); +0x04 ptr vertices (block 2); +0x08 self/link ptr; +0x0C ptr cell (block 3)
- +0x10 s16 vertex count (obj_QueueDrawGroup writes 0xC bytes per vertex); +0x14 s32 16.16 (e.g. 0xb0000) [guess: size];
  +0x18 16.16 bounding radius (cull_CircleVsRect); +0x1C s16,s16 unknown.

Vertex: 3 x s32 = 12 bytes, plain integers. Game y is down (up = -y). A bike spans about 70 long, 22 wide, 40 tall.
Unit scale unknown; exporter default 1/32 [guess, about 3 cm per unit].

Command list: records of 4 u16 {nfaces, word1, unknown, size_in_u16}; payload starts 8 bytes after the record start:
a 4-byte prefix then nfaces * stride. nfaces = 0 ends the list. Verified: 4 + stride*nfaces == size*2 for every record.
- type = word1 & 0x3fff: 0 flat stride 12, 1 textured stride 16, 0x200 flat double-sided, 0x201 textured double-sided.
  Types 8 (stride 16) and 9 (stride 20) exist in model_ExecuteCommandList 0x0602c8a0 but were not seen in the data.
- mode = word1 >> 14 (0,1,2) selects a render variant via a jump table [guess: transparent/shadow].
- Dispatch (model_ExecuteCommandList): 0 -> poly_CullFacesStride12 0x06056734; 1 -> model_DrawFacesCullC 0x060144a4;
  8 -> poly_CullFacesStride16 0x06056914; 9 -> poly_CullFacesStride20 0x06056d30; 0x200/0x201/0x208/0x209 ->
  poly_DispatchByMode_1/3/2/4 (re-dispatch at payload+0xC, no backface cull). model_DrawFacesCullA/B/C = 0x0601409c / 0x060142a0 / 0x060144a4.

Face record: 4 u16 vertex byte offsets (index*12); a triangle repeats its last index; then VDP1 fields:
- flat (12 B): {pmod, colr}; textured (16 B): {srcA, size, pmod, colr}.
- Backface test: visible if (p2y-p0y)*(p1x-p0x) < (p1y-p0y)*(p2x-p0x) in screen coords (y down).

## 3. Texture format (VDP1)
- srcA = CMDSRCA: texture VRAM address = srcA*8. size = CMDSIZE: (W/8)<<8 | H. pmod = CMDPMOD; colour mode = (pmod>>3)&7.
  pmod 0x14e8: mode 5 (RGB555, bit 15 set in colr). 0x1488 / 0x14c8: mode 1 = 16-colour LUT, colr*8 = CLUT address (16 RGB555 words).
  Pixels 4bpp, high nibble first, row-major, W*H/2 bytes. Colour 0 transparent. Corner order A TL, B TR, C BR, D BL [guess].
- VRI.chunks = repeat {u32 dest, u32 size, data}. dest 0x25C0xxxx = VDP1 VRAM, 0x25F0xxxx = colour RAM.
  COMMON.VRI (073) loads at VRAM 0x51000 (size 0x29760): rider textures and CLUTs, e.g. srcA 0xc4bc -> 0x625e0, colr 0xc308 -> 0x61840.
  COMSHEEP.VRI also loads at 0x51000. Livery VRIs (R_SUZ, BHONDA1...) load at 0x7b000 (size ~0x2980-0x31a0):
  CLUT 0xf600 -> 0x7b000, textures from 0xf62c up.
- Livery RBHs (~2.6 KB) hold 3 small sticker/decal objects (e.g. a 4-vertex quad, 16x8). They are NOT the full bike.
  Where the player's full bike body lives is unresolved [guess: MISC or COMMON].

## 4. Parts
- EBIKES (081): block 0 has 21 object pointers = 7 groups of 3: high-LOD bike (54-65 verts), 32-vertex low LOD, and a 4-vertex card
  (z=26, type 0x201) [guess: shadow/billboard]. The preview shows a bike silhouette.
- PRIDERS (079): block 0 has 36 row pointers; each row = 11 object pointers (table at the start of block 1: 36*11 entries, 0x630 bytes;
  the first command list follows). Each row is one rider pose variant, 11 parts in local space around the origin; 203 vertices total [row meaning: guess, lean angle].
  bike_DrawRiderModel 0x0602aef8 picks the variant by a lean-angle threshold chain (bike record field +0x14, stride 0x40); mapping not finished.
- bike_DrawBikeWithShadow 0x0602b1ac / bike_DrawModelParts 0x0602b524: shadow = object list element at +0x14; per-player array indexed by LOD
  (param_4) = bike body; another array holds two wheels (offsets +0 and +8), each rotated by RotX of a per-player spin value [guess: TYRES].
  Bike transform: Push, Translate(rec x,y,z), RotY(-yaw), RotX(pitch), RotZ(roll) from the 0x40-byte per-player record at PTR_DAT_0602b4c4
  (+0xC pitch, +0x10 yaw, +0x14 roll). Rider drawn by rider_UpdateAnimPathDraw.

## 5. Rider skeleton and pose animation
Pose = 33 s16 angles (11 parts x 3). anim_InterpolatePoseMatricesA 0x06029ac8 (uses obj_QueueDrawGroup) / B 0x06029eb4
(uses vdp1_QueueTextureTransfer) lerp two poses with math_FixedLerpAngle and draw the 11 parts. Per part: RotZ(a[3k+2]), RotY(a[3k+1]), RotX(a[3k]);
elbows/knees use RotZ only. Translations are 16.16, bones along local +X. Constants read from cd/0.AAA near 0x06029cfa-0x06029d48 and 0x06029e82-0x06029eb0.
- part0 root T(0,2.16,0); part1 child of 0 T(5.63,-0.21,-6.08); part2 child of 1 X+16.58, RotZ a[8];
  part3 child of 0 T(5.60,-0.21,6.09); part4 child of 3 X+16.63, RotZ a[0xe];
  part5 second root T(0,2.18,0); part6 child of 5 T(14.60,0.18,7.38); part7 child of 6 X+11.32, RotZ a[23];
  part8 child of 5 T(16.20,0.018,0.016), single piece [guess: head]; part9 child of 5 T(14.66,0.21,-7.37); part10 child of 9 X+11.42, RotZ a[32].
  Part names (legs / torso / arms) are [guess].
- Animation = {s16 nkeys, s16 pad, keys at +4, 16 bytes each: {u32 ptr to 33-short pose, s32 x, s32 y, s32 z}}.
  Time is a 16.16 key index: integer part = key k, fraction lerps key k and k+1. Translation = lerp(xyz)*4.
- Player: rider_UpdateAnimPathDraw 0x0603c4a4, rider_SetAnimPathDraw 0x0603c7d8 (called from the bike select screen).
  State table at PTR_DAT_0603c624 + player*0x18: +0 lock byte, +4 state (0..5), +8 previous state, +0x10 anim index, +0x14 16.16 time.
  States: 0 reset to anim 2; 1 anim 1, time from racer field +8; 2 idle, time bounces; 3 anim 3 forward until the end, triggered when a global byte == 0x13
  (race finished) [guess: finish animation, not crash]; 5 anim 4; -1 modulo loop. param_2 = array of 5 animation pointers.
  Matrix: Push, car_GetPositionVec, RotX(car_GetRacerFieldB + ...), Y translate from car_GetRacerFieldClamped*const, RotY(const).
  Racer inputs seen: field B (pitch), clamped field (height), racer +8. Mapping of lean, speed, gear, wheelie and crash (rec+0x2E)
  to specific RIDER_M clips was NOT traced.
- RIDER_M.RBH (080, 8172 B, one block of 7364 B): top table of 77 pointers; entries at 0x130 (nkeys 1, pose at 0x144), 0x188 (nkeys 15),
  0x688, 0x840, 0xd94, 0xdec... (strides 0x58 and 0x14), then 0x184c... (stride 0x58). Clip-to-state mapping unknown.

## 6. Exporter
`py -3.13 -I tools/rbh2obj.py <file.RBH> <outdir> [--vri A.VRI.chunks ...] [--scale S] [--preview]`
One OBJ per root (parts as OBJ groups), MTL, PNG per distinct texture (use --vri COMMON for rider, livery VRI for decals).
Output is x, -y, z times scale, winding reversed. Not done: posed rider assembly with the skeleton above; ERIDERS/TYRES untested.

## Resolved (models pass, 10-13): who loads what
hud_LoadCommonArt 0x06027398 (mode 1, 1-player branch) loads into a resource struct (offsets are literal shorts at 0x06027586..0x060275a4):
- 0xf0 = livery RBH (from table 0x0606e71c, 12 x 16 bytes {VRI path, RBH path, block, offset}; all block 0 / offset 0;
  second set *2 at 0x0606e7dc); 0x12c (+player*4) = livery block 0 base = the per-player BIKE BODY LOD list.
- 0x110 COMMON.RBH, 0x134 = COMMON block0 +4. 0x108 EBIKES, 0x11c its root. 0xf8 TYRES, 0x124 its root (wheels).
- 0x10c MISC, 0x128 its root (shadow = root[5], read at +0x14). 0x100 PRIDERS, 0x118 its root. 0xfc ERIDERS, 0x120 its root.
- 0x104 RIDER_M, 0x114 its root (animation set).
bike_DrawModelParts 0x0602b524: body = *(*(s+0x12c+player*4) + LOD*4); wheels = TYRES root[LOD] (+0, +8), each RotX by a
per-player spin at 0x0606f048 + player*4; the rider = rider_UpdateAnimPathDraw(RIDER_M root, PRIDERS root[row]),
row = bikeSel*2 + LOD when *0x06088398 == 3, else bikeSel + 0x18 with LOD forced 0. Bike select byte: 0x06088f24 (player 1)
/ 0x06088f18 (param_6 != 0). So PRIDERS rows are per-livery rider skins, NOT lean steps.
- BIKE BODY CONFIRMED: livery RBH root = 3 objects {57-vertex body, 32-vertex low LOD, 4-vertex far card}, the same layout as EBIKES.
  The earlier "decals only" line was wrong. The textured render (tools/objview.py) shows the full Honda; texture corner order A TL, B TR, C BR, D BL looks right.
- Bike draw frame: body is drawn after Translate(0,-3,0) and Scale 0x4000 (0.25) on top of the bike matrix. Wheels (in the same scaled frame):
  front = TYRES root[LOD] at T(0, 0xcccc=0.8, 0x386664=56.4), rear = root[LOD+2] at the origin; 56.4 x 0.25 = the 14.1 wheelbase.
  TYRES objects 0/1 = 12 v, 2/3 = 18 v, 4/5 = 99/101 v (4/5 not used by bike_DrawModelParts [guess: bike select close-up]).
- Angles: 12-bit (mtx_RotX 0x06059404 masks & 0xfff into the sin/cos table 0x0604e518, {sin,cos} 16.16). Matrix: column 0 = local X
  (mtx_TranslateLocalX 0x0605925c adds p*m[0],m[3],m[6]); translation m[9..11].
- RIDER_M block 0 = root table: clip0 0x130 (1 key), clip1 0x188 (15 keys), clip2 0x688, clip3 0x840, clip4 0xd94 (next entries 0xdec.. = other data).
  rider_UpdateAnimPathDraw (state rec 0x0606f12c + player*0x18, +0x10 clip, +0x14 16.16 time); bike_DrawModelParts requests state 1, passes
  param_8 = bike rec (0x0606ee48+p*0x40) +0x24 [guess: speed] and param_5 = rec+0xc (pitch, yaw, roll).
  State 1 = clip 1 LEAN: time = (roll<<16)*0x1948b0fd>>35 + 7.0 (key 7 = upright, 15 keys) while param_8 > 0x4ccb.
  Else state 2 = clip 2 STOPPED (idle; time 4.0, steps +-0.7841 bounce); when param_8 > 0x4ccc again it plays back to 0 then returns to state 1 at key 7.
  Race finished (byte 0x13 at the race-state global, own player) -> state 3 = clip 3 forward once (step 0x6666/tick), holds last key.
  State 5 (set by other callers) = clip 4 from 0. State 0 = reset to clip 2 at 4.0. State -1 = clip loops on a global timer.
  Rider root: Push, RotX(racer field B + ...), T(0, clamped field*0x6664 - 22.0, 0), RotY(0xf800 = -180 deg), T(lerp key xyz *4); then the 11-part pose.
- POSED RIDER VERIFIED (tools/riderpose.py, rotation matrices standard right-hand in game space, M = parent*T*Rz*Ry*Rx): PRIDERS row 6
  (blue leathers = BHONDA1, bikeSel 3) with clip 1 key 7 sits on the BHONDA1 body with hands on the bars; keys 0 / 14 hang off opposite sides.
