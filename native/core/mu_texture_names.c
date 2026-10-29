/* The rebuilt bitmap-name map. See mu_texture_names.h. */
#include "mu_texture_names.h"

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../../reconstructed/objects/item_texture.h"
#include "../../reconstructed/objects/texture_lookup.h"
#include "mu_bmd.h"
#include "mu_image.h"
#include "mu_objects.h"

typedef struct entry {
    char key[64];      /* lowercased file name of the loaded path, the client's map key */
    char path[1024];   /* installed file */
} entry;

static struct {
    char root[1024];
    int startup_done;
    int32_t startup_names;   /* entries from the startup models; the world's follow */
    int32_t world;
    entry *entries;
    int32_t count, capacity;
    int32_t startup_models, world_models;
} map = {.world = -1};

typedef struct lookup {
    const char *root;
    char path[1024];   /* the file of the last answer */
    int startup_bitmaps;   /* item lookups: the startup LoadBitmap files are in the map (RENDER-ITEMS-TEX-001) */
} lookup;

#include "mu_startup_bitmaps.inc"

static void lower_key(const char *name, char *out, size_t size)
{
    size_t i = 0;
    for (; name[i] && i + 1 < size; ++i)
        out[i] = (char)tolower((unsigned char)name[i]);
    out[i] = 0;
}

static int32_t find_key(const char *name)
{
    char key[64];
    lower_key(name, key, sizeof key);
    for (int32_t i = 0; i < map.count; ++i)
        if (!strcmp(map.entries[i].key, key))
            return i;
    return -1;
}

/* std::map::insert in the loaders (0x00c9a55f): an existing name keeps its first bitmap. */
static int32_t insert(const char *file_name, const char *path)
{
    const int32_t found = find_key(file_name);
    if (found >= 0)
        return found;
    if (map.count == map.capacity) {
        const int32_t capacity = map.capacity ? map.capacity * 2 : 256;
        entry *grown = realloc(map.entries, (size_t)capacity * sizeof *grown);
        if (!grown)
            return -1;
        map.entries = grown;
        map.capacity = capacity;
    }
    entry *e = &map.entries[map.count];
    lower_key(file_name, e->key, sizeof e->key);
    snprintf(e->path, sizeof e->path, "%s", path);
    return map.count++;
}

/* LoadImage: the client path "Data\Dir\name" -> the installed file (case-insensitive folders, .jpg -> .OZJ and
 * .tga -> .OZT as mu_image_resolve); a loaded file enters the name map under its file name. */
static int32_t host_load(void *context, const char *client_path, uint32_t filter, uint32_t wrap)
{
    (void)filter;
    (void)wrap;
    lookup *l = context;
    char relative[512], directory[2048], file[4096];
    snprintf(relative, sizeof relative, "%s", client_path);
    for (char *p = relative; *p; ++p)
        if (*p == '\\')
            *p = '/';
    char *slash = strrchr(relative, '/');
    if (!slash || !slash[1])
        return MU_TL_DEFAULT;
    *slash = 0;
    const char *name = slash + 1;
    if (!mu_objects_resolve(l->root, relative, directory, sizeof directory) ||
        !mu_image_resolve(directory, name, file, sizeof file))
        return MU_TL_DEFAULT;
    snprintf(l->path, sizeof l->path, "%s", file);
    const int32_t index = insert(name, file);
    return index >= 0 ? index : 0;
}

static int32_t host_load(void *context, const char *client_path, uint32_t filter, uint32_t wrap);

/* The startup LoadBitmap file named `name` (mu_startup_bitmaps.inc), entered in the map on first use. */
static int32_t startup_bitmap(lookup *l, const char *name)
{
    char key[64];
    lower_key(name, key, sizeof key);
    for (size_t i = 0; i < sizeof startup_bitmaps / sizeof startup_bitmaps[0]; ++i) {
        const char *file = strrchr(startup_bitmaps[i], '\\');
        char other[64];
        lower_key(file ? file + 1 : startup_bitmaps[i], other, sizeof other);
        if (strcmp(key, other))
            continue;
        char client[512];
        snprintf(client, sizeof client, "Data\\%s", startup_bitmaps[i]);
        const int32_t index = host_load(l, client, 0x2601, 0x2901);
        l->path[0] = 0;   /* the answer is the map entry, not a load of this mesh */
        return index == MU_TL_DEFAULT ? -1 : index;
    }
    return -1;
}

static int32_t host_find(void *context, const char *name, const char **path)
{
    lookup *l = context;
    int32_t index = find_key(name);
    if (index < 0 && l->startup_bitmaps)
        index = startup_bitmap(l, name);
    if (index < 0)
        return -1;
    *path = map.entries[index].path;
    return index;
}

