/* Reconstructed client audio logic (NATIVE-AUDIO-001).
 *
 * The client drives FMOD Ex through 35 imported C++ methods (stdcall, `this`
 * on the stack). Those calls are the platform boundary: this module never
 * mixes audio itself. It reproduces the client's decisions and issues the
 * same boundary calls, in the same order and with the same arguments, through
 * the function table below. The native engine (native/core/mu_audio.c) and
 * the Unicorn validator (scripts/validate_audio.py) both implement the table.
 *
 * Client routines (restored text, main.exe SHA-256 3cf91f3c...b5527a):
 *   0x010aad03 system init          0x010aaa97 create sound (path cache)
 *   0x010aaffb play on a group       0x010ab480 apply settings
 *   0x010ab506 read settings         0x010ab15f stop a group
 *   0x00a6ab76 SND_Load              0x00a6ac96 SND_Play
 *   0x00a6ad76 SND_Stop              0x00a6add6 SND_Remove
 *   0x00a6ae37 channel callback      0x0120f602 PlayMp3, 0x0120f5a0 StopMp3
 *   0x0185280c..0x01854498           per-frame ambient and music selection
 *   0x018290be..0x018293a6           OpenWorld music-group volume rule
 * Names are investigator choices, not original symbols.
 */
#ifndef MU_CLIENT_AUDIO_H
#define MU_CLIENT_AUDIO_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ---- FMOD Ex boundary --------------------------------------------------- */

/* Constants observed as immediates in the client. */
enum {
    MU_FMOD_OK = 0,
    MU_FMOD_ERR_OUTPUT_CREATEBUFFER = 0x3a,  /* init retried with stereo */
    MU_FMOD_OUTPUT_NOSOUND = 2,
    MU_FMOD_OUTPUT_DSOUND = 6,
    MU_FMOD_CAPS_HARDWARE_EMULATED = 2,
    MU_FMOD_SPEAKERMODE_STEREO = 2,
    MU_FMOD_SOUND_FORMAT_PCMFLOAT = 5,
    MU_FMOD_RESAMPLER_LINEAR = 1,
    MU_FMOD_CHANNEL_FREE = -1,
    MU_FMOD_LOOP_NORMAL = 2,
    /* LOWMEM | HARDWARE | 2D | LOOP_OFF: the only mode the client uses. */
    MU_FMOD_CLIENT_MODE = 0x08000029,
    MU_FMOD_CHANNEL_CALLBACKTYPE_END = 0,
    MU_FMOD_MAX_CHANNELS = 16,
    MU_FMOD_INIT_FLAGS = 0
};

/* Channel groups created by init, in order, under the master group. */
enum { MU_AUDIO_GROUP_MUSIC = 0, MU_AUDIO_GROUP_ENVIRONMENT = 1, MU_AUDIO_GROUP_EFFECT = 2,
       MU_AUDIO_GROUPS = 3 };

typedef uint32_t mu_fmod_handle;  /* System*, Sound*, Channel*, ChannelGroup* */
typedef int32_t (*mu_fmod_channel_callback)(mu_fmod_handle channel, int32_t type,
                                            void *command1, void *command2);

/* One entry per imported method; the order is the import thunk order
 * (thunk 0x018eb289 + 6*k). Booleans are C++ bool (0 or 1). */
