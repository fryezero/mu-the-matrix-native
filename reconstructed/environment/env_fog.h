#ifndef MU_ENV_FOG_H
#define MU_ENV_FOG_H

#include <stdint.h>

/* The render scene's fog (RENDER-WORLDS-FOG, docs/research/client-worlds-fog.md).
 *
 * RenderMainScene 0x01859419 tests world 0x1e (Data/World31) and the hero's position (Hero 0x0a39d754 + 0x33ac,
 * the OBJECT's Position) once before the scene (0x018596b4..0x01859797) and once after it (0x01859bfa..0x01859cb3).
 * Inside the box x 16100..19000, y 18900..21700 (both ends included; a NaN coordinate is outside) it calls StartFog
 * 0x00d8cca8 before the perspective setup 0x01849f08 and EndFog 0x00d8cd12 after the combat effects 0x0169159e,
 * before the screen haze 0x00def268. Everything between, terrain, objects, characters, items, particles and
 * effects, is drawn with the fixed-function fog on. */

enum {
    MU_ENV_FOG_KEEP = 0,   /* world != 0x1e: no GL call (0x018596d6 jumps past both branches) */
    MU_ENV_FOG_OFF = 1,    /* world 0x1e outside the box: glDisable(GL_FOG) 0x0185978b */
    MU_ENV_FOG_ON = 2      /* world 0x1e inside the box: StartFog 0x00d8cca8 */
};

/* StartFog's GL calls, in order: glEnable(GL_FOG 0x0b60); glFogfv(GL_FOG_COLOR 0x0b66, color);
 * glFogf(GL_FOG_MODE 0x0b65, 9729.0f = GL_LINEAR, 0x01aa6ac0); glFogf(GL_FOG_START 0x0b63, 2000.0f, 0x01a802d8);
 * glFogf(GL_FOG_END 0x0b64, 2700.0f, 0x01aa6aa8). No GL_FOG_DENSITY (linear fog does not read it). */
typedef struct mu_env_fog {
    float color[4];   /* the caller's three zeroed floats [ebp-0x74..-0x6c]; GL reads a fourth float, the caller's
                         stale [ebp-0x68], which only the fog colour's alpha takes (fog leaves alpha unchanged) */
    float mode;       /* 9729.0f, passed as a float */
    float start, end; /* 2000.0f, 2700.0f */
} mu_env_fog;

/* The test before the scene. Fills fog only for MU_ENV_FOG_ON. hero = the hero OBJECT's Position. */
int mu_env_scene_fog_begin(int32_t world, const float hero[3], mu_env_fog *fog);
/* The test after the scene: 1 when it calls EndFog 0x00d8cd12 (glDisable(GL_FOG)), 0 for no call. */
int mu_env_scene_fog_end(int32_t world, const float hero[3]);

#endif
