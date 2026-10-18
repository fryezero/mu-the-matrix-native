#define _POSIX_C_SOURCE 200809L /* opendir with -std=c11 on glibc */
#include "mu_objects.h"

#include <ctype.h>
#include <dirent.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../../reconstructed/model-codec/model_codec.h"

void mu_objects_init(mu_objects *o, int32_t world)
{
    memset(o, 0, sizeof *o);
    o->world = world;
    o->folder = mu_objects_world_folder(world);
    o->status = MU_OBJECTS_FILE_ERROR;
}

static void free_models(mu_objects *o)
{
    for (int32_t t = 0; t < MU_OBJECT_TYPES; ++t) {
        mu_object_model *m = o->models[t];
        if (!m)
            continue;
        if (m->loaded) {
            mu_textures_free(&m->textures);
            mu_model_free(&m->model);
            mu_bmd_free(&m->bmd);
        }
        free(m);
        o->models[t] = NULL;
    }
    o->models_loaded = o->models_missing = o->types_used = 0;
}

void mu_objects_free(mu_objects *o)
{
    free_models(o);
    free(o->records);
    o->records = NULL;
    o->count = 0;
}

int32_t mu_objects_world_folder(int32_t world)
{
    return mu_world_folder(world);
}

static int find_component(const char *directory, const char *name, char *out, size_t size)
{
    DIR *dir = opendir(directory);
    if (!dir)
        return 0;
    struct dirent *entry;
    int found = 0;
    while (!found && (entry = readdir(dir)) != NULL) {
        const char *a = entry->d_name, *b = name;
        while (*a && *b && tolower((unsigned char)*a) == tolower((unsigned char)*b))
            ++a, ++b;
        if (!*a && !*b) {
            int n = snprintf(out, size, "%s/%s", directory, entry->d_name);
            found = n > 0 && (size_t)n < size;
        }
    }
    closedir(dir);
    return found;
}

int mu_objects_resolve(const char *game_root, const char *relative, char *out, size_t size)
{
    char current[2048], part[256];
    int n = snprintf(current, sizeof current, "%s", game_root);
    if (n <= 0 || (size_t)n >= sizeof current)
        return 0;
    const char *p = relative;
    while (*p) {
        size_t len = strcspn(p, "/\\");
        if (len == 0) {
            ++p;
            continue;
        }
        if (len >= sizeof part)
            return 0;
        memcpy(part, p, len);
        part[len] = 0;
        char next[2048];
        if (!find_component(current, part, next, sizeof next))
            return 0;
        snprintf(current, sizeof current, "%s", next);
        p += len;
    }
    n = snprintf(out, size, "%s", current);
    return n > 0 && (size_t)n < size;
}

static uint8_t *read_all(const char *path, size_t *size)
{
    FILE *f = fopen(path, "rb");
    if (!f)
        return NULL;
    uint8_t *data = NULL;
    if (fseek(f, 0, SEEK_END) == 0) {
        long length = ftell(f);
        if (length >= 0 && length < 0x40000000L && fseek(f, 0, SEEK_SET) == 0) {
            data = malloc((size_t)length + 1);
            if (data && fread(data, 1, (size_t)length, f) != (size_t)length) {
                free(data);
                data = NULL;
            }
            *size = (size_t)length;
        }
    }
    fclose(f);
    return data;
}

int mu_objects_load_plain(mu_objects *o, const uint8_t *plain, size_t size, char *error, size_t error_size)
{
    free(o->records);
    o->records = NULL;
    o->count = 0;
    memset(&o->header, 0, sizeof o->header);
    int32_t parsed = 0;
    int status = mu_objects_parse(plain, size, &o->header, NULL, 0, &parsed);
    /* OpenWorld compares the loader's return value (the map byte) whatever the records hold. */
    if (size >= 4 && o->header.map != (uint8_t)o->folder) {
        snprintf(error, error_size, "map number %u != folder %d (OpenWorld refuses the file)", o->header.map,
                 o->folder);
        return o->status = MU_OBJECTS_FILE_REFUSED;
    }
    if (status != MU_OBJECTS_OK) {
        snprintf(error, error_size, "object records run past the plaintext (%zu bytes)", size);
        return o->status = MU_OBJECTS_FILE_TRUNCATED;
    }
    int32_t n = o->header.count > 0 ? o->header.count : 0;
    o->records = calloc((size_t)(n ? n : 1), sizeof *o->records);
    if (!o->records) {
        snprintf(error, error_size, "out of memory");
        return o->status = MU_OBJECTS_FILE_ERROR;
    }
    mu_objects_parse(plain, size, &o->header, o->records, n, &parsed);
    o->count = parsed;
    snprintf(o->source, sizeof o->source, "plain");
    return o->status = MU_OBJECTS_FILE_OK;
}

int mu_objects_load_installed(mu_objects *o, const char *game_root, char *error, size_t error_size)
{
    char relative[128], path[2048];
    snprintf(relative, sizeof relative, "Data/World%d/EncTerrain%d.obj", o->folder, o->folder);
    size_t size = 0;
    uint8_t *raw = mu_objects_resolve(game_root, relative, path, sizeof path) ? read_all(path, &size) : NULL;
    if (!raw) {
        snprintf(error, error_size, "%s not found", relative);
        return o->status = MU_OBJECTS_FILE_MISSING;
    }
    if (size > 0x7fffffff) {
        free(raw);
        snprintf(error, error_size, "%s too large", relative);
        return o->status = MU_OBJECTS_FILE_ERROR;
    }
    uint8_t *plain = malloc(size + 1);
    if (!plain) {
        free(raw);
        snprintf(error, error_size, "out of memory");
        return o->status = MU_OBJECTS_FILE_ERROR;
    }
    mu_bmd12_decode(plain, raw, (int32_t)size);   /* 0x0098c5f2, as 0x016d9ac5 calls it */
    free(raw);
    int status = mu_objects_load_plain(o, plain, size, error, error_size);
    free(plain);
    if (status == MU_OBJECTS_FILE_OK)
        snprintf(o->source, sizeof o->source, "installed");
    return status;
}

