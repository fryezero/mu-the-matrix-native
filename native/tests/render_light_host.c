/* RENDER-WORLDS-AFTER4: the after pass's render-time AddTerrainLight (Kardamahal 143 type 0x71, slot 0x3c
 * 0x00e118fd) lands in the map's frame light; without a map it is refused and counted. Production runtime. */
#include <assert.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>
#include "../core/mu_objects.h"
#include "../core/mu_terrain.h"

static const char *model_path;

static mu_objects *kardamahal(void)
{
    mu_objects *o = calloc(1, sizeof *o);
    assert(o);
    o->world = 143;
    o->rt.ready = 1;
    o->count = 1;
    o->rt.images = calloc(1, MU_OBJ_SIZE);
    assert(o->rt.images);
    uint8_t *img = o->rt.images;
    img[MU_OBJF_LIVE] = 1;
    mu_obj_set_i32(img, MU_OBJF_TYPE, 0x71);
    mu_obj_set_i32(img, MU_OBJF_HIDDEN_MESH, -1);
    mu_obj_set_f32(img, MU_OBJF_ALPHA, 1.0f);
    mu_obj_set_f32(img, MU_OBJF_SCALE, 1.0f);
    mu_obj_set_f32(img, MU_OBJF_POSITION, 3050.0f);       /* tile (30, 40) */
    mu_obj_set_f32(img, MU_OBJF_POSITION + 4, 4040.0f);
    o->rt.after_list = calloc(1, sizeof(int32_t));
    o->rt.after_count = 1;
    memset(o->rt.stream, 0xff, sizeof o->rt.stream);
    mu_object_model *m = calloc(1, sizeof *m);
    char error[256];
    assert(m && mu_bmd_load_file(model_path, &m->bmd, error, sizeof error) == 0);
    assert(mu_model_init(&m->model, &m->bmd, NULL, error, sizeof error) == 0);
    m->loaded = 1;
    o->models[0x71] = m;
    return o;
}

static void release(mu_objects *o)
{
    mu_model_free(&o->models[0x71]->model);
    mu_bmd_free(&o->models[0x71]->bmd);
    free(o->models[0x71]);
    free(o->rt.after_list);
    free(o->rt.images);
    free(o);
}

int main(int argc, char **argv)
{
    assert(argc > 1);
    model_path = argv[1];
    mu_world *map = calloc(1, sizeof *map);
    assert(map);
    mu_objects *o = kardamahal();
    mu_object_mesh meshes[8];
    int32_t count = -1;
    mu_objects_prepare_after(o, 0, map, 6, meshes, 8, &count);
    assert(o->rt.render_light_events == 1 && o->rt.draw_unsupported == 0 && count == 0);
    /* L = (rand() % 4 + 3) * 0.1 * 0.4 + 0.4 for rand() in 0..3 gives 0.52..0.64; light (L, 0.2 L, 0.1 L) */
    const float *cell = map->light;
    for (int32_t c = 0; c < 256 * 256; ++c)   /* the brightest cell: the light's centre */
        if (map->light[3 * c] > cell[0])
            cell = &map->light[3 * c];
    assert(cell != map->light || cell[0] > 0.0f);
    {
        const int32_t c = (int32_t)(cell - map->light) / 3;   /* within a tile of (30, 40) either way round */
        const int32_t a = c % 256, b = c / 256;
        assert((abs(a - 30) <= 1 && abs(b - 40) <= 1) || (abs(a - 40) <= 1 && abs(b - 30) <= 1));
    }
    assert(cell[0] > 0.0f && fabsf(cell[1] - 0.2f * cell[0]) < 1e-5f && fabsf(cell[2] - 0.1f * cell[0]) < 1e-5f);
    float before = cell[0];
    mu_objects_prepare_after(o, 0, map, 6, meshes, 8, &count);   /* a second frame without a copy adds again */
    assert(o->rt.render_light_events == 2 && cell[0] > before);
    release(o);
    o = kardamahal();
    mu_objects_prepare_after(o, 0, NULL, 6, meshes, 8, &count);   /* no light grid: refused and counted */
    assert(o->rt.render_light_events == 0 && o->rt.draw_unsupported == 1);
    release(o);
    free(map);
    return 0;
}
