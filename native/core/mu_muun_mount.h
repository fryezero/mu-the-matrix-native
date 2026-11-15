#ifndef MU_MUUN_MOUNT_NATIVE_H
#define MU_MUUN_MOUNT_NATIVE_H
#include "mu_muun_visual.h"
#include "../../reconstructed/muun/riding.h"
#include "../../reconstructed/helpers/helpers.h"
#include "mu_particles.h"
#include "../../reconstructed/muun/secondary.h"
typedef struct mu_muun_mount {
    mu_bmd bmd;
    mu_model model;
    mu_textures textures;
    int32_t model_code, bone, mapped_action;
    int loaded, visible, posed, attached, retired;
    int32_t owner_key;
    uint32_t generation;
    float attachment[3];
    long draws, refused_actions, refused_bones, refused_modes;
    int32_t counter, render_mode;
    int owner_kind, buff18;
    int buff_hidden;
    long hidden_modes;
    mu_hp_object fade;
    long particle_requests, particle_created, particle_refused, particle_bones_refused;

} mu_muun_mount;
/* Loaded only on an explicit kind-1 mount fixture; shares the base slot's terminal lease. */
int mu_muun_mount_open(mu_muun_mount *m, const mu_muun_visual *base, const char *root,
                       char *error, size_t error_size);
void mu_muun_mount_close(mu_muun_mount *m);
void mu_muun_mount_step(mu_muun_mount *m, const mu_muun_visual *base, int32_t owner_action);
void mu_muun_mount_frame(mu_muun_mount *m, const mu_muun_visual *base, const mu_mv_owner *owner,
                         int32_t selected_item, int hidden, int buff26, int predicate, int frustum);
/* Visual-only authored flags. Fade uses the existing verified FadeAlpha consumer. */
void mu_muun_mount_style(mu_muun_mount *m, int owner_kind, int buff18);
void mu_muun_mount_emit(mu_muun_mount *m, mu_world_particles *particles);
/* Never falls back to an unposed/shared bone. Returns a render position only. */
int mu_muun_mount_rider_position(const mu_muun_mount *m, uint16_t action, const float position[3], float out[3]);
void mu_muun_mount_draw(mu_muun_mount *m, float time, const mu_render_backend *backend, mu_draw_stats *stats);
#endif
