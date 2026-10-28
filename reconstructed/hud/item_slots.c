/* Reconstructed 3D item pass (see item_slots.h).  Float expressions keep the
 * client's operation order (binary32, no contraction). */
#include "item_slots.h"

#include <string.h>
#include "item3d_overrides.h"

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
    /* 0x016c1afc jumps outside the restored image for Box of Luck levels >7.
     * Preserve that evidence boundary; never guess the displaced compare. */
    int32_t level = in->level_word >> 3;
    if (in->code == 0x1c0b && level > 7)
        return MU_ITEM3D_SPECIAL;
    int32_t model = in->code + 0xae6;
    int32_t level_word = in->level_word;
    float angle[3];
    memcpy(angle, in->trs.rotation, sizeof angle);
    /* Data-like branches of 0x016c168a..0x016c222d, generated from instructions. */
    for (size_t i = 0; i < sizeof item3d_overrides / sizeof item3d_overrides[0]; ++i) {
        const struct item3d_override *r = &item3d_overrides[i];
        if (r->code != in->code || (r->level != -1 && r->level != level))
            continue;
        if (r->mask & 1u) model = r->model;
        if (r->mask & 2u) fx = r->values[0];
        if (r->mask & 4u) fy = r->values[1];
        for (int k = 0; k < 3; ++k)
            if (r->mask & (8u << k)) angle[k] = r->values[k + 2];
        if (r->mask & 64u) scale = r->values[5];
        if (r->mask & 128u) level_word = r->level_word;
        break;
    }
    /* 0x016c19f9: these attachments spin even without the hover selection. */
    if (in->code >= 0x1a47 && in->code <= 0x1a4b && !select)
        angle[1] = in->time * 0.2f;
    /* 0x016c219d: NewUI's special-item window +0x1c forces selection after no_select. */
    if (in->code == 0x1c64 && in->special_window_active)
        select = 1;
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
    out->level_word = level_word;
    out->excellent = in->excellent;
    out->set_bits = in->set_bits;
    out->select = select;
    out->a28 = in->a28;
    out->a2c = in->a2c;
    out->a30 = in->a30;
    out->scale = in->frame_scale * scale;
    out->a44 = in->a44;
    out->a48 = in->a48;
    memcpy(out->angle, angle, sizeof out->angle);
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

/* ---- RenderObjectScreen 0x016c2d82 ---- */

static int ros_player_posed(int32_t type)
{
    return (type >= 0x18e6 && type < 0x22e6) || type == 0xace || type == 0xacf || type == 0xad0 || type == 0xae5;
}

void mu_hud_object_screen(const mu_hud_ros_in *in, mu_hud_ros_out *out)
{
    memset(out, 0, sizeof *out);
    int32_t level = (in->level_word >> 3) & 0xf;                         /* 0x016c2dbd */
    int32_t level_word = in->level_word;
    if (in->has_record && in->kind_a == 0xc)                              /* 0x016c2de0 */
        level_word = 0;
    float position[3] = {in->position[0], in->position[1], in->position[2]};
    float scale = in->scale;
    if (in->held)                                                         /* 0x016c2e30 */
        scale = scale * 1.4f;
    if (in->select == 1) {                                                /* 0x016c2e4a */
        out->spin = 1;
        out->spin_angle = in->time * 0.2f;
    }
    int32_t type = in->type, pose = in->type;
    if (ros_player_posed(type)) {                                         /* 0x016c2e82 */
        pose = 0xa91;
    } else if (type == 0x26f2) {                                          /* 0x016c2ed6 (patched site) */
        if (level == 0)
            pose = type = 0x3890;
        else if (level == 2)
            pose = type = 0x3891;
    }
    out->pose_model = pose;
    out->render_type = type;
    if (!in->pose_model_exists)                                           /* 0x016c2f27 */
        return;
    out->drawn = 1;
    float height = 0.0f;                                                  /* 0x016c2f50 */
    int kind4 = in->has_record && in->item_kind == 4;
    if (type >= 0x18e6 && type < 0x1ae6) {
        height = -160.0f;
        if (kind4)
            height = height - 10.0f;
        if (type == 0x1927 || type == 0x192c)
            position[0] = position[0] + 0.04f;
        if (type >= 0x193b && type <= 0x1940)
            height = height + 10.0f;
    } else if (type >= 0x1ae6 && type < 0x1ce6) {
        height = -100.0f;
        if (kind4)
            height = height - 13.0f;
        if (type >= 0x1b3a && type <= 0x1b3f)
            height = height + 13.0f;
        if (type == 0x1b40)
            height = height - 32.0f;
    } else if (type >= 0x1ee6 && type < 0x20e6) {
        height = -70.0f;
    } else if (type >= 0x1ce6 && type < 0x1ee6) {
        height = -50.0f;
    }
    if (type == 0xace || type == 0xad0 || type == 0xacf || type == 0xae5)  /* 0x016c312c */
        height = -100.0f;
    out->height = height;
    if (in->anim_present && in->has_state) {                              /* 0x016c318e */
        out->action = in->anim_action;
        out->anim_frame = in->state_frame;
        out->anim_prior_frame = in->state_prior_frame;
        out->anim_prior_action = in->state_prior_action;
        if (in->tick) {
            out->ticked = 1;
            out->tick_speed = in->anim_speed;
        }
    }
    for (int k = 0; k < 3; ++k) {
        out->position[k] = position[k];
        out->light[k] = 1.0f;                                             /* 0x016c3364 */
    }
    out->scale = scale;
    out->alpha = in->object_alpha;
    out->lighting = 0;                                                    /* 0x016c32ca */
    out->level_word = level_word;
    out->excellent = in->excellent;
    out->set_bits = in->set_bits;
    out->a2c = in->a2c;
    out->a30 = in->a30;
}
