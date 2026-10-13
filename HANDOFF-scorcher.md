# Manx TT Super Bike (Saturn) decompile: handoff to the Scorcher chat (2026-10-13)

The user asked: "after you get the handling system fogured out pass it to the scorcher chat please".
For reference and ideas only; nothing here needs doing in Scorcher.

## State
- Project: C:\Users\john\Documents\ManxTT (NOTES.md is the log). Program 0.AAA, SH-2, base 0x06010000.
- Names: ghidra\hand_0.txt (1204 functions, 0 FUN_). Full C: ghidra\decomp_0.c (each function starts `// ==== <name> @ <addr>`).
- Public repo: github.com/indieindie7/manxtt-decomp (names, notes, tools; no game data).
- Study reports (read these, they have the numbers): ghidra\study\study_handling.md, study_ai_camera.md, study_archive.md
  study_chasecam.md: cam_UpdateByState 0x0602d2c8, offset (0,-4,-26) from pivot (0,-12,+7), yaw lag 1/8, pitch lag 1/18, speed>>3 pull-back.

## Handling in short (study_handling.md)
- Per racer per tick, bike_UpdateRacerPhysics: state switch (rec+0x2E) -> car_UpdateThrottleSpeed 0x06032918 ->
  bike_UpdateGear 0x06037728 -> car_UpdateHeadingAngle 0x06032714 -> car_UpdateLeanBalance 0x06031F14 ->
  car_UpdateSteeringSkid 0x06032450; bike_UpdateSteeringTorque 0x060384CC feeds them; then
  bike_SubstepMoveCollide 0x06037238 (10 substeps), front/rear ground probes, car_UpdateFallState 0x060321BC,
  race_UpdateCheckpointLap 0x0603A710.
- Units: dt 0.04 s (one tick per frame; PAL 25 Hz), 9.81 is only a kgf-to-newton unit factor, 16.16 fixed point, 12-bit angles.
- Speed: real-ish physics. a = F * 9.81 / (mass + 12); mass 237 + 60 rider. Engine force = torque curve[rpm/100]
  x gear ratio (2.4, 1.94, 1.63, 1.43, 1.29, 1.19) x per-gear efficiency; drag Cd (0.502 / 0.3765) x v^2;
  brake 437..618 kgf per bike. Top speed is emergent, not stored.
- RPM 1300..15000, eased toward target (0.54 falling / 0.67 rising), free-revs in the air.
  Gears: up at 13000, down at 10000, 26-tick shift delay.
- Steering: cubic input shaping, scaled down with speed, clamp +-0x1A. Steer drives a lean spring-damper
  (spring 300, damping 0.51); lean angle = -atan2(displacement, 1.41) turns the heading. Heading vs course clamped
  +-73 deg; self-centring on lateral velocity; steer decays 0x22/tick when released.
- No tyre model: slip angle only drives skid sound.
- Ground: two probes give pitch over crests; airborne above a 1.57 gap. Position Y is not integrated with gravity in the air: height holds and snaps back to the ground (see "Slope pitch and gravity" below).
  Landing (drill pass): rec+0xd8 tracks vertical delta + a 0.3924 gravity step; on the first grounded tick rec+0xf0 = d8 x mass,
  read only by car_UpdateLeanBalance, which decays it (mass x 0.0392/tick) and drives a squat spring rec+0x128 used by the
  bike/rider draw offset and first-person camera Y. Visual suspension only: no speed loss, no sound.
- Off-road: surface byte rec+0x33, type 1 speed x0.9/tick, type 3 x0.6/tick.
- Walls: a failed substep reverts the position and zeroes speed (no bounce).
- Crash states 3/4 damp 0.98/tick (else 0.91); recovery counter rec+0x154 = 3 ticks (0.12 s), then back to state 1.
- Bike stat table 0x0606F6D4, stride 0x20: mass, 12.0, Cd, steer factor, brake, torque-curve ptr, ratios ptr, efficiency ptr.
- Checkpoints table 0x0606F1FC (0x18 each, 0x60 per course); time extend = table value x 25 ticks.

## AI, ghost, camera (study_ai_camera.md)
- Rubber band: ai_SelectSpeedTarget 0x06034E80, 29-entry {base, slope} speed table keyed on rank gap; AI uses
  the player's engine model but its own shift points (14000 up / 7000 down vs the player's 13000 / 10000); collision shoves decay 1% per frame; speed table at 0x0606EAAC (3 used sets x 29). Direction (drill pass): reference = the bike one rank ahead (leader uses
  the player); gap = ownRank - refRank; behind -> multiplier 1.10..1.23 (set 0, up to 1.98 in set 2), ahead -> 0.925..1.1
  (default 0.9). car_ComputeCatchupBonus 0x060330e0: pull toward the bike ahead within 600 units, capped 80.0, for every
  non-leader bike (player too), speed gate 5.0 in the caller.
- Ghost: one 0x18-byte sample per frame (no decimation, max 3000), delta-packed to 8 bytes, 0x14-byte header + checksum,
  saved only on a new best, double buffer swapped at lap change.
- Timing (drill pass): race frame divider 2 = one physics tick per rendered frame (30 fps NTSC / 25 fps PAL), no dt
  compensation, so dt 0.04 is exact only on PAL.
