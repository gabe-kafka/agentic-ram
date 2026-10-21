# Bentley RAM RSS archive map

This is an evidence-based map of Bentley RAM Structural System 2025 `.rss`
files. The format is proprietary and undocumented. Treat every offset here as
version-specific until it is reproduced on another RAM release.

The map was built from controlled one-change model diffs, RAM UI/member-report
validation, archive count reconciliation, and successful reopen/Data Check
cycles. It is not derived from Bentley source code.

## Safety boundary

- An RSS is a ZIP archive containing one model-named member for each internal
  extension.
- Read-only inspection is safe while RAM has the model open, but a mutation
  workflow must operate on a closed saved copy.
- Never overwrite the source RSS.
- Preserve archive member names, order, ZIP comment, and unchanged payloads.
- A structurally consistent ZIP is not sufficient proof of a valid RAM model.
  Open only the generated copy and run RAM Data Check.

## Confidence labels

- **Confirmed**: reproduced through controlled changes and reconciled against
  RAM UI or reports.
- **Strongly inferred**: multiple independent record/count relationships agree,
  but a single-field controlled probe has not isolated it.
- **Unknown**: observed but not safe to interpret or mutate.

## Confirmed fixed-record members

| Member | Record size | Confirmed role |
| --- | ---: | --- |
| `.flt` | 472 bytes | Floor/layout type metadata and array ranges |
| `.sty` | 336 bytes | Story Data metadata and story member ranges |
| `.c3d` | 1072 bytes | Layout column records |
| `.w3d` | 584 bytes | Layout wall records |
| `.sec` | 184 bytes | Concrete column-section definitions |
| `.lpt` | 72 bytes | Surface, line, then point load properties |
| `.lod` | 20 bytes | Placed-load metadata |
| `.pol` | 16 bytes | Shared XY coordinate pool |

The `.ram` member is XML-like text. Field payloads are hexadecimal bytes, most
often little-endian 32-bit integers or floats. Field names are more stable and
safer to use than byte positions inside `.ram`.

## Global `.ram` relationships

Confirmed fields include:

| Field | Relationship |
| --- | --- |
| `NumFlrTypes` | Number of 472-byte `.flt` records |
| `NumStories` | Number of 336-byte `.sty` records |
| `nNumGravColumns` | Gravity-column subset represented by `.sty` |
| `nNumGravWalls` | Gravity-wall subset represented by `.sty` |
| `NumSLoadProps` | Leading surface-property records in `.lpt` |
| `NumLLoadProps` | Following line-property records in `.lpt` |
| `NumPLoadProps` | Trailing point-property records in `.lpt` |
| `nNumConcDeckProps` | Number of concrete deck/slab properties |
| `NumConcColSections` | Number of concrete column sections |
| `lNumConcCols` | Number of concrete columns |
| `bModelHasSteelColumns` | Global steel-column presence flag |

For a healthy model:

```text
len(.lpt) / 72 =
    NumSLoadProps + NumLLoadProps + NumPLoadProps
```

## `.flt` floor/layout record

Confirmed offsets are relative to each 472-byte record:

| Offset | Type | Meaning |
| ---: | --- | --- |
| 0 | C string | Layout label; stop at the first NUL |
| 24 | `u32` | Column count |
| 28 | `u32` | Wall count |
| 32 | `u32` | Beam count |
| 52 | `u32` | Surface-load placement count |
| 56 | `u32` | Line-load placement count |
| 60 | `u32` | Point-load placement count |
| 76 | `u32` | Starting column record index |
| 80 | `u32` | Starting wall record index |
| 84 | `u32` | Starting beam record index |
| 288 | `u32` | Column label/counter metadata |
| 292 | `u32` | Next wall label/counter metadata |

Counts and starts describe contiguous blocks in their corresponding member
arrays. Moving a whole block requires updating all affected later starts, the
matching `.sty` ranges, and relevant `.ram` totals. This is why the repository
merge skills only support narrow validated arrangements.

Additional observed `.flt` values are not yet mutation-safe:

