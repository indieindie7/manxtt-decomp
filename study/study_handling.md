# Manx TT Super Bike (Saturn) - how the bike handles

Source: study/handling.c (Ghidra decompile, SH-2, program at 0x06010000). Constants decoded from the ROM image (0.AAA, offset = addr - 0x06010000).
Conventions: 16.16 fixed point unless noted; angles 12-bit (0x1000 = 360 deg, 0x400 = 90 deg; sin/cos table indexed (angle & 0xFFF), 8-byte entries). Everything marked (guess) is inference, not read from code.

Scope: I read the physics, steering, collision, fall, checkpoint code. I deliberately skipped rendering code (handling.c lines 233-2005 and course drawing 6668-7092) and did not read race-end timer functions (7500-7913), gate signs / playfield (8253-8695), car_SpawnAtTrackPoint (4328-4537) and track_FindPolygonUnderPoint (2834-3032; only its call sites).

Per-bike record: a 0x45-word working record per racer. Fields used (inferred from usage): +0x10 heading, +0x0C pitch, +0x14 steer/lean input, +0x24 speed, +0x2E state byte, +0x30 slot, +0x32 rank, +0x33 surface type, +0xBC rpm, +0x110 lateral velocity, +0x124 lean displacement, +0x134 lean angle, +0x140 gear, +0x148 grounded byte, +0x14C air counter.

## 1. Per-frame update chain
bike_UpdateRacerPhysics runs per racer per tick, in this order:
1. Switch on state byte rec+0x2E (0 prestart, 1 normal, 2 normal + aftereffect, 3/4 crash, 8, 9, 0xD grid start).
2. In normal states: car_UpdateThrottleSpeed (@06032918) -> gearbox (menu_UpdateSelectionLevel @06037728, really the gear logic) -> car_UpdateHeadingAngle (@06032714) -> car_UpdateLeanBalance (@06031F14) -> car_UpdateSteeringSkid (@06032450).
3. Steering torque (bike_UpdateSteeringTorque @060384CC) feeds the heading/lean calls.
4. Position bookkeeping, then bike_SubstepMoveCollide (@06037238): 10 substeps, each tries the move, reverts and zeroes speed on collision.
5. bike_CalcSteerAxisVelocity (@0603831C), bike_CalcLateralOffsetFromHeading (@06038428).
6. Ground probes (front/rear) -> grounded flag, pitch, surface type.
7. car_UpdateFallState (@060321BC), car_FindNearbyCars, then sound logic (engine pitch from rpm, skid, crash).
8. race_UpdateCheckpointLap (@0603A710) per racer.

Physics step dt = 0x0A3D = 0.04 s (guess: 25 Hz physics tick). Gravity 0x9CF5C = 9.81. km/h = speed * 0x39999 (3.6).

## 2. Throttle, brake, speed, top speed
- Forces are in kgf; acceleration a = F * 9.81 / (mass + 12). Mass = bike table +0 (237.0) + 60.0 rider = 297 kg for the base bike.
- Engine force = torque curve [rpm/100] (ptr in stat +0x14 = 0x0603AF7C; first entries 3.43, 3.56, 3.69, 3.83, 3.97 ... up to 4.85) * gear ratio * per-gear efficiency.
- Gear ratios (0x0606F664): 2.4, 1.94, 1.63, 1.43, 1.29, 1.19. Efficiency tables: 0x0606F680 (1.0, .92, .90, .88, .86, .83, .80), 0x0606F69C (1.125, 1.03, 1.0, .99, .97, .94, .90), 0x0606F6B8 (another set).
- Drag: Cd at stat +8 (0x8083 = 0.502 or 0x6062 = 0.3765) times speed squared (guess on exact form).
- Brake: stat +0x10 integer (500/618/481/437/600/562 kgf for the bikes).
- RPM: rec+0xBC, clamp 1300 to 15000. Target rpm = speed * 4.5605 * 30.715 * ratio. Eased toward target: factor 0.5409 when falling, 0.6662 when rising, snap if within 200 rpm.
- Gearbox: gears 1-6, upshift at 13000 rpm, downshift at 10000, 26-tick delay between shifts.
- Surface slowdown on speed: surface type 1 x0.9, type 3 x0.6 (see section 6).
- Airborne: rpm free-revs (no load).
- Top speed: emergent from torque * ratio vs drag; not a stored constant (guess). Not computed here.
- Rubber band: car_ComputeCatchupBonus: only if speed > 5.0 (0x4ffff, gate in the caller), range 600.0, angle <= 0xC3, bonus capped 80.0 (the cap, not a speed gate), never for the leader. Applies to every non-leader bike, player and AI (see Resolved (drill pass, 10-13)).

