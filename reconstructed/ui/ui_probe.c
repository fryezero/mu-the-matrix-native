/* Flat views of widget state for scripts/validate_ui_widgets.py (NATIVE-UI-002).
 *
 * Each probe writes 32-bit words in a fixed order that the validator reads
 * from the client's objects at the client offsets listed in ui_widget.h and
 * ui_server.h, so object state can be compared word for word alongside the
 * platform-call streams.  Not part of the native module.
 */
#include "ui_credit.h"
#include "ui_server.h"

#include <string.h>

size_t mu_ui_probe_sizeof(int which);
int mu_ui_probe_sprite(const mu_ui_sprite *sprite, uint32_t *out);
int mu_ui_probe_button(const mu_ui_button *button, uint32_t *out);
int mu_ui_probe_win(const mu_ui_win *win, uint32_t *out);
int mu_ui_probe_winex(const mu_ui_winex *win, uint32_t *out);
int mu_ui_probe_server_win(const mu_ui_server_win *win, uint32_t *out);
int32_t mu_ui_probe_held(const mu_ui_ctx *ctx, const mu_ui_win *win);
void mu_ui_probe_select(mu_ui_server_win *win, int32_t selected);
int mu_ui_probe_credit_win(const mu_ui_credit_win *win, uint32_t *out);

static uint32_t fw(float value)
{
    uint32_t word;
    memcpy(&word, &value, 4);
    return word;
}

size_t mu_ui_probe_sizeof(int which)
{
    switch (which) {
    case 0: return sizeof(mu_ui_ctx);
    case 1: return sizeof(mu_ui_button);
    case 2: return sizeof(mu_ui_win);
    case 3: return sizeof(mu_ui_winex);
    case 4: return sizeof(mu_ui_server_win);
    case 5: return sizeof(mu_ui_server_list);
    case 6: return sizeof(mu_ui_sprite);
    case 7: return sizeof(mu_ui_credit_win);
    default: return 0;
    }
}

int mu_ui_probe_sprite(const mu_ui_sprite *s, uint32_t *out)
{
    int n = 0, i;
    out[n++] = (uint32_t)s->texture;
    out[n++] = fw(s->screen_height);
    out[n++] = fw(s->width);
    out[n++] = fw(s->height);
    for (i = 0; i < 4; ++i) {
        out[n++] = fw(s->position[i][0]);
        out[n++] = fw(s->position[i][1]);
    }
    for (i = 0; i < 4; ++i) {
        out[n++] = fw(s->texcoord[i][0]);
        out[n++] = fw(s->texcoord[i][1]);
    }
    out[n++] = fw(s->datum_x);
    out[n++] = fw(s->datum_y);
    out[n++] = (uint32_t)s->alpha | (uint32_t)s->red << 8 | (uint32_t)s->green << 16 | (uint32_t)s->blue << 24;
    out[n++] = (uint32_t)s->max_frame;
    out[n++] = (uint32_t)s->now_frame;
    out[n++] = (uint32_t)s->start_frame;
    out[n++] = (uint32_t)s->end_frame;
    out[n++] = s->tile;
    out[n++] = (uint32_t)s->sizing_datums;
    out[n++] = fw(s->scale_x);
    out[n++] = fw(s->scale_y);
    out[n++] = s->show;
    out[n++] = (uint32_t)s->has_frames;
    for (i = 0; i < (s->has_frames ? s->max_frame : 0) && i < MU_UI_SPRITE_MAX_FRAMES; ++i) {
        out[n++] = fw(s->frames[i][0]);
        out[n++] = fw(s->frames[i][1]);
    }
    return n;
}

int mu_ui_probe_button(const mu_ui_button *b, uint32_t *out)
{
    int n = mu_ui_probe_sprite(&b->sprite, out), i;
    out[n++] = (uint32_t)b->enable | (uint32_t)b->active << 8 | (uint32_t)b->click << 16 | (uint32_t)b->check << 24;
    for (i = 0; i < 8; ++i)
        out[n++] = (uint32_t)b->image_map[i];
    out[n++] = (uint32_t)b->has_text;
    if (b->has_text) {
        size_t length = strlen(b->text);
        out[n++] = (uint32_t)length;
        for (i = 0; i < (int)length; ++i)
            out[n++] = (uint8_t)b->text[i];
        out[n++] = (uint32_t)b->color_count;
        for (i = 0; i < b->color_count; ++i)
            out[n++] = b->text_colors[i];
        out[n++] = b->text_color;
    }
    out[n++] = fw(b->text_add_y);
    return n;
}

