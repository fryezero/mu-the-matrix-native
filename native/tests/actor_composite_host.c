/* RENDER-ACTORS-004: production composite loading, animation, draw and cleanup. */
#include "../core/mu_world_actors.c"

static unsigned vertices;
static float min_alpha = 2.0f, max_alpha = -1.0f;
static void texcoord(void *c, float u, float v) { (void)c; (void)u; (void)v; }
static void vertex(void *c, const float p[3]) { (void)c; (void)p; ++vertices; }
static void color3(void *c, const float p[3]) { (void)c; (void)p; }
static void color4(void *c, float r, float g, float b, float alpha)
{
    (void)c; (void)r; (void)g; (void)b;
    if (alpha < min_alpha) min_alpha = alpha;
    if (alpha > max_alpha) max_alpha = alpha;
}
int main(int argc, char **argv)
{
    if (argc != 4) return 2;
    mu_world *map = calloc(1, sizeof *map);
    mu_world_actors actors = {0};
    actors.map = map; map->world = atoi(argv[3]);
    actors.list = calloc(1, sizeof *actors.list);
    char error[1024]; int cl = atoi(argv[2]);
    if (load_actor(&actors, actors.list, argv[1], cl, 128, 124, 5, 0, "DemoActor", 0, error, sizeof error)) {
        fprintf(stderr, "%s\n", error); free(actors.list); free(map); return 1;
    }
    actors.count = 1; mu_world_actor *a = actors.list;
    if (!a->player || !mu_actor_npc_recipe(cl, NULL)) return 3;
    mu_world_actors_frame(&actors, .1f);
    float initial = mu_model_frame(&a->player->player);
    for (int i = 0; i < 3; ++i) actor_step(&actors, a);
    mu_world_actors_frame(&actors, .1f);
    float frame = mu_model_frame(&a->player->player);
    float lo[3], hi[3];
    if (!mu_character_bounds(a->player, lo, hi)) return 4;
    printf("{\"class\":%d,\"base_model\":%d,\"base_meshes\":%d,\"scale\":%.9g,\"initial\":%.9g,\"frame\":%.9g,\"actor_frame\":%.9g,\"height\":%.9g,\"slots\":[",
        cl, a->actor.spec.model_index, a->actor.bmd.mesh_count, (double)a->actor.spec.scale,
        (double)initial, (double)frame, (double)mu_actor_frame(&a->actor), (double)(hi[2]-lo[2]));
    mu_render_backend backend = {0};
    backend.sink.texcoord = texcoord; backend.sink.vertex = vertex;
    backend.sink.color3 = color3; backend.sink.color4 = color4;
    for (int k = 5; k >= 0; --k) {
        const mu_character_item *p = &a->player->items[k];
        mu_draw_stats stats = {0};
        unsigned before = vertices;
        if (p->loaded && mu_world_actor_npc_part_draw(a, k, .375f, &backend, &stats)) return 5;
        printf("%s[%d,%d,%d,%d,%u,\"%s\"]", k == 5 ? "" : ",", k, p->loaded, a->player_glow[k].type,
            p->textures.missing, vertices-before, p->loaded ? p->path + strlen(argv[1]) + 1 : "");
    }
    printf("],\"alpha\":[%.9g,%.9g],\"refused\":[%d,%d]}\n", (double)min_alpha, (double)max_alpha,
        mu_world_actor_npc_part_draw(a, -1, 1, &backend, NULL),
        mu_world_actor_npc_part_draw(a, 6, 1, &backend, NULL));
    mu_world_actors_free(&actors); free(map); return 0;
}
