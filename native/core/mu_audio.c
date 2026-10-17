#define _POSIX_C_SOURCE 200809L /* opendir, stat with -std=c11 on glibc */
#include "mu_audio.h"

#include <ctype.h>
#include <dirent.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#define SYSTEM_HANDLE 0x1u
#define GROUP_BASE 0x100u
#define SOUND_BASE 0x10000u
#define CHANNEL_BASE 0x1000000u
#define MAX_GROUPS 16

typedef struct engine_sound {
    mu_fmod_handle handle;
    mu_pcm pcm;
    uint32_t mode;
    int stream;
} engine_sound;

typedef struct engine_group {
    int used;
    float volume;
    int mute, paused;
    int parent;  /* index, -1 for the master */
    char name[32];
} engine_group;

typedef struct voice {
    int active;
    mu_fmod_handle handle;
    engine_sound *sound;
    double position;
    int paused;
    int loop;
    int group;
    int32_t priority;
    void *user_data;
    mu_fmod_channel_callback callback;
    uint64_t serial;
} voice;

typedef struct pending_end {
    mu_fmod_channel_callback callback;
    mu_fmod_handle channel;
    void *user_data;
} pending_end;

struct mu_audio_engine {
    mu_fmod_api api;
    mu_audio_engine_config config;
    char *game_root;
    int created, initialised;
    engine_sound **sounds;
    size_t sound_count, sound_capacity;
    uint32_t next_sound;
    engine_group groups[MAX_GROUPS];
    voice voices[MU_AUDIO_VOICES];
    uint64_t next_channel;
    pending_end *pending;
    size_t pending_count, pending_capacity;
};

static void logf_engine(mu_audio_engine *e, const char *format, ...)
{
    if (!e->config.log) return;
    char message[600];
    va_list args;
    va_start(args, format);
    vsnprintf(message, sizeof message, format, args);
    va_end(args);
    e->config.log(e->config.log_ctx, message);
}

/* ---- paths and decoding --------------------------------------------------- */

int mu_audio_resolve_path(const char *game_root, const char *client_path, char *out, size_t out_size)
{
    char current[4096];
    snprintf(current, sizeof current, "%s", game_root && *game_root ? game_root : ".");
    const char *p = client_path;
    while (*p) {
        while (*p == '\\' || *p == '/') p++;
        if (!*p) break;
        const char *end = p;
        while (*end && *end != '\\' && *end != '/') end++;
        size_t length = (size_t)(end - p);
        char component[512];
        if (length >= sizeof component) return -1;
        memcpy(component, p, length);
        component[length] = 0;
        char candidate[4096];
        int written = snprintf(candidate, sizeof candidate, "%s/%s", current, component);
        if (written < 0 || (size_t)written >= sizeof candidate) return -1;
        struct stat st;
        if (stat(candidate, &st) != 0) {
            /* Windows paths are case-insensitive: search the directory. */
            DIR *dir = opendir(current);
            if (!dir) return -1;
            struct dirent *entry;
            int found = 0;
            while ((entry = readdir(dir))) {
                const char *a = entry->d_name, *b = component;
                while (*a && *b && tolower((unsigned char)*a) == tolower((unsigned char)*b)) { a++; b++; }
                if (!*a && !*b) {
                    snprintf(candidate, sizeof candidate, "%s/%s", current, entry->d_name);
                    found = 1;
                    break;
                }
            }
            closedir(dir);
            if (!found) return -1;
        }
        snprintf(current, sizeof current, "%s", candidate);
        p = end;
    }
    if ((size_t)snprintf(out, out_size, "%s", current) >= out_size) return -1;
    return 0;
}

static int read_file(const char *path, uint8_t **data, size_t *size)
{
    FILE *f = fopen(path, "rb");
    if (!f) return -1;
    if (fseek(f, 0, SEEK_END) != 0) { fclose(f); return -1; }
    long length = ftell(f);
    if (length < 0 || fseek(f, 0, SEEK_SET) != 0) { fclose(f); return -1; }
    uint8_t *buffer = malloc((size_t)length + 1);
    if (!buffer) { fclose(f); return -1; }
    size_t got = fread(buffer, 1, (size_t)length, f);
    fclose(f);
    if (got != (size_t)length) { free(buffer); return -1; }
    *data = buffer;
    *size = got;
    return 0;
}

