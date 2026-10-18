/* Reconstructed legacy window/widget layer of the pinned client (NATIVE-UI-002).
 *
 * The client's pre-GFx interface is a small class family drawn with the 2D
 * routines of ui2d.h:
 *
 *   CSprite   (ui2d.h)      textured quad with frames, hit test PtInSprite
 *   CButton   0xe0 bytes    CSprite + enable/active/click/check state, an
 *                           image map (frame per state) and optional text
 *   CWin      0x3c bytes    window rectangle, optional background sprite,
 *                           registered buttons, drag state; virtual methods
 *   CWinEx    CWin + a 5-sprite frame (background, top, bottom, left, right)
 *                           whose height is a number of texture lines
 *
 * Every routine names the client function it restates.  Virtual methods are
 * function pointers in mu_ui_win_class, in the client's vtable order.  The
 * client's singletons (CInput, the text facade g_pRenderText, the font
 * handles, CButton's held-button pointer, GlobalText) are passed in mu_ui_ctx.
 */
#ifndef MU_UI_WIDGET_H
#define MU_UI_WIDGET_H

#include "ui2d.h"
#include "ui_text.h"

#ifdef __cplusplus
extern "C" {
#endif

/* CInput (instance 0x01ec79a8) fields read by the widgets. */
typedef struct mu_ui_input {
    int32_t cursor_x, cursor_y;       /* +0x0c, +0x10: window pixels, origin top left */
    uint8_t lbutton_down;             /* +0x1c: left button went down this frame */
    uint8_t lbutton_up;               /* +0x1e: left button went up this frame */
    int32_t screen_width;             /* +0x28 */
    int32_t screen_height;            /* +0x2c */
} mu_ui_input;

/* HFONT handles created by CreateFonts 0x0182a0da. */
typedef struct mu_ui_fonts {
    uint32_t normal;                  /* 0x06fc9ca4 */
    uint32_t bold;                    /* 0x06fc9ca8 */
    uint32_t big;                     /* 0x06fc9cac */
    uint32_t fixed;                   /* 0x06fc9cb0: 12 px, GlobalText[18] face */
} mu_ui_fonts;

typedef const char *(*mu_ui_global_text)(void *user, int32_t index);

/* Platform services the windows ask for besides drawing: a GDI font
 * (CreateFontA, returns the handle) and a texture load (LoadBitmap). */
typedef struct mu_ui_platform {
    void *user;
    uint32_t (*create_font)(void *user, int32_t height, int32_t weight, uint32_t charset, int32_t quality,
                            const char *face);
    void (*load_bitmap)(void *user, const char *path, uint32_t index, uint32_t filter, uint32_t wrap);
} mu_ui_platform;

typedef struct mu_ui_ctx {
    mu_ui_state *state;
    mu_ui_text *text;                 /* the CUIRenderTextOriginal behind g_pRenderText */
    mu_ui_input input;
    mu_ui_fonts fonts;
    const void *held_button;          /* CButton::s_pBtnHeld 0x01d1dc2c */
    mu_ui_global_text global_text;    /* GlobalText[index] (Data\Lang.mpr, an input) */
    void *global_text_user;
    mu_ui_platform platform;
    uint32_t charset;                 /* the font character set byte 0x01cf0c20 */
} mu_ui_ctx;

/* Client events handed to game logic through MU_UI_EVENT. */
enum mu_ui_event {
    MU_UI_EVENT_SERVER_GROUP = 1,     /* a server group button was chosen: (button index); the client then
                                         asks the server for the list (network, not reconstructed) */
    MU_UI_EVENT_SERVER_CONNECT = 2,   /* a server button was chosen: (server slot); the client hides the
                                         window and starts connecting (network, not reconstructed) */
    MU_UI_EVENT_HIDE_WINDOW = 3,      /* CUIMng::HideWin(window) requested by a window */
    MU_UI_EVENT_CREDITS_DONE = 4,     /* the credits reached their end record: the client sends a request
                                         (network, not reconstructed) and switches the music */
    MU_UI_EVENT_MUSIC_STOP = 5,       /* 0x0120f5a0 with music table entry (argument) 0x01cf1680[i] */
    MU_UI_EVENT_MUSIC_PLAY = 6        /* 0x0120f602 with music table entry (argument) */
};

/* Text facade calls (g_pRenderText 0x011a07b2 wrappers). */
void mu_ui_ctx_set_font(mu_ui_ctx *ctx, uint32_t font);              /* 0x011a0a4e -> SelectObject */
void mu_ui_ctx_set_text_color(mu_ui_ctx *ctx, uint32_t color);       /* 0x011a09ca (r | g<<8 | b<<16 | a<<24) */
void mu_ui_ctx_set_back_color(mu_ui_ctx *ctx, uint32_t color);       /* 0x011a0a25 */
void mu_ui_ctx_render_text(mu_ui_ctx *ctx, int32_t x, int32_t y, const char *string, int32_t box_width,
                           int32_t box_height, int32_t sort);         /* 0x011a0a77 */
const char *mu_ui_ctx_global_text(mu_ui_ctx *ctx, int32_t index);     /* 0x0095f027 */
void mu_ui_ctx_event(mu_ui_ctx *ctx, int32_t event, int32_t argument);

/* ---- CButton (vtable 0x01a7e46c) --------------------------------------- */
enum {
    MU_UI_BTN_UP, MU_UI_BTN_DOWN, MU_UI_BTN_OVER, MU_UI_BTN_DISABLE,
    MU_UI_BTN_CHECK_UP, MU_UI_BTN_CHECK_DOWN, MU_UI_BTN_CHECK_OVER, MU_UI_BTN_CHECK_DISABLE
};
enum { MU_UI_BUTTON_TEXT_MAX = 128 };

typedef struct mu_ui_button {
    mu_ui_sprite sprite;
    uint8_t enable;                   /* +0xa8 */
    uint8_t active;                   /* +0xa9: hit testing on */
    uint8_t click;                    /* +0xaa: released over the button this frame */
    uint8_t check;                    /* +0xab */
    int32_t image_map[8];             /* +0xac: frame per MU_UI_BTN_* state */
    int has_text;                     /* +0xcc != NULL */
    char text[MU_UI_BUTTON_TEXT_MAX];
    int color_count;                  /* +0xd0: 4, or 8 when the button has check frames */
    uint32_t text_colors[8];
    uint32_t text_color;              /* +0xd4 */
    float text_add_y;                 /* +0xd8: 0.5, 1.5 while pressed */
} mu_ui_button;

void mu_ui_button_init(mu_ui_button *button);                                     /* 0x00986569 */
void mu_ui_button_create(mu_ui_ctx *ctx, mu_ui_button *button, int32_t width, int32_t height, int32_t texture,
                         int32_t max_frame, int32_t down, int32_t over, int32_t disable, int32_t check_up,
                         int32_t check_down, int32_t check_over, int32_t check_disable); /* 0x009865f4 */
void mu_ui_button_release(mu_ui_button *button);                                  /* 0x009865e2 */
void mu_ui_button_set_text(mu_ui_button *button, const char *text, const uint32_t *colors); /* 0x00986d95 */
void mu_ui_button_show(mu_ui_button *button, int show);                           /* 0x00986d49 */
int mu_ui_button_cursor_in(const mu_ui_ctx *ctx, const mu_ui_button *button);    /* 0x00986d72 */
void mu_ui_button_update(mu_ui_ctx *ctx, mu_ui_button *button, double delta);     /* 0x009867e3 */
void mu_ui_button_render(mu_ui_ctx *ctx, const mu_ui_button *button);            /* 0x00986bbd */

/* ---- CWin (vtable 0x01ac7468) ------------------------------------------ */
enum { MU_UI_WIN_MAX_BUTTONS = 64 };
enum { MU_UI_WA_ALL = 0, MU_UI_WA_MOVE = 2, MU_UI_WA_BUTTON = 3, MU_UI_WA_RESIZE_BOTTOM = 4, MU_UI_WA_RESIZE_TOP = 5 };
enum { MU_UI_WS_NORMAL = 0, MU_UI_WS_MOVE = 2, MU_UI_WS_RESIZE_TOP = 3, MU_UI_WS_RESIZE_BOTTOM = 4 };

typedef struct mu_ui_win mu_ui_win;
typedef struct mu_ui_win_class {
    void (*release)(mu_ui_ctx *, mu_ui_win *);                              /* slot 1 */
    void (*release_controls)(mu_ui_ctx *, mu_ui_win *);                     /* slot 8 */
    void (*set_position)(mu_ui_ctx *, mu_ui_win *, int32_t x, int32_t y);   /* slot 2 */
    int (*cursor_in_win)(mu_ui_ctx *, mu_ui_win *, int32_t area);            /* slot 3 */
    void (*show)(mu_ui_ctx *, mu_ui_win *, int show);                        /* slot 4 */
    void (*render)(mu_ui_ctx *, mu_ui_win *);                                /* slot 6 */
    int (*cursor_in_controls)(mu_ui_ctx *, mu_ui_win *);                     /* slot 9 */
    void (*update_while_show)(mu_ui_ctx *, mu_ui_win *, double);             /* slot 10 */
    void (*check_additional_state)(mu_ui_ctx *, mu_ui_win *);                /* slot 11 */
    void (*update_while_active)(mu_ui_ctx *, mu_ui_win *, double);           /* slot 12 */
    void (*render_controls)(mu_ui_ctx *, mu_ui_win *);                       /* slot 13 */
} mu_ui_win_class;

struct mu_ui_win {
    const mu_ui_win_class *cls;
    int32_t held_x, held_y;           /* +0x04: cursor when a drag started */
    uint8_t show;                     /* +0x0c */
    uint8_t active;                   /* +0x0d */
    uint8_t docking;                  /* +0x0e */
    int32_t state;                    /* +0x10: MU_UI_WS_* */
    mu_ui_sprite *background;         /* +0x14 */
    int32_t x, y;                     /* +0x18 */
    int32_t width, height;            /* +0x20 */
    int32_t temp_x, temp_y;           /* +0x28 */
    mu_ui_button *buttons[MU_UI_WIN_MAX_BUTTONS];   /* +0x30: registration order */
    int button_count;
    mu_ui_sprite background_storage;
};

extern const mu_ui_win_class mu_ui_win_base_class;
/* CWin's empty virtual defaults (0x009828c4, 0x00982877, 0x0098290f, 0x0098286e, 0x0107537c, 0x009828cd). */
void mu_ui_win_nop(mu_ui_ctx *ctx, mu_ui_win *win);
int mu_ui_win_no_controls(mu_ui_ctx *ctx, mu_ui_win *win);
void mu_ui_win_nop_delta(mu_ui_ctx *ctx, mu_ui_win *win, double delta);

void mu_ui_win_init(mu_ui_win *win, const mu_ui_win_class *cls);                 /* 0x0120cc8a */
void mu_ui_win_create(mu_ui_ctx *ctx, mu_ui_win *win, int32_t width, int32_t height, int32_t texture,
                      int tile);                                                  /* 0x0120ccfd */
void mu_ui_win_release(mu_ui_ctx *ctx, mu_ui_win *win);                          /* 0x0120ce41 */
void mu_ui_win_register_button(mu_ui_win *win, mu_ui_button *button);            /* 0x0120d2e3 */
void mu_ui_win_set_position(mu_ui_ctx *ctx, mu_ui_win *win, int32_t x, int32_t y); /* 0x0120ceb4 */
void mu_ui_win_set_size(mu_ui_win *win, int32_t width, int32_t height, int32_t which); /* 0x0120ceee */
int mu_ui_win_cursor_in_win(mu_ui_ctx *ctx, mu_ui_win *win, int32_t area);       /* 0x0120cf39 */
void mu_ui_win_show(mu_ui_ctx *ctx, mu_ui_win *win, int show);                   /* 0x0120d090 */
void mu_ui_win_set_active(mu_ui_win *win, int active);                           /* 0x0098285a */
void mu_ui_win_update(mu_ui_ctx *ctx, mu_ui_win *win, double delta);             /* 0x0120d0ce */
void mu_ui_win_render(mu_ui_ctx *ctx, mu_ui_win *win);                           /* 0x0120d26d */
void mu_ui_win_render_buttons(mu_ui_ctx *ctx, mu_ui_win *win);                   /* 0x0120d2fd */
void mu_ui_win_active_buttons(mu_ui_win *win, int active);                       /* 0x0120d2a2 */

/* ---- CWinEx (vtable 0x01ac74a4) ---------------------------------------- */
enum { MU_UI_WINEX_BACK, MU_UI_WINEX_TOP, MU_UI_WINEX_BOTTOM, MU_UI_WINEX_LEFT, MU_UI_WINEX_RIGHT };

typedef struct mu_ui_winex {
    mu_ui_win win;
    mu_ui_sprite sprites[5];          /* +0x14 points at a new[5] array */
    int32_t line_max;                 /* +0x3c */
    int32_t line_min;                 /* +0x40 */
    int32_t lines;                    /* +0x44 */
    int32_t resize_base;              /* +0x48 */
} mu_ui_winex;

extern const mu_ui_win_class mu_ui_winex_class;

void mu_ui_winex_init(mu_ui_winex *win);                                          /* 0x0120d37a */
void mu_ui_winex_release(mu_ui_ctx *ctx, mu_ui_win *win);                        /* 0x0120d69e */
void mu_ui_winex_create(mu_ui_ctx *ctx, mu_ui_winex *win, const mu_ui_image_info info[5], int32_t line_min,
                        int32_t line_max);                                        /* 0x0120d3df */
int32_t mu_ui_winex_set_line(mu_ui_winex *win, int32_t lines);                   /* 0x0120d861 */
void mu_ui_winex_set_position(mu_ui_ctx *ctx, mu_ui_win *win, int32_t x, int32_t y); /* 0x0120d73c */
int mu_ui_winex_cursor_in_win(mu_ui_ctx *ctx, mu_ui_win *win, int32_t area);     /* 0x0120da21 */
void mu_ui_winex_show(mu_ui_ctx *ctx, mu_ui_win *win, int show);                 /* 0x0120db2c */
void mu_ui_winex_render(mu_ui_ctx *ctx, mu_ui_win *win);                         /* 0x0120db7e */
void mu_ui_winex_check_additional_state(mu_ui_ctx *ctx, mu_ui_win *win);         /* 0x0120dbc7 */

/* CutText 0x01859f23: wraps src into up to `lines` rows of `width` bytes
 * (dst is lines*width bytes), preferring to break after a space that is
 * fewer than min(width/2, 10) bytes back.  Returns the row count.  The
 * client measures characters with _mbclen; this restatement treats every
 * byte as one character (single-byte code page). */
int32_t mu_ui_cut_text(const char *src, char *dst, int32_t lines, int32_t width);

#ifdef __cplusplus
}
#endif
#endif
