/* The GFx interface layer of the native client (NATIVE-GFX-002); see mu_gfx_layer.h.
 *
 * Client facts used here (static readings, docs/research/client-hud.md and
 * the movies' own ActionScript, read locally with JPEXS):
 *   - InventoryFrame reports UIInit(uid), requestWindowPos(x, y),
 *     requestSlotInfo(x, y, w, h, page) and requestItemSlotClick/ClickR/
 *     Over/Out(index); MUItemSlot.onReleaseAux sends ClickR for button 1;
 *   - main is Frame.Main (`_level0.mc`); its clips mcSkillHotKey,
 *     mcItemHotKey and mcExpBar are the names NATIVE-HUD-001 found in the
 *     client's invokes; main reports onLoad/onResize/onHotKey/onSelectSkill/
 *     onSkillTooltip/... on its "main" channel;
 *   - chat.swf is a symbol library: the UI loader attaches its "Chat" symbol
 *     (Frame.Chat, channel "chat"); OpenEditText/CloseEditText/AddChatInfo/
 *     onPushText are its game-facing methods, onEnterText/onFocuseText its
 *     reports, fscommand("TextInput", "focusIn"/"focusOut") its IME signal;
 *   - CharacterInfoFrame: SetName(position, index, sort, text, v1, v2,
 *     button), SetCharacterInfo, SetCharacterName, InitText, SetPointText;
 *     its "+" buttons report onClickButton(index);
 *   - InfoPopup: SetInfoPopup(x, y, w, h, html) positions itself around the
 *     rectangle; SetInfoPopupMainSmall(x, y, w, h, hotkey, name) for the bar;
 *     SetInfoPopupClose hides it.
 * Host choices (not client facts) are marked "layer choice". */
#define _POSIX_C_SOURCE 200809L
#define _DARWIN_C_SOURCE 1
#include "mu_gfx_layer.h"

#include <dlfcn.h>
#include <math.h>
#include <stdarg.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#ifdef __APPLE__
#include <mach-o/dyld.h>
#endif

#ifndef MU_GFX_NO_GL
#ifdef __APPLE__
#define GL_SILENCE_DEPRECATION 1
#include <OpenGL/OpenGL.h>
#include <OpenGL/gl.h>
#include <OpenGL/glext.h>
#include <OpenGL/CGLIOSurface.h>
#else
#include <GL/gl.h>
#endif
#endif

#include "inv_grid.h"
#include "item_slots.h"
#include "tooltip_html.h"
#include "mugfx/include/mugfx.h"

#define MAX_ITEMS 48

/* ---- mugfx, loaded at run time --------------------------------------------- */

typedef struct mugfx_api {
    void *dl;
    int (*abi_version)(void);
    MuGfx *(*open)(const char *, int, int, char *, size_t);
    MuGfx *(*open_shared)(const char *, int, int, char *, size_t);
    void (*close)(MuGfx *);
    void (*set_callback)(MuGfx *, mugfx_callback, void *);
    void (*start)(MuGfx *);
    void (*advance)(MuGfx *, double);
    int (*needs_render)(MuGfx *);
    int (*render)(MuGfx *, uint8_t *, size_t);
    int (*render_shared)(MuGfx *, int);
    void (*gpu_wait)(void);
    void *(*iosurface)(MuGfx *, int *, int *, uint32_t *);
    const char *(*invoke)(MuGfx *, const char *, const char *, const char *);
    int (*set_variable)(MuGfx *, const char *, const char *);
    const char *(*get_variable)(MuGfx *, const char *);
    int (*mouse)(MuGfx *, int, int, double, double);
    int (*hit_test)(MuGfx *, double, double);
    int (*cursor)(MuGfx *);
    int (*key)(MuGfx *, int, int, uint32_t, int);
    int (*text)(MuGfx *, const char *);
    int (*text_focus)(MuGfx *);
    int (*set_view)(MuGfx *, int, int, int, int, int, int, double);
    void (*size)(MuGfx *, int *, int *);
    void (*stats)(MuGfx *, MuGfxStats *);
} mugfx_api;

static int exe_dir(char *out, size_t cap)
{
    char path[4096];
#ifdef __APPLE__
    uint32_t size = sizeof path;
    if (_NSGetExecutablePath(path, &size) != 0)
        return 0;
#else
    ssize_t n = readlink("/proc/self/exe", path, sizeof path - 1);
    if (n <= 0)
        return 0;
    path[n] = 0;
#endif
    char *slash = strrchr(path, '/');
    if (!slash)
        return 0;
    *slash = 0;
    snprintf(out, cap, "%s", path);
    return 1;
}

static int api_load(mugfx_api *api, const char *explicit_path, char *error, size_t cap)
{
#ifdef __APPLE__
    const char *lib = "libmugfx.dylib";
#else
    const char *lib = "libmugfx.so";
#endif
    char candidates[4][4096];
    int n = 0;
    if (explicit_path)
        snprintf(candidates[n++], sizeof candidates[0], "%s", explicit_path);
    if (getenv("MU_GFX_LIB"))
        snprintf(candidates[n++], sizeof candidates[0], "%s", getenv("MU_GFX_LIB"));
    char dir[4096];
    if (exe_dir(dir, sizeof dir))   /* native/build/<tool> -> native/gfx/mugfx/target/release */
        snprintf(candidates[n++], sizeof candidates[0], "%s/../gfx/mugfx/target/release/%s", dir, lib);
    snprintf(candidates[n++], sizeof candidates[0], "native/gfx/mugfx/target/release/%s", lib);
    for (int i = 0; i < n && !api->dl; i++)
        api->dl = dlopen(candidates[i], RTLD_NOW | RTLD_LOCAL);
    if (!api->dl) {
        snprintf(error, cap, "libmugfx not found (build it with native/gfx/build-mugfx.sh or set MU_GFX_LIB): %s",
                 dlerror());
        return -1;
    }
#define SYM(field, name)                                                                                     \
    do {                                                                                                       \
        *(void **)&api->field = dlsym(api->dl, name);                                                          \
        if (!api->field) {                                                                                     \
            snprintf(error, cap, "libmugfx lacks %s (rebuild it)", name);                                       \
            return -1;                                                                                         \
        }                                                                                                      \
    } while (0)
    SYM(abi_version, "mugfx_abi_version");
    if (api->abi_version() != MUGFX_ABI_VERSION) {
        snprintf(error, cap, "libmugfx ABI %d, expected %d (rebuild it)", api->abi_version(), MUGFX_ABI_VERSION);
        return -1;
    }
    SYM(open, "mugfx_open");
    SYM(open_shared, "mugfx_open_shared");
    SYM(close, "mugfx_close");
    SYM(set_callback, "mugfx_set_callback");
    SYM(start, "mugfx_start");
    SYM(advance, "mugfx_advance");
    SYM(needs_render, "mugfx_needs_render");
    SYM(render, "mugfx_render");
    SYM(render_shared, "mugfx_render_shared");
    SYM(gpu_wait, "mugfx_gpu_wait");
    SYM(iosurface, "mugfx_iosurface");
    SYM(invoke, "mugfx_invoke");
    SYM(set_variable, "mugfx_set_variable");
    SYM(get_variable, "mugfx_get_variable");
    SYM(mouse, "mugfx_mouse");
    SYM(hit_test, "mugfx_hit_test");
    SYM(cursor, "mugfx_cursor");
    SYM(key, "mugfx_key");
    SYM(text, "mugfx_text");
    SYM(text_focus, "mugfx_text_focus");
    SYM(set_view, "mugfx_set_view");
    SYM(size, "mugfx_size");
    SYM(stats, "mugfx_stats");
#undef SYM
    return 0;
}

/* ---- state ---------------------------------------------------------------------- */

typedef struct movie {
    const char *file;           /* movie file stem */
    MuGfx *g;
    mu_gfx_layer *L;
    int id;
    int open;                   /* shown (windows) */
    char path[96];              /* instance path of the window */
    int32_t view[4];            /* x, y, w, h in window pixels */
    int view_dirty, frame_valid, needs_upload;
    uint8_t *rgba;              /* read-back frame */
    size_t rgba_cap;
#ifndef MU_GFX_NO_GL
    GLuint tex;
    uint32_t seed;
    int tex_w, tex_h;
#endif
    double next_bounds_ms;
} movie;

typedef struct item {
    mu_grid_item grid;
    int32_t level;
    char name[64];
    float rgb[3];
} item;

struct mu_gfx_layer {
    mu_gfx_layer_config cfg;
    mugfx_api api;
    movie mv[MU_GFX_MOVIES];
    int order[MU_GFX_MOVIES];   /* window z-order, bottom first */
    int norder;
    int32_t w, h;               /* the movies' stage in points */
    int32_t px_w, px_h;         /* window pixels */
    double scale;               /* pixels per point (Retina 2) */
    int shared;
    mu_gfx_hero hero, shown;    /* current values, values last sent to main */
    int hero_dirty_char;
    /* inventory */
    mu_grid grid;
    item items[MAX_ITEMS];
    int nitems, held, hover;
    float win_x, win_y, slot_x, slot_y, slot_w, slot_h, gap_x, gap_y;
    int have_slot;
    /* chat */
    int chat_edit, chat_ready;
    char last_sent[256];
    /* skills */
    int selected_skill;
    int32_t potions;
    /* input */
    double mouse_x, mouse_y;
    int capture;                /* movie that took the last button press, or -1 */
    int key_used;               /* a movie callback used the current key */
    int main_down_vk;           /* last key pressed while the bar had the keyboard */
    /* time */
    double time_ms, next_step_ms;
    long steps, callbacks, invokes, view_changes;
    long renders[MU_GFX_MOVIES];
    double render_ms[MU_GFX_MOVIES], capture_ms[MU_GFX_MOVIES], upload_ms[MU_GFX_MOVIES];
    double gpu_wait_ms;
    long gpu_waits;
    char reply[256];
};

