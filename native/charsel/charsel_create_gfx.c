/* The character select's create panel, delete flow, message boxes and system menu (NATIVE-CHARCREATE-001);
 * see charsel_create_gfx.h. */
#define _POSIX_C_SOURCE 200809L
#include "charsel_create_gfx.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "../../reconstructed/camera/client_camera.h"
#include "../core/mu_bmd.h"
#include "../core/mu_model.h"
#include "../core/mu_raster.h"
#include "../core/mu_scene.h"
#include "../core/mu_textures.h"

#define CAUTION_PATH "_level0.g_mcCaution"
#define MENU_PATH "_level0.mcSystemMenu"
#define LIST_WINDOW "_level0.g_mcCharacterSelect"
#define QUEUE 8
#define WORDS_MAX 256

typedef struct message {
    char owner;                /* 'w' the CharacterSelect window, '0' none, 'x' the exit countdown */
    int32_t id, ui_type, length;
    char text[1024], title[256];
} message;

typedef struct movie {
    MuGfx *m;
    uint8_t *pixels;
    int have, dirty;
} movie;

struct mu_charsel_create {
    mu_charsel_mugfx a;        /* a copy of the list's function table (the library stays loaded by the list) */
    mu_charsel_create_config cfg;
    mu_csg_window *list;
    mu_csg_env gfx, menu_gfx;  /* the list's environment; the menu's (its invokes go to winSystemMenu) */
    mu_ccr_window w;
    mu_ccr_env e;
    uint8_t preview[MU_CHARSEL_RECORD];
    int32_t protocol;
    uint8_t init_scene;
    float fov;
    /* name tables */
    char *filter_words[WORDS_MAX], *filter_name_words[WORDS_MAX];
    /* the stashed callback arguments (client bytes) */
    char name[64], input[64];
    /* the preview model */
    int32_t preview_model;     /* 0x135 + class, -1 none */
    mu_bmd bmd;
    mu_model model;
    mu_textures textures;
    int model_loaded;
    mu_raster raster;
    int32_t raster_w, raster_h;
    /* pending offline answers */
    int create_pending, delete_pending;
    char pending_name[MU_CCR_NAME_MAX + 1];
    uint8_t pending_class;
    double countdown_ms;       /* the exit countdown (0 none) */
    /* Caution */
    movie caution;
    message queue[QUEUE];
    int32_t queue_count;
    message current;
    int caution_open;
    /* winSystemMenu */
    movie menu;
    int menu_loaded;
    uint8_t legacy_hidden;
    mu_charsel_create_stats stats;
};

/* ------------------------------------------------------------------ small helpers */

static const char *gt(mu_charsel_create *c, int32_t index)
{
    const char *s = c->cfg.text ? c->cfg.text(c->cfg.text_user, index) : NULL;
    static char buf[32];
    if (s && *s)
        return s;
    snprintf(buf, sizeof buf, "GT%d", index);
    return buf;
}

static void status(mu_charsel_create *c, const char *text)
{
    snprintf(c->stats.status, sizeof c->stats.status, "%s", text);
}

/* a JSON string at *p ('"' first) into out (bytes; \uXXXX below 0x100 as one byte); returns the end */
static const char *json_string(const char *p, char *out, size_t cap)
{
    size_t n = 0;
    if (*p != '"') {
        if (cap)
            out[0] = 0;
        return p;
    }
    for (++p; *p && *p != '"'; ++p) {
        char ch = *p;
        if (ch == '\\' && p[1]) {
            ++p;
            switch (*p) {
            case 'n': ch = '\n'; break;
            case 't': ch = '\t'; break;
            case 'r': ch = '\r'; break;
            case 'b': ch = '\b'; break;
            case 'f': ch = '\f'; break;
            case 'u': {
                unsigned v = 0;
                for (int k = 1; k <= 4 && p[k]; ++k) {
                    char h = p[k];
                    v = v * 16u + (unsigned)(h >= 'a' ? h - 'a' + 10 : h >= 'A' ? h - 'A' + 10 : h - '0');
                }
                p += 4;
                ch = (char)(v < 0x100 ? v : '?');
                break;
            }
            default: ch = *p; break;
            }
        }
        if (n + 1 < cap)
            out[n++] = ch;
    }
    if (cap)
        out[n] = 0;
    return *p ? p + 1 : p;
}

static const char *skip_space(const char *p)
{
    while (*p == ' ')
        ++p;
    return p;
}

/* UTF-8 from the movie -> the client's single-byte code page (Windows ANSI on the English setup the native
 * port assumes): ASCII stays, Latin-1 code points become their byte, anything else '?'. */
static void to_client_bytes(const char *utf8, char *out, size_t cap)
{
    size_t n = 0;
    const unsigned char *p = (const unsigned char *)utf8;
    while (*p && n + 1 < cap) {
        unsigned cp;
        int len;
        if (*p < 0x80) { cp = *p; len = 1; }
        else if ((*p & 0xe0) == 0xc0 && p[1]) { cp = (unsigned)(*p & 0x1f) << 6 | (p[1] & 0x3fu); len = 2; }
        else if ((*p & 0xf0) == 0xe0 && p[1] && p[2]) { cp = 0xfffd; len = 3; }
        else if ((*p & 0xf8) == 0xf0 && p[1] && p[2] && p[3]) { cp = 0xfffd; len = 4; }
        else { cp = 0xfffd; len = 1; }
        out[n++] = (char)(cp < 0x100 ? cp : '?');
        p += len;
    }
    out[n] = 0;
}

/* client bytes -> UTF-8 for the movies (Latin-1 bytes as their code point) */
static void to_utf8(const char *bytes, char *out, size_t cap)
{
    size_t n = 0;
    for (const unsigned char *p = (const unsigned char *)bytes; *p && n + 3 < cap; ++p) {
        if (*p < 0x80) {
            out[n++] = (char)*p;
        } else {
            out[n++] = (char)(0xc0 | (*p >> 6));
            out[n++] = (char)(0x80 | (*p & 0x3f));
        }
    }
    out[n] = 0;
}

