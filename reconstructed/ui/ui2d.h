/* Reconstructed 2D interface layer of the pinned Mu The Matrix client
 * (NATIVE-UI-001).  Every routine names the client function it restates.
 *
 * OpenGL and Windows calls are platform boundaries: the code emits them
 * through mu_ui_sink in the client's exact order with the client's exact
 * argument values, and a caller (the native software renderer, the
 * validator's recorder) gives them meaning.  Client globals live in
 * mu_ui_state; their client addresses are listed next to each field.
 *
 * Arithmetic follows the client's scalar SSE code in source order; build with
 * -ffp-contract=off.
 */
#ifndef MU_UI2D_H
#define MU_UI2D_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Platform calls, in client order.  Words are 32-bit argument words in call
 * order; floats are passed as their bit patterns and doubles as two words
 * (low, high).  For MU_GL_TEXIMAGE2D the ninth word is zero and data/bytes
 * describe the uploaded pixels. */
enum mu_ui_op {
    MU_GL_MATRIXMODE = 1, MU_GL_PUSHMATRIX, MU_GL_POPMATRIX, MU_GL_LOADIDENTITY, MU_GL_VIEWPORT,
    MU_GL_BEGIN, MU_GL_END, MU_GL_VERTEX2F, MU_GL_TEXCOORD2F, MU_GL_COLOR4F, MU_GL_COLOR3F,
    MU_GL_COLOR4UB, MU_GL_BINDTEXTURE, MU_GL_ENABLE, MU_GL_DISABLE, MU_GL_BLENDFUNC, MU_GL_DEPTHMASK,
    MU_GL_TEXIMAGE2D, MU_GL_TEXPARAMETERI, MU_GL_TEXENVF, MU_GL_GENTEXTURES, MU_GL_CLEAR,
    MU_GL_CLEARCOLOR, MU_GLU_PERSPECTIVE, MU_GLU_ORTHO2D,
    MU_GDI_SETBKCOLOR, MU_GDI_SETTEXTCOLOR, MU_GDI_TEXTOUT, MU_GDI_GETTEXTEXTENT,
    /* NATIVE-UI-002: SelectObject(font DC, font handle) from the text facade's
     * SetFont, a sound request (PlayBuffer id), and a client event the UI
     * hands to game logic (enum mu_ui_event; words after the code are its
     * arguments).  Renderers ignore the last two. */
    MU_GDI_SELECTOBJECT, MU_UI_SOUND, MU_UI_EVENT,
    MU_UI_OP_COUNT
};

typedef struct mu_ui_sink {
    void *user;
    void (*call)(void *user, int op, const uint32_t *words, int count, const void *data, size_t bytes);
} mu_ui_sink;

/* The client's per-texture record (BITMAP_t, 0x222 bytes) fields used here. */
typedef struct mu_ui_bitmap {
    uint32_t index;         /* +0x000 */
    float width, height;    /* +0x204, +0x208: power-of-two texture size */
    int32_t image_width;    /* +0x20c: decoded image size */
    int32_t image_height;   /* +0x210 */
    uint8_t components;     /* +0x214: 3 (JPEG) or 4 (TGA) */
    uint32_t texture;       /* +0x215: GL texture name */
    uint8_t *buffer;        /* +0x21a: kept only for a few indices (font 0x7532) */
} mu_ui_bitmap;

typedef mu_ui_bitmap *(*mu_ui_lookup)(void *user, uint32_t index);

typedef struct mu_ui_state {
    mu_ui_sink sink;
    uint32_t window_width;   /* 0x01cf1624 */
    uint32_t window_height;  /* 0x01cf1628 */
    float znear;             /* 0x01cf162c */
    float zfar;              /* 0x01cf1630 */
    float fov;               /* 0x01cf1634 */
    int32_t bound_texture;   /* 0x01cf1620: BindTexture cache */
    uint8_t alpha_test;      /* 0x0bdc58b5 */
    uint8_t fog;             /* 0x0bdc597c */
    uint8_t texture_2d;      /* 0x0bdc597d */
    uint8_t depth_test;      /* 0x0bdc597e */
    uint8_t cull_face;       /* 0x0bdc597f */
    uint8_t depth_mask;      /* 0x0bdc5980 */
    int32_t blend_mode;      /* 0x0bdc58c4 */
    float screen_rate_x;     /* 0x06fbcd94 */
    float screen_rate_y;     /* 0x06fbcd98 */
    mu_ui_lookup lookup;     /* Bitmaps.GetTexture 0x00ebbec8 / FindTexture 0x00c97ce3 */
    void *lookup_user;
} mu_ui_state;

/* Initial state as the client leaves it after its 3D camera setup
 * 0x0184adc7: texture, depth test, cull face and depth mask enabled, alpha
 * test, blend and fog off.  Window size and screen rates are inputs. */