## 3. Steering and lean
- bike_UpdateSteeringTorque (@060384CC): input shaped by a cubic (fine control near center), scaled down with speed, clamped to +-0x1A, multiplied by 56.4 then 0.04.
- car_UpdateHeadingAngle (@06032714): heading relative to the course clamped to +-0x33C (about +-73 deg). Self-centering: MulHigh(rec+0x110, 0x4B4F). Steer input decays 0x22 per tick when released.
- car_UpdateLeanBalance (@06031F14): a spring-damper on lean displacement: spring 300.0, damping 0.51. Lean angle = -atan2(rec+0x124, 1.41) (1.41 = DAT_0603208c = 0x168F5 = 1.40999, the constant second argument of Atan2; lever-arm-like constant; no further meaning recoverable). So the bike leans against the lateral displacement, and the lean angle turns the heading (steer comes through lean, not directly).
- Counter-steer feel (guess): because input drives a spring-damper lean and lean drives heading, there is a short lag then a settled turn, and releasing returns by spring plus the self-centering term.
- car_UpdateSteeringSkid (@06032450): slip = atan2(lateral, forward); above 0x400 (90 deg units: threshold is large, effectively only in real slides) it triggers skid sound by frame mask.

## 4. Gravity, jumps, ground following, slopes
- Two probes: front (rec+0x4C) and rear (rec+0x70) via track_FindPolygonUnderPoint + track_ComputeSurfaceInfo.
- Airborne if the height offset above the surface > 1.5696 (0x191D0). Grounded byte rec+0x148, air counter rec+0x14C.
- Pitch is eased toward the surface slope from the two probes (so the bike pitches over crests); while airborne gravity 9.81 integrates vertical speed.
- Slopes: car_ComputeFixedPolynomial adds slot-mass-weighted terms from three stack-passed components; p5 = local normal y, p6 = local normal z of the rear ground probe (see Resolved (trim pass)).

## 5. Grip / slide
- No tire model per se; lateral velocity rec+0x110 is damped by self-centering (0x4B4F factor) and slip angle is only used for sound/effects. Slides are visual/audio, not a separate friction regime (guess).

## 6. Off-road and grass
- Surface type byte rec+0x33. Type 1 multiplies speed by 0.9 per tick (rough/edge), type 3 by 0.6 (grass/gravel: heavy slowdown). Other types normal.

## 7. Collisions
- Wall/barrier: bike_SubstepMoveCollide splits the move into 10 substeps; on a failed substep the position reverts, speed is set to zero, byte +0x2F is decremented, rubber-band pointer reset.
- Rider-rider: car_FindNearbyCars threshold 0x2B (proximity); response goes through the same substep path (guess).

## 8. Crashes / falls
- State byte 3/4 = crash with a recovery counter; car_UpdateFallState (@060321BC) damps with 0.98 per tick in states 3/4, otherwise 0.91. Crash sound when speed*0.62137*90 (high part) > 5. State 2 is normal driving with an after-effect (damp 0.98). Recovery duration: RESOLVED, counter rec+0x154 is set to 3 and the state returns to 1 after 3 physics ticks (about 0.12 s at dt 0.04); car_UpdateFallState branches on counter == 3, not on the state byte (see Resolved (final pass)).

## 9. Bike stats (table 0x0606F6D4, stride 0x20, 14 entries)
+0 mass 237.0; +4 12.0; +8 Cd (0.502 / 0.3765); +0xC steer factor; +0x10 brake (500/618/481/437/600/562); +0x14 torque curve ptr 0x0603AF7C; +0x18 gear ratio table 0x0606F664; +0x1C efficiency table ptr (0x0606F680 / 0x0606F69C / 0x0606F6B8). Per-slot mass words at 0x0607910C.

