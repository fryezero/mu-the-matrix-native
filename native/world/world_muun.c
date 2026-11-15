/* MUUN-VISUAL-001: authored demo-owner adapter; no inventory, session selector or packet feed. */
#include "world_muun.h"
#include "world_rt_internal.h"
#include "../core/mu_muun_visual.h"
#include "../core/mu_muun_mount.h"
#include "../core/mu_frame_time.h"
#include "../../reconstructed/environment/env.h"
#include "../../reconstructed/movement/client_movement.h"
#include <errno.h>
#include <stdlib.h>
#include <string.h>
#ifndef MU_WORLD_NO_GL
#include "../viewer/gl_backend.h"
#endif

struct mu_world_muun {
    mu_muun_visual visual;
    int32_t command_category;
    int mount_fixture, rider_fixture, remote_fixture, remote, borrowed;
    float remote_elapsed;
    long transition_requests, transition_created, transition_refused, rider_draws, rider_refused, rider_restored;
    uint64_t prepared_frame;
    uint16_t rider_action, rider_prior, saved_action, saved_prior;
    float rider_frame, rider_prior_frame, saved_frame, saved_prior_frame;
    mu_character_params saved_params;
    mu_muun_mount mount;
#ifndef MU_WORLD_NO_GL
    mu_gl_backend gl, mount_gl;
#endif
};

static mu_mv_owner owner_of(const mu_world_rt *a)
{
    mu_mv_owner o = {.key = 77, .live = (uint8_t)(a->has_character != 0), .moving = a->walk.hero.movement};
    memcpy(o.position, a->walk.hero.position, sizeof o.position);
    memcpy(o.angle, a->walk.hero.angle, sizeof o.angle);
    return o;
}

int mu_world_muun_open(mu_world_rt *a, mu_world_muun **out)
{
    *out = NULL;
    const char *arg = getenv("MU_MUUN_FIXTURE");
    if (!arg || !*arg) return 0;
    char *end;
    errno = 0;
    long code = strtol(arg, &end, 10);
    if (errno || *end || code < 0 || code > INT32_MAX) {
        fprintf(stderr, "MU_MUUN_FIXTURE needs an authored MuunRenderInfo id\n"); return 1;
    }
    mu_world_muun *m = calloc(1, sizeof *m);
    if (!m) return 1;
    char error[512], fallback[2048];
    const char *lang = getenv("MU_LANG_DIR");
    if (getenv("MU_NATIVE_DATA_DIR")) {
        snprintf(fallback, sizeof fallback, "%s/lang", getenv("MU_NATIVE_DATA_DIR"));
        char table[2100];
        snprintf(table, sizeof table, "%s/muuneffects.tsv", fallback);
        FILE *file = fopen(table, "rb");
        if (file) { fclose(file); lang = fallback; }
    }
    mu_mv_owner owner = owner_of(a);
    if (mu_muun_visual_open(&m->visual, a->root, lang, (int32_t)code, &owner, 1, error, sizeof error)) {
        fprintf(stderr, "%s\n", error); free(m); return 1;
    }
    const char *command = getenv("MU_MUUN_COMMAND_FIXTURE");
    if (command && *command) {
        errno = 0;
        long category = strtol(command, &end, 10);
        if (errno || *end || category < 50 || category > 55) {
            fprintf(stderr, "MU_MUUN_COMMAND_FIXTURE needs an authored category 50..55\n");
            mu_world_muun_close(m); return 1;
        }
        m->command_category = (int32_t)category;
    }
    const char *mount = getenv("MU_MUUN_MOUNT_FIXTURE");
    if (mount && *mount) {
        if (strcmp(mount, "1") || mu_muun_mount_open(&m->mount, &m->visual, a->root, error, sizeof error)) {
            fprintf(stderr, "MU_MUUN_MOUNT_FIXTURE=1 requires a valid kind-1 appearance\n");
            mu_world_muun_close(m); return 1;
        }
        m->mount_fixture = 1;
    }
    const char *rider = getenv("MU_MUUN_RIDER_FIXTURE");
    const char *owner_kind = getenv("MU_MUUN_OWNER_KIND_FIXTURE");
    const char *buff18 = getenv("MU_MUUN_BUFF18_FIXTURE");
    const char *remote = getenv("MU_MUUN_REMOTE_FIXTURE");
    if ((rider && strcmp(rider, "1")) || (rider && !m->mount_fixture) ||
        (owner_kind && strcmp(owner_kind, "1") && strcmp(owner_kind, "2")) ||
        (buff18 && strcmp(buff18, "1")) || ((owner_kind || buff18) && !m->mount_fixture) ||
        (remote && strcmp(remote, "1"))) {
        fprintf(stderr, "Muun visual flags require an explicit compatible fixture\n");
        mu_world_muun_close(m); return 1;
    }
    m->rider_fixture = rider != NULL;
    m->remote_fixture = m->remote = remote != NULL;
    m->prepared_frame = UINT64_MAX;
    mu_muun_mount_style(&m->mount, owner_kind && !strcmp(owner_kind, "2") ? 2 : 1, buff18 != NULL);
    a->muun_fixture = m;
    m->visual.model.params.world = a->map->world;
    if (m->mount.loaded) m->mount.model.params.world = a->map->world;
    mu_effect_scene_set_world(&m->visual.scene, a->map);
    *out = m;
    return 0;
}