int mu_audio_load_file(const char *game_root, const char *client_path, mu_pcm *out, char *error, size_t error_size)
{
    char host[4096];
    memset(out, 0, sizeof *out);
    if (mu_audio_resolve_path(game_root, client_path, host, sizeof host)) {
        snprintf(error, error_size, "file not found: %s", client_path);
        return MU_AUDIO_ERR_FILE_NOTFOUND;
    }
    uint8_t *data;
    size_t size;
    if (read_file(host, &data, &size)) {
        snprintf(error, error_size, "cannot read %s", host);
        return MU_AUDIO_ERR_FILE_NOTFOUND;
    }
    int result;
    if (size >= 12 && !memcmp(data, "RIFF", 4) && !memcmp(data + 8, "WAVE", 4)) {
        result = mu_wav_decode(data, size, out, error, error_size) ? MU_AUDIO_ERR_FORMAT : 0;
    } else {
        result = mu_audio_decode_platform(host, out, error, error_size) ? MU_AUDIO_ERR_FORMAT : 0;
    }
    free(data);
    return result;
}

/* ---- handles ----------------------------------------------------------- */

static engine_sound *find_sound(mu_audio_engine *e, mu_fmod_handle handle, size_t *index)
{
    for (size_t i = 0; i < e->sound_count; i++)
        if (e->sounds[i]->handle == handle) {
            if (index) *index = i;
            return e->sounds[i];
        }
    return NULL;
}

static voice *find_voice(mu_audio_engine *e, mu_fmod_handle handle)
{
    for (int i = 0; i < MU_AUDIO_VOICES; i++)
        if (e->voices[i].active && e->voices[i].handle == handle) return &e->voices[i];
    return NULL;
}

static int group_index(mu_audio_engine *e, mu_fmod_handle handle)
{
    if (handle < GROUP_BASE || handle >= GROUP_BASE + MAX_GROUPS) return -1;
    int index = (int)(handle - GROUP_BASE);
    return e->groups[index].used ? index : -1;
}

static void queue_end(mu_audio_engine *e, voice *v)
{
    if (!v->active) return;
    v->active = 0;
    if (!v->callback) return;
    if (e->pending_count == e->pending_capacity) {
        size_t capacity = e->pending_capacity ? e->pending_capacity*2 : 32;
        pending_end *items = realloc(e->pending, capacity*sizeof *items);
        if (!items) return;
        e->pending = items;
        e->pending_capacity = capacity;
    }
    e->pending[e->pending_count++] = (pending_end){v->callback, v->handle, v->user_data};
}

static int in_group(mu_audio_engine *e, int group, int ancestor)
{
    for (int g = group, guard = 0; g >= 0 && guard < MAX_GROUPS; g = e->groups[g].parent, guard++)
        if (g == ancestor) return 1;
    return 0;
}

/* ---- FMOD API ------------------------------------------------------------ */

#define ENGINE(ctx) ((mu_audio_engine *)(ctx))

static int32_t channel_stop(void *ctx, mu_fmod_handle channel)
{
    voice *v = find_voice(ENGINE(ctx), channel);
    if (!v) return MU_AUDIO_ERR_INVALID_HANDLE;
    queue_end(ENGINE(ctx), v);
    return MU_FMOD_OK;
}

static int32_t channel_set_callback(void *ctx, mu_fmod_handle channel, mu_fmod_channel_callback cb)
{
    voice *v = find_voice(ENGINE(ctx), channel);
    if (!v) return MU_AUDIO_ERR_INVALID_HANDLE;
    v->callback = cb;
    return MU_FMOD_OK;
}

static int32_t channel_set_user_data(void *ctx, mu_fmod_handle channel, void *data)
{
    voice *v = find_voice(ENGINE(ctx), channel);
    if (!v) return MU_AUDIO_ERR_INVALID_HANDLE;
    v->user_data = data;
    return MU_FMOD_OK;
}