int mu_ui_probe_win(const mu_ui_win *w, uint32_t *out)
{
    int n = 0;
    out[n++] = (uint32_t)w->show | (uint32_t)w->active << 8 | (uint32_t)w->docking << 16;
    out[n++] = (uint32_t)w->state;
    out[n++] = (uint32_t)w->x;
    out[n++] = (uint32_t)w->y;
    out[n++] = (uint32_t)w->width;
    out[n++] = (uint32_t)w->height;
    out[n++] = (uint32_t)w->temp_x;
    out[n++] = (uint32_t)w->temp_y;
    out[n++] = (uint32_t)w->held_x;
    out[n++] = (uint32_t)w->held_y;
    out[n++] = (uint32_t)w->button_count;
    return n;
}

int mu_ui_probe_winex(const mu_ui_winex *w, uint32_t *out)
{
    int n = mu_ui_probe_win(&w->win, out), i;
    for (i = 0; i < 5; ++i)
        n += mu_ui_probe_sprite(&w->sprites[i], out + n);
    out[n++] = (uint32_t)w->line_max;
    out[n++] = (uint32_t)w->line_min;
    out[n++] = (uint32_t)w->lines;
    return n;
}

int mu_ui_probe_server_win(const mu_ui_server_win *w, uint32_t *out)
{
    int n = mu_ui_probe_win(&w->win, out), i;
    for (i = 0; i < MU_UI_SSW_GROUPS; ++i)
        n += mu_ui_probe_button(&w->groups[i], out + n);
    for (i = 0; i < MU_UI_SSW_SERVERS; ++i) {
        n += mu_ui_probe_button(&w->servers[i], out + n);
        n += mu_ui_probe_sprite(&w->gauges[i].bar, out + n);
        out[n++] = (uint32_t)w->gauges[i].rect[0];
        out[n++] = (uint32_t)w->gauges[i].rect[1];
        out[n++] = (uint32_t)w->gauges[i].rect[2];
        out[n++] = (uint32_t)w->gauges[i].rect[3];
        out[n++] = (uint32_t)w->gauges[i].x;
        out[n++] = (uint32_t)w->gauges[i].y;
    }
    for (i = 0; i < 2; ++i)
        n += mu_ui_probe_sprite(&w->decos[i], out + n);
    for (i = 0; i < 2; ++i)
        n += mu_ui_probe_sprite(&w->arrows[i], out + n);
    n += mu_ui_probe_winex(&w->description, out + n);
    out[n++] = (uint32_t)w->group_count;
    out[n++] = (uint32_t)w->left_count;
    out[n++] = (uint32_t)w->right_count;
    out[n++] = (uint32_t)w->server_count;
    out[n++] = (uint32_t)w->top_count;
    out[n++] = (uint32_t)w->selected;
    out[n++] = w->group && w->list ? (uint32_t)(w->group - w->list->groups) : 0xffffffffu;
    for (i = 0; i < 2 * MU_UI_SSW_TEXT_LINE; ++i)
        out[n++] = (uint8_t)w->text[i / MU_UI_SSW_TEXT_LINE][i % MU_UI_SSW_TEXT_LINE];
    return n;
}

int32_t mu_ui_probe_held(const mu_ui_ctx *ctx, const mu_ui_win *win)
{
    int i;
    if (ctx->held_button == NULL)
        return -1;
    for (i = 0; i < win->button_count; ++i)
        if (ctx->held_button == win->buttons[i])
            return i;
    return -2;
}

void mu_ui_probe_select(mu_ui_server_win *win, int32_t selected)
{
    win->selected = selected;
}

int mu_ui_probe_credit_win(const mu_ui_credit_win *w, uint32_t *out)
{
    int n = mu_ui_probe_win(&w->win, out), i;
    uint64_t bits;
    n += w->win.background ? mu_ui_probe_sprite(w->win.background, out + n) : 0;
    for (i = 0; i < 7; ++i)
        n += mu_ui_probe_sprite(&w->sprites[i], out + n);
    out[n++] = (uint32_t)w->image_state;
    memcpy(&bits, &w->image_timer, 8);
    out[n++] = (uint32_t)bits;
    out[n++] = (uint32_t)(bits >> 32);
    out[n++] = w->image;
    out[n++] = w->font;
    out[n++] = (uint32_t)w->next;
    out[n++] = (uint32_t)w->name_count;
    out[n++] = (uint32_t)w->rows[0];
    out[n++] = (uint32_t)w->rows[1];
    for (i = 0; i < 4; ++i)
        out[n++] = (uint32_t)w->names[i];
    for (i = 0; i < 3; ++i)
        out[n++] = (uint32_t)w->text_states[i];
    memcpy(&bits, &w->text_timer, 8);
    out[n++] = (uint32_t)bits;
    out[n++] = (uint32_t)(bits >> 32);
    return n;
}