void mu_world_muun_close(mu_world_muun *m)
{
    if (!m) return;
    mu_muun_mount_close(&m->mount);
    mu_muun_visual_close(&m->visual);
    free(m);
}

void mu_world_muun_tick(mu_world_rt *a, mu_world_muun *m)
{
    if (!m) return;
    mu_mv_owner owner = owner_of(a);
    /* Fixed authored 100-step clock; same-owner command only, with an explicit demo target. */
    if (m->command_category && m->visual.steps % 100 == 0) {
        const float target[3] = {owner.position[0] + 200.0f, owner.position[1], owner.position[2]};
        mu_muun_visual_command(&m->visual, m->command_category, target);
    }
    mu_muun_visual_step(&m->visual, &owner, 1);
    if (m->remote_fixture && m->visual.live && mu_mv_transition_step(&m->remote, &m->remote_elapsed, 3.0f, 0.04f)) {
        float position[3];
        mu_mv_rider_position(m->visual.state.position, m->visual.info.offset, position);
        ++m->transition_requests;
        if (a->has_particles && mu_world_particles_effect(&a->particles, 0x47a, 0, position,
            m->visual.state.angle, m->visual.model.params.color, -1, 0.0f, NULL)) ++m->transition_created;
        else ++m->transition_refused;
    }
    if (m->rider_fixture) {
        /* Four explicit unarmed appearance inputs, independent of equipment or gameplay actions. */
        const int32_t how[] = {0, 1, 2, 6};
        mu_hp_owner fixture = {.weapon = {-1, -1}};
        mu_helpers helpers = {.owners = &fixture, .owner_count = 1};
        int32_t action = mu_hp_rider_action(&helpers, 0, how[(m->visual.steps / 25) % 4]);
        if (action < 0 || action >= a->ch.player_bmd.action_count || a->ch.player_bmd.actions[action].keys <= 0) {
            ++m->rider_refused; return;
        }
        mu_move_set_action(&m->rider_action, &m->rider_prior, &m->rider_frame, &m->rider_prior_frame,
            a->ch.player_bmd.action_count, action);
        /* Tick the authored animation through the existing model consumer, then restore the logical hero. */
        uint16_t saved_action = mu_model_action(&a->ch.player), saved_prior = mu_model_prior_action(&a->ch.player);
        float saved_frame = mu_model_frame(&a->ch.player), saved_prior_frame = mu_model_prior_frame(&a->ch.player);
        mu_character_set_state(&a->ch, m->rider_action, m->rider_frame, m->rider_prior_frame, m->rider_prior);
        uint8_t loop = 0;
        mu_character_tick(&a->ch, mu_character_action_speed(&a->ch, m->rider_action), &loop);
        m->rider_frame = mu_model_frame(&a->ch.player); m->rider_prior_frame = mu_model_prior_frame(&a->ch.player);
        m->rider_prior = mu_model_prior_action(&a->ch.player);
        mu_character_set_state(&a->ch, saved_action, saved_frame, saved_prior_frame, saved_prior);
        mu_muun_mount_step(&m->mount, &m->visual, m->rider_action);
        return;
    }
    /* Authored rider actions, independent of hero combat or authoritative mount state. */
    const int32_t actions[] = {1, 65, 248};
    mu_muun_mount_step(&m->mount, &m->visual, actions[(m->visual.steps / 25) % 3]);
}

