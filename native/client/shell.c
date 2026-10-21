/* mu-client's scene manager runtime (NATIVE-SHELL-001). See shell.h. */
#define _POSIX_C_SOURCE 200809L
#include "shell.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "../../reconstructed/audio/client_audio.h"
#include "../../reconstructed/camera/client_input.h"
#include "../../reconstructed/ui/ui_loading.h"
#include "../../reconstructed/ui/ui_login.h"
#include "../../reconstructed/ui/ui_server.h"
#include "../../reconstructed/ui/ui_text.h"
#include "../core/mu_audio_host.h"
#include "../core/mu_charsel_ui.h"
#include "../core/mu_lang.h"
#include "../charsel/charsel_list_gfx.h"
#include "../core/mu_ui_assets.h"
#include "../core/mu_ui_font.h"
#include "../core/mu_ui_raster.h"

/* ---- the host's object space ------------------------------------------- */

/* Handles the shell returns for client objects; peek/poke land in these
 * buffers (the reconstructed routines read and write object fields). */
enum {
    H_UI = 0x10000000u, H_OWNER = 0x10010000u, H_GFX = 0x10020000u, H_GFX_A0 = 0x10030000u,
    H_STATE = 0x10040000u, H_CONFIG = 0x10050000u, H_HERO = 0x10060000u, H_RECORD = 0x10070000u,
    H_TABLE = 0x10080000u, H_LOADING = 0x10090000u, H_SINGLE = 0x100a0000u, H_MUSIC_LOGIN = 0x100b0000u,
    H_SERVER = 0x100c0000u, H_ID = 0x100d0000u, H_CAMERA = 0x100e0000u, H_GLOBALS = 0x01d1df00u
};

typedef struct region {
    uint32_t base, size;
    uint8_t *bytes;
} region;

#define REGIONS 16
#define TRANSITIONS 64

static const char *const LOGIN_THEME = "data\\music\\login_theme.mp3";
static const uint32_t FONT_HANDLES[4] = {0x0f0f0001u, 0x0f0f0002u, 0x0f0f0003u, 0x0f0f0004u};

/* GlobalText strings the scenes show, read off the live screen: used when no
 * table read from the client is loaded (NATIVE-LANG-001, MU_LANG_DIR). */
static const char *const TEXT_454 = "Mu The Matrix, Private Server Since 2005 / ";
static const char *const TEXT_455 = "  COPYRIGHT WEBZEN, INC. ALL RIGHTS RESERVED.";
static const char *const TEXT_565 = "Mu The Matrix Private Server";
static const char *const TEXT_566 = "More than 20 years Online";
static const char *const TEXT_567 = "enjoy our community!";

struct mu_shell {
    mu_shell_config cfg;
    mu_shell_platform platform;
    mu_scenemgr_globals g;
    mu_scenemgr_host host;
    mu_offline_session session;
    /* object space */
    region regions[REGIONS];
    uint8_t ui_mem[0x6600], owner_mem[0x240], gfx_mem[0x100], gfx_a0_mem[0x40], state_mem[0x40], config_mem[16],
        hero_mem[0x400], record_mem[0x200], table_mem[16], loading_mem[0x2a8], single_mem[0x300], music_mem[64],
        server_mem[32], id_mem[64], globals_mem[0x40], camera_mem[0x60];
    /* the 2D layer (one software GL subset over the frame) */
    mu_ui_raster raster;
    mu_ui_assets assets;
    mu_ui_state state;
    mu_ui_text text;
    mu_ui_font_set fonts;
    mu_ui_ctx ctx;
    mu_ui_sink inner;
    int32_t events[32][2], event_count;
    mu_ui_title *title;
    mu_ui_loading loading;
    int loading_created;
    mu_ui_server_win *server;
    int server_created, server_shown;
    uint8_t *frame;                 /* top-down RGBA for present */
    /* login panel (placeholder for the GFx account dialog) */
    int panel, field, typed[2];
    /* embeds */
    mu_charsel_embed *charsel;
    mu_charsel_ui *charsel_ui;
    mu_charsel_list_gfx *charsel_gfx;   /* NATIVE-CHARSEL-003 */
    long picks, pick_hits, double_clicks, gfx_callbacks, gfx_enters, gfx_creates;   /* closed visits */
    long charsel_rebuilds;          /* NATIVE-CHARCREATE-001: CreateCharacterScene again after a create / delete */
    mu_charsel_create_stats create_total;   /* the counters of closed visits */
    int32_t menu_seen, panel_close_seen;
    uint8_t legacy_hidden;
    uint32_t gfx_clock, last_click;
    int32_t last_click_x, last_click_y;
    int32_t enter_seen;
    mu_world_embed *world;
    mu_login_session *login;        /* NATIVE-LOGIN-001: the 3D login world */
    int login_draw3d;               /* the login render's 3D block ran this frame */
    int join_answer;                /* the offline session answered a join request */
    int32_t hero_slot;
    uint8_t hero_class;
    uint16_t hero_level;
    /* audio */
    mu_audio_host *audio;
    /* input */
    int32_t mouse_x, mouse_y;
    uint8_t button_down, button_up, button_held;
    int keys[64][2], key_count;
    int escapes;
    /* frame */
    uint32_t now, frame_start;
    int quit;
    char status[256];
    char transition_text[TRANSITIONS][96];
    const char *transition_lines[TRANSITIONS];
    int32_t transition_count;
    int32_t last_scene;
};

static void log_transition(mu_shell *s, const char *why)
{
    if (s->g.scene == s->last_scene)
        return;
    if (s->transition_count < TRANSITIONS) {
        snprintf(s->transition_text[s->transition_count], sizeof s->transition_text[0], "%d -> %d at %u ms: %s",
                 s->last_scene, s->g.scene, s->now, why);
        s->transition_lines[s->transition_count] = s->transition_text[s->transition_count];
        ++s->transition_count;
    }
    if (!s->cfg.quiet)
        fprintf(stderr, "scene %d -> %d (%s)\n", s->last_scene, s->g.scene, why);
    s->last_scene = s->g.scene;
}

static region *find(mu_shell *s, uint32_t address)
{
    for (int i = 0; i < REGIONS; ++i)
        if (s->regions[i].bytes && address >= s->regions[i].base && address - s->regions[i].base < s->regions[i].size)
            return &s->regions[i];
    return NULL;
}

static uint32_t peek(void *user, uint32_t address, int32_t size)
{
    mu_shell *s = user;
    uint32_t v = 0;
    for (int32_t i = 0; i < size; ++i) {
        region *r = find(s, address + (uint32_t)i);
        if (r)
            v |= (uint32_t)r->bytes[address + (uint32_t)i - r->base] << (8 * i);
    }
    return v;
}

static void poke(void *user, uint32_t address, uint32_t value, int32_t size)
{
    mu_shell *s = user;
    for (int32_t i = 0; i < size; ++i) {
        region *r = find(s, address + (uint32_t)i);
        if (r)
            r->bytes[address + (uint32_t)i - r->base] = (uint8_t)(value >> (8 * i));
    }
}

static void put_string(mu_shell *s, uint32_t address, const char *text)
{
    size_t n = strlen(text);
    for (size_t i = 0; i <= n; ++i)
        poke(s, address + (uint32_t)i, (uint8_t)text[i], 1);
}

static void get_string(mu_shell *s, uint32_t address, char *out, size_t size)
{
    size_t i = 0;
    for (; i + 1 < size; ++i) {
        char c = (char)peek(s, address + (uint32_t)i, 1);
        if (!c)
            break;
        out[i] = c;
    }
    out[i] = 0;
}

static void regions_init(mu_shell *s)
{
    region r[REGIONS] = {
        {H_UI, sizeof s->ui_mem, s->ui_mem}, {H_OWNER, sizeof s->owner_mem, s->owner_mem},
        {H_GFX, sizeof s->gfx_mem, s->gfx_mem}, {H_GFX_A0, sizeof s->gfx_a0_mem, s->gfx_a0_mem},
        {H_STATE, sizeof s->state_mem, s->state_mem}, {H_CONFIG, sizeof s->config_mem, s->config_mem},
        {H_HERO, sizeof s->hero_mem, s->hero_mem}, {H_RECORD, sizeof s->record_mem, s->record_mem},
        {H_TABLE, sizeof s->table_mem, s->table_mem}, {H_LOADING, sizeof s->loading_mem, s->loading_mem},
        {H_SINGLE, sizeof s->single_mem, s->single_mem}, {H_MUSIC_LOGIN, sizeof s->music_mem, s->music_mem},
        {H_SERVER, sizeof s->server_mem, s->server_mem}, {H_ID, sizeof s->id_mem, s->id_mem},
        {H_GLOBALS, sizeof s->globals_mem, s->globals_mem}, {H_CAMERA, sizeof s->camera_mem, s->camera_mem}};
    memcpy(s->regions, r, sizeof r);
    poke(s, H_OWNER + 0x22c, H_GFX, 4);
    poke(s, H_OWNER + 0xa0, H_GFX_A0, 4);
    poke(s, MU_SCENE_G_HERO, H_HERO, 4);
    put_string(s, H_MUSIC_LOGIN, LOGIN_THEME);
    put_string(s, H_SERVER, "offline");
}

