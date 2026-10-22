/* The in-game options window (winOption) and system menu (winSystemMenu) over the GFx layer
 * (NATIVE-PROGRESS-001, docs/research/client-progression.md).
 *
 * The windows' game side is the client's, reconstructed: winOption in reconstructed/progress
 * (mu_prg_options_*, verified), winSystemMenu in reconstructed/charsel (mu_csm_*, NATIVE-CHARCREATE-001).
 * The host maps their lines to the layer (invokes, show/hide), the native audio module (the Effect group's
 * volume, the Music group's mute), the overhead names' monster info and the settings file:
 *
 *   ~/Library/Application Support/MuTheMatrixNative/option.ini (MU_NATIVE_SETTINGS_DIR overrides the folder)
 *
 * in the client's own format (./option.ini, read with GetPrivateProfileIntA): [DEFAULT] IsAutoAttack,
 * IsWhisperSound, IsSlideHelp, IsPlayerInfo, IsMonsterInfo, IsMusicPlay, Volum, IsMute, IsUpdateData,
 * IsSwitchMode, SwitchModeTime and [OPTION] Effect.  The client writes only [OPTION] Effect there and keeps
 * the toggles on the server (the option byte of opcode 0xA0 sub 0x03); offline, the native session writes
 * the [DEFAULT] keys too, so the client's own loader reads them back at the next join. */
#ifndef WORLD_GFX_OPTIONS_H
#define WORLD_GFX_OPTIONS_H

#include <stdint.h>

#include "../../reconstructed/progress/progress.h"

struct mu_gfx_layer;
struct mu_audio_client;

typedef struct wg_options wg_options;

typedef struct wg_options_hooks {
    void *user;
    struct mu_audio_client *(*audio)(void *user);   /* the native audio module's client, or NULL */
    void (*monster_info)(void *user, int view);      /* hudPlayerName's monster info (0x00c83c86) */
    void (*chat)(void *user, const char *text);      /* a system line (the exit countdown) */
} wg_options_hooks;

/* settings_dir: NULL = the default folder above */
wg_options *wg_options_open(struct mu_gfx_layer *layer, const char *settings_dir, const wg_options_hooks *hooks);
void wg_options_close(wg_options *o);
void wg_options_set_hooks(wg_options *o, const wg_options_hooks *hooks);
/* The layer's callbacks of winOption / winSystemMenu (cfg.progress_call). */
void wg_options_call(wg_options *o, int movie, const char *name, const char *args_json);
/* Logic time: the option window's per-frame update, the exit countdown. */
void wg_options_step(wg_options *o, double dt_ms);
/* The menu's request since the last call: -1 none, 0 exit game, 1 switch character, 2 select server. */
int wg_options_take_request(wg_options *o);
const mu_prg_options *wg_options_values(const wg_options *o);
const char *wg_options_path(const wg_options *o);

#endif
