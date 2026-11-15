/* RENDER-ACTORS-007: batch actual asset, texture, plan and draw checks. */
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
        int admitted = mu_world_actor_plain_options(a, .375f, &options);
        mu_render_backend backend = {0}; backend.sink.vertex = vertex; backend.sink.texcoord = texcoord;
        backend.sink.color3 = color3; backend.sink.color4 = color4;
        vertices = 0; low = 2; high = -1; mu_draw_stats stats = {0};
        int status = mu_scene_draw_model(&a->actor.model, &options, &backend, &stats);
        /* Every mesh texture must be exactly the file in the opener's registered directory.
         * Reload it independently of actor storage, and compare upload bytes and sampler state. */
        mu_actor_group_body_plan plan = {0};
        if (!mu_actor_group_plan(cl, &plan)) {
            mu_world_actors_free(&actors); free(map);
            printf("{\"class\":%d,\"plan_unadmitted\":true}\n", cl);
            continue;
        }
        int plan_state_equal = options.select == plan.blend_mesh && options.skip_mesh == plan.hidden_mesh;
        uint32_t blend_bits; memcpy(&blend_bits, &options.color_scale, 4);
        plan_state_equal = plan_state_equal && blend_bits == plan.blend_light_bits &&
            !memcmp(a->actor.object + 0x60, &plan.subtype, 4) &&
            !memcmp(a->actor.object + 0x68, &plan.hidden_mesh, 4) &&
            !memcmp(a->actor.object + 0x74, &plan.blend_mesh, 4) &&
            !memcmp(a->actor.object + 0xa8, &plan.blend_light_bits, 4);
        int textures_equal = a->actor.textures.model_count == a->actor.bmd.mesh_count;
        uint32_t attached = 0;
        for (int k=0;k<2;++k) if (mu_world_actor_weapon(a,k)) attached |= 1u << k;
        int guards[4], guard_options[4];
        mu_draw_options refused, probe;
        memset(&refused, 0, sizeof refused);
        refused.select = 123; refused.skip_mesh = 456; refused.color_scale = .625f;
        refused.alpha = .625f; refused.flags = 0x1234; refused.texture = 17;
        memcpy(&probe, &refused, sizeof probe);
        a->actor.spec.model_index++;
        guards[0] = mu_world_actor_plain_options(a, .375f, &probe);
        guard_options[0] = !memcmp(&probe, &refused, sizeof probe);
        a->actor.spec.model_index--;
        memcpy(&probe, &refused, sizeof probe);
        float saved_scale = a->actor.spec.scale; a->actor.spec.scale += 1;
        guards[1] = mu_world_actor_plain_options(a, .375f, &probe);
        guard_options[1] = !memcmp(&probe, &refused, sizeof probe);
        a->actor.spec.scale = saved_scale;
        memcpy(&probe, &refused, sizeof probe);
        a->effect_count++;
        guards[2] = mu_world_actor_plain_options(a, .375f, &probe);
        guard_options[2] = !memcmp(&probe, &refused, sizeof probe);
        a->effect_count--;
        /* Invert one hand without loading or drawing a synthetic attachment. */
        static mu_world_actor_weapons phantom;
        mu_world_actor_weapons *saved_weapons = a->weapons;
        phantom.slots[0].loaded = !(plan.weapon_mask & 1u);
        phantom.slots[1].loaded = (plan.weapon_mask & 2u) != 0;
        a->weapons = &phantom;
        memcpy(&probe, &refused, sizeof probe);
        guards[3] = mu_world_actor_plain_options(a, .375f, &probe);
        guard_options[3] = !memcmp(&probe, &refused, sizeof probe);
        a->weapons = saved_weapons;

        for (int i = 0; i < a->actor.bmd.mesh_count; ++i) {
            char path[4096], directory[4096]; mu_image image = {0}; int8_t components = 0;
            snprintf(directory, sizeof directory, "%s/%s", argv[1], plan.textures);
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
        char result[4096];
        snprintf(result, sizeof result, "{\"class\":%d,\"model\":%d,\"scale\":%.9g,\"frame\":%.9g,\"file\":\"%s\","
            "\"missing\":%d,\"textures_equal\":%d,\"meshes\":%d,\"vertices\":%u,\"status\":%d,\"refused\":%ld,"
            "\"alpha\":[%.9g,%.9g],\"admitted\":%d,\"flags\":%u,\"attach\":%u,\"transform_translate\":%d,\"guards\":[%d,%d,%d,%d],\"guard_options\":[%d,%d,%d,%d],\"plan_state_equal\":%d}\n",
            cl, a->actor.spec.model_index, (double)a->actor.spec.scale, (double)mu_actor_frame(&a->actor),
            a->actor.spec.path + strlen(argv[1]) + 1, a->actor.textures.missing, textures_equal,
            a->actor.bmd.mesh_count, vertices, status, stats.refused, (double)low, (double)high, admitted,
            options.flags, attached, a->actor.model.params.transform_translate, guards[0], guards[1], guards[2], guards[3],
            guard_options[0], guard_options[1], guard_options[2], guard_options[3], plan_state_equal);
        mu_world_actors_free(&actors); free(map);
        /* A cleanup failure must leave this selector unreported to the batch. */
        fputs(result, stdout);
    }
    return 0;
}
