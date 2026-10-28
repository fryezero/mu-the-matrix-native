/* RENDER-TIME-001: read-only, post-draw samples. No pointers or record images leave the process.
 * Included only by world_tool.c. Group checksums cover the ordered selected values, not struct padding. */
#ifndef MU_WORLD_TIME_SERIES_H
#define MU_WORLD_TIME_SERIES_H

static void time_values(const char *name, const double *v, int n)
{
    printf(",\"%s\":[", name);
    for (int i = 0; i < n; ++i) printf("%s%.12g", i ? "," : "", v[i]);
    printf("]");
}

static uint64_t time_hash(uint64_t h, const void *data, size_t n)
{
    const uint8_t *p = data;
    for (size_t i = 0; i < n; ++i) h = (h ^ p[i]) * UINT64_C(1099511628211);
    return h;
}

static void time_series_sample(const mu_world_rt *a, int frame, const uint8_t *rgba, const char *image_hash)
{
    const mu_hero *hero = &a->walk.hero;
    const mu_client_view *view = &a->walk.frame.view;
    double camera[] = {hero->position[0], hero->position[1], hero->position[2], hero->frame,
                       view->position[0], view->position[1], view->position[2], view->fov, view->angle[0]};
    printf("{\"time_series\":1,\"frame\":%d,\"world\":%d,\"world_time\":%.9g,\"steps\":%u",
           frame, a->world, (double)a->map->time, a->walk.steps);
    time_values("camera", camera, 9);
    /* Ordered sums plus a checksum preserve cancellation-sensitive changes. Object list order is native-only. */
    const int offsets[] = {MU_OBJF_FRAME, MU_OBJF_PRIOR_FRAME, MU_OBJF_ALPHA, MU_OBJF_BLEND_U,
        MU_OBJF_BLEND_V, MU_OBJF_BLEND_LIGHT, MU_OBJF_POSITION, MU_OBJF_POSITION+4, MU_OBJF_POSITION+8,
        MU_OBJF_ANGLE, MU_OBJF_ANGLE+4, MU_OBJF_ANGLE+8, MU_OBJF_LIGHT, MU_OBJF_LIGHT+4, MU_OBJF_LIGHT+8, MU_OBJF_TIMER};
    double objects[19] = {0};
    uint64_t oh = UINT64_C(14695981039346656037);
    for (int i = 0; a->has_objects && i < a->objects.count; ++i) {
        const uint8_t *o = a->objects.rt.images + i * MU_OBJ_SIZE;
        if (!o[MU_OBJF_LIVE]) continue;
        objects[0]++;
        uint16_t action; memcpy(&action, o + MU_OBJF_ACTION, sizeof action);
        objects[17] += o[MU_OBJF_VISIBLE]; objects[18] += action;
        oh = time_hash(oh, o + MU_OBJF_VISIBLE, 1);
        oh = time_hash(oh, &action, sizeof action);
        for (int k = 0; k < 16; ++k) {
            float f; memcpy(&f, o + offsets[k], sizeof f);
            objects[k+1] += f;
            oh = time_hash(oh, &f, sizeof f);
        }
    }
    time_values("objects", objects, 19);
    printf(",\"objects_hash\":\"%016llx\"", (unsigned long long)oh);
    double particles[10] = {0};
    uint64_t ph = UINT64_C(14695981039346656037);
    for (int i = 0; a->has_particles && i < a->particles.list.count; ++i) {
        const mu_pt_particle *p = &a->particles.list.records[i];
        if (!p->live) continue;
        const float f[] = {p->position[0], p->position[1], p->position[2], p->rotation, p->alpha,
                           p->scale, (float)p->lifetime, (float)p->type};
        particles[0]++;
        for (int k = 0; k < 8; ++k) particles[k+1] += f[k];
        ph = time_hash(ph, f, sizeof f);
    }
    particles[9] = a->particles.stats.live_effects;
    time_values("particles", particles, 10);
    printf(",\"particles_hash\":\"%016llx\"", (unsigned long long)ph);
    double environment[8] = {0};
    uint64_t eh = UINT64_C(14695981039346656037);
    for (int i = 0; a->has_env && i < MU_ENV_BOIDS + MU_ENV_FISHS; ++i) {
        const mu_env_object *o = i < MU_ENV_BOIDS ? &a->env.env.boids[i] : &a->env.env.fishs[i-MU_ENV_BOIDS];
        if (!o->live) continue;
        const float f[] = {o->position[0], o->position[1], o->position[2], o->frame, o->alpha};
        environment[0]++;
        for (int k = 0; k < 5; ++k) environment[k+1] += f[k];
        eh = time_hash(eh, f, sizeof f);
    }
    for (int i = 0; a->has_env && i < MU_ENV_LEAVES; ++i) {
        const mu_env_leaf *p = &a->env.env.leaves[i];
        if (!p->live) continue;
        environment[6]++; environment[7] += p->rotation;
        eh = time_hash(eh, p->position, sizeof p->position);
        eh = time_hash(eh, &p->rotation, sizeof p->rotation);
    }
    time_values("environment", environment, 8);
    printf(",\"environment_hash\":\"%016llx\"", (unsigned long long)eh);
    double lights[6] = {0};
    for (int i = 0; i < 3 * MU_TERRAIN_CELLS; ++i) {
        lights[i%3] += a->map->primary[i] / (double)MU_TERRAIN_CELLS;
        lights[3+i%3] += a->map->light[i] / (double)MU_TERRAIN_CELLS;
    }
    time_values("lights", lights, 6);
    uint64_t lh = time_hash(UINT64_C(14695981039346656037), a->map->primary, sizeof a->map->primary);
    lh = time_hash(lh, a->map->light, sizeof a->map->light);
    printf(",\"lights_hash\":\"%016llx\"", (unsigned long long)lh);
    uint8_t clear[4] = {0};
    if (a->has_env) mu_world_env_clear(&a->env, clear);
    double sky[] = {clear[0], clear[1], clear[2], a->particles.stats.live_joints};
    time_values("sky", sky, 4);
    double rng[] = {a->objects.rt.seed, a->env.env.rand_state, a->particles.rand_state,
                    (double)a->env.env.rand_calls, (double)a->particles.rand_calls};
    time_values("rng", rng, 5);
    /* 4x4 RGB means retain sky/lighting/motion evidence without writing frame dumps. */
    double image[48] = {0}; int counts[16] = {0};
    for (int y = 0; y < a->height; ++y) for (int x = 0; x < a->width; ++x) {
        int cell = (y * 4 / a->height) * 4 + x * 4 / a->width;
        size_t pixel = ((size_t)y * (size_t)a->width + (size_t)x) * 4;
        for (int c = 0; c < 3; ++c) image[3*cell+c] += rgba[pixel+(size_t)c];
        counts[cell]++;
    }
    for (int i = 0; i < 48; ++i) image[i] /= counts[i/3];
    time_values("image", image, 48);
    printf(",\"image_hash\":\"%s\"}\n", image_hash);
}
#endif
