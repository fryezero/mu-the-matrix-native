/* Game-side pieces of the GFx interface over the native world (NATIVE-GFX-003);
 * see world_gfx_game.h. */
#define _POSIX_C_SOURCE 200809L
#include "world_gfx_game.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifndef WG_SKILLS_ONLY   /* tests build the skill decoder alone */
#ifdef __APPLE__
#define GL_SILENCE_DEPRECATION 1
#include <OpenGL/gl.h>
#include <OpenGL/glext.h>
#else
#define GL_GLEXT_PROTOTYPES 1
#include <GL/gl.h>
#include <GL/glext.h>
#endif

#include "../core/mu_bmd.h"
#include "../core/mu_character.h"
#include "../core/mu_lang.h"
#include "../core/mu_hud.h"
#include "../core/mu_model.h"
#include "../core/mu_particles.h"
#include "../core/mu_renderchar.h"
#include "../core/mu_scene.h"
#include "../core/mu_textures.h"
#include "../viewer/gl_backend.h"
#include "../../reconstructed/items/ground_items.h"

/* Item render info scale factor (NATIVE-HUD-001's authored calibration of
 * itemtrsdata's 0.001..0.004 scales to the client's pixel-orthographic pass). */
#define ITEM_SCALE_FACTOR 200.0f
#define MAX_MODELS 64

typedef struct item_model {
    int32_t code;
    int32_t type;               /* the drawn model type (code + 0xae6, or RenderObjectScreen's remap) */
    int state;                  /* 0 unused, 1 loaded, -1 failed */
    int armour;                 /* skinned against the Player mannequin's shared bones */
    /* the item's animation state (item +0x108) for InvenItemAnimation codes: prior action +2, frame +4,
     * prior frame +8 (RenderObjectScreen's tick advances it) */
    uint16_t anim_prior_action;
    float anim_frame, anim_prior_frame;
    mu_hud_item info;           /* record, model path, size */
    mu_bmd bmd;
    mu_model model;
    mu_textures textures;
    mu_gl_backend gl;
} item_model;

struct wg_items {
    mu_lang *lang;
    char root[1024];
    int have_root;
    mu_data_table items;
    int have_items;
    mu_hud_trs_table trs;
    int have_trs;
    item_model models[MAX_MODELS];
    mu_character *mannequin;    /* the Player model RenderObjectScreen poses armour parts on */
    int mannequin_failed;
    double time_ms;
    long drawn, missing, icons;
    GLuint fbo, color, depth;
    int fbo_w, fbo_h, fbo_failed;
    mu_world_particles *skin_particles;
    mu_gl_backend skin_gl;
};

wg_items *wg_items_open(const char *game_root)
{
    wg_items *w = calloc(1, sizeof *w);
    if (!w)
        return NULL;
    w->lang = mu_lang_load_default();
    if (game_root && game_root[0]) {
        snprintf(w->root, sizeof w->root, "%s", game_root);
        w->have_root = 1;
        char path[2048];
        snprintf(path, sizeof path, "%s/Data/Local/item.bmd", game_root);
        w->have_items = mu_data_load(path, NULL, &w->items) == 0 && w->items.result.status == 0;
        snprintf(path, sizeof path, "%s/Data/Local/itemtrsdata.bmd", game_root);
        w->have_trs = mu_hud_trs_load(path, &w->trs) == 0;
    }
    return w;
}

static void model_free(item_model *m)
{
    if (m->state == 1) {
        mu_gl_release(&m->gl);
        mu_textures_free(&m->textures);
        mu_model_free(&m->model);
        mu_bmd_free(&m->bmd);
    }
    memset(m, 0, sizeof *m);
}

void wg_items_close(wg_items *w)
{
    if (!w)
        return;
    for (int i = 0; i < MAX_MODELS; i++)
        model_free(&w->models[i]);
    if (w->skin_particles) {
        mu_gl_release(&w->skin_gl);
        mu_world_particles_close(w->skin_particles);
        free(w->skin_particles);
    }
    if (w->mannequin) {
        mu_character_free(w->mannequin);
        free(w->mannequin);
    }
    if (w->have_items)
        mu_data_free(&w->items);
    if (w->have_trs)
        mu_hud_trs_free(&w->trs);
    if (w->fbo) {
        glDeleteFramebuffersEXT(1, &w->fbo);
        glDeleteTextures(1, &w->color);
        glDeleteRenderbuffersEXT(1, &w->depth);
    }
    mu_lang_free(w->lang);
    free(w);
}