static void json_escape(const char *utf8, char *out, size_t cap)
{
    size_t n = 0;
    if (cap < 3)
        return;
    out[n++] = '"';
    for (const unsigned char *p = (const unsigned char *)utf8; *p && n + 8 < cap; ++p) {
        if (*p == '"' || *p == '\\') {
            out[n++] = '\\';
            out[n++] = (char)*p;
        } else if (*p == '\n') {
            out[n++] = '\\';
            out[n++] = 'n';
        } else if (*p < 0x20) {
            n += (size_t)snprintf(out + n, cap - n, "\\u%04x", *p);
        } else {
            out[n++] = (char)*p;
        }
    }
    out[n++] = '"';
    out[n] = 0;
}

static char *unescape_word(const char *s)
{
    size_t n = strlen(s);
    char *out = malloc(n + 1), *o = out;
    if (!out)
        return NULL;
    for (; *s; ++s) {
        if (*s == '\\' && s[1]) {
            ++s;
            if (*s == 'x' && s[1] && s[2]) {
                char hex[3] = {s[1], s[2], 0};
                *o++ = (char)strtol(hex, NULL, 16);
                s += 2;
            } else {
                *o++ = *s == 't' ? '\t' : *s == 'n' ? '\n' : *s == 'r' ? '\r' : *s;
            }
        } else {
            *o++ = *s;
        }
    }
    *o = 0;
    return out;
}

/* filter.txt / filtername.txt (scripts/live_lang_filters.py): one escaped word per line */
static int32_t load_words(const char *dir, const char *file, char **out)
{
    if (!dir)
        return 0;
    char path[2048];
    snprintf(path, sizeof path, "%s/%s", dir, file);
    FILE *f = fopen(path, "rb");
    if (!f)
        return 0;
    char line[1024];
    int32_t n = 0;
    while (n < WORDS_MAX && fgets(line, sizeof line, f)) {
        size_t len = strlen(line);
        while (len && (line[len - 1] == '\n' || line[len - 1] == '\r'))
            line[--len] = 0;
        out[n] = unescape_word(line);
        if (out[n])
            ++n;
    }
    fclose(f);
    return n;
}

/* ------------------------------------------------------------------ movies */

static const char *caution_call(void *user, const char *name, const char *args);
static const char *menu_call(void *user, const char *name, const char *args);

static int movie_open(mu_charsel_create *c, movie *mv, const char *file, mugfx_callback cb, char *error, size_t cap)
{
    char path[4096];
    snprintf(path, sizeof path, "%s/%s", c->cfg.movie_dir, file);
    if (access(path, R_OK) != 0) {
        snprintf(error, cap, "%s missing (convert it with native/gfx/gfxconvert.py --bridge)", path);
        return -1;
    }
    const double scale = c->cfg.scale > 0 ? c->cfg.scale : 1.0;
    const int sw = (int)lround(c->cfg.width / scale), sh = (int)lround(c->cfg.height / scale);
    mv->m = c->a.open(path, sw, sh, error, cap);
    if (!mv->m)
        return -1;
    c->a.set_view(mv->m, sw, sh, 0, 0, sw, sh, scale);
    mv->pixels = malloc((size_t)c->cfg.width * (size_t)c->cfg.height * 4);
    c->a.set_callback(mv->m, cb, c);
    c->a.start(mv->m);
    c->a.advance(mv->m, 0.0);
    return 0;
}

static void movie_close(mu_charsel_create *c, movie *mv)
{
    if (mv->m)
        c->a.close(mv->m);
    free(mv->pixels);
    memset(mv, 0, sizeof *mv);
}

static void movie_composite(mu_charsel_create *c, movie *mv, uint8_t *rgba, int32_t width, int32_t height)
{
    if (!mv->m || !mv->pixels || width != c->cfg.width || height != c->cfg.height)
        return;
    if (!mv->have || c->a.needs_render(mv->m)) {
        if (c->a.render(mv->m, mv->pixels, (size_t)width * (size_t)height * 4) == 0)
            mv->have = 1;
    }
    if (!mv->have)
        return;
    const size_t n = (size_t)width * (size_t)height;
    for (size_t i = 0; i < n; ++i) {
        const uint8_t *s = mv->pixels + 4 * i;
        uint8_t *d = rgba + 4 * i;
        const unsigned al = s[3];
        if (!al)
            continue;
        for (int k = 0; k < 3; ++k)
            d[k] = (uint8_t)((s[k] * al + d[k] * (255u - al) + 127u) / 255u);
    }
}

static void invoke(mu_charsel_create *c, MuGfx *m, const char *path, const char *method, const char *args)
{
    if (m)
        c->a.invoke(m, path, method, args);
}

/* ------------------------------------------------------------------ Caution (static reading of 0x00b390a9) */