## 10. Checkpoints, laps, time extend
- race_UpdateCheckpointLap (@0603A710). Checkpoint table at 0x0606F1FC: stride 0x18 per checkpoint, 0x60 per course.
- Time extend: bonus = double(table value) * 25.0 (double at 0x0603A704) added to the global timer (PTR_DAT_0603A89C + 8). Units are ticks-ish (guess).
- Lap trigger when the progress counter == total checkpoints * (lap + 1). Final-lap flag at lap == laps - 2. Best-lap compare, race end state 0x13.
- race_InitState (@060391DC): modes 0xE/0xD, start timers 0x4B / 0x37.

## 11. What makes it feel good (guess where noted)
- Cubic steering shaping + speed scaling: precise at speed, lively when slow.
- Lean as a damped spring (300.0 / 0.51) gives weight and a smooth lean-in.
- Self-centering gives stability without a wobble.
- Dual-probe pitch gives visible bike attitude over crests.
- Gearbox with hysteresis and rpm easing gives engine feel; free-rev in the air.
- Rubber band keeps packs close without touching the leader.
- Collision zeros speed instead of bouncing (punishing, readable).

## Ideas for a fan bike/racing game
- Keep steer -> lean spring-damper -> heading; tune spring 300 / damping 0.51 as the starting point.
- Cubic input shaping and speed-scaled steering clamp are cheap and feel good.
- Use two ground probes for pitch; flag airborne at a ~1.5 unit gap.
- Gear/rpm easing with up/down thresholds (13000/10000) and a shift delay makes engine audio sell speed.
- Surface-type multipliers (x0.9, x0.6) are a simple off-road model.
- Rubber band only for trailing riders and only above a speed floor.
- Lap/time-extend checkpoint tables per course (arcade time attack).
- Fixed 25 Hz physics with 10 collision substeps avoids tunneling.
- Per-bike stat table (mass, Cd, brake, torque curve, ratios) for variety.

## Name fixes
- math_ApplyDeadzoneOffset @060332AC -> math_WrapAngle12
- menu_UpdateSelectionLevel @06037728 -> bike_UpdateGear
- several table_* helpers used as small math/lookup functions (see v3_handling.txt for the ones I am medium-sure about).

## Resolved (final pass)
1. Crash recovery
- rec+0x154 is set to 3 on entering the crash state; decrements once per tick in states 3/4; at < 1 the state returns to 1. That is 3 ticks = 0.12 s at dt 0.04.
- car_UpdateFallState tests counter == 3 (not the state byte). On that tick: rpm and speed damped by 0xFAE1 (0.98), sound 0x405, state 3 or 4 picked by lateral sign. Other ticks: velocity damped by 0xE8F5 (0.91). State 8 is a lateral-slide state.
- Crash trigger resolved: see Resolved (trim pass) item 2.

2. The 1.41
- DAT_0603208c = 0x168F5 = 1.41. Lean angle rec+0x134 = -Atan2(rec+0x124, 1.41). Meaning of 1.41 not recoverable from code (only used as Atan2 divisor).
- Spring-damper error = rec[0xcc] - FixedMul(rec[0xd0], 0x828F (=0.51)) - FixedMul(300.0, rec[0x124]).

3. Slope / drag force
- car_ComputeFixedPolynomial returns mass[slot]*p6 - 0.012*mass[slot]*p5 - drag. 0.012 = 0x312 (786). Drag = 0.0334 (0x88b = 2187) * Cd * v^2. Per-slot mass array at 0x0607910C.
- p5/p6 resolved as the local-frame ground normal y/z, see Resolved (trim pass) item 1.
- car_ApplyScaledOffset multiplies by 9.81 (0x9cf5c) and divides by (mass + 12).

## Resolved (trim pass)
All values read from cd/0.AAA (big-endian, base 0x06010000) and the SH-2 disassembly. Y is down-positive. Bike record rec = 0x0607c480 + slot*0x16c.