/* ---- 2D layer ----------------------------------------------------------- */

static void sink_call(void *user, int op, const uint32_t *words, int count, const void *data, size_t bytes)
{
    mu_shell *s = user;
    if (op == MU_GDI_SELECTOBJECT && count >= 1)
        mu_ui_font_set_select(&s->fonts, words[0]);
    else if (op == MU_UI_EVENT && count >= 2 && s->event_count < 32) {
        s->events[s->event_count][0] = (int32_t)words[0];
        s->events[s->event_count][1] = (int32_t)words[1];
        s->event_count++;
    }
    s->inner.call(s->inner.user, op, words, count, data, bytes);
}

static const char *global_text(void *user, int32_t index)
{
    (void)user;
    const char *text = mu_lang_text(mu_lang_shared(), index);
    if (text)
        return text;
    switch (index) {
    case 0x235: return TEXT_565;
    case 0x236: return TEXT_566;
    case 0x237: return TEXT_567;
    default: return "";
    }
}

static int ui_init(mu_shell *s)
{
    int32_t w = s->cfg.width, h = s->cfg.height;
    if (mu_ui_raster_init(&s->raster, w, h))
        return 1;
    s->inner = mu_ui_raster_sink(&s->raster);
    s->state.sink.user = s;
    s->state.sink.call = sink_call;
    s->state.lookup = mu_ui_assets_lookup;
    s->state.lookup_user = &s->assets;
    mu_ui_state_init(&s->state, (uint32_t)w, (uint32_t)h);
    mu_ui_assets_init(&s->assets, s->cfg.root);
    mu_ui_font_set_open(&s->fonts, s->cfg.font, s->cfg.font, (uint32_t)w, FONT_HANDLES);
    s->text.gdi = mu_ui_font_set_gdi(&s->fonts);
    mu_ui_text_init(&s->text, &s->state);
    s->text.dib = calloc((size_t)mu_ui_text_dib_stride(s->text.dib_width) * (size_t)s->text.dib_height, 1);
    s->frame = malloc((size_t)w * (size_t)h * 4);
    if (!s->text.dib || !s->frame)
        return 1;
    mu_ui_ctx *ctx = &s->ctx;
    ctx->state = &s->state;
    ctx->text = &s->text;
    ctx->input.screen_width = w;
    ctx->input.screen_height = h;
    ctx->input.cursor_x = ctx->input.cursor_y = -1000;
    ctx->fonts.normal = FONT_HANDLES[0];
    ctx->fonts.bold = FONT_HANDLES[1];
    ctx->fonts.big = FONT_HANDLES[2];
    ctx->fonts.fixed = FONT_HANDLES[3];
    ctx->global_text = global_text;
    ctx->global_text_user = s;
    return 0;
}

static void load_texture(mu_shell *s, const char *path, uint32_t index, uint32_t filter, uint32_t wrap)
{
    int r = mu_ui_assets_load(&s->assets, &s->state, path, index, filter, wrap);
    if (r != MU_UI_TEXTURE_LOADED && !s->cfg.quiet)
        fprintf(stderr, "texture %#x %s: %s\n", index, path, r < 0 ? "missing" : "not loaded");
}

static void ensure_font_texture(mu_shell *s)
{
    if (!mu_ui_assets_lookup(&s->assets, 0x7532)) {
        load_texture(s, "Interface\\FontInput.tga", 0x7532, 0x2600, 0x2900);
        if (!mu_ui_assets_lookup(&s->assets, 0x7532))
            mu_ui_assets_add(&s->assets, &s->state, 0x7532, 256, 32, NULL);
    }
}

static void clear_2d(mu_shell *s)
{
    uint32_t color[4] = {0, 0, 0, 0x3f800000u};
    uint32_t mask = 0x4100;
    s->state.sink.call(s->state.sink.user, MU_GL_CLEARCOLOR, color, 4, NULL, 0);
    s->state.sink.call(s->state.sink.user, MU_GL_CLEAR, &mask, 1, NULL, 0);
}

static void copy_in(mu_shell *s, const uint8_t *rgba)
{
    size_t row = (size_t)s->raster.width * 4;
    for (int32_t y = 0; y < s->raster.height; ++y)
        memcpy(s->raster.rgba + (size_t)(s->raster.height - 1 - y) * row, rgba + (size_t)y * row, row);
}

/* The OFFLINE DEMO label (native, not client UI): two lines at the top left. */
static void offline_label(mu_shell *s, const char *hint)
{
    ensure_font_texture(s);
    mu_ui_ctx_set_font(&s->ctx, s->ctx.fonts.bold);
    mu_ui_text_set_back_color(&s->text, 0, 0, 0, 160);
    mu_ui_text_set_color(&s->text, 255, 210, 60, 255);
    mu_ui_render_text(&s->state, &s->text, 320, 4,
                      s->cfg.label && s->cfg.label[0] ? s->cfg.label
                                                      : "OFFLINE DEMO - native client, no server connection",
                      0, 0, 8, NULL);
    if (hint && hint[0]) {
        mu_ui_ctx_set_font(&s->ctx, s->ctx.fonts.normal);
        mu_ui_text_set_color(&s->text, 230, 230, 230, 255);
        mu_ui_render_text(&s->state, &s->text, 320, 18, hint, 0, 0, 8, NULL);
    }
    mu_ui_text_set_back_color(&s->text, 0, 0, 0, 0);
}

static void present_2d(mu_shell *s, const char *hint)
{
    mu_ui_begin_bitmap(&s->state);
    offline_label(s, hint);
    mu_ui_end_bitmap(&s->state);
    mu_ui_raster_read_top_down(&s->raster, s->frame);
    if (s->platform.present)
        s->platform.present(s->platform.user, s->frame);
}

/* ---- audio -------------------------------------------------------------- */

static void audio_open(mu_shell *s)
{
    if (!s->cfg.audio)
        return;
    mu_audio_host_config config;
    memset(&config, 0, sizeof config);
    config.engine.rate = (uint32_t)(s->cfg.audio_rate > 0 ? s->cfg.audio_rate : 44100);
    config.engine.game_root = s->cfg.root;
    char error[256];
    s->audio = mu_audio_host_new(&config, error, sizeof error);
    if (!s->audio && !s->cfg.quiet)
        fprintf(stderr, "audio: %s (continuing without music)\n", error);
}

static void music(mu_shell *s, uint32_t routine, uint32_t name)
{
    if (!s->audio)
        return;
    char path[128];
    get_string(s, name, path, sizeof path);
    if (!path[0])
        return;
    mu_audio_client *client = mu_audio_host_client(s->audio);
    if (routine == MU_SC_PLAY_MP3)
        mu_audio_play_mp3(client, path);
    else
        mu_audio_stop_mp3(client, path);
}

/* ---- embeds ------------------------------------------------------------- */

static void close_charsel(mu_shell *s)
{
    if (s->charsel) {
        const mu_charsel_session *cs = mu_charsel_embed_session(s->charsel);
        s->picks += cs->picks;
        s->pick_hits += cs->pick_hits;
        s->double_clicks += cs->double_clicks;
    }
    if (s->charsel_gfx) {
        mu_charsel_list_gfx_stats st;
        mu_charsel_list_gfx_stats_get(s->charsel_gfx, &st);
        s->gfx_callbacks += st.callbacks;
        s->gfx_enters += st.enters;
        s->gfx_creates += st.create_requests;
        mu_charsel_create_stats cs;
        mu_charsel_list_gfx_create_stats(s->charsel_gfx, &cs);
        mu_charsel_create_stats *t = &s->create_total;
        t->creates += cs.creates;
        t->created += cs.created;
        t->refused += cs.refused;
        t->deletes += cs.deletes;
        t->deleted += cs.deleted;
        t->messages += cs.messages;
        t->menu_events += cs.menu_events;
        t->preview_frames += cs.preview_frames;
        if (cs.last_message[0])
            snprintf(t->last_message, sizeof t->last_message, "%s", cs.last_message);
    }
    mu_charsel_list_gfx_close(s->charsel_gfx);
    s->charsel_gfx = NULL;
    if (s->charsel_ui) {
        mu_charsel_ui_free(s->charsel_ui);
        free(s->charsel_ui);
        s->charsel_ui = NULL;
    }
    if (s->charsel) {
        if (s->platform.embed_closing)
            s->platform.embed_closing(s->platform.user, MU_SHELL_EMBED_CHARSEL, s->charsel);
        mu_charsel_embed_close(s->charsel);
        s->charsel = NULL;
    }
}

