/* The create-character panel, the delete flow and the system menu (NATIVE-CHARCREATE-001): authored C
 * for the routines listed in charcreate.h.  Addresses are the pinned restored text (capture09). */
#include "charcreate.h"

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

/* JSON string as Python's json.dumps(ensure_ascii=False) writes it (bytes >= 0x80 pass through) */
static void put_json_n(line *l, const char *s, size_t n)
{
    put(l, "\"");
    const unsigned char *p = (const unsigned char *)(s ? s : "");
    for (size_t i = 0; i < n && p[i]; ++i) {
        char esc[8];
        unsigned char c = p[i];
        if (c == '"') put(l, "\\\"");
        else if (c == '\\') put(l, "\\\\");
        else if (c == '\n') put(l, "\\n");
        else if (c == '\r') put(l, "\\r");
        else if (c == '\t') put(l, "\\t");
        else if (c == '\b') put(l, "\\b");
        else if (c == '\f') put(l, "\\f");
        else if (c < 0x20) { snprintf(esc, sizeof esc, "\\u%04x", c); put(l, esc); }
        else { esc[0] = (char)c; esc[1] = 0; put(l, esc); }
    }
    put(l, "\"");
}

static void put_json(line *l, const char *s) { put_json_n(l, s, (size_t)-1); }

static void emit(const mu_ccr_env *e, const line *l)
{
    if (e->gfx && e->gfx->emit)
        e->gfx->emit(e->gfx->context, l->text);
}

static void call0(const mu_ccr_env *e, uint32_t address)
{
    line l = {{0}, 0};
    putf(&l, "call %08x", address);
    emit(e, &l);
}

static void callf(const mu_ccr_env *e, uint32_t address, const char *fmt, ...)
{
    line l = {{0}, 0};
    char buf[1024];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(buf, sizeof buf, fmt, ap);
    va_end(ap);
    putf(&l, "call %08x %s", address, buf);
    emit(e, &l);
}

static void invoke0(const mu_ccr_env *e, const char *method)
{
    line l = {{0}, 0};
    putf(&l, "invoke %s []", method);
    emit(e, &l);
}

static void invoked(const mu_ccr_env *e, const char *method, int32_t value)
{
    line l = {{0}, 0};
    putf(&l, "invoke %s [%d]", method, value);
    emit(e, &l);
}

static void invokes(const mu_ccr_env *e, const char *method, const char *value)
{
    line l = {{0}, 0};
    putf(&l, "invoke %s [", method);
    put_json(&l, value);
    put(&l, "]");
    emit(e, &l);
}

static uint32_t fbits(float f)
{
    uint32_t u;
    memcpy(&u, &f, 4);
    return u;
}

/* ---------------------------------------------------------------- records */

static uint8_t *character(const mu_ccr_env *e, int32_t index)
{
    if (index < 0 || index >= MU_CHARSEL_CHARACTERS || !e->gfx || !e->gfx->character)
        return NULL;   /* 0x009a13f4 */
    return e->gfx->character(e->gfx->context, index);
}

static uint8_t live(const uint8_t *c) { return c[MU_CHARSEL_OBJECT + MU_OBJ_LIVE]; }

static void setf(uint8_t *p, size_t o, float v) { memcpy(p + o, &v, 4); }

static const char *gt(const mu_ccr_env *e, int32_t index)
{
    const char *s = e->gfx && e->gfx->global_text ? e->gfx->global_text(e->gfx->context, index) : NULL;
    return s ? s : "";
}

static const char *record_name(const mu_ccr_env *e, const uint8_t *c)
{
    if (e->gfx && e->gfx->name)
        return e->gfx->name(e->gfx->context, c);
    uint32_t cap = (uint32_t)c[0x3658 + 0x14] | (uint32_t)c[0x3658 + 0x15] << 8 | (uint32_t)c[0x3658 + 0x16] << 16 |
                   (uint32_t)c[0x3658 + 0x17] << 24;
    return cap >= 0x10 ? "" : (const char *)(c + 0x3658);
}

