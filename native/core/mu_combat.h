/* Combat in the walk-around world (NATIVE-COMBAT-001, docs/research/client-combat.md).
 *
 * The client-side half of a fight, joined to the mu_walk session and the
 * demo-placed actors of mu_world_actors:
 *
 *   - the hero's attack (MoveHero's attack case 0x01697c17): a click on a
 *     monster selects it, the hero walks until the target is within the
 *     client's range (mu_hero_attack_range, the in-range test 0x016a52a6),
 *     faces it (CreateAngle), takes the SetPlayerAttack action
 *     (mu_player_attack_action) with the SetAttackSpeed PlaySpeed and starts
 *     AttackTime; skills take the action of the magic receive handlers;
 *   - the attack timeline of MoveCharacter: AttackTime counts to 15, and the
 *     end-of-attack switch creates the visuals (arrows for bow actions, the
 *     Fire Ball model, the Energy Ball and Heal bitmaps, ...);
 *   - the receive side: damage text through ShowDamage / CreatePoint
 *     (mu_show_damage) with the client colours and scales, MovePoints every
 *     step and RenderPoints / RenderNumber / RenderSpriteUV every frame;
 *     the monster hit reaction (mu_shock_action: action 5), death (the dead
 *     counter, SetPlayerDie -> action 6 from 15 on, the fade and sink of
 *     0x013a5ea1, removal) and the monster attack toward the hero (action
 *     packet 0x78: SetPlayerAttack's monster branch, AttackTime).
 *
 * DEMO, not client behaviour (there is no server): who hits, the damage
 * values, types and the miss chance, the hit-point pools, the latency of
 * the damage and death packets, the monsters' counter-attacks and their
 * timing, the respawn after removal, the skill ranges without the client's
 * skill table (NATIVE-LANG-001 supplies it from MU_LANG_DIR), auto-repeating the
 * attack while the target lives, and the picking of a monster under the
 * cursor (a cylinder around the actor, not the client's selection routine).
 * NATIVE-COMBAT-002: the skills' visuals run the client's older effect
 * system (reconstructed/combat/skill_fx: CreateEffect / MoveEffect for the
 * supported types, the particles and the joints they emit, the hit checks
 * that end a projectile at its target, the area skills' own end-of-attack
 * code) in three pools moved once per logic step; models draw through the
 * scene draw with the effect's blend mesh, particles as RenderSprite
 * billboards and joints as RenderJoints ribbons in their blend modes.
 * Viewer choices left: the animation player of effect models (frame +=
 * speed, looping), sprites (CreateSprite) and the effect kinds the
 * reconstruction does not cover are counted, not drawn. */
#ifndef MU_COMBAT_NATIVE_H
#define MU_COMBAT_NATIVE_H

#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

#include "../../reconstructed/combat/combat.h"
#include "../../reconstructed/combat/skill_fx.h"
#include "mu_bmd.h"
#include "mu_character.h"
#include "mu_image.h"
#include "mu_joints.h"
#include "mu_model.h"
#include "mu_scene.h"
#include "mu_textures.h"
#include "mu_walk.h"
#include "mu_world_actors.h"

enum {
    MU_COMBAT_WEAPON_NONE = 0,
    MU_COMBAT_WEAPON_SWORD,
    MU_COMBAT_WEAPON_TWO_HANDED,
    MU_COMBAT_WEAPON_SPEAR,
    MU_COMBAT_WEAPON_BOW,
    MU_COMBAT_WEAPON_CROSSBOW,
    MU_COMBAT_WEAPON_STAFF
};

/* Plays a client sound id through the sound table (SND_Play 0x00a6ac96). */
typedef void (*mu_combat_sound_fn)(void *context, int32_t id);

typedef struct mu_combat_config {
    int32_t weapon;           /* MU_COMBAT_WEAPON_* */
    float attack_speed;       /* character attribute +0x1b6 (demo value) */
    float magic_speed;        /* character attribute +0x1c2 (demo value) */
    uint32_t seed;            /* demo damage rolls */
    int32_t monster_hp;       /* demo hit points of every monster */
    int32_t damage_min, damage_max;   /* demo damage range */
    int32_t latency_steps;    /* demo server latency (damage after the attack starts) */
    int32_t respawn_steps;    /* demo respawn delay after removal */
    int32_t counter_attack;   /* 1: hit monsters attack the hero back (demo) */
    int32_t hero_hp;          /* demo hit points of the hero (0: the hero cannot die) */
    int32_t hero_respawn_steps; /* demo: steps from the death action to the respawn */
} mu_combat_config;

