#ifndef MU_SOCIAL_ITEM_VIEW_H
#define MU_SOCIAL_ITEM_VIEW_H
#include "mu_social_item_tables.h"
#include "mu_hud_tip.h"
#include "../../reconstructed/social/item_display.h"
#define MU_SOCIAL_OPTION_LINES 128
/* A complete wire instance plus resolved display rows. Activation of equipment
 * bonuses and opaque client predicates is distinct from this trade preview. */
typedef struct mu_social_item_view {
    mu_social_item_wire wire;
    mu_social_item_context context;
    mu_social_item_decoded decoded;
    mu_social_item_finalized finalized;
    int count, unresolved, excellent_known, requested_excellent[9];
    char text[MU_SOCIAL_OPTION_LINES][256];
    int color[MU_SOCIAL_OPTION_LINES];
} mu_social_item_view;
typedef struct mu_social_item_hero {
    int known, level, class_byte, hp_known, max_hp, mp_known, max_mp;
    int strength, agility, energy;
} mu_social_item_hero;
int mu_social_item_view_build(const mu_social_item_tables *, const mu_hud_tip_tables *, const uint8_t[15],
                              const mu_social_item_hero *, mu_social_item_view *);
size_t mu_social_item_view_html(const mu_social_item_view *, char *, size_t);
#endif
