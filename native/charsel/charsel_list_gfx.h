#ifndef MU_CHARSEL_LIST_GFX_H
#define MU_CHARSEL_LIST_GFX_H

/* The character select's GFx list in the native client (NATIVE-CHARSEL-003).
 *
 * Plays the client's CharacterSelect movie (Data\Interface\GFx\CharacterSelect.ozg converted with
 * native/gfx/gfxconvert.py --bridge) as one full-window player of libmugfx (Ruffle with the GFx patch
 * series, loaded at run time like the HUD layer native/gfx/mu_gfx_layer.c, which this module does not
 * touch), and plays the game side of the movie with the reconstructed window code
 * reconstructed/charsel/charsel_gfx.c (compared with the client in Unicorn):
 *
 *   - the movie's UIInit -> the window's initialisation 0x00b4915b (InitText, InitStat, InitClassInfo, ...),
 *     then CreateCharacterScene's list step: SetSelectText from the session's CharactersClient records
 *     and, when a character exists, show(1) (SelectIndex, SetSelectVisible, SetCharSelArrow);
 *   - OnCharSelectedClick / OnCharSelectedDClick / onCharSelArrow -> 0x00b4c1df: the selection
 *     (SelectedHero and the shown character of the session), entry by double click (the session's
 *     enter request, as 0x0185a75a(0)), the reorder arrows;
 *   - an empty row, OnClickCreateCharacter and OnEnterCharacterName open or use the create-character
 *     panel: with config.create, charsel_create_gfx.c plays it (NATIVE-CHARCREATE-001: the panel, the
 *     preview, the Caution boxes, the delete flow and winSystemMenu; OFFLINE DEMO answers from the caller's
 *     hooks); without, they are counted and reported, nothing created (NATIVE-CHARSEL-003).
 *
 * GlobalText comes from the caller (NATIVE-LANG-001 tables) or "GT<n>" stand-ins; class names follow the
 * client's class-name switch 0x0139cc2e (executed for every class byte, NATIVE-CHARCREATE-001) over the
 * same GlobalText.  The movie and its
 * renders are client-derived and stay local. */

#include <stddef.h>
#include <stdint.h>

#include "../core/mu_charsel.h"
#include "charsel_create_gfx.h"

typedef struct mu_charsel_list_gfx mu_charsel_list_gfx;

typedef const char *(*mu_charsel_text_fn)(void *user, int32_t index);

typedef struct mu_charsel_list_gfx_config {
    const char *movie_dir;      /* CharacterSelect.swf */
    const char *lib_path;       /* libmugfx; NULL: $MU_GFX_LIB, next to the executable, the repository build */
    int32_t width, height;      /* window pixels */
    double scale;               /* pixels per point (Retina 2), 0 = 1 */
    mu_charsel_text_fn text;    /* GlobalText, may be NULL */
    void *text_user;
    const char *log_path;       /* every emitted line and callback, or NULL */
    /* NATIVE-CHARCREATE-001: the create panel, the delete flow, the Caution boxes and the menu
     * (charsel_create_gfx.h); 0 keeps NATIVE-CHARSEL-003's OFFLINE DEMO no-op */
    int create;
    const char *game_root;      /* Data/Logo/NewFaceNN.bmd for the creation preview */
    const char *lang_dir;       /* filter.txt, filtername.txt (scripts/live_lang_filters.py), may be NULL */
    mu_charsel_create_hooks hooks;
    int32_t created, limit;     /* the daily creation counts of the character list (offline: the store's) */
    int shared;                 /* NATIVE-PERF-001: render into an IOSurface (macOS) for a GL compositor */
} mu_charsel_list_gfx_config;

mu_charsel_list_gfx *mu_charsel_list_gfx_open(const mu_charsel_list_gfx_config *config, mu_charsel_session *session,
                                              char *error, size_t error_size);
void mu_charsel_list_gfx_close(mu_charsel_list_gfx *g);

/* Input in window pixels (kind 0 move, 1 down, 2 up; button 0 left).  Returns 1 when the movie is under
 * the cursor (the 3D scene and CCharSelMainWin must not take the event). */
int mu_charsel_list_gfx_mouse(mu_charsel_list_gfx *g, int kind, int button, double x, double y);
/* The native shortcuts (1..5, Left/Right): the list's row click 0x00b4bd6c plus SelectIndex so the movie
 * shows it (native choice; the movie itself ignores arrow keys, MUComponent.handleInput). */
