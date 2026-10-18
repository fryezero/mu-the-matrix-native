/* RenderSprite, CreateSprite and RenderSprites (NATIVE-PARTICLE-001). */
#include <string.h>

#include "particles.h"
#include "particles_internal.h"
#include "../record-math/record_math.h"

/* ---------------------------------------------------------------- RenderSprite 0x0184c39c */

void mu_pt_sprite_corners(const float camera[12], const mu_pt_sprite_call *s, float c[4][3], float uv[4][2])
{
    float eye[3];
    mu_vector_transform(s->position, camera, eye);   /* VectorTransform 0x00d002b2 */
    const float w = s->width * 0.5f, h = s->height * 0.5f;
    if (s->rotation == 0.0f) {
        c[0][0] = eye[0] - w;
        c[0][1] = eye[1] - h;
        c[0][2] = eye[2];
        c[1][0] = eye[0] + w;
        c[1][1] = eye[1] - h;
        c[1][2] = eye[2];
        c[2][0] = eye[0] + w;
        c[2][1] = eye[1] + h;
        c[2][2] = eye[2];
        c[3][0] = eye[0] - w;
        c[3][1] = eye[1] + h;
        c[3][2] = eye[2];
    } else {
        /* 0x0184c5a1: the corners about the origin, AngleMatrix of the rotation on the chosen axes */
        const float local[4][3] = {{-w, -h, 0.0f}, {w, -h, 0.0f}, {w, h, 0.0f}, {-w, h, 0.0f}};
        float a[3] = {0.0f, 0.0f, 0.0f}, m[12];
        if (s->axes & 1)
            a[0] = s->rotation;
        if (s->axes & 2)
            a[1] = s->rotation;
        if (s->axes & 4)
            a[2] = s->rotation;
        mu_angle_matrix(a, m);
        for (int k = 0; k < 4; ++k) {
            mu_vector_rotate(local[k], m, c[k]);
            c[k][0] = c[k][0] + eye[0];
            c[k][1] = c[k][1] + eye[1];
            c[k][2] = c[k][2] + eye[2];
        }
    }
    uv[0][0] = s->u;
    uv[0][1] = s->v + s->vh;
    uv[1][0] = s->u + s->uw;
    uv[1][1] = s->v + s->vh;
    uv[2][0] = s->u + s->uw;
    uv[2][1] = s->v;
    uv[3][0] = s->u;
    uv[3][1] = s->v;
}

void mu_pt_render_sprite(const float camera[12], const mu_pt_sprite_call *s, int32_t components, const mu_pt_gl *gl)
{
    if (gl && gl->bind)
        gl->bind(gl->context, s->bitmap);
    float c[4][3], uv[4][2];
    mu_pt_sprite_corners(camera, s, c, uv);
    if (!gl)
        return;
    if (gl->begin)
        gl->begin(gl->context, MU_PT_GL_QUADS);
    if (components == 3) {
        if (gl->color3)
            gl->color3(gl->context, s->light);
    } else if (s->bitmap == 0x7f49 || s->bitmap == 0x7df3) {
        if (gl->color4)
            gl->color4(gl->context, s->light[0], s->light[1], s->light[2], 1.0f);
    } else if (gl->color4) {
        gl->color4(gl->context, s->light[0], s->light[1], s->light[2], s->light[0]);
    }
    for (int k = 0; k < 4; ++k) {
        if (gl->texcoord)
            gl->texcoord(gl->context, uv[k][0], uv[k][1]);
        if (gl->vertex)
            gl->vertex(gl->context, c[k]);
    }
    if (gl->end)
        gl->end(gl->context);
}

/* ---------------------------------------------------------------- CreateSprite 0x01692508 */

int32_t mu_pt_sprite_create(mu_pt_sprites *s, int32_t bitmap, const float position[3], float scale,
                            const float light[3], int32_t owner, float rotation, int32_t blend, int32_t axes,
                            const mu_pt_sheet *sheet)
{
    for (int32_t i = 0; i < MU_PT_SPRITES; ++i) {
        mu_pt_sprite *o = &s->records[i];
        if (o->live)
            continue;
        o->live = 1;                    /* SetLive(1) 0x0129f4a5 */
        o->type = bitmap;
        o->blend = blend;
        o->owner = owner;
        o->alpha = 1.0f;
        o->scale = scale;
        o->rotation = rotation;
        o->axes = axes;
        for (int k = 0; k < 3; ++k)
            o->position[k] = position[k];
        for (int k = 0; k < 3; ++k)
            o->start[k] = position[k];
        for (int k = 0; k < 3; ++k)
            o->light[k] = light[k];
        o->sheet[0] = (float)sheet->across;
        o->sheet[1] = (float)sheet->down;
        o->sheet_time = mu_pt_cvttss2si(sheet->ms);
        s->created++;
        return i;
    }
    s->full++;
    return 0;
}

void mu_pt_sprites_mark_visible(mu_pt_sprites *s)
{
    for (int32_t i = 0; i < MU_PT_SPRITES; ++i)
        if (s->records[i].live)
            s->records[i].visible = 1;
}

/* ---------------------------------------------------------------- RenderSprites 0x0169270e */

