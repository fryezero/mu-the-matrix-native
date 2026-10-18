/* SPDX-License-Identifier: MIT */
/* mugl: opengl32.dll proxy that batches legacy immediate-mode geometry.
 *
 * Under CrossOver on Apple Silicon every 32-bit GL call crosses a WoW64 thunk.
 * Mu The Matrix draws its world with glBegin/glTexCoord/glVertex/glEnd, so
 * per-vertex calls dominate the frame. This proxy:
 *   - buffers glBegin..glEnd blocks in-process,
 *   - merges consecutive mergeable blocks (points/lines/triangles/quads) while no
 *     other GL call intervenes (current color/texcoord/normal changes between
 *     blocks are tracked, not sent),
 *   - submits a batch with glInterleavedArrays + glDrawArrays.
 * Every other export is a pass-through jump (stubs.S) that first synchronizes
 * (submits the pending batch and re-sends tracked current values). A non-vertex
 * call made inside a block replays that block as immediate mode and passes the
 * rest of the block through with its original primitive mode.
 * Build with SSE math (-msse2 -mfpmath=sse): x87 is extremely slow under Rosetta.
 */
#include <windows.h>
#include <GL/gl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stddef.h>

#include "names.h"
#include "triangles.h"
#include <limits.h>

typedef void (WINAPI *PFN1u)(GLenum);
typedef void (WINAPI *PFN0)(void);
typedef void (WINAPI *PFNfv)(const GLfloat *);
typedef void (WINAPI *PFNf3)(GLfloat, GLfloat, GLfloat);
typedef void (WINAPI *PFNget)(GLenum, GLfloat *);
typedef void (WINAPI *PFNia)(GLenum, GLsizei, const void *);
typedef void (WINAPI *PFNda)(GLenum, GLint, GLsizei);
typedef void (WINAPI *PFNpca)(GLbitfield);
typedef void (WINAPI *PFNcl)(GLuint);
typedef void (WINAPI *PFNcls)(GLsizei, GLenum, const void *);
typedef PROC (WINAPI *PFNgpa)(LPCSTR);
typedef BOOL (WINAPI *PFNswap)(HDC);

#define R(name, type) ((type)real_##name)

/* ---- state ---- */
unsigned char mugl_in_begin;     /* batching inside glBegin..glEnd */
unsigned char mugl_busy;         /* in_begin || pending || dirty: stubs must call mugl_sync */
static int passthrough;          /* inside a block that fell back to immediate mode */
static int pending;              /* batch (closed blocks) not yet submitted */
static GLenum cur_mode, batch_mode;
static GLfloat cur_t[2] = {0, 0}, cur_c[4] = {1, 1, 1, 1}, cur_n[3] = {0, 0, 1};
static int cur_known = 1;        /* tracked current values match what GL will have after sync */
static int dirty_t, dirty_c, dirty_n; /* tracked value differs from GL's current value */
static int merge_enabled = 1, batching_enabled = 1;
static int list_compiling;
static GLenum shade_model = GL_SMOOTH;
typedef void (WINAPI *PFNbindbuffer)(GLenum, GLuint);
static PFNbindbuffer bind_buffer;
static GLuint array_buffer;
static void (WINAPI *bind_vertex_array)(GLuint);
typedef void (WINAPI *PFNactive)(GLenum);
static PFNactive active_texture, client_active_texture;
static int client_known, client_units;
static GLint client_unit;
static GLboolean texture_arrays[32];
static int has_provoking_vertex, last_vertex = 1;

typedef struct { GLfloat t[2], c[4], n[3], v[3]; } Vtx;
static Vtx *vb; static int vcount, vcap;     /* batch vertices */
static int block_start;                      /* index of first vertex of the open block */
static GLfloat *pack; static int packcap;
static int set_t, set_c, set_n;              /* attribute specified anywhere in the batch */

static long st_blocks, st_verts, st_fallbacks, st_draws, st_frames;
static FILE *st_file; static DWORD st_last;
static long st_breaks[sizeof(mugl_names) / sizeof(mugl_names[0])]; static long st_modes[10]; static long st_modeverts[10];

static void disable_batching(const char *reason)
{
    if (batching_enabled && st_file) { fprintf(st_file, "batching disabled: %s\n", reason); fflush(st_file); }
    batching_enabled = 0;
}

static void update_busy(void) { mugl_busy = (unsigned char)(mugl_in_begin || pending || dirty_t || dirty_c || dirty_n); }

