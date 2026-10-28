/* WORLD-RT-001: the world runtime's internals, shared by world_rt.c, input.c, parts/<part>.c and world_tool.c only.
 *
 * struct mu_world_rt is world/main.c's file-static `app` without the command line's script state (world_tool.c)
 * and without the parts' GL handles (each part's own state).  Field names are main.c's, so the moved code reads
 * as it did.  The demo subsystems stay here as shared fields because they still point into each other (see
 * world_part.h); the options are copied into the fields world/main.c read them from. */
#ifndef MU_WORLD_RT_INTERNAL_H
#define MU_WORLD_RT_INTERNAL_H

#include <stddef.h>
#include <stdint.h>

#ifndef MU_WORLD_NO_GL
#ifdef __APPLE__
#include <OpenGL/gl.h>
#else
#include <GL/gl.h>
#endif
#endif

#include "../core/mu_character.h"
#include "../core/mu_combat.h"
#include "../core/mu_env.h"
#include "../core/mu_items.h"
#include "../core/mu_map.h"
#include "../core/mu_npc.h"
#include "../core/mu_objects.h"
#include "../core/mu_particles.h"
#include "../core/mu_progress.h"
#include "../core/mu_social.h"
#include "../core/mu_terrain.h"
#include "../core/mu_walk.h"
#include "../core/mu_world_actors.h"
#include "../core/mu_world_audio.h"
#include "../core/mu_world_helpers.h"
#include "../core/mu_world_names.h"
#include "../core/mu_world_players.h"
#ifndef MU_WORLD_NO_GL
#include "../viewer/gl_batch.h"
#include "world_gfx.h"
#include "world_gfx_map.h"
#include "world_gfx_social.h"
#include "world_names_gfx.h"
#endif
#include "mu_world_rt.h"
#include "world_part.h"

enum {
#define MU_PART(id, ...) MU_PART_##id,
#include "parts.def"
#undef MU_PART
    MU_PART_COUNT
};

