# Manx TT Super Bike (Saturn): AI, Ghostrider, demo replay, camera

Source: study/aicam.c (32 functions, read fully). Fixed point: 16.16 or 12-bit; angles in a 16-bit-style unit.
Limit: DAT_xxxxxxxx are literal-pool constants whose values are not printed in the decompile, so most tuning numbers
below are "value not extracted" (names given). Numbers shown are literal constants in the code. GUESS marks inference.
NOT FOUND in this file: the in-race chase camera (distance/height/lag/look-ahead). tlCamera_Create is called from
gamestart_TaskMain @060252a4 and optback_TaskHandler @06015648 only; the chase logic must be in a race-task function elsewhere.

## 1. Rival rider AI
Racer record = 0x40 bytes per rider. Race state byte: 0x10 = racing, 0x13 = finished.
- ai_UpdateRacerSpeedGear @06033774: the AI uses the SAME engine/gear model as the player (rpm, gear shift: DAT_06033882 is the rpm field offset 0xBC, DAT_0603388c = 0x36B00000 = 14000.0 rpm upshift, DAT_06033890 = 0x1B57FFFF ~ 7000.0 rpm downshift; see Resolved (final pass)). Riders are not scripted speed sliders; a target speed drives throttle.
- ai_SelectSpeedTarget @06034e80: target speed from a table indexed by rank gap (player vs rider). 8 bytes per entry {base, slope}, 29 (0x1d) entries per course/difficulty. This IS the rubber band: slower riders in front of the player ease off, riders behind speed up (direction RESOLVED 10-13: AI ahead of its reference slow down, trailing AI speed up; see Resolved (drill pass, 10-13)).
- ai_UpdatePathFollow @060346b4: follows track data. Waypoint record 0x1c bytes, segment lengths via vec_DistanceScaled. Path table stride 8 bytes, two lines (offsets +0 and +0x18) interpolated with one shared t, so the rider sits between a left and right line. Lane offset = per-segment byte array, shifted <<16 (16.16) and blended between the two lines.
- Steering/lean: lean ramp +-2 per frame, cap +-0x14 (20), reset value +-0xc (12), deadband 0x1c (28). Heading error from Atan2 on halved deltas (shift-halving loop avoids overflow before IntSqrt/Atan2).
- Overtake/avoid: "cone behind another bike" test with an angle window of +-0x61 (97 units); inside it the rider matches the speed of the bike ahead rather than closing. Collision shove velocities stored at racer +0x68..+0x74 with per-frame decay (decay 0x028F = 655/65536 ~ 1.0% per frame on +0x68/+0x6c; the +0x70/+0x74 impulses are multiplied by the same 0.01 each frame; see Resolved).
- Crash/recover: a state switch hands the rider to ai_UpdateRacerPathStep @06036448, which steps the rider back to the path.
- ai_UpdateRacerRubberBand @06035104 (4390 bytes, largest AI function): combines gap table, cone test, shoves and lane blend (name is broader than its content: it is effectively the main per-frame AI update).
- path_ComputeSegmentValue @0602cad0: per-segment value used by the path tables.
- cam_FindNearestSplinePoint @06022378: nearest point on the 12-byte-point track spline; shared with the demo camera.

