/* parts/particles.c (WORLD-RT-001): CreateParticle, CreateSprite, RenderBodyShadow (NATIVE-PARTICLE-001) and the
 * world objects' joint and effect pools (NATIVE-JOINT-001): MoveEffects, MoveJoints and MoveParticles after the
 * other movers of the in-world tick, their terrain lights, the effect models, RenderJoints(0) and the sprite
 * section.  With --no-particles the objects' fires draw as NATIVE-OBJECTS-002's stand-in billboards here. */
#include <stdio.h>
#include <string.h>

#include "../../core/mu_perf.h"
#include "../../core/mu_scene.h"
#ifndef MU_WORLD_NO_GL
#include "../../viewer/gl_backend.h"
#endif
#include "../world_rt_internal.h"

static int particles_open(struct mu_world_rt *a, void *self)
{
    (void)self;
    char error[1024];
    if (!a->no_particles) {   /* NATIVE-PARTICLE-001: CreateParticle, CreateSprite, RenderBodyShadow */
        if (mu_world_particles_open(&a->particles, a->root, a->map, a->world, a->particle_seed, 0, error,
                                    sizeof error)) {
            fprintf(stderr, "particles: %s\n", error);
            return 1;
        }
        a->has_particles = 1;
        mu_world_particles_attach(&a->particles, a->has_objects ? &a->objects : NULL, a->has_env ? &a->env : NULL);
        a->particles.actors = &a->actors;
        for (int32_t i = 0; i < a->actors.count; i++) {
            const mu_world_actor *npc = &a->actors.list[i];
            if (npc->server_class == 257)
                mu_world_particles_joint(&a->particles, MU_JT_BITMAP_FLARE, npc->position, npc->position, npc->angle,
                                         42, MU_WORLD_ACTOR_FX_BASE + i, 15.0f, 0xffff, 0, 0, 0xffff, 0, NULL);
        }
    }
    return 0;
}

static void particles_close(struct mu_world_rt *a, void *self)
{
    (void)self;
    if (a->has_particles)
        mu_world_particles_close(&a->particles);
}

static void particles_tick(struct mu_world_rt *a, void *self)
{
    (void)self;
    const mu_walk *w = &a->walk;
    const mu_hero *h = &w->hero;
    if (a->has_particles && a->joint_demo >= 0 && w->steps % 20 == 1) {
        /* --joint-demo (a viewer test, not client behaviour): a Tormenta lightning joint 0x7f7d of the subtype
         * above the hero every 20 steps, through the world objects' joint pool */
        const float at[3] = {h->position[0], h->position[1], h->position[2] + 150.0f}, angle[3] = {0.0f, 0.0f, 0.0f};
        mu_world_particles_joint(&a->particles, MU_JT_TYPE_THUNDER_BOLT, at, at, angle, a->joint_demo, -1, 1.0f, 0xffff,
                                 0, 0, 0xffff, 0, NULL);
    }
    if (a->has_particles) {   /* MoveEffects, MoveJoints, MoveParticles after the other movers of the in-world tick */
        mu_world_particles_set_hero(&a->particles, h->position);
        mu_world_particles_step(&a->particles, a->map->time);
    }
}

static void particles_frame(struct mu_world_rt *a, void *self, uint32_t now)
{
    (void)self;
    (void)now;
    if (a->has_particles)
        mu_world_particles_apply_lights(&a->particles, a->map);
}

static void particles_draw_soft(struct mu_world_rt *a, void *self, mu_world_draw *d)
{
    (void)self;
    const mu_client_view *v = &a->walk.frame.view;
    if (a->has_particles) {   /* effect models, RenderJoints(0), the sprite section (NATIVE-PARTICLE-001, -JOINT-001) */
        mu_world_particles_draw_models_raster(&a->particles, d->raster);
        mu_world_particles_draw_raster(&a->particles, d->raster, v->modelview);
    }
}

static void particles_report_summary(const struct mu_world_rt *a, const void *self)
{
    (void)self;
    if (a->has_particles) {
        const mu_world_particles_stats *p = &a->particles.stats;
        printf("{\"particles\": true, \"created\": %llu, \"dropped\": %llu, \"unsupported\": %llu,"
               " \"overflow\": %llu, \"live\": %u, \"max_live\": %u, \"steps\": %u, \"sprites_created\": %llu,"
               " \"drawn_particles\": %u, \"drawn_sprites\": %u, \"shadows\": %u, \"shadow_vertices\": %u,"
               " \"visuals\": %u, \"joints\": %llu, \"effects\": %llu, \"rand_calls\": %llu, \"bitmaps\": [",
               (unsigned long long)p->created, (unsigned long long)p->dropped, (unsigned long long)p->unsupported,
               (unsigned long long)p->overflow, p->live, p->max_live, p->steps,
               (unsigned long long)p->sprites_created, p->drawn_particles, p->drawn_sprites, p->shadows,
               p->shadow_vertices, p->visuals, (unsigned long long)p->joints, (unsigned long long)p->effects,
               (unsigned long long)a->particles.rand_calls);
        for (int i = 0; i < MU_WORLD_PT_BITMAPS; ++i)
            printf("%s%d", i ? ", " : "", a->particles.bitmap_present[i]);
        printf("]}\n");
        /* NATIVE-JOINT-001: the world objects' joint and effect pools */
        printf("{\"joints\": true, \"created\": %llu, \"unsupported\": %llu, \"full\": %llu, \"live\": %u,"
               " \"max_live\": %u, \"quads\": %u, \"effects_created\": %llu, \"effects_unsupported\": %llu,"
               " \"effects_live\": %u, \"effect_models\": %u, \"sounds\": %llu, \"decal_fans\": %llu}\n",
               (unsigned long long)p->joints_created, (unsigned long long)p->joints_unsupported,
               (unsigned long long)p->joints_full, p->live_joints, p->max_joints, p->drawn_joint_quads,
               (unsigned long long)p->effects_created, (unsigned long long)p->effects_unsupported, p->live_effects,
               p->drawn_effect_models, (unsigned long long)p->sounds, (unsigned long long)p->decals_total);
    }
}

