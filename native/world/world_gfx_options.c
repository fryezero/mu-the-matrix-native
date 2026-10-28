/* The in-game options window and system menu over the GFx layer (NATIVE-PROGRESS-001); see
 * world_gfx_options.h. */
#define _POSIX_C_SOURCE 200809L
#include "world_gfx_options.h"

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#include "../../reconstructed/audio/client_audio.h"
#include "../../reconstructed/charsel/charcreate.h"
#include "../core/mu_lang.h"
#include "../gfx/mu_gfx_layer.h"

#define SCENE_MAIN 6   /* SceneFlag in the world (enum.GameScene.Main) */
#define INI_MAX 32

typedef struct ini_entry {
    char section[16], key[32], value[32];
} ini_entry;

struct wg_options {
    mu_lang *lang;
    mu_gfx_layer *layer;
    wg_options_hooks h;
    char path[1024];
    ini_entry ini[INI_MAX];
    int nini;
    mu_prg_options opts;
    mu_prg_options_env env;
    int option_open;
    /* the switch mode (GFx manager 0x00ac16d0 +0x98/+0x9c), offline only kept */
    int switch_on;
    float switch_minutes;
    /* the movie's onChange object */
    const char *change;
    /* system menu */
    mu_csg_window list;
    mu_csg_env csg;
    mu_ccr_env ccr;
    int request;
    double exit_ms;
    /* without the audio module: the groups' values as the window last set them */
    float effect_volume;
    int music_muted;
    int applied;      /* the stored volume reached the audio module */
};

/* ---- the settings file (the client's option.ini format) ---------------------------------------------------- */

static void ini_set(wg_options *o, const char *section, const char *key, const char *value)
{
    for (int i = 0; i < o->nini; i++)
        if (!strcmp(o->ini[i].section, section) && !strcmp(o->ini[i].key, key)) {
            snprintf(o->ini[i].value, sizeof o->ini[i].value, "%s", value);
            return;
        }
    if (o->nini >= INI_MAX)
        return;
    ini_entry *e = &o->ini[o->nini++];
    snprintf(e->section, sizeof e->section, "%s", section);
    snprintf(e->key, sizeof e->key, "%s", key);
    snprintf(e->value, sizeof e->value, "%s", value);
}

static void ini_load(wg_options *o)
{
    FILE *f = fopen(o->path, "r");
    if (!f)
        return;
    char line[256], section[16] = "";
    while (fgets(line, sizeof line, f)) {
        char *s = line;
        while (*s == ' ' || *s == '\t')
            s++;
        s[strcspn(s, "\r\n")] = 0;
        if (*s == '[') {
            char *end = strchr(s, ']');
            if (end) {
                *end = 0;
                snprintf(section, sizeof section, "%s", s + 1);
            }
            continue;
        }
        char *eq = strchr(s, '=');
        if (!eq || !section[0])
            continue;
        *eq = 0;
        char *k = s, *v = eq + 1;
        size_t kn = strlen(k);
        while (kn && (k[kn - 1] == ' ' || k[kn - 1] == '\t'))
            k[--kn] = 0;
        while (*v == ' ' || *v == '\t')
            v++;
        ini_set(o, section, k, v);
    }
    fclose(f);
}

static void ensure_dir(const char *path)
{
    char dir[1024];
    snprintf(dir, sizeof dir, "%s", path);
    for (char *p = dir + 1; *p; p++)
        if (*p == '/') {
            *p = 0;
            mkdir(dir, 0755);
            *p = '/';
        }
}

static void ini_save(wg_options *o)
{
    ensure_dir(o->path);
    FILE *f = fopen(o->path, "w");
    if (!f)
        return;
    static const char *const SECTIONS[2] = {"DEFAULT", "OPTION"};
    for (int s = 0; s < 2; s++) {
        int any = 0;
        for (int i = 0; i < o->nini; i++) {
            if (strcmp(o->ini[i].section, SECTIONS[s]))
                continue;
            if (!any)
                fprintf(f, "%s[%s]\n", s ? "\n" : "", SECTIONS[s]);
            any = 1;
            fprintf(f, "%s=%s\n", o->ini[i].key, o->ini[i].value);
        }
    }
    fclose(f);
}

