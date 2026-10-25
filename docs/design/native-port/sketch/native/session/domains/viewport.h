/* domains/viewport.h (sketch, PUBLIC) */
#ifndef MU_DOM_VIEWPORT_H
#define MU_DOM_VIEWPORT_H
#include <stdint.h>
#include "../../../reconstructed/players/remote_players.h"

typedef struct mu_session mu_session;

typedef struct mu_viewport_view {
    const mu_rp_character *chars;        /* MU_VIEWPORT_MAX entries; read-only outside a mu_sim lease */
    const uint8_t *used;
    const uint32_t *generation;
    int32_t count;
    int32_t hero_index;
} mu_viewport_view;

mu_viewport_view mu_session_viewport(const mu_session *s);
/* The entry with a server key, or -1 (the client's lookup rule). */
int32_t mu_session_find_key(const mu_session *s, int16_t key);

#endif
