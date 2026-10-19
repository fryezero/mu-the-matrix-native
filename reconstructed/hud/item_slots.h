/* Reconstructed 3D item pass of the GFx item windows (NATIVE-HUD-001).
 *
 * The GFx movie draws an item window's frame and empty slots.  After the
 * movie, the per-window pass 0x00abfcca sets glViewport(0, 0, W, H),
 * glOrtho(0, W, 0, H, 20, 2000), clears depth, sets glColor4f(1, 1, 1,
 * alpha) and calls the window's item render (vtable +0x20).  For the item
 * frames that is the slot pass 0x00ab6130, which walks the window's pages
 * (the grids of inv_grid.h) and calls the slot wrapper 0x016c23d5 per item,
 * which calls RenderItem3D 0x016c154e, which calls RenderObjectScreen
 * 0x016c2d82 (model render, not reconstructed here).
 *
 * Coordinates: the movie reports each page's slot geometry in screen
 * pixels through its "requestSlotInfo" callback (0x00abce9f): origin,
 * cell size and cell gap.  The frame's own position comes from the movie
 * position (+0x70/+0x74, in a 1024 x 768 design space) and the movie's
 * view alignment (Scaleform's nine anchors).  The slot pass converts to
 * 640 x 480 units with the GFx manager's rates 640/W and 480/H
 * (+0x2cc/+0x2d0, set by 0x00acb333); RenderItem3D converts back to window
 * pixels with the origin at the bottom (0x0184a18f).
 */
#ifndef MU_HUD_ITEM_SLOTS_H
#define MU_HUD_ITEM_SLOTS_H

#include <stdint.h>

#include "inv_grid.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Scaleform view alignments as returned by the movie view (vtable +0x78),
 * read by 0x00aaeadc. */
enum {
    MU_ALIGN_CENTER = 0, MU_ALIGN_TOP_CENTER, MU_ALIGN_BOTTOM_CENTER, MU_ALIGN_CENTER_LEFT, MU_ALIGN_CENTER_RIGHT,
    MU_ALIGN_TOP_LEFT, MU_ALIGN_TOP_RIGHT, MU_ALIGN_BOTTOM_LEFT, MU_ALIGN_BOTTOM_RIGHT
};

/* 0x00aae509: window x from the movie x (+0x70) and the alignment; an
 * alignment above 8 gives 0. */
float mu_frame_x(int32_t align, float movie_x, int32_t screen_w);
/* 0x00aae601: window y from the movie y (+0x74). */
float mu_frame_y(int32_t align, float movie_y, int32_t screen_h);

/* One page record of the item frame's vector at +0x78 (0x1c bytes). */
typedef struct mu_slot_page {
    const mu_grid *grid;        /* +0x00 */
    float x, y;                 /* +0x04, +0x08: slot origin from requestSlotInfo */
    float cell_w, cell_h;       /* +0x0c, +0x10 */
    float gap_x, gap_y;         /* +0x14, +0x18 */
} mu_slot_page;

typedef struct mu_slot_frame {
    int visible;                /* 0x00aadd42 (movie loaded, shown, not hidden) */
    int32_t align;              /* 0x00aaeadc */
    float movie_x, movie_y;     /* +0x70, +0x74 */
    float alpha;                /* +0x50 (0x00abedd2) */
    float scale;                /* +0x58 (0x00abedc3) */
    const mu_slot_page *pages;
    int32_t page_count;
    uint32_t frame_id;          /* the frame pointer passed on to the wrapper (opaque word) */
} mu_slot_frame;

/* Arguments of one slot-wrapper call 0x016c23d5 as the slot pass makes it. */
typedef struct mu_slot_call {
    const mu_grid_item *item;
    int32_t page;
    float x, y, w, h;           /* 640 x 480 units */
    int32_t page_type;          /* grid +0x44 */
    uint8_t page_flag;          /* grid +0x48 */
    uint8_t type8_seen;         /* 1 once any page so far had type 8 (never reset) */
    uint32_t frame_id;
} mu_slot_call;

