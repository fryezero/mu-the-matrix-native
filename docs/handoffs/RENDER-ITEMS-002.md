# RENDER-ITEMS-002 part 1

Inventory RenderItem3D special-code handling is implemented. [Finding](../research/client-render-items.md)
holds the addresses, evidence classes, case counts, limitations and local artifact paths.

- Constant overrides generated from pinned restored instructions; time/window logic in C.
- 28 codes in the old "27" list. Box of Luck signed levels >7 still cross an uncaptured external jump.
- Native inventory resolves the drawn model before loading geometry; frame time reaches the special spin.
- Unicorn: 5,512 cases, five families, zero mismatches, 6/6 compiled C mutants caught. Older generic/wrapper
  comparison: 3,000 cases, zero mismatches. Portable/native regression and local before/after renders.
- Local snapshots: 16 Muun records decoded per snapshot. EnchantEffect+0x5c has 38 world records but every
  nested type map is absent. Exact missing reads are in the local effect-inputs report.

Remaining: the 1,674 RenderObjDraw type branches, RenderLinkItem effect switch, character/ground body-effect
integration, Muun owners/effects, special-window activation for code 0x1c64, unresolved costume-model files,
and the missing nested map-object effects. No live game was started, stopped or read.

Local gate on the part-1 tree: `bash scripts/local-macos-ci.sh tools/python/bin/python` passed,
1,304 tests across 38 suites, 156 explicit skips, native builds and publication audit clean.
The validator harness reports 5,512 cases and 6 mutants, pass. Self-review against the brief
and repository evidence rules found no remaining blocking issue in this bounded scope.
