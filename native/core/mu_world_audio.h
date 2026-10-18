/* In-world sound for the walk-around session (NATIVE-WORLD-002).
 *
 * Runs the client's own audio decisions on the native engine (mu_audio,
 * mu_audio_host) at the points of the client loop where they happen:
 *
 *   - every logic step, after MoveHero and the character animation:
 *       HeroTile (0x0b437c10) = layer-1 tile under the hero (MoveHero tail
 *       0x016ad7a5), the foot-flag reset when the hero's animation step
 *       returned 0 (0x013a773c), and the footstep trigger (0x013b8090 in
 *       0x013b23f8) with PlayWalkSound 0x013b1f61 -> SND_Play(id);
 *   - every rendered frame, after the frame cap: the per-frame ambient and
 *     music block 0x0185280c..0x01854498 (Lorencia wind, the pub tile, the
 *     safe-zone music) and System::update;
 *   - at world entry: OpenWorld's music-group volume (0x018290be).
 *
 * The rules are reconstructed/audio (hero_sound.c verified by
 * scripts/validate_hero_sound.py, audio_world.c by scripts/validate_audio.py).
 * Sound ids and music indices resolve through the sound table that
 * scripts/extract_audio_tables.py extracts locally (not committed).
 * Session inputs that come from systems the native session does not have are
 * fixed and labelled: no rain (0x0a3a9acc = 0), the external character-state
 * predicate 0x0106b9f7(hero, 2, 1) false, no boss zone.
 */
#ifndef MU_WORLD_AUDIO_H
#define MU_WORLD_AUDIO_H

#include <stddef.h>
#include <stdint.h>

#include "../../reconstructed/audio/hero_sound.h"
#include "mu_audio.h"
#include "mu_audio_host.h"

/* Hero fields the step reads (client offsets in hero_sound.h). */
typedef struct mu_world_sound_hero {
    float position[2];        /* object +0x158 */
    int32_t tile[2];          /* character +0x180 / +0x184 */
    uint16_t action;          /* object +0x2a */
    float frame;              /* object +0xd0 after this step's tick */
    uint8_t step_result;      /* AL of this step's animation step (0 = wrapped) */
    uint8_t safe_zone;        /* character +4 */
    int32_t object_type;      /* object +0x5c (0xa91 for the Player model) */
} mu_world_sound_hero;

#define MU_WORLD_SOUND_LOG 32

typedef struct mu_world_sound {
    mu_audio_host *host;
    mu_audio_table table;
    int has_table;
    int32_t world;
    int32_t rain;             /* 0x0a3a9acc: 0 (no weather system) */
    uint8_t foot[2];          /* character +0xc / +0xd */
    int32_t field_168;        /* character +0x168 (written by the reset) */
    int32_t hero_tile;        /* 0x0b437c10 */
    /* statistics */
    uint32_t steps, frames, footsteps, footstep_ids[4], bridge_steps, resets;
    uint32_t ambient_plays, ambient_stops, music_plays, music_stops, delegates;
    int32_t last_music;       /* music table index of the last PlayMp3 event, -1 none */
    char log[MU_WORLD_SOUND_LOG][96];
    int32_t log_count;
} mu_world_sound;

/* Opens the engine (game_root for the files, table_path = the extracted TSV,
 * may be NULL: then nothing resolves and the session is silent), applies
 * Data/Sound/Option.ini and OpenWorld's music volume for `world`.
 * Returns 0, or 1 with a message. */
int mu_world_sound_open(mu_world_sound *sound, const char *game_root, const char *table_path, uint32_t rate,
                        int32_t world, char *error, size_t error_size);
void mu_world_sound_close(mu_world_sound *sound);

/* One logic step for the hero (after MoveHero and the animation step).
 * layer1 and attributes are the world's 256x256 grids. Returns the id
 * PlayWalkSound passed to SND_Play this step, or -1. */
int32_t mu_world_sound_hero_step(mu_world_sound *sound, const mu_world_sound_hero *hero, const uint8_t *layer1,
                                 const uint16_t *attributes);

/* One rendered frame after the cap: the per-frame block for the hero state,
 * then System::update. attribute is TerrainWall at the hero tile. */
void mu_world_sound_frame(mu_world_sound *sound, const mu_world_sound_hero *hero, uint16_t attribute);

/* Mixes interleaved stereo float frames. */
void mu_world_sound_mix(mu_world_sound *sound, float *out, uint32_t frames);
uint32_t mu_world_sound_rate(const mu_world_sound *sound);
int mu_world_sound_voices(const mu_world_sound *sound);

#endif