#ifndef MU_WORLD_NO_GL
typedef struct particles_part {
    mu_gl_backend particle_gl;                       /* NATIVE-PARTICLE-001: the effect bitmaps */
    mu_gl_backend particle_model_gl[MU_WORLD_FX_MODELS]; /* NATIVE-JOINT-001: the world objects' effect models */
} particles_part;

static void particles_gl_setup(struct mu_world_rt *a, void *self)
{
    particles_part *p = self;
    memset(&p->particle_gl, 0, sizeof p->particle_gl);
    memset(p->particle_model_gl, 0, sizeof p->particle_model_gl);
    if (a->has_particles)
        mu_gl_upload(&p->particle_gl, &a->particles.bitmaps, 0);
}

static void particles_gl_teardown(struct mu_world_rt *a, void *self)
{
    (void)a;
    particles_part *p = self;
    if (p->particle_gl.textures)
        mu_gl_release(&p->particle_gl);
    for (int i = 0; i < MU_WORLD_FX_MODELS; ++i)
        if (p->particle_model_gl[i].textures)
            mu_gl_release(&p->particle_model_gl[i]);
}

static int particle_gl_backend(void *context, const mu_world_particles *wp, mu_render_backend *out)
{
    particles_part *p = context;
    (void)wp;
    mu_gl_backend_bind(&p->particle_gl, out);
    return 0;
}

/* NATIVE-JOINT-001: the world objects' effect models (the Tormenta tornado) through the scene draw. */
static void particle_model_gl(void *context, const mu_model *model, const mu_textures *textures, int32_t slot,
                              const mu_draw_options *draw_options)
{
    particles_part *p = context;
    mu_gl_backend *gl = &p->particle_model_gl[slot];
    if (!gl->textures)
        mu_gl_upload(gl, textures, 0);
    mu_render_backend backend;
    mu_gl_backend_bind(gl, &backend);
    mu_draw_stats ds = {0, 0, 0, 0};
    mu_scene_draw_model(model, draw_options, &backend, &ds);
}

static void particles_draw_gl(struct mu_world_rt *a, void *self, mu_world_draw *d)
{
    const mu_client_view *v = &a->walk.frame.view;
    d->perf = mu_perf_begin();
    if (a->has_particles) {   /* effect models, RenderJoints(0), the sprite section (NATIVE-PARTICLE-001, -JOINT-001) */
        mu_world_particles_draw_models(&a->particles, particle_model_gl, self);
        mu_world_particles_target target = {self, particle_gl_backend};
        mu_world_particles_draw(&a->particles, v->modelview, &target);
        glBindTexture(GL_TEXTURE_2D, 0);
        glDepthMask(GL_TRUE);
        glDisable(GL_BLEND);
        glDisable(GL_ALPHA_TEST);
    }
    else if (a->has_objects) {   /* --no-particles: the NATIVE-OBJECTS-002 stand-in billboards of the object fires */
        static mu_fx_vertex quads[4 * MU_OBJECT_PARTICLES];
        float eye[3], target[3];
        world_rt_effect_camera(a, eye, target);
        for (int32_t b = 0; b < 2; ++b) {
            mu_fx_draw_state state;
            uint32_t n = mu_objects_particle_quads(&a->objects, b, eye, target, quads, 4 * MU_OBJECT_PARTICLES, &state);
            if (n)
                world_rt_gl_effect(a, quads, n, &state, b == 0 ? &a->objects.rt.fire : &a->objects.rt.smoke, NULL);
        }
        glBindTexture(GL_TEXTURE_2D, 0);
        glDepthMask(GL_TRUE);
        glDisable(GL_BLEND);
    }
    mu_perf_end(MU_PERF_PARTICLES, d->perf);
}
#endif

const mu_world_part_ops mu_part_particles = {
    .name = "particles",
#ifndef MU_WORLD_NO_GL
    .state_size = sizeof(particles_part),
    .draw_gl = particles_draw_gl,
    .gl_setup = particles_gl_setup,
    .gl_teardown = particles_gl_teardown,
#endif
    .open = particles_open,
    .close = particles_close,
    .tick = particles_tick,
    .frame = particles_frame,
    .draw_soft = particles_draw_soft,
    .report_summary = particles_report_summary,
};
