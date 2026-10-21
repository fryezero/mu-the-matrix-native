/* Native login scene (NATIVE-LOGIN-001). See mu_login.h and docs/research/client-login-scene.md. */
#include "mu_login.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "mu_effect.h"
#include "mu_scene.h"

static const uint8_t black[4] = {0, 0, 0, 255};

static void camera_setup(mu_login_session *s, uint32_t width, uint32_t height, float near_plane)
{
    mu_frame_world *f = s->frame;
    mu_frame_world_init(f, width, height, 128, 128);
    memcpy(f->heights, s->map->height, sizeof f->heights);
    memcpy(f->walls, s->map->attributes, sizeof f->walls);
    f->terrain.water_height = s->map->water_height;
    mu_world_camera *c = &f->camera;
    c->scene = MU_LOGIN_SCENE;
    c->world = MU_LOGIN_WORLD_INDEX;
    c->world_fov = s->info.fov;            /* scenes other than 6 take the world FOV (0x01851a7f) */
    c->far_scale[0] = s->info.distance;
    c->far_scale[1] = s->info.z_distance;
    c->far_scale[2] = 1.0f;                /* the record manager's +0x10 (live: 1.0) */
    memcpy(c->scene_angle, s->info.angle, sizeof c->scene_angle);
    memcpy(c->scene_position, s->info.position, sizeof c->scene_position);
    f->view.fov = s->info.fov;
    f->view.view_near = near_plane;
    mu_world_camera_enter(c, &f->view);
}

static void frustum(mu_login_session *s)
{
    const mu_client_view *v = &s->frame->view;
    float rows[12];
    for (int r = 0; r < 3; ++r)
        for (int c = 0; c < 4; ++c)
            rows[r * 4 + c] = v->modelview[r + 4 * c];
    /* CreateFrustrum(width / 640, record position, 0); the box test runs on the 640-wide virtual screen */
    mu_world_client_frustum(s->map, rows, v->position, s->info.position, v->angle[0], 640, 0, v->view_far, v->fov,
                            &s->frustum);
}

int mu_login_init(mu_login_session *s, const char *root, const char *objects_dir, uint32_t width, uint32_t height,
                  float near_plane)
{
    memset(s, 0, sizeof *s);
    char error[512];
    s->frame = calloc(1, sizeof *s->frame);
    if (!s->frame) {
        snprintf(s->error, sizeof s->error, "out of memory");
        return 1;
    }
    s->map = mu_world_load(root, MU_LOGIN_WORLD_INDEX, 1, 1, error, sizeof error);
    if (!s->map) {
        snprintf(s->error, sizeof s->error, "world 0x5e: %s", error);
        return 1;
    }
    if (mu_camera_info_load(root, s->map->report.folder, &s->info, error, sizeof error)) {
        snprintf(s->error, sizeof s->error, "camera record: %s", error);
        return 1;
    }
    camera_setup(s, width, height, near_plane);
    mu_objects_init(&s->objects, MU_LOGIN_WORLD_INDEX);
    if (objects_dir) {
        if (mu_objects_load_dir(&s->objects, objects_dir, error, sizeof error) == MU_OBJECTS_FILE_OK) {
            mu_objects_load_models(&s->objects, root, 0);
            if (!mu_objects_start(&s->objects, root))   /* CreateObject per record, CGMLogInScene_Ex slot 0x2c */
                s->has_objects = 1;
        } else {
            fprintf(stderr, "login objects: %s (terrain only)\n", error);
        }
    }
    /* NATIVE-JOINT-001: CreateSprite / CreateParticle through the reconstructed particle module */
    if (!mu_world_particles_open(&s->particles, root, s->map, MU_LOGIN_WORLD_INDEX, 1, 0, error, sizeof error)) {
        s->has_particles = 1;
        mu_world_particles_attach(&s->particles, s->has_objects ? &s->objects : NULL, NULL);
    }
    /* the first render's frustum (the frame-light copy of the first step uses it) */
    mu_move_main_camera(&s->frame->camera, &s->frame->view, 0);
    mu_view_begin_opengl(&s->frame->view, 0, 0, 640, 480);
    frustum(s);
    s->draw_3d = 1;
    return 0;
}

void mu_login_free(mu_login_session *s)
{
    if (s->has_particles)
        mu_world_particles_close(&s->particles);
    if (s->has_objects || s->objects.records)
        mu_objects_free(&s->objects);
    if (s->map)
        mu_world_free(s->map);
    free(s->frame);
    memset(s, 0, sizeof *s);
}

