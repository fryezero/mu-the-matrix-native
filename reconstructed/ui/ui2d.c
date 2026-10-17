/* Reconstructed 2D interface routines (NATIVE-UI-001).  See ui2d.h. */
#include "ui2d.h"

#include <math.h>
#include <string.h>

#define GL_PROJECTION 0x1701u
#define GL_MODELVIEW 0x1700u
#define GL_TRIANGLE_FAN 6u
#define GL_TEXTURE_2D 0x0de1u
#define GL_DEPTH_TEST 0x0b71u
#define GL_CULL_FACE 0x0b44u
#define GL_ALPHA_TEST 0x0bc0u
#define GL_BLEND 0x0be2u
#define GL_FOG 0x0b60u

static uint32_t fbits(float value)
{
    uint32_t word;
    memcpy(&word, &value, 4);
    return word;
}

static void emit(mu_ui_state *state, int op, const uint32_t *words, int count)
{
    if (state->sink.call)
        state->sink.call(state->sink.user, op, words, count, NULL, 0);
}

static void emit1(mu_ui_state *state, int op, uint32_t a)
{
    emit(state, op, &a, 1);
}

static void emit2(mu_ui_state *state, int op, uint32_t a, uint32_t b)
{
    uint32_t words[2] = {a, b};
    emit(state, op, words, 2);
}

static void emitf(mu_ui_state *state, int op, int count, float a, float b, float c, float d)
{
    uint32_t words[4] = {fbits(a), fbits(b), fbits(c), fbits(d)};
    emit(state, op, words, count);
}

static void emitd4(mu_ui_state *state, int op, double a, double b, double c, double d)
{
    double values[4] = {a, b, c, d};
    uint32_t words[8];
    memcpy(words, values, sizeof words);   /* little-endian: low word first */
    emit(state, op, words, 8);
}

/* cvtsi2sd of a uint32 global plus the 2^32 correction table at 0x01bd3050,
 * then cvtsd2ss: exactly (float)(double)value. */
static float ufloat(uint32_t value)
{
    return (float)(double)value;
}

int32_t mu_ui_cvtt(float value)
{
    if (!(value > -2147483904.0f && value < 2147483648.0f))
        return INT32_MIN;            /* x86 integer indefinite */
    return (int32_t)value;
}

void mu_ui_state_init(mu_ui_state *state, uint32_t window_width, uint32_t window_height)
{
    mu_ui_sink sink = state->sink;
    mu_ui_lookup lookup = state->lookup;
    void *lookup_user = state->lookup_user;
    memset(state, 0, sizeof *state);
    state->sink = sink;
    state->lookup = lookup;
    state->lookup_user = lookup_user;
    state->window_width = window_width;
    state->window_height = window_height;
    state->bound_texture = -1;
    state->texture_2d = 1;
    state->depth_test = 1;
    state->cull_face = 1;
    state->depth_mask = 1;
    state->fov = 35.0f;
    state->znear = 20.0f;
    state->zfar = 2000.0f;
    state->screen_rate_x = (float)window_width / 640.0f;
    state->screen_rate_y = (float)window_height / 480.0f;
}

float mu_ui_convert_x(const mu_ui_state *state, float x)
{
    return ufloat(state->window_width) * x / 640.0f;
}

float mu_ui_convert_y(const mu_ui_state *state, float y)
{
    return ufloat(state->window_height) * y / 480.0f;
}

/* ---- state wrappers --------------------------------------------------- */

static void enable_flag(mu_ui_state *state, uint8_t *flag, uint32_t cap)
{
    if (!*flag) {
        *flag = 1;
        emit1(state, MU_GL_ENABLE, cap);
    }
}

static void disable_flag(mu_ui_state *state, uint8_t *flag, uint32_t cap)
{
    if (*flag) {
        *flag = 0;
        emit1(state, MU_GL_DISABLE, cap);
    }
}

void mu_ui_enable_depth_test(mu_ui_state *state) { enable_flag(state, &state->depth_test, GL_DEPTH_TEST); }
void mu_ui_disable_depth_test(mu_ui_state *state) { disable_flag(state, &state->depth_test, GL_DEPTH_TEST); }
void mu_ui_enable_cull_face(mu_ui_state *state) { enable_flag(state, &state->cull_face, GL_CULL_FACE); }
void mu_ui_disable_cull_face(mu_ui_state *state) { disable_flag(state, &state->cull_face, GL_CULL_FACE); }