static void stats_tick(void)
{
    if (!st_file) return;
    DWORD now = GetTickCount();
    if (now - st_last < 2000) return;
    double secs = st_last ? (now - st_last) / 1000.0 : 1.0;
    fprintf(st_file, "fps=%.1f blocks=%ld verts=%ld v/block=%.1f draws=%ld v/draw=%.1f fallbacks=%ld\n",
            st_frames / secs, st_blocks, st_verts, st_blocks ? (double)st_verts / st_blocks : 0.0,
            st_draws, st_draws ? (double)st_verts / st_draws : 0.0, st_fallbacks);
    int top[6] = {-1, -1, -1, -1, -1, -1};
    for (int i = 0; i < (int)(sizeof(st_breaks) / sizeof(st_breaks[0])); i++) {
        if (!st_breaks[i]) continue;
        for (int k = 0; k < 6; k++) if (top[k] < 0 || st_breaks[i] > st_breaks[top[k]]) { for (int j = 5; j > k; j--) top[j] = top[j - 1]; top[k] = i; break; }
    }
    fprintf(st_file, "  breaks:");
    for (int k = 0; k < 6 && top[k] >= 0; k++) fprintf(st_file, " %s=%ld", mugl_names[top[k]], st_breaks[top[k]]);
    fprintf(st_file, "\n  modes:");
    static const char *mn[10] = {"POINTS","LINES","LINE_LOOP","LINE_STRIP","TRIANGLES","TRIANGLE_STRIP","TRIANGLE_FAN","QUADS","QUAD_STRIP","POLYGON"};
    for (int k = 0; k < 10; k++) if (st_modes[k]) fprintf(st_file, " %s=%ld(v/b %.1f)", mn[k], st_modes[k], (double)st_modeverts[k] / st_modes[k]);
    fprintf(st_file, "\n");
    memset(st_breaks, 0, sizeof st_breaks); memset(st_modes, 0, sizeof st_modes); memset(st_modeverts, 0, sizeof st_modeverts);
    fflush(st_file);
    st_blocks = st_verts = st_fallbacks = st_draws = st_frames = 0; st_last = now;
}

static void ensure_known(void)
{
    if (cur_known) return;
    GLfloat t4[4];
    R(glGetFloatv, PFNget)(GL_CURRENT_COLOR, cur_c);
    GLint active = 0x84c0;
    if (active_texture) {
        R(glGetIntegerv, void (WINAPI *)(GLenum, GLint *))(0x84e0, &active);
        if (active != 0x84c0) active_texture(0x84c0);
    }
    R(glGetFloatv, PFNget)(GL_CURRENT_TEXTURE_COORDS, t4);
    if (active_texture && active != 0x84c0) active_texture((GLenum)active);
    R(glGetFloatv, PFNget)(GL_CURRENT_NORMAL, cur_n);
    cur_t[0] = t4[0]; cur_t[1] = t4[1];
    /* A 2D interleaved array cannot represent R/Q texture coordinates. */
    if (t4[2] != 0 || t4[3] != 1) disable_batching("non-2D texture coordinates");
    GLfloat polygon[2];
    R(glGetFloatv, PFNget)(GL_POLYGON_MODE, polygon);
    if (polygon[0] != GL_FILL || polygon[1] != GL_FILL) disable_batching("non-fill polygon state");
    if (bind_buffer) {
        GLint binding;
        R(glGetIntegerv, void (WINAPI *)(GLenum, GLint *))(0x8894, &binding);
        array_buffer = (GLuint)binding; /* GL_ARRAY_BUFFER_BINDING */
    }
    if (has_provoking_vertex) {
        GLint convention;
        R(glGetIntegerv, void (WINAPI *)(GLenum, GLint *))(0x8e4f, &convention);
        last_vertex = convention == 0x8e4e;
    }
    GLfloat shade;
    R(glGetFloatv, PFNget)(GL_SHADE_MODEL, &shade);
    shade_model = (GLenum)shade;
    cur_known = 1;
}

static void *checked_realloc(void *, size_t);

static void push_vertex(GLfloat x, GLfloat y, GLfloat z)
{
    if (vcount == vcap) {
        vcap = vcap ? vcap * 2 : 8192;
        vb = checked_realloc(vb, sizeof(Vtx) * vcap);
    }
    Vtx *p = &vb[vcount++];
    p->t[0] = cur_t[0]; p->t[1] = cur_t[1];
    memcpy(p->c, cur_c, sizeof cur_c); memcpy(p->n, cur_n, sizeof cur_n);
    p->v[0] = x; p->v[1] = y; p->v[2] = z;
}

