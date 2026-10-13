# Manx TT Super Bike (Saturn): AI, Ghostrider, demo replay, camera

Source: study/aicam.c (32 functions, read fully). Fixed point: 16.16 or 12-bit; angles in a 16-bit-style unit.
Limit: DAT_xxxxxxxx are literal-pool constants whose values are not printed in the decompile, so most tuning numbers
below are "value not extracted" (names given). Numbers shown are literal constants in the code. GUESS marks inference.
NOT FOUND in this file: the in-race chase camera (distance/height/lag/look-ahead). tlCamera_Create is called from
gamestart_TaskMain @060252a4 and optback_TaskHandler @06015648 only; the chase logic must be in a race-task function elsewhere.

## 1. Rival rider AI
Racer record = 0x40 bytes per rider. Race state byte: 0x10 = racing, 0x13 = finished.
- ai_UpdateRacerSpeedGear @06033774: the AI uses the SAME engine/gear model as the player (rpm, gear shift: DAT_06033882 is the rpm field offset 0xBC, DAT_0603388c = 0x36B00000 = 14000.0 rpm upshift, DAT_06033890 = 0x1B57FFFF ~ 7000.0 rpm downshift; see Resolved (final pass)). Riders are not scripted speed sliders; a target speed drives throttle.
- ai_SelectSpeedTarget @06034e80: target speed from a table indexed by rank gap (player vs rider). 8 bytes per entry {base, slope}, 29 (0x1d) entries per course/difficulty. This IS the rubber band: slower riders in front of the player ease off, riders behind speed up (GUESS on direction; structure confirmed).
- ai_UpdatePathFollow @060346b4: follows track data. Waypoint record 0x1c bytes, segment lengths via vec_DistanceScaled. Path table stride 8 bytes, two lines (offsets +0 and +0x18) interpolated with one shared t, so the rider sits between a left and right line. Lane offset = per-segment byte array, shifted <<16 (16.16) and blended between the two lines.
- Steering/lean: lean ramp +-2 per frame, cap +-0x14 (20), reset value +-0xc (12), deadband 0x1c (28). Heading error from Atan2 on halved deltas (shift-halving loop avoids overflow before IntSqrt/Atan2).
- Overtake/avoid: "cone behind another bike" test with an angle window of +-0x61 (97 units); inside it the rider matches the speed of the bike ahead rather than closing. Collision shove velocities stored at racer +0x68..+0x74 with per-frame decay (decay 0x028F = 655/65536 ~ 1.0% per frame on +0x68/+0x6c; the +0x70/+0x74 impulses are multiplied by the same 0.01 each frame; see Resolved).
- Crash/recover: a state switch hands the rider to ai_UpdateRacerPathStep @06036448, which steps the rider back to the path.
- ai_UpdateRacerRubberBand @06035104 (4390 bytes, largest AI function): combines gap table, cone test, shoves and lane blend (name is broader than its content: it is effectively the main per-frame AI update).
- path_ComputeSegmentValue @0602cad0: per-segment value used by the path tables.
- cam_FindNearestSplinePoint @06022378: nearest point on the 12-byte-point track spline; shared with the demo camera.

## 2. Ghostrider (best-lap ghost)
- ghost_InitState @0602ec70; ghost_UpdateRecordPlayback @0602ee70 (swaps double buffer on "Lap Change"); ghost_PrintBestTime @0602ed48.
- Recorded per frame (every frame, so 60 Hz NTSC / 50 Hz PAL; GUESS: no decimation in code seen): one 0x18-byte sample = x, y, z (3 ints) + 3 angle ints.
- Playback: interpolates toward the next sample; ghost speed = IntSqrt(dx^2+dy^2+dz^2) * scale (used for wheel/engine animation).
- Backup RAM file (ghost_SaveToBackup @06020c28, ghost_LoadFromBackup @060209f8): +0 lap time, +4 point count, +8..0x13 start xyz, +0x14 onward 8 bytes per point (3 signed-byte deltas + 3 packed 12-bit angles), last 4 bytes = checksum + salt. So 0x18 bytes raw shrinks to 8 (3x). Header 0x14 bytes.
- ghost_DeltaEncodePoints @0602075c / ghost_DeltaDecodePoints @060207f8 / ghost_UnpackPoints @0602094c do the packing.
- Saved only if faster than the stored record; save string "Ghostrider"; per-course file name table.
- Size estimate (GUESS): a 90 s lap at 60 Hz = 5400 samples * 8 = ~43 KB, close to the Saturn internal backup limit (GUESS: so a sampling step may exist in the pack stage; not confirmed).

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
- Ghost: record pos + 3 angles every frame, delta-pack to 8 bytes/sample with a checksum; save only on a new best; double buffer swapped at lap change.
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
3. Rubber-band direction (line 12) stays an inference; the ghost sampling rate (lines 23, 28) is also unconfirmed.