void mu_combat_default_config(mu_combat_config *config);

/* Bitmap slots the renderer binds by id. */
enum { MU_COMBAT_BITMAPS = 16 };

typedef struct mu_combat_bitmap {
    int32_t id;               /* client bitmap index (0x7534 font, 0x7df3.. specials, 0x7f2b, 0x7f84) */
    mu_image image;           /* client upload (power of two, rows in upload order) */
    int8_t components;
    int loaded;
} mu_combat_bitmap;

/* A model the effects draw (Data/Skill, the demo weapon for Twisting Slash). */
typedef struct mu_combat_model {
    int32_t type;             /* client model index (0x43b MODEL_ARROW, 0x413 MODEL_FIRE, ...) */
    int loaded;
    mu_bmd bmd;
    mu_model model;
    mu_textures textures;
} mu_combat_model;

enum {
    MU_COMBAT_MODEL_ARROW = 0, MU_COMBAT_MODEL_FIRE, MU_COMBAT_MODEL_CIRCLE, MU_COMBAT_MODEL_CIRCLE_LIGHT,
    MU_COMBAT_MODEL_INFERNO, MU_COMBAT_MODEL_LASER, MU_COMBAT_MODEL_STONE1, MU_COMBAT_MODEL_STONE2,
    MU_COMBAT_MODEL_WEAPON, MU_COMBAT_MODELS
};

#define MU_COMBAT_PARTICLES 2048
#define MU_COMBAT_LIGHTS 256
#define MU_COMBAT_EVENTS 64
#define MU_COMBAT_HERO_OBJECT MU_WORLD_ACTORS_MAX   /* object index of the hero in the effect environment */

/* One AddTerrainLight call of the last logic step (re-applied after the
 * frame light copy of every rendered frame). */
typedef struct mu_combat_light {
    float x, y, rgb[3];
    int32_t range;
} mu_combat_light;

/* A pending demo server message. */
typedef struct mu_combat_event {
    int32_t step;             /* due logic step */
    int32_t kind;             /* 1 damage to a monster, 2 damage to the hero */
    int32_t actor;
    int32_t damage, type;
    uint8_t flag8, flag_a;
} mu_combat_event;

typedef struct mu_combat_monster {
    int32_t hp;               /* demo */
    uint8_t dead;             /* c + 0x23 */
    uint8_t attack_time;      /* c + 0x21 */
    uint8_t counter;          /* c + 0x28 */
    float fade_timer;         /* c + 0x1a8 */
    float alpha;              /* o + 0xdc */
    uint8_t removed;
    int32_t respawn;          /* demo: steps until respawn */
    int32_t saved_wander;     /* wander radius while not fighting */
    int32_t aggro;            /* demo: attacks the hero */
    int32_t cooldown;         /* demo: steps until the next counter-attack */
    float home[3];
    float voice_3324;         /* c + 0x3324: SetPlayerDie's sound block marks it 0.001 (NATIVE-ITEMS-001) */
} mu_combat_monster;

typedef struct mu_combat_stats {
    uint32_t attacks, skills, arrows, fx_created, hits, misses, kills, removed, respawns;
    uint32_t points_created, monster_attacks, hero_hits, picks, pick_hits;
    uint32_t shocks, deaths;
    uint32_t particles_created, joints_created, projectile_hits, area_requests, unsupported, sprites;
    uint32_t hero_shocks, hero_deaths;
    uint32_t monster_voices;  /* NATIVE-ITEMS-001: monster hurt and death sounds played */
} mu_combat_stats;

struct mu_world_particles;

