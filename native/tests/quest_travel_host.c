/* Request -> world reload -> delayed F6 answer -> remaining movement, on synthetic data. */
#define main mu_world_test_cli_main
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wunused-function"
#include "../world/main.c"
#pragma GCC diagnostic pop
#undef main
#include "../core/mu_quest.h"

typedef struct context {
    app *a;
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
    if (argc != 3) return 2;
    app *a = calloc(1, sizeof *a);
    if (!a) return 2;
    a->root = argv[1];
    a->tile[0] = a->tile[1] = 80;
    a->width = a->height = 64;
    a->no_env = a->no_particles = a->no_helpers = a->no_names = a->no_players = a->quiet = 1;
    if (load(a)) return 2;
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
    advance(a, 0);
    const int restored = a->world == 3 && a->walk.hero.tile[0] == 10 && a->walk.auto_path.flag == 1 &&
                         a->walk.auto_path.mode == 1 && a->walk.auto_path.target_x == 42 &&
                         a->walk.auto_path.target_y == 43;
    for (int k = 0; k < 4; ++k) mu_quest_session_step(&q);
    const int resumed = c.answers == 1 && a->walk.auto_path.flag == 2 && a->walk.hero.movement;
    for (uint32_t now = 40; now <= 30000; now += 40) advance(a, now);
    const int arrived = a->walk.hero.tile[0] == 42 && a->walk.hero.tile[1] == 43 && !a->walk.hero.movement;
    printf("{\"armed\":%d,\"restored\":%d,\"resumed\":%d,\"arrived\":%d}\n", armed, restored, resumed, arrived);
    mu_quest_session_close(&q);
    unload(a);
    free(a);
    return armed && restored && resumed && arrived ? 0 : 1;
}