static void *checked_realloc(void *ptr, size_t size)
{
    void *result = realloc(ptr, size);
    if (!result && size) abort();
    return result;
}

static int varies(size_t off, size_t len)
{
    const char *first = (const char *)&vb[0] + off;
    for (int i = 1; i < vcount; i++)
        if (memcmp((const char *)&vb[i] + off, first, len)) return 1;
    return 0;
}

static void send_current(void)
{
    if (dirty_t) { R(glTexCoord2fv, PFNfv)(cur_t); dirty_t = 0; }
    if (dirty_c) { R(glColor4fv, PFNfv)(cur_c); dirty_c = 0; }
    if (dirty_n) { R(glNormal3fv, PFNfv)(cur_n); dirty_n = 0; }
}

/* InterleavedArrays addresses the client-selected unit. Immediate mode ignores
   all enabled client arrays, including other units' texture coordinate arrays. */
static void ensure_client_state(void)
{
    if (client_known || !client_active_texture) return;
    R(glGetIntegerv, void (WINAPI *)(GLenum, GLint *))(0x84e1, &client_unit);
    R(glGetIntegerv, void (WINAPI *)(GLenum, GLint *))(0x8871, &client_units);
    if (client_units < 1 || client_units > 32) abort();
    for (int i = 1; i < client_units; i++) {
        client_active_texture((GLenum)(0x84c0 + i));
        texture_arrays[i] = R(glIsEnabled, GLboolean (WINAPI *)(GLenum))(GL_TEXTURE_COORD_ARRAY);
    }
    client_active_texture((GLenum)client_unit);
    client_known = 1;
}

/* Submit vb[0..vcount) as one draw. Afterwards GL current values equal cur_*. */
static void submit_batch(void)
{
    if (vcount == 0) { send_current(); return; }
    int vt = varies(offsetof(Vtx, t), sizeof(vb[0].t));
    int vc = varies(offsetof(Vtx, c), sizeof(vb[0].c));
    int vn = varies(offsetof(Vtx, n), sizeof(vb[0].n));
    /* attributes constant over the batch: one current-value call, no array.
       Vertices always carry the tracked values, so sending vb[0] is exact. */
    if (!vt) R(glTexCoord2fv, PFNfv)(vb[0].t);
    if (!vc) R(glColor4fv, PFNfv)(vb[0].c);
    if (!vn) R(glNormal3fv, PFNfv)(vb[0].n);

    GLenum fmt; int stride;
    if (vt && vc)            { fmt = GL_T2F_C4F_N3F_V3F; stride = 12; }
    else if (vc)             { fmt = GL_C4F_N3F_V3F; stride = 10; }
    else if (vt && vn)       { fmt = GL_T2F_N3F_V3F; stride = 8; }
    else if (vn)             { fmt = GL_N3F_V3F; stride = 6; }
    else if (vt)             { fmt = GL_T2F_V3F; stride = 5; }
    else                     { fmt = GL_V3F; stride = 3; }
    int has_t = fmt == GL_T2F_C4F_N3F_V3F || fmt == GL_T2F_N3F_V3F || fmt == GL_T2F_V3F;
    int has_c = fmt == GL_T2F_C4F_N3F_V3F || fmt == GL_C4F_N3F_V3F;
    int has_n = fmt != GL_T2F_V3F && fmt != GL_V3F;
    if (vcount * stride > packcap) { packcap = vcount * stride * 2; pack = checked_realloc(pack, sizeof(GLfloat) * packcap); }
    GLfloat *o = pack;
    for (int i = 0; i < vcount; i++) {
        Vtx *p = &vb[i];
        if (has_t) { *o++ = p->t[0]; *o++ = p->t[1]; }
        if (has_c) { memcpy(o, p->c, 16); o += 4; }
        if (has_n) { memcpy(o, p->n, 12); o += 3; }
        memcpy(o, p->v, 12); o += 3;
    }
    GLint saved_vao = 0, saved_client_unit = 0x84c0;
    if (client_active_texture)
        R(glGetIntegerv, void (WINAPI *)(GLenum, GLint *))(0x84e1, &saved_client_unit);
    if (bind_vertex_array) {
        R(glGetIntegerv, void (WINAPI *)(GLenum, GLint *))(0x85b5, &saved_vao);
        if (saved_vao) bind_vertex_array(0);
    }
    /* Client memory is not legal in a nonzero ARB VAO. Work in default VAO
       state, save/restore that state, then restore the application's VAO. */
    ensure_client_state();
    R(glPushClientAttrib, PFNpca)(GL_CLIENT_VERTEX_ARRAY_BIT);
    if (client_active_texture) {
        for (int i = 1; i < client_units; i++) if (texture_arrays[i]) {
            client_active_texture((GLenum)(0x84c0 + i));
            R(glDisableClientState, PFN1u)(GL_TEXTURE_COORD_ARRAY);
        }
        client_active_texture(0x84c0);
    }
    /* CPU array pointers must not be interpreted as offsets into an existing
       VBO. Keep the application's client arrays and buffer binding intact. */
    if (bind_buffer && array_buffer) bind_buffer(0x8892, 0);
    R(glInterleavedArrays, PFNia)(fmt, 0, pack);
    R(glDrawArrays, PFNda)(batch_mode, 0, vcount);
    R(glPopClientAttrib, PFN0)();
    if (bind_vertex_array && saved_vao) bind_vertex_array((GLuint)saved_vao);
    if (bind_buffer && array_buffer) bind_buffer(0x8892, array_buffer);
    if (client_active_texture) client_active_texture((GLenum)saved_client_unit);
    /* arrays leave current values undefined; constant ones may differ from cur_* */
    if (has_t || memcmp(vb[0].t, cur_t, sizeof cur_t)) R(glTexCoord2fv, PFNfv)(cur_t);
    if (has_c || memcmp(vb[0].c, cur_c, sizeof cur_c)) R(glColor4fv, PFNfv)(cur_c);
    if (has_n || memcmp(vb[0].n, cur_n, sizeof cur_n)) R(glNormal3fv, PFNfv)(cur_n);
    dirty_t = dirty_c = dirty_n = 0;
    st_draws++;
    vcount = 0; set_t = set_c = set_n = 0;
}

