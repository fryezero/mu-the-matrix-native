/* RENDER-EFFECTS-006: the requests the world lanes refused, through the production objects runtime and the
 * production particle/effect module (mu_world_particles, no bitmaps). argv[1]: an authored 21-bone, 3-action
 * model; argv[2]: a game root whose Data/Effect holds the four 136 .ein names (synthetic), argv[3] one without.
 *
 * Each world runs twice: without consumers (the lanes' state: refused and counted) and with the module
 * attached (the refusal counters stay at 0, the effects live in the pool with their owner, and their own
 * particles are native kinds: nothing unsupported, nothing approximated). */
#include "../core/mu_objects.h"
#include "../core/mu_particles.h"
#include "../core/mu_effect_scene.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { N = 8, STEPS = 400 };
static mu_object_model *model;

static mu_objects *start(int world, const int *types, int n, mu_object_record *rec)
{
    mu_objects *o = calloc(1, sizeof *o);
    memset(rec, 0, N * sizeof *rec);
    for (int i = 0; i < n; ++i) {
        rec[i].type = (int16_t)types[i];
        rec[i].position[0] = 1000.0f + 40.0f * (float)i; rec[i].position[1] = 1200.0f; rec[i].position[2] = 5;
        rec[i].scale = 1.5f;
        rec[i].flag_2c = 1; rec[i].flag_2d = 1; rec[i].flag_2e = 1;
    }
    mu_objects_init(o, world);
    o->records = rec; o->count = n;
    assert(mu_objects_start(o, NULL) == 0);
    for (int i = 0; i < n; ++i) {
        o->models[types[i]] = model;
        o->rt.images[i * MU_OBJ_SIZE + MU_OBJF_VISIBLE] = 1;
    }
    for (int s = 0; s < 256; ++s) o->rt.world.block_visible[s] = 1;
    return o;
}

static void finish(mu_objects *o)
{
    o->records = NULL;
    mu_objects_runtime_free(o);
    free(o);
}

/* MoveObjects, the visual pass of every object, then MoveEffects/MoveParticles (the in-world tick order). */
static void run(mu_objects *o, int n, mu_world_particles *p, int steps)
{
    mu_objects_step_inputs in;
    memset(&in, 0, sizeof in);
    in.scene_state = 6;
    mu_draw_options options;
    for (int k = 0; k < steps; ++k) {
        in.time = 3.0f * (float)k;   /* (int)WorldTime % 1024 < 30 recurs (Gray Aida 0x46) */
        mu_objects_step(o, &in);
        for (int i = 0; i < n; ++i)
            (void)mu_objects_prepare_index(o, i, NULL, 6, &options);
        if (p)
            mu_world_particles_step(p, in.time);
    }
}

typedef struct world_case {
    int world, types[N], n, kind, sub;
} world_case;

static const world_case cases[] = {
    {91, {57, 1, 2}, 3, 0x59a, 3},          /* Acheron 57 (RENDER-WORLDS-Q) */
    {122, {83, 176, 1}, 3, 0x59a, 3},       /* Swamp of Darkness 83 (0x59a) and 176 (0x199) */
    {123, {161, 1}, 2, 0x195, 0},           /* Kubera 161 */
    {134, {0x46, 1}, 2, 0x199, 0},          /* Gray Aida 0x46 (RENDER-WORLDS-R) */
    {142, {196, 1}, 2, 0x199, 0},           /* Twisted Karutan 196 (RENDER-WORLDS-R2) */
    {143, {161, 1}, 2, 0x195, 0},           /* Kardamahal 161 */
    {144, {185, 1}, 2, 0x199, 1},           /* Swamp of Destruction 185 */
    {0x87, {0xa5, 15, 1}, 3, 0x59a, 3},     /* Old Kethotum 0xa5 (RENDER-WORLDS-P) and 15's two particle kinds */
};

static int live_of(const mu_world_particles *p, int32_t type, int32_t sub, int32_t *owner_ok, int n)
{
    int live = 0;
    for (int i = 0; i < MU_WORLD_FX_EFFECTS; ++i)
        if (p->effects[i].live && p->effects[i].type == type && p->effects[i].subtype == sub) {
            ++live;
            *owner_ok &= p->effects[i].owner >= 0 && p->effects[i].owner < n;
        }
    return live;
}