/* the [DEFAULT] keys the native session keeps (offline stand-in for the server's option byte) */
static void store_defaults(wg_options *o)
{
    const mu_prg_options *p = &o->opts;
    struct { const char *key; int32_t value; } KEYS[] = {
        {"IsAutoAttack", p->auto_attack}, {"IsWhisperSound", p->whisper_sound}, {"IsSlideHelp", p->slide_help},
        {"IsPlayerInfo", p->player_info}, {"IsMonsterInfo", p->monster_info}, {"IsMusicPlay", p->music_play},
        {"Volum", p->volume}, {"IsMute", p->mute}, {"IsSwitchMode", p->switch_mode},
        {"SwitchModeTime", p->switch_time}};
    char v[32];
    for (size_t i = 0; i < sizeof KEYS / sizeof KEYS[0]; i++) {
        snprintf(v, sizeof v, "%d", KEYS[i].value);
        ini_set(o, "DEFAULT", KEYS[i].key, v);
    }
    ini_save(o);
}

/* ---- the options window's environment ------------------------------------------------------------------- */

static int32_t env_ini_int(void *user, const char *section, const char *key, int32_t fallback)
{
    wg_options *o = user;
    for (int i = 0; i < o->nini; i++)
        if (!strcmp(o->ini[i].section, section) && !strcmp(o->ini[i].key, key)) {
            /* GetPrivateProfileIntA: the leading decimal number, the default when there is none */
            char *end;
            long v = strtol(o->ini[i].value, &end, 10);
            return end == o->ini[i].value ? fallback : (int32_t)v;
        }
    return fallback;
}

static void env_ini_write(void *user, const char *section, const char *key, const char *value)
{
    wg_options *o = user;
    ini_set(o, section, key, value);
    ini_save(o);
}

static mu_audio_client *audio(wg_options *o)
{
    return o->h.audio ? o->h.audio(o->h.user) : NULL;
}

static float env_group_volume(void *user, int32_t group)
{
    wg_options *o = user;
    mu_audio_client *a = audio(o);
    if (a)
        return mu_audio_get_group_volume(a, group);
    return group == 2 ? o->effect_volume : 1.0f;
}

static int env_group_muted(void *user, int32_t group)
{
    wg_options *o = user;
    mu_audio_client *a = audio(o);
    if (a)
        return mu_audio_get_group_mute(a, group);
    return group == 0 ? o->music_muted : 0;
}

static void env_set_group_volume(void *user, int32_t group, float volume)
{
    wg_options *o = user;
    mu_audio_client *a = audio(o);
    if (a)
        mu_audio_set_group_volume(a, group, volume);
    if (group == 2)
        o->effect_volume = volume;
}

static void env_set_group_mute(void *user, int32_t group, int mute)
{
    wg_options *o = user;
    mu_audio_client *a = audio(o);
    if (a)
        mu_audio_set_group_mute(a, group, mute);
    if (group == 0)
        o->music_muted = mute;
}

static int env_visible(void *user)
{
    return ((wg_options *)user)->option_open;
}

static int env_window(void *user, uint32_t getter)
{
    wg_options *o = user;
    if (getter == 0x0095c5da)   /* the main frame */
        return 1;
    if (getter == 0x009a19ae)   /* hudPlayerName */
        return o->h.monster_info != NULL;
    return 0;
}

static int env_switch(void *user, float *minutes)
{
    wg_options *o = user;
    *minutes = o->switch_minutes;
    return o->switch_on;
}

/* a member of the onChange object: "name":true|false|number */
static const char *member(const char *json, const char *name)
{
    char pat[64];
    snprintf(pat, sizeof pat, "\"%s\":", name);
    const char *p = json ? strstr(json, pat) : NULL;
    return p ? p + strlen(pat) : NULL;
}

