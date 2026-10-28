# SESSION-MAP-001a

Bounded minimap-marker migration from origin/main `26018b4`. Travel, warp requests, gates,
teleport placement and respawn remain with their existing owners.

The session owns 128 NPC/portal markers and 256 compacted detector dots. Only recorded C1
E7/03 and /04 marker bodies and C2 E7/05 detector bodies apply. The seed appends the three
handler addresses already named in client-maps.md, with MU_STATIC provenance. No dispatcher
jump table, dispatch.def, decode or encrypted transport was touched.

The map view borrows immutable records; each HUD adapter has its own revision and binding
cache. Showing or rebinding the movie replays the collection without changing it. The fixture
owns synthetic gate/NPC marker generation and the `detected kind x y ...` refresh command,
including an empty `detected` command. It delivers ordinary plaintext frames. The world
part opens its bounded overlay fixture when a world opens, detaches it before close and
recreates it on world reload. Account-owned session lifetime is a later prerequisite.

Detector packets replace the entire compacted dot list, skip zero-kind entries, retain the
16-bit coordinates and use the existing instruction-verified kind+1 conversion. Empty refresh
explicitly removes stale movie dots. This is a native empty-refresh policy: the original helper
skips its movie invocation for an empty vector. The original E7/05 handler's show setter is
reflected as a per-consumer detector sequence, without submitting a new show/travel request.
Malformed names, short lists, mismatched lengths, unsupported head/body pairs and over-capacity
collections leave session state and revision unchanged. Repeated marker identity updates in place;
removal matches type and key. No new per-frame allocation was introduced.

## Verification

- New original-instruction comparison: marker3, marker4, detector_packet, 500 cases each,
  **1,500 cases, zero mismatches, 4/4 compiled planted mutants caught**. The actual wrapper,
  packet loop, coordinate conversion and marker/detector GFx helper instructions run. Heap,
  smart-pointer lookup, vector insertion/copy and GFx value operations are modeled. The show
  setter is outside this collection comparison. Target pins remain capture09 text and run10 data.
- Existing map comparison: **5,001 cases, zero mismatches, 10/10 historical mutants caught**,
  using the original lang4 snapshot. No reconstructed/map implementation changed.
- Bounded teleport/registration regression: **876 checks, zero mismatches, 3/3 historical
  mutants caught**. This reruns the existing bounded slices without migrating travel.
- Portable reconstructed map tests: **11 pass**. Native travel tests: **9 pass**, including the private Lorencia → Noria → Lorencia check with manifest-backed inputs. New tests cover recorded routing, add/update/delete, malformed
  atomicity, empty refresh, full collection update/remove/reuse, 16-bit/count bounds, lease
  mutation refusal, and movie-host detach/rebind. The private comparison is registered in
  validators.toml at 120 cases with four compiled mutants.
- Real installed hudMap under ABI-3 Ruffle: ten checked ticks, portal/NPC/user/monster counts
  read from the actual movie arrays. All four types appear; malformed frames retain them;
  empty detector refresh clears dots; removal clears markers; reopening the host reconstructs
  retained records. Three representative captures were made and the populated frame inspected.
  These are synthetic marker positions over the real movie and map image, not live-game evidence.

A baseline/current render comparison compiled the pre-migration map adapter from `26018b4`
and the session adapter against identical synthetic portal/NPC inputs and the installed real movies.
With the existing deterministic GFx test clock, all **4,096,000 RGBA bytes match exactly**, SHA-256
`42882ea88738acdcb6aa4bafc388cd8faa5e5fdd46c4e08322d837e7b88b1625`. An initial ordinary-clock
comparison differed only in animated skill icons; no map pixel differed. No render pins changed.

Final locked gate and fixture-suite counts are recorded after the final merge with origin/main.
No hosted workflow or live client/launcher was used. Source and synthetic fixtures only are
committed; input symlinks, local reports and renders remain untracked and are deleted after merge.
PERF-004 confirmed parts/map.c and the map adapter free of overlap before the runtime hook edit.

## Remaining SESSION-MAP-001

Full teleport/warp migration requires encrypted delivery, a complete 0x0128136d handler family,
request transform 0x00cda52b and its server-provided key, plus account/world barrier ownership.
Warp cost/session money, respawn place and the travel demo migration remain outside this slice.
The navimap formatter still lacks captured C++ locale state. Party icons retain their social
owner. No world/account relog persistence or real-server marker policy is claimed.
