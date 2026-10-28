#ifndef MU_CHARACTERS_H
#define MU_CHARACTERS_H
#include <stddef.h>
#include <stdint.h>
#include "../../../reconstructed/players/remote_players.h"
typedef struct mu_session mu_session;
#define MU_CHARACTERS_MAX 400

typedef struct mu_characters_view {
    const mu_rp_character *records;
    const uint8_t *used;
    const uint32_t *generation;
    const uint32_t *equipment_revision;
    const mu_rp_calls *equipment_calls;
    const uint8_t (*equipment)[MU_RP_EQUIP_BYTES];
    const uint8_t *store_open;
    const char (*store_title)[0x2e];
    int32_t capacity;
} mu_characters_view;
mu_characters_view mu_session_characters(const mu_session *s);
int32_t mu_session_character_index(const mu_session *s, uint16_t key);
/* Projection of the reconstructed subset. Unknown bytes and the two independent
 * scene/name fields remain caller-owned. Each mapped range uses manifest offsets. */
int mu_character_project(const mu_rp_character *c, uint8_t *raw, size_t size);
int mu_character_restore(mu_rp_character *c, const uint8_t *raw, size_t size);
#endif