static void close_world(mu_shell *s)
{
    if (s->world) {
        if (s->platform.embed_closing)
            s->platform.embed_closing(s->platform.user, MU_SHELL_EMBED_WORLD, s->world);
        mu_world_embed_close(s->world);
        s->world = NULL;
    }
}

/* NATIVE-LOGIN-001: OpenWorld(0x5e) in the login scene's creation: the 3D login world. The camera-record
 * manager the render reads (0x0098647b: +0xc the record, +0x10 the far scale) mirrors the session's record. */
static void close_login(mu_shell *s)
{
    if (s->login) {
        if (s->platform.embed_closing)
            s->platform.embed_closing(s->platform.user, MU_SHELL_EMBED_LOGIN, s->login);
        mu_login_free(s->login);
        free(s->login);
        s->login = NULL;
    }
}

static void open_login(mu_shell *s)
{
    if (s->login)
        return;
    s->login = calloc(1, sizeof *s->login);
    if (!s->login)
        return;
    if (mu_login_init(s->login, s->cfg.root, s->cfg.login_objects, (uint32_t)s->cfg.width, (uint32_t)s->cfg.height,
                      20.0f)) {
        snprintf(s->status, sizeof s->status, "login world: %s", s->login->error);
        if (!s->cfg.quiet)
            fprintf(stderr, "%s (the login screen stays black)\n", s->status);
        mu_login_free(s->login);
        free(s->login);
        s->login = NULL;
        return;
    }
    const mu_camera_info *info = &s->login->info;
    uint32_t record = H_CAMERA + 0x20u;
    poke(s, H_CAMERA + 0xc, record, 4);
    float one = 1.0f;
    uint32_t bits;
    memcpy(&bits, &one, 4);
    poke(s, H_CAMERA + 0x10, bits, 4);
    const float fields[9] = {info->angle[0], info->angle[1], info->angle[2], info->position[0], info->position[1],
                             info->position[2], info->z_distance, info->distance, info->fov};
    for (uint32_t i = 0; i < 9; ++i) {
        memcpy(&bits, &fields[i], 4);
        poke(s, record + 4u * i, bits, 4);
    }
    if (s->platform.embed_opened)
        s->platform.embed_opened(s->platform.user, MU_SHELL_EMBED_LOGIN, s->login);
}

static const char *charsel_text(void *user, int32_t index)
{
    (void)user;
    return mu_lang_text(mu_lang_shared(), index);
}

/* ---- NATIVE-CHARCREATE-001: the OFFLINE DEMO answers to create, delete and the menu's requests ---- */

static void store_save(mu_shell *s)
{
    if (mu_offline_session_save(&s->session) && !s->cfg.quiet)
        fprintf(stderr, "cannot write the character store %s\n", s->session.store_path);
}

static void hook_create(void *user, const char *name, uint8_t class_code, mu_ccr_created *answer)
{
    mu_shell *s = user;
    int32_t slot = -1;
    uint8_t server_class = 0;
    int result = mu_offline_session_create(&s->session, name, class_code, &slot, &server_class);
    memset(answer, 0, sizeof *answer);
    answer->result = (uint8_t)result;
    if (result == 1) {
        size_t n = strlen(name);
        memcpy(answer->name, name, n < sizeof answer->name ? n : sizeof answer->name);
        answer->slot = (uint8_t)slot;
        answer->level = 1;
        answer->class_code = server_class;
        store_save(s);
        log_transition(s, "OFFLINE DEMO: character created in the local store");
    }
    answer->created = (uint8_t)s->session.created_today;
    answer->limit = (uint8_t)s->session.create_limit;
}

static uint8_t hook_remove(void *user, int32_t slot)
{
    mu_shell *s = user;
    int result = mu_offline_session_delete(&s->session, slot);
    if (result == 1)
        store_save(s);
    return (uint8_t)result;
}

static void hook_menu(void *user, int kind)
{
    mu_shell *s = user;
    if (kind == 0) {   /* Exit Game, after the countdown box */
        s->quit = 1;
        log_transition(s, "menu: exit game");
    } else if (kind == 2) {   /* Select Server: offline the server's logout answer comes at once */
        s->g.scene = MU_SCENE_LOGIN;
        s->g.init_login = 0;
        s->g.init_character = 0;
        s->g.protocol = 0;
        log_transition(s, "menu: select server (offline answer)");
    }
}

/* CreateCharacterScene (the scene-5 tick's first step) with the session's list. */
static int open_charsel(mu_shell *s)
{
    mu_charsel_embed_config c;
    memset(&c, 0, sizeof c);
    c.root = s->cfg.root;
    c.list_path = s->session.characters_path[0] ? s->session.characters_path : NULL;
    c.list = &s->session.characters;   /* NATIVE-CHARCREATE-001: the session's characters (and the store's) */
    c.objects_dir = s->cfg.charsel_objects;
    c.width = s->cfg.width;
    c.height = s->cfg.height;
    c.slot = s->hero_slot >= 0 && mu_offline_session_character(&s->session, s->hero_slot) ? s->hero_slot : -1;
    char error[512];
    s->charsel = mu_charsel_embed_open(&c, error, sizeof error);
    if (!s->charsel) {
        snprintf(s->status, sizeof s->status, "character select: %s", error);
        fprintf(stderr, "%s\n", s->status);
        return 1;
    }
    mu_charsel_session *cs = mu_charsel_embed_session(s->charsel);
    cs->frame.clock.frame_tick = s->now;
    s->enter_seen = cs->enter_requests;
    s->charsel_ui = calloc(1, sizeof *s->charsel_ui);
    if (s->charsel_ui && mu_charsel_ui_init(s->charsel_ui, s->cfg.root, s->cfg.width, s->cfg.height, s->cfg.font, cs,
                                            NULL)) {
        free(s->charsel_ui);
        s->charsel_ui = NULL;
    }
    if (s->platform.embed_opened)
        s->platform.embed_opened(s->platform.user, MU_SHELL_EMBED_CHARSEL, s->charsel);
    if (s->cfg.gfx_dir) {   /* NATIVE-CHARSEL-003: the GFx list (the GFx manager loads the scene's movie) */
        mu_charsel_list_gfx_config gc;
        memset(&gc, 0, sizeof gc);
        gc.movie_dir = s->cfg.gfx_dir;
        gc.lib_path = s->cfg.gfx_lib;
        gc.width = s->cfg.width;
        gc.height = s->cfg.height;
        gc.scale = s->cfg.gfx_scale;
        gc.text = charsel_text;
        gc.log_path = s->cfg.gfx_log;
        gc.create = 1;   /* NATIVE-CHARCREATE-001 */
        gc.game_root = s->cfg.root;
        gc.lang_dir = getenv("MU_LANG_DIR");
        gc.hooks.user = s;
        gc.hooks.create = hook_create;
        gc.hooks.remove = hook_remove;
        gc.hooks.menu = hook_menu;
        gc.created = s->session.created_today;
        gc.limit = s->session.create_limit;
        s->charsel_gfx = mu_charsel_list_gfx_open(&gc, cs, error, sizeof error);
        if (!s->charsel_gfx && !s->cfg.quiet)
            fprintf(stderr, "character select GFx: %s (continuing without the list)\n", error);
        s->gfx_clock = s->now;
    }
    s->menu_seen = s->panel_close_seen = 0;
    s->legacy_hidden = 0;
    return 0;
}

/* NATIVE-CHARCREATE-001: the created / deleted answer cleared InitCharacterScene, so the next tick runs
 * CreateCharacterScene again with the new list: the scene and CCharSelMainWin are rebuilt, the GFx windows
 * (the GFx manager's) stay and get the list again. */
static int rebuild_charsel(mu_shell *s)
{
    mu_charsel_list_gfx *gfx = s->charsel_gfx;
    s->charsel_gfx = NULL;   /* kept across the rebuild */
    const mu_charsel_session *old = s->charsel ? mu_charsel_embed_session(s->charsel) : NULL;
    if (old) {
        s->picks += old->picks;
        s->pick_hits += old->pick_hits;
        s->double_clicks += old->double_clicks;
    }
    if (s->charsel_ui) {
        mu_charsel_ui_free(s->charsel_ui);
        free(s->charsel_ui);
        s->charsel_ui = NULL;
    }
    if (s->charsel) {
        if (s->platform.embed_closing)
            s->platform.embed_closing(s->platform.user, MU_SHELL_EMBED_CHARSEL, s->charsel);
        mu_charsel_embed_close(s->charsel);
        s->charsel = NULL;
    }
    const char *dir = s->cfg.gfx_dir;
    s->cfg.gfx_dir = NULL;
    int status = open_charsel(s);
    s->cfg.gfx_dir = dir;
    s->charsel_gfx = gfx;
    ++s->charsel_rebuilds;
    if (status)
        return status;
    mu_charsel_session *cs = mu_charsel_embed_session(s->charsel);
    cs->selected = cs->shown = -1;   /* CreateCharacterScene: SelectedHero = -1 */
    mu_charsel_list_gfx_rebind(gfx, cs);
    return 0;
}

