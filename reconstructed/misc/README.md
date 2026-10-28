# Miscellaneous window reconstruction, WIP

`misc.c` reconstructs only BossHPUI's five-integer bar state and arithmetic.
It does not provide a session domain, receive handler, request builder or native view.
The module is compiled in a temporary directory by `native/tests/test_misc.py` and
`scripts/validate_misc.py`; it is not linked into the product yet.

| Function | Original instructions | Boundary |
|---|---|---|
| `mu_misc_boss_init` | `0x00b360b1` | five state writes |
| `mu_misc_boss_colour` | `0x00b35d65` | zero maps to palette index 3 |
| `mu_misc_boss_gauge` | `0x00b35d89` | segment remainder, full-health exception, nonpositive HP |
| `mu_misc_boss_update` | `0x00b35c40` | remaining layers and palette; CRT ceil/conversion modeled |
| `mu_misc_boss_set_maximum` | `0x00b35b1d..0x00b35b37` | bounded interior unit write, caller frame supplied |

The two native bars use independent structs. Window pointers, string services,
ActionScript, movie placement, animation and game-state replication are outside
these comparisons. The guards on nonpositive unit/segment counts are authored host
refusals, not original instruction behavior. Original divide faults are not executed.

Run `python scripts/validate_misc.py --cases 500 --mutants` with the configured
repository Python and private pinned captures. This runs 2,500 comparisons in five
families and catches six compiled mistakes. Every family and mutant starts with fresh
emulation stubs. Portable tests need only a C compiler; the private check is opt-in.

[Evidence, scope mismatch and remaining work](../../docs/research/client-misc-windows.md).