static const char *const FILES[MU_GFX_MOVIES] = {"main", "InventoryFrame", "InfoPopup", "CharacterInfoFrame", "chat"};

static double now_ms(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec * 1000.0 + (double)ts.tv_nsec / 1e6;
}

static void logf_(mu_gfx_layer *L, const char *fmt, ...)
{
    if (!L->cfg.log)
        return;
    va_list ap;
    va_start(ap, fmt);
    fprintf(L->cfg.log, "[%8.1f] ", L->time_ms);
    vfprintf(L->cfg.log, fmt, ap);
    fputc('\n', L->cfg.log);
    va_end(ap);
    fflush(L->cfg.log);
}

/* ---- tiny JSON helpers (callback arguments are arrays of scalars/objects) -------- */

static int json_numbers(const char *s, double *out, int max)
{
    int n = 0, depth = 0, in_str = 0;
    for (const char *p = s; *p && n < max; p++) {
        if (in_str) {
            if (*p == '\\' && p[1]) p++;
            else if (*p == '"') in_str = 0;
            continue;
        }
        if (*p == '"') { in_str = 1; continue; }
        if (*p == '{' || *p == '[') { depth++; continue; }
        if (*p == '}' || *p == ']') { depth--; continue; }
        if (depth == 1 && (*p == '-' || (*p >= '0' && *p <= '9'))) {
            char *end;
            out[n++] = strtod(p, &end);
            p = end - 1;
        }
    }
    return n;
}

static int json_string(const char *s, int index, char *out, size_t cap)
{
    int n = 0, depth = 0;
    for (const char *p = s; *p; p++) {
        if (*p == '{' || *p == '[') { depth++; continue; }
        if (*p == '}' || *p == ']') { depth--; continue; }
        if (*p == '"') {
            const char *q = p + 1;
            while (*q && *q != '"') { if (*q == '\\' && q[1]) q++; q++; }
            if (depth == 1 && n++ == index) {
                size_t len = (size_t)(q - p - 1), o = 0;
                for (size_t i = 0; i < len && o + 1 < cap; i++) {
                    char c = p[1 + i];
                    if (c == '\\' && i + 1 < len) c = p[1 + ++i];
                    out[o++] = c;
                }
                out[o] = 0;
                return 1;
            }
            p = q;
        }
    }
    return 0;
}

static double json_field(const char *s, const char *key, double fallback)
{
    char pat[64];
    snprintf(pat, sizeof pat, "\"%s\":", key);
    const char *p = strstr(s, pat);
    return p ? strtod(p + strlen(pat), NULL) : fallback;
}

static int json_field_string(const char *s, const char *key, char *out, size_t cap)
{
    char pat[64];
    snprintf(pat, sizeof pat, "\"%s\":\"", key);
    const char *p = strstr(s, pat);
    if (!p)
        return 0;
    p += strlen(pat);
    size_t o = 0;
    while (*p && *p != '"' && o + 1 < cap) {
        if (*p == '\\' && p[1]) p++;
        out[o++] = *p++;
    }
    out[o] = 0;
    return 1;
}

/* JSON string literal of `s` (quotes included). */
static void json_quote(char *out, size_t cap, const char *s)
{
    size_t o = 0;
    if (cap < 3) {
        if (cap) out[0] = 0;
        return;
    }
    out[o++] = '"';
    for (; *s && o + 7 < cap; s++) {
        unsigned char c = (unsigned char)*s;
        if (c == '"' || c == '\\') { out[o++] = '\\'; out[o++] = (char)c; }
        else if (c == '\n') { out[o++] = '\\'; out[o++] = 'n'; }
        else if (c < 0x20) o += (size_t)snprintf(out + o, cap - o, "\\u%04x", c);
        else out[o++] = (char)c;
    }
    out[o++] = '"';
    out[o] = 0;
}

static void commas(char *out, size_t cap, int64_t v)
{
    char digits[32];
    snprintf(digits, sizeof digits, "%lld", (long long)(v < 0 ? -v : v));
    size_t n = strlen(digits), o = 0;
    if (v < 0 && o + 1 < cap) out[o++] = '-';
    for (size_t i = 0; i < n && o + 2 < cap; i++) {
        out[o++] = digits[i];
        if ((n - i - 1) % 3 == 0 && i + 1 < n)
            out[o++] = ',';
    }
    out[o] = 0;
}

/* ---- game -> movie --------------------------------------------------------------- */

static const char *invokef(mu_gfx_layer *L, int m, const char *path, const char *method, const char *fmt, ...)
{
    movie *mv = &L->mv[m];
    if (!mv->g || !path || !path[0])
        return NULL;
    char *args = malloc(16384);
    if (!args)
        return NULL;
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(args, 16384, fmt, ap);
    va_end(ap);
    L->invokes++;
    const char *r = L->api.invoke(mv->g, path, method, args);
    logf_(L, "%s <- %s.%s(%.300s) = %.200s", mv->file, path, method, args, r ? r : "(queued)");
    free(args);
    mv->view_dirty = 1;
    return r;
}

static void slot_states(mu_gfx_layer *L)
{
    movie *mv = &L->mv[MU_GFX_INVENTORY];
    if (!mv->path[0])
        return;
    /* The movie colours a cell's background by state (frames of
     * MuItemSlot_icons01); the client informs it through the status refresh
     * 0x00c94193.  Occupied cells: state 2, free: 1 (layer choice). */
    char list[512];
    size_t n = 0;
    for (int i = 0; i < L->grid.cols * L->grid.rows; i++)
        n += (size_t)snprintf(list + n, sizeof list - n, "%s%d", i ? "," : "", L->grid.cells[i] ? 2 : 1);
    invokef(L, MU_GFX_INVENTORY, mv->path, "SetSlotStateAll", "[0,\"%s\"]", list);
}

static void zen_text(mu_gfx_layer *L)
{
    char zen[32], ruud[32];
    commas(zen, sizeof zen, L->hero.zen);
    commas(ruud, sizeof ruud, L->hero.ruud);
    invokef(L, MU_GFX_INVENTORY, L->mv[MU_GFX_INVENTORY].path, "SetZenText",
            "[\"<font color='#FFCC19'>%s</font>\"]", zen);
    invokef(L, MU_GFX_INVENTORY, L->mv[MU_GFX_INVENTORY].path, "SetRuudText",
            "[\"<font color='#FFCC19'>%s</font>\"]", ruud);
}

static void feed_main(mu_gfx_layer *L)
{
    movie *mv = &L->mv[MU_GFX_MAIN];
    const mu_gfx_hero *h = &L->hero, *s = &L->shown;
    if (!mv->path[0])
        return;
    if (h->hp != s->hp || h->max_hp != s->max_hp || h->mp != s->mp || h->max_mp != s->max_mp || h->sd != s->sd ||
        h->max_sd != s->max_sd || h->ag != s->ag || h->max_ag != s->max_ag)
        invokef(L, MU_GFX_MAIN, mv->path, "setHPMP",
                "[{\"isToxic\":false,\"hp\":%d,\"maxHp\":%d,\"mp\":%d,\"maxMp\":%d,\"Shield\":%d,\"ShieldMax\":%d,"
                "\"SkillMana\":%d,\"SkillManaMax\":%d}]",
                h->hp, h->max_hp, h->mp, h->max_mp, h->sd, h->max_sd, h->ag, h->max_ag);
    if (h->exp != s->exp || h->exp_max != s->exp_max || h->level != s->level) {
        char cur[32], max[32];
        commas(cur, sizeof cur, h->exp);
        commas(max, sizeof max, h->exp_max);
        double rate = h->exp_max > 0 ? 100.0 * (double)h->exp / (double)h->exp_max : 0;
        char path[128];
        snprintf(path, sizeof path, "%s.mcExpBar", mv->path);
        invokef(L, MU_GFX_MAIN, path, "setExpData",
                "[{\"ClassLevel\":%d,\"rate\":%.2f,\"curExp\":\"%s\",\"maxExp\":\"%s\",\"page\":%d}]",
                h->master_level > 0 ? 3 : 1, rate, cur, max, (int)(rate / 10.0));
    }
    if (h->strength != s->strength || h->agility != s->agility || h->vitality != s->vitality ||
        h->energy != s->energy || h->command != s->command || h->points != s->points || h->level != s->level ||
        strcmp(h->name, s->name))
        L->hero_dirty_char = 1;
    if (h->zen != s->zen || h->ruud != s->ruud)
        zen_text(L);
    L->shown = L->hero;
}

static void feed_item_hotkeys(mu_gfx_layer *L)
{
    char path[128];
    snprintf(path, sizeof path, "%s.mcItemHotKey", L->mv[MU_GFX_MAIN].path);
    /* Icons come from the client's root image movie (gSystem.Image), which is
     * not loaded; the counts show (layer choice: one potion slot). */
    invokef(L, MU_GFX_MAIN, path, "setItemHotKeyAll",
            "[[{\"slot\":0,\"selectGroup\":1,\"itemType\":7181,\"itemLevel\":0,\"itemCount\":%d},"
            "{\"slot\":1,\"selectGroup\":0},{\"slot\":2,\"selectGroup\":0},{\"slot\":3,\"selectGroup\":0}]]",
            L->potions);
}

static void feed_skills(mu_gfx_layer *L)
{
    char path[128], slots[1024];
    size_t n = 0;
    snprintf(path, sizeof path, "%s.mcSkillHotKey", L->mv[MU_GFX_MAIN].path);
    for (int i = 0; i < 10; i++)
        n += (size_t)snprintf(slots + n, sizeof slots - n, "%s{\"slot\":%d,\"skill\":%d,\"isUse\":true,"
                              "\"damageType\":0}", i ? "," : "", i, i < 6 ? i + 1 : 0);
    invokef(L, MU_GFX_MAIN, path, "SetSkillSlot",
            "[{\"Elemental\":0,\"SelectSlot\":%d,\"SelectSkill\":%d,\"SelectUseSkill\":true,"
            "\"SelectSkill_damageType\":0,\"arrSlots\":[%s]}]", L->selected_skill, L->selected_skill + 1, slots);
}

