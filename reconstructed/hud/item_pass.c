/* Reconstructed per-window GFx render pass (see item_pass.h). */
#include "item_pass.h"

#include <string.h>

static void emit(mu_ui_state *state, int op, const uint32_t *words, int count)
{
    if (state->sink.call)
        state->sink.call(state->sink.user, op, words, count, NULL, 0);
}

static uint32_t fbits(float value)
{
    uint32_t word;
    memcpy(&word, &value, 4);
    return word;
}

static void emit_double(uint32_t *words, double value)
{
    uint64_t bits;
    memcpy(&bits, &value, 8);
    words[0] = (uint32_t)bits;
    words[1] = (uint32_t)(bits >> 32);
}

static void color4f(mu_ui_state *state, float r, float g, float b, float a)
{
    uint32_t w[4] = {fbits(r), fbits(g), fbits(b), fbits(a)};
    emit(state, MU_GL_COLOR4F, w, 4);
}

static void matrix_mode(mu_ui_state *state, uint32_t mode)
{
    emit(state, MU_GL_MATRIXMODE, &mode, 1);
}

/* 0x0184a569(dst): glGetFloatv(GL_MODELVIEW_MATRIX), dst[i][j] = m[j*4 + i]. */
static void read_modelview(mu_ui_state *state, mu_hud_camera *camera, mu_hud_get_modelview get, void *user)
{
    float m[16] = {0};
    uint32_t pname = 0xba6;
    emit(state, MU_HUD_GL_GETFLOATV, &pname, 1);
    if (get)
        get(user, m);
    for (int i = 0; i < 3; i++)
        for (int j = 0; j < 4; j++)
            camera->matrix[i][j] = m[j * 4 + i];
}

/* 0x0184b705: camera transform restore. */
static void camera_restore(mu_ui_state *state, mu_hud_camera *camera, mu_hud_get_modelview get, void *user)
{
    emit(state, MU_GL_LOADIDENTITY, NULL, 0);
    uint32_t t[3] = {fbits(-camera->position[0]), fbits(-camera->position[1]), fbits(-camera->position[2])};
    emit(state, MU_HUD_GL_TRANSLATEF, t, 3);
    read_modelview(state, camera, get, user);
    float v[3] = {-camera->matrix[0][3], -camera->matrix[1][3], -camera->matrix[2][3]};
    for (int j = 0; j < 3; j++)                        /* VectorIRotate 0x00cfff3c */
        camera->eye[j] = v[0] * camera->matrix[0][j] + v[1] * camera->matrix[1][j] + v[2] * camera->matrix[2][j];
}

void mu_hud_window_pass(mu_ui_state *state, mu_hud_camera *camera, const mu_hud_window *windows, int32_t count,
                        int ui_hidden, mu_hud_get_modelview get_modelview, void *user)   /* 0x00abfcca */
{
    for (int32_t k = 0; k < count; k++) {
        const mu_hud_window *w = &windows[k];
        if (w->id == 0)
            continue;
        if (!w->identity && ui_hidden)
            continue;
        if (w->excluded)
            continue;
        uint32_t attrib = 0xfffff, id = w->id;
        emit(state, MU_HUD_GL_PUSHATTRIB, &attrib, 1);
        emit(state, MU_HUD_WINDOW_DISPLAY, &id, 1);
        emit(state, MU_HUD_GL_POPATTRIB, NULL, 0);
        camera->saved_rate[0] = camera->rate[0];       /* 0x01850433 */
        camera->saved_rate[1] = camera->rate[1];
        memcpy(camera->saved, camera->matrix, sizeof camera->saved);   /* 0x0185038d */
        matrix_mode(state, 0x1701);
        emit(state, MU_GL_PUSHMATRIX, NULL, 0);
        emit(state, MU_GL_LOADIDENTITY, NULL, 0);
        uint32_t vp[4] = {0, 0, state->window_width, state->window_height};
        emit(state, MU_GL_VIEWPORT, vp, 4);
        uint32_t o[12];
        emit_double(o + 0, 0.0);
        emit_double(o + 2, (double)state->window_width);
        emit_double(o + 4, 0.0);
        emit_double(o + 6, (double)state->window_height);
        emit_double(o + 8, 20.0);
        emit_double(o + 10, 2000.0);
        emit(state, MU_HUD_GL_ORTHO, o, 12);
        matrix_mode(state, 0x1700);
        emit(state, MU_GL_PUSHMATRIX, NULL, 0);
        emit(state, MU_GL_LOADIDENTITY, NULL, 0);
        read_modelview(state, camera, get_modelview, user);
        mu_ui_enable_depth_test(state);                /* 0x0184a6b7 */
        mu_ui_enable_depth_mask(state);                /* 0x0184a743 */
        uint32_t mask = 0x100;
        emit(state, MU_GL_CLEAR, &mask, 1);
        color4f(state, 1.0f, 1.0f, 1.0f, w->alpha);
        emit(state, MU_HUD_WINDOW_ITEMS, &id, 1);
        camera_restore(state, camera, get_modelview, user);
        matrix_mode(state, 0x1700);
        emit(state, MU_GL_POPMATRIX, NULL, 0);
        matrix_mode(state, 0x1701);
        emit(state, MU_GL_POPMATRIX, NULL, 0);
        camera->rate[0] = camera->saved_rate[0];       /* 0x01850458 */
        camera->rate[1] = camera->saved_rate[1];
        memcpy(camera->matrix, camera->saved, sizeof camera->matrix);  /* 0x018503e0 */
        mu_ui_begin_bitmap(state);
        color4f(state, 1.0f, 1.0f, 1.0f, 1.0f);
        emit(state, MU_HUD_WINDOW_OVERLAY, &id, 1);
        color4f(state, 0.0f, 0.0f, 0.0f, 1.0f);
        mu_ui_end_bitmap(state);
    }
}
