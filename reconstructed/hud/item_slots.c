/* Reconstructed 3D item pass (see item_slots.h).  Float expressions keep the
 * client's operation order (binary32, no contraction). */
#include "item_slots.h"

#include <string.h>

static float int_as_float(int32_t value)
{
    /* cvtsi2sd + unsigned correction (0x01bd3050 table) + cvtsd2ss */
    double d = (double)(uint32_t)value;
    return (float)d;
}

float mu_frame_x(int32_t align, float movie_x, int32_t screen_w)   /* 0x00aae509 */
{
    switch (align) {
    case 0: case 1: case 2: {
        float margin = (1024.0f - int_as_float(screen_w)) / 2.0f;
        return movie_x - margin;
    }
    case 3: case 5: case 7:
        return movie_x;
    case 4: case 6: case 8: {
        float margin = 1024.0f - int_as_float(screen_w);
        return movie_x - margin;
    }
    default:
        return 0.0f;
    }
}

float mu_frame_y(int32_t align, float movie_y, int32_t screen_h)   /* 0x00aae601 */
{
    switch (align) {
    case 0: case 3: case 4: {
        float margin = (768.0f - int_as_float(screen_h)) / 2.0f;
        return movie_y - margin;
    }
    case 1: case 5: case 6:
        return movie_y;
    case 2: case 7: case 8: {
        float margin = 768.0f - int_as_float(screen_h);
        return movie_y - margin;
    }
    default:
        return 0.0f;
    }
}

float mu_gfx_rate_x(int32_t screen_w)                  /* 0x00acb333 */
{
    return 640.0f / (float)screen_w;
}

float mu_gfx_rate_y(int32_t screen_h)
{
    return 480.0f / (float)screen_h;
}

int mu_slot_pass(const mu_slot_frame *frame, int32_t screen_w, int32_t screen_h, float rate_x, float rate_y,
                 mu_slot_color color, mu_slot_emit emit, void *user)   /* 0x00ab6130 */
{
    if (!frame->visible)
        return 0;
    uint8_t type8 = 0;
    for (int32_t p = 0; p < frame->page_count; p++) {
        const mu_slot_page *page = &frame->pages[p];
        const mu_grid *grid = page->grid;
        int32_t type = grid->type;                     /* 0x00abeca4 */
        uint8_t flag = grid->flag_48;                  /* 0x00ad5094 */
        if (type == 8)
            type8 = 1;
        for (int32_t i = 0; i < grid->item_count; i++) {   /* 0x00ad3c43, 0x00ad3fa4 */
            const mu_grid_item *item = grid->items[i];
            if (!item || item->code < 0)
                continue;
            float fx = mu_frame_x(frame->align, frame->movie_x, screen_w);
            float cx = (float)item->col * (page->cell_w + page->gap_x) + page->x;
            float x = (fx + cx * frame->scale) * rate_x;
            float fy = mu_frame_y(frame->align, frame->movie_y, screen_h);
            float cy = (float)item->row * (page->cell_h + page->gap_y) + page->y;
            float y = (fy + cy * frame->scale) * rate_y;
            float w = (float)item->width * page->cell_w * rate_x * frame->scale;
            float h = (float)item->height * page->cell_h * rate_y * frame->scale;
            if (color)
                color(user, 1.0f, 1.0f, 1.0f, frame->alpha);
            mu_slot_call call = {item, p, x, y, w, h, type, flag, type8, frame->frame_id};
            if (emit)
                emit(user, &call);
        }
    }
    return 1;
}

static const int32_t SPECIAL_CODES[] = {
    0x103b, 0x103c, 0x103d, 0x1049, 0x1053, 0x1088, 0x1a0b, 0x1a0e, 0x1a13, 0x1a14, 0x1a47, 0x1a48, 0x1a49,
    0x1a4a, 0x1a4b, 0x1c09, 0x1c0b, 0x1c0c, 0x1c15, 0x1c17, 0x1c18, 0x1c20, 0x1c21, 0x1c22, 0x1c2e, 0x1c30,
    0x1c64};

int mu_item3d_is_special(int32_t code)
{
    for (size_t i = 0; i < sizeof SPECIAL_CODES / sizeof SPECIAL_CODES[0]; i++)
        if (SPECIAL_CODES[i] == code)
            return 1;
    if (code >= 0x1c2e && code <= 0x1c30)
        return 1;
    return 0;
}