static void feed_character(mu_gfx_layer *L)
{
    movie *mv = &L->mv[MU_GFX_CHARACTER];
    const mu_gfx_hero *h = &L->hero;
    if (!mv->path[0])
        return;
    char lv[32], exp[32], expmax[48], v[5][32], pts[32];
    snprintf(lv, sizeof lv, "%d", h->level);
    commas(exp, sizeof exp, h->exp);
    char tmp[32];
    commas(tmp, sizeof tmp, h->exp_max);
    snprintf(expmax, sizeof expmax, "/ %s", tmp);
    const int32_t stats[5] = {h->strength, h->agility, h->vitality, h->energy, h->command};
    for (int i = 0; i < 5; i++)
        commas(v[i], sizeof v[i], stats[i]);
    snprintf(pts, sizeof pts, "%d", h->points);
    char name[64], cls[64];
    json_quote(name, sizeof name, h->name);
    json_quote(cls, sizeof cls, h->class_name);
    invokef(L, MU_GFX_CHARACTER, mv->path, "ClearItems", "[]");
    invokef(L, MU_GFX_CHARACTER, mv->path, "SetCharacterName", "[%s]", name);
    /* Base info (TEXT_TYPE_CHARACTER_BASE_INFO = 1, sort orders 0..6) and stat
     * rows (TEXT_TYPE_CHARACTER_STAT_INFO = 2, button type 1 = "+").  The
     * client's labels come from its GlobalText; these are English stand-ins. */
    invokef(L, MU_GFX_CHARACTER, mv->path, "SetName", "[1,0,0,\"Level\",\"%s\",\"%s\",0]", lv,
            h->master_level ? "" : "");
    invokef(L, MU_GFX_CHARACTER, mv->path, "SetName", "[1,1,1,\"Class\",%s,\"\",0]", cls);
    invokef(L, MU_GFX_CHARACTER, mv->path, "SetName", "[1,2,2,\"Exp\",\"%s\",\"%s\",0]", exp, expmax);
    invokef(L, MU_GFX_CHARACTER, mv->path, "SetName", "[1,3,3,\"Points\",\"%s\",\"\",0]", pts);
    static const char *const LABELS[5] = {"Strength", "Agility", "Vitality", "Energy", "Command"};
    for (int i = 0; i < 5; i++)
        invokef(L, MU_GFX_CHARACTER, mv->path, "SetName", "[2,%d,%d,\"%s\",\"%s\",\"\",1]", i + 1, i, LABELS[i],
                v[i]);
    char dmg[64];
    snprintf(dmg, sizeof dmg, "%d ~ %d", h->strength / 6 + h->level, h->strength / 4 + h->level * 2);
    invokef(L, MU_GFX_CHARACTER, mv->path, "SetName", "[3,10,0,\"Damage\",\"%s\",\"\",0]", dmg);
    invokef(L, MU_GFX_CHARACTER, mv->path, "UpdateScorllList", "[2]");
    invokef(L, MU_GFX_CHARACTER, mv->path, "SetPointText", "[%s]", h->points > 0 ? "true" : "false");
    L->hero_dirty_char = 0;
}

/* ---- tooltips ---------------------------------------------------------------------- */

static void builtin_tooltip(const item *it, char *html, size_t cap)
{
    /* Minimal tooltip through the reconstructed HTML assembly (0x00b8d94b /
     * 0x00ab4dc0): name in the name colour, a blank line, level and size. */
    char name[96], level[48], size[48];
    snprintf(name, sizeof name, it->level > 0 ? "%s +%d" : "%s", it->name, (int)it->level);
    snprintf(level, sizeof level, "Item code %d", (int)it->grid.code);
    snprintf(size, sizeof size, "%d x %d", it->grid.width, it->grid.height);
    mu_tooltip_line lines[4] = {{name, 3, 0, 0}, {"\n", 0, 0, 0}, {level, 0, 0, 0}, {size, 1, 0, 0}};
    char raw[1024];
    mu_tooltip_html(raw, sizeof raw, lines, 4, NULL);
    mu_latin1_to_utf8(html, cap, raw);
}

static void show_item_tooltip(mu_gfx_layer *L, int cell)
{
    movie *tip = &L->mv[MU_GFX_TOOLTIP];
    mu_grid_item *gi = mu_grid_item_at(&L->grid, cell);
    if (!tip->g || !gi || !L->grid.cells[cell] || L->held >= 0)
        return;
    item *it = (item *)gi;
    static char html[8192], quoted[16384];
    if (!L->cfg.tooltip || L->cfg.tooltip(L->cfg.tooltip_user, it->grid.code, it->level, html, sizeof html))
        builtin_tooltip(it, html, sizeof html);
    json_quote(quoted, sizeof quoted, html);
    float x = L->win_x + L->slot_x + it->grid.col * (L->slot_w + L->gap_x);
    float y = L->win_y + L->slot_y + it->grid.row * (L->slot_h + L->gap_y);
    float w = it->grid.width * L->slot_w, h = it->grid.height * L->slot_h;
    tip->open = 1;
    invokef(L, MU_GFX_TOOLTIP, tip->path, "SetInfoPopup", "[%d,%d,%d,%d,%s]", (int)x, (int)y, (int)w, (int)h,
            quoted);
}

static void hide_tooltip(mu_gfx_layer *L)
{
    movie *tip = &L->mv[MU_GFX_TOOLTIP];
    if (tip->open)
        invokef(L, MU_GFX_TOOLTIP, tip->path, "SetInfoPopupClose", "[]");
    tip->open = 0;
}

/* ---- windows ------------------------------------------------------------------------ */

static void raise_window(mu_gfx_layer *L, int m)
{
    int k = 0;
    for (int i = 0; i < L->norder; i++)
        if (L->order[i] != m)
            L->order[k++] = L->order[i];
    L->order[k++] = m;
    L->norder = k;
}

void mu_gfx_layer_show(mu_gfx_layer *L, int m, int open)
{
    if (!L || m < 0 || m >= MU_GFX_MOVIES || !L->mv[m].g)
        return;
    movie *mv = &L->mv[m];
    if (m == MU_GFX_MAIN || m == MU_GFX_CHAT) {
        mv->open = open;
        return;
    }
    if (m == MU_GFX_TOOLTIP) {
        if (!open)
            hide_tooltip(L);
        return;
    }
    if (mv->open == open)
        return;
    mv->open = open;
    if (open)
        raise_window(L, m);
    if (!open && m == MU_GFX_INVENTORY)
        hide_tooltip(L);
    if (open && m == MU_GFX_CHARACTER)
        feed_character(L);
    invokef(L, m, mv->path, "SetVisible", "[%s]", open ? "true" : "false");
    mv->next_bounds_ms = 0;
}

void mu_gfx_layer_toggle(mu_gfx_layer *L, int m)
{
    if (L && m >= 0 && m < MU_GFX_MOVIES)
        mu_gfx_layer_show(L, m, !L->mv[m].open);
}

int mu_gfx_layer_is_open(const mu_gfx_layer *L, int m)
{
    return L && m >= 0 && m < MU_GFX_MOVIES && L->mv[m].g && L->mv[m].open;
}

/* ---- inventory -------------------------------------------------------------------------- */

static void inventory_click(mu_gfx_layer *L, int index)
{
    int cols = L->grid.cols;
    if (index < 0 || index >= cols * L->grid.rows)
        return;
    if (L->held < 0) {
        mu_grid_item *gi = mu_grid_item_at(&L->grid, index);
        if (gi && L->grid.cells[index]) {
            L->held = (int)((item *)gi - L->items);
            mu_grid_remove(&L->grid, gi);
            hide_tooltip(L);
            logf_(L, "game: pick item %u (%dx%d) from cell %d", gi->id, gi->width, gi->height, index);
        }
    } else {
        item *it = &L->items[L->held];
        int col = index % cols, row = index / cols;
        if (mu_grid_fits(&L->grid, col, row, it->grid.width, it->grid.height)) {
            mu_grid_place(&L->grid, col, row, &it->grid);
            logf_(L, "game: drop item %u at cell %d (%d,%d)", it->grid.id, index, col, row);
            L->held = -1;
        } else {
            logf_(L, "game: item %u does not fit at cell %d", it->grid.id, index);
        }
    }
    slot_states(L);
}

static void inventory_click_r(mu_gfx_layer *L, int index)
{
    /* Right click on an item: the client uses or equips it (0x00b907b9's
     * handler; not reconstructed).  The layer logs it and, for the demo
     * potion code, drinks one (layer choice). */
    mu_grid_item *gi = index >= 0 && index < L->grid.cols * L->grid.rows ? mu_grid_item_at(&L->grid, index) : NULL;
    if (gi && L->grid.cells[index]) {
        logf_(L, "game: right click item %u code %d at cell %d", gi->id, gi->code, index);
        if (gi->code == 7181 || gi->code == 7182) {
            L->hero.hp = L->hero.max_hp;
            logf_(L, "game: potion restores HP");
        }
    }
}