typedef struct mu_fmod_api {
    void *ctx;
    int32_t (*channel_stop)(void *ctx, mu_fmod_handle channel);                               /* 0 */
    int32_t (*channel_set_callback)(void *ctx, mu_fmod_handle channel, mu_fmod_channel_callback cb);
    int32_t (*channel_set_user_data)(void *ctx, mu_fmod_handle channel, void *data);
    int32_t (*channel_get_user_data)(void *ctx, mu_fmod_handle channel, void **data);
    int32_t (*sound_release)(void *ctx, mu_fmod_handle sound);
    int32_t (*system_create)(void *ctx, mu_fmod_handle *system);                              /* 5 */
    int32_t (*system_release)(void *ctx, mu_fmod_handle system);
    int32_t (*system_set_output)(void *ctx, mu_fmod_handle system, int32_t output);
    int32_t (*system_get_num_drivers)(void *ctx, mu_fmod_handle system, int32_t *count);
    int32_t (*system_get_driver_info)(void *ctx, mu_fmod_handle system, int32_t id, char *name,
                                      int32_t name_length, void *guid);
    int32_t (*system_get_driver_caps)(void *ctx, mu_fmod_handle system, int32_t id, uint32_t *caps,
                                      int32_t *min_frequency, int32_t *max_frequency,
                                      int32_t *speaker_mode);                                /* 10 */
    int32_t (*system_set_software_format)(void *ctx, mu_fmod_handle system, int32_t rate,
                                          int32_t format, int32_t output_channels,
                                          int32_t max_input_channels, int32_t resampler);
    int32_t (*system_set_dsp_buffer_size)(void *ctx, mu_fmod_handle system, uint32_t length,
                                          int32_t count);
    int32_t (*system_set_speaker_mode)(void *ctx, mu_fmod_handle system, int32_t mode);
    int32_t (*system_init)(void *ctx, mu_fmod_handle system, int32_t max_channels, uint32_t flags,
                           void *extra_driver_data);
    int32_t (*system_close)(void *ctx, mu_fmod_handle system);                                /* 15 */
    int32_t (*system_update)(void *ctx, mu_fmod_handle system);
    int32_t (*system_create_stream)(void *ctx, mu_fmod_handle system, const char *path, uint32_t mode,
                                    void *exinfo, mu_fmod_handle *sound);
    int32_t (*system_create_sound)(void *ctx, mu_fmod_handle system, const char *path, uint32_t mode,
                                   void *exinfo, mu_fmod_handle *sound);
    int32_t (*system_create_channel_group)(void *ctx, mu_fmod_handle system, const char *name,
                                           mu_fmod_handle *group);
    int32_t (*system_play_sound)(void *ctx, mu_fmod_handle system, int32_t index, mu_fmod_handle sound,
                                 int32_t paused, mu_fmod_handle *channel);                  /* 20 */
    int32_t (*system_get_master_channel_group)(void *ctx, mu_fmod_handle system, mu_fmod_handle *group);
    int32_t (*channel_set_paused)(void *ctx, mu_fmod_handle channel, int32_t paused);
    int32_t (*channel_set_priority)(void *ctx, mu_fmod_handle channel, int32_t priority);
    int32_t (*channel_set_channel_group)(void *ctx, mu_fmod_handle channel, mu_fmod_handle group);
    int32_t (*channel_set_mode)(void *ctx, mu_fmod_handle channel, uint32_t mode);           /* 25 */
    int32_t (*group_release)(void *ctx, mu_fmod_handle group);
    int32_t (*group_set_volume)(void *ctx, mu_fmod_handle group, float volume);
    int32_t (*group_get_volume)(void *ctx, mu_fmod_handle group, float *volume);
    int32_t (*group_set_paused)(void *ctx, mu_fmod_handle group, int32_t paused);
    int32_t (*group_get_paused)(void *ctx, mu_fmod_handle group, int32_t *paused);           /* 30 */
    int32_t (*group_set_mute)(void *ctx, mu_fmod_handle group, int32_t mute);
    int32_t (*group_get_mute)(void *ctx, mu_fmod_handle group, int32_t *mute);
    int32_t (*group_stop)(void *ctx, mu_fmod_handle group);
    int32_t (*group_add_group)(void *ctx, mu_fmod_handle group, mu_fmod_handle child);
} mu_fmod_api;

/* ---- settings (Data/Sound/Option.ini) ------------------------------------ */

/* Layout of the client's settings record (0x10ab480/0x10ab506). */
typedef struct mu_audio_settings {
    int32_t master_mute;
    float master_volume;
    int32_t group_mute[MU_AUDIO_GROUPS];
    float group_volume[MU_AUDIO_GROUPS];
} mu_audio_settings;

/* FMOD group defaults (unmuted, volume 1.0): what remains when Option.ini is
 * missing, because the client then applies nothing. */
void mu_audio_settings_fmod_default(mu_audio_settings *settings);
/* Option.ini as the client reads it: returns 1 and fills *out, or 0 when the
 * document does not parse (the client then keeps the current settings).
 * Missing members read as false/0.0 like jsoncpp null values. */
int mu_audio_options_parse(const char *text, size_t length, mu_audio_settings *out);
/* The bytes the client's writer produces (CRLF, tabs, "%#.16g" doubles with
 * trailing zeros trimmed to one). Returns the length, NUL-terminated. */
size_t mu_audio_options_format(const mu_audio_settings *settings, char *buffer, size_t size);

/* ---- sound system (FMOD wrapper object) --------------------------------- */

/* A loaded file. The client shares one per path (cache keyed case-insensitively
 * by _stricmp) and releases the FMOD sound with the last reference. */
typedef struct mu_audio_sound {
    char *path;
    mu_fmod_handle sound;
    int references;
} mu_audio_sound;

/* Sound-table entry created by SND_Load (std::map keyed by sound id). */
typedef struct mu_audio_entry {
    int32_t id;
    mu_audio_sound *sound;  /* NULL when FMOD failed to open the file */
    int32_t playing;        /* entry+0x0c: set by SND_Play, cleared at channel end */
    mu_fmod_handle channel; /* entry+0x10 */
} mu_audio_entry;

