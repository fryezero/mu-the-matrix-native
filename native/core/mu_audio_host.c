#include "mu_audio_host.h"

#include <ctype.h>
#include <errno.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Startup sound sets (the two loaders that register the permanent ids). */
static const uint32_t startup_loaders[] = {0x018392db, 0x018433ed};

struct mu_audio_host {
    mu_audio_engine *engine;
    mu_audio_client client;
    const mu_audio_table *table;
    mu_audio_engine_config engine_config;
    int world_active;
    mu_world_audio_state world;
    int32_t boss_zone;
    uint32_t rand_state;
    int delegate_logged;
};

static char *copy_string(const char *text, size_t length)
{
    char *out = malloc(length + 1);
    if (out) {
        memcpy(out, text, length);
        out[length] = 0;
    }
    return out;
}

static int failf(char *error, size_t size, const char *format, ...)
{
    if (error && size) {
        va_list args;
        va_start(args, format);
        vsnprintf(error, size, format, args);
        va_end(args);
    }
    return -1;
}

static void host_log(mu_audio_host *host, const char *format, ...)
{
    if (!host->engine_config.log) return;
    char message[600];
    va_list args;
    va_start(args, format);
    vsnprintf(message, sizeof message, format, args);
    va_end(args);
    host->engine_config.log(host->engine_config.log_ctx, message);
}

/* ---- tables -------------------------------------------------------------- */

static int parse_int(const char *text, int32_t *value)
{
    if (!text || !*text || !strcmp(text, "-") || !strcmp(text, "None")) return 0;
    char *end;
    errno = 0;
    long v = strtol(text, &end, 0);
    if (*end || errno || v < INT32_MIN || v > INT32_MAX) return 0;
    *value = (int32_t)v;
    return 1;
}

int mu_audio_table_load(const char *path, mu_audio_table *table, char *error, size_t error_size)
{
    memset(table, 0, sizeof *table);
    FILE *f = fopen(path, "rb");
    if (!f) return failf(error, error_size, "cannot open table %s", path);
    char line[2048];
    size_t capacity = 0;
    int number = 0;
    while (fgets(line, sizeof line, f)) {
        number++;
        size_t n = strcspn(line, "\r\n");
        line[n] = 0;
        if (!line[0] || line[0] == '#') continue;
        char *fields[6] = {0};
        int count = 0;
        for (char *p = line; count < 6;) {
            fields[count++] = p;
            char *tab = strchr(p, '\t');
            if (!tab) break;
            *tab = 0;
            p = tab + 1;
        }
        int32_t id;
        if (count < 3 || !parse_int(fields[1], &id)) {
            fclose(f);
            mu_audio_table_free(table);
            return failf(error, error_size, "%s:%d: malformed row", path, number);
        }
        if (!strcmp(fields[0], "music")) {
            if (id < 0 || id >= MU_AUDIO_MUSIC_ENTRIES) continue;
            free(table->music[id]);
            table->music[id] = copy_string(fields[2], strlen(fields[2]));
        } else if (!strcmp(fields[0], "sound")) {
            if (table->count == capacity) {
                capacity = capacity ? capacity*2 : 512;
                mu_audio_table_row *rows = realloc(table->rows, capacity*sizeof *rows);
                if (!rows) {
                    fclose(f);
                    mu_audio_table_free(table);
                    return failf(error, error_size, "out of memory");
                }
                table->rows = rows;
            }
            mu_audio_table_row *row = &table->rows[table->count++];
            row->id = id;
            row->path = copy_string(fields[2], strlen(fields[2]));
            row->legacy_channels = row->legacy_3d = -1;
            if (count > 3) parse_int(fields[3], &row->legacy_channels);
            if (count > 4) parse_int(fields[4], &row->legacy_3d);
            int32_t loader = 0;
            row->loader = count > 5 && parse_int(fields[5], &loader) ? (uint32_t)loader : 0;
        }
    }
    fclose(f);
    return 0;
}

void mu_audio_table_free(mu_audio_table *table)
{
    for (size_t i = 0; i < table->count; i++) free(table->rows[i].path);
    free(table->rows);
    for (int i = 0; i < MU_AUDIO_MUSIC_ENTRIES; i++) free(table->music[i]);
    memset(table, 0, sizeof *table);
}