## 2. Ghostrider (best-lap ghost)
- ghost_InitState @0602ec70; ghost_UpdateRecordPlayback @0602ee70 (swaps double buffer on "Lap Change"); ghost_PrintBestTime @0602ed48.
- Recorded once per game frame (RESOLVED 10-13: one sample per call of ghost_UpdateRecordPlayback, which runs once per main-loop iteration = 2 VBlanks during a race, so 30 Hz NTSC / 25 Hz PAL [guess on region]; no decimation; cap 3000 samples): one 0x18-byte sample = x, y, z (3 ints) + 3 angle ints.
- Playback: interpolates toward the next sample; ghost speed = IntSqrt(dx^2+dy^2+dz^2) * scale (used for wheel/engine animation).
- Backup RAM file (ghost_SaveToBackup @06020c28, ghost_LoadFromBackup @060209f8): +0 lap time, +4 point count, +8..0x13 start xyz, +0x14 onward 8 bytes per point (3 signed-byte deltas + 3 packed 12-bit angles), last 4 bytes = checksum + salt. So 0x18 bytes raw shrinks to 8 (3x). Header 0x14 bytes.
- ghost_DeltaEncodePoints @0602075c / ghost_DeltaDecodePoints @060207f8 / ghost_UnpackPoints @0602094c do the packing.
- Saved only if faster than the stored record; save string "Ghostrider"; per-course file name table.
- Size estimate (corrected 10-13): the recorder stops at 3000 samples (100 s at 30 Hz, 120 s at 25 Hz), so a ghost is at most 3000 * 8 = 24000 bytes plus the 0x14 header; the old 60 Hz / 5400 sample estimate is wrong.

## 3. Attract / demo replay
- demo_StartReplayTask @06022d50, demo_UpdateReplayState @06022dac, demo_AdvanceReplayEntry @06022ce0.
- 16-byte cut table entries: mode, 2 params, 1 more; -1 terminator then loops.
- 3 camera modes: demo_StepReplayCamMode1 @060225b4, Mode2 @060226c8, Mode3 @06022988. Cut triggers: camera loses sight of the bike (heading vs nearest spline direction) or the polygon/track section changes.
- Smoothing: cam_StepAccelToTarget @06022064, trapezoidal accel to a target: struct {current, target, velocity, accel, max speed, active byte at +0x14}. Reusable for any camera/ramp.

## 4. Camera infrastructure
- tlCamera_Create @0604d148 (errors on null viewport or existing camera), tlCamera_Destroy @0604d194, camera_TaskHandler @0604d1d0, camera_AttachToViewport @0604d468, camera_CallIfAttached @0604d070, camera_ApplyViewTransform @0604d08c.
- Struct: pos +0x18/+0x1c/+0x20, pitch +0x24, yaw +0x28, roll +0x2c. View matrix = RotZ(roll), RotX(pitch), RotY(yaw), then translate. Look-at = Atan2 on halved deltas.
- Chase distance/height/lag/look-ahead/lean-roll: NOT in aicam.c (open item; check race task callers writing +0x18..+0x2c).
- view_UpdateCameraPathDraw @0603c4a4 and view_SetCameraPathDraw @0603c7d8 are NOT cameras: 16-byte keys feeding anim_InterpolatePoseMatrices (A/B) from racer position = rider/bike pose animation players.
- Scene helpers: scene_QueueMapObjectQuads @0603b3dc (max 24 quads, 21-frame index modulo), scene_QueueBillboardRing @0603ba80 (48 iterations, spiral); both queue type-2 billboard records into the z-sort buffer.

## Ideas for a fan bike/racing game
- Give AI riders the player's physics (same engine/gear model) and drive them only by a target speed + lane; it reads as fair and cheap.
- Rubber band through a small {base, slope} table indexed by rank gap, per course and difficulty (29 entries is plenty); tune data, not code.
- Two edge lines per track segment plus a per-segment lane byte gives varied lines for every rider with one shared t.
- Cone-behind test (+-97/256-ish angle) for "match speed of bike ahead" gives believable following and overtakes without a full planner.
- Collision shove as decaying velocity added on top of path following, then a recover state that rejoins the path.
- Ghost: record pos + 3 angles every game frame (30 Hz, max 3000 samples), delta-pack to 8 bytes/sample with a checksum; save only on a new best; double buffer swapped at lap change.
- Demo mode as a small cut table (mode, params) looping, with auto cuts when the camera loses sight of the subject.
- Trapezoidal-acceleration smoother struct as a universal camera/UI easing primitive.