/* the message-box calls: one line with the arguments in the callee's order */
static void msg1(const mu_ccr_env *e, const char *owner, int32_t id, const char *text, int32_t mode)
{
    line l = {{0}, 0};
    putf(&l, "call 00b3967c %s %d ", owner, id);
    put_json(&l, text);
    putf(&l, " \"\" 0 0 %d", mode);
    emit(e, &l);
}

static void msg2(const mu_ccr_env *e, int32_t id, const char *text)
{
    line l = {{0}, 0};
    putf(&l, "call 00b39648 w %d ", id);
    put_json(&l, text);
    put(&l, " \"\" 0 0 0 0");
    emit(e, &l);
}

/* ---------------------------------------------------- the panel 0xb49bf4 */

void mu_ccr_show_create(mu_csg_window *list, mu_ccr_window *w, const mu_ccr_env *e, uint8_t flag)
{
    w->create_open = flag;
    if (w->create_open)
        call0(e, 0x00af0ce9);   /* 0x01d22c60 ->0x00af0ce9(the window's movie): focus */
    else
        invoked(e, "SetClassInfo", 1);
    invoked(e, "SetCreateVisible", w->create_open);
    mu_csg_show(list, e->gfx, (uint8_t)(w->create_open == 0));
}

void mu_ccr_restrict_classes(mu_ccr_window *w, const mu_ccr_env *e)
{
    /* 0x00b4b684 tests +0x9c and then jumps unconditionally (`jmp 0x00b4b7ed`) past its body: the
     * rename mode's SetClassDisable loop, SetClassInfo and ExplainChangeName never run. */
    (void)w;
    (void)e;
}

/* ------------------------------------------------- the preview 0xb4a442 */

const mu_ccr_pose mu_ccr_poses[MU_CCR_CLASSES] = {
    /* 0x00b4a4a1, jump table 0x00b4aeb1 (executed in Unicorn by scripts/validate_charcreate.py --emit-poses) */
    {{0.0f, 0.0f, 0.0f}, {0.0f, 0.0f, -40.0f}, 4.9f, 1},
    {{0.0f, 0.0f, 0.0f}, {0.0f, 0.0f, -12.0f}, 5.0f, 1},
    {{4.8f, 0.0f, 0.0f}, {8.0f, 0.0f, 5.0f}, 8.0f, 1},
    {{0.0f, 0.0f, 4.8f}, {8.0f, 0.0f, -13.0f}, 5.0f, 1},
    {{0.0f, 0.0f, 0.0f}, {8.0f, 0.0f, -18.0f}, 5.1f, 1},
    {{4.8f, 0.0f, 0.0f}, {2.0f, 0.0f, 2.0f}, 8.0f, 1},
    {{2.0f, 0.0f, -7.5f}, {0.0f, 0.0f, 0.0f}, 5.1f, 0},
    {{4.8f, 0.0f, -2.0f}, {8.0f, 0.0f, -2.0f}, 8.0f, 1},
    {{10.8f, 0.0f, 2.8f}, {8.0f, 0.0f, -2.0f}, 8.0f, 1},
    {{10.8f, 0.0f, -1.0f}, {1.0f, 0.0f, -2.0f}, 8.0f, 1},
    {{10.8f, 0.0f, -1.0f}, {1.0f, 0.0f, -2.0f}, 5.2f, 1},
    {{14.8f, 0.0f, 5.0f}, {1.0f, 0.0f, -2.0f}, 7.6f, 1},
    {{10.8f, 0.0f, 4.0f}, {1.0f, 0.0f, -2.0f}, 0.078f, 1},
    {{10.8f, 0.0f, 0.0f}, {1.0f, 0.0f, -2.0f}, 8.6f, 1},
    {{14.8f, 0.0f, 0.0f}, {1.0f, 0.0f, -2.0f}, 7.6f, 1},
    {{12.8f, 0.0f, -23.0f}, {1.0f, 0.0f, -2.0f}, 0.19f, 1}};

