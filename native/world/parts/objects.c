/* parts/objects.c (WORLD-RT-001): the world's static objects from local decoded files (--objects-dir,
 * NATIVE-OBJECTS-001/002): CreateObject per record, MoveObjects in the in-world tick, the object light sources
 * after the terrain frame (AddTerrainLight) and RenderObjects with the client's sector and object visibility. */
#include <stdio.h>
#include <string.h>

#include "../../core/mu_perf.h"
#include "../../core/mu_scene.h"
#ifndef MU_WORLD_NO_GL
#include "../../viewer/gl_backend.h"
#endif
#include "../world_rt_internal.h"
#include "../../core/mu_session_audio.h"

static void object_sound(void *context, int32_t id)
{
    mu_world_rt *a = context;
    mu_session *session = world_rt_characters_session(a);
    if (session) {
        if (mu_session_object_sound(session, id)) world_rt_characters_audio_drain(a);
    } else if (a->has_sound) mu_audio_host_play(a->sound.host, id, 0);
}

static int objects_open(struct mu_world_rt *a, void *self)
{
    (void)self;
    char error[1024];
    if (a->objects_dir) {
        mu_objects_init(&a->objects, a->world);
        if (mu_objects_load_dir(&a->objects, a->objects_dir, error, sizeof error) == MU_OBJECTS_FILE_OK) {
            mu_objects_load_models(&a->objects, a->root, 0);
            mu_objects_start(&a->objects, a->root);   /* NATIVE-OBJECTS-002: CreateObject per record */
            a->has_objects = 1;
            a->objects.sound = object_sound;
            a->objects.sound_context = a;
        } else {
            fprintf(stderr, "objects: %s (drawing none)\n", error);
        }
    }
    return 0;
}

static void objects_close(struct mu_world_rt *a, void *self)
{
    (void)self;
    if (a->has_objects)
        mu_objects_free(&a->objects);
}

/* MoveObjects in the client's in-world tick (NATIVE-OBJECTS-002). */
static void objects_tick(struct mu_world_rt *a, void *self)
{
    (void)self;
    const mu_hero *h = &a->walk.hero;
    if (a->has_objects) {
        const int32_t index = ((h->tile[1] & 0xff) << 8) + (h->tile[0] & 0xff);
        mu_objects_step_inputs in = {6, a->map->layer1[index], a->map->time,
                                     {h->position[0], h->position[1], h->position[2]}, a->frustum.x2d,
                                     a->frustum.y2d};
        a->objects.rt.hero_action = h->action;
        a->objects.rt.environment = a->has_env ? &a->env.env : NULL;
        a->objects.rt.hero_safe = (uint8_t)(a->map->attributes[index] & 1u);
        if (a->world == 57 || a->world == 58) mu_objects_set_clock(&a->objects, a->walk.frame.now);
        memcpy(a->objects.rt.raklion_hero_angle, h->angle, sizeof h->angle);
        mu_objects_step(&a->objects, &in);
    }
}

/* The object light sources of the last MoveObjects (AddTerrainLight), after the terrain frame's light copy (the
 * legacy box has none). */
static void objects_frame(struct mu_world_rt *a, void *self, uint32_t now)
{
    (void)self;
    (void)now;
    if (a->legacy_box)
        return;
    if (a->has_objects) {
        mu_objects_apply_lights(&a->objects, a->map);
        if (a->world == 57 || a->world == 58) a->walk.frame.camera.earthquake = a->objects.rt.raklion_quake;
    }
}

static void objects_draw_soft(struct mu_world_rt *a, void *self, mu_world_draw *d)
{
    (void)self;
    if (a->has_objects) {   /* RenderObjects with the client's visibility (NATIVE-OBJECTS-002) */
        float eye[3], target[3];
        world_rt_effect_camera(a, eye, target);
        a->objects_drawn = mu_objects_render_raster(&a->objects, a->map, d->raster, &a->frustum, 6, eye, target);
    }
}

static void objects_report_summary(const struct mu_world_rt *a, const void *self)
{
    (void)self;
    if (a->has_objects)
        printf(
            "{\"objects\": %d, \"object_models\": %d, \"object_models_missing\": %d, \"objects_drawn\": %ld,"
            " \"objects_created\": %d, \"objects_create_unsupported\": %d, \"object_steps\": %u,"
            " \"objects_moved\": %ld, \"object_ticks\": %ld, \"object_lights\": %ld, \"object_particles\": "
            "%ld,"
            " \"object_sounds\": %ld, \"object_draw_list\": %d, \"object_lights_last_step\": %d,"
            " \"objects_animated\": %d, \"object_after_meshes\": %ld, \"object_textures_retried\": %d,"
            " \"object_textures_unresolved\": %d}\n",
            a->objects.count, a->objects.models_loaded, a->objects.models_missing, a->objects_drawn,
            a->objects.rt.created, a->objects.rt.create_unsupported, a->objects.rt.steps, a->objects.rt.moved,
            a->objects.rt.ticks, a->objects.rt.light_events, a->objects.rt.particle_events,
            a->objects.rt.sound_events, a->objects.rt.draw_count, a->objects.rt.light_count,
            mu_objects_animated(&a->objects), a->objects.rt.after_meshes,
            a->objects.textures_retried, a->objects.textures_unresolved);
}

#ifndef MU_WORLD_NO_GL
typedef struct objects_part {
    mu_gl_backend object_gl[MU_OBJECT_TYPES];
} objects_part;

static void objects_gl_setup(struct mu_world_rt *a, void *self)
{
    objects_part *p = self;
    for (int32_t t = 0; t < MU_OBJECT_TYPES; ++t) {
        memset(&p->object_gl[t], 0, sizeof p->object_gl[t]);
        if (a->has_objects && a->objects.models[t] && a->objects.models[t]->loaded)
            mu_gl_upload(&p->object_gl[t], &a->objects.models[t]->textures, 0);
        p->object_gl[t].batch = a->batch;
    }
}

