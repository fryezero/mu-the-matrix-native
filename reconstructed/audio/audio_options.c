/* Data/Sound/Option.ini: the JSON document the client loads after FMOD init
 * (0x010ab7e0, from 0x0120e8c0) and writes at shutdown (0x010ab573, from
 * 0x01210eb3). The client uses a jsoncpp-style reader and styled stream
 * writer through a text-mode stream; this file reproduces the observed key
 * set, value conversions and byte format (CRLF line ends, tab indent, "%#.16g"
 * doubles with trailing zeros trimmed to one).
 */
#include "client_audio.h"

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void mu_audio_settings_fmod_default(mu_audio_settings *settings)
{
    /* FMOD channel groups start unmuted at volume 1.0 (platform default, used
     * when Option.ini is missing or unreadable: the client then applies
     * nothing). */
    memset(settings, 0, sizeof *settings);
    settings->master_volume = 1.0f;
    for (int i = 0; i < MU_AUDIO_GROUPS; i++) settings->group_volume[i] = 1.0f;
}

/* ---- minimal JSON value reader ------------------------------------------ */

enum { J_NULL, J_BOOL, J_NUMBER, J_STRING, J_ARRAY, J_OBJECT, J_ERROR };

typedef struct parser {
    const char *p, *end;
    int depth;
} parser;

static void skip_ws(parser *ps)
{
    while (ps->p < ps->end) {
        char c = *ps->p;
        if (c == ' ' || c == '\t' || c == '\r' || c == '\n') {
            ps->p++;
        } else if (c == '/' && ps->p + 1 < ps->end && ps->p[1] == '/') {  /* comments are accepted */
            while (ps->p < ps->end && *ps->p != '\n') ps->p++;
        } else if (c == '/' && ps->p + 1 < ps->end && ps->p[1] == '*') {
            ps->p += 2;
            while (ps->p + 1 < ps->end && !(ps->p[0] == '*' && ps->p[1] == '/')) ps->p++;
            ps->p = ps->p + 1 < ps->end ? ps->p + 2 : ps->end;
        } else {
            break;
        }
    }
}

static int match(parser *ps, const char *word)
{
    size_t n = strlen(word);
    if ((size_t)(ps->end - ps->p) >= n && memcmp(ps->p, word, n) == 0) {
        ps->p += n;
        return 1;
    }
    return 0;
}

/* A scanned scalar or the position of a container. */
typedef struct jvalue {
    int type;
    double number;
    int boolean;
    const char *start;  /* containers and strings: first byte after the opener */
} jvalue;

static int skip_value(parser *ps, jvalue *out);

static int skip_string(parser *ps)
{
    if (ps->p >= ps->end || *ps->p != '"') return 0;
    ps->p++;
    while (ps->p < ps->end && *ps->p != '"') {
        if (*ps->p == '\\') ps->p++;
        ps->p++;
    }
    if (ps->p >= ps->end) return 0;
    ps->p++;
    return 1;
}

static int skip_value(parser *ps, jvalue *out)
{
    skip_ws(ps);
    if (ps->p >= ps->end || ++ps->depth > 64) return 0;
    jvalue v = {J_ERROR, 0.0, 0, NULL};
    char c = *ps->p;
    if (c == '{' || c == '[') {
        char close = c == '{' ? '}' : ']';
        v.type = c == '{' ? J_OBJECT : J_ARRAY;
        ps->p++;
        v.start = ps->p;
        skip_ws(ps);
        if (ps->p < ps->end && *ps->p == close) {
            ps->p++;
        } else {
            for (;;) {
                if (v.type == J_OBJECT) {
                    skip_ws(ps);
                    if (!skip_string(ps)) return 0;
                    skip_ws(ps);
                    if (ps->p >= ps->end || *ps->p != ':') return 0;
                    ps->p++;
                }
                jvalue inner;
                if (!skip_value(ps, &inner)) return 0;
                skip_ws(ps);
                if (ps->p < ps->end && *ps->p == ',') { ps->p++; continue; }
                if (ps->p < ps->end && *ps->p == close) { ps->p++; break; }
                return 0;
            }
        }
    } else if (c == '"') {
        v.type = J_STRING;
        v.start = ps->p + 1;
        if (!skip_string(ps)) return 0;
    } else if (match(ps, "true")) {
        v.type = J_BOOL;
        v.boolean = 1;
    } else if (match(ps, "false")) {
        v.type = J_BOOL;
    } else if (match(ps, "null")) {
        v.type = J_NULL;
    } else if (c == '-' || (c >= '0' && c <= '9')) {
        char buffer[64];
        size_t n = 0;
        while (ps->p < ps->end && n + 1 < sizeof buffer &&
               (isdigit((unsigned char)*ps->p) || *ps->p == '-' || *ps->p == '+' || *ps->p == '.' ||
                *ps->p == 'e' || *ps->p == 'E'))
            buffer[n++] = *ps->p++;
        buffer[n] = 0;
        char *stop = NULL;
        v.number = strtod(buffer, &stop);
        if (!stop || *stop) return 0;
        v.type = J_NUMBER;
    } else {
        return 0;
    }
    ps->depth--;
    *out = v;
    return 1;
}