static void host_reuse(void *context, int32_t index, const char *path, uint32_t filter, uint32_t wrap)
{
    (void)filter;
    (void)wrap;
    (void)path;
    lookup *l = context;
    snprintf(l->path, sizeof l->path, "%s", map.entries[index].path);
}

/* OpenTexture for every mesh of one preloaded model. */
static int open_model(const char *root, const mu_tl_preload *p)
{
    char relative[512], file[2048], message[256];
    mu_bmd model;
    if (!mu_tl_preload_file(p, relative, (int32_t)sizeof relative) ||
        !mu_objects_resolve(root, relative, file, sizeof file) ||
        mu_bmd_load_file(file, &model, message, sizeof message) != MU_BMD_OK)
        return 0;
    lookup l = {root, "", 0};
    const mu_tl_host host = {&l, host_load, host_find, host_reuse, NULL};
    for (int32_t i = 0; i < model.mesh_count; ++i)
        mu_tl_open(&host, p->subfolder, model.meshes[i].texture, 0x2901, 0x2600, NULL);
    mu_bmd_free(&model);
    return 1;
}

static void prepare(const char *root, int32_t world)
{
    if (strcmp(map.root, root)) {
        mu_texture_names_reset();
        snprintf(map.root, sizeof map.root, "%s", root);
    }
    if (!map.startup_done) {
        for (int32_t i = 0; i < mu_tl_startup_count(); ++i)
            map.startup_models += open_model(root, mu_tl_startup(i));
        map.startup_done = 1;
        map.startup_names = map.count;
    }
    if (map.world != world) {
        map.count = map.startup_names;   /* the previous world's extras are released */
        map.world = world;
        map.world_models = 0;
        const mu_tl_preload *first = NULL;
        const int32_t n = mu_tl_world_preloads(world, &first);
        for (int32_t i = 0; i < n; ++i)
            map.world_models += open_model(root, &first[i]);
    }
}

int mu_texture_names_find(const char *game_root, int32_t world, const char *subfolder, const char *name,
                          char *path, size_t size, int *step)
{
    if (!game_root || !name)
        return 0;
    prepare(game_root, world);
    lookup l = {game_root, "", 0};
    const mu_tl_host host = {&l, host_load, host_find, host_reuse, NULL};
    int found = MU_TL_MISSING;
    const int32_t index = mu_tl_open(&host, subfolder, name, 0x2901, 0x2600, &found);
    if (step)
        *step = found;
    if (found == MU_TL_MISSING || !l.path[0] || index == MU_TL_DEFAULT)   /* no file, or a special bitmap */
        return 0;
    snprintf(path, size, "%s", l.path);
    return 1;
}

int mu_texture_names_item(const char *game_root, const char *folder, const char *subfolder, const char *name,
                          char *path, size_t size, int32_t *type, int32_t *special, int *step)
{
    if (special)
        *special = 0;
    if (!game_root || !name)
        return 0;
    prepare(game_root, strcmp(map.root, game_root) ? -1 : map.world);   /* items keep the world part */
    lookup l = {game_root, "", 1};
    const mu_tl_host host = {&l, host_load, host_find, host_reuse, NULL};
    int found = MU_TL_MISSING, field = 0;
    int32_t ignored = 0;
    const int32_t index = folder ? mu_it_open(&host, folder, name, type ? type : &ignored, &field, &found)
                                 : mu_tl_open(&host, subfolder, name, 0x2901, 0x2600, &found);
    if (step)
        *step = found;
    if (found == MU_TL_MISSING || !l.path[0] || index == MU_TL_DEFAULT || index == MU_TL_SKIN ||
        index == MU_TL_HIDE || index == MU_TL_HAIR || index == MU_TL_FACE || index == MU_TL_HQ_SKIN ||
        index == MU_TL_HQ_SKIN2 || index == MU_TL_HQ_SKIN3 || index == MU_TL_HQ_HAIR) {
        if (special && index != MU_TL_DEFAULT)
            *special = index;
        return 0;
    }
    /* the file of the bitmap the mesh keeps (a field_ name loads a second file after it) */
    snprintf(path, size, "%s", index >= 0 && index < map.count ? map.entries[index].path : l.path);
    return 1;
}

void mu_texture_names_get_stats(mu_texture_names_stats *out)
{
    out->names = map.count;
    out->startup_models = map.startup_models;
    out->world_models = map.world_models;
    out->world = map.world;
}

void mu_texture_names_reset(void)
{
    free(map.entries);
    memset(&map, 0, sizeof map);
    map.world = -1;
}