## Resolved (final pass)
1. Gear thresholds (ai_UpdateRacerSpeedGear)
- DAT_06033882 = 0xBC (rpm field offset); gear at +0x140.
- DAT_0603388c = 0x36B00000 = 14000.0 (upshift rpm). DAT_06033890 = 0x1B57FFFF ~ 7000.0 (downshift).
- Downshift sets state bits 0x20 (gear 2), 0x40 (gears 3-4), 0x80 (gears 5-6). Not an else branch: see Resolved (trim pass).

2. Shove decay
- DAT_0603604e = 0x028F = 655 = 0.01. The +0x68/+0x6c velocities decay 1% per frame; impulse words +0x70/+0x74 are added into them and collapse to 1% per frame.

3. Speed table of ai_SelectSpeedTarget
- At 0x0606EAAC: 29 entries of 8 bytes {base, slope}, 16.16, set stride 232 bytes. Set 0 at 0x0606EAAC, set 1 at 0x0606EB94, set 2 at 0x0606EC7C, empty set 3 at 0x0606ED64.
- Index = RAM byte 0x0607f72c * 29 + sub-index (byte meaning: see Resolved (trim pass)). Result = base - gapfield(rec+0xa0) * slope via FixedMul with speed. Speed floor 0x13ffff (~20.0); gap threshold 0x3332 (0.2).
- Sub-index map: +3 cone/behind case, +4 default, +0x15..0x1c gap bands, +0xd+count ahead cases.
- Set 1 differs from set 0 at indices 22 and 26; set 2 is a harder set. Full first-13 entries are in section 8 of this report.
- Checked 10-13 (main chat): the AI shift points differ from the player's. Player bike_UpdateGear 0x06037728 uses 0x32c80000 = 13000.0 up (0x06037844), 0x270fffff ~ 10000 down (0x06037848), plus 0x2af7ffff ~ 11000 (0x0603784c); the AI's own gear code uses 14000 / 7000. Same engine model, different shift points.

## Resolved (trim pass)
1. ai_UpdateRacerSpeedGear (0x06033774): the shift code is two sequential ifs, not an else branch. At 0x06033792: if rpm (rec+0xbc) > 14000.0 [0x36b00000], gear (rec+0x140) is incremented when gear <= 5 (0x0603379e-0x603a6). Then rpm is reloaded and at 0x060337ac: if rpm <= 7000.0 [0x1b57ffff] and gear > 1, a jump table (0x060337c4) ORs 0x20, 0x40 or 0x80 into rec byte +0x2e and gear is decremented (0x060337fa). After an upshift rpm is still above 7000, so the two cannot both fire in one call. Gear 1 never downshifts.
2. Byte 0x0607f72c: written in courseselect_TaskHandler (0x0601a612-0x0601a624: constants 0 and 2, or a menu field at +0x174 stored byte-wide) and hiscore_TaskHandler (0x06018f6a-0x06019000, values 0/2/menu field); read by load_SetupLoadingScreen (0x06024912) and ai_SelectSpeedTarget (0x06034e9c, times 29). It is the course/class selection chosen on the course-select screen (values 0..2); the exact on-screen label (difficulty or course) was not traced. It picks the AI speed table set, set 3 being empty.
3. Rubber-band direction and ghost sampling rate: both RESOLVED in the drill pass (10-13), see below.