static void owned_effects(const char *root)
{
    for (size_t c = 0; c < sizeof cases / sizeof cases[0]; ++c) {
        const world_case *w = &cases[c];
        mu_object_record rec[N];
        /* the lanes' state: no consumer, every request refused and counted */
        mu_objects *o = start(w->world, w->types, w->n, rec);
        run(o, w->n, NULL, STEPS);
        const long refused_before = o->rt.draw_unsupported, events_before = o->rt.effect_events;
        finish(o);
        /* with the production module */
        mu_world_particles p;
        char error[256];
        assert(mu_world_particles_open(&p, root, NULL, w->world, 0x1234u, 1, error, sizeof error) == 0);
        o = start(w->world, w->types, w->n, rec);
        mu_world_particles_attach(&p, o, NULL);
        int owners_ok = 1, peak = 0;
        for (int k = 0; k < STEPS; ++k) {
            run(o, w->n, &p, 1);
            const int live = live_of(&p, w->kind, w->sub, &owners_ok, w->n);
            if (live > peak) peak = live;
        }
        printf("{\"world\": %d, \"kind\": \"%#x/%d\", \"refused_before\": %ld, \"effect_events_before\": %ld,"
               " \"refused_after\": %ld, \"effect_events\": %ld, \"effects_created\": %llu,"
               " \"effects_unsupported\": %llu, \"peak_live\": %d, \"particles\": %llu, \"particles_unsupported\": %llu}\n",
               w->world, w->kind, w->sub, refused_before, events_before, o->rt.draw_unsupported, o->rt.effect_events,
               (unsigned long long)p.stats.effects_created, (unsigned long long)p.stats.effects_unsupported, peak,
               (unsigned long long)p.stats.created, (unsigned long long)p.stats.unsupported);
        /* the refusals are gone and the requests are effects in the pool, owned by their objects */
        if (w->world != 0x87)
            assert(refused_before > 0 && events_before == 0);
        assert(o->rt.draw_unsupported == 0);
        assert(o->rt.effect_events > 0 && p.stats.effects_created > 0 && p.stats.effects_unsupported == 0);
        assert(peak > 0 && owners_ok);
        assert(p.stats.unsupported == 0);   /* 0x7ef7/9, 0x7f25/15, 0x7efa/2, 0x7f26/14 are native kinds */
        finish(o);
        mu_world_particles_close(&p);
    }
}

/* 136 type 0xb5: the four red .ein requests, attach on bone 20 with the glow flag as the owner's visibility. */
static void ein_requests(const char *root, int valid)
{
    static const int types[] = {0xb5, 1};
    mu_object_record rec[N];
    mu_objects *o = start(0x88, types, 2, rec);
    run(o, 2, NULL, 5);
    const long refused_before = o->rt.move_unsupported;
    finish(o);
    mu_world_particles p;
    char error[256];
    assert(mu_world_particles_open(&p, root, NULL, 0x88, 0x1234u, 1, error, sizeof error) == 0);
    o = start(0x88, types, 2, rec);
    mu_world_particles_attach(&p, o, NULL);
    int glowing = 0;
    for (int k = 0; k < STEPS; ++k) {
        run(o, 2, &p, 1);
        if (!valid)
            continue;
        const uint8_t *img = o->rt.images;
        for (int32_t q = 0; q < p.ein_link_count; ++q) {
            const mu_effect_instance *inst = &p.ein->instances[p.ein_links[q].instance];
            assert(inst->owner.visible == img[0x38] && inst->owner.action == mu_obj_u16(img, MU_OBJF_ACTION));
            assert(inst->has_external);
            glowing += img[0x38] != 0;
        }
    }
    printf("{\"ein\": %d, \"refused_before\": %ld, \"refused_after\": %ld, \"requests\": %llu, \"invalid\": %llu,"
           " \"attached\": %llu, \"updates\": %llu, \"unposed\": %llu, \"glowing_updates\": %d}\n",
           valid, refused_before, o->rt.move_unsupported, (unsigned long long)p.ein_requests,
           (unsigned long long)p.ein_invalid, (unsigned long long)p.ein_attached, (unsigned long long)p.ein_updates,
           (unsigned long long)p.ein_unposed, glowing);
    assert(refused_before == 5);   /* one counted refusal per move step without a consumer */
    if (valid) {
        /* four factory results, one attach each, no further request (the list is not empty) */
        assert(o->rt.move_unsupported == 0 && p.ein_requests == 4 && p.ein_invalid == 0 && p.ein_attached == 4);
        assert(p.ein && p.ein->instance_count == 4 && p.ein_link_count == 4);
        for (int32_t q = 0; q < 4; ++q)
            assert(p.ein_links[q].object == 0 && p.ein_links[q].bone == 20 && p.ein_links[q].follow == 1 &&
                   p.ein_links[q].timed == 0);
        assert(p.ein_updates == 4u * STEPS && p.ein_unposed == 0 && glowing > 0);
        /* the scale is template scale x object scale every frame: fire09-red01 asked for 35 */
        assert(p.ein->instances[p.ein_links[0].instance].fx.scale == 35.0f * 1.5f);
        /* bone 20 missing: no stale matrix, counted */
        const int32_t bones = model->bmd.bone_count;
        model->bmd.bone_count = 20;
        run(o, 2, &p, 1);
        assert(p.ein_unposed == 4);
        model->bmd.bone_count = bones;
    } else {
        /* the factory fails for every path: requested again each step, refused and counted, nothing created */
        assert(o->rt.move_unsupported == STEPS && p.ein_attached == 0 && (!p.ein || p.ein->instance_count == 0));
        assert(p.ein_requests == 4u * STEPS && p.ein_invalid == 4u * STEPS);
    }
    finish(o);
    mu_world_particles_close(&p);
}

int main(int argc, char **argv)
{
    assert(argc == 4);
    model = calloc(1, sizeof *model);
    char error[256];
    assert(model && mu_bmd_load_file(argv[1], &model->bmd, error, sizeof error) == 0);
    assert(model->bmd.bone_count == 21);
    assert(mu_model_init(&model->model, &model->bmd, NULL, error, sizeof error) == 0);
    model->loaded = 1;
    owned_effects(argv[3]);
    ein_requests(argv[2], 1);
    ein_requests(argv[3], 0);
    mu_model_free(&model->model);
    mu_bmd_free(&model->bmd);
    free(model);
    return 0;
}