static void caution_show_next(mu_charsel_create *c)
{
    if (c->caution_open || !c->queue_count)
        return;
    c->current = c->queue[0];
    memmove(c->queue, c->queue + 1, (size_t)(c->queue_count - 1) * sizeof c->queue[0]);
    --c->queue_count;
    c->caution_open = 1;
    snprintf(c->stats.last_message, sizeof c->stats.last_message, "%s", c->current.text);
    ++c->stats.messages;
    if (!c->caution.m)
        return;
    /* SetUIType("%d %s %s %d": type, title, text, text type), SetDisableOkBtn(0), InitCaution(OK GT 0xe4, Cancel
     * GT 0xe5), for the input types SetInputBoxLength and SetInputFocus */
    char title[600], text[2400], args[3200], ok[256], cancel[256], u[1200];
    to_utf8(c->current.title, u, sizeof u);
    json_escape(u, title, sizeof title);
    to_utf8(c->current.text, u, sizeof u);
    json_escape(u, text, sizeof text);
    invoke(c, c->caution.m, CAUTION_PATH, "SetVisible", "[true]");
    snprintf(args, sizeof args, "[%d,%s,%s,0]", c->current.ui_type, title, text);
    invoke(c, c->caution.m, CAUTION_PATH, "SetUIType", args);
    invoke(c, c->caution.m, CAUTION_PATH, "SetDisableOkBtn", "[0]");
    to_utf8(gt(c, 0xe4), u, sizeof u);
    json_escape(u, ok, sizeof ok);
    to_utf8(gt(c, 0xe5), u, sizeof u);
    json_escape(u, cancel, sizeof cancel);
    snprintf(args, sizeof args, "[%s,%s]", ok, cancel);
    invoke(c, c->caution.m, CAUTION_PATH, "InitCaution", args);
    if (c->current.ui_type == 3 || c->current.ui_type == 4) {
        snprintf(args, sizeof args, "[%d]", c->current.length);
        invoke(c, c->caution.m, CAUTION_PATH, "SetInputBoxLength", args);
        invoke(c, c->caution.m, CAUTION_PATH, "SetInputFocus", "[\"\"]");
    }
    c->caution.dirty = 1;
}

static void caution_hide(mu_charsel_create *c)
{
    c->caution_open = 0;
    invoke(c, c->caution.m, CAUTION_PATH, "SetVisible", "[false]");
}

static void enqueue(mu_charsel_create *c, char owner, int32_t id, int32_t ui_type, int32_t length, const char *text,
                    const char *title)
{
    if (c->queue_count >= QUEUE)
        return;
    message *m = &c->queue[c->queue_count++];
    memset(m, 0, sizeof *m);
    m->owner = owner;
    m->id = id;
    m->ui_type = ui_type;
    m->length = length;
    snprintf(m->text, sizeof m->text, "%s", text ? text : "");
    snprintf(m->title, sizeof m->title, "%s", title ? title : "");
    caution_show_next(c);
}

/* OnClickBtnOK / OnClickBtnCancel -> the window's button handler 0x00b39912 -> the owner's result
 * (CharacterSelect: 0x00b49967) (static reading) */
static void caution_answer(mu_charsel_create *c, int32_t button, const char *utf8)
{
    if (!c->caution_open)
        return;
    message m = c->current;
    char text[256] = "";
    if (utf8)
        to_client_bytes(utf8, text, sizeof text);
    caution_hide(c);
    if (m.owner == 'w')
        mu_ccr_message_result(c->list, &c->w, &c->e, m.id, button, text);
    memset(text, 0, sizeof text);   /* the password box's text is not kept */
    caution_show_next(c);
}

static const char *caution_call(void *user, const char *name, const char *args)
{
    mu_charsel_create *c = user;
    c->caution.dirty = 1;
    if (!strcmp(name, "OnClickBtnOK")) {
        char text[256] = "";
        const char *p = strchr(args, '"');
        if (p)
            json_string(p, text, sizeof text);
        caution_answer(c, 0, text);
        memset(text, 0, sizeof text);
    } else if (!strcmp(name, "OnClickBtnCancel")) {
        caution_answer(c, 1, NULL);
    }
    /* onClickCautionInputCancel / onClickInputPassWord (a mouse release outside / inside the input box) only move
     * the IME focus in the client (0x00b3aadd: 0x009a595b()->0x010afc0a(0), static): not answers */
    return NULL;
}

/* ------------------------------------------------------------------ winSystemMenu */

/* the menu window's invokes go to its movie, the rest (the list's show) to CharacterSelect */
static void menu_emit(void *user, const char *line)
{
    mu_charsel_create *c = user;
    if (!strncmp(line, "invoke ", 7)) {
        char method[64];
        const char *rest = line + 7, *space = strchr(rest, ' ');
        size_t n = space ? (size_t)(space - rest) : strlen(rest);
        snprintf(method, sizeof method, "%.*s", (int)n, rest);
        if (!strcmp(method, "InitText") || !strcmp(method, "SceneChange") || !strcmp(method, "openWindow") ||
            !strcmp(method, "closeWindow")) {
            invoke(c, c->menu.m, MENU_PATH, method, space ? space + 1 : "[]");
            if (c->gfx.emit) {   /* the list's log keeps the menu's invokes too */
                char logged[1100];
                snprintf(logged, sizeof logged, "menu %s", line);
                c->gfx.emit(c->gfx.context, logged);
            }
            c->menu.dirty = 1;
            return;
        }
    }
    if (!strncmp(line, "call 00000010 4bb0 ", 19)) {   /* CCharSelMainWin vtable +0x10 (shown with the list) */
        c->legacy_hidden = line[19] == '0';
        return;
    }
    if (!strncmp(line, "call 009a5ab2 ", 14)) {
        int kind = atoi(line + 14);
        if (kind == 0)
            return;   /* the exit: after the countdown box */
        if (c->cfg.hooks.menu)
            c->cfg.hooks.menu(c->cfg.hooks.user, kind);
        return;
    }
    if (!strncmp(line, "call 00b39b2f ", 14)) {   /* the countdown box (0, 0x76, text, "", 5 s) */
        const char *p = strchr(line + 14, '"');
        char text[512] = "";
        if (p)
            json_string(p, text, sizeof text);
        enqueue(c, 'x', 0x76, 2, 0, text, "");
        c->countdown_ms = 5000.0;
        return;
    }
    if (!strcmp(line, "call 00be7079")) {
        status(c, "OFFLINE DEMO: the option window is not played");
        if (c->cfg.hooks.menu)
            c->cfg.hooks.menu(c->cfg.hooks.user, 3);
        return;
    }
    if (c->gfx.emit)
        c->gfx.emit(c->gfx.context, line);
}

