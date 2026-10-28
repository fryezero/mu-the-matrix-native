/* Internal helpers of the environment module (NATIVE-ENV-001). */
#ifndef MU_ENV_INTERNAL_H
#define MU_ENV_INTERNAL_H

#include <stdint.h>

#include "env.h"

/* Negative controls of scripts/validate_environment.py (0 = the reconstruction). */
#ifndef MU_ENV_MUTATION
#define MU_ENV_MUTATION 0
#endif

void mu_env_raklion_snow(mu_env *, const mu_env_inputs *, mu_env_leaf *);
float env_sin(float x);
float env_cos(float x);
float env_sqrt(float x);
float env_atan(float x);
float env_fabs(float x);
int32_t env_tile_index(int32_t x, int32_t y);
float env_terrain(mu_env *env, float x, float y);
void env_sound(mu_env *env, int32_t id, const mu_env_object *o, int32_t loop);
void env_set_action(mu_env *env, mu_env_object *o, int32_t action);
void env_set_live(mu_env *env, mu_env_object *o, uint8_t live);
void env_fade_alpha(mu_env_object *o);
void env_flock(mu_env *env, mu_env_object *o, int32_t index, mu_env_object *list, int32_t count);

/* World predicates, all leaf routines of the client (address in the comment). */
static inline int env_blood_castle(int32_t w) { return (w >= 11 && w <= 17) || w == 52; }  /* 0x009dacec */
static inline int env_chaos_castle(int32_t w) { return (w >= 18 && w <= 23) || w == 53 || w == 97; }  /* 0x009dacb8 */
static inline int env_kalima(int32_t w) { return (w >= 24 && w <= 29) || w == 36; }  /* 0x009b0418 */
static inline int env_devil_square(int32_t w) { return w == 9 || w == 0x66; }  /* 0x009dad09 */
static inline int env_deep_dungeon(int32_t w) { return w >= 0x74 && w <= 0x78; }  /* 0x016a887a */
static inline int env_abyss(int32_t w) { return w >= 0x80 && w <= 0x82; }  /* 0x016a8325 */
static inline int env_atlans(int32_t w) { return w == 7 || env_abyss(w); }  /* 0x016a88ae */
static inline int env_water_world(int32_t w) { return env_atlans(w) || env_kalima(w); }  /* 0x016a88d3 */
static inline int env_tormenta(int32_t w) { return w == 0x8d; }  /* 0x00e54061 */

/* The guard lists of the tick and of the render scene name these leaf predicates. */
static inline int env_event_leaf_world(int32_t w)
{
    return (w >= 0x39 && w <= 0x3a) || w == 0x3e || w == 0x3f || (w >= 0x52 && w <= 0x5a) || w == 0x45 ||
           w == 0x46 || w == 0x47 || (w >= 0x48 && w <= 0x4a) || w == 0x4f;
}

#endif