void wg_items_set_time(wg_items *w, double time_ms)
{
    if (w)
        w->time_ms = time_ms;
}

void wg_items_counts(const wg_items *w, long *drawn, long *missing, long *icons)
{
    *drawn = w ? w->drawn : 0;
    *missing = w ? w->missing : 0;
    *icons = w ? w->icons : 0;
}

static int is_armour_type(int32_t type)
{
    return type >= 0x18e6 && type < 0x22e6;   /* RenderObjectScreen poses the Player model 0xa91 for these */
}

static mu_character *mannequin(wg_items *w)
{
    if (w->mannequin || w->mannequin_failed)
        return w->mannequin;
    char path[2048], error[256];
    snprintf(path, sizeof path, "%s/Data/Player/Player.bmd", w->root);
    mu_model_params p;
    mu_model_default_params(&p);
    w->mannequin = calloc(1, sizeof *w->mannequin);
    if (!w->mannequin || mu_character_init(w->mannequin, path, &p, error, sizeof error)) {
        free(w->mannequin);
        w->mannequin = NULL;
        w->mannequin_failed = 1;
    }
    return w->mannequin;
}

/* The model of an item code drawn as `type`, loaded once (Item.bmd record -> model file, NATIVE-DATA-002's
 * model getter; models outside Item.bmd from the item-model loader 0x0183220e's table, NATIVE-FIDELITY-001;
 * textures with the effect specials). */
static item_model *model_for(wg_items *w, int32_t code, int32_t type)
{
    item_model *free_slot = NULL;
    for (int i = 0; i < MAX_MODELS; i++) {
        if (w->models[i].state && w->models[i].code == code && w->models[i].type == type)
            return w->models[i].state == 1 ? &w->models[i] : NULL;
        if (!w->models[i].state && !free_slot)
            free_slot = &w->models[i];
    }
    if (!free_slot || !w->have_root)
        return NULL;
    item_model *m = free_slot;
    memset(m, 0, sizeof *m);
    m->code = code;
    m->type = type;
    m->state = -1;
    mu_hud_inventory *scratch = malloc(sizeof *scratch);
    if (!scratch)
        return NULL;
    mu_hud_inventory_init(scratch);
    int k = mu_hud_inventory_add(scratch, w->have_items ? &w->items : NULL, w->root, code, 0, 1, 1);
    if (k >= 0)
        m->info = scratch->items[k];
    free(scratch);
    char error[256];
    if (type != code + 0xae6)
        k = mu_hud_item_model_path(w->have_items ? &w->items : NULL, w->root, type,
                                   m->info.model_path, sizeof m->info.model_path) ? 0 : -1;
    if (k < 0 || !m->info.model_path[0] || mu_bmd_load_file(m->info.model_path, &m->bmd, error, sizeof error) != MU_BMD_OK)
        return NULL;
    mu_model_params params;
    mu_model_default_params(&params);
    if (mu_model_init(&m->model, &m->bmd, &params, error, sizeof error) != MU_MODEL_OK) {
        mu_bmd_free(&m->bmd);
        return NULL;
    }
    if (is_armour_type(type)) {   /* a body part: skinned against the Player skeleton's shared bones */
        mu_character *man = mannequin(w);
        if (!man) {
            mu_model_free(&m->model);
            mu_bmd_free(&m->bmd);
            return NULL;
        }
        mu_model_relocate(&m->model, &m->bmd);
        mu_model_share(&m->model, man->shared_bones, man->shared_root, man->shared_quaternions);
        m->armour = 1;
    }
    char directory[1024];
    snprintf(directory, sizeof directory, "%s", m->info.model_path);
    char *slash = strrchr(directory, '/');
    if (slash)
        slash[1] = 0;
    mu_textures_load(&m->textures, &m->bmd, directory);
    if (m->textures.missing > 0) {
        /* The installed armour-part item models (Data/Item/HelmMale02.bmd, ...)
         * have their textures in Data/Player, next to the character parts
         * (installed files; the client's texture path for them is not
         * reconstructed). */
        char player[1100];
        snprintf(player, sizeof player, "%s/Data/Player/", w->root);
        mu_textures alt;
        memset(&alt, 0, sizeof alt);
        if (mu_textures_load(&alt, &m->bmd, player) == 0 && alt.missing < m->textures.missing) {
            mu_textures_free(&m->textures);
            m->textures = alt;
        } else {
            mu_textures_free(&alt);
        }
    }
    mu_gl_upload(&m->gl, &m->textures, 0);
    m->state = 1;
    return m;
}