static void frame(mu_world_rt *a, mu_world_muun *m)
{
    m->visual.particles = a->has_particles ? &a->particles : NULL;
    if (m->prepared_frame == a->rendered_frames) return;
    m->prepared_frame = a->rendered_frames;
    mu_muun_visual *v = &m->visual;
    const int frustum = a->legacy_box || mu_terrain_test_frustum_2d(a->frustum.x2d, a->frustum.y2d, 6,
        v->state.position[0] * 0.01f, v->state.position[1] * 0.01f, -20.0f);
    float light[3] = {0, 0, 0};
    mu_obj_terrain_light(a->map->light, 6, 1, v->state.position[0], v->state.position[1], light);
    mu_env_object object = {0};
    object.flag_05 = 1;
    object.light[0] = object.light[1] = object.light[2] = 1.0f;
    mu_env_body_light(&object, light, v->model.params.color, &v->model.params.lighting);
    v->model.params.light_ambient = MU_ENV_LIGHT_AMBIENT;
    v->model.params.light_scale = MU_ENV_LIGHT_SCALE;
    v->model.params.light_minimum = MU_ENV_LIGHT_MINIMUM;
    mu_mv_owner owner = owner_of(a);
    mu_muun_visual_frame(v, &owner, 1, frustum, mu_frame_time_value());
    const int mount_frustum = a->legacy_box || mu_terrain_test_frustum_2d(a->frustum.x2d, a->frustum.y2d, 6,
        owner.position[0] * 0.01f, owner.position[1] * 0.01f, -20.0f);
    if (m->mount.loaded) {
        float mount_light[3] = {0, 0, 0};
        mu_obj_terrain_light(a->map->light, 6, 1, owner.position[0], owner.position[1], mount_light);
        mu_env_body_light(&object, mount_light, m->mount.model.params.color, &m->mount.model.params.lighting);
        m->mount.model.params.light_ambient = MU_ENV_LIGHT_AMBIENT;
        m->mount.model.params.light_scale = MU_ENV_LIGHT_SCALE;
        m->mount.model.params.light_minimum = MU_ENV_LIGHT_MINIMUM;
    }
    mu_muun_mount_frame(&m->mount, v, &owner, m->mount_fixture ? v->info.item : -1, 0, 0, 0, mount_frustum);
}

/* Ordinary models use RenderBodyShadow(-1,-1,-1,-1,0). */
static void shadow(mu_world_rt *a, mu_world_muun *m, const mu_render_backend *backend)
{
    if (!a->has_particles || !m->visual.visible) return;
    float alpha = mu_mv_shadow_alpha(a->map->world, 0, 1, 1.0f, m->visual.shadow_alpha);
    if (alpha == 0.0f) return;
    const float rgba[4] = {0, 0, 0, alpha};
    mu_world_particles_shadow(&a->particles, &m->visual.model, &m->visual.bmd, rgba, backend);
}