const char *mu_audio_table_sound_path(const mu_audio_table *table, int32_t id)
{
    if (!table) return NULL;
    const char *first = NULL;
    for (size_t i = 0; i < table->count; i++) {
        if (table->rows[i].id != id) continue;
        for (size_t k = 0; k < sizeof startup_loaders/sizeof startup_loaders[0]; k++)
            if (table->rows[i].loader == startup_loaders[k]) return table->rows[i].path;
        if (!first) first = table->rows[i].path;
    }
    return first;
}

const char *mu_audio_table_music_path(const mu_audio_table *table, int32_t index)
{
    if (!table || index < 0 || index >= MU_AUDIO_MUSIC_ENTRIES) return NULL;
    return table->music[index];
}

/* ---- host ------------------------------------------------------------------ */

static int read_text(const char *path, char **text, size_t *size)
{
    FILE *f = fopen(path, "rb");
    if (!f) return -1;
    char *buffer = NULL;
    size_t length = 0, capacity = 0;
    for (;;) {
        if (length + 4096 + 1 > capacity) {
            capacity = capacity ? capacity*2 : 8192;
            char *grown = realloc(buffer, capacity);
            if (!grown) { free(buffer); fclose(f); return -1; }
            buffer = grown;
        }
        size_t got = fread(buffer + length, 1, 4096, f);
        length += got;
        if (got < 4096) break;
    }
    fclose(f);
    buffer[length] = 0;
    *text = buffer;
    *size = length;
    return 0;
}

static int apply_options_file(mu_audio_host *host, const char *path, int required, char *error, size_t size)
{
    char *text;
    size_t length;
    if (read_text(path, &text, &length)) {
        if (required) return failf(error, size, "cannot read %s", path);
        host_log(host, "no Option.ini at %s: FMOD defaults stay", path);
        return 0;
    }
    mu_audio_settings settings;
    int ok = mu_audio_options_parse(text, length, &settings);
    free(text);
    if (!ok) {
        if (required) return failf(error, size, "%s does not parse", path);
        host_log(host, "Option.ini does not parse: settings unchanged");
        return 0;
    }
    mu_audio_apply_settings(&host->client, &settings);
    host_log(host, "Option.ini applied: master %.3f%s, music %.3f%s, environment %.3f%s, effect %.3f%s",
             (double)settings.master_volume, settings.master_mute ? " muted" : "",
             (double)settings.group_volume[0], settings.group_mute[0] ? " muted" : "",
             (double)settings.group_volume[1], settings.group_mute[1] ? " muted" : "",
             (double)settings.group_volume[2], settings.group_mute[2] ? " muted" : "");
    return 0;
}

mu_audio_host *mu_audio_host_new(const mu_audio_host_config *config, char *error, size_t error_size)
{
    mu_audio_host *host = calloc(1, sizeof *host);
    if (!host) {
        failf(error, error_size, "out of memory");
        return NULL;
    }
    host->engine_config = config->engine;
    host->table = config->table;
    host->rand_state = 1;  /* the CRT's initial seed */
    host->engine = mu_audio_engine_new(&config->engine);
    if (!host->engine) {
        free(host);
        failf(error, error_size, "out of memory");
        return NULL;
    }
    mu_audio_client_init_state(&host->client, mu_audio_engine_api(host->engine));
    mu_audio_set_callback_client(&host->client);
    if (!mu_audio_system_init(&host->client, NULL)) {
        mu_audio_host_free(host);
        failf(error, error_size, "sound system init failed");
        return NULL;
    }
    if (!config->skip_options) {
        char path[4096];
        const char *options = config->options_path;
        if (!options) {
            snprintf(path, sizeof path, "%s", "");
            if (!config->engine.game_root ||
                mu_audio_resolve_path(config->engine.game_root, "Data/Sound/Option.ini", path, sizeof path))
                path[0] = 0;
            options = path[0] ? path : NULL;
        }
        if (options && apply_options_file(host, options, config->options_path != NULL, error, error_size)) {
            mu_audio_host_free(host);
            return NULL;
        }
    }
    return host;
}