void mu_ui_state_init(mu_ui_state *state, uint32_t window_width, uint32_t window_height);

/* ---- small helpers ---------------------------------------------------- */
float mu_ui_convert_x(const mu_ui_state *state, float x);   /* 0x01850636 */
float mu_ui_convert_y(const mu_ui_state *state, float y);   /* 0x01850679 */
int32_t mu_ui_cvtt(float value);                             /* cvttss2si */

/* ---- GL state wrappers 0x0184a6b7..0x0184acf6 ------------------------- */
void mu_ui_enable_depth_test(mu_ui_state *state);    /* 0x0184a6b7 */
void mu_ui_disable_depth_test(mu_ui_state *state);   /* 0x0184a6da */
void mu_ui_enable_cull_face(mu_ui_state *state);     /* 0x0184a6fd */
void mu_ui_disable_cull_face(mu_ui_state *state);    /* 0x0184a720 */
void mu_ui_enable_depth_mask(mu_ui_state *state);    /* 0x0184a743 */
void mu_ui_disable_depth_mask(mu_ui_state *state);   /* 0x0184a763 */
void mu_ui_disable_texture(mu_ui_state *state, int alpha_test);   /* 0x0184a783 */
void mu_ui_disable_alpha_blend(mu_ui_state *state);  /* 0x0184a7f3 */
void mu_ui_enable_alpha_test(mu_ui_state *state, int depth_mask); /* 0x0184a990 */
void mu_ui_enable_alpha_blend(mu_ui_state *state);   /* 0x0184aa2b */
void mu_ui_bind_texture(mu_ui_state *state, int32_t index);       /* 0x0184acf6 */

/* ---- 2D projection ------------------------------------------------------ */
void mu_ui_begin_bitmap(mu_ui_state *state);   /* 0x0184f793 */
void mu_ui_end_bitmap(mu_ui_state *state);     /* 0x0184f8d7 */

/* ---- 2D quads ------------------------------------------------------------ */
void mu_ui_render_bitmap(mu_ui_state *state, int32_t texture, float x, float y, float width, float height,
                         float u, float v, float u_width, float v_height, int scale, int start_scale,
                         float alpha);                                        /* 0x0184dcb1 */
void mu_ui_render_color(mu_ui_state *state, float x, float y, float width, float height, float alpha,
                        int32_t mode);                                        /* 0x0184d9bb */
void mu_ui_end_render_color(mu_ui_state *state);                              /* 0x0184dc62 */
/* RenderColorBitmap 0x0184e01a (also reached through 0x00ec52a9): always
 * 640x480 units, per-vertex glColor4ub(color & 0xff, ..., color >> 24). */
void mu_ui_render_color_bitmap(mu_ui_state *state, int32_t texture, float x, float y, float width, float height,
                               float u, float v, float u_width, float v_height, uint32_t color);

/* ---- CSprite (0xa8 bytes; vtable 0x01ab9ba8) ----------------------------- */
enum { MU_UI_SPRITE_MAX_FRAMES = 16 };
typedef struct mu_ui_sprite {
    float screen_height;      /* +0x08: window height / scale y */
    mu_ui_bitmap *bitmap;     /* +0x0c */
    int32_t texture;          /* +0x10 */
    float width, height;      /* +0x14, +0x18 */
    float position[4][2];     /* +0x1c: corners (x, y) in unscaled GL space */
    float texcoord[4][2];     /* +0x3c */
    float datum_x, datum_y;   /* +0x5c, +0x60 */
    uint8_t alpha, red, green, blue;  /* +0x64..+0x67 */
    int32_t max_frame;        /* +0x68 */
    int32_t now_frame;        /* +0x6c */
    uint8_t tile;             /* +0x98 */
    int32_t sizing_datums;    /* +0x9c: bit 0 bottom anchor, bit 1 right anchor */
    float scale_x, scale_y;   /* +0x90, +0x94 */
    uint8_t show;             /* +0xa0 */
    /* Frame animation (NATIVE-UI-002); the client keeps the frame table in a
     * new[] block at +0x78, here it is inline. */
    int32_t start_frame;      /* +0x70 */
    int32_t end_frame;        /* +0x74 */
    int has_frames;           /* +0x78 != NULL */
    float frames[MU_UI_SPRITE_MAX_FRAMES][2];  /* texture coordinates of each frame's top-left corner */
    uint8_t repeat;           /* +0x7c */
    double interval;          /* +0x80: frame time (ms) */
    double elapsed;           /* +0x88 */
} mu_ui_sprite;

void mu_ui_sprite_init(mu_ui_sprite *sprite);                                 /* 0x010ad7b2 */
/* Create without frame coordinates (the only form the title scene uses). */
void mu_ui_sprite_create(mu_ui_state *state, mu_ui_sprite *sprite, int32_t width, int32_t height,
                         int32_t texture, int32_t datum_x, int32_t datum_y, int tile, int32_t sizing_datums,
                         float scale_x, float scale_y);                       /* 0x010ad847 */