void mu_world_muun_soft(mu_world_rt *a, mu_world_muun *m, mu_world_draw *draw)
{
    if (!m) return;
    frame(a, m);
    if (!m->visual.visible && !m->mount.visible) return;
    mu_raster *r = draw->raster;
    r->textures = m->visual.textures.slots; r->texture_count = m->visual.textures.count;
    r->texture_filter = m->visual.textures.filter; r->texture_wrap = m->visual.textures.wrap;
    mu_render_backend backend;
    mu_raster_backend(r, &backend);
    mu_draw_stats stats = {0};
    shadow(a, m, &backend);
    mu_muun_visual_draw(&m->visual, a->map->time, &backend, &stats);
    r->textures = m->mount.textures.slots; r->texture_count = m->mount.textures.count;
    r->texture_filter = m->mount.textures.filter; r->texture_wrap = m->mount.textures.wrap;
    mu_muun_mount_draw(&m->mount, a->map->time, &backend, &stats);
    mu_muun_mount_emit(&m->mount, a->has_particles ? &a->particles : NULL);
    r->textures = NULL; r->texture_count = 0; r->texture_filter = NULL; r->texture_wrap = NULL;
    float eye[3], at[3];
    world_rt_effect_camera(a, eye, at);
    const mu_client_view *v = &a->walk.frame.view;
    mu_effect_scene_render(&m->visual.scene, eye, at, v->fov, (float)r->width / (float)r->height,
        v->view_near, v->view_far * 1.4f, r);
}

#ifndef MU_WORLD_NO_GL
void mu_world_muun_gl_teardown(mu_world_muun *m)
{
    if (m && m->gl.textures) mu_gl_release(&m->gl);
    if (m && m->mount_gl.textures) mu_gl_release(&m->mount_gl);
}

void mu_world_muun_gl(mu_world_rt *a, mu_world_muun *m, mu_world_draw *draw)
{
    if (!m) return;
    frame(a, m);
    if (!m->visual.visible && !m->mount.visible) return;
    if (a->batch && !a->players) mu_gl_batch_session_end(a->batch);
    if (!m->gl.textures) mu_gl_upload(&m->gl, &m->visual.textures, 0);
    mu_render_backend backend;
    mu_gl_backend_bind(&m->gl, &backend);
    mu_draw_stats stats = {0};
    shadow(a, m, &backend);
    mu_muun_visual_draw(&m->visual, a->map->time, &backend, &stats);
    if (m->mount.visible) {
        if (!m->mount_gl.textures) mu_gl_upload(&m->mount_gl, &m->mount.textures, 0);
        mu_gl_backend_bind(&m->mount_gl, &backend);
        mu_muun_mount_draw(&m->mount, a->map->time, &backend, &stats);
        mu_muun_mount_emit(&m->mount, a->has_particles ? &a->particles : NULL);
    }
    float eye[3], at[3];
    world_rt_effect_camera(a, eye, at);
    const mu_client_view *v = &a->walk.frame.view;
    glEnable(GL_DEPTH_TEST);
    mu_effect_scene_render_to(&m->visual.scene, eye, at, v->fov, (float)draw->width / (float)draw->height,
        v->view_near, v->view_far * 1.4f, world_rt_gl_effect, a);
    glBindTexture(GL_TEXTURE_2D, 0); glDepthMask(GL_TRUE); glDisable(GL_BLEND); glDisable(GL_ALPHA_TEST);
    if (a->batch && !a->players) mu_gl_batch_session_begin(a->batch);
}
#endif