static int32_t channel_get_user_data(void *ctx, mu_fmod_handle channel, void **data)
{
    mu_audio_engine *e = ENGINE(ctx);
    voice *v = find_voice(e, channel);
    if (v) {
        *data = v->user_data;
        return MU_FMOD_OK;
    }
    for (size_t i = 0; i < e->pending_count; i++)
        if (e->pending[i].channel == channel) {
            *data = e->pending[i].user_data;
            return MU_FMOD_OK;
        }
    *data = NULL;
    return MU_AUDIO_ERR_INVALID_HANDLE;
}

static int32_t sound_release(void *ctx, mu_fmod_handle sound)
{
    mu_audio_engine *e = ENGINE(ctx);
    size_t index;
    engine_sound *s = find_sound(e, sound, &index);
    if (!s) return MU_AUDIO_ERR_INVALID_HANDLE;
    for (int i = 0; i < MU_AUDIO_VOICES; i++)
        if (e->voices[i].active && e->voices[i].sound == s) queue_end(e, &e->voices[i]);
    mu_pcm_free(&s->pcm);
    free(s);
    memmove(e->sounds + index, e->sounds + index + 1, (e->sound_count - index - 1)*sizeof *e->sounds);
    e->sound_count--;
    return MU_FMOD_OK;
}

static int32_t system_create(void *ctx, mu_fmod_handle *system)
{
    mu_audio_engine *e = ENGINE(ctx);
    e->created = 1;
    memset(e->groups, 0, sizeof e->groups);
    e->groups[0] = (engine_group){1, 1.0f, 0, 0, -1, "master"};
    *system = SYSTEM_HANDLE;
    return MU_FMOD_OK;
}

static int check_system(mu_audio_engine *e, mu_fmod_handle system)
{
    return e->created && system == SYSTEM_HANDLE;
}

static int32_t system_release(void *ctx, mu_fmod_handle system)
{
    mu_audio_engine *e = ENGINE(ctx);
    if (!check_system(e, system)) return MU_AUDIO_ERR_INVALID_HANDLE;
    e->created = e->initialised = 0;
    return MU_FMOD_OK;
}

static int32_t system_set_output(void *ctx, mu_fmod_handle system, int32_t output)
{
    mu_audio_engine *e = ENGINE(ctx);
    if (!check_system(e, system)) return MU_AUDIO_ERR_INVALID_HANDLE;
    logf_engine(e, "output type %d (%s)", output, output == MU_FMOD_OUTPUT_DSOUND ? "DirectSound" :
                                                  output == MU_FMOD_OUTPUT_NOSOUND ? "no sound" : "other");
    return MU_FMOD_OK;
}

static int32_t system_get_num_drivers(void *ctx, mu_fmod_handle system, int32_t *count)
{
    mu_audio_engine *e = ENGINE(ctx);
    if (!check_system(e, system)) return MU_AUDIO_ERR_INVALID_HANDLE;
    *count = e->config.drivers;
    return MU_FMOD_OK;
}

static int32_t system_get_driver_info(void *ctx, mu_fmod_handle system, int32_t id, char *name, int32_t length,
                                      void *guid)
{
    (void)id;
    (void)guid;
    if (!check_system(ENGINE(ctx), system)) return MU_AUDIO_ERR_INVALID_HANDLE;
    if (name && length > 0) snprintf(name, (size_t)length, "%s", "mu native mixer");
    return MU_FMOD_OK;
}

static int32_t system_get_driver_caps(void *ctx, mu_fmod_handle system, int32_t id, uint32_t *caps,
                                      int32_t *min_frequency, int32_t *max_frequency, int32_t *speaker_mode)
{
    (void)id;
    mu_audio_engine *e = ENGINE(ctx);
    if (!check_system(e, system)) return MU_AUDIO_ERR_INVALID_HANDLE;
    if (caps) *caps = 0;
    if (min_frequency) *min_frequency = (int32_t)e->config.rate;
    if (max_frequency) *max_frequency = (int32_t)e->config.rate;
    if (speaker_mode) *speaker_mode = MU_FMOD_SPEAKERMODE_STEREO;
    return MU_FMOD_OK;
}

static int32_t system_set_software_format(void *ctx, mu_fmod_handle system, int32_t rate, int32_t format,
                                          int32_t output_channels, int32_t max_input_channels, int32_t resampler)
{
    (void)rate; (void)format; (void)output_channels; (void)max_input_channels; (void)resampler;
    return check_system(ENGINE(ctx), system) ? MU_FMOD_OK : MU_AUDIO_ERR_INVALID_HANDLE;
}