int mu_gfx_layer_add_item(mu_gfx_layer *L, int32_t code, int32_t level, int32_t width, int32_t height,
                          const char *name)
{
    if (!L || L->nitems >= MAX_ITEMS)
        return -1;
    item *it = &L->items[L->nitems];
    memset(it, 0, sizeof *it);
    it->grid.id = (uint32_t)(L->nitems + 1);
    it->grid.code = code;
    it->grid.width = (uint8_t)(width < 1 ? 1 : width);
    it->grid.height = (uint8_t)(height < 1 ? 1 : height);
    it->level = level;
    snprintf(it->name, sizeof it->name, "%s", name && name[0] ? name : "Item");
    int col, row;
    if (!mu_grid_find_free(&L->grid, it->grid.width, it->grid.height, &col, &row))
        return -1;
    mu_grid_place(&L->grid, col, row, &it->grid);
    /* Stand-in colour per item group (layer choice: no RenderItem3D models). */
    static const float PALETTE[8][3] = {{.85f, .35f, .25f}, {.35f, .55f, .9f}, {.95f, .8f, .3f}, {.55f, .75f, .4f},
                                        {.7f, .45f, .85f}, {.3f, .8f, .8f}, {.9f, .55f, .2f}, {.8f, .8f, .8f}};
    memcpy(it->rgb, PALETTE[(code >> 9) & 7], sizeof it->rgb);
    L->nitems++;
    slot_states(L);
    return L->nitems - 1;
}

/* ---- chat ----------------------------------------------------------------------------------- */

void mu_gfx_layer_chat(mu_gfx_layer *L, int type, const char *name, const char *message)
{
    if (!L || !L->mv[MU_GFX_CHAT].g)
        return;
    char qn[96], qm[600];
    json_quote(qn, sizeof qn, name ? name : "");
    json_quote(qm, sizeof qm, message ? message : "");
    invokef(L, MU_GFX_CHAT, L->mv[MU_GFX_CHAT].path, "AddChatInfo", "[{\"type\":%d,\"name\":%s,\"msg\":%s}]", type,
            qn, qm);
}

static void chat_open(mu_gfx_layer *L, int open)
{
    movie *mv = &L->mv[MU_GFX_CHAT];
    if (!mv->g || L->chat_edit == open)
        return;
    L->chat_edit = open;
    invokef(L, MU_GFX_CHAT, mv->path, open ? "OpenEditText" : "CloseEditText", "[]");
}

static void chat_submit(mu_gfx_layer *L)
{
    movie *mv = &L->mv[MU_GFX_CHAT];
    const char *r = L->api.invoke(mv->g, mv->path, "getText", "[]");
    char text[512] = "";
    if (r && r[0] == '"') {
        char wrapped[600];
        snprintf(wrapped, sizeof wrapped, "[%s]", r);
        json_string(wrapped, 0, text, sizeof text);
    }
    if (!text[0]) {
        chat_open(L, 0);
        return;
    }
    /* The movie's own submit path (the client's IME pushes the composed
     * string with position 0): it reports chat/onEnterText. */
    char q[600];
    json_quote(q, sizeof q, text);
    invokef(L, MU_GFX_CHAT, mv->path, "onPushText", "[{\"pos\":0,\"str\":%s}]", q);
    chat_open(L, 0);
}

/* ---- movie -> game ---------------------------------------------------------------------------- */

static const char *on_call(void *user, const char *name, const char *args)
{
    movie *mv = user;
    mu_gfx_layer *L = mv->L;
    L->callbacks++;
    if (strcmp(name, "TweenTimeSet") && strcmp(name, "requestSlotInfo") && strcmp(name, "EQUIPrequestSlotInfo"))
        logf_(L, "%s -> %s %.300s", mv->file, name, args);
    double v[8];
    int n = json_numbers(args, v, 8);
    char s[256];
    mv->view_dirty = 1;
    if (!strcmp(name, "UIInit") && json_string(args, 0, s, sizeof s)) {
        snprintf(mv->path, sizeof mv->path, "_level0.%s", s);
        return NULL;
    }
    if (!strcmp(name, "CloseWindow")) {
        mu_gfx_layer_show(L, mv->id, 0);     /* queued: we are inside the movie */
        return NULL;
    }
    if (!strcmp(name, "fscommand")) {
        if (json_string(args, 1, s, sizeof s) && mv->id == MU_GFX_CHAT)
            L->chat_edit = !strcmp(s, "focusIn") ? 1 : !strcmp(s, "focusOut") ? 0 : L->chat_edit;
        return NULL;
    }
    switch (mv->id) {
    case MU_GFX_MAIN:
        if (!strcmp(name, "main") && json_string(args, 0, s, sizeof s)) {
            if (!strcmp(s, "onLoad")) {
                char path[96];
                if (json_string(args, 1, path, sizeof path))
                    snprintf(mv->path, sizeof mv->path, "%s", path);
            } else if (!strcmp(s, "onHotKey")) {
                int key = (int)json_field(args, "keyCode", 0);
                L->key_used = 1;
                if (key == 'I' || key == 'V')
                    mu_gfx_layer_toggle(L, MU_GFX_INVENTORY);
                else if (key == 'C')
                    mu_gfx_layer_toggle(L, MU_GFX_CHARACTER);
                else if (key == 27) {
                    if (L->mv[MU_GFX_INVENTORY].open || L->mv[MU_GFX_CHARACTER].open) {
                        mu_gfx_layer_show(L, MU_GFX_INVENTORY, 0);
                        mu_gfx_layer_show(L, MU_GFX_CHARACTER, 0);
                    }
                }
            } else if (!strcmp(s, "onSelectSkill")) {
                L->key_used = 1;
                int slot = (int)json_field(args, "slot", 0), skill = (int)json_field(args, "skill", 0);
                char path[128];
                snprintf(path, sizeof path, "%s.mcSkillHotKey", mv->path);
                L->selected_skill = slot;
                invokef(L, MU_GFX_MAIN, path, "setSelectSkill", "[{\"slot\":%d}]", slot);
                invokef(L, MU_GFX_MAIN, path, "onUseSkillDelay", "[{\"skill\":%d,\"delaytime\":1500}]", skill);
                if (L->hero.ag >= 20)
                    L->hero.ag -= 20;
            } else if (!strcmp(s, "onSkillTooltip")) {
                int slot = (int)json_field(args, "slot", 0), skill = (int)json_field(args, "skill", 0);
                char hotkey[8], label[48];
                snprintf(hotkey, sizeof hotkey, "%d", (slot + 1) % 10);
                snprintf(label, sizeof label, "Skill %d", skill);
                L->mv[MU_GFX_TOOLTIP].open = 1;
                invokef(L, MU_GFX_TOOLTIP, L->mv[MU_GFX_TOOLTIP].path, "SetInfoPopupMainSmall",
                        "[%d,%d,%d,%d,\"%s\",\"%s\"]", (int)json_field(args, "x", 0), (int)json_field(args, "y", 0),
                        (int)json_field(args, "w", 32), (int)json_field(args, "h", 32), hotkey, label);
            } else if (!strcmp(s, "offSkillTooltip") || !strcmp(s, "offItemTooltip") ||
                       !strcmp(s, "offExpTooltip")) {
                hide_tooltip(L);
            } else if (!strcmp(s, "useItemHotKey")) {
                if (L->potions > 0) {
                    L->potions--;
                    L->hero.hp = L->hero.hp + L->hero.max_hp / 4 > L->hero.max_hp ? L->hero.max_hp
                                                                                    : L->hero.hp + L->hero.max_hp / 4;
                    feed_item_hotkeys(L);
                }
            }
        }
        return NULL;
    case MU_GFX_INVENTORY:
        if (!strcmp(name, "requestWindowPos") && n >= 2) {
            L->win_x = (float)v[0];
            L->win_y = (float)v[1];
        } else if (!strcmp(name, "requestSlotInfo") && n >= 5 && v[4] == 0) {
            L->slot_x = (float)v[0];
            L->slot_y = (float)v[1];
            L->slot_w = (float)v[2];
            L->slot_h = (float)v[3];
            L->have_slot = 1;
        } else if (!strcmp(name, "requestItemSlotClick") && n >= 1) {
            inventory_click(L, (int)v[0]);
        } else if (!strcmp(name, "requestItemSlotClickR") && n >= 1) {
            inventory_click_r(L, (int)v[0]);
        } else if (!strcmp(name, "requestItemSlotOver") && n >= 1) {
            L->hover = (int)v[0];
            show_item_tooltip(L, L->hover);
        } else if (!strcmp(name, "requestItemSlotOut")) {
            L->hover = -1;
            hide_tooltip(L);
        }
        return NULL;
    case MU_GFX_CHARACTER:
        if (!strcmp(name, "onClickButton") && n >= 1 && L->hero.points > 0) {
            int index = (int)v[0];
            int32_t *stat = index == 1 ? &L->hero.strength : index == 2 ? &L->hero.agility
                          : index == 3 ? &L->hero.vitality : index == 4 ? &L->hero.energy
                          : index == 5 ? &L->hero.command : NULL;
            if (stat) {
                (*stat)++;
                L->hero.points--;
                L->hero_dirty_char = 1;
                logf_(L, "game: stat %d +1 (points left %d)", index, L->hero.points);
            }
        }
        return NULL;
    case MU_GFX_CHAT:
        if (!strcmp(name, "chat") && json_string(args, 0, s, sizeof s)) {
            if (!strcmp(s, "onLoad")) {
                char path[96];
                if (json_string(args, 1, path, sizeof path))
                    snprintf(mv->path, sizeof mv->path, "%s", path);
            } else if (!strcmp(s, "onEnterText")) {
                char text[256] = "";
                json_field_string(args, "text", text, sizeof text);
                snprintf(L->last_sent, sizeof L->last_sent, "%s", text);
                /* Local echo (layer choice): the server would send it back. */
                mu_gfx_layer_chat(L, 1, L->hero.name, text);
            } else if (!strcmp(s, "onFocuseText")) {
                if (strstr(args, "\"focused\":true"))
                    chat_open(L, 1);
                else if (strstr(args, "\"focused\":false"))
                    chat_open(L, 0);
            }
        }
        return NULL;
    default:
        return NULL;
    }
}

/* ---- setup -------------------------------------------------------------------------------------- */

