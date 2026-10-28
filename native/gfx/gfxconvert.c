/* Standalone first-run converter. Python gfxconvert.py remains the test oracle.
 * No interpreter or image library is used at runtime. The existing Modulus
 * reader handles the asset envelope; zlib produces the SWF and bitmap streams. */
#define _POSIX_C_SOURCE 200809L
#include "gfxconvert.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <math.h>
#include <stdarg.h>
#include <setjmp.h>
#include <dirent.h>
#include <errno.h>
#include <sys/stat.h>
#include <zlib.h>

/* Bound all decompression, image and dynamic-buffer allocations. */
#define LIMIT ((size_t)256 * 1024 * 1024)
extern int mu_modulus_decrypt(const unsigned char *, size_t, unsigned char *, size_t,
                             size_t *, char *, size_t);
typedef struct Allocation { void *p; struct Allocation *next; } Allocation;
static Allocation *allocated;
static jmp_buf error_jump;
static char error_text[1024];
static jmp_buf *error_target = &error_jump;
void fail(const char *fmt, ...) {
    va_list ap; va_start(ap, fmt); vsnprintf(error_text, sizeof(error_text), fmt, ap); va_end(ap);
    longjmp(*error_target, 1);
}
void *mem(size_t n) {
    if (n > LIMIT) fail("allocation exceeds 256 MiB");
    void *p = calloc(n ? n : 1, 1);
    Allocation *a = malloc(sizeof(*a));
    if (!p || !a) { free(p); free(a); fail("out of memory"); }
    a->p = p; a->next = allocated; allocated = a;
    return p;
}
void *grow(void *p, size_t n) {
    if (!p) return mem(n);
    if (n > LIMIT) fail("buffer exceeds 256 MiB");
    for (Allocation *a = allocated; a; a = a->next) if (a->p == p) {
        void *q = realloc(p, n ? n : 1);
        if (!q) fail("out of memory");
        a->p = q; return q;
    }
    fail("untracked allocation"); return NULL;
}
static void release(void) {
    while (allocated) { Allocation *a = allocated; allocated = a->next; free(a->p); free(a); }
}
void add(Buf *b, const void *p, size_t n) {
    if (n > LIMIT || b->n > LIMIT - n) fail("buffer exceeds 256 MiB");
    if (b->n + n > b->cap) {
        b->cap = b->n + n + 1024;
        b->p = grow(b->p, b->cap);
    }
    if (n) memcpy(b->p + b->n, p, n);
    b->n += n;
}
void byte(Buf *b, unsigned v) { unsigned char c = (unsigned char)v; add(b, &c, 1); }
void word(Buf *b, unsigned v) { byte(b, v); byte(b, v >> 8); }
void dword(Buf *b, uint32_t v) { word(b, v); word(b, v >> 16); }
void strz(Buf *b, const char *s) { add(b, s, strlen(s) + 1); }
Read take(Read *r, size_t n) {
    if (n > r->n - r->pos) fail("truncated input at %zu (need %zu)", r->pos, n);
    Read out = {r->p + r->pos, n, 0}; r->pos += n; return out;
}
unsigned u8(Read *r) { return *take(r, 1).p; }
unsigned u16(Read *r) { Read s = take(r, 2); return s.p[0] | (unsigned)s.p[1] << 8; }
uint32_t u32(Read *r) { uint32_t a = u16(r), b = u16(r); return a | b << 16; }
char *cstring(Read *r) {
    const unsigned char *p = r->p + r->pos;
    const unsigned char *end = memchr(p, 0, r->n - r->pos);
    if (!end) fail("unterminated string");
    size_t n = (size_t)(end - p); char *s = mem(n + 1); memcpy(s, p, n); r->pos += n + 1; return s;
}
char *pstring(Read *r) {
    unsigned n = u8(r); Read s = take(r, n); char *out = mem(n + 1); memcpy(out, s.p, n); return out;
}
size_t rect_size(Read *r) {
    if (r->pos == r->n) fail("missing RECT");
    size_t n = (5 + 4 * (r->p[r->pos] >> 3) + 7) / 8;
    take(r, n); return n;
}
int next_tag(Read *r, Tag *t) {
    if (r->pos == r->n) return 0;
    unsigned hdr = u16(r); size_t n = hdr & 63;
    if (n == 63) n = u32(r);
    t->code = (int)(hdr >> 6); t->data = take(r, n); return 1;
}
void tag(Buf *b, int code, Buf data, int force_long) {
    word(b, (unsigned)code << 6 | (data.n < 63 && !force_long ? (unsigned)data.n : 63));
    if (data.n >= 63 || force_long) dword(b, (uint32_t)data.n);
    add(b, data.p, data.n);
}
Buf deflate_buf(const void *p, size_t n, int level) {
    uLongf len = compressBound(n); Buf b = {mem(len), 0, len};
    if (compress2(b.p, &len, p, n, level) != Z_OK) fail("zlib compression failed");
    b.n = len; return b;
}
static Buf read_file(const char *path) {
    FILE *f = fopen(path, "rb");
    if (!f) fail("cannot read %s: %s", path, strerror(errno));
    if (fseek(f, 0, SEEK_END) || ftell(f) < 0) { fclose(f); fail("cannot size %s", path); }
    long size = ftell(f);
    if ((size_t)size > LIMIT) { fclose(f); fail("file exceeds 256 MiB"); }
    rewind(f); Buf b = {mem((size_t)size), (size_t)size, (size_t)size};
    int ok = fread(b.p, 1, b.n, f) == b.n; fclose(f);
    if (!ok) fail("cannot read %s", path);
    return b;
}
Buf container(const char *path) {
    Buf b = read_file(path);
    if (b.n >= 4 && (!memcmp(b.p, "DDS ", 4) || !memcmp(b.p, "CFX", 3) ||
        !memcmp(b.p, "GFX", 3) || !memcmp(b.p, "CWS", 3) || !memcmp(b.p, "FWS", 3))) return b;
    Buf out = {mem(b.n), 0, b.n}; char err[256];
    if (mu_modulus_decrypt(b.p, b.n, out.p, b.n, &out.n, err, sizeof(err))) fail("envelope: %s", err);
    return out;
}
Movie movie(const char *path) {
    Buf b = container(path); Read r = {b.p, b.n, 0}; Read sig = take(&r, 3);
    if (memcmp(sig.p, "CFX", 3) && memcmp(sig.p, "GFX", 3) && memcmp(sig.p, "CWS", 3) && memcmp(sig.p, "FWS", 3))
        fail("not a SWF/GFx movie");
    Movie m = {0}; m.version = (unsigned char)u8(&r); u32(&r);
    if (sig.p[0] == 'C') {
        z_stream z = {0};
        if (inflateInit(&z) != Z_OK) fail("zlib init failed");
        z.next_in = b.p + 8; z.avail_in = (uInt)(b.n - 8);
        int status;
        do {
            unsigned char block[32768]; z.next_out = block; z.avail_out = sizeof(block);
            status = inflate(&z, Z_NO_FLUSH);
            if (status != Z_OK && status != Z_STREAM_END) { inflateEnd(&z); fail("invalid compressed movie"); }
            if (m.body.n + sizeof(block) - z.avail_out > LIMIT - 1024) { inflateEnd(&z); fail("movie too large"); }
            add(&m.body, block, sizeof(block) - z.avail_out);
        } while (status != Z_STREAM_END);
        inflateEnd(&z);
    } else add(&m.body, b.p + 8, b.n - 8);
    Read h = {m.body.p, m.body.n, 0}; rect_size(&h); take(&h, 4); m.tags = h.pos; return m;
}
int gfx_try_movie(const char *path) {
    jmp_buf local; jmp_buf *previous = error_target; error_target = &local;
    if (setjmp(local)) { error_target = previous; return 0; }
    Movie m = movie(path); Read r = {m.body.p, m.body.n, m.tags}; Tag t;
    while (next_tag(&r, &t)) { /* validate the top-level stream */ }
    error_target = previous; return 1;
}
Buf gfx_read_text(const char *path) { Buf b = read_file(path); byte(&b, 0); return b; }
int gfx_file_exists(const char *path) { struct stat st; return !stat(path, &st); }
char *path_join(const char *a, const char *b) {
    size_t n = strlen(a) + strlen(b) + 2; char *s = mem(n); snprintf(s, n, "%s/%s", a, b); return s;
}
static void mkdirs(const char *path) {
    char *s = mem(strlen(path) + 1); strcpy(s, path);
    for (char *p = s + 1; ; p++) if (*p == '/' || !*p) {
        char c = *p; *p = 0;
        if (mkdir(s, 0700) && errno != EEXIST) fail("mkdir %s: %s", s, strerror(errno));
        *p = c; if (!c) break;
    }
}
static void write_file(const char *path, Buf b) {
    FILE *f = fopen(path, "wb"); if (!f) fail("cannot write %s", path);
    int ok = fwrite(b.p, 1, b.n, f) == b.n; if (fclose(f)) ok = 0;
    if (!ok) { remove(path); fail("write failed: %s", path); }
}
static void json_string(FILE *f, const char *s) {
    fputc('"', f);
    for (; *s; s++) { unsigned char c = (unsigned char)*s;
        if (c == '"' || c == '\\') { fputc('\\', f); fputc(c, f); }
        else if (c < 32) fprintf(f, "\\u%04x", c); else fputc(c, f);
    }
    fputc('"', f);
}
typedef struct { Image im; int w, h; unsigned id; } Atlas;
static int images, subimages, atlases, missing, unconverted;
static Buf convert(const char *path, const char *dir, const char *config, int subset,
                   int transparent, int bridge, char **vars, int nvars) {
    Movie m = movie(path); Read r = {m.body.p, m.body.n, m.tags}; Buf out = {0};
    Atlas *a = mem(65536 * sizeof(*a)); Tag t; int inserted = 0;
    while (r.pos < r.n) {
        size_t start = r.pos; next_tag(&r, &t); Read d = t.data;
        if (!inserted && t.code == 1 && (bridge || nvars)) {
            tag(&out, 12, host_actions(vars, nvars, bridge), 0); inserted = 1;
        }
        if (t.code == 1000 || (t.code == 9 && transparent)) continue;
        if (t.code == 1001 || t.code == 1009) {
            unsigned id = t.code == 1009 ? u32(&d) : u16(&d); u16(&d);
            int w = (int)u16(&d), h = (int)u16(&d); pstring(&d); char *file = pstring(&d);
            char *stem = file;
            for (char *p = file; *p; p++) if (*p == '/' || *p == '\\') stem = p + 1;
            char *ext = strrchr(stem, '.'); if (ext) *ext = 0;
            Buf name = {0}; add(&name, stem, strlen(stem)); strz(&name, ".ozd");
            char *src = path_join(dir, (char *)name.p); struct stat st;
            if (stat(src, &st)) { missing++; continue; }
            Image im = decode_dds(container(src));
            if (id >> 16) { a[id & 65535] = (Atlas){im, w, h, id}; atlases++; continue; }
            if (w && h && (im.w != w || im.h != h)) im = resize(im, w, h);
            tag(&out, 36, lossless(id, im), 0); images++; continue;
        }
        if (t.code == 1008) {
            unsigned id = u16(&d), index = u16(&d);
            int x1 = (int)u16(&d), y1 = (int)u16(&d), x2 = (int)u16(&d), y2 = (int)u16(&d);
            Atlas at = a[index]; if (!at.id) { unconverted++; continue; }
            Image im;
            if (at.w && at.h && (at.im.w != at.w || at.im.h != at.h)) {
                /* Python round is ties-to-even. nearbyint uses the default IEEE rounding mode. */
                im = crop(at.im, (int)nearbyint(x1 * ((double)at.im.w / at.w)),
                          (int)nearbyint(y1 * ((double)at.im.h / at.h)),
                          (int)nearbyint(x2 * ((double)at.im.w / at.w)),
                          (int)nearbyint(y2 * ((double)at.im.h / at.h)));
                im = resize(im, x2 > x1 ? x2 - x1 : 1, y2 > y1 ? y2 - y1 : 1);
            } else im = crop(at.im, x1, y1, x2, y2);
            tag(&out, 36, lossless(id, im), 0); subimages++; continue;
        }
        if (t.code == 57 || t.code == 71 || t.code == 1005) {
            unconverted += inline_fonts(&out, t, dir, config, subset); continue;
        }
        if (t.code >= 1002 && t.code <= 1007) { unconverted++; continue; }
        add(&out, r.p + start, r.pos - start);
    }
    if (!inserted && (bridge || nvars)) tag(&out, 12, host_actions(vars, nvars, bridge), 0);
    Buf body = {0}; add(&body, m.body.p, m.tags); add(&body, out.p, out.n);
    Buf swf = {0}; add(&swf, "CWS", 3); byte(&swf, m.version); dword(&swf, (uint32_t)body.n + 8);
    Buf z = deflate_buf(body.p, body.n, 9); add(&swf, z.p, z.n); return swf;
}
static int name_cmp(const void *a, const void *b) { return strcmp(*(char *const *)a, *(char *const *)b); }
static char **names(const char *dir, const char *suffix, int *count) {
    DIR *d = opendir(dir); if (!d) fail("cannot open %s", dir);
    char **out = mem(65536 * sizeof(*out)); struct dirent *ent; *count = 0;
    while ((ent = readdir(d))) {
        size_t n = strlen(ent->d_name), k = strlen(suffix);
        if (n < k || strcasecmp(ent->d_name + n - k, suffix)) continue;
        if (*count == 65536) { closedir(d); fail("too many files"); }
        out[*count] = mem(n + 1); strcpy(out[(*count)++], ent->d_name);
    }
    closedir(d); qsort(out, (size_t)*count, sizeof(*out), name_cmp); return out;
}
int main(int argc, char **argv) {
    const char *root = getenv("MU_GAME_ROOT"), *out = NULL, *config = NULL, *report = NULL;
    char **vars = calloc((size_t)argc, sizeof(*vars)), **selected = calloc((size_t)argc, sizeof(*selected));
    if (!vars || !selected) return 2;
    int nv = 0, ns = 0, subset = 0, bridge = 0, transparent = 0;
    for (int i = 1; i < argc; i++) {
        const char *arg = argv[i];
        if (!strcmp(arg, "--bridge")) bridge = 1;
        else if (!strcmp(arg, "--transparent")) transparent = 1;
        else if (i + 1 < argc) {
            char *v = argv[++i];
            if (!strcmp(arg, "--root")) root = v;
            else if (!strcmp(arg, "--out")) out = v;
            else if (!strcmp(arg, "--fontconfig")) config = v;
            else if (!strcmp(arg, "--report")) report = v;
            else if (!strcmp(arg, "--var")) vars[nv++] = v;
            else if (!strcmp(arg, "--movie")) selected[ns++] = v;
            else if (!strcmp(arg, "--font-subset") && !strcmp(v, "latin")) subset = 1;
            else { fprintf(stderr, "invalid option: %s\n", arg); return 2; }
        } else { fprintf(stderr, "missing value or invalid option: %s\n", arg); return 2; }
    }
    if (!root || !out) { fprintf(stderr, "usage: gfxconvert --root GAME --out DIRECTORY [--bridge --transparent --fontconfig English --font-subset latin --var PATH=VALUE]\n"); return 2; }
    if (setjmp(error_jump)) { fprintf(stderr, "%s\n", error_text); release(); return 1; }
    mkdirs(out);
    char *dir = path_join(root, "Data/Interface/GFx");
    int count; char **files = names(dir, ".ozg", &count);
    if (!count && !ns) fail("no .ozg movies in %s", dir);
    /* CLI metadata lives in the outer arena; per-movie scratch is reclaimed below. */
    Allocation *outer = allocated; allocated = NULL;
    FILE *rep = report ? fopen(report, "w") : NULL;
    if (report && !rep) { fprintf(stderr, "cannot write report\n"); return 1; }
    if (rep) fputs("{\n", rep);
    int errors = 0;
    for (int i = 0; i < (ns ? ns : count); i++) {
        const char *stem = ns ? selected[i] : files[i];
        images = subimages = atlases = missing = unconverted = 0;
        if (rep) { if (i) fputs(",\n", rep); }
        if (setjmp(error_jump)) {
            fprintf(stderr, "%s: ERROR %s\n", stem, error_text); errors++;
            if (rep) { json_string(rep, stem); fputs(":{\"error\":", rep); json_string(rep, error_text); fputc('}', rep); }
            release(); continue;
        }
        if (strchr(stem, '/') || strchr(stem, '\\') || !strcmp(stem, "..")) fail("invalid movie stem");
        Buf filename = {0}; add(&filename, stem, strlen(stem));
        if (ns) strz(&filename, ".ozg"); else byte(&filename, 0);
        char *s = mem(strlen(stem) + 1); strcpy(s, stem); if (!ns) s[strlen(s) - 4] = 0;
        Buf result = convert(path_join(dir, (char *)filename.p), dir, config, subset, transparent, bridge, vars, nv);
        Buf target = {0}; add(&target, s, strlen(s)); strz(&target, ".swf");
        write_file(path_join(out, (char *)target.p), result);
        printf("%s: %zu bytes, %d images, %d sub-images, %d atlases, %d missing, %d unconverted\n",
               s, result.n, images, subimages, atlases, missing, unconverted);
        if (rep) { json_string(rep, s); fprintf(rep, ":{\"bytes\":%zu,\"images\":%d,\"sub_images\":%d,\"atlases\":%d,\"missing_files\":%d,\"unconverted\":%d}",
                      result.n, images, subimages, atlases, missing, unconverted); }
        release();
    }
    if (!ns) {
        if (setjmp(error_jump)) { fprintf(stderr, "NaviMap: %s\n", error_text); errors++; }
        else {
            char *src = path_join(dir, "NaviMap"); struct stat st;
            if (!stat(src, &st) && S_ISDIR(st.st_mode)) {
                int n; char **nav = names(src, ".ozp", &n); char *dst = path_join(out, "NaviMap"); mkdirs(dst);
                for (int i = 0; i < n; i++) {
                    Buf b = read_file(path_join(src, nav[i]));
                    if (b.n >= 12 && !memcmp(b.p + 4, "\x89PNG\r\n\x1a\n", 8)) { b.p += 4; b.n -= 4; }
                    for (char *p = nav[i]; *p; p++) if (*p >= 'A' && *p <= 'Z') *p += 'a' - 'A';
                    write_file(path_join(dst, nav[i]), b);
                }
                if (rep) fprintf(rep, ",\n\"NaviMap\":{\"images\":%d}", n);
            }
        }
        release();
    }
    if (rep) { fputs("\n}\n", rep); if (fclose(rep)) errors++; }
    allocated = outer; release(); free(vars); free(selected); return errors ? 1 : 0;
}