typedef void (*mu_slot_color)(void *user, float r, float g, float b, float a);   /* glColor4f */
typedef void (*mu_slot_emit)(void *user, const mu_slot_call *call);

/* 0x00ab6130: returns 0 when the frame is not visible, else 1.  Per page and
 * item (code >= 0): glColor4f(1, 1, 1, alpha) then the wrapper call.  Item
 * sizes come from the grid items (Item.bmd width/height). */
int mu_slot_pass(const mu_slot_frame *frame, int32_t screen_w, int32_t screen_h, float rate_x, float rate_y,
                 mu_slot_color color, mu_slot_emit emit, void *user);

/* GFx manager rates (0x00acb333): 640/W and 480/H. */
float mu_gfx_rate_x(int32_t screen_w);
float mu_gfx_rate_y(int32_t screen_h);

/* ---- RenderItem3D 0x016c154e, general path ------------------------- */

/* Per-code render info (map 0x06fbb624+0x38, default record 0x06fbaa40;
 * filled from Data/Local/itemtrsdata.bmd by a loader outside the restored
 * code): slot offset factors, rotation (degrees) and scale. */
typedef struct mu_item_trs {
    float offset_x, offset_y;
    float rotation[3];
    float scale;
} mu_item_trs;

typedef struct mu_item3d_in {
    float x, y, w, h;           /* +0x08..+0x14: 640 x 480 units */
    int32_t code;               /* +0x18 */
    int32_t level_word;         /* +0x1c: item object +0x14 (level << 3 | options) */
    int32_t excellent;          /* +0x20 */
    int32_t set_bits;           /* +0x24 */
    int32_t a28, a2c, a30;      /* passed through */
    uint8_t select;             /* +0x34: forced selection */
    float scale_override;       /* +0x38: used when > 0 */
    uint8_t flip_y;             /* +0x3c: offset from the bottom; also disables the hover test */
    uint8_t no_select;          /* +0x40 */
    int32_t a44, a48;           /* passed through */
    int32_t code2;              /* +0x4c: code tested for kind B 0x6a in the first tail test */
    /* Inputs the client reads from other systems: */
    uint8_t gfx_busy;           /* GFx manager +0xd4 -> 0x00c08654 != 0 */
    uint8_t cursor_in;          /* 0x00ec4bf2(int x, int y, int w, int h): cursor inside */
    uint8_t ui_3e_visible;      /* NewUI window 0x3e visible (0x00f2aba9) */
    uint8_t ui_b602;            /* 0x00f2b602 */
    uint8_t kind_b_6a, kind_a_22;          /* code has kind B 0x6a / kind A 0x22 */
    uint8_t code2_kind_b_6a;    /* code2 has kind B 0x6a */
    mu_item_trs trs;            /* the render info found for code */
    float frame_scale;          /* GFx manager +0xa0 -> +0x58 */
    float rate_x, rate_y;       /* GFx manager +0x2cc, +0x2d0 */
} mu_item3d_in;

/* RenderObjectScreen 0x016c2d82 arguments. */
typedef struct mu_item3d_out {
    int32_t model;              /* code + 0xae6 on the general path */
    int32_t level_word, excellent, set_bits;
    float position[3];          /* window pixels, origin bottom left; z -100/-130/-140 */
    uint8_t select;
    int32_t a28, a2c, a30;
    float scale;
    int32_t a44, a48;
    float angle[3];             /* the item angle global 0x0b5e3c2c at the call */
} mu_item3d_out;

enum { MU_ITEM3D_NONE = 0, MU_ITEM3D_DRAW = 1, MU_ITEM3D_SPECIAL = 2 };

/* Returns NONE for code -1, SPECIAL for the 27 codes with model/offset
 * special cases (not reconstructed; one of them runs through a runtime
 * patch), DRAW with *out filled otherwise. */
