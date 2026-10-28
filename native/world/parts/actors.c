/* parts/actors.c (WORLD-RT-001): monsters and NPCs from the DEMO placement file (NATIVE-WORLD-002; the server
 * places them in the real game), animated with the client action tables, with the EffectManager effects their
 * creation attaches.  Two rows: actors (the step, the per-frame effect update, the models in the characters'
 * phase) and actor_effects (the effect instances in the effects phase). */
#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <unistd.h>
#include "../../session/mu_session.h"
#include "../../session/mu_session_seed.h"
#include "../../fixture/mu_fixture.h"
#include "../../fixture/monsters_demo.h"
#include "../../fixture/skills_demo.h"
#include <stdlib.h>
#include <string.h>

#include "../../core/mu_perf.h"
#include "../../core/mu_lang.h"
#include "../../core/mu_renderchar.h"
#include "../../core/mu_scene.h"
#ifndef MU_WORLD_NO_GL
#include "../../viewer/gl_backend.h"
#endif
#include "../world_rt_internal.h"

#ifndef MU_WORLD_NO_GL
static void actors_gl_setup(mu_world_rt *a, void *self);
static void actors_gl_teardown(mu_world_rt *a, void *self);
#endif
static uint64_t record_stamp(const mu_characters_view *v)
{
    uint64_t stamp = 1469598103934665603ull;
    for (int32_t i = 0; i < v->capacity; ++i) {
        if (!v->used[i] || v->records[i].kind != 2) continue;
        stamp = (stamp ^ (uint64_t)(unsigned)i) * 1099511628211ull;
        stamp = (stamp ^ (uint16_t)v->records[i].key) * 1099511628211ull;
        stamp = (stamp ^ v->equipment_revision[i]) * 1099511628211ull;
    }
    return stamp;
}
static void label_actors(mu_world_rt *a)
{
    void *demo = mu_fixture_behavior_state(a->actors.fixture, "monsters");
    for (int32_t i = 0; i < a->actors.count; ++i) {
        mu_world_actor *actor = &a->actors.list[i];
        const mu_monster_spec *spec = mu_monsters_demo_spec(demo, actor->session_key - 0x400);
        if (spec) {
            snprintf(actor->label, sizeof actor->label, "%s", spec->label);
            actor->wander = spec->wander; /* compatibility with the not-yet-migrated combat pause */
        }
    }
}
/* Open-model audio registration follows the viewport/cache order. Audio's model cache
 * prevents a despawn or cache rebuild from registering an already-open model again. */
static void actors_audio_register(mu_world_rt *a)
{
    if (!a->has_sound) return;
    for (int32_t i = 0; i < a->actors.count; ++i) {
        const mu_actor_spec *spec = &a->actors.list[i].actor.spec;
        mu_audio_host_register_actor(a->sound.host, spec->monster_type, spec->model_index);
    }
}

/* Cache identity changes also drop old effect instances. Session lifetime stays in characters. */
void world_rt_actors_sync(mu_world_rt *a)
{
    if (!a->actors.session) return;
    mu_characters_view view = mu_session_characters(a->actors.session);
    uint64_t stamp = record_stamp(&view);
    if (stamp == a->actors.record_stamp) return;
    mu_world_actors next;
    char error[1024];
    if (mu_world_actors_init_records(&next, a->root, a->map, &view, error, sizeof error)) {
        fprintf(stderr, "actors: %s\n", error);
        /* A refused asset must not leave a destroyed/replaced actor or effect visible. */
        memset(&next, 0, sizeof next); next.map = a->map;
    }
    next.session = a->actors.session; next.fixture = a->actors.fixture; next.transport = a->actors.transport;
    next.record_stamp = stamp;
#ifndef MU_WORLD_NO_GL
    if (a->gl_ready) actors_gl_teardown(a, a->part[MU_PART_actors]);
#endif
    mu_world_actors_free(&a->actors); a->actors = next; label_actors(a);
    actors_audio_register(a);
#ifndef MU_WORLD_NO_GL
    if (a->gl_ready) actors_gl_setup(a, a->part[MU_PART_actors]);
#endif
}