void mu_ccr_preview_pose(mu_ccr_window *w, const mu_ccr_env *e)
{
    w->camera_offset[0] = w->camera_offset[1] = w->camera_offset[2] = 0.0f;
    uint8_t c = e->preview[MU_CHAR_CLASS];
    if (c >= MU_CCR_CLASSES)
        return;   /* `ja 0x00b4aeae` */
    const mu_ccr_pose *p = &mu_ccr_poses[c];
    uint8_t *o = e->preview + MU_CHARSEL_OBJECT;
    for (int k = 0; k < 3; ++k) {
        w->camera_offset[k] = p->camera_offset[k];
        if (p->sets_angle)
            setf(o, MU_OBJ_ANGLE + 4u * (unsigned)k, p->angle[k]);
    }
    setf(o, MU_OBJ_SCALE, p->scale);
}

void mu_ccr_set_selected_class(mu_ccr_window *w, const mu_ccr_env *e, uint8_t class_index)
{
    e->preview[MU_CHAR_CLASS] = class_index;
    /* CreateCharacter 0x0137d8a1(preview, model, x 0, y 0, angle 0.0) */
    callf(e, 0x0137d8a1, "p %d 0 0 00000000", MU_CCR_PREVIEW_MODEL + e->preview[MU_CHAR_CLASS]);
    e->preview[MU_CHARSEL_OBJECT + MU_CCR_OBJ_ACTION_FLAG] = 0;
    e->preview[MU_CHARSEL_OBJECT + MU_CCR_OBJ_FLAG_3] = 0;
    mu_ccr_preview_pose(w, e);
    callf(e, 0x012affa4, "p+0x3254 1");   /* SetAction(object, 1) */
}

/* -------------------------------------------- SetCreateBoardInfo 0xb4a349 */

void mu_ccr_board_info(mu_ccr_window *w, const mu_ccr_env *e, int32_t x, int32_t y, int32_t width, int32_t height)
{
    const float s = e->window_scale;   /* each product is a float product (mulss) */
    float px = (float)x * s, py = (float)y * s, pw = (float)width * s, ph = (float)height * s;
    w->board[0] = (int32_t)(e->window_x + px);
    w->board[1] = (int32_t)(e->window_y + py);
    w->board[2] = (int32_t)pw;
    w->board[3] = (int32_t)ph;
}

/* ------------------------------------------------------------ name checks */

static int lead(const mu_ccr_env *e, uint8_t c)
{
    return e->lead_byte ? e->lead_byte(e->gfx ? e->gfx->context : NULL, c) : 0;
}

/* _mbclen 0x01994240 */
static size_t mbclen(const mu_ccr_env *e, const unsigned char *p)
{
    return lead(e, p[0]) && p[1] ? 2 : 1;
}

/* 0x0185c95d(text, word, 0): an MBCS-stepped search for word in text */
static int mbcs_contains(const mu_ccr_env *e, const char *text, const char *word)
{
    long n = (long)strlen(word), diff = (long)strlen(text) - n;
    if (diff < 0)
        return 0;
    for (long i = 0; i <= diff; i += (long)mbclen(e, (const unsigned char *)text + i)) {
        int same = 1;
        for (long k = 0; k < n; ++k)
            if (text[i + k] != word[k]) {
                same = 0;
                break;
            }
        if (same)
            return 1;
    }
    return 0;
}

/* std::string::find(word) < size() */
static int contains(const char *text, size_t length, const char *word)
{
    size_t n = strlen(word);
    if (n == 0)
        return length > 0;   /* find("") is 0 */
    if (n > length)
        return 0;
    for (size_t i = 0; i + n <= length; ++i)
        if (!memcmp(text + i, word, n))
            return 1;
    return 0;
}

int mu_ccr_name_filtered(const mu_ccr_env *e, const char *name, size_t length)
{
    /* FilterName(kor) 0x0110cb45: any word of +0x38 found in the name */
    for (int32_t i = 0; i < e->filter_name_count; ++i)
        if (contains(name, length, e->filter_name[i] ? e->filter_name[i] : ""))
            return 1;
    /* Filter(kor) 0x0110c9f2: the name without spaces (0x0110c960), each word by 0x0185c95d */
    char stripped[256];
    size_t n = 0;
    for (size_t i = 0; i < length && n + 1 < sizeof stripped; ++i)
        if (name[i] != ' ')
            stripped[n++] = name[i];
    stripped[n] = 0;
    for (int32_t i = 0; i < e->filter_count; ++i)
        if (mbcs_contains(e, stripped, e->filter[i] ? e->filter[i] : ""))
            return 1;
    return 0;
}

