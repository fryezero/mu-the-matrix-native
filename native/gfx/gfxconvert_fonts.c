/* Font imports and the oracle's Latin DefineFont3 subset. Shape bytes remain
 * untouched; only IDs, names, offsets and matching layout rows change. */
#define _POSIX_C_SOURCE 200809L
#include "gfxconvert.h"
#include <string.h>
#include <dirent.h>
#include <stdlib.h>
typedef struct Font {
    unsigned id, glyphs; int bold; char *name; char *export_name;
    Tag *tags; size_t ntags;
} Font;
typedef struct { Font *fonts; size_t n; } Library;
static Font *font_id(Library *lib, unsigned id) {
    for (size_t i = 0; i < lib->n; i++) if (lib->fonts[i].id == id) return &lib->fonts[i];
    if (lib->n >= 65536) fail("too many fonts");
    Font *f = &lib->fonts[lib->n++]; f->id = id; return f;
}
static Library library(const char *path) {
    Movie m = movie(path); Read r = {m.body.p, m.body.n, m.tags}; Tag t;
    Library lib = {mem(65536 * sizeof(Font)), 0};
    while (next_tag(&r, &t)) {
        Read d = t.data;
        if (t.code == 10 || t.code == 48 || t.code == 75 || t.code == 91 || t.code == 73 || t.code == 88) {
            unsigned id = u16(&d); Font *f = font_id(&lib, id);
            if (t.code == 48 || t.code == 75) {
                f->bold = (int)(u8(&d) & 1); u8(&d); f->name = pstring(&d); f->glyphs = u16(&d);
            }
            int define = t.code != 73 && t.code != 88;
            f->tags = grow(f->tags, (f->ntags + 1) * sizeof(Tag));
            if (define) { memmove(f->tags + 1, f->tags, f->ntags * sizeof(Tag)); f->tags[0] = t; }
            else f->tags[f->ntags] = t;
            f->ntags++;
        } else if (t.code == 56) {
            unsigned n = u16(&d);
            for (unsigned i = 0; i < n; i++) { unsigned id = u16(&d); char *name = cstring(&d); font_id(&lib, id)->export_name = name; }
        }
    }
    return lib;
}
static int latin(unsigned c) {
    return (c >= 0x20 && c <= 0x24f) || (c >= 0x2000 && c <= 0x22ff) ||
           (c >= 0x2460 && c <= 0x27bf) || (c >= 0xff00 && c <= 0xffef);
}
static Buf subset_font(Read d) {
    Read r = d; unsigned id = u16(&r), flags = u8(&r), lang = u8(&r), nlen = u8(&r);
    Read name = take(&r, nlen); unsigned n = u16(&r); size_t table = r.pos;
    if (!(flags & 4)) return (Buf){(unsigned char *)d.p, d.n, d.n};
    unsigned *offs = mem(((size_t)n + 1) * sizeof(unsigned)), *codes = mem((size_t)n * sizeof(unsigned));
    for (unsigned i = 0; i <= n; i++) offs[i] = flags & 8 ? u32(&r) : u16(&r);
    size_t table_end = r.pos;
    if (offs[n] > d.n - table || table + offs[n] < table_end) fail("invalid font code offset");
    r.pos = table + offs[n];
    unsigned kept = 0;
    for (unsigned i = 0; i < n; i++) { codes[i] = u16(&r); if (latin(codes[i])) kept++; }
    Read metrics = {0}, advances = {0}; Read *bounds = mem((size_t)n * sizeof(Read));
    unsigned nkern = 0; Read kern = {0};
    if (flags & 128) {
        metrics = take(&r, 6); advances = take(&r, 2 * (size_t)n);
        for (unsigned i = 0; i < n; i++) { size_t start = r.pos; rect_size(&r); bounds[i] = (Read){r.p + start, r.pos - start, 0}; }
        nkern = u16(&r); kern = take(&r, 6 * (size_t)nkern);
    }
    Buf out = {0}; word(&out, id); byte(&out, flags | 8); byte(&out, lang); byte(&out, nlen);
    add(&out, name.p, name.n); word(&out, kept);
    unsigned cur = 4 * kept + 4;
    for (unsigned i = 0; i < n; i++) {
        if (offs[i] < table_end - table || offs[i] > offs[i + 1] || offs[i + 1] > offs[n]) fail("invalid font glyph offset");
        if (latin(codes[i])) { dword(&out, cur); cur += offs[i + 1] - offs[i]; }
    }
    dword(&out, cur);
    for (unsigned i = 0; i < n; i++) if (latin(codes[i])) add(&out, d.p + table + offs[i], offs[i + 1] - offs[i]);
    for (unsigned i = 0; i < n; i++) if (latin(codes[i])) word(&out, codes[i]);
    if (flags & 128) {
        add(&out, metrics.p, metrics.n);
        for (unsigned i = 0; i < n; i++) if (latin(codes[i])) add(&out, advances.p + 2 * i, 2);
        for (unsigned i = 0; i < n; i++) if (latin(codes[i])) add(&out, bounds[i].p, bounds[i].n);
        Buf ks = {0}; unsigned count = 0;
        /* Membership is in the actual retained code table, not just the ranges. */
        unsigned char *have = mem(65536);
        for (unsigned i = 0; i < n; i++) if (latin(codes[i])) have[codes[i]] = 1;
        for (unsigned i = 0; i < nkern; i++) {
            Read k = take(&kern, 6), q = k; unsigned a = u16(&q), b = u16(&q);
            if (have[a] && have[b]) { count++; add(&ks, k.p, k.n); }
        }
        word(&out, count); add(&out, ks.p, ks.n);
    }
    return out;
}
static void emit(Buf *out, Font *f, unsigned id, const char *name, int subset) {
    for (size_t i = 0; i < f->ntags; i++) {
        Tag t = f->tags[i]; if (subset && t.code == 73) continue;
        Buf src = subset && t.code == 75 ? subset_font(t.data) : (Buf){(unsigned char *)t.data.p, t.data.n, t.data.n};
        Read r = {src.p, src.n, 0}; u16(&r); Buf b = {0}; word(&b, id);
        if ((t.code == 48 || t.code == 75) && name) {
            Read flags = take(&r, 2); unsigned nlen = u8(&r); take(&r, nlen);
            size_t n = strlen(name); if (n > 255) fail("font name too long");
            add(&b, flags.p, 2); byte(&b, (unsigned)n); add(&b, name, n);
        }
        add(&b, r.p + r.pos, r.n - r.pos); tag(out, t.code, b, 1);
    }
}
static int safe_rel(const char *s) {
    if (!*s || *s == '/' || strchr(s, '\\')) return 0;
    const char *part = s;
    do {
        const char *end = strchr(part, '/'); size_t n = end ? (size_t)(end - part) : strlen(part);
        if (!n || (n == 2 && !memcmp(part, "..", 2))) return 0;
        if (!end) return 1;
        part = end + 1;
    } while (*part);
    return 0;
}
static Font *by_name(Library lib, const char *name, int bold) {
    Font *found = NULL;
    for (size_t i = 0; i < lib.n; i++) if (lib.fonts[i].name && !strcmp(lib.fonts[i].name, name) && lib.fonts[i].bold == bold)
        found = &lib.fonts[i];
    return found;
}
static Font *resolve(const char *dir, const char *url, const char *sym, const char *config) {
    if (config) {
        /* Parse only the selected section, preserving fontlib and map order. */
        Buf text = gfx_read_text(path_join(dir, "fontconfig.txt"));
        char **libs = mem(4096 * sizeof(char *)); size_t nl = 0;
        char *fontname = NULL; int bold = 0, active = 0, seen = 0;
        char *save; char *line = strtok_r((char *)text.p, "\r\n", &save);
        for (; line; line = strtok_r(NULL, "\r\n", &save)) {
            while (*line == ' ' || *line == '\t') line++;
            if (strlen(line) >= 3 && !memcmp(line, "\xef\xbb\xbf", 3)) line += 3;
            if (!strncmp(line, "[FontConfig \"", 13)) {
                char *end = strchr(line + 13, '"'); if (!end) continue; *end = 0;
                active = !strcmp(line + 13, config); if (active) seen = 1;
            } else if (active && !strncmp(line, "fontlib \"", 9)) {
                char *end = strchr(line + 9, '"'); if (!end) continue; *end = 0;
                if (nl == 4096) fail("too many font libraries"); libs[nl++] = line + 9;
            } else if (active && !strncmp(line, "map \"", 5)) {
                char *symbol = line + 5, *end = strchr(symbol, '"'); if (!end) continue; *end++ = 0;
                char *value = strchr(end, '"'); if (!value) continue; value++;
                end = strchr(value, '"'); if (!end) continue; *end++ = 0;
                if (!strcmp(symbol, sym)) { fontname = value; while (*end == ' ' || *end == '\t') end++; bold = !strncmp(end, "Bold", 4); }
            }
        }
        if (!seen) fail("font config not found: %s", config);
        if (fontname) for (size_t i = 0; i < nl; i++) {
            if (!safe_rel(libs[i])) fail("unsafe font library path");
            Library lib = library(path_join(dir, libs[i]));
            Font *f = by_name(lib, fontname, bold);
            if (!f) f = by_name(lib, fontname, 0);
            if (!f) f = by_name(lib, fontname, 1);
            if (f) return f;
        }
    }
    if (!safe_rel(url)) fail("unsafe font import path");
    char *path = path_join(dir, url);
    if (!gfx_file_exists(path)) return NULL;
    Library lib = library(path);
    for (size_t i = 0; i < lib.n; i++) if (lib.fonts[i].export_name && !strcmp(lib.fonts[i].export_name, sym)) return &lib.fonts[i];
    return NULL;
}
static int compare_names(const void *a, const void *b) { return strcmp(*(char *const *)a, *(char *const *)b); }
static Font *compacted(const char *dir, const char *name) {
    DIR *d = opendir(dir); if (!d) fail("cannot read movie directory");
    char **files = mem(65536 * sizeof(char *)); size_t n = 0; struct dirent *ent;
    while ((ent = readdir(d))) {
        size_t len = strlen(ent->d_name);
        if (len < 4 || strcmp(ent->d_name + len - 4, ".ozg")) continue;
        if (n == 65536) { closedir(d); fail("too many movies"); }
        files[n] = mem(len + 1); strcpy(files[n++], ent->d_name);
    }
    closedir(d); qsort(files, n, sizeof(*files), compare_names);
    Font *best = NULL; unsigned glyphs = 0;
    for (size_t i = 0; i < n; i++) {
        /* These are ordinary local font source movies, never original instructions. */
        char *path = path_join(dir, files[i]); if (!gfx_try_movie(path)) continue;
        Library lib = library(path);
        for (size_t j = 0; j < lib.n; j++) {
            Font *f = &lib.fonts[j];
            if (f->name && !strcmp(f->name, name) && f->glyphs > glyphs) { best = f; glyphs = f->glyphs; }
        }
    }
    return best;
}
int inline_fonts(Buf *out, Tag t, const char *dir, const char *config, int subset) {
    Read r = t.data;
    if (t.code == 1005) {
        unsigned id = u16(&r); char *name = NULL;
        size_t end = 2; while (end < r.n && end < 68 && r.p[end] >= 32 && r.p[end] < 127) end++;
        if (end > 3 && end < r.n && r.p[end] == 0) {
            r.pos = 2; name = cstring(&r);
        } else for (size_t p = 2; p + 1 < r.n && p < 16; p++) {
            unsigned len = r.p[p]; if (len < 2 || len > 64 || len > r.n - p - 1) continue;
            unsigned i = 0; for (; i < len; i++) if (r.p[p + 1 + i] < 32 || r.p[p + 1 + i] >= 127) break;
            if (i == len) { name = mem(len + 1); memcpy(name, r.p + p + 1, len); break; }
        }
        Font *f = name ? compacted(dir, name) : NULL;
        if (!f) f = resolve(dir, "gfxfontlib.swf", "$NormalFont", config);
        if (f) emit(out, f, id, name ? name : "", 0);
        return f ? 0 : 1;
    }
    char *url = cstring(&r); if (t.code == 71) take(&r, 2); unsigned n = u16(&r); int kept = 0;
    for (unsigned i = 0; i < n; i++) {
        unsigned id = u16(&r); char *sym = cstring(&r); Font *f = resolve(dir, url, sym, config);
        if (!f || !f->ntags) { kept++; continue; }
        emit(out, f, id, sym, subset);
    }
    if (kept) tag(out, t.code, (Buf){(unsigned char *)t.data.p, t.data.n, t.data.n}, t.data.n >= 63);
    return kept;
}