void mu_login_resize(mu_login_session *s, uint32_t width, uint32_t height)
{
    mu_frame_world *f = s->frame;
    f->view.window_width = width;
    f->view.window_height = height;
    f->mouse.scale_x = (float)width / 640.0f;   /* NATIVE-PERF-001: as mu_frame_world_init */
    f->mouse.scale_y = (float)height / 480.0f;
}

void mu_login_step(mu_login_session *s, uint32_t now)
{
    /* 0x016ca4fa: the frame light = the primary light over the last frustum box grown by 3 tiles */
    const mu_terrain_frustum *fr = &s->frustum;
    int32_t x0 = fr->x_min, y0 = fr->y_min, x1 = fr->x_max + 3, y1 = fr->y_max + 3;
    mu_world_frame_box(s->map, (float)now, x0 < 0 ? 0 : x0, y0 < 0 ? 0 : y0, x1 > 255 ? 255 : x1,
                       y1 > 255 ? 255 : y1);
    if (s->has_objects) {
        mu_objects_set_clock(&s->objects, now);
        mu_objects_step_inputs in = {MU_LOGIN_SCENE, 0, s->map->time, {0.0f, 0.0f, 0.0f}, fr->x2d, fr->y2d};
        mu_objects_step(&s->objects, &in);   /* MoveObjects 0x016d82c7 with CGMLogInScene_Ex slot 0x30 */
        mu_objects_apply_lights(&s->objects, s->map);
    }
    if (s->has_particles)   /* MoveEffects, MoveJoints, MoveParticles of the tick head (NATIVE-JOINT-001) */
        mu_world_particles_step(&s->particles, s->map->time);
    ++s->steps;
}

int32_t mu_login_update(mu_login_session *s, uint32_t now)
{
    int32_t steps = 0;
    mu_frame_world *f = s->frame;
    f->now = now;
    mu_frame_begin(&f->clock);
    while (mu_frame_logic_step(&f->clock)) {
        mu_login_step(s, now);
        ++steps;
    }
    return steps;
}

void mu_login_begin_render(mu_login_session *s, uint32_t now, int draw_3d)
{
    mu_frame_world *f = s->frame;
    f->now = now;
    mu_frame_render_start(&f->clock, now);
    f->camera.hero_tile_wall = 0;
    mu_move_main_camera(&f->camera, &f->view, now);   /* scene-3 record path */
    mu_view_begin_opengl(&f->view, 0, 0, 640, 480);
    frustum(s);
    s->view_far = f->view.view_far;
    s->draw_3d = draw_3d;
    if (s->has_objects)
        mu_objects_set_clock(&s->objects, now);
    ++s->frames;
}

void mu_login_frame(mu_login_session *s, uint32_t now)
{
    mu_login_begin_render(s, now, 1);
    if (!s->has_objects)
        return;
    mu_objects *o = &s->objects;
    const uint64_t sprites = s->particles.stats.sprites_created;
    mu_objects_visibility(o, &s->frustum, MU_LOGIN_SCENE);
    for (int32_t k = 0; k < o->rt.draw_count; ++k) {
        mu_draw_options options;
        mu_objects_prepare(o, k, s->map, MU_LOGIN_SCENE, &options);
    }
    mu_objects_after_visibility(o, &s->frustum, MU_LOGIN_SCENE);
    if (s->has_particles) {
        s->frame_sprites = (int32_t)(s->particles.stats.sprites_created - sprites);
        mu_world_particles_discard_sprites(&s->particles);   /* a frame without drawing: RenderSprites' kill */
    }
}

void mu_login_eye(const mu_login_session *s, float eye[3], float target[3])
{
    const mu_client_view *v = &s->frame->view;
    for (int k = 0; k < 3; ++k) {
        eye[k] = v->position[k];
        target[k] = v->position[k] - v->modelview[4 * k + 2] * 1000.0f;
    }
}