/* Replay the open block as immediate mode (after submitting earlier closed
   blocks) and continue it unbatched. */
static void fallback_open_block(void)
{
    st_fallbacks++;
    int n = vcount - block_start;
    Vtx *tmp = NULL;
    if (n > 0) { tmp = checked_realloc(NULL, sizeof(Vtx) * n); memcpy(tmp, &vb[block_start], sizeof(Vtx) * n); }
    GLfloat save_t[2], save_c[4], save_n[3];
    memcpy(save_t, cur_t, sizeof cur_t); memcpy(save_c, cur_c, sizeof cur_c); memcpy(save_n, cur_n, sizeof cur_n);
    vcount = block_start;
    if (vcount) {
        /* the closed blocks' final values were current when they ended */
        memcpy(cur_t, vb[vcount - 1].t, sizeof cur_t); memcpy(cur_c, vb[vcount - 1].c, sizeof cur_c); memcpy(cur_n, vb[vcount - 1].n, sizeof cur_n);
        submit_batch();
    }
    vcount = 0; set_t = set_c = set_n = 0;
    R(glBegin, PFN1u)(cur_mode);
    for (int i = 0; i < n; i++) {
        Vtx *p = &tmp[i];
        if (i == 0 || memcmp(tmp[i - 1].t, p->t, sizeof p->t)) R(glTexCoord2fv, PFNfv)(p->t);
        if (i == 0 || memcmp(tmp[i - 1].c, p->c, sizeof p->c)) R(glColor4fv, PFNfv)(p->c);
        if (i == 0 || memcmp(tmp[i - 1].n, p->n, sizeof p->n)) R(glNormal3fv, PFNfv)(p->n);
        R(glVertex3fv, PFNfv)(p->v);
    }
    free(tmp);
    memcpy(cur_t, save_t, sizeof cur_t); memcpy(cur_c, save_c, sizeof cur_c); memcpy(cur_n, save_n, sizeof cur_n);
    R(glTexCoord2fv, PFNfv)(cur_t); R(glColor4fv, PFNfv)(cur_c); R(glNormal3fv, PFNfv)(cur_n);
    dirty_t = dirty_c = dirty_n = 0;
    mugl_in_begin = 0; pending = 0; passthrough = 1;
    update_busy();
}

/* Called by pass-through stubs with the export index (registers preserved by the stub). */
void mugl_sync(void);
void mugl_sync_from(int idx)
{
    if ((pending || mugl_in_begin) && idx >= 0 && (size_t)idx < sizeof(st_breaks) / sizeof(st_breaks[0])) st_breaks[idx]++;
    mugl_sync();
    if (idx >= 0 && (size_t)idx < sizeof(mugl_names) / sizeof(mugl_names[0]) && mugl_invalidates[idx])
    {
        cur_known = 0;
        const char *name = mugl_names[idx];
        if (!strcmp(name, "glPopClientAttrib") || !strcmp(name, "glInterleavedArrays") ||
            !strcmp(name, "glEnableClientState") || !strcmp(name, "glDisableClientState") ||
            !strncmp(name, "wglMake", 7)) client_known = 0;
    }
}