int mu_ccr_name_invalid(const mu_ccr_env *e, const char *name)
{
    for (const unsigned char *p = (const unsigned char *)name; *p; ++p) {
        if (mbclen(e, p) == 1) {
            unsigned c = p[0];
            int ok = (c >= 0x30 && c < 0x3a) || (c >= 0x41 && c < 0x5b) || (c >= 0x61 && c <= 0x7a);
            if (!ok)
                return 1;
            continue;
        }
        unsigned a = p[0], b = p[1];
        if (a < 0x81 || a > 0xc8)
            return 1;
        int trail = (b >= 0x41 && b <= 0x5a) || (b >= 0x61 && b <= 0x7a) || (b >= 0x81 && b <= 0xfe);
        if (!trail)
            return 1;
        if (a >= 0xa1 && a <= 0xaf && b >= 0xa1)
            return 1;   /* the symbol rows */
        if (a == 0xc6 && b >= 0x53 && b <= 0xa0)
            return 1;
        if (a >= 0xc7 && a <= 0xc8 && b <= 0xa0)
            return 1;
        ++p;   /* the second byte */
    }
    return 0;
}

/* ------------------------------------------ OnEnterCharacterName 0xb49eca */

void mu_ccr_enter_name(mu_ccr_window *w, const mu_ccr_env *e, const char *name, size_t length, int32_t class_index)
{
    (void)class_index;   /* the movie's class argument is not read: the preview's class is sent */
    if (w->created >= w->limit) {
        msg1(e, "w", 0x64, gt(e, 0x1832), 0);   /* GlobalText through 0x011753c3 */
        return;
    }
    if (length < 4) {
        msg1(e, "w", 0x64, gt(e, 0x186), 0);
        return;
    }
    if (mu_ccr_name_filtered(e, name, length)) {
        msg1(e, "w", 0x64, gt(e, 0x6b3), 0);
        return;
    }
    if (mu_ccr_name_invalid(e, name)) {
        msg1(e, "w", 0x64, gt(e, 0x187), 0);
        return;
    }
    if (w->rename_mode == 1) {
        uint8_t *c = character(e, w->delete_target);
        if (c) {
            line l = {{0}, 0};
            put(&l, "call 009a4708 ");   /* (the character's name, the new name) */
            put_json(&l, record_name(e, c));
            put(&l, " ");
            put_json(&l, name);
            emit(e, &l);
        }
        return;
    }
    *e->protocol_state = 0x34;
    /* the request 0x009a4588/0x009a466c: strncpy(name, 10), class (class << 4) + skin of the preview */
    line l = {{0}, 0};
    put(&l, "call 009a466c ");
    put_json_n(&l, name, MU_CCR_NAME_MAX);
    putf(&l, " %d", (uint8_t)((e->preview[MU_CHAR_CLASS] << 4) + e->preview[MU_CHAR_SKIN]));
    emit(e, &l);
}

/* ------------------------------------------------- UpdateInput 0xb4b31a */

void mu_ccr_update_input(const mu_ccr_env *e, const char *text)
{
    /* the movie's text to the client code page (0x00b0c2f0) and back (0x00a99d93): identity here */
    if (strlen(text) < MU_CCR_NAME_MAX)
        return;
    char cut[MU_CCR_NAME_MAX + 1];
    memcpy(cut, text, MU_CCR_NAME_MAX);   /* resize(10) 0x009516a8 */
    cut[MU_CCR_NAME_MAX] = 0;
    invokes(e, "SetCharacterName", cut);
}

/* --------------------------------------------- UpdateCreateCount 0xb49d0d */

void mu_ccr_update_count(mu_ccr_window *w, const mu_ccr_env *e, int32_t created, int32_t limit)
{
    w->created = created;
    w->limit = limit;
    int32_t left = w->limit - w->created;
    /* the formatter 0x009d59cc/0x009d40f5/0x009d6d27 over GlobalText 0x1831 ("...: %d left") */
    const char *f = gt(e, 0x1831);
    char text[512];
    const char *at = strstr(f, "%d");
    if (at)
        snprintf(text, sizeof text, "%.*s%d%s", (int)(at - f), f, left, at + 2);
    else
        snprintf(text, sizeof text, "%s", f);
    invokes(e, "UpdateCreateCount", text);
}

