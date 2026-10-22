/* The GFx interface layer of the native client (NATIVE-GFX-002/003); see mu_gfx_layer.h.
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
 * NATIVE-GFX-003 (static readings of the client, docs/research/native-gfx3.md):
 *   - the HUD is one base movie: base.swf loads ExternalBase.swf, whose
 *     UIFrame reports onLoad; the game answers with LoadFrameFiles and the
 *     movie list of 0x00c8f05d; ASData (DataMan) gets skill.setSkillAll with
 *     {Index, Magic_Icon, Name, Delay, SkillUseType, MasteryType} (0x00c5ebaa);
 *     the main frame's handler sends InitMenuInfo (0x00c71fc2: menu ids, not
 *     key codes, GlobalText labels) and registers image0 (0x00c71f4b);
 *   - item hotkey icons: each occupied slot gets a 20 x 20 render rectangle
 *     in image0, x stepping by 32 and wrapping (0x00c552b1); the bar draws
 *     _root.getBitmap(0) flipped (Frame.mainAssets.ItemHotKey.DrawIcon);
 *   - window registry 0x00ac4a79: InventoryFrame alignment 11 (Align_Right),
 *     CharacterInfoFrame and InfoPopup 9 (none); the window creator 0x00ac9edc
 *     sends SetAlign + SetWindowSize(window size) unless the alignment is 9,
 *     and SetScale(83) below 700 pixels of height for most windows
 *     (handler +0x58 = scale / 100, used by the item pass);
 *   - menu id 1 toggles CharacterInfoFrame (0x00c714bd case 1 -> 0x00c733cf),
 *     id 14 InventoryFrame (case 14 -> 0x00c73a2f).
 * Host choices (not client facts) are marked "layer choice". */
#define _POSIX_C_SOURCE 200809L
#define _DARWIN_C_SOURCE 1
#include "mu_gfx_layer.h"
#include "../../reconstructed/social/item_options.h"

#include <dlfcn.h>
#include <math.h>
#include <stdarg.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
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
    int (*set_image)(MuGfx *, const char *, int, int, const uint8_t *, int);
    int (*resolve)(MuGfx *, const char *, char *, size_t);
    int (*ime)(MuGfx *, const char *, int, int);
    int (*set_double_buffer)(MuGfx *, int);
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
    SYM(set_image, "mugfx_set_image");
    SYM(resolve, "mugfx_resolve");
    SYM(ime, "mugfx_ime");
    SYM(set_double_buffer, "mugfx_set_double_buffer");
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
    int alias;                  /* plays inside another movie's player (base mode chat): not rendered/advanced */
    float win_x, win_y;          /* requestWindowPos, handler +0x70/+0x74 */
} movie;

typedef struct item {
    mu_grid_item grid;
    int32_t level;
    int32_t option, excellent, durability, period, set_bits, element;
    char name[64];
    float rgb[3];
    uint8_t has_data, data[15];
} item;
/* Materialize only the mutable inventory fields; all other instance bytes stay
 * verbatim. This lets jewel/repair answers and trade share one owned item. */
static void item_wire(const item *it, uint8_t out[15]) {
    if (it->has_data)
        memcpy(out, it->data, 15);
    else {
        memset(out, 0, 15);
        memset(out + 7, 255, 8);
        unsigned code = (unsigned)it->grid.code;
        out[0] = (uint8_t)code;
        out[3] = (uint8_t)((code >> 1) & 128);
        out[5] = (uint8_t)(((code >> 5) & 240) | ((code >> 13) & 1));
    }
    out[1] = (uint8_t)((out[1] & 0x84) | ((it->level & 15) << 3) | (it->option & 3));
    out[2] = (uint8_t)it->durability;
    out[3] = (uint8_t)((out[3] & 0xbf) | ((it->option & 4) << 4));
    out[5] = (uint8_t)((out[5] & 0xfd) | (it->period ? 2 : 0));
}
static void item_instance(item *it, const mu_gfx_slot_item *src) {
    it->has_data = src->has_data;
    memcpy(it->data, src->data, 15);
    it->excellent = src->excellent;
    it->set_bits = src->set_bits;
    it->element = src->has_data ? src->element : -1;
    if (src->has_data) {
        it->level = (src->data[1] >> 3) & 15;
        it->durability = src->data[2];
        it->option = (src->data[1] & 3) + ((src->data[3] & 64) >> 4);
        it->period = !!(src->data[5] & 2);
    }
}

#define SLOT_ITEMS 120          /* NpcShop / StorageInven pages: 8 x 15 */
typedef struct slot_window {
    int movie;
    const char *frame;          /* member holding isSlot0..119 */
    mu_grid grid;
    item items[SLOT_ITEMS];
    int64_t prices[SLOT_ITEMS];
    int nitems, hover, have_slot, gap_done;
    float win_x, win_y, slot_x, slot_y, slot_w, slot_h, gap_x, gap_y, scale;
} slot_window;

#define ICON_W 512              /* image0 size (layer choice: the item render passes 512.0) */
#define ICON_H 512
#define MAX_SKILLS 1024
#define MAX_CHANNELS 16

typedef struct hotkey_item {
    int32_t code, level, count;
    float render[4];            /* renderX, renderY, renderW, renderH in image0 */
} hotkey_item;

#include "mu_gfx_services_state.h"

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
    char exp_json[256];         /* NATIVE-PROGRESS-001: the client's setExpData object ("" stand-in) */
    int exp_json_dirty;
    /* inventory */
    mu_grid grid;
    item items[MAX_ITEMS];
    int nitems, held, hover;
    uint8_t trade_reserved[MAX_ITEMS];
    float win_x, win_y, slot_x, slot_y, slot_w, slot_h, gap_x, gap_y;
    int have_slot;
    /* chat */
    int chat_edit, chat_ready;
    char last_sent[256];
    void (*chat_hook)(void *user, const char *text);   /* NATIVE-NAMES-001: the sent line (bubble echo) */
    void *chat_hook_user;
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
    /* NATIVE-GFX-003 */
    int base_mode;
    struct { char name[24], path[128]; } channels[MAX_CHANNELS];
    int nchannels;
    int ui_loaded, main_inited, chat_inited, skills_sent, icons_dirty, scene_sent;
    mu_gfx_skill skills[MAX_SKILLS];
    int nskills;
    hotkey_item hotkeys[4];
    uint8_t *icon_rgba;
    float inv_scale, char_scale;   /* SetScale / 100 (handler +0x58) */
    float applied_scale[MU_GFX_MOVIES];   /* NATIVE-PERF-001: the SetScale each window has (1 = the movie's 100) */
    char compose[256];
    int composing;
    int in_callback;
    char map_name[64];
    int map_x, map_y, map_sent;
    /* NATIVE-NPC-001 */
    slot_window swin[3];        /* NpcShop, StorageInven */
    struct {
        char title[96], text[4096], pages[16][1024], options[13][96];
        int npages, page, noptions, hide_contribute, wrapped;
    } dlg;
    char npc_last[160];
    int64_t vault_zen;
    /* NATIVE-LANG-002 */
    mu_gfx_buff buffs[64];
    int nbuffs, buffs_sent;
    mu_gfx_char_row *char_rows;
    int nchar_rows;
    /* NATIVE-SKILL-001 */
    mu_gfx_skill_host skill;
    int have_skill_host;
    struct {
        float win_x, win_y, slot_w, slot_h, slots[20][2], stamp_offset[2];
        int have_slot[20], drag_from, page, select_page, inited, saved;
        char last[160];
    } stamp;
    mu_gfx_social_hooks socialh;
    mu_gfx_item_draw trade_items[64];
    int trade_nitems;
    struct { int group, pending, outcome, source, target; double due;
        int origin[SLOT_ITEMS]; mu_mix_quote quote; } mix;
    struct item_services services;
    mu_gfx_map_hooks maph;   /* NATIVE-MAP-001 */
};

static const char *const FILES[MU_GFX_MOVIES] = {"main", "InventoryFrame", "InfoPopup", "CharacterInfoFrame", "chat",
                                                 "NpcDialogue", "NpcShop", "StorageInven", "NpcQuestProgress",
                                                 "MyQuestInfo", "SkillInfoPopup", "SkillStampFrame", "MoveCommand",
                                                 "MasterSkillTree", "SkillTree4th", "SkillTree5th",
                                                 "winQuestSummary", "QuestProgressInfo", "NpcJobChangeQuest", "winParty", "Trade", "FriendMenu", "FriendWindow", "MixGoblinSel", "MixInventoryFrame", "PersonalShopProductList", "PersonalShopRegister", "PersonalShopPurchase",
                                                 "winOption", "winSystemMenu"};

static int service_reserved(const mu_gfx_layer *L,int index);
static int service_inventory(mu_gfx_layer *L,int cell);
static void service_step(mu_gfx_layer *L);
static int service_draws(mu_gfx_layer *L,int m,mu_gfx_item_draw *out,int max);
static void service_call(movie *mv,const char *name,const char *args,const double *v,int n);
static void service_tooltip(mu_gfx_layer *L,item *it,char *html,size_t cap);
static int inventory_busy(const mu_gfx_layer *L) { return L->mix.pending || L->services.pending; }
static int item_reserved(const mu_gfx_layer *L,int i) { return L->trade_reserved[i] || service_reserved(L,i); }

/* NATIVE-NPC-001 (section "NPC windows" below) */
static const char *npc_call(movie *mv, const char *name, const char *args, const double *v, int n);
static int npc_inventory_r(mu_gfx_layer *L, int index);
static mu_mix_item mix_snapshot(const item *it);
static void mix_refresh(mu_gfx_layer *L);
static void mix_step(mu_gfx_layer *L);
static int mix_jewel(mu_gfx_layer *L, int target);
static int mix_return(mu_gfx_layer *L);
static int mix_free_slot(mu_gfx_layer *L);
static void swin_init(mu_gfx_layer *L);
static void swin_composite(mu_gfx_layer *L, int m, uint8_t *rgba, int32_t W, int32_t H);
/* NATIVE-LANG-002 */
static void swin_show_tooltip(mu_gfx_layer *L, slot_window *sw, int cell);
static int is_bufflist(const char *name);
static void bufflist_event(mu_gfx_layer *L, const char *event, const char *args);
/* NATIVE-SKILL-001 (section "skills" below) */
static const char *skill_call(movie *mv, const char *name, const char *args, const double *v, int n);
static void skill_main_event(mu_gfx_layer *L, movie *mv, const char *event, const char *args);
static void skill_feed(mu_gfx_layer *L);
static void skill_window_shown(mu_gfx_layer *L, int m, int open);
static void skill_init_window(mu_gfx_layer *L);
#ifndef MU_GFX_NO_GL
static void skill_draw_gl(mu_gfx_layer *L);
#endif
static void skill_composite(mu_gfx_layer *L, uint8_t *rgba, int32_t W, int32_t H);

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