static int env_member_bool(void *user, const char *name)
{
    const char *p = member(((wg_options *)user)->change, name);
    return p && (!strncmp(p, "true", 4) || (*p >= '1' && *p <= '9'));
}

static int32_t env_member_int(void *user, const char *name)
{
    const char *p = member(((wg_options *)user)->change, name);
    if (!p)
        return 0;
    if (*p == '"')
        p++;
    return (int32_t)strtol(p, NULL, 10);
}

static const char *env_text(void *user, int32_t index)
{
    (void)user;
    const char *t = mu_lang_text(((wg_options *)user)->lang, index);
    if (t && *t)
        return t;
    switch (index) {   /* English stand-ins of the labels (the client's GlobalText, NATIVE-LANG-001) */
    case 0x927: return "Option";
    case 0x185: return "Volume";
    case 0x730: return "+Effect limitation";
    case 0x182: return "Automatic Attack";
    case 0x183: return "Whispering";
    case 0x397: return "Slide Help";
    case 0xef8: return "Name display";
    case 0xef9: return "Monster display";
    case 0x3ea: return "Close";
    case 0x1178: return "BGM On/Off";
    case 0x1314: return "mute";
    case 0x1530: return "Switch on";
    case 0x1531: return "min";
    case 0xd7a: return "System Menu";
    case 0x17d: return "Exit Game";
    case 0x17e: return "Select Server";
    case 0x17f: return "Switch Character";
    case 0x181: return "Option";
    case 0x17c: return "You will exit game in %d seconds.";
    default: return "";
    }
}

static void invoke_line(wg_options *o, int movie, const char *rest)
{
    char method[64];
    const char *space = strchr(rest, ' ');
    size_t n = space ? (size_t)(space - rest) : strlen(rest);
    snprintf(method, sizeof method, "%.*s", (int)n, rest);
    const char *args = space ? space + 1 : "[]";
    char wrapped[2200];
    if (*args != '[') {
        snprintf(wrapped, sizeof wrapped, "[%s]", args);
        args = wrapped;
    }
    if (!strcmp(method, "useHelpText")) {   /* on the main frame */
        mu_gfx_layer_invoke(o->layer, MU_GFX_MAIN, mu_gfx_layer_path(o->layer, MU_GFX_MAIN), method, args);
        return;
    }
    mu_gfx_layer_invoke(o->layer, movie, mu_gfx_layer_path(o->layer, movie), method, args);
}

static void option_show(wg_options *o, int open)
{
    o->option_open = open;
    mu_gfx_layer_invoke(o->layer, MU_GFX_OPTION, mu_gfx_layer_path(o->layer, MU_GFX_OPTION),
                        open ? "openWindow" : "closeWindow", "[]");
    mu_gfx_layer_show(o->layer, MU_GFX_OPTION, open);
}

static void option_emit(void *user, const char *line)
{
    wg_options *o = user;
    unsigned v = 0;
    if (!strncmp(line, "invoke ", 7))
        invoke_line(o, MU_GFX_OPTION, line + 7);
    else if (!strcmp(line, "call 00b6b21e"))
        option_show(o, 0);
    else if (!strcmp(line, "call 00be7079"))
        option_show(o, 1);
    else if (sscanf(line, "call 00c83c86 %x", &v) == 1 && o->h.monster_info)
        o->h.monster_info(o->h.user, (int)v);
}

/* ---- the system menu ---------------------------------------------------------------------------------- */