void mugl_sync(void)
{
    if (mugl_in_begin) { fallback_open_block(); return; }
    if (pending) { submit_batch(); pending = 0; }
    send_current();
    update_busy();
}

/* Batch class of a primitive: triangle-like blocks are converted to GL_TRIANGLES
   (exact for fans/strips; quads/polygons only under smooth shading, where the
   flat-shading provoking vertex does not matter). 0 = not mergeable. */
static GLenum canon(GLenum m)
{
    switch (m) {
    case GL_POINTS: case GL_LINES: case GL_TRIANGLES: return m;
    case GL_TRIANGLE_FAN: case GL_TRIANGLE_STRIP:
        return shade_model == GL_SMOOTH || last_vertex ? GL_TRIANGLES : 0;
    case GL_QUADS: case GL_QUAD_STRIP: case GL_POLYGON: return shade_model == GL_SMOOTH ? GL_TRIANGLES : 0;
    default: return 0;
    }
}
static Vtx *tri; static int tricap;
/* Rewrite vb[block_start..vcount) of primitive cur_mode as a triangle list. */
static void convert_open_block(void)
{
    int n = vcount - block_start;
    if (cur_mode == GL_TRIANGLES || cur_mode == GL_LINES) {
        int width = cur_mode == GL_TRIANGLES ? 3 : 2;
        vcount -= n % width;
        return;
    }
    if (cur_mode == GL_POINTS) return;
    if (n > tricap) { tricap = n; tri = checked_realloc(tri, sizeof(Vtx) * tricap); }
    if (n) memcpy(tri, &vb[block_start], sizeof(Vtx) * n);
    vcount = block_start;
    size_t count = mugl_triangle_count(cur_mode, (size_t)n);
    if (count > (size_t)(INT_MAX - vcount) / 3) abort();
    int needed = vcount + (int)(count * 3);
    if (needed > vcap) { vcap = needed; vb = checked_realloc(vb, sizeof(Vtx) * vcap); }
    for (size_t t = 0; t < count; t++) {
        size_t idx[3];
        mugl_triangle(cur_mode, (size_t)n, t, idx);
        for (int j = 0; j < 3; j++) vb[vcount++] = tri[idx[j]];
    }
}

/* ---- intercepted entry points ---- */
void WINAPI mugl_glBegin(GLenum mode)
{
    if (!batching_enabled || list_compiling || mugl_in_begin || passthrough) {
        mugl_sync(); R(glBegin, PFN1u)(mode);
        if (batching_enabled && !list_compiling) passthrough = 1;
        return;
    }
    ensure_known();
    GLenum cls = merge_enabled ? canon(mode) : 0;
    if (pending && !(cls && cls == batch_mode)) { submit_batch(); pending = 0; }
    if (!batching_enabled) { R(glBegin, PFN1u)(mode); return; }
    if (!pending) { vcount = 0; set_t = set_c = set_n = 0; batch_mode = cls ? cls : mode; }
    cur_mode = mode; block_start = vcount; mugl_in_begin = 1; pending = 0;
    update_busy();
}

void WINAPI mugl_glEnd(void)
{
    if (passthrough) { passthrough = 0; R(glEnd, PFN0)(); cur_known = 0; return; }
    if (!mugl_in_begin) { mugl_sync(); R(glEnd, PFN0)(); return; }
    mugl_in_begin = 0; st_blocks++; st_verts += vcount - block_start;
    if (cur_mode < 10) { st_modes[cur_mode]++; st_modeverts[cur_mode] += vcount - block_start; }
    if (merge_enabled && canon(cur_mode)) { convert_open_block(); pending = 1; }
    else submit_batch();
    update_busy();
}