void mu_audio_host_free(mu_audio_host *host)
{
    if (!host) return;
    mu_audio_system_shutdown(&host->client);
    mu_audio_client_free_state(&host->client);
    mu_audio_engine_free(host->engine);
    free(host);
}

mu_audio_engine *mu_audio_host_engine(mu_audio_host *host) { return host->engine; }
mu_audio_client *mu_audio_host_client(mu_audio_host *host) { return &host->client; }

static int ensure_loaded(mu_audio_host *host, int32_t id)
{
    if (mu_audio_snd_find(&host->client, id)) return 1;
    const char *path = mu_audio_table_sound_path(host->table, id);
    if (!path) {
        host_log(host, "sound %d is not in the table", id);
        return 0;
    }
    return mu_audio_snd_load(&host->client, id, path, 0, 0);
}

static const char *music_argument(mu_audio_host *host, const char *argument)
{
    int32_t index;
    if (parse_int(argument, &index)) {
        const char *path = mu_audio_table_music_path(host->table, index);
        if (!path) host_log(host, "music index %d is unresolved or no table is loaded", index);
        return path;
    }
    return argument;
}

static int group_by_name(const char *name)
{
    if (!strcmp(name, "master")) return -1;
    if (!strcmp(name, "music")) return MU_AUDIO_GROUP_MUSIC;
    if (!strcmp(name, "environment")) return MU_AUDIO_GROUP_ENVIRONMENT;
    if (!strcmp(name, "effect")) return MU_AUDIO_GROUP_EFFECT;
    return -2;
}

/* World-frame hooks. */
static int32_t host_rand(void *ctx)
{
    mu_audio_host *host = ctx;
    host->rand_state = host->rand_state*214013u + 2531011u;  /* MSVC rand */
    return (int32_t)((host->rand_state >> 16) & 0x7fff);
}

static int32_t host_boss(void *ctx, int32_t world, int32_t x, int32_t y)
{
    (void)world; (void)x; (void)y;
    return ((mu_audio_host *)ctx)->boss_zone;
}

static void host_event(void *ctx, int kind, int32_t a, int32_t b)
{
    mu_audio_host *host = ctx;
    switch (kind) {
    case MU_WORLD_SND_PLAY:
        if (ensure_loaded(host, a)) mu_audio_snd_play(&host->client, a, NULL, b);
        break;
    case MU_WORLD_SND_STOP:
        mu_audio_snd_stop(&host->client, a);
        break;
    case MU_WORLD_MP3_PLAY:
    case MU_WORLD_MP3_STOP: {
        const char *path = mu_audio_table_music_path(host->table, a);
        if (!path) break;
        if (kind == MU_WORLD_MP3_PLAY) mu_audio_play_mp3(&host->client, path);
        else mu_audio_stop_mp3(&host->client, path);
        break;
    }
    default:
        if (!host->delegate_logged) {
            host_log(host, "event-world managers and the protector-virtualised gap are not reconstructed");
            host->delegate_logged = 1;
        }
        break;
    }
}

void mu_audio_host_tick(mu_audio_host *host)
{
    if (host->world_active) {
        mu_world_audio_hooks hooks = {host, host_rand, host_boss, host_event};
        mu_world_audio_frame(&host->world, &hooks);
    }
    mu_audio_system_update(&host->client);
}

