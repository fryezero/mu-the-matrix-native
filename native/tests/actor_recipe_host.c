/* RENDER-ACTORS-001: exercise the production actor loader without a session. */
#include "../core/mu_world_actors.c"

static void texcoord(void *context, float u, float v) { (void)context; (void)u; (void)v; }
static void vector(void *context, const float xyz[3]) { (void)context; (void)xyz; }
static void color(void *context, float r, float g, float b, float a)
{ (void)context; (void)r; (void)g; (void)b; (void)a; }

int main(int argc, char **argv)
{
    if (argc != 4) return 2;
    mu_world *map = calloc(1, sizeof *map);
    mu_world_actors actors = {0};
    mu_world_actor actor;
    map->world = atoi(argv[3]);
    actors.map = map;
    char error[1024];
    int cl = atoi(argv[2]);
    int result = load_actor(&actors, &actor, argv[1], cl, 128, 124, 5, 0,
                            "DemoActor", 0, error, sizeof error);
    if (result) { fprintf(stderr, "%s\n", error); free(map); return 1; }
    const char *body_file = actor.player ? actor.player->items[0].path : "";
    size_t root_length = strlen(argv[1]);
    if (!strncmp(body_file, argv[1], root_length) && body_file[root_length] == '/')
        body_file += root_length + 1;
    printf("{\"class\":%d,\"player\":%d,\"scale\":%.9g,\"body_file\":\"%s\",\"slots\":[", cl,
           actor.player != NULL, (double)actor.actor.spec.scale, body_file);
    if (actor.player) {
        if (mu_character_update(actor.player) != MU_MODEL_OK) return 3;
        float lo[3], hi[3];
        if (!mu_character_bounds(actor.player, lo, hi) || !(hi[2] > lo[2])) return 4;
        for (int i = 0; i < MU_CHARACTER_ITEMS; ++i) {
            const mu_character_item *part = &actor.player->items[i];
            mu_renderchar_stats stats = {0};
            if (part->loaded && i == 0) {
                mu_renderchar_env env;
                mu_renderchar_default_env(&env);
                mu_render_backend backend = {0};
                backend.sink.texcoord = texcoord;
                backend.sink.color3 = backend.sink.vertex = vector;
                backend.sink.color4 = color;
                mu_draw_options options;
                mu_draw_default_options(&options);
                const float light[3] = {1.0f, 1.0f, 1.0f};
                if (mu_renderchar_draw_item(&part->model, &actor.player_glow[i], &env,
                    light, 1.0f, &options, &backend, NULL, &stats)) return 5;
            }
            printf("%s[%d,%d,%d,%d,%d,%ld,%ld]", i ? "," : "", part->loaded,
                actor.player_glow[i].type, actor.player_glow[i].level,
                part->bmd.mesh_count, part->textures.missing, stats.passes, stats.special);
        }
        mu_character_free(actor.player); free(actor.player);
    }
    printf("]}\n");
    mu_actor_free(&actor.actor); free(map);
    return 0;
}