## Resolved (drill pass, 10-13)
### Q3 Rubber band direction (ai_SelectSpeedTarget 0x06034E80)
Table 0x0606EAAC, 3 sets x 29 entries x {base, slope} 16.16 (set 0 0x0606EAAC, set 1 0x0606EB94, set 2 0x0606EC7C, set 3 0x0606ED64 empty). Index = byte[0x0607f72c] * 29 + sub-index. Returned target = FixedMul(ratio, base - X * slope), X = AI struct +0xa0, ratio = math_NormalizedShortRatio(0) (0x06037690, speed-profile fraction from path data).
Set 0 {base / slope}: 0: 1.0/0.04; 1: 1.15/0.02; 2: 1.15/0.02; 3: 1.5/0.04 (standing start); 4: 0.9/0.03 (default); 5: 0.98/0.04; 6: 0.97/0.04; 7: 0.96/0.04; 8: 0.96/0.04; 9: 0.95/0.05; 10: 0.94/0.06; 11: 0.93/0.06; 12: 0.92/0.06; 13: 1.2/0.04; 14: 1.1/0.04; 15: 1.05/0.04; 16: 1.05/0.04; 17: 0.955/0.05; 18: 0.945/0.06; 19: 0.935/0.06; 20: 0.925/0.06; 21: 1.12/0.05; 22: 1.15/0.035; 23: 1.10/0.05; 24: 1.22/0.04; 25: 1.15/0.03; 26: 1.23/0.038; 27: 1.14/0.04; 28: 1.15/0.04.
Set 1 = set 0 except 22 = 1.30/0.035 and 26 = 1.26/0.035. Set 2 (harder): 3: 1.535/0.04; 5: 1.555; 6: 1.444; 7: 1.333; 8: 1.222; 9: 1.111/0.05; 10: 1.0/0.06; 11: 0.99; 12: 0.98; 13: 1.3; 14: 1.28; 15: 1.24; 16: 1.22; 17: 1.135/0.05; 18: 1.10; 19: 0.985; 20: 0.976; 21: 1.3; 22: 1.3/0.025; 23: 1.4; 24: 1.4/0.03; 25: 1.5/0.02; 26: 1.5/0.015; 27: 1.98/0.03; 28: 1.98/0.03; entries 0, 1, 2, 4 as set 0.
Caller: ai_UpdateRacerRubberBand (call at 0x060354e2) passes (struct, *(struct+0x20) = 0x40 record, own rank, reference racer index). Rank 0 = leader. Reference = the live racer one rank ahead (skipping dead ones with +0x2f >= 8); for the leader it defaults to the player bike (byte 0x0606e624).
Cases:
- Own speed <= 0x13ffff (~20.0): entry 0. Byte 0x06088c0c < 0x10: ratio returned unchanged (no rubber band).
- Start zone (+0x1a < 0x6e in modes 1/3/4, <= 0xcf in mode 2): entry 3 (1.5x launch boost).
- Reference ahead of this AI (refRank < ownRank, AI trailing): own rank < 4: gap >= 3 gives entry 0x1c (ratio > 0.2) or 0x1b, gap < 3 gives 0x1a (ratio > 0.2) or 0x19; own rank >= 4: gap >= 2 gives 0x18 or 0x17, else 0x16 or 0x15. Bases 1.10 to 1.23 in set 0 (up to 1.98 in set 2), larger for larger gap: trailing AI speed up.
- Reference not ahead (refRank >= ownRank, AI leading): ratio > 0x3332 (0.2): entry N + 13 where N = *0x060886e4 (count of consecutive running ranks, init 7 at 0x0603349a, recomputed in car_UpdateNearestRivals 0x06033732): entries 14..20, base 1.10 down to 0.925, slope up to 0.06: leading AI slow down. Ratio <= 0.2: entry 4 (0.9/0.03). Then a clamp to the speed of the rival ahead when N - rank == 1.
- Sign convention: gap = ownRank - refRank. Positive (AI behind) = multiplier above 1; zero or negative (AI ahead) = multiplier at or below 1.1 and down to 0.925/0.9.
- X = struct +0xa0 is written at 0x06033df2 from a runtime-filled table at 0x06033a4c + 0x1c * [0x06080038] + 4 * riderIdx (zero in the file, 0x06033a38..0x06033b37). [guess] a per-rider skill/aggression value; unresolved.
- Caveat: the "ahead" entries are indexed by the active-racer count N, not by the gap value.
- The player is also pulled by car_ComputeCatchupBonus (see study_handling.md, Resolved (drill pass, 10-13)).

