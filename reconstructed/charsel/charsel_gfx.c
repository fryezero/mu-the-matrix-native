/* The character-select GFx window (NATIVE-CHARSEL-003): authored C for the
 * routines listed in charsel_gfx.h.  Addresses are the pinned restored text
 * (capture09).  Strings the client builds with std::string and boost-style
 * formatters are built here with snprintf into fixed buffers. */
#include "charsel_gfx.h"

#include <stdarg.h>
#include <stdio.h>
#include <string.h>

/* ------------------------------------------------------------------ output */

typedef struct line {
    char text[MU_CSG_LINE];
    size_t len;
} line;

static void put(line *l, const char *s)
{
    size_t n = strlen(s);
    if (l->len + n >= sizeof l->text)
        n = sizeof l->text - 1 - l->len;
    memcpy(l->text + l->len, s, n);
    l->len += n;
    l->text[l->len] = 0;
}

static void putf(line *l, const char *fmt, ...)
{
    char buf[512];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(buf, sizeof buf, fmt, ap);
    va_end(ap);
    put(l, buf);
}

/* JSON string as Python's json.dumps(ensure_ascii=False) writes it */
static void put_json_string(line *l, const char *s)
{
    put(l, "\"");
    for (const unsigned char *p = (const unsigned char *)(s ? s : ""); *p; ++p) {
        char esc[8];
        if (*p == '"') put(l, "\\\"");
        else if (*p == '\\') put(l, "\\\\");
        else if (*p == '\n') put(l, "\\n");
        else if (*p == '\r') put(l, "\\r");
        else if (*p == '\t') put(l, "\\t");
        else if (*p == '\b') put(l, "\\b");
        else if (*p == '\f') put(l, "\\f");
        else if (*p < 0x20) { snprintf(esc, sizeof esc, "\\u%04x", *p); put(l, esc); }
        else { esc[0] = (char)*p; esc[1] = 0; put(l, esc); }
    }
    put(l, "\"");
}

static void emit(const mu_csg_env *env, const line *l)
{
    if (env->emit)
        env->emit(env->context, l->text);
}

static void call0(const mu_csg_env *env, uint32_t address)
{
    line l = {{0}, 0};
    putf(&l, "call %08x", address);
    emit(env, &l);
}

static void call1(const mu_csg_env *env, uint32_t address, const char *arg)
{
    line l = {{0}, 0};
    putf(&l, "call %08x %s", address, arg);
    emit(env, &l);
}

static void calli(const mu_csg_env *env, uint32_t address, int32_t value)
{
    char a[32];
    snprintf(a, sizeof a, "%d", value);
    call1(env, address, a);
}

static void callr(const mu_csg_env *env, uint32_t address, int32_t index)
{
    char a[32];
    snprintf(a, sizeof a, "r%d", index);
    call1(env, address, a);
}

/* invoke with no arguments (0x00aaf23f) */
static void invoke0(const mu_csg_env *env, const char *method)
{
    line l = {{0}, 0};
    putf(&l, "invoke %s []", method);
    emit(env, &l);
}

/* the printf-style invoke 0x00aae7e0 with "%d" */
static void invoked(const mu_csg_env *env, const char *method, int32_t value)
{
    line l = {{0}, 0};
    putf(&l, "invoke %s [%d]", method, value);
    emit(env, &l);
}

/* ------------------------------------------------------------- characters */

static uint8_t *character(const mu_csg_env *env, int32_t index)
{
    if (index < 0 || index >= MU_CHARSEL_CHARACTERS || !env->character)
        return NULL;   /* 0x009a13f4: NULL outside 0..399 */
    return env->character(env->context, index);
}

static uint8_t live(const uint8_t *c) { return c[MU_CHARSEL_OBJECT + MU_OBJ_LIVE]; }   /* 0x0095f977 */

static uint16_t get16(const uint8_t *p, size_t o) { return (uint16_t)(p[o] | p[o + 1] << 8); }
static uint32_t get32(const uint8_t *p, size_t o)
{
    return (uint32_t)p[o] | (uint32_t)p[o + 1] << 8 | (uint32_t)p[o + 2] << 16 | (uint32_t)p[o + 3] << 24;
}

