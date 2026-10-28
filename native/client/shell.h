#ifndef MU_SHELL_H
#define MU_SHELL_H

/* mu-client's scene manager runtime (NATIVE-SHELL-001,
 * docs/research/client-scene-manager.md).
 *
 * Runs the client's own scene flow with the reconstructed scene routines
 * (reconstructed/scene) driving the native modules through their host calls:
 *
 *   2 title     mu_scenemgr_intro: the title textures, the title screen with the
 *               startup progress 0..9 (CreateTitleSceneUI/RenderTitleSceneUI)
 *   3 login     mu_scenemgr_login_create + the scene-3 tick: the 3D login world
 *               (core/mu_login, NATIVE-LOGIN-001: the tick head and the render's
 *               3D part from reconstructed/scene) under the login overlay,
 *               the server-select window with the offline session's list, an
 *               OFFLINE DEMO account panel (placeholder for the GFx login
 *               dialog: any input, nothing kept), protocol 0x14 -> the tick
 *               tail -> scene 5
 *   5 select    the mu-charsel session (charsel/mu_charsel_rt) with the
 *               session's characters and the CCharSelMainWin 2D layer; the
 *               scene tick's Enter -> mu_scenemgr_start_loading(0) (join
 *               request: answered by the offline session) -> (1) -> scene 4
 *   4 loading   mu_scenemgr_loading: Interface\LSBg01_1..4 and CLoadingScene,
 *               one frame, scene 6; the world loads while it is shown
 *   6 world     the world runtime (world/mu_world_rt.h, mu-world's session) with the chosen
 *               character's class (copied into the Hero by start loading) and
 *               equipment at the session's join position; Esc returns to
 *               character select (mu_scenemgr_return_to_character)
 *
 * Every rendered frame ends with the frame driver's music block
 * (mu_scenemgr_frame_music: login theme in scenes 3 and 5).
 *
 * The shell does no GL itself: the front end (client/main.c) draws the 3D
 * view the shell names (character select or world) with the embed's or the world runtime's GL or
 * software renderer, then hands the frame to mu_shell_overlay for the 2D
 * layer. The title and loading scenes block inside the dispatcher like the
 * client's and show their frames through platform.present.
 */

#include <stddef.h>
#include <stdint.h>

#include "../../reconstructed/scene/scene.h"
#include "../charsel/charsel_create_gfx.h"
#include "../charsel/mu_charsel_rt.h"
#include "../core/mu_login.h"
#include "../core/mu_ui_raster.h"
#include "../world/mu_world_rt.h"
#include "offline-session.h"

typedef struct mu_shell mu_shell;

enum { MU_SHELL_VIEW_2D = 0, MU_SHELL_VIEW_CHARSEL = 1, MU_SHELL_VIEW_WORLD = 2, MU_SHELL_VIEW_LOGIN = 3 };
enum { MU_SHELL_EMBED_CHARSEL = 1, MU_SHELL_EMBED_WORLD = 2, MU_SHELL_EMBED_LOGIN = 3 };

