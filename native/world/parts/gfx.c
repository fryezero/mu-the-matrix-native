/* parts/gfx.c (WORLD-RT-001): the quest demo server's step at its place in the tick (NATIVE-QUEST-001).  The
 * quest session lives in the front end's GFx interface (world/world_gfx.c), so builds without GL have no quests;
 * SESSION-QUEST-001 moves it into the session and steps it from this row. */
#include "../world_rt_internal.h"

static void quest_step_tick(struct mu_world_rt *a, void *self)
{
    (void)self;
#ifndef MU_WORLD_NO_GL
    if (a->gfx)   /* NATIVE-QUEST-001: the quest demo server's answers */
        world_gfx_quest_step(a->gfx);
#else
    (void)a;
#endif
}

const mu_world_part_ops mu_part_quest_step = {
    .name = "quest_step",
    .tick = quest_step_tick,
};