int mu_objects_load_plain_file(mu_objects *o, const char *path, char *error, size_t error_size)
{
    size_t size = 0;
    uint8_t *plain = read_all(path, &size);
    if (!plain) {
        snprintf(error, error_size, "%s: cannot read", path);
        return o->status = MU_OBJECTS_FILE_MISSING;
    }
    int status = mu_objects_load_plain(o, plain, size, error, error_size);
    free(plain);
    return status;
}

int mu_objects_gallery(mu_objects *o, const char *game_root, const mu_world *map, int32_t tile_x, int32_t tile_y,
                       int32_t columns, float spacing, char *error, size_t error_size)
{
    free(o->records);
    o->records = calloc(MU_OBJECT_TYPES, sizeof *o->records);
    o->count = 0;
    if (!o->records) {
        snprintf(error, error_size, "out of memory");
        return o->status = MU_OBJECTS_FILE_ERROR;
    }
    if (columns <= 0)
        columns = 12;
    for (int32_t type = 0; type < MU_OBJECT_TYPES; ++type) {
        char relative[512], path[2048];
        if (!mu_objects_model_file(o->world, type, relative, sizeof relative) ||
            !mu_objects_resolve(game_root, relative, path, sizeof path))
            continue;
        mu_object_record *r = &o->records[o->count];
        mu_objects_record_init(r);
        r->type = (int16_t)type;
        r->position[0] = ((float)tile_x + 0.5f) * 100.0f + (float)(o->count % columns) * spacing;
        r->position[1] = ((float)tile_y + 0.5f) * 100.0f + (float)(o->count / columns) * spacing;
        r->position[2] = map ? mu_world_height_at(map, r->position[0], r->position[1]) : 0.0f;
        ++o->count;
    }
    memset(&o->header, 0, sizeof o->header);
    o->header.map = (uint8_t)o->folder;
    o->header.count = (int16_t)o->count;
    snprintf(o->source, sizeof o->source, "gallery");
    o->uniform_light = 1.0f;
    return o->status = MU_OBJECTS_FILE_OK;
}

int mu_objects_load_models(mu_objects *o, const char *game_root, int no_textures)
{
    free_models(o);
    o->skipped_types = 0;
    for (int32_t i = 0; i < o->count; ++i) {
        int32_t type = o->records[i].type;
        if (type < 0 || type >= MU_OBJECT_TYPES) {
            ++o->skipped_types;
            continue;
        }
        if (o->models[type])
            continue;
        mu_object_model *m = calloc(1, sizeof *m);
        if (!m)
            return 1;
        m->type = type;
        o->models[type] = m;
        ++o->types_used;
        char relative[512], message[512];
        if (!mu_objects_model_file(o->world, type, relative, sizeof relative) ||
            !mu_objects_resolve(game_root, relative, m->path, sizeof m->path) ||
            mu_bmd_load_file(m->path, &m->bmd, message, sizeof message) != MU_BMD_OK) {
            ++o->models_missing;
            continue;
        }
        mu_model_params p;
        mu_model_default_params(&p);
        p.world = o->world;
        if (mu_model_init(&m->model, &m->bmd, &p, message, sizeof message) != MU_MODEL_OK) {
            mu_bmd_free(&m->bmd);
            ++o->models_missing;
            continue;
        }
        if (!no_textures) {
            char directory[2048];
            mu_path_directory(m->path, directory, sizeof directory);
            mu_textures_load(&m->textures, &m->bmd, directory);
        }
        m->loaded = 1;
        ++o->models_loaded;
    }
    return 0;
}

mu_object_model *mu_objects_place(mu_objects *o, int32_t index, const mu_world *map)
{
    if (index < 0 || index >= o->count)
        return NULL;
    const mu_object_record *r = &o->records[index];
    if (r->type < 0 || r->type >= MU_OBJECT_TYPES || !o->models[r->type] || !o->models[r->type]->loaded)
        return NULL;
    mu_object_model *m = o->models[r->type];
    mu_model_params p = m->model.params;
    for (int k = 0; k < 3; ++k) {
        p.origin[k] = r->position[k];
        p.angles[k] = r->angle[k];
        p.color[k] = 1.0f;
    }
    p.body_scale = r->scale;
    if (o->uniform_light > 0.0f) {
        for (int k = 0; k < 3; ++k)
            p.color[k] = o->uniform_light;
    } else if (map) {
        int32_t x = (int32_t)(r->position[0] / 100.0f), y = (int32_t)(r->position[1] / 100.0f);
        if (x >= 0 && x < MU_TERRAIN_SIDE && y >= 0 && y < MU_TERRAIN_SIDE)
            for (int k = 0; k < 3; ++k)
                p.color[k] = map->primary[3 * (y * MU_TERRAIN_SIDE + x) + k];
    }
    mu_model_apply_params(&m->model, &p);
    mu_model_set_state(&m->model, 0, 0.0f, 0.0f, 0);
    if (mu_model_pose(&m->model) != MU_MODEL_OK || mu_model_transform_all(&m->model) != MU_MODEL_OK)
        return NULL;
    return m;
}
