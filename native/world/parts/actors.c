/* parts/actors.c (WORLD-RT-001): monsters and NPCs from the DEMO placement file (NATIVE-WORLD-002; the server
 * places them in the real game), animated with the client action tables, with the EffectManager effects their
 * creation attaches.  Two rows: actors (the step, the per-frame effect update, the models in the characters'
 * phase) and actor_effects (the effect instances in the effects phase). */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../../core/mu_perf.h"
#include "../../core/mu_renderchar.h"
#include "../../core/mu_scene.h"
#ifndef MU_WORLD_NO_GL
#include "../../viewer/gl_backend.h"
#endif
#include "../world_rt_internal.h"

static int actors_open(struct mu_world_rt *a, void *self)
{
    (void)self;
    char error[1024];
    if (a->npc_demo && a->npc_demo->placement_length) {
        size_t cap = (1u << 20) + sizeof a->npc_demo->placement;
        char *text = malloc(cap);
        size_t n = 0;
        if (text && a->placement) {
            FILE *f = fopen(a->placement, "rb");
            if (f) {
                n = fread(text, 1, cap - sizeof a->npc_demo->placement - 2, f);
                fclose(f);
            }
        }
        if (!text) {
            fprintf(stderr, "npc: out of memory\n");
            return 1;
        }
        text[n++] = '\n';
        memcpy(text + n, a->npc_demo->placement, a->npc_demo->placement_length + 1);
        int bad = mu_world_actors_load_text(&a->actors, a->root, a->map, text, 0, error, sizeof error);
        free(text);
        if (bad) {
            fprintf(stderr, "placement: %s\n", error);
            return 1;
        }
        a->has_actors = 1;
    } else if (a->placement) {
        if (mu_world_actors_load(&a->actors, a->root, a->map, a->placement, 0, error, sizeof error)) {
            fprintf(stderr, "placement: %s\n", error);
            return 1;
        }
        a->has_actors = 1;
    }
    return 0;
}

static void actors_close(struct mu_world_rt *a, void *self)
{
    (void)self;
    if (a->has_actors)
        mu_world_actors_free(&a->actors);
}

static void actors_tick(struct mu_world_rt *a, void *self)
{
    (void)self;
    if (a->has_actors)
        mu_world_actors_step(&a->actors);
}

static void actors_frame(struct mu_world_rt *a, void *self, uint32_t now)
{
    (void)self;
    (void)now;
    if (a->has_actors)
        mu_world_actors_frame(&a->actors, 0.1f);   /* effect node update per frame, dt [0x01cf103c] = 0.1 */
}

static void npc_item_draw(mu_world_rt *a, const mu_world_actor *npc, int item, const mu_render_backend *backend)
{
    const mu_character_item *part = &npc->player->items[item];
    mu_renderchar_env env;
    mu_renderchar_default_env(&env);
    env.time = a->map->time;
    env.quality = 5;
    mu_draw_options options;
    mu_draw_default_options(&options);
    options.textures = &part->textures;
    mu_draw_stats ds = {0};
    mu_renderchar_stats rs = {0};
    mu_renderchar_draw_item(&part->model, &npc->player_glow[item], &env, npc->player->params.light, 1.0f,
                             &options, backend, &ds, &rs);
    if (item >= MU_CHARACTER_PART_SLOTS && a->has_particles)
        mu_renderchar_link_effects(&part->model, part->bones, npc->player_glow[item].type, &a->particles);
}

static void actors_draw_soft(struct mu_world_rt *a, void *self, mu_world_draw *d)
{
    (void)self;
    mu_raster *raster = d->raster;
    mu_render_backend backend;
    mu_raster_backend(raster, &backend);
    mu_draw_options options;
    mu_draw_default_options(&options);
    for (int32_t i = 0; a->has_actors && i < a->actors.count; ++i) {
        const mu_world_actor *actor = &a->actors.list[i];
        float alpha = a->combat ? mu_combat_actor_alpha(a->combat, i) : 1.0f;   /* o + 0xdc */
        if (alpha <= 0.0f)
            continue;
        if (actor->player) {
            for (int n = 0; n < MU_CHARACTER_ITEMS; n++) {
                int k = mu_world_draw_order[n];
                const mu_character_item *part = &actor->player->items[k];
                if (!part->loaded)
                    continue;
                raster->textures = part->textures.slots;
                raster->texture_count = part->textures.count;
                raster->texture_filter = part->textures.filter;
                raster->texture_wrap = part->textures.wrap;
                if (a->has_particles)
                    mu_world_particles_character_shadow(&a->particles, &part->model, &part->bmd, &backend);
                npc_item_draw(a, actor, k, &backend);
            }
            continue;
        }
        if (a->has_particles)
            mu_world_particles_character_shadow(&a->particles, &actor->actor.model, &actor->actor.bmd, &backend);
        options.alpha = alpha;
        raster->textures = actor->actor.textures.slots;
        raster->texture_count = actor->actor.textures.count;
        raster->texture_filter = actor->actor.textures.filter;
        raster->texture_wrap = actor->actor.textures.wrap;
        options.textures = &actor->actor.textures;
        mu_draw_stats ds = {0, 0, 0, 0};
        mu_scene_draw_model(&actor->actor.model, &options, &backend, &ds);
    }
}

