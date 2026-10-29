/* Item model textures. See mu_item_textures.h. */
#include "mu_item_textures.h"

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>

#include "../../reconstructed/items/ground_items.h"
#include "../../reconstructed/model-codec/character.h"
#include "../../reconstructed/objects/texture_lookup.h"
#include "../../reconstructed/renderchar/renderchar.h"
#include "mu_objects.h"
#include "mu_texture_names.h"

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

static int has_extra(const mu_textures *t, int32_t index)
{
    for (int32_t j = 0; j < t->extra_count; ++j)
        if (t->extra_index[j] == index)
            return 1;
    return 0;
}

/* Adds the LoadBitmap registration of client bitmap `index` (mu_item_bitmaps.inc) as an extra bitmap. Returns 0
 * when added (its slot may stay empty when the file is not installed), 1 out of memory, -1 not registered. */
static int add_registered(mu_textures *t, const char *game_root, int32_t index)
{
    const char *path;
    uint32_t filter, wrap;
    char relative[512], directory[2048];
    if (!game_root || !mu_item_bitmap_registration(index, &path, &filter, &wrap))
        return -1;
    snprintf(relative, sizeof relative, "Data/%s", path);
    for (char *p = relative; *p; ++p)
        if (*p == '\\')
            *p = '/';
    char *slash = strrchr(relative, '/');
    *slash = 0;
    const char *name = slash + 1;
    if (!mu_objects_resolve(game_root, relative, directory, sizeof directory))
        return -1;
    const char *dirs[1] = {directory};
    const char *names[1] = {name};
    return mu_textures_add_extras(t, &index, dirs, names, 1, filter, wrap) ? 1 : 0;
}

/* The skin bitmaps the mesh draw substitutes (0x012b8e78..): base + model +0xa4. */
static const int32_t skin_bases[] = {0x7725, 0x7776, 0x77c7, 0x7818, 0x7869, 0x78ba};

int mu_item_textures_wear_shift(mu_textures *t, const char *game_root, int8_t shift)
{
    t->skin_shift = shift;
    if (!t->client_index)
        return 0;
    for (size_t b = 0; b < sizeof skin_bases / sizeof skin_bases[0]; ++b) {
        int used = 0;
        for (int32_t k = 0; k < t->model_count && !used; ++k)
            used = t->client_index[k] == skin_bases[b];
        const int32_t index = skin_bases[b] + shift;
        if (used && !has_extra(t, index) && add_registered(t, game_root, index) == 1)
            return 1;
    }
    return 0;
}

int mu_item_textures_is_part(int32_t type)
{
    return (type >= MU_ITEM_MODEL_BASE + 7 * 512 && type < MU_ITEM_MODEL_BASE + 12 * 512) || is_class_part(type);
}

int mu_item_textures_wear(mu_textures *t, const char *game_root, uint8_t class_byte)
{
    return mu_item_textures_wear_shift(t, game_root, (int8_t)mu_character_skin_index(class_byte));
}

int mu_item_textures_reload(mu_textures *t, const mu_bmd *model, const mu_data_table *items, const char *game_root,
                            int32_t type, const char *model_path)
{
    if (!game_root || type < 0)
        return 0;
    mu_textures fresh;
    memset(&fresh, 0, sizeof fresh);
    mu_item_textures_stats stats;
    if (mu_item_textures_load(&fresh, model, items, game_root, type, model_path, &stats) == 0 &&
        stats.rule != MU_ITEM_RULE_FOLDER) {
        mu_textures_free(t);
        *t = fresh;
        return 1;
    }
    mu_textures_free(&fresh);
    return 0;
}

int mu_item_textures_character(mu_character *c, int slot, const mu_data_table *items, const char *game_root,
                               int32_t type, int32_t class_byte)
{
    if (slot < 0 || slot >= MU_CHARACTER_ITEMS || !c->items[slot].loaded)
        return 0;
    mu_character_item *item = &c->items[slot];
    mu_item_textures_reload(&item->textures, &item->bmd, items, game_root, type, item->path);
    if (slot >= MU_PART_HELM && slot <= MU_PART_BOOTS && class_byte >= 0)
        return mu_item_textures_wear(&item->textures, game_root, (uint8_t)class_byte);
    return 0;
}