void mu_ccr_reset_create(const mu_ccr_env *e)
{
    invoked(e, "SetInputExplainVisible", 1);   /* 0x00b4b278(1) */
    invokes(e, "SetCharacterName", "");
    invoked(e, "SetClassInfo", 1);
}

void mu_ccr_set_row(mu_csg_window *list, int32_t row)
{
    list->row = (uint32_t)row > 10u ? 0 : row;   /* `cmp 0xa; jbe`: 10 itself is kept */
}

void mu_ccr_set_target(mu_ccr_window *w, int32_t slot) { w->delete_target = slot; }

void mu_ccr_delete_pending(mu_ccr_window *w, int32_t slot)
{
    w->delete_target = slot;
    w->flag_79 = 1;
}

void mu_ccr_delete_clear(mu_ccr_window *w)
{
    w->delete_target = -1;
    w->flag_79 = 0;
}

/* --------------------------------------- the created answer 0x0122b648 */

uint8_t mu_ccr_class_from_server(uint8_t v)
{
    unsigned r = ((unsigned)(v >> 3) & 1u) << 4 | (unsigned)(v >> 4) | ((unsigned)(v >> 2) & 1u) << 5 |
                 ((unsigned)(v >> 1) & 1u) << 6;
    return (uint8_t)(r | ((unsigned)v & 1u) << 7);
}

void mu_ccr_created_answer(mu_csg_window *list, mu_ccr_window *w, const mu_ccr_env *e, const mu_ccr_created *p)
{
    if (p->result == 1) {
        int32_t slot = p->slot;
        /* x, y and the angle are 0 for slots 0..4; other slots pass uninitialised locals (the position
         * is then set by SetCharacterPosition) */
        callf(e, 0x0137c457, "%d", slot);   /* the slot's character released */
        uint8_t class_byte = mu_ccr_class_from_server(p->class_code);
        callf(e, 0x0137f824, "%d %d %d 00000000 00000000 00000000", slot, class_byte, e->preview[MU_CHAR_SKIN]);
        uint8_t *c = character(e, slot);
        if (c) {
            c[0x144] = (uint8_t)p->level;
            c[0x145] = (uint8_t)(p->level >> 8);
            c[MU_CHAR_CLASS] = class_byte;
            line l = {{0}, 0};
            putf(&l, "call 0129de8d r%d ", slot);
            put_json_n(&l, p->name, MU_CCR_NAME_MAX);
            emit(e, &l);
        }
        callf(e, 0x00da9ff3, "%d", slot);   /* SetCharacterPosition through the world handler of 0x5d */
        *e->protocol_state = 0x35;
        mu_ccr_reset_create(e);
        mu_ccr_show_create(list, w, e, 0);
        call0(e, 0x009a4dd7);   /* CCharSelMainWin UpdateDisplay */
        call0(e, 0x009a23d7);   /* CUIMng +0x63a0 */
        mu_ccr_set_row(list, slot);
        *e->init_scene = 0;     /* the scene is created again on the next tick */
        call0(e, 0x01287a66);
        mu_ccr_update_count(w, e, p->created, p->limit);
    } else if (p->result == 0) {
        mu_ccr_show_create(list, w, e, 1);
        msg1(e, "w", 0x64, gt(e, 0x6b4), 1);
    } else if (p->result == 2) {
        mu_ccr_show_create(list, w, e, 0);
        msg1(e, "w", 0x64, gt(e, 0x18c), 1);
    } else if (p->result == 5) {
        mu_ccr_show_create(list, w, e, 1);
        msg1(e, "w", 0x64, gt(e, 0x179b), 1);
    }
}

/* ------------------------------------------- message results 0xb49967 */

