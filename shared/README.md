# Shared

This folder is reserved for utilities and contracts that are genuinely neutral
between RAM Structural System and RAM Concept.

Appropriate examples:

- checkpoint and artifact naming
- logging and process discovery
- common test helpers
- explicit handoff schemas for geometry, loads, materials, and units
- office design criteria both products check against (`JTE_DEFLECTION_LIMITS.md`)

Do not place product APIs, binary record layouts, menu automation, or analysis
assumptions here. Start code in its owning product and move it into `shared/`
only after both products use the same tested contract.