/* Slot wrapper + RenderItem3D (reconstructed/hud) for one item of the pass. */
static int place_item(const wg_items *w, const mu_gfx_item_draw *d, int32_t stage_w,
                      int32_t stage_h, mu_item3d_out *out)
{
    float rx = mu_gfx_rate_x(stage_w), ry = mu_gfx_rate_y(stage_h);
    mu_slot_wrapper_in win;
    memset(&win, 0, sizeof win);
    win.code = d->code;
    win.level_word = d->has_options ? d->level_word : d->level << 3;
    win.set_bits = (uint8_t)d->set_bits;
    win.excellent = (uint8_t)d->excellent;
    win.element = d->has_options ? d->element : -1;
    win.x = d->slot[0];
    win.y = d->slot[1];
    win.w = d->slot[2];
    win.h = d->slot[3];
    win.a1c = d->page_type;
    win.a20 = (uint8_t)d->page_flag;
    win.a28 = (uint8_t)d->type8_seen;
    win.a2c = (uint32_t)d->frame_id;
    win.a38 = -1;
    win.a40 = 1;
    win.frame_active = 1;
    win.cursor_in = (uint8_t)d->select;
    mu_item3d_in sys;
    memset(&sys, 0, sizeof sys);
    sys.cursor_in = win.cursor_in;
    mu_hud_trs_find(w->have_trs ? &w->trs : NULL, d->code, ITEM_SCALE_FACTOR, &sys.trs);
    mu_item record;
    if (w->have_items && mu_item_find(&w->items, (uint32_t)d->code, &record) == 0) {
        sys.kind_b_6a = record.attributes.kind_b == 0x6a;
        sys.kind_a_22 = record.attributes.kind_a == 0x22;
    }
    sys.time = (float)w->time_ms;
    sys.frame_scale = d->frame_scale > 0 ? d->frame_scale : 1.0f;
    sys.rate_x = rx;
    sys.rate_y = ry;
    mu_slot_wrapper_out wout;
    mu_slot_wrapper(1, &win, &sys, &wout);
    return mu_item3d(&wout.item3d, out);
}

/* RenderObjectScreen 0x016c2d82 (reconstructed/hud mu_hud_object_screen, verified): the pose model, its height
 * and action, then RenderPartObject with the object's light (1, 1, 1), lighting flag cleared, light terms
 * 0.4/0.8/0.2. */
static void ros_inputs(wg_items *w, const item_model *m, const mu_gfx_item_draw *d, const mu_item3d_out *out,
                       mu_hud_ros_in *in)
{
    memset(in, 0, sizeof *in);
    in->type = out->model;
    in->level_word = out->level_word;
    in->excellent = out->excellent;
    in->set_bits = out->set_bits;
    memcpy(in->position, out->position, sizeof in->position);
    in->select = out->select;
    in->held = (uint8_t)(d->held != 0);
    in->a2c = out->a2c;
    in->a30 = out->a30;
    in->scale = out->scale;
    in->has_state = 1;                       /* the slot wrapper passes item +0x108 */
    in->state_prior_action = m->anim_prior_action;
    in->state_frame = m->anim_frame;
    in->state_prior_frame = m->anim_prior_frame;
    in->tick = 1;                            /* the slot pass's wrapper argument a40 = 1 */
    in->time = (float)w->time_ms;
    mu_item record;
    if (w->have_items && mu_item_model(&w->items, out->model, &record) == 1) {
        in->has_record = 1;
        in->kind_a = record.attributes.kind_a;
        in->item_kind = record.attributes.type;
    }
    /* InvenItemAnimation (Lang.mpr, MU_LANG_DIR): absent without the tables */
    in->anim_present = mu_lang_inven_anim(w->lang, d->code, &in->anim_action, &in->anim_speed);
    in->pose_model_exists = 1;
    in->object_alpha = 1.0f;                 /* ItemObjectAttribute's alpha (1 for these items) */
}

static int skin_backend(void *context, const mu_world_particles *p, mu_render_backend *out)
{
    wg_items *w = context;
    if (!w->skin_gl.textures)
        mu_gl_upload(&w->skin_gl, &p->bitmaps, 0);
    mu_gl_backend_bind(&w->skin_gl, out);
    return 0;
}