- offset 36 tracked 164 slab-related objects in the validation model;
- offset 44 tracked 26 wall openings and agreed with `.opn / 48`;
- offset 48 tracked one deck/slab assignment;
- offsets 64 and 68 tracked edge/node-like geometry totals.

These are **strongly inferred**, not confirmed field names.

## `.sty` story record

| Offset | Type | Meaning |
| ---: | --- | --- |
| 0 | `u32` | Story number/order |
| 4 | C string | Story label |
| 28 | `f32` | Story height in inches |
| 52 | `u32` | Column count |
| 56 | `u32` | Wall count |
| 60 | `u32` | Beam count |
| 168 | `u32` | Starting column index |
| 172 | `u32` | Starting wall index |
| 176 | `u32` | Starting beam index |

The six count/start fields form a useful `.flt`-to-`.sty` signature when
identifying which layout is represented by Story Data.

## `.c3d` column record

| Offset | Type | Meaning |
| ---: | --- | --- |
| 0 | `f64` | X coordinate in inches |
| 8 | `f64` | Y coordinate in inches |
| 44 | `u32` | Displayed column number |
| 48 | 16-byte C string | Section label |
| 112 | `f32` | Concrete f'c in ksi |
| 116 | `f32` | Concrete unit weight in pcf |
| 120 | `f32` | Poisson's ratio |
| 416 | `f32` | Self-weight unit weight in pcf |
| 552 | `f64` | Longitudinal reinforcement fy in ksi |
| 560 | `f64` | Tie reinforcement fy in ksi |

The validation model's 72 concrete columns reconciled across `.c3d`, `.flt`,
`.sty`, `nNumGravColumns`, and `lNumConcCols`. An independent reference model
showed that `.sty` member totals can also include reference/other categories,
so gravity totals are a subset and must not be assumed equal in every model.

## `.sec` concrete column-section record

| Offset | Type | Meaning |
| ---: | --- | --- |
| 0 | 20-byte C string | Section label |
| 20 | `f32` | Rectangular B in inches |
| 24 | `f32` | Rectangular H in inches |
| 60 | `f32` | Flexure cracked-section factor |
| 152 | `u32` | Shape enum; 1033 was rectangular |
| 156 | `f32` | Axial cracked-section factor |
| 160 | `f32` | Torsion cracked-section factor |

## `.w3d` wall record

| Offset | Type | Meaning |
| ---: | --- | --- |
| 0, 8 | `f64`, `f64` | I-end X/Y in inches |
| 16, 24 | `f64`, `f64` | J-end X/Y in inches |
| 52 | `u32` | Wall number |
| 56 | `f32` | Thickness in inches |
| 60 | `f32` | f'c in ksi |
| 64 | `f32` | Unit weight in pcf |
| 68 | `f32` | Poisson's ratio |
| 80 | `u32` | Material enum; 5 is concrete |
| 172 | `f32` | Cracked membrane factor |
| 232 | `f32` | Self-weight unit weight in pcf |
| 300 | `f32` | Cracked bending factor |
| 368 | `f64` | Distributed reinforcement fy in ksi |
| 376 | `f64` | Boundary reinforcement fy in ksi |
| 384 | `f64` | Tie/link reinforcement fy in ksi |

These fields were confirmed against RAM's detailed member report for a
14-inch, 4-ksi concrete wall.

## Load properties: `.lpt`

Every property is 72 bytes. Property blocks are ordered:

```text
[surface properties][line properties][point properties]
```

| Offset | Type | Meaning |
| ---: | --- | --- |
| 0 | 20-byte C string | Label |
| 20 | `f32` | Dead load |
| 24 | `f32` | Construction dead load |
| 28 | `f32` | Construction live load |
| 32 | `f32` | Live load |
| 36 | `f32` | Mass dead load |
| 40 | `u32` | Live-load reduction enum; 1265 is Unreducible |
| 44 | `u32` | Number of geometric assignments |
| 52 | `u32` | Property UID |
| 64 | `f32` | Partition load |

Internal units depend on property category:

- surface values x 144,000 = psf;
- line values x 12 = k/ft.
- point values are stored directly in kips.