/* std::string at +0x3658: buffer or pointer at +0, size +0x10, capacity +0x14 (0x008e7940) */
static const char *record_name(const mu_csg_env *env, const uint8_t *c)
{
    if (env->name)
        return env->name(env->context, c);
    if (get32(c, 0x3658 + 0x14) >= 0x10)
        return "";   /* a heap string is not reachable from a record image */
    return (const char *)(c + 0x3658);
}

static const char *gt(const mu_csg_env *env, int32_t index)
{
    const char *s = env->global_text ? env->global_text(env->context, index) : NULL;
    return s ? s : "";
}

/* ------------------------------------------------------------------- HTML */

static const char *const HTML_COLOURS[22] = {
    "#FFFFFF", "#7FB2FF", "#FF3319", "#FFCC19", "#19FF7F", "#A00000", "#FF19FF", "#0000A0", "#A06600", "#00FF00",
    "#666666", "#CC7FCC", "#B266FF", "#E56B0A", "#800080", "#FFFF00", "#00B0F0", "#00B050", "#CCFF00", "#00FFFF",
    "#BCBCBC", "#C1C469"};   /* 0x00ab4ea1 jump table 0x00ab5154 -> 0x01a8379c.. */

/* '<' -> "&lt;" everywhere (0x00970f81 find / 0x00971de9 replace loop) */
static void escape_lt(char *out, size_t cap, const char *text)
{
    size_t n = 0;
    for (const char *p = text; *p && n + 1 < cap; ++p) {
        if (*p == '<') {
            if (n + 4 >= cap)
                break;
            memcpy(out + n, "&lt;", 4);
            n += 4;
        } else {
            out[n++] = *p;
        }
    }
    out[n] = 0;
}

char *mu_csg_html(char *out, size_t cap, const char *text, uint32_t colour, uint8_t bold)
{
    out[0] = 0;
    if (!text || !strcmp(text, "\n") || !text[0])
        return out;
    char body[MU_CSG_LINE];
    escape_lt(body, sizeof body, text);
    const char *c = colour <= 0x15 ? HTML_COLOURS[colour] : "#FFFFFF";   /* default 0x00ab5032 */
    if (bold == 1)
        snprintf(out, cap, "<font color='%s'><b>%s</b></font><br>", c, body);   /* 0x01a8384c */
    else
        snprintf(out, cap, "<font color='%s'>%s</font><br>", c, body);          /* 0x01a83874 */
    return out;
}

char *mu_csg_html_rgba(char *out, size_t cap, const char *text, uint32_t rgba, uint8_t bold)
{
    out[0] = 0;
    if (!text || !strcmp(text, "\n") || !text[0])
        return out;
    char body[MU_CSG_LINE];
    escape_lt(body, sizeof body, text);
    /* 0x0096ff52: (c & 0xff) << 16 | (c & 0xff00) | (c & 0xff0000) >> 16, "%06x" */
    uint32_t hex = (rgba & 0xffu) << 16 | (rgba & 0xff00u) | (rgba & 0xff0000u) >> 16;
    if (bold == 1)
        snprintf(out, cap, "<font color='#%06x'><b>%s</b></font>", hex, body);   /* 0x01a7e204 */
    else
        snprintf(out, cap, "<font color='#%06x'>%s</font>", hex, body);          /* 0x01a7e228 */
    return out;
}

/* --------------------------------------------------------- the list 0xb4b927 */