static void menu_emit(void *context, const char *line)
{
    wg_options *o = context;
    int kind;
    if (!strncmp(line, "invoke ", 7)) {
        invoke_line(o, MU_GFX_SYSTEM_MENU, line + 7);
        if (!strncmp(line + 7, "openWindow", 10)) {
            o->ccr.menu_open = 1;
            mu_gfx_layer_show(o->layer, MU_GFX_SYSTEM_MENU, 1);
        } else if (!strncmp(line + 7, "closeWindow", 11)) {
            o->ccr.menu_open = 0;
            mu_gfx_layer_show(o->layer, MU_GFX_SYSTEM_MENU, 0);
        }
    } else if (sscanf(line, "call 009a5ab2 %d", &kind) == 1) {
        if (kind == 1 || kind == 2)
            o->request = kind;   /* switch character / select server (0: the exit, after the countdown) */
    } else if (!strncmp(line, "call 00b39b2f ", 14)) {   /* the countdown box: "You will exit game in 5 seconds." */
        const char *q = strchr(line + 14, '"');
        char text[256] = "";
        size_t n = 0;
        for (const char *p = q ? q + 1 : ""; *p && *p != '"' && n + 1 < sizeof text; p++)
            text[n++] = *p == '\\' && p[1] ? *++p : *p;
        text[n] = 0;
        if (o->h.chat)
            o->h.chat(o->h.user, text);
        o->exit_ms = 5000.0;
    } else if (!strcmp(line, "call 00be7079")) {   /* onOptionClick: the option window opens */
        if (!o->option_open)
            mu_prg_options_event(&o->env, &o->opts, "close", SCENE_MAIN);
    }
}

static const char *menu_text(void *context, int32_t index)
{
    return env_text(context, index);
}

/* ---- public ------------------------------------------------------------------------------------------------ */

wg_options *wg_options_open(mu_gfx_layer *layer, const char *settings_dir, const wg_options_hooks *hooks)
{
    wg_options *o = calloc(1, sizeof *o);
    if (!o)
        return NULL;
    o->lang = mu_lang_load_default();
    o->layer = layer;
    if (hooks)
        o->h = *hooks;
    const char *dir = settings_dir ? settings_dir : getenv("MU_NATIVE_SETTINGS_DIR");
    if (dir && *dir)
        snprintf(o->path, sizeof o->path, "%s/option.ini", dir);
    else
        snprintf(o->path, sizeof o->path, "%s/Library/Application Support/MuTheMatrixNative/option.ini",
                 getenv("HOME") ? getenv("HOME") : ".");
    ini_load(o);
    o->request = -1;
    o->switch_minutes = 10.0f;
    o->effect_volume = 5.0f / 9.0f;
    mu_prg_options_env *e = &o->env;
    e->user = o;
    e->emit = option_emit;
    e->global_text = env_text;
    e->ini_int = env_ini_int;
    e->ini_write = env_ini_write;
    e->group_volume = env_group_volume;
    e->group_muted = env_group_muted;
    e->set_group_volume = env_set_group_volume;
    e->set_group_mute = env_set_group_mute;
    e->visible = env_visible;
    e->window = env_window;
    e->switch_state = env_switch;
    e->member_bool = env_member_bool;
    e->member_int = env_member_int;
    /* the join: 0x00c76115 and 0x00c76314, then the values applied (the client applies them through the
     * window's onChange path; at the join the sound volumes come from Data/Sound/Option.ini) */
    mu_prg_options_load(e, &o->opts);
    mu_prg_options_load_effect(e, &o->opts);
    o->effect_volume = o->opts.mute ? 0.0f : (float)o->opts.volume / 9.0f;
    /* the join's saved options (opcode 0xA0 sub 0x03, 0x0126f225) go through the setters 0x00c76022..0x00c760fa,
     * which mark the update: the window shows them (setDatas) at its first visible frame.  Offline, the
     * values are the stored ones. */
    const int32_t joined[9] = {o->opts.auto_attack, o->opts.whisper_sound, o->opts.slide_help, o->opts.player_info,
                               o->opts.monster_info, o->opts.music_play, o->opts.switch_mode, o->opts.switch_time,
                               o->opts.effect};
    for (int32_t i = 0; i < 9; i++)
        mu_prg_options_set(&o->opts, i, joined[i]);
    o->music_muted = !o->opts.music_play;
    if (o->h.monster_info)
        o->h.monster_info(o->h.user, o->opts.monster_info);
    /* the menu's environment (NATIVE-CHARCREATE-001's code; the world has no character list) */
    o->csg.context = o;
    o->csg.emit = menu_emit;
    o->csg.global_text = menu_text;
    o->ccr.gfx = &o->csg;
    o->ccr.scene = SCENE_MAIN;
    o->ccr.menu_check = 1;   /* 0x00c8cbe2: nothing blocks leaving offline */
    return o;
}