static uint8_t *menu_character(void *user, int32_t index)
{
    mu_charsel_create *c = user;
    return c->gfx.character ? c->gfx.character(c->gfx.context, index) : NULL;
}

static const char *menu_text(void *user, int32_t index)
{
    mu_charsel_create *c = user;
    return c->gfx.global_text ? c->gfx.global_text(c->gfx.context, index) : "";
}

static const char *menu_class(void *user, int32_t class_byte)
{
    mu_charsel_create *c = user;
    return c->gfx.class_name ? c->gfx.class_name(c->gfx.context, class_byte) : "";
}

static const char *menu_call(void *user, const char *name, const char *args)
{
    mu_charsel_create *c = user;
    c->menu.dirty = 1;
    if (strcmp(name, "winSystemMenu"))
        return NULL;
    char event[64] = "";
    const char *p = strchr(args, '"');
    if (p)
        json_string(p, event, sizeof event);
    if (!strcmp(event, "onOpenWindow")) {
        const char *v = strstr(args, ",");
        c->e.menu_open = v && strstr(v, "true") ? 1 : 0;   /* the KeyWindow's open flag (+0x1c) */
        return NULL;
    }
    ++c->stats.menu_events;
    c->e.gfx = &c->menu_gfx;   /* the menu window's environment while its code runs */
    mu_csm_event(c->list, &c->e, event);
    c->e.gfx = &c->gfx;
    return NULL;
}

static void menu_load(mu_charsel_create *c)
{
    if (!c->menu.m || c->menu_loaded)
        return;
    /* the window loader attaches the window's class symbol and calls onFileLoad (KeyWindow -> "onLoad") */
    /* the movie's own timeline instance of the window (Ruffle names it instance1) stays hidden: the client's
     * loader shows only the window it attaches */
    c->a.set_variable(c->menu.m, "_level0.instance1._visible", "false");
    invoke(c, c->menu.m, "_level0", "attachMovie", "[\"SystemMenu\",\"mcSystemMenu\",100]");
    c->menu_loaded = 1;   /* onFileLoad follows once the clip's first frame ran (MovieClipLoader.onLoadInit) */
}

/* ------------------------------------------------------------------ the preview */

static void preview_free(mu_charsel_create *c)
{
    if (c->model_loaded) {
        mu_model_free(&c->model);
        mu_textures_free(&c->textures);
        mu_bmd_free(&c->bmd);
        c->model_loaded = 0;
    }
}

static void preview_load(mu_charsel_create *c, int32_t model)
{
    if (model == c->preview_model && c->model_loaded)
        return;
    preview_free(c);
    c->preview_model = model;
    c->stats.preview_class = model - MU_CCR_PREVIEW_MODEL;
    if (!c->cfg.game_root || model < MU_CCR_PREVIEW_MODEL || model >= MU_CCR_PREVIEW_MODEL + MU_CCR_CLASSES)
        return;
    char path[4096], dir[4096], error[256];
    snprintf(dir, sizeof dir, "%s/Data/Logo", c->cfg.game_root);
    snprintf(path, sizeof path, "%s/NewFace%02d.bmd", dir, model - MU_CCR_PREVIEW_MODEL + 1);   /* 0x0182a74d */
    if (mu_bmd_load_file(path, &c->bmd, error, sizeof error) != MU_BMD_OK)
        return;
    mu_model_params p;
    mu_model_scene_params(&p);
    if (mu_model_init(&c->model, &c->bmd, &p, error, sizeof error) != MU_MODEL_OK) {
        mu_bmd_free(&c->bmd);
        return;
    }
    mu_textures_load(&c->textures, &c->bmd, dir);
    c->model_loaded = 1;
    mu_model_set_state(&c->model, 0, 0.0f, 0.0f, 0);
}

/* SetAction 0x012affa4: a new action restarts at frame 0, the current one becomes the prior */
static void preview_action(mu_charsel_create *c, uint16_t action)
{
    if (!c->model_loaded || action >= c->bmd.action_count || action == mu_model_action(&c->model))
        return;
    mu_model_set_state(&c->model, action, 0.0f, mu_model_frame(&c->model), mu_model_action(&c->model));
}

/* the animation step 0x013960d2 for models 0x135..0x144: PlaySpeed 0.3 for actions 0 and 1 (0.25 for model
 * 0x13a action 0, OpenCharacterSceneData 0x0182a809, static) times the per-model factor (verified,
 * reconstructed/actors: x1.5 for 0x13f and 0x142, x2 for 0x143, x1/x1.5 for 0x144, else x2) */
static float preview_speed(const mu_charsel_create *c)
{
    uint16_t action = mu_model_action(&c->model);
    float speed = c->preview_model == 0x13a && action == 0 ? 0.25f : 0.3f;
    switch (c->preview_model - 0x135) {
    case 0xa:
    case 0xd: return speed * 1.5f;
    case 0xe: return speed * 2.0f;
    case 0xf: return action == 0 ? speed : speed * 1.5f;
    default: return speed * 2.0f;
    }
}

static void render_emit(void *user, const char *line)
{
    mu_charsel_create *c = user;
    int action = 0;
    if (sscanf(line, "call 012affa4 p+0x3254 %d", &action) == 1)
        preview_action(c, (uint16_t)action);
}