#define VTX(x, y, z) do { if (mugl_in_begin) push_vertex((x), (y), (z)); else { if (mugl_busy) mugl_sync(); R(glVertex3f, PFNf3)((x), (y), (z)); } } while (0)
void WINAPI mugl_glVertex2f(GLfloat x, GLfloat y) { VTX(x, y, 0); }
void WINAPI mugl_glVertex2fv(const GLfloat *v) { VTX(v[0], v[1], 0); }
void WINAPI mugl_glVertex3f(GLfloat x, GLfloat y, GLfloat z) { VTX(x, y, z); }
void WINAPI mugl_glVertex3fv(const GLfloat *v) { VTX(v[0], v[1], v[2]); }
void WINAPI mugl_glVertex2i(GLint x, GLint y) { VTX((GLfloat)x, (GLfloat)y, 0); }
void WINAPI mugl_glVertex3i(GLint x, GLint y, GLint z) { VTX((GLfloat)x, (GLfloat)y, (GLfloat)z); }
void WINAPI mugl_glVertex2iv(const GLint *v) { VTX((GLfloat)v[0], (GLfloat)v[1], 0); }
void WINAPI mugl_glVertex3iv(const GLint *v) { VTX((GLfloat)v[0], (GLfloat)v[1], (GLfloat)v[2]); }
void WINAPI mugl_glVertex2d(GLdouble x, GLdouble y) { VTX((GLfloat)x, (GLfloat)y, 0); }
void WINAPI mugl_glVertex3d(GLdouble x, GLdouble y, GLdouble z) { VTX((GLfloat)x, (GLfloat)y, (GLfloat)z); }
void WINAPI mugl_glVertex3dv(const GLdouble *v) { VTX((GLfloat)v[0], (GLfloat)v[1], (GLfloat)v[2]); }

/* Attribute calls: inside a batched block record; between merged blocks only
   track (dirty, sent on sync); otherwise forward. */
static void attr_done(int *setf, int *dirtyf, void (*fwd)(void))
{
    if (mugl_in_begin) { *setf = 1; *dirtyf = 1; }
    else if (pending) { *dirtyf = 1; update_busy(); }
    else { if (mugl_busy) mugl_sync(); fwd(); }
}
static void fwd_t(void) { R(glTexCoord2fv, PFNfv)(cur_t); }
static void fwd_c(void) { R(glColor4fv, PFNfv)(cur_c); }
static void fwd_n(void) { R(glNormal3fv, PFNfv)(cur_n); }
void WINAPI mugl_glTexCoord2f(GLfloat s, GLfloat t) { if (!mugl_in_begin && !passthrough && !list_compiling && batching_enabled) ensure_known(); cur_t[0] = s; cur_t[1] = t; attr_done(&set_t, &dirty_t, fwd_t); }
void WINAPI mugl_glTexCoord2fv(const GLfloat *v) { mugl_glTexCoord2f(v[0], v[1]); }
void WINAPI mugl_glTexCoord2d(GLdouble s, GLdouble t) { mugl_glTexCoord2f((GLfloat)s, (GLfloat)t); }
void WINAPI mugl_glTexCoord2i(GLint s, GLint t) { mugl_glTexCoord2f((GLfloat)s, (GLfloat)t); }
void WINAPI mugl_glColor4f(GLfloat r, GLfloat g, GLfloat b, GLfloat a) { if (!mugl_in_begin && !passthrough && !list_compiling && batching_enabled) ensure_known(); cur_c[0] = r; cur_c[1] = g; cur_c[2] = b; cur_c[3] = a; attr_done(&set_c, &dirty_c, fwd_c); }
void WINAPI mugl_glColor3f(GLfloat r, GLfloat g, GLfloat b) { mugl_glColor4f(r, g, b, 1.0f); }
void WINAPI mugl_glColor3fv(const GLfloat *v) { mugl_glColor4f(v[0], v[1], v[2], 1.0f); }
void WINAPI mugl_glColor4fv(const GLfloat *v) { mugl_glColor4f(v[0], v[1], v[2], v[3]); }
void WINAPI mugl_glColor3d(GLdouble r, GLdouble g, GLdouble b) { mugl_glColor4f((GLfloat)r, (GLfloat)g, (GLfloat)b, 1.0f); }
void WINAPI mugl_glColor4d(GLdouble r, GLdouble g, GLdouble b, GLdouble a) { mugl_glColor4f((GLfloat)r, (GLfloat)g, (GLfloat)b, (GLfloat)a); }
#define UB(x) ((GLfloat)(x) / 255.0f)
void WINAPI mugl_glColor3ub(GLubyte r, GLubyte g, GLubyte b) { mugl_glColor4f(UB(r), UB(g), UB(b), 1.0f); }
void WINAPI mugl_glColor4ub(GLubyte r, GLubyte g, GLubyte b, GLubyte a) { mugl_glColor4f(UB(r), UB(g), UB(b), UB(a)); }
void WINAPI mugl_glColor3ubv(const GLubyte *v) { mugl_glColor4f(UB(v[0]), UB(v[1]), UB(v[2]), 1.0f); }
void WINAPI mugl_glColor4ubv(const GLubyte *v) { mugl_glColor4f(UB(v[0]), UB(v[1]), UB(v[2]), UB(v[3])); }
void WINAPI mugl_glNormal3f(GLfloat x, GLfloat y, GLfloat z) { if (!mugl_in_begin && !passthrough && !list_compiling && batching_enabled) ensure_known(); cur_n[0] = x; cur_n[1] = y; cur_n[2] = z; attr_done(&set_n, &dirty_n, fwd_n); }
void WINAPI mugl_glNormal3fv(const GLfloat *v) { mugl_glNormal3f(v[0], v[1], v[2]); }