static float actors_height(void *ctx, float x, float y)
{
    mu_world_rt *a = ctx;
    return mu_request_terrain_height(a->map->height, a->map->attributes, a->map->water_height, 6, x, y);
}
static int actors_open(struct mu_world_rt *a, void *self)
{
    (void)self;
    if (!a->placement && !(a->npc_demo && a->npc_demo->placement_length)) return 0;
    char error[1024] = {0};
    char placement[] = "/tmp/mu-monsters-placement-XXXXXX", scenario[] = "/tmp/mu-monsters-XXXXXX";
    int fd = mkstemp(placement);
    if (fd < 0) return 1;
    FILE *out = fdopen(fd, "w");
    if (!out) { close(fd); unlink(placement); return 1; }
    if (a->placement) {
        FILE *in = fopen(a->placement, "r");
        if (!in) { fclose(out); unlink(placement); fprintf(stderr, "placement: cannot open file\n"); return 1; }
        char line[1024]; while (fgets(line, sizeof line, in)) fputs(line, out);
        fclose(in);
    }
    if (a->npc_demo) fprintf(out, "\n%s", a->npc_demo->placement);
    fclose(out);
    fd = mkstemp(scenario);
    if (fd < 0) { unlink(placement); return 1; }
    out = fdopen(fd, "w");
    if (!out) { close(fd); unlink(placement); unlink(scenario); return 1; }
    fprintf(out, "endpoint game 127.0.0.1:55902\nuse monsters file=%s\n", placement);
    if (a->players_file && !a->no_players)
        fprintf(out, "use characters defer=1 x=%d y=%d file=%s\n", a->walk.hero.tile[0], a->walk.hero.tile[1], a->players_file);
    if (a->combat_on) fprintf(out,"use combat hp=%d lo=%d hi=%d latency=%d seed=%u counter=%d respawn=%d hero_hp=%d hero_respawn=%d\n",
        a->combat_config.monster_hp,a->combat_config.damage_min,a->combat_config.damage_max,a->combat_config.latency_steps,
        a->combat_config.seed,a->combat_config.counter_attack,a->combat_config.respawn_steps,a->combat_config.hero_hp,a->combat_config.hero_respawn_steps);
    fprintf(out,"use items latency=%d despawn=%d\n",a->items_config.pickup_latency,a->items_config.despawn_steps);
    fprintf(out,"use skills\nat 1 skills root %s\nat 1 skills login %d 30\n",a->root,a->walk.hero.class_byte);
    mu_skills_demo_hero(out, a->walk.hero.class_byte, a->map->world,
                        a->walk.hero.tile[0], a->walk.hero.tile[1], a->walk.hero.angle[2]);
    fclose(out);
    mu_fixture_options options = {scenario, NULL, 0x5eed2026u};
    mu_fixture *fixture = mu_fixture_open(&options, error, sizeof error);
    unlink(placement); unlink(scenario);
    if (!fixture) { fprintf(stderr, "placement: %s\n", error); return 1; }
    mu_transport *transport = mu_fixture_transport(fixture);
    mu_session_config cfg = {0}; cfg.transport = transport;
    mu_fixture_endpoint(fixture, "game", &cfg.connect_server);
    cfg.build = &MU_PINNED_BUILD; cfg.proof = mu_proof_not_required();
    mu_session_seed seed = {0}; seed.class_byte = a->walk.hero.class_byte; seed.place.world = a->map->world;
    mu_session *session = mu_session_open_seeded(&cfg, &seed, error, sizeof error);
    if (!session) { mu_transport_free(transport); mu_fixture_close(fixture); return 1; }
    mu_session_skills_bind(session, a->lang, getenv("MU_LANG_DIR"), a->root);
    mu_world_port port = {0}; port.context = a; port.world = a->map->world; port.terrain_height = actors_height;
    mu_session_attach_world(session, &port);
    mu_transport_poll(transport, 40); mu_session_pump(session, 40);
    mu_characters_view view = mu_session_characters(session);
    if (mu_world_actors_init_records(&a->actors, a->root, a->map, &view, error, sizeof error)) {
        fprintf(stderr, "placement: %s\n", error);
        mu_session_close(session); mu_transport_free(transport); mu_fixture_close(fixture); return 1;
    }
    a->actors.session = session; a->actors.fixture = fixture; a->actors.transport = transport;
    a->actors.record_stamp = record_stamp(&view);
    label_actors(a);
    a->has_actors = 1;
    actors_audio_register(a);
    return 0;
}

static void actors_close(struct mu_world_rt *a, void *self)
{
    (void)self;
    if (a->actors.session) mu_session_close(a->actors.session);
    if (a->actors.transport) mu_transport_free(a->actors.transport);
    if (a->actors.fixture) mu_fixture_close(a->actors.fixture);
    if (a->has_actors) mu_world_actors_free(&a->actors);
    a->has_actors = 0;
}

/* Reserved tick-20 hook. The one characters lease at tick 21 now steps actors. */
static void actors_tick(mu_world_rt *a, void *self) { (void)a; (void)self; }

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
    env.lang = a->lang;
    env.time = a->map->time;
    env.quality = 5;
    mu_draw_options options;
    mu_draw_default_options(&options);
    options.textures = &part->textures;
    mu_draw_stats ds = {0};
    mu_renderchar_stats rs = {0};
    mu_renderchar_draw_item(&part->model, &npc->player_glow[item], &env, npc->player->params.light, 1.0f,
                             &options, backend, &ds, &rs);
    if ((item >= MU_CHARACTER_PART_SLOTS || npc->player_glow[item].type == 0x389c ||
         npc->player_glow[item].type == 0x389d) && a->has_particles)
        mu_renderchar_link_effects(&part->model,
            item < MU_CHARACTER_PART_SLOTS ? npc->player->player_bones : part->bones,
            npc->player_glow[item].type, &a->particles);
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
        mu_characters_view view = mu_session_characters(a->actors.session);
        if (!view.used[actor->session_slot] || view.records[actor->session_slot].key != actor->session_key) continue;
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
        mu_characters_view view = mu_session_characters(a->actors.session);
        if (!view.used[actor->session_slot] || view.records[actor->session_slot].key != actor->session_key) continue;
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
    mu_perf_end(a->perf, MU_PERF_CHARACTERS, d->perf);
}

/* The effects' phase: the actors' EffectManager instances (the combat part closes the phase). */
static void actor_effects_draw_gl(struct mu_world_rt *a, void *self, mu_world_draw *d)
{
    (void)self;
    const mu_client_view *v = &a->walk.frame.view;
    d->perf = mu_perf_begin(a->perf);
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