void mu_ui_enable_depth_mask(mu_ui_state *state)
{
    if (!state->depth_mask) {
        state->depth_mask = 1;
        emit1(state, MU_GL_DEPTHMASK, 1);
    }
}

void mu_ui_disable_depth_mask(mu_ui_state *state)
{
    if (state->depth_mask) {
        state->depth_mask = 0;
        emit1(state, MU_GL_DEPTHMASK, 0);
    }
}

void mu_ui_disable_texture(mu_ui_state *state, int alpha_test)
{
    mu_ui_enable_depth_mask(state);
    if ((uint8_t)alpha_test == 1)
        enable_flag(state, &state->alpha_test, GL_ALPHA_TEST);
    else
        disable_flag(state, &state->alpha_test, GL_ALPHA_TEST);
    disable_flag(state, &state->texture_2d, GL_TEXTURE_2D);
}

void mu_ui_disable_alpha_blend(mu_ui_state *state)
{
    if (state->blend_mode != 0) {
        state->blend_mode = 0;
        emit1(state, MU_GL_DISABLE, GL_BLEND);
    }
    mu_ui_enable_cull_face(state);
    mu_ui_enable_depth_mask(state);
    disable_flag(state, &state->alpha_test, GL_ALPHA_TEST);
    enable_flag(state, &state->texture_2d, GL_TEXTURE_2D);
    if (state->fog)
        emit1(state, MU_GL_ENABLE, GL_FOG);
}

void mu_ui_enable_alpha_test(mu_ui_state *state, int depth_mask)
{
    if (state->blend_mode != 2) {
        state->blend_mode = 2;
        emit1(state, MU_GL_ENABLE, GL_BLEND);
        emit2(state, MU_GL_BLENDFUNC, 0x302, 0x303);   /* SRC_ALPHA, ONE_MINUS_SRC_ALPHA */
    }
    mu_ui_disable_cull_face(state);
    if ((uint8_t)depth_mask)
        mu_ui_enable_depth_mask(state);
    enable_flag(state, &state->alpha_test, GL_ALPHA_TEST);
    enable_flag(state, &state->texture_2d, GL_TEXTURE_2D);
    if (state->fog)
        emit1(state, MU_GL_ENABLE, GL_FOG);
}

void mu_ui_enable_alpha_blend(mu_ui_state *state)
{
    if (state->blend_mode != 3) {
        state->blend_mode = 3;
        emit1(state, MU_GL_ENABLE, GL_BLEND);
        emit2(state, MU_GL_BLENDFUNC, 1, 1);           /* ONE, ONE */
    }
    mu_ui_disable_cull_face(state);
    mu_ui_disable_depth_mask(state);
    disable_flag(state, &state->alpha_test, GL_ALPHA_TEST);
    enable_flag(state, &state->texture_2d, GL_TEXTURE_2D);
    if (state->fog)
        emit1(state, MU_GL_DISABLE, GL_FOG);
}

void mu_ui_bind_texture(mu_ui_state *state, int32_t index)
{
    if (state->bound_texture == index)
        return;
    state->bound_texture = index;
    if (index >= 0) {
        mu_ui_bitmap *bitmap = state->lookup ? state->lookup(state->lookup_user, (uint32_t)index) : NULL;
        emit2(state, MU_GL_BINDTEXTURE, GL_TEXTURE_2D, bitmap ? bitmap->texture : 0);
    } else {
        emit2(state, MU_GL_BINDTEXTURE, GL_TEXTURE_2D, (uint32_t)(index * -1));
    }
}

/* ---- projection -------------------------------------------------------- */

void mu_ui_begin_bitmap(mu_ui_state *state)
{
    uint32_t viewport[4] = {0, 0, state->window_width, state->window_height};
    float aspect;
    emit1(state, MU_GL_MATRIXMODE, GL_PROJECTION);
    emit(state, MU_GL_PUSHMATRIX, NULL, 0);
    emit(state, MU_GL_LOADIDENTITY, NULL, 0);
    emit(state, MU_GL_VIEWPORT, viewport, 4);
    aspect = ufloat(state->window_width) / ufloat(state->window_height);
    emitd4(state, MU_GLU_PERSPECTIVE, (double)state->fov, (double)aspect, (double)state->znear,
           (double)state->zfar);
    emit(state, MU_GL_LOADIDENTITY, NULL, 0);
    emitd4(state, MU_GLU_ORTHO2D, 0.0, (double)state->window_width, 0.0, (double)state->window_height);
    emit1(state, MU_GL_MATRIXMODE, GL_MODELVIEW);
    emit(state, MU_GL_PUSHMATRIX, NULL, 0);
    emit(state, MU_GL_LOADIDENTITY, NULL, 0);
    mu_ui_disable_depth_test(state);
}