### 1. Slope pitch and gravity: step-by-step formula
Per tick, bike_UpdateRacerPhysics (0x0602f7d0), main race path:
1. Rear probe point P2 = (rec.x, rec.y + 0x4f97 raw (0.3109), rec.z) at 0x060301f8-0x060301fc. track_FindPolygonUnderPoint (0x0602e0d4) then track_ComputeSurfaceInfo (0x0602e82c) write the result to rec+0x70. Its fields: normal (A,B,C) at rec+0x80/0x84/0x88, height h2 = groundY - pointY at rec+0x8c, flags rec+0x90.
2. Front probe point P3 = rec position + R(-yaw)*(0, 0.2 [0x3333], 14.0 [0x000e0000]) (vector at 0x0602eb6c); its y is then set to (rec.y + 0.2) + 0x4b50 raw (0.2942). Result goes to rec+0x4c: normal rec+0x5c/60/64, h3 at rec+0x68, flags rec+0x6c.
3. Grounded test on h2 (0x0603030a-0x0603030c): threshold 0x000191d0 = 1.5696 (= 0.16 * 9.81).
   - h2 > 1.5696: airborne. rec+0x148 = 0 and rec+0x28 = rec.y + h2 (ground height shown under the bike) when h2 > 1.0 (0x0000ffff), otherwise rec+0x28 = rec.y. rec.y is NOT changed.
   - h2 <= 1.5696: grounded. If rec+0x148 was 0 (landing): rec+0xf0 = FixedMul(rec[0xd8], rec[0xd0]) (landing impulse; its only reader is car_UpdateLeanBalance, see Resolved (drill pass, 10-13)). Then rec+0x148 = 1, rec.y += h2 (snap to ground, so rec.y = groundY), rec+0x28 = rec.y.
   - rec+0x149 is the previous tick's grounded flag; rec+0x14c counts airborne ticks (0x060307fc-0x060308aa: +1 per tick while rec+0x148 == 0, reset to 0 on the tick after a grounded tick).
4. Target pitch rec+0xb8 (0x06030544-0x06030590):
   - grounded: rec+0xb8 = Atan2( (P2.y + h2) - (P3.y + h3), 14.1 [0x000e1999] ), i.e. rear ground height minus front ground height over a 14.1 baseline. Y is down, so rear lower than front (uphill) gives a positive angle.
   - not grounded but grounded last tick (takeoff): if (h3 - h2) > 0x27fff (2.5) then rec+0xb8 = rec+0xc + 0xe3 (227 = 20 deg on the 0x1000 scale); else unchanged.
   - otherwise unchanged.
