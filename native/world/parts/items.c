#define _POSIX_C_SOURCE 200809L
/* parts/items.c (WORLD-RT-001): ground items (NATIVE-ITEMS-001, core/mu_items, on with --combat or --items):
 * monsters that die drop DEMO items (the server's item viewport message, made up here), which fall, spin and land
 * as CreateItem/MoveItems do, render through RenderItems' plan with the item render passes and carry
 * hudPlayerName-style labels; the mouse selects them (SelectItem), a click walks there and picks up.  Two rows:
 * items (pick-up case, MoveItems, selection, RenderItems after the characters) and item_labels (the labels over
 * the frame). */
#include <stdio.h>
#include <unistd.h>
#include "../../session/mu_session_seed.h"
#include "../../fixture/mu_fixture.h"
#include "../../fixture/behavior.h"
#include <stdlib.h>
#include <string.h>

#include "../../core/mu_perf.h"
#include "../../core/mu_renderchar.h"
#ifndef MU_WORLD_NO_GL
#include "../../viewer/gl_backend.h"
#endif
#include "../world_rt_internal.h"

typedef struct items_part {
#ifndef MU_WORLD_NO_GL
    mu_gl_backend item_gl[MU_WORLD_ITEM_MODELS];
#endif
    mu_world_rt *rt;
    mu_session *session;
    mu_fixture *fixture;
    mu_transport *transport;
    uint32_t tick;
    int owned;
} items_part;

static int items_open(struct mu_world_rt *a, void *self)
{
    items_part *p=self;
    char error[1024];
    if ((a->combat_on || a->items_on) && !a->no_items) {   /* NATIVE-ITEMS-001 */
        a->ground = calloc(1, sizeof *a->ground);
        if (!a->ground ||
            mu_world_items_open(a->ground, a->root, &a->walk, &a->items_config, error, sizeof error)) {
            fprintf(stderr, "items: %s (continuing without them)\n", a->ground ? error : "out of memory");
            if (a->ground)
                mu_world_items_close(a->ground);
            free(a->ground);
            a->ground = NULL;
        } else {
            p->session=a->actors.session; p->fixture=a->actors.fixture;
            if(!p->session) {
                char path[]="/tmp/mu-items-XXXXXX"; int fd=mkstemp(path); if(fd<0)return 1;
                FILE *f=fdopen(fd,"w"); if(!f) {close(fd);unlink(path);return 1;}
                fprintf(f,"endpoint game 127.0.0.1:55906\nuse items latency=%d despawn=%d\n",
                        a->items_config.pickup_latency,a->items_config.despawn_steps); fclose(f);
                mu_fixture_options opt={path,NULL,a->items_config.seed};
                p->fixture=mu_fixture_open(&opt,error,sizeof error);unlink(path); if(!p->fixture)return 1;
                p->owned=1;p->transport=mu_fixture_transport(p->fixture);
                mu_session_config cfg={0};cfg.transport=p->transport;
                mu_fixture_endpoint(p->fixture,"game",&cfg.connect_server);
                mu_session_seed seed={0};seed.place.world=a->map->world;
                p->session=mu_session_open_seeded(&cfg,&seed,error,sizeof error);if(!p->session)return 1;
            }
            mu_world_items_bind(a->ground,p->session,mu_fixture_behavior_state(p->fixture,"items"));
            if (a->has_particles)
                a->ground->particles = &a->particles;
            a->ground->frustum = &a->frustum;   /* RenderItems' TestFrustrum uses the frame's planes */
            if (a->has_sound) {
                a->ground->play_sound = world_rt_env_sound;
                a->ground->sound_context = a;
            }
        }
    }
    return 0;
}

static void items_close(struct mu_world_rt *a, void *self)
{
    items_part *p=self;
    if (a->ground) {
        mu_world_items_close(a->ground);
        free(a->ground);
        a->ground = NULL;
    }
    if(p->owned) {mu_session_close(p->session);mu_transport_free(p->transport);mu_fixture_close(p->fixture);}
}

/* NATIVE-ITEMS-001: a click on the selected item starts the pick-up walk. */
static void items_pre_tick(struct mu_world_rt *a, void *self)
{
    (void)self;
    if (a->ground)
        mu_world_items_pre_step(a->ground);
}

/* NATIVE-ITEMS-001: the demo server's drops, MoveItems, the pick-up mode. */
static void items_tick(struct mu_world_rt *a, void *self)
{
    items_part *p=self;
    if (a->ground) {
        if(p->owned) {++p->tick;mu_transport_poll(p->transport,p->tick*40);mu_session_pump(p->session,p->tick*40);}
        mu_sim sim=mu_session_sim_begin(p->session);
        mu_world_items_step(a->ground);
        mu_session_sim_end(p->session,&sim);
    }
}