void mu_csg_build_list(mu_csg_window *w, const mu_csg_env *env)
{
    line l = {{0}, 0};
    put(&l, "invoke SetSelectText [[");
    for (int32_t i = 0; i < MU_CSG_ROWS; ++i) {
        int32_t index = w->slots[i];
        uint8_t *c = character(env, index);
        if (i)
            put(&l, ",");
        put(&l, "{");
        if (c && live(c)) {
            uint8_t flags = c[MU_CHAR_FLAG_14];
            /* the name colour (0x00b4ba01..0x00b4bab3) is computed and never used; only its "webzen"
             * test (0x0129debb: the name contains "webzen") is a call */
            if (!(flags & 1) && !(flags & 0x12) && !(flags & 4) && !(flags & 8) && !(flags & 0x20))
                callr(env, 0x0129debb, index);
            int32_t state = 0;
            switch (c[0x17]) {   /* guild status */
            case 0xff: state = 0x1e8; break;
            case 0x00: state = 0x532; break;
            case 0x20: state = 0x516; break;
            case 0x40: state = 0x515; break;
            case 0x80: state = 0x514; break;
            default: break;
            }
            putf(&l, "\"type\":0,\"index\":%d,\"textJob\":", i);
            put_json_string(&l, env->class_name ? env->class_name(env->context, c[MU_CHAR_CLASS]) : "");
            put(&l, ",\"textState\":");
            put_json_string(&l, gt(env, state));
            char html[1024], number[64];
            put(&l, ",\"textName\":");
            put_json_string(&l, mu_csg_html(html, sizeof html, record_name(env, c), 3, 0));
            snprintf(number, sizeof number, "%d", get16(c, 0x144));
            put(&l, ",\"textLevel\":");
            put_json_string(&l, mu_csg_html(html, sizeof html, number, 3, 0));
        } else {
            int type = 1, text = 0x1464;
            if (env->slot_mode /* || 0x0185bdbd(), which returns 0 */) {
                if (i >= env->slot_limit) {
                    type = 2;
                    text = 0x1465;
                }
            }
            putf(&l, "\"type\":%d,\"textCreat\":", type);
            put_json_string(&l, gt(env, text));
        }
        put(&l, "}");
    }
    put(&l, "]]");
    emit(env, &l);
}

/* ----------------------------------------------------------- show 0xb4b848 */

void mu_csg_show(mu_csg_window *w, const mu_csg_env *env, uint8_t flag)
{
    if (flag) {
        int none = 1;
        for (int32_t i = 0; i < MU_CSG_ROWS; ++i) {
            uint8_t *c = character(env, w->slots[i]);
            if (c && live(c)) {   /* the client dereferences without a test; a byte index is always < 400 */
                none = 0;
                break;
            }
        }
        if (none) {
            invoked(env, "SetSelectVisible", flag);
            return;
        }
        call0(env, 0x00af0ce9);   /* 0x01d22c60 ->0x00af0ce9(the window's movie): focus */
        mu_csg_select_index(w, env, w->row);
    }
    invoked(env, "SetSelectVisible", flag);
    invoke0(env, "SetCharSelArrow");
}

void mu_csg_fill_and_show(mu_csg_window *w, const mu_csg_env *env)
{
    mu_csg_build_list(w, env);
    mu_csg_show(w, env, 1);
}

/* ------------------------------------------------------ SelectIndex 0xb4bed3 */

void mu_csg_select_index(mu_csg_window *w, const mu_csg_env *env, int32_t slot)
{
    (void)w;
    invoked(env, "SelectIndex", slot);
    *env->selected = slot;
    *env->shown = slot;
    call0(env, 0x009a4dd7);   /* CUIMng +0x4bb0 CCharSelMainWin::UpdateDisplay */
    invoke0(env, "SetCharSelArrow");
}

/* --------------------------------------------------------- a row 0xb4bd6c */

void mu_csg_select_row(mu_csg_window *w, const mu_csg_env *env, int32_t row, uint8_t enter)
{
    if ((uint32_t)row >= MU_CSG_ROWS)
        return;
    uint8_t *previous = character(env, *env->selected);
    if (previous && (previous[MU_CHAR_CLASS] & 0xf) == 5)   /* 0x0095f5cc: Dark Lord */
        callr(env, 0x010b03cb, *env->selected);             /* 0x06fba940 ->0x010b03cb(previous) */
    int32_t index = w->slots[row];
    uint8_t *c = character(env, index);
    if (c && live(c)) {
        *env->shown = index;
        *env->selected = index;
        w->row = row;
    } else {
        *env->shown = -1;
        *env->selected = -1;
        calli(env, 0x00b49bf4, 1);   /* GFx +0x22c: the create-character panel */
        calli(env, 0x009a5920, 0);   /* its +0x9c = 0 */
        call0(env, 0x00b4b684);
    }
    call0(env, 0x009a4dd7);
    if (enter == 1) {
        calli(env, 0x009a5029, *env->selected);
        if (env->enter_refused)
            return;
        calli(env, 0x0185a75a, 0);
    }
    invoke0(env, "SetCharSelArrow");
}

/* ------------------------------------------------------- arrows 0xb4bfc2 */