void wg_options_close(wg_options *o)
{
    mu_lang_free(o->lang);
    free(o);
}

void wg_options_set_hooks(wg_options *o, const wg_options_hooks *hooks)
{
    if (!o)
        return;
    if (hooks)
        o->h = *hooks;
    else
        memset(&o->h, 0, sizeof o->h);
    o->applied = 0;
    if (o->h.monster_info)
        o->h.monster_info(o->h.user, o->opts.monster_info);
}

/* the event of a KeyWindow channel call: [event, data] */
static void event_name(const char *args, char *out, size_t cap)
{
    const char *q = args ? strchr(args, '"') : NULL;
    size_t n = 0;
    if (q)
        for (q++; *q && *q != '"' && n + 1 < cap; q++)
            out[n++] = *q;
    out[n] = 0;
}

void wg_options_call(wg_options *o, int movie, const char *name, const char *args_json)
{
    if (!o)
        return;
    char event[64];
    if (!strcmp(name, "key")) {
        if (movie == MU_GFX_OPTION)   /* O: the window's toggle 0x00c75fe2 */
            mu_prg_options_event(&o->env, &o->opts, "close", SCENE_MAIN);
        else if (movie == MU_GFX_SYSTEM_MENU) {   /* Esc: 0x00c8c8b1 */
            if (o->option_open) {
                mu_prg_options_event(&o->env, &o->opts, "close", SCENE_MAIN);
                return;
            }
            mu_csm_toggle(&o->list, &o->ccr);
        }
        return;
    }
    event_name(args_json, event, sizeof event);
    if (!strcmp(event, "onOpenWindow")) {   /* the KeyWindow's open flag */
        int open = strstr(args_json, "true") != NULL;
        if (movie == MU_GFX_OPTION)
            o->option_open = open;
        else
            o->ccr.menu_open = (uint8_t)open;
        return;
    }
    if (movie == MU_GFX_OPTION) {
        const char *data = strchr(args_json, ',');
        o->change = data ? data + 1 : "";
        mu_prg_options_event(&o->env, &o->opts, event, SCENE_MAIN);
        o->change = NULL;
        if (!strcmp(event, "onChange"))
            store_defaults(o);   /* offline: the toggles the server would keep */
    } else if (movie == MU_GFX_SYSTEM_MENU) {
        mu_csm_event(&o->list, &o->ccr, event);
    }
}

void wg_options_step(wg_options *o, double dt_ms)
{
    if (!o)
        return;
    if (!o->applied && audio(o)) {   /* native: the stored volume and music switch (see the header) */
        o->applied = 1;
        if (env_ini_int(o, "DEFAULT", "Volum", -1) >= 0) {
            env_set_group_volume(o, 2, o->opts.mute ? 0.0f : (float)o->opts.volume / 9.0f);
            env_set_group_mute(o, 0, !o->opts.music_play);
        }
    }
    mu_prg_options_tick(&o->env, &o->opts);
    if (o->exit_ms > 0.0) {
        o->exit_ms -= dt_ms;
        if (o->exit_ms <= 0.0)
            o->request = 0;
    }
}

int wg_options_take_request(wg_options *o)
{
    if (!o)
        return -1;
    int r = o->request;
    o->request = -1;
    return r;
}

const mu_prg_options *wg_options_values(const wg_options *o)
{
    return o ? &o->opts : NULL;
}

const char *wg_options_path(const wg_options *o)
{
    return o ? o->path : "";
}
