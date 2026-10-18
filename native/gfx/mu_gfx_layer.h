/* The GFx interface layer of the native client (NATIVE-GFX-002, NATIVE-GFX-003).
 *
 * Plays the client's GFx windows (converted movies, native/gfx/gfxconvert.py
 * --bridge) through mugfx (Ruffle with the GFx patch series) over a host's
 * 3D view, and plays the game side of their boundary the way the client's
 * GFx manager and window handlers do (docs/research/client-hud.md,
 * docs/research/native-gfx.md):
 *
 *   main                bottom bar: HP/MP orbs, SD/AG bars, EXP bar
 *                       (mcExpBar), skill hotkeys (mcSkillHotKey), item hotkeys
 *                       (mcItemHotKey), menu buttons; its onHotKey opens windows;
 *   InventoryFrame      8 x 8 page over the reconstructed item grid
 *                       (reconstructed/hud/inv_grid.c) with pick/drop, right
 *                       click (requestItemSlotClickR) and hover tooltips;
 *   InfoPopup           item and skill tooltips (SetInfoPopup with the HTML the
 *                       host's tooltip pipeline builds);
 *   CharacterInfoFrame  character window filled from the hero values, stat
 *                       points spent through its "+" buttons (onClickButton);
 *   chat                chat window: Enter opens the input, typed text goes to
 *                       the movie's text field, Enter sends; local echo.
 *
 * mugfx is loaded at run time (dlopen), so a host builds without Rust; when
 * the library or the movies are missing, mu_gfx_layer_open fails cleanly.
 * Players are sized to each window's bounds (mugfx_set_view) and, with
 * `shared`, render into IOSurfaces that the GL compositor samples directly
 * (macOS); otherwise frames are read back and uploaded.  Only movies that
 * changed are rendered.
 *
 * NATIVE-GFX-003: when the movie directory holds base.swf, the bar, chat
 * and the other HUD movies run as in the client: one base movie (base.swf ->
 * ExternalBase.swf) whose UI loader loads the movies of the client's list
 * (LoadFrameFiles, static reading of the UIFrame handler 0x00c8f05d:
 * ImageData; Tooltip, Popups; main; ItemDurability, Chat, AlarmFrame,
 * topmenu, bufflist; hudPlayerName, hudMap, hudNotice), so the skill icons
 * (ImageData + the skill data the game sends to ASData) and the item hotkey
 * icons (the game's render target image0) appear.  Without base.swf the
 * layer plays main.swf and chat.swf on their own (NATIVE-GFX-002).  The
 * item windows get the client's placement (registry alignment, SetScale
 * below 700 pixels) and the host can draw the item models over them
 * (items callback, the per-window item pass 0x00abfcca).
 *
 * The movies and every render are client-derived and stay local. */
#ifndef MU_GFX_LAYER_H
#define MU_GFX_LAYER_H

#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct mu_gfx_layer mu_gfx_layer;

enum { MU_GFX_MAIN, MU_GFX_INVENTORY, MU_GFX_TOOLTIP, MU_GFX_CHARACTER, MU_GFX_CHAT, MU_GFX_MOVIES };

/* Character values the windows show (demo values until a game feeds them). */
typedef struct mu_gfx_hero {
    char name[32], class_name[32];
    int32_t level, master_level, points;
    int32_t hp, max_hp, mp, max_mp, sd, max_sd, ag, max_ag;
    int64_t exp, exp_max;
    int32_t strength, agility, vitality, energy, command;
    int64_t zen, ruud;
} mu_gfx_hero;

/* The InfoPopup HTML for an item (the client's tooltip pipeline, see
 * reconstructed/hud/tooltip_html.c); returns 0 and writes UTF-8 HTML, or
 * non-zero to use the layer's minimal built-in tooltip. */
typedef int (*mu_gfx_tooltip_fn)(void *user, int32_t code, int32_t level, char *html, size_t cap);

/* One item model to draw over a window (NATIVE-GFX-003): the slot call of
 * the reconstructed slot pass 0x00ab6130 in 640 x 480 units for a stage of
 * stage_w x stage_h points, and the cell rectangle in stage points (top-left
 * origin).  select: the cursor is over the item (RenderItem3D spins it);
 * held: the item hangs at the cursor (RenderObjectScreen enlarges it 1.4x). */