void mu_ccr_message_result(mu_csg_window *list, mu_ccr_window *w, const mu_ccr_env *e, int32_t id, int32_t button,
                           const char *text)
{
    switch (id) {
    case 0x64:   /* a create error: OK reopens the panel */
        if (button == 0)
            mu_ccr_show_create(list, w, e, 1);
        break;
    case 0x65:   /* "Would you like to delete %s character?" */
        if (button == 0) {
            char t[2048];
            snprintf(t, sizeof t, "%s\n%s", gt(e, 0xea7), gt(e, 0xea8));
            msg2(e, 0x66, t);
        } else if (button == 1) {
            call0(e, 0x00b399db);   /* 0x00b49cba: the Caution window's close */
        }
        break;
    case 0x66:   /* "You cannot restore a deleted character!" */
        if (button == 0) {
            line l = {{0}, 0};
            put(&l, "call 00b3974a w 103 ");
            put_json(&l, gt(e, 0x6b1));
            put(&l, " \"\" 20 0 0");
            emit(e, &l);
        } else if (button == 1) {
            call0(e, 0x00b399db);
        }
        break;
    case 0x67:   /* the password */
        if (button == 0)
            mu_ccr_delete_request(e, text ? text : "");
        else if (button == 1)
            call0(e, 0x00b399db);
        break;
    case 0x77: { /* "Character was deleted successfully." */
        int none = 1;
        for (int32_t i = 0; i < 5; ++i) {
            uint8_t *c = character(e, i);
            if (c && live(c) == 1) {
                none = 0;
                break;
            }
        }
        if (none)
            mu_ccr_show_create(list, w, e, 1);
        break;
    }
    default:
        break;
    }
}

/* ----------------------------------------------- delete 0xb4a0da / 0x12326c4 */

void mu_ccr_delete_request(const mu_ccr_env *e, const char *password)
{
    uint8_t *c = character(e, *e->gfx->selected);
    if (!c)
        return;
    *e->protocol_state = 0x38;
    line l = {{0}, 0};
    put(&l, "call 00b4c76a ");
    put_json_n(&l, record_name(e, c), MU_CCR_NAME_MAX);
    put(&l, " ");
    put_json_n(&l, password, 20);
    emit(e, &l);
}

void mu_ccr_delete_answer(mu_csg_window *list, mu_ccr_window *w, const mu_ccr_env *e, uint8_t result)
{
    uint8_t *selected = character(e, *e->gfx->selected);
    if (result == 1) {
        uint8_t *target = character(e, w->delete_target);
        int16_t key = target ? (int16_t)(target[MU_CHAR_KEY] | target[MU_CHAR_KEY + 1] << 8) : 0;
        callf(e, 0x0137c457, "%d", key);
        if (selected) {
            int32_t index = *e->gfx->selected;
            callf(e, 0x0129f4a5, "r%d+0x3254 0", index);
            callf(e, 0x00c9ea70, "r%d+0x3254", index);
            call0(e, 0x0106ba49);   /* 0x009c104e([0x0a39d754]) ->0x0106ba49 */
            *e->gfx->selected = -1;
            call0(e, 0x009a4dd7);
            call0(e, 0x009a23d7);
            msg1(e, "w", 0x77, gt(e, 0x6b2), 0);
        }
        *e->init_scene = 0;
        mu_ccr_set_row(list, 0);
        callf(e, 0x0137c276, "-1");
        call0(e, 0x01287a66);
    } else if (result == 0) {
        msg1(e, "0", 0, gt(e, 0x676), 0);
    } else if (result == 3) {
        msg1(e, "0", 0, gt(e, 0x1b7), 0);
    } else {
        msg1(e, "0", 0, gt(e, 0x191), 0);
    }
    mu_ccr_delete_clear(w);
}

/* ------------------------------------------------ the preview's render */

