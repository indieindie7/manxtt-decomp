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
Racer records: 0x40 bytes at 0x0606ee48 (+0..8 pos, +0xc pitch, +0x10 yaw, +0x14 roll/lean, +0x24 speed). Bike physics record 0x16c bytes near 0x0607c480 (+0x2e bike state: 2 wall flag, 3/4 crash, 8 lateral slide).

## 2. Views and the view button
- car_InitState: game-mode byte (0x06088c0c) 0 or 0x15 gives state 0xf (out of range, default case becomes 2). Otherwise state 5 (intro), timer 0x32 = 50 frames, offset (0,-4.0,-200.0) lerping to (0,-4.0,-26.0).
- Button: flag array 0x0606ea4c[player], written in pad_UpdatePlayerControl@06029378 (at 0602964c, 06029880, 06029a78) as (pad word at param_4+0x10 AND per-player mask) != 0; mask resolved in "Resolved (final pass)" (OR of the buttons bound to action code 0xC4).
- car_UpdateByState: if game mode in 0xf..0x12, flag set and timer [0x17] == 0, then state++; above 4 wraps to 2. Preset entry[state] is loaded from ROM table 0x0602cda8 (stride 0x48) by car_ApplyInitParams, which sets timer = 7. Holding the button cycles every 7 frames.
- Cycle 2 -> 3 -> 4 -> 2. States 1/2 = first-person/handlebar (see Resolved (drill pass, 10-13) for labels): camera at racer, RotX(-FieldB-FieldA), translate (0, -clamped*0.1, 0). Roll [11] = racer lean, so it rolls with the bike. States 3/4 = chase (state 4 returns to 2 when timer hits 0; GUESS it is a short roll view). State 5 intro. States 6/0xe/7 use look-at. Finish/results presets are set from race_* functions (resolved: ROM presets 0x0602cf10/cf58/cfa0, see Resolved (final pass)).
- Chase code only runs if flag byte PTR_DAT_0602d624 == 0.

## 3. Chase camera maths (states 3 and 4)
| Item | Value |
|---|---|
| Target offset (preset 3, words 9,0xa) | (0, -4.0, -26.0): 26 behind, 4 up (negative Y is up: Y is down-positive, confirmed by the ground probes) |
| Offset blend | each frame cur += FixedMul(target-cur, Div(0x10000, timer)); done when timer hits 0 (7 frames) |
| Pivot | racer pos + local (0, -12.0, +7.0) after RotY(-yaw), RotX(pitch); DAT_0602d820 = -12, DAT_0602d81c = 7 |
| Speed pull-back | state 3 only, game mode < 0x12: extra local Z of -(speed(+0x24) >> 3) |
| Final position | translate(pivot), RotY(-[10]), LocalZ(-pull), RotX([9]), translate([3],[4],[5]) |
| Yaw lag | err = wrap12(cam[10]-racerYaw); cam[10] -= err >> 3 (1/8 per frame) |
| Pitch lag | bike state != 8: eases toward int[0x50] by 1/18.048 per frame (double at 0x0602d2c0); else clamp 260 branch |
| Roll | state 4: target roll [0x1d] = racer lean (+0x14), lerped like offset; state 3: 0. So roll follows lean in state 4 and first-person (GUESS on state 4) |
| Look-ahead | FixedMul(Div((a-b)<<16,(c-d))>>1, 0.698 [0xb2b8]) from per-player course-point short tables, clamp +-130 (0x82), scaled by 0x1a, added to yaw. RESOLVED: the clamp is real and degenerate: |x| > 130 raw is replaced by +-130 raw (not 130.0), then scaled by 26/65536, so the term is 0 (or -1 for negative) angle units per frame; see Resolved (final pass) |
| Angle unit | 4096 per turn; math_ApplyDeadzoneOffset@060332ac is really a 12-bit wrap (2048/-4096/-2048/4096) |
| Other | height factor 0.1 (0x1999), clamp max 12.5 (DAT_06032d08 = 0xc8000), speed scale 0.04 (DAT_06032de4 = 2621) |

## 4. FOV / screen scale
- tlCamera_Create 3rd argument (camera int[0x10]) is the focal value: 1P 350 (0x15e, DAT_06025a64) if flag at pointer 0x06025ab4 nonzero else 232 (0xe8, DAT_06025b48); 2P 180 (0xb4, DAT_06025d74). Flag = global word at 0x0607ec18, a screen/flow class (0 = race, 1/2 = menu-type flow); see Resolved (final pass).
- int[0xd] = viewport width * 1.6 (DAT_0604d310 = 0x19999).
- gfx_BuildScreenScaleTables: x = f*(W>>5)*65536/(z*11), y = f*(H>>5)*65536/(z*7), z from 4. The 11:7 is an aspect factor.
- Messages (0x0604d2f8..fe): 0x400 sets focal, 0x401 int[0x11] (default 2), 0x403 re-adds layer sprite (race uses it with pad_UpdatePlayerSlot0/1 as callback), 0x404 look-at.