void mu_ui_end_bitmap(mu_ui_state *state)
{
    emit1(state, MU_GL_MATRIXMODE, GL_MODELVIEW);
    emit(state, MU_GL_POPMATRIX, NULL, 0);
    emit1(state, MU_GL_MATRIXMODE, GL_PROJECTION);
    emit(state, MU_GL_POPMATRIX, NULL, 0);
}

/* ---- quads -------------------------------------------------------------- */

void mu_ui_render_bitmap(mu_ui_state *state, int32_t texture, float x, float y, float width, float height,
                         float u, float v, float u_width, float v_height, int scale, int start_scale,
                         float alpha)
{
    float p[4][2], c[4][2];
    int i;
    if ((uint8_t)start_scale) {
        x = mu_ui_convert_x(state, x);
        y = mu_ui_convert_y(state, y);
    }
    if ((uint8_t)scale) {
        width = mu_ui_convert_x(state, width);
        height = mu_ui_convert_y(state, height);
    }
    mu_ui_bind_texture(state, texture);
    y = ufloat(state->window_height) - y;
    p[0][0] = x;          p[0][1] = y;
    p[1][0] = x;          p[1][1] = y - height;
    p[2][0] = x + width;  p[2][1] = y - height;
    p[3][0] = x + width;  p[3][1] = y;
    c[0][0] = u;           c[0][1] = v;
    c[3][0] = u + u_width; c[3][1] = v;
    c[2][0] = u + u_width; c[2][1] = v + v_height;
    c[1][0] = u;           c[1][1] = v + v_height;
    emit1(state, MU_GL_BEGIN, GL_TRIANGLE_FAN);
    for (i = 0; i < 4; ++i) {
        if (alpha > 0.0f)
            emitf(state, MU_GL_COLOR4F, 4, 1.0f, 1.0f, 1.0f, alpha);
        emitf(state, MU_GL_TEXCOORD2F, 2, c[i][0], c[i][1], 0, 0);
        emitf(state, MU_GL_VERTEX2F, 2, p[i][0], p[i][1], 0, 0);
        if (alpha > 0.0f)
            emitf(state, MU_GL_COLOR4F, 4, 1.0f, 1.0f, 1.0f, 1.0f);
    }
    emit(state, MU_GL_END, NULL, 0);
}

void mu_ui_render_color(mu_ui_state *state, float x, float y, float width, float height, float alpha,
                        int32_t mode)
{
    float p[4][2];
    int i;
    mu_ui_disable_texture(state, 0);
    x = mu_ui_convert_x(state, x);
    y = mu_ui_convert_y(state, y);
    width = mu_ui_convert_x(state, width);
    height = mu_ui_convert_y(state, height);
    y = ufloat(state->window_height) - y;
    p[0][0] = x;          p[0][1] = y;
    p[1][0] = x;          p[1][1] = y - height;
    p[2][0] = x + width;  p[2][1] = y - height;
    p[3][0] = x + width;  p[3][1] = y;
    emit1(state, MU_GL_BEGIN, GL_TRIANGLE_FAN);
    for (i = 0; i < 4; ++i) {
        if (alpha > 0.0f) {
            if (mode == 0)
                emitf(state, MU_GL_COLOR4F, 4, 1.0f, 1.0f, 1.0f, alpha);
            else if (mode == 1)
                emitf(state, MU_GL_COLOR4F, 4, 0.0f, 0.0f, 0.0f, alpha);
        }
        emitf(state, MU_GL_VERTEX2F, 2, p[i][0], p[i][1], 0, 0);
        if (alpha > 0.0f)
            emitf(state, MU_GL_COLOR4F, 4, 1.0f, 1.0f, 1.0f, 1.0f);
    }
    emit(state, MU_GL_END, NULL, 0);
}

void mu_ui_end_render_color(mu_ui_state *state)
{
    emitf(state, MU_GL_COLOR4F, 4, 1.0f, 1.0f, 1.0f, 1.0f);
    emit1(state, MU_GL_ENABLE, GL_TEXTURE_2D);   /* raw glEnable: the cache flag is not updated */
}