/* Looks up `key` among the members of the object whose body starts at start. */
static int object_member(const char *start, const char *end, const char *key, jvalue *out)
{
    parser ps = {start, end, 0};
    size_t key_length = strlen(key);
    skip_ws(&ps);
    if (ps.p < ps.end && *ps.p == '}') return 0;
    for (;;) {
        skip_ws(&ps);
        const char *name = ps.p + 1;
        if (!skip_string(&ps)) return 0;
        size_t name_length = (size_t)(ps.p - 1 - name);
        skip_ws(&ps);
        if (ps.p >= ps.end || *ps.p != ':') return 0;
        ps.p++;
        jvalue v;
        if (!skip_value(&ps, &v)) return 0;
        if (name_length == key_length && memcmp(name, key, key_length) == 0) {
            *out = v;
            return 1;
        }
        skip_ws(&ps);
        if (ps.p < ps.end && *ps.p == ',') { ps.p++; continue; }
        return 0;
    }
}

static int array_element(const char *start, const char *end, int index, jvalue *out)
{
    parser ps = {start, end, 0};
    skip_ws(&ps);
    if (ps.p < ps.end && *ps.p == ']') return 0;
    for (int i = 0;; i++) {
        jvalue v;
        if (!skip_value(&ps, &v)) return 0;
        if (i == index) {
            *out = v;
            return 1;
        }
        skip_ws(&ps);
        if (ps.p < ps.end && *ps.p == ',') { ps.p++; continue; }
        return 0;
    }
}

/* jsoncpp asBool/asFloat on null (missing member) yield false/0.0. */
static int as_bool(const jvalue *v, int *ok)
{
    switch (v->type) {
    case J_NULL: return 0;
    case J_BOOL: return v->boolean;
    case J_NUMBER: return v->number != 0.0;
    default: *ok = 0; return 0;
    }
}

static float as_float(const jvalue *v, int *ok)
{
    switch (v->type) {
    case J_NULL: return 0.0f;
    case J_BOOL: return v->boolean ? 1.0f : 0.0f;
    case J_NUMBER: return (float)v->number;
    default: *ok = 0; return 0.0f;
    }
}

int mu_audio_options_parse(const char *text, size_t length, mu_audio_settings *out)
{
    parser ps = {text, text + length, 0};
    jvalue root;
    if (!skip_value(&ps, &root)) return 0;
    skip_ws(&ps);
    if (ps.p != ps.end) return 0;
    mu_audio_settings s;
    memset(&s, 0, sizeof s);
    int ok = 1;
    jvalue v, mutes = {J_NULL, 0, 0, NULL}, volumes = {J_NULL, 0, 0, NULL};
    if (root.type == J_OBJECT) {
        const char *end = text + length;
        if (object_member(root.start, end, "MasterMute", &v)) s.master_mute = as_bool(&v, &ok);
        if (object_member(root.start, end, "MasterVolume", &v)) s.master_volume = as_float(&v, &ok);
        object_member(root.start, end, "ChannelMutes", &mutes);
        object_member(root.start, end, "ChannelVolumes", &volumes);
        for (int i = 0; i < MU_AUDIO_GROUPS; i++) {
            if (mutes.type == J_ARRAY && array_element(mutes.start, end, i, &v)) s.group_mute[i] = as_bool(&v, &ok);
            else if (mutes.type != J_ARRAY && mutes.type != J_NULL) ok = 0;
            if (volumes.type == J_ARRAY && array_element(volumes.start, end, i, &v))
                s.group_volume[i] = as_float(&v, &ok);
            else if (volumes.type != J_ARRAY && volumes.type != J_NULL) ok = 0;
        }
    } else if (root.type != J_NULL) {
        ok = 0;
    }
    if (!ok) return 0;
    *out = s;
    return 1;
}

/* ---- writer ---------------------------------------------------------------- */

/* jsoncpp-0.5 style valueToString(double), as the client's 0x00943757 does it:
 * "%#.16g", then trailing zeros trimmed so that two characters remain after
 * the last non-zero digit when a decimal point precedes it (0.5 -> "0.50",
 * 1.0 -> "1.0"). */
static void format_double(double value, char *buffer, size_t size)
{
    snprintf(buffer, size, "%#.16g", value);
    char *ch = buffer + strlen(buffer) - 1;
    if (*ch != '0') return;
    while (ch > buffer && *ch == '0') --ch;
    char *last_nonzero = ch;
    while (ch >= buffer) {
        if (*ch >= '0' && *ch <= '9') {
            --ch;
            continue;
        }
        if (*ch == '.') last_nonzero[2] = 0;  /* keep one zero after the point */
        return;
    }
}

size_t mu_audio_options_format(const mu_audio_settings *s, char *buffer, size_t size)
{
    char v[MU_AUDIO_GROUPS][40], master[40];
    for (int i = 0; i < MU_AUDIO_GROUPS; i++) format_double((double)s->group_volume[i], v[i], sizeof v[i]);
    format_double((double)s->master_volume, master, sizeof master);
    const char *b[2] = {"false", "true"};
    int n = snprintf(buffer, size,
                     "\r\n{\r\n"
                     "\t\"ChannelMutes\" : [ %s, %s, %s ],\r\n"
                     "\t\"ChannelVolumes\" : [ %s, %s, %s ],\r\n"
                     "\t\"MasterMute\" : %s,\r\n"
                     "\t\"MasterVolume\" : %s\r\n"
                     "}\r\n",
                     b[s->group_mute[0] != 0], b[s->group_mute[1] != 0], b[s->group_mute[2] != 0],
                     v[0], v[1], v[2], b[s->master_mute != 0], master);
    return n < 0 ? 0 : (size_t)n;
}
