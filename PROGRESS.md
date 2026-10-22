# NATIVE-MAP-001 progress (not for main)
Done: reconstructed/map + scripts/validate_map.py (2,000 Unicorn cases, 0 mismatches, 10/10 planted mistakes), core/mu_map
(session, demo server, travel API mu_map_travel_to/_move/_take_teleport), world changes in mu-world/mu-client, hudMap +
MoveCommand GFx glue (Tab overlay and Move window verified under Ruffle: renders/map/gfx/), NaviMap conversion in gfxconvert.
Headless travel verified (move keys, gate Lorencia->Dungeon). Live notes: ~/Documents/mu-mac-tools/native/scratch/map/NOTES.md.
Remaining: GFx row-click travel check (mclick), portable tests (reconstructed/map/test_map.py, native mu-walk travel test),
docs/research/client-maps.md, status/roadmap/handoff rows, rebase, local CI, PR/merge, Preview.app rebuild.
Gaps: Move window position (centred, client left), NPC markers, party icons static, mu-client s->g.world after travel.
