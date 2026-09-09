# Podium concrete hand-guide

Reusable Bentley RAM Structural System sequence for a wood-over-concrete
podium. Guide the live GUI. Do not mutate a production model unless the user
asks. Keep job kips, stories, soil values, and model paths in the matching
`eng-agent` project.

```text
spreadsheet ELF (project)
  -> Modeler: concrete walls Lateral; spreads under columns; mats under walls
  -> Frame: user-defined EQX / EQY story forces
  -> Concrete: Concept forces green -> Analyze -> walls -> columns
  -> Foundations: column spreads in RAM Foundation; wall mats later in Concept
```

## Notes to read

- Modeler foundations: `RAM_MODELER_FOUNDATION_NOTES.md`
- Frame: `RAM_FRAME_NOTES.md`
- Concrete walls and columns: `RAM_CONCRETE_NOTES.md`
- Column spread-footing design: `../skills/concrete-footing-design-ram/SKILL.md`

## Two-stage until upper shear walls exist

- Convert concrete walls to Lateral. Construction does not distinguish gravity
  vs lateral concrete walls unless there is a special reason.
- Apply spreadsheet unfactored ELF as user-defined story forces. Do not run
  program seismic or wind on this first pass.
- When the upper R exceeds the podium R, multiply the force transferred to the
  lower structure by that R ratio before adding it to the podium base shear.
  Use the unfactored total base, not ASD.
- After wood shear-wall locations exist, replace the single story force with
  nodal loads at those locations and then consider program seismic, omega
  cases, and torsion.

## Guide style

Give the next command path only. Job numbers come from the project
spreadsheet or transcript, not from these notes.
