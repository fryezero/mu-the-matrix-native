/* Item model textures. See mu_item_textures.h. */
#include "mu_item_textures.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../../reconstructed/items/ground_items.h"
#include "../../reconstructed/model-codec/character.h"
#include "../../reconstructed/objects/texture_lookup.h"
#include "../../reconstructed/renderchar/renderchar.h"
#include "mu_objects.h"
#include "mu_texture_names.h"

#define GL_NEAREST_ 0x2600u
#define GL_CLAMP_ 0x2900u

typedef struct item_bitmap {
    int32_t index;
    const char *path;
    uint32_t filter, wrap;
} item_bitmap;

#include "mu_item_bitmaps.inc"

int mu_item_bitmap_registration(int32_t index, const char **path, uint32_t *filter, uint32_t *wrap)
{
    for (size_t i = 0; i < sizeof item_bitmaps / sizeof item_bitmaps[0]; ++i)
        if (item_bitmaps[i].path && item_bitmaps[i].index == index) {
            *path = item_bitmaps[i].path;
            *filter = item_bitmaps[i].filter;
            *wrap = item_bitmaps[i].wrap;
            return 1;
        }
    return 0;
}

static int is_special(int32_t index)
{
    for (int k = 0; k < MU_TEXTURE_SPECIAL_COUNT; ++k)
        if (mu_texture_specials[k].index == index)
            return 1;
    return 0;
}

static void add_unique(int32_t *out, int32_t capacity, int32_t *count, int32_t index)
{
    if (index < 0 || is_special(index))
        return;
    for (int32_t i = 0; i < *count; ++i)
        if (out[i] == index)
            return;
    if (*count < capacity)
        out[*count] = index;
    ++*count;
}

static int32_t probe_random(void *context)
{
    (void)context;
    return 0;
}
static void probe_transform(void *context, int32_t bone, const float local[3], float out[3])
{
    (void)context;
    (void)bone;
    memcpy(out, local, 3 * sizeof *out);
}
static void probe_emit(void *context, const mu_rc_owner_fx *fx)
{
    (void)context;
    (void)fx;
}

int32_t mu_item_textures_overrides(int32_t type, const mu_data_table *items, int32_t *out, int32_t capacity)
{
    int32_t count = 0;
    mu_item record;
    const int has_record = items && type >= MU_ITEM_MODEL_BASE &&
                           mu_item_find(items, (uint32_t)(type - MU_ITEM_MODEL_BASE), &record) == 0;
    static const int32_t ext[] = {0, 5, 8};
    static const float times[] = {0.0f, 333.0f, 1000.0f, 2500.0f};
    const int rank5 = mu_rc_item_rank5(type);
    for (int32_t level = 0; level < 16; ++level)
        for (int32_t excellent = 0; excellent < 2; ++excellent)
            for (size_t e = 0; e < sizeof ext / sizeof ext[0]; ++e)
                for (int32_t lit = 0; lit < 2; ++lit)
                    for (size_t k = 0; k < sizeof times / sizeof times[0]; ++k)
                        for (int owner = 0; owner <= rank5; ++owner) {
                            mu_rc_item it;
                            memset(&it, 0, sizeof it);
                            it.type = type;
                            it.item_level = level << 3;
                            it.option1 = excellent;
                            it.ext_option = ext[e];
                            it.render_type = 2;
                            it.a10 = it.a11 = -1;
                            it.a12 = 3;
                            it.alpha = it.object_alpha = 1.0f;
                            it.blend_mesh = -1;
                            if (type >= 0x2322 && type <= 0x2327)
                                it.object_hidden = -1;   /* as mu_renderchar's fill_item */
                            it.time = times[k];
                            it.quality = 5;
                            for (int c = 0; c < 3; ++c)
                                it.light[c] = it.enchant[c] = 1.0f;
                            if (has_record) {
                                it.has_record = 1;
                                it.kind_a = record.attributes.kind_a;
                                it.kind_b = record.attributes.kind_b;
                                it.item_kind = record.attributes.type;
                            }
                            mu_rc_model m = {{1.0f, 1.0f, 1.0f}, 0, {1.0f, 1.0f, 1.0f}, 0, 0};
                            mu_rc_item_context context = {lit, rank5 ? 0 : -1, probe_random, NULL};
                            mu_rc_owner_host host = {36, 0, probe_transform, probe_random, probe_emit, NULL};
                            mu_rc_draw draws[48];
                            int32_t n = 0;
                            const int status = owner ? mu_rc_item_draws_owner(&it, &m, draws, 48, &n, &context, &host)
                                                     : mu_rc_item_draws_context(&it, &m, draws, 48, &n, &context);
                            if (status != MU_RC_OK)
                                continue;
                            for (int32_t i = 0; i < n && i < 48; ++i)
                                add_unique(out, capacity, &count, draws[i].texture);
                        }
    return count;
}