int mu_audio_host_command(mu_audio_host *host, const char *command, char *error, size_t error_size)
{
    char buffer[1024];
    snprintf(buffer, sizeof buffer, "%s", command);
    char *argv[16];
    int argc = 0;
    for (char *p = strtok(buffer, " \t"); p && argc < 16; p = strtok(NULL, " \t")) argv[argc++] = p;
    if (!argc) return 0;
    const char *name = argv[0];
    int32_t value = 0, value2 = 0;
    mu_audio_client *client = &host->client;
    if (!strcmp(name, "end")) return 1;
    if (!strcmp(name, "load")) {
        if (argc < 2 || !parse_int(argv[1], &value)) return failf(error, error_size, "load <id> [path]");
        const char *path = argc > 2 ? argv[2] : mu_audio_table_sound_path(host->table, value);
        if (!path) return failf(error, error_size, "sound %d is not in the table", value);
        if (!mu_audio_snd_load(client, value, path, 0, 0)) host_log(host, "load %d failed (%s)", value, path);
        return 0;
    }
    if (!strcmp(name, "play")) {
        if (argc < 2 || !parse_int(argv[1], &value)) return failf(error, error_size, "play <id> [loop]");
        if (argc > 2 && !parse_int(argv[2], &value2)) return failf(error, error_size, "play <id> [loop]");
        if (ensure_loaded(host, value)) mu_audio_snd_play(client, value, NULL, value2);
        return 0;
    }
    if (!strcmp(name, "stop") || !strcmp(name, "remove")) {
        if (argc < 2 || !parse_int(argv[1], &value)) return failf(error, error_size, "%s <id>", name);
        if (name[0] == 's') mu_audio_snd_stop(client, value);
        else mu_audio_snd_remove(client, value);
        return 0;
    }
    if (!strcmp(name, "music") || !strcmp(name, "stopmusic")) {
        if (argc < 2) return failf(error, error_size, "%s <index|path>", name);
        const char *path = music_argument(host, argv[1]);
        if (path) {
            if (name[0] == 'm') mu_audio_play_mp3(client, path);
            else mu_audio_stop_mp3(client, path);
        }
        return 0;
    }
    if (!strcmp(name, "volume") || !strcmp(name, "mute")) {
        int group = argc > 2 ? group_by_name(argv[1]) : -2;
        if (group == -2) return failf(error, error_size, "%s <master|music|environment|effect> <value>", name);
        char *end;
        double v = strtod(argv[2], &end);
        if (*end) return failf(error, error_size, "bad value %s", argv[2]);
        if (name[0] == 'v') {
            if (group < 0) mu_audio_set_master_volume(client, (float)v);
            else mu_audio_set_group_volume(client, group, (float)v);
        } else {
            if (group < 0) mu_audio_set_master_mute(client, v != 0.0);
            else mu_audio_set_group_mute(client, group, v != 0.0);
        }
        return 0;
    }
    if (!strcmp(name, "effectlevel")) {
        if (argc < 2 || !parse_int(argv[1], &value)) return failf(error, error_size, "effectlevel <0..9>");
        mu_audio_set_group_volume(client, MU_AUDIO_GROUP_EFFECT, mu_audio_level_to_volume(value));
        return 0;
    }
    if (!strcmp(name, "musicon")) {
        if (argc < 2 || !parse_int(argv[1], &value)) return failf(error, error_size, "musicon <0|1>");
        mu_audio_set_group_mute(client, MU_AUDIO_GROUP_MUSIC, value == 0);
        return 0;
    }
    if (!strcmp(name, "openworld")) {
        if (argc < 2 || !parse_int(argv[1], &value)) return failf(error, error_size, "openworld <world>");
        mu_audio_set_group_volume(client, MU_AUDIO_GROUP_MUSIC, mu_audio_world_music_volume(value));
        return 0;
    }
    if (!strcmp(name, "world")) {
        if (argc < 2 || !parse_int(argv[1], &value)) return failf(error, error_size, "world <world> [key=value...]");
        mu_world_audio_state s = {6, value, 0, 0, 1, 128, 128, 0};
        int32_t boss = 0;
        for (int i = 2; i < argc; i++) {
            char *equals = strchr(argv[i], '=');
            int32_t v;
            if (!equals || !parse_int(equals + 1, &v)) return failf(error, error_size, "bad world field %s", argv[i]);
            *equals = 0;
            if (!strcmp(argv[i], "tile")) s.hero_tile = v;
            else if (!strcmp(argv[i], "safe")) s.hero_safe_zone = v;
            else if (!strcmp(argv[i], "x")) s.hero_x = v;
            else if (!strcmp(argv[i], "y")) s.hero_y = v;
            else if (!strcmp(argv[i], "rain")) s.rain = v;
            else if (!strcmp(argv[i], "attr")) s.hero_attribute = (uint16_t)v;
            else if (!strcmp(argv[i], "boss")) boss = v;
            else if (!strcmp(argv[i], "scene")) s.scene = v;
            else return failf(error, error_size, "unknown world field %s", argv[i]);
        }
        host->world = s;
        host->boss_zone = boss;
        host->world_active = 1;
        return 0;
    }
    if (!strcmp(name, "noworld")) {
        host->world_active = 0;
        return 0;
    }
    if (!strcmp(name, "options")) {
        if (argc < 2) return failf(error, error_size, "options <path>");
        return apply_options_file(host, argv[1], 1, error, error_size);
    }
    return failf(error, error_size, "unknown command %s", name);
}