/* The join-map answer and the main-scene initialisation: the world of the
 * session's join line with the Hero's class (written by start loading) and
 * the list entry's equipment. */
static int open_world(mu_shell *s)
{
    mu_offline_join join = mu_offline_session_join(&s->session, s->hero_slot);
    const mu_charsel_entry *entry = mu_offline_session_character(&s->session, s->hero_slot);
    mu_world_embed_config c;
    memset(&c, 0, sizeof c);
    c.root = s->cfg.root;
    c.world = join.world;
    c.class_byte = s->hero_class;
    c.tile[0] = join.tile[0];
    c.tile[1] = join.tile[1];
    c.angle = join.angle;
    c.width = s->cfg.width;
    c.height = s->cfg.height;
    c.sound_table = s->cfg.sound_table;
    c.audio = s->cfg.audio && s->cfg.sound_table;
    c.audio_rate = s->cfg.audio_rate;
    c.placement = join.world == 0 ? s->cfg.placement : NULL;
    c.combat = s->cfg.world_combat;   /* NATIVE-APP-001 */
    c.ground_items = s->cfg.world_items;
    c.npc = s->cfg.world_npc;
    c.npc_demo = join.world == 0 ? s->cfg.npc_demo : NULL;
    c.no_names = s->cfg.world_no_names;
    c.no_env = s->cfg.world_no_env;
    c.no_particles = s->cfg.world_no_particles;
    c.players = join.world == 0 ? s->cfg.players : NULL;   /* NATIVE-PLAYERS-001: Lorencia's demo players */
    c.objects_dir = s->cfg.world_objects;
    c.quiet = s->cfg.quiet;
    c.hero_name = entry && entry->name[0] ? entry->name : NULL;
    for (int i = 0; entry && i < MU_CHARACTER_ITEMS; ++i)
        c.items[i] = entry->items[i];
    char error[512];
    s->world = mu_world_embed_open(&c, error, sizeof error);
    if (!s->world) {
        snprintf(s->status, sizeof s->status, "world %d: %s", join.world, error);
        fprintf(stderr, "%s\n", s->status);
        return 1;
    }
    mu_world_embed_set_clock(s->world, s->now);
    s->g.world = join.world;
    s->g.world_folder = mu_world_embed_folder(s->world);
    if (s->platform.embed_opened)
        s->platform.embed_opened(s->platform.user, MU_SHELL_EMBED_WORLD, s->world);
    return 0;
}

/* ---- the login scene's server window and the offline account panel ----- */

static void server_open(mu_shell *s)
{
    if (!s->server)
        s->server = calloc(1, sizeof *s->server);
    if (!s->server)
        return;
    mu_ui_server_win_init(s->server, &s->session.servers);
    mu_ui_server_win_create(&s->ctx, s->server);
    mu_ui_server_win_place(&s->ctx, s->server);
    s->server_created = 1;
    s->server_shown = 0;
}

static void server_hide(mu_shell *s)
{
    if (s->server && s->server_shown) {
        s->server->win.cls->show(&s->ctx, &s->server->win, 0);
        mu_ui_win_set_active(&s->server->win, 0);
    }
    s->server_shown = 0;
}

static void choose_server(mu_shell *s, int32_t slot)
{
    int32_t group = s->server && s->server->group ? (int32_t)(s->server->group - s->session.servers.groups) : 0;
    mu_offline_session_choose_server(&s->session, group, slot);
    server_hide(s);
    s->panel = 1;          /* the account dialog (GFx in the client) appears after the server choice */
    s->field = 0;
    s->typed[0] = s->typed[1] = 0;
}

static void login_accept(mu_shell *s)
{
    s->g.protocol = mu_offline_session_login(&s->session);   /* what the login answer sets */
    s->panel = 0;
    s->typed[0] = s->typed[1] = 0;   /* nothing typed is kept */
}

/* ---- host calls ----------------------------------------------------------- */

static void title_step(mu_shell *s, uint32_t now_step, uint32_t total)
{
    if (!s->title)
        return;
    clear_2d(s);
    mu_ui_title_render(&s->state, s->title, now_step, total);
    present_2d(s, "title: startup progress");
}

static uint32_t host_call(void *user, const mu_scenemgr_call *c)
{
    mu_shell *s = user;
    switch (c->routine) {
    case MU_SC_UI_MANAGER: return H_UI;
    case 0x00ac3bf7u: return H_OWNER;
    case 0x009a595bu: return H_STATE;
    case 0x0095f75du: return H_CONFIG;   /* +4 = 0: the lo_back_s5 title pictures */
    case 0x0095f6dbu: return H_TABLE;
    case 0x00cd4ea8u: case 0x00cd5d29u: case 0x00c74245u: case 0x00f2bb92u: case 0x00f2efe9u: case 0x00988c5cu:
        return H_SINGLE;
    case MU_SC_GET_TICK_COUNT:
        return s->platform.ticks ? s->platform.ticks(s->platform.user) : s->now;
    case MU_SC_RAND: return (uint32_t)rand() & 0x7fffu;
    case MU_SC_LOAD_BITMAP:
        if (c->text)
            load_texture(s, c->text, c->args[1], c->args[2], c->args[3]);
        return 1;
    case MU_SC_DELETE_BITMAP: return 0;   /* the native asset table keeps decoded textures */
    /* title */
    case MU_SC_TITLE_CREATE:
        if (!s->title)
            s->title = calloc(1, sizeof *s->title);
        if (s->title)
            mu_ui_title_create(&s->state, s->title, s->cfg.width, s->cfg.height);
        return 0;
    case MU_SC_OPEN_BASIC_DATA:
        /* The client's startup loader renders the title with progress 0..8 of 9
         * at fixed points (static reading of 0x0182049e); the native client has
         * none of that data to load and shows the nine frames. */
        for (uint32_t i = 0; i <= 8; ++i) {
            title_step(s, i, 9);
            if (s->platform.pause && s->cfg.title_step_ms)
                s->platform.pause(s->platform.user, s->cfg.title_step_ms);
        }
        return 0;
    case MU_SC_TITLE_RENDER: title_step(s, c->args[1], c->args[2]); return 0;
    case MU_SC_TITLE_RELEASE:
        free(s->title);
        s->title = NULL;
        return 0;
    /* login scene */
    case MU_SC_OPEN_WORLD:
        if ((int32_t)c->args[0] == MU_SCENE_LOGIN_WORLD)
            open_login(s);
        if (s->audio)
            mu_audio_set_group_volume(mu_audio_host_client(s->audio), MU_AUDIO_GROUP_MUSIC,
                                      mu_audio_world_music_volume((int32_t)c->args[0]));
        return 1;
    case 0x0182a34cu: {   /* OpenLogoSceneData: the login overlay and server window textures */
        static const struct { uint32_t index; const char *path; uint32_t filter, wrap; } t[] = {
            {0x7b1e, "Logo\\MU-logo.tga", 0x2601, 0x2900}, {0x7b1f, "Logo\\MU-logo_g.tga", 0x2601, 0x2900},
            {0x7532, "Interface\\FontInput.tga", 0x2600, 0x2900}, {0x7b0e, "Interface\\cha_bt.tga", 0x2600, 0x2900},
            {0x7b0f, "Interface\\server_b2_all.tga", 0x2600, 0x2900},
            {0x7b10, "Interface\\server_b2_loding.jpg", 0x2600, 0x2900},
            {0x7b11, "Interface\\server_deco_all.tga", 0x2600, 0x2900},
            {0x7b19, "Interface\\server_ex03.tga", 0x2600, 0x2901},
            {0x7b1a, "Interface\\server_ex01.tga", 0x2600, 0x2900},
            {0x7b1b, "Interface\\server_ex02.jpg", 0x2600, 0x2901}};
        for (size_t i = 0; i < sizeof t / sizeof t[0]; ++i)
            load_texture(s, t[i].path, t[i].index, t[i].filter, t[i].wrap);
        ensure_font_texture(s);
        return 0;
    }
    case 0x011e2dc0u: server_open(s); return 0;   /* CUIMng::CreateLoginScene */
    /* the login tick head and render (NATIVE-LOGIN-001) */
    case MU_SC_LOGIN_CREATE: mu_scenemgr_login_create(&s->host, &s->g); return 0;
    case MU_SC_MOVE_OBJECTS:
        if (s->login && s->g.scene == MU_SCENE_LOGIN)
            mu_login_step(s->login, s->now);   /* the frame-light copy and MoveObjects */
        return 0;
    case MU_SC_CAMERA_RECORD: return H_CAMERA;
    case MU_SC_SCREEN_WIDTH: return (uint32_t)s->cfg.width;
    case MU_SC_RENDER_TERRAIN: s->login_draw3d = 1; return 0;
    case 0x0121c055u:   /* connect: the offline session's server list arrives (handler 0x0127ec2f) */
        if (s->server_created) {
            mu_ui_server_win_open(&s->ctx, s->server);
            s->server_shown = 1;
        }
        return 1;
    case MU_SC_PLAY_MP3: case MU_SC_STOP_MP3: music(s, c->routine, c->args[0]); return 0;
    case 0x00988d22u:   /* the character-list request: the session's list arrives */
        s->g.protocol = mu_offline_session_character_list(&s->session);
        return 0;
    /* start loading */
    case 0x009a13f4u: {   /* CharactersClient lookup of SelectedHero */
        const mu_charsel_entry *e = mu_offline_session_character(&s->session, (int32_t)c->args[0]);
        if (!e)
            return 0;
        memset(s->record_mem, 0, sizeof s->record_mem);
        poke(s, H_RECORD + 0x12, e->class_byte, 1);
        poke(s, H_RECORD + 0x13, 0, 1);
        poke(s, H_RECORD + 0x14, 0, 1);
        poke(s, H_RECORD + 0x144, e->level, 2);
        put_string(s, H_RECORD + 0x44, e->name);
        return H_RECORD;
    }
    case MU_SCENE_NET_SEND:
        if (s->g.scene == MU_SCENE_CHARACTER)
            s->join_answer = 1;   /* the join request: the session answers at once */
        return 0;
    case 0x00a00031u: s->hero_level = (uint16_t)c->args[0]; return 0;
    case MU_SC_STRCPY: {
        char text[64];
        get_string(s, c->args[1], text, sizeof text);
        put_string(s, c->args[0], text);
        return c->args[0];
    }
    case MU_SC_STRLEN: {
        char text[64];
        get_string(s, c->args[0], text, sizeof text);
        return (uint32_t)strlen(text);
    }
    /* loading scene */
    case MU_SC_NEW: return H_LOADING;
    case MU_SC_LOADING_CTOR: return c->ecx;
    case MU_SC_LOADING_CREATE:
        mu_ui_loading_create(&s->state, &s->loading, s->cfg.width, s->cfg.height);
        s->loading_created = 1;
        return 0;
    case MU_SC_GL_CLEAR: clear_2d(s); return 0;
    case MU_SC_BEGIN_BITMAP: mu_ui_begin_bitmap(&s->state); return 0;
    case MU_SC_LOADING_RENDER:
        if (s->loading_created)
            mu_ui_loading_render(&s->state, &s->loading);
        return 0;
    case MU_SC_END_BITMAP: mu_ui_end_bitmap(&s->state); return 0;
    case MU_SC_SWAP_BUFFERS: present_2d(s, "loading the world"); return 1;
    case MU_SC_VCALL:
        if (c->ecx == H_LOADING && c->args[0] == 0)
            s->loading_created = 0;   /* scalar deleting destructor */
        return 0;
    default:
        return 0;
    }
}

