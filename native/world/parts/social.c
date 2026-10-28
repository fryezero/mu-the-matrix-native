/* parts/social.c (WORLD-RT-001): party, trade, friends and messages (core/mu_social, local echo; the offline
 * social demo).  The social session outlives world changes: a travel re-points it at the new world's players. */
#include <stdio.h>
#include <stdlib.h>

#include "../world_rt_internal.h"

static int social_open(struct mu_world_rt *a, void *self)
{
    (void)self;
    if (!a->social) {
        a->social = calloc(1, sizeof *a->social);
        if (!a->social) return 1;
        mu_social_init(a->social, a->hero_name, a->players);
        if (!a->social->session) return 1;
    } else {
        a->social->players = a->players;
        a->social->revision++;
    }
    if (a->players) a->players->social = a->social;
    return 0;
}

/* The session stays (mu_world_rt_close frees it); its GFx view closes with the world. */
static void social_close(struct mu_world_rt *a, void *self)
{
    (void)self;
#ifndef MU_WORLD_NO_GL
    if (a->gfxsocial) { world_gfx_social_close(a->gfxsocial); a->gfxsocial = NULL; }
#endif
    if (a->social) a->social->players = NULL;
}

static void social_tick(struct mu_world_rt *a, void *self)
{
    (void)self;
    const mu_hero *h = &a->walk.hero;
    if (a->social) mu_social_step(a->social, a->world, h->tile[0], h->tile[1]);
}

static void social_frame(struct mu_world_rt *a, void *self, uint32_t now)
{
    (void)self;
    (void)now;
#ifndef MU_WORLD_NO_GL
    if (a->gfxsocial && a->gfx == a->gfxsocial_owner) world_gfx_social_frame(a->gfxsocial);
#else
    (void)a;
#endif
}

static void social_report_summary(const struct mu_world_rt *a, const void *self)
{
    (void)self;
    if (a->social)
        printf("{\"social\":true,\"party\":%d,\"friends\":%d,\"pending\":%d,\"trade_open\":%d,\"trade_result\":%d,\"completed\":%d,\"received_items\":%d,\"zen\":%lld}\n",
               a->social->party.count, a->social->friends.count, a->social->pending, a->social->trade.open,
               a->social->trade.result, a->social->completed, a->social->received_items, (long long)a->social->zen);
}

const mu_world_part_ops mu_part_social = {
    .name = "social",
    .open = social_open,
    .close = social_close,
    .tick = social_tick,
    .frame = social_frame,
    .report_summary = social_report_summary,
};
