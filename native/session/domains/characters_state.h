#ifndef MU_CHARACTERS_STATE_H
#define MU_CHARACTERS_STATE_H
#include "characters.h"
typedef struct mu_dom_characters {
    mu_rp_character records[MU_CHARACTERS_MAX];
    uint8_t used[MU_CHARACTERS_MAX];
    uint32_t generation[MU_CHARACTERS_MAX], equipment_revision[MU_CHARACTERS_MAX];
    uint8_t equipment[MU_CHARACTERS_MAX][MU_RP_EQUIP_BYTES];
    mu_rp_calls equipment_calls[MU_CHARACTERS_MAX];
    uint8_t store_open[MU_CHARACTERS_MAX];
    char store_title[MU_CHARACTERS_MAX][0x2e];
} mu_dom_characters;
#endif
