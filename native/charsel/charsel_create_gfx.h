#ifndef MU_CHARSEL_CREATE_GFX_H
#define MU_CHARSEL_CREATE_GFX_H

/* The character select's create panel, delete flow, message boxes and system menu in the native client
 * (NATIVE-CHARCREATE-001, docs/research/client-character-select.md section 11).
 *
 * Owned by the GFx list (charsel_list_gfx.c), which hands it the lines the reconstructed window code emits.
 * It plays the game side with reconstructed/charsel/charcreate.c (compared with the client in Unicorn):
 *
 *   - the create panel of the CharacterSelect movie: SetSelectedClass, SetCreateBoardInfo,
 *     OnEnterCharacterName (limit, length, the Filter/FilterName tables from MU_LANG_DIR, allowed characters),
 *     UpdateInput, OnClickCreateCancel;
 *   - the creation preview: the class's NewFace model (Data/Logo/NewFaceNN.bmd, model 0x135 + class) with the
 *     class's pose, its intro action 1 then action 0, drawn in software into the panel's rectangle under the
 *     client's preview camera (angle (-90, 0, 0), FOV 10, position (5, -500, 46) - the class offset);
 *   - the message boxes: the client's Caution movie (Caution.swf) for the create errors, the three delete
 *     steps (confirmation, warning, password) and the results;
 *   - the system menu: winSystemMenu.swf attached as the client's window loader does (KeyWindow onLoad),
 *     InitText, SceneChange, open/close, Exit / Select Server / Option / Close;
 *   - OFFLINE DEMO: the create and delete requests and the menu's logout requests go to the caller's hooks
 *     (client/shell.c answers them from the local store) instead of the server.  The delete password is
 *     never stored, logged or compared. */

#include <stddef.h>
#include <stdint.h>

#include "../../reconstructed/charsel/charcreate.h"
#include "../core/mu_charsel.h"
#include "charsel_mugfx.h"

typedef struct mu_charsel_create mu_charsel_create;

typedef struct mu_charsel_create_hooks {
    void *user;
    /* OFFLINE DEMO server: the create request 0x009a466c (name = the client's bytes, class code = (class << 4)
     * + skin); fills the answer the character-created handler 0x0122b648 reads */
    void (*create)(void *user, const char *name, uint8_t class_code, mu_ccr_created *answer);
    /* the delete request 0x00b4a0da for CharactersClient `slot`: returns the answer's result (1 deleted) */
    uint8_t (*remove)(void *user, int32_t slot);
    /* the menu's requests: 0x009a5ab2(0) exit after the countdown, (1) character select, (2) server select;
     * 3 the option window (not played) */
    void (*menu)(void *user, int kind);
} mu_charsel_create_hooks;

typedef struct mu_charsel_create_config {
    const char *movie_dir;              /* Caution.swf, winSystemMenu.swf (optional: missing ones are reported) */
    const char *game_root;              /* Data/Logo/NewFaceNN.bmd */
    int32_t width, height;
    double scale;
    const char *(*text)(void *user, int32_t index);
    void *text_user;
    const char *lang_dir;               /* filter.txt, filtername.txt (scripts/live_lang_filters.py), may be NULL */
    mu_charsel_create_hooks hooks;
    int32_t created, limit;             /* the list packet's daily creation counts (offline: the store's) */
} mu_charsel_create_config;

mu_charsel_create *mu_charsel_create_open(const mu_charsel_create_config *config, const mu_charsel_mugfx *api,
                                          mu_csg_window *list, const mu_csg_env *gfx, char *error, size_t cap);
void mu_charsel_create_close(mu_charsel_create *c);
/* The list's environment changed (a rebuilt session). */
void mu_charsel_create_rebind(mu_charsel_create *c, const mu_csg_env *gfx);

/* A line the list's environment emitted: 1 when it belongs to this module (it may also be passed on). */
int mu_charsel_create_line(mu_charsel_create *c, const char *line);
/* The movie's callback arguments of OnEnterCharacterName / UpdateInput (UTF-8), before the window's dispatch. */
void mu_charsel_create_stash(mu_charsel_create *c, const char *name, const char *text);
/* The list movie is loaded: the daily counts (UpdateCreateCount, from the character list's handler). */
void mu_charsel_create_ready(mu_charsel_create *c);

/* CCharSelMainWin's events (reconstructed/ui/ui_charsel.h): Create 0x20, Menu 0x21, message 0x23 (GlobalText),
 * delete confirmation 0x25. */
void mu_charsel_create_event(mu_charsel_create *c, int32_t code, int32_t argument);
/* Esc through the scene tick: the menu (0x00c8c8b1) or the create panel closed (0x00b49bf4(0)). */
void mu_charsel_create_menu_toggle(mu_charsel_create *c);
void mu_charsel_create_close_panel(mu_charsel_create *c);

/* Pending server answers (the offline hooks) and the countdown; call once per frame. */
void mu_charsel_create_advance(mu_charsel_create *c, double dt_ms);
/* Input: 1 when one of the module's movies takes it (Caution modal first, then the menu). */
int mu_charsel_create_mouse(mu_charsel_create *c, int kind, int button, double x, double y);
int mu_charsel_create_key(mu_charsel_create *c, int vk, int down);
int mu_charsel_create_text(mu_charsel_create *c, const char *utf8);
/* Drawing: the preview under the CharacterSelect movie, the menu and the Caution box over it. */
void mu_charsel_create_draw_preview(mu_charsel_create *c, uint8_t *rgba, int32_t width, int32_t height);
void mu_charsel_create_draw_windows(mu_charsel_create *c, uint8_t *rgba, int32_t width, int32_t height);

typedef struct mu_charsel_create_stats {
    uint8_t create_open, menu_open, caution_open, legacy_hidden;
    int32_t preview_class;              /* -1 none */
    int32_t board[4];
    long creates, created, refused, deletes, deleted, messages, menu_events, preview_frames;
    int32_t rebuild;                    /* InitCharacterScene was cleared: the caller recreates the scene */
    char last_message[160];
    char status[160];
} mu_charsel_create_stats;
void mu_charsel_create_stats_get(const mu_charsel_create *c, mu_charsel_create_stats *out);
void mu_charsel_create_clear_rebuild(mu_charsel_create *c);
/* Window-pixel centre of a create-panel / menu / Caution control for scripted input ("class:N", "createok",
 * "createcancel", "msgok", "msgcancel", "menu:exit", "menu:server", "menu:option", "menu:close"); 0 unknown. */
int mu_charsel_create_control(mu_charsel_create *c, MuGfx *list_movie, const char *list_path, const char *name,
                              double *x, double *y);

#endif
