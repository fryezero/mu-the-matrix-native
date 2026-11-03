/* Native audio engine (NATIVE-AUDIO-001).
 *
 * Implements the FMOD Ex boundary the client uses (mu_fmod_api from
 * reconstructed/audio/client_audio.h) with an offline-decoding software
 * mixer, so the reconstructed client logic runs unchanged on top of it:
 *
 *   - sounds: WAV through mu_wav, MP3/OGG through the platform decoder
 *     (AudioToolbox on macOS), decoded fully at open (streams included);
 *   - 16 voices (the client's System::init(16, ...)), playback starts paused
 *     and is released by Channel::setPaused(false) as the client does;
 *   - channel groups with volume and mute; a voice's gain is the product of
 *     its group and the master group, 0 when either is muted;
 *   - linear interpolation to the output rate; mono sources feed both output
 *     channels at full level;
 *   - PLAY-FIX-001: a peak limiter on the mixed output (mu_audio_limiter), so
 *     overlapping voices never reach full scale; it is the identity while the
 *     mix stays below its ceiling, so every voice keeps the client's group
 *     gain (level / 9 for effects, 0.4 or 1.0 for music);
 *   - end callbacks (natural end, Channel::stop, ChannelGroup::stop, voice
 *     stealing, Sound::release) are queued and delivered by System::update.
 *
 * The voice-stealing rule, pan law and error codes are this engine's choices:
 * the FMOD library is not part of the installation and was not analysed.
 */
#ifndef MU_AUDIO_H
#define MU_AUDIO_H

#include <stddef.h>
#include <stdint.h>

#include "../../reconstructed/audio/client_audio.h"
#include "mu_wav.h"

typedef struct mu_audio_engine mu_audio_engine;

typedef struct mu_audio_engine_config {
    uint32_t rate;                 /* output rate, default 44100 */
    const char *game_root;         /* client paths resolve below it (case-insensitive) */
    int32_t drivers;               /* getNumDrivers answer: 0 = default 1, negative = none */
    void *log_ctx;
    void (*log)(void *ctx, const char *message);
} mu_audio_engine_config;

enum {
    MU_AUDIO_ERR_FILE_NOTFOUND = 0x17,
    MU_AUDIO_ERR_FORMAT = 0x19,
    MU_AUDIO_ERR_CHANNEL_ALLOC = 0x0b,
    MU_AUDIO_ERR_INVALID_HANDLE = 0x24,
    MU_AUDIO_ERR_MEMORY = 0x2b,
    MU_AUDIO_VOICES = 16
};

/* PLAY-FIX-001: the output stage.  The client hands everything to FMOD Ex (no
 * gain of its own beyond the group volumes, docs/research/client-audio.md);
 * FMOD's own output stage is outside the pinned captures.  Native choice: a
 * linked-stereo peak limiter with instant attack and a 50 ms release to the
 * ceiling MU_AUDIO_CEILING (-0.3 dBFS).  While no frame exceeds the ceiling the
 * gain is exactly 1 and the samples pass unchanged (bit for bit), so a single
 * voice at any level stays at source x group gain; only a sum above the
 * ceiling is pulled down instead of clipping. */
#define MU_AUDIO_CEILING 0.9660509f
#define MU_AUDIO_RELEASE_MS 50.0
typedef struct mu_audio_limiter {
    float gain, release, ceiling;
    uint64_t limited_frames;       /* frames whose gain was below 1 */
} mu_audio_limiter;
void mu_audio_limiter_init(mu_audio_limiter *limiter, uint32_t rate);
void mu_audio_limiter_process(mu_audio_limiter *limiter, float *stereo, uint32_t frames);
/* Frames the engine's limiter has reduced so far. */
uint64_t mu_audio_engine_limited_frames(const mu_audio_engine *engine);

mu_audio_engine *mu_audio_engine_new(const mu_audio_engine_config *config);
void mu_audio_engine_free(mu_audio_engine *engine);
/* FMOD boundary bound to this engine (ctx = engine). */
const mu_fmod_api *mu_audio_engine_api(mu_audio_engine *engine);
/* Mixes `frames` stereo frames (interleaved float) and advances playback. */
void mu_audio_engine_mix(mu_audio_engine *engine, float *out, uint32_t frames);
uint32_t mu_audio_engine_rate(const mu_audio_engine *engine);
int mu_audio_engine_active_voices(const mu_audio_engine *engine);

/* Loads a client path (backslashes allowed) below the game root and decodes
 * it. Returns 0, or an MU_AUDIO_ERR_* code with a message. */
int mu_audio_load_file(const char *game_root, const char *client_path, mu_pcm *out, char *error, size_t error_size);
/* Resolves a client path to an existing host path (case-insensitive per
 * component). Returns 0 on success. */
int mu_audio_resolve_path(const char *game_root, const char *client_path, char *out, size_t out_size);

/* Platform decoder for compressed files (MP3, OGG Vorbis): float interleaved
 * at the file's own rate. Returns 0, or -1 with a message when unavailable. */
int mu_audio_decode_platform(const char *host_path, mu_pcm *out, char *error, size_t error_size);

#endif