int mu_item3d(const mu_item3d_in *in, mu_item3d_out *out)   /* 0x016c154e */
{
    if (in->code == -1)
        return MU_ITEM3D_NONE;
    uint8_t select = in->select;
    if (!select && !in->gfx_busy && in->cursor_in && !in->flip_y) {
        if (in->ui_3e_visible)
            select = 1;
        else if (!in->ui_b602)
            select = 1;
    }
    if (in->no_select)
        select = 0;
    float fx = in->trs.offset_x, fy = in->trs.offset_y;
    float scale = !(0.0f >= in->scale_override) ? in->scale_override : in->trs.scale;
    if (mu_item3d_is_special(in->code))
        return MU_ITEM3D_SPECIAL;                      /* the special-case chain is not reconstructed */
    int32_t model = in->code + 0xae6;
    float x = in->x, y = in->y;
    if (in->code2_kind_b_6a && in->kind_a_22)
        y = y - in->h * scale;
    x = in->w * fx + x;
    if (in->flip_y)
        y = (1.0f - fy) * in->h + y;
    else
        y = in->h * fy + y;
    float z = -100.0f;
    if (in->kind_b_6a)
        z = -140.0f;
    else if (in->kind_a_22)
        z = -130.0f;
    memset(out, 0, sizeof *out);
    if (!in->flip_y) {                                 /* 0x0184a18f with the conversion flag */
        out->position[0] = x / in->rate_x;
        out->position[1] = (480.0f - y) / in->rate_y;
    } else {
        out->position[0] = x;
        out->position[1] = y;
    }
    out->position[2] = z;
    out->model = model;
    out->level_word = in->level_word;
    out->excellent = in->excellent;
    out->set_bits = in->set_bits;
    out->select = select;
    out->a28 = in->a28;
    out->a2c = in->a2c;
    out->a30 = in->a30;
    out->scale = in->frame_scale * scale;
    out->a44 = in->a44;
    out->a48 = in->a48;
    memcpy(out->angle, in->trs.rotation, sizeof out->angle);   /* 0x00cfc8f2 into 0x0b5e3c2c */
    return MU_ITEM3D_DRAW;
}

int mu_slot_wrapper(int item_present, const mu_slot_wrapper_in *in, const mu_item3d_in *sys,
                    mu_slot_wrapper_out *out)        /* 0x016c23d5 */
{
    memset(out, 0, sizeof *out);
    if (!item_present)
        return 0;
    if (in->a2c != 0 && in->frame_active && !in->gfx_busy && !in->gfx_cc && in->cursor_in && !in->a24) {
        out->status = 1;
        out->hover = 1;
        out->hover_rect[0] = (int32_t)in->x;
        out->hover_rect[1] = (int32_t)in->y;
        out->hover_rect[2] = (int32_t)in->w;
        out->hover_rect[3] = (int32_t)in->h;
    }
    out->element_value[0] = -1;
    out->element_value[1] = -1;
    if (in->element > -1 && in->element < 6)
        out->element_unmodelled = 1;
    mu_item3d_in *r = &out->item3d;
    *r = *sys;
    r->x = in->x;
    r->y = in->y;
    r->w = in->w;
    r->h = in->h;
    r->code = in->code;
    r->level_word = in->level_word;
    /* 0x00cd0995(1) answers 0 outside codes 0..0x2c00.  The client stores the
     * answer as a byte at [ebp-0x28] and pushes the whole word; its upper bytes
     * are whatever the stack held (zero here). */
    r->excellent = (in->code >= 0 && in->code <= 0x2c00) ? in->excellent : 0;
    r->set_bits = in->set_bits;
    r->a28 = in->a24;
    r->a2c = out->element_value[0];
    r->a30 = out->element_value[1];
    r->select = (uint8_t)in->a30;
    r->scale_override = in->a34;
    r->flip_y = (uint8_t)in->a3c;
    r->no_select = (uint8_t)in->a44;
    r->a44 = (int32_t)in->item_108;
    r->a48 = in->a40;
    r->code2 = -1;
    r->code2_kind_b_6a = 0;
    out->overlay_scale = 1.0f;
    return 1;
}
