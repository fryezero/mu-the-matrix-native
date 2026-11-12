# UI-WINDOWS-001

## WIP checkpoint

Branch `codex/ui-windows-001`, base `d4af71dd`. Five optional original movies
are bound with presentation-only adapters: D CommandWindow, N MatchingSelect,
B GensRanking, Y PetInventoryFrame, K GremoryCase. Original menu IDs 11, 12,
13 and 15 also toggle their windows. Command actions, matching requests,
Muun item/appearance/sort/book operations and Gremory claims are refused.
Gremory tabs and five empty Muun pages are local presentation.

Done: root build; production controller test with 115 callback refusals,
eight immediate menu sound deliveries, unchanged hero/items, close, focus,
page bounds, tab validation, detached sound and unavailable-movie controls;
existing Help lifecycle tests. Three tests pass in 1.800 seconds. The original
menu dispatcher sound site is `0x00c716f6`, separate from AUDIO-002G's CButton.
No generic movie-click sound was added.

Left: graphical mu-client build and window-only journeys, private tests,
complete missing-movie inventory, affected selection/checks, default identity
sweep with rebuilt binaries, diff review and final docs/PR. The software
mu-shell run reaches scene 6 but does not count as graphical window proof.

Help investigation: `+0x120`, registration `0x00ac678a`, constructor
`0x00b89588`, getter `0x00b6cba2`. Its one direct caller `0x00b6b744`
reads the retained auxiliary help list for EventMapHelper, rather than opening
HelpWindow. No original open route recovered yet; native Ctrl+H stays labeled
as native policy. Neither menu 3 nor menu 8 opens Help. F1 is not invented.

Next: build `make -C native -j4 client world`, then use numeric script VKs and
mu-client's actual window `shot:NAME` actions. Respect the load/memory guard.
Scratch and renders are under `mu-mac-tools/native/{scratch,renders}/ui-windows-001`.
The baseline comparison tree is the lane's detached scratch `base` worktree.
No installed app, original client or live service was touched.
