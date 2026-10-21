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
 *     panel in the client, which needs the server: OFFLINE DEMO, counted and reported, nothing created.
 *
 * GlobalText comes from the caller (NATIVE-LANG-001 tables) or "GT<n>" stand-ins; class names follow the
 * client's class-name switch 0x0139cc2e (static reading) over the same GlobalText.  The movie and its
 * renders are client-derived and stay local. */

#include <stddef.h>
#include <stdint.h>

#include "../core/mu_charsel.h"

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

/* GlobalText index of the class name 0x0139cc2e(class, 1) (static reading), -1 unknown. */
int32_t mu_charsel_class_name_text(uint8_t class_byte);

#endif