void mu_charsel_create_draw_preview(mu_charsel_create *c, uint8_t *rgba, int32_t width, int32_t height)
{
    if (!c)
        return;
    /* the window's render hook 0x00b49cd7 -> 0x00b4a14c (calls logged by the reconstruction) */
    c->e.animation_running = 1;
    uint8_t loop = 1;
    if (c->model_loaded && c->w.create_open)
        mu_model_tick(&c->model, preview_speed(c), &loop);
    c->e.animation_running = loop;
    /* the hook's per-frame call log stays out of the GFx log: only SetAction(0) is acted on */
    mu_csg_env quiet = c->gfx;
    quiet.context = c;
    quiet.emit = render_emit;
    c->e.gfx = &quiet;
    mu_ccr_render_hook(&c->w, &c->e);
    c->e.gfx = &c->gfx;
    if (!c->w.create_open || !c->model_loaded)
        return;
    const int32_t x0 = c->w.board[0], y0 = c->w.board[1], bw = c->w.board[2], bh = c->w.board[3];
    if (bw <= 0 || bh <= 0 || bw > 4096 || bh > 4096)
        return;
    if (bw != c->raster_w || bh != c->raster_h) {
        mu_raster_free(&c->raster);
        if (mu_raster_init(&c->raster, bw, bh))
            return;
        c->raster_w = bw;
        c->raster_h = bh;
    }
    /* the pose: the class's angle and scale on the object (0x00b4a4a1), its light (1, 1, 1) */
    const uint8_t *o = c->preview + MU_CHARSEL_OBJECT;
    mu_model_params p = c->model.params;
    memcpy(&p.body_scale, o + MU_OBJ_SCALE, 4);
    memcpy(p.angles, o + MU_OBJ_ANGLE, 12);
    for (int k = 0; k < 3; ++k) {
        p.origin[k] = 0.0f;
        p.color[k] = 1.0f;
    }
    mu_model_apply_params(&c->model, &p);
    if (mu_model_update(&c->model) != MU_MODEL_OK)
        return;
    /* BeginOpengl2 0x0184b27e(x, y, w, h): glViewport2 in window pixels, gluPerspective2(FOV, w/h, near, far
     * x1.4), the camera rotations and translation; the camera from 0x01854879 (yaw 0: position = object +
     * offset, angle (-90, 0, 0)) */
    mu_client_view v;
    memset(&v, 0, sizeof v);
    v.window_width = (uint32_t)width;
    v.window_height = (uint32_t)height;
    v.fov = *c->e.camera_fov;
    v.view_near = 20.0f;
    v.view_far = 2400.0f;
    v.angle[0] = -90.0f;
    for (int k = 0; k < 3; ++k)
        v.position[k] = (k == 0 ? 5.0f : k == 1 ? -500.0f : 46.0f) - c->w.camera_offset[k];
    mu_view_begin_opengl(&v, 0, 0, 640, 480);   /* the modelview (the projection is replaced below) */
    memset(v.projection, 0, sizeof v.projection);   /* glMatrixMode(GL_PROJECTION), glLoadIdentity */
    v.projection[0] = v.projection[5] = v.projection[10] = v.projection[15] = 1.0f;
    mu_view_perspective2(&v, v.fov, (float)bw / (float)bh, v.view_near, v.view_far * 1.4f);
    /* the viewport draws into the frame as it is (GL blends against the framebuffer): the board rectangle of
     * the frame is the raster's starting colour, the depth is cleared */
    const uint8_t clear[4] = {0, 0, 0, 255};
    mu_raster_clear(&c->raster, clear);
    for (int32_t y = 0; y < bh; ++y)
        for (int32_t x = 0; x < bw; ++x) {
            int32_t tx = x0 + x, ty = y0 + y;
            if (tx >= 0 && tx < width && ty >= 0 && ty < height)
                memcpy(c->raster.color + ((size_t)y * (size_t)bw + (size_t)x) * 4,
                       rgba + ((size_t)ty * (size_t)width + (size_t)tx) * 4, 4);
        }
    memcpy(c->raster.view, v.modelview, sizeof c->raster.view);
    memcpy(c->raster.projection, v.projection, sizeof c->raster.projection);
    c->raster.textures = c->textures.slots;
    c->raster.texture_count = c->textures.count;
    c->raster.texture_filter = c->textures.filter;
    c->raster.texture_wrap = c->textures.wrap;
    mu_render_backend backend;
    mu_raster_backend(&c->raster, &backend);
    mu_draw_options options;
    mu_draw_default_options(&options);
    options.textures = &c->textures;
    mu_draw_stats ds = {0, 0, 0, 0};
    mu_scene_draw_model(&c->model, &options, &backend, &ds);
    ++c->stats.preview_frames;
    if (getenv("MU_CHARCREATE_DEBUG"))
        fprintf(stderr, "preview: meshes %ld corners %ld refused %ld triangles %ld fragments %ld scale %g\n",
                ds.meshes, ds.corners, ds.refused, c->raster.triangles, c->raster.fragments, (double)p.body_scale);
    for (int32_t y = 0; y < bh; ++y) {
        int32_t ty = y0 + y;
        if (ty < 0 || ty >= height)
            continue;
        for (int32_t x = 0; x < bw; ++x) {
            int32_t tx = x0 + x;
            if (tx >= 0 && tx < width)
                memcpy(rgba + ((size_t)ty * (size_t)width + (size_t)tx) * 4,
                       c->raster.color + ((size_t)y * (size_t)bw + (size_t)x) * 4, 3);
        }
    }
}

/* ------------------------------------------------------------------ lines */