/* ---- frame driver logic per scene ----------------------------------------- */

static void login_frame(mu_shell *s)
{
    if (!s->g.init_login)
        s->panel = 0;
    mu_scenemgr_login_tick_head(&s->host, &s->g);   /* creation on the first step, then the 3D movers */
    for (int k = 0; k < s->key_count; ++k) {
        int vk = s->keys[k][0];
        if (!s->keys[k][1])
            continue;
        if (s->panel) {
            if (vk == 0x0d)
                login_accept(s);
            else if (vk == 0x09)
                s->field ^= 1;
            else if (vk == 0x08 && s->typed[s->field] > 0)
                --s->typed[s->field];
            else if (vk == 0x1b) {
                s->panel = 0;   /* back to the server list */
                if (s->server_created) {
                    mu_ui_server_win_open(&s->ctx, s->server);
                    s->server_shown = 1;
                }
            }
        } else if (vk == 0x0d && s->server_shown) {
            /* keyboard shortcut (native): the first selectable server of the shown group */
            mu_ui_server_group *g = s->server->group ? s->server->group : &s->session.servers.groups[0];
            for (int i = 0; i < g->server_count; ++i)
                if (g->servers[i].percent < 0x80) {
                    choose_server(s, g->servers[i].slot);
                    break;
                }
        } else if (vk == 0x1b) {
            if (++s->escapes >= 2)
                s->quit = 1;
        }
        if (vk != 0x1b)
            s->escapes = 0;
    }
    if (s->server_shown) {
        s->event_count = 0;
        s->ctx.input.cursor_x = s->mouse_x;
        s->ctx.input.cursor_y = s->mouse_y;
        s->ctx.input.lbutton_down = s->button_down;
        s->ctx.input.lbutton_up = s->button_up;
        mu_ui_win_update(&s->ctx, &s->server->win, 40.0);
        s->ctx.input.lbutton_down = s->ctx.input.lbutton_up = 0;
        for (int32_t e = 0; e < s->event_count; ++e) {
            if (s->events[e][0] == MU_UI_EVENT_SERVER_GROUP)
                mu_ui_server_win_update_display(&s->ctx, s->server);   /* the group's list reply */
            else if (s->events[e][0] == MU_UI_EVENT_SERVER_CONNECT)
                choose_server(s, s->events[e][1]);
        }
    }
    mu_scenemgr_login_tick_tail(&s->host, &s->g);
    log_transition(s, "login accepted (offline session), character list requested");
    if (s->g.scene == MU_SCENE_LOGIN) {
        /* the login render 0x01857ed9, its 3D part; the front end draws what it names */
        s->login_draw3d = 0;
        mu_scenemgr_login_render_3d(&s->host, &s->g);
        if (s->login)
            mu_login_begin_render(s->login, s->now, s->login_draw3d);
    } else {
        close_login(s);   /* scene 5 opens World94 */
    }
}

