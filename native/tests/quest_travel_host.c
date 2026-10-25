/* Request -> world reload -> delayed F6 answer -> remaining movement, on synthetic data.  WORLD-RT-001: over the
 * world runtime (world/mu_world_rt.h, its internals for the walk, the map session and the travel counters)
 * instead of compiling world/main.c into this file. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../core/mu_quest.h"
#include "../world/world_rt_internal.h"

typedef struct context {
    mu_world_rt *a;
    int answers;
} context;

static int start_path(void *user, int32_t flag, int32_t sx, int32_t sy, int32_t x, int32_t y,
                      int32_t mode, int32_t error_check)
{
    (void)sx; (void)sy;
    return mu_walk_auto_move_ex(&((context *)user)->a->walk, flag, x, y, mode, error_check);
}

static int enter_map(void *user, int32_t world, int32_t x, int32_t y)
{
    (void)x; (void)y;
    /* The demo server enters short of the quest goal, so teleporting cannot mask a lost path. */
    return mu_map_travel_to(((context *)user)->a->mapsess, world, 10, 10);
}

static void resume_path(void *user, uint8_t subcode)
{
    context *c = user;
    c->answers++;
    mu_walk_auto_resume(&c->a->walk, subcode);
}

int main(int argc, char **argv)
{
    if (argc != 3 && argc != 4) return 2;
    const int fail = argc == 4;
    mu_world_rt_options o;
    memset(&o, 0, sizeof o);   /* the bare runtime: world 0, class 0, no sound, the map session on */
    o.root = argv[1];
    o.tile[0] = o.tile[1] = 80;
    o.width = o.height = 64;
    o.no_env = o.no_particles = o.no_helpers = o.no_names = o.no_players = o.quiet = 1;
    char open_error[512];
    mu_world_rt *a = mu_world_rt_open(&o, open_error, sizeof open_error);
    if (!a) return 2;
    context c = {a, 0};
    mu_quest_host host = {.user = &c, .path_start = start_path};
    mu_quest_session q;
    char error[256];
    if (mu_quest_session_open(&q, argv[2], "guide 11\n", &host, error, sizeof error)) return 2;
    q.user = &c;
    q.travel = enter_map;
    mu_quest_set_move_answer(&q.client, resume_path);
    for (int k = 0; k < 4; ++k) mu_quest_session_step(&q);
    q.client.hero_class = 1;
    q.client.hero_level = q.client.hero_level_total = 10;
    q.client.hero_x = q.client.hero_y = 80;
    mu_guide_go(&q.client);
    const int armed = q.stats.requests == 1 && q.travels == 1 && a->walk.auto_path.flag == 1;
    mu_world_rt_frame(a, 0);
    const int restored = fail ? a->world == 0 && a->walk.hero.tile[0] == 80 && a->walk.auto_path.flag == 0 :
                               a->world == 3 && a->walk.hero.tile[0] == 10 && a->walk.auto_path.flag == 1 &&
                               a->walk.auto_path.mode == 1 && a->walk.auto_path.target_x == 42 &&
                               a->walk.auto_path.target_y == 43;
    mu_quest_session_travel_complete(&q, !a->travel_failures);
    for (int k = 0; k < 4; ++k) mu_quest_session_step(&q);
    const int resumed = fail ? c.answers == 0 && !a->walk.hero.movement :
                              c.answers == 1 && a->walk.auto_path.flag == 2 && a->walk.hero.movement;
    for (uint32_t now = 40; now <= 30000; now += 40) mu_world_rt_frame(a, now);
    const int arrived = fail ? a->walk.hero.tile[0] == 80 && a->walk.hero.tile[1] == 80 :
                              a->walk.hero.tile[0] == 42 && a->walk.hero.tile[1] == 43 && !a->walk.hero.movement;
    printf("{\"armed\":%d,\"restored\":%d,\"resumed\":%d,\"arrived\":%d}\n", armed, restored, resumed, arrived);
    mu_quest_session_close(&q);
    mu_world_rt_close(a);
    return armed && restored && resumed && arrived ? 0 : 1;
}
