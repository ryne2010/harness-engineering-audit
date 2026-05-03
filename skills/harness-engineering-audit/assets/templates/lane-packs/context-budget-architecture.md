# Context Budget Architecture

Separate hot-path guidance from deep references so agents stay grounded without overloading context.

## Layers

- Hot path: root `AGENTS.md`, docs index, active lane registry
- Lane context: source docs and constraints for the current lane
- Deep references: ADRs, architecture notes, long specs, generated reports

## Rule

Load deep references only when the lane or task requires them.