Observed property UID suffixes were `17` for surface, `16` for line, and `15`
for point-load properties.

## Load geometry: `.lod` and `.pol`

Each `.lod` record is:

```text
<u32 point_count, u32 point_start, u32 property_index, u32 id, u32 uid>
```

Each `.pol` record is:

```text
<f64 x_inches, f64 y_inches>
```

`point_start` is a zero-based index into the `.pol` point pool. A normal line
load has two points, a point load has one, and a surface load references its
polygon vertices.

`.lod` placement blocks follow the same category order as `.lpt`:

```text
[surface placements][line placements][point placements]
```

Within each category, `property_index` is local and zero-based. The number of
observed placements for each property must equal the assignment count at
`.lpt + 44`. This relationship reconciled all 438 placements and all 1,522
coordinate-pool points in the validation model.

An independent model reproduced the same ordering and reconciliation with four
surface properties, 23 line properties, one point property, and 416 total
placements. Its point property stored 2.186 kip dead and 2.73 kip live directly,
used UID suffix `15`, and referenced one `.pol` point per `.lod` placement.

This is the key relationship for Data Check debugging:

```text
Data Check coordinates
  -> `.lod` line segment
  -> local line property index
  -> `.lpt` label and load values
```

One unsupported warning matched `.lod` record 142 exactly and decoded to line
property `EW1`, placement ID 208, UID 165010. The line was approximately
0.53 ft from the nearest parallel support wall. A second warning described a
subspan rather than a standalone `.lod` record, but the nearest parallel wall
was identified 0.50 ft away. This shows why both exact-record matching and
nearest-support geometry are needed.

## RAM Data Check `.prnx`

RAM's `.prnx` report is gzip-compressed XML from DevExpress. Human-visible
report text is stored in element `Text` attributes. Findings commonly appear as:

```text
Warning 1 - Line Load not supported on Layout Type 1st.
Detected at coordinates ( ft ) (x1,y1), (x2,y2)
```

The XML element order is not necessarily page-reading order. Correlation should
pair nearby finding and coordinate labels, then match coordinates to `.lod`
and nearby `.w3d` support geometry.

## Read-only inspector

Run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\ram-structural-system\scripts\inspect-ram-rss.ps1 `
  -Source "MODEL.rss" -ListLoads
```

To correlate Data Check findings:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\ram-structural-system\scripts\inspect-ram-rss.ps1 `
  -Source "MODEL.rss" -DataCheck "Data Check.prnx"
```

The inspector checks archive CRCs, record sizes, global/floor/story totals,
load-property totals, property assignment counts, and all `.lod` references
into `.pol`. `-AsJson` provides complete decoded output for later tooling.

## Next controlled probes

The highest-value unresolved mappings are:

1. slab/deck definitions, assignments, edge records, and openings;
2. beam and joist records;
3. point-load properties and placements;
4. gravity/lateral and member-type flags inside `.c3d` and `.w3d`;
5. floor/story identifiers beyond the confirmed range signatures;
6. automatic repair of unsupported line loads by snapping a copied placement
   to a validated wall centerline.

Each probe should change exactly one RAM field or object, save two separate
models, compare archive payloads, confirm the UI/member report, and reopen the
generated copy before promoting an offset from inferred to confirmed.

## `.edg` slab edge segments (strongly inferred)

Seen on 2612_08 (RAM SS 2025, 2026-10-20). `.edg` is a run of 48-byte records:

| Offset | Type | Meaning |
| ---: | --- | --- |
| 0, 8 | `f64`, `f64` | Segment start X/Y in inches |
| 16, 24 | `f64`, `f64` | Segment end X/Y in inches |
| 32-47 | 4 x `i32` | Not decoded |

- The file was 140 records: the same closed 70-segment outline for each of the two layouts (TYP and ROOF).
- `.flt` offset 36 read 70 for each layout, which fits a per-layout edge count.
- Plotted against `.w3d` walls and `.c3d` columns, the segments trace the slab edge, with every column inside it.
- Use it read-only, for example for plan extents (the wind width B). Do not write to it.