void mu_ui_render_color_bitmap(mu_ui_state *state, int32_t texture, float x, float y, float width, float height,
                               float u, float v, float u_width, float v_height, uint32_t color)
{
    float p[4][2], c[4][2];
    uint32_t rgba[4] = {color & 0xff, (color >> 8) & 0xff, (color >> 16) & 0xff, (color >> 24) & 0xff};
    int i;
    x = mu_ui_convert_x(state, x);
    y = mu_ui_convert_y(state, y);
    width = mu_ui_convert_x(state, width);
    height = mu_ui_convert_y(state, height);
    mu_ui_bind_texture(state, texture);
    y = ufloat(state->window_height) - y;
    p[0][0] = x;          p[0][1] = y;
    p[1][0] = x;          p[1][1] = y - height;
    p[2][0] = x + width;  p[2][1] = y - height;
    p[3][0] = x + width;  p[3][1] = y;
    c[0][0] = u;           c[0][1] = v;
    c[3][0] = u + u_width; c[3][1] = v;
    c[2][0] = u + u_width; c[2][1] = v + v_height;
    c[1][0] = u;           c[1][1] = v + v_height;
    emit1(state, MU_GL_BEGIN, GL_TRIANGLE_FAN);
    for (i = 0; i < 4; ++i) {
        emit(state, MU_GL_COLOR4UB, rgba, 4);
        emitf(state, MU_GL_TEXCOORD2F, 2, c[i][0], c[i][1], 0, 0);
        emitf(state, MU_GL_VERTEX2F, 2, p[i][0], p[i][1], 0, 0);
        emitf(state, MU_GL_COLOR4F, 4, 1.0f, 1.0f, 1.0f, 1.0f);
    }
    emit(state, MU_GL_END, NULL, 0);
}

/* ---- CSprite ------------------------------------------------------------ */

void mu_ui_sprite_init(mu_ui_sprite *sprite)
{
    memset(sprite, 0, sizeof *sprite);
}

void mu_ui_sprite_create_frames(mu_ui_state *state, mu_ui_sprite *sprite, int32_t width, int32_t height,
                                int32_t texture, int32_t max_frame, const int32_t (*frame_xy)[2], int32_t datum_x,
                                int32_t datum_y, int tile, int32_t sizing_datums, float scale_x, float scale_y)
{
    float sh;
    sprite->bitmap = NULL;                       /* Release 0x010ad814 frees the frame table */
    sprite->has_frames = 0;
    sprite->width = (float)width;
    sprite->height = (float)height;
    sprite->texture = texture;
    sprite->bitmap = state->lookup ? state->lookup(state->lookup_user, (uint32_t)texture) : NULL;
    sprite->screen_height = ufloat(state->window_height) / scale_y;
    sh = sprite->screen_height;
    sprite->position[0][0] = 0.0f;
    sprite->position[0][1] = sh;
    sprite->position[1][0] = 0.0f;
    sprite->position[1][1] = sh - sprite->height;
    sprite->position[2][0] = sprite->width;
    sprite->position[2][1] = sh - sprite->height;
    sprite->position[3][0] = sprite->width;
    sprite->position[3][1] = sh;
    sprite->now_frame = -1;
    if (texture > -1) {
        float tw = sprite->bitmap ? sprite->bitmap->width : 0.0f;
        float th = sprite->bitmap ? sprite->bitmap->height : 0.0f;
        sprite->texcoord[0][0] = 0.5f / tw;
        sprite->texcoord[0][1] = 0.5f / th;
        sprite->texcoord[1][0] = 0.5f / tw;
        sprite->texcoord[1][1] = (sprite->height - 0.5f) / th;
        sprite->texcoord[2][0] = (sprite->width - 0.5f) / tw;
        sprite->texcoord[2][1] = (sprite->height - 0.5f) / th;
        sprite->texcoord[3][0] = (sprite->width - 0.5f) / tw;
        sprite->texcoord[3][1] = 0.5f / th;
        if (frame_xy != NULL) {
            int32_t i;
            sprite->max_frame = max_frame;
            sprite->has_frames = 1;
            for (i = 0; i < max_frame && i < MU_UI_SPRITE_MAX_FRAMES; ++i) {
                sprite->frames[i][0] = ((float)frame_xy[i][0] + 0.5f) / tw;
                sprite->frames[i][1] = ((float)frame_xy[i][1] + 0.5f) / th;
            }
            sprite->end_frame = 0;
            sprite->start_frame = 0;
            mu_ui_sprite_set_now_frame(sprite, 0);
            sprite->tile = 0;
        } else {
            sprite->max_frame = 0;
            sprite->end_frame = -1;
            sprite->start_frame = -1;
            sprite->tile = (uint8_t)tile;
        }
    } else {
        memset(sprite->texcoord, 0, sizeof sprite->texcoord);
        sprite->max_frame = 0;
        sprite->end_frame = -1;
        sprite->start_frame = -1;
        sprite->tile = 0;
    }
    sprite->alpha = sprite->red = sprite->green = sprite->blue = 0xff;
    sprite->datum_x = (float)datum_x;
    sprite->datum_y = (float)datum_y;
    sprite->repeat = 0;
    sprite->elapsed = 0.0;
    sprite->interval = 0.0;
    sprite->sizing_datums = sizing_datums;
    sprite->scale_x = scale_x;
    sprite->scale_y = scale_y;
    sprite->show = 0;
}

