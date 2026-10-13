# Manx TT Super Bike: in-race chase camera (program 0.AAA, base 0x06010000)

Supersedes the "chase camera NOT FOUND" line in study_ai_camera.md. Guesses are marked GUESS.

## 1. Who drives the camera
The camera is a per-player "car_*" record (0x188 bytes each, DAT_0602d2b4 = 392, base RAM 0x06078d64), not a tlCamera message handler.
- Init: task_MainGameLoopCreate@06037c04 -> table_CallOnEntry@0602d08c -> car_InitState@0602d0c4.
- Per frame: pad_UpdatePlayerSlot0@06029aa0 / Slot1@06029ab4 -> table_CallOnEntry_2@0602d29c -> car_UpdateByState@0602d2c8 (size 2106). This is the camera driver.
- View matrix: matrix_ApplyInverseCarTransform@0602def8 = RotZ(-roll[11]), RotX(-pitch[9]), RotY(yaw[10]), Translate(-pos).
- Helpers: car_SnapToStartPosition@0602dc8c, car_ApplyTransformFromState@0602dd8c, car_ApplyInitParams@0602ddf4 (loads a view preset), vec_BuildRotatedVector@0602d008 (look-at angles via Atan2).
- Draw: title_DrawLayersB@06023e00 / C@06023e84 call course_DrawRoadAheadPlayer@06038b8c, which copies the 12-word view matrix.
- NOT cameras: view_UpdateCameraPathDraw@0603c4a4 and view_SetCameraPathDraw@0603c7d8 are rider pose animation.
- tlCamera (camera_TaskHandler@0604d1d0) is only the viewport and perspective table. Made in gamestart_TaskMain@060252a4 (task +0x58 P1, +0x5c P2). Only it calls gfx_BuildScreenScaleTables@0604d524.

Camera record int fields: [0..2] position, [3..5] local offset, [6..8] pivot, [9] pitch, [10] yaw, [11] roll, [0xc..0xe] angle offsets, [0x11] ushort course lookup, [0x13] nearest course point, [0x14] view state, [0x15] racer id, [0x17] transition timer, [0x18..0x1a] target offset, [0x1d] target roll, +0x178 player index.
Racer records: 0x40 bytes at 0x0606ee48 (+0..8 pos, +0xc pitch, +0x10 yaw, +0x14 roll/lean, +0x24 speed). Bike physics record 0x16c bytes near 0x0607c480 (+0x2e bike state, GUESS 8 = crash).

## 2. Views and the view button
- car_InitState: game-mode byte (0x06088c0c) 0 or 0x15 gives state 0xf (out of range, default case becomes 2). Otherwise state 5 (intro), timer 0x32 = 50 frames, offset (0,-4.0,-200.0) lerping to (0,-4.0,-26.0).
- Button: flag array 0x0606ea4c[player], written in pad_UpdatePlayerControl@06029378 (at 0602964c, 06029880, 06029a78) as pad bit AND per-player mask (mask unresolved).
- car_UpdateByState: if game mode in 0xf..0x12, flag set and timer [0x17] == 0, then state++; above 4 wraps to 2. Preset entry[state] is loaded from ROM table 0x0602cda8 (stride 0x48) by car_ApplyInitParams, which sets timer = 7. Holding the button cycles every 7 frames.
- Cycle 2 -> 3 -> 4 -> 2. States 1/2 = first-person/handlebar (GUESS): camera at racer, RotX(-FieldB-FieldA), translate (0, -clamped*0.1, 0). Roll [11] = racer lean, so it rolls with the bike. States 3/4 = chase (state 4 returns to 2 when timer hits 0; GUESS it is a short roll view). State 5 intro. States 6/0xe/7 use look-at (finish/results presets set from race_* functions; GUESS).
- Chase code only runs if flag byte PTR_DAT_0602d624 == 0.

## 3. Chase camera maths (states 3 and 4)
| Item | Value |
|---|---|
| Target offset (preset 3, words 9,0xa) | (0, -4.0, -26.0): 26 behind, 4 up (GUESS: negative Y is up) |
| Offset blend | each frame cur += FixedMul(target-cur, Div(0x10000, timer)); done when timer hits 0 (7 frames) |
| Pivot | racer pos + local (0, -12.0, +7.0) after RotY(-yaw), RotX(pitch); DAT_0602d820 = -12, DAT_0602d81c = 7 |
| Speed pull-back | state 3 only, game mode < 0x12: extra local Z of -(speed(+0x24) >> 3) |
| Final position | translate(pivot), RotY(-[10]), LocalZ(-pull), RotX([9]), translate([3],[4],[5]) |
| Yaw lag | err = wrap12(cam[10]-racerYaw); cam[10] -= err >> 3 (1/8 per frame) |
| Pitch lag | bike state != 8: eases toward int[0x50] by 1/18.048 per frame (double at 0x0602d2c0); else clamp 260 branch |
| Roll | state 4: target roll [0x1d] = racer lean (+0x14), lerped like offset; state 3: 0. So roll follows lean in state 4 and first-person (GUESS on state 4) |
| Look-ahead | FixedMul(Div((a-b)<<16,(c-d))>>1, 0.698 [0xb2b8]) from per-player course-point short tables, clamp +-130 (0x82), scaled by 0x1a, added to yaw. UNRESOLVED: as decoded the clamp leaves it near zero; needs disassembly |
| Angle unit | 4096 per turn; math_ApplyDeadzoneOffset@060332ac is really a 12-bit wrap (2048/-4096/-2048/4096) |
| Other | height factor 0.1 (0x1999), clamp max 12.5 (DAT_06032d08 = 0xc8000), speed scale 0.04 (DAT_06032de4 = 2621) |

## 4. FOV / screen scale
- tlCamera_Create 3rd argument (camera int[0x10]) is the focal value: 1P 350 (0x15e, DAT_06025a64) if flag at pointer 0x06025ab4 nonzero else 232 (0xe8, DAT_06025b48); 2P 180 (0xb4, DAT_06025d74). Flag meaning unresolved.
- int[0xd] = viewport width * 1.6 (DAT_0604d310 = 0x19999).
- gfx_BuildScreenScaleTables: x = f*(W>>5)*65536/(z*11), y = f*(H>>5)*65536/(z*7), z from 4. The 11:7 is an aspect factor.
- Messages (0x0604d2f8..fe): 0x400 sets focal, 0x401 int[0x11] (default 2), 0x403 re-adds layer sprite (race uses it with pad_UpdatePlayerSlot0/1 as callback), 0x404 look-at.

## 5. Unresolved
View-button pad mask; which race_* calls set finish/results presets; 0x06025ab4 focal flag; look-ahead clamp; car_SortByProgress / car_FindNearbyCars also use the 0x188 table (names possibly wrong, not renamed).