void WINAPI mugl_glShadeModel(GLenum m) { mugl_sync(); if (!list_compiling && (m == GL_FLAT || m == GL_SMOOTH)) shade_model = m; R(glShadeModel, PFN1u)(m); }

void WINAPI mugl_glPolygonMode(GLenum face, GLenum mode)
{
    mugl_sync();
    if ((face == GL_FRONT || face == GL_BACK || face == GL_FRONT_AND_BACK) &&
        (mode == GL_LINE || mode == GL_POINT)) disable_batching("non-fill polygon mode");
    R(glPolygonMode, void (WINAPI *)(GLenum, GLenum))(face, mode);
}
GLint WINAPI mugl_glRenderMode(GLenum mode)
{
    mugl_sync();
    if (mode == GL_SELECT || mode == GL_FEEDBACK) disable_batching("selection/feedback mode");
    return R(glRenderMode, GLint (WINAPI *)(GLenum))(mode);
}

void WINAPI mugl_glNewList(GLuint list, GLenum mode)
{
    mugl_sync();
    R(glNewList, void (WINAPI *)(GLuint, GLenum))(list, mode);
    /* Valid application calls only. Never turn array submission into a list. */
    list_compiling = 1;
}
void WINAPI mugl_glEndList(void)
{
    R(glEndList, PFN0)();
    list_compiling = 0; cur_known = 0;
}

/* calls that change current values behind our back */
void WINAPI mugl_glPopAttrib(void) { mugl_sync(); R(glPopAttrib, PFN0)(); cur_known = 0; }
void WINAPI mugl_glCallList(GLuint l) { mugl_sync(); R(glCallList, PFNcl)(l); cur_known = 0; }
void WINAPI mugl_glCallLists(GLsizei n, GLenum type, const void *lists) { mugl_sync(); R(glCallLists, PFNcls)(n, type, lists); cur_known = 0; }

#include "fps.c"
BOOL WINAPI mugl_wglSwapBuffers(HDC dc)
{
    mugl_sync();
    fps_activetex = (void *)active_texture; fps_frame(dc);
    st_frames++; stats_tick();
    return R(wglSwapBuffers, PFNswap)(dc);
}

/* extension pointers: wrap so calls synchronize first */
static void extension_sync(void) { mugl_sync(); cur_known = 0; }