void mu_ui_sprite_create(mu_ui_state *state, mu_ui_sprite *sprite, int32_t width, int32_t height,
                         int32_t texture, int32_t datum_x, int32_t datum_y, int tile, int32_t sizing_datums,
                         float scale_x, float scale_y)
{
    mu_ui_sprite_create_frames(state, sprite, width, height, texture, 0, NULL, datum_x, datum_y, tile,
                               sizing_datums, scale_x, scale_y);
}

void mu_ui_sprite_create_image(mu_ui_state *state, mu_ui_sprite *sprite, const mu_ui_image_info *info,
                               int32_t datum_x, int32_t datum_y, int tile, int32_t sizing_datums, float scale_x,
                               float scale_y)
{
    if (info->x == 0 && info->y == 0) {
        mu_ui_sprite_create_frames(state, sprite, info->width, info->height, info->texture, 0, NULL, datum_x,
                                   datum_y, tile, sizing_datums, scale_x, scale_y);
    } else {
        int32_t frame[1][2] = {{info->x, info->y}};
        mu_ui_sprite_create_frames(state, sprite, info->width, info->height, info->texture, 1,
                                   (const int32_t (*)[2])frame, datum_x, datum_y, tile, sizing_datums, scale_x,
                                   scale_y);
    }
}

void mu_ui_sprite_set_action(mu_ui_sprite *sprite, int32_t start, int32_t end, double interval, int repeat)
{
    if (sprite->max_frame <= 1)
        return;
    sprite->now_frame = start;
    sprite->start_frame = start;
    sprite->end_frame = end;
    sprite->repeat = (uint8_t)repeat;
    sprite->interval = interval;
}

void mu_ui_sprite_set_now_frame(mu_ui_sprite *sprite, int32_t frame)
{
    float w, h;
    const float *f;
    float (*c)[2] = sprite->texcoord;
    if (!sprite->has_frames || frame == sprite->now_frame)
        return;
    if (frame < sprite->start_frame || frame > sprite->end_frame)
        return;
    sprite->now_frame = frame;
    w = c[3][0] - c[0][0];
    h = c[1][1] - c[0][1];
    f = sprite->frames[frame < MU_UI_SPRITE_MAX_FRAMES ? frame : MU_UI_SPRITE_MAX_FRAMES - 1];
    c[0][0] = f[0];
    c[0][1] = f[1];
    c[3][0] = f[0] + w;
    c[3][1] = f[1];
    c[1][0] = f[0];
    c[1][1] = f[1] + h;
    c[2][0] = c[3][0];
    c[2][1] = c[1][1];
}

void mu_ui_sprite_update(mu_ui_sprite *sprite, double delta)
{
    int32_t frame;
    if (!sprite->show || sprite->max_frame <= 1)
        return;
    sprite->elapsed = sprite->elapsed + delta;
    if (!(sprite->elapsed >= sprite->interval))
        return;
    frame = sprite->now_frame + 1;
    if (sprite->repeat)
        frame = frame > sprite->end_frame ? sprite->start_frame : frame;
    else
        frame = frame > sprite->end_frame ? sprite->end_frame : frame;
    mu_ui_sprite_set_now_frame(sprite, frame);
    sprite->elapsed = 0.0;
}

int mu_ui_sprite_contains(const mu_ui_sprite *sprite, int32_t x, int32_t y)
{
    int32_t left, top, right, bottom;
    if (!sprite->show)
        return 0;
    left = mu_ui_cvtt(sprite->position[0][0] * sprite->scale_x);
    top = mu_ui_cvtt((sprite->screen_height - sprite->position[0][1]) * sprite->scale_y);
    right = mu_ui_cvtt(sprite->position[2][0] * sprite->scale_x);
    bottom = mu_ui_cvtt((sprite->screen_height - sprite->position[2][1]) * sprite->scale_y);
    return x >= left && x < right && y >= top && y < bottom;   /* PtInRect */
}