static int is_class_part(int32_t type)
{
    return type >= (int32_t)MU_CHARACTER_PART_BASE &&
           type < (int32_t)(MU_CHARACTER_PART_BASE + 5 * MU_CHARACTER_PART_STRIDE);
}

/* Special-model and class-part subfolders of the startup OpenTexture calls (0x0182cd66.., 0x0182bb43). */
static const char *startup_subfolder(int32_t type)
{
    char file[256];
    if (is_class_part(type))
        return "Player\\";
    if (!mu_gi_special_model_file(type, file, sizeof file))
        return NULL;
    return type == 0x38a2 ? "Monster\\" : "Item\\";
}

int mu_item_textures_load(mu_textures *t, const mu_bmd *model, const mu_data_table *items, const char *game_root,
                          int32_t type, const char *model_path, mu_item_textures_stats *stats)
{
    mu_item_textures_stats local;
    if (!stats)
        stats = &local;
    memset(stats, 0, sizeof *stats);
    mu_item record;
    const char *subfolder = startup_subfolder(type);
    const int item_rule = !subfolder && items && mu_item_model(items, type, &record) == 1;
    char effects[2048];
    if (!game_root || (!subfolder && !item_rule) || !mu_objects_resolve(game_root, "Data/Effect", effects, sizeof effects)) {
        char directory[2048];
        mu_path_directory(model_path, directory, sizeof directory);
        if (mu_textures_load(t, model, directory))
            return 1;
        stats->missing_meshes = t->missing;
    } else {
        stats->rule = item_rule ? MU_ITEM_RULE_ITEM : MU_ITEM_RULE_OPEN_TEXTURE;
        if (mu_textures_load_specials(t, model, effects))
            return 1;
        for (int32_t k = 0; k < model->mesh_count; ++k) {
            char file[4096];
            int step = 0;
            int32_t texture_type = 0, special = 0;
            const int found = mu_texture_names_item(game_root, item_rule ? record.folder : NULL, subfolder,
                                                    model->meshes[k].texture, file, sizeof file, &texture_type,
                                                    &special, &step);
            if (special) {
                if (!t->client_index && !(t->client_index = calloc((size_t)t->model_count, sizeof *t->client_index)))
                    return 1;
                t->client_index[k] = special;
                stats->special_meshes++;
            }
            stats->typed_meshes += texture_type != 0;
            if (found && mu_textures_set_file(t, model, k, file) == 0) {
                if (item_rule) {   /* LoadImage(path, GL_NEAREST, GL_CLAMP) 0x00cd5b50 */
                    t->filter[k] = GL_NEAREST_;
                    t->wrap[k] = GL_CLAMP_;
                }
                stats->name_map += step == MU_TL_NAME_MAP;
            } else if (found || step != MU_TL_DIRECT) {   /* a special name answers DIRECT without a file */
                stats->missing_meshes++;
            }
        }
        t->missing = stats->missing_meshes;
    }
    int32_t want[64];
    const int32_t n = mu_item_textures_overrides(type, items, want, 64);
    stats->bitmaps = n;
    for (int32_t i = 0; i < n && i < 64; ++i) {
        const char *path;
        uint32_t filter, wrap;
        char relative[512], directory[2048];
        const char *name = NULL;
        int ok = 0;
        if (game_root && mu_item_bitmap_registration(want[i], &path, &filter, &wrap)) {
            snprintf(relative, sizeof relative, "Data/%s", path);
            for (char *p = relative; *p; ++p)
                if (*p == '\\')
                    *p = '/';
            char *slash = strrchr(relative, '/');
            *slash = 0;
            name = slash + 1;
            if (mu_objects_resolve(game_root, relative, directory, sizeof directory)) {
                const char *dirs[1] = {directory};
                const char *names[1] = {name};
                if (mu_textures_add_extras(t, &want[i], dirs, names, 1, filter, wrap))
                    return 1;
                ok = t->slots[t->count - 1] != NULL;
            }
        }
        if (!ok) {
            if (stats->missing_bitmaps < MU_ITEM_TEXTURES_REPORT)
                stats->missing_index[stats->missing_bitmaps] = want[i];
            stats->missing_bitmaps++;
        }
    }
    return 0;
}