static void charsel_frame(mu_shell *s, uint32_t now)
{
    if (!s->g.init_character) {
        s->g.init_character = 1;
        s->g.world = MU_SCENE_CHARACTER_WORLD;
        s->g.world_folder = MU_SCENE_CHARACTER_WORLD;
        if (!s->charsel && open_charsel(s)) {
            s->g.scene = MU_SCENE_LOGIN;   /* cannot show the scene: back to the server list */
            s->g.init_login = 0;
            log_transition(s, "character select did not load");
            return;
        }
    }
    if (!s->charsel)
        return;
    mu_charsel_session *cs = mu_charsel_embed_session(s->charsel);
    for (int k = 0; k < s->key_count; ++k) {
        int vk = s->keys[k][0], down = s->keys[k][1];
        /* NATIVE-CHARCREATE-001: the Caution box and the create panel's name box take the keys first; with the
         * GFx list, Esc is the scene tick's (the menu, or the create panel closed) */
        if (s->charsel_gfx && mu_charsel_list_gfx_key(s->charsel_gfx, vk, down))
            continue;
        if (vk == 0x1b && s->charsel_gfx) {
            mu_charsel_key(cs, vk, down);
            mu_charsel_message(cs, down ? 0x100u : 0x101u, (uint32_t)vk, 0);
            continue;
        }
        if (vk == 0x1b) {
            if (down) {
                /* offline shortcut: back to the server list (the client's GFx menu asks the server) */
                s->g.scene = MU_SCENE_LOGIN;
                s->g.init_login = 0;
                s->g.init_character = 0;
                s->g.protocol = 0;
                log_transition(s, "Esc: back to the server list (offline shortcut)");
                return;
            }
            continue;
        }
        if (down && (vk == 0x25 || vk == 0x27)) {
            mu_charsel_embed_select_next(s->charsel, vk == 0x27 ? 1 : -1);   /* the GFx list's selection */
            if (s->charsel_gfx)
                mu_charsel_list_gfx_select_slot(s->charsel_gfx, cs->selected);
            continue;
        }
        if (down && vk >= 0x31 && vk < 0x31 + cs->list.count) {
            if (s->charsel_gfx)   /* native shortcut through the list's row click */
                mu_charsel_list_gfx_select_slot(s->charsel_gfx, cs->list.entries[vk - 0x31].slot);
            else
                mu_charsel_select(cs, cs->list.entries[vk - 0x31].slot);
            continue;
        }
        mu_charsel_key(cs, vk, down);
        mu_charsel_message(cs, down ? 0x100u : 0x101u, (uint32_t)vk, 0);
    }
    mu_charsel_message(cs, MU_WM_MOUSEMOVE, 0, ((uint32_t)(uint16_t)s->mouse_y << 16) | (uint16_t)s->mouse_x);
    if (s->charsel_gfx) {
        mu_charsel_list_gfx_advance(s->charsel_gfx, (double)(now - s->gfx_clock));
        s->gfx_clock = now;
    }
    if (s->charsel_gfx) {   /* NATIVE-CHARCREATE-001: the GFx window's flags the tick reads */
        mu_charsel_create_stats st;
        mu_charsel_list_gfx_create_stats(s->charsel_gfx, &st);
        cs->gfx_create_open = st.create_open;
        cs->gfx_flag_79 = st.caution_open;
    }
    mu_charsel_update(cs, now);
    if (s->charsel_gfx && cs->menu_requests != s->menu_seen) {   /* Esc: 0x00c8c8b1 */
        s->menu_seen = cs->menu_requests;
        mu_charsel_list_gfx_menu(s->charsel_gfx);
    }
    if (s->charsel_gfx && cs->panel_close_requests != s->panel_close_seen) {   /* Esc: 0x00b49bf4(0) */
        s->panel_close_seen = cs->panel_close_requests;
        mu_charsel_list_gfx_close_panel(s->charsel_gfx);
    }
    if (s->charsel_ui) {
        s->charsel_ui->event_count = 0;
        mu_charsel_ui_update(s->charsel_ui, cs, s->mouse_x, s->mouse_y, s->button_down, s->button_up);
        /* CCharSelMainWin's events: Connect enters (0x0185a75a(0)); with the GFx windows, Create, Menu, the
         * refusals and the delete confirmation (NATIVE-CHARCREATE-001) */
        for (int32_t i = 0; i < s->charsel_ui->event_count; ++i) {
            int32_t code = s->charsel_ui->events[i][0], argument = s->charsel_ui->events[i][1];
            if (code == MU_UI_EVENT_CHARSEL_CONNECT)
                ++cs->enter_requests;
            else if (s->charsel_gfx)
                mu_charsel_list_gfx_event(s->charsel_gfx, code, argument);
        }
        s->charsel_ui->event_count = 0;
    }
    if (s->charsel_gfx) {
        mu_charsel_create_stats st;
        mu_charsel_list_gfx_create_stats(s->charsel_gfx, &st);
        if (s->charsel_ui && st.legacy_hidden != s->legacy_hidden) {   /* the menu hides CCharSelMainWin */
            s->legacy_hidden = st.legacy_hidden;
            mu_ui_charsel_win_show(&s->charsel_ui->ctx, &s->charsel_ui->win.win, !st.legacy_hidden);
        }
        if (st.rebuild) {
            mu_charsel_list_gfx_create_done(s->charsel_gfx);
            if (rebuild_charsel(s)) {
                s->g.scene = MU_SCENE_LOGIN;
                s->g.init_login = 0;
                log_transition(s, "character select did not load");
                return;
            }
            cs = mu_charsel_embed_session(s->charsel);
        }
        if (s->quit)
            return;
    }
    if (cs->enter_requests != s->enter_seen) {
        s->enter_seen = cs->enter_requests;
        /* the scene tick called 0x0185a75a(0): the join request */
        s->g.selected_hero = cs->selected;
        s->join_answer = 0;
        mu_scenemgr_start_loading(&s->host, &s->g, 0);
        if (s->join_answer) {   /* the server's answer: 0x0185a75a(1) */
            s->join_answer = 0;
            mu_scenemgr_start_loading(&s->host, &s->g, 1);
            s->hero_slot = s->g.selected_hero;
            s->hero_class = (uint8_t)peek(s, H_HERO + 0x187, 1);
            log_transition(s, "Enter: join answered by the offline session");
        }
    }
    if (s->g.scene == MU_SCENE_CHARACTER)
        mu_charsel_begin_render(cs, now);
}

static void world_frame(mu_shell *s, uint32_t now)
{
    if (!s->world)
        return;
    if (!s->g.init_main)
        s->g.init_main = 1;   /* the main-scene initialisation (0x0185613e first step, static) */
    for (int k = 0; k < s->key_count; ++k) {
        int vk = s->keys[k][0], down = s->keys[k][1];
        if (vk == 0x1b && down) {
            /* the GFx menu's "select character" goes through the server; offline the
             * answer (handler 0x0125294e subcode 1) comes at once */
            close_world(s);
            mu_scenemgr_return_to_character(&s->g);
            s->g.protocol = mu_offline_session_character_list(&s->session);
            log_transition(s, "Esc: back to character select");
            return;
        }
        mu_world_embed_key(s->world, vk, down);
        mu_world_embed_message(s->world, down ? 0x100u : 0x101u, (uint32_t)vk, 0);
    }
    mu_world_embed_advance(s->world, now);
}

static void frame_driver(mu_shell *s)
{
    switch (s->g.scene) {
    case MU_SCENE_LOGIN: login_frame(s); break;
    case MU_SCENE_CHARACTER: charsel_frame(s, s->now); break;
    case MU_SCENE_MAIN: world_frame(s, s->now); break;
    default: break;
    }
}

static uint32_t dispatch_call(void *user, const mu_scenemgr_call *c)
{
    mu_shell *s = user;
    switch (c->routine) {
    case MU_SC_INTRO: mu_scenemgr_intro(&s->host, &s->g, c->args[0]); return 0;
    case MU_SC_LOADING: mu_scenemgr_loading(&s->host, &s->g, c->args[0]); return 0;
    case MU_SC_FRAME: frame_driver(s); return 0;
    default: return host_call(user, c);
    }
}

/* ---- public ----------------------------------------------------------------- */

mu_shell *mu_shell_new(const mu_shell_config *config, const mu_shell_platform *platform, char *error,
                       size_t error_size)
{
    mu_shell *s = calloc(1, sizeof *s);
    if (!s) {
        snprintf(error, error_size, "out of memory");
        return NULL;
    }
    s->cfg = *config;
    if (!s->cfg.font)
        s->cfg.font = "Tahoma";
    if (platform)
        s->platform = *platform;
    if (config->session_path) {
        if (mu_offline_session_load(&s->session, config->session_path, config->root, error, error_size)) {
            free(s);
            return NULL;
        }
    } else {
        mu_offline_session_default(&s->session);
        snprintf(s->session.root, sizeof s->session.root, "%s", config->root ? config->root : "");
    }
    {   /* NATIVE-CHARCREATE-001: the OFFLINE DEMO character store */
        char today[16];
        time_t t = time(NULL);
        struct tm tm;
        localtime_r(&t, &tm);
        strftime(today, sizeof today, "%Y-%m-%d", &tm);
        if (mu_offline_session_use_store(&s->session, config->store_path, today, error, error_size)) {
            free(s);
            return NULL;
        }
    }
    regions_init(s);
    if (ui_init(s)) {
        snprintf(error, error_size, "2D layer initialisation failed");
        mu_shell_free(s);
        return NULL;
    }
    audio_open(s);
    s->host.user = s;
    s->host.call = dispatch_call;
    s->host.peek = peek;
    s->host.poke = poke;
    /* the start state: SceneFlag 2 (title), no saved account name (remember-ID off), nothing selected */
    s->g.scene = MU_SCENE_INTRO;
    s->g.music_login = H_MUSIC_LOGIN;
    s->g.server_address = H_SERVER;
    s->g.server_port = 0;
    s->g.remember_id = 1;
    s->g.id_buffer = H_ID;
    s->g.selected_hero = -1;
    s->hero_slot = -1;
    s->last_scene = s->g.scene;
    return s;
}

void mu_shell_free(mu_shell *s)
{
    if (!s)
        return;
    close_charsel(s);
    close_world(s);
    close_login(s);
    free(s->title);
    free(s->server);
    free(s->text.dib);
    free(s->frame);
    mu_ui_font_set_close(&s->fonts);
    mu_ui_assets_free(&s->assets);
    mu_ui_raster_free(&s->raster);
    if (s->audio)
        mu_audio_host_free(s->audio);
    free(s);
}

void mu_shell_mouse_move(mu_shell *s, int32_t x, int32_t y)
{
    s->mouse_x = x;
    s->mouse_y = y;
    if (s->g.scene == MU_SCENE_CHARACTER && s->charsel_gfx)
        mu_charsel_list_gfx_mouse(s->charsel_gfx, 0, 0, x, y);
    if (s->g.scene == MU_SCENE_MAIN && s->world)
        mu_world_embed_message(s->world, MU_WM_MOUSEMOVE, s->button_held ? 1u : 0u,
                               ((uint32_t)(uint16_t)y << 16) | (uint16_t)x);
}

