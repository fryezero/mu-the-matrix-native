/* domains/quests_state.h (sketch, PRIVATE)
 *
 * The whole reconstructed mu_quest_client lives here, including its window-handler state
 * (progress window, info window, dialog list, guide tab, summary HUD, classic manager), because
 * mu_quest_receive and the verified quest window handlers take the whole client and write all
 * of it - in the original these are the quest manager's globals. Moves here from
 * world/world_gfx.c:52 (GL builds only), so quests now exist in mu-walk/mu-shell too and
 * survive a return to character select.
 *
 * Its mirror fields (money, hero_level, hero_class, world, hero_x/y, time) are written by the
 * env refresh before every call into the quest code and are never read by anything else.
 */
#ifndef MU_DOM_QUESTS_STATE_H
#define MU_DOM_QUESTS_STATE_H
#include "../../../reconstructed/quest/quest.h"
typedef struct mu_dom_quests {
    mu_quest_client client;
} mu_dom_quests;
#endif
