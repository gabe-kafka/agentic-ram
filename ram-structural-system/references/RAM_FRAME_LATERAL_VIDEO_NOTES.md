# RAM Frame lateral analysis: lessons from two Bentley webinars

Notes for the RAM Frame lateral skill for ordinary concrete shear wall
buildings. Read with `RAM_FRAME_NOTES.md` (verified GUI lessons). These are
notes in our words with timestamps, not transcripts; the full auto-captions are
on each video's YouTube page (Show transcript).

Sources (both Allen Adams, Bentley RAM chief engineer):

1. *Understanding Building Drift Code Requirements using RAM Structural
   System*, Dec 2014 webinar, ASCE 7-10 -
   https://www.youtube.com/watch?v=-FP5z-6E2fY (53 min).
2. *Performing an Accurate Lateral Analysis with RAM Structural System*, Tech
   Talk with Q&A - https://www.youtube.com/watch?v=Au8K9pQxe7g (56 min).

Menu paths marked **(manual)** were checked against the installed
`RAMFrame.pdf` (V25), not yet clicked. Code sections are the video's ASCE 7-10
numbers; check them against the job's code edition (2612_08 is ASCE 7-16).

## Video 1: drift

### Terms (2:00)

- Displacement: how far a point moves under the load.
- Story drift: displacement at a level minus displacement of the same plan
  point on the level below.
- Drift ratio: story drift / story height. Work in drift ratios: one limit
  for every story regardless of height.
- RAM Frame drift reports list **elastic** values (delta_xe), never amplified
  by Cd (manual: "The resulting reported drifts are not factored by Cd").

### Seismic forces for drift are allowed to be smaller (4:00-9:00)

Two relaxations apply only to forces used for drift, never for member strength:

- The minimum Cs (eq. 12.8-5) need not be met for drift (12.8.6.1 exception);
  eq. 12.8-6 still applies where S1 is high.
- The period cap T <= Cu*Ta does not apply for drift (12.8.6.2): use the
  computed (eigen) period, which gives a lower Cs cap.

