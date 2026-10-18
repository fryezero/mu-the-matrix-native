/* The character-select scene's legacy 2D window (NATIVE-CHARSEL-001). See mu_charsel_ui.h. */
#include "mu_charsel_ui.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const uint32_t FONT_HANDLES[4] = {0x0f0f0001u, 0x0f0f0002u, 0x0f0f0003u, 0x0f0f0004u};

/* OpenCharacterSceneData 0x0182a553: GL_NEAREST, GL_CLAMP */
static const struct { uint32_t index; const char *path; } TEXTURES[] = {
    {0x7b10, "Interface\\deco.tga"},
    {0x7b11, "Interface\\b_create.tga"},
    {0x7b12, "Interface\\server_menu_b_all.tga"},
    {0x7b13, "Interface\\b_connect.tga"},
    {0x7b14, "Interface\\b_delete.tga"},
    {0x7532, "Interface\\FontInput.tga"},
};

/* Observed on the live screen (Data\Lang.mpr is not decoded). */
static const char *const LIVE_TIP = "Long game time may be harmful to your health!";

static const char *global_text(void *user, int32_t index)
{
    mu_charsel_ui *ui = user;
    const char *tip = (const char *)ui->ctx.platform.user;
    switch (index) {
    case 0x6ae: case 0x6cb: case 0x6cc: return tip;
    default: return "";
    }
}

static void sink_call(void *user, int op, const uint32_t *words, int count, const void *data, size_t bytes)
{
    mu_charsel_ui *ui = user;
    if (op == MU_GDI_SELECTOBJECT && count >= 1)
        mu_ui_font_set_select(&ui->fonts, words[0]);
    else if (op == MU_UI_EVENT && count >= 2 && ui->event_count < 16) {
        ui->events[ui->event_count][0] = (int32_t)words[0];
        ui->events[ui->event_count][1] = (int32_t)words[1];
        ui->event_count++;
    } else if (op == MU_UI_SOUND)
        ui->sounds++;
    ui->inner.call(ui->inner.user, op, words, count, data, bytes);
}

static void refresh(mu_charsel_ui *ui, const mu_charsel_session *s)
{
    mu_ui_charsel_input *in = &ui->input;
    for (int32_t i = 0; i < MU_UI_CHARSEL_SLOTS; ++i) {
        const uint8_t *r = s->records + (size_t)i * MU_CHARSEL_RECORD;
        mu_ui_charsel_slot *slot = &in->slots[i];
        slot->live = r[MU_CHARSEL_OBJECT + MU_OBJ_LIVE];
        slot->flags = r[MU_CHAR_FLAG_14];
        slot->byte_17 = 0xff;                       /* no pending state on synthetic characters */
        slot->level = (uint16_t)(r[0x144] | (r[0x145] << 8));
        slot->byte_3634 = 0;
        int32_t e = mu_charsel_entry_of(s, i);
        snprintf(slot->name, sizeof slot->name, "%s", e >= 0 ? s->list.entries[e].name : "");
    }
    in->selected = s->selected;
}

int mu_charsel_ui_init(mu_charsel_ui *ui, const char *root, int32_t width, int32_t height, const char *font,
                       const mu_charsel_session *s, const char *tip)
{
    memset(ui, 0, sizeof *ui);
    if (mu_ui_raster_init(&ui->raster, width, height))
        return 1;
    ui->inner = mu_ui_raster_sink(&ui->raster);
    ui->state.sink.user = ui;
    ui->state.sink.call = sink_call;
    ui->state.lookup = mu_ui_assets_lookup;
    ui->state.lookup_user = &ui->assets;
    mu_ui_state_init(&ui->state, (uint32_t)width, (uint32_t)height);
    mu_ui_assets_init(&ui->assets, root);
    for (size_t i = 0; i < sizeof TEXTURES / sizeof TEXTURES[0]; ++i)
        if (mu_ui_assets_load(&ui->assets, &ui->state, TEXTURES[i].path, TEXTURES[i].index, 0x2600, 0x2900) ==
            MU_UI_TEXTURE_LOADED)
            ++ui->textures;
    if (!mu_ui_assets_lookup(&ui->assets, 0x7532))
        mu_ui_assets_add(&ui->assets, &ui->state, 0x7532, 256, 32, NULL);
    mu_ui_font_set_open(&ui->fonts, font, font, (uint32_t)width, FONT_HANDLES);
    ui->text.gdi = mu_ui_font_set_gdi(&ui->fonts);
    mu_ui_text_init(&ui->text, &ui->state);
    ui->text.dib = calloc((size_t)mu_ui_text_dib_stride(ui->text.dib_width) * (size_t)ui->text.dib_height, 1);
    mu_ui_ctx *ctx = &ui->ctx;
    ctx->state = &ui->state;
    ctx->text = &ui->text;
    ctx->input.screen_width = width;
    ctx->input.screen_height = height;
    ctx->input.cursor_x = ctx->input.cursor_y = -1000;
    ctx->fonts.normal = FONT_HANDLES[0];
    ctx->fonts.bold = FONT_HANDLES[1];
    ctx->fonts.big = FONT_HANDLES[2];
    ctx->fonts.fixed = FONT_HANDLES[3];
    ctx->global_text = global_text;
    ctx->global_text_user = ui;
    ctx->platform.user = (void *)(tip ? tip : LIVE_TIP);
    /* CUIMng::CreateCharacterScene: Create, SetPosition(0x16, height - h - 0xe),
     * UpdateDisplay, ShowWin */
    refresh(ui, s);
    ui->input.random = 0;     /* the rand() draw picks the tip index; all three show the same string here */
    mu_ui_charsel_win_init(&ui->win, &ui->input);
    mu_ui_charsel_win_create(ctx, &ui->win);
    mu_ui_charsel_win_place(ctx, &ui->win);
    mu_ui_charsel_win_update_display(ctx, &ui->win);
    ui->win.win.cls->show(ctx, &ui->win.win, 1);
    mu_ui_win_set_active(&ui->win.win, 1);
    return 0;
}

void mu_charsel_ui_free(mu_charsel_ui *ui)
{
    free(ui->text.dib);
    mu_ui_font_set_close(&ui->fonts);
    mu_ui_assets_free(&ui->assets);
    mu_ui_raster_free(&ui->raster);
    memset(ui, 0, sizeof *ui);
}

void mu_charsel_ui_update(mu_charsel_ui *ui, const mu_charsel_session *s, int32_t x, int32_t y, uint8_t down,
                          uint8_t up)
{
    refresh(ui, s);
    mu_ui_charsel_win_update_display(&ui->ctx, &ui->win);   /* the GFx list's selection calls it */
    ui->ctx.input.cursor_x = x;
    ui->ctx.input.cursor_y = y;
    ui->ctx.input.lbutton_down = down;
    ui->ctx.input.lbutton_up = up;
    mu_ui_win_update(&ui->ctx, &ui->win.win, 40.0);
}

void mu_charsel_ui_render(mu_charsel_ui *ui, uint8_t *rgba)
{
    mu_ui_raster *r = &ui->raster;
    size_t row = (size_t)r->width * 4;
    for (int32_t y = 0; y < r->height; ++y)
        memcpy(r->rgba + (size_t)(r->height - 1 - y) * row, rgba + (size_t)y * row, row);
    mu_ui_begin_bitmap(&ui->state);
    ui->win.win.cls->render(&ui->ctx, &ui->win.win);   /* CUIMng::Render: the window list */
    mu_ui_end_bitmap(&ui->state);
    mu_ui_raster_read_top_down(r, rgba);
}