typedef struct mu_gfx_item_draw {
    int32_t item;               /* layer item index */
    int32_t code, level, excellent;
    float slot[4];              /* x, y, w, h in 640 x 480 units */
    int32_t page_type, page_flag, type8_seen, frame_id;
    float rect[4];              /* stage points, top-left origin */
    float frame_scale;          /* window SetScale / 100 (handler +0x58) */
    float alpha;
    int select, held;
} mu_gfx_item_draw;

/* Draw item models over the current GL framebuffer.  The layer calls it
 * right after the window's movie, as the client's per-window item pass
 * 0x00abfcca does; the callee sets up glOrtho(0, stage_w, 0, stage_h, 20,
 * 2000) over the whole viewport (stage points; the viewport is in pixels). */
typedef void (*mu_gfx_items_fn)(void *user, const mu_gfx_item_draw *items, int n, int32_t stage_w, int32_t stage_h);

/* Render the item hotkey icons into the game image `image0` (w x h pixels,
 * RGBA rows bottom-up as glReadPixels returns them: the client renders them
 * into a GL texture and the bar's ItemHotKey draws it flipped).  Each item's
 * rect is its render rectangle in that image, top-left origin.  Returns 0
 * when it drew, else the layer draws stand-ins. */
typedef int (*mu_gfx_icons_fn)(void *user, const mu_gfx_item_draw *items, int n, uint8_t *rgba, int32_t w,
                               int32_t h);

/* A skill as the game sends it to the data movie (ASData skill.setSkillAll,
 * static reading of 0x00c5ebaa: Index, Magic_Icon, Name, Delay,
 * SkillUseType, MasteryType). */
typedef struct mu_gfx_skill {
    int32_t index, icon, delay, use_type, mastery;
    char name[64];
} mu_gfx_skill;

typedef struct mu_gfx_layer_config {
    const char *movie_dir;      /* main.swf, InventoryFrame.swf, ... */
    const char *lib_path;       /* libmugfx; NULL: $MU_GFX_LIB, then next to the executable / repository build */
    int32_t width, height;      /* window pixels (the movies' stage) */
    int shared;                 /* IOSurface sharing (macOS; a GL context must be current) */
    int full_stage;             /* 1: every player covers the whole window (no per-window views) */
    int demo;                   /* 1: animate the demo hero values (orbs, bars) */
    mu_gfx_tooltip_fn tooltip;
    void *tooltip_user;
    FILE *log;                  /* callbacks and invokes, or NULL */
    double scale;               /* window pixels per point (Retina 2); 0 = 1.  The movies lay
                                   themselves out in points, as in a 1x window of that size */
    /* NATIVE-GFX-003 */
    mu_gfx_items_fn items;      /* item models over the item windows (NULL: coloured stand-ins) */
    mu_gfx_icons_fn icons;      /* item hotkey icons (NULL: stand-ins) */
    void *items_user;
    int standalone;             /* 1: play main/chat on their own even when base.swf is present */
    int double_buffer;          /* shared: two surfaces per movie, no GPU wait before drawing
                                   (frames may show one frame late) */
} mu_gfx_layer_config;

mu_gfx_layer *mu_gfx_layer_open(const mu_gfx_layer_config *config, char *error, size_t error_size);
void mu_gfx_layer_close(mu_gfx_layer *layer);
void mu_gfx_layer_resize(mu_gfx_layer *layer, int32_t width, int32_t height);

void mu_gfx_layer_set_hero(mu_gfx_layer *layer, const mu_gfx_hero *hero);
/* Skills the data movie knows (sent to ASData with skill.setSkillAll). */
void mu_gfx_layer_set_skills(mu_gfx_layer *layer, const mu_gfx_skill *skills, int n);
/* 1 when the HUD runs as the client's base movie (base.swf), 0 standalone. */
int mu_gfx_layer_base_mode(const mu_gfx_layer *layer);
/* Instance path of a HUD channel ("UIFrame", "ASData", "main", "chat", ...)
 * as the movies reported it, "" when unknown. */
const char *mu_gfx_layer_channel_path(const mu_gfx_layer *layer, const char *channel);
/* The location the top menu shows (map name, hero cell). */
void mu_gfx_layer_set_location(mu_gfx_layer *layer, const char *map, int x, int y);
/* IME composition text (SDL TEXTEDITING) shown in the chat input; "" ends it. */
int mu_gfx_layer_compose(mu_gfx_layer *layer, const char *utf8, int cursor);
const mu_gfx_hero *mu_gfx_layer_hero(const mu_gfx_layer *layer);
/* Put an item into the first free place of the inventory page (0x00ad49fb);
 * returns its index or -1 when it does not fit. */