void mu_shell_mouse_button(mu_shell *s, int button, int down)
{
    if (s->g.scene == MU_SCENE_CHARACTER && s->charsel) {
        /* NATIVE-CHARSEL-003: the GFx list takes the clicks over it; elsewhere a second press within 500 ms
         * and 4 pixels is WM_LBUTTONDBLCLK (the client's window class has CS_DBLCLKS), which the render's pick
         * turns into an entry when it is over a character */
        if (s->charsel_gfx && mu_charsel_list_gfx_mouse(s->charsel_gfx, down ? 1 : 2, button, s->mouse_x,
                                                        s->mouse_y) && down)
            return;
        if (button == 0 && down) {
            mu_charsel_session *cs = mu_charsel_embed_session(s->charsel);
            uint32_t lp = ((uint32_t)(uint16_t)s->mouse_y << 16) | (uint16_t)s->mouse_x;
            int dbl = s->last_click && s->now - s->last_click < 500 && abs(s->mouse_x - s->last_click_x) <= 4 &&
                      abs(s->mouse_y - s->last_click_y) <= 4;
            mu_charsel_message(cs, dbl ? MU_WM_LBUTTONDBLCLK : MU_WM_LBUTTONDOWN, 1u, lp);
            s->last_click = dbl ? 0 : (s->now ? s->now : 1);
            s->last_click_x = s->mouse_x;
            s->last_click_y = s->mouse_y;
        } else if (button == 0) {
            mu_charsel_message(mu_charsel_embed_session(s->charsel), MU_WM_LBUTTONUP, 0u,
                               ((uint32_t)(uint16_t)s->mouse_y << 16) | (uint16_t)s->mouse_x);
        }
    }
    if (button == 0) {
        if (down) {
            s->button_down = 1;
            s->button_held = 1;
        } else {
            s->button_up = 1;
            s->button_held = 0;
        }
    }
    if (s->g.scene == MU_SCENE_MAIN && s->world) {
        uint32_t message = button == 0 ? (down ? 0x201u : 0x202u) : button == 1 ? (down ? 0x204u : 0x205u)
                                                                               : (down ? 0x207u : 0x208u);
        mu_world_embed_message(s->world, message, down && button == 0 ? 1u : 0u,
                               ((uint32_t)(uint16_t)s->mouse_y << 16) | (uint16_t)s->mouse_x);
    }
}

void mu_shell_wheel(mu_shell *s, int32_t delta)
{
    if (s->g.scene == MU_SCENE_MAIN && s->world)
        mu_world_embed_message(s->world, MU_WM_MOUSEWHEEL, (uint32_t)(uint16_t)(delta * 120) << 16, 0);
}

void mu_shell_key(mu_shell *s, int vk, int down)
{
    if (s->key_count < 64) {
        s->keys[s->key_count][0] = vk;
        s->keys[s->key_count][1] = down;
        s->key_count++;
    }
}

void mu_shell_char(mu_shell *s, int ch)
{
    if (s->g.scene == MU_SCENE_CHARACTER && s->charsel_gfx && ch > 0 && ch < 0x100) {   /* NATIVE-CHARCREATE-001 */
        char utf8[3] = {0};
        if (ch < 0x80) {
            utf8[0] = (char)ch;
        } else {
            utf8[0] = (char)(0xc0 | (ch >> 6));
            utf8[1] = (char)(0x80 | (ch & 0x3f));
        }
        mu_charsel_list_gfx_text(s->charsel_gfx, utf8);
        return;
    }
    if (s->panel && ch >= 32 && ch < 127 && s->typed[s->field] < 10)
        ++s->typed[s->field];   /* counted for the masked display only; the character itself is dropped */
}

void mu_shell_frame(mu_shell *s, uint32_t now)
{
    s->now = now;
    s->frame_start = now;
    /* leaving character select: the scene's objects go before the loading scene */
    if (s->g.scene != MU_SCENE_CHARACTER && s->charsel)
        close_charsel(s);
    if (s->g.scene != MU_SCENE_LOGIN)
        server_hide(s);
    mu_scenemgr_dispatch(&s->host, &s->g, 0x0d0c0001u);
    log_transition(s, s->g.scene == MU_SCENE_LOGIN ? "title done" : s->g.scene == MU_SCENE_MAIN ? "loading done"
                                                                                                 : "dispatcher");
    if (s->g.scene == MU_SCENE_MAIN && !s->world) {
        /* the join-map answer and main-scene data load while the loading frame is shown */
        if (open_world(s)) {
            mu_scenemgr_return_to_character(&s->g);
            s->g.protocol = mu_offline_session_character_list(&s->session);
            log_transition(s, "world did not load: back to character select");
        }
    }
    s->key_count = 0;
    s->button_down = s->button_up = 0;
}

int mu_shell_view(const mu_shell *s)
{
    if (s->g.scene == MU_SCENE_CHARACTER && s->charsel)
        return MU_SHELL_VIEW_CHARSEL;
    if (s->g.scene == MU_SCENE_MAIN && s->world)
        return MU_SHELL_VIEW_WORLD;
    if (s->g.scene == MU_SCENE_LOGIN && s->login)
        return MU_SHELL_VIEW_LOGIN;
    return MU_SHELL_VIEW_2D;
}

mu_login_session *mu_shell_login(mu_shell *s)
{
    return s->login;
}

struct mu_charsel_list_gfx *mu_shell_charsel_gfx(mu_shell *s) { return s->charsel_gfx; }

void mu_shell_charsel_counts(const mu_shell *s, long out[6])
{
    long v[6] = {s->picks, s->pick_hits, s->double_clicks, s->gfx_callbacks, s->gfx_enters, s->gfx_creates};
    if (s->charsel) {
        const mu_charsel_session *cs = mu_charsel_embed_session(s->charsel);
        v[0] += cs->picks;
        v[1] += cs->pick_hits;
        v[2] += cs->double_clicks;
    }
    if (s->charsel_gfx) {
        mu_charsel_list_gfx_stats st;
        mu_charsel_list_gfx_stats_get(s->charsel_gfx, &st);
        v[3] += st.callbacks;
        v[4] += st.enters;
        v[5] += st.create_requests;
    }
    memcpy(out, v, sizeof v);
}

void mu_shell_charsel_create_stats(const mu_shell *s, mu_charsel_create_stats *out, long *rebuilds)
{
    mu_charsel_list_gfx_create_stats(s->charsel_gfx, out);
    const mu_charsel_create_stats *t = &s->create_total;   /* closed visits too */
    out->creates += t->creates;
    out->created += t->created;
    out->refused += t->refused;
    out->deletes += t->deletes;
    out->deleted += t->deleted;
    out->messages += t->messages;
    out->menu_events += t->menu_events;
    out->preview_frames += t->preview_frames;
    if (!out->last_message[0])
        snprintf(out->last_message, sizeof out->last_message, "%s", t->last_message);
    if (rebuilds)
        *rebuilds = s->charsel_rebuilds;
}

int mu_shell_charsel_control(mu_shell *s, const char *name, int32_t *x, int32_t *y)
{
    static const char *const BUTTONS[4] = {"create", "menu", "connect", "delete"};   /* CCharSelMainWin +0x190 */
    for (int i = 0; i < 4; ++i)
        if (!strcmp(name, BUTTONS[i])) {
            if (!s->charsel_ui)
                return 0;
            const mu_ui_button *b = &s->charsel_ui->win.buttons[i];
            *x = mu_ui_sprite_x(&b->sprite) + mu_ui_sprite_width(&b->sprite) / 2;
            *y = mu_ui_sprite_y(&b->sprite) + mu_ui_sprite_height(&b->sprite) / 2;
            return 1;
        }
    double fx, fy;
    if (!s->charsel_gfx || !mu_charsel_list_gfx_control(s->charsel_gfx, name, &fx, &fy))
        return 0;
    *x = (int32_t)fx;
    *y = (int32_t)fy;
    return 1;
}

int mu_shell_charsel_row(mu_shell *s, int32_t row, int32_t *x, int32_t *y)
{
    double fx, fy;
    if (!s->charsel_gfx || !mu_charsel_list_gfx_row_center(s->charsel_gfx, row, &fx, &fy))
        return 0;
    *x = (int32_t)fx;
    *y = (int32_t)fy;
    return 1;
}

mu_charsel_embed *mu_shell_charsel(mu_shell *s)
{
    return s->charsel;
}

mu_world_embed *mu_shell_world(mu_shell *s)
{
    return s->world;
}