- Camera (study_chasecam.md): cam_UpdateByState 0x0602d2c8 drives it per frame on 0x188-byte per-player records;
  states: 2 first person (default), 3 near chase (also the far result cam), 4 a 7-frame roll/blend step back to 2,
  5 intro flyover, 6/0xe finish look-at cut. View button 2 -> 3 -> 4 -> 2, so in practice first person <-> chase; yaw lag 1/8, pitch lag 1/18,
  state 3 pulls back by speed>>3; roll follows lean in first person. camera_TaskHandler 0x0604D1D0 is only the viewport.

## Ideas for Scorcher
- Steer -> lean spring-damper -> heading is the core of the feel; Scorcher's car_ApplyControls could borrow the
  cubic input shaping + speed-scaled steer clamp.
- 10 collision substeps per tick against tunnelling; two ground probes for pitch.
- Rubber band both ways: trailing AI speeds up, leading AI eases off; plus a capped pull toward the bike ahead.
- rpm easing with hysteresis gives engine audio that sells speed.

## Archive (bonus)
CDIMAGE.ELF = 16-byte header + 147-entry TOC {hash, sector, size, sectors}, 2048-byte sectors, name hash h=2h+c,
no compression. tools\elfarc.py lists/extracts it.

## Slope pitch and gravity (trim pass, 10-13; study_handling.md "Resolved (trim pass)")
Y is down-positive; rec = 0x0607c480 + slot*0x16c; all in bike_UpdateRacerPhysics 0x0602f7d0 except forces (car_UpdateThrottleSpeed 0x06032918).
1. Rear probe P2 = (x, y + 0.31, z) -> surface normal rec+0x80..88, height gap h2 = groundY - pointY (rec+0x8c).
   Front probe P3 = pos + R(-yaw)*(0, 0.2, 14.0) -> normal rec+0x5c..64, gap h3 (rec+0x68).
2. Airborne if h2 > 1.5696: grounded flag rec+0x148 = 0, y unchanged. Else grounded: y += h2 (snap), flag 1.
3. Target pitch: grounded = atan2((P2.y + h2) - (P3.y + h3), 14.1) (rear minus front ground height over the 14.1 wheelbase; uphill positive).
   On takeoff, if h3 - h2 > 2.5: target = pitch + 227 (about 20 deg nose-up kick).
4. Pitch eases 30%/tick: pitch += 0.3 * (target - pitch).
5. Slope force: rotate the rear-probe normal by +yaw into the bike frame (+z forward) = (nx', ny', nz').
   F_poly = m*nz' - 0.012*m*ny' - 0.0334*Cd*v^2 (m = rider+bike slot mass; m*nz' = gravity along the slope). The course normal points UP (ny' ~ -1 on flat), so the 0.012 term is a small constant FORWARD push, not rolling resistance (drill pass).
6. F = F_engine (x0.9 / x0.6 on rough / grass) + F_poly - F_brake + F_catchup; a = F * 9.81 / (m + 12); speed += a * 0.04, floor 0.
7. Air: no gravity integration. After 5+ airborne ticks only drag acts on speed.
Sign RESOLVED (drill pass 10-13): checked over every L1UNIQUE collision polygon, all flat ones have ny < 0 (up, Y down-positive); uphill gives nz' < 0 so m*nz' decelerates uphill.

## Models (models pass + open items, 10-13; study_models.md "Resolved" sections)
- Player bike: the livery RBH root = {57 v body, 32 v low LOD, 4 v far card}; drawn after T(0,-3,0) and Scale 0.25 on the bike matrix.
  Wheels = TYRES root[LOD] front at (0, 0.8, 56.4) in the scaled frame (wheelbase 14.1), root[LOD+2] rear at origin, RotX spin per player.
  TYRES 4/5 = high-detail wheels for the attract-mode bike only.
- Player rider: PRIDERS rows = per-livery skins (bikeSel*2+LOD while racing, bikeSel+0x18 on grid/attract/results), 11-part skeleton,
  12-bit angles, M = parent*T*Rz*Ry*Rx. RIDER_M clip 1 = lean (15 keys keyed by roll, key 7 upright), clip 2 = idle at speed <= 0.3,
  clip 3 = finish (leading human only); clips 0/4 unused.
- Rival riders (ERIDERS): no skeleton; rigid pre-posed meshes swapped by roll: 5 steps close (+-15 / +-30 deg), 3 mid, 1 far; 4 skins x 8 rows.
  Cheap trick worth copying: swap baked lean poses instead of animating.
- Tools in the repo: tools/rbh2obj.py (RBH -> OBJ), tools/riderpose.py (pose a rider on the bike), tools/objview.py (4-view render).

## Guess dig (10-13)
- Disc is PAL (area E, 1997-02-17), so dt 0.04 s per tick is exact.
- AI rec+0xa0 = per-rider pace handicap 1 (fastest) .. 7, subtracted (x 0.02..0.06 slope) from the AI target speed in ai_SelectSpeedTarget.
- Camera states 0/1/7/0xe are unreachable; only 2 (first person) and 3/4 (chase) are used in play.

## Status
Manx TT is DONE: 1204 functions named, 0 provisional, all studies settled (one unused sound bank left as a guess).
Repo github.com/indieindie7/manxtt-decomp. Nothing here needs doing in Scorcher; take what helps.