static int same_path(const char *a, const char *b)
{
    for (;; ++a, ++b) {
        const int x = *a == '\\' ? '/' : tolower((unsigned char)*a);
        const int y = *b == '\\' ? '/' : tolower((unsigned char)*b);
        if (x != y)
            return 0;
        if (!x)
            return 1;
    }
}

int32_t mu_item_textures_type_of_path(const mu_data_table *items, const char *game_root, const char *path)
{
    if (!path)
        return -1;
    const size_t n = items ? mu_item_count(items) : 0;
    for (size_t i = 0; i < n && game_root; ++i) {
        mu_item record;
        char file[2048];
        if (mu_item_get(items, i, &record))
            continue;
        snprintf(file, sizeof file, "%s/%s%s", game_root, record.folder, record.file);
        if (same_path(file, path))
            return (int32_t)record.code + MU_ITEM_MODEL_BASE;
    }
    static const char *parts[] = {"Helm", "Armor", "Pant", "Glove", "Boot"};
    const char *base = strrchr(path, '/');
    base = base ? base + 1 : path;
    for (int k = 0; k < 5; ++k) {
        char prefix[16];
        snprintf(prefix, sizeof prefix, "%sClass", parts[k]);
        const size_t len = strlen(prefix);
        if (strncasecmp(base, prefix, len) || !isdigit((unsigned char)base[len]))
            continue;
        const long number = strtol(base + len, NULL, 10);
        if (number >= 1 && number <= (long)MU_CHARACTER_PART_STRIDE)
            return (int32_t)(MU_CHARACTER_PART_BASE + (uint32_t)k * MU_CHARACTER_PART_STRIDE) + (int32_t)number - 1;
    }
    return -1;
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
            mu_texture_names_upload upload;
            const int found = mu_texture_names_item(game_root, item_rule ? record.folder : NULL, subfolder,
                                                    model->meshes[k].texture, file, sizeof file, &texture_type,
                                                    &special, &step, &upload);
            if (texture_type) {   /* RENDER-ITEMS-TEX-002: TextureType, read by the mesh draw */
                if (!t->texture_type && !(t->texture_type = calloc((size_t)t->model_count, sizeof *t->texture_type)))
                    return 1;
                t->texture_type[k] = texture_type;
            }
            t->field |= (uint8_t)(upload.field != 0);   /* model +0xa6 */
            if (special) {
                if (!t->client_index && !(t->client_index = calloc((size_t)t->model_count, sizeof *t->client_index)))
                    return 1;
                t->client_index[k] = special;
                stats->special_meshes++;
            }
            stats->typed_meshes += texture_type != 0;
            if (found && mu_textures_set_file(t, model, k, file) == 0) {
                /* RENDER-ITEMS-TEX-002: the slot takes the bitmap's own upload parameters. The item loader loads
                 * with GL_NEAREST, GL_CLAMP (LoadImage 0x00c97689 called at 0x00cd5b50, and at 0x00cd58c6.. for
                 * field_); a name-map hit reuses the bitmap as first loaded (0x00c97730 only counts a reference):
                 * a startup LoadBitmap's filter and wrap, or a startup model's OpenTexture GL_NEAREST, GL_REPEAT. */
                if (upload.wrap) {
                    t->filter[k] = upload.filter;
                    t->wrap[k] = upload.wrap;
                }
                stats->name_map += step == MU_TL_NAME_MAP;
            } else if (found || step != MU_TL_DIRECT) {   /* a special name answers DIRECT without a file */
                stats->missing_meshes++;
            }
        }
        t->missing = stats->missing_meshes;
        if (mu_item_textures_wear_shift(t, game_root, 0))   /* +0xa4 is 0 after the loader's memset */
            return 1;
    }
    int32_t want[64];
    const int32_t n = mu_item_textures_overrides(type, items, want, 64);
    stats->bitmaps = n;
    for (int32_t i = 0; i < n && i < 64; ++i) {
        const int added = add_registered(t, game_root, want[i]);
        if (added == 1)
            return 1;
        const int ok = added == 0 && t->slots[t->count - 1] != NULL;
        if (!ok) {
            if (stats->missing_bitmaps < MU_ITEM_TEXTURES_REPORT)
                stats->missing_index[stats->missing_bitmaps] = want[i];
            stats->missing_bitmaps++;
        }
    }
    return 0;
}