static void objects_gl_teardown(struct mu_world_rt *a, void *self)
{
    (void)a;
    objects_part *p = self;
    for (int32_t t = 0; t < MU_OBJECT_TYPES; ++t)
        if (p->object_gl[t].textures)
            mu_gl_release(&p->object_gl[t]);
}

static void objects_draw_gl(struct mu_world_rt *a, void *self, mu_world_draw *d)
{
    objects_part *p = self;
    d->perf = mu_perf_begin(a->perf);
    a->objects_drawn = 0;
    if (a->has_objects) {   /* RenderObjects: client sector/object visibility, RenderObject per entry */
        if (a->batch)
            mu_gl_batch_session_begin(a->batch);
        mu_objects_visibility(&a->objects, &a->frustum, 6);
        for (int32_t k = 0; k < a->objects.rt.draw_count; ++k) {
            mu_draw_options object_options;
            mu_object_model *m = mu_objects_prepare(&a->objects, k, a->map, 6, &object_options);
            if (!m)
                continue;
            mu_render_backend backend;
            mu_gl_backend_bind(&p->object_gl[m->type], &backend);
            mu_draw_stats ds = {0, 0, 0, 0};
            mu_object_mesh meshes[MU_OBJECT_FIRST_MESHES];
            const int32_t count = mu_objects_first_meshes(&a->objects, k, a->map, m, meshes, MU_OBJECT_FIRST_MESHES);
            if (count) {
                for (int32_t j = 0; j < count; ++j) {
                    meshes[j].options.fields = &meshes[j].fields;
                    mu_scene_draw_model(&m->model, &meshes[j].options, &backend, &ds);
                }
                ++a->objects_drawn;
            } else if (!mu_scene_draw_model(&m->model, &object_options, &backend, &ds))
                ++a->objects_drawn;
        }
        if (a->batch)
            mu_gl_batch_session_end(a->batch);
        glDisable(GL_BLEND);
        glDepthMask(GL_TRUE);
    }
    mu_perf_end(a->perf, MU_PERF_OBJECTS, d->perf);
}
#endif

/* RENDER-WORLDS-A: 0x016d6949 after characters/items and the environment. */
static void objects_after_draw_soft(struct mu_world_rt *a, void *self, mu_world_draw *d)
{
    (void)self;
    if (!a->has_objects)
        return;
    mu_objects_after_visibility(&a->objects, &a->frustum, 6);
    const int linear = d->raster->linear;
    d->raster->linear = 1;
    mu_render_backend backend;
    mu_raster_backend(d->raster, &backend);
    for (int32_t k = 0; k < a->objects.rt.after_count; ++k) {
        mu_object_mesh meshes[40];
        int32_t count;
        mu_object_model *m = mu_objects_prepare_after(&a->objects, k, a->map, 6, meshes, 40, &count);
        if (!m)
            continue;
        d->raster->textures = m->textures.slots;
        d->raster->texture_count = m->textures.count;
        d->raster->texture_filter = m->textures.filter;
        d->raster->texture_wrap = m->textures.wrap;
        for (int32_t j = 0; j < count; ++j) {
            meshes[j].options.fields = &meshes[j].fields;
            mu_draw_stats ds = {0};
            mu_scene_draw_model(&m->model, &meshes[j].options, &backend, &ds);
        }
    }
    d->raster->linear = linear;
    d->raster->textures = NULL;
    d->raster->texture_count = 0;
    d->raster->texture_filter = NULL;
    d->raster->texture_wrap = NULL;
}
#ifndef MU_WORLD_NO_GL
static void objects_after_draw_gl(struct mu_world_rt *a, void *self, mu_world_draw *d)
{
    (void)self;
    objects_part *p = a->part[MU_PART_objects];
    (void)d;
    if (!a->has_objects)
        return;
    mu_objects_after_visibility(&a->objects, &a->frustum, 6);
    if (a->batch)
        mu_gl_batch_session_begin(a->batch);
    for (int32_t k = 0; k < a->objects.rt.after_count; ++k) {
        mu_object_mesh meshes[40];
        int32_t count;
        mu_object_model *m = mu_objects_prepare_after(&a->objects, k, a->map, 6, meshes, 40, &count);
        if (!m)
            continue;
        mu_render_backend backend;
        mu_gl_backend_bind(&p->object_gl[m->type], &backend);
        for (int32_t j = 0; j < count; ++j) {
            meshes[j].options.fields = &meshes[j].fields;
            mu_draw_stats ds = {0};
            mu_scene_draw_model(&m->model, &meshes[j].options, &backend, &ds);
        }
    }
    if (a->batch)
        mu_gl_batch_session_end(a->batch);
    glDisable(GL_BLEND);
    glDepthMask(GL_TRUE);
}
#endif
const mu_world_part_ops mu_part_objects_after = {
    .name = "objects_after",
#ifndef MU_WORLD_NO_GL
    .draw_gl = objects_after_draw_gl,
#endif
    .draw_soft = objects_after_draw_soft,
};

const mu_world_part_ops mu_part_objects = {
    .name = "objects",
#ifndef MU_WORLD_NO_GL
    .state_size = sizeof(objects_part),
    .draw_gl = objects_draw_gl,
    .gl_setup = objects_gl_setup,
    .gl_teardown = objects_gl_teardown,
#endif
    .open = objects_open,
    .close = objects_close,
    .tick = objects_tick,
    .frame = objects_frame,
    .draw_soft = objects_draw_soft,
    .report_summary = objects_report_summary,
};