typedef struct mu_shell_platform {
    void *user;
    /* a finished 2D frame from inside the title or loading scene (top-down RGBA, width x height) */
    void (*present)(void *user, const uint8_t *rgba);
    /* millisecond clock (GetTickCount) */
    uint32_t (*ticks)(void *user);
    /* an embed or the world runtime opened (GL front ends upload its textures) / is about to close */
    void (*embed_opened)(void *user, int kind, void *embed);
    void (*embed_closing)(void *user, int kind, void *embed);
    /* wait `ms` between the title's startup steps (window front ends), may be NULL */
    void (*pause)(void *user, uint32_t ms);
    /* NATIVE-PERF-001: the 2D layer on the GPU (all NULL: the software raster over a frame read back).
     * ui_target gives the sink that replaces a software raster of w x h (the shell's, the character
     * select window's; `raster` holds what was loaded before) and returns 0, ui_target_free releases it;
     * ui_begin/ui_end bracket each series of 2D calls; image draws a top-down RGBA picture with straight
     * alpha over the whole frame (the GFx character list), `changed` when its pixels are new. With
     * ui_target, mu_shell_overlay draws over the current framebuffer (its rgba is unused, may be NULL)
     * and present() receives NULL: the title/loading frame is in the back buffer. */
    int (*ui_target)(void *user, const mu_ui_raster *raster, int32_t w, int32_t h, mu_ui_sink *out);
    void (*ui_target_free)(void *user, const mu_ui_sink *sink);
    void (*ui_begin)(void *user);
    void (*ui_end)(void *user);
    void (*image)(void *user, const uint8_t *rgba, int32_t w, int32_t h, int changed);
    /* the same picture as an IOSurfaceRef (BGRA, premultiplied; macOS) when `surface` is set: the list
     * then renders into it (mugfx shared rendering) and nothing is read back */
    void (*surface)(void *user, void *iosurface, int32_t w, int32_t h, uint32_t seed);
    /* while the character select's create panel, menu or Caution box is open: the frame read back (top-down
     * RGBA, width x height) and written back after the software compositing (NATIVE-CHARCREATE-001's parts) */
    uint8_t *(*read_frame)(void *user);
    void (*write_frame)(void *user, const uint8_t *rgba);
} mu_shell_platform;

typedef struct mu_shell_config {
    const char *root;
    const char *session_path;      /* NULL: built-in demo data */
    const char *font;              /* GDI face (CoreText) */
    int32_t width, height;         /* drawable pixels */
    int audio;                     /* login music (mu_audio engine) */
    int32_t audio_rate;
    /* NATIVE-APP-001: the offline label's first line (NULL: the default) */
    const char *label;
    /* WORLD-RT-001: scene 6's world runtime options as the front end parsed them (mu_world_rt_default_options,
     * then the world sound table, demo placement, NPC table and players, objects and mu-world's feature
     * switches); open_world adds the join (world, class, tile, angle, equipment, name, level), the drawable
     * size, the audio switch and quiet */
    mu_world_rt_options world;
    const char *charsel_objects;   /* local decoded EncTerrain94.plain, may be NULL */
    const char *login_objects;     /* local decoded EncTerrain95.plain (login world), may be NULL */
    uint32_t title_step_ms;        /* platform.pause between the title's progress frames */
    int quiet;
    /* NATIVE-CHARSEL-003: the character select's GFx list (CharacterSelect.swf in gfx_dir), NULL: none */
    const char *gfx_dir;
    const char *gfx_lib;           /* libmugfx, NULL: the layer's search */
    double gfx_scale;              /* window pixels per point (Retina 2), 0 = 1 */
    const char *gfx_log;           /* the list's lines and callbacks, may be NULL */
    /* NATIVE-CHARCREATE-001: the OFFLINE DEMO character store (characters created and deleted in character
     * select; offline-session.h), NULL or "": changes stay in memory */
    const char *store_path;
} mu_shell_config;

mu_shell *mu_shell_new(const mu_shell_config *config, const mu_shell_platform *platform, char *error,
                       size_t error_size);
void mu_shell_free(mu_shell *s);

/* Input in window pixels / Win32 virtual keys. */
void mu_shell_mouse_move(mu_shell *s, int32_t x, int32_t y);
void mu_shell_mouse_button(mu_shell *s, int button, int down);   /* 0 left, 1 right, 2 middle */
void mu_shell_wheel(mu_shell *s, int32_t delta);                 /* +1 = one notch away from the user */
void mu_shell_key(mu_shell *s, int vk, int down);
void mu_shell_char(mu_shell *s, int ch);                         /* typed character (login panel) */

/* One pass of the WinMain idle loop: the scene dispatcher with the shell as
 * its host (title and loading render inside; the frame driver's logic for
 * scenes 3, 5 and 6). */
