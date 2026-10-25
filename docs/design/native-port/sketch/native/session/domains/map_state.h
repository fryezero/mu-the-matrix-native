/* domains/map_state.h (sketch, PRIVATE): where the hero is, as the server last said.
 * Moves here from core/mu_map.c's mu_map_session (whose 10,000,000 demo Zen is deleted; warp
 * costs read mu_session_money) and from the shell's offline join table. Fixes the per-visit
 * mapsess leak by construction: there is no per-visit map session any more. */
#ifndef MU_DOM_MAP_STATE_H
#define MU_DOM_MAP_STATE_H
#include "../../../reconstructed/map/map.h"
typedef struct mu_dom_map {
    int32_t world;                 /* [0x01cf15fc] */
    int32_t tile[2];
    float angle;
    uint32_t seq;
    /* the E7 03 minimap records and the Move window's availability inputs (reconstructed/map types) */
    /* TODO(SESSION-MAP-001): mu_map_minimap records[]; move window state the verified manager writes */
} mu_dom_map;
#endif