## 5. Unresolved
(Items 1-4 resolved below.) Still open: car_SortByProgress / car_FindNearbyCars also use the 0x188 table (names possibly wrong, not renamed).

## Resolved (final pass)
Image 0.AAA at 0x06010000, big-endian. Values read from ROM/decomp_0.c. Unproven items are marked GUESS.

1. View-button mask
- Flag array 0x0606ea4c[p] = ((pad word at +0x10) & mask) != 0. Written at pool sites 0x0602964c (cfg0), 0x06029a78 (cfg1), 0x06029880 (cfg2); consumed at 0x0602d490.
- Masks are RAM at 0x060886f0 + 8*cfg + 4*p, filled by input_BuildActionButtonMasks (0x060291c4) as the OR of buttons bound to action code 0xC4 (case 3).
- Binding tables: cfg pointers at 0x0606ea40 -> 0x0606b374, 0x0606b3f4, 0x0606b474; 4 presets x 8 words (action codes 0xC1..0xC5); preset chosen by RAM byte array 0x060896bc; button bit tables at 0x0606e9e0 + 0x20*cfg.
- Action 0xC4 mask (hex):

| cfg | preset 0 | preset 1 | preset 2 | preset 3 |
|---|---|---|---|---|
| 0 | 0x70 | 0x88 | 0x88 | 0x560 |
| 1 | 0x560 | 0x70 | 0x88 | 0x88 |
| 2 | 0x440 | 0x440 | 0x3000 | 0x70 |

- Button names per bit resolved: see Resolved (trim pass).

2. Focal flag 0x06025ab4
- Reads global word 0x0607ec18: nonzero -> 350 (0x15e), zero -> 232 (0xe8).
- Written 0 in boot_TaskEventHandler, 1 in game_NextTrackDecide (0x06016470) and congrats_TaskHandler (0x0601f090), 2 in title_TaskMain (0x06023750).
- Values: see Resolved (trim pass); 0 = live race, nonzero = non-race flow.

3. Look-ahead clamp
- x = FixedMul(Div(dA<<16, dB)>>1, 0xb2b8 (=0.698)). If |x| > 0x82 (130 raw) then x = FixedMul(+-0x10000, 0x82) = +-130 raw (about 0.002 as 16.16, not 130.0). Then cam[10] += FixedMul(x, 0x1a): 0 for positive x, -1 for negative. Effectively dead.
- Runs only when speed > 0 and bike state != 8.

4. Finish/results camera presets (struct 18 words = 0x48 bytes, table 0x0602cda8; [1] state, [9]/[10] offset Y/Z, [17] timer)

| Address | State | Offset (Y, Z) | Timer | Used by |
|---|---|---|---|---|
| 0x0602ce80 | 3 | -4, -26 | 7 | normal chase |
| 0x0602cec8 | 4 | 0, 0 | 7 | race_CountdownStepA 0x060397a0, race_CountdownTickA 0x060398f4 (race timer 0x0607bf70 == 7) |
| 0x0602cf10 | 3 | -4, -26 | 25 | race_FinishInit 0x0603a118, both players |
| 0x0602cf58 | 6 | look-at words 20, -8, -80, 10, -20, 80 | 75 | race_EndTimerTickB 0x0603a22c at timer == 225 |
| 0x0602cfa0 | 3 | -30, -200 | 300 | race_EndTimerTickA 0x0603a054 (at 100); race_FinishToResultsA 0x0603a4b4, B 0x0603a550, C 0x0603a648 |

- State 4 has a zero offset, so it is cockpit-like; earlier text calling it a chase variant is superseded.