int mu_gfx_layer_add_item(mu_gfx_layer *layer, int32_t code, int32_t level, int32_t width, int32_t height,
                          const char *name);

/* Input in window pixels.  mouse kind 0 move, 1 down, 2 up, 3 wheel (button =
 * lines); button 0 left, 1 right, 2 middle.  Returns 1 when the interface
 * took the event (the 3D world must not see it). */
int mu_gfx_layer_mouse(mu_gfx_layer *layer, int kind, int button, double x, double y);
/* Keys: Windows/Flash virtual key codes; mods 1 shift, 2 ctrl/cmd, 4 alt.
 * Returns 1 when the interface used the key (text entry, window hotkeys). */
int mu_gfx_layer_key(mu_gfx_layer *layer, int down, int vk, uint32_t codepoint, int mods);
int mu_gfx_layer_text(mu_gfx_layer *layer, const char *utf8);
/* 1 while a text field (chat input) has the keyboard. */
int mu_gfx_layer_text_active(const mu_gfx_layer *layer);
/* Cursor shape the movie under the mouse asked for: 0 arrow, 1 hand, 2 I-beam. */
int mu_gfx_layer_cursor(const mu_gfx_layer *layer);

void mu_gfx_layer_toggle(mu_gfx_layer *layer, int movie);
void mu_gfx_layer_show(mu_gfx_layer *layer, int movie, int open);
int mu_gfx_layer_is_open(const mu_gfx_layer *layer, int movie);
/* Chat: add a line (type 1 normal, 3 system, ...) as the server echo would. */
void mu_gfx_layer_chat(mu_gfx_layer *layer, int type, const char *name, const char *message);
/* Run a JSON-argument GFx invoke on a movie (tests, scripted runs). */
const char *mu_gfx_layer_invoke(mu_gfx_layer *layer, int movie, const char *path, const char *method,
                                const char *args_json);
/* The instance path of a movie's window (e.g. "_level0.g_mcInventory"). */
const char *mu_gfx_layer_path(const mu_gfx_layer *layer, int movie);
/* Window-pixel centre of an inventory cell (scripted input). */
int mu_gfx_layer_cell_center(const mu_gfx_layer *layer, int32_t cell, double *x, double *y);
/* View rectangle of a movie's player in stage points (pixels / scale). */
void mu_gfx_layer_view(const mu_gfx_layer *layer, int movie, int32_t rect[4]);

/* Advance the movies by dt (ms) and run the 40 ms game steps (feeds). */
void mu_gfx_layer_advance(mu_gfx_layer *layer, double dt_ms);
/* Render the movies that changed (GL context current when shared). */
void mu_gfx_layer_render(mu_gfx_layer *layer);
/* Composite the windows over the current GL framebuffer (OpenGL 2.1;
 * leaves matrices and the touched state as it found them). */
void mu_gfx_layer_draw_gl(mu_gfx_layer *layer);
/* Composite over an RGBA buffer (top row first) on the CPU: headless runs
 * without GL.  Renders the players by read-back. */
void mu_gfx_layer_composite(mu_gfx_layer *layer, uint8_t *rgba, int32_t width, int32_t height);

typedef struct mu_gfx_layer_stats {
    long renders[MU_GFX_MOVIES];
    double render_ms[MU_GFX_MOVIES], capture_ms[MU_GFX_MOVIES], upload_ms[MU_GFX_MOVIES];
    int32_t view[MU_GFX_MOVIES][4];
    long callbacks, invokes, steps, view_changes, gpu_waits;
    double gpu_wait_ms;         /* shared: total wait for the GPU before compositing */
    int shared;
} mu_gfx_layer_stats;
void mu_gfx_layer_stats_get(const mu_gfx_layer *layer, mu_gfx_layer_stats *out);

/* Inventory state for tests: held item index (-1 none), item cell, count. */
int mu_gfx_layer_held(const mu_gfx_layer *layer);
int mu_gfx_layer_item_cell(const mu_gfx_layer *layer, int item);
int mu_gfx_layer_item_count(const mu_gfx_layer *layer);
/* The item draws the inventory's item pass would hand to the items
 * callback now (slot pass outputs); returns the count. */
int mu_gfx_layer_item_draws(mu_gfx_layer *layer, mu_gfx_item_draw *out, int max);
/* Last chat line sent by the player ("" when none). */
const char *mu_gfx_layer_last_sent(const mu_gfx_layer *layer);

#ifdef __cplusplus
}
#endif

#endif
