#include "mu_muun_mount.h"
#include "mu_data.h"
#include "mu_objects.h"
#include "../../reconstructed/movement/client_movement.h"
#include <stdio.h>
#include <string.h>

/* Startup model loads 0x0183678c..0x0183694a and the model-name search in 0x009b9281.
 * SMD names are model header names, not the filenames of the installed BMD envelopes. */
static const char *const files[] = {
    "wolfpetVehicle", "wolfpetVehicle_evol", "rippen_ride", "rippenUp_ride",
    "pon_ride", "ponUp_ride", "griffs_ride", "griffsUp_ride"
};
void mu_muun_mount_close(mu_muun_mount *m)
{
    mu_textures_free(&m->textures);
    mu_model_free(&m->model);
    mu_bmd_free(&m->bmd);
    memset(m, 0, sizeof *m);
}
int mu_muun_mount_open(mu_muun_mount *m, const mu_muun_visual *base, const char *root,
                       char *error, size_t error_size)
{
    memset(m, 0, sizeof *m);
    char relative[256], path[2048], directory[2048];
    if (!base->live || base->slot_kind != 1 || !base->secondary_name[0]) goto fail;
    /* The startup lookup is by the BMD's model name. Never guess a filename from the record name. */
    for (int k = 0; k < 8; ++k) {
        snprintf(relative, sizeof relative, "Data/Skill/%s.bmd", files[k]);
        if (!mu_objects_resolve(root, relative, path, sizeof path)) continue;
        if (mu_bmd_load_file(path, &m->bmd, error, error_size) != MU_BMD_OK) goto fail;
        if (!strcmp(m->bmd.name, base->secondary_name)) { m->model_code = 0x5cb + k; break; }
        mu_bmd_free(&m->bmd);
    }
    if (!m->model_code || m->bmd.action_count < 5) goto fail;
    mu_model_params p;
    mu_model_scene_params(&p);
    p.body_scale = mu_mv_riding_scale(m->model_code);
    p.pose_translate = 0;
    p.transform_translate = 1;
    memcpy(p.origin, base->state.position, sizeof p.origin);
    if (mu_model_init(&m->model, &m->bmd, &p, error, error_size) != MU_MODEL_OK) goto fail;
    mu_path_directory(path, directory, sizeof directory);
    mu_textures_load(&m->textures, &m->bmd, directory);
    m->bone = -1;
    for (int k = 0; k < m->bmd.bone_count; ++k)
        if (!strcmp(m->bmd.bones[k].name, "Bip01 Spine1")) { m->bone = k; break; }
    if (m->bone < 0 || m->bmd.bones[m->bone].dummy || m->bmd.bones[m->bone].unresolved) ++m->refused_bones;
    m->owner_key = base->state.key;
    m->generation = base->generation;
    m->mapped_action = 0;
    m->loaded = 1;
    return 0;
fail:
    mu_muun_mount_close(m);
    snprintf(error, error_size, "Muun mount fixture: missing/invalid kind-1 secondary model");
    return 1;
}
static int lease(mu_muun_mount *m, const mu_muun_visual *base)
{
    if (!base->live || base->state.key != m->owner_key || base->generation != m->generation)
        m->retired = 1;
    return m->loaded && !m->retired;
}
void mu_muun_mount_step(mu_muun_mount *m, const mu_muun_visual *base, int32_t owner_action)
{
    if (!lease(m, base)) { m->visible = m->posed = m->attached = 0; return; }
    int32_t action = mu_mv_riding_action(owner_action);
    if (action >= 0) {
        if (action >= m->bmd.action_count || m->bmd.actions[action].keys <= 0) {
            ++m->refused_actions; m->visible = m->posed = m->attached = 0; return;
        }
        if (action != m->mapped_action) {
            uint16_t current = mu_model_action(&m->model), prior = mu_model_prior_action(&m->model);
            float frame = mu_model_frame(&m->model), prior_frame = mu_model_prior_frame(&m->model);
            mu_move_set_action(&current, &prior, &frame, &prior_frame, m->bmd.action_count, action);
            mu_model_set_state(&m->model, current, frame, prior_frame, prior);
            m->mapped_action = action;
        }
    }
    uint8_t loop = 0;
    mu_model_tick(&m->model, mu_mv_riding_speed(m->model_code, m->mapped_action), &loop);
}
void mu_muun_mount_frame(mu_muun_mount *m, const mu_muun_visual *base, const mu_mv_owner *owner,
                         int32_t selected_item, int hidden, int buff26, int predicate, int frustum)
{
    m->visible = m->posed = m->attached = 0;
    if (owner && (!owner->live || owner->key != m->owner_key)) m->retired = 1;
    if (!lease(m, base) || !mu_mv_riding_admit(owner != NULL, hidden, m->loaded,
        base->live, buff26, selected_item, base->info.item, predicate) || !frustum) return;
    mu_model_params p = m->model.params;
    p.body_scale = mu_mv_riding_scale(m->model_code);
    memcpy(p.origin, owner->position, sizeof p.origin);
    memcpy(p.angles, owner->angle, sizeof p.angles);
    mu_model_apply_params(&m->model, &p);
    /* Refuse an unavailable action instead of mu_model_pose's identity fallback. */
    int action = mu_model_action(&m->model), prior = mu_model_prior_action(&m->model);
    if (action >= m->bmd.action_count || prior >= m->bmd.action_count ||
        m->bmd.actions[action].keys <= 0 || m->bmd.actions[prior].keys <= 0) { ++m->refused_actions; return; }
    if (mu_model_pose(&m->model) != MU_MODEL_OK || !m->model.posed ||
        mu_model_transform_all(&m->model) != MU_MODEL_OK) return;
    m->visible = m->posed = 1;
    if (m->bone >= 0 && m->bone < m->bmd.bone_count && !m->bmd.bones[m->bone].dummy &&
        !m->bmd.bones[m->bone].unresolved) {
        mu_mv_riding_attachment(mu_model_bone_matrices(&m->model) + 12 * m->bone, p.body_scale, m->attachment);
        m->attachment[2] += 30.0f;
        m->attached = 1;
    }
}
void mu_muun_mount_draw(mu_muun_mount *m, float time, const mu_render_backend *backend, mu_draw_stats *stats)
{
    if (!m->visible || !m->posed) return;
    mu_draw_options o;
    mu_draw_default_options(&o);
    o.textures = &m->textures;
    o.time = time;
    mu_scene_draw_model(&m->model, &o, backend, stats);
    ++m->draws;
}
