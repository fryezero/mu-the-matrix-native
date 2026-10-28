/* Script-driven host for the native audio module: runs the reconstructed
 * client audio logic (reconstructed/audio) on the native engine (mu_audio)
 * in the client's fixed 40 ms frames, with the sound and music tables
 * extracted locally by scripts/extract_audio_tables.py.
 *
 * Script lines are "<milliseconds> <command> [arguments]":
 *   load <id> [path]          SND_Load (path from the table when omitted)
 *   play <id> [loop]          SND_Play; ids missing from the sound table entry
 *                             list are loaded from the table first
 *   stop <id> | remove <id>   SND_Stop / SND_Remove
 *   music <index|path>        PlayMp3 (index into the music table)
 *   stopmusic <index|path>    StopMp3
 *   volume <group> <value>    ChannelGroup::setVolume (master, music,
 *                             environment, effect)
 *   mute <group> <0|1>        ChannelGroup::setMute
 *   effectlevel <0..9>        options-window effect slider (level / 9)
 *   musicon <0|1>             options-window music check box (mutes music)
 *   openworld <world>         OpenWorld music-group volume (1.0 or 0.4)
 *   world <world> [tile=N safe=N x=N y=N rain=N attr=N boss=N]
 *                             per-frame ambient/music selection from now on
 *   noworld                   stop running the per-frame selection
 *   options <path>            load an Option.ini and apply it
 *   end                       end of the render
 */
#ifndef MU_AUDIO_HOST_H
#define MU_AUDIO_HOST_H

#include <stddef.h>
#include <stdint.h>

#include "mu_audio.h"
#include "../session/mu_cue.h"

#define MU_AUDIO_MUSIC_ENTRIES 76
#define MU_AUDIO_FRAME_MS 40

typedef struct mu_audio_table_row {
    int32_t id;
    char *path;
    int32_t legacy_channels, legacy_3d;  /* -1 when computed at the call site */
    uint32_t loader;
    uint32_t site; /* optional seventh TSV column, AUDIO-002 */
} mu_audio_table_row;

typedef struct mu_audio_table {
    mu_audio_table_row *rows;
    size_t count;
    char *music[MU_AUDIO_MUSIC_ENTRIES];
} mu_audio_table;

int mu_audio_table_load(const char *path, mu_audio_table *table, char *error, size_t error_size);
void mu_audio_table_free(mu_audio_table *table);
/* Path a startup loader registers for the id, else the first registration. */
const char *mu_audio_table_sound_path(const mu_audio_table *table, int32_t id);
const char *mu_audio_table_music_path(const mu_audio_table *table, int32_t index);

typedef struct mu_audio_host mu_audio_host;

typedef struct mu_audio_host_config {
    mu_audio_engine_config engine;
    const mu_audio_table *table;   /* may be NULL */
    const char *options_path;      /* Option.ini to apply after init (NULL: <root>/Data/Sound/Option.ini) */
    int skip_options;
} mu_audio_host_config;

mu_audio_host *mu_audio_host_new(const mu_audio_host_config *config, char *error, size_t error_size);
void mu_audio_host_free(mu_audio_host *host);
mu_audio_engine *mu_audio_host_engine(mu_audio_host *host);
mu_audio_client *mu_audio_host_client(mu_audio_host *host);

/* Applies one command (without the time field). Returns 0, 1 for "end", or
 * -1 with a message. */
int mu_audio_host_command(mu_audio_host *host, const char *command, char *error, size_t error_size);
/* SND_Play of a table id (loaded from the table first when needed), as the
 * client's game code calls it. Returns 1 when it started playing. */
int mu_audio_host_play(mu_audio_host *host, int32_t id, int32_t loop);
/* AUDIO-002: consume typed session cues once per reader, including headless runs.
 * The log is enabled by MU_AUDIO_CUE_LOG, JSONL v1; failures to open it fail init. */
int mu_audio_host_cue(mu_audio_host *host, const mu_cue *cue, uint32_t session_tick);
void mu_audio_host_cue_loss(mu_audio_host *host, uint32_t lost, uint32_t session_tick);
/* Scene music uses a pinned client string-literal address as its identifier
 * when the shell has no music table. No native pointer or filename is logged. */
void mu_audio_host_music_literal(mu_audio_host *host, const char *path, uint32_t literal, int play);
void mu_audio_host_set_event_music(mu_audio_host *host, const mu_event_music_state *state);
/* Explicit model-open registration in client order, with first-successful-load wins. */
int mu_audio_host_register_monster(mu_audio_host *host, int32_t type, int preloaded);
int mu_audio_host_register_npc(mu_audio_host *host, int32_t model, int preloaded);
/* Model cache survives viewport rebuilds for this audio host. monster_type < 0 selects OpenNpc. */
void mu_audio_host_register_actor(mu_audio_host *host, int32_t monster_type, int32_t model);
/* The per-frame world selection state from now on (the "world" command). */
void mu_audio_host_set_world(mu_audio_host *host, const mu_world_audio_state *state, int32_t boss_zone);
/* Observer of the per-frame block's events (mu_world_audio_event_kind). */
void mu_audio_host_set_observer(mu_audio_host *host, void (*observer)(void *ctx, int kind, int32_t a, int32_t b),
                                void *ctx);
/* One client frame: per-frame world selection (when active) then System::update. */
void mu_audio_host_tick(mu_audio_host *host);

typedef struct mu_audio_script_line {
    uint32_t time_ms;
    char *command;
    int line;
} mu_audio_script_line;

typedef struct mu_audio_script {
    mu_audio_script_line *lines;
    size_t count;
    uint32_t end_ms;  /* time of "end", or the last command plus two seconds */
} mu_audio_script;

int mu_audio_script_parse(const char *text, mu_audio_script *script, char *error, size_t error_size);
void mu_audio_script_free(mu_audio_script *script);

/* Runs the script frame by frame and hands each frame's stereo samples to
 * sink (frames = rate*40/1000). Returns 0 or -1 with a message. */
typedef int (*mu_audio_sink)(void *ctx, const float *stereo, uint32_t frames);
int mu_audio_host_run(mu_audio_host *host, const mu_audio_script *script, mu_audio_sink sink, void *sink_ctx,
                      char *error, size_t error_size);

#endif