5. Pitch easing: rec+0xc += FixedMul(rec+0xb8 - rec+0xc, 0x4ccc [0.3]) (16-bit constant, 0x06030594 area). The same pitch is copied to the racer record at 0x0606ee48 + idx*0x40 + 0xc.
6. Force along the slope (car_UpdateThrottleSpeed 0x06032918, also the AI copy in ai_UpdateRacerSpeedGear 0x06033774): the REAR probe normal (rec+0x80/84/88) is rotated by +yaw (rec+0x10) into the bike frame, giving (nx', ny', nz'); local +z is forward. These go on the stack as p4 = nx' (unused), p5 = ny', p6 = nz'.
   car_ComputeFixedPolynomial (0x06032fb8): F_poly = m*nz' - 0.012*m*ny' - Drag, where m = mass[slot] (array 0x0607910c), 0.012 = 0x0312 raw (786), Drag = 0.0334 [0x088b] * Cd [bike table 0x0606f6d4 + slot*0x20, field +8] * v^2 (car_ComputeDragForce). So the slope/gravity part is m*nz' (the forward component of the unit ground normal, i.e. sin of slope) and the rolling resistance part is 0.012*m*ny' (cos of slope).
   Total F = F_engine + F_poly - F_brake + F_catchup (catchup only when v > 5.0 [0x4ffff]). F_engine and F_brake come from the gear/rpm tables via table_CalcInterpolatedOffset / table_MulEntryField; throttle and brake are 0..1.0 (see item 3 of this section for forced values). Engine force is scaled by 0.9 [0xe666] if rec+0x33 == 1 and 0.6 [0x9999] if rec+0x33 == 3 (0x06032ad8 / 0x06032af8), and divided by |rec+0x110| when |rec+0x110| > 1.0.
7. Speed: a = F * 9.81 [0x9cf5c] / (m + statMass) (car_ApplyScaledOffset 0x06032f58; statMass = bike table field +4); rec+0xc0 = FixedMul(a, 0x0a3d [0.04 s]); speed rec+0x24 += rec+0xc0. Speed floored at 0. Displayed speed = FixedMul(speed, 0x39999 [3.6]) (0x06032c70), capped at 140.0 [0x008c0000] when above 0xd1ffff, with the 70 offset rule above 70.
8. Airborne (rec+0x148 != 1 and rec+0x14c >= 5): no engine/slope force; speed += FixedMul(ApplyScaledOffset(Drag(speed)), 0x0a3d). Only drag acts.
9. Vertical motion: rec.y is not integrated with gravity in bike_UpdateRacerPhysics or car_UpdateRacerMotion (CORRECTED 10-13: rec+0xd8 does hold a per-tick vertical delta plus a gravity step 0x6474 = 0.3924, built in bike_CalcLateralOffsetFromHeading 0x06038428; it is used only for the landing impulse) (0x060314b8; same probe block repeated at 0x060319cc/0x06031b04). 9.81 appears only as the unit factor in item 7. Airborne, rec.y simply stays at its last grounded value (only rec+0x28 follows the ground), and the bike snaps to rec.y += h2 on the next tick with h2 <= 1.5696. Only the visual pitch (item 4, +227 nose-up on takeoff, eased at 0.3/tick) changes in the air.
10. Unknowable from code alone: the sign convention of the course-data normal (n = (P2-P1) x (P0-P1) normalised, polygon winding set by the course files, which I could not parse). Consistency check: the rolling term -0.012*m*ny' must decelerate on flat ground, so ny' > 0 (B > 0) in the rear-probe output; then the slope term acts as +m*nz'.

### 2. Crash trigger (state byte rec+0x2e)
Top of bike_UpdateRacerPhysics, in this order:
- (rec+0xb4 & 0x80) set (head probe on a flag-0x80 polygon): state 2, rec+0x150 = 3.
- else (rec+0x90 & 0x80) set (rear probe): state 2, rec+0x150 = 1. Bit 0x80 is the track polygon attribute copied into probe flags; its meaning is track data (wall-type), not decodable from code.
- else, idx = byte at 0x0606e624[slot]; if byte racerrec[0x0606ee48 + idx*0x40 + 0x31] != rec byte +0x30 (own index) and state != 0: rec+0x154 = 3, state = 3 (crash).
- racerrec+0x31 is written by car_FindNearbyCars (0x0602cb68) with the index of a neighbouring bike when 3*max(|dx|,|dz|) + min(|dx|,|dz|) (integer parts) is < 0x2b (43). It is reset to the own index at the end of each physics tick. So crash state 3 = another bike within a metric of 43 world units. Then car_UpdateFallState (0x060321bc) on counter == 3 picks state 3 or 4 by the sign of the local x of the push vector (<= 0 state 3, > 0 state 4).
- state 8 is set if rec+0x110 != 0 and none of the above applied (lateral slide, ends when rec+0x110 returns to 0).

### 3. Throttle and brake values (car_UpdateThrottleSpeed 0x0603292c-0x0603297e)
Char at 0x06088c0c: 0x11, 0x12, 0x13: throttle 0, brake 1.5 [0x00018000]. 0x0d: throttle 1.0 [0x00010000], brake 0. Otherwise: if word 0x0607ec18 != 0: throttle 0.9 [0x0000e666], brake 0; if 0: both from math_NormalizedShortRatio / _2 (player input).

## Resolved (drill pass, 10-13): course normal sign
- Course collision mesh: L1UNIQUE.RBH block 0 offset 0x1a3c = {vertex ptr, 714 sections, section ptrs} (root reached via track_SetCurrentSection 0x0602e014, globals 0x06079074 / +0xc). Vertex = 3 x s16 (x,y,z), 6 bytes. Section = groups {s16 count, s16 flags, count x 12-byte entries (s16 i0,i1,i2[,i3], ...)}, count 0 ends; flags bit 0x80 = quad group, low bits = surface type 0..3 (counts in L1: 0:3168, 1:3868, 2:128, 3:1680, 0x80:2859).
- Normal (track_FindPolygonUnderPoint 0x0602e0d4) = normalise((V2-V1) x (V0-V1)) into 0x06079078 (A,B,C,D); vec_NormalizeFixed 0x0602e034 keeps the sign; track_ComputeSurfaceInfo copies A,B,C to rec+0x80/84/88.
- Checked over all L1UNIQUE polygons (scratchpad sign.py): every near-flat polygon has B < 0 (8446 tris + 2740 quads, 0 with B > 0). With Y down-positive the normal points UP: B ~ -1 on flat ground.
- Disassembly (ghidra/asm_phys.txt, DumpAsm.java): rotation of rec+0x80 by yaw -> frame+0x184; throttle call 0x0602fa6c passes r6 = nx', r7 = ny', stack = nz' -> polynomial p4/p5/p6 = nx'/ny'/nz'. Confirmed.
- So F_poly = m*nz' - 0.012*m*ny' with ny' ~ -1: the 0.012 term is a small constant FORWARD push (+0.012*m*cos(slope)), not rolling resistance (correction to item 6/10 above). Slope term: uphill (ground rising ahead) tilts the up-normal back, nz' < 0, so m*nz' decelerates uphill and accelerates downhill, as expected.

## Resolved (drill pass, 10-13) - landing impulse and catch-up (Q2, Q3 part)
Landing, rec+0xf0 (bike_UpdateRacerPhysics 0x0602f7d0, write at 0x0603033a):
- rec+0xd0 = per-slot mass, set at init from car_GetRacerValue 0x06032ed0 (array at 0x0607910c; init sites 0x0602f716, 0x060313f2, 0x06034516).
- rec+0xd4/0xd8/0xdc = per-tick displacement vector built in bike_CalcLateralOffsetFromHeading 0x06038428: d4 lateral, d8 = (rec.y - prevY [rec+0x44]) + 0x6474 (0.3924 = 9.81 * 0.04, Y is down-positive), dc forward. car_UpdateSteeringSkid 0x06032450 also adds 0x6474 to d8 (0x06032508). So rec+0xd8 is the vertical speed per tick including one gravity step.
- On the first grounded tick (rec+0x148 was 0, h2 = rec+0x8c <= 0x191d0): rec+0xf0 = FixedMul(d8, d0) = landing impulse (vertical speed * mass). The same code is repeated at 0x06030c92 (unnamed function between 0x06030b3e and 0x06030efc), 0x06031a48 (car_UpdateRacerMotion), 0x06034b08 (ai_UpdatePathFollow), 0x06035dd2 (ai_UpdateRacerRubberBand).
- Only reader of rec+0xf0 is car_UpdateLeanBalance 0x06031f14:
  - 0x0603204c: while grounded (rec+0x148 == 1), rec+0xf0 -= FixedMul(rec+0xd0, 0xa0b = 0.0392) per tick, floored at 0 (decays by mass * 0.0392 per tick).
  - 0x060320b0: r10 = FixedMul(rec+0xf0, 0x41 = 0.001); r4 = r10 - FixedMul(0x1ba5 = 0.1065, rec+0x128); r7 = FixedMul(r4, 0x9425e = 9.29). If r7 >= 0 then rec+0x128 += r7 and rec+0x130 = 0; else a damped branch via rec+0x130 and FixedMul(rec+0x128, 0x161). Both clamped >= 0. So rec+0x128 is a spring-driven suspension compression (squat) displacement kicked by the landing impulse.
- Consumers of rec+0x128 (via car_GetRacerFieldClamped 0x06032ce4, clamp 12.5 = 0xc8000): the bike/rider draw functions (bike_DrawRiderModel 0x0602aef8, bike_DrawBikeWithShadow 0x0602b1ac with FixedMul(clamped, 0x6664 = 0.4) as translate Y, bike_DrawModelParts and variants, also 0x0603bcfc, 0x0603c17a, 0x060395ec) and cam_UpdateByState (0x0602d518, 0x0602d570: camera Y translate in the first-person states).
- Verdict: visual suspension bounce of body, rider and first-person camera. No speed loss (rec+0x24 untouched) and no sound found. [guess] the impulse is not fed back into the physics.

Rubber band, car_ComputeCatchupBonus 0x060330e0 (called at 0x06032a3e in car_UpdateThrottleSpeed 0x06032918 only when speed rec+0x24 > 0x4ffff = 5.0):
- Returns 0 for the leader (rank byte +0x32 == 0) or when (*0x0607d008 & 2). Otherwise the rival is the racer one rank ahead. If abs(Atan2(dx, dz) + rec[0x10]) <= 0xC3 and distance (vec_DistanceScaled 0x060332d8) is within 600.0 (0x2580000): bonus = FixedMul(600.0 - dist, (0xC3 - angle) * 100), capped at 0x500000 (80.0). It is added to the forward force (F = engine + poly - brake + catchup).
- Applies to every non-leader bike, player and AI, and grows when the bike ahead is close and dead ahead: a draft/catch-up pull toward the bike in front, not a rank-gap table. The old "only if speed > 80.0" was wrong (80.0 is the cap).
