/* The client's FMOD wrapper (0x010aa9xx..0x010acc20), its sound table
 * (0x00a6ab76..0x00a6ae37) and music player (0x0120f5a0, 0x0120f602).
 *
 * Every FMOD call the client makes is issued through mu_fmod_api in the same
 * order with the same arguments, including calls whose results the client
 * ignores. Reference counting reproduces the client's shared_ptr ownership of
 * a loaded file: the FMOD sound is released when the last owner (sound-table
 * entry or the music slot) lets go, which also drops it from the path cache.
 */
#include "client_audio.h"

#include <stdlib.h>
#include <string.h>

const char *const mu_audio_group_names[MU_AUDIO_GROUPS] = {"Music", "Environment", "Effect"};

static mu_audio_client *callback_client;

void mu_audio_client_init_state(mu_audio_client *client, const mu_fmod_api *api)
{
    memset(client, 0, sizeof *client);
    client->api = *api;
}

mu_audio_client *mu_audio_client_new(const mu_fmod_api *api)
{
    mu_audio_client *client = malloc(sizeof *client);
    if (client) mu_audio_client_init_state(client, api);
    return client;
}

void mu_audio_client_delete(mu_audio_client *client)
{
    if (!client) return;
    mu_audio_client_free_state(client);
    free(client);
}

static int failed(int32_t result) { return result != MU_FMOD_OK; } /* 0x010aba19 */

static char *copy_string(const char *text)
{
    size_t n = strlen(text);
    char *out = malloc(n + 1);
    if (out) memcpy(out, text, n + 1);
    return out;
}

/* ---- path cache ---------------------------------------------------------- */

/* The cache is a std::map whose comparator is _stricmp(a, b) < 0: paths that
 * differ only in ASCII case share one FMOD sound (verified in Unicorn). */
static size_t cache_lower_bound(const mu_audio_client *client, const char *path)
{
    size_t lo = 0, hi = client->cache_count;
    while (lo < hi) {
        size_t mid = (lo + hi)/2;
        if (mu_audio_stricmp(client->cache[mid]->path, path) < 0) lo = mid + 1;
        else hi = mid;
    }
    return lo;
}

static mu_audio_sound *cache_find(mu_audio_client *client, const char *path, size_t *index)
{
    size_t i = cache_lower_bound(client, path);
    if (i < client->cache_count && mu_audio_stricmp(client->cache[i]->path, path) == 0) {
        if (index) *index = i;
        return client->cache[i];
    }
    return NULL;
}

static int cache_insert(mu_audio_client *client, mu_audio_sound *sound)
{
    if (client->cache_count == client->cache_capacity) {
        size_t capacity = client->cache_capacity ? client->cache_capacity*2 : 16;
        mu_audio_sound **items = realloc(client->cache, capacity*sizeof *items);
        if (!items) return 0;
        client->cache = items;
        client->cache_capacity = capacity;
    }
    size_t at = cache_lower_bound(client, sound->path);
    memmove(client->cache + at + 1, client->cache + at, (client->cache_count - at)*sizeof *client->cache);
    client->cache[at] = sound;
    client->cache_count++;
    return 1;
}

/* Holder destructor 0x010aaa2a. */
static void sound_destroy(mu_audio_client *client, mu_audio_sound *sound)
{
    if (sound->sound) {
        client->api.sound_release(client->api.ctx, sound->sound);
        sound->sound = 0;
    }
    size_t index;
    if (cache_find(client, sound->path, &index) == sound) {  /* 0x010aacab */
        memmove(client->cache + index, client->cache + index + 1,
                (client->cache_count - index - 1)*sizeof *client->cache);
        client->cache_count--;
    }
    free(sound->path);
    free(sound);
}

void mu_audio_sound_unref(mu_audio_client *client, mu_audio_sound *sound)
{
    if (sound && --sound->references == 0) sound_destroy(client, sound);
}