static int32_t system_set_dsp_buffer_size(void *ctx, mu_fmod_handle system, uint32_t length, int32_t count)
{
    (void)length; (void)count;
    return check_system(ENGINE(ctx), system) ? MU_FMOD_OK : MU_AUDIO_ERR_INVALID_HANDLE;
}

static int32_t system_set_speaker_mode(void *ctx, mu_fmod_handle system, int32_t mode)
{
    (void)mode;
    return check_system(ENGINE(ctx), system) ? MU_FMOD_OK : MU_AUDIO_ERR_INVALID_HANDLE;
}

static int32_t system_init(void *ctx, mu_fmod_handle system, int32_t max_channels, uint32_t flags, void *extra)
{
    (void)flags; (void)extra;
    mu_audio_engine *e = ENGINE(ctx);
    if (!check_system(e, system)) return MU_AUDIO_ERR_INVALID_HANDLE;
    logf_engine(e, "init: %d channels, %u Hz stereo mixer", max_channels, e->config.rate);
    e->initialised = 1;
    return MU_FMOD_OK;
}

static int32_t system_close(void *ctx, mu_fmod_handle system)
{
    mu_audio_engine *e = ENGINE(ctx);
    if (!check_system(e, system)) return MU_AUDIO_ERR_INVALID_HANDLE;
    for (int i = 0; i < MU_AUDIO_VOICES; i++) queue_end(e, &e->voices[i]);
    e->initialised = 0;
    return MU_FMOD_OK;
}

static int32_t system_update(void *ctx, mu_fmod_handle system)
{
    mu_audio_engine *e = ENGINE(ctx);
    if (!check_system(e, system)) return MU_AUDIO_ERR_INVALID_HANDLE;
    /* Callbacks may stop or start channels; deliver a snapshot. */
    size_t count = e->pending_count;
    pending_end *items = count ? malloc(count*sizeof *items) : NULL;
    if (count && !items) return MU_AUDIO_ERR_MEMORY;
    if (count) memcpy(items, e->pending, count*sizeof *items);
    for (size_t i = 0; i < count; i++)
        items[i].callback(items[i].channel, MU_FMOD_CHANNEL_CALLBACKTYPE_END, NULL, NULL);
    memmove(e->pending, e->pending + count, (e->pending_count - count)*sizeof *e->pending);
    e->pending_count -= count;
    free(items);
    return MU_FMOD_OK;
}

static int32_t create(mu_audio_engine *e, mu_fmod_handle system, const char *path, uint32_t mode, int stream,
                      mu_fmod_handle *sound)
{
    if (!check_system(e, system) || !e->initialised) return MU_AUDIO_ERR_INVALID_HANDLE;
    engine_sound *s = calloc(1, sizeof *s);
    if (!s) return MU_AUDIO_ERR_MEMORY;
    char error[600];
    int result = mu_audio_load_file(e->game_root, path, &s->pcm, error, sizeof error);
    if (result) {
        logf_engine(e, "open failed: %s", error);
        free(s);
        return result;
    }
    if (e->sound_count == e->sound_capacity) {
        size_t capacity = e->sound_capacity ? e->sound_capacity*2 : 64;
        engine_sound **items = realloc(e->sounds, capacity*sizeof *items);
        if (!items) {
            mu_pcm_free(&s->pcm);
            free(s);
            return MU_AUDIO_ERR_MEMORY;
        }
        e->sounds = items;
        e->sound_capacity = capacity;
    }
    s->handle = SOUND_BASE + e->next_sound++;
    s->mode = mode;
    s->stream = stream;
    e->sounds[e->sound_count++] = s;
    *sound = s->handle;
    return MU_FMOD_OK;
}

static int32_t system_create_stream(void *ctx, mu_fmod_handle system, const char *path, uint32_t mode,
                                    void *exinfo, mu_fmod_handle *sound)
{
    (void)exinfo;
    return create(ENGINE(ctx), system, path, mode, 1, sound);
}