/* SelectObjects: with Alt held items come first, else only without a monster under the cursor. */
static void items_frame(struct mu_world_rt *a, void *self, uint32_t now)
{
    (void)self;
    (void)now;
    if (a->ground) {
        int alt = a->walk.frame.sample.down[0x12] != 0;
        int no_character = !(a->combat && mu_combat_pick(a->combat) >= 0);
        mu_world_items_select(a->ground, alt, no_character);
    }
}

static void items_model_raster(void *context, const mu_world_item_draw *d)
{
    mu_raster *raster = ((void **)context)[0];
    mu_world_rt *a = ((void **)context)[1];
    raster->textures = d->textures->slots;
    raster->texture_count = d->textures->count;
    raster->texture_filter = d->textures->filter;
    raster->texture_wrap = d->textures->wrap;
    mu_render_backend backend;
    mu_raster_backend(raster, &backend);
    mu_renderchar_glow glow = {d->type, d->level, d->option1, d->ext, d->has_record, d->kind_a, d->kind_b,
                               d->item_kind};
    mu_renderchar_env env;
    mu_renderchar_default_env(&env);
    env.lang = a->lang;
    env.time = a->map->time;
    env.quality = a->ground->config.quality;
    memcpy(env.glow_color, a->ground->config.glow_color, sizeof env.glow_color);
    mu_draw_options options;
    mu_draw_default_options(&options);
    options.textures = d->textures;
    mu_draw_stats ds = {0, 0, 0, 0};
    mu_renderchar_stats rs = {0, 0};
    mu_renderchar_draw_item(d->model, &glow, &env, d->light, d->alpha, &options, &backend, &ds, &rs);
    if (a->has_particles)
        mu_renderchar_skin_effects(d->model, mu_model_bone_matrices(d->model), d->type, &a->particles);
}

/* RenderItems (NATIVE-ITEMS-001); the raster's texture binding ends with the characters' passes. */
static void items_draw_soft(struct mu_world_rt *a, void *self, mu_world_draw *d)
{
    (void)self;
    mu_raster *raster = d->raster;
    if (a->ground) {
        void *context[2] = {raster, a};
        mu_world_items_draw(a->ground, items_model_raster, context);
    }
    raster->textures = NULL;
    raster->texture_count = 0;
    raster->texture_filter = NULL;
    raster->texture_wrap = NULL;
}

static void items_report_frame(const struct mu_world_rt *a, const void *self, int32_t frame)
{
    (void)self;
    if (a->ground)
        mu_world_items_report_frame(a->ground, stdout, frame);
}

static void items_report_summary(const struct mu_world_rt *a, const void *self)
{
    (void)self;
    if (a->ground)
        mu_world_items_report_summary(a->ground, stdout);
}

/* the labels over the frame (NATIVE-ITEMS-001) */
static void item_labels_draw_soft(struct mu_world_rt *a, void *self, mu_world_draw *d)
{
    (void)self;
    mu_raster *raster = d->raster;
    if (a->ground) {
        mu_world_item_label labels[MU_WORLD_ITEM_LABELS];
        int32_t n = mu_world_items_labels(a->ground, labels, MU_WORLD_ITEM_LABELS);
        for (int32_t i = 0; i < n; ++i)
            mu_world_items_label_blit(a->ground, &labels[i], raster->color, raster->width, raster->height);
    }
}

#ifndef MU_WORLD_NO_GL
static void items_gl_teardown(struct mu_world_rt *a, void *self)
{
    (void)a;
    items_part *p = self;
    for (int i = 0; i < MU_WORLD_ITEM_MODELS; ++i)
        if (p->item_gl[i].textures)
            mu_gl_release(&p->item_gl[i]);
}

/* NATIVE-ITEMS-001: RenderItems' RenderPartObject calls through the item render passes. */
static void items_model_gl(void *context, const mu_world_item_draw *d)
{
    items_part *p = context;
    mu_world_rt *a = p->rt;
    mu_gl_backend *gl = &p->item_gl[d->slot];
    if (!gl->textures)
        mu_gl_upload(gl, d->textures, 0);
    mu_render_backend backend;
    mu_gl_backend_bind(gl, &backend);
    mu_renderchar_glow glow = {d->type, d->level, d->option1, d->ext, d->has_record, d->kind_a, d->kind_b,
                               d->item_kind};
    mu_renderchar_env env;
    mu_renderchar_default_env(&env);
    env.lang = a->lang;
    env.time = a->map->time;
    env.quality = a->ground->config.quality;
    memcpy(env.glow_color, a->ground->config.glow_color, sizeof env.glow_color);
    mu_draw_options options;
    mu_draw_default_options(&options);
    options.textures = d->textures;
    mu_draw_stats ds = {0, 0, 0, 0};
    mu_renderchar_stats rs = {0, 0};
    mu_renderchar_draw_item(d->model, &glow, &env, d->light, d->alpha, &options, &backend, &ds, &rs);
    if (a->has_particles)
        mu_renderchar_skin_effects(d->model, mu_model_bone_matrices(d->model), d->type, &a->particles);
}

