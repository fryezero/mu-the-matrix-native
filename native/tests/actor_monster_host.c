/* RENDER-ACTORS-005: production loading, both hand poses, draw and owner cleanup. */
#include "../core/mu_world_actors.c"

static unsigned vertices;
static float low = 2.0f, high = -1.0f;
static void texcoord(void *c, float u, float v) { (void)c; (void)u; (void)v; }
static void vertex(void *c, const float p[3]) { (void)c; (void)p; ++vertices; }
static void color3(void *c, const float p[3]) { (void)c; (void)p; }
static void color4(void *c, float r, float g, float b, float alpha)
{
    (void)c; (void)r; (void)g; (void)b;
    if (alpha < low) low = alpha;
    if (alpha > high) high = alpha;
}

int main(int argc, char **argv)
{
    if (argc != 5) return 2;
    mu_world *map = calloc(1, sizeof *map);
    mu_world_actors actors = {0}; actors.map = map; map->world = atoi(argv[3]);
    actors.list = calloc(1, sizeof *actors.list);
    char error[1024]; int cl = atoi(argv[2]);
    if (load_actor(&actors, actors.list, argv[1], cl, 128, 124, 5, 0, "DemoActor", 0, error, sizeof error)) {
        fprintf(stderr, "%s\n", error); free(actors.list); free(map); return 1;
    }
    actors.count = 1; mu_world_actor *a = actors.list;
    if (!a->weapons || a->player) return 3;
    mu_actor_set_action(&a->actor, atoi(argv[4]));
    for (int n = 0; n < 3; ++n) mu_actor_step(&a->actor, NULL);
    mu_world_actors_frame(&actors, .1f);
    mu_render_backend backend = {0}; backend.sink.texcoord = texcoord; backend.sink.vertex = vertex;
    backend.sink.color3 = color3; backend.sink.color4 = color4;
    mu_renderchar_env env; mu_renderchar_default_env(&env);
    printf("{\"class\":%d,\"model\":%d,\"scale\":%.9g,\"frame\":%.9g,\"body_missing\":%d,\"body_file\":\"%s\",\"weapons\":[",
        cl, a->actor.spec.model_index, (double)a->actor.spec.scale, (double)mu_actor_frame(&a->actor), a->actor.textures.missing, a->actor.spec.path + strlen(argv[1]) + 1);
    for (int k = 0; k < 2; ++k) {
        const mu_renderchar_attachment *p = mu_world_actor_weapon(a, k);
        if (!p) { printf("%snull", k ? "," : ""); continue; }
        /* Independent per-hand replay starts from an isolated body pose. This
         * catches the second hand reading the first weapon's overwritten bones. */
        mu_actor body; mu_renderchar_host host = {0}; mu_renderchar_attachment ref = {0};
        if (mu_actor_load(&body, &a->actor.spec, &a->actor.model.params, 1, error, sizeof error) ||
            mu_renderchar_host_init(&host, &body.model)) return 4;
        mu_model_set_state(&body.model, mu_actor_action(&a->actor), mu_actor_frame(&a->actor),
            mu_model_prior_frame(&a->actor.model), mu_model_prior_action(&a->actor.model));
        if (mu_actor_update(&body)) return 5;
        mu_monster_class row; mu_actor_monster_recipe(cl, &row);
        int32_t right = -1, left = -1; mu_renderchar_link_bones(row.model, &right, &left);
        mu_data_table table = {0}; char path[4096];
        snprintf(path, sizeof path, "%s/Data/Local/Item.bmd", argv[1]);
        if (mu_data_load(path, NULL, &table) || table.result.status) return 6;
        mu_item item; if (mu_item_model(&table, row.slots[6+k].type, &item) != 1) return 7;
        snprintf(path, sizeof path, "%s/%s%s", argv[1], item.folder, item.file);
        for (char *c = path; *c; ++c) if (*c == '\\') *c = '/';
        if (mu_renderchar_attach_load(&ref, &host, path, k ? left : right, 1, error, sizeof error) ||
            mu_renderchar_attach_update(&ref, &body.model, NULL, a->position, a->actor.spec.scale,
                a->actor.model.params.color)) return 8;
        int same = p->bmd.mesh_count == ref.bmd.mesh_count;
        for (int m = 0; m < p->bmd.mesh_count && same; ++m)
            same = !memcmp(mu_model_vertices(&p->model, m), mu_model_vertices(&ref.model, m),
                (size_t)p->bmd.meshes[m].vertex_count * 12);
        mu_draw_stats stats = {0}; unsigned before = vertices;
        if (mu_world_actor_weapon_draw(a, k, .375f, &env, &backend, &stats)) return 9;
        printf("%s{\"type\":%d,\"bone\":%d,\"missing\":%d,\"same_pose\":%d,\"vertices\":%u,\"refused\":%ld,\"file\":\"%s\"}",
            k ? "," : "", p->glow.type, p->bone, p->textures.missing, same, vertices-before,
            stats.refused, path + strlen(argv[1]) + 1);
        mu_data_free(&table); mu_renderchar_attach_free(&ref); mu_actor_free(&body); mu_renderchar_host_free(&host);
    }
    printf("],\"alpha\":[%.9g,%.9g],\"invalid\":[%d,%d]}\n", (double)low, (double)high,
        mu_world_actor_weapon_draw(a, -1, 1, &env, &backend, NULL),
        mu_world_actor_weapon_draw(a, 2, 1, &env, &backend, NULL));
    mu_world_actors_free(&actors);
    if (actors.list || actors.count) return 10;
    free(map); return 0;
}