static int open_movie(mu_gfx_layer *L, int m, char *error, size_t cap)
{
    movie *mv = &L->mv[m];
    char path[4096], err[512];
    snprintf(path, sizeof path, "%s/%s.swf", L->cfg.movie_dir, FILES[m]);
    mv->file = FILES[m];
    mv->L = L;
    mv->id = m;
    mv->g = L->shared ? L->api.open_shared(path, L->px_w, L->px_h, err, sizeof err)
                      : L->api.open(path, L->px_w, L->px_h, err, sizeof err);
    if (!mv->g) {
        snprintf(error, cap, "%s: %s", path, err);
        return -1;
    }
    L->api.set_callback(mv->g, on_call, mv);
    L->api.set_view(mv->g, L->w, L->h, 0, 0, 0, 0, L->scale);
    L->api.start(mv->g);
    mv->view[0] = mv->view[1] = 0;
    mv->view[2] = L->w;
    mv->view[3] = L->h;
    mv->view_dirty = 1;
    return 0;
}

static void slot_gap(mu_gfx_layer *L)
{
    /* Gap between cells: the second slot's offset minus the cell width (the
     * movie reports only slot 0; layer choice, not a client fact). */
    movie *mv = &L->mv[MU_GFX_INVENTORY];
    char p[192];
    double x0, x1, y0, y8;
    snprintf(p, sizeof p, "%s.mcInventoryFrame.isSlot0._x", mv->path);
    const char *a = L->api.get_variable(mv->g, p);
    x0 = a ? atof(a) : 0;
    snprintf(p, sizeof p, "%s.mcInventoryFrame.isSlot1._x", mv->path);
    a = L->api.get_variable(mv->g, p);
    x1 = a ? atof(a) : 0;
    snprintf(p, sizeof p, "%s.mcInventoryFrame.isSlot0._y", mv->path);
    a = L->api.get_variable(mv->g, p);
    y0 = a ? atof(a) : 0;
    snprintf(p, sizeof p, "%s.mcInventoryFrame.isSlot8._y", mv->path);
    a = L->api.get_variable(mv->g, p);
    y8 = a ? atof(a) : 0;
    L->gap_x = x1 > x0 ? (float)(x1 - x0) - L->slot_w : 0;
    L->gap_y = y8 > y0 ? (float)(y8 - y0) - L->slot_h : 0;
}

static void window_sizes(mu_gfx_layer *L)
{
    /* GetWindowWidth/Height of MUComponent come from the host. */
    for (int m = MU_GFX_INVENTORY; m <= MU_GFX_CHARACTER; m++)
        invokef(L, m, L->mv[m].path, "SetWindowSize", "[%d,%d]", L->w, L->h - (m == MU_GFX_INVENTORY ? 120 : 0));
}

static void init_movies(mu_gfx_layer *L)
{
    movie *m_main = &L->mv[MU_GFX_MAIN], *chat = &L->mv[MU_GFX_CHAT];
    /* main.gfx places Frame.Main as "mc"; the client's UI loader triggers
     * its onFileLoad, which reports main/onLoad with the path (layer plays
     * the loader). */
    invokef(L, MU_GFX_MAIN, "_level0.mc", "onFileLoad", "[]");
    if (m_main->path[0]) {
        invokef(L, MU_GFX_MAIN, m_main->path, "InitMenuInfo",
                "[{\"IngameShop\":{\"keyCode\":88,\"key\":\"X\",\"label\":\"In-game shop\"},"
                "\"CharacterInfo\":{\"keyCode\":67,\"key\":\"C\",\"label\":\"Character\"},"
                "\"Inventory\":{\"label\":\"Inventory\",\"subMenu\":[{\"keyCode\":73,\"key\":\"I\",\"label\":\"Inventory\"},"
                "{\"keyCode\":75,\"key\":\"K\",\"label\":\"Gremory case\"}]},"
                "\"Quest\":{\"keyCode\":84,\"key\":\"T\",\"label\":\"Quest\"},"
                "\"Community\":{\"label\":\"Community\",\"subMenu\":[{\"keyCode\":70,\"key\":\"F\",\"label\":\"Friends\"}]},"
                "\"System\":{\"label\":\"System\",\"subMenu\":[{\"keyCode\":27,\"key\":\"ESC\",\"label\":\"System\"}]}}]");
        m_main->open = 1;
        feed_main(L);
        feed_skills(L);
        feed_item_hotkeys(L);
    }
    /* chat.swf is a symbol library; the UI loader attaches "Chat" (layer plays it). */
    if (chat->g) {
        invokef(L, MU_GFX_CHAT, "_level0", "attachMovie", "[\"Chat\",\"mc\",10]");
        L->api.advance(chat->g, 0.0);
        invokef(L, MU_GFX_CHAT, "_level0.mc", "onFileLoad", "[]");
        if (chat->path[0]) {
            invokef(L, MU_GFX_CHAT, chat->path, "InitData",
                    "[{\"MaxInputSize\":\"60\",\"MaxUsetNameSize\":\"10\",\"strNormal\":\"All\",\"strParty\":\"Party\","
                    "\"strGuild\":\"Guild\",\"strGens\":\"Gens\",\"strWhisper\":\"Whisper\",\"strSystem\":\"System\","
                    "\"strBlock\":\"Block\",\"typeFormatWHISPER\":\"W\",\"typeFormatPARTY\":\"P\","
                    "\"typeFormatGUILD\":\"G\",\"typeFormatUNION\":\"U\",\"typeFormatGENS\":\"Gens\"}]");
            invokef(L, MU_GFX_CHAT, chat->path, "CloseEditText", "[]");
            chat->open = 1;
        }
    }
    movie *inv = &L->mv[MU_GFX_INVENTORY];
    if (inv->path[0]) {
        invokef(L, MU_GFX_INVENTORY, inv->path, "InitText",
                "[{\"Title\":\"Inventory\",\"Zen\":\"\",\"Ruud\":\"\",\"Artifact\":\"Artifact\","
                "\"PrivateStore\":\"Personal S\",\"ExtensionBag\":\"Expanded\",\"Repair\":\"Repair\","
                "\"Divide\":\"Divide\",\"Disassemble\":\"Disassemb\",\"Bundle\":\"Bundle\"}]");
        invokef(L, MU_GFX_INVENTORY, inv->path, "SetAlign", "[4]");   /* right, as the live window */
        zen_text(L);
        slot_gap(L);
        slot_states(L);
    }
    if (L->mv[MU_GFX_CHARACTER].path[0])
        invokef(L, MU_GFX_CHARACTER, L->mv[MU_GFX_CHARACTER].path, "InitText",
                "[{\"StatButton\":\"Stats\",\"PentagramButton\":\"Pentagram\",\"MasterSkillTree\":\"Master\","
                "\"SkillTree4th\":\"4th Tree\",\"SkillTree5th\":\"5th Tree\",\"DetailInfo\":\"Details\"}]");
    window_sizes(L);
    for (int m = MU_GFX_INVENTORY; m <= MU_GFX_CHARACTER; m++)
        if (L->mv[m].path[0] && m != MU_GFX_TOOLTIP)
            invokef(L, m, L->mv[m].path, "SetVisible", "[false]");
    hide_tooltip(L);
    L->order[L->norder++] = MU_GFX_INVENTORY;
    L->order[L->norder++] = MU_GFX_CHARACTER;
}

static void demo_hero(mu_gfx_hero *h)
{
    memset(h, 0, sizeof *h);
    snprintf(h->name, sizeof h->name, "Nighty");
    snprintf(h->class_name, sizeof h->class_name, "Blade Knight");
    h->level = 400;
    h->master_level = 120;
    h->points = 5;
    h->max_hp = 117918;
    h->max_mp = 18526;
    h->max_sd = 24000;
    h->max_ag = 9000;
    h->hp = h->max_hp * 3 / 4;
    h->mp = h->max_mp / 2;
    h->sd = h->max_sd;
    h->ag = h->max_ag;
    h->exp = 1234567890;
    h->exp_max = 2000000000;
    h->strength = 1250;
    h->agility = 800;
    h->vitality = 650;
    h->energy = 300;
    h->command = 0;
    h->zen = 182790999;
    h->ruud = 411067;
}

mu_gfx_layer *mu_gfx_layer_open(const mu_gfx_layer_config *c, char *error, size_t cap)
{
    mu_gfx_layer *L = calloc(1, sizeof *L);
    if (!L) {
        snprintf(error, cap, "out of memory");
        return NULL;
    }
    L->cfg = *c;
    L->px_w = c->width > 0 ? c->width : 1280;
    L->px_h = c->height > 0 ? c->height : 800;
    L->scale = c->scale > 0 ? c->scale : 1.0;
    L->w = (int32_t)lround(L->px_w / L->scale);
    L->h = (int32_t)lround(L->px_h / L->scale);
    L->held = L->hover = L->capture = -1;
    L->potions = 25;
    demo_hero(&L->hero);
    memset(&L->shown, 0xff, sizeof L->shown);   /* everything differs: first feed sends all */
    L->shown.name[0] = 0;
    if (api_load(&L->api, c->lib_path, error, cap)) {
        mu_gfx_layer_close(L);
        return NULL;
    }
    L->shared = c->shared;
#if defined(MU_GFX_NO_GL) || !defined(__APPLE__)
    L->shared = 0;
#endif
    mu_grid_construct(&L->grid);
    mu_grid_init(&L->grid, 1, 0, 0, 0, 8, 8, 0);   /* 0x00ab7277(1, 8, 8, 1): inventory page */
    for (int m = 0; m < MU_GFX_MOVIES; m++)
        if (open_movie(L, m, error, cap)) {
            if (L->shared && m == 0) {   /* no IOSurface: fall back to read-back */
                L->shared = 0;
                if (!open_movie(L, m, error, cap))
                    continue;
            }
            mu_gfx_layer_close(L);
            return NULL;
        }
    init_movies(L);
    if (!L->mv[MU_GFX_MAIN].path[0] || !L->mv[MU_GFX_INVENTORY].path[0]) {
        snprintf(error, cap, "movies did not report their paths (main '%s', inventory '%s'): convert them with "
                             "gfxconvert.py --bridge --var _root.isClient=true", L->mv[MU_GFX_MAIN].path,
                 L->mv[MU_GFX_INVENTORY].path);
        mu_gfx_layer_close(L);
        return NULL;
    }
    return L;
}