mu_audio_sound *mu_audio_create_sound(mu_audio_client *client, const char *path, int kind)
{
    if (!client->system) return NULL;
    mu_audio_sound *cached = cache_find(client, path, NULL);
    if (cached) {
        cached->references++;
        return cached;
    }
    mu_fmod_handle sound = 0;
    switch (kind) {
    case 0: case 1:
        if (failed(client->api.system_create_sound(client->api.ctx, client->system, path,
                                                   MU_FMOD_CLIENT_MODE, NULL, &sound)))
            return NULL;
        break;
    case 2:
        if (failed(client->api.system_create_stream(client->api.ctx, client->system, path,
                                                    MU_FMOD_CLIENT_MODE, NULL, &sound)))
            return NULL;
        break;
    default:
        break;  /* the client still creates a holder with no FMOD sound */
    }
    mu_audio_sound *holder = calloc(1, sizeof *holder);
    if (!holder) return NULL;
    holder->path = copy_string(path);
    holder->sound = sound;
    holder->references = 1;
    if (!holder->path || !cache_insert(client, holder)) {
        free(holder->path);
        free(holder);
        return NULL;
    }
    return holder;
}

/* ---- system ------------------------------------------------------------ */

int mu_audio_system_create(mu_audio_client *client)
{
    return !failed(client->api.system_create(client->api.ctx, &client->system));
}

int mu_audio_system_init(mu_audio_client *client, void *extra_driver_data)
{
    const mu_fmod_api *a = &client->api;
    if (client->system) return 1;
    if (!mu_audio_system_create(client)) return 0;
    mu_fmod_handle s = client->system;
    int32_t drivers = 0;
    if (failed(a->system_get_num_drivers(a->ctx, s, &drivers))) return 0;
    if (drivers == 0) {
        if (failed(a->system_set_output(a->ctx, s, MU_FMOD_OUTPUT_NOSOUND))) return 0;
    } else {
        if (failed(a->system_set_output(a->ctx, s, MU_FMOD_OUTPUT_DSOUND))) return 0;
        uint32_t caps = 0;
        int32_t speaker_mode = 0;
        if (failed(a->system_get_driver_caps(a->ctx, s, 0, &caps, NULL, NULL, &speaker_mode))) return 0;
        if (failed(a->system_set_speaker_mode(a->ctx, s, speaker_mode))) return 0;
        if (caps & MU_FMOD_CAPS_HARDWARE_EMULATED) {
            if (failed(a->system_set_dsp_buffer_size(a->ctx, s, 1024, 10))) return 0;
        }
        char name[256];
        memset(name, 0, sizeof name);
        if (failed(a->system_get_driver_info(a->ctx, s, 0, name, 256, NULL))) return 0;
        name[sizeof name - 1] = 0;
        if (strstr(name, "SigmaTel")) {
            if (failed(a->system_set_software_format(a->ctx, s, 48000, MU_FMOD_SOUND_FORMAT_PCMFLOAT, 0, 0,
                                                     MU_FMOD_RESAMPLER_LINEAR)))
                return 0;
        }
    }
    int32_t result = a->system_init(a->ctx, s, MU_FMOD_MAX_CHANNELS, MU_FMOD_INIT_FLAGS, extra_driver_data);
    if (failed(result)) {
        if (result != MU_FMOD_ERR_OUTPUT_CREATEBUFFER) return 0;
        if (failed(a->system_set_speaker_mode(a->ctx, s, MU_FMOD_SPEAKERMODE_STEREO))) return 0;
        if (failed(a->system_init(a->ctx, s, MU_FMOD_MAX_CHANNELS, MU_FMOD_INIT_FLAGS, extra_driver_data)))
            return 0;
    }
    if (failed(a->system_get_master_channel_group(a->ctx, s, &client->master))) return 0;
    for (int i = 0; i < MU_AUDIO_GROUPS; i++) {
        if (failed(a->system_create_channel_group(a->ctx, s, mu_audio_group_names[i], &client->groups[i])))
            return 0;
        if (failed(a->group_add_group(a->ctx, client->master, client->groups[i]))) return 0;
    }
    return 1;
}

void mu_audio_system_update(mu_audio_client *client) /* 0x010aafdd */
{
    if (client->system) client->api.system_update(client->api.ctx, client->system);
}