int32_t mu_ui_sprite_x(const mu_ui_sprite *sprite) { return mu_ui_cvtt(sprite->position[0][0]); }
int32_t mu_ui_sprite_y(const mu_ui_sprite *sprite) { return mu_ui_cvtt(sprite->screen_height - sprite->position[0][1]); }
int32_t mu_ui_sprite_width(const mu_ui_sprite *sprite) { return mu_ui_cvtt(sprite->position[3][0] - sprite->position[0][0]); }
int32_t mu_ui_sprite_height(const mu_ui_sprite *sprite) { return mu_ui_cvtt(sprite->position[0][1] - sprite->position[1][1]); }

int32_t mu_ui_sprite_texture_height(const mu_ui_sprite *sprite)
{
    return sprite->texture > -1 && sprite->bitmap ? mu_ui_cvtt(sprite->bitmap->height) : 0;
}

void mu_ui_sprite_show(mu_ui_sprite *sprite, int show)
{
    sprite->show = (uint8_t)show;
}

void mu_ui_sprite_set_position(mu_ui_sprite *sprite, int32_t x, int32_t y, int32_t which)
{
    float (*p)[2] = sprite->position;
    if (which & 1) {
        float w = p[3][0] - p[0][0];
        if (sprite->sizing_datums & 2) {
            float t = (float)x + sprite->width - sprite->datum_x;
            p[2][0] = t;
            p[3][0] = t;
            t = p[3][0] - w;
            p[1][0] = t;
            p[0][0] = t;
        } else {
            float t = (float)x - sprite->datum_x;
            p[1][0] = t;
            p[0][0] = t;
            t = p[0][0] + w;
            p[2][0] = t;
            p[3][0] = t;
        }
    }
    if (which & 2) {
        float h = p[0][1] - p[1][1];
        if (sprite->sizing_datums & 1) {
            float t = sprite->screen_height - (float)y - sprite->height + sprite->datum_y;
            p[2][1] = t;
            p[1][1] = t;
            t = p[1][1] + h;
            p[3][1] = t;
            p[0][1] = t;
        } else {
            float t = sprite->screen_height - (float)y + sprite->datum_y;
            p[3][1] = t;
            p[0][1] = t;
            t = p[0][1] - h;
            p[2][1] = t;
            p[1][1] = t;
        }
    }
}

void mu_ui_sprite_set_size(mu_ui_sprite *sprite, int32_t width, int32_t height, int32_t which)
{
    float (*p)[2] = sprite->position;
    float (*c)[2] = sprite->texcoord;
    float tw = sprite->bitmap ? sprite->bitmap->width : 0.0f;
    float th = sprite->bitmap ? sprite->bitmap->height : 0.0f;
    if (which & 1) {
        if (sprite->sizing_datums & 2) {
            float t = p[3][0] - (float)width;
            p[1][0] = t;
            p[0][0] = t;
            if (sprite->tile) {
                t = c[3][0] - (float)width / tw;
                c[1][0] = t;
                c[0][0] = t;
            }
        } else {
            float t = p[0][0] + (float)width;
            p[2][0] = t;
            p[3][0] = t;
            if (sprite->tile) {
                t = (float)width / tw;
                c[2][0] = t;
                c[3][0] = t;
            }
        }
    }
    if (which & 2) {
        if (sprite->sizing_datums & 1) {
            float t = p[1][1] + (float)height;
            p[3][1] = t;
            p[0][1] = t;
            if (sprite->tile) {
                t = c[1][1] - (float)height / th;
                c[3][1] = t;
                c[0][1] = t;
            }
        } else {
            float t = p[0][1] - (float)height;
            p[2][1] = t;
            p[1][1] = t;
            if (sprite->tile) {
                t = (float)height / th;
                c[2][1] = t;
                c[1][1] = t;
            }
        }
    }
}