### Q4 Ghost sample rate and frame timing
- ghost_UpdateRecordPlayback 0x0602ee70 is registered as a per-frame event callback (gamestart_TaskMain 0x06025f62 passes 0x06026638 to 0x060427cc; 0x06026638 calls the ghost function at 0x06026674). main_GameLoop 0x06042a90 fires evt_FireChannel (0x060426a4) channels 1, 0, 2 once per iteration, so the ghost function runs once per main-loop iteration.
- It runs only when (*0x0607d008 & 0x82) == 0x82. Recording block (0x0602f030): when mode byte 0x06088c0c == 0x10 and sample count [0x0607c414] <= 2999 (0xbb7), it copies the first 0x18 bytes of the player's record (0x0606ee48: x, y, z, 3 angles) to buffer [0x0607c424] + count * 0x18 and increments count. So: one sample per call, no decimation, max 3000 samples. Playback block (0x0602ee88-0x0602eff8, needs [0x0607c400] bit 0 and mode 0x10): reads sample [0x0607c40c] of buffer [0x0607c420], wraps at length [0x0607c410], interpolates with the next, writes pos/angles to 0x0606ee48 + 0x40..0x54 (the ghost record), speed = IntSqrt(dx^2+dy^2+dz^2) * scale to +0x64, and advances the index by 1 per call. The lap-change block (0x0603aec4 lap vs [0x0607c408]) swaps buffers.
- Frame pacing: vdp_EndFrameSync 0x060475ac waits for the vblank flag 0x0607f718, then waits until halfword 0x060710e8 (reloaded from 0x060710ea, decremented by irq_VBlankIn 0x06046690) reaches 0. 0x060710ea is the VBlanks-per-frame divider: set to 1 in menus and to 2 in gamestart_TaskMain at 0x06025372 (race setup; reset to 1 at 0x060261f4). VBlank counter = 0x0606fa24 (++ at 0x06046782); irq_VBlankIn also ++ 0x0607c12c.
- So during a race there is exactly one game/physics tick per rendered frame, locked to 2 VBlanks (30 fps NTSC, 25 fps PAL) and at least 2 VBlanks long (a slow frame lasts 3+ VBlanks and simply runs slower). The measured frame length (0x060710f0, written at 0x06047640) has no reader found, so there is no frame-skip and no dt compensation: physics (dt 0x0a3d = 0.04) is tied to the frame rate. [guess] 0.04 s is exact for PAL (25 Hz); on NTSC the sim runs 30 ticks per real second.
- Correction: 0x0606fa20 is not a tick counter; it is zeroed together with 0x0606fa24 (obj_ClearRootPointers 0x06040008) and never incremented in the code seen. Its &1/&3 uses (0x0603211c, 0x06032588, 0x06030654, 0x060333ac) are unresolved. [guess] unrelated to the 25 Hz tick.

## Resolved (guess dig, 10-13)
- AI rec +0xa0 (was [guess] skill/aggression): RESOLVED, it is a per-rider PACE HANDICAP slot 1..7 (1 = fastest AI, 7 = slowest), not random skill. The table at 0x06033a4c + 0x1c*N + 4*riderIdx is constant data in the file (N=1:(1); 2:(1,4); 3:(1,3,5); 4:(1,2,4,6); 5:(1,2,3,5,7); 6:(1,2,3,4,6,7); 7:(1..7)). N = [0x06080038] = AI racer count, set in task_InitMainEnemy 0x06033380 (literal 0x060334ec) as 8 - [0x0606ed64] (human count) when < 2. task_InitMainEnemy2 0x06033b38 copies the row into +0xa0 (literals 0x06033ea0 table, 0x06033e9c count).
- Use: ai_SelectSpeedTarget 0x06034e80 computes FixedMul(ratio, base[0x0606eaac + idx*8] - rec[+0xa0]*slope) (offset literals DAT_060350fa / DAT_06035044 = 0xa0); slope 0.02-0.06, so the slowest AI loses ~0.2-0.4 of target speed.