int mu_pt_sprite_draw_call(mu_pt_sprite *o, const mu_pt_bitmap *b, float world_time, mu_pt_sprite_call *out)
{
    /* 0x01692931: the alpha ramp */
    if (o->visible) {
        o->alpha = o->alpha + 0.1f;
        if (o->alpha > 1.0f)
            o->alpha = 1.0f;
    } else {
        o->alpha = o->alpha - 0.1f;
        if (0.2f > o->alpha)
            o->alpha = 0.2f;
    }
    const float size = o->alpha * o->scale;
    const float width = b->width * size, height = b->height * size;
    memset(out, 0, sizeof *out);
    if (o->type == 0x7fea) {
        /* 0x01692a39: a 64x64 cell of a 3x3 sheet chosen by the blend value (table 0x01692e29) */
        static const float cells[8][2] = {{0.0f, 0.0f},   {0.33f, 0.0f},  {0.66f, 0.0f},  {0.0f, 0.33f},
                                          {0.33f, 0.33f}, {0.66f, 0.33f}, {0.0f, 0.66f},  {0.33f, 0.66f}};
        out->bitmap = o->type;
        for (int k = 0; k < 3; ++k)
            out->position[k] = o->position[k];
        out->width = 64.0f;
        out->height = 64.0f;
        for (int k = 0; k < 3; ++k)
            out->light[k] = o->light[k];
        out->rotation = o->rotation;
        if (o->blend >= 0 && o->blend <= 7) {
            out->u = cells[o->blend][0];
            out->v = cells[o->blend][1];
        }
        out->uw = 0.33f;
        out->vh = 0.33f;
        out->axes = o->axes;
        return 1;
    }
    out->bitmap = o->type;
    for (int k = 0; k < 3; ++k)
        out->position[k] = o->position[k];
    out->width = width;
    out->height = height;
    for (int k = 0; k < 3; ++k)
        out->light[k] = o->light[k];
    out->rotation = o->rotation;
    out->axes = o->axes;
    if (o->sheet[0] == 1.0f && o->sheet[1] == 1.0f) {
        out->u = 0.0f;
        out->v = 0.0f;
        out->uw = 1.0f;
        out->vh = 1.0f;
        return 1;
    }
    /* 0x01692c19: the cell of the world time */
    const float cell_u = 1.0f / o->sheet[0], cell_v = 1.0f / o->sheet[1];
    const int32_t ms = o->sheet_time;
    int32_t cells = mu_pt_cvttss2si(o->sheet[0] * o->sheet[1]);
    if (cells <= 0)
        cells = 1;
    const int32_t t = mu_pt_cvttss2si(world_time);
    const int32_t cell = (t % (cells * ms)) / ms;
    const int32_t across = mu_pt_cvttss2si(o->sheet[0]);
    out->u = (float)(cell % across) * (1.0f / o->sheet[0]);
    out->v = (float)(cell / across) * (1.0f / o->sheet[1]);
    out->uw = cell_u;
    out->vh = cell_v;
    return 1;
}

static void blend_state(const mu_pt_gl *gl, int32_t type, int32_t blend)
{
    if (!gl || !gl->state)
        return;
    if (type == 0x7fea) {
        gl->state(gl->context, MU_PT_STATE_ALPHA, 1);
        return;
    }
    switch (blend) {
    case 0: gl->state(gl->context, MU_PT_STATE_ADD, 0); break;
    case 1: gl->state(gl->context, MU_PT_STATE_SUBTRACT, 0); break;
    case 2: gl->state(gl->context, MU_PT_STATE_ALPHA, 1); break;
    case 3: gl->state(gl->context, MU_PT_STATE_ADD_INVERSE, 0); break;
    case 4:
        gl->state(gl->context, MU_PT_STATE_ADD_FOG, 0);
        gl->state(gl->context, MU_PT_STATE_ALPHA, 1);
        break;
    default: break;
    }
}

int32_t mu_pt_sprites_render(mu_pt_sprites *s, uint8_t mode, float world_time, const float camera[12],
                             mu_pt_bitmap_fn bitmap, void *bitmap_context, const mu_pt_gl *gl,
                             void (*kill)(void *context, int32_t index), void *kill_context)
{
    int32_t drawn = 0;
    for (int32_t i = 0; i < MU_PT_SPRITES; ++i) {
        mu_pt_sprite *o = &s->records[i];
        if (mode == 1 && o->position[2] > 350.0f)
            continue;
        if (mode == 2 && 300.0f >= o->position[2]) {
            o->live = 0;                 /* SetLive(0) */
            if (kill)
                kill(kill_context, i);
            continue;
        }
        if (!o->live)
            continue;
        blend_state(gl, o->type, o->blend);
        mu_pt_bitmap b = {0.0f, 0.0f, 4};
        int have = bitmap && bitmap(bitmap_context, o->type, &b);
        mu_pt_sprite_call call;
        if (have && mu_pt_sprite_draw_call(o, &b, world_time, &call)) {
            mu_pt_render_sprite(camera, &call, b.components, gl);
            drawn++;
        }
        if (mode == 0 || mode == 2) {
            o->live = 0;
            if (kill)
                kill(kill_context, i);
        }
    }
    return drawn;
}