void mu_gfx_layer_close(mu_gfx_layer *L)
{
    if (!L)
        return;
    for (int m = 0; m < MU_GFX_MOVIES; m++) {
        movie *mv = &L->mv[m];
#ifndef MU_GFX_NO_GL
        if (mv->tex)
            glDeleteTextures(1, &mv->tex);
#endif
        if (mv->g)
            L->api.close(mv->g);
        free(mv->rgba);
    }
    if (L->api.dl)
        dlclose(L->api.dl);
    free(L);
}

void mu_gfx_layer_resize(mu_gfx_layer *L, int32_t w, int32_t h)
{
    if (!L || w <= 0 || h <= 0 || (w == L->px_w && h == L->px_h))
        return;
    L->px_w = w;
    L->px_h = h;
    w = L->w = (int32_t)lround(w / L->scale);
    h = L->h = (int32_t)lround(h / L->scale);
    for (int m = 0; m < MU_GFX_MOVIES; m++)
        if (L->mv[m].g) {
            L->api.set_view(L->mv[m].g, w, h, 0, 0, 0, 0, L->scale);
            L->mv[m].view[0] = L->mv[m].view[1] = 0;
            L->mv[m].view[2] = w;
            L->mv[m].view[3] = h;
            L->mv[m].view_dirty = 1;
            L->mv[m].frame_valid = 0;
        }
    window_sizes(L);
}

void mu_gfx_layer_set_hero(mu_gfx_layer *L, const mu_gfx_hero *h)
{
    if (L && h)
        L->hero = *h;
}

const mu_gfx_hero *mu_gfx_layer_hero(const mu_gfx_layer *L)
{
    return L ? &L->hero : NULL;
}

/* ---- views: each player sized to its window ----------------------------------------------------- */

static int visible(const mu_gfx_layer *L, int m)
{
    const movie *mv = &L->mv[m];
    return mv->g && (mv->open || (m == MU_GFX_TOOLTIP && mv->open));
}

static void update_view(mu_gfx_layer *L, int m)
{
    movie *mv = &L->mv[m];
    if (!mv->g || L->cfg.full_stage || !visible(L, m))
        return;
    if (!mv->view_dirty && L->time_ms < mv->next_bounds_ms)
        return;
    mv->view_dirty = 0;
    mv->next_bounds_ms = L->time_ms + 250.0;
    /* The content bounds of the movie's root in stage pixels. */
    const char *r = L->api.invoke(mv->g, "_level0", "getBounds", "[]");
    if (!r)
        return;
    double x0 = json_field(r, "xMin", 0), x1 = json_field(r, "xMax", L->w);
    double y0 = json_field(r, "yMin", 0), y1 = json_field(r, "yMax", L->h);
    if (!(x1 > x0) || !(y1 > y0) || x1 - x0 > 1e6)
        x0 = 0, y0 = 0, x1 = L->w, y1 = L->h;
    /* Pad and round outwards to 32 pixels so small changes keep the surface. */
    int32_t ix0 = (int32_t)floor((x0 - 4) / 32) * 32, iy0 = (int32_t)floor((y0 - 4) / 32) * 32;
    int32_t ix1 = (int32_t)ceil((x1 + 4) / 32) * 32, iy1 = (int32_t)ceil((y1 + 4) / 32) * 32;
    if (ix0 < 0) ix0 = 0;
    if (iy0 < 0) iy0 = 0;
    if (ix1 > L->w) ix1 = L->w;
    if (iy1 > L->h) iy1 = L->h;
    if (ix1 - ix0 < 8 || iy1 - iy0 < 8)
        return;
    int32_t nv[4] = {ix0, iy0, ix1 - ix0, iy1 - iy0};
    if (!memcmp(nv, mv->view, sizeof nv))
        return;
    memcpy(mv->view, nv, sizeof nv);
    L->api.set_view(mv->g, L->w, L->h, nv[0], nv[1], nv[2], nv[3], L->scale);
    mv->frame_valid = 0;
    L->view_changes++;
    logf_(L, "%s view %d,%d %dx%d", mv->file, nv[0], nv[1], nv[2], nv[3]);
}

void mu_gfx_layer_view(const mu_gfx_layer *L, int m, int32_t rect[4])
{
    if (L && m >= 0 && m < MU_GFX_MOVIES)
        memcpy(rect, L->mv[m].view, 4 * sizeof rect[0]);
}

/* ---- input ---------------------------------------------------------------------------------------- */

/* Interactive movies from the top: windows by z-order, then chat, then the bar. */
static int stacking(const mu_gfx_layer *L, int out[MU_GFX_MOVIES])
{
    int n = 0;
    for (int i = L->norder - 1; i >= 0; i--)
        if (visible(L, L->order[i]))
            out[n++] = L->order[i];
    if (visible(L, MU_GFX_CHAT))
        out[n++] = MU_GFX_CHAT;
    if (visible(L, MU_GFX_MAIN))
        out[n++] = MU_GFX_MAIN;
    return n;
}

/* Window point (x, y) -> the movie's viewport pixels; 1 when inside its view. */
static int local(const mu_gfx_layer *L, const movie *mv, double x, double y, double *lx, double *ly)
{
    double px = x - mv->view[0], py = y - mv->view[1];
    *lx = px * L->scale;
    *ly = py * L->scale;
    return px >= 0 && py >= 0 && px < mv->view[2] && py < mv->view[3];
}

int mu_gfx_layer_mouse(mu_gfx_layer *L, int kind, int button, double x, double y)
{
    if (!L)
        return 0;
    int stack[MU_GFX_MOVIES], n = stacking(L, stack);
    double lx, ly;
    x /= L->scale;      /* window pixels -> stage points */
    y /= L->scale;
    if (kind == 0) {
        L->mouse_x = x;
        L->mouse_y = y;
        int over = 0;
        for (int i = 0; i < n; i++) {
            movie *mv = &L->mv[stack[i]];
            int inside = local(L, mv, x, y, &lx, &ly);
            /* Every visible movie sees the move (roll-outs), outside ones
             * at their own coordinates. */
            L->api.mouse(mv->g, 0, 0, lx, ly);
            if (inside && !over && L->api.hit_test(mv->g, lx, ly))
                over = 1;
        }
        return over || L->capture >= 0;
    }
    if (kind == 2) {   /* release: to the movie that took the press */
        int m = L->capture;
        L->capture = -1;
        if (m < 0)
            return 0;
        local(L, &L->mv[m], x, y, &lx, &ly);
        L->api.mouse(L->mv[m].g, 2, button, lx, ly);
        L->mv[m].view_dirty = 1;
        return 1;
    }
    for (int i = 0; i < n; i++) {
        movie *mv = &L->mv[stack[i]];
        if (!local(L, mv, x, y, &lx, &ly) || !L->api.hit_test(mv->g, lx, ly))
            continue;
        if (kind == 1) {
            L->capture = stack[i];
            if (stack[i] == MU_GFX_INVENTORY || stack[i] == MU_GFX_CHARACTER)
                raise_window(L, stack[i]);
        }
        L->api.mouse(mv->g, kind, button, lx, ly);
        return 1;
    }
    if (kind == 1 && L->held >= 0) {
        /* A held item released over the world: the client drops it on the
         * ground (server request, out of scope); the layer puts it back. */
        item *it = &L->items[L->held];
        int col, row;
        if (mu_grid_find_free(&L->grid, it->grid.width, it->grid.height, &col, &row)) {
            mu_grid_place(&L->grid, col, row, &it->grid);
            L->held = -1;
            slot_states(L);
            logf_(L, "game: item %u returned to the inventory (dropping is a server action)", it->grid.id);
        }
        return 1;
    }
    return 0;
}

int mu_gfx_layer_cursor(const mu_gfx_layer *L)
{
    if (!L)
        return 0;
    int stack[MU_GFX_MOVIES], n = stacking(L, stack);
    for (int i = 0; i < n; i++) {
        const movie *mv = &L->mv[stack[i]];
        double lx, ly;
        if (local(L, mv, L->mouse_x, L->mouse_y, &lx, &ly) && L->api.hit_test(mv->g, lx, ly))
            return L->api.cursor(mv->g);
    }
    return 0;
}

int mu_gfx_layer_text_active(const mu_gfx_layer *L)
{
    return L && L->chat_edit;
}