void mu_world_muun_report(const mu_world_muun *m, FILE *out)
{
    if (!m) return;
    const mu_muun_visual *v = &m->visual;
    if (m->remote_fixture) fprintf(out, "{\"muun_transition\":%ld,\"created\":%ld,\"refused\":%ld,\"pending\":%d}\n",
        m->transition_requests, m->transition_created, m->transition_refused, m->remote);
    if (m->rider_fixture) fprintf(out, "{\"muun_rider\":%u,\"draws\":%ld,\"refused\":%ld,\"restored\":%ld}\n",
        m->rider_action, m->rider_draws, m->rider_refused, m->rider_restored);
    if (m->mount_fixture) fprintf(out, "{\"muun_style\":%d,\"mode\":%d,\"alpha\":%.6f,\"particle_requests\":%ld,"
        "\"particle_created\":%ld,\"particle_refused\":%ld,\"particle_bones_refused\":%ld,\"refused_modes\":%ld}\n",
        m->mount.owner_kind, m->mount.render_mode, (double)m->mount.fade.alpha, m->mount.particle_requests,
        m->mount.particle_created, m->mount.particle_refused, m->mount.particle_bones_refused, m->mount.refused_modes);
    if (m->mount_fixture) fprintf(out, "{\"muun_mount\":%d,\"visible\":%d,\"action\":%u,"
        "\"attached\":%d,\"missing\":%d,\"refused_actions\":%ld,\"refused_bones\":%ld,\"draws\":%ld}\n",
        m->mount.model_code, m->mount.visible, mu_model_action(&m->mount.model), m->mount.attached,
        m->mount.textures.missing, m->mount.refused_actions, m->mount.refused_bones, m->mount.draws);
    fprintf(out, "{\"muun_bone_requests\":%ld,\"created\":%ld,\"refused\":%ld,\"invalid_points\":%ld}\n",
        v->bone_requests,v->bone_created,v->bone_refused,v->bone_points_refused);
    fprintf(out, "{\"muun_fixture\":%d,\"model\":%d,\"live\":%d,\"visible\":%d,\"state\":%d,"
        "\"position\":[%.3f,%.3f,%.3f],\"action\":%u,\"frame\":%.3f,\"textures_missing\":%d,"
        "\"mesh_passes\":%d,\"mesh_draws\":%ld,\"refused_meshes\":%ld,\"commands\":%ld,\"refused_commands\":%ld,\"attachments\":%d,\"invalid\":%ld,\"refused_bones\":%ld,\"updates\":%ld,\"vertices\":%u}\n",
        v->info.code, v->state.model, v->live, v->visible, v->state.state,
        (double)v->state.position[0], (double)v->state.position[1], (double)v->state.position[2],
        v->state.action, (double)v->state.frame, v->textures.missing, v->mesh_count, v->mesh_draws, v->refused_meshes, v->command_draws, v->refused_commands, v->effects.count, v->effects.invalid,
        v->refused_bones, v->effects.updates, v->scene.vertices_drawn);
}

void mu_world_muun_rider_begin(mu_world_rt *a)
{
    mu_world_muun *m = a->muun_fixture;
    if (!m || !m->rider_fixture || !a->has_character) return;
    frame(a, m);
    float position[3];
    if (!mu_muun_mount_rider_position(&m->mount, m->rider_action, a->walk.hero.position, position)) return;
    m->saved_params = a->ch.params;
    m->saved_action = mu_model_action(&a->ch.player); m->saved_prior = mu_model_prior_action(&a->ch.player);
    m->saved_frame = mu_model_frame(&a->ch.player); m->saved_prior_frame = mu_model_prior_frame(&a->ch.player);
    memcpy(a->ch.params.position, position, sizeof position);
    mu_character_set_state(&a->ch, m->rider_action, m->rider_frame, m->rider_prior_frame, m->rider_prior);
    if (mu_character_update(&a->ch) == MU_MODEL_OK) ++m->rider_draws;
    else ++m->rider_refused;
    m->borrowed = 1;
}
void mu_world_muun_rider_end(mu_world_rt *a)
{
    mu_world_muun *m = a->muun_fixture;
    if (!m || !m->borrowed) return;
    a->ch.params = m->saved_params;
    mu_character_set_state(&a->ch, m->saved_action, m->saved_frame, m->saved_prior_frame, m->saved_prior);
    mu_character_update(&a->ch);
    if (mu_model_action(&a->ch.player) == m->saved_action && mu_model_prior_action(&a->ch.player) == m->saved_prior &&
        mu_model_frame(&a->ch.player) == m->saved_frame && mu_model_prior_frame(&a->ch.player) == m->saved_prior_frame &&
        !memcmp(&a->ch.params, &m->saved_params, sizeof m->saved_params)) ++m->rider_restored;
    m->borrowed = 0;
}