int mu_charsel_create_line(mu_charsel_create *c, const char *line)
{
    if (!c || strncmp(line, "call ", 5))
        return 0;
    unsigned address = 0;
    int used = 0;
    if (sscanf(line + 5, "%x%n", &address, &used) != 1)
        return 0;
    const char *rest = skip_space(line + 5 + used);
    int a0 = 0, a1 = 0, a2 = 0, a3 = 0;
    switch (address) {
    case 0x00b49bf4:   /* the create panel (the list's empty row, OnClickCreateCharacter, OnClickCreateCancel) */
        mu_ccr_show_create(c->list, &c->w, &c->e, (uint8_t)atoi(rest));
        return 1;
    case 0x009a5920:   /* +0x9c, the rename mode */
        c->w.rename_mode = (uint8_t)atoi(rest);
        return 1;
    case 0x00b4b684:
        mu_ccr_restrict_classes(&c->w, &c->e);
        return 1;
    case 0x00b4a442:
        mu_ccr_set_selected_class(&c->w, &c->e, (uint8_t)atoi(rest));
        return 1;
    case 0x0137d8a1:   /* CreateCharacter(p, model, 0, 0, 0): the preview's model */
        if (sscanf(rest, "p %d", &a0) == 1)
            preview_load(c, a0);
        return 1;
    case 0x012affa4:
        if (sscanf(rest, "p+0x3254 %d", &a0) == 1)
            preview_action(c, (uint16_t)a0);
        return 1;
    case 0x00b4a349:
        if (sscanf(rest, "%d %d %d %d", &a0, &a1, &a2, &a3) == 4) {
            mu_ccr_board_info(&c->w, &c->e, a0, a1, a2, a3);
            memcpy(c->stats.board, c->w.board, sizeof c->stats.board);
        }
        return 1;
    case 0x00b49eca:   /* OnEnterCharacterName(name, class) with the stashed client bytes */
        mu_ccr_enter_name(&c->w, &c->e, c->name, strlen(c->name), atoi(strrchr(rest, ' ') ? strrchr(rest, ' ') : rest));
        return 1;
    case 0x00b4c806:
        mu_ccr_set_target(&c->w, atoi(rest));
        return 1;
    case 0x00b4b31a:
        mu_ccr_update_input(&c->e, c->input);
        return 1;
    case 0x009a466c: { /* the create request: answered by the offline hooks on the next frame */
        char name[64] = "";
        const char *p = json_string(rest, name, sizeof name);
        snprintf(c->pending_name, sizeof c->pending_name, "%s", name);
        c->pending_class = (uint8_t)atoi(skip_space(p));
        c->create_pending = 1;
        ++c->stats.creates;
        status(c, "OFFLINE DEMO: create request answered by the local store");
        return 1;
    }
    case 0x009a4708:
        status(c, "OFFLINE DEMO: rename requests are not answered");
        return 1;
    case 0x00b4c76a:   /* the delete request (name, password): the password is dropped here */
        c->delete_pending = 1;
        ++c->stats.deletes;
        status(c, "OFFLINE DEMO: delete request answered by the local store (no password check)");
        return 1;
    case 0x00b3967c:
    case 0x00b39648:
    case 0x00b3974a: {
        char owner[8] = "", text[1024] = "", title[256] = "";
        int id = 0, n = 0;
        if (sscanf(rest, "%7s %d %n", owner, &id, &n) < 2)
            return 1;
        const char *p = json_string(rest + n, text, sizeof text);
        p = json_string(skip_space(p), title, sizeof title);
        int x = 0;
        sscanf(p, "%d", &x);
        int type = address == 0x00b3967c ? 1 : address == 0x00b39648 ? 0 : 4;
        enqueue(c, owner[0] == 'w' ? 'w' : '0', id, type, address == 0x00b3974a ? x : 0, text, title);
        return 1;
    }
    case 0x00b399db:   /* the Caution window closed */
        if (c->caution_open)
            caution_hide(c);
        return 1;
    default:
        break;
    }
    return 0;
}

void mu_charsel_create_stash(mu_charsel_create *c, const char *name, const char *text)
{
    if (!c)
        return;
    if (name)
        to_client_bytes(name, c->name, sizeof c->name);
    if (text)
        to_client_bytes(text, c->input, sizeof c->input);
}

/* ------------------------------------------------------------------ public */

mu_charsel_create *mu_charsel_create_open(const mu_charsel_create_config *config, const mu_charsel_mugfx *api,
                                          mu_csg_window *list, const mu_csg_env *gfx, char *error, size_t cap)
{
    mu_charsel_create *c = calloc(1, sizeof *c);
    if (!c) {
        snprintf(error, cap, "out of memory");
        return NULL;
    }
    c->a = *api;
    c->cfg = *config;
    c->list = list;
    c->preview_model = -1;
    c->stats.preview_class = -1;
    c->protocol = 0x35;
    c->init_scene = 1;
    c->fov = 35.0f;
    c->w.limit = config->limit;
    c->w.created = config->created;
    c->w.delete_target = -1;
    int32_t nf = load_words(config->lang_dir, "filter.txt", c->filter_words);
    int32_t nn = load_words(config->lang_dir, "filtername.txt", c->filter_name_words);
    c->e.filter = (const char *const *)c->filter_words;
    c->e.filter_count = nf;
    c->e.filter_name = (const char *const *)c->filter_name_words;
    c->e.filter_name_count = nn;
    c->e.preview = c->preview;
    c->e.protocol_state = &c->protocol;
    c->e.init_scene = &c->init_scene;
    c->e.camera_fov = &c->fov;
    c->e.lead_byte = NULL;   /* a single-byte ANSI code page (the English setup) */
    c->e.window_x = 0.0f;
    c->e.window_y = 0.0f;
    c->e.window_scale = (float)(config->scale > 0 ? config->scale : 1.0);
    c->e.screen_width = config->width;
    c->e.screen_height = config->height;
    c->e.base_render = 1;
    c->e.scene = 5;
    c->e.menu_check = 1;    /* 0x00c8cbe2: no window blocks leaving (its macro save is not ported) */
    mu_charsel_create_rebind(c, gfx);
    /* the preview's starting class: CreateCharacterScene creates it with model 0x136 and class 1 (0x018515a0) */
    c->preview[MU_CHAR_CLASS] = 1;
    char err[512];
    if (config->movie_dir && movie_open(c, &c->caution, "Caution.swf", caution_call, err, sizeof err))
        snprintf(c->stats.status, sizeof c->stats.status, "%s", err);
    if (config->movie_dir && movie_open(c, &c->menu, "winSystemMenu.swf", menu_call, err, sizeof err))
        snprintf(c->stats.status, sizeof c->stats.status, "%s", err);
    if (c->caution.m)
        invoke(c, c->caution.m, CAUTION_PATH, "SetVisible", "[false]");
    menu_load(c);
    (void)error;
    (void)cap;
    return c;
}

