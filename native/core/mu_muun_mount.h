#ifndef MU_MUUN_MOUNT_NATIVE_H
#define MU_MUUN_MOUNT_NATIVE_H
#include "mu_muun_visual.h"
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
    long draws, refused_actions, refused_bones;
} mu_muun_mount;
/* Loaded only on an explicit kind-1 mount fixture; shares the base slot's terminal lease. */
int mu_muun_mount_open(mu_muun_mount *m, const mu_muun_visual *base, const char *root,
                       char *error, size_t error_size);
void mu_muun_mount_close(mu_muun_mount *m);
void mu_muun_mount_step(mu_muun_mount *m, const mu_muun_visual *base, int32_t owner_action);
void mu_muun_mount_frame(mu_muun_mount *m, const mu_muun_visual *base, const mu_mv_owner *owner,
                         int32_t selected_item, int hidden, int buff26, int predicate, int frustum);
void mu_muun_mount_draw(mu_muun_mount *m, float time, const mu_render_backend *backend, mu_draw_stats *stats);
#endif