/* The full Create 0x010ad847: max_frame frames whose top-left texel
 * positions are frame_xy[i] (x, y), at most MU_UI_SPRITE_MAX_FRAMES. */
void mu_ui_sprite_create_frames(mu_ui_state *state, mu_ui_sprite *sprite, int32_t width, int32_t height,
                                int32_t texture, int32_t max_frame, const int32_t (*frame_xy)[2], int32_t datum_x,
                                int32_t datum_y, int tile, int32_t sizing_datums, float scale_x, float scale_y);
/* SImgInfo {texture, x, y, width, height} as passed to 0x010adc87. */
typedef struct mu_ui_image_info {
    int32_t texture, x, y, width, height;
} mu_ui_image_info;
void mu_ui_sprite_create_image(mu_ui_state *state, mu_ui_sprite *sprite, const mu_ui_image_info *info,
                               int32_t datum_x, int32_t datum_y, int tile, int32_t sizing_datums, float scale_x,
                               float scale_y);                                 /* 0x010adc87 */
void mu_ui_sprite_set_action(mu_ui_sprite *sprite, int32_t start, int32_t end, double interval, int repeat); /* 0x010ae3a1 */
void mu_ui_sprite_set_now_frame(mu_ui_sprite *sprite, int32_t frame);      /* 0x010ae3eb */
void mu_ui_sprite_update(mu_ui_sprite *sprite, double delta);              /* 0x010ae557 */
/* PtInSprite 0x010ae2a5 (the cursor test of CursorInObject 0x010ae375). */
int mu_ui_sprite_contains(const mu_ui_sprite *sprite, int32_t x, int32_t y);
int32_t mu_ui_sprite_x(const mu_ui_sprite *sprite);       /* 0x00986f2e */
int32_t mu_ui_sprite_y(const mu_ui_sprite *sprite);       /* 0x00986f46 */
int32_t mu_ui_sprite_width(const mu_ui_sprite *sprite);   /* 0x00986f01 */
int32_t mu_ui_sprite_height(const mu_ui_sprite *sprite);  /* 0x00986ed4 */
int32_t mu_ui_sprite_texture_height(const mu_ui_sprite *sprite);  /* 0x0120ddd5 */
void mu_ui_sprite_show(mu_ui_sprite *sprite, int show);   /* 0x00986f8a */
void mu_ui_sprite_set_position(mu_ui_sprite *sprite, int32_t x, int32_t y, int32_t which); /* 0x010add3c */
void mu_ui_sprite_set_size(mu_ui_sprite *sprite, int32_t width, int32_t height, int32_t which); /* 0x010adfe4 */
void mu_ui_sprite_render(mu_ui_state *state, const mu_ui_sprite *sprite);     /* 0x010ae63d */

/* ---- CGaugeBar (0xd0 bytes) ------------------------------------------- */
typedef struct mu_ui_gauge {
    mu_ui_sprite bar;          /* +0x08 */
    int32_t rect[4];           /* +0xb0: left, top, right, bottom */
    int has_back;              /* +0xc0 != 0 (unused by the title scene) */
    int32_t x, y;              /* +0xc8, +0xcc */
} mu_ui_gauge;

void mu_ui_gauge_create(mu_ui_state *state, mu_ui_gauge *gauge, int32_t width, int32_t height, int32_t texture,
                        const int32_t *rect, int fixed_left, float scale_x, float scale_y); /* 0x00aac99a */
void mu_ui_gauge_set_position(mu_ui_gauge *gauge, int32_t x, int32_t y);      /* 0x00aacbdd */
void mu_ui_gauge_set_value(mu_ui_gauge *gauge, uint32_t now, uint32_t total);  /* 0x00aacceb */
void mu_ui_gauge_render(mu_ui_state *state, const mu_ui_gauge *gauge);        /* 0x00aacfd6 */
void mu_ui_gauge_show(mu_ui_gauge *gauge, int show);                           /* 0x00aacf9e (no back sprite) */

/* ---- Title scene (CreateTitleSceneUI 0x011e230d, Render 0x011e2c8c) ---- */
enum { MU_UI_TITLE_SPRITES = 13 };
typedef struct mu_ui_title {
    mu_ui_sprite sprites[MU_UI_TITLE_SPRITES];
    mu_ui_gauge gauge;
} mu_ui_title;

/* screen_width/height: CInput screen size (0x009828b5 / 0x009828a6). */
void mu_ui_title_create(mu_ui_state *state, mu_ui_title *title, int32_t screen_width, int32_t screen_height);
/* Render body between the GL calls the client makes; progress now/total. */
void mu_ui_title_render(mu_ui_state *state, mu_ui_title *title, uint32_t now, uint32_t total);

#ifdef __cplusplus
}
#endif
#endif