void mu_csg_arrow(mu_csg_window *w, const mu_csg_env *env, uint8_t up)
{
    if (w->slots[w->row] == 0xff)
        return;
    int32_t step = up == 1 ? -1 : 1;
    int32_t old = w->row, target = w->row + step;
    if (target < 0 || target >= w->count)
        return;
    w->row = target;
    for (int32_t i = 0; i < MU_CSG_ROWS; ++i) {
        uint8_t *c = character(env, w->slots[i]);
        w->slots[i] = c && live(c) ? c[MU_CHAR_KEY] : 0xff;   /* the key byte +0x3e */
    }
    if (w->slots[target] == 0xff)
        return;
    uint8_t t = w->slots[old];   /* 0x00b4bf4e */
    w->slots[old] = w->slots[target];
    w->slots[target] = t;
    invoked(env, "SelectIndex", target);
    mu_csg_select_row(w, env, target, 0);
    mu_csg_build_list(w, env);
}

/* ---------------------------------------------------- callbacks 0xb4c1df */

static double number(const mu_csg_arg *args, int32_t count, int32_t i)
{
    return i < count && args ? args[i].number : 0.0;
}

static int32_t ftol(double v) { return (int32_t)v; }   /* 0x0191c5e0 (truncation) */

void mu_csg_callback(mu_csg_window *w, const mu_csg_env *env, const char *name, const mu_csg_arg *args,
                     int32_t count)
{
    if (!name)
        return;
    if (env->gfx_busy && env->window_flag_79)
        return;
    call1(env, 0x00aaf5d3, name);   /* the window base's dispatcher */
    char a[256];
    if (!strcmp(name, "SetSelectedClass")) {
        calli(env, 0x00b4a442, ftol(number(args, count, 0)));
    } else if (!strcmp(name, "SetCreateBoardInfo")) {
        snprintf(a, sizeof a, "%d %d %d %d", ftol(number(args, count, 0)), ftol(number(args, count, 1)),
                 ftol(number(args, count, 2)), ftol(number(args, count, 3)));
        call1(env, 0x00b4a349, a);
    } else if (!strcmp(name, "OnEnterCharacterName")) {
        snprintf(a, sizeof a, "%s %d", count > 0 && args[0].string ? args[0].string : "",
                 ftol(number(args, count, 1)));
        call1(env, 0x00b49eca, a);
    } else if (!strcmp(name, "OnClickCreateCancel")) {
        calli(env, 0x00b49bf4, 0);
        calli(env, 0x00b4c806, -1);
    } else if (!strcmp(name, "UpdateInput")) {
        if (count == 1 && args[0].type == 4)
            call1(env, 0x00b4b31a, args[0].string ? args[0].string : "");
    } else if (!strcmp(name, "OnClickCreateCharacter")) {
        calli(env, 0x00b49bf4, 1);
    } else if (!strcmp(name, "OnCharSelectedClick")) {
        /* 0x0191c720: to unsigned; the "< 0" test after it never holds */
        mu_csg_select_row(w, env, (int32_t)(uint32_t)(int64_t)number(args, count, 0), 0);
    } else if (!strcmp(name, "OnCharSelectedDClick")) {
        mu_csg_select_row(w, env, (int32_t)(uint32_t)(int64_t)number(args, count, 0), 1);
    } else if (!strcmp(name, "onCharSelArrow")) {
        mu_csg_arrow(w, env, (uint8_t)(number(args, count, 0) != 0.0));   /* 0x00aad487 (bool) */
    }
}

/* ------------------------------------------------- initialisation 0xb4915b */

const mu_csg_class mu_csg_classes[MU_CSG_CLASSES] = {
    /* 0x00b4af38..0x00b4b249: button, class type, name, Str, Dex, Vit, Ene, Cha, explanation, cannot */
    {0, 0, 0x14, 18, 18, 15, 30, 0, 0x6a9, 0},     {1, 1, 0x15, 28, 20, 25, 10, 0, 0x6aa, 0},
    {2, 2, 0x16, 22, 25, 20, 15, 0, 0x6ab, 0},     {3, 5, 0x697, 21, 21, 18, 23, 0, 0x69a, 0},
    {4, 6, 0xc4e, 32, 27, 25, 20, 0, 0xc50, 0},    {5, 3, 0x17, 26, 26, 26, 26, 0, 0x6ac, 0},
    {6, 4, 0x18, 26, 20, 20, 15, 25, 0x6ad, 0},    {7, 7, 0x11ec, 30, 30, 25, 24, 0, 0x11ee, 0},
    {8, 8, 0x14f8, 13, 18, 14, 40, 0, 0x14f9, 0},  {9, 9, 0x1596, 28, 30, 15, 10, 0, 0x1595, 0},
    {10, 10, 0x169a, 20, 18, 20, 25, 0, 0x169f, 0}, {11, 11, 0x171a, 19, 19, 15, 30, 0, 0x171f, 0},
    {12, 12, 0x1723, 18, 18, 19, 30, 0, 0x1728, 0}, {13, 13, 0x17aa, 25, 28, 15, 10, 0, 0x17b3, 0},
    {14, 14, 0x19fc, 15, 20, 23, 25, 0, 0x1a02, 0}, {15, 15, 0x1a92, 26, 18, 19, 20, 0, 0x1a98, 0}};