void mu_ui_sprite_render(mu_ui_state *state, const mu_ui_sprite *sprite)
{
    uint32_t color[4];
    int i;
    if (!sprite->show)
        return;
    color[0] = sprite->red;
    color[1] = sprite->green;
    color[2] = sprite->blue;
    color[3] = sprite->alpha;
    if (sprite->texture > -1) {
        enable_flag(state, &state->texture_2d, GL_TEXTURE_2D);
        mu_ui_bind_texture(state, sprite->texture);
        emit1(state, MU_GL_BEGIN, GL_TRIANGLE_FAN);
        emit(state, MU_GL_COLOR4UB, color, 4);
        for (i = 0; i < 4; ++i) {
            emitf(state, MU_GL_TEXCOORD2F, 2, sprite->texcoord[i][0], sprite->texcoord[i][1], 0, 0);
            emitf(state, MU_GL_VERTEX2F, 2, sprite->position[i][0] * sprite->scale_x,
                  sprite->position[i][1] * sprite->scale_y, 0, 0);
        }
        emit(state, MU_GL_END, NULL, 0);
    } else {
        disable_flag(state, &state->texture_2d, GL_TEXTURE_2D);
        emit1(state, MU_GL_BEGIN, GL_TRIANGLE_FAN);
        emit(state, MU_GL_COLOR4UB, color, 4);
        for (i = 0; i < 4; ++i)
            emitf(state, MU_GL_VERTEX2F, 2, sprite->position[i][0] * sprite->scale_x,
                  sprite->position[i][1] * sprite->scale_y, 0, 0);
        emit(state, MU_GL_END, NULL, 0);
    }
}

/* ---- CGaugeBar ---------------------------------------------------------- */

void mu_ui_gauge_create(mu_ui_state *state, mu_ui_gauge *gauge, int32_t width, int32_t height, int32_t texture,
                        const int32_t *rect, int fixed_left, float scale_x, float scale_y)
{
    int32_t sizing = (uint8_t)fixed_left ? 0 : 2;
    gauge->has_back = 0;                         /* Release 0x00aacb59 */
    mu_ui_sprite_create(state, &gauge->bar, width, height, texture, 0, 0, 1, sizing, scale_x, scale_y);
    if (rect == NULL) {
        gauge->rect[0] = 0;
        gauge->rect[1] = 0;
        gauge->rect[2] = width;
        gauge->rect[3] = height;
    } else {
        memcpy(gauge->rect, rect, sizeof gauge->rect);
        mu_ui_sprite_set_size(&gauge->bar, 0, gauge->rect[3] - gauge->rect[1], 2);
    }
    gauge->y = 0;
    gauge->x = 0;
}

void mu_ui_gauge_set_position(mu_ui_gauge *gauge, int32_t x, int32_t y)
{
    mu_ui_sprite_set_position(&gauge->bar, x + gauge->rect[0], y + gauge->rect[1], 3);
    gauge->x = x;
    gauge->y = y;
}

void mu_ui_gauge_set_value(mu_ui_gauge *gauge, uint32_t now, uint32_t total)
{
    uint32_t width;
    total = total < 1 ? 1 : total;
    now = now > total ? total : now;
    width = (uint32_t)(gauge->rect[2] - gauge->rect[0]) * now / total;
    if (gauge->bar.sizing_datums & 2) {
        int32_t texture_width = gauge->bar.texture > -1 && gauge->bar.bitmap
                                ? mu_ui_cvtt(gauge->bar.bitmap->width) : 0;
        width = (uint32_t)(texture_width - (gauge->rect[2] - gauge->rect[0])) + width;
    }
    mu_ui_sprite_set_size(&gauge->bar, (int32_t)width, 0, 1);
}

void mu_ui_gauge_render(mu_ui_state *state, const mu_ui_gauge *gauge)
{
    mu_ui_sprite_render(state, &gauge->bar);
}

void mu_ui_gauge_show(mu_ui_gauge *gauge, int show)
{
    mu_ui_sprite_show(&gauge->bar, show);
}

/* ---- title scene -------------------------------------------------------- */