int mu_audio_play(mu_audio_client *client, mu_audio_sound *sound, int group, int loop,
                  mu_fmod_handle *channel)
{
    const mu_fmod_api *a = &client->api;
    if (!client->system || !sound || !sound->sound) return 0;
    mu_fmod_handle ch = 0;
    if (failed(a->system_play_sound(a->ctx, client->system, MU_FMOD_CHANNEL_FREE, sound->sound, 1, &ch)))
        return 0;
    if (failed(a->channel_set_channel_group(a->ctx, ch, client->groups[group]))) {
        a->channel_stop(a->ctx, ch);
        return 0;
    }
    if (failed(a->channel_set_priority(a->ctx, ch, group))) {
        a->channel_stop(a->ctx, ch);
        return 0;
    }
    if (loop && failed(a->channel_set_mode(a->ctx, ch, MU_FMOD_LOOP_NORMAL))) {
        a->channel_stop(a->ctx, ch);
        return 0;
    }
    if (failed(a->channel_set_paused(a->ctx, ch, 0))) {
        a->channel_stop(a->ctx, ch);
        return 0;
    }
    if (channel) *channel = ch;
    return 1;
}

void mu_audio_stop_group(mu_audio_client *client, int group)
{
    if (client->groups[group]) client->api.group_stop(client->api.ctx, client->groups[group]);
}

void mu_audio_stop_master(mu_audio_client *client)
{
    if (client->master) client->api.group_stop(client->api.ctx, client->master);
}

void mu_audio_set_master_volume(mu_audio_client *client, float volume)
{
    if (client->master) client->api.group_set_volume(client->api.ctx, client->master, volume);
}

void mu_audio_set_group_volume(mu_audio_client *client, int group, float volume)
{
    if (client->groups[group]) client->api.group_set_volume(client->api.ctx, client->groups[group], volume);
}

void mu_audio_set_master_mute(mu_audio_client *client, int mute)
{
    if (client->master) client->api.group_set_mute(client->api.ctx, client->master, mute ? 1 : 0);
}

void mu_audio_set_group_mute(mu_audio_client *client, int group, int mute)
{
    if (client->groups[group]) client->api.group_set_mute(client->api.ctx, client->groups[group], mute ? 1 : 0);
}

static float get_volume(mu_audio_client *client, mu_fmod_handle group)
{
    if (!group) return 0.0f;
    float volume = 0.0f;
    client->api.group_get_volume(client->api.ctx, group, &volume);
    return volume;
}

static int get_mute(mu_audio_client *client, mu_fmod_handle group)
{
    if (!group) return 0;
    int32_t mute = 0;
    client->api.group_get_mute(client->api.ctx, group, &mute);
    return mute != 0;
}

float mu_audio_get_group_volume(mu_audio_client *client, int group)
{
    return get_volume(client, client->groups[group]);
}

int mu_audio_get_group_mute(mu_audio_client *client, int group)
{
    return get_mute(client, client->groups[group]);
}

void mu_audio_apply_settings(mu_audio_client *client, const mu_audio_settings *settings)
{
    if (!client->system) return;
    mu_audio_set_master_mute(client, settings->master_mute);
    mu_audio_set_master_volume(client, settings->master_volume);
    for (int i = 0; i < MU_AUDIO_GROUPS; i++) {
        mu_audio_set_group_mute(client, i, settings->group_mute[i]);
        mu_audio_set_group_volume(client, i, settings->group_volume[i]);
    }
}

void mu_audio_read_settings(mu_audio_client *client, mu_audio_settings *settings)
{
    if (!settings) return;
    settings->master_mute = get_mute(client, client->master);
    settings->master_volume = get_volume(client, client->master);
    for (int i = 0; i < MU_AUDIO_GROUPS; i++) {
        settings->group_mute[i] = mu_audio_get_group_mute(client, i);
        settings->group_volume[i] = mu_audio_get_group_volume(client, i);
    }
}

/* ---- sound table --------------------------------------------------------- */