void mu_ccr_render_preview(mu_ccr_window *w, const mu_ccr_env *e)
{
    call0(e, 0x013960d2);   /* the animation step of (p, p+0x3254) */
    if (!e->animation_running)
        callf(e, 0x012affa4, "p+0x3254 0");
    uint8_t *o = e->preview + MU_CHARSEL_OBJECT;
    for (int k = 0; k < 3; ++k)
        setf(o, MU_OBJ_LIGHT + 4u * (unsigned)k, 1.0f);
    float position[3] = {5.0f - w->camera_offset[0], -500.0f - w->camera_offset[1], 46.0f - w->camera_offset[2]};
    float angle[3] = {-90.0f, 0.0f, 0.0f};
    *e->camera_fov = 10.0f;
    /* the camera walk 0x01854879(object position, offset, angle) */
    callf(e, 0x01854879, "p+0x33ac %08x %08x %08x %08x %08x %08x", fbits(position[0]), fbits(position[1]),
          fbits(position[2]), fbits(angle[0]), fbits(angle[1]), fbits(angle[2]));
    callf(e, 0x0184b27e, "%d %d %d %d", w->board[0], w->board[1], w->board[2], w->board[3]);   /* BeginOpengl */
    callf(e, 0x016d4fe4, "p+0x3254 1 0 0 -1 -1");                                               /* RenderObject */
    callf(e, 0x01849ec4, "0 0 %d %d", e->screen_width, e->screen_height);
    call0(e, 0x0184b6dd);
}

int mu_ccr_render_hook(mu_ccr_window *w, const mu_ccr_env *e)
{
    if (w->create_open)
        mu_ccr_render_preview(w, e);
    call0(e, 0x00aadcbf);
    return e->base_render ? 1 : 0;
}

/* ------------------------------------------------------- class names */

/* 0x0139cc2e(class, flag) by skin index 0x0139d6a2 (code = (tier - 1) * 16 + class & 0xf, see
 * reconstructed/model-codec character.h); every class byte executed in Unicorn
 * (scripts/validate_charcreate.py, family classname).  Codes 9/25/41/57 and 10/26/42/58 read GlobalText
 * through the std::string accessor 0x011753c3; with flag 0, codes 11 and 12 take 0x1750 / 0x1751. */
static const int16_t CLASS_TEXT[80] = {
    20,   21,   22,   23,   24,   1687, 3150, 4588, 5368, 5526, 5786, 5914, 5923, 6058, 6652, 6802,
    25,   26,   27,   2305, 2305, 1688, 2305, 2305, 5400, 5527, 5787, 5915, 5924, 6059, 6653, 6803,
    1669, 1668, 1670, 1671, 1672, 1689, 3151, 4589, 5401, 5528, 5788, 5916, 5925, 6060, 6654, 6804,
    5163, 5164, 5165, 5167, 5168, 5166, 5169, 5170, 5414, 5529, 5789, 5917, 5926, 6061, 6655, 6805,
    6286, 6287, 6288, 6290, 6291, 6289, 6292, 6293, 6294, 6295, 6296, 6297, 6298, 6299, 6656, 6806};

static uint8_t skin_index(uint8_t class_byte)
{
    /* 0x0139d6a2 = (class & 0xf) + 16 * (tier - 1); tier 0x0139cb8a from the high bits
     * (model-codec character.c mu_character_skin_index; repeated here to keep libcharsel standalone) */
    uint8_t tier;
    if (class_byte & 0x80) tier = 5;
    else if (class_byte & 0x40) tier = 4;
    else if (class_byte & 0x20) tier = 3;
    else if (class_byte & 0x10) tier = 2;
    else tier = 1;
    return (uint8_t)((class_byte & 0xf) + 16 * (tier - 1));
}

int32_t mu_ccr_class_name_text(uint8_t class_byte, uint8_t flag)
{
    uint8_t code = skin_index(class_byte);
    if (!flag && code == 11)
        return 0x1750;
    if (!flag && code == 12)
        return 0x1751;
    return code < 80 ? CLASS_TEXT[code] : 2305;
}

/* ---------------------------------------------------------- system menu */

static void scene_window(const mu_ccr_env *e, const char *which, uint8_t flag)
{
    callf(e, 0x00000010, "%s %d", which, flag);   /* (CUIMng + which)->vtable[+0x10](flag) */
}

void mu_csm_scene_windows(mu_csg_window *list, const mu_ccr_env *e, uint8_t flag)
{
    if (e->scene == 3) {
        scene_window(e, "ab0", flag);
    } else if (e->scene == 5) {
        scene_window(e, "4bb0", flag);
        mu_csg_show(list, e->gfx, flag);
    }
}

void mu_csm_toggle(mu_csg_window *list, const mu_ccr_env *e)
{
    if (e->menu_open) {
        invoke0(e, "closeWindow");   /* 0x00b6b221 */
        mu_csm_scene_windows(list, e, 1);
    } else {
        invoke0(e, "openWindow");    /* 0x00be7079 */
        mu_csm_scene_windows(list, e, 0);
    }
}

