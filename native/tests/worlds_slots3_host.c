/* RENDER-WORLDS-SLOTS3: RenderObjectVisual's outer rand() % 30 (0x017f9797) in the production first pass of the
 * worlds without a class and Tormenta 141, with the world particle module attached: one draw of the object
 * generator for an object with a model (none without), before the world's own visual; the particle visual reads
 * that value (Lorencia's MerchantAnimal flares) and draws only its branches' own rand() calls from the particle
 * generator. Production runtime. */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../core/mu_objects.h"
#include "../core/mu_particles.h"

static mu_world_particles p;
static mu_object_model model;

static uint32_t msvc_next(uint32_t seed) { return seed * 214013u + 2531011u; }

/* one pass over one object of `type` in `world`; returns the object generator's draws (seed 1 before) */
static int object_draws(mu_objects *o, int32_t world, int32_t type, int with_model, uint64_t *particle_draws)
{
    uint8_t *img = o->rt.images;
    memset(img, 0, MU_OBJ_SIZE);
    img[MU_OBJF_LIVE] = 1;
    mu_obj_set_i32(img, MU_OBJF_TYPE, type);
    mu_obj_set_i32(img, MU_OBJF_HIDDEN_MESH, -1);
    mu_obj_set_i32(img, MU_OBJF_BLEND_MESH, -1);
    mu_obj_set_f32(img, MU_OBJF_ALPHA, 1.0f);
    mu_obj_set_f32(img, MU_OBJF_SCALE, 1.0f);
    mu_obj_set_f32(img, MU_OBJF_POSITION, 3050.0f);
    mu_obj_set_f32(img, MU_OBJF_POSITION + 4, 4040.0f);
    memset(o->models, 0, sizeof o->models);
    if (with_model)
        o->models[type] = &model;
    o->world = p.world = world;
    o->rt.seed = 1;
    mu_pt_system_clear(&p.list);
    memset(p.sprites, 0, sizeof *p.sprites);
    const uint64_t calls = p.rand_calls;
    mu_draw_options options;
    (void)mu_objects_prepare_index(o, 0, NULL, 6, &options);
    *particle_draws = p.rand_calls - calls;
    int draws = 0;
    for (uint32_t s = 1; s != o->rt.seed && draws < 64; s = msvc_next(s))
        ++draws;
    return draws;
}

int main(int argc, char **argv)
{
    assert(argc > 1);
    char error[256];
    assert(mu_bmd_load_file(argv[1], &model.bmd, error, sizeof error) == 0);
    assert(mu_model_init(&model.model, &model.bmd, NULL, error, sizeof error) == 0);
    model.loaded = 1;
    assert(mu_world_particles_open(&p, NULL, NULL, 0, 7, 1, error, sizeof error) == 0);
    mu_objects *o = calloc(1, sizeof *o);
    assert(o);
    o->count = 1;
    o->rt.ready = 1;
    o->rt.images = calloc(1, MU_OBJ_SIZE);
    assert(o->rt.images);
    mu_world_particles_attach(&p, o, NULL);
    int failures = 0;
    /* worlds without a class (their own visual: none, the particle visual, Icarus' cover, the Kanturu flames, the
     * built-in Lost Tower/Atlans/Tarkan visual) and Tormenta 141; type 250 is named by none of their branches */
    static const int32_t worlds[] = {0, 1, 2, 3, 4, 6, 7, 8, 9, 10, 11, 18, 24, 30, 33, 34, 37, 38, 40, 41, 46, 51,
                                     56, 65, 73, 74, 98, 102, 141};
    for (size_t k = 0; k < sizeof worlds / sizeof worlds[0]; ++k)
        for (int with_model = 0; with_model <= 1; ++with_model) {
            uint64_t particle;
            const int draws = object_draws(o, worlds[k], 250, with_model, &particle);
            if (draws != with_model || particle != 0) {
                fprintf(stderr, "world %d model %d: %d object draws, %llu particle draws\n", worlds[k], with_model,
                        draws, (unsigned long long)particle);
                ++failures;
            }
        }
    uint64_t particle;
    /* Lorencia MerchantAnimal01 0x38: two flares at scale l * 5, l from the object generator's outer draw */
    int draws = object_draws(o, 0, 0x38, 1, &particle);
    const float l = (float)((int32_t)((msvc_next(1) >> 16) & 0x7fff) % 30 + 70) * 0.01f;
    assert(draws == 1 && particle == 0 && p.sprites->created == 2);
    assert(p.sprites->records[0].scale == l * 5.0f && p.sprites->records[0].light[0] == l * 0.6f);
    /* Waterspout01 0x69: the particle generator draws its own rand % 2 (and the puffs' offsets) only */
    draws = object_draws(o, 0, 0x69, 1, &particle);
    assert(draws == 1 && (particle == 1 || particle >= 5));
    /* Tormenta 141 type 2: the slot's rand % 50 is the particle generator's only draw */
    draws = object_draws(o, 141, 2, 1, &particle);
    assert(draws == 1 && particle == 1);
    /* Kanturu 37 type 0x3b: the outer draw, then the flame's rand % 3, both from the object generator */
    draws = object_draws(o, 37, 0x3b, 1, &particle);
    assert(draws == 2 && particle == 0);
    o->rt.images[0] = 0;
    p.objects = NULL;
    mu_world_particles_close(&p);
    free(o->rt.images);
    free(o);
    mu_model_free(&model.model);
    mu_bmd_free(&model.bmd);
    return failures != 0;
}
