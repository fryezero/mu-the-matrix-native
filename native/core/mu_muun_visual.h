#ifndef MU_MUUN_VISUAL_NATIVE_H
#define MU_MUUN_VISUAL_NATIVE_H
#include "../../reconstructed/muun/visual.h"
#include "mu_model.h"
#include "mu_scene.h"
#include "../../reconstructed/muun/passes.h"
#include "mu_textures.h"
#include "mu_muun_effects.h"
#include "mu_effect_scene.h"

typedef struct mu_muun_visual {
    mu_mv_info info;
    uint8_t slot_kind;
    char secondary_name[257];
    mu_mv_state state;
    uint8_t *mesh_records;
    int32_t *mesh_textures;
    int32_t mesh_count;
    int base_body;
    float shadow_alpha;
    long mesh_draws, refused_meshes, command_draws, refused_commands;
    mu_bmd bmd;
    mu_model model;
    mu_textures textures;
    mu_muun_effects *table;
    mu_effect_scene scene;
    mu_muun_owner effects;
    uint32_t generation, rng;
    int loaded, live, visible, posed;
    long refused_bones, refused_pose, steps;
} mu_muun_visual;

/* An authored appearance id, never an inventory/packet selector. owner generation is a native fixture lease. */
int mu_muun_visual_open(mu_muun_visual *v, const char *root, const char *lang, int32_t code,
                        const mu_mv_owner *owner, uint32_t generation, char *error, size_t error_size);
void mu_muun_visual_close(mu_muun_visual *v);
/* Retires on owner death/key/generation change. Retirement is terminal; an explicit new fixture open is needed. */
void mu_muun_visual_step(mu_muun_visual *v, const mu_mv_owner *owner, uint32_t generation);
/* Pose and effect update happen at render, as in 0x009a9ae2. frustum is supplied by the scene. */
void mu_muun_visual_frame(mu_muun_visual *v, const mu_mv_owner *owner, uint32_t generation, int frustum, float dt);
/* The authored command category is explicit; no command, target or inventory feed is consulted. */
int mu_muun_visual_command(mu_muun_visual *v, int32_t category, const float target[3]);
void mu_muun_visual_draw(mu_muun_visual *v, float time, const mu_render_backend *backend, mu_draw_stats *stats);
/* Safety at the native boundary, before the original's unchecked shared-pose fallback. */
int mu_muun_visual_bone_available(int32_t bone, int32_t count, int posed);
#endif