/* json_string with the escapes decoded (\n, \t, \", \; \uXXXX below 0x80 as ASCII, else '?'). */
static int json_string_decoded(const char *s, int index, char *out, size_t cap)
{
    int n = 0, depth = 0;
    for (const char *p = s; *p; p++) {
        if (*p == '{' || *p == '[') { depth++; continue; }
        if (*p == '}' || *p == ']') { depth--; continue; }
        if (*p != '"')
            continue;
        const char *q = p + 1;
        size_t o = 0;
        int take = depth == 1 && n++ == index;
        while (*q && *q != '"') {
            char c = *q;
            if (c == '\\' && q[1]) {
                q++;
                c = *q == 'n' ? '\n' : *q == 't' ? '\t' : *q == 'r' ? '\r' : *q;
                if (*q == 'u' && q[1] && q[2] && q[3] && q[4]) {
                    char hex[5] = {q[1], q[2], q[3], q[4], 0};
                    long u = strtol(hex, NULL, 16);
                    c = u > 0 && u < 0x80 ? (char)u : '?';
                    q += 4;
                }
            }
            if (take && o + 1 < cap)
                out[o++] = c;
            q++;
        }
        if (take) {
            out[o] = 0;
            return 1;
        }
        p = q;
    }
    return 0;
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

/* GlobalText[index] from the host (NATIVE-LANG-001) as a JSON literal, or
 * the stand-in.  The client's strings are ANSI: bytes outside printable
 * ASCII become '?' so the JSON stays valid UTF-8. */
static const char *gtext(const mu_gfx_layer *L, int32_t index, const char *fallback)
{
    const char *s = L->cfg.text && index >= 0 ? L->cfg.text(L->cfg.text_user, index) : NULL;
    return s ? s : fallback;
}

void mu_gfx_layer_social_notice(mu_gfx_layer *L, int32_t text_id, const char *fallback) {
    const char *s = gtext(L, text_id, fallback);
    if (strchr(s, '%'))
        s = fallback; /* This notice has no formatter arguments. */
    char clean[512];
    size_t n = 0;
    for (; *s && n + 1 < sizeof clean; s++)
        clean[n++] = (unsigned char)*s >= 32 && (unsigned char)*s < 127 ? *s : '?';
    clean[n] = 0;
    mu_gfx_layer_chat(L, 3, "", clean);
}
static void gt_quote(const mu_gfx_layer *L, char *out, size_t cap, int32_t index, const char *fallback)
{
    char clean[512];
    const char *s = gtext(L, index, fallback);
    size_t n = 0;
    for (; s && *s && n + 1 < sizeof clean; s++)
        clean[n++] = ((unsigned char)*s >= 0x20 && (unsigned char)*s < 0x7f) ? *s : '?';
    clean[n] = 0;
    json_quote(out, cap, clean);
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

/* ---- HUD channels (base mode) ----------------------------------------------------- */

static void set_channel(mu_gfx_layer *L, const char *name, const char *path)
{
    for (int i = 0; i < L->nchannels; i++)
        if (!strcmp(L->channels[i].name, name)) {
            snprintf(L->channels[i].path, sizeof L->channels[i].path, "%s", path);
            return;
        }
    if (L->nchannels < MAX_CHANNELS) {
        snprintf(L->channels[L->nchannels].name, sizeof L->channels[0].name, "%s", name);
        snprintf(L->channels[L->nchannels].path, sizeof L->channels[0].path, "%s", path);
        L->nchannels++;
    }
}

static const char *channel(const mu_gfx_layer *L, const char *name)
{
    for (int i = 0; i < L->nchannels; i++)
        if (!strcmp(L->channels[i].name, name))
            return L->channels[i].path;
    return "";
}

/* ---- game -> movie --------------------------------------------------------------- */

static const char *invokef(mu_gfx_layer *L, int m, const char *path, const char *method, const char *fmt, ...)
{
    movie *mv = &L->mv[m];
    if (!mv->g || !path || !path[0])
        return NULL;
    va_list ap;
    va_start(ap, fmt);
    int len = vsnprintf(NULL, 0, fmt, ap);
    va_end(ap);
    if (len < 0)
        return NULL;
    char *args = malloc((size_t)len + 1);
    if (!args)
        return NULL;
    va_start(ap, fmt);
    vsnprintf(args, (size_t)len + 1, fmt, ap);
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
    for (int i = 0; i < L->grid.cols * L->grid.rows; i++) {
        uint32_t id = L->grid.cells[i];
        int occupied = id && !(id <= MAX_ITEMS && L->trade_reserved[id - 1]);
        n += (size_t)snprintf(list + n, sizeof list - n, "%s%d", i ? "," : "", occupied ? 2 : 1);
    }
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
    if (L->exp_json[0] && L->exp_json_dirty) {   /* NATIVE-PROGRESS-001: the client's own object */
        char path[128];
        snprintf(path, sizeof path, "%s.mcExpBar", mv->path);
        invokef(L, MU_GFX_MAIN, path, "setExpData", "[%s]", L->exp_json);
        L->exp_json_dirty = 0;
    } else if (!L->exp_json[0] && (h->exp != s->exp || h->exp_max != s->exp_max || h->level != s->level)) {
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

static const float ICON_PALETTE[8][3] = {{.85f, .35f, .25f}, {.35f, .55f, .9f}, {.95f, .8f, .3f}, {.55f, .75f, .4f},
                                         {.7f, .45f, .85f}, {.3f, .8f, .8f}, {.9f, .55f, .2f}, {.8f, .8f, .8f}};

/* image0: the item hotkey icons (game image of base.swf).  Render
 * rectangles as the client lays them out (0x00c552b1, static): x from 0 in
 * steps of 32, wrapping to the next row of 32 when past the image width;
 * each icon 20 x 20 (the double 20.0 at 0x01a83c80). */
static void layout_hotkeys(mu_gfx_layer *L)
{
    int x = 0, y = 0;
    for (int i = 0; i < 4; i++) {
        hotkey_item *h = &L->hotkeys[i];
        if (h->count <= 0)
            continue;
        h->render[0] = (float)x;
        h->render[1] = (float)y;
        h->render[2] = h->render[3] = 20.0f;
        x += 32;
        if (x > ICON_W) {
            x = 0;
            y += 32;
        }
    }
}

static void update_icons(mu_gfx_layer *L)
{
    movie *mv = &L->mv[MU_GFX_MAIN];
    if (!L->base_mode || !mv->g)
        return;
    if (L->in_callback) {   /* mugfx refuses images from inside the movie: retry from pump */
        L->icons_dirty = 1;
        return;
    }
    L->icons_dirty = 0;
    if (!L->icon_rgba && !(L->icon_rgba = malloc((size_t)ICON_W * ICON_H * 4)))
        return;
    memset(L->icon_rgba, 0, (size_t)ICON_W * ICON_H * 4);
    mu_gfx_item_draw draws[4];
    int n = 0;
    for (int i = 0; i < 4; i++) {
        hotkey_item *h = &L->hotkeys[i];
        if (h->count <= 0)
            continue;
        mu_gfx_item_draw *d = &draws[n++];
        memset(d, 0, sizeof *d);
        d->item = -1;
        d->code = h->code;
        d->level = h->level;
        memcpy(d->rect, h->render, sizeof d->rect);
        d->slot[0] = h->render[0] * 640.0f / ICON_W;      /* the image as a 640 x 480 "screen" */
        d->slot[1] = h->render[1] * 480.0f / ICON_H;
        d->slot[2] = h->render[2] * 640.0f / ICON_W;
        d->slot[3] = h->render[3] * 480.0f / ICON_H;
        d->frame_scale = 1.0f;
        d->alpha = 1.0f;
    }
    if (!L->cfg.icons || L->cfg.icons(L->cfg.items_user, draws, n, L->icon_rgba, ICON_W, ICON_H)) {
        /* Stand-ins (layer choice): a coloured square per item group, in the
         * bottom-up row order the bar's flipped bitmap fill expects. */
        for (int k = 0; k < n; k++) {
            const float *rgb = ICON_PALETTE[(draws[k].code >> 9) & 7];
            for (int yy = 2; yy < 18; yy++)
                for (int xx = 2; xx < 18; xx++) {
                    int px = (int)draws[k].rect[0] + xx, row = ICON_H - 1 - ((int)draws[k].rect[1] + yy);
                    if (px < 0 || px >= ICON_W || row < 0 || row >= ICON_H)
                        continue;
                    uint8_t *o = L->icon_rgba + ((size_t)row * ICON_W + (size_t)px) * 4;
                    int edge = xx < 4 || yy < 4 || xx >= 16 || yy >= 16;
                    for (int c = 0; c < 3; c++)
                        o[c] = (uint8_t)(255 * rgb[c] * (edge ? 0.6f : 1.0f));
                    o[3] = 255;
                }
        }
    }
    L->api.set_image(mv->g, "image0", ICON_W, ICON_H, L->icon_rgba, 0);
    logf_(L, "game: image0 (%d item icons)", n);
}

static void feed_item_hotkeys(mu_gfx_layer *L)
{
    char path[160], list[1024];
    size_t n = 0;
    snprintf(path, sizeof path, "%s.mcItemHotKey", L->mv[MU_GFX_MAIN].path);
    L->hotkeys[0].count = L->potions;   /* layer choice: one potion slot */
    layout_hotkeys(L);
    for (int i = 0; i < 4; i++) {
        const hotkey_item *h = &L->hotkeys[i];
        if (h->count > 0)
            n += (size_t)snprintf(list + n, sizeof list - n,
                                  "%s{\"slot\":%d,\"selectGroup\":1,\"itemType\":%d,\"itemLevel\":%d,"
                                  "\"itemCount\":%d,\"InventoryIndex\":-1,\"renderX\":%g,\"renderY\":%g,"
                                  "\"renderW\":%g,\"renderH\":%g}", i ? "," : "", i, h->code, h->level, h->count,
                                  h->render[0], h->render[1], h->render[2], h->render[3]);
        else
            n += (size_t)snprintf(list + n, sizeof list - n, "%s{\"slot\":%d,\"selectGroup\":0}", i ? "," : "", i);
    }
    /* The image first: ItemHotKey.DrawIcon fetches _root.getBitmap(0) while
     * setItemHotKeyAll runs (inside a callback the update is deferred). */
    if (L->api.set_image && L->base_mode)
        update_icons(L);
    invokef(L, MU_GFX_MAIN, path, "setItemHotKeyAll", "[[%s]]", list);
}

/* The skill table of the data movie (0x00c5e990 / 0x00c5ebaa). */
static void send_skills(mu_gfx_layer *L)
{
    const char *path = channel(L, "ASData");
    if (!path[0])
        return;
    size_t cap = (size_t)L->nskills * 256 + 16;
    char *list = malloc(cap), p[160];
    if (!list)
        return;
    size_t n = 0;
    for (int i = 0; i < L->nskills && n + 256 < cap; i++) {
        char name[160];
        json_quote(name, sizeof name, L->skills[i].name);
        n += (size_t)snprintf(list + n, cap - n,
                              "%s{\"Index\":%d,\"Magic_Icon\":%d,\"Name\":%s,\"Delay\":%d,\"SkillUseType\":%d,"
                              "\"MasteryType\":%d}", i ? "," : "", L->skills[i].index, L->skills[i].icon, name,
                              L->skills[i].delay, L->skills[i].use_type, L->skills[i].mastery);
    }
    list[n] = 0;
    snprintf(p, sizeof p, "%s.skill", path);
    invokef(L, MU_GFX_MAIN, p, "setSkillAll", "[[%s]]", list);
    free(list);
    L->skills_sent = 1;
}

static const mu_gfx_skill *skill_info(const mu_gfx_layer *L, int index)
{
    for (int i = 0; i < L->nskills; i++)
        if (L->skills[i].index == index)
            return &L->skills[i];
    return NULL;
}

static void feed_skills(mu_gfx_layer *L)
{
    char path[160], slots[1024];
    size_t n = 0;
    snprintf(path, sizeof path, "%s.mcSkillHotKey", L->mv[MU_GFX_MAIN].path);
    for (int i = 0; i < 10; i++)
        n += (size_t)snprintf(slots + n, sizeof slots - n, "%s{\"slot\":%d,\"skill\":%d,\"isUse\":true,"
                              "\"damageType\":0}", i ? "," : "", i, i < 6 ? i + 1 : 0);
    invokef(L, MU_GFX_MAIN, path, "SetSkillSlot",
            "[{\"Elemental\":0,\"SelectSlot\":%d,\"SelectSkill\":%d,\"SelectUseSkill\":true,"
            "\"SelectSkill_damageType\":0,\"arrSlots\":[%s]}]", L->selected_skill, L->selected_skill + 1, slots);
}

/* NATIVE-PROGRESS-001: the values of the class formula's rows ("-" until the host sets them) */
static const char *derived_row(const mu_gfx_hero *h, int key, char *buf, size_t cap)
{
    if (!h->has_derived && key != MU_GFX_ROW_HP && key != MU_GFX_ROW_MANA && key != MU_GFX_ROW_SD &&
        key != MU_GFX_ROW_AG)
        return "-";
    switch (key) {
    case MU_GFX_ROW_ATK_RATE: snprintf(buf, cap, "%d", h->atk_rate); break;
    case MU_GFX_ROW_PVP_RATE: snprintf(buf, cap, "%d", h->pvp_rate); break;
    case MU_GFX_ROW_DEFENSE: snprintf(buf, cap, "%d", h->defense); break;
    case MU_GFX_ROW_DEF_RATE: snprintf(buf, cap, "%d", h->def_rate); break;
    case MU_GFX_ROW_PVP_DEFRATE: snprintf(buf, cap, "%d", h->pvp_defrate); break;
    case MU_GFX_ROW_MAGIC: snprintf(buf, cap, "%d ~ %d", h->magic_min, h->magic_max); break;
    case MU_GFX_ROW_CURSE: snprintf(buf, cap, "%d ~ %d", h->curse_min, h->curse_max); break;
    case MU_GFX_ROW_HP: snprintf(buf, cap, "%d / %d", h->hp, h->max_hp); break;
    case MU_GFX_ROW_MANA: snprintf(buf, cap, "%d / %d", h->mp, h->max_mp); break;
    case MU_GFX_ROW_SD: snprintf(buf, cap, "%d / %d", h->sd, h->max_sd); break;
    case MU_GFX_ROW_AG: snprintf(buf, cap, "%d / %d", h->ag, h->max_ag); break;
    case MU_GFX_ROW_ATK_SPEED:
        if (!h->speed_text[0])
            return "-";
        snprintf(buf, cap, "%s", h->speed_text);
        break;
    default: return "-";
    }
    return buf;
}

static void feed_character(mu_gfx_layer *L)
{
    movie *mv = &L->mv[MU_GFX_CHARACTER];
    const mu_gfx_hero *h = &L->hero;
    if (!mv->path[0])
        return;
    char lv[32], exp[32], expmax[48], v[5][32], pts[32], add[5][32];
    /* NATIVE-PROGRESS-001: the window's level row shows level + master level (live: Nighty 400 + 1200 = 1600) */
    snprintf(lv, sizeof lv, "%d", h->has_derived ? h->level + h->master_level : h->level);
    commas(exp, sizeof exp, h->exp);
    char tmp[32];
    commas(tmp, sizeof tmp, h->exp_max);
    snprintf(expmax, sizeof expmax, "/ %s", tmp);
    const int32_t stats[5] = {h->strength, h->agility, h->vitality, h->energy, h->command};
    for (int i = 0; i < 5; i++) {
        commas(v[i], sizeof v[i], h->has_derived ? stats[i] - h->added[i] : stats[i]);
        if (h->added[i] > 0)
            snprintf(add[i], sizeof add[i], "(+%d)", h->added[i]);
        else
            snprintf(add[i], sizeof add[i], "-");
    }
    snprintf(pts, sizeof pts, "%d", h->points);
    char name[64], cls[64];
    json_quote(name, sizeof name, h->name);
    json_quote(cls, sizeof cls, h->class_name);
    invokef(L, MU_GFX_CHARACTER, mv->path, "ClearItems", "[]");
    invokef(L, MU_GFX_CHARACTER, mv->path, "SetCharacterName", "[%s]", name);
    char dmg[64], extra[64];
    if (h->has_derived)   /* NATIVE-PROGRESS-001: the class formula (reconstructed/progress) */
        snprintf(dmg, sizeof dmg, "%d ~ %d", h->dmg_min, h->dmg_max);
    else
        snprintf(dmg, sizeof dmg, "%d ~ %d", h->strength / 6 + h->level, h->strength / 4 + h->level * 2);
    if (L->nchar_rows > 0) {
        /* NATIVE-LANG-002: the client's rows (CharacterInfoSetup, row builder 0x00b3dedc): SetName("%d %d %d %s
         * %s %s %d", type, id, sort, line(label, colour), line(value, value colour), "", button), the lines
         * through the reconstructed line builder 0x00ab4dc0.  The client sends "-" and fills the values later
         * (SetCharacterInfo, not reconstructed); the layer puts the hero values it has into the known rows. */
        for (int r = 0; r < L->nchar_rows; r++) {
            const mu_gfx_char_row *row = &L->char_rows[r];
            const char *value = "-";
            switch (row->value_key) {
            case MU_GFX_ROW_CLASS: value = h->class_name; break;
            case MU_GFX_ROW_LEVEL: value = lv; break;
            case MU_GFX_ROW_POINTS: value = pts; break;
            case MU_GFX_ROW_STRENGTH: value = v[0]; break;
            case MU_GFX_ROW_AGILITY: value = v[1]; break;
            case MU_GFX_ROW_VITALITY: value = v[2]; break;
            case MU_GFX_ROW_ENERGY: value = v[3]; break;
            case MU_GFX_ROW_COMMAND: value = v[4]; break;
            case MU_GFX_ROW_DAMAGE: value = dmg; break;
            default: value = derived_row(h, row->value_key, extra, sizeof extra); break;
            }
            const char *third = "";   /* NATIVE-PROGRESS-001: the stat rows' added value ("(+N)", "-" for none, live) */
            if (h->has_derived && row->value_key >= MU_GFX_ROW_STRENGTH && row->value_key <= MU_GFX_ROW_COMMAND)
                third = add[row->value_key - MU_GFX_ROW_STRENGTH];
            char lhtml[512], vhtml[256], lraw[512], vraw[256], lq[1100], vq[600], tq[96];
            mu_tooltip_html_line(lraw, sizeof lraw, row->label, row->color, 0);
            mu_tooltip_html_line(vraw, sizeof vraw, value, row->value_color, 0);
            mu_latin1_to_utf8(lhtml, sizeof lhtml, lraw);
            mu_latin1_to_utf8(vhtml, sizeof vhtml, vraw);
            json_quote(lq, sizeof lq, lhtml);
            json_quote(vq, sizeof vq, vhtml);
            json_quote(tq, sizeof tq, third);
            invokef(L, MU_GFX_CHARACTER, mv->path, "SetName", "[%d,%d,%d,%s,%s,%s,%d]", row->type, row->id,
                    row->sort, lq, vq, tq, row->button);
        }
    } else {
    /* Base info (TEXT_TYPE_CHARACTER_BASE_INFO = 1, sort orders 0..6) and stat
     * rows (TEXT_TYPE_CHARACTER_STAT_INFO = 2, button type 1 = "+").  Without
     * the CharacterInfoSetup table these are English stand-ins. */
    invokef(L, MU_GFX_CHARACTER, mv->path, "SetName", "[1,0,0,\"Level\",\"%s\",\"%s\",0]", lv,
            h->master_level ? "" : "");
    invokef(L, MU_GFX_CHARACTER, mv->path, "SetName", "[1,1,1,\"Class\",%s,\"\",0]", cls);
    invokef(L, MU_GFX_CHARACTER, mv->path, "SetName", "[1,2,2,\"Exp\",\"%s\",\"%s\",0]", exp, expmax);
    invokef(L, MU_GFX_CHARACTER, mv->path, "SetName", "[1,3,3,\"Points\",\"%s\",\"\",0]", pts);
    static const char *const LABELS[5] = {"Strength", "Agility", "Vitality", "Energy", "Command"};
    for (int i = 0; i < 5; i++)
        invokef(L, MU_GFX_CHARACTER, mv->path, "SetName", "[2,%d,%d,\"%s\",\"%s\",\"\",1]", i + 1, i, LABELS[i],
                v[i]);
    invokef(L, MU_GFX_CHARACTER, mv->path, "SetName", "[3,10,0,\"Damage\",\"%s\",\"\",0]", dmg);
    }
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
    int context = L->mv[MU_GFX_NPC_SHOP].open ? MU_GFX_TIP_SELL : MU_GFX_TIP_PLAIN;   /* NATIVE-LANG-002 */
    mu_mix_item snapshot=mix_snapshot(it);
    if (L->cfg.tooltip_snapshot ? L->cfg.tooltip_snapshot(L->cfg.tooltip_user,&snapshot,context,html,sizeof html) :
        L->cfg.tooltip_ex ? L->cfg.tooltip_ex(L->cfg.tooltip_user, it->grid.code, it->level, context, html, sizeof html)
                          : (!L->cfg.tooltip || L->cfg.tooltip(L->cfg.tooltip_user, it->grid.code, it->level, html,
                                                               sizeof html)))
        builtin_tooltip(it, html, sizeof html);
    uint8_t wire[15];
    item_wire(it, wire);
    int full_packet = L->cfg.tooltip_packet &&
                      !L->cfg.tooltip_packet(L->cfg.tooltip_user, wire, context, html, sizeof html);
    if (!full_packet && it->option) {
        size_t used = strlen(html);
        snprintf(html + used, sizeof html - used, "<br>Additional option +%d", it->option * 4);
    }
    service_tooltip(L,it,html,sizeof html);
    json_quote(quoted, sizeof quoted, html);
    float sc = L->inv_scale;
    float x = L->win_x + (L->slot_x + it->grid.col * (L->slot_w + L->gap_x)) * sc;
    float y = L->win_y + (L->slot_y + it->grid.row * (L->slot_h + L->gap_y)) * sc;
    float w = it->grid.width * L->slot_w * sc, h = it->grid.height * L->slot_h * sc;
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
    if (!open && inventory_busy(L) && (m==MU_GFX_INVENTORY || m==MU_GFX_NPC_SHOP || m>=MU_GFX_STORE_LIST))return;
    if (!open && m==MU_GFX_STORE_REGISTER)L->services.draft_active=0;
    if (!open && m==MU_GFX_INVENTORY) {
        for(int k=MU_GFX_STORE_LIST;k<=MU_GFX_STORE_PURCHASE;k++)mu_gfx_layer_show(L,k,0);
    }
    if (!open && m==MU_GFX_NPC_SHOP && L->services.repair_mode) {
        L->services.repair_mode=0;
        invokef(L,MU_GFX_INVENTORY,L->mv[MU_GFX_INVENTORY].path,"SetRepairMode","[false]");
    }
    if (m == MU_GFX_MAIN || m == MU_GFX_CHAT) {
        mv->open = open;
        return;
    }
    if (m == MU_GFX_TOOLTIP) {
        if (!open)
            hide_tooltip(L);
        return;
    }
    if (open && m == MU_GFX_QUEST_NOTICE && L->api.set_variable)
        L->api.set_variable(mv->g, "_level0._visible", "true");   /* the notice animation hides its root at frame 65 */
    if (!open && (m == MU_GFX_MIX || m == MU_GFX_INVENTORY) &&
        (L->mix.pending || (L->mv[MU_GFX_MIX].open && !mix_return(L))))
        return;
    if (!open && m == MU_GFX_INVENTORY) {
        mu_gfx_layer_show(L,MU_GFX_MIX,0);
        mu_gfx_layer_show(L,MU_GFX_MIX_SELECT,0);
    }
    if (mv->open == open)
        return;
    mv->open = open;
    if (open)
        raise_window(L, m);
    if (!open && (m == MU_GFX_INVENTORY || m == MU_GFX_NPC_SHOP || m == MU_GFX_STORAGE))
        hide_tooltip(L);
    if (open && m == MU_GFX_CHARACTER)
        feed_character(L);
    if (m == MU_GFX_PARTY)
        invokef(L, m, mv->path, open ? "openWindow" : "closeWindow", "[]");
    else
        invokef(L, m, mv->path, "SetVisible", "[%s]", open ? "true" : "false");
    if (!open && m==MU_GFX_MIX)
        mu_gfx_layer_show(L,MU_GFX_INVENTORY,0);
    mv->next_bounds_ms = 0;
    if (m == MU_GFX_SKILL_STAMP)
        skill_window_shown(L, m, open);
    if (m >= MU_GFX_MASTER_TREE && m <= MU_GFX_TREE5 && L->cfg.quest_call)
        L->cfg.quest_call(L->cfg.tooltip_user, m, open ? "WindowShown" : "WindowHidden", "[]");
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
    if (inventory_busy(L)) return;
    if (service_inventory(L,index))return;
    if (L->socialh.inventory && L->socialh.inventory(L->socialh.user, index))
        return;
    int cols = L->grid.cols;
    if (index < 0 || index >= cols * L->grid.rows)
        return;
    if (L->held < 0) {
        mu_grid_item *gi = mu_grid_item_at(&L->grid, index);
        if (gi && L->grid.cells[index]) {
            if (item_reserved(L,(int)((item *)gi-L->items))) return;
            L->held = (int)((item *)gi - L->items);
            mu_grid_remove(&L->grid, gi);
            hide_tooltip(L);
            logf_(L, "game: pick item %u (%dx%d) from cell %d", gi->id, gi->width, gi->height, index);
        }
    } else {
        if (mix_jewel(L, index)) return;
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
    if (inventory_busy(L)) return;
    if (service_inventory(L,index))return;
    if (L->mv[MU_GFX_MIX].open) { mu_gfx_layer_mix_action(L, "mixput", index, 0); return; }
    if (L->socialh.inventory && L->socialh.inventory(L->socialh.user, index))
        return;
    if (npc_inventory_r(L, index))   /* NATIVE-NPC-001: sell / put while NpcShop or StorageInven is open */
        return;
    /* Right click on an item: the client uses or equips it (0x00b907b9's
     * handler; not reconstructed).  The layer logs it and, for the demo
     * potion code, drinks one (layer choice). */
    mu_grid_item *gi = index >= 0 && index < L->grid.cols * L->grid.rows ? mu_grid_item_at(&L->grid, index) : NULL;
    if (gi && L->grid.cells[index]) {
        logf_(L, "game: right click item %u code %d at cell %d", gi->id, gi->code, index);
        if (gi->code >= 14 * 512 && gi->code <= 14 * 512 + 3) {   /* apple, healing potions (14,0..3) */
            L->hero.hp = L->hero.max_hp;
            logf_(L, "game: potion restores HP");
        }
    }
}

int mu_gfx_layer_add_item(mu_gfx_layer *L, int32_t code, int32_t level, int32_t width, int32_t height,
                          const char *name)
{
    if (!L || inventory_busy(L))
        return -1;
    int index;
    for(index=0;index<L->nitems;index++) {
        int owned=L->held==index || item_reserved(L,index);
        for(int k=0;k<L->grid.item_count;k++)owned|=L->grid.items[k]==&L->items[index].grid;
        slot_window *sw=&L->swin[2];
        for(int k=0;k<sw->grid.item_count;k++) {
            int slot=(int)((item *)sw->grid.items[k]-sw->items);
            owned|=L->mix.origin[slot]==index;
        }
        if(!owned)break;
    }
    if(index>=MAX_ITEMS)return -1;
    item *it = &L->items[index];
    memset(it, 0, sizeof *it);
    it->grid.id = (uint32_t)(index + 1);
    it->grid.code = code;
    it->grid.width = (uint8_t)(width < 1 ? 1 : width);
    it->grid.height = (uint8_t)(height < 1 ? 1 : height);
    it->level = level;
    it->durability = 1;
    it->element = -1;
    snprintf(it->name, sizeof it->name, "%s", name && name[0] ? name : "Item");
    int col, row;
    if (!mu_grid_find_free(&L->grid, it->grid.width, it->grid.height, &col, &row)) {
        it->grid.code = -1;
        return -1;
    }
    mu_grid_place(&L->grid, col, row, &it->grid);
    /* Stand-in colour per item group (layer choice: no RenderItem3D models). */
    static const float PALETTE[8][3] = {{.85f, .35f, .25f}, {.35f, .55f, .9f}, {.95f, .8f, .3f}, {.55f, .75f, .4f},
                                        {.7f, .45f, .85f}, {.3f, .8f, .8f}, {.9f, .55f, .2f}, {.8f, .8f, .8f}};
    memcpy(it->rgb, PALETTE[(code >> 9) & 7], sizeof it->rgb);
    if(index==L->nitems)L->nitems++;
    slot_states(L);
    return index;
}

int mu_gfx_layer_add_slot_item(mu_gfx_layer *L, const mu_gfx_slot_item *src) {
    if (!src)
        return -1;
    int k = mu_gfx_layer_add_item(L, src->code, src->level, src->width, src->height, src->name);
    if (k >= 0) {
        item_instance(&L->items[k], src);
    }
    return k;
}

int mu_gfx_layer_social_item(mu_gfx_layer *L, const uint8_t b[15], mu_gfx_slot_item *out) {
    if (!L || !b || !out)
        return 0;
    int code = mu_social_item_code(b);
    memset(out, 0, sizeof *out);
    out->code = code;
    out->width = out->height = 1;
    snprintf(out->name, sizeof out->name, "Item %d", code);
    out->level = (b[1] >> 3) & 15;
    out->set_bits = b[4];
    out->element = -1;
    out->has_data = 1;
    memcpy(out->data, b, sizeof out->data);
    if (L->cfg.social_item_info && !L->cfg.social_item_info(L->cfg.tooltip_user, code, out))
        return 0;
    return out->width > 0 && out->height > 0;
}

void mu_gfx_layer_social_tooltip(mu_gfx_layer *L, const mu_gfx_slot_item *src, const float rect[4]) {
    if (!L || !src || !rect || !L->mv[MU_GFX_TOOLTIP].g)
        return;
    char html[8192], quoted[16384];
    if (!src->has_data || !L->cfg.tooltip_packet ||
        L->cfg.tooltip_packet(L->cfg.tooltip_user, src->data, MU_GFX_TIP_PLAIN, html, sizeof html)) {
        item it;
        memset(&it, 0, sizeof it);
        it.grid.code = src->code;
        it.grid.width = (uint8_t)src->width;
        it.grid.height = (uint8_t)src->height;
        it.level = src->level;
        snprintf(it.name, sizeof it.name, "%s", src->name);
        builtin_tooltip(&it, html, sizeof html);
    }
    json_quote(quoted, sizeof quoted, html);
    L->mv[MU_GFX_TOOLTIP].open = 1;
    invokef(L, MU_GFX_TOOLTIP, L->mv[MU_GFX_TOOLTIP].path, "SetInfoPopup", "[%d,%d,%d,%d,%s]", (int)rect[0],
            (int)rect[1], (int)rect[2], (int)rect[3], quoted);
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

static const char *on_call_(movie *mv, const char *name, const char *args);

static const char *on_call(void *user, const char *name, const char *args)
{
    movie *mv = user;
    mu_gfx_layer *L = mv->L;
    L->callbacks++;
    L->in_callback++;
    const char *r = on_call_(mv, name, args);
    L->in_callback--;
    return r;
}

/* NATIVE-QUEST-001/002: the movies the host drives with the client's quest code */
static int is_quest_movie(int id)
{
    return (id >= MU_GFX_MASTER_TREE && id <= MU_GFX_TREE5) ||
           id == MU_GFX_QUEST_PROGRESS || id == MU_GFX_MY_QUEST || id == MU_GFX_QUEST_SUMMARY ||
           id == MU_GFX_QUEST_NOTICE || id == MU_GFX_JOB_QUEST;
}

static const char *on_call_(movie *mv, const char *name, const char *args)
{
    mu_gfx_layer *L = mv->L;
    if (strcmp(name, "TweenTimeSet") && strcmp(name, "requestSlotInfo") && strcmp(name, "EQUIPrequestSlotInfo"))
        logf_(L, "%s -> %s %.300s", mv->file, name, args);
    double v[8];
    int n = json_numbers(args, v, 8);
    if (!strcmp(name, "requestWindowPos") && n >= 2) {
        mv->win_x = (float)v[0];
        mv->win_y = (float)v[1];
    }
    char s[256] = "";
    mv->view_dirty = 1;
    if (mv->id == MU_GFX_OPTION || mv->id == MU_GFX_SYSTEM_MENU) {   /* NATIVE-PROGRESS-001 */
        if (L->cfg.progress_call)
            L->cfg.progress_call(L->cfg.tooltip_user, mv->id, name, args);
        return NULL;
    }
    if (mv->id>=MU_GFX_STORE_LIST && mv->id<=MU_GFX_STORE_PURCHASE && strcmp(name,"UIInit") && strcmp(name,"CloseWindow")) {
        service_call(mv,name,args,v,n);return NULL;
    }
    if (mv->id >= MU_GFX_PARTY && mv->id <= MU_GFX_MESSENGER) {
        char command[96] = "";
        if (mv->id == MU_GFX_PARTY && !strcmp(name, "PartyFrame")) {
            json_string(args, 0, command, sizeof command);
            if (!strcmp(command, "onLoad")) json_string(args, 1, mv->path, sizeof mv->path);
        } else {
            snprintf(command, sizeof command, "%s", name);
            if (!strcmp(name, "UIInit") && json_string(args, 0, s, sizeof s))
                snprintf(mv->path, sizeof mv->path, "_level0.%s", s);
        }
        if (L->socialh.window) L->socialh.window(L->socialh.user, mv->id, command, args);
        return NULL;
    }
    if (mv->id == MU_GFX_QUEST_SUMMARY && !strcmp(name, "QuestSummary")) {
        /* This window belongs to the second GFx layer. Its channel carries (command, object), and its
         * loader reports a complete targetPath rather than the old layer's UIInit name. */
        char command[64] = "", arguments[96];
        json_string(args, 0, command, sizeof command);
        if (!strcmp(command, "onLoad"))
            json_string(args, 1, mv->path, sizeof mv->path);
        if (!strcmp(command, "onOpenWindow")) {
            mv->open = strstr(args, "true") != NULL;
            if (mv->open)
                raise_window(L, mv->id);
        }
        snprintf(arguments, sizeof arguments, "[%.0f,%.0f]", json_field(args, "category", 0),
                 json_field(args, "index", 0));
        if (L->cfg.quest_call)
            L->cfg.quest_call(L->cfg.tooltip_user, mv->id, command, arguments);
        return NULL;
    }
    if (!strcmp(name, "UIInit") && json_string(args, 0, s, sizeof s)) {
        snprintf(mv->path, sizeof mv->path, "_level0.%s", s);
        if (mv->id == MU_GFX_MOVE_COMMAND && L->maph.window)
            L->maph.window(L->maph.user, mv->id, name, args);   /* NATIVE-MAP-001 */
        if (is_quest_movie(mv->id) && L->cfg.quest_call)
            L->cfg.quest_call(L->cfg.tooltip_user, mv->id, name, args);   /* NATIVE-QUEST-001: the handler's OnLoad */
        return NULL;
    }
    if (mv->id == MU_GFX_MOVE_COMMAND && strcmp(name, "TweenTimeSet")) {
        /* NATIVE-MAP-001: the Move window's handler runs in the host (reconstructed/map) */
        if (L->maph.window)
            L->maph.window(L->maph.user, mv->id, name, args);
        else if (!strcmp(name, "CloseWindow"))
            mu_gfx_layer_show(L, mv->id, 0);
        return NULL;
    }
    if (is_quest_movie(mv->id) && strcmp(name, "TweenTimeSet")) {
        /* NATIVE-QUEST-001: the host runs the client's handler (reconstructed/quest) */
        if (L->cfg.quest_call)
            L->cfg.quest_call(L->cfg.tooltip_user, mv->id, name, args);
        else if (!strcmp(name, "CloseWindow"))
            mu_gfx_layer_show(L, mv->id, 0);
        return NULL;
    }
    if (!strcmp(name, "CloseWindow")) {
        mu_gfx_layer_show(L, mv->id, 0);     /* queued: we are inside the movie */
        return NULL;
    }
    if (!strcmp(name, "fscommand")) {
        /* The chat's TextInput focusIn/focusOut (the client's IME signal);
         * in base mode it comes through the base movie. */
        if (json_string(args, 1, s, sizeof s) && (mv->id == MU_GFX_CHAT || (L->base_mode && mv->id == MU_GFX_MAIN)))
            L->chat_edit = !strcmp(s, "focusIn") ? 1 : !strcmp(s, "focusOut") ? 0 : L->chat_edit;
        return NULL;
    }
    if (L->base_mode && mv->id == MU_GFX_MAIN) {
        /* The base movie's channels (KeyMovieClip EventCall names). */
        if (json_string(args, 0, s, sizeof s) && !strcmp(s, "onLoad")) {
            char path[128] = "";
            json_string(args, 1, path, sizeof path);
            set_channel(L, name, path);
            if (!strcmp(name, "UIFrame"))
                L->ui_loaded = 0;                           /* LoadFrameFiles follows (pump) */
            else if (!strcmp(name, "ASData"))
                L->skills_sent = 0;
            else if (!strcmp(name, "main"))
                snprintf(L->mv[MU_GFX_MAIN].path, sizeof L->mv[MU_GFX_MAIN].path, "%s", path);
            else if (!strcmp(name, "chat"))
                snprintf(L->mv[MU_GFX_CHAT].path, sizeof L->mv[MU_GFX_CHAT].path, "%s", path);
            else if (is_bufflist(name))
                L->buffs_sent = 0;                          /* the buffs are sent again (pump) */
            return NULL;
        }
        if (!strcmp(name, "UIFrame") && !strcmp(s, "onFileLoad")) {
            L->ui_loaded = 1;
            return NULL;
        }
        if (!strcmp(name, "chat"))
            goto chat_channel;
        if (is_bufflist(name)) {
            bufflist_event(L, s, args);
            return NULL;
        }
        if (strcmp(name, "main")) {
            if (L->maph.channel)   /* NATIVE-MAP-001: hudMap's events (showMap, baseMovie) */
                L->maph.channel(L->maph.user, name, args);
            return NULL;
        }
    }
    switch (mv->id) {
    case MU_GFX_MAIN:
        if (!strcmp(name, "main") && json_string(args, 0, s, sizeof s)) {
            if (!strcmp(s, "onLoad")) {
                char path[96];
                if (json_string(args, 1, path, sizeof path))
                    snprintf(mv->path, sizeof mv->path, "%s", path);
            } else if (!strcmp(s, "onHotKey")) {
                /* A menu button: keyCode is the client's menu id (0x00c71fc2),
                 * dispatched by 0x00c714bd (static): id 1 toggles
                 * CharacterInfoFrame (0x00c733cf), id 14 InventoryFrame
                 * (0x00c73a2f); the other windows are not played. */
                int id = (int)json_field(args, "keyCode", -1);
                L->key_used = 1;
                logf_(L, "game: menu id %d", id);
                if (id == 1)
                    mu_gfx_layer_toggle(L, MU_GFX_CHARACTER);
                else if (id == 14)
                    mu_gfx_layer_toggle(L, MU_GFX_INVENTORY);
            } else if (L->have_skill_host && (!strcmp(s, "onSelectSkill") || !strcmp(s, "onSkillTooltip") ||
                                              !strcmp(s, "offSkillTooltip") || !strcmp(s, "onOpenSkillWindow"))) {
                skill_main_event(L, mv, s, args);       /* NATIVE-SKILL-001 */
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
                char hotkey[8], label[160];
                snprintf(hotkey, sizeof hotkey, "%d", (slot + 1) % 10);
                const mu_gfx_skill *sk = skill_info(L, skill);
                if (sk && sk->name[0])
                    json_quote(label, sizeof label, sk->name);
                else
                    snprintf(label, sizeof label, "\"Skill %d\"", skill);
                L->mv[MU_GFX_TOOLTIP].open = 1;
                invokef(L, MU_GFX_TOOLTIP, L->mv[MU_GFX_TOOLTIP].path, "SetInfoPopupMainSmall",
                        "[%d,%d,%d,%d,\"%s\",%s]", (int)json_field(args, "x", 0), (int)json_field(args, "y", 0),
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
        if (!strcmp(name,"onClickbtnPrivateStore")) { mu_gfx_layer_service_action(L,"store",0,0);return NULL; }
        if (!strcmp(name,"onClickbtnRepair")) { mu_gfx_layer_service_action(L,"selfrepair",0,0);return NULL; }
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
        if (!strcmp(name, "onClickbtnMasterSkillTree"))
            mu_gfx_layer_toggle(L, MU_GFX_MASTER_TREE);
        else if (!strcmp(name, "OnClick4thSkillTree"))
            mu_gfx_layer_toggle(L, MU_GFX_TREE4);
        else if (!strcmp(name, "OnClick5thSkillTree"))
            mu_gfx_layer_toggle(L, MU_GFX_TREE5);
        else if (!strcmp(name, "onClickButton") && n >= 1 && L->cfg.stat_button &&
                 L->cfg.stat_button(L->cfg.tooltip_user, v[0])) {
            /* NATIVE-PROGRESS-001: the client's rule and request (the host's demo server answers) */
        } else if (!strcmp(name, "onClickButton") && n >= 1 && L->hero.points > 0) {
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
    chat_channel:
        if (!strcmp(name, "chat") && json_string(args, 0, s, sizeof s)) {
            if (!strcmp(s, "onLoad")) {
                char path[96];
                if (json_string(args, 1, path, sizeof path))
                    snprintf(mv->path, sizeof mv->path, "%s", path);
            } else if (!strcmp(s, "onEnterText")) {
                char text[256] = "";
                json_field_string(args, "text", text, sizeof text);
                snprintf(L->last_sent, sizeof L->last_sent, "%s", text);
                char whisper[64] = "";
                json_field_string(args, "wisper", whisper, sizeof whisper);
                if (L->socialh.chat && L->socialh.chat(L->socialh.user, whisper, text))
                    return NULL;
                mu_gfx_layer_chat(L, 1, L->hero.name, text);
                if (L->chat_hook)
                    L->chat_hook(L->chat_hook_user, text);
            } else if (!strcmp(s, "onFocuseText")) {
                if (strstr(args, "\"focused\":true"))
                    chat_open(L, 1);
                else if (strstr(args, "\"focused\":false"))
                    chat_open(L, 0);
            }
        }
        return NULL;
    default:
        if (mv->id == MU_GFX_SKILL_POPUP || mv->id == MU_GFX_SKILL_STAMP)
            return skill_call(mv, name, args, v, n);
        return npc_call(mv, name, args, v, n);
    }
}

/* ---- setup -------------------------------------------------------------------------------------- */

static int open_movie(mu_gfx_layer *L, int m, char *error, size_t cap)
{
    movie *mv = &L->mv[m];
    char path[4096], err[512];
    mv->file = FILES[m];
    mv->L = L;
    mv->id = m;
    if (L->base_mode && m == MU_GFX_MAIN)
        mv->file = "base";
    if (L->base_mode && m == MU_GFX_CHAT) {
        /* The base movie loads Chat itself: the chat plays inside its player. */
        mv->file = "Chat";
        mv->g = L->mv[MU_GFX_MAIN].g;
        mv->alias = 1;
        return 0;
    }
    snprintf(path, sizeof path, "%s/%s.swf", L->cfg.movie_dir, mv->file);
    if (m >= MU_GFX_NPC_DIALOG && access(path, R_OK) != 0) {   /* NPC windows are optional */
        mv->g = NULL;
        return 0;
    }
    mv->g = L->shared ? L->api.open_shared(path, L->px_w, L->px_h, err, sizeof err)
                      : L->api.open(path, L->px_w, L->px_h, err, sizeof err);
    if (!mv->g) {
        snprintf(error, cap, "%s: %s", path, err);
        return -1;
    }
    L->api.set_callback(mv->g, on_call, mv);
    if (L->shared && L->cfg.double_buffer)
        L->api.set_double_buffer(mv->g, 1);
    /* 0x00aad716 advances SkillStampFrame before the first SetViewport. Its MUComponent prototype thus
     * captures the authored 1024x768 stage, not the native window. SetWindowSize can then preserve its
     * centre's screen fraction, as in 0x00acb333. */
    int authored_stamp = m == MU_GFX_SKILL_STAMP;
    L->api.set_view(mv->g, authored_stamp ? 1024 : L->w, authored_stamp ? 768 : L->h, 0, 0, 0, 0, L->scale);
    L->api.start(mv->g);
    if (authored_stamp)
        L->api.set_view(mv->g, L->w, L->h, 0, 0, 0, 0, L->scale);
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

/* Window placement of the window creator 0x00ac9edc (static): registry
 * alignment InventoryFrame 11 (MUDefines.Align_Right), CharacterInfoFrame
 * and InfoPopup 9 (Align_None: no SetAlign/SetWindowSize); SetWindowSize
 * gets the window size (0x01cf1624/8) and SetScale(83) applies below 700
 * pixels of height to both (handler +0x58 = scale / 100). */
static const int WINDOW_ALIGN[MU_GFX_MOVIES] = {
    [MU_GFX_MAIN] = 9, [MU_GFX_INVENTORY] = 11, [MU_GFX_TOOLTIP] = 9, [MU_GFX_CHARACTER] = 9,
    [MU_GFX_CHAT] = 9, [MU_GFX_NPC_DIALOG] = 9, [MU_GFX_NPC_SHOP] = 9, [MU_GFX_STORAGE] = 9,
    [MU_GFX_QUEST_PROGRESS] = 9, [MU_GFX_MY_QUEST] = 9, [MU_GFX_SKILL_POPUP] = 9, [MU_GFX_SKILL_STAMP] = 9,
    [MU_GFX_MOVE_COMMAND] = 10, [MU_GFX_MASTER_TREE] = 0, [MU_GFX_TREE4] = 0, [MU_GFX_TREE5] = 3,
    [MU_GFX_QUEST_SUMMARY] = 9, [MU_GFX_QUEST_NOTICE] = 9, [MU_GFX_JOB_QUEST] = 9,
    [MU_GFX_PARTY] = 9, [MU_GFX_TRADE] = 9, [MU_GFX_FRIENDS] = 9, [MU_GFX_MESSENGER] = 9,
    [MU_GFX_MIX_SELECT] = 9, [MU_GFX_MIX] = 9,
    [MU_GFX_OPTION] = 9, [MU_GFX_SYSTEM_MENU] = 9
};

static void window_sizes(mu_gfx_layer *L)
{
    for (int m = MU_GFX_INVENTORY; m < MU_GFX_MOVIES; m++) {
        if (m == MU_GFX_CHAT || !L->mv[m].g || !L->mv[m].path[0])
            continue;
        /* no SetScale for the info popups (InfoPopup, SkillInfoPopup) */
        float scale = (m != MU_GFX_TOOLTIP && m != MU_GFX_SKILL_POPUP && L->h < 700) ? 0.83f : 1.0f;
        if (m == MU_GFX_MASTER_TREE && L->h < 700)
            scale = 0.9f;
        if (m == MU_GFX_INVENTORY)
            L->inv_scale = scale;
        else if (m == MU_GFX_CHARACTER)
            L->char_scale = scale;
        else if (m == MU_GFX_NPC_SHOP || m == MU_GFX_STORAGE || m == MU_GFX_MIX)
            L->swin[m == MU_GFX_MIX ? 2 : m == MU_GFX_STORAGE].scale = scale;
        /* the client calls SetScale(83) once, at creation, below 700 pixels; a resized window (native) also
         * goes back to 100 */
        if (scale != (L->applied_scale[m] > 0.0f ? L->applied_scale[m] : 1.0f))
            invokef(L, m, L->mv[m].path, "SetScale", "[%g]", scale * 100.0f);
        L->applied_scale[m] = scale;
        if (WINDOW_ALIGN[m] != 9) {
            invokef(L, m, L->mv[m].path, "SetAlign", "[%d]", WINDOW_ALIGN[m]);
        }
        /* 0x00acb333 -> 0x00aae4ae sizes every handler, including the align-9 stamp window. */
        if (WINDOW_ALIGN[m] != 9 || m == MU_GFX_SKILL_STAMP) {
            invokef(L, m, L->mv[m].path, "SetWindowSize", "[%d,%d]", L->w, L->h);
        }
    }
}

/* InitMenuInfo as the main frame's handler builds it (0x00c71fc2, executed
 * under Unicorn by scripts/validate_gfx3.py: groups, submenus, ids and
 * GlobalText numbers equal): keyCode is a menu id (dispatched by
 * 0x00c714bd; ids 13/14/15 toggle PetInventoryFrame, InventoryFrame,
 * GremoryCase, static), key and label are
 * GlobalText strings: the host's text provider (NATIVE-LANG-001, the
 * tables read from the running client) when it has them; otherwise English
 * stand-ins where the entry's role is known and "GlobalText <n>"
 * placeholders elsewhere.  MU_GFX_GT_IDS=1 shows the numbers everywhere. */
typedef struct menu_entry { const char *group; int id; int key_gt; const char *key; int label_gt; const char *label; } menu_entry;
static const menu_entry MENU[] = {
    {"IngameShop", 0, 0xd5c, "X", 0xd5d, "In-game shop"},
    {"CharacterInfo", 1, 0xd5e, "C", 0xd5f, "Character"},
    {"Inventory", -1, -1, "", 0xd61, "Inventory"},
    {"Inventory/", 13, 0x10f6, "", 0x10b9, "Pet inventory"},      /* toggles PetInventoryFrame */
    {"Inventory/", 14, 0xd60, "I", 0xd7d, "Inventory"},           /* toggles InventoryFrame (0x00c73a2f) */
    {"Inventory/", 15, 0x118d, "", 0x118e, "Gremory case"},       /* toggles GremoryCase */
    {"Quest", -1, -1, "", 0xd63, "Quest"},
    {"Quest/", 2, 0xd62, "", 0xd63, NULL},
    {"Quest/", 0x16, -1, "CTRL+T", 0x193b, NULL},
    {"Community", -1, -1, "", 0xd64, "Community"},
    {"Community/", 9, 0xd76, "", 0x3de, NULL},
    {"Community/", 10, 0xd78, "", 0xee2, NULL},
    {"Community/", 11, 0xd79, "", 0xee3, NULL},
    {"Community/", 12, 0xf4c, "", 0xf4d, NULL},
    {"System", -1, -1, "", 0xd65, "System"},
    {"System/", 4, 0xd72, "", 0xd75, NULL},
    {"System/", 5, 0xd73, "", 0x927, NULL},
    {"System/", 7, 0xd77, "", 0x1021, NULL},
    {"System/", 8, 0xecc, "", 0xd4f, NULL},
};

static size_t menu_item(const mu_gfx_layer *L, char *out, size_t cap, const menu_entry *e, int gt_ids)
{
    char key[96], label[160], tmp[48];
    if (gt_ids && e->key_gt >= 0) {
        snprintf(tmp, sizeof tmp, "GT%d", e->key_gt);
        json_quote(key, sizeof key, tmp);
    } else {
        gt_quote(L, key, sizeof key, e->key_gt, e->key);
    }
    if (gt_ids) {
        snprintf(tmp, sizeof tmp, "GlobalText %d", e->label_gt);
        json_quote(label, sizeof label, tmp);
    } else {
        snprintf(tmp, sizeof tmp, "GlobalText %d", e->label_gt);   /* unknown text: a labelled placeholder */
        gt_quote(L, label, sizeof label, e->label_gt, e->label ? e->label : tmp);
    }
    return (size_t)snprintf(out, cap, "{\"keyCode\":%d,\"key\":%s,\"label\":%s", e->id, key, label);
}

static void init_menu(mu_gfx_layer *L)
{
    int gt = getenv("MU_GFX_GT_IDS") && atoi(getenv("MU_GFX_GT_IDS"));
    char buf[8192];
    size_t n = 0;
    n += (size_t)snprintf(buf + n, sizeof buf - n, "[{");
    int ngroups = 0;
    for (size_t i = 0; i < sizeof MENU / sizeof MENU[0]; i++) {
        const menu_entry *e = &MENU[i];
        if (strchr(e->group, '/'))
            continue;
        n += (size_t)snprintf(buf + n, sizeof buf - n, "%s\"%s\":", ngroups++ ? "," : "", e->group);
        n += menu_item(L, buf + n, sizeof buf - n, e, gt);
        char sub[32];
        snprintf(sub, sizeof sub, "%s/", e->group);
        int nsub = 0;
        for (size_t k = 0; k < sizeof MENU / sizeof MENU[0]; k++)
            if (!strcmp(MENU[k].group, sub)) {
                n += (size_t)snprintf(buf + n, sizeof buf - n, "%s", nsub++ ? "}," : ",\"subMenu\":[");
                n += menu_item(L, buf + n, sizeof buf - n, &MENU[k], gt);
            }
        n += (size_t)snprintf(buf + n, sizeof buf - n, "%s}", nsub ? "}]" : "");
    }
    snprintf(buf + n, sizeof buf - n, "}]");
    invokef(L, MU_GFX_MAIN, L->mv[MU_GFX_MAIN].path, "InitMenuInfo", "%s", buf);
}

/* The other HUD movies of the base movie: the location in the top menu
 * (topmenu setMapName / setPosition; the map name is GlobalText, the host
 * supplies it) and the alarm frame's event boxes off (no ranking, PC room or
 * play-time events offline: layer choice). */
static void init_hud(mu_gfx_layer *L)
{
    const char *alarm = channel(L, "alarmframe");
    if (alarm[0]) {
        invokef(L, MU_GFX_MAIN, alarm, "SetRankingScoreVisible", "[false]");
        invokef(L, MU_GFX_MAIN, alarm, "setPCRoomInfo", "[{\"enable\":false}]");
        invokef(L, MU_GFX_MAIN, alarm, "setPlayTimeInfo", "[{\"enable\":false}]");
    }
    L->map_sent = 0;
}

/* ---- NATIVE-LANG-002: the bufflist ---- */

static int is_bufflist(const char *name)
{
    return !strcasecmp(name, "bufflist");
}

static const char *bufflist_path(const mu_gfx_layer *L)
{
    for (int i = 0; i < L->nchannels; i++)
        if (is_bufflist(L->channels[i].name))
            return L->channels[i].path;
    return "";
}

/* The addBuff object of the client's handler 0x00c5f278 (members set by 0x00ae957f / 0x00aecd73, invoke
 * 0x00c8fac2). */
static void send_buff(mu_gfx_layer *L, const mu_gfx_buff *b)
{
    const char *path = bufflist_path(L);
    char detail[48] = "";
    if (b->has_detail)
        snprintf(detail, sizeof detail, ",\"BuffDetailType\":%d", (int)b->detail);
    invokef(L, MU_GFX_MAIN, path, "addBuff", "[{\"BuffType\":%d,\"isDebuff\":%s,\"isCashBuff\":%s%s}]", (int)b->buff,
            b->is_debuff ? "true" : "false", b->is_cash ? "true" : "false", detail);
}

static void feed_buffs(mu_gfx_layer *L)
{
    if (!bufflist_path(L)[0] || L->buffs_sent >= L->nbuffs)
        return;
    for (; L->buffs_sent < L->nbuffs; L->buffs_sent++)
        send_buff(L, &L->buffs[L->buffs_sent]);
}

int mu_gfx_layer_add_buff(mu_gfx_layer *L, const mu_gfx_buff *b)
{
    if (!L || !b || L->nbuffs >= (int)(sizeof L->buffs / sizeof L->buffs[0]))
        return 0;
    for (int i = 0; i < L->nbuffs; i++)
        if (L->buffs[i].buff == b->buff)
            return 0;
    L->buffs[L->nbuffs++] = *b;
    if (!L->in_callback)
        feed_buffs(L);
    return 1;
}

int mu_gfx_layer_buff_count(const mu_gfx_layer *L)
{
    return L ? L->nbuffs : 0;
}

/* onTooltip {BuffType, x, y}: the client's 0x00c5efb4 hands the buff and the position (times the GFx rates) to
 * the InfoPopup builder 0x00b8d4de; the host builds the HTML (cfg.buff_tooltip). */
static void bufflist_event(mu_gfx_layer *L, const char *event, const char *args)
{
    movie *tip = &L->mv[MU_GFX_TOOLTIP];
    if (!strcmp(event, "onTooltip")) {
        int buff = (int)json_field(args, "BuffType", 0);
        static char html[8192], quoted[16384];
        if (!tip->g || !L->cfg.buff_tooltip || L->cfg.buff_tooltip(L->cfg.tooltip_user, buff, html, sizeof html))
            return;
        json_quote(quoted, sizeof quoted, html);
        tip->open = 1;
        invokef(L, MU_GFX_TOOLTIP, tip->path, "SetInfoPopup", "[%d,%d,%d,%d,%s]", (int)json_field(args, "x", 0),
                (int)json_field(args, "y", 0), 32, 32, quoted);
        logf_(L, "game: buff tooltip %d", buff);
    } else if (!strcmp(event, "offTooltip") || !strcmp(event, "offBundleTooltip")) {
        hide_tooltip(L);
    }
}

void mu_gfx_layer_set_char_rows(mu_gfx_layer *L, const mu_gfx_char_row *rows, int n)
{
    if (!L)
        return;
    free(L->char_rows);
    L->char_rows = NULL;
    L->nchar_rows = 0;
    if (n > 0 && rows && (L->char_rows = malloc((size_t)n * sizeof *rows)) != NULL) {
        memcpy(L->char_rows, rows, (size_t)n * sizeof *rows);
        L->nchar_rows = n;
    }
    L->hero_dirty_char = 1;
}

static void feed_location(mu_gfx_layer *L)
{
    const char *top = channel(L, "topmenu");
    if (!top[0])
        return;
    char q[160];
    json_quote(q, sizeof q, L->map_name);
    invokef(L, MU_GFX_MAIN, top, "setMapName", "[%s]", q);
    invokef(L, MU_GFX_MAIN, top, "setPosition", "[{\"x\":%d,\"y\":%d}]", L->map_x, L->map_y);
    L->map_sent = 1;
}

void mu_gfx_layer_set_location(mu_gfx_layer *L, const char *map, int x, int y)
{
    if (!L)
        return;
    if (map && strcmp(map, L->map_name))
        snprintf(L->map_name, sizeof L->map_name, "%s", map), L->map_sent = 0;
    if (x != L->map_x || y != L->map_y)
        L->map_x = x, L->map_y = y, L->map_sent = 0;
}

static void init_main(mu_gfx_layer *L)
{
    movie *m_main = &L->mv[MU_GFX_MAIN];
    L->main_inited = 1;
    init_menu(L);
    m_main->open = 1;
    feed_main(L);
    feed_skills(L);
    feed_item_hotkeys(L);
}

/* The chat's InitData labels (static reading of the chat handler near
 * 0x00c611e3: each member is set from GlobalText[n]). */
static const struct { const char *member; int32_t gt; const char *standin; } CHAT_TEXT[] = {
    {"strNormal", 3406, "All"},           {"strParty", 944, "Party"},     {"strGuild", 946, "Guild"},
    {"strGens", 3091, "Gens"},            {"strWhisper", 945, "Whisper"}, {"strSystem", 3407, "System"},
    {"strBlock", 4651, "Block"},          {"typeFormatWHISPER", 3813, "W"}, {"typeFormatPARTY", 3812, "P"},
    {"typeFormatGUILD", 3810, "G"},       {"typeFormatUNION", 1295, "U"}, {"typeFormatGENS", 3811, "Gens"},
};

static void init_chat(mu_gfx_layer *L)
{
    movie *chat = &L->mv[MU_GFX_CHAT];
    L->chat_inited = 1;
    char buf[2048], q[160];
    size_t n = (size_t)snprintf(buf, sizeof buf, "[{\"MaxInputSize\":\"60\",\"MaxUsetNameSize\":\"10\"");
    for (size_t i = 0; i < sizeof CHAT_TEXT / sizeof CHAT_TEXT[0] && n < sizeof buf; i++) {
        gt_quote(L, q, sizeof q, CHAT_TEXT[i].gt, CHAT_TEXT[i].standin);
        n += (size_t)snprintf(buf + n, sizeof buf - n, ",\"%s\":%s", CHAT_TEXT[i].member, q);
    }
    snprintf(buf + n, sizeof buf - n, "}]");
    invokef(L, MU_GFX_CHAT, chat->path, "InitData", "%s", buf);
    invokef(L, MU_GFX_CHAT, chat->path, "CloseEditText", "[]");
    chat->open = 1;
}

/* The base movie's UI loader list (0x00c8f05d, static), limited to the
 * movies present in the movie directory (a missing one would keep the
 * loader waiting). */
static void load_frame_files(mu_gfx_layer *L)
{
    static const struct { const char *slot; const char *files[6]; } LIST[] = {
        {"mcData", {"ImageData"}},
        {"mcTopLevel", {"Tooltip", "Popups"}},
        {"mcBottomFrame", {"main"}},
        {"mcBottom", {"ItemDurability", "Chat", "AlarmFrame", "topmenu", "bufflist"}},
        {"mcBottomHud", {"hudPlayerName", "hudMap", "hudNotice"}},
    };
    char buf[1024];
    size_t n = (size_t)snprintf(buf, sizeof buf, "[{");
    for (size_t i = 0; i < sizeof LIST / sizeof LIST[0]; i++) {
        n += (size_t)snprintf(buf + n, sizeof buf - n, "%s\"%s\":[", i ? "," : "", LIST[i].slot);
        int k = 0;
        for (int f = 0; f < 6 && LIST[i].files[f]; f++) {
            char name[96], found[4096];
            snprintf(name, sizeof name, "%s.swf", LIST[i].files[f]);
            if (L->api.resolve(L->mv[MU_GFX_MAIN].g, name, found, sizeof found) < 0) {
                logf_(L, "game: %s not converted, left out of LoadFrameFiles", name);
                continue;
            }
            n += (size_t)snprintf(buf + n, sizeof buf - n, "%s\"%s\"", k++ ? "," : "", LIST[i].files[f]);
        }
        n += (size_t)snprintf(buf + n, sizeof buf - n, "]");
    }
    snprintf(buf + n, sizeof buf - n, "}]");
    invokef(L, MU_GFX_MAIN, channel(L, "UIFrame"), "LoadFrameFiles", "%s", buf);
}

/* Deferred game-side steps (outside the movies' callbacks). */
static void pump(mu_gfx_layer *L)
{
    if (L->base_mode) {
        static const char *const SENT = "sent";
        if (channel(L, "UIFrame")[0] && strcmp(channel(L, "LoadFrameFiles"), SENT)) {
            set_channel(L, "LoadFrameFiles", SENT);
            load_frame_files(L);
        }
        if (L->ui_loaded && !L->scene_sent) {
            L->scene_sent = 1;
            invokef(L, MU_GFX_MAIN, channel(L, "UIFrame"), "changeScene", "[6]");   /* GameScene.Main */
            init_hud(L);
        }
        if (channel(L, "ASData")[0] && !L->skills_sent)
            send_skills(L);
    }
    if (L->mv[MU_GFX_MAIN].path[0] && !L->main_inited)
        init_main(L);
    if (L->mv[MU_GFX_CHAT].path[0] && !L->chat_inited)
        init_chat(L);
    if (L->icons_dirty)
        update_icons(L);
    if (L->base_mode && L->ui_loaded && !L->map_sent && L->map_name[0])
        feed_location(L);
    if (L->base_mode && L->ui_loaded)
        feed_buffs(L);                                  /* NATIVE-LANG-002 */
}

static void init_windows(mu_gfx_layer *L)
{
    movie *inv = &L->mv[MU_GFX_INVENTORY];
    if (inv->path[0]) {
        /* InitText as the inventory handler 0x00b908e4 builds it (static: Title and the buttons from
         * GlobalText; English stand-ins without the host's text). */
        static const struct { const char *member; int32_t gt; const char *standin; } INV_TEXT[] = {
            {"Title", 3453, "Inventory"},      {"Artifact", 6083, "Artifact"}, {"PrivateStore", 1102, "Personal S"},
            {"ExtensionBag", 3451, "Expanded"}, {"Repair", 1559, "Repair"},     {"Divide", 5233, "Divide"},
            {"Disassemble", 4753, "Disassemb"}, {"Bundle", 5823, "Bundle"}};
        char buf[2048], q[160];
        size_t n = (size_t)snprintf(buf, sizeof buf, "[{\"Zen\":\"\",\"Ruud\":\"\"");
        for (size_t i = 0; i < sizeof INV_TEXT / sizeof INV_TEXT[0] && n < sizeof buf; i++) {
            gt_quote(L, q, sizeof q, INV_TEXT[i].gt, INV_TEXT[i].standin);
            n += (size_t)snprintf(buf + n, sizeof buf - n, ",\"%s\":%s", INV_TEXT[i].member, q);
        }
        snprintf(buf + n, sizeof buf - n, "}]");
        invokef(L, MU_GFX_INVENTORY, inv->path, "InitText", "%s", buf);
        zen_text(L);
        slot_gap(L);
        slot_states(L);
    }
    if (L->mv[MU_GFX_CHARACTER].path[0]) {
        /* InitText as the character handler 0x00b3d161 builds it (static, GlobalText). */
        static const struct { const char *member; int32_t gt; const char *standin; } CHAR_TEXT[] = {
            {"StatButton", 4853, "Stats"},       {"PentagramButton", 4854, "Pentagram"},
            {"MasterSkillTree", 6412, "Master"}, {"SkillTree4th", 6413, "4th Tree"},
            {"SkillTree5th", 6414, "5th Tree"},  {"DetailInfo", 4856, "Details"}};
        char buf[2048], q[160];
        size_t n = (size_t)snprintf(buf, sizeof buf, "[{");
        for (size_t i = 0; i < sizeof CHAR_TEXT / sizeof CHAR_TEXT[0] && n < sizeof buf; i++) {
            gt_quote(L, q, sizeof q, CHAR_TEXT[i].gt, CHAR_TEXT[i].standin);
            n += (size_t)snprintf(buf + n, sizeof buf - n, "%s\"%s\":%s", i ? "," : "", CHAR_TEXT[i].member, q);
        }
        snprintf(buf + n, sizeof buf - n, "}]");
        invokef(L, MU_GFX_CHARACTER, L->mv[MU_GFX_CHARACTER].path, "InitText", "%s", buf);
    }
    skill_init_window(L);
    window_sizes(L);
    for (int m = MU_GFX_INVENTORY; m < MU_GFX_MOVIES; m++)
        if (L->mv[m].g && L->mv[m].path[0] && m != MU_GFX_TOOLTIP && m != MU_GFX_CHAT)
            invokef(L, m, L->mv[m].path, "SetVisible", "[false]");
    hide_tooltip(L);
    L->order[L->norder++] = MU_GFX_INVENTORY;
    L->order[L->norder++] = MU_GFX_CHARACTER;
}

static void init_movies(mu_gfx_layer *L)
{
    movie *m_main = &L->mv[MU_GFX_MAIN], *chat = &L->mv[MU_GFX_CHAT];
    if (L->base_mode) {
        /* base.swf runs the client's loader by itself (its onLoad loads
         * ExternalBase.swf); the game side answers its channels (pump).
         * Advance until the UI loader finished (bounded). */
        for (int i = 0; i < 200 && !(L->ui_loaded && L->main_inited && L->chat_inited && L->skills_sent); i++) {
            L->api.advance(m_main->g, 40.0);
            pump(L);
        }
        logf_(L, "game: base movie %s (UIFrame %s, main %s, chat %s)", L->ui_loaded ? "loaded" : "NOT loaded",
              channel(L, "UIFrame"), m_main->path, chat->path);
    } else {
        /* main.gfx places Frame.Main as "mc"; the client's UI loader triggers
         * its onFileLoad, which reports main/onLoad with the path (layer plays
         * the loader). */
        invokef(L, MU_GFX_MAIN, "_level0.mc", "onFileLoad", "[]");
        /* chat.swf is a symbol library; the UI loader attaches "Chat" (layer plays it). */
        if (chat->g) {
            invokef(L, MU_GFX_CHAT, "_level0", "attachMovie", "[\"Chat\",\"mc\",10]");
            L->api.advance(chat->g, 0.0);
            invokef(L, MU_GFX_CHAT, "_level0.mc", "onFileLoad", "[]");
        }
        pump(L);
    }
    init_windows(L);
}

/* Demo skill table (layer choice): indices 1..60, icon = index (the
 * installed leftover skill.bmd carries Magic_Icon = index for these), the
 * normal skill sheet (SkillUseType 0).  Hosts replace it with
 * mu_gfx_layer_set_skills. */
static void demo_skills(mu_gfx_layer *L)
{
    L->nskills = 0;
    for (int i = 1; i <= 60 && L->nskills < MAX_SKILLS; i++) {
        mu_gfx_skill *k = &L->skills[L->nskills++];
        memset(k, 0, sizeof *k);
        k->index = i;
        k->icon = i;
        snprintf(k->name, sizeof k->name, "Skill %d", i);
    }
}

void mu_gfx_layer_set_skills(mu_gfx_layer *L, const mu_gfx_skill *skills, int n)
{
    if (!L || !skills || n < 0)
        return;
    L->nskills = n > MAX_SKILLS ? MAX_SKILLS : n;
    memcpy(L->skills, skills, (size_t)L->nskills * sizeof *skills);
    L->skills_sent = 0;
    if (L->base_mode && channel(L, "ASData")[0])
        send_skills(L);
    if (L->main_inited)
        feed_skills(L);   /* the slots look their skills up again */
}

int mu_gfx_layer_base_mode(const mu_gfx_layer *L) { return L && L->base_mode; }
float mu_gfx_layer_window_scale(const mu_gfx_layer *L, int movie_id)
{
    return L && movie_id >= 0 && movie_id < MU_GFX_MOVIES && L->applied_scale[movie_id] > 0
               ? L->applied_scale[movie_id] : 1.0f;
}
void mu_gfx_layer_window_position(const mu_gfx_layer *L, int movie_id, float *x, float *y)
{
    if (x)
        *x = L && movie_id >= 0 && movie_id < MU_GFX_MOVIES ? L->mv[movie_id].win_x : 0;
    if (y)
        *y = L && movie_id >= 0 && movie_id < MU_GFX_MOVIES ? L->mv[movie_id].win_y : 0;
}

const char *mu_gfx_layer_channel_path(const mu_gfx_layer *L, const char *name)
{
    return L && name ? channel(L, name) : "";
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
    swin_init(L);
    L->inv_scale = L->char_scale = 1.0f;
    L->hotkeys[0].code = 14 * 512 + 3;              /* demo hotkey item: a healing potion (layer choice) */
    demo_skills(L);
    {
        char base[4096];
        snprintf(base, sizeof base, "%s/base.swf", c->movie_dir);
        L->base_mode = !c->standalone && access(base, R_OK) == 0;
    }
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
    if (L->mv[MU_GFX_PARTY].g) {
        movie *party = &L->mv[MU_GFX_PARTY];
        L->api.set_variable(party->g, "_global.gSystem", "{\"isClient\":true}");
        L->api.set_variable(party->g, "_global.gStandard", "{\"ResizeStageHeight\":700}");
        snprintf(party->path, sizeof party->path, "_level0.instance1");
        invokef(L, MU_GFX_PARTY, party->path, "onFileLoad", "[]");
    }
    for (int k = MU_GFX_OPTION; k <= MU_GFX_SYSTEM_MENU; k++) {   /* NATIVE-PROGRESS-001: the KeyWindows' loader */
        movie *w = &L->mv[k];
        if (!w->g)
            continue;
        L->api.set_variable(w->g, "_global.gSystem", "{\"isClient\":true}");
        L->api.set_variable(w->g, "_global.gStandard", "{\"ResizeStageHeight\":700}");
        snprintf(w->path, sizeof w->path, "_level0.instance1");
        invokef(L, k, w->path, "onFileLoad", "[]");
    }
    if (L->mv[MU_GFX_QUEST_SUMMARY].g) {
        /* MovieLoader normally supplies these globals and calls onFileLoad on the placed "win" clip.
         * Each optional window has its own player here, so perform that loader lifecycle explicitly. */
        movie *summary = &L->mv[MU_GFX_QUEST_SUMMARY];
        L->api.set_variable(summary->g, "_global.gSystem", "{\"isClient\":true}");
        L->api.set_variable(summary->g, "_global.gStandard", "{\"ResizeStageHeight\":700}");
        snprintf(summary->path, sizeof summary->path, "_level0.win");
        invokef(L, MU_GFX_QUEST_SUMMARY, summary->path, "onFileLoad", "[]");
    }
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
        if (mv->g && !mv->alias)
            L->api.close(mv->g);
        free(mv->rgba);
    }
    free(L->icon_rgba);
    free(L->char_rows);
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
        if (L->mv[m].g && !L->mv[m].alias) {
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
    if (L && h) {
        if (h->has_derived && memcmp(&L->hero, h, sizeof *h))   /* NATIVE-PROGRESS-001: the rows follow */
            L->hero_dirty_char = 1;
        L->hero = *h;
    }
}

void mu_gfx_layer_exp_data(mu_gfx_layer *L, const char *json)
{
    if (!L)
        return;
    snprintf(L->exp_json, sizeof L->exp_json, "%s", json ? json : "");
    L->exp_json_dirty = 1;
}

const mu_gfx_hero *mu_gfx_layer_hero(const mu_gfx_layer *L)
{
    return L ? &L->hero : NULL;
}

/* ---- views: each player sized to its window ----------------------------------------------------- */

static int visible(const mu_gfx_layer *L, int m)
{
    const movie *mv = &L->mv[m];
    return mv->g && !mv->alias && mv->open;
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
            if (stack[i] != MU_GFX_MAIN && stack[i] != MU_GFX_CHAT && stack[i] != MU_GFX_TOOLTIP)
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

static int service_focus(const mu_gfx_layer *L)
{
    if(!L)return -1;
    for(int k=L->norder-1;k>=0;k--) {
        int m=L->order[k];
        if(m>=MU_GFX_STORE_LIST && L->mv[m].g && L->mv[m].open && L->api.text_focus(L->mv[m].g))return m;
    }
    return -1;
}

int mu_gfx_layer_text_active(const mu_gfx_layer *L)
{
    if(service_focus(L)>=0)return 1;
    if (L && L->mv[MU_GFX_MESSENGER].open && L->mv[MU_GFX_MESSENGER].g &&
        L->api.text_focus(L->mv[MU_GFX_MESSENGER].g)) return 1;
    return L && L->chat_edit;
}

int mu_gfx_layer_key(mu_gfx_layer *L, int down, int vk, uint32_t codepoint, int mods)
{
    if (!L)
        return 0;
    int focused=service_focus(L);
    if(focused>=0) {
        if(!inventory_busy(L)) {
            if(down && vk==27)mu_gfx_layer_show(L,focused,0);
            else L->api.key(L->mv[focused].g,down?0:1,vk,codepoint,mods);
        }
        return 1;
    }
    if (L->mv[MU_GFX_MESSENGER].open && L->mv[MU_GFX_MESSENGER].g &&
        L->api.text_focus(L->mv[MU_GFX_MESSENGER].g)) {
        L->api.key(L->mv[MU_GFX_MESSENGER].g, down ? 0 : 1, vk, codepoint, mods);
        return 1;
    }
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
    /* The bar's own Key listener turns digit/QWER keys into onSelectSkill
     * (SkillHotKeyPage.onKeyDown); keys it uses belong to the interface. */
    L->key_used = 0;
    L->api.key(main->g, down ? 0 : 1, vk, codepoint, mods);
    int used = L->key_used;
    /* Window hotkeys: the client's own key scan opens the windows (the menu
     * ids of InitMenuInfo are not key codes, so Frame.Main.onKeyUp does not
     * produce them); the scan is not reconstructed, the layer maps I/V, C
     * and Esc (layer choice). */
    if (down && !mods && L->socialh.key && L->socialh.key(L->socialh.user, vk))
        return 1;
    if (down && !mods && L->maph.key && L->maph.key(L->maph.user, vk))
        return 1;                            /* NATIVE-MAP-001: M (Move window) */
    if (down && !mods && L->cfg.window_key && L->cfg.window_key(L->cfg.tooltip_user, vk))
        return 1;                            /* NATIVE-QUEST-001: the host's window hotkeys (T, the quest window keys) */
    if (down && !mods) {
        if (vk == 'I' || vk == 'V') {
            mu_gfx_layer_toggle(L, MU_GFX_INVENTORY);
            used = 1;
        } else if (vk == 'C') {
            mu_gfx_layer_toggle(L, MU_GFX_CHARACTER);
            used = 1;
        } else if (vk == 'U' && L->mv[MU_GFX_SKILL_STAMP].g && L->mv[MU_GFX_SKILL_STAMP].path[0]) {
            /* NATIVE-SKILL-001: the client's key scan toggles SkillStampFrame on U (0x00efcea8) */
            mu_gfx_layer_toggle(L, MU_GFX_SKILL_STAMP);
            used = 1;
        } else if (vk == 'A' && L->mv[MU_GFX_MASTER_TREE].g) {
            mu_gfx_layer_toggle(L, MU_GFX_MASTER_TREE);
            used = 1;
        } else if (vk == 27 && (L->mv[MU_GFX_MASTER_TREE].open || L->mv[MU_GFX_TREE4].open || L->mv[MU_GFX_TREE5].open)) {
            mu_gfx_layer_show(L, MU_GFX_MASTER_TREE, 0);
            mu_gfx_layer_show(L, MU_GFX_TREE4, 0);
            mu_gfx_layer_show(L, MU_GFX_TREE5, 0);
            mu_gfx_layer_skill_popup(L, 0, 0, NULL, NULL);
            used = 1;
        } else if (vk==27 && (L->mv[MU_GFX_STORE_REGISTER].open || L->mv[MU_GFX_STORE_PURCHASE].open || L->mv[MU_GFX_STORE_LIST].open)) {
            int m=L->mv[MU_GFX_STORE_REGISTER].open?MU_GFX_STORE_REGISTER:L->mv[MU_GFX_STORE_PURCHASE].open?MU_GFX_STORE_PURCHASE:MU_GFX_STORE_LIST;
            mu_gfx_layer_show(L,m,0);return 1;
        } else if (vk == 27 && (L->mv[MU_GFX_MIX].open || L->mv[MU_GFX_MIX_SELECT].open)) {
            mu_gfx_layer_show(L,MU_GFX_MIX,0);
            mu_gfx_layer_show(L,MU_GFX_MIX_SELECT,0);
            used=1;
        } else if (vk == 27 && (L->mv[MU_GFX_INVENTORY].open || L->mv[MU_GFX_CHARACTER].open ||
                                L->mv[MU_GFX_SKILL_STAMP].open)) {
            mu_gfx_layer_show(L, MU_GFX_INVENTORY, 0);
            mu_gfx_layer_show(L, MU_GFX_CHARACTER, 0);
            mu_gfx_layer_show(L, MU_GFX_SKILL_STAMP, 0);
            used = 1;
        } else if (vk == 'O' && L->mv[MU_GFX_OPTION].g && L->cfg.progress_call) {   /* NATIVE-PROGRESS-001 */
            L->cfg.progress_call(L->cfg.tooltip_user, MU_GFX_OPTION, "key", "[79]");
            used = 1;
        } else if (vk == 27 && L->mv[MU_GFX_SYSTEM_MENU].g && L->cfg.progress_call) {
            L->cfg.progress_call(L->cfg.tooltip_user, MU_GFX_SYSTEM_MENU, "key", "[27]");
            used = 1;
        }
    }
    static const int UI_KEYS[] = {'I', 'V', 'C', 'X', 'K', 'T', 'F', 'U', '0', '1', '2', '3', '4', '5', '6', '7', '8',
                                  '9'};
    for (size_t i = 0; i < sizeof UI_KEYS / sizeof UI_KEYS[0]; i++)
        if (vk == UI_KEYS[i])
            used = 1;
    if (vk == 27 && (L->mv[MU_GFX_INVENTORY].open || L->mv[MU_GFX_CHARACTER].open))
        used = 1;
    return used;
}

int mu_gfx_layer_text(mu_gfx_layer *L, const char *utf8)
{
    int focused=service_focus(L);
    if(focused>=0) {if(!inventory_busy(L))L->api.text(L->mv[focused].g,utf8);return 1;}
    if (L && L->mv[MU_GFX_MESSENGER].open && L->mv[MU_GFX_MESSENGER].g &&
        L->api.text_focus(L->mv[MU_GFX_MESSENGER].g)) {
        L->api.text(L->mv[MU_GFX_MESSENGER].g, utf8);
        return 1;
    }
    if (!L || !L->chat_edit || !L->mv[MU_GFX_CHAT].g)
        return 0;
    if (L->composing) {   /* the IME committed: the composing text is replaced */
        L->api.ime(L->mv[MU_GFX_CHAT].g, "", -1, 0);
        L->composing = 0;
        L->compose[0] = 0;
    }
    L->api.text(L->mv[MU_GFX_CHAT].g, utf8);
    return 1;
}

int mu_gfx_layer_compose(mu_gfx_layer *L, const char *utf8, int cursor)
{
    int focused=service_focus(L);
    if(focused>=0) {
        int byte=0;
        for(int k=0;utf8 && utf8[byte] && k<cursor;k++) {byte++;while((utf8[byte]&0xc0)==0x80)byte++;}
        if(!inventory_busy(L))L->api.ime(L->mv[focused].g,utf8?utf8:"",cursor<0?-1:byte,0);
        return 1;
    }
    /* The composing text goes into the chat's input field as Ruffle's IME
     * preedit (the client shows it through its own IME movie IME.swf and
     * fscommand TextInput; that path is not played, layer choice). */
    if (!L || !L->chat_edit || !L->mv[MU_GFX_CHAT].g)
        return 0;
    snprintf(L->compose, sizeof L->compose, "%s", utf8 ? utf8 : "");
    L->composing = L->compose[0] != 0;
    /* cursor: code points (SDL) -> UTF-8 bytes (mugfx_ime) */
    int byte = cursor < 0 ? -1 : 0;
    for (int cp = 0; cursor >= 0 && cp < cursor && L->compose[byte]; cp++)
        do
            byte++;
        while ((L->compose[byte] & 0xc0) == 0x80);
    L->api.ime(L->mv[MU_GFX_CHAT].g, L->compose, byte, 0);
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
        skill_feed(L);
        mix_step(L);
        service_step(L);
    }
    for (int m = 0; m < MU_GFX_MOVIES; m++)
        if (L->mv[m].g && !L->mv[m].alias && (visible(L, m) || m == MU_GFX_CHAT || m == MU_GFX_TOOLTIP))
            L->api.advance(L->mv[m].g, dt);
    pump(L);
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
    if (submitted && !L->cfg.double_buffer) {
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

/* Items over the inventory, placed by the reconstructed slot pass: the
 * host's item models (cfg.items) or coloured stand-ins. */
#define RECT_MAX (SLOT_ITEMS + 8)
typedef struct rect_list {
    float r[RECT_MAX][4];
    int item[RECT_MAX];
    mu_slot_call call[RECT_MAX];
    int n;
    mu_gfx_layer *L;
    const item *base;           /* the window's item array (inventory or slot window) */
} rect_list;

static void emit_rect(void *user, const mu_slot_call *call)
{
    rect_list *R = user;
    mu_gfx_layer *L = R->L;
    if (R->base == L->items) {
        int i = (int)((const item *)call->item - L->items);
        if (i >= 0 && i < MAX_ITEMS && L->trade_reserved[i]) return;
    }
    if (R->n >= RECT_MAX - 1)
        return;
    /* 640 x 480 units back to window pixels (0x0184a18f, top-left origin here). */
    float *r = R->r[R->n];
    r[0] = call->x / mu_gfx_rate_x(L->w);
    r[1] = call->y / mu_gfx_rate_y(L->h);
    r[2] = call->w / mu_gfx_rate_x(L->w);
    r[3] = call->h / mu_gfx_rate_y(L->h);
    R->call[R->n] = *call;
    R->item[R->n++] = (int)((const item *)call->item - R->base);
}

static void item_rects(mu_gfx_layer *L, rect_list *R)
{
    R->n = 0;
    R->L = L;
    R->base = L->items;
    if (!L->have_slot || !L->mv[MU_GFX_INVENTORY].open)
        return;
    mu_slot_page page = {&L->grid, L->slot_x, L->slot_y, L->slot_w, L->slot_h, L->gap_x, L->gap_y};
    mu_slot_frame frame = {1, MU_ALIGN_TOP_LEFT, L->win_x, L->win_y, 1.0f, L->inv_scale, &page, 1, 1};
    mu_slot_pass(&frame, L->w, L->h, mu_gfx_rate_x(L->w), mu_gfx_rate_y(L->h), NULL, emit_rect, R);
}

static int held_rect(const mu_gfx_layer *L, float r[4])
{
    if (L->held < 0)
        return 0;
    const item *it = &L->items[L->held];
    r[2] = it->grid.width * (L->slot_w > 0 ? L->slot_w : 26) * L->inv_scale;
    r[3] = it->grid.height * (L->slot_h > 0 ? L->slot_h : 26) * L->inv_scale;
    r[0] = (float)L->mouse_x - r[2] / 2;
    r[1] = (float)L->mouse_y - r[3] / 2;
    return 1;
}

static void item_draw_from(const mu_gfx_layer *L, int idx, const float rect[4], mu_gfx_item_draw *d)
{
    const item *it = &L->items[idx];
    memset(d, 0, sizeof *d);
    d->item = idx;
    d->code = it->grid.code;
    d->level = it->level;
    d->has_options = it->has_data;
    d->level_word =
        it->has_data ? (it->data[1] & 0x84) | (it->level << 3) | (it->option & 3) : it->level << 3;
    d->excellent = it->excellent;
    d->set_bits = it->set_bits;
    d->element = it->element;
    memcpy(d->rect, rect, sizeof d->rect);
    d->slot[0] = rect[0] * mu_gfx_rate_x(L->w);
    d->slot[1] = rect[1] * mu_gfx_rate_y(L->h);
    d->slot[2] = rect[2] * mu_gfx_rate_x(L->w);
    d->slot[3] = rect[3] * mu_gfx_rate_y(L->h);
    d->frame_scale = L->inv_scale;
    d->alpha = 1.0f;
    d->page_type = 1;
}

static int build_item_draws(mu_gfx_layer *L, const rect_list *R, mu_gfx_item_draw *draws, int max)
{
    int n = 0;
    for (int i = 0; i < R->n && n < max; i++) {
        mu_gfx_item_draw *d = &draws[n++];
        item_draw_from(L, R->item[i], R->r[i], d);
        d->slot[0] = R->call[i].x;     /* the slot pass's own 640 x 480 values */
        d->slot[1] = R->call[i].y;
        d->slot[2] = R->call[i].w;
        d->slot[3] = R->call[i].h;
        d->page_type = R->call[i].page_type;
        d->page_flag = R->call[i].page_flag;
        d->type8_seen = R->call[i].type8_seen;
        d->frame_id = (int32_t)R->call[i].frame_id;
        int cell = L->hover;
        d->select = cell >= 0 && cell < L->grid.cols * L->grid.rows && L->grid.cells[cell] &&
                    mu_grid_item_at(&L->grid, cell) == &L->items[R->item[i]].grid;
    }
    return n;
}

#ifndef MU_GFX_NO_GL
/* The per-window item pass of the inventory (0x00abfcca) through the host. */
static int host_items(mu_gfx_layer *L, const rect_list *R)
{
    if (!L->cfg.items)
        return 0;
    mu_gfx_item_draw draws[MAX_ITEMS + 1];
    int n = build_item_draws(L, R, draws, MAX_ITEMS + 1);
    L->cfg.items(L->cfg.items_user, draws, n, L->w, L->h);
    return 1;
}
#endif

int mu_gfx_layer_item_draws(mu_gfx_layer *L, mu_gfx_item_draw *out, int max)
{
    if (!L || !out)
        return 0;
    rect_list R;
    item_rects(L, &R);
    return build_item_draws(L, &R, out, max);
}

#ifndef MU_GFX_NO_GL
static int host_held(mu_gfx_layer *L, const float r[4])
{
    if (!L->cfg.items)
        return 0;
    mu_gfx_item_draw d;
    item_draw_from(L, L->held, r, &d);
    d.held = 1;
    L->cfg.items(L->cfg.items_user, &d, 1, L->w, L->h);
    return 1;
}
#endif

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
        swin_composite(L, order[k], rgba, W, H);
        mu_gfx_item_draw service_items[SERVICE_BUNDLE];
        int ns=service_draws(L,order[k],service_items,SERVICE_BUNDLE);
        for(int j=0;j<ns;j++)fill_cpu(rgba,W,H,service_items[j].rect,(float[]){.8f,.6f,.3f},L->scale);
        if (order[k] == MU_GFX_SKILL_STAMP)
            skill_composite(L, rgba, W, H);
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

/* The host's item pass runs with its own matrices and state. */
static void host_gl_begin(const mu_gfx_layer *L)
{
    if (!L->cfg.items)
        return;
    glPushAttrib(GL_ALL_ATTRIB_BITS);
    glMatrixMode(GL_PROJECTION);
    glPushMatrix();
    glMatrixMode(GL_MODELVIEW);
    glPushMatrix();
}

static void host_gl_end(const mu_gfx_layer *L)
{
    if (!L->cfg.items)
        return;
    glMatrixMode(GL_PROJECTION);
    glPopMatrix();
    glMatrixMode(GL_MODELVIEW);
    glPopMatrix();
    glPopAttrib();
    glBindTexture(GL_TEXTURE_2D, 0);
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

/* ---- NPC windows (NATIVE-NPC-001) ---------------------------------------------------------------- */

static slot_window *swin_for(mu_gfx_layer *L, int m)
{
    return m == MU_GFX_NPC_SHOP ? &L->swin[0] : m == MU_GFX_STORAGE ? &L->swin[1] : m == MU_GFX_MIX ? &L->swin[2] : NULL;
}

static void npc_last(mu_gfx_layer *L, const char *fmt, ...)
{
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(L->npc_last, sizeof L->npc_last, fmt, ap);
    va_end(ap);
    logf_(L, "game: %s", L->npc_last);
}

static void swin_slot_states(mu_gfx_layer *L, slot_window *sw)
{
    movie *mv = &L->mv[sw->movie];
    if (!mv->path[0])
        return;
    char list[1024];
    size_t n = 0;
    for (int i = 0; i < sw->grid.cols * sw->grid.rows && n < sizeof list; i++)
        n += (size_t)snprintf(list + n, sizeof list - n, "%s%d", i ? "," : "", sw->grid.cells[i] ? 2 : 1);
    invokef(L, sw->movie, mv->path, "SetSlotStateAll", "[0,\"%s\"]", list);
}

static void swin_gap(mu_gfx_layer *L, slot_window *sw)
{
    movie *mv = &L->mv[sw->movie];
    char p[192];
    double v[4];
    static const char *const SLOT[4] = {"isSlot0._x", "isSlot1._x", "isSlot0._y", "isSlot8._y"};
    for (int k = 0; k < 4; k++) {
        snprintf(p, sizeof p, "%s.%s.%s", mv->path, sw->frame, SLOT[k]);
        const char *a = L->api.get_variable(mv->g, p);
        v[k] = a ? atof(a) : 0;
    }
    sw->gap_x = v[1] > v[0] ? (float)(v[1] - v[0]) - sw->slot_w : 0;
    sw->gap_y = v[3] > v[2] ? (float)(v[3] - v[2]) - sw->slot_h : 0;
    sw->gap_done = 1;
}

static void swin_clear(slot_window *sw)
{
    int32_t type = sw->grid.type;
    mu_grid_construct(&sw->grid);
    mu_grid_init(&sw->grid, type, 0, 0, 0, 8, sw->movie == MU_GFX_MIX ? 4 : 15, 0);
    sw->nitems = 0;
    sw->hover = -1;
}

static int swin_add(slot_window *sw, const mu_gfx_slot_item *src)
{
    int index;
    for(index=0;index<sw->nitems;index++) {
        int owned=0;
        for(int k=0;k<sw->grid.item_count;k++)owned|=sw->grid.items[k]==&sw->items[index].grid;
        if(!owned)break;
    }
    if(index>=SLOT_ITEMS)return -1;
    item *it = &sw->items[index];
    memset(it, 0, sizeof *it);
    it->grid.id = (uint32_t)(1000 + index);
    it->grid.code = src->code;
    it->grid.width = (uint8_t)(src->width < 1 ? 1 : src->width);
    it->grid.height = (uint8_t)(src->height < 1 ? 1 : src->height);
    it->level = src->level;
    item_instance(it, src);
    snprintf(it->name, sizeof it->name, "%s", src->name[0] ? src->name : "Item");
    int col, row;
    if (!mu_grid_find_free(&sw->grid, it->grid.width, it->grid.height, &col, &row))
        return -1;
    mu_grid_place(&sw->grid, col, row, &it->grid);
    static const float PALETTE[8][3] = {{.85f, .35f, .25f}, {.35f, .55f, .9f}, {.95f, .8f, .3f}, {.55f, .75f, .4f},
                                        {.7f, .45f, .85f}, {.3f, .8f, .8f}, {.9f, .55f, .2f}, {.8f, .8f, .8f}};
    memcpy(it->rgb, PALETTE[(src->code >> 9) & 7], sizeof it->rgb);
    sw->prices[index] = src->price;
    if(index==sw->nitems)sw->nitems++;
    return index;
}

static void swin_show_tooltip(mu_gfx_layer *L, slot_window *sw, int cell)
{
    movie *tip = &L->mv[MU_GFX_TOOLTIP];
    mu_grid_item *gi = cell >= 0 && cell < sw->grid.cols * sw->grid.rows ? mu_grid_item_at(&sw->grid, cell) : NULL;
    if (!tip->g || !gi || !sw->grid.cells[cell])
        return;
    item *it = (item *)gi;
    static char html[8192], quoted[16384];
    int context = sw->movie == MU_GFX_NPC_SHOP ? MU_GFX_TIP_SHOP : MU_GFX_TIP_PLAIN;   /* NATIVE-LANG-002 */
    if (L->cfg.tooltip_ex ? L->cfg.tooltip_ex(L->cfg.tooltip_user, it->grid.code, it->level, context, html, sizeof html)
                          : (!L->cfg.tooltip || L->cfg.tooltip(L->cfg.tooltip_user, it->grid.code, it->level, html,
                                                               sizeof html)))
        builtin_tooltip(it, html, sizeof html);
    if (it->has_data && L->cfg.tooltip_packet) {
        uint8_t wire[15];
        item_wire(it, wire);
        L->cfg.tooltip_packet(L->cfg.tooltip_user, wire, context, html, sizeof html);
    }
    json_quote(quoted, sizeof quoted, html);
    float sc = sw->scale;
    float x = sw->win_x + (sw->slot_x + it->grid.col * (sw->slot_w + sw->gap_x)) * sc;
    float y = sw->win_y + (sw->slot_y + it->grid.row * (sw->slot_h + sw->gap_y)) * sc;
    tip->open = 1;
    invokef(L, MU_GFX_TOOLTIP, tip->path, "SetInfoPopup", "[%d,%d,%d,%d,%s]", (int)x, (int)y,
            (int)(it->grid.width * sw->slot_w * sc), (int)(it->grid.height * sw->slot_h * sc), quoted);
}

/* A click on a slot: NpcShop buys (DEMO: the item goes to the first free
 * inventory place and its price leaves the zen), StorageInven moves
 * the item to the inventory (DEMO).  The client sends a request and waits
 * for the server's answer instead. */
static void item_slot(const item *it, mu_gfx_slot_item *out) {
    memset(out, 0, sizeof *out);
    out->code = it->grid.code;
    out->level = it->level;
    out->width = it->grid.width;
    out->height = it->grid.height;
    out->has_data = 1;
    out->excellent = it->excellent;
    out->set_bits = it->set_bits;
    out->element = it->element;
    item_wire(it, out->data);
    snprintf(out->name, sizeof out->name, "%s", it->name);
}
static void swin_click(mu_gfx_layer *L, slot_window *sw, int index)
{
    if (inventory_busy(L)) return;
    mu_grid_item *gi = index >= 0 && index < sw->grid.cols * sw->grid.rows ? mu_grid_item_at(&sw->grid, index) : NULL;
    if (!gi || !sw->grid.cells[index])
        return;
    item *it = (item *)gi;
    int k = (int)(it - sw->items);
    mu_gfx_slot_item transfer;
    item_slot(it, &transfer);
    if (sw->movie == MU_GFX_NPC_SHOP) {
        if (L->hero.zen < sw->prices[k]) {
            npc_last(L, "buy %s: not enough zen (demo)", it->name);
            return;
        }
        if (mu_gfx_layer_add_slot_item(L, &transfer) < 0) {
            npc_last(L, "buy %s: no room in the inventory (demo)", it->name);
            return;
        }
        L->hero.zen -= sw->prices[k];
        zen_text(L);
        npc_last(L, "bought %s for %lld zen (demo)", it->name, (long long)sw->prices[k]);
    } else {
        int added = mu_gfx_layer_add_slot_item(L, &transfer);
        if (added < 0) {
            npc_last(L, "take %s: no room in the inventory (demo)", it->name);
            return;
        }
        L->items[added].option=it->option;L->items[added].excellent=it->excellent;
        L->items[added].durability=it->durability;L->items[added].period=it->period;
        mu_grid_remove(&sw->grid, gi);
        hide_tooltip(L);
        swin_slot_states(L, sw);
        npc_last(L, "took %s from the vault (demo)", it->name);
    }
}

/* A right click on an inventory item while NpcShop or StorageInven is open:
 * sell it (DEMO sale at the client's sell price, NATIVE-LANG-002) or put it into the vault
 * (layer choice for the client's drag onto the window). */
static int npc_inventory_r(mu_gfx_layer *L, int index)
{
    if (inventory_busy(L)) return 1;
    int shop = L->mv[MU_GFX_NPC_SHOP].open, vault = L->mv[MU_GFX_STORAGE].open;
    if (!shop && !vault)
        return 0;
    mu_grid_item *gi = index >= 0 && index < L->grid.cols * L->grid.rows ? mu_grid_item_at(&L->grid, index) : NULL;
    if (!gi || !L->grid.cells[index])
        return 1;
    item *it = (item *)gi;
    if (item_reserved(L,(int)(it-L->items))) {
        npc_last(L, "item reserved for trade (demo)");
        return 1;
    }
    if (shop) {
        /* NATIVE-LANG-002: the client's sell price ItemValue(item, 1) when the host has it (the server decides
         * the sale in the real game) */
        int64_t price = L->cfg.price_ex ? L->cfg.price_ex(L->cfg.tooltip_user, it->grid.code, it->level, 1)
                        : L->cfg.price ? L->cfg.price(L->cfg.tooltip_user, it->grid.code, it->level) / 3 : 0;
        mu_grid_remove(&L->grid, gi);
        L->hero.zen += price;
        zen_text(L);
        npc_last(L, "sold %s for %lld zen (demo)", it->name, (long long)price);
    } else {
        slot_window *sw = &L->swin[1];
        mu_gfx_slot_item s;
        item_slot(it, &s);
        int added=swin_add(sw,&s);
        if (added < 0) {
            npc_last(L, "put %s: the vault is full (demo)", it->name);
            return 1;
        }
        sw->items[added].option=it->option;sw->items[added].excellent=it->excellent;
        sw->items[added].durability=it->durability;sw->items[added].period=it->period;
        mu_grid_remove(&L->grid, gi);
        swin_slot_states(L, sw);
        npc_last(L, "put %s into the vault (demo)", it->name);
    }
    it->grid.code=-1;
    hide_tooltip(L);
    slot_states(L);
    return 1;
}

/* npcdialogue pages: the movie wraps the text (SetDialogueMentDivide ->
 * NPCDialogTextWidth(lines, wrapped)); the layer shows MU_DLG_LINES lines a
 * page (layer choice) with SetDialogueMent(text, page) as the handler's
 * "%s %d" invoke 0x00be8724 does, and the arrows when there are more. */
#define MU_DLG_LINES 6
static void dialog_page(mu_gfx_layer *L)
{
    movie *mv = &L->mv[MU_GFX_NPC_DIALOG];
    char q[2200];
    json_quote(q, sizeof q, L->dlg.pages[L->dlg.page]);
    invokef(L, MU_GFX_NPC_DIALOG, mv->path, "SetDialogueMent", "[%s,%d]", q, L->dlg.page);
    invokef(L, MU_GFX_NPC_DIALOG, mv->path, "VisibleArrowBtn", "[%s,%s]", L->dlg.page > 0 ? "true" : "false",
            L->dlg.page + 1 < L->dlg.npages ? "true" : "false");
}

static void dialog_wrapped(mu_gfx_layer *L, const char *wrapped)
{
    L->dlg.npages = 0;
    const char *p = wrapped;
    while (*p && L->dlg.npages < 16) {
        char *page = L->dlg.pages[L->dlg.npages++];
        size_t n = 0;
        for (int line = 0; line < MU_DLG_LINES && *p; line++) {
            const char *nl = strchr(p, '\n');
            size_t len = nl ? (size_t)(nl - p) : strlen(p);
            if (n + len + 2 >= sizeof L->dlg.pages[0])
                len = sizeof L->dlg.pages[0] - n - 2;
            memcpy(page + n, p, len);
            n += len;
            p += len;
            if (*p == '\n')
                p++;
            if (line + 1 < MU_DLG_LINES && *p)
                page[n++] = '\n';
        }
        page[n] = 0;
    }
    if (!L->dlg.npages) {
        L->dlg.npages = 1;
        L->dlg.pages[0][0] = 0;
    }
    L->dlg.page = 0;
    dialog_page(L);
}

static void dialog_send(mu_gfx_layer *L)
{
    movie *mv = &L->mv[MU_GFX_NPC_DIALOG];
    char q[4400], list[1600];
    json_quote(q, sizeof q, L->dlg.title);
    invokef(L, MU_GFX_NPC_DIALOG, mv->path, "SetTitle", "[%s]", q);
    /* 0x00be84ac: VisibleContribute(0) only for the dialogue NPCs 0x248, 0x2fc, 0x2fd, 0x3ab, 0x3ac */
    if (L->dlg.hide_contribute)
        invokef(L, MU_GFX_NPC_DIALOG, mv->path, "VisibleContribute", "[0]");
    /* 0x00be89f7: SetDialogueMentDivide(text, ";"): the client's dialogue text separates lines with ';';
     * the movie answers with NPCDialogTextWidth, which pages the text (dialog_wrapped). */
    json_quote(q, sizeof q, L->dlg.text);
    L->dlg.wrapped = 0;
    invokef(L, MU_GFX_NPC_DIALOG, mv->path, "SetDialogueMentDivide", "[%s,\";\"]", q);
    if (!L->dlg.wrapped) {   /* no callback (stand-in movie): the lines as they are */
        char plain[4096];
        snprintf(plain, sizeof plain, "%s", L->dlg.text);
        for (char *p = plain; *p; p++)
            if (*p == ';')
                *p = '\n';
        dialog_wrapped(L, plain);
    }
    size_t n = 0;
    list[0] = 0;
    for (int i = 0; i < L->dlg.noptions && n < sizeof list; i++)
        n += (size_t)snprintf(list + n, sizeof list - n, "%d. %s;", i + 1, L->dlg.options[i]);
    json_quote(q, sizeof q, list);
    invokef(L, MU_GFX_NPC_DIALOG, mv->path, "SetSelectBtnContent", "[%s]", q);
    invokef(L, MU_GFX_NPC_DIALOG, mv->path, "SetPosLeftCenter", "[]");
}

static void npc_open_window(mu_gfx_layer *L, int m)
{
    for (int k = MU_GFX_NPC_DIALOG; k <= MU_GFX_STORAGE; k++)
        if (k != m)
            mu_gfx_layer_show(L, k, 0);
    mu_gfx_layer_show(L, m, 1);
}

int mu_gfx_layer_npc_dialog(mu_gfx_layer *L, const mu_gfx_npc_dialog *d)
{
    if (!L || !d || !L->mv[MU_GFX_NPC_DIALOG].g || !L->mv[MU_GFX_NPC_DIALOG].path[0])
        return 0;
    snprintf(L->dlg.title, sizeof L->dlg.title, "%s", d->title ? d->title : "");
    snprintf(L->dlg.text, sizeof L->dlg.text, "%s", d->text ? d->text : "");
    L->dlg.noptions = d->noptions > 13 ? 13 : d->noptions;
    for (int i = 0; i < L->dlg.noptions; i++)
        snprintf(L->dlg.options[i], sizeof L->dlg.options[0], "%s", d->options[i] ? d->options[i] : "");
    L->dlg.hide_contribute = d->hide_contribute;
    npc_open_window(L, MU_GFX_NPC_DIALOG);
    dialog_send(L);
    npc_last(L, "dialogue %s (%d page(s), %d option(s))", L->dlg.title, L->dlg.npages, L->dlg.noptions);
    return 1;
}

static int swin_open(mu_gfx_layer *L, int m, const char *title, const mu_gfx_slot_item *items, int n)
{
    slot_window *sw = swin_for(L, m);
    movie *mv = &L->mv[m];
    if (!sw || !mv->g || !mv->path[0] || inventory_busy(L))
        return 0;
    swin_clear(sw);
    for (int i = 0; i < n; i++)
        swin_add(sw, &items[i]);
    char q[256];
    json_quote(q, sizeof q, title ? title : "");
    invokef(L, m, mv->path, "InitTitle", "[%s]", q);
    npc_open_window(L, m);
    if (!sw->gap_done && sw->have_slot)
        swin_gap(L, sw);
    swin_slot_states(L, sw);
    /* NpcShop's Open 0x00bf0354 and StorageInven's open the inventory with
     * them (static reading of the shop's; the vault the same, inference). */
    mu_gfx_layer_show(L, MU_GFX_INVENTORY, 1);
    return 1;
}

int mu_gfx_layer_npc_shop(mu_gfx_layer *L, const char *title, int repair, int tabs, const mu_gfx_slot_item *items,
                          int n)
{
    if (!L || !L->mv[MU_GFX_NPC_SHOP].g || !L->mv[MU_GFX_NPC_SHOP].path[0])
        return 0;
    movie *mv = &L->mv[MU_GFX_NPC_SHOP];
    if(inventory_busy(L))return 0;
    L->services.npc_repair=repair!=0;L->services.repair_mode=0;
    /* NpcShop: SetVisibleRepair by the repair flag the talk case set (0x00bf172e), the tab count of the
     * answer (0x00bf17c2 -> SetAvailableTabs), labels (GlobalText stand-ins) */
    invokef(L, MU_GFX_NPC_SHOP, mv->path, "SetVisibleRepair", "[%s]", repair ? "true" : "false");
    invokef(L, MU_GFX_NPC_SHOP, mv->path, "SetAvailableTabs", "[%d]", tabs < 1 ? 1 : tabs > 5 ? 5 : tabs);
    invokef(L, MU_GFX_NPC_SHOP, mv->path, "InitBtnTitle", "[\"Repair\",\"Repair all\",\"Rebuy\"]");
    invokef(L, MU_GFX_NPC_SHOP, mv->path, "InitTax", "[\"\"]");
    int ok = swin_open(L, MU_GFX_NPC_SHOP, title, items, n);
    if (ok)
        npc_last(L, "shop %s: %d item(s), repair %d", title ? title : "", L->swin[0].nitems, repair);
    return ok;
}

int mu_gfx_layer_storage(mu_gfx_layer *L, const char *title, const mu_gfx_slot_item *items, int n)
{
    if (!L || !L->mv[MU_GFX_STORAGE].g || !L->mv[MU_GFX_STORAGE].path[0])
        return 0;
    movie *mv = &L->mv[MU_GFX_STORAGE];
    invokef(L, MU_GFX_STORAGE, mv->path, "InitText", "[\"Zen\",\"Fee\"]");
    invokef(L, MU_GFX_STORAGE, mv->path, "InitButton", "[\"Deposit\",\"Withdraw\",\"Lock\",\"Extend\"]");
    char zen[32];
    commas(zen, sizeof zen, L->vault_zen);
    invokef(L, MU_GFX_STORAGE, mv->path, "SetKeepZen", "[\"%s\"]", zen);
    invokef(L, MU_GFX_STORAGE, mv->path, "SetCharge", "[\"0\"]");
    int ok = swin_open(L, MU_GFX_STORAGE, title, items, n);
    if (ok)
        npc_last(L, "vault: %d item(s)", L->swin[1].nitems);
    return ok;
}

void mu_gfx_layer_npc_close(mu_gfx_layer *L)
{
    if (!L)
        return;
    for (int k = MU_GFX_NPC_DIALOG; k <= MU_GFX_STORAGE; k++)
        mu_gfx_layer_show(L, k, 0);
    mu_gfx_layer_show(L, MU_GFX_MIX_SELECT, 0);
    mu_gfx_layer_show(L, MU_GFX_MIX, 0);
}

int mu_gfx_layer_npc_window(const mu_gfx_layer *L)
{
    if (L && L->mv[MU_GFX_MIX].open) return MU_GFX_MIX;
    if (L && L->mv[MU_GFX_MIX_SELECT].open) return MU_GFX_MIX_SELECT;
    for (int k = MU_GFX_NPC_DIALOG; L && k <= MU_GFX_STORAGE; k++)
        if (L->mv[k].g && L->mv[k].open)
            return k;
    return -1;
}

int mu_gfx_layer_npc_action(mu_gfx_layer *L, const char *verb, int arg)
{
    if (!L || !verb)
        return 0;
    if (!strcmp(verb, "close")) {
        int open = mu_gfx_layer_npc_window(L) >= 0;
        mu_gfx_layer_npc_close(L);
        return open;
    }
    if (!strcmp(verb, "buy") && L->mv[MU_GFX_NPC_SHOP].open) {
        swin_click(L, &L->swin[0], arg);
        return 1;
    }
    if (!strcmp(verb, "take") && L->mv[MU_GFX_STORAGE].open) {
        swin_click(L, &L->swin[1], arg);
        return 1;
    }
    if (!strcmp(verb, "sell") || !strcmp(verb, "put"))
        return npc_inventory_r(L, arg);
    if (!strcmp(verb, "option") && L->mv[MU_GFX_NPC_DIALOG].open) {
        npc_call(&L->mv[MU_GFX_NPC_DIALOG], "onClickSelectBtn", "[0,\"\"]", (double[]){arg, 0}, 2);
        return 1;
    }
    if (!strcmp(verb, "next") && L->mv[MU_GFX_NPC_DIALOG].open) {
        npc_call(&L->mv[MU_GFX_NPC_DIALOG], "onClickbtnNext", "[\"\"]", NULL, 0);
        return 1;
    }
    /* NATIVE-LANG-002 (scripted hovers): "tip" a NpcShop / StorageInven slot, "tipinv" an inventory cell */
    if (!strcmp(verb, "tip") && (L->mv[MU_GFX_NPC_SHOP].open || L->mv[MU_GFX_STORAGE].open)) {
        swin_show_tooltip(L, &L->swin[L->mv[MU_GFX_NPC_SHOP].open ? 0 : 1], arg);
        return L->mv[MU_GFX_TOOLTIP].open;
    }
    if (!strcmp(verb, "tipinv")) {
        show_item_tooltip(L, arg);
        return L->mv[MU_GFX_TOOLTIP].open;
    }
    if (!strcmp(verb, "bufftip")) {   /* the bufflist's onTooltip for buff `arg` (scripted: a fixed position) */
        char args[96];
        snprintf(args, sizeof args, "[\"onTooltip\",{\"BuffType\":%d,\"x\":360,\"y\":60}]", arg);
        bufflist_event(L, "onTooltip", args);
        return L->mv[MU_GFX_TOOLTIP].open;
    }
    return 0;
}

void mu_gfx_layer_npc_note(mu_gfx_layer *L, const char *note)
{
    if (L && note)
        npc_last(L, "%s", note);
}

const char *mu_gfx_layer_npc_last(const mu_gfx_layer *L)
{
    return L ? L->npc_last : "";
}

int mu_gfx_layer_npc_page(const mu_gfx_layer *L, int *pages)
{
    if (pages)
        *pages = L ? L->dlg.npages : 0;
    return L ? L->dlg.page : 0;
}

int mu_gfx_layer_slot_center(const mu_gfx_layer *L, int m, int32_t cell, double *x, double *y)
{
    const slot_window *sw = m == MU_GFX_NPC_SHOP ? &L->swin[0] : m == MU_GFX_STORAGE ? &L->swin[1] : m == MU_GFX_MIX ? &L->swin[2] : NULL;
    if (!L || !sw || !sw->have_slot || cell < 0 || cell >= sw->grid.cols * sw->grid.rows)
        return 0;
    int col = cell % sw->grid.cols, row = cell / sw->grid.cols;
    *x = (sw->win_x + (sw->slot_x + (float)col * (sw->slot_w + sw->gap_x) + sw->slot_w / 2) * sw->scale) * L->scale;
    *y = (sw->win_y + (sw->slot_y + (float)row * (sw->slot_h + sw->gap_y) + sw->slot_h / 2) * sw->scale) * L->scale;
    return 1;
}

int mu_gfx_layer_slot_items(const mu_gfx_layer *L, int m)
{
    if (!L)
        return 0;
    const slot_window *sw = m == MU_GFX_NPC_SHOP ? &L->swin[0] : m == MU_GFX_STORAGE ? &L->swin[1] : m == MU_GFX_MIX ? &L->swin[2] : NULL;
    if (!sw)
        return 0;
    return sw->grid.item_count;
}

/* Callbacks of the NPC movies. */
static const char *npc_call(movie *mv, const char *name, const char *args, const double *v, int n)
{
    mu_gfx_layer *L = mv->L;
    slot_window *sw = swin_for(L, mv->id);
    if (sw) {
        if (mv->id==MU_GFX_NPC_SHOP && !strcmp(name,"onClickbtnRepair")) {
            mu_gfx_layer_service_action(L,"repairmode",0,0);return NULL;
        }
        if (mv->id==MU_GFX_NPC_SHOP && !strcmp(name,"onClickbtnRepairAll")) {
            mu_gfx_layer_service_action(L,"repairall",0,0);return NULL;
        }
        if (!strcmp(name, "requestWindowPos") && n >= 2) {
            sw->win_x = (float)v[0];
            sw->win_y = (float)v[1];
        } else if (!strcmp(name, "requestSlotInfo") && n >= 5 && v[4] == 0) {
            sw->slot_x = (float)v[0];
            sw->slot_y = (float)v[1];
            sw->slot_w = (float)v[2];
            sw->slot_h = (float)v[3];
            sw->have_slot = 1;
        } else if (!strcmp(name, "requestItemSlotClick") && n >= 1) {
            if (mv->id == MU_GFX_MIX)
                mu_gfx_layer_mix_action(L, L->held>=0 ? "mixdrop" : "mixtake", (int)v[0], 0);
            else swin_click(L, sw, (int)v[0]);
        } else if (!strcmp(name, "requestItemSlotOver") && n >= 1) {
            sw->hover = (int)v[0];
            swin_show_tooltip(L, sw, sw->hover);
        } else if (!strcmp(name, "requestItemSlotOut")) {
            sw->hover = -1;
            hide_tooltip(L);
        } else if (mv->id == MU_GFX_MIX && !strcmp(name, "requestItemSlotClickR") && n>=1) {
            mu_gfx_layer_mix_action(L, "mixtake", (int)v[0], 0);
        } else if (mv->id == MU_GFX_MIX && !strcmp(name, "onClickbtnMix")) {
            mu_gfx_layer_mix_action(L, "mix", 0, 0);
        } else if (!strncmp(name, "onClick", 7)) {
            npc_last(L, "%s: %s (not played: a server request in the client)", mv->file, name + 7);
        }
        return NULL;
    }
    if (mv->id == MU_GFX_MIX_SELECT && !strcmp(name, "onClickGoblinMenu") && n>=2) {
        if ((int)v[0]==1) mu_gfx_layer_mix_action(L, "mixopen", 0, 0);
        else {
            npc_last(L,"This Chaos Goblin system is not supported by the preview");
            mu_gfx_layer_chat(L,3,"",L->npc_last);
        }
    }
    if (mv->id == MU_GFX_NPC_DIALOG) {
        if (!strcmp(name, "NPCDialogTextWidth")) {
            char wrapped[4096] = "";
            json_string_decoded(args, 0, wrapped, sizeof wrapped);
            L->dlg.wrapped = 1;
            if (L->cfg.dialog_wrapped)
                L->cfg.dialog_wrapped(L->cfg.tooltip_user, wrapped);
            dialog_wrapped(L, wrapped);
        } else if (!strcmp(name, "onClickSelectBtn") && n >= 1 && L->cfg.dialog_choice &&
                   L->cfg.dialog_choice(L->cfg.tooltip_user, (int)v[0])) {
            /* NATIVE-LANG-002: the host ran the client's choice (0x00be906d) */
        } else if (!strcmp(name, "onClickSelectBtn") && n >= 1) {
            int i = (int)v[0];
            /* DEMO: the client sends the choice to the server (0x00be829f builds packet 0xf8); the layer
             * closes the window after the last option and pages forward otherwise. */
            npc_last(L, "dialogue option %d%s%s", i + 1, i < L->dlg.noptions ? ": " : "",
                     i < L->dlg.noptions ? L->dlg.options[i] : "");
            if (i + 1 >= L->dlg.noptions)
                mu_gfx_layer_show(L, MU_GFX_NPC_DIALOG, 0);
            else if (L->dlg.page + 1 < L->dlg.npages) {
                L->dlg.page++;
                dialog_page(L);
            }
        } else if (!strcmp(name, "onClickbtnNext") && L->dlg.page + 1 < L->dlg.npages) {
            L->dlg.page++;
            dialog_page(L);
        } else if (!strcmp(name, "onClickbtnPrevious") && L->dlg.page > 0) {
            L->dlg.page--;
            dialog_page(L);
        }
    }
    return NULL;
}

/* Item models over NpcShop / StorageInven: the reconstructed slot pass over
 * the window's page (page type 8 / 9 as 0x00ab7277 sets them). */
static void swin_rects(mu_gfx_layer *L, slot_window *sw, rect_list *R)
{
    R->n = 0;
    R->L = L;
    R->base = sw->items;
    if (!sw->have_slot || !L->mv[sw->movie].open)
        return;
    mu_slot_page page = {&sw->grid, sw->slot_x, sw->slot_y, sw->slot_w, sw->slot_h, sw->gap_x, sw->gap_y};
    mu_slot_frame frame = {1, MU_ALIGN_TOP_LEFT, sw->win_x, sw->win_y, 1.0f, sw->scale, &page, 1, 2};
    mu_slot_pass(&frame, L->w, L->h, mu_gfx_rate_x(L->w), mu_gfx_rate_y(L->h), NULL, emit_rect, R);
}

static int swin_draws(slot_window *sw, const rect_list *R, mu_gfx_item_draw *draws, int max)
{
    int n = 0;
    for (int i = 0; i < R->n && n < max; i++) {
        const item *it = &sw->items[R->item[i]];
        mu_gfx_item_draw *d = &draws[n++];
        memset(d, 0, sizeof *d);
        d->item = R->item[i];
        d->code = it->grid.code;
        d->level = it->level;
        d->has_options = it->has_data;
        d->level_word =
            it->has_data ? (it->data[1] & 0x84) | (it->level << 3) | (it->option & 3) : it->level << 3;
        d->excellent = it->excellent;
        d->set_bits = it->set_bits;
        d->element = it->element;
        memcpy(d->rect, R->r[i], sizeof d->rect);
        d->slot[0] = R->call[i].x;
        d->slot[1] = R->call[i].y;
        d->slot[2] = R->call[i].w;
        d->slot[3] = R->call[i].h;
        d->page_type = R->call[i].page_type;
        d->page_flag = R->call[i].page_flag;
        d->type8_seen = R->call[i].type8_seen;
        d->frame_id = (int32_t)R->call[i].frame_id;
        d->frame_scale = sw->scale;
        d->alpha = 1.0f;
        int cell = sw->hover;
        d->select = cell >= 0 && cell < sw->grid.cols * sw->grid.rows && sw->grid.cells[cell] &&
                    mu_grid_item_at(&sw->grid, cell) == &it->grid;
    }
    return n;
}

int mu_gfx_layer_slot_draws(mu_gfx_layer *L, int m, mu_gfx_item_draw *out, int max)
{
    slot_window *sw = L ? swin_for(L, m) : NULL;
    if (L && out && m>=MU_GFX_STORE_REGISTER)return service_draws(L,m,out,max);
    if (!sw || !out)
        return 0;
    rect_list R;
    swin_rects(L, sw, &R);
    return swin_draws(sw, &R, out, max);
}

static void swin_composite(mu_gfx_layer *L, int m, uint8_t *rgba, int32_t W, int32_t H)
{
    slot_window *sw = swin_for(L, m);
    if (!sw)
        return;
    rect_list R;
    swin_rects(L, sw, &R);
    for (int i = 0; i < R.n; i++)
        fill_cpu(rgba, W, H, R.r[i], sw->items[R.item[i]].rgb, L->scale);
}

#ifndef MU_GFX_NO_GL
static void swin_draw_gl(mu_gfx_layer *L, int m)
{
    slot_window *sw = swin_for(L, m);
    if (!sw)
        return;
    rect_list R;
    swin_rects(L, sw, &R);
    if (L->cfg.items) {
        static mu_gfx_item_draw draws[RECT_MAX];
        int n = swin_draws(sw, &R, draws, RECT_MAX);
        host_gl_begin(L);
        L->cfg.items(L->cfg.items_user, draws, n, L->w, L->h);
        host_gl_end(L);
    } else {
        for (int i = 0; i < R.n; i++)
            fill_gl(R.r[i], sw->items[R.item[i]].rgb, L->scale);
    }
}
#endif

static void swin_init(mu_gfx_layer *L)
{
    static const struct { int movie, type; const char *frame; } W[3] = {{MU_GFX_NPC_SHOP, 8, "mcNPCShop"},
                                                                      {MU_GFX_STORAGE, 9, "mcStorageInven"},
                                                                      {MU_GFX_MIX, 4, "mcMixInventory"}};
    L->mix.outcome = 1;L->services.outcome=1;
    for (int k = 0; k < SLOT_ITEMS; k++) L->mix.origin[k] = -1;
    for (int k = 0; k < 3; k++) {
        slot_window *sw = &L->swin[k];
        memset(sw, 0, sizeof *sw);
        sw->movie = W[k].movie;
        sw->frame = W[k].frame;
        sw->scale = 1.0f;
        sw->hover = -1;
        mu_grid_construct(&sw->grid);
        mu_grid_init(&sw->grid, W[k].type, 0, 0, 0, 8, k == 2 ? 4 : 15, 0);   /* 0x00ab7277(type, 8, 15, ...) */
    }
    L->vault_zen = 1250000;   /* demo */
}

/* ---- NATIVE-MIX-001: movie boundary and delayed offline demo answers ---- */
static mu_mix_item mix_snapshot(const item *it)
{
    return (mu_mix_item){it->grid.code, it->level, it->option, it->excellent, it->durability, it->period};
}

int mu_gfx_layer_item_snapshot(const mu_gfx_layer *L, int i, mu_mix_item *out)
{
    if (!L || !out || i < 0 || i >= L->nitems) return 0;
    *out = mix_snapshot(&L->items[i]);
    return 1;
}

int mu_gfx_layer_mix_pending(const mu_gfx_layer *L) { return L ? L->mix.pending : 0; }

static void mix_refresh(mu_gfx_layer *L)
{
    slot_window *sw = &L->swin[2];
    mu_mix_item items[32]; int n = 0;
    for (int k=0;k<sw->grid.item_count && n<32;k++)
        items[n++] = mix_snapshot((const item *)sw->grid.items[k]);
    memset(&L->mix.quote,0,sizeof L->mix.quote); L->mix.quote.recipe=-1;
    snprintf(L->mix.quote.title,sizeof L->mix.quote.title,"Chaos Machine");
    snprintf(L->mix.quote.detail,sizeof L->mix.quote.detail,"Mix table unavailable.");
    if (L->cfg.mix_quote)
        L->cfg.mix_quote(L->cfg.tooltip_user,L->mix.group,items,n,&L->mix.quote);
    char title[256],detail[600];
    json_quote(title,sizeof title,L->mix.quote.title);json_quote(detail,sizeof detail,L->mix.quote.detail);
    movie *mv=&L->mv[MU_GFX_MIX];
    invokef(L,MU_GFX_MIX,mv->path,"InitText","[%s,\"Mix\",\"\"]",title);
    invokef(L,MU_GFX_MIX,mv->path,"SetText","[%s,\"Offline demo\"]",detail);
    invokef(L,MU_GFX_MIX,mv->path,"SetVisibleMixButton","[%s]",
            L->mix.quote.ready && L->mix.quote.supported && !L->mix.pending ? "true":"false");
    swin_slot_states(L,sw); slot_states(L);
}

static int mix_return(mu_gfx_layer *L)
{
    slot_window *sw=&L->swin[2];
    if (inventory_busy(L)) return 0;
    if (L->held>=0 && sw->grid.item_count) {
        npc_last(L,"Place the held item before closing the mix window");return 0;
    }
    /* Reserve every destination before moving any item. A full inventory
     * leaves the window open with every item intact. */
    mu_grid scratch=L->grid; mu_grid_item copies[32]; int dest[32][2],ids[32],n=0;
    for(int k=0;k<sw->nitems;k++) {
        item *it=&sw->items[k]; int cell=it->grid.row*8+it->grid.col;
        if(mu_grid_item_at(&sw->grid,cell)!=&it->grid)continue;
        if(n>=32 || !mu_grid_find_free(&scratch,it->grid.width,it->grid.height,&dest[n][0],&dest[n][1])) {
            npc_last(L,"Close: inventory has no room for the mix items (demo)"); return 0;
        }
        copies[n]=it->grid;mu_grid_place(&scratch,dest[n][0],dest[n][1],&copies[n]);ids[n++]=k;
    }
    for(int j=0;j<n;j++) {
        int k=ids[j],origin=L->mix.origin[k];
        if(origin<0 || origin>=L->nitems)return 0;
        item *dst=&L->items[origin];*dst=sw->items[k];
        mu_grid_place(&L->grid,dest[j][0],dest[j][1],&dst->grid);
    }
    swin_clear(sw);slot_states(L);hide_tooltip(L);return 1;
}

static int mix_jewel(mu_gfx_layer *L,int cell)
{
    if(L->held<0 || inventory_busy(L) || cell<0 || cell>=64)return 0;
    item *jewel=&L->items[L->held];
    if(jewel->grid.code!=0x1c0d && jewel->grid.code!=0x1c0e && jewel->grid.code!=0x1c10)return 0;
    mu_grid_item *gi=mu_grid_item_at(&L->grid,cell);
    if(!gi)return 0;
    mu_mix_item target=mix_snapshot((item *)gi);
    if (item_reserved(L,(int)((item *)gi-L->items))) return 1;
    if(!L->cfg.jewel_check || !L->cfg.jewel_check(L->cfg.tooltip_user,jewel->grid.code,&target,L->mv[MU_GFX_MIX].open)) {
        npc_last(L,"Jewel cannot be used on this item");return 1;
    }
    L->mix.source=L->held;L->mix.target=(int)((item *)gi-L->items);
    L->held=-1; /* the pending request owns this source, never the cursor */
    L->mix.pending=2;L->mix.due=L->time_ms+160;
    if(L->cfg.jewel_request)L->cfg.jewel_request(L->cfg.tooltip_user,jewel->grid.row*8+jewel->grid.col,cell);
    npc_last(L,"Jewel request sent; waiting for offline demo answer");
    hide_tooltip(L);return 1;
}

static void mix_step(mu_gfx_layer *L)
{
    if(!L->mix.pending || L->time_ms<L->mix.due)return;
    int pending=L->mix.pending;L->mix.pending=0;
    if(pending==2) {
        item *source=&L->items[L->mix.source],*target=&L->items[L->mix.target];
        if(L->mix.outcome==0) {
            int col,row;
            if(mu_grid_find_free(&L->grid,source->grid.width,source->grid.height,&col,&row))
                mu_grid_place(&L->grid,col,row,&source->grid);
            else L->held=L->mix.source;
            npc_last(L,"Jewel rejected by offline demo server; items unchanged");
        } else {
            if(L->mix.outcome==1) {
                if(source->grid.code==0x1c10)target->option++;
                else target->level++;
            } else if(source->grid.code==0x1c0e)target->level=0;
            else if(source->grid.code==0x1c10)target->option=0;
            npc_last(L,"Jewel %s (offline demo answer)",L->mix.outcome==1?"succeeded":"failed");
        }
        if(L->mix.outcome!=0)source->grid.code=-1;
        slot_states(L);hide_tooltip(L);return;
    }
    slot_window *sw=&L->swin[2];
    if(L->mix.outcome==0) {
        mix_refresh(L);npc_last(L,"Mix rejected by offline demo server; items and zen unchanged");
        invokef(L,MU_GFX_MIX,L->mv[MU_GFX_MIX].path,"SetText","[\"Mix rejected by offline demo server.\",\"Items and zen unchanged.\"]");
        return;
    }
    L->hero.zen-=(int64_t)L->mix.quote.cost;zen_text(L);
    int first=sw->grid.item_count?(int)((item *)sw->grid.items[0]-sw->items):-1;
    for(int k=0;k<sw->nitems;k++) {
        item *it=&sw->items[k];int cell=it->grid.row*8+it->grid.col;
        if(mu_grid_item_at(&sw->grid,cell)==&it->grid) {
            mu_grid_remove(&sw->grid,&it->grid);
            int origin=L->mix.origin[k];if(origin>=0 && origin<L->nitems)L->items[origin].grid.code=-1;
        }
    }
    if(L->mix.outcome==1 && first>=0) {
        item result=sw->items[first];int origin=L->mix.origin[first];
        result.level=result.level<15?result.level+1:15;
        swin_clear(sw);sw->items[0]=result;sw->nitems=1;L->mix.origin[0]=origin;
        mu_grid_place(&sw->grid,0,0,&sw->items[0].grid);
    } else swin_clear(sw);
    mix_refresh(L);npc_last(L,"Mix %s (offline demo answer)",L->mix.outcome==1?"succeeded":"failed");
    invokef(L,MU_GFX_MIX,L->mv[MU_GFX_MIX].path,"SetText","[\"Mix %s (offline demo answer).\",\"%s\"]",
            L->mix.outcome==1?"succeeded":"failed",L->mix.outcome==1?"Take your result from the mix window.":"The demo server consumed the ingredients.");
}

static int mix_free_slot(mu_gfx_layer *L)
{
    slot_window *sw=&L->swin[2];
    for(int k=0;k<sw->nitems;k++) {
        mu_grid_item *it=&sw->items[k].grid;
        if(mu_grid_item_at(&sw->grid,it->row*8+it->col)!=it)return k;
    }
    return sw->nitems<32?sw->nitems++:-1;
}

int mu_gfx_layer_mix_action(mu_gfx_layer *L,const char *verb,int a,int b)
{
    if(!L || !verb)return 0;
    if(!strcmp(verb,"mixresult")) {
        if(L->mix.pending || a<0 || a>2)return 0;
        L->mix.outcome=a;return 1;
    }
    if(inventory_busy(L))return 0;
    if(!strcmp(verb,"goblin")) {
        if(!L->mv[MU_GFX_MIX_SELECT].g)return 0;
        mu_gfx_layer_npc_close(L);
        movie *mv=&L->mv[MU_GFX_MIX_SELECT];
        invokef(L,MU_GFX_MIX_SELECT,mv->path,"initFixedTextObj",
                "[{\"Title\":\"Chaos Goblin\",\"btnCloseLabel\":\"Close\",\"mixExplain\":\"Offline demo\",\"ChanceInfo\":\"Mix\"}]");
        invokef(L,MU_GFX_MIX_SELECT,mv->path,"initButtonInfo",
                "[[{\"Label\":\"Regular combination\",\"MixSystem\":1,\"MixType\":-1},{\"Label\":\"Chaos weapon (unavailable)\",\"MixSystem\":0,\"MixType\":0}]]");
        invokef(L,MU_GFX_MIX_SELECT,mv->path,"setBtnYPos","[2]");
        mu_gfx_layer_show(L,MU_GFX_MIX_SELECT,1);npc_last(L,"Chaos Goblin (offline demo)");return 1;
    }
    if(!strcmp(verb,"mixopen")) {
        if(L->mv[MU_GFX_TRADE].open)return 0;
        if(L->services.shop_open || L->services.draft_active || L->mv[MU_GFX_STORE_LIST].open)return 0;
        if(!L->mv[MU_GFX_MIX].g || a<0 || a>=22 || !mix_return(L))return 0;
        mu_gfx_layer_npc_close(L);L->mix.group=a;
        mu_gfx_layer_show(L,MU_GFX_MIX,1);mu_gfx_layer_show(L,MU_GFX_INVENTORY,1);
        invokef(L,MU_GFX_MIX,L->mv[MU_GFX_MIX].path,"SetMixType","[0]");
        mix_refresh(L);return 1;
    }
    if(!strcmp(verb,"jewel")) {
        if(L->services.draft_active || L->services.repair_mode)return 0;
        if(a<0 || a>=64 || b<0 || b>=64 || L->held>=0 || !mu_grid_item_at(&L->grid,a))return 0;
        inventory_click(L,a);int done=mix_jewel(L,b);
        if(!L->mix.pending && L->held>=0)inventory_click(L,a);
        return done;
    }
    if(!L->mv[MU_GFX_MIX].open)return 0;
    slot_window *sw=&L->swin[2];
    if(!strcmp(verb,"mixdrop")) {
        if(L->held<0 || a<0 || a>=32)return 0;
        item *it=&L->items[L->held];
        if(!mu_grid_fits(&sw->grid,a%8,a/8,it->grid.width,it->grid.height))return 0;
        int k=mix_free_slot(L);if(k<0)return 0;
        sw->items[k]=*it;L->mix.origin[k]=L->held;
        mu_grid_place(&sw->grid,a%8,a/8,&sw->items[k].grid);L->held=-1;
        hide_tooltip(L);mix_refresh(L);return 1;
    }
    if(!strcmp(verb,"mixput")) {
        if(a<0 || a>=64 || L->held>=0)return 0;
        mu_grid_item *gi=mu_grid_item_at(&L->grid,a);int col,row;
        if(!gi || !mu_grid_find_free(&sw->grid,gi->width,gi->height,&col,&row))return 0;
        int origin=(int)((item *)gi-L->items);
        if(item_reserved(L,origin))return 0;
        int k=mix_free_slot(L);if(k<0)return 0;
        sw->items[k]=L->items[origin];L->mix.origin[k]=origin;
        mu_grid_remove(&L->grid,gi);mu_grid_place(&sw->grid,col,row,&sw->items[k].grid);
        hide_tooltip(L);mix_refresh(L);return 1;
    }
    if(!strcmp(verb,"mixtake")) {
        if(a<0 || a>=32 || L->held>=0)return 0;
        mu_grid_item *gi=mu_grid_item_at(&sw->grid,a);int col,row;
        if(!gi || !mu_grid_find_free(&L->grid,gi->width,gi->height,&col,&row))return 0;
        int k=(int)((item *)gi-sw->items),origin=L->mix.origin[k];
        L->items[origin]=sw->items[k];mu_grid_remove(&sw->grid,gi);
        mu_grid_place(&L->grid,col,row,&L->items[origin].grid);hide_tooltip(L);mix_refresh(L);return 1;
    }
    if(!strcmp(verb,"mix")) {
        mix_refresh(L);
        if(L->held>=0 || !L->mix.quote.ready || !L->mix.quote.supported || L->hero.zen<L->mix.quote.cost) {
            npc_last(L,"Mix refused: ingredients, rule support, held item or zen");return 0;
        }
        L->mix.pending=1;L->mix.due=L->time_ms+160;
        invokef(L,MU_GFX_MIX,L->mv[MU_GFX_MIX].path,"SetVisibleMixButton","[false]");
        invokef(L,MU_GFX_MIX,L->mv[MU_GFX_MIX].path,"SetText","[\"Waiting for offline demo answer...\",\"\"]");
        npc_last(L,"Mix request recipe %d group %d; waiting for offline demo answer",L->mix.quote.recipe,L->mix.group);
        return 1;
    }
    return 0;
}

#include "mu_gfx_services.inc"

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
            host_gl_begin(L);
            int drawn = host_items(L, &R);
            host_gl_end(L);
            if (!drawn)
                for (int i = 0; i < R.n; i++)
                    fill_gl(R.r[i], L->items[R.item[i]].rgb, L->scale);
        }
        swin_draw_gl(L, order[k]);
        if(L->cfg.items) {
            mu_gfx_item_draw service_items[SERVICE_BUNDLE];
            int ns=service_draws(L,order[k],service_items,SERVICE_BUNDLE);
            if(ns) {host_gl_begin(L);L->cfg.items(L->cfg.items_user,service_items,ns,L->w,L->h);host_gl_end(L);}
        }
        if (order[k] == MU_GFX_TRADE && L->trade_nitems && L->cfg.items) {
            host_gl_begin(L);
            L->cfg.items(L->cfg.items_user, L->trade_items, L->trade_nitems, L->w, L->h);
            host_gl_end(L);
        }
        if (order[k] == MU_GFX_SKILL_STAMP)
            skill_draw_gl(L);
        if (L->cfg.window_draw) {
            host_gl_begin(L);
            L->cfg.window_draw(L->cfg.tooltip_user, order[k], L->w, L->h);
            host_gl_end(L);
        }
    }
    float hr[4];
    if (held_rect(L, hr)) {
        host_gl_begin(L);
        int drawn = host_held(L, hr);
        host_gl_end(L);
        if (!drawn)
            fill_gl(hr, L->items[L->held].rgb, L->scale);
    }
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
    /* This asset's PlayAnimation calls gotoAndPlay(0). Ruffle ignores frame 0,
     * leaving QuestNotice at alpha 0. Start the same authored timeline at its first Flash frame. */
    if (m == MU_GFX_QUEST_NOTICE && !strcmp(method, "PlayAnimation"))
        invokef(L, m, path ? path : L->mv[m].path, "gotoAndPlay", "[1]");
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
    float sc = L->inv_scale;
    *x = (L->win_x + (L->slot_x + (float)col * (L->slot_w + L->gap_x) + L->slot_w / 2) * sc) * L->scale;
    *y = (L->win_y + (L->slot_y + (float)row * (L->slot_h + L->gap_y) + L->slot_h / 2) * sc) * L->scale;
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

int mu_gfx_layer_items_placed(const mu_gfx_layer *L) { return L ? L->grid.item_count : 0; }

int mu_gfx_layer_count_item(const mu_gfx_layer *L, int32_t code, int32_t level)
{
    int count = 0;
    for (int i = 0; L && i < L->nitems; i++)
        if (mu_grid_find_id(&L->grid, L->items[i].grid.id) && i != L->held && !item_reserved(L,i) &&
            L->items[i].grid.code == code && L->items[i].level == level)
            count++;
    return count;
}

const char *mu_gfx_layer_last_sent(const mu_gfx_layer *L) { return L ? L->last_sent : ""; }

/* ---- NATIVE-NAMES-001: hudPlayerName ---------------------------------------------------------- */

void mu_gfx_layer_set_map_hooks(mu_gfx_layer *L, const mu_gfx_map_hooks *hooks)
{
    if (!L)
        return;
    memset(&L->maph, 0, sizeof L->maph);
    if (hooks)
        L->maph = *hooks;
}

int mu_gfx_layer_set_variable(mu_gfx_layer *L, int m, const char *path, const char *value_json)
{
    if (!L || m < 0 || m >= MU_GFX_MOVIES || !L->mv[m].g || !path || !path[0] || !L->api.set_variable)
        return 0;
    L->mv[m].view_dirty = 1;
    return L->api.set_variable(L->mv[m].g, path, value_json);
}

void mu_gfx_layer_set_chat_hook(mu_gfx_layer *L, void (*hook)(void *user, const char *text), void *user)
{
    if (!L)
        return;
    L->chat_hook = hook;
    L->chat_hook_user = user;
}

const char *mu_gfx_layer_get_variable(mu_gfx_layer *L, int m, const char *path)
{
    if (!L || m < 0 || m >= MU_GFX_MOVIES || !L->mv[m].g || !path || !path[0] || !L->api.get_variable)
        return NULL;
    return L->api.get_variable(L->mv[m].g, path);
}

/* ---- skills (NATIVE-SKILL-001) ---------------------------------------------------------------------- */

static void skill_last(mu_gfx_layer *L, const char *fmt, ...)
{
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(L->stamp.last, sizeof L->stamp.last, fmt, ap);
    va_end(ap);
    logf_(L, "game: %s", L->stamp.last);
}

/* GlobalText as a JSON literal keeping '\n' (the explain texts are "%s\n %s", 0x00c1fef9). */
static void gt_quote_nl(const mu_gfx_layer *L, char *out, size_t cap, const char *text)
{
    char clean[1024];
    size_t n = 0;
    for (const char *s = text; s && *s && n + 1 < sizeof clean; s++)
        clean[n++] = *s == '\n' || ((unsigned char)*s >= 0x20 && (unsigned char)*s < 0x7f) ? *s : '?';
    clean[n] = 0;
    (void)L;
    json_quote(out, cap, clean);
}

void mu_gfx_layer_set_skill_host(mu_gfx_layer *L, const mu_gfx_skill_host *host)
{
    if (!L)
        return;
    memset(&L->skill, 0, sizeof L->skill);
    L->have_skill_host = host != NULL;
    if (host)
        L->skill = *host;
    skill_feed(L);
}

static void skill_bar_path(const mu_gfx_layer *L, char *out, size_t cap)
{
    snprintf(out, cap, "%s.mcSkillHotKey", L->mv[MU_GFX_MAIN].path);
}

/* The bar feed 0x00c58797 (every logic step): SetSkillSlot when the host reports a change. */
static void skill_feed(mu_gfx_layer *L)
{
    if (!L->have_skill_host || !L->skill.feed || !L->mv[MU_GFX_MAIN].path[0] || !L->main_inited)
        return;
    static char json[8192];
    if (!L->skill.feed(L->skill.user, json, sizeof json))
        return;
    char path[160];
    skill_bar_path(L, path, sizeof path);
    invokef(L, MU_GFX_MAIN, path, "SetSkillSlot", "[%s]", json);
}

void mu_gfx_layer_skill_delay(mu_gfx_layer *L, int32_t skill, int32_t delay_ms)
{
    if (!L || !L->mv[MU_GFX_MAIN].path[0])
        return;
    char path[160];
    skill_bar_path(L, path, sizeof path);
    invokef(L, MU_GFX_MAIN, path, "onUseSkillDelay", "[{\"skill\":%d,\"delaytime\":%d}]", skill, delay_ms);
}

static void skill_popup_close(mu_gfx_layer *L)
{
    mu_gfx_layer_show(L, MU_GFX_SKILL_POPUP, 0);
    hide_tooltip(L);
}

/* SkillInfoPopup's Show (0x00c1ef6b -> 0x00c1f204 -> builder 0x0117da56 -> 0x00c1f2b0): the popup gets
 * SetInfoPopupSkillStamp(x, y, 0, 0, title, body, 0) at the hovered slot's centre and top (the rate
 * divisions cancel out in stage points), then opens. */
static void skill_popup(mu_gfx_layer *L, int32_t skill, int x, int y)
{
    static char title[4096], body[32768];
    if (!L->skill.tooltip || !skill || !L->skill.tooltip(L->skill.user, skill, title, sizeof title, body, sizeof body)) {
        skill_popup_close(L);
        return;
    }
    mu_gfx_layer_skill_popup(L, x, y, title, body);
    skill_last(L, "tooltip skill %d at %d,%d", skill, x, y);
}

void mu_gfx_layer_skill_popup(mu_gfx_layer *L, int x, int y, const char *title, const char *body)
{
    if (!L)
        return;
    if (!title) {
        skill_popup_close(L);
        return;
    }
    static char qt[8192], qb[65536];
    json_quote(qt, sizeof qt, title);
    json_quote(qb, sizeof qb, body);
    movie *pop = &L->mv[MU_GFX_SKILL_POPUP];
    if (pop->g && pop->path[0]) {
        invokef(L, MU_GFX_SKILL_POPUP, pop->path, "SetInfoPopupSkillStamp", "[%d,%d,0,0,%s,%s,0]", x, y, qt, qb);
        mu_gfx_layer_show(L, MU_GFX_SKILL_POPUP, 1);
        raise_window(L, MU_GFX_SKILL_POPUP);
    } else {
        /* SkillInfoPopup not converted: InfoPopup with title + body (layer choice) */
        movie *tip = &L->mv[MU_GFX_TOOLTIP];
        static char both[40000], qboth[80000];
        snprintf(both, sizeof both, "%s%s", title, body);
        json_quote(qboth, sizeof qboth, both);
        tip->open = 1;
        invokef(L, MU_GFX_TOOLTIP, tip->path, "SetInfoPopup", "[%d,%d,0,0,%s]", x, y, qboth);
    }
}

static void skill_main_event(mu_gfx_layer *L, movie *mv, const char *event, const char *args)
{
    (void)mv;
    int slot = (int)json_field(args, "slot", 0), skill = (int)json_field(args, "skill", 0);
    if (!strcmp(event, "onSelectSkill")) {
        L->key_used = 1;
        if (L->skill.select)
            L->skill.select(L->skill.user, slot, skill);
        skill_last(L, "select slot %d skill %d", slot, skill);
    } else if (!strcmp(event, "onSkillTooltip")) {
        int x = (int)json_field(args, "x", 0), y = (int)json_field(args, "y", 0), w = (int)json_field(args, "w", 0);
        skill_popup(L, skill, x + w / 2, y);       /* 0x00c7089d: x + w / 2 (cdq; sub; sar) */
    } else if (!strcmp(event, "offSkillTooltip")) {
        skill_popup_close(L);
    } else if (!strcmp(event, "onOpenSkillWindow")) {
        mu_gfx_layer_toggle(L, MU_GFX_SKILL_STAMP);
    }
}

/* SkillStampFrame's creation (0x00c1fb1b): its labels. */
static void skill_init_window(mu_gfx_layer *L)
{
    movie *st = &L->mv[MU_GFX_SKILL_STAMP];
    L->stamp.drag_from = -1;
    L->stamp.page = 1;
    if (!st->g || !st->path[0] || L->stamp.inited)
        return;
    L->stamp.inited = 1;
    char q[5][256];
    static const int32_t TEXT[5] = {0x1299, 0x129c, 0x129d, 0x129e, 0x129f};
    static const char *const TEXT_IN[5] = {"Skill Imprint", "Select Skill (Basic Skill)", "Select Skill (Special Skill)",
                                           "Register a skill by dragging.", "Elemental Imprint"};
    for (int i = 0; i < 5; i++)
        gt_quote(L, q[i], sizeof q[i], TEXT[i], TEXT_IN[i]);
    invokef(L, MU_GFX_SKILL_STAMP, st->path, "InitText", "[%s,%s,%s,%s,%s]", q[0], q[1], q[2], q[3], q[4]);
    static const int32_t BUTTON[4] = {0x129a, 0x129b, 0xdaf, 0xe5};
    static const char *const BUTTON_IN[4] = {"Basic Skill", "Special Skill", "Save", "Cancel"};
    for (int i = 0; i < 4; i++)
        gt_quote(L, q[i], sizeof q[i], BUTTON[i], BUTTON_IN[i]);
    invokef(L, MU_GFX_SKILL_STAMP, st->path, "InitButton", "[%s,%s,%s,%s]", q[0], q[1], q[2], q[3]);
    char a[600], b[600];
    snprintf(a, sizeof a, "%s\n %s", gtext(L, 0x12a0, "Elemental Imprint gets activated after equipping Pentagram."),
             gtext(L, 0x12a1, "Skill Damage increase depends on the Pentagram."));
    snprintf(b, sizeof b, "%s\n %s", gtext(L, 0x12ae, "Special Skills are not affected by the Elemental Imprints."),
             gtext(L, 0x12af, "Castle Siege and Dark Raven command skills only."));
    gt_quote_nl(L, q[0], sizeof q[0], a);
    gt_quote_nl(L, q[1], sizeof q[1], b);
    invokef(L, MU_GFX_SKILL_STAMP, st->path, "InitStampExplain", "[%s,%s]", q[0], q[1]);
}

/* Open (0x00c2008b) and close (0x00c2012d: unsaved changes ask for a confirmation in the client; the layer
 * restores the bar, layer choice). */
static void skill_window_shown(mu_gfx_layer *L, int m, int open)
{
    movie *st = &L->mv[m];
    if (open) {
        skill_init_window(L);
        L->stamp.page = 1;
        L->stamp.select_page = 0;
        L->stamp.drag_from = -1;
        L->stamp.saved = 0;
        if (L->skill.stamp_open)
            L->skill.stamp_open(L->skill.user, 1);
        invokef(L, m, st->path, "UpdateSkillPage", "[%d]", L->stamp.page);
        /* 0x00c21bd5 without a pentagram: element 0, "Elemental Imprint is not active.", "To activate ..." */
        char q1[256], q2[256];
        gt_quote(L, q1, sizeof q1, 0x12ac, "Elemental Imprint is not active.");
        gt_quote(L, q2, sizeof q2, 0x12ad, "To activate equip a Pentagram.");
        invokef(L, m, st->path, "SetStampDamage", "[0,%s,%s]", q1, q2);
        invokef(L, m, st->path, "SetSkillSlotSize", "[]");
        skill_last(L, "Skill Imprint window opened");
    } else {
        skill_popup_close(L);
        if (!L->stamp.saved && L->skill.stamp_open)
            L->skill.stamp_open(L->skill.user, 0);
        skill_last(L, "Skill Imprint window closed%s", L->stamp.saved ? " (saved)" : "");
    }
}

static int skill_slot_rect(const mu_gfx_layer *L, int slot, float r[4])
{
    if (slot < 0 || slot >= 20 || !L->stamp.have_slot[slot])
        return 0;
    float sc = L->applied_scale[MU_GFX_SKILL_STAMP] > 0.0f ? L->applied_scale[MU_GFX_SKILL_STAMP] : 1.0f;
    float w = L->stamp.slot_w > 0 ? L->stamp.slot_w : 32.0f, h = L->stamp.slot_h > 0 ? L->stamp.slot_h : 32.0f;
    r[0] = L->stamp.win_x + L->stamp.slots[slot][0] * sc;
    r[1] = L->stamp.win_y + L->stamp.slots[slot][1] * sc;
    r[2] = w * sc;
    r[3] = h * sc;
    return 1;
}

int mu_gfx_layer_skill_icons(const mu_gfx_layer *L, mu_gfx_skill_icon *out, int max)
{
    if (!L || !L->mv[MU_GFX_SKILL_STAMP].open || !L->skill.stamp_skill)
        return 0;
    int n = 0;
    for (int slot = 0; slot < 20 && n < max; slot++) {
        mu_gfx_skill_icon *ic = &out[n];
        if (!skill_slot_rect(L, slot, ic->rect))
            continue;
        ic->slot = slot;
        ic->skill = L->skill.stamp_skill(L->skill.user, slot);
        ic->delay = ic->skill && L->skill.delay_left ? L->skill.delay_left(L->skill.user, ic->skill) : 0.0f;
        ic->frame_scale = mu_gfx_layer_window_scale(L, MU_GFX_SKILL_STAMP);
        ic->stamp_offset[0] = L->stamp.stamp_offset[0];
        ic->stamp_offset[1] = L->stamp.stamp_offset[1];
        if (ic->skill)
            n++;
    }
    return n;
}

#ifndef MU_GFX_NO_GL
static void skill_draw_gl(mu_gfx_layer *L)
{
    mu_gfx_skill_icon icons[20];
    int n = mu_gfx_layer_skill_icons(L, icons, 20);
    if (!n)
        return;
    if (L->skill.icons) {
        glPushAttrib(GL_ALL_ATTRIB_BITS);
        glMatrixMode(GL_PROJECTION);
        glPushMatrix();
        glMatrixMode(GL_MODELVIEW);
        glPushMatrix();
        L->skill.icons(L->skill.user, icons, n, L->w, L->h);
        glMatrixMode(GL_PROJECTION);
        glPopMatrix();
        glMatrixMode(GL_MODELVIEW);
        glPopMatrix();
        glPopAttrib();
        glBindTexture(GL_TEXTURE_2D, 0);
    } else {
        static const float rgb[3] = {.35f, .55f, .9f};
        for (int i = 0; i < n; i++)
            fill_gl(icons[i].rect, rgb, L->scale);
    }
}
#endif

static void skill_composite(mu_gfx_layer *L, uint8_t *rgba, int32_t W, int32_t H)
{
    mu_gfx_skill_icon icons[20];
    int n = mu_gfx_layer_skill_icons(L, icons, 20);
    for (int i = 0; i < n; i++)
        fill_cpu(rgba, W, H, icons[i].rect, ICON_PALETTE[icons[i].skill % 8], L->scale);
}

static void skill_drop(mu_gfx_layer *L, int to)
{
    int from = L->stamp.drag_from;
    L->stamp.drag_from = -1;
    if (from < 0 || !L->skill.stamp_drop)
        return;
    int r = L->skill.stamp_drop(L->skill.user, from, to);
    if (r < 0) {
        mu_gfx_layer_chat(L, 3, "", gtext(L, 0x12bb, "You cannot register a skill that you did not learn."));
        skill_last(L, "drag %d -> %d: not learned", from, to);
    } else {
        skill_last(L, "drag %d -> %d%s", from, to, r ? ": the bar changed" : "");
    }
    L->mv[MU_GFX_SKILL_STAMP].view_dirty = 1;
}

static const char *skill_call(movie *mv, const char *name, const char *args, const double *v, int n)
{
    mu_gfx_layer *L = mv->L;
    (void)args;
    if (mv->id == MU_GFX_SKILL_POPUP)
        return NULL;
    if (!strcmp(name, "requestWindowPos") && n >= 2) {
        L->stamp.win_x = (float)v[0];
        L->stamp.win_y = (float)v[1];
    } else if (!strcmp(name, "requestSkillSlotInfo") && n >= 4 && v[3] >= 0 && v[3] < 20) {
        int i = (int)v[3];
        L->stamp.slots[i][0] = (float)v[0];
        L->stamp.slots[i][1] = (float)v[1];
        L->stamp.have_slot[i] = 1;
    } else if (!strcmp(name, "requestSkillSlotSize") && n >= 2) {
        L->stamp.slot_w = (float)v[0];
        L->stamp.slot_h = (float)v[1];
    } else if (!strcmp(name, "requestStampRelativePosition") && n >= 2) {
        L->stamp.stamp_offset[0] = (float)v[0];
        L->stamp.stamp_offset[1] = (float)v[1];
    } else if ((!strcmp(name, "onClickprevBtn") || !strcmp(name, "onClicknextBtn")) && L->skill.stamp_page) {
        int page = L->skill.stamp_page(L->skill.user, 0, name[7] == 'p' ? -1 : 1);   /* 0x00c21aa2 */
        if (page != L->stamp.page) {
            L->stamp.page = page;
            invokef(L, MU_GFX_SKILL_STAMP, mv->path, "UpdateSkillPage", "[%d]", page);
        }
    } else if (!strcmp(name, "onClickSelectSlotPrev") || !strcmp(name, "onClickSelectSlotNext")) {
        if (L->skill.stamp_page)                    /* 0x010976db(-1 / +1) */
            L->stamp.select_page = L->skill.stamp_page(L->skill.user, 1, name[17] == 'P' ? -1 : 1);
    } else if (!strcmp(name, "onClickBaseSKill") || !strcmp(name, "onClickSpecialSkill")) {
        /* the tab flag (handler +0x8c): page 1 of the stamp manager's basic or special tab */
        if (L->skill.stamp_tab)
            L->skill.stamp_tab(L->skill.user, name[7] == 'S');
        L->stamp.page = 1;
        invokef(L, MU_GFX_SKILL_STAMP, mv->path, "UpdateSkillPage", "[1]");
        L->mv[MU_GFX_SKILL_STAMP].view_dirty = 1;
    } else if (!strcmp(name, "requestSkillSlotOver") && n >= 1) {
        float r[4];
        int slot = (int)v[0];
        int32_t skill = L->skill.stamp_skill ? L->skill.stamp_skill(L->skill.user, slot) : 0;
        if (skill && skill_slot_rect(L, slot, r))
            skill_popup(L, skill, (int)(r[0] + r[2] / 2), (int)r[1]);
    } else if (!strcmp(name, "requestSkillSlotOut")) {
        skill_popup_close(L);
    } else if (!strcmp(name, "requestSkillSlotDragStart") && n >= 1) {
        L->stamp.drag_from = (int)v[0];
        skill_popup_close(L);
    } else if (!strcmp(name, "requestSkillSlotDragEnd")) {
        invokef(L, MU_GFX_SKILL_STAMP, mv->path, "CheckOverSlot", "[]");   /* 0x00c221f0 */
    } else if ((!strcmp(name, "DragEndSlotIndex_Mouse") || !strcmp(name, "DragEndSlotIndex")) && n >= 1) {
        skill_drop(L, (int)v[0]);
    } else if (!strcmp(name, "onClickbtnSaveOption")) {
        if (L->skill.stamp_save)
            L->skill.stamp_save(L->skill.user);
        L->stamp.saved = 1;
        mu_gfx_layer_chat(L, 3, "", gtext(L, 0x12c1, "Skill Imprint saved."));
        mu_gfx_layer_show(L, MU_GFX_SKILL_STAMP, 0);
    } else if (!strcmp(name, "onClickbtnCancel") || !strcmp(name, "onClickbtnClose")) {
        mu_gfx_layer_show(L, MU_GFX_SKILL_STAMP, 0);
    }
    return NULL;
}

int mu_gfx_layer_skill_action(mu_gfx_layer *L, const char *verb, int a, int b)
{
    if (!L || !verb)
        return 0;
    movie *st = &L->mv[MU_GFX_SKILL_STAMP];
    double v[4] = {a, b, 0, 0};
    if (!strcmp(verb, "open") || !strcmp(verb, "close")) {
        mu_gfx_layer_show(L, MU_GFX_SKILL_STAMP, verb[0] == 'o');
        return st->g != NULL;
    }
    if (!strcmp(verb, "tip")) {                     /* the bar's slot a: its skill's tooltip */
        int32_t skill = L->skill.stamp_skill ? L->skill.stamp_skill(L->skill.user, 100 + a) : 0;
        skill_popup(L, skill, (int)L->w / 2, (int)L->h - 120);
        return skill != 0;
    }
    if (!st->g || !st->open)
        return 0;
    if (!strcmp(verb, "drag")) {
        L->stamp.drag_from = a;
        skill_drop(L, b);
    } else if (!strcmp(verb, "over")) {
        skill_call(st, "requestSkillSlotOver", "", v, 1);
    } else if (!strcmp(verb, "out")) {
        skill_call(st, "requestSkillSlotOut", "", v, 0);
    } else if (!strcmp(verb, "save")) {
        skill_call(st, "onClickbtnSaveOption", "", v, 0);
    } else if (!strcmp(verb, "cancel")) {
        skill_call(st, "onClickbtnCancel", "", v, 0);
    } else if (!strcmp(verb, "page")) {
        skill_call(st, a < 0 ? "onClickprevBtn" : "onClicknextBtn", "", v, 0);
    } else if (!strcmp(verb, "select")) {
        skill_call(st, a < 0 ? "onClickSelectSlotPrev" : "onClickSelectSlotNext", "", v, 0);
    } else if (!strcmp(verb, "tab")) {
        skill_call(st, a ? "onClickSpecialSkill" : "onClickBaseSKill", "", v, 0);
    } else {
        return 0;
    }
    return 1;
}

const char *mu_gfx_layer_skill_last(const mu_gfx_layer *L)
{
    return L ? L->stamp.last : "";
}

void mu_gfx_layer_set_social_hooks(mu_gfx_layer *L, const mu_gfx_social_hooks *hooks)
{
    if (!L) return;
    if (hooks) L->socialh = *hooks; else memset(&L->socialh, 0, sizeof L->socialh);
}
void mu_gfx_layer_trade_items(mu_gfx_layer *L, const mu_gfx_item_draw *items, int n)
{
    if (!L) return;
    if (n < 0) n = 0;
    if (n > 64) n = 64;
    if (n && items) memcpy(L->trade_items, items, (size_t)n * sizeof *items);
    L->trade_nitems = n;
}

void mu_gfx_layer_stage_size(const mu_gfx_layer *L, int32_t *w, int32_t *h)
{
    if (!L) return;
    if (w) *w = L->w;
    if (h) *h = L->h;
}

int mu_gfx_layer_inventory_reserve(mu_gfx_layer *L, int cell, mu_gfx_slot_item *out)
{
    if (!L || !out || inventory_busy(L) || L->mv[MU_GFX_MIX].open || L->held >= 0 || cell < 0 || cell >= L->grid.cols * L->grid.rows) return 0;
    mu_grid_item *gi = mu_grid_item_at(&L->grid, cell);
    if (!gi || !L->grid.cells[cell]) return 0;
    int idx = (int)((item *)gi - L->items);
    if (idx < 0 || idx >= L->nitems || item_reserved(L,idx)) return 0;
    item *it = &L->items[idx];
    memset(out, 0, sizeof *out);
    out->code = gi->code; out->level = it->level; out->width = gi->width; out->height = gi->height;
    snprintf(out->name, sizeof out->name, "%s", it->name);
    out->has_data = 1;
    out->excellent = it->excellent;
    out->set_bits = it->set_bits;
    out->element = it->element;
    item_wire(it, out->data);
    L->trade_reserved[idx] = 1;
    slot_states(L); hide_tooltip(L);
    return idx + 1;
}

void mu_gfx_layer_inventory_finish(mu_gfx_layer *L, int token, int commit)
{
    if (!L || token <= 0 || token > L->nitems || !L->trade_reserved[token - 1]) return;
    item *it = &L->items[token - 1];
    if (commit) {mu_grid_remove(&L->grid, &it->grid);it->grid.code=-1;}
    L->trade_reserved[token - 1] = 0;
    slot_states(L);
}

int mu_gfx_layer_inventory_can_receive(const mu_gfx_layer *L, int count)
{
    if (!L || count < 0) return 0;
    int free_cells=0, items=0;
    for(int i=0;i<L->grid.cols*L->grid.rows;i++) {
        uint32_t id=L->grid.cells[i];
        if(!id || (id<=MAX_ITEMS && L->trade_reserved[id-1]))free_cells++;
    }
    for(int i=0;i<L->nitems;i++)if(L->items[i].grid.code!=-1&&!L->trade_reserved[i])items++;
    return free_cells>=count && items+count<=MAX_ITEMS;
}

int mu_gfx_layer_inventory_exchange(mu_gfx_layer *L, const int tokens[32], const mu_gfx_slot_item *incoming, int n)
{
    if (!L || !tokens || inventory_busy(L) || n < 0 || n > 32 || (n && !incoming)) return 0;
    item saved[MAX_ITEMS];
    uint8_t reserved[MAX_ITEMS];
    mu_grid grid = L->grid; /* pointers refer to L->items, whose addresses do not change */
    int count = L->nitems;
    memcpy(saved, L->items, sizeof saved);
    memcpy(reserved, L->trade_reserved, sizeof reserved);
    for (int i = 0; i < 32; i++)
        if (tokens[i]) mu_gfx_layer_inventory_finish(L, tokens[i], 1);
    for (int i = 0; i < n; i++)
        if (mu_gfx_layer_add_slot_item(L, &incoming[i]) < 0) {
            memcpy(L->items, saved, sizeof saved);
            memcpy(L->trade_reserved, reserved, sizeof reserved);
            L->grid = grid;
            L->nitems = count;
            slot_states(L);
            return 0;
        }
    return 1;
}