/* RenderItems after the characters (0x0185988d in the render scene). */
static void items_draw_gl(struct mu_world_rt *a, void *self, mu_world_draw *d)
{
    items_part *p = self;
    d->perf = mu_perf_begin(a->perf);
    if (a->ground) {
        p->rt = a;
        mu_world_items_draw(a->ground, items_model_gl, p);
        glDisable(GL_BLEND);
        glDepthMask(GL_TRUE);
        glDisable(GL_ALPHA_TEST);
    }
    mu_perf_end(a->perf, MU_PERF_ITEMS, d->perf);
}

/* The labels as a screen-space overlay (the hudPlayerName movie draws them over the 3D view). */
static void items_labels_gl(mu_world_rt *a, int32_t width, int32_t height)
{
    mu_world_item_label labels[MU_WORLD_ITEM_LABELS];
    int32_t n = mu_world_items_labels(a->ground, labels, MU_WORLD_ITEM_LABELS);
    if (!n)
        return;
    glMatrixMode(GL_PROJECTION);
    glPushMatrix();
    glLoadIdentity();
    glOrtho(0.0, (double)width, (double)height, 0.0, -1.0, 1.0);
    glMatrixMode(GL_MODELVIEW);
    glPushMatrix();
    glLoadIdentity();
    glViewport(0, 0, width, height);
    glDisable(GL_DEPTH_TEST);
    glDisable(GL_CULL_FACE);
    glDisable(GL_ALPHA_TEST);
    glEnable(GL_BLEND);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
    for (int32_t i = 0; i < n; ++i) {
        const mu_world_item_label *l = &labels[i];
        float x0 = l->anchor[0] + l->box.bg_x, y0 = l->anchor[1] + l->box.bg_y;
        glDisable(GL_TEXTURE_2D);
        glColor4f(0.0f, 0.0f, 0.0f, 0.5f);
        glBegin(GL_QUADS);
        glVertex2f(x0, y0);
        glVertex2f(x0 + l->box.bg_w, y0);
        glVertex2f(x0 + l->box.bg_w, y0 + l->box.bg_h);
        glVertex2f(x0, y0 + l->box.bg_h);
        glEnd();
        int32_t tw = l->text_width, th = l->text_height;
        if (tw <= 0 || th <= 0 || tw > 2048 || th > 256)
            continue;
        uint8_t *rgba = malloc((size_t)tw * (size_t)th * 4);
        if (!rgba || mu_world_items_label_bitmap(a->ground, l, rgba, tw, th)) {
            free(rgba);
            continue;
        }
        GLuint tex;
        glGenTextures(1, &tex);
        glBindTexture(GL_TEXTURE_2D, tex);
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, tw, th, 0, GL_RGBA, GL_UNSIGNED_BYTE, rgba);
        free(rgba);
        glEnable(GL_TEXTURE_2D);
        glTexEnvi(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_MODULATE);
        glColor4f(l->rgb[0], l->rgb[1], l->rgb[2], 1.0f);
        float tx = l->anchor[0] + l->box.text_x + 3.0f, ty = l->anchor[1] + l->box.text_y + 2.0f;
        glBegin(GL_QUADS);
        glTexCoord2f(0.0f, 0.0f);
        glVertex2f(tx, ty);
        glTexCoord2f(1.0f, 0.0f);
        glVertex2f(tx + (float)tw, ty);
        glTexCoord2f(1.0f, 1.0f);
        glVertex2f(tx + (float)tw, ty + (float)th);
        glTexCoord2f(0.0f, 1.0f);
        glVertex2f(tx, ty + (float)th);
        glEnd();
        glDeleteTextures(1, &tex);
    }
    glBindTexture(GL_TEXTURE_2D, 0);
    glDisable(GL_TEXTURE_2D);
    glDisable(GL_BLEND);
    glEnable(GL_DEPTH_TEST);
    glMatrixMode(GL_PROJECTION);
    glPopMatrix();
    glMatrixMode(GL_MODELVIEW);
    glPopMatrix();
}

/* Opens the labels' phase (the names part closes it). */
static void item_labels_draw_gl(struct mu_world_rt *a, void *self, mu_world_draw *d)
{
    (void)self;
    d->perf = mu_perf_begin(a->perf);
    if (a->ground)
        items_labels_gl(a, d->width, d->height);
}
#endif

const mu_world_part_ops mu_part_items = {
    .name = "items",
    .state_size = sizeof(items_part),
#ifndef MU_WORLD_NO_GL
    .draw_gl = items_draw_gl,
    .gl_teardown = items_gl_teardown,
#endif
    .open = items_open,
    .close = items_close,
    .pre_tick = items_pre_tick,
    .tick = items_tick,
    .frame = items_frame,
    .draw_soft = items_draw_soft,
    .report_frame = items_report_frame,
    .report_summary = items_report_summary,
};

const mu_world_part_ops mu_part_item_labels = {
    .name = "item_labels",
#ifndef MU_WORLD_NO_GL
    .draw_gl = item_labels_draw_gl,
#endif
    .draw_soft = item_labels_draw_soft,
};