int mu_item3d(const mu_item3d_in *in, mu_item3d_out *out);
/* 1 when `code` is one of RenderItem3D's special-case codes. */
int mu_item3d_is_special(int32_t code);

/* ---- slot wrapper 0x016c23d5 ------------------------------------- */

typedef struct mu_slot_wrapper_in {
    /* item object fields */
    int32_t code;               /* +0x10 */
    int32_t level_word;         /* +0x14 */
    uint8_t set_bits;           /* +0x3b */
    uint8_t excellent;          /* item +0x98 == 1 (0x00cd0995(1) also needs code 0..0x2c00) */
    int32_t element;            /* +0x84: 0..5 selects a per-code element record (not reconstructed) */
    uint32_t item_108;          /* address of item +0x108 (passed on as an opaque word) */
    /* wrapper arguments as the slot pass passes them */
    float x, y, w, h;
    int32_t a1c, a20, a24, a28;
    uint32_t a2c;               /* frame */
    int32_t a30;
    float a34;
    int32_t a38, a3c, a40, a44;
    /* other systems */
    uint8_t frame_active;       /* GFx manager +0x2e4 == frame */
    uint8_t gfx_busy;           /* +0xd4 -> 0x00c08654 */
    uint8_t gfx_cc;             /* +0xcc -> 0x00aae6f9 */
    uint8_t cursor_in;          /* 0x00ec4bf2 */
} mu_slot_wrapper_in;

typedef struct mu_slot_wrapper_out {
    uint8_t status;             /* 0x00c94193(item, a1c, a38) was called */
    uint8_t hover;              /* 0x00cda1cf(item, frame, (int)x, (int)y, (int)w, (int)h, a1c, a20, a28, 0) */
    int32_t hover_rect[4];
    int32_t element_value[2];   /* RenderItem3D +0x2c/+0x30: -1 unless the element record applies */
    uint8_t element_unmodelled; /* element in 0..5: the record lookup is not reconstructed */
    mu_item3d_in item3d;        /* inputs filled from the wrapper (other-system fields copied from `sys`) */
    float overlay_scale;        /* 0x016bf1fb gets 1.0f here */
} mu_slot_wrapper_out;

/* Fills the RenderItem3D arguments the wrapper passes; `sys` supplies the
 * fields of mu_item3d_in that come from other systems (cursor, kinds, render
 * info, rates).  Returns 0 without calls for a null item (`item_present` 0). */
int mu_slot_wrapper(int item_present, const mu_slot_wrapper_in *in, const mu_item3d_in *sys,
                    mu_slot_wrapper_out *out);