/* ---- scripts --------------------------------------------------------------- */

int mu_audio_script_parse(const char *text, mu_audio_script *script, char *error, size_t error_size)
{
    memset(script, 0, sizeof *script);
    size_t capacity = 0;
    int number = 0, have_end = 0;
    uint32_t last = 0;
    for (const char *p = text; *p;) {
        const char *end = p + strcspn(p, "\n");
        number++;
        char line[1024];
        size_t length = (size_t)(end - p);
        if (length >= sizeof line) {
            mu_audio_script_free(script);
            return failf(error, error_size, "line %d too long", number);
        }
        memcpy(line, p, length);
        line[length] = 0;
        p = *end ? end + 1 : end;
        char *hash = strchr(line, '#');
        if (hash) *hash = 0;
        char *s = line;
        while (isspace((unsigned char)*s)) s++;
        size_t n = strlen(s);
        while (n && isspace((unsigned char)s[n - 1])) s[--n] = 0;
        if (!*s) continue;
        char *rest;
        unsigned long time = strtoul(s, &rest, 10);
        if (rest == s || !isspace((unsigned char)*rest) || time > 24ul*3600*1000) {
            mu_audio_script_free(script);
            return failf(error, error_size, "line %d: expected '<milliseconds> <command>'", number);
        }
        if (time < last) {
            mu_audio_script_free(script);
            return failf(error, error_size, "line %d: times must not decrease", number);
        }
        while (isspace((unsigned char)*rest)) rest++;
        if (script->count == capacity) {
            capacity = capacity ? capacity*2 : 32;
            mu_audio_script_line *lines = realloc(script->lines, capacity*sizeof *lines);
            if (!lines) {
                mu_audio_script_free(script);
                return failf(error, error_size, "out of memory");
            }
            script->lines = lines;
        }
        script->lines[script->count++] = (mu_audio_script_line){(uint32_t)time, copy_string(rest, strlen(rest)), number};
        last = (uint32_t)time;
        if (!strncmp(rest, "end", 3) && (!rest[3] || isspace((unsigned char)rest[3]))) {
            have_end = 1;
            script->end_ms = (uint32_t)time;
        }
    }
    if (!have_end) script->end_ms = last + 2000;
    return 0;
}

void mu_audio_script_free(mu_audio_script *script)
{
    for (size_t i = 0; i < script->count; i++) free(script->lines[i].command);
    free(script->lines);
    memset(script, 0, sizeof *script);
}

int mu_audio_host_run(mu_audio_host *host, const mu_audio_script *script, mu_audio_sink sink, void *sink_ctx,
                      char *error, size_t error_size)
{
    uint32_t rate = mu_audio_engine_rate(host->engine);
    uint64_t rendered = 0;
    float *chunk = malloc((size_t)(rate/10 + 64)*2*sizeof(float));
    if (!chunk) return failf(error, error_size, "out of memory");
    size_t next = 0;
    int ended = 0;
    for (uint32_t now = 0; now < script->end_ms && !ended; now += MU_AUDIO_FRAME_MS) {
        while (next < script->count && script->lines[next].time_ms <= now) {
            char message[512];
            int result = mu_audio_host_command(host, script->lines[next].command, message, sizeof message);
            if (result < 0) {
                free(chunk);
                return failf(error, error_size, "script line %d: %s", script->lines[next].line, message);
            }
            if (result == 1) ended = 1;
            next++;
        }
        if (ended) break;
        mu_audio_host_tick(host);
        /* Exact frame boundaries: samples up to (now + 40 ms) * rate / 1000. */
        uint64_t target = (uint64_t)(now + MU_AUDIO_FRAME_MS)*rate/1000u;
        uint32_t frames = (uint32_t)(target - rendered);
        mu_audio_engine_mix(host->engine, chunk, frames);
        rendered = target;
        if (sink && sink(sink_ctx, chunk, frames)) {
            free(chunk);
            return failf(error, error_size, "output failed");
        }
    }
    free(chunk);
    return 0;
}