In RAM Frame this is the seismic load case option **Provisions for: Member
Forces / Drift** (manual 6.3.1.10, "the limit imposed on T is removed if
analysis is carried out for story drift"). Drift-provision cases are
unconservative for strength; strength cases are conservative for drift.

Adams' advice: for moment frames build both sets, since drift sizes the
members. **For shear walls and braced frames drift rarely controls, so check
drift with the strength seismic cases and skip the second set** unless that
check fails.

### Where drift is measured (10:00-13:00)

- At the center of mass (CM) of each level, against the point vertically
  below it on the level below; not CM-to-CM when the CMs move between floors.
  If the CMs are close and rotation is small, one representative point is
  acceptable.
- Torsionally irregular buildings (Type 1a/1b): the worst drift at any edge
  point, including diaphragm rotation (ASCE 7-16 12.8.6: SDC C-F with 1a/1b).

### Torsional irregularity and Ax (13:00-15:00)

- At each floor, drift at the two extreme ends: max / average > 1.2 is Type 1a
  (torsional), > 1.4 is Type 1b (extreme). To call a building regular, check
  every story, both directions.
- If 1a/1b, amplify the 5% accidental eccentricity by
  Ax = (delta_max / 1.2 delta_avg)^2, 1.0 <= Ax <= 3.0 (eq. 12.8-14), per level
  and per direction (do not swap X and Y).
- **RAM Frame does not apply Ax** (manual 6.3.1.9: "Equation (12.8-14) is not
  enforced"). Compute it by hand and enter the larger eccentricity in the
  seismic load cases.
- RAM support: **Results > Drift > At Control Points** with at least two
  control points prints a Torsional Irregularity section (max/avg) for seismic
  and response spectrum cases (manual 3.6.13). Put control points at the
  extreme corners.

### Design drift and the elastic limit (15:00-19:00)

- Design story drift: Delta = Cd * delta_xe / Ie (12.8.6).
- Limits: Table 12.12-1. Typical: 0.020 h_sx for "all other structures"
  (Risk Cat I/II), 0.015 (III), 0.010 (IV); 0.025 h_sx only for buildings of
  4 stories or less with partitions and cladding detailed for drift.
- Shortcut: an **elastic drift ratio limit** = limit * Ie / Cd, compared
  straight against the RAM report. With different systems in X and Y, one
  elastic limit per direction.
- Video example: special RC shear wall, Cd = 5 (steel SMF Cd = 5.5).
- Ordinary RC shear walls (ASCE 7-16 Table 12.2-1, check before use): bearing
  wall system A.2: R = 4, Omega0 = 2.5, Cd = 4; building frame system B.5:
  R = 5, Omega0 = 2.5, Cd = 4.5. Permitted in SDC B and C only.
  With 0.020 and Ie = 1.0: elastic limit 0.0050 (Cd 4) or 0.0044 (Cd 4.5).

### P-delta and stability coefficient (19:00-22:00)

- theta = Px * Delta * Ie / (Vx * h_sx * Cd) (12.8-16). Delta*Ie/Cd is the
  elastic drift RAM reports, so use it directly. theta <= 0.10: P-delta may be
  ignored.
- theta_max = 0.5 / (beta * Cd) <= 0.25 (12.8-17). Over it: unstable,
  redesign (more stiffness).
- If P-delta is included in the analysis, compare theta / (1 + theta) against
  theta_max.
- Adams: include P-delta in every analysis regardless of theta.
- RAM: **Criteria > General, P-Delta Yes** (manual 3.1.1.2); theta and
  theta_max are in the **ASCE 7 Stability Coefficients** report (manual
  6.3.1.11).

### Wind drift (22:00-27:00)

- No code limit; office choice (common H/500 = drift ratio 0.002; H/400 is
  also used). Some offices use a lower-return wind for drift.
- Measure wind drift at the building corners, not at the CM.
- **Office rule (engineer, 2026-10-19): wind drift ratio <= 1/600 = 0.00167
  at the worst-case corner, every story.** Each story passing keeps the roof
  within H/600 too. **Checked under 0.6W** (the ASD level of the ASCE 7-16
  strength wind).
- How in RAM (manual 4.1, not yet clicked): **Mode > Analysis > Load
  Combinations**, then **Combination > Custom Combinations**. Make one
  combination per wind case, factor 0.6. Signs do not flip on their own, so
  add a -0.6 row where needed. Click **Validate**, tick **Use**, then
  **Results > Drift > At Control Points** reads the 0.6W drift against
  0.00167 directly. Custom combinations add up results already solved, so
  there is no re-analysis.
- Torsionally regular under wind (26.2): case 2 (3/4 wind + torsion) never
  displaces any point more than case 1. Then Appendix D lets you drop cases 2
  and 4 (12 wind cases down to 4). You must run case 2 once to show it.
  RAM labels in the video: W1 = case 1 X, W2 = case 1 Y, W3-W6 = case 2
  permutations.

### Steel only (27:00-29:00)

AISC 360 direct analysis stiffness reduction (0.8 tau_b) is for strength, not
drift or periods. Not relevant to concrete walls; leave it off.

### RAM Frame demo (30:00-52:00)

Steel building, but the commands are the same.

1. Analysis criteria for the drift run: gravity, seismic drift cases and
   wind cases; skip strength seismic and notional cases.
2. Drift report at control points: the CM of each level plus the four
   extreme corners (the video shows 8; the manual says up to four control
   points, so check the installed version). **Results > Drift > At a Point**
   picks any plan point (manual).
3. Filter load cases in the report. Dead/live drift was negligible, so drop
   it.
4. Wind: read the corner points against 0.002. Seismic: read the CM points
   against 0.025/5.5 = 0.0045.
5. Failing stories go to the **Drift Control** module (virtual work):
   - Virtual load case per failing story: **Loads > Load Cases**, type
     Virtual, a nominal force in the drift direction at that story's CM. The
     manual suggests 20-50% of base shear.
   - Analyze the gravity, seismic drift and virtual cases.
   - **Mode > Drift Control**, **Loads > Load Pairs**: real seismic case +
     virtual case, factor 1.0; **Process > Analyze**.
   - Members colored by participation; "displacement per volume" ranks
     stiffness-for-material.
   - **Process > View/Update** on a member splits its participation into
     axial / shear / flexural / joint / connection. That says which property
     to grow: area if axial shortening dominates, I if flexure dominates.
6. Resize, reanalyze, read drift again; repeat until it passes. Then rerun
   everything and recheck wind, theta and the strength checks.

The manual's Drift Control chapter talks about beams, columns and braces only.
Whether walls get participation factors is untested.

## Video 2: accuracy (Tech Talk)

- **Basic FE results agree across programs** (2:00-10:00). RAM Frame, STAAD
  and another big program gave periods within 0.004 s, the same total
  reactions and the same column forces. A semi-rigid meshed two-story model
  matched to 0.0005 s. Mode shapes with flipped signs are equivalent.
  Differences come from the special options: P-delta, live load reduction,
  response spectrum. To trust a model, run it once with those off and check
  periods and total reactions against a hand number.
- **Mesh size** (10:00-13:00). A finer mesh on a wall or diaphragm spikes
  local shear at stress concentrations; a single tiny element is not a design
  value, because the concrete spreads that stress. Use a regular, moderate
  mesh and spread the force over a realistic width. RAM: **Criteria >
  General**, Max. Distance between Nodes on Mesh Line. It drives both the wall
  and diaphragm mesh; the manual says coarse is stiffer.
- **P-delta lengthens the period** (13:00-17:00). 1.590 s with P-delta and
  1.532 s without, in his example.
- **RAM uses a non-iterative geometric stiffness P-delta.** It softens the
  structure once from the total factored gravity load (e.g. 1.2D + the live
  factor of the governing seismic combination, with live load reduction). So:
  - P-delta stays in response spectrum analysis. An iterative P-delta program
    has to drop it in RSA.
  - Load cases stay separate and are combined later in each design module
    (Frame, Concrete, Foundation).

  Gravity loads are used here because seismic up- and down-loads cancel over
  the whole building.
- **RSA with and without P-delta** (16:00-22:00). Base shear about 156 vs 149 kips
  in his example (captions garbled), and member forces moved by different ratios. Scaling to ELF
  does not fix the distribution. Base shear can rise with P-delta when the
  softer building moves closer to a resonant mode.
- **Without P-delta in the analysis**, magnify moments per story by B2 (AISC)
  or the ACI sway magnifier delta_s. It is often 1.04-1.08; at 1.15-1.2 or
  more, stiffen the building. It is calculated story by story.
- **Precision vs practicality** (24:00-30:00). Common W shapes jump about 12%
  in capacity and bar sets about 3-40% in area. Be right, not falsely precise;
  a bias that is always 5% one way is still a bias.

## RAM Frame facts from the manual that matter for concrete walls

- **Crack factors** for walls are set in **RAM Modeler** (membrane/in-plane
  and bending/out-of-plane). Frame applies them (manual 6.6). Bentley calls
  them strength values; service combinations take one modifier in **Load
  Combinations mode, Criteria > Advanced Analysis** (manual 4.1). The office
  values are still to be chosen. ACI 318-19 Table 6.6.3.1.1 gives cracked
  walls 0.35 Ig and uncracked 0.70 Ig; 6.6.3.2.2 allows 1.4x for service
  lateral deflection (not from the videos; check).
- **P-delta options** (Criteria > General): Use Mass Loads (default, with a
  factor up to 10) or Use Gravity Loads (separate D/L factors).
- **Semi-rigid P-delta ("Preliminary P-Delta")** takes axial force from
  **columns and braces only** inside the diaphragm (manual 7.16.2). **Open:**
  check on 2612_08 whether a wall-only building gets any P-delta softening
  (period and drift with P-delta on and off).
- **Drift on a semi-rigid diaphragm** is computed from averaged nodal
  displacements within the diaphragm boundary (manual 3.6.13). On a rigid
  diaphragm it includes rotation about the CM.
- Wall mesh, semi-rigid meshing and shell-warning handling: see
  `RAM_FRAME_NOTES.md`.

## Draft workflow for the skill (not yet run on a job)

Engineer decides first: SDC and risk category (Ie); bearing wall vs building
frame (R, Cd); wall crack factors; P-delta load source and
factors.

1. Work on a copy of the `.rss`. Walls are Lateral in Modeler
   (`RAM_FRAME_NOTES.md`).
2. Criteria: diaphragm (semi-rigid office default), Ground Level, P-Delta Yes
   with its load source, mesh distance.
3. Seismic: ASCE 7 ELF cases X/Y with +/-5% eccentricity, Provisions for
   Member Forces. Add Drift cases only if the wall drift check fails.
4. Wind: ASCE 7 cases (12); after one run, Appendix D may cut them to 4.
5. Analyze. Sanity check: total D and L reactions against a takeoff,
   periods, story shears and mass.
6. Torsion: control points at the extreme corners, Torsional Irregularity
   section, Type 1a/1b, Ax by hand, rerun with the amplified eccentricity if
   needed.
7. Seismic drift (CM, or edges if 1a/1b in SDC C+) against limit * Ie / Cd.
8. Wind drift at the worst-case corner, each story: custom 0.6W
   combinations against 0.00167 (Load Combinations mode, Results > Drift).
9. ASCE 7 Stability Coefficients report: theta / (1 + theta) <= theta_max.
10. If drift fails: Drift Control (virtual load per failing story), then
    thicken or lengthen the walls the module points to.
11. Then RAM Concrete wall design (`RAM_FRAME_NOTES.md`, "After a clean Frame
    run").
