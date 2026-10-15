# RAM Modeler loads notes

Seen 2026-10-15 on Mt Pleasant (terrace loading change asked by Ryan
Darling: 145 psf SDL / 30 psf LL on MP2 and MP3). Do not apply to RAM
Concept.

## Where the SDL lives

`PropTable > Loads > Surface` → Surface Load Properties. One row per load
label (Residential, Lobby/Corridor, Balcony, Terrace ...), placed on the slab
with `Layout > Loads > Surface Loads`. Changing a row changes every area it
is placed on.

- **Dead Load (psf) is the superimposed dead load only.** Self-weight is
  computed by the program: RAM Manager `Criteria > Self-Weight`, mirrored in
  the dialog's right-hand panel (Member Dead Loads: Beams, Columns, Walls,
  Slabs/Decks ticked). With Slabs/Decks ticked, never add slab weight into
  Dead Load; it comes from the thickness and unit weight in `PropTable >
  Decking`.
- **Mass Dead Load (psf)** is separate (RAM Frame story mass); move it with
  the Dead Load.
- **Live Load (psf)** with its reduction radio: Reducible, Storage,
  Unreducible, Roof. Clicking in the group box changes the radio; check it
  before Change.
- Construction DL / Construction LL matter only for unshored composite
  steel; leave them on a concrete job.
- **Change, then OK.** The table at the bottom shows the stored values;
  typing in the fields alone changes nothing.

Terrace on Mt Pleasant went from 43 / 100 Unreducible to 145 / 30
Unreducible, Mass DL 145.

## After a load change

Save in Modeler. The office order is Modeler → RAM Frame → RAM Concrete
(Concept forces) → Concept checks; the engineer runs Frame before touching
Concept. A Concept floor opened from RAM Manager takes its loads from the RSS
model on the next update (*expected*, not yet seen); a standalone `.cpt`
gets the SDL as an area load on its Other Dead Loading layer instead.
