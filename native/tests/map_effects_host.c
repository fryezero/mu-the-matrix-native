/* RENDER-EFFECTS-008: the map-object effect table through the production loader (mu_map_effects), the attach
 * 0x0183067e and the objects runtime's per-frame update. argv[1]: an authored 21-bone model; argv[2]: a game root
 * whose Data/Effect holds synthetic fxa.ein and fxb.ein; argv[3]: a lang directory with a synthetic
 * mapeffects.tsv (test_native_map_effects.py writes all three). */
#include "../core/mu_map_effects.h"
#include "../core/mu_objects.h"
#include "../core/mu_particles.h"
#include "../core/mu_effect_scene.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { N = 8, STEPS = 30 };
static mu_object_model *model;

typedef struct placed {
    int type, hidden;
    float x;
} placed;

static mu_objects *start(int world, const placed *objects, int n, mu_object_record *rec)
{
    mu_objects *o = calloc(1, sizeof *o);
    memset(rec, 0, N * sizeof *rec);
    for (int i = 0; i < n; ++i) {
        rec[i].type = (int16_t)objects[i].type;
        rec[i].position[0] = objects[i].x; rec[i].position[1] = 1200.0f; rec[i].position[2] = 5;
        rec[i].scale = 1.5f;
        rec[i].flag_2c = 1; rec[i].flag_2d = 1; rec[i].flag_2e = 1;
        rec[i].hidden = (uint8_t)objects[i].hidden;
    }
    mu_objects_init(o, world);
    o->records = rec; o->count = n;
    assert(mu_objects_start(o, NULL) == 0);
    for (int i = 0; i < n; ++i) {
        o->models[objects[i].type] = model;
        o->rt.images[i * MU_OBJ_SIZE + MU_OBJF_VISIBLE] = 1;
        assert(o->rt.images[i * MU_OBJ_SIZE + 0x38] == 1);   /* Initialize 0x0129eb81 */
    }
    for (int s = 0; s < 256; ++s) o->rt.world.block_visible[s] = 1;
    return o;
}

static void run(mu_objects *o, int n, mu_world_particles *p, int steps)
{
    mu_objects_step_inputs in;
    memset(&in, 0, sizeof in);
    in.scene_state = 6;
    mu_draw_options options;
    for (int k = 0; k < steps; ++k) {
        in.time = 40.0f * (float)k;
        mu_objects_step(o, &in);
        for (int i = 0; i < n; ++i)
            (void)mu_objects_prepare_index(o, i, NULL, 6, &options);
        mu_world_particles_step(p, in.time);
    }
}

static void world(const mu_map_effects *table, const char *root, int id, const placed *objects, int n)
{
    mu_object_record rec[N];
    mu_world_particles p;
    char error[256];
    assert(mu_world_particles_open(&p, root, NULL, id, 0x1234u, 1, error, sizeof error) == 0);
    mu_objects *o = start(id, objects, n, rec);
    mu_world_particles_attach(&p, o, NULL);
    mu_map_effects_stats stats = {0};
    mu_map_effects_attach_world(table, id, o, &p, &stats);
    printf("{\"world\": %d, \"cleared\": %ld, \"requested\": %ld, \"invalid\": %ld, \"attached\": %ld, \"primed\": %ld,"
           " \"links\": [", id, stats.cleared, stats.requested, stats.invalid, stats.attached, stats.primed);
    for (int32_t q = 0; q < p.ein_link_count; ++q)
        printf("%s[%d, %d, %d, %d, %.1f]", q ? ", " : "", p.ein_links[q].object, p.ein_links[q].bone,
               p.ein_links[q].follow, p.ein_links[q].timed, (double)p.ein_links[q].template_scale);
    run(o, n, &p, STEPS);
    int external = 0, visible = 0;
    for (int32_t q = 0; q < p.ein_link_count; ++q) {
        const mu_effect_instance *inst = &p.ein->instances[p.ein_links[q].instance];
        external += inst->has_external;
        visible += inst->owner.visible;
    }
    printf("], \"updates\": %llu, \"unposed\": %llu, \"external\": %d, \"owner_visible\": %d, \"instances\": %u}\n",
           (unsigned long long)p.ein_updates, (unsigned long long)p.ein_unposed, external, visible,
           p.ein ? p.ein->instance_count : 0u);
    o->records = NULL;
    mu_objects_runtime_free(o);
    free(o);
    mu_world_particles_close(&p);
}

int main(int argc, char **argv)
{
    assert(argc == 4);
    model = calloc(1, sizeof *model);
    char error[256];
    assert(model && mu_bmd_load_file(argv[1], &model->bmd, error, sizeof error) == 0);
    assert(mu_model_init(&model->model, &model->bmd, NULL, error, sizeof error) == 0);
    model->loaded = 1;
    assert(!mu_map_effects_load(NULL) && !mu_map_effects_load("/nonexistent-map-effects"));
    mu_map_effects *table = mu_map_effects_load(argv[3]);
    assert(table);
    printf("{\"table\": true, \"worlds\": %d, \"types\": %d, \"entries\": %d}\n", table->world_count,
           table->type_count, table->entry_count);
    /* object 0 stands in sector 48, the rest in sector 0: the sector walk attaches 1..4 first */
    const placed deep[] = {{62, 1, 5000.0f}, {62, 1, 1000.0f}, {67, 1, 1040.0f}, {70, 0, 1080.0f}, {1, 0, 1120.0f}};
    world(table, argv[2], 118, deep, 5);       /* Deep Dungeon 3: RenderObjects' other-world path */
    const placed canyon[] = {{62, 1, 1000.0f}, {1, 0, 1040.0f}};
    world(table, argv[2], 131, canyon, 2);     /* Scorched Canyon: the primary RenderObjectVisual branch */
    world(table, argv[2], 7, canyon, 2);       /* a world the table does not hold */
    mu_map_effects_free(table);
    mu_model_free(&model->model);
    mu_bmd_free(&model->bmd);
    free(model);
    return 0;
}
