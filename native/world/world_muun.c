/* MUUN-VISUAL-001: authored demo-owner adapter; no inventory, session selector or packet feed. */
#include "world_muun.h"
#include "world_rt_internal.h"
#include "../core/mu_muun_visual.h"
#include "../core/mu_frame_time.h"
#include "../../reconstructed/environment/env.h"
#include <errno.h>
#include <stdlib.h>
#include <string.h>
#ifndef MU_WORLD_NO_GL
#include "../viewer/gl_backend.h"
#endif

struct mu_world_muun {
    mu_muun_visual visual;
    int32_t command_category;
#ifndef MU_WORLD_NO_GL
    mu_gl_backend gl;
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
    m->visual.model.params.world = a->map->world;
    mu_effect_scene_set_world(&m->visual.scene, a->map);
    *out = m;
    return 0;
}

void mu_world_muun_close(mu_world_muun *m)
{
    if (!m) return;
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
}

static void frame(mu_world_rt *a, mu_world_muun *m)
{
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
}

/* Ordinary models use RenderBodyShadow(-1,-1,-1,-1,0). */
static void shadow(mu_world_rt *a, mu_world_muun *m, const mu_render_backend *backend)
{
    if (!a->has_particles) return;
    float alpha = mu_mv_shadow_alpha(a->map->world, 0, 1, 1.0f, m->visual.shadow_alpha);
    if (alpha == 0.0f) return;
    const float rgba[4] = {0, 0, 0, alpha};
    mu_world_particles_shadow(&a->particles, &m->visual.model, &m->visual.bmd, rgba, backend);
}

void mu_world_muun_soft(mu_world_rt *a, mu_world_muun *m, mu_world_draw *draw)
{
    if (!m) return;
    frame(a, m);
    if (!m->visual.visible) return;
    mu_raster *r = draw->raster;
    r->textures = m->visual.textures.slots; r->texture_count = m->visual.textures.count;
    r->texture_filter = m->visual.textures.filter; r->texture_wrap = m->visual.textures.wrap;
    mu_render_backend backend;
    mu_raster_backend(r, &backend);
    mu_draw_stats stats = {0};
    shadow(a, m, &backend);
    mu_muun_visual_draw(&m->visual, a->map->time, &backend, &stats);
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
}

void mu_world_muun_gl(mu_world_rt *a, mu_world_muun *m, mu_world_draw *draw)
{
    if (!m) return;
    frame(a, m);
    if (!m->visual.visible) return;
    if (a->batch && !a->players) mu_gl_batch_session_end(a->batch);
    if (!m->gl.textures) mu_gl_upload(&m->gl, &m->visual.textures, 0);
    mu_render_backend backend;
    mu_gl_backend_bind(&m->gl, &backend);
    mu_draw_stats stats = {0};
    shadow(a, m, &backend);
    mu_muun_visual_draw(&m->visual, a->map->time, &backend, &stats);
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
    fprintf(out, "{\"muun_fixture\":%d,\"model\":%d,\"live\":%d,\"visible\":%d,\"state\":%d,"
        "\"position\":[%.3f,%.3f,%.3f],\"action\":%u,\"frame\":%.3f,\"textures_missing\":%d,"
        "\"mesh_passes\":%d,\"mesh_draws\":%ld,\"refused_meshes\":%ld,\"commands\":%ld,\"refused_commands\":%ld,\"attachments\":%d,\"invalid\":%ld,\"refused_bones\":%ld,\"updates\":%ld,\"vertices\":%u}\n",
        v->info.code, v->state.model, v->live, v->visible, v->state.state,
        (double)v->state.position[0], (double)v->state.position[1], (double)v->state.position[2],
        v->state.action, (double)v->state.frame, v->textures.missing, v->mesh_count, v->mesh_draws, v->refused_meshes, v->command_draws, v->refused_commands, v->effects.count, v->effects.invalid,
        v->refused_bones, v->effects.updates, v->scene.vertices_drawn);
}