static size_t entry_lower_bound(const mu_audio_client *client, int32_t id)
{
    size_t lo = 0, hi = client->entry_count;
    while (lo < hi) {
        size_t mid = (lo + hi)/2;
        if (client->entries[mid]->id < id) lo = mid + 1;
        else hi = mid;
    }
    return lo;
}

static mu_audio_entry *entry_find(const mu_audio_client *client, int32_t id)
{
    size_t i = entry_lower_bound(client, id);
    return i < client->entry_count && client->entries[i]->id == id ? client->entries[i] : NULL;
}

const mu_audio_entry *mu_audio_snd_find(const mu_audio_client *client, int32_t id)
{
    return entry_find(client, id);
}

int mu_audio_snd_load(mu_audio_client *client, int32_t id, const char *path,
                      int32_t legacy_channels, int32_t legacy_3d)
{
    (void)legacy_channels;
    (void)legacy_3d;
    if (entry_find(client, id)) return 1;
    mu_audio_sound *sound = mu_audio_create_sound(client, path, 2);
    if (!sound) return 0;
    mu_audio_entry *entry = calloc(1, sizeof *entry);
    if (!entry) {
        mu_audio_sound_unref(client, sound);
        return 0;
    }
    entry->id = id;
    entry->sound = sound;
    if (client->entry_count == client->entry_capacity) {
        size_t capacity = client->entry_capacity ? client->entry_capacity*2 : 64;
        mu_audio_entry **items = realloc(client->entries, capacity*sizeof *items);
        if (!items) {
            mu_audio_sound_unref(client, sound);
            free(entry);
            return 0;
        }
        client->entries = items;
        client->entry_capacity = capacity;
    }
    size_t at = entry_lower_bound(client, id);
    memmove(client->entries + at + 1, client->entries + at, (client->entry_count - at)*sizeof *client->entries);
    client->entries[at] = entry;
    client->entry_count++;
    return 1;
}

int mu_audio_snd_play(mu_audio_client *client, int32_t id, const void *object_ignored, int32_t loop)
{
    (void)object_ignored;
    mu_audio_entry *entry = entry_find(client, id);
    if (!entry) return 0;
    if (entry->playing) return 1;
    mu_fmod_handle channel = 0;
    if (!mu_audio_play(client, entry->sound, MU_AUDIO_GROUP_EFFECT, loop != 0, &channel)) return 0;
    entry->playing = 1;
    entry->channel = channel;
    if (failed(client->api.channel_set_user_data(client->api.ctx, channel, entry))) return 0;
    if (failed(client->api.channel_set_callback(client->api.ctx, channel, mu_audio_fmod_channel_callback)))
        return 0;
    return 1;
}

void mu_audio_snd_stop(mu_audio_client *client, int32_t id)
{
    mu_audio_entry *entry = entry_find(client, id);
    if (entry && entry->channel) client->api.channel_stop(client->api.ctx, entry->channel);
}

void mu_audio_snd_remove(mu_audio_client *client, int32_t id)
{
    size_t at = entry_lower_bound(client, id);
    if (at >= client->entry_count || client->entries[at]->id != id) return;
    mu_audio_entry *entry = client->entries[at];
    memmove(client->entries + at, client->entries + at + 1, (client->entry_count - at - 1)*sizeof *client->entries);
    client->entry_count--;
    mu_audio_sound_unref(client, entry->sound);
    entry->sound = NULL;
    /* The client frees the node; FMOD may still hold its address as channel
     * user data and the end callback writes through it. Park it instead. */
    if (client->detached_count == client->detached_capacity) {
        size_t capacity = client->detached_capacity ? client->detached_capacity*2 : 16;
        mu_audio_entry **items = realloc(client->detached, capacity*sizeof *items);
        if (!items) {
            free(entry);
            return;
        }
        client->detached = items;
        client->detached_capacity = capacity;
    }
    client->detached[client->detached_count++] = entry;
}

int32_t mu_audio_channel_callback(mu_audio_client *client, mu_fmod_handle channel, int32_t type)
{
    if (type != MU_FMOD_CHANNEL_CALLBACKTYPE_END) return 0;
    void *data = NULL;
    client->api.channel_get_user_data(client->api.ctx, channel, &data);
    if (data) {
        mu_audio_entry *entry = data;
        entry->playing = 0;
        entry->channel = 0;
    }
    return 0;
}