int mu_csg_init(mu_csg_window *w, const mu_csg_env *env)
{
    (void)w;
    call0(env, 0x00aadbc3);
    if (!env->base_ready)
        return 0;
    invoked(env, "SetInputBoxLength", 10);
    {
        line l = {{0}, 0};
        static const struct { const char *member; int32_t gt; } TEXT[6] = {
            {"StrOK", 0xe4}, {"StrCancel", 0xe5}, {"StrName", 0x101c}, {"ChangeName", 0x2a4},
            {"BaseCharSlot", 0x1464}, {"LockCharSlot", 0x1465}};
        put(&l, "invoke InitText [{");
        for (int i = 0; i < 6; ++i) {
            putf(&l, "%s\"%s\":", i ? "," : "", TEXT[i].member);
            put_json_string(&l, gt(env, TEXT[i].gt));
        }
        /* MoveCharText: GT 0x4d9 "\n" GT 0x4da "\n" GT 0x4db through 0x0096fe90 with the colour
         * 0x00b4c6aa(0xff, 0xc8, 0xb4, 0xff) */
        char joined[MU_CSG_LINE], html[MU_CSG_LINE], part[3][1024];
        for (int k = 0; k < 3; ++k)   /* each GlobalText read before the next (the host may reuse its buffer) */
            snprintf(part[k], sizeof part[k], "%s", gt(env, 0x4d9 + k));
        snprintf(joined, sizeof joined, "%s\n%s\n%s", part[0], part[1], part[2]);
        put(&l, ",\"MoveCharText\":");
        put_json_string(&l, mu_csg_html_rgba(html, sizeof html, joined, 0xffb4c8ffu, 0));
        put(&l, ",\"ViewableSelectedWinNum\":10}]");
        emit(env, &l);
    }
    {
        /* InitStat("%s %s %s %s %s"): Strength 0xa6, Agility 0xa7, Vitality 0xa9, Energy 0xa8, Command 0x76c,
         * each through 0x00a99d93 (code-page conversion; identity on ASCII) */
        static const int32_t STAT[5] = {0xa6, 0xa7, 0xa9, 0xa8, 0x76c};
        line l = {{0}, 0};
        put(&l, "invoke InitStat [");
        for (int i = 0; i < 5; ++i) {
            if (i)
                put(&l, ",");
            put_json_string(&l, gt(env, STAT[i]));
        }
        put(&l, "]");
        emit(env, &l);
    }
    invoked(env, "SetInputBoxLength", 10);
    {
        line l = {{0}, 0};
        put(&l, "invoke InitClassInfo [[");
        for (int i = 0; i < MU_CSG_CLASSES; ++i) {
            const mu_csg_class *k = &mu_csg_classes[i];
            putf(&l, "%s{\"ButtonIndex\":%d,\"ClassType\":%d,\"ClassName\":", i ? "," : "", k->button, k->type);
            put_json_string(&l, gt(env, k->name_gt));
            putf(&l, ",\"Strength\":%d,\"Dexerity\":%d,\"Vitality\":%d,\"Energy\":%d,\"Charisma\":%d,\"Explain\":",
                 k->strength, k->dexterity, k->vitality, k->energy, k->charisma);
            put_json_string(&l, gt(env, k->explain_gt));
            putf(&l, ",\"CanNotBeCreated\":%s}", k->cannot_create ? "true" : "false");
        }
        put(&l, "]]");
        emit(env, &l);
    }
    invoked(env, "SetClassInfo", 1);
    invoked(env, "SetnumViewableSelctedWin", 10);
    return 1;
}