struct mu_world_rt {
    uint8_t input_state[256], input_down[256];
    int input_composing, input_x, input_y, input_suspended;
    /* the world and the hero (world/main.c's options) */
    const char *root, *player;
    int32_t world, width, height, quiet;
    int32_t tile[2];
    float angle, near_plane;
    uint8_t class_byte;
    int32_t boots;                 /* NATIVE-PATH-002: hero boots level (run counter) */
    int has_auto;                  /* the tool's --auto-move: the summary's run row */
    mu_world *map;
    mu_camera_info info;
    mu_character ch;
    int has_character;
    mu_walk walk;
    /* stats */
    double walked;
    uint32_t moving_steps;
    /* NATIVE-WORLD-002 */
    const char *sound_table, *placement;
    int audio, legacy_box, audio_rate;
    mu_world_sound sound;
    int has_sound;
    size_t wav_frames;             /* the tool's headless WAV (the sound summary's wav_frames) */
    mu_world_actors actors;
    int has_actors;
    /* NATIVE-OBJECTS-001 */
    const char *objects_dir;
    mu_objects objects;
    int has_objects;
    long objects_drawn;
    const char *fidelity_dump;     /* NATIVE-FIDELITY-002 */
    mu_terrain_frustum frustum;
    mu_terrain_tile_stats tile_stats;
    /* NATIVE-ENV-001 */
    mu_world_env env;
    int has_env, no_env, env_tga;
    uint32_t env_seed;
    /* NATIVE-PARTICLE-001 */
    mu_world_particles particles;
    int has_particles, no_particles;
    uint32_t particle_seed;
    int32_t joint_demo;            /* NATIVE-JOINT-001: --joint-demo SUB (-1 off) */
    /* NATIVE-NAMES-001 */
    mu_world_names *names;
    int no_names, no_monster_info;
    const char *hero_name;
    /* NATIVE-PLAYERS-001 */
    mu_social_session *social;
    const char *players_file;
    int no_players;
    int32_t player_range;
    mu_world_players *players;
    /* NATIVE-HELPERS-001 */
    const char *helper_arg;
    int32_t helper_state;
    int no_helpers;
    mu_world_helpers *helpers;
    uint32_t effects_visible;
    /* NATIVE-COMBAT-001 */
    int combat_on;
    mu_combat_config combat_config;
    mu_combat *combat;
    /* NATIVE-ITEMS-001 */
    int items_on, no_items;
    mu_world_items_config items_config;
    mu_world_items *ground;
    /* NATIVE-NPC-001 */
    int npc_on;
    const char *npc_demo_path;
    mu_npc_demo *npc_demo;
    mu_npc *npc;
    /* NATIVE-SKILL-001 */
    uint32_t skill_casts, skill_refused;
    /* NATIVE-MAP-001 */
    int no_map;
    mu_map_session *mapsess;
    uint32_t travels, travel_failures;
    int32_t start_world;
    const char *start_placement, *start_npc_demo, *start_players;
    int start_set;
    const char *equip[MU_CHARACTER_ITEMS];   /* the embedding front end's equipment, applied again after a travel */
    int equip_combat, equip_set;
    /* NATIVE-PROGRESS-001 */
    int progress_on;
    mu_progress_config progress_config;
    mu_progress *progress;
#ifndef MU_WORLD_NO_GL
    int gl_ready;
    mu_gl_batch *batch;            /* NATIVE-PERF-001: terrain, objects and characters (NULL: MU_NO_GL_BATCH=1) */
    const mu_image *fx_images[64]; /* the effect textures (actor effects, the object fires' stand-in) */
    GLuint fx_names[64];
    int fx_count;
    /* NATIVE-GFX-002: the front end's GFx interface over the world and its views of the parts */
    world_gfx *gfx;
    world_names_gfx names_gfx;     /* NATIVE-NAMES-001: hudPlayerName through the layer */
    world_gfx_social *gfxsocial;
    world_gfx *gfxsocial_owner;
    world_gfx_map *gfxmap;
    world_gfx *gfxmap_owner;
    double gfx_scale;
#endif
    void *part[MU_PART_COUNT];     /* each part's own state (world_part.h state_size) */
};

/* RenderCharacter's part order (shared by the hero, players and player-model actors). */
extern const int mu_world_draw_order[MU_CHARACTER_ITEMS];

/* world_rt.c */
int world_rt_load(mu_world_rt *a);
void world_rt_unload(mu_world_rt *a);
int world_rt_travel(mu_world_rt *a, const mu_teleport *t);
int world_rt_apply_equipment(mu_world_rt *a, char *error, size_t error_size);
void world_rt_effect_camera(const mu_world_rt *a, float eye[3], float target[3]);
void world_rt_report_frame(const mu_world_rt *a, int32_t frame, uint32_t now, const char *hash, const char *png);
void world_rt_report_summary(const mu_world_rt *a, const char *renderer);
#ifndef MU_WORLD_NO_GL
void world_rt_names_gfx_attach(mu_world_rt *a, double scale);
void world_rt_gl_effect(void *context, const mu_fx_vertex *vertices, uint32_t count, const mu_fx_draw_state *state,
                        const mu_image *texture, const float *matrix);
#endif

/* parts/sound.c */
void world_rt_sound_frame(mu_world_rt *a);
void world_rt_env_sound(void *context, int32_t id);
void world_rt_characters_audio_drain(mu_world_rt *a);
mu_session *world_rt_characters_session(mu_world_rt *a);
struct mu_fixture *world_rt_characters_fixture(mu_world_rt *a);
void world_rt_ambient_sound(void *context, int32_t id);

/* parts/combat.c: the hero's respawn (the demo's 0xA0 sub 0x30 answer, also the travel script's "respawn") */
int world_rt_combat_respawned(void *context);

/* input.c: NATIVE-SKILL-001's cast of the skill bar's selection at a monster (MU_SKILL_CAST_*) */
#ifndef MU_WORLD_NO_GL
int world_rt_skill_cast_at(mu_world_rt *a, int32_t actor, int32_t *skill);
#endif

#endif