typedef struct mu_audio_client {
    mu_fmod_api api;
    mu_fmod_handle system;
    mu_fmod_handle master;
    mu_fmod_handle groups[MU_AUDIO_GROUPS];
    mu_audio_sound **cache;    /* std::map<std::string, weak_ptr> ordered by _stricmp */
    size_t cache_count, cache_capacity;
    mu_audio_entry **entries;  /* sorted by id */
    size_t entry_count, entry_capacity;
    mu_audio_entry **detached; /* removed entries a late channel callback may still touch */
    size_t detached_count, detached_capacity;
    mu_audio_sound *music;     /* global 0x06fc9fe0 */
    int32_t stricmp_mode;      /* 0: ASCII case fold (C locale, as observed) */
} mu_audio_client;

/* Names of the three channel groups as initialised at runtime (the strings
 * live in uncaptured .data; the names come from the adjacent literals). */
extern const char *const mu_audio_group_names[MU_AUDIO_GROUPS];

void mu_audio_client_init_state(mu_audio_client *client, const mu_fmod_api *api);
void mu_audio_client_free_state(mu_audio_client *client);
mu_audio_client *mu_audio_client_new(const mu_fmod_api *api);
void mu_audio_client_delete(mu_audio_client *client);

/* 0x010aad03 (System_Create happens at 0x010acc0e before it). Returns 1 on
 * success, 0 when any checked call fails (as the client does). */
int mu_audio_system_create(mu_audio_client *client);
int mu_audio_system_init(mu_audio_client *client, void *extra_driver_data);
void mu_audio_system_update(mu_audio_client *client);
void mu_audio_system_shutdown(mu_audio_client *client);

/* 0x010aaa97: open (kind 0/1 = sample via createSound, 2 = stream) or reuse. */
mu_audio_sound *mu_audio_create_sound(mu_audio_client *client, const char *path, int kind);
void mu_audio_sound_unref(mu_audio_client *client, mu_audio_sound *sound);
/* 0x010aaffb. Returns 1 when the channel is playing; *channel receives it. */
int mu_audio_play(mu_audio_client *client, mu_audio_sound *sound, int group, int loop,
                  mu_fmod_handle *channel);

void mu_audio_stop_group(mu_audio_client *client, int group);         /* 0x010ab15f */
void mu_audio_stop_master(mu_audio_client *client);                   /* 0x010ab13b */
void mu_audio_set_group_volume(mu_audio_client *client, int group, float volume); /* 0x010ab1be */
void mu_audio_set_group_mute(mu_audio_client *client, int group, int mute);       /* 0x010ab220 */
void mu_audio_set_master_volume(mu_audio_client *client, float volume);           /* 0x010ab18d */
void mu_audio_set_master_mute(mu_audio_client *client, int mute);                 /* 0x010ab1f7 */
float mu_audio_get_group_volume(mu_audio_client *client, int group);              /* 0x010ab2e3 */
int mu_audio_get_group_mute(mu_audio_client *client, int group);                  /* 0x010ab359 */
void mu_audio_apply_settings(mu_audio_client *client, const mu_audio_settings *settings);
void mu_audio_read_settings(mu_audio_client *client, mu_audio_settings *settings);

/* ---- sound table (SND_*) ------------------------------------------------- */

/* 0x00a6ab76. legacy_channels/legacy_3d are pushed by every caller and never
 * read by the routine. Returns 1 when the id is (already) registered. */
int mu_audio_snd_load(mu_audio_client *client, int32_t id, const char *path,
                      int32_t legacy_channels, int32_t legacy_3d);
/* 0x00a6ac96. The object argument is never read: playback is not positional. */
int mu_audio_snd_play(mu_audio_client *client, int32_t id, const void *object_ignored, int32_t loop);
void mu_audio_snd_stop(mu_audio_client *client, int32_t id);   /* 0x00a6ad76 */
void mu_audio_snd_remove(mu_audio_client *client, int32_t id); /* 0x00a6add6 */
const mu_audio_entry *mu_audio_snd_find(const mu_audio_client *client, int32_t id);
/* 0x00a6ae37, the FMOD channel callback registered on every SND_Play channel. */
int32_t mu_audio_channel_callback(mu_audio_client *client, mu_fmod_handle channel, int32_t type);
/* The callback pointer handed to FMOD (forwards to the client set with
 * mu_audio_set_callback_client). */
int32_t mu_audio_fmod_channel_callback(mu_fmod_handle channel, int32_t type, void *c1, void *c2);
void mu_audio_set_callback_client(mu_audio_client *client);

/* ---- music ---------------------------------------------------------------- */

void mu_audio_play_mp3(mu_audio_client *client, const char *path); /* 0x0120f602 */
void mu_audio_stop_mp3(mu_audio_client *client, const char *path); /* 0x0120f5a0 */
/* MSVC _stricmp in the C locale (0x0198c794 with __locale_changed == 0). */
int mu_audio_stricmp(const char *a, const char *b);