int mu_gfx_layer_key(mu_gfx_layer *L, int down, int vk, uint32_t codepoint, int mods)
{
    if (!L)
        return 0;
    movie *chat = &L->mv[MU_GFX_CHAT], *main = &L->mv[MU_GFX_MAIN];
    if (L->chat_edit && chat->g) {
        L->main_down_vk = 0;
        if (down && vk == 13) {
            chat_submit(L);
            return 1;
        }
        if (down && vk == 27) {
            chat_open(L, 0);
            return 1;
        }
        L->api.key(chat->g, down ? 0 : 1, vk, codepoint, mods);
        return 1;
    }
    if (vk == 13 && chat->g && chat->path[0]) {
        L->main_down_vk = 0;
        if (down)
            chat_open(L, 1);
        return 1;
    }
    if (!main->g)
        return 0;
    /* The bar's own Key listeners turn keys into onHotKey (Main.onKeyUp)
     * and onSelectSkill (SkillHotKeyPage.onKeyDown); keys they use belong
     * to the interface. */
    L->key_used = 0;
    L->api.key(main->g, down ? 0 : 1, vk, codepoint, mods);
    /* Frame.Main.onKeyUp is a clip key handler (it fires for the clip with
     * keyboard focus, which the client's GFx manager gives the bar); the
     * layer calls it after the key reached the player, so Key.getCode()
     * reads this key (layer choice). */
    if (down)
        L->main_down_vk = vk;
    else if (main->path[0] && L->main_down_vk == vk)
        invokef(L, MU_GFX_MAIN, main->path, "onKeyUp", "[]");
    int used = L->key_used;
    static const int UI_KEYS[] = {'I', 'V', 'C', 'X', 'K', 'T', 'F', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9'};
    for (size_t i = 0; i < sizeof UI_KEYS / sizeof UI_KEYS[0]; i++)
        if (vk == UI_KEYS[i])
            used = 1;
    if (vk == 27 && (L->mv[MU_GFX_INVENTORY].open || L->mv[MU_GFX_CHARACTER].open))
        used = 1;
    return used;
}

int mu_gfx_layer_text(mu_gfx_layer *L, const char *utf8)
{
    if (!L || !L->chat_edit || !L->mv[MU_GFX_CHAT].g)
        return 0;
    L->api.text(L->mv[MU_GFX_CHAT].g, utf8);
    return 1;
}

/* ---- time --------------------------------------------------------------------------------------- */

static void demo_step(mu_gfx_layer *L)
{
    double t = L->time_ms / 1000.0;
    mu_gfx_hero *h = &L->hero;
    h->hp = (int32_t)(h->max_hp * (0.55 + 0.45 * sin(t * 0.9)));
    h->mp = (int32_t)(h->max_mp * (0.5 + 0.5 * cos(t * 0.6)));
    h->sd = (int32_t)(h->max_sd * (0.5 + 0.5 * sin(t * 1.3 + 1.0)));
    if (h->ag < h->max_ag)
        h->ag += 9;
    h->exp += 12345;
    if (h->exp >= h->exp_max)
        h->exp = 0;
}

void mu_gfx_layer_advance(mu_gfx_layer *L, double dt)
{
    if (!L)
        return;
    L->time_ms += dt;
    if (L->next_step_ms <= 0)
        L->next_step_ms = L->time_ms;
    while (L->time_ms >= L->next_step_ms) {   /* the client's 40 ms logic step */
        L->next_step_ms += 40.0;
        L->steps++;
        if (L->cfg.demo)
            demo_step(L);
        feed_main(L);
        if (L->hero_dirty_char && L->mv[MU_GFX_CHARACTER].open)
            feed_character(L);
    }
    for (int m = 0; m < MU_GFX_MOVIES; m++)
        if (L->mv[m].g && (visible(L, m) || m == MU_GFX_CHAT || m == MU_GFX_TOOLTIP))
            L->api.advance(L->mv[m].g, dt);
    /* The chat view fills itself with test lines once its CLIK components
     * initialise (ChatView.testChatType); clear them, then greet (layer choice). */
    if (!L->chat_ready && L->time_ms >= 200 && L->mv[MU_GFX_CHAT].path[0]) {
        L->chat_ready = 1;
        invokef(L, MU_GFX_CHAT, L->mv[MU_GFX_CHAT].path, "ClearAllChatHistory", "[]");
        mu_gfx_layer_chat(L, 3, "", "Welcome to MU (native client, offline demo).");
    }
}

/* ---- rendering ------------------------------------------------------------------------------------ */

static void render_readback(mu_gfx_layer *L, movie *mv, int m)
{
    int w = 0, h = 0;
    L->api.size(mv->g, &w, &h);
    size_t need = (size_t)w * (size_t)h * 4;
    if (need > mv->rgba_cap) {
        free(mv->rgba);
        mv->rgba = malloc(need);
        mv->rgba_cap = mv->rgba ? need : 0;
    }
    if (mv->rgba && L->api.render(mv->g, mv->rgba, need) == 0) {
        MuGfxStats st;
        L->api.stats(mv->g, &st);
        L->renders[m]++;
        L->render_ms[m] += st.last_render_ms;
        L->capture_ms[m] += st.last_capture_ms;
        mv->frame_valid = 1;
        mv->needs_upload = 1;
    }
}

static void render_movies(mu_gfx_layer *L, int force_readback)
{
    int submitted = 0;
    double t_submit = now_ms();
    for (int m = 0; m < MU_GFX_MOVIES; m++) {
        movie *mv = &L->mv[m];
        if (!visible(L, m))
            continue;
        update_view(L, m);
        if (mv->frame_valid && !L->api.needs_render(mv->g))
            continue;
        if (L->shared && !force_readback) {
            /* Submit every changed movie, then wait once for the GPU (one
             * queue) before the GL compositor samples the surfaces. */
            if (L->api.render_shared(mv->g, 0) == 0) {
                MuGfxStats st;
                L->api.stats(mv->g, &st);
                L->renders[m]++;
                L->render_ms[m] += st.last_render_ms;
                mv->frame_valid = 1;
                submitted |= 1 << m;
            }
        } else {
            render_readback(L, mv, m);
        }
    }
    if (submitted) {
        double t = now_ms();
        L->api.gpu_wait();
        double wait = now_ms() - t;
        (void)t_submit;
        L->gpu_wait_ms += wait;
        L->gpu_waits++;
    }
}

void mu_gfx_layer_render(mu_gfx_layer *L)
{
    if (L)
        render_movies(L, 0);
}

/* Item stand-ins over the inventory, placed by the reconstructed slot pass. */
typedef struct rect_list { float r[MAX_ITEMS + 1][4]; int item[MAX_ITEMS + 1]; int n; mu_gfx_layer *L; } rect_list;

static void emit_rect(void *user, const mu_slot_call *call)
{
    rect_list *R = user;
    mu_gfx_layer *L = R->L;
    if (R->n >= MAX_ITEMS)
        return;
    /* 640 x 480 units back to window pixels (0x0184a18f, top-left origin here). */
    float *r = R->r[R->n];
    r[0] = call->x / mu_gfx_rate_x(L->w);
    r[1] = call->y / mu_gfx_rate_y(L->h);
    r[2] = call->w / mu_gfx_rate_x(L->w);
    r[3] = call->h / mu_gfx_rate_y(L->h);
    R->item[R->n++] = (int)((const item *)call->item - L->items);
}

static void item_rects(mu_gfx_layer *L, rect_list *R)
{
    R->n = 0;
    R->L = L;
    if (!L->have_slot || !L->mv[MU_GFX_INVENTORY].open)
        return;
    mu_slot_page page = {&L->grid, L->slot_x, L->slot_y, L->slot_w, L->slot_h, L->gap_x, L->gap_y};
    mu_slot_frame frame = {1, MU_ALIGN_TOP_LEFT, L->win_x, L->win_y, 1.0f, 1.0f, &page, 1, 1};
    mu_slot_pass(&frame, L->w, L->h, mu_gfx_rate_x(L->w), mu_gfx_rate_y(L->h), NULL, emit_rect, R);
}

static int held_rect(const mu_gfx_layer *L, float r[4])
{
    if (L->held < 0)
        return 0;
    const item *it = &L->items[L->held];
    r[2] = it->grid.width * (L->slot_w > 0 ? L->slot_w : 26);
    r[3] = it->grid.height * (L->slot_h > 0 ? L->slot_h : 26);
    r[0] = (float)L->mouse_x - r[2] / 2;
    r[1] = (float)L->mouse_y - r[3] / 2;
    return 1;
}

static void blend_px(uint8_t *dst, const uint8_t *src)
{
    unsigned a = src[3];
    for (int c = 0; c < 3; c++)
        dst[c] = (uint8_t)((src[c] * a + dst[c] * (255 - a)) / 255);
}

static void fill_cpu(uint8_t *rgba, int32_t W, int32_t H, const float rp[4], const float rgb[3], double scale)
{
    const float r[4] = {rp[0] * (float)scale, rp[1] * (float)scale, rp[2] * (float)scale, rp[3] * (float)scale};
    for (int y = (int)r[1] + 2; y < (int)(r[1] + r[3]) - 2; y++)
        for (int x = (int)r[0] + 2; x < (int)(r[0] + r[2]) - 2; x++) {
            if (x < 0 || y < 0 || x >= W || y >= H)
                continue;
            int edge = y < (int)r[1] + 4 || x < (int)r[0] + 4 || y >= (int)(r[1] + r[3]) - 4 ||
                       x >= (int)(r[0] + r[2]) - 4;
            uint8_t src[4] = {(uint8_t)(255 * rgb[0] * (edge ? 0.6f : 1)), (uint8_t)(255 * rgb[1] * (edge ? 0.6f : 1)),
                              (uint8_t)(255 * rgb[2] * (edge ? 0.6f : 1)), 200};
            blend_px(rgba + ((size_t)y * (size_t)W + (size_t)x) * 4, src);
        }
}

/* Composite order: bar, chat, windows by z-order (items after the
 * inventory, as the GFx manager's per-window item pass 0x00abfcca), the
 * tooltip, the held item. */
static int draw_order(const mu_gfx_layer *L, int out[MU_GFX_MOVIES])
{
    int n = 0;
    if (visible(L, MU_GFX_MAIN)) out[n++] = MU_GFX_MAIN;
    if (visible(L, MU_GFX_CHAT)) out[n++] = MU_GFX_CHAT;
    for (int i = 0; i < L->norder; i++)
        if (visible(L, L->order[i])) out[n++] = L->order[i];
    if (visible(L, MU_GFX_TOOLTIP)) out[n++] = MU_GFX_TOOLTIP;
    return n;
}

void mu_gfx_layer_composite(mu_gfx_layer *L, uint8_t *rgba, int32_t W, int32_t H)
{
    if (!L || !rgba)
        return;
    render_movies(L, 1);
    int order[MU_GFX_MOVIES], n = draw_order(L, order);
    rect_list R;
    for (int k = 0; k < n; k++) {
        movie *mv = &L->mv[order[k]];
        if (!mv->frame_valid || !mv->rgba) {
            render_readback(L, mv, order[k]);
            if (!mv->rgba)
                continue;
        }
        int w = 0, h = 0;
        L->api.size(mv->g, &w, &h);
        int ox = (int)lround(mv->view[0] * L->scale), oy = (int)lround(mv->view[1] * L->scale);
        for (int y = 0; y < h; y++) {
            int wy = oy + y;
            if (wy < 0 || wy >= H)
                continue;
            for (int x = 0; x < w; x++) {
                int wx = ox + x;
                const uint8_t *src = mv->rgba + ((size_t)y * (size_t)w + (size_t)x) * 4;
                if (wx >= 0 && wx < W && src[3])
                    blend_px(rgba + ((size_t)wy * (size_t)W + (size_t)wx) * 4, src);
            }
        }
        if (order[k] == MU_GFX_INVENTORY) {
            item_rects(L, &R);
            for (int i = 0; i < R.n; i++)
                fill_cpu(rgba, W, H, R.r[i], L->items[R.item[i]].rgb, L->scale);
        }
    }
    float hr[4];
    if (held_rect(L, hr))
        fill_cpu(rgba, W, H, hr, L->items[L->held].rgb, L->scale);
}

#ifndef MU_GFX_NO_GL
static void quad(float x, float y, float w, float h, float s1, float t1)
{
    glBegin(GL_QUADS);
    glTexCoord2f(0, 0); glVertex2f(x, y);
    glTexCoord2f(s1, 0); glVertex2f(x + w, y);
    glTexCoord2f(s1, t1); glVertex2f(x + w, y + h);
    glTexCoord2f(0, t1); glVertex2f(x, y + h);
    glEnd();
}

static void fill_gl(const float rp[4], const float rgb[3], double scale)
{
    const float r[4] = {rp[0] * (float)scale, rp[1] * (float)scale, rp[2] * (float)scale, rp[3] * (float)scale};
    glColor4f(rgb[0], rgb[1], rgb[2], 0.8f);
    glBegin(GL_QUADS);
    glVertex2f(r[0] + 2, r[1] + 2); glVertex2f(r[0] + r[2] - 2, r[1] + 2);
    glVertex2f(r[0] + r[2] - 2, r[1] + r[3] - 2); glVertex2f(r[0] + 2, r[1] + r[3] - 2);
    glEnd();
}

static void draw_movie_gl(mu_gfx_layer *L, movie *mv, int m)
{
    if (!mv->frame_valid)
        return;
    float x = (float)(mv->view[0] * L->scale), y = (float)(mv->view[1] * L->scale);
#ifdef __APPLE__
    if (L->shared) {
        int w = 0, h = 0;
        uint32_t seed = 0;
        IOSurfaceRef surface = (IOSurfaceRef)L->api.iosurface(mv->g, &w, &h, &seed);
        if (!surface)
            return;
        if (!mv->tex)
            glGenTextures(1, &mv->tex);
        glBindTexture(GL_TEXTURE_RECTANGLE_ARB, mv->tex);
        if (seed != mv->seed) {
            CGLTexImageIOSurface2D(CGLGetCurrentContext(), GL_TEXTURE_RECTANGLE_ARB, GL_RGBA8, w, h, GL_BGRA,
                                   GL_UNSIGNED_INT_8_8_8_8_REV, surface, 0);
            glTexParameteri(GL_TEXTURE_RECTANGLE_ARB, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
            glTexParameteri(GL_TEXTURE_RECTANGLE_ARB, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
            mv->seed = seed;
            mv->tex_w = w;
            mv->tex_h = h;
        }
        glEnable(GL_TEXTURE_RECTANGLE_ARB);
        glBlendFunc(GL_ONE, GL_ONE_MINUS_SRC_ALPHA);   /* premultiplied */
        glColor4f(1, 1, 1, 1);
        quad(x, y, (float)w, (float)h, (float)w, (float)h);
        glDisable(GL_TEXTURE_RECTANGLE_ARB);
        glBindTexture(GL_TEXTURE_RECTANGLE_ARB, 0);
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
        return;
    }
#endif
    int w = 0, h = 0;
    L->api.size(mv->g, &w, &h);
    if (!mv->tex)
        glGenTextures(1, &mv->tex);
    glBindTexture(GL_TEXTURE_2D, mv->tex);
    if (mv->needs_upload && mv->rgba) {
        double t = now_ms();
        if (w != mv->tex_w || h != mv->tex_h) {
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, mv->rgba);
            mv->tex_w = w;
            mv->tex_h = h;
        } else {
            glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, w, h, GL_RGBA, GL_UNSIGNED_BYTE, mv->rgba);
        }
        L->upload_ms[m] += now_ms() - t;
        mv->needs_upload = 0;
    }
    glEnable(GL_TEXTURE_2D);
    glColor4f(1, 1, 1, 1);
    quad(x, y, (float)w, (float)h, 1.0f, 1.0f);
    glDisable(GL_TEXTURE_2D);
    glBindTexture(GL_TEXTURE_2D, 0);
}
#endif

void mu_gfx_layer_draw_gl(mu_gfx_layer *L)
{
#ifndef MU_GFX_NO_GL
    if (!L)
        return;
    render_movies(L, 0);
    glPushAttrib(GL_ALL_ATTRIB_BITS);
    glMatrixMode(GL_PROJECTION);
    glPushMatrix();
    glLoadIdentity();
    glOrtho(0, L->px_w, L->px_h, 0, -1, 1);
    glMatrixMode(GL_MODELVIEW);
    glPushMatrix();
    glLoadIdentity();
    glViewport(0, 0, L->px_w, L->px_h);
    glDisable(GL_DEPTH_TEST);
    glDisable(GL_CULL_FACE);
    glDisable(GL_LIGHTING);
    glDisable(GL_ALPHA_TEST);
    glDisable(GL_FOG);
    glDisable(GL_SCISSOR_TEST);
    glDisable(GL_STENCIL_TEST);
    glDisable(GL_TEXTURE_2D);
    glBindTexture(GL_TEXTURE_2D, 0);
    glDepthMask(GL_FALSE);
    glEnable(GL_BLEND);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
    int order[MU_GFX_MOVIES], n = draw_order(L, order);
    rect_list R;
    for (int k = 0; k < n; k++) {
        draw_movie_gl(L, &L->mv[order[k]], order[k]);
        if (order[k] == MU_GFX_INVENTORY) {
            item_rects(L, &R);
            for (int i = 0; i < R.n; i++)
                fill_gl(R.r[i], L->items[R.item[i]].rgb, L->scale);
        }
    }
    float hr[4];
    if (held_rect(L, hr))
        fill_gl(hr, L->items[L->held].rgb, L->scale);
    glMatrixMode(GL_PROJECTION);
    glPopMatrix();
    glMatrixMode(GL_MODELVIEW);
    glPopMatrix();
    glPopAttrib();
#else
    (void)L;
#endif
}

/* ---- queries -------------------------------------------------------------------------------------- */

const char *mu_gfx_layer_invoke(mu_gfx_layer *L, int m, const char *path, const char *method, const char *args)
{
    if (!L || m < 0 || m >= MU_GFX_MOVIES || !L->mv[m].g)
        return NULL;
    const char *r = invokef(L, m, path ? path : L->mv[m].path, method, "%s", args ? args : "[]");
    snprintf(L->reply, sizeof L->reply, "%s", r ? r : "");
    return L->reply;
}

const char *mu_gfx_layer_path(const mu_gfx_layer *L, int m)
{
    return L && m >= 0 && m < MU_GFX_MOVIES ? L->mv[m].path : "";
}

int mu_gfx_layer_cell_center(const mu_gfx_layer *L, int32_t cell, double *x, double *y)
{
    if (!L || !L->have_slot || cell < 0 || cell >= L->grid.cols * L->grid.rows)
        return 0;
    int col = cell % L->grid.cols, row = cell / L->grid.cols;
    *x = (L->win_x + L->slot_x + (float)col * (L->slot_w + L->gap_x) + L->slot_w / 2) * L->scale;
    *y = (L->win_y + L->slot_y + (float)row * (L->slot_h + L->gap_y) + L->slot_h / 2) * L->scale;
    return 1;
}

void mu_gfx_layer_stats_get(const mu_gfx_layer *L, mu_gfx_layer_stats *out)
{
    memset(out, 0, sizeof *out);
    if (!L)
        return;
    for (int m = 0; m < MU_GFX_MOVIES; m++) {
        out->renders[m] = L->renders[m];
        out->render_ms[m] = L->render_ms[m];
        out->capture_ms[m] = L->capture_ms[m];
        out->upload_ms[m] = L->upload_ms[m];
        memcpy(out->view[m], L->mv[m].view, sizeof out->view[m]);
    }
    out->callbacks = L->callbacks;
    out->invokes = L->invokes;
    out->steps = L->steps;
    out->view_changes = L->view_changes;
    out->shared = L->shared;
    out->gpu_waits = L->gpu_waits;
    out->gpu_wait_ms = L->gpu_wait_ms;
}

int mu_gfx_layer_held(const mu_gfx_layer *L) { return L ? L->held : -1; }

int mu_gfx_layer_item_cell(const mu_gfx_layer *L, int i)
{
    if (!L || i < 0 || i >= L->nitems || i == L->held)
        return -1;
    return L->items[i].grid.row * L->grid.cols + L->items[i].grid.col;
}

int mu_gfx_layer_item_count(const mu_gfx_layer *L) { return L ? L->nitems : 0; }

const char *mu_gfx_layer_last_sent(const mu_gfx_layer *L) { return L ? L->last_sent : ""; }
