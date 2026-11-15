# HERO-ITEMS-002

Branch/worktree `claude/hero-items-002` from main `c5b9d5ca` (Claude Fable 5.2, effort high). Offline/static only:
no live client, launcher, network, protection or character-power work; no installed-app work.

## WIP (checkpoint 2)

Done (see the commit): the reconstruction, the validator families `head_rows`, `castle`, `scale`, `part_loop`,
`part_type` (development run 0 mismatches; 51 mutants, final run pending), the native loader (head slot item 0,
castle weapons, class scale, part floats), portable worked examples and private scenes in
`native/tests/test_native_hero_items.py` (22 tests OK), main `c255e4dd` merged.

Left: final `validate_hero_items` run with mutants through `run_validators.py`, affected validators and suites,
the default identity sweep (base worktree `~/Documents/MTM/worktrees/hero-items-002-base` at `c255e4dd`), research
part 43, status lines, PR, ready line, cleanup.

Next step: `run_validators.py --private --cache --only validate_hero_items`, then `--list-affected origin/main`.