static void draw_skin(wg_items *w, const mu_model *model, int32_t type)
{
    if (type != 0x389c && type != 0x389d)
        return;
    if (!w->skin_particles) {
        char error[256];
        mu_world_particles *p = calloc(1, sizeof *p);
        if (!p)
            return;
        if (mu_world_particles_open(p, w->have_root ? w->root : NULL, NULL, 0, 1,
                                    !w->have_root, error, sizeof error)) {
            free(p);
            return;
        }
        w->skin_particles = p;
    }
    w->skin_particles->world_time = (float)w->time_ms;
    mu_renderchar_skin_effects(model, mu_model_bone_matrices(model), type, w->skin_particles);
    /* Consume only this icon's one-frame sprites, in its current projection/FBO. */
    float view[16];
    glGetFloatv(GL_MODELVIEW_MATRIX, view);
    const mu_world_particles_target target = {w, skin_backend};
    mu_world_particles_draw(w->skin_particles, view, &target);
}

static void draw_model(wg_items *w, item_model *m, const mu_gfx_item_draw *d, const mu_item3d_out *out,
                       int32_t stage_h)
{
    (void)stage_h;
    mu_hud_ros_in in;
    mu_hud_ros_out ros;
    ros_inputs(w, m, d, out, &in);
    mu_hud_object_screen(&in, &ros);
    if (!ros.drawn)
        return;
    float angles[3] = {out->angle[0], out->angle[1], out->angle[2]};
    if (ros.spin)
        angles[1] = ros.spin_angle;          /* the hovered item spins */
    mu_model_params params = m->model.params;
    params.lighting = ros.lighting;          /* RenderPartObject copies object +5 (cleared) to model +0x50 */
    params.light_ambient = 0.4f;             /* RenderPartObject's Transform constants (0x017e6840) */
    params.light_scale = 0.8f;
    params.light_minimum = 0.2f;
    params.body_scale = ros.scale;
    memcpy(params.origin, ros.position, sizeof params.origin);
    if (m->armour) {
        /* the Player model posed at the pose height and action, translate 0 (Animation's last argument), then
         * the part skinned with translate 1 at the object's position and scale (as RenderItems' armour) */
        mu_character *man = w->mannequin;
        if (!man) {
            w->missing++;
            return;
        }
        for (int q = 0; q < 3; ++q) {
            man->params.position[q] = ros.position[q];
            man->params.angles[q] = angles[q];
        }
        man->params.head[0] = man->params.head[1] = 0.0f;
        man->params.scale = ros.scale;
        mu_model_params pp = man->player.params;
        pp.height = ros.height;
        mu_model_apply_params(&man->player, &pp);
        mu_character_set_state(man, ros.action, ros.anim_frame, ros.anim_prior_frame, ros.anim_prior_action);
        if (mu_character_update(man) != MU_MODEL_OK) {
            w->missing++;
            return;
        }
        for (int q = 0; q < 3; ++q)
            params.angles[q] = 0.0f;
        params.head_angles[0] = params.head_angles[1] = 0.0f;
        params.transform_translate = 1;
        params.vertex_scale = 0.0f;
        params.height = 0.0f;
        mu_model_apply_params(&m->model, &params);
        if (mu_model_transform_all(&m->model) != MU_MODEL_OK) {
            w->missing++;
            return;
        }
    } else {
        memcpy(params.angles, angles, sizeof params.angles);
        params.height = ros.height;
        mu_model_apply_params(&m->model, &params);
        mu_model_set_state(&m->model, ros.action, ros.anim_frame, ros.anim_prior_frame, ros.anim_prior_action);
        if (ros.ticked) {
            /* the tick 0x012b4dd3 on the item's animation state at the record's speed */
            uint8_t loop = 0;
            mu_model_tick(&m->model, ros.tick_speed, &loop);
            m->anim_frame = mu_model_frame(&m->model);
            m->anim_prior_frame = mu_model_prior_frame(&m->model);
            m->anim_prior_action = mu_model_prior_action(&m->model);
            mu_model_set_state(&m->model, ros.action, ros.anim_frame, ros.anim_prior_frame, ros.anim_prior_action);
        }
        if (mu_model_update(&m->model) != MU_MODEL_OK) {
            w->missing++;
            return;
        }
    }
    mu_renderchar_glow glow;
    memset(&glow, 0, sizeof glow);
    glow.type = ros.render_type;
    glow.level = d->level;
    glow.option1 = d->excellent;
    if (m->info.has_record) {
        glow.has_record = 1;
        glow.kind_a = m->info.record.attributes.kind_a;
        glow.kind_b = m->info.record.attributes.kind_b;
        glow.item_kind = m->info.record.attributes.type;
    }
    mu_renderchar_env env;
    mu_renderchar_default_env(&env);
    env.lang = w->lang;
    env.time = (float)w->time_ms;
    env.particles = w->skin_particles;
    mu_draw_options draw;
    mu_draw_default_options(&draw);
    draw.textures = &m->textures;
    mu_render_backend backend;
    mu_gl_backend_bind(&m->gl, &backend);
    mu_draw_stats stats = {0, 0, 0, 0};
    mu_renderchar_stats rstats = {0, 0};
    if (getenv("MU_GFX_PLAIN_ITEMS"))   /* debug: one plain textured body pass */
        mu_scene_draw_model(&m->model, &draw, &backend, &stats);
    else {
        mu_renderchar_draw_item(&m->model, &glow, &env, ros.light, d->alpha > 0 ? d->alpha : 1.0f, &draw, &backend,
                                &stats, &rstats);
        draw_skin(w, &m->model, ros.render_type);
    }
    w->drawn++;
}