/* ---- options UI (0x00c7635f, 0x00f2fbdb, 0x00f2fcd8) ---------------------- */

/* Slider level 0..9 to group volume: (float)level / 9.0f. */
float mu_audio_level_to_volume(int32_t level);
/* Group volume to slider level: (int)(volume * 9.0f + 0.5f), truncating. */
int32_t mu_audio_volume_to_level(float volume);

/* ---- OpenWorld music-group volume (0x018290be..0x018293a6) --------------- */

/* 1 when OpenWorld sets the music group to 1.0 (the world is in the client's
 * 57-entry list), 0 when it sets 0.4. */
int mu_audio_world_full_music_volume(int32_t world);
float mu_audio_world_music_volume(int32_t world);
size_t mu_audio_full_volume_worlds(const int32_t **worlds);

/* ---- per-frame ambient and music selection (0x0185280c..0x01854498) ------ */

typedef struct mu_world_audio_state {
    int32_t scene;          /* 0x01d1df70; the block runs only for scene 6 */
    int32_t world;          /* 0x01cf15fc */
    int32_t hero_tile;      /* 0x0b437c10 */
    int32_t rain;           /* 0x0a3a9acc */
    int32_t hero_safe_zone; /* hero+0x04 (byte) */
    int32_t hero_x;         /* hero+0x180 */
    int32_t hero_y;         /* hero+0x184 */
    uint16_t hero_attribute;/* terrain attribute word at 0x0b795420[x + y*256] */
} mu_world_audio_state;

enum mu_world_audio_event_kind {
    MU_WORLD_SND_PLAY = 1,     /* a = id, b = loop */
    MU_WORLD_SND_STOP,         /* a = id */
    MU_WORLD_MP3_PLAY,         /* a = music table index */
    MU_WORLD_MP3_STOP,         /* a = music table index */
    MU_WORLD_DELEGATE,         /* a = client routine address, b = argument or -1 */
    MU_WORLD_UNRECOVERED       /* a = first address of the protector-virtualised gap */
};

/* Inputs the block obtains from other subsystems, supplied by the caller. */
typedef struct mu_world_audio_hooks {
    void *ctx;
    int32_t (*rand)(void *ctx);                                   /* CRT rand, world 3 */
    int32_t (*in_boss_zone)(void *ctx, int32_t world, int32_t x, int32_t y); /* world 0x7a */
    void (*event)(void *ctx, int kind, int32_t a, int32_t b);
} mu_world_audio_hooks;

/* Runs the block once. Segment A (0x0185280c..0x01854279) and segment B
 * (0x018542c2..0x01854498) are reconstructed; the 0x01854279..0x018542c2 gap
 * jumps into protector-virtualised code and is reported as one
 * MU_WORLD_UNRECOVERED event. */
void mu_world_audio_frame(const mu_world_audio_state *state, const mu_world_audio_hooks *hooks);

/* World predicates the block calls (0x009dad09, 0x016a887a, 0x016a88ae,
 * 0x00e18ae9, 0x00e1e4b6, 0x00e45d40). */
int mu_world_is_devil_square(int32_t world);
int mu_world_is_dungeon(int32_t world);
int mu_world_is_atlans(int32_t world);
int mu_world_is_karutan(int32_t world);
int mu_world_is_kubera(int32_t world);
int mu_world_is_scorched(int32_t world);

/* AUDIO-002: event inputs are supplied by their owning domains. Unknown fields
 * emit UNRECOVERED rather than choosing an event phase. */
enum { MU_AUDIO_CRYWOLF = 1, MU_AUDIO_KANTURU = 2,
       MU_AUDIO_TEMPLE = 4, MU_AUDIO_RAKLION = 8, MU_AUDIO_DOPPELGANGER = 16 };
typedef struct mu_event_music_state {
    int32_t world, crywolf, crywolf_result, kanturu, temple, raklion;
    uint32_t known;
    /* AUDIO-002F: dword +0x44 of the object at +0x78 of singleton 0x00f2bb92. */
    int32_t doppelganger;
} mu_event_music_state;
int mu_event_music(uint32_t manager, const mu_event_music_state *state,
                   const mu_world_audio_hooks *hooks);

/* Ordered registration at model open. preloaded means the opener exited before
 * loading anything. Each site resolves against the local audio TSV, not id order. */
void mu_audio_register_monster(int32_t type, int preloaded,
    void (*load)(void *, uint32_t, int32_t, int32_t, int32_t), void *ctx);
void mu_audio_register_npc(int32_t type, int preloaded,
    void (*load)(void *, uint32_t, int32_t, int32_t, int32_t), void *ctx);

int32_t mu_audio_npc_voice(int32_t model, int32_t random, uint16_t action,
                          float frame, int buff_1b);

#ifdef __cplusplus
}
#endif
#endif