static void actors_report_summary(const struct mu_world_rt *a, const void *self)
{
    (void)self;
    if (a->has_actors) {
        const mu_world_actors *s = &a->actors;
        printf("{\"actors\": %d, \"actor_steps\": %u, \"actor_moves\": %u, \"actor_arrivals\": %u,"
               " \"effect_instances\": %u}\n", s->count, s->steps, s->moves, s->arrivals, s->effect_instances);
        for (int32_t i = 0; i < s->count; ++i) {
            const mu_world_actor *x = &s->list[i];
            printf("{\"actor\": %d, \"class\": %d, \"label\": \"%s\", \"model\": %d, \"tile\": [%d, %d],"
                   " \"action\": %u, \"frame\": %.3f, \"speed\": %.4f, \"moves\": %u, \"arrivals\": %u,"
                   " \"player_model\": %d, \"scale\": %.3f,"
                   " \"effects\": %d, \"light\": [%.6g, %.6g, %.6g], \"light_override\": %d}\n", i, x->server_class,
                   x->label, x->actor.spec.model_index, x->tile[0], x->tile[1],
                   x->player ? mu_model_action(&x->player->player) : mu_actor_action(&x->actor),
                   (double)(x->player ? mu_model_frame(&x->player->player) : mu_actor_frame(&x->actor)),
                   (double)x->actor.last_speed, x->moves, x->arrivals, x->player != NULL, (double)x->actor.spec.scale,
                   x->effect_count, (double)x->actor.model.params.color[0], (double)x->actor.model.params.color[1],
                   (double)x->actor.model.params.color[2], x->actor.model.params.light_override);
        }
    }
}

#ifndef MU_WORLD_NO_GL
typedef struct actors_part {
    mu_gl_backend actor_gl[MU_WORLD_ACTORS_MAX];
    mu_gl_backend actor_part_gl[MU_WORLD_ACTORS_MAX][MU_CHARACTER_ITEMS];
} actors_part;

static void actors_gl_setup(struct mu_world_rt *a, void *self)
{
    actors_part *p = self;
    for (int32_t i = 0; i < MU_WORLD_ACTORS_MAX; ++i) {
        memset(&p->actor_gl[i], 0, sizeof p->actor_gl[i]);
        p->actor_gl[i].batch = a->batch;
    }
    memset(p->actor_part_gl, 0, sizeof p->actor_part_gl);
    for (int32_t i = 0; a->has_actors && i < a->actors.count; ++i) {
        const mu_world_actor *npc = &a->actors.list[i];
        if (npc->player) {
            for (int k = 0; k < MU_CHARACTER_ITEMS; k++)
                if (npc->player->items[k].loaded)
                    mu_gl_upload(&p->actor_part_gl[i][k], &npc->player->items[k].textures, 0);
        } else {
            mu_gl_upload(&p->actor_gl[i], &npc->actor.textures, 0);
        }
    }
}

static void actors_gl_teardown(struct mu_world_rt *a, void *self)
{
    actors_part *p = self;
    for (int32_t i = 0; a->has_actors && i < a->actors.count; ++i) {
        mu_gl_release(&p->actor_gl[i]);
        for (int k = 0; k < MU_CHARACTER_ITEMS; k++)
            if (p->actor_part_gl[i][k].textures)
                mu_gl_release(&p->actor_part_gl[i][k]);
    }
}

