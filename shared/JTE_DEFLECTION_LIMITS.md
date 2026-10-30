# JTE deflection and drift limits

Source: `S:\02_Design\01_JTE Standards\Design Standards\Loads and Deflections\Deflections.pdf`
(3 pages, dated 2026-03-24 on the drive). The PDF controls; this is a working
summary for the agent. Product-neutral: RAM Concept slabs, RAM Modeler and RAM
Steel beams, and RAM Frame drift all read from it.

## Ground rules

- Limits assume simply supported members. **Cantilevers: multiply the
  allowable deflection by 2** (L/240 becomes L/120 on the cantilever length).
- Gravity deflections use service loads (ASD).
- LL = live load deflection. TL = total load deflection.
- Where a ratio and an inch cap are both given, the smaller governs.

## Concrete (RAM Concept slabs)

| Check | Limit | Concept plan (load history step) |
|---|---|---|
| Immediate LL | L/360, and 3/4 in max at exterior conditions | Immediate LL |
| Long-term TL minus initial DL | L/240 | Sustained + Immediate LL minus DL Attachment |
| Same, perimeter spans | L/480 | same plan, at the slab edge |
| Supporting brick or CMU | immediate TL L/600 or 0.5 in | the immediate total load plan |
| Long-term deflection, absolute | **2 in, regardless of the initial DL deflection** | Sustained + Immediate LL, nothing subtracted |

The 2 in cap is the one the slab options workflow calls "max deflection shall
not exceed 2 in": total long-term, read on the Sustained + Immediate LL plan
(see `ram-concept/references/RAM_CONCEPT_SLAB_OPTIONS.md`).

## Residential (wood and steel beams, joists)

| Member | LL | TL |
|---|---|---|
| Beam, L < 30 ft | L/360, 1/2 in max | L/240, 3/4 in max |
| Beam, L > 30 ft | L/360, 3/4 in max | L/240, 1 in max |
| Floor joist | L/480 | L/240 or 0.75 in; TJI Pro rating above 50 |
| Under a NanaWall | L/720 or 0.25 in | |

Any member supporting brick or masonry: L/600 or 0.5 in.

## Existing buildings

Beam supporting existing flooring or framing above: TL L/400, 3/8 in max.

## Steel commercial

| Member | Limit |
|---|---|
| Noncomposite beam | LL L/360; TL L/240 or 1.5 in |
| Supporting brick or masonry | TL L/600 or 0.5 in |
| Composite, initial (construction dead load) | L/360 or 0.75 in |
| Composite, post-composite live | L/360 |
| Composite, post-composite superimposed | L/240 |
| Composite, net total | L/240 or 1.5 in |

## Other gravity

- Glass: LL L/360; L/480 where it is a concern.
- Members supporting masonry: TL L/600 or 0.5 in. Masonry out of plane: L/150.
- NanaWall: vertical TL L/720 or 0.25 in. Out of plane TL L/360 or 3 in,
  drift H/40 (2.5 percent), 5 psf (1.0 x 5 psf ASD) interior lateral pressure.

## Lateral: components and cladding

| Finish or wall | Limit | Load for the check |
|---|---|---|
| Flexible finishes (metal panel, siding), stud walls | L/120 | 0.42W (L/84 with 0.6W) |
| Sheetrock walls | L/360 | 0.42W (L/252 with 0.6W) |
| Glass, L < 13.5 ft | L/175 | 0.6W C&C |
| Glass, L > 13.5 ft | L/240 + 1/4 in | 0.6W C&C |
| Brick | L/600 | 0.42W (L/420 with 0.6W) |
| Masonry | L/150 unless another finish governs | 0.42W (L/63 with 1.0W) |
| NanaWall | L/360 or 3 in, drift H/40 | 5 psf interior |

Every wall is checked for both its interior and its exterior finish.

## Lateral: main wind force resisting system (RAM Frame drift)

- Checked as story drift: a floor's deflection minus the floor below.
- Wind drift at the building corners; seismic drift at the building centre.
- Steel: no reduced stiffness for the deflection checks.
- **Wind:** serviceability 0.6W combinations for quick calcs (wind speed for
  the risk category), the 50-year MRI wind speed in RAM's drift provisions,
  or 1.0D + 0.5L + 0.7W for ASCE 7-05. Brittle finishes (brick, stucco, CMU
  finish, plaster, stone) H/600; flexible finishes H/400.
- **Seismic:** use 1.0E even for an ASD design; for steel, reduce loads
  through the drift provisions. Allowable story drift:

| Structure | Allowable drift |
|---|---|
| Masonry | 0.007 h Ie / Cd |
| Other, risk category I or II | 0.020 h Ie / Cd |
| Other, risk category III | 0.015 h Ie / Cd |
| Other, risk category IV | 0.010 h Ie / Cd |

The standard writes L for the story height; h is used here. RAM Frame notes:
`ram-structural-system/references/RAM_FRAME_NOTES.md` (drift at control
points, 1.0E and 0.6W combinations).