static void login_panel(mu_shell *s)
{
    ensure_font_texture(s);
    mu_ui_enable_alpha_blend(&s->state);
    mu_ui_render_color(&s->state, 200.0f, 180.0f, 240.0f, 110.0f, 0.75f, 1);
    mu_ui_end_render_color(&s->state);
    char account[16], password[16];
    memset(account, '*', sizeof account);
    memset(password, '*', sizeof password);
    account[s->typed[0]] = 0;
    password[s->typed[1]] = 0;
    char line[96];
    mu_ui_text_set_back_color(&s->text, 0, 0, 0, 0);
    mu_ui_ctx_set_font(&s->ctx, s->ctx.fonts.bold);
    mu_ui_text_set_color(&s->text, 255, 210, 60, 255);
    mu_ui_render_text(&s->state, &s->text, 320, 188, "OFFLINE DEMO LOGIN", 0, 0, 8, NULL);
    mu_ui_ctx_set_font(&s->ctx, s->ctx.fonts.normal);
    const mu_ui_server_list *l = &s->session.servers;
    const mu_ui_server_group *g = s->session.server_group >= 0 && s->session.server_group < l->group_count
                                      ? &l->groups[s->session.server_group] : NULL;
    snprintf(line, sizeof line, "Server: %s", g && s->session.server_slot >= 0 && s->session.server_slot < g->server_count
                                                  ? g->servers[s->session.server_slot].name : "-");
    mu_ui_text_set_color(&s->text, 230, 230, 230, 255);
    mu_ui_render_text(&s->state, &s->text, 215, 206, line, 0, 0, 1, NULL);
    snprintf(line, sizeof line, "%s Account:  %s_", s->field == 0 ? ">" : " ", account);
    mu_ui_render_text(&s->state, &s->text, 215, 224, line, 0, 0, 1, NULL);
    snprintf(line, sizeof line, "%s Password: %s_", s->field == 1 ? ">" : " ", password);
    mu_ui_render_text(&s->state, &s->text, 215, 240, line, 0, 0, 1, NULL);
    mu_ui_text_set_color(&s->text, 180, 180, 180, 255);
    mu_ui_render_text(&s->state, &s->text, 215, 260, "Any input is accepted; nothing is sent or stored.", 0, 0, 1, NULL);
    mu_ui_render_text(&s->state, &s->text, 215, 274, "Enter: log in   Tab: next field   Esc: servers", 0, 0, 1, NULL);
}

void mu_shell_overlay(mu_shell *s, uint8_t *rgba)
{
    switch (s->g.scene) {
    case MU_SCENE_LOGIN: {
        copy_in(s, rgba);
        mu_ui_begin_bitmap(&s->state);
        mu_ui_login_text strings;
        memset(&strings, 0, sizeof strings);
        strings.text454 = mu_lang_text_or(mu_lang_shared(), 454, TEXT_454);
        strings.text455 = mu_lang_text_or(mu_lang_shared(), 455, TEXT_455);
        strings.format456 = "Ver %s";   /* GlobalText[456] is a format: kept fixed in the shell */
        for (int i = 0; i < 5; ++i)
            strings.version_bytes[i] = (uint8_t)("10000"[i] + i + 1);
        ensure_font_texture(s);
        mu_ui_ctx_set_font(&s->ctx, s->ctx.fonts.normal);
        mu_ui_login_overlay(&s->state, &s->text, &s->g.login_fade, 640, &strings);   /* 0x01858108.. */
        if (s->server_shown)
            s->server->win.cls->render(&s->ctx, &s->server->win);   /* CUIMng::Render */
        if (s->panel)
            login_panel(s);
        offline_label(s, s->panel ? "login: any input is accepted" : "server select: click a server or press Enter");
        mu_ui_end_bitmap(&s->state);
        mu_ui_raster_read_top_down(&s->raster, rgba);
        break;
    }
    case MU_SCENE_CHARACTER:
        if (s->charsel_ui)
            mu_charsel_ui_render(s->charsel_ui, rgba);
        copy_in(s, rgba);
        mu_ui_begin_bitmap(&s->state);
        if (s->charsel_gfx) {
            mu_charsel_list_gfx_composite(s->charsel_gfx, rgba, s->cfg.width, s->cfg.height);
            mu_charsel_list_gfx_stats st;
            mu_charsel_list_gfx_stats_get(s->charsel_gfx, &st);
            copy_in(s, rgba);
            mu_ui_begin_bitmap(&s->state);
            offline_label(s, st.status[0] ? st.status
                                          : "character select: click a character in the list, double-click or "
                                            "Enter plays, Create / Delete (local store), Esc: the menu");
            mu_ui_end_bitmap(&s->state);
            mu_ui_raster_read_top_down(&s->raster, rgba);
            break;
        }
        offline_label(s, "character select: Enter plays, Left/Right or 1-5 choose, Esc returns to the servers");
        mu_ui_end_bitmap(&s->state);
        mu_ui_raster_read_top_down(&s->raster, rgba);
        break;
    case MU_SCENE_MAIN:
        copy_in(s, rgba);
        mu_ui_begin_bitmap(&s->state);
        offline_label(s, "world: click to walk, wheel zooms, Esc returns to character select");
        mu_ui_end_bitmap(&s->state);
        mu_ui_raster_read_top_down(&s->raster, rgba);
        break;
    default:
        break;
    }
}

int32_t mu_shell_end_frame(mu_shell *s, uint32_t now)
{
    int32_t sleep;
    if (s->g.scene == MU_SCENE_CHARACTER && s->charsel)
        sleep = mu_charsel_end_render(mu_charsel_embed_session(s->charsel));
    else if (s->g.scene == MU_SCENE_MAIN && s->world)
        sleep = mu_world_embed_end_frame(s->world);
    else {
        uint32_t elapsed = now - s->frame_start;
        sleep = elapsed < 40 ? (int32_t)(40 - elapsed) : 0;   /* Sleep(40 - elapsed), 0x0185267a */
    }
    mu_scenemgr_frame_music(&s->host, &s->g);   /* 0x0185276c: login theme in scenes 3 and 5 */
    if (s->audio)
        mu_audio_host_tick(s->audio);
    return sleep;
}

uint32_t mu_shell_audio_rate(const mu_shell *s)
{
    if (s->audio)
        return mu_audio_engine_rate(mu_audio_host_engine(s->audio));
    return 44100;
}

void mu_shell_mix(mu_shell *s, float *out, uint32_t frames)
{
    memset(out, 0, (size_t)frames * 2 * sizeof *out);
    if (s->audio)
        mu_audio_engine_mix(mu_audio_host_engine(s->audio), out, frames);
    if (s->g.scene == MU_SCENE_MAIN && s->world && mu_world_embed_has_sound(s->world) &&
        mu_world_embed_sound_rate(s->world) == mu_shell_audio_rate(s)) {
        static float world[2 * 4096];
        for (uint32_t done = 0; done < frames;) {
            uint32_t n = frames - done > 4096 ? 4096 : frames - done;
            mu_world_embed_mix(s->world, world, n);
            for (uint32_t i = 0; i < 2 * n; ++i)
                out[2 * done + i] += world[i];
            done += n;
        }
    }
}

int mu_shell_scene(const mu_shell *s)
{
    return s->g.scene;
}

int mu_shell_quit(const mu_shell *s)
{
    return s->quit;
}

void mu_shell_request_quit(mu_shell *s)
{
    s->quit = 1;
}

const mu_scenemgr_globals *mu_shell_globals(const mu_shell *s)
{
    return &s->g;
}

const mu_offline_session *mu_shell_session(const mu_shell *s)
{
    return &s->session;
}

int32_t mu_shell_hero_slot(const mu_shell *s)
{
    return s->hero_slot;
}

uint8_t mu_shell_hero_class(const mu_shell *s)
{
    return s->hero_class;
}

static int sprite_centre(const mu_ui_sprite *b, int32_t *x, int32_t *y)
{
    *x = mu_ui_sprite_x(b) + mu_ui_sprite_width(b) / 2;
    *y = mu_ui_sprite_y(b) + mu_ui_sprite_height(b) / 2;
    return 1;
}

int mu_shell_server_group_button(const mu_shell *s, int32_t index, int32_t *x, int32_t *y)
{
    if (!s->server_shown)
        return 0;
    const mu_ui_server_list *l = &s->session.servers;
    if (index < 0 || index >= l->group_count || l->groups[index].button < 0 ||
        l->groups[index].button >= MU_UI_SSW_GROUPS)
        return 0;
    return sprite_centre(&s->server->groups[l->groups[index].button].sprite, x, y);
}

int mu_shell_server_button(const mu_shell *s, int32_t index, int32_t *x, int32_t *y)
{
    if (!s->server_shown || index < 0 || index >= s->server->server_count || index >= MU_UI_SSW_SERVERS)
        return 0;
    return sprite_centre(&s->server->servers[index].sprite, x, y);
}

int mu_shell_login_panel(const mu_shell *s)
{
    return s->panel;
}

int32_t mu_shell_transitions(const mu_shell *s, const char *const **lines)
{
    *lines = s->transition_lines;
    return s->transition_count;
}

const char *mu_shell_status(const mu_shell *s)
{
    return s->status;
}