typedef struct mu_combat {
    mu_combat_config config;
    /* NATIVE-PARTICLE-001: when set, CreateSprite calls and the particle kinds skill_fx does not reconstruct go
     * to the legacy particle module (mu_particles.h), which draws them in its sprite pass. */
    struct mu_world_particles *legacy_particles;
    mu_walk *walk;
    mu_character *hero_character;
    mu_world_actors *actors;
    const mu_world *map;
    mu_point points[MU_POINTS];
    mu_combat_monster monsters[MU_WORLD_ACTORS_MAX];
    mu_sfx_effect effects[MU_SFX_EFFECTS];
    mu_sfx_particle particles[MU_COMBAT_PARTICLES];
    int32_t particle_count;
    mu_sfx_joint joints[MU_SFX_JOINTS];
    mu_sfx_object objects[MU_WORLD_ACTORS_MAX + 1];
    mu_sfx_env env;
    mu_jt_env jenv;            /* NATIVE-JOINT-001: the joint module's view of env (mu_joints.h) */
    uint32_t crt_seed;         /* the client's rand() recurrence for the effect randomness */
    uint8_t serial;            /* [[0x01d1df18] + 0x2dec] */
    mu_combat_light lights[MU_COMBAT_LIGHTS];
    int32_t light_count;
    float time_step;           /* [0x01cf103c] */
    mu_combat_event events[MU_COMBAT_EVENTS];
    int32_t event_count;
    /* hero */
    int32_t hero_key;          /* 0x06fca288 */
    int32_t target;            /* actor index or -1 */
    int32_t intent_skill;      /* -1 none, 0 normal attack, else the base skill */
    int32_t attack_target;     /* target of the running attack */
    int32_t attack_skill;      /* skill of the running attack */
    uint8_t hero_attack_time;  /* c + 0x21 */
    int32_t hero_hp;           /* demo */
    uint8_t hero_dead;         /* c + 0x23 */
    float hero_3324;           /* c + 0x3324: SetPlayerDie's voice runs once (0.001 after it) */
    int32_t hero_respawn;      /* demo: steps until the respawn, 0 none */
    int32_t hero_home[2];      /* demo: the respawn tile */
    mu_combat_sound_fn play_sound;   /* optional (mu-world sets it when sound is on) */
    void *sound_context;
    uint32_t sounds_played;
    int32_t last_sound;
    int32_t pending_target;    /* demo: the projectile attack whose damage waits for its hit check */
    int32_t pending_deadline;
    int32_t pending_damage, pending_type;
    uint8_t pending_flag8;
    uint8_t hero_counter;      /* c + 0x28 */
    int16_t weapon_item[2];    /* c + 0x19ac (client item indices of the demo weapon) */
    float speeds[MU_PLAYER_ACTIONS];   /* SetAttackSpeed result; < 0 for actions it does not store */
    int32_t step;
    uint32_t rng;
    mu_combat_bitmap bitmaps[MU_COMBAT_BITMAPS];
    int32_t bitmap_count;
    mu_combat_model models[MU_COMBAT_MODELS];
    mu_combat_stats stats;
    char log[32][96];
    int32_t log_count;
    const struct mu_lang *lang;   /* NATIVE-LANG-001: skill table (names, distance, mana), or NULL */
} mu_combat;

/* Binds the combat state to a session (all pointers stay owned by the
 * caller) and loads the bitmaps and models from game_root (missing files
 * are reported in the log and drawn as nothing). Returns 0 on success. */
int mu_combat_init(mu_combat *combat, const char *game_root, mu_walk *walk, mu_character *hero,
                   mu_world_actors *actors, const mu_combat_config *config, char *error, size_t error_size);
void mu_combat_free(mu_combat *combat);

/* Item model file of the demo weapon (Data/Item/...), NULL for fists. */
const char *mu_combat_weapon_file(int32_t weapon);

/* Logic step, part 1: run by mu_walk before MoveHero's walk and click code
 * (pre_step_hook). Consumes a left click that hits a monster and runs the
 * hero's attack decision. */
void mu_combat_pre_step(mu_combat *combat);
/* Logic step, part 2: after MoveCharacters (step_hook, after the actors'
 * step): attack timers, end-of-attack effects, the demo server's messages,
 * hit reactions, death, fade, removal and respawn, effect movement and
 * MovePoints. */
void mu_combat_step(mu_combat *combat);