void mu_ui_title_create(mu_ui_state *state, mu_ui_title *title, int32_t screen_width, int32_t screen_height)
{
    static const int32_t gauge_rect[4] = {0, 0, 0x290, 0xf};
    mu_ui_sprite *s = title->sprites;
    float sx800 = (float)screen_width / 800.0f;
    float sy600 = (float)screen_height / 600.0f;
    float s1280 = (float)screen_width / 1280.0f;
    float aspect, virtual_height, sx, sy;
    int32_t top, bottom, offset, gauge_height;
    int i;
    for (i = 0; i < MU_UI_TITLE_SPRITES; ++i)
        mu_ui_sprite_init(&s[i]);

    mu_ui_sprite_create(state, &s[0], 0x190, 0x45, 0x7b81, 0, 0, 0, 0, sx800, sy600);
    mu_ui_sprite_set_position(&s[0], 0, 0, 3);
    mu_ui_sprite_create(state, &s[1], 0x190, 0x45, 0x7b82, 0, 0, 0, 0, sx800, sy600);
    mu_ui_sprite_set_position(&s[1], 0x190, 0, 3);
    mu_ui_sprite_create(state, &s[5], 0x190, 0x64, 0x7b87, 0, 0, 0, 0, sx800, sy600);
    mu_ui_sprite_set_position(&s[5], 0, 0x1f4, 3);
    mu_ui_sprite_create(state, &s[6], 0x190, 0x64, 0x7b88, 0, 0, 0, 0, sx800, sy600);
    mu_ui_sprite_set_position(&s[6], 0x190, 0x1f4, 3);

    aspect = ufloat(state->window_width) / ufloat(state->window_height);
    virtual_height = 1280.0f / aspect;
    sx = (float)screen_width / 1280.0f;
    sy = (float)screen_height / virtual_height;
    top = 0x200;
    bottom = 0xdf;
    offset = mu_ui_cvtt((float)(top + bottom) - (float)(top + bottom) * (virtual_height / 1024.0f));
    if (offset > bottom) {
        top -= offset - bottom;
        bottom = 0;
    } else {
        bottom -= offset;
    }
    gauge_height = mu_ui_cvtt(virtual_height / 600.0f * 69.0f);
    mu_ui_sprite_create(state, &s[7], 0x200, top, 0x7b89, 0, 0, 0, 0, sx, sy);
    mu_ui_sprite_set_position(&s[7], 0, gauge_height, 3);
    mu_ui_sprite_create(state, &s[8], 0x200, top, 0x7b8a, 0, 0, 0, 0, sx, sy);
    mu_ui_sprite_set_position(&s[8], 0x200, gauge_height, 3);
    mu_ui_sprite_create(state, &s[9], 0x100, top, 0x7b8b, 0, 0, 0, 0, sx, sy);
    mu_ui_sprite_set_position(&s[9], 0x400, gauge_height, 3);
    mu_ui_sprite_create(state, &s[10], 0x200, bottom, 0x7b8c, 0, 0, 0, 0, sx, sy);
    mu_ui_sprite_set_position(&s[10], 0, gauge_height + 0x200, 3);
    mu_ui_sprite_create(state, &s[11], 0x200, bottom, 0x7b8d, 0, 0, 0, 0, sx, sy);
    mu_ui_sprite_set_position(&s[11], 0x200, gauge_height + 0x200, 3);
    mu_ui_sprite_create(state, &s[12], 0x100, bottom, 0x7b8e, 0, 0, 0, 0, sx, sy);
    mu_ui_sprite_set_position(&s[12], 0x400, gauge_height + 0x200, 3);

    mu_ui_sprite_create(state, &s[2], 0xd8, 0x8a, 0x7b83, 0, 0, 0, 0, s1280, s1280);
    if ((float)screen_width == 1280.0f)
        mu_ui_sprite_set_position(&s[2], 0x214, 0x2cc, 3);
    else
        mu_ui_sprite_set_position(&s[2], 0x214, 0x297, 3);
    mu_ui_sprite_create(state, &s[3], 0x100, 0xce, 0x7b84, 0, 0, 0, 0, sx800, sy600);
    mu_ui_sprite_set_position(&s[3], 0x220, 0x3c, 3);
    mu_ui_sprite_create(state, &s[4], 0x35, 0x2e, 0x7b85, 0, 0, 0, 0, 1.0f, 1.0f);
    mu_ui_sprite_set_position(&s[4], 0x10, 8, 3);

    mu_ui_gauge_create(state, &title->gauge, 4, 0xf, 0x7b86, gauge_rect, 1, sx800, sy600);
    mu_ui_gauge_set_position(&title->gauge, 0x48, 0x21c);
    for (i = 0; i < MU_UI_TITLE_SPRITES; ++i)
        s[i].show = 1;
    title->gauge.bar.show = 1;
    s[3].show = 0;
}

void mu_ui_title_render(mu_ui_state *state, mu_ui_title *title, uint32_t now, uint32_t total)
{
    int i;
    mu_ui_begin_bitmap(state);
    for (i = 0; i < MU_UI_TITLE_SPRITES; ++i) {
        if (i == 2)
            continue;
        mu_ui_sprite_render(state, &title->sprites[i]);
    }
    mu_ui_gauge_set_value(&title->gauge, now, total);
    mu_ui_gauge_render(state, &title->gauge);
    mu_ui_end_bitmap(state);
}