typedef struct { char name[64]; void *real; unsigned char *tramp; } Ext;
#define MAX_EXTENSIONS 4096
#define TRAMP_BYTES (MAX_EXTENSIONS * 64)
static Ext exts[MAX_EXTENSIONS]; static int nexts;
static unsigned char *tramp_mem; static int tramp_used;
static void extension_sync_from(int idx, const unsigned *args)
{
    extension_sync();
    const char *name = exts[idx].name;
    int ordinary_buffer = !strcmp(name, "glBindBuffer") || !strcmp(name, "glBindBufferARB");
    if (ordinary_buffer && args[0] == 0x8892) array_buffer = args[1];
    if (strstr(name, "ProvokingVertex") && (args[0] == 0x8e4d || args[0] == 0x8e4e))
        last_vertex = args[0] == 0x8e4e;
    /* Other-unit coordinates specified inside a block take the existing
       immediate replay fallback. Between blocks synchronization preserves the
       driver's constant current coordinates for those units. */
    if (strstr(name, "ClientActiveTexture")) client_known = 0;
    if (strstr(name, "VertexArray")) client_known = 0;
    if (strstr(name, "BindBuffer") && !ordinary_buffer)
        disable_batching(name);
}
PROC WINAPI mugl_wglGetProcAddress(LPCSTR name)
{
    mugl_sync();
    PROC p = R(wglGetProcAddress, PFNgpa)(name);
    if (!p || !name || p == (PROC)1 || p == (PROC)2 || p == (PROC)3 || p == (PROC)-1) return p;
    for (int i = 0; i < nexts; i++) if (!strcmp(exts[i].name, name) && exts[i].real == (void *)p) return (PROC)exts[i].tramp;
    if (nexts >= MAX_EXTENSIONS) { disable_batching("extension table exhausted"); return p; }
    if (!tramp_mem) tramp_mem = VirtualAlloc(NULL, TRAMP_BYTES, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
    if (!tramp_mem || tramp_used + 64 > TRAMP_BYTES) { disable_batching("extension trampoline allocation failed"); return p; }
    if (!strcmp(name, "glBindBuffer") || !strcmp(name, "glBindBufferARB")) {
        bind_buffer = (PFNbindbuffer)(void *)p;
        cur_known = 0;
    }
    if (!strcmp(name, "glActiveTexture") || !strcmp(name, "glActiveTextureARB"))
        active_texture = (PFNactive)(void *)p;
    if (!strcmp(name, "glClientActiveTexture") || !strcmp(name, "glClientActiveTextureARB")) {
        client_active_texture = (PFNactive)(void *)p;
        client_known = 0;
    }
    if (!strcmp(name, "glBindVertexArray") || !strcmp(name, "glBindVertexArrayAPPLE")) {
        bind_vertex_array = (void (WINAPI *)(GLuint))(void *)p;
        client_known = 0;
    }
    if (strstr(name, "ProvokingVertex")) { has_provoking_vertex = 1; cur_known = 0; }
    Ext *e = &exts[nexts++];
    strncpy(e->name, name, 63); e->real = (void *)p;
    unsigned char *c = tramp_mem + tramp_used; tramp_used += 64; e->tramp = c;
    void **slot = &e->real;
    /* pushad; pushfd; lea eax,[esp+40] (original first argument);
       push eax; push index; call sync_from; add esp,8; popfd; popad; jmp real.
       The callback observes arguments but never changes the caller's stack. */
    unsigned char *q = c;
    *q++ = 0x60; *q++ = 0x9c;
    *q++ = 0x8d; *q++ = 0x44; *q++ = 0x24; *q++ = 40;
    *q++ = 0x50;
    *q++ = 0x68; *(int *)q = nexts - 1; q += 4;
    *q++ = 0xe8; *(int *)q = (int)((unsigned char *)extension_sync_from - (q + 4)); q += 4;
    *q++ = 0x83; *q++ = 0xc4; *q++ = 8;
    *q++ = 0x9d; *q++ = 0x61;
    *q++ = 0xff; *q++ = 0x25; *(void ***)q = slot; q += 4;
    FlushInstructionCache(GetCurrentProcess(), c, 64);
    return (PROC)c;
}

/* ---- loading ---- */
static HMODULE real_mod;
static int load_real(HINSTANCE self)
{
    char path[MAX_PATH] = "";
    HMODULE m = LoadLibraryA("C:\\windows\\system32\\opengl32.dll");
    if (m && m != self) { real_mod = m; GetModuleFileNameA(m, path, sizeof path); }
    if (!real_mod) { fprintf(stderr, "mugl: cannot load system32 builtin OpenGL (%lu)\n", GetLastError()); return 0; }
    for (size_t i = 0; i < sizeof(mugl_names) / sizeof(mugl_names[0]); i++)
    {
        *mugl_slots[i] = (void *)GetProcAddress(real_mod, mugl_names[i]);
        if (!*mugl_slots[i]) { fprintf(stderr, "mugl: missing real export %s\n", mugl_names[i]); return 0; }
    }
    const char *mode = getenv("MUGL_MODE"); /* "off" = pure pass-through, "nomerge" = per-block */
    if (mode && !strcmp(mode, "off")) batching_enabled = 0;
    if (mode && !strcmp(mode, "nomerge")) merge_enabled = 0;
    st_last = GetTickCount();
    if (getenv("MUGL_STATS")) {
        st_file = fopen(getenv("MUGL_STATS"), "a");
        if (st_file) { fprintf(st_file, "mugl loaded; real=%s mode=%s\n", path, mode ? mode : "merge"); fflush(st_file); }
    }
    return 1;
}

BOOL WINAPI DllMain(HINSTANCE inst, DWORD reason, LPVOID reserved)
{
    (void)reserved;
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(inst);
        if (!load_real(inst)) return FALSE;
    }
    return TRUE;
}