void mu_shell_frame(mu_shell *s, uint32_t now);
/* What the front end draws before the overlay, and the embed or world runtime to draw. */
int mu_shell_view(const mu_shell *s);
mu_charsel_rt *mu_shell_charsel(mu_shell *s);
mu_world_rt *mu_shell_world(mu_shell *s);
mu_login_session *mu_shell_login(mu_shell *s);
/* The 2D layer over the frame (top-down RGBA, width x height). */
void mu_shell_overlay(mu_shell *s, uint8_t *rgba);
/* NATIVE-PERF-001: the 2D layer goes to the GPU (platform.ui_target accepted). */
int mu_shell_gpu_overlay(const mu_shell *s);
/* NATIVE-PERF-001: the window changed size (drawable pixels).  The 2D layer takes the client's layout for
 * the new size (screen rates, fonts chosen by window width, the server window and the character-select
 * window placed again), the 3D views of the open scene follow; the front end resizes its GFx layer and
 * framebuffers.  Called between frames (not from inside the title or loading scene). */
void mu_shell_resize(mu_shell *s, int32_t width, int32_t height);
/* After the frame is shown: the music block and audio update; returns the
 * client's frame-cap sleep in ms. */
int32_t mu_shell_end_frame(mu_shell *s, uint32_t now);

/* Audio: stereo float frames (the world's sound in scene 6, the login music otherwise). */
uint32_t mu_shell_audio_rate(const mu_shell *s);
void mu_shell_mix(mu_shell *s, float *out, uint32_t frames);

int mu_shell_scene(const mu_shell *s);
/* NATIVE-PROGRESS-001: the in-world system menu's choice (0 exit game, 1 switch character, 2 select server). */
void mu_shell_world_menu(mu_shell *s, int kind);
int mu_shell_quit(const mu_shell *s);
void mu_shell_request_quit(mu_shell *s);
const mu_scenemgr_globals *mu_shell_globals(const mu_shell *s);
const mu_offline_session *mu_shell_session(const mu_shell *s);
/* The character the world was entered with (-1 none) and its class byte. */
int32_t mu_shell_hero_slot(const mu_shell *s);
uint8_t mu_shell_hero_class(const mu_shell *s);
/* Positions of the server window's first selectable group and server buttons
 * (window pixels), for scripted input; return 0 when not shown. */
int mu_shell_server_group_button(const mu_shell *s, int32_t index, int32_t *x, int32_t *y);
int mu_shell_server_button(const mu_shell *s, int32_t index, int32_t *x, int32_t *y);
/* The login panel is shown (a server was chosen). */
int mu_shell_login_panel(const mu_shell *s);
/* Scene transition log (one line per transition) and counters for reports. */
int32_t mu_shell_transitions(const mu_shell *s, const char *const **lines);
const char *mu_shell_status(const mu_shell *s);
/* NATIVE-CHARSEL-003: the character select's GFx list (NULL outside scene 5 or without --gfx). */
struct mu_charsel_list_gfx *mu_shell_charsel_gfx(mu_shell *s);
/* Window-pixel centre of the GFx list's row (scripted input); 0 when there is no list. */
int mu_shell_charsel_row(mu_shell *s, int32_t row, int32_t *x, int32_t *y);
/* Over every character-select visit: picks, pick hits, double clicks, GFx list callbacks, entries from the
 * list, create-character requests (offline no-ops). */
void mu_shell_charsel_counts(const mu_shell *s, long out[6]);
/* NATIVE-CHARCREATE-001: the create panel / delete flow / menu state of the current visit (zeros without the
 * GFx list); the scene rebuilds after a created or deleted answer (counted). */
void mu_shell_charsel_create_stats(const mu_shell *s, mu_charsel_create_stats *out, long *rebuilds);
/* Window-pixel centre of a control for scripted input: CCharSelMainWin's buttons "create", "menu",
 * "connect", "delete" and the GFx controls of charsel_create_gfx.h ("class:N", "createok", "msgok", ...);
 * 0 when not shown. */
int mu_shell_charsel_control(mu_shell *s, const char *name, int32_t *x, int32_t *y);

#endif