void mu_charsel_list_gfx_select_slot(mu_charsel_list_gfx *g, int32_t slot);
/* Advance the movie (ms). */
void mu_charsel_list_gfx_advance(mu_charsel_list_gfx *g, double dt_ms);
/* Render when changed and blend over rgba (top-down RGBA8, the open size). */
void mu_charsel_list_gfx_composite(mu_charsel_list_gfx *g, uint8_t *rgba, int32_t width, int32_t height);
/* NATIVE-PERF-001: the movie's frame (top-down RGBA, straight alpha, width x height) rendered when it
 * changed, for a GPU compositor; *changed is set when the pixels differ from the previous call's. NULL when
 * there is no frame (or the size differs from the list's). */
const uint8_t *mu_charsel_list_gfx_frame(mu_charsel_list_gfx *g, int32_t width, int32_t height, int *changed);
/* NATIVE-PERF-001, GPU compositors: the create panel's preview, the menu or a Caution box is open, so the scene
 * needs mu_charsel_list_gfx_composite over the frame read back (the preview draws over the frame in software);
 * otherwise mu_charsel_list_gfx_hook runs the window's per-frame render hook and the list goes through
 * mu_charsel_list_gfx_frame / _surface. */
int mu_charsel_list_gfx_needs_frame(const mu_charsel_list_gfx *g);
void mu_charsel_list_gfx_hook(mu_charsel_list_gfx *g);
/* NATIVE-PERF-001: the window changed size (pixels): the movie's stage and view follow it. */
void mu_charsel_list_gfx_resize(mu_charsel_list_gfx *g, int32_t width, int32_t height);
/* NATIVE-PERF-001, shared lists: renders when the movie changed (waiting for the GPU) and returns the
 * IOSurfaceRef (BGRA, premultiplied alpha) with its size and a seed that changes when the surface is
 * replaced; NULL when the list is not shared or has no frame. */
void *mu_charsel_list_gfx_surface(mu_charsel_list_gfx *g, int32_t *width, int32_t *height, uint32_t *seed);

typedef struct mu_charsel_list_gfx_stats {
    int ready;                  /* UIInit answered */
    long invokes, callbacks, enters, create_requests, renders;
    int32_t row;                /* window +0xa0 */
    char last_callback[64];
    char status[160];           /* the offline-demo note, "" none */
} mu_charsel_list_gfx_stats;
void mu_charsel_list_gfx_stats_get(const mu_charsel_list_gfx *g, mu_charsel_list_gfx_stats *out);
/* Window-pixel centre of list row `row` (scripted input); 0 when unknown. */
int mu_charsel_list_gfx_row_center(const mu_charsel_list_gfx *g, int32_t row, double *x, double *y);

/* GlobalText index of the class name 0x0139cc2e(class, 1) (every class byte executed in Unicorn,
 * NATIVE-CHARCREATE-001; 2305 for the codes the switch has no case for). */
int32_t mu_charsel_class_name_text(uint8_t class_byte);

/* NATIVE-CHARCREATE-001 (no effect without config.create): CCharSelMainWin's events (Create 0x20, Menu 0x21,
 * message 0x23, delete confirmation 0x25); the menu toggled / the create panel closed (the scene tick's Esc);
 * keys and typed text (1 when the Caution box or the create panel's name box takes them); a rebuilt session
 * (InitCharacterScene cleared by the created / deleted answer); the module's state; control centres for
 * scripted input (charsel_create_gfx.h names). */
void mu_charsel_list_gfx_event(mu_charsel_list_gfx *g, int32_t code, int32_t argument);
void mu_charsel_list_gfx_menu(mu_charsel_list_gfx *g);
void mu_charsel_list_gfx_close_panel(mu_charsel_list_gfx *g);
int mu_charsel_list_gfx_key(mu_charsel_list_gfx *g, int vk, int down);
int mu_charsel_list_gfx_text(mu_charsel_list_gfx *g, const char *utf8);
void mu_charsel_list_gfx_rebind(mu_charsel_list_gfx *g, mu_charsel_session *session);
void mu_charsel_list_gfx_create_stats(const mu_charsel_list_gfx *g, mu_charsel_create_stats *out);
void mu_charsel_list_gfx_create_done(mu_charsel_list_gfx *g);
int mu_charsel_list_gfx_control(const mu_charsel_list_gfx *g, const char *name, double *x, double *y);

#endif
