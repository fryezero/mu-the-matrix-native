/* GFX-WINDOWS-* (sketch): a GFx window as a view of the session.
 *
 * Today mu_gfx_layer.c (4,610 lines) owns the inventory (item items[48]), demo hero values
 * (mu_gfx_hero, three setters), its own Zen, and the per-window wiring of 30 movies in one
 * FILES[] list. In this shape the layer keeps the movie mechanics (Ruffle, slots, hit tests,
 * tooltips, item models over cells) and every window becomes one small view file:
 *
 *   reads    the session domains it shows        -> sync() when a watched revision changed
 *   replays  the cues addressed to it            -> MU_CUE_WINDOW (open/show/close/invoke) by movie name
 *   submits  intents for its buttons/drags       -> mu_session_submit; a refusal shows the client's notice
 *   owns     only view state                     -> open/closed, scroll, drag in progress, focus
 *
 * Windows whose handler state is session-owned (quest windows, the character window's stat
 * copy, messenger rooms) forward their movie callbacks as their generated MU_INTENT_WINDOW_<MOVIE> kind and render
 * what the session's handler state says.
 *
 * Adding one of the ~135 unwired movies = one row in windows.def + one file
 * native/gfx/windows/<movie>.c. Nothing else lists movies (FILES[] is generated from windows.def).
 */
#ifndef MU_WINDOW_VIEW_H
#define MU_WINDOW_VIEW_H

#include <stdint.h>

#include "../session/mu_session.h"

struct mu_gfx_layer;
struct mu_gfx_movie;

#define MU_WINDOW_WATCH 8

typedef struct mu_window_view_ops {
    const char *movie;                        /* registry movie name, e.g. "InventoryFrame" */
    mu_domain watch[MU_WINDOW_WATCH];         /* domains whose revision triggers sync */
    int watch_count;
    size_t state_size;
    int (*open)(void *self, struct mu_gfx_layer *L, struct mu_gfx_movie *m, const mu_session *s);
    /* Re-render from state. Idempotent: called again with unchanged state it pushes the same values. */
    void (*sync)(void *self, struct mu_gfx_movie *m, const mu_session *s);
    /* A cue for this movie (verb/method/args as the client's handler called it). */
    void (*cue)(void *self, struct mu_gfx_movie *m, const mu_cue *cue);
    /* A movie callback (AS2 fscommand / ExternalInterface): typically builds an intent and submits it. */
    int (*callback)(void *self, struct mu_gfx_movie *m, mu_session *s, const char *name, const char *args);
    void (*close)(void *self);
} mu_window_view_ops;

/* The layer's per-frame driver (one call from the gfx part):
 *   for each open view: if any watched rev differs from the view's last seen -> sync
 *   drain the gfx part's cue cursor; route MU_CUE_WINDOW by movie name; open closed movies on OPEN */
void mu_gfx_layer_sync(struct mu_gfx_layer *L, mu_session *s, mu_cue_cursor *cursor);

#endif