static int32_t system_create_sound(void *ctx, mu_fmod_handle system, const char *path, uint32_t mode,
                                   void *exinfo, mu_fmod_handle *sound)
{
    (void)exinfo;
    return create(ENGINE(ctx), system, path, mode, 0, sound);
}

static int32_t system_create_channel_group(void *ctx, mu_fmod_handle system, const char *name,
                                           mu_fmod_handle *group)
{
    mu_audio_engine *e = ENGINE(ctx);
    if (!check_system(e, system)) return MU_AUDIO_ERR_INVALID_HANDLE;
    for (int i = 1; i < MAX_GROUPS; i++) {
        if (!e->groups[i].used) {
            e->groups[i] = (engine_group){1, 1.0f, 0, 0, 0, ""};
            snprintf(e->groups[i].name, sizeof e->groups[i].name, "%s", name ? name : "");
            *group = GROUP_BASE + (mu_fmod_handle)i;
            return MU_FMOD_OK;
        }
    }
    return MU_AUDIO_ERR_MEMORY;
}

/* Voice allocation: a free voice, else the voice with the largest priority
 * number (least important), oldest first, provided it is not more important
 * than the priority FMOD gives new channels (128). The client lowers the
 * number afterwards (0 music, 2 effects), so a full set of client channels is
 * stolen oldest-effect-first and music last. */
static voice *allocate_voice(mu_audio_engine *e)
{
    for (int i = 0; i < MU_AUDIO_VOICES; i++)
        if (!e->voices[i].active) return &e->voices[i];
    voice *chosen = NULL;
    for (int i = 0; i < MU_AUDIO_VOICES; i++) {
        voice *v = &e->voices[i];
        if (!chosen || v->priority > chosen->priority ||
            (v->priority == chosen->priority && v->serial < chosen->serial))
            chosen = v;
    }
    queue_end(e, chosen);
    logf_engine(e, "voice stolen (priority %d)", chosen->priority);
    return chosen;
}

static int32_t system_play_sound(void *ctx, mu_fmod_handle system, int32_t index, mu_fmod_handle sound,
                                 int32_t paused, mu_fmod_handle *channel)
{
    (void)index;
    mu_audio_engine *e = ENGINE(ctx);
    if (!check_system(e, system) || !e->initialised) return MU_AUDIO_ERR_INVALID_HANDLE;
    engine_sound *s = find_sound(e, sound, NULL);
    if (!s) return MU_AUDIO_ERR_INVALID_HANDLE;
    voice *v = allocate_voice(e);
    *v = (voice){1, CHANNEL_BASE + (mu_fmod_handle)(e->next_channel & 0xffffff), s, 0.0, paused != 0,
                 (s->mode & MU_FMOD_LOOP_NORMAL) != 0, 0, 128, NULL, NULL, e->next_channel};
    e->next_channel++;
    *channel = v->handle;
    return MU_FMOD_OK;
}

static int32_t system_get_master_channel_group(void *ctx, mu_fmod_handle system, mu_fmod_handle *group)
{
    if (!check_system(ENGINE(ctx), system)) return MU_AUDIO_ERR_INVALID_HANDLE;
    *group = GROUP_BASE;
    return MU_FMOD_OK;
}

static int32_t channel_set_paused(void *ctx, mu_fmod_handle channel, int32_t paused)
{
    voice *v = find_voice(ENGINE(ctx), channel);
    if (!v) return MU_AUDIO_ERR_INVALID_HANDLE;
    v->paused = paused != 0;
    return MU_FMOD_OK;
}

static int32_t channel_set_priority(void *ctx, mu_fmod_handle channel, int32_t priority)
{
    voice *v = find_voice(ENGINE(ctx), channel);
    if (!v) return MU_AUDIO_ERR_INVALID_HANDLE;
    v->priority = priority;
    return MU_FMOD_OK;
}

static int32_t channel_set_channel_group(void *ctx, mu_fmod_handle channel, mu_fmod_handle group)
{
    mu_audio_engine *e = ENGINE(ctx);
    voice *v = find_voice(e, channel);
    int g = group_index(e, group);
    if (!v || g < 0) return MU_AUDIO_ERR_INVALID_HANDLE;
    v->group = g;
    return MU_FMOD_OK;
}