void mu_charsel_create_rebind(mu_charsel_create *c, const mu_csg_env *gfx)
{
    if (!c)
        return;
    c->gfx = *gfx;
    c->e.gfx = &c->gfx;
    /* the menu's environment: the list's, with the create module as the context (trampolines) */
    c->menu_gfx = *gfx;
    c->menu_gfx.context = c;
    c->menu_gfx.emit = menu_emit;
    c->menu_gfx.character = menu_character;
    c->menu_gfx.global_text = menu_text;
    c->menu_gfx.class_name = menu_class;
    c->menu_gfx.name = NULL;
}

void mu_charsel_create_close(mu_charsel_create *c)
{
    if (!c)
        return;
    preview_free(c);
    mu_raster_free(&c->raster);
    movie_close(c, &c->caution);
    movie_close(c, &c->menu);
    for (int i = 0; i < WORDS_MAX; ++i) {
        free(c->filter_words[i]);
        free(c->filter_name_words[i]);
    }
    memset(c->name, 0, sizeof c->name);
    free(c);
}

void mu_charsel_create_ready(mu_charsel_create *c)
{
    if (c)
        mu_ccr_update_count(&c->w, &c->e, c->w.created, c->w.limit);
}

void mu_charsel_create_event(mu_charsel_create *c, int32_t code, int32_t argument)
{
    if (!c)
        return;
    switch (code) {
    case 0x20:   /* Create: 0x00b49bf4(1), 0x009a5920(0), 0x00b4b684() */
        mu_ccr_show_create(c->list, &c->w, &c->e, 1);
        c->w.rename_mode = 0;
        mu_ccr_restrict_classes(&c->w, &c->e);
        break;
    case 0x21:   /* Menu */
        mu_charsel_create_menu_toggle(c);
        break;
    case 0x23:   /* a refusal: GFx message box with the GlobalText */
        enqueue(c, '0', 0, 1, 0, gt(c, argument), "");
        break;
    case 0x25: { /* the delete confirmation 0x009a56a1..0x009a570a: sprintf(GT 0x6b0, name), message 0x65 */
        int32_t sel = *c->gfx.selected;
        const uint8_t *r = sel >= 0 && sel < MU_CHARSEL_CHARACTERS && c->gfx.character
                               ? c->gfx.character(c->gfx.context, sel) : NULL;
        char name[32] = "", text[512];
        if (r)
            snprintf(name, sizeof name, "%.15s", (const char *)(r + 0x3658));
        const char *f = gt(c, 0x6b0);
        const char *at = strstr(f, "%s");
        if (at)
            snprintf(text, sizeof text, "%.*s%s%s", (int)(at - f), f, name, at + 2);
        else
            snprintf(text, sizeof text, "%s", f);
        enqueue(c, 'w', 0x65, 0, 0, text, "");
        mu_ccr_delete_pending(&c->w, sel);
        break;
    }
    default:
        break;
    }
}

void mu_charsel_create_menu_toggle(mu_charsel_create *c)
{
    if (!c)
        return;
    if (!c->menu.m) {
        status(c, "winSystemMenu.swf missing: the menu is not shown");
        return;
    }
    c->e.gfx = &c->menu_gfx;
    mu_csm_toggle(c->list, &c->e);
    c->e.gfx = &c->gfx;
}

void mu_charsel_create_close_panel(mu_charsel_create *c)
{
    if (c)
        mu_ccr_show_create(c->list, &c->w, &c->e, 0);
}

void mu_charsel_create_advance(mu_charsel_create *c, double dt_ms)
{
    if (!c)
        return;
    if (c->caution.m)
        c->a.advance(c->caution.m, dt_ms);
    if (c->menu.m) {
        c->a.advance(c->menu.m, dt_ms);
        if (c->menu_loaded && ++c->menu_loaded == 3)   /* two frames after the attach: the window's onFileLoad */
            invoke(c, c->menu.m, MENU_PATH, "onFileLoad", "[]");
    }
    if (c->create_pending) {
        c->create_pending = 0;
        mu_ccr_created answer;
        memset(&answer, 0, sizeof answer);
        answer.result = 2;
        if (c->cfg.hooks.create)
            c->cfg.hooks.create(c->cfg.hooks.user, c->pending_name, c->pending_class, &answer);
        if (answer.result == 1)
            ++c->stats.created;
        else
            ++c->stats.refused;
        mu_ccr_created_answer(c->list, &c->w, &c->e, &answer);
        if (c->init_scene == 0) {
            c->stats.rebuild = 1;
            c->init_scene = 1;
        }
    }
    if (c->delete_pending) {
        c->delete_pending = 0;
        int32_t target = *c->gfx.selected;
        uint8_t result = c->cfg.hooks.remove ? c->cfg.hooks.remove(c->cfg.hooks.user, target) : 2;
        if (result == 1)
            ++c->stats.deleted;
        mu_ccr_delete_answer(c->list, &c->w, &c->e, result);
        if (c->init_scene == 0) {
            c->stats.rebuild = 1;
            c->init_scene = 1;
        }
    }
    if (c->countdown_ms > 0.0) {
        c->countdown_ms -= dt_ms;
        if (c->countdown_ms <= 0.0) {
            c->countdown_ms = 0.0;
            if (c->cfg.hooks.menu)
                c->cfg.hooks.menu(c->cfg.hooks.user, 0);
        }
    }
}

int mu_charsel_create_mouse(mu_charsel_create *c, int kind, int button, double x, double y)
{
    if (!c)
        return 0;
    if (c->caution_open && c->caution.m) {   /* modal */
        c->a.mouse(c->caution.m, kind, button, x, y);
        c->caution.dirty = 1;
        return 1;
    }
    if (c->e.menu_open && c->menu.m) {
        int over = c->a.hit_test(c->menu.m, x, y);
        if (over || kind == 0 || kind == 2)
            c->a.mouse(c->menu.m, kind, button, x, y);
        return over;
    }
    return 0;
}

