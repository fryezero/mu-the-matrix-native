/* SESSION-QUEST-001: quest logic at tick 40 in both headless and GFx tools. */
#include "../world_rt_internal.h"
#include "../../core/mu_quest.h"
#include <stdlib.h>
#include <string.h>
typedef struct quest_part
{
    mu_quest_session q;
} quest_part;
static void quest_step_tick(struct mu_world_rt *a, void *self)
{
#ifndef MU_WORLD_NO_GL
    if (a->gfx)
    {
        world_gfx_quest_step(a->gfx);
        return;
    }
#endif
    quest_part *p = self;
    if (!p->q.ready)
    {
        if (!getenv("MU_LANG_DIR"))
            return;
        char error[256];
        if (mu_quest_session_open(&p->q, NULL, a->npc_demo ? a->npc_demo->quests : NULL, NULL, error,
                                  sizeof error))
            return;
        mu_quest_session_load_classic(&p->q, a->root);
    }
    mu_intent in = {.kind = MU_INTENT_QUEST_CONTEXT};
    in.u.quest_context.world = a->walk.world;
    in.u.quest_context.x = a->walk.hero.tile[0];
    in.u.quest_context.y = a->walk.hero.tile[1];
    in.u.quest_context.class_byte = a->walk.hero.class_byte;
    in.u.quest_context.level = in.u.quest_context.total = 1;
    mu_session_submit(p->q.session, &in);
    mu_quest_session_step(&p->q);
}
static void quest_close(struct mu_world_rt *a, void *self)
{
    (void)a;
    mu_quest_session_close(&((quest_part *)self)->q);
}
static void quest_report(const struct mu_world_rt *a, const void *self)
{
    (void)a;
    mu_quest_session_report(&((const quest_part *)self)->q, stdout);
}
const mu_world_part_ops mu_part_quest_step = {
    .name = "quest_step",
    .state_size = sizeof(quest_part),
    .tick = quest_step_tick,
    .close = quest_close,
    .report_summary = quest_report,
};
