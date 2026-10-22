# Item mix and jewel rule library

Build with `make -C reconstructed/mix`. Run synthetic examples with
`python3 -m unittest discover -s reconstructed/mix -p 'test_*.py' -v`.
The private comparison is `scripts/validate_mix.py`.

Read [the finding](../../docs/research/client-mix.md) for input identities,
client addresses, modelled boundaries, counts and remaining work. This is
the first NATIVE-MIX-001 slice. Native/GFx integration, recipe ranking,
result handling, personal store and repair flows are open.

The host supplies summaries and decoded rows; no game data is embedded.
Readiness mutates scratch summaries even on rejection. Harmony sources
and cost mode D are unsupported. An unsupported cost's zero return must
not be interpreted as a valid free quote. Non-finite formulas are rejected.