/* Script and keyboard entry points: attack an actor, cast a skill at an
 * actor (actor -1: the current target), stop. */
void mu_combat_attack(mu_combat *combat, int32_t actor);
void mu_combat_cast(mu_combat *combat, int32_t skill, int32_t actor);
void mu_combat_stop(mu_combat *combat);
/* NATIVE-ITEMS-001: the monster under the mouse ray (the demo picking of
 * the click), -1 if none. The item selection runs when none is. */
int32_t mu_combat_pick(mu_combat *combat);

/* Actor index by label or number ("bull fighter", "3"), -1 if none. */
int32_t mu_combat_find_actor(const mu_combat *combat, const char *name);

/* Drawing. Alpha of an actor's body (1 normal); 0 when removed (not drawn). */
float mu_combat_actor_alpha(const mu_combat *combat, int32_t actor);

/* A textured quad of the frame: eye-space corners when eye_space (drawn with
 * an identity modelview, as RenderSpriteUV), world-space otherwise. */
typedef struct mu_combat_quad {
    float position[4][3];
    float texcoord[4][2];
    float color[4][4];
    int32_t bitmap;           /* index into combat->bitmaps, -1 untextured */
    uint8_t eye_space;
    uint8_t additive;         /* blend (ONE, ONE) instead of (SRC_ALPHA, ONE_MINUS_SRC_ALPHA) */
    uint8_t depth_test;
    uint32_t src, dst;        /* when non-zero: the GL blend factors (they override additive) */
} mu_combat_quad;

/* The frame's quads: joints (RenderJoints), particles (RenderParticles mode
 * 0 through RenderSprite), then RenderPoints (mode 0) through RenderNumber
 * and RenderSpriteUV with the session's camera modelview. Returns the
 * number of quads written. */
int32_t mu_combat_quads(mu_combat *combat, mu_combat_quad *quads, int32_t max);

/* Effect models: places and poses the model of every live model effect and
 * calls draw for it with the options RenderObject passes to RenderBody
 * (flags 2, or 0x82 for effects with +0x80 == 0x80; the effect's alpha,
 * blend mesh, its light and texture scroll). The callback must draw before
 * returning: the model instance is shared. Returns the number of models. */
typedef void (*mu_combat_model_fn)(void *context, const mu_model *model, const mu_textures *textures, int32_t slot,
                                   const mu_draw_options *options);
int32_t mu_combat_draw_models(mu_combat *combat, mu_combat_model_fn draw, void *context);

/* AddTerrainLight calls of the last logic step, applied to the world's frame
 * light after its per-frame copy (the client copies in its move phase and
 * the effects add during the same step). */
void mu_combat_terrain_lights(const mu_combat *combat, mu_world *map);

/* Software drawing of the frame's effect models and quads into a raster
 * whose view/projection are the session's (mu_raster textures are restored). */
struct mu_raster;
void mu_combat_draw_raster(mu_combat *combat, struct mu_raster *raster);

/* Scripted combat for headless runs and tests:
 *   "FRAME:attack:ACTOR FRAME:skill:N:ACTOR FRAME:click:ACTOR FRAME:stop ..."
 * ACTOR is a label or an actor index; click sends a mouse click on the
 * actor's screen position (through the picking), the others call the entry
 * points directly. */
#define MU_COMBAT_SCRIPT 32
typedef struct mu_combat_script_item {
    int32_t frame;
    char verb[8];
    int32_t skill;
    char actor[48];
} mu_combat_script_item;
typedef struct mu_combat_script {
    mu_combat_script_item items[MU_COMBAT_SCRIPT];
    int32_t count;
} mu_combat_script;
int mu_combat_script_parse(mu_combat_script *script, const char *text);

/* One JSON object per call (headless reports). */
void mu_combat_report_frame(const mu_combat *combat, FILE *out, int32_t frame);
void mu_combat_report_summary(const mu_combat *combat, FILE *out, int quiet);

/* Live points, effects, particles and joints (reports). */
int32_t mu_combat_live_points(const mu_combat *combat);
int32_t mu_combat_live_fx(const mu_combat *combat);
int32_t mu_combat_live_particles(const mu_combat *combat);
int32_t mu_combat_live_joints(const mu_combat *combat);

#endif
