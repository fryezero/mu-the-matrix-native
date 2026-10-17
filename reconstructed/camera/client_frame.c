/* Frame driver timing. See client_frame.h. */
#include "client_frame.h"

void mu_frame_begin(mu_frame_clock *c)
{
    c->pending = c->accumulator;
}

int mu_frame_logic_step(mu_frame_clock *c)
{
    if (c->pending < MU_FRAME_STEP_MS)
        return 0;
    ++c->logic_steps;
    c->pending -= MU_FRAME_STEP_MS;
    return 1;
}

void mu_frame_render_start(mu_frame_clock *c, uint32_t now)
{
    c->previous_tick = c->frame_tick;
    c->frame_tick = now;
    ++c->frames;
}

int32_t mu_frame_finish(mu_frame_clock *c)
{
    int32_t elapsed = (int32_t)(c->frame_tick - c->previous_tick);
    int32_t sleep = -1;
    if (elapsed < MU_FRAME_STEP_MS) {
        sleep = MU_FRAME_STEP_MS - elapsed;
        c->frame_tick = c->frame_tick + (uint32_t)sleep;
        elapsed = MU_FRAME_STEP_MS;
    }
    c->accumulator = (int32_t)((uint32_t)c->pending + (uint32_t)elapsed);
    return sleep;
}