static int32_t channel_set_mode(void *ctx, mu_fmod_handle channel, uint32_t mode)
{
    voice *v = find_voice(ENGINE(ctx), channel);
    if (!v) return MU_AUDIO_ERR_INVALID_HANDLE;
    if (mode & MU_FMOD_LOOP_NORMAL) v->loop = 1;
    if (mode & 1u) v->loop = 0;  /* FMOD_LOOP_OFF */
    return MU_FMOD_OK;
}

static int32_t group_release(void *ctx, mu_fmod_handle group)
{
    mu_audio_engine *e = ENGINE(ctx);
    int g = group_index(e, group);
    if (g <= 0) return MU_AUDIO_ERR_INVALID_HANDLE;
    for (int i = 0; i < MU_AUDIO_VOICES; i++)
        if (e->voices[i].active && e->voices[i].group == g) e->voices[i].group = 0;
    e->groups[g].used = 0;
    return MU_FMOD_OK;
}

static int32_t group_set_volume(void *ctx, mu_fmod_handle group, float volume)
{
    mu_audio_engine *e = ENGINE(ctx);
    int g = group_index(e, group);
    if (g < 0) return MU_AUDIO_ERR_INVALID_HANDLE;
    e->groups[g].volume = volume;
    return MU_FMOD_OK;
}

static int32_t group_get_volume(void *ctx, mu_fmod_handle group, float *volume)
{
    mu_audio_engine *e = ENGINE(ctx);
    int g = group_index(e, group);
    if (g < 0) return MU_AUDIO_ERR_INVALID_HANDLE;
    *volume = e->groups[g].volume;
    return MU_FMOD_OK;
}

static int32_t group_set_paused(void *ctx, mu_fmod_handle group, int32_t paused)
{
    mu_audio_engine *e = ENGINE(ctx);
    int g = group_index(e, group);
    if (g < 0) return MU_AUDIO_ERR_INVALID_HANDLE;
    e->groups[g].paused = paused != 0;
    return MU_FMOD_OK;
}

static int32_t group_get_paused(void *ctx, mu_fmod_handle group, int32_t *paused)
{
    mu_audio_engine *e = ENGINE(ctx);
    int g = group_index(e, group);
    if (g < 0) return MU_AUDIO_ERR_INVALID_HANDLE;
    *paused = e->groups[g].paused;
    return MU_FMOD_OK;
}

static int32_t group_set_mute(void *ctx, mu_fmod_handle group, int32_t mute)
{
    mu_audio_engine *e = ENGINE(ctx);
    int g = group_index(e, group);
    if (g < 0) return MU_AUDIO_ERR_INVALID_HANDLE;
    e->groups[g].mute = mute != 0;
    return MU_FMOD_OK;
}

static int32_t group_get_mute(void *ctx, mu_fmod_handle group, int32_t *mute)
{
    mu_audio_engine *e = ENGINE(ctx);
    int g = group_index(e, group);
    if (g < 0) return MU_AUDIO_ERR_INVALID_HANDLE;
    *mute = e->groups[g].mute;
    return MU_FMOD_OK;
}

static int32_t group_stop(void *ctx, mu_fmod_handle group)
{
    mu_audio_engine *e = ENGINE(ctx);
    int g = group_index(e, group);
    if (g < 0) return MU_AUDIO_ERR_INVALID_HANDLE;
    for (int i = 0; i < MU_AUDIO_VOICES; i++)
        if (e->voices[i].active && in_group(e, e->voices[i].group, g)) queue_end(e, &e->voices[i]);
    return MU_FMOD_OK;
}

static int32_t group_add_group(void *ctx, mu_fmod_handle group, mu_fmod_handle child)
{
    mu_audio_engine *e = ENGINE(ctx);
    int g = group_index(e, group), c = group_index(e, child);
    if (g < 0 || c <= 0 || in_group(e, g, c)) return MU_AUDIO_ERR_INVALID_HANDLE;
    e->groups[c].parent = g;
    return MU_FMOD_OK;
}

/* ---- engine ---------------------------------------------------------------- */

