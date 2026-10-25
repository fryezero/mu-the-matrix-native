/* domains/viewport_state.h (sketch, PRIVATE): the client's CharactersClient table.
 *
 * Players, monsters and NPCs share one table in the client (memread reads all 400 entries).
 * The session owns it. The record type is reconstructed/players' mu_rp_character, the
 * CHARACTER subset the verified viewport/move/equipment handlers write.
 *
 * Two writers by design, never at the same time:
 *   - apply (mu_session_pump): create, delete, equipment, hp, path set by a move packet
 *   - the world tick through mu_sim (MoveCharacters' remote step, dead fade): motion fields
 * This is the client's own arrangement (handlers and MoveCharacters write one record, serialized
 * on the UI thread). The lease makes the serialization explicit and audits the field split.
 *
 * Access patterns:
 *   by server key (every packet): linear scan of 400 entries, the client's 0x0137c724 rule,
 *     so slot choice equals the original's and memread comparison is index for index
 *   all live entries (tick, render, pick): array walk over used[]
 *   (index, generation) for render caches: views key GL/animation caches by both, so a slot
 *     reused by another character can never inherit the previous one's cache
 */
#ifndef MU_DOM_VIEWPORT_STATE_H
#define MU_DOM_VIEWPORT_STATE_H
#include "../../../reconstructed/players/remote_players.h"

#define MU_VIEWPORT_MAX 400

typedef struct mu_dom_viewport {
    mu_rp_character chars[MU_VIEWPORT_MAX];
    uint8_t used[MU_VIEWPORT_MAX];
    uint32_t generation[MU_VIEWPORT_MAX];
    int32_t hero_index;                  /* the hero's slot; its MOTION is mu_walk's (world), its record here */
    int16_t hero_key;                    /* [0x06fca288] */
    mu_rp_calls calls;                   /* scratch: the handlers' engine-call lists, turned into cues */
} mu_dom_viewport;

#endif