/* ---- RenderObjectScreen 0x016c2d82 (NATIVE-FIDELITY-001) ------------
 * The item model of an inventory cell, a hotkey or the held item:
 *   level = (level word >> 3) & 15; kind A 0xc (0x00cd5fac): the level word passed on is 0
 *   held (arg 7): scale *= 1.4; select == 1: item angle [1] (0x0b5e3c2c) = time * 0.2
 *   pose model (0x0b5e3b24) = type; armour parts 0x18e6..0x22e5 and 0xace/0xacf/0xad0/0xae5 pose the
 *     Player model 0xa91; type 0x26f2 by level: 0 -> 0x3890, 2 -> 0x3891 (also the drawn type).
 *     The compare at 0x016c2ed6 is a runtime-patched jump in the capture; its leftover bytes
 *     (0b f2 26 00 00) are the tail of `cmp dword ptr [0x0b5e3b24], 0x26f2` (inferred, as RenderPartObject's
 *     own 0x26f2 rule 0x017e645f).
 *   no pose model: return.  Pose-model height +0x90 by the drawn type: helms 0x18e6..0x1ae5 -160 (record type
 *     +0x252 == 4: -10 more; 0x193b..0x1940 +10; 0x1927/0x192c: position x += 0.04), armours 0x1ae6..0x1ce5 -100
 *     (type 4: -13; 0x1b3a..0x1b3f +13; 0x1b40 -32), gloves 0x1ee6..0x20e5 -70, pants 0x1ce6..0x1ee5 -50,
 *     else 0; 0xace/0xacf/0xad0/0xae5 -100.
 *   InvenItemAnimation (Lang.mpr table 0x06fbc830, lookup 0x0111d824 by code): with a record and the item's
 *     animation state (arg 11, item +0x108): pose action +0xa8 = record +8, Animation(0x06fce398, state +4,
 *     state +8, state +2, angle, head angle, 0, 0) and, when arg 12 is set, the tick 0x012b4dd3(state +4,
 *     +8, +2, record +0xc speed, 0x0b5e3c20, angle); otherwise action 0 and Animation(..., 0, 0, 0, ...).
 *   the object: a stack CHARACTER (0x0129d272), its object's type = the drawn type, ItemObjectAttribute
 *     0x016da00b, then +5 (LightEnable) = 0, scale +0xa0 = scale, position = arg 5, light (1, 1, 1);
 *     RenderPartObject(o, type, 0, light, o alpha, level word, excellent, set bits, 1, 1, 1, 0, 2, a2c, a30, 0).
 * RenderPartObject 0x017e63f4 then copies +5 into the model's lighting byte +0x50 (cleared: one flat colour),
 * runs the body light 0x017ec3d8 and Transform with the constants 0.4 / 0.8 / 0.2, and RenderObjDraw sets the
 * body colour from the light argument (1, 1, 1) (static readings; RenderObjDraw is verified). */
typedef struct mu_hud_ros_in {
    int32_t type;               /* arg 1: model index (code + 0xae6 on RenderItem3D's general path) */
    int32_t level_word;         /* arg 2 */
    int32_t excellent, set_bits;/* args 3, 4 */
    float position[3];          /* arg 5 */
    int32_t select;             /* arg 6 */
    uint8_t held;               /* arg 7 */
    int32_t a2c, a30;           /* args 8, 9 */
    float scale;                /* arg 10 */
    int32_t has_state;          /* arg 11 != NULL */
    uint16_t state_prior_action;/* state +2 */
    float state_frame, state_prior_frame; /* state +4, +8 */
    uint8_t tick;               /* arg 12 */
    float time;                 /* 0x06fce370 */
    int32_t has_record;         /* the type's Item.bmd record (0x00cd5d29 on type - 0xae6) */
    int32_t kind_a;             /* record +0x250 */
    int32_t item_kind;          /* record +0x252 */
    int32_t anim_present;       /* InvenItemAnimation has the code */
    uint16_t anim_action;       /* its record +8 */
    float anim_speed;           /* its record +0xc */
    int32_t pose_model_exists;  /* the model getter's answer for the pose model */
    float object_alpha;         /* object +0xdc after ItemObjectAttribute */
} mu_hud_ros_in;

typedef struct mu_hud_ros_out {
    int32_t drawn;              /* 0: no pose model (nothing after the model getter) */
    int32_t spin;               /* the item angle [1] was set */
    float spin_angle;
    int32_t pose_model, render_type;
    float height;               /* pose model +0x90 */
    uint16_t action;            /* pose model +0xa8 */
    float anim_frame, anim_prior_frame;
    uint16_t anim_prior_action;
    int32_t ticked;
    float tick_speed;
    float position[3];          /* object +0x158 (x may gain 0.04) */
    float scale;                /* object +0xa0 */
    float alpha;
    float light[3];
    uint8_t lighting;           /* object +5 */
    int32_t level_word, excellent, set_bits, a2c, a30;
} mu_hud_ros_out;

void mu_hud_object_screen(const mu_hud_ros_in *in, mu_hud_ros_out *out);

#ifdef __cplusplus
}
#endif

#endif
