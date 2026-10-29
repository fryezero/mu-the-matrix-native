#include "mu_frame_time.h"
#include <string.h>
void mu_frame_time_init(mu_frame_time *t)
{
    memset(t, 0, sizeof *t);
    t->frame_time = 0.1f;
}
void mu_frame_time_update(mu_frame_time *t, mu_time_get_fn get, void *context)
{
    if (!t->started) {
        t->frames = 0;
        t->base = get(context);
        t->started = 1;
    }
    ++t->frames;
    ++t->next_frames;
    const uint32_t clock = get(context);
    t->world_time = (float)(double)clock;   /* cvtsi2sd + 2^32 for the high bit, cvtsd2ss */
    t->now = get(context);
    t->delta = (int32_t)(t->now - t->prior);
    const double elapsed = (double)(int32_t)(t->now - t->base) / 1000.0;
    const double fps = elapsed == 0.0 ? -1.0 : (double)t->frames / elapsed;
    if (elapsed > 2.0 && t->frames > 10) {
        t->base = t->next_base;
        t->frames = t->next_frames;
        t->next_base = get(context);
        t->next_frames = 0;
    }
    t->frame_time = (float)(int32_t)(t->now - t->prior) / 1000.0f;
    if (t->now == t->prior)
        t->frame_time = 0x1.a36e30p-14f;   /* [0x01ac8d6c], bits 0x38d1b718 (one ulp above 0.0001f) */
    t->fps = (float)fps;
    t->prior = t->now;
}
static mu_frame_time global = {0, 0, 0, 0, 0, 0, 0, 0.0f, 0.0f, 0.1f, 0};
static uint32_t global_now;
static uint32_t global_get(void *context)
{
    (void)context;
    return global_now;
}
float mu_frame_time_value(void) { return global.frame_time; }
void mu_frame_time_tick(uint32_t now_ms)
{
    global_now = now_ms;
    mu_frame_time_update(&global, global_get, NULL);
}
void mu_frame_time_reset(void) { mu_frame_time_init(&global); }