/* The item pass state of 0x00abfcca: orthographic projection over the
 * stage, depth on and cleared, white colour with the frame alpha. */
static void pass_begin(int32_t stage_w, int32_t stage_h)
{
    float projection[16];
    mu_hud_item_projection(stage_w, stage_h, projection);
    glMatrixMode(GL_PROJECTION);
    glLoadMatrixf(projection);
    glMatrixMode(GL_MODELVIEW);
    glLoadIdentity();
    glShadeModel(GL_SMOOTH);
    glDepthFunc(GL_LEQUAL);
    glAlphaFunc(GL_GREATER, 0.25f);
    glDisable(GL_LIGHTING);
    glDisable(GL_FOG);
    glDisable(GL_SCISSOR_TEST);
    glTexEnvi(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_MODULATE);
    glEnable(GL_DEPTH_TEST);
    glDepthMask(GL_TRUE);
    glClear(GL_DEPTH_BUFFER_BIT);
    glFrontFace(GL_CCW);
    glColor4f(1, 1, 1, 1);
}

void wg_items_draw(void *user, const mu_gfx_item_draw *items, int n, int32_t stage_w, int32_t stage_h)
{
    wg_items *w = user;
    if (!w || n <= 0)
        return;
    pass_begin(stage_w, stage_h);
    for (int i = 0; i < n; i++) {
        mu_item3d_out out;
        if (place_item(w, &items[i], stage_w, stage_h, &out) != MU_ITEM3D_DRAW) {
            w->missing++;
            continue;
        }
        item_model *m = model_for(w, items[i].code, out.model);
        if (!m) {
            w->missing++;
            continue;
        }
        /* RenderObjectScreen may draw another model (0x26f2 by level: 0x3890/0x3891) */
        mu_hud_ros_in in;
        mu_hud_ros_out ros;
        ros_inputs(w, m, &items[i], &out, &in);
        mu_hud_object_screen(&in, &ros);
        if (ros.render_type != m->type) {
            item_model *other = model_for(w, items[i].code, ros.render_type);
            if (!other) {
                w->missing++;
                continue;
            }
            m = other;
        }
        draw_model(w, m, &items[i], &out, stage_h);
    }
}