mu_audio_engine *mu_audio_engine_new(const mu_audio_engine_config *config)
{
    mu_audio_engine *e = calloc(1, sizeof *e);
    if (!e) return NULL;
    if (config) e->config = *config;
    if (!e->config.rate) e->config.rate = 44100;
    /* 0 selects the default single driver; a negative value reports none. */
    e->config.drivers = e->config.drivers == 0 ? 1 : e->config.drivers < 0 ? 0 : e->config.drivers;
    if (e->config.game_root) {
        size_t n = strlen(e->config.game_root);
        e->game_root = malloc(n + 1);
        if (!e->game_root) { free(e); return NULL; }
        memcpy(e->game_root, e->config.game_root, n + 1);
    }
    e->api = (mu_fmod_api){
        e, channel_stop, channel_set_callback, channel_set_user_data, channel_get_user_data, sound_release,
        system_create, system_release, system_set_output, system_get_num_drivers, system_get_driver_info,
        system_get_driver_caps, system_set_software_format, system_set_dsp_buffer_size, system_set_speaker_mode,
        system_init, system_close, system_update, system_create_stream, system_create_sound,
        system_create_channel_group, system_play_sound, system_get_master_channel_group, channel_set_paused,
        channel_set_priority, channel_set_channel_group, channel_set_mode, group_release, group_set_volume,
        group_get_volume, group_set_paused, group_get_paused, group_set_mute, group_get_mute, group_stop,
        group_add_group};
    return e;
}

void mu_audio_engine_free(mu_audio_engine *e)
{
    if (!e) return;
    for (size_t i = 0; i < e->sound_count; i++) {
        mu_pcm_free(&e->sounds[i]->pcm);
        free(e->sounds[i]);
    }
    free(e->sounds);
    free(e->pending);
    free(e->game_root);
    free(e);
}

const mu_fmod_api *mu_audio_engine_api(mu_audio_engine *e) { return &e->api; }
uint32_t mu_audio_engine_rate(const mu_audio_engine *e) { return e->config.rate; }

int mu_audio_engine_active_voices(const mu_audio_engine *e)
{
    int n = 0;
    for (int i = 0; i < MU_AUDIO_VOICES; i++) n += e->voices[i].active;
    return n;
}

static float voice_gain(const mu_audio_engine *e, const voice *v, int *paused)
{
    float gain = 1.0f;
    *paused = v->paused;
    for (int g = v->group, guard = 0; g >= 0 && guard < MAX_GROUPS; g = e->groups[g].parent, guard++) {
        const engine_group *group = &e->groups[g];
        if (group->mute) gain = 0.0f;
        else gain *= group->volume;
        if (group->paused) *paused = 1;
    }
    return gain;
}

void mu_audio_engine_mix(mu_audio_engine *e, float *out, uint32_t frames)
{
    memset(out, 0, (size_t)frames*2*sizeof *out);
    for (int i = 0; i < MU_AUDIO_VOICES; i++) {
        voice *v = &e->voices[i];
        if (!v->active) continue;
        int paused;
        float gain = voice_gain(e, v, &paused);
        if (paused) continue;
        const mu_pcm *pcm = &v->sound->pcm;
        if (!pcm->frames) {
            queue_end(e, v);
            continue;
        }
        const double step = (double)pcm->rate/(double)e->config.rate;
        const uint32_t channels = pcm->channels;
        for (uint32_t f = 0; f < frames; f++) {
            uint32_t index = (uint32_t)v->position;
            double fraction = v->position - (double)index;
            uint32_t next = index + 1;
            int has_next = next < pcm->frames || v->loop;
            if (next >= pcm->frames) next = v->loop ? 0 : index;
            const float *a = pcm->samples + (size_t)index*channels;
            const float *b = pcm->samples + (size_t)next*channels;
            float left, right;
            float t = has_next ? (float)fraction : 0.0f;
            left = a[0] + (b[0] - a[0])*t;
            right = channels > 1 ? a[1] + (b[1] - a[1])*t : left;
            out[2*f] += left*gain;
            out[2*f + 1] += right*gain;
            v->position += step;
            if (v->position >= (double)pcm->frames) {
                if (v->loop) {
                    while (v->position >= (double)pcm->frames) v->position -= (double)pcm->frames;
                } else {
                    queue_end(e, v);
                    break;
                }
            }
        }
    }
}