void mu_csm_init_text(const mu_ccr_env *e)
{
    static const struct { const char *member; int32_t gt; } TEXT[6] = {
        {"tfTitle", 0xd7a}, {"btnExit", 0x17d}, {"btnServerSelect", 0x17e}, {"btnCharSelect", 0x17f},
        {"btnOption", 0x181}, {"btnClose", 0x3ea}};
    line l = {{0}, 0};
    put(&l, "invoke InitText [{");
    for (int i = 0; i < 6; ++i) {
        putf(&l, "%s\"%s\":", i ? "," : "", TEXT[i].member);
        put_json(&l, gt(e, TEXT[i].gt));
    }
    put(&l, "}]");
    emit(e, &l);
}

/* 0x00b4c117: the list's row map becomes 0..count-1 (the old order goes to 0x00b4c6ce) */
static void list_order(mu_csg_window *list, const mu_ccr_env *e)
{
    char old[64];
    size_t n = 0;
    for (int32_t i = 0; i < MU_CSG_ROWS; ++i)
        n += (size_t)snprintf(old + n, sizeof old - n, "%s%d", i ? "," : "", list->slots[i]);
    callf(e, 0x00b4c6ce, "%s", old);
    for (int32_t i = 0; i < list->count && i < MU_CSG_ROWS; ++i)
        list->slots[i] = (uint8_t)i;
}

void mu_csm_event(mu_csg_window *list, const mu_ccr_env *e, const char *name)
{
    if (!strcmp(name, "onLoad")) {
        mu_csm_init_text(e);
        invoked(e, "SceneChange", e->scene);   /* 0x00c5cd60 */
        invoke0(e, "closeWindow");
        return;
    }
    if (!strcmp(name, "onUnload"))
        return;
    if (!strcmp(name, "onClose")) {
        invoke0(e, "closeWindow");
        mu_csm_scene_windows(list, e, 1);
        return;
    }
    if (!strcmp(name, "onExit")) {   /* 0x00c8cb13 */
        call0(e, 0x00c8cbe2);
        if (e->menu_check) {
            list_order(list, e);
            char text[512];
            const char *f = gt(e, 0x17c);   /* "You will exit game in %d seconds." (sprintf 0x009619dd) */
            const char *at = strstr(f, "%d");
            if (at)
                snprintf(text, sizeof text, "%.*s%d%s", (int)(at - f), f, 5, at + 2);
            else
                snprintf(text, sizeof text, "%s", f);
            callf(e, 0x009a5ab2, "0");
            line l = {{0}, 0};
            put(&l, "call 00b39b2f 0 118 ");
            put_json(&l, text);
            put(&l, " \"\" 5 0 1");
            emit(e, &l);
            callf(e, 0x009a5ab2, "0");
        } else {
            call0(e, 0x00c8cfa6);
            if (e->shutdown_blocked) {
                callf(e, 0x00c8cfb9, "0");
                call0(e, 0x01206598);   /* "ShutDown command can not be performed..." */
            }
        }
        invoke0(e, "closeWindow");
    }
    if (!strcmp(name, "onServerSelectClick")) {   /* 0x00c8cc8e */
        list_order(list, e);
        call0(e, 0x00c8cbe2);
        if (e->menu_check)
            callf(e, 0x009a5ab2, "2");
        invoke0(e, "closeWindow");
    }
    if (!strcmp(name, "onCharSelectClick")) {   /* 0x00c8cccb */
        call0(e, 0x00c8cbe2);
        if (e->menu_check)
            callf(e, 0x009a5ab2, "1");
        invoke0(e, "closeWindow");
    }
    if (!strcmp(name, "onOptionClick")) {   /* 0x00c8ccf4 */
        invoke0(e, "closeWindow");
        call0(e, 0x00be7079);   /* the option window (0x01d22c7c ->0x0095f160) openWindow */
    }
    /* 0x06fc9bdc ->0x0095fbdc() == 1 logs "winSystemMenu %s": a developer log, off (modelled as 0) */
}