void mu_audio_set_callback_client(mu_audio_client *client) { callback_client = client; }

int32_t mu_audio_fmod_channel_callback(mu_fmod_handle channel, int32_t type, void *c1, void *c2)
{
    (void)c1;
    (void)c2;
    return callback_client ? mu_audio_channel_callback(callback_client, channel, type) : 0;
}

/* ---- music ----------------------------------------------------------------- */

int mu_audio_stricmp(const char *a, const char *b)
{
    for (;; a++, b++) {
        int ca = (unsigned char)*a, cb = (unsigned char)*b;
        if (ca >= 'A' && ca <= 'Z') ca += 'a' - 'A';
        if (cb >= 'A' && cb <= 'Z') cb += 'a' - 'A';
        if (ca != cb || !ca) return ca - cb;
    }
}

void mu_audio_play_mp3(mu_audio_client *client, const char *path)
{
    if (client->music) {
        if (mu_audio_stricmp(client->music->path, path) == 0) return;
        mu_audio_stop_group(client, MU_AUDIO_GROUP_MUSIC);
        mu_audio_sound *old = client->music;
        client->music = NULL;
        mu_audio_sound_unref(client, old);
    }
    client->music = mu_audio_create_sound(client, path, 0);
    if (client->music) mu_audio_play(client, client->music, MU_AUDIO_GROUP_MUSIC, 1, NULL);
}

void mu_audio_stop_mp3(mu_audio_client *client, const char *path)
{
    if (!client->music) return;
    if (mu_audio_stricmp(client->music->path, path) != 0) return;
    mu_audio_stop_group(client, MU_AUDIO_GROUP_MUSIC);
    mu_audio_sound *old = client->music;
    client->music = NULL;
    mu_audio_sound_unref(client, old);
}

/* ---- shutdown (0x010aba2a) --------------------------------------------- */

void mu_audio_system_shutdown(mu_audio_client *client)
{
    const mu_fmod_api *a = &client->api;
    mu_audio_stop_master(client);
    /* The destructor detaches every cached holder in path order (0x010aaa2a
     * on each live one releases its sound and leaves the cache). */
    for (size_t i = 0; i < client->cache_count; i++) {
        mu_audio_sound *sound = client->cache[i];
        if (sound->sound) {
            a->sound_release(a->ctx, sound->sound);
            sound->sound = 0;
        }
    }
    client->cache_count = 0;
    for (int i = 0; i < MU_AUDIO_GROUPS; i++)
        if (client->groups[i]) a->group_release(a->ctx, client->groups[i]);
    if (client->system) {
        a->system_close(a->ctx, client->system);
        a->system_release(a->ctx, client->system);
    }
    client->system = 0;
}

void mu_audio_client_free_state(mu_audio_client *client)
{
    if (callback_client == client) callback_client = NULL;
    for (size_t i = 0; i < client->entry_count; i++) {
        mu_audio_entry *entry = client->entries[i];
        mu_audio_sound *sound = entry->sound;
        if (sound && --sound->references == 0) {
            free(sound->path);
            free(sound);
        }
        free(entry);
    }
    if (client->music && --client->music->references == 0) {
        free(client->music->path);
        free(client->music);
    }
    for (size_t i = 0; i < client->detached_count; i++) free(client->detached[i]);
    free(client->detached);
    free(client->entries);
    free(client->cache);
    memset(client, 0, sizeof *client);
}

/* ---- options UI ------------------------------------------------------------ */

float mu_audio_level_to_volume(int32_t level)
{
    return (float)level/9.0f;
}

int32_t mu_audio_volume_to_level(float volume)
{
    float scaled = volume*9.0f;
    scaled = scaled + 0.5f;
    /* cvttss2si: truncation, and 0x80000000 for NaN or out-of-range values. */
    if (!(scaled > -2147483904.0f && scaled < 2147483648.0f)) return INT32_MIN;
    return (int32_t)scaled;
}