/* The last of the characters' phase (opened by the hero part). */
static void actors_draw_gl(struct mu_world_rt *a, void *self, mu_world_draw *d)
{
    actors_part *p = self;
    mu_draw_options options;
    mu_draw_default_options(&options);
    if (a->batch && a->players)
        mu_gl_batch_session_begin(a->batch);
    for (int32_t i = 0; a->has_actors && i < a->actors.count; ++i) {
        const mu_world_actor *actor = &a->actors.list[i];
        float alpha = a->combat ? mu_combat_actor_alpha(a->combat, i) : 1.0f;   /* o + 0xdc */
        if (alpha <= 0.0f)
            continue;   /* removed by the dead fade */
        if (actor->player) {
            if (a->batch)
                mu_gl_batch_session_end(a->batch);
            for (int n = 0; n < MU_CHARACTER_ITEMS; n++) {
                int k = mu_world_draw_order[n];
                const mu_character_item *part = &actor->player->items[k];
                if (!part->loaded)
                    continue;
                mu_render_backend part_backend;
                mu_gl_backend_bind(&p->actor_part_gl[i][k], &part_backend);
                if (a->has_particles)
                    mu_world_particles_character_shadow(&a->particles, &part->model, &part->bmd, &part_backend);
                npc_item_draw(a, actor, k, &part_backend);
            }
            if (a->batch)
                mu_gl_batch_session_begin(a->batch);
            continue;
        }
        mu_render_backend backend;
        mu_gl_backend_bind(&p->actor_gl[i], &backend);
        if (a->has_particles)
            mu_world_particles_character_shadow(&a->particles, &actor->actor.model, &actor->actor.bmd, &backend);
        options.textures = &actor->actor.textures;
        options.alpha = alpha;
        mu_draw_stats ds = {0, 0, 0, 0};
        mu_scene_draw_model(&actor->actor.model, &options, &backend, &ds);
    }
    if (a->batch)
        mu_gl_batch_session_end(a->batch);
    mu_perf_end(MU_PERF_CHARACTERS, d->perf);
}

/* The effects' phase: the actors' EffectManager instances (the combat part closes the phase). */
static void actor_effects_draw_gl(struct mu_world_rt *a, void *self, mu_world_draw *d)
{
    (void)self;
    const mu_client_view *v = &a->walk.frame.view;
    d->perf = mu_perf_begin();
    if (a->has_actors && a->actors.has_effects && a->actors.effects.instance_count) {
        float eye[3], target[3];
        world_rt_effect_camera(a, eye, target);
        glEnable(GL_DEPTH_TEST);
        a->effects_visible = mu_effect_scene_render_to(&a->actors.effects, eye, target, v->fov,
                                                       (float)d->width / (float)d->height, v->view_near,
                                                       v->view_far * 1.4f, world_rt_gl_effect, a);
        glBindTexture(GL_TEXTURE_2D, 0);   /* the pass ends with glBindTexture(GL_TEXTURE_2D, 0) */
        glDepthMask(GL_TRUE);
        glDisable(GL_BLEND);
    }
}
#endif

static void actor_effects_draw_soft(struct mu_world_rt *a, void *self, mu_world_draw *d)
{
    (void)self;
    mu_raster *raster = d->raster;
    const mu_client_view *v = &a->walk.frame.view;
    if (a->has_actors && a->actors.has_effects && a->actors.effects.instance_count) {
        float eye[3], target[3];
        world_rt_effect_camera(a, eye, target);
        a->effects_visible = mu_effect_scene_render(&a->actors.effects, eye, target, v->fov,
                                                    (float)raster->width / (float)raster->height, v->view_near,
                                                    v->view_far * 1.4f, raster);
    }
}

const mu_world_part_ops mu_part_actors = {
    .name = "actors",
#ifndef MU_WORLD_NO_GL
    .state_size = sizeof(actors_part),
    .draw_gl = actors_draw_gl,
    .gl_setup = actors_gl_setup,
    .gl_teardown = actors_gl_teardown,
#endif
    .open = actors_open,
    .close = actors_close,
    .tick = actors_tick,
    .frame = actors_frame,
    .draw_soft = actors_draw_soft,
    .report_summary = actors_report_summary,
};

const mu_world_part_ops mu_part_actor_effects = {
    .name = "actor_effects",
#ifndef MU_WORLD_NO_GL
    .draw_gl = actor_effects_draw_gl,
#endif
    .draw_soft = actor_effects_draw_soft,
};
