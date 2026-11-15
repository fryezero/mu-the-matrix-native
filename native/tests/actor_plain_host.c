/* RENDER-ACTORS-006: batch actual asset, texture, plan and draw checks. */
#include "../core/mu_world_actors.c"
static unsigned vertices;
static void texcoord(void *ctx, float u, float v) { (void)ctx; (void)u; (void)v; }
static float low, high;
static void vertex(void *ctx, const float p[3]) { (void)ctx; (void)p; ++vertices; }
static void color3(void *ctx, const float p[3]) { (void)ctx; (void)p; }
static void color4(void *ctx, float r, float g, float b, float alpha)
{ (void)ctx; (void)r; (void)g; (void)b; if (alpha < low) low = alpha; if (alpha > high) high = alpha; }
int main(int argc, char **argv)
{
    if (argc != 2) return 2;
    setvbuf(stdout, NULL, _IOLBF, 0);
    int cl;
    while (scanf("%d", &cl) == 1) {
        mu_world *map = calloc(1, sizeof *map);
        mu_world_actors actors = {0}; actors.map = map;
        actors.list = calloc(1, sizeof *actors.list);
        char error[1024] = {0};
        if (load_actor(&actors, actors.list, argv[1], cl, 128, 124, 5, 0, "DemoActor", 0, error, sizeof error)) {
            printf("{\"class\":%d,\"load_failed\":true}\n", cl);
            free(actors.list); free(map); continue;
        }
        actors.count = 1; mu_world_actor *a = actors.list;
        for (int n = 0; n < 3; ++n) mu_actor_step(&a->actor, NULL);
        mu_world_actors_frame(&actors, .1f);
        mu_draw_options options; mu_draw_default_options(&options);
        options.alpha = .375f; options.textures = &a->actor.textures;
#ifndef PLAIN_BOOTSTRAP
        int admitted = mu_world_actor_plain_options(a, .375f, &options);
#else
        int admitted = 1;
#endif
        mu_render_backend backend = {0}; backend.sink.vertex = vertex; backend.sink.texcoord = texcoord;
        backend.sink.color3 = color3; backend.sink.color4 = color4;
        vertices = 0; low = 2; high = -1; mu_draw_stats stats = {0};
        int status = mu_scene_draw_model(&a->actor.model, &options, &backend, &stats);
        /* Every mesh texture must be exactly the file in the opener's Monster directory.
         * Reload it independently of actor storage, and compare upload bytes and sampler state. */
        int textures_equal = a->actor.textures.model_count == a->actor.bmd.mesh_count;
        for (int i = 0; i < a->actor.bmd.mesh_count; ++i) {
            char path[4096], directory[4096]; mu_image image = {0}; int8_t components = 0;
            snprintf(directory, sizeof directory, "%s/Data/Monster", argv[1]);
            const char *name = a->actor.bmd.meshes[i].texture;
            const char *dot = strrchr(name, '.'); char kind = dot ? (char)tolower((unsigned char)dot[1]) : 0;
            if (!mu_image_resolve(directory, name, path, sizeof path) ||
                mu_texture_upload_file(path, kind, &image, &components, error, sizeof error)) textures_equal = 0;
            const mu_image *actual = a->actor.textures.slots[i];
            if (!actual || image.width != actual->width || image.height != actual->height ||
                components != a->actor.textures.components[i] || !actual->rgba || !image.rgba ||
                (image.rgba && actual->rgba && memcmp(image.rgba, actual->rgba, (size_t)image.width * (size_t)image.height * 4)) ||
                a->actor.textures.filter[i] != 0x2600 || a->actor.textures.wrap[i] != 0x2901) textures_equal = 0;
            mu_image_free(&image);
        }
        printf("{\"class\":%d,\"model\":%d,\"scale\":%.9g,\"frame\":%.9g,\"file\":\"%s\","
            "\"missing\":%d,\"textures_equal\":%d,\"meshes\":%d,\"vertices\":%u,\"status\":%d,\"refused\":%ld,"
            "\"alpha\":[%.9g,%.9g],\"admitted\":%d,\"flags\":%u,\"attach\":%d}\n",
            cl, a->actor.spec.model_index, (double)a->actor.spec.scale, (double)mu_actor_frame(&a->actor),
            a->actor.spec.path + strlen(argv[1]) + 1, a->actor.textures.missing, textures_equal,
            a->actor.bmd.mesh_count, vertices, status, stats.refused, (double)low, (double)high, admitted,
            options.flags, a->weapons != NULL || a->player != NULL || a->effect_count != 0);
        mu_world_actors_free(&actors); free(map);
    }
    return 0;
}