long mu_login_draw_soft(mu_login_session *s, mu_raster *raster)
{
    const mu_client_view *v = &s->frame->view;
    memcpy(raster->view, v->modelview, sizeof raster->view);
    memcpy(raster->projection, v->projection, sizeof raster->projection);
    mu_raster_clear(raster, black);
    if (!s->draw_3d)
        return 0;
    mu_world_draw_stats stats;
    memset(&stats, 0, sizeof stats);
    mu_world_draw_raster_view(s->map, raster, &s->frustum, MU_LOGIN_SCENE, 0, &stats);   /* RenderTerrain(0) */
    s->objects_drawn = s->after_meshes = s->billboards = 0;
    if (!s->has_objects)
        return stats.tiles.faces;
    mu_objects *o = &s->objects;
    mu_render_backend backend;
    mu_raster_backend(raster, &backend);
    const int linear = raster->linear;
    raster->linear = 1;
    const uint64_t sprites = s->particles.stats.sprites_created;
    /* RenderObjects 0x016d5020 */
    mu_objects_visibility(o, &s->frustum, MU_LOGIN_SCENE);
    for (int32_t k = 0; k < o->rt.draw_count; ++k) {
        mu_draw_options options;
        mu_object_model *m = mu_objects_prepare(o, k, s->map, MU_LOGIN_SCENE, &options);
        if (!m)
            continue;
        raster->textures = m->textures.slots;
        raster->texture_count = m->textures.count;
        raster->texture_filter = m->textures.filter;
        raster->texture_wrap = m->textures.wrap;
        mu_draw_stats ds = {0, 0, 0, 0};
        if (!mu_scene_draw_model(&m->model, &options, &backend, &ds))
            ++s->objects_drawn;
    }
    /* RenderObjects_AfterCharacter 0x016d6949: the after-character objects' glow meshes (slot 0x3c) */
    mu_objects_after_visibility(o, &s->frustum, MU_LOGIN_SCENE);
    for (int32_t k = 0; k < o->rt.after_count; ++k) {
        mu_object_mesh meshes[MU_LOGIN_MESHES];
        int32_t count = 0;
        mu_object_model *m = mu_objects_prepare_after(o, k, s->map, MU_LOGIN_SCENE, meshes, MU_LOGIN_MESHES, &count);
        if (!m)
            continue;
        raster->textures = m->textures.slots;
        raster->texture_count = m->textures.count;
        raster->texture_filter = m->textures.filter;
        raster->texture_wrap = m->textures.wrap;
        for (int32_t j = 0; j < count; ++j) {
            meshes[j].options.fields = &meshes[j].fields;
            mu_draw_stats ds = {0, 0, 0, 0};
            if (!mu_scene_draw_model(&m->model, &meshes[j].options, &backend, &ds))
                ++s->after_meshes;
        }
    }
    raster->textures = NULL;
    raster->texture_count = 0;
    raster->texture_filter = NULL;
    raster->texture_wrap = NULL;
    raster->linear = linear;
    /* RenderSprites(0) / RenderParticles(0) (NATIVE-JOINT-001: the reconstructed particle module) */
    if (s->has_particles) {
        s->frame_sprites = (int32_t)(s->particles.stats.sprites_created - sprites);
        s->billboards = mu_world_particles_draw_raster(&s->particles, raster, v->modelview);
    }
    return stats.tiles.faces;
}

void mu_login_report(const mu_login_session *s, char *out, size_t size)
{
    const mu_objects *o = &s->objects;
    const mu_client_view *v = &s->frame->view;
    snprintf(out, size,
             "{\"world\": %d, \"camera_angle\": [%g, %g, %g], \"camera_position\": [%.3f, %.3f, %.3f], \"fov\": %g,"
             " \"view_far\": %.3f, \"steps\": %u, \"frames\": %u, \"objects\": %d, \"objects_created\": %d,"
             " \"object_models\": %d, \"object_models_missing\": %d, \"objects_drawn\": %ld, \"draw_list\": %d,"
             " \"after_character\": %d, \"after_meshes\": %ld, \"sprites\": %d, \"particles\": %d,"
             " \"billboards\": %ld, \"objects_animated\": %d}",
             MU_LOGIN_WORLD_INDEX, v->angle[0], v->angle[1], v->angle[2], v->position[0], v->position[1],
             v->position[2], v->fov, s->view_far, s->steps, s->frames, o->count, o->rt.created, o->models_loaded,
             o->models_missing, s->objects_drawn, o->rt.draw_count, o->rt.after_count, s->after_meshes,
             s->frame_sprites, (int32_t)s->particles.stats.live, s->billboards,
             s->has_objects ? mu_objects_animated(o) : 0);
}