int mu_charsel_create_key(mu_charsel_create *c, int vk, int down)
{
    if (!c)
        return 0;
    if (c->caution_open && c->caution.m) {
        c->a.key(c->caution.m, down ? 0 : 1, vk, vk == 0x0d ? '\r' : vk == 0x08 ? 8 : 0, 0);
        return 1;
    }
    return 0;
}

int mu_charsel_create_text(mu_charsel_create *c, const char *utf8)
{
    if (!c)
        return 0;
    if (c->caution_open && c->caution.m) {
        c->a.text(c->caution.m, utf8);
        return 1;
    }
    return 0;
}

void mu_charsel_create_draw_windows(mu_charsel_create *c, uint8_t *rgba, int32_t width, int32_t height)
{
    if (!c)
        return;
    if (c->e.menu_open)
        movie_composite(c, &c->menu, rgba, width, height);
    if (c->caution_open)
        movie_composite(c, &c->caution, rgba, width, height);
}

void mu_charsel_create_stats_get(const mu_charsel_create *c, mu_charsel_create_stats *out)
{
    memset(out, 0, sizeof *out);
    if (!c)
        return;
    *out = c->stats;
    out->create_open = c->w.create_open;
    out->menu_open = c->e.menu_open;
    out->caution_open = (uint8_t)c->caution_open;
    out->legacy_hidden = c->legacy_hidden;
    memcpy(out->board, c->w.board, sizeof out->board);
}

void mu_charsel_create_clear_rebuild(mu_charsel_create *c)
{
    if (c)
        c->stats.rebuild = 0;
}

static double variable(mu_charsel_create *c, MuGfx *m, const char *path, double fallback)
{
    const char *v = m ? c->a.get_variable(m, path) : NULL;
    if (!v || !*v || !strcmp(v, "null"))
        return fallback;
    char *end;
    double d = strtod(v, &end);
    return end == v ? fallback : d;
}

/* the centre of a nested clip: the parents' _x/_y summed (no scaled parents in these movies) */
static int clip_center(mu_charsel_create *c, MuGfx *m, const char *root, const char *members, double *x, double *y)
{
    char path[512], member[512];
    double sx = variable(c, m, (snprintf(path, sizeof path, "%s._x", root), path), NAN);
    double sy = variable(c, m, (snprintf(path, sizeof path, "%s._y", root), path), NAN);
    if (isnan(sx) || isnan(sy))
        return 0;
    snprintf(member, sizeof member, "%s", members);
    char prefix[512];
    snprintf(prefix, sizeof prefix, "%s", root);
    for (char *t = strtok(member, "."); t; t = strtok(NULL, ".")) {
        size_t n = strlen(prefix);
        snprintf(prefix + n, sizeof prefix - n, ".%s", t);
        double px = variable(c, m, (snprintf(path, sizeof path, "%s._x", prefix), path), NAN);
        double py = variable(c, m, (snprintf(path, sizeof path, "%s._y", prefix), path), NAN);
        if (isnan(px) || isnan(py))
            return 0;
        sx += px;
        sy += py;
    }
    double w = variable(c, m, (snprintf(path, sizeof path, "%s._width", prefix), path), 0.0);
    double h = variable(c, m, (snprintf(path, sizeof path, "%s._height", prefix), path), 0.0);
    const double scale = c->cfg.scale > 0 ? c->cfg.scale : 1.0;
    *x = (sx + w / 2.0) * scale;
    *y = (sy + h / 2.0) * scale;
    return 1;
}

int mu_charsel_create_control(mu_charsel_create *c, MuGfx *list_movie, const char *list_path, const char *name,
                              double *x, double *y)
{
    if (!c)
        return 0;
    int n = 0;
    char member[64];
    (void)list_path;
    if (sscanf(name, "class:%d", &n) == 1) {
        snprintf(member, sizeof member, "mcCharacterCreate.btnClass%d", n);
        return clip_center(c, list_movie, LIST_WINDOW, member, x, y);
    }
    if (!strcmp(name, "createok"))
        return clip_center(c, list_movie, LIST_WINDOW, "mcCharacterCreate.btnOK", x, y);
    if (!strcmp(name, "createcancel"))
        return clip_center(c, list_movie, LIST_WINDOW, "mcCharacterCreate.btnCancel", x, y);
    if (!strcmp(name, "createname"))
        return clip_center(c, list_movie, LIST_WINDOW, "mcCharacterCreate.tiCharacterName", x, y);
    if (!strcmp(name, "msgok") || !strcmp(name, "msgcancel")) {
        int ok = name[3] == 'o';
        const char *m = c->current.ui_type == 3 || c->current.ui_type == 4 ? (ok ? "mcInput.btnInputOk" : "mcInput.btnInputCancel")
                        : c->current.ui_type == 1 ? "mcCaution.mcBottom.btnCaution3"
                        : ok ? "mcCaution.mcBottom.btnCaution1" : "mcCaution.mcBottom.btnCaution2";
        return clip_center(c, c->caution.m, CAUTION_PATH, m, x, y);
    }
    if (!strcmp(name, "msginput"))
        return clip_center(c, c->caution.m, CAUTION_PATH, "mcInput.tiInput", x, y);
    if (!strncmp(name, "menu:", 5)) {
        const char *b = !strcmp(name + 5, "exit") ? "_btnExit" : !strcmp(name + 5, "server") ? "_btnServerSelect"
                        : !strcmp(name + 5, "option") ? "_btnOption" : !strcmp(name + 5, "character") ? "_btnCharSelect"
                        : "_btnClose";
        return clip_center(c, c->menu.m, MENU_PATH, b, x, y);
    }
    return 0;
}