## Resolved (trim pass)
1. Pad word bit order (table at 0x0606e9e0, 8 words per cfg: 0x40, 0x20, 0x10, 0x200, 0x100, 0x400, 0x08, 0x80; cfg2 ends 0x1000, 0x2000). It matches the Saturn SMPC digital pad word (data0 high byte, data1 low byte): bit 15 Right, 14 Left, 13 Down, 12 Up, 11 Start, 10 A, 9 C, 8 B, 7 R, 6 X, 5 Y, 4 Z, 3 L. Table order is therefore X, Y, Z, C, B, A, L, R.
2. Action 0xC4 (view) masks decoded:
- 0x70 = X + Y + Z
- 0x88 = R + L (shoulders)
- 0x560 = A + B + X + Y (0x400 + 0x100 + 0x40 + 0x20)
- 0x440 = A + X
- 0x3000 = Up + Down (D-pad)
So the default cfg 0 / preset 0 view button is any of X, Y, Z; preset 1 and 2 use the shoulder buttons; preset 3 face buttons A/B/X/Y. Bit 0x1000 (Up) and 0x2000 (Down) only appear in cfg 2's table.
3. Word 0x0607ec18 (referenced by about 55 literal pools, 0x06014a68..0x06039d40, mostly menu/title code 0x06024xxx-0x06029xxx): written 0 in boot_TaskEventHandler, 1 in game_NextTrackDecide (pool 0x06016470) and congrats_TaskHandler (0x0601f090), 2 in title_TaskMain (0x06023750). Read by tlCamera focal choice (0x06025ab4: nonzero 350, zero 232) and by car_UpdateThrottleSpeed (0x06032ad4: nonzero means scripted throttle 0.9 [0xe666], brake 0). Conclusion: 0 = live race with player input; nonzero = non-race flow (1 menu/results/congrats, 2 title). Finer meaning of 1 vs 2 is only visible in the menu code and not traced.

## Resolved (drill pass, 10-13) - cam_UpdateByState state labels (Q5)
State = camera record int[0x14]. Presets in ROM table 0x0602cda8 (stride 0x48, entry index = state): entry 0 state 0; entry 1 state 1 (word 6 = -12.0); entry 2 state 2; entry 3 state 3 offset (-4, -26); entry 4 state 4 zero offset; entry 5 state 3 timer 25; entry 6 state 6 (look-at words); entry 7 state 3 offset (-30, -200) timer 300. Unknown states go to the default case, which sets state 2.

| State | Label | Offsets used (code at) |
|---|---|---|
| 0 | camera off / no update | switch does nothing; no code found that selects it [guess] |
| 1 | rider-eye view, unscaled height | cam_SnapToStartPosition to the racer, RotX(-FieldB - FieldA), translate Y = +clamped rec+0x128 unscaled (0x0602d4f0..0x0602d526). Only preset entry 1; no caller found that selects it [guess: unused/debug] |
| 2 | first person (rider/handlebar), the default state | same snap, RotX(-FieldB - FieldA - extra pitch from car_GetPositionVec), translate Y = -FixedMul(clamped rec+0x128, 0x1999 = 0.1) (0x0602d56c..0x0602d526): the landing squat moves the view by 0.1 of its size. Rolls with the bike |
| 3 | near chase (normal outside view) | shared chase code: pivot racer pos + local (0, -12, +7) after RotY(-yaw)/RotX(pitch), camera offset (0, -4, -26) blended in over 7 frames, extra pull-back speed >> 3 when game mode < 0x12, yaw lag 1/8 per frame, pitch lag ~1/18, roll 0. The finish camera (entry 5, 25 frames) and the far result camera (entry 7: offset (-30, -200), 300 frames) reuse state 3, so "far chase" = state 3 with entry 7's larger offset, not a separate state |
| 4 | roll/blend step into first person | same code as 3 with offset (0, 0) and target roll [0x1d] = racer lean (+0x14); no pull-back (state 3 only). It sets state 2 as soon as the transition timer int[0x17] reaches 0 (7 frames). Also used by the countdown (race_CountdownStepA 0x060397a0) |
| 5 | intro flyover | racer pivot, offset lerped from (0, -4, -200) to (0, -4, -26) over int[0x17] = 50 frames, plus lerped angle offsets [0xc..0xe]; set by cam_InitState at race start |
| 6 and 0xe | fixed look-at cut (finish / results camera) | pivot and angle offsets copied from the racer, then cam_ApplyTransformFromState; entry 6 words 20, -8, -80 and 10, -20, 80, 75 frames, used at race_EndTimerTickB 0x0603a22c (timer 225). State 0xe falls into the same code |
| 7 | lerped fixed camera | lerps local offset [3..5] toward [0x18..0x1a] while the timer is nonzero, then cam_ApplyTransformFromState; no preset selects it [guess] |
| 0xf and above | invalid | cam_InitState stores 0xf in game modes 0 / 0x15; the default case turns it into state 2 |

View button cycle (0x0602d44a): entry index 2 -> 3 -> 4 -> wraps to 2, each load sets the timer to 7. Because state 4 returns to 2 when its timer expires, the visible cycle is first person (2) <-> near chase (3), with 4 as a 7-frame blend step. The button works only in game modes 0xf..0x12 (byte 0x06088c0c - 0xf < 4) and when the per-player flag 0x0606ea4c[p] is set.
Corrections to older lines: state 2 is confirmed first person; state 1 is the same rig without the 0.1 height scale and has no known user; state 4 is a short roll/blend state, not a persistent cockpit view (supersedes the "cockpit-like" line in Resolved (final pass) item 4).
