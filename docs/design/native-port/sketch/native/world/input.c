/* input.c (sketch): THE input router. Moves world/main.c windowed() 3179-3368 here and makes
 * mu-client reach every branch (digit casts, Alt/Space, right-click skills were unreachable). */
#include "world_rt_internal.h"

int mu_world_rt_input(mu_world_rt *rt, const mu_input_msg *msg)
{
    /* TODO
     *   1. if rt has the gfx part and mu_part_gfx.input(rt, gfx, msg): return 1      // first refusal
     *   2. key messages -> mu key scan state (0x00ec5475, verified) -> panel binding table:
     *        the panel key toggles a window: view-local state of the gfx part (open/close the movie);
     *        windows whose open state is client handler state (quest, character) -> that window's MU_INTENT_WINDOW_<MOVIE>
     *   3. for each part with .input in parts.def order: if consumed return 1
     *        skills part:  digits -> MU_INTENT_CAST {bar slot's skill, target under cursor}
     *        items part:   Alt highlights labels (local), Space/click -> MU_INTENT_PICK_UP {item key}
     *        npc part:     click on an NPC -> MoveHero's talk case: walk there, then MU_INTENT_TALK
     *        combat part:  click on a monster/player -> attack target (pre_tick sends)
     *   4. mu_walk_message / mu_walk_key (left click walk: mu_walk walks locally and the map part
     *      submits MU_INTENT_WALK with the PATH_t the client's SendMove reads)
     */
    (void)rt; (void)msg;
    MU_NOT_IMPLEMENTED();
}
