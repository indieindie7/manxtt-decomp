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
- Rubber band: car_ComputeCatchupBonus: only if speed > 80.0, range 600.0, angle <= 0xC3, bonus capped 80.0, never for the leader. Trailing AI/players get a push (guess: applies to AI mostly).

## 3. Steering and lean
- bike_UpdateSteeringTorque (@060384CC): input shaped by a cubic (fine control near center), scaled down with speed, clamped to +-0x1A, multiplied by 56.4 then 0.04.
- car_UpdateHeadingAngle (@06032714): heading relative to the course clamped to +-0x33C (about +-73 deg). Self-centering: MulHigh(rec+0x110, 0x4B4F). Steer input decays 0x22 per tick when released.
- car_UpdateLeanBalance (@06031F14): a spring-damper on lean displacement: spring 300.0, damping 0.51. Lean angle = -atan2(rec+0x124, 1.41) (the 1.41 is the effective lever height, guess). So the bike leans against the lateral displacement, and the lean angle turns the heading (steer comes through lean, not directly).
- Counter-steer feel (guess): because input drives a spring-damper lean and lean drives heading, there is a short lag then a settled turn, and releasing returns by spring plus the self-centering term.
- car_UpdateSteeringSkid (@06032450): slip = atan2(lateral, forward); above 0x400 (90 deg units: threshold is large, effectively only in real slides) it triggers skid sound by frame mask.

## 4. Gravity, jumps, ground following, slopes
- Two probes: front (rec+0x4C) and rear (rec+0x70) via track_FindPolygonUnderPoint + track_ComputeSurfaceInfo.
- Airborne if the height offset above the surface > 1.5696 (0x191D0). Grounded byte rec+0x148, air counter rec+0x14C.
- Pitch is eased toward the surface slope from the two probes (so the bike pitches over crests); while airborne gravity 9.81 integrates vertical speed.
- Slopes: gravity component along the surface adds/subtracts from speed (guess; the chain includes a pitch term in the force).

## 5. Grip / slide
- No tire model per se; lateral velocity rec+0x110 is damped by self-centering (0x4B4F factor) and slip angle is only used for sound/effects. Slides are visual/audio, not a separate friction regime (guess).

## 6. Off-road and grass
- Surface type byte rec+0x33. Type 1 multiplies speed by 0.9 per tick (rough/edge), type 3 by 0.6 (grass/gravel: heavy slowdown). Other types normal.

## 7. Collisions
- Wall/barrier: bike_SubstepMoveCollide splits the move into 10 substeps; on a failed substep the position reverts, speed is set to zero, byte +0x2F is decremented, rubber-band pointer reset.
- Rider-rider: car_FindNearbyCars threshold 0x2B (proximity); response goes through the same substep path (guess).

## 8. Crashes / falls
- State byte 3/4 = crash with a recovery counter; car_UpdateFallState (@060321BC) damps with 0.98 per tick in states 3/4, otherwise 0.91. Crash sound when speed*0.62137*90 (high part) > 5. State 2 is normal driving with an after-effect (damp 0.98). Recovery duration: counter value not decoded (guess: about 1-2 s).

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