static int fbo_ready(wg_items *w, int32_t width, int32_t height, GLuint previous)
{
    if (w->fbo_failed)
        return 0;
    if (w->fbo && w->fbo_w == width && w->fbo_h == height)
        return 1;
    if (w->fbo) {
        glDeleteFramebuffersEXT(1, &w->fbo);
        glDeleteTextures(1, &w->color);
        glDeleteRenderbuffersEXT(1, &w->depth);
        w->fbo = 0;
    }
    glGenTextures(1, &w->color);
    glBindTexture(GL_TEXTURE_2D, w->color);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, NULL);
    glBindTexture(GL_TEXTURE_2D, 0);
    glGenRenderbuffersEXT(1, &w->depth);
    glBindRenderbufferEXT(GL_RENDERBUFFER_EXT, w->depth);
    glRenderbufferStorageEXT(GL_RENDERBUFFER_EXT, GL_DEPTH_COMPONENT24, width, height);
    glBindRenderbufferEXT(GL_RENDERBUFFER_EXT, 0);
    glGenFramebuffersEXT(1, &w->fbo);
    glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, w->fbo);
    glFramebufferTexture2DEXT(GL_FRAMEBUFFER_EXT, GL_COLOR_ATTACHMENT0_EXT, GL_TEXTURE_2D, w->color, 0);
    glFramebufferRenderbufferEXT(GL_FRAMEBUFFER_EXT, GL_DEPTH_ATTACHMENT_EXT, GL_RENDERBUFFER_EXT, w->depth);
    int ok = glCheckFramebufferStatusEXT(GL_FRAMEBUFFER_EXT) == GL_FRAMEBUFFER_COMPLETE_EXT;
    glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, previous);   /* the host may render into an FBO itself */
    if (!ok) {
        w->fbo_failed = 1;
        return 0;
    }
    w->fbo_w = width;
    w->fbo_h = height;
    return 1;
}

int wg_items_icons(void *user, const mu_gfx_item_draw *items, int n, uint8_t *rgba, int32_t width, int32_t height)
{
    wg_items *w = user;
    if (!w || !w->have_root)
        return 1;
    GLint previous = 0, viewport[4];
    glGetIntegerv(GL_FRAMEBUFFER_BINDING_EXT, &previous);
    if (!fbo_ready(w, width, height, (GLuint)previous))
        return 1;
    glGetIntegerv(GL_VIEWPORT, viewport);
    glPushAttrib(GL_ALL_ATTRIB_BITS);
    glMatrixMode(GL_PROJECTION);
    glPushMatrix();
    glMatrixMode(GL_MODELVIEW);
    glPushMatrix();
    glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, w->fbo);
    glViewport(0, 0, width, height);
    glDisable(GL_SCISSOR_TEST);
    glClearColor(0, 0, 0, 0);
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
    /* The image as a screen of its own size: the slot rectangles are in its
     * 640 x 480 units, the same RenderItem3D path places the models. */
    long before = w->drawn;
    wg_items_draw(w, items, n, width, height);
    glPixelStorei(GL_PACK_ALIGNMENT, 1);
    glReadPixels(0, 0, width, height, GL_RGBA, GL_UNSIGNED_BYTE, rgba);   /* bottom-up rows, as GFx sees the target */
    glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, (GLuint)previous);
    glMatrixMode(GL_PROJECTION);
    glPopMatrix();
    glMatrixMode(GL_MODELVIEW);
    glPopMatrix();
    glPopAttrib();
    glViewport(viewport[0], viewport[1], viewport[2], viewport[3]);
    w->icons += w->drawn - before;
    return w->drawn > before ? 0 : 1;
}

#endif /* WG_SKILLS_ONLY */

/* ---- skills ----------------------------------------------------------------------------- */

int wg_skills_decode(const uint8_t *data, size_t size, mu_gfx_skill *out, int max)
{
    static const uint8_t KEY[3] = {0xfc, 0xcf, 0xab};
    enum { RECORD = 120 };
    if (!data || size < RECORD + 4 || (size - 4) % RECORD)
        return 0;
    int n = 0;
    size_t records = (size - 4) / RECORD;
    for (size_t i = 1; i < records && n < max; i++) {
        uint8_t r[RECORD];
        for (int k = 0; k < RECORD; k++)
            r[k] = data[i * RECORD + (size_t)k] ^ KEY[k % 3];
        if (!r[0])
            continue;   /* unnamed record: no skill */
        mu_gfx_skill *s = &out[n++];
        memset(s, 0, sizeof *s);
        s->index = (int32_t)i;
        s->icon = r[74] | r[75] << 8;
        s->mastery = r[54];
        s->use_type = r[55];
        snprintf(s->name, sizeof s->name, "Skill %d", (int)i);
    }
    return n;
}

int wg_skills_load(const char *game_root, mu_gfx_skill *out, int max)
{
    if (!game_root)
        return 0;
    char path[2048];
    snprintf(path, sizeof path, "%s/Data/Local/skill.bmd", game_root);
    FILE *f = fopen(path, "rb");
    if (!f)
        return 0;
    uint8_t *buf = malloc(1 << 20);
    size_t size = buf ? fread(buf, 1, 1 << 20, f) : 0;
    fclose(f);
    int n = wg_skills_decode(buf, size, out, max);
    free(buf);
    return n;
}
