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
 * rest of the block through unchanged, so semantics never depend on batching.
 * Build with SSE math (-msse2 -mfpmath=sse): x87 is extremely slow under Rosetta.
 */
#include <windows.h>
#include <GL/gl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stddef.h>
#include <math.h>

#include "names.h"
#include "private-build.h"
#include "../mumodes/modehook.c"

typedef ptrdiff_t GLsizeiptr; typedef ptrdiff_t GLintptr;

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
static int dirty_t, dirty_c, dirty_n; /* tracked value differs from GL's current value (derived) */
static GLfloat gl_t[2], gl_c[4], gl_n[3]; static int gl_t_ok, gl_c_ok, gl_n_ok; /* values GL holds */
static int owned;                /* our interleaved arrays are set (client attrib pushed) */
static GLenum owned_fmt; static GLfloat *owned_ptr;
static int vbo_seen; static void *real_bindbuf; /* glBindBuffer(ARB) seen via wglGetProcAddress */
static int vbo_emu; static GLuint emu_bind[2], real_bind[2]; static long st_sub_bytes, st_sub_calls;
static int mstk_valid = 1; static int mmode_known = 1; static GLenum mmode = GL_MODELVIEW; static void matrix_modified(void);
static GLint saved_array_buffer; static GLuint bound_buf[2]; /* game's GL_ARRAY_BUFFER / GL_ELEMENT_ARRAY_BUFFER */ /* game's GL_ARRAY_BUFFER binding, unbound while our arrays are owned */
static int merge_enabled = 1, batching_enabled = 1, nodraw;
/* timing mode ("+time" in the mode file): QPC time spent inside selected real GL calls */
static int time_mode; static long long tm_ticks[11]; static long tm_calls[11];
static const char *tm_names[11] = {"draw", "arrays", "clientattrib", "popattrib", "enable", "bindtex", "swap", "pack", "meshloop", "meshtotal", "shadow"};
#define TIMED(slot, stmt) do { if (time_mode) { LARGE_INTEGER t0_, t1_; QueryPerformanceCounter(&t0_); stmt; QueryPerformanceCounter(&t1_); tm_ticks[slot] += t1_.QuadPart - t0_.QuadPart; tm_calls[slot]++; } else { stmt; } } while (0)

typedef struct { GLfloat t[2], c[4], n[3], v[3]; } Vtx;
typedef char vtx_layout_check[(sizeof(Vtx) == 48 && offsetof(Vtx, v) == 36) ? 1 : -1];
static int zero_copy_full;   /* hotpatch bit 2048: draw T2F_C4F_N3F_V3F batches straight from vb */
static int strided_arrays, owned_strided;   /* hotpatch bit 4096: all batch formats read vb in place (stride 48) */
typedef void (WINAPI *PFNptr4)(GLint, GLenum, GLsizei, const void *);
typedef void (WINAPI *PFNptr3)(GLenum, GLsizei, const void *);
static Vtx *vb; static int vcount, vcap;     /* batch vertices */
static int block_start;                      /* index of first vertex of the open block */
static GLfloat *pack; static int packcap;
static int set_t, set_c, set_n;              /* attribute specified anywhere in the batch */

static long st_blocks, st_verts, st_fallbacks, st_draws, st_frames;
static FILE *st_file; static DWORD st_last;
typedef struct { char name[64]; void *real; unsigned char *tramp; unsigned char flags; } Ext;
void mugl_sync_ext(int i);
static unsigned char ext_flags(const char *n);
static Ext exts[512]; static int nexts;
static long st_breaks[400]; static long st_skipped; static long st_orphans, st_subs; static void forget_state(void); static int count_mode; static long st_calls[400]; static long st_ext[512]; static long st_modes[10]; static long st_modeverts[10];

/* One-shot GL stream trace (diagnostic, v7.3): C:\mutools\mugl-trace.txt holding a frame count starts it; the
   stream of the next frames is written to C:\mutools\mugl-trace-<frame>.txt (see trace format in stall.c). */
static int ts_active_flag;   /* terrain run open (terrain.c) */
static int mugl_client;      /* this process is the client (main.exe): only then are code patches, pacing and client reads used */
static int cs_dirty;         /* deferred client-array enables differ from GL (lazy client state, bit 262144) */
static int cs_lazy; static unsigned char cs_real[6], cs_want[6]; static long st_cs_skipped, st_cs_sent;
static int lz_on, lz_n, lz_list; static long st_lz_deferred, st_lz_cancelled, st_lz_sent, st_tp_skipped; static void lz_apply(void);
static int tr_on, tr_frames; static char *tr_buf; static size_t tr_len, tr_cap;
static void tr_add(const char *fmt, ...) __attribute__((format(printf, 1, 2)));
#include <stdarg.h>
static void tr_add(const char *fmt, ...)
{
    if (tr_cap - tr_len < 256) { size_t nc = tr_cap ? tr_cap * 2 : (1u << 24); char *nb = realloc(tr_buf, nc); if (!nb) { tr_on = 0; return; } tr_buf = nb; tr_cap = nc; }
    va_list ap; va_start(ap, fmt); int n = vsnprintf(tr_buf + tr_len, tr_cap - tr_len, fmt, ap); va_end(ap);
    if (n > 0) tr_len += (size_t)n;
}
#define TR(...) do { if (tr_on) tr_add(__VA_ARGS__); } while (0)
static void update_busy(void)
{
    dirty_t = !gl_t_ok || memcmp(gl_t, cur_t, sizeof gl_t);
    dirty_c = !gl_c_ok || memcmp(gl_c, cur_c, sizeof gl_c);
    dirty_n = !gl_n_ok || memcmp(gl_n, cur_n, sizeof gl_n);
    mugl_busy = (unsigned char)(count_mode || tr_on || ts_active_flag || cs_dirty || lz_n || mugl_in_begin || pending || owned || dirty_t || dirty_c || dirty_n);
}
static void set_gl_t(const GLfloat *v) { if (!gl_t_ok || memcmp(gl_t, v, sizeof gl_t)) { R(glTexCoord2fv, PFNfv)(v); memcpy(gl_t, v, sizeof gl_t); gl_t_ok = 1; } }
static void set_gl_c(const GLfloat *v) { if (!gl_c_ok || memcmp(gl_c, v, sizeof gl_c)) { R(glColor4fv, PFNfv)(v); memcpy(gl_c, v, sizeof gl_c); gl_c_ok = 1; } }
static void set_gl_n(const GLfloat *v) { if (!gl_n_ok || memcmp(gl_n, v, sizeof gl_n)) { R(glNormal3fv, PFNfv)(v); memcpy(gl_n, v, sizeof gl_n); gl_n_ok = 1; } }
static void forget_gl_current(void) { gl_t_ok = gl_c_ok = gl_n_ok = 0; }
static void release_arrays(void)
{
    if (!owned) return;
    TIMED(2, R(glPopClientAttrib, PFN0)());
    if (saved_array_buffer) { ((void (WINAPI *)(GLenum, GLuint))real_bindbuf)(0x8892, (GLuint)saved_array_buffer); real_bind[0] = (GLuint)saved_array_buffer; }
    saved_array_buffer = 0;
    owned = 0; owned_fmt = 0; owned_ptr = NULL; owned_strided = 0;
}

static LARGE_INTEGER qpf; static long long sleep_ticks; static long xf_calls, xf_checked, xf_bad; static void md_stats(FILE *f); static void sh_stats(FILE *f); static void td_stats(FILE *f); static long st_pace_skips; static long long st_fmtverts[6]; static void pace_stats(FILE *f); static void io_stats(FILE *f); static void ts_stats(FILE *f); static void jp_stats(FILE *f); static int jp_install(int on, int verify); static void cr_stats(FILE *f); static int cr_install(int on, int verify);
void mugl_sync_from(int idx);
static void matrix_modified(void);
#include "gpudiag.c"
#include "cull.c"
static void stats_tick(void)
{
    if (!st_file) return;
    DWORD now = GetTickCount();
    if (now - st_last < 2000) return;
    double secs = st_last ? (now - st_last) / 1000.0 : 1.0;
    if (qpf.QuadPart && st_frames) { double sl = (double)sleep_ticks / qpf.QuadPart; fprintf(st_file, "work=%.2fms sleep=%.2fms ", (secs - sl) * 1000 / st_frames, sl * 1000 / st_frames); }
    sleep_ticks = 0;
    if (xf_calls) { fprintf(st_file, "xform calls=%ld checked=%ld mismatches=%ld\n", xf_calls, xf_checked, xf_bad); xf_calls = 0; }
    md_stats(st_file); sh_stats(st_file); td_stats(st_file); jp_stats(st_file); cr_stats(st_file);
    if (time_mode && qpf.QuadPart && st_frames) {
        fprintf(st_file, "time/frame:");
        for (int k = 0; k < 11; k++) if (tm_calls[k]) fprintf(st_file, " %s=%.2fms(%ld)", tm_names[k], tm_ticks[k] * 1000.0 / qpf.QuadPart / st_frames, tm_calls[k] / st_frames);
        static const char *fn[6] = {"T2F_C4F_N3F_V3F", "C4F_N3F_V3F", "T2F_N3F_V3F", "N3F_V3F", "T2F_V3F", "V3F"};
        fprintf(st_file, "\n  packed verts/frame:");
        for (int k = 0; k < 6; k++) if (st_fmtverts[k]) fprintf(st_file, " %s=%lld", fn[k], st_fmtverts[k] / st_frames);
        memset(st_fmtverts, 0, sizeof st_fmtverts);
        fprintf(st_file, "\n"); memset(tm_ticks, 0, sizeof tm_ticks); memset(tm_calls, 0, sizeof tm_calls);
    }
    cull_stats(st_file, st_frames); dc_stats(st_file, st_frames);
    pace_stats(st_file); io_stats(st_file); ts_stats(st_file);
    if (st_pace_skips) { fprintf(st_file, "pace: skipped game sleeps=%ld ", st_pace_skips); st_pace_skips = 0; }
    if (cs_lazy) { fprintf(st_file, "clientstate deferred=%ld sent=%ld ", st_cs_skipped, st_cs_sent); st_cs_skipped = st_cs_sent = 0; }
    if (lz_on) { fprintf(st_file, "enables deferred=%ld cancelled=%ld sent=%ld texparam skipped=%ld ", st_lz_deferred, st_lz_cancelled, st_lz_sent, st_tp_skipped); st_lz_deferred = st_lz_cancelled = st_lz_sent = st_tp_skipped = 0; }
    if (cull_on) { fprintf(st_file, "culled=%ld/%ld batches %ld verts ", st_cull_batches, st_cull_tested, st_cull_verts); st_cull_batches = st_cull_tested = st_cull_verts = 0; }
    if (cull_verify) { fprintf(st_file, "cullverify checked=%ld nonzero=%ld total %lld/%lld ", st_cv_checked, st_cv_bad, cv_tot_checked, cv_tot_bad); st_cv_checked = st_cv_bad = 0; }
    fprintf(st_file, "skipped=%ld orphans=%ld/%ld subKB=%ld vbo=%d ", st_skipped, st_orphans, st_subs, st_sub_bytes / 1024, vbo_emu); st_skipped = 0; st_orphans = st_subs = 0; st_sub_bytes = st_sub_calls = 0;
    fprintf(st_file, "fps=%.1f blocks=%ld verts=%ld v/block=%.1f draws=%ld v/draw=%.1f fallbacks=%ld\n",
            st_frames / secs, st_blocks, st_verts, st_blocks ? (double)st_verts / st_blocks : 0.0,
            st_draws, st_draws ? (double)st_verts / st_draws : 0.0, st_fallbacks);
    int top[6] = {-1, -1, -1, -1, -1, -1};
    for (int i = 0; i < 400; i++) {
        if (!st_breaks[i]) continue;
        for (int k = 0; k < 6; k++) if (top[k] < 0 || st_breaks[i] > st_breaks[top[k]]) { for (int j = 5; j > k; j--) top[j] = top[j - 1]; top[k] = i; break; }
    }
    fprintf(st_file, "  breaks:");
    for (int k = 0; k < 6 && top[k] >= 0; k++) fprintf(st_file, " %s=%ld", mugl_names[top[k]], st_breaks[top[k]]);
    fprintf(st_file, "\n  modes:");
    static const char *mn[10] = {"POINTS","LINES","LINE_LOOP","LINE_STRIP","TRIANGLES","TRIANGLE_STRIP","TRIANGLE_FAN","QUADS","QUAD_STRIP","POLYGON"};
    for (int k = 0; k < 10; k++) if (st_modes[k]) fprintf(st_file, " %s=%ld(v/b %.1f)", mn[k], st_modes[k], (double)st_modeverts[k] / st_modes[k]);
    fprintf(st_file, "\n");
    if (count_mode) {
        fprintf(st_file, "  calls:");
        for (int k = 0; k < 40; k++) {
            int bi = -1; long bv = 0; int ext = 0;
            for (int i = 0; i < 400; i++) if (st_calls[i] > bv) { bv = st_calls[i]; bi = i; ext = 0; }
            for (int i = 0; i < nexts; i++) if (st_ext[i] > bv) { bv = st_ext[i]; bi = i; ext = 1; }
            if (bi < 0) break;
            fprintf(st_file, " %s=%ld", ext ? exts[bi].name : mugl_names[bi], bv);
            if (ext) st_ext[bi] = -st_ext[bi]; else st_calls[bi] = -st_calls[bi];
        }
        fprintf(st_file, "\n");
        memset(st_calls, 0, sizeof st_calls); memset(st_ext, 0, sizeof st_ext);
    }
    memset(st_breaks, 0, sizeof st_breaks); memset(st_modes, 0, sizeof st_modes); memset(st_modeverts, 0, sizeof st_modeverts);
    fflush(st_file);
    st_blocks = st_verts = st_fallbacks = st_draws = st_frames = 0; st_last = now;
}

static void ensure_known(void)
{
    if (cur_known) return;
    GLfloat t4[4];
    R(glGetFloatv, PFNget)(GL_CURRENT_COLOR, cur_c);
    R(glGetFloatv, PFNget)(GL_CURRENT_TEXTURE_COORDS, t4);
    R(glGetFloatv, PFNget)(GL_CURRENT_NORMAL, cur_n);
    cur_t[0] = t4[0]; cur_t[1] = t4[1];
    memcpy(gl_t, cur_t, sizeof gl_t); memcpy(gl_c, cur_c, sizeof gl_c); memcpy(gl_n, cur_n, sizeof gl_n);
    gl_t_ok = gl_c_ok = gl_n_ok = 1;
    cur_known = 1;
}

static void push_vertex(GLfloat x, GLfloat y, GLfloat z)
{
    if (vcount == vcap) {
        vcap = vcap ? vcap * 2 : 8192;
        vb = realloc(vb, sizeof(Vtx) * vcap);
    }
    Vtx *p = &vb[vcount++];
    p->t[0] = cur_t[0]; p->t[1] = cur_t[1];
    memcpy(p->c, cur_c, sizeof cur_c); memcpy(p->n, cur_n, sizeof cur_n);
    p->v[0] = x; p->v[1] = y; p->v[2] = z;
}

static int varies(size_t off, size_t len)
{
    const char *first = (const char *)&vb[0] + off;
    for (int i = 1; i < vcount; i++)
        if (memcmp((const char *)&vb[i] + off, first, len)) return 1;
    return 0;
}

static void send_current(void) { set_gl_t(cur_t); set_gl_c(cur_c); set_gl_n(cur_n); }

/* Submit vb[0..vcount) as one draw. Afterwards GL current values equal cur_*. */
static void submit_batch(void)
{
    if (vcount == 0) return;
    if (lz_n) lz_apply();   /* not expected: deferred enables are sent at glBegin */
    if (batch_mode == GL_TRIANGLES && cull_batch(vb, vcount)) { vcount = 0; set_t = set_c = set_n = 0; return; }   /* no fragment: not drawn */
    LARGE_INTEGER sb_t0; if (time_mode) QueryPerformanceCounter(&sb_t0);
    int vt = set_t && varies(offsetof(Vtx, t), sizeof(vb[0].t));
    int vc = set_c && varies(offsetof(Vtx, c), sizeof(vb[0].c));
    int vn = set_n && varies(offsetof(Vtx, n), sizeof(vb[0].n));
    /* attributes constant over the batch: one current-value call, no array.
       Vertices always carry the tracked values, so sending vb[0] is exact. */
    if (!vt) set_gl_t(vb[0].t);
    if (!vc) set_gl_c(vb[0].c);
    if (!vn) set_gl_n(vb[0].n);

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
    st_fmtverts[stride == 12 ? 0 : stride == 10 ? 1 : stride == 8 ? 2 : stride == 6 ? 3 : stride == 5 ? 4 : 5] += vcount;
    GLfloat *src = pack; int strided = 0;
    if (zero_copy_full && fmt == GL_T2F_C4F_N3F_V3F) src = (GLfloat *)vb;   /* Vtx is exactly the T2F_C4F_N3F_V3F layout */
    else if (strided_arrays) strided = 1;   /* arrays read vb in place with stride sizeof(Vtx) */
    else {
        if (vcount * stride > packcap) { packcap = vcount * stride * 2; pack = realloc(pack, sizeof(GLfloat) * packcap); }
        GLfloat *o = pack; src = pack;
        for (int i = 0; i < vcount; i++) {
            Vtx *p = &vb[i];
            if (has_t) { *o++ = p->t[0]; *o++ = p->t[1]; }
            if (has_c) { memcpy(o, p->c, 16); o += 4; }
            if (has_n) { memcpy(o, p->n, 12); o += 3; }
            memcpy(o, p->v, 12); o += 3;
        }
    }
    if (time_mode) { LARGE_INTEGER t1_; QueryPerformanceCounter(&t1_); tm_ticks[7] += t1_.QuadPart - sb_t0.QuadPart; tm_calls[7]++; }
    if (!owned) {
        /* our arrays live in client memory: no array buffer may be bound while they are owned,
           and the client attribute stack is only used with binding 0 */
        GLint bound = (vbo_seen && real_bindbuf && !vbo_emu) ? (GLint)real_bind[0] : 0;
        if (bound) ((void (WINAPI *)(GLenum, GLuint))real_bindbuf)(0x8892 /* GL_ARRAY_BUFFER */, 0);
        saved_array_buffer = bound;
        TIMED(2, R(glPushClientAttrib, PFNpca)(GL_CLIENT_VERTEX_ARRAY_BIT)); owned = 1; owned_fmt = 0; owned_ptr = NULL;
    }
    if (strided) {
        /* glInterleavedArrays with stride 48 sets the enables and pointers; formats whose later attributes are not at the
           packed offsets get those pointers corrected. Same attribute values per vertex as the packed arrays. */
        GLfloat *base = fmt == GL_C4F_N3F_V3F ? vb[0].c : fmt == GL_N3F_V3F ? vb[0].n : fmt == GL_V3F ? vb[0].v : vb[0].t;
        if (fmt != owned_fmt || base != owned_ptr || !owned_strided) {
            TIMED(1, R(glInterleavedArrays, PFNia)(fmt, sizeof(Vtx), base));
            if (fmt == GL_T2F_V3F || fmt == GL_T2F_N3F_V3F) TIMED(1, R(glVertexPointer, PFNptr4)(3, GL_FLOAT, sizeof(Vtx), vb[0].v));
            if (fmt == GL_T2F_N3F_V3F) TIMED(1, R(glNormalPointer, PFNptr3)(GL_FLOAT, sizeof(Vtx), vb[0].n));
            owned_fmt = fmt; owned_ptr = base; owned_strided = 1;
        }
    } else if (fmt != owned_fmt || src != owned_ptr || owned_strided) {
        TIMED(1, R(glInterleavedArrays, PFNia)(fmt, 0, src));
        owned_fmt = fmt; owned_ptr = src; owned_strided = 0;
    }
    TR("DRAW %x %d fmt=%x\n", batch_mode, vcount, fmt);
    dq_switch(batch_cls);
    if (cull_mode && batch_mode == GL_TRIANGLES) cull_diag(vb, vcount, batch_cls);
    if (!nodraw) {
        if (time_mode) { LARGE_INTEGER t0_, t1_; QueryPerformanceCounter(&t0_); R(glDrawArrays, PFNda)(batch_mode, 0, vcount); QueryPerformanceCounter(&t1_);
                         tm_ticks[0] += t1_.QuadPart - t0_.QuadPart; tm_calls[0]++; dc_add(batch_cls, t1_.QuadPart - t0_.QuadPart, vcount); }
        else R(glDrawArrays, PFNda)(batch_mode, 0, vcount);
    }
    /* drawing with an array leaves that current value undefined */
    if (has_t) gl_t_ok = 0;
    if (has_c) gl_c_ok = 0;
    if (has_n) gl_n_ok = 0;
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
    if (n > 0) { tmp = malloc(sizeof(Vtx) * n); memcpy(tmp, &vb[block_start], sizeof(Vtx) * n); }
    GLfloat save_t[2], save_c[4], save_n[3];
    memcpy(save_t, cur_t, sizeof cur_t); memcpy(save_c, cur_c, sizeof cur_c); memcpy(save_n, cur_n, sizeof cur_n);
    vcount = block_start;
    if (vcount) {
        /* the closed blocks' final values were current when they ended */
        memcpy(cur_t, vb[vcount - 1].t, sizeof cur_t); memcpy(cur_c, vb[vcount - 1].c, sizeof cur_c); memcpy(cur_n, vb[vcount - 1].n, sizeof cur_n);
        submit_batch();
    }
    vcount = 0; set_t = set_c = set_n = 0;
    release_arrays(); /* immediate mode inside the block must see the game's arrays */
    R(glBegin, PFN1u)(cur_mode);
    for (int i = 0; i < n; i++) {
        Vtx *p = &tmp[i];
        set_gl_t(p->t); set_gl_c(p->c); set_gl_n(p->n);
        R(glVertex3fv, PFNfv)(p->v);
    }
    free(tmp);
    memcpy(cur_t, save_t, sizeof cur_t); memcpy(cur_c, save_c, sizeof cur_c); memcpy(cur_n, save_n, sizeof cur_n);
    send_current();
    mugl_in_begin = 0; pending = 0; passthrough = 1;
    update_busy();
}

/* ---- lazy client-array enables (hotpatch bit 262144, v7.4) ----
   The effect code draws each sprite from a vertex buffer as glEnableClientState x3, glDrawArrays, glDisableClientState
   x3 (about 2,800 calls per frame zoomed out). With the bit, enables of the vertex, normal, color, index, texture
   coordinate and edge-flag arrays are recorded and sent only when something can observe them: before any call that
   uses or reads array state (the generated stubs with the "release" flag: draws, glArrayElement, glInterleavedArrays,
   client attribute push/pop, glGet*, glIsEnabled, wgl*; array-related extensions, display lists, glBegin) and on full
   synchronization. A disable followed by an enable of the same array before the next such call cancels out, so the
   arrays GL sees at every draw are the ones the client asked for. State that mugl cannot know (after a client
   attribute pop, glInterleavedArrays or a client texture unit change) makes the next call pass through. */
static int cs_idx_en = -1, cs_idx_dis = -1;
typedef void (WINAPI *PFN1e)(GLenum);
static void release_arrays(void);
static void cs_forget(void) { memset(cs_real, 0, sizeof cs_real); memset(cs_want, 0, sizeof cs_want); cs_dirty = 0; }
static void cs_apply(void)
{
    if (!cs_dirty) return;
    release_arrays();   /* the client's own array state must be current */
    for (int k = 0; k < 6; k++) {
        if (!cs_real[k] || cs_want[k] == cs_real[k]) continue;
        if (cs_want[k] == 2) R(glEnableClientState, PFN1e)(0x8074 + k); else R(glDisableClientState, PFN1e)(0x8074 + k);
        cs_real[k] = cs_want[k]; st_cs_sent++;
    }
    cs_dirty = 0;
}

/* Called by pass-through stubs with the export index (registers preserved by the stub). */
void mugl_sync(void);
static void ts_end_hook(void); static int ts_begin_hook(GLenum mode, void *ret); static void ts_glend_hook(void); static int ts_on_flag, ts_in_face_flag, ts_verify;
static int qs_on_flag, qs_verify;   /* quad runs (quads.c) */
static void flush_pending(void)
{
    if (ts_active_flag) ts_end_hook();
    if (mugl_in_begin) { fallback_open_block(); return; }
    if (pending) { submit_batch(); pending = 0; }
}
void mugl_sync_from(int idx)
{
    if (count_mode && idx >= 0 && idx < 400) st_calls[idx]++;
    if (tr_on && idx >= 0 && idx < 400) TR("S %s%s\n", mugl_names[idx], passthrough ? " (in block)" : "");
    if (passthrough) { update_busy(); return; } /* inside a real glBegin/glEnd: nothing may be emitted */
    if ((pending || mugl_in_begin) && idx >= 0 && idx < 400) st_breaks[idx]++;
    flush_pending();
    if (cs_dirty && idx >= 0 && idx < (int)sizeof mugl_flags && (mugl_flags[idx] & 2)) cs_apply();
    if (idx >= 0 && idx < (int)sizeof mugl_flags) {
        const char *nm = mugl_names[idx];
        int mx = !strcmp(nm, "glTranslatef") || !strcmp(nm, "glTranslated") || !strcmp(nm, "glRotatef") || !strcmp(nm, "glRotated") ||
            !strcmp(nm, "glScalef") || !strcmp(nm, "glScaled") || !strncmp(nm, "glLoadMatrix", 12) || !strncmp(nm, "glMultMatrix", 12) ||
            !strcmp(nm, "glOrtho") || !strcmp(nm, "glFrustum");
        if (mx) matrix_modified();
        else if (lz_n) lz_apply();   /* every export except state calls (index -1) and matrix calls may observe enables */
        if (!strncmp(nm, "wglMakeCurrent", 14) || !strncmp(nm, "wglDeleteContext", 16)) { forget_state(); mstk_valid = 0; cs_forget(); }
        if (mugl_flags[idx] & 2) release_arrays();
        if (mugl_flags[idx] & 1) send_current();
        if (mugl_flags[idx] & 4) forget_gl_current(); /* array draws may leave current values at the last element */
    }
    update_busy();
}

/* Full synchronization: submit, restore client arrays and current values. */
void mugl_sync(void)
{
    if (passthrough) return;
    flush_pending();
    lz_apply();
    cs_apply();
    release_arrays();
    send_current();
    forget_gl_current(); /* unknown call (extension draw, list, ...) may change current values */
    update_busy();
}
static void cs_set(GLenum a, unsigned char v)
{
    int k = (int)a - 0x8074;
    if (k < 0 || k > 5) k = -1;
    if (cs_lazy && !passthrough && k >= 0 && cs_real[k]) { cs_want[k] = v; cs_dirty = memcmp(cs_want, cs_real, sizeof cs_real) != 0; st_cs_skipped++; update_busy(); return; }
    /* pass-through, exactly like the generated stub */
    if (cs_idx_en < 0) for (int i = 0; i < (int)(sizeof mugl_names / sizeof mugl_names[0]); i++) {
        if (!strcmp(mugl_names[i], "glEnableClientState")) cs_idx_en = i;
        if (!strcmp(mugl_names[i], "glDisableClientState")) cs_idx_dis = i;
    }
    if (mugl_busy) mugl_sync_from(v == 2 ? cs_idx_en : cs_idx_dis);
    if (v == 2) R(glEnableClientState, PFN1e)(a); else R(glDisableClientState, PFN1e)(a);
    if (k >= 0 && !passthrough) { cs_real[k] = cs_want[k] = v; cs_dirty = memcmp(cs_want, cs_real, sizeof cs_real) != 0; update_busy(); }
}
void WINAPI mugl_glEnableClientState(GLenum a) { cs_set(a, 2); }
void WINAPI mugl_glDisableClientState(GLenum a) { cs_set(a, 1); }

static GLenum shade_model = GL_SMOOTH;
/* Batch class of a primitive: triangle-like blocks are converted to GL_TRIANGLES
   (exact for fans/strips; quads/polygons only under smooth shading, where the
   flat-shading provoking vertex does not matter). 0 = not mergeable. */
static GLenum canon(GLenum m)
{
    switch (m) {
    case GL_POINTS: case GL_LINES: case GL_TRIANGLES: return m;
    case GL_TRIANGLE_FAN: case GL_TRIANGLE_STRIP: return GL_TRIANGLES;
    case GL_QUADS: case GL_QUAD_STRIP: case GL_POLYGON: return shade_model == GL_SMOOTH ? GL_TRIANGLES : 0;
    default: return 0;
    }
}
static Vtx *tri; static int tricap;
/* Rewrite vb[block_start..vcount) of primitive cur_mode as a triangle list. */
static void convert_open_block(void)
{
    int n = vcount - block_start;
    if (cur_mode == GL_TRIANGLES || cur_mode == GL_POINTS || cur_mode == GL_LINES) return;
    int ntri = 0;
    if (n > tricap) { tricap = n * 2; tri = realloc(tri, sizeof(Vtx) * tricap); }
    memcpy(tri, &vb[block_start], sizeof(Vtx) * n);
    vcount = block_start;
    #define EMIT(a, b, c) do { if (vcount + 3 > vcap) { vcap = (vcount + 3) * 2; vb = realloc(vb, sizeof(Vtx) * vcap); } \
        vb[vcount++] = tri[a]; vb[vcount++] = tri[b]; vb[vcount++] = tri[c]; ntri++; } while (0)
    switch (cur_mode) {
    case GL_TRIANGLE_FAN: case GL_POLYGON:
        for (int i = 1; i + 1 < n; i++) EMIT(0, i, i + 1);
        break;
    case GL_TRIANGLE_STRIP:
        for (int i = 0; i + 2 < n; i++) { if (i & 1) EMIT(i + 1, i, i + 2); else EMIT(i, i + 1, i + 2); }
        break;
    case GL_QUADS:
        for (int i = 0; i + 3 < n; i += 4) { EMIT(i, i + 1, i + 2); EMIT(i, i + 2, i + 3); }
        break;
    case GL_QUAD_STRIP:
        for (int i = 0; i + 3 < n; i += 2) { EMIT(i, i + 1, i + 3); EMIT(i, i + 3, i + 2); }
        break;
    }
    #undef EMIT
    (void)ntri;
}


/* ---- intercepted entry points ---- */
void WINAPI mugl_glBegin(GLenum mode)
{
    TR("G %x %p\n", mode, __builtin_return_address(0));
    if (cs_dirty && !passthrough) { cs_apply(); update_busy(); }   /* glArrayElement may be used inside the block */
    if (lz_n && !passthrough) lz_apply();   /* vertices from here on are drawn with the deferred enables */
    if ((ts_on_flag || qs_on_flag || ts_active_flag) && batching_enabled && merge_enabled && !mugl_in_begin && !passthrough && ts_begin_hook(mode, __builtin_return_address(0))) return;
    if (!batching_enabled || mugl_in_begin || passthrough) {
        flush_pending(); release_arrays(); send_current(); update_busy(); R(glBegin, PFN1u)(mode);
        passthrough = 1; /* real block in progress: nothing else may be emitted until glEnd */
        return;
    }
    GLenum cls = merge_enabled ? canon(mode) : 0;
    if (pending && !(cls && cls == batch_mode)) { submit_batch(); pending = 0; }
    ensure_known();
    if (!pending) { vcount = 0; set_t = set_c = set_n = 0; batch_mode = cls ? cls : mode; batch_cls = dc_of(__builtin_return_address(0)); }
    cur_mode = mode; block_start = vcount; mugl_in_begin = 1; pending = 0;
    update_busy();
}

void WINAPI mugl_glEnd(void)
{
    TR("/ %d\n", mugl_in_begin ? vcount - block_start : -1);
    if (ts_in_face_flag) { ts_glend_hook(); return; }
    if (passthrough) { passthrough = 0; R(glEnd, PFN0)(); forget_gl_current(); update_busy(); return; }
    if (!mugl_in_begin) { mugl_sync(); R(glEnd, PFN0)(); return; }
    mugl_in_begin = 0; st_blocks++; st_verts += vcount - block_start;
    if (cur_mode < 10) { st_modes[cur_mode]++; st_modeverts[cur_mode] += vcount - block_start; }
    if (merge_enabled && canon(cur_mode)) { convert_open_block(); pending = 1; }
    else submit_batch();
    update_busy();
}

#define VTX(x, y, z) do { if (mugl_in_begin) push_vertex((x), (y), (z)); else { if (mugl_busy && !passthrough) mugl_sync(); R(glVertex3f, PFNf3)((x), (y), (z)); } } while (0)
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
    if (mugl_in_begin) *setf = 1;
    else if (pending) { *dirtyf = 1; *setf = 1; update_busy(); } /* value may differ between merged blocks */
    else { fwd(); update_busy(); }
}
static void fwd_t(void) { set_gl_t(cur_t); }
static void fwd_c(void) { set_gl_c(cur_c); }
static void fwd_n(void) { set_gl_n(cur_n); }
void WINAPI mugl_glTexCoord2f(GLfloat s, GLfloat t) { cur_t[0] = s; cur_t[1] = t; attr_done(&set_t, &dirty_t, fwd_t); }
void WINAPI mugl_glTexCoord2fv(const GLfloat *v) { mugl_glTexCoord2f(v[0], v[1]); }
void WINAPI mugl_glTexCoord2d(GLdouble s, GLdouble t) { mugl_glTexCoord2f((GLfloat)s, (GLfloat)t); }
void WINAPI mugl_glTexCoord2i(GLint s, GLint t) { mugl_glTexCoord2f((GLfloat)s, (GLfloat)t); }
void WINAPI mugl_glColor4f(GLfloat r, GLfloat g, GLfloat b, GLfloat a) { cur_c[0] = r; cur_c[1] = g; cur_c[2] = b; cur_c[3] = a; attr_done(&set_c, &dirty_c, fwd_c); }
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
void WINAPI mugl_glNormal3f(GLfloat x, GLfloat y, GLfloat z) { cur_n[0] = x; cur_n[1] = y; cur_n[2] = z; attr_done(&set_n, &dirty_n, fwd_n); }
void WINAPI mugl_glNormal3fv(const GLfloat *v) { mugl_glNormal3f(v[0], v[1], v[2]); }

void WINAPI mugl_glShadeModel(GLenum m) { mugl_sync(); shade_model = m; R(glShadeModel, PFN1u)(m); }

/* ---- redundant state filtering ----
   Skipped calls neither reach GL nor end the pending batch. Caches are dropped
   whenever state may change behind our back (attribute stack, display lists,
   texture deletion, context changes, unknown extensions affecting units). */
static unsigned char cap_cache[8][0x10000];   /* per texture unit: 0 unknown, 1 off, 2 on */
static GLuint tex_cache[8]; static unsigned char tex_ok[8];
static GLenum blend_s, blend_d; static int blend_ok;
static GLboolean depth_mask; static int depth_mask_ok;
static GLenum matrix_mode; static int matrix_mode_ok;
static GLenum alpha_func; static GLclampf alpha_ref; static int alpha_ok;
static GLenum depth_func; static int depth_func_ok;
static int active_unit;                       /* tracked via glActiveTexture(ARB) wrapper */
static int filter_enabled = 1;
/* v7.5: forget_state() ran a 512 KB memset of cap_cache on every glPopAttrib (about 3% of the boss-fight samples).
   Entries become non-zero only in mugl_glEnable/Disable (recorded here when they leave 0) and in terrain.c's three
   unit-0 caps (cleared explicitly), so clearing the recorded entries leaves the same all-zero cache. */
static unsigned cap_touched[2048]; static int cap_ntouched, cap_overflow;
static void cap_touch(unsigned char *s)
{
    if (*s) return;
    if (cap_ntouched < 2048) cap_touched[cap_ntouched++] = (unsigned)(s - &cap_cache[0][0]); else cap_overflow = 1;
}
static void forget_state(void)
{
    if (cap_overflow) memset(cap_cache, 0, sizeof cap_cache);
    else { for (int i = 0; i < cap_ntouched; i++) (&cap_cache[0][0])[cap_touched[i]] = 0;
           cap_cache[0][GL_BLEND] = cap_cache[0][GL_CULL_FACE] = cap_cache[0][GL_ALPHA_TEST] = 0; }
    cap_ntouched = 0; cap_overflow = 0;
    memset(tex_ok, 0, sizeof tex_ok);
    blend_ok = depth_mask_ok = matrix_mode_ok = alpha_ok = depth_func_ok = 0;
}
static int unit_cap(GLenum cap)
{   /* caps that are per texture unit */
    return cap == GL_TEXTURE_1D || cap == GL_TEXTURE_2D || cap == 0x8513 /* CUBE_MAP */ || cap == 0x806F /* 3D */ ||
           (cap >= GL_TEXTURE_GEN_S && cap <= GL_TEXTURE_GEN_Q) || cap == 0x84F5 /* RECTANGLE */;
}
static unsigned char *cap_slot(GLenum cap)
{
    if (cap >= 0x10000) return NULL;
    int u = unit_cap(cap) ? active_unit : 0;
    if (u < 0 || u >= 8) return NULL;
    return &cap_cache[u][cap];
}
static int ts_cap(GLenum cap, int on); static int ts_tex(GLenum target, GLuint tex); static int ts_blendfunc(GLenum s, GLenum d);
static int ts_depthmask(GLboolean m); static int ts_alphafunc(GLenum f, GLclampf r);
/* ---- deferred enables and redundant texture parameters (bit 1073741824, v7.6) ----
   Zoomed out in the boss fight about 3,200 glEnable/glDisable calls per frame reached GL, and in a two-frame trace 61%
   of them were undone before anything could observe them (mostly GL_CULL_FACE and GL_FRAGMENT_PROGRAM_ARB toggled by
   the effect and interface code); every call is a 32-to-64-bit thunk under CrossOver. With the bit, an enable or
   disable of a cap that is not per texture unit and whose real state is known is recorded instead of sent: the batch
   recorded so far is submitted first (it was specified under the old state), a change back cancels the record, and
   the records are sent before anything that can observe them: glBegin (any later geometry), every exported call except
   the state calls mugl filters (enable/disable, texture binding, blend function, depth mask, alpha and depth
   function) and the matrix calls, glGet*, glPopAttrib, display lists and full synchronization. While a display list is
   compiled nothing is deferred. glTexParameteri of GL_TEXTURE_2D's filters and wraps on a known non-zero binding is
   dropped when it repeats the value last set on that texture object; any other parameter call on it, glPopAttrib,
   texture deletion and display lists forget the recorded values. */
static GLenum lz_cap[64]; static unsigned char lz_want[64];
static void lz_apply(void)
{
    if (!lz_n) return;
    int n = lz_n; lz_n = 0;
    for (int i = 0; i < n; i++) {
        if (lz_want[i] == 2) TIMED(4, R(glEnable, PFN1u)(lz_cap[i])); else TIMED(4, R(glDisable, PFN1u)(lz_cap[i]));
        unsigned char *s = &cap_cache[0][lz_cap[i]]; cap_touch(s); *s = lz_want[i]; st_lz_sent++;
    }
    update_busy();
}
/* 1 = handled (recorded, cancelled or redundant) */
static int lz_set(GLenum cap, unsigned char *s, unsigned char want)
{
    if (!lz_on || passthrough || lz_list || !s || !*s || unit_cap(cap) || !filter_enabled) return 0;
    int i = 0; while (i < lz_n && lz_cap[i] != cap) i++;
    unsigned char eff = i < lz_n ? lz_want[i] : *s;
    if (eff == want) { st_skipped++; return 1; }
    if (i == lz_n && lz_n == 64) return 0;
    flush_pending();   /* the vertices so far were specified under the old state */
    if (i < lz_n) { lz_cap[i] = lz_cap[lz_n - 1]; lz_want[i] = lz_want[lz_n - 1]; lz_n--; st_lz_cancelled++; }   /* back to the real state */
    else { lz_cap[lz_n] = cap; lz_want[lz_n] = want; lz_n++; st_lz_deferred++; }
    update_busy();
    return 1;
}
void WINAPI mugl_glEnable(GLenum cap)
{
    if (ts_active_flag && ts_cap(cap, 1)) return;
    unsigned char *s = cap_slot(cap);
    if (lz_set(cap, s, 2)) { TR("E %x ~ %p\n", cap, __builtin_return_address(0)); return; }
    TR("E %x%s %p\n", cap, filter_enabled && s && *s == 2 && !passthrough ? " =" : "", __builtin_return_address(0));
    if (filter_enabled && s && *s == 2 && !passthrough) { st_skipped++; return; }
    mugl_sync_from(-1); TIMED(4, R(glEnable, PFN1u)(cap)); if (s) { cap_touch(s); *s = 2; }
}
void WINAPI mugl_glDisable(GLenum cap)
{
    if (ts_active_flag && ts_cap(cap, 0)) return;
    unsigned char *s = cap_slot(cap);
    if (lz_set(cap, s, 1)) { TR("D %x ~ %p\n", cap, __builtin_return_address(0)); return; }
    TR("D %x%s %p\n", cap, filter_enabled && s && *s == 1 && !passthrough ? " =" : "", __builtin_return_address(0));
    if (filter_enabled && s && *s == 1 && !passthrough) { st_skipped++; return; }
    mugl_sync_from(-1); TIMED(4, R(glDisable, PFN1u)(cap)); if (s) { cap_touch(s); *s = 1; }
}
typedef void (WINAPI *PFNbt)(GLenum, GLuint);
void WINAPI mugl_glBindTexture(GLenum target, GLuint tex)
{
    if (ts_active_flag && ts_tex(target, tex)) return;
    int u = active_unit;
    TR("T %u%s %p\n", tex, filter_enabled && target == GL_TEXTURE_2D && u >= 0 && u < 8 && tex_ok[u] && tex_cache[u] == tex && !passthrough ? " =" : "", __builtin_return_address(0));
    if (filter_enabled && target == GL_TEXTURE_2D && u >= 0 && u < 8 && tex_ok[u] && tex_cache[u] == tex && !passthrough) { st_skipped++; return; }
    mugl_sync_from(-1); TIMED(5, R(glBindTexture, PFNbt)(target, tex));
    if (target == GL_TEXTURE_2D && u >= 0 && u < 8) { tex_cache[u] = tex; tex_ok[u] = 1; }
}
typedef void (WINAPI *PFNdt)(GLsizei, const GLuint *);
static unsigned tp_gen = 1, tp_g[65536]; static GLint tp_val[65536][4];
void WINAPI mugl_glDeleteTextures(GLsizei n, const GLuint *t)
{
    mugl_sync_from(-1); R(glDeleteTextures, PFNdt)(n, t); memset(tex_ok, 0, sizeof tex_ok); tp_gen++;
}
static int tp_idx = -1, tp_idxf = -1, tp_idxiv = -1, tp_idxfv = -1;
static int tp_export(int *cache, const char *n) { if (*cache < 0) for (int i = 0; i < (int)(sizeof mugl_names / sizeof mugl_names[0]); i++) if (!strcmp(mugl_names[i], n)) { *cache = i; break; } return *cache; }
static GLuint tp_bound(GLenum target)
{
    int u = active_unit;
    return target == GL_TEXTURE_2D && u >= 0 && u < 8 && tex_ok[u] && tex_cache[u] < 65536 ? tex_cache[u] : 0;
}
typedef void (WINAPI *PFNtpi)(GLenum, GLenum, GLint); typedef void (WINAPI *PFNtpf)(GLenum, GLenum, GLfloat); typedef void (WINAPI *PFNtpv)(GLenum, GLenum, const void *);
void WINAPI mugl_glTexParameteri(GLenum target, GLenum pname, GLint v)
{
    GLuint t = tp_bound(target);
    int k = pname == GL_TEXTURE_MIN_FILTER ? 0 : pname == GL_TEXTURE_MAG_FILTER ? 1 : pname == GL_TEXTURE_WRAP_S ? 2 : pname == GL_TEXTURE_WRAP_T ? 3 : -1;
    int ok = lz_on && !passthrough && !lz_list && filter_enabled && t && k >= 0;
    if (ok && tp_g[t] == tp_gen && tp_val[t][k] == v) { st_tp_skipped++; return; }
    if (mugl_busy) mugl_sync_from(tp_export(&tp_idx, "glTexParameteri"));
    R(glTexParameteri, PFNtpi)(target, pname, v);
    if (!t || passthrough || lz_list) return;
    if (!ok) { tp_g[t] = 0; return; }
    if (tp_g[t] != tp_gen) { tp_g[t] = tp_gen; tp_val[t][0] = tp_val[t][1] = tp_val[t][2] = tp_val[t][3] = (GLint)0x80000000; }
    tp_val[t][k] = v;
}
void WINAPI mugl_glTexParameterf(GLenum target, GLenum pname, GLfloat v)
{
    if (mugl_busy) mugl_sync_from(tp_export(&tp_idxf, "glTexParameterf"));
    R(glTexParameterf, PFNtpf)(target, pname, v); GLuint t = tp_bound(target); if (t) tp_g[t] = 0;
}
void WINAPI mugl_glTexParameteriv(GLenum target, GLenum pname, const GLint *v)
{
    if (mugl_busy) mugl_sync_from(tp_export(&tp_idxiv, "glTexParameteriv"));
    R(glTexParameteriv, PFNtpv)(target, pname, v); GLuint t = tp_bound(target); if (t) tp_g[t] = 0;
}
void WINAPI mugl_glTexParameterfv(GLenum target, GLenum pname, const GLfloat *v)
{
    if (mugl_busy) mugl_sync_from(tp_export(&tp_idxfv, "glTexParameterfv"));
    R(glTexParameterfv, PFNtpv)(target, pname, v); GLuint t = tp_bound(target); if (t) tp_g[t] = 0;
}
typedef void (WINAPI *PFNnl)(GLuint, GLenum);
void WINAPI mugl_glNewList(GLuint l, GLenum m) { mugl_sync(); R(glNewList, PFNnl)(l, m); lz_list = 1; tp_gen++; update_busy(); }
void WINAPI mugl_glEndList(void) { mugl_sync(); R(glEndList, PFN0)(); lz_list = 0; tp_gen++; forget_state(); update_busy(); }
typedef void (WINAPI *PFN2u)(GLenum, GLenum);
void WINAPI mugl_glBlendFunc(GLenum sf, GLenum df)
{
    if (ts_active_flag && ts_blendfunc(sf, df)) return;
    TR("B %x %x%s\n", sf, df, filter_enabled && blend_ok && blend_s == sf && blend_d == df && !passthrough ? " =" : "");
    if (filter_enabled && blend_ok && blend_s == sf && blend_d == df && !passthrough) { st_skipped++; return; }
    mugl_sync_from(-1); R(glBlendFunc, PFN2u)(sf, df); blend_s = sf; blend_d = df; blend_ok = 1;
}
typedef void (WINAPI *PFNdm)(GLboolean);
void WINAPI mugl_glDepthMask(GLboolean f)
{
    if (ts_active_flag && ts_depthmask(f)) return;
    TR("M %d%s\n", f, filter_enabled && depth_mask_ok && depth_mask == f && !passthrough ? " =" : "");
    if (filter_enabled && depth_mask_ok && depth_mask == f && !passthrough) { st_skipped++; return; }
    mugl_sync_from(-1); R(glDepthMask, PFNdm)(f); depth_mask = f; depth_mask_ok = 1;
}
void WINAPI mugl_glMatrixMode(GLenum m)
{
    mmode = m; mmode_known = 1;
    if (filter_enabled && matrix_mode_ok && matrix_mode == m && !passthrough) { st_skipped++; return; }
    /* matrix mode does not affect pending vertices: no flush */
    R(glMatrixMode, PFN1u)(m); matrix_mode = m; matrix_mode_ok = 1;
}
typedef void (WINAPI *PFNaf)(GLenum, GLclampf);
void WINAPI mugl_glAlphaFunc(GLenum f, GLclampf ref)
{
    if (ts_active_flag && ts_alphafunc(f, ref)) return;
    TR("A %x %g%s\n", f, (double)ref, filter_enabled && alpha_ok && alpha_func == f && alpha_ref == ref && !passthrough ? " =" : "");
    if (filter_enabled && alpha_ok && alpha_func == f && alpha_ref == ref && !passthrough) { st_skipped++; return; }
    mugl_sync_from(-1); R(glAlphaFunc, PFNaf)(f, ref); alpha_func = f; alpha_ref = ref; alpha_ok = 1;
}
void WINAPI mugl_glDepthFunc(GLenum f)
{
    TR("Z %x%s\n", f, filter_enabled && depth_func_ok && depth_func == f && !passthrough ? " =" : "");
    if (filter_enabled && depth_func_ok && depth_func == f && !passthrough) { st_skipped++; return; }
    mugl_sync_from(-1); R(glDepthFunc, PFN1u)(f); depth_func = f; depth_func_ok = 1;
}
static void *real_activetex;

/* ---- matrix stack elision ----
   glPushMatrix never changes the current matrix, and a glPopMatrix after no matrix
   modification since the matching push restores an identical matrix: neither needs to
   end the pending batch. Matrix-modifying calls (stubs) flush as before and mark the
   current level modified. Tracking is per matrix mode; unknown states fall back to flushing. */
static int cur_mmode_idx(void);
static unsigned char mstk[4][64]; static int msp[4];   /* modified flags per push level */
static int cur_mmode_idx(void)
{
    switch (mmode) { case GL_MODELVIEW: return 0; case GL_PROJECTION: return 1; case GL_TEXTURE: return 2; default: return 3; }
}
static void matrix_modified(void) { int m = cur_mmode_idx(); if (msp[m] > 0 && msp[m] <= 64) mstk[m][msp[m] - 1] = 1; }
void WINAPI mugl_glPushMatrix(void)
{
    TR("push\n");
    if (passthrough) { R(glPushMatrix, PFN0)(); return; }
    /* no flush: pending vertices are unaffected by a push */
    R(glPushMatrix, PFN0)();
    int m = cur_mmode_idx(); if (msp[m] < 64) mstk[m][msp[m]] = 0; msp[m]++;
}
void WINAPI mugl_glPopMatrix(void)
{
    TR("pop\n");
    if (passthrough) { R(glPopMatrix, PFN0)(); return; }
    int m = cur_mmode_idx();
    int unchanged = mstk_valid && mmode_known && msp[m] > 0 && msp[m] <= 64 && !mstk[m][msp[m] - 1];
    if (!unchanged) mugl_sync_from(-1);
    R(glPopMatrix, PFN0)();
    if (!unchanged) mx_epoch++;   /* after the call: the flush above may re-read the matrices */
    if (msp[m] > 0) msp[m]--;
    if (!unchanged) matrix_modified();          /* the restored matrix differs for the enclosing level */
    else st_skipped++;
}
void WINAPI mugl_glLoadIdentity(void)
{
    TR("loadidentity\n");
    mugl_sync_from(-1); R(glLoadIdentity, PFN0)(); matrix_modified(); mx_epoch++;
}

/* ---- queries: only current-value and client-array queries need synchronization ---- */
static int pname_current(GLenum p) { return p == GL_CURRENT_COLOR || p == GL_CURRENT_TEXTURE_COORDS || p == GL_CURRENT_NORMAL ||
                                            p == GL_CURRENT_INDEX || p == GL_CURRENT_RASTER_COLOR || p == GL_CURRENT_RASTER_TEXTURE_COORDS; }
static int pname_client(GLenum p) { return (p >= 0x8074 && p <= 0x8092) /* array enables/sizes/pointers */ || p == 0x84E1 /* CLIENT_ACTIVE_TEXTURE */ ||
                                           (p >= 0x8894 && p <= 0x889F) /* buffer bindings */ || p == GL_CLIENT_ATTRIB_STACK_DEPTH; }
static int emu_query(GLenum p, GLint *out)
{
    if (!vbo_emu) return 0;
    if (p == 0x8894) { *out = (GLint)emu_bind[0]; return 1; }
    if (p == 0x8895) { *out = (GLint)emu_bind[1]; return 1; }
    return 0;
}
static void query_prep(GLenum p)
{
    if (passthrough) return;
    if (lz_n) lz_apply();   /* glGet* can read enables */
    if (pname_current(p)) { flush_pending(); send_current(); }
    if (pname_client(p)) { flush_pending(); cs_apply(); release_arrays(); }
    update_busy();
}
typedef void (WINAPI *PFNgv)(GLenum, void *);
void WINAPI mugl_glGetFloatv(GLenum p, GLfloat *v) { GLint e; if (emu_query(p, &e)) { *v = (GLfloat)e; return; } query_prep(p); R(glGetFloatv, PFNgv)(p, v); }
void WINAPI mugl_glGetDoublev(GLenum p, GLdouble *v) { query_prep(p); R(glGetDoublev, PFNgv)(p, v); }
void WINAPI mugl_glGetIntegerv(GLenum p, GLint *v) { GLint e; if (emu_query(p, &e)) { *v = e; return; } query_prep(p); R(glGetIntegerv, PFNgv)(p, v); }
void WINAPI mugl_glGetBooleanv(GLenum p, GLboolean *v) { query_prep(p); R(glGetBooleanv, PFNgv)(p, v); }

/* ---- VBO emulation ----
   When enabled ("vbo" token in the mode file), array/element buffer contents live in
   client memory shadows: uploads are memcpy, pointers/indices given as buffer offsets
   are rewritten to client addresses, and the real GL bindings stay 0. Apple's GL then
   never synchronizes with the GPU on buffer updates. Shadow blocks never move (growth
   allocates a new block and keeps the old one), so previously specified pointers stay valid. */
typedef struct { GLuint id; unsigned char *data; size_t size, cap; GLenum usage; int real_stale; } Shadow;
static Shadow shadows[8192]; static int nshadows;
static GLuint bind_stack[16][2]; static int bind_sp;
static Shadow *shadow_of(GLuint id, int create)
{
    if (!id) return NULL;
    for (int i = 0; i < nshadows; i++) if (shadows[i].id == id) return &shadows[i];
    if (!create || nshadows >= 8192) return NULL;
    Shadow *s = &shadows[nshadows++]; memset(s, 0, sizeof *s); s->id = id; return s;
}
static void shadow_reserve(Shadow *s, size_t size)
{
    if (size <= s->cap) return;
    size_t cap = size < 65536 ? 65536 : size + size / 2;
    unsigned char *n = (unsigned char *)malloc(cap);           /* old block intentionally kept */
    if (!n) return;
    if (s->data && s->size) memcpy(n, s->data, s->size);
    s->data = n; s->cap = cap;
}
static const void *emu_ptr(int k, const void *p)
{   /* rewrite a buffer offset to a client address when emulating and a buffer is bound */
    if (!vbo_emu || !emu_bind[k]) return p;
    Shadow *s = shadow_of(emu_bind[k], 1);
    if (!s) return p;
    shadow_reserve(s, 1);
    return s->data + (size_t)p;
}
static void real_bind_to(int k, GLuint id)
{
    if (!real_bindbuf || real_bind[k] == id) return;
    ((void (WINAPI *)(GLenum, GLuint))real_bindbuf)(k ? 0x8893 : 0x8892, id); real_bind[k] = id;
}
static void *real_bufdata_p;
static void vbo_emu_set(int on)
{
    if (on == vbo_emu) return;
    flush_pending(); release_arrays();
    if (on) { real_bind_to(0, 0); real_bind_to(1, 0); }
    else {
        /* re-upload shadows that changed while emulated, then restore the game's bindings */
        for (int i = 0; i < nshadows; i++) {
            Shadow *s = &shadows[i];
            if (!s->real_stale || !s->usage || !real_bufdata_p) continue;
            real_bind_to(0, s->id);
            ((void (WINAPI *)(GLenum, GLsizeiptr, const void *, GLenum))real_bufdata_p)(0x8892, (GLsizeiptr)s->size, s->data, s->usage);
            s->real_stale = 0;
        }
        real_bind_to(0, emu_bind[0]); real_bind_to(1, emu_bind[1]);
    }
    vbo_emu = on; update_busy();
}
static void pre_array_call(void) { if (!passthrough) { flush_pending(); release_arrays(); update_busy(); } }
typedef void (WINAPI *PFNptr4)(GLint, GLenum, GLsizei, const void *);
typedef void (WINAPI *PFNptr3)(GLenum, GLsizei, const void *);
void WINAPI mugl_glVertexPointer(GLint sz, GLenum t, GLsizei st, const void *p) { pre_array_call(); R(glVertexPointer, PFNptr4)(sz, t, st, emu_ptr(0, p)); }
void WINAPI mugl_glColorPointer(GLint sz, GLenum t, GLsizei st, const void *p) { pre_array_call(); R(glColorPointer, PFNptr4)(sz, t, st, emu_ptr(0, p)); }
void WINAPI mugl_glTexCoordPointer(GLint sz, GLenum t, GLsizei st, const void *p) { pre_array_call(); R(glTexCoordPointer, PFNptr4)(sz, t, st, emu_ptr(0, p)); }
void WINAPI mugl_glNormalPointer(GLenum t, GLsizei st, const void *p) { pre_array_call(); R(glNormalPointer, PFNptr3)(t, st, emu_ptr(0, p)); }
void WINAPI mugl_glIndexPointer(GLenum t, GLsizei st, const void *p) { pre_array_call(); R(glIndexPointer, PFNptr3)(t, st, emu_ptr(0, p)); }
void WINAPI mugl_glEdgeFlagPointer(GLsizei st, const void *p) { pre_array_call(); ((void (WINAPI *)(GLsizei, const void *))real_glEdgeFlagPointer)(st, emu_ptr(0, p)); }
void WINAPI mugl_glInterleavedArrays(GLenum f, GLsizei st, const void *p)
{
    if (!passthrough) cs_apply();
    pre_array_call(); R(glInterleavedArrays, PFNptr3)(f, st, emu_ptr(0, p));
    if (!passthrough) cs_forget();   /* the format sets the enables */
}
typedef void (WINAPI *PFNde)(GLenum, GLsizei, GLenum, const void *);
void WINAPI mugl_glDrawElements(GLenum m, GLsizei n, GLenum t, const void *idx)
{
    if (!passthrough) { flush_pending(); lz_apply(); cs_apply(); release_arrays(); send_current(); dq_switch(DC_ARRAYS); }
    R(glDrawElements, PFNde)(m, n, t, emu_ptr(1, idx));
    forget_gl_current(); update_busy();
}
void WINAPI mugl_glPushClientAttrib(GLbitfield mask)
{
    if (!passthrough) cs_apply();
    pre_array_call(); R(glPushClientAttrib, PFNpca)(mask);
    if (bind_sp < 16) { bind_stack[bind_sp][0] = emu_bind[0]; bind_stack[bind_sp][1] = emu_bind[1]; } bind_sp++;
}
void WINAPI mugl_glPopClientAttrib(void)
{
    if (!passthrough) { cs_apply(); cs_forget(); }
    pre_array_call(); R(glPopClientAttrib, PFN0)();
    if (bind_sp > 0 && --bind_sp < 16) {
        emu_bind[0] = bind_stack[bind_sp][0]; emu_bind[1] = bind_stack[bind_sp][1];
        bound_buf[0] = emu_bind[0]; bound_buf[1] = emu_bind[1];
        if (vbo_emu) { real_bind[0] = real_bind[1] = (GLuint)-1; real_bind_to(0, 0); real_bind_to(1, 0); } /* pop may have restored real ids */
        else { real_bind[0] = emu_bind[0]; real_bind[1] = emu_bind[1]; }
    }
}

/* ---- buffer objects: orphan whole-buffer updates to avoid GPU sync stalls ---- */
typedef struct { GLuint id; GLsizeiptr size; GLenum usage; } BufInfo;
static BufInfo bufs[4096]; static int nbufs;
static void *real_bufdata, *real_bufsub;
static BufInfo *buf_info(GLuint id, int create)
{
    for (int i = 0; i < nbufs; i++) if (bufs[i].id == id) return &bufs[i];
    if (!create || nbufs >= 4096) return NULL;
    bufs[nbufs].id = id; bufs[nbufs].size = -1; bufs[nbufs].usage = 0; return &bufs[nbufs++];
}
static int tgt_index(GLenum t) { return t == 0x8892 ? 0 : t == 0x8893 ? 1 : -1; }
typedef void (WINAPI *PFNbb)(GLenum, GLuint);
typedef void (WINAPI *PFNbd)(GLenum, GLsizeiptr, const void *, GLenum);
typedef void (WINAPI *PFNbs)(GLenum, GLintptr, GLsizeiptr, const void *);
static void *real_mapbuf, *real_unmapbuf, *real_getbufsub, *real_getbufparam, *real_drawrange, *real_vattrib, *real_delbuf;
static void *WINAPI mugl_MapBuffer(GLenum t, GLenum access)
{
    int k = tgt_index(t);
    if (vbo_emu && k >= 0 && emu_bind[k]) { Shadow *s = shadow_of(emu_bind[k], 1); if (s) { shadow_reserve(s, 1); s->real_stale = 1; return s->data; } }
    return ((void *(WINAPI *)(GLenum, GLenum))real_mapbuf)(t, access);
}
static GLboolean WINAPI mugl_UnmapBuffer(GLenum t)
{
    int k = tgt_index(t);
    if (vbo_emu && k >= 0 && emu_bind[k]) return GL_TRUE;
    return ((GLboolean (WINAPI *)(GLenum))real_unmapbuf)(t);
}
static void WINAPI mugl_GetBufferSubData(GLenum t, GLintptr off, GLsizeiptr size, void *out)
{
    int k = tgt_index(t);
    if (vbo_emu && k >= 0 && emu_bind[k]) { Shadow *s = shadow_of(emu_bind[k], 0); if (s && off >= 0 && (size_t)off + (size_t)size <= s->size) memcpy(out, s->data + off, (size_t)size); return; }
    ((void (WINAPI *)(GLenum, GLintptr, GLsizeiptr, void *))real_getbufsub)(t, off, size, out);
}
static void WINAPI mugl_GetBufferParameteriv(GLenum t, GLenum pname, GLint *v)
{
    int k = tgt_index(t);
    if (vbo_emu && k >= 0 && emu_bind[k]) {
        Shadow *s = shadow_of(emu_bind[k], 0);
        if (pname == 0x8764 /* SIZE */) { *v = s ? (GLint)s->size : 0; return; }
        if (pname == 0x8765 /* USAGE */) { *v = s ? (GLint)s->usage : 0x88E4; return; }
        if (pname == 0x88BC /* MAPPED */) { *v = 0; return; }
        if (pname == 0x88BB /* ACCESS */) { *v = 0x88BA; return; }
    }
    ((void (WINAPI *)(GLenum, GLenum, GLint *))real_getbufparam)(t, pname, v);
}
static void WINAPI mugl_DrawRangeElements(GLenum m, GLuint lo, GLuint hi, GLsizei n, GLenum t, const void *idx)
{
    if (!passthrough) { flush_pending(); cs_apply(); release_arrays(); send_current(); }
    ((void (WINAPI *)(GLenum, GLuint, GLuint, GLsizei, GLenum, const void *))real_drawrange)(m, lo, hi, n, t, emu_ptr(1, idx));
    forget_gl_current(); update_busy();
}
static void WINAPI mugl_VertexAttribPointer(GLuint i, GLint sz, GLenum t, GLboolean norm, GLsizei st, const void *p)
{
    pre_array_call();
    ((void (WINAPI *)(GLuint, GLint, GLenum, GLboolean, GLsizei, const void *))real_vattrib)(i, sz, t, norm, st, emu_ptr(0, p));
}
static void WINAPI mugl_DeleteBuffers(GLsizei n, const GLuint *ids)
{
    for (int i = 0; i < n; i++) {
        Shadow *s = shadow_of(ids[i], 0); if (s) { s->size = 0; s->usage = 0; s->real_stale = 0; }
        for (int k = 0; k < 2; k++) if (emu_bind[k] == ids[i]) { emu_bind[k] = 0; bound_buf[k] = 0; }
        for (int k = 0; k < 2; k++) if (real_bind[k] == ids[i]) real_bind[k] = 0;
    }
    ((void (WINAPI *)(GLsizei, const GLuint *))real_delbuf)(n, ids);
}
static void WINAPI mugl_BindBuffer(GLenum t, GLuint id)
{
    if (!passthrough && (pending || mugl_in_begin || owned)) { flush_pending(); release_arrays(); update_busy(); }
    int k = tgt_index(t); if (k >= 0) { bound_buf[k] = id; emu_bind[k] = id; } /* after the flush: pending draws ran with the old binding */
    if (k >= 0 && vbo_emu) return;                          /* emulated: GL keeps binding 0 */
    if (k >= 0) real_bind[k] = id;
    ((PFNbb)real_bindbuf)(t, id);
}
static void WINAPI mugl_BufferData(GLenum t, GLsizeiptr size, const void *data, GLenum usage)
{
    int k = tgt_index(t);
    if (k >= 0 && bound_buf[k]) { BufInfo *b = buf_info(bound_buf[k], 1); if (b) { b->size = size; b->usage = usage; } }
    if (k >= 0 && emu_bind[k]) {                            /* keep the shadow current in every mode */
        Shadow *s = shadow_of(emu_bind[k], 1);
        if (s) { shadow_reserve(s, (size_t)size); if (s->cap >= (size_t)size) { s->size = (size_t)size; s->usage = usage; if (data) memcpy(s->data, data, (size_t)size); } }
        if (vbo_emu) { if (s) s->real_stale = 1; return; }
    }
    ((PFNbd)real_bufdata)(t, size, data, usage);
}
static void WINAPI mugl_BufferSubData(GLenum t, GLintptr off, GLsizeiptr size, const void *data)
{
    int k = tgt_index(t); st_subs++; st_sub_calls++; st_sub_bytes += (long)size;
    if (k >= 0 && emu_bind[k]) {
        Shadow *s = shadow_of(emu_bind[k], 1);
        if (s && off >= 0 && (size_t)off + (size_t)size <= s->size) memcpy(s->data + off, data, (size_t)size);
        if (vbo_emu) { if (s) s->real_stale = 1; return; }
    }
    BufInfo *b = (k >= 0 && bound_buf[k]) ? buf_info(bound_buf[k], 0) : NULL;
    if (filter_enabled && real_bufdata && b && off == 0 && size == b->size && b->usage) {
        ((PFNbd)real_bufdata)(t, size, NULL, b->usage);   /* orphan: fresh storage, no wait on the GPU */
        st_orphans++;
    }
    ((PFNbs)real_bufsub)(t, off, size, data);
}
static void WINAPI mugl_ActiveTexture(GLenum unit)
{
    if (ts_active_flag) ts_end_hook();   /* terrain runs track unit 0 only */
    ((void (WINAPI *)(GLenum))real_activetex)(unit);
    active_unit = (int)(unit - 0x84C0 /* GL_TEXTURE0 */);
}

/* calls that change current values behind our back */
void WINAPI mugl_glPopAttrib(void) { flush_pending(); lz_apply(); TIMED(3, R(glPopAttrib, PFN0)()); tp_gen++; cur_known = 0; forget_gl_current(); forget_state(); mmode_known = 0; update_busy(); }
void WINAPI mugl_glCallList(GLuint l) { mugl_sync(); R(glCallList, PFNcl)(l); tp_gen++; mx_epoch++; cur_known = 0; forget_gl_current(); forget_state(); mstk_valid = 0; update_busy(); }
void WINAPI mugl_glCallLists(GLsizei n, GLenum type, const void *lists) { mugl_sync(); R(glCallLists, PFNcls)(n, type, lists); tp_gen++; mx_epoch++; cur_known = 0; forget_gl_current(); forget_state(); mstk_valid = 0; update_busy(); }

/* Live mode switch: C:\mutools\mugl-mode.txt holds one of full|nomerge|nofilter|off (checked ~1/s). */
static DWORD mode_check; static char mode_cur[64] = "full";
static void check_mode_file(void)
{
    DWORD now = GetTickCount();
    if (now - mode_check < 1000) return;
    mode_check = now;
    FILE *f = fopen("C:\\mutools\\mugl-mode.txt", "r");
    if (!f) return;
    char m[64] = ""; if (fscanf(f, "%63s", m) != 1) m[0] = 0; fclose(f);
    if (!m[0] || !strcmp(m, mode_cur)) return;
    strcpy(mode_cur, m);
    /* "+" tokens in any order: vbo, time, finish, samples (see gpudiag.c) */
    int want_vbo = 0; time_mode = finish_mode = samples_mode = cull_mode = 0;
    for (char *tok = strchr(m, '+'); tok; ) {
        *tok++ = 0; char *nx = strchr(tok, '+'); if (nx) *nx = 0;
        if (!strcmp(tok, "vbo")) want_vbo = 1; else if (!strcmp(tok, "time")) time_mode = 1;
        else if (!strcmp(tok, "finish")) finish_mode = 1; else if (!strcmp(tok, "samples")) samples_mode = 1;
        else if (!strcmp(tok, "cull")) cull_mode = 1;
        if (nx) *nx = '+';
        tok = nx;
    }
    vbo_emu_set(want_vbo);
    nodraw = !strcmp(m, "nodraw"); if (nodraw) strcpy(m, "full");   /* diagnostic: skip batched draws */
    batching_enabled = strcmp(m, "off") != 0;
    merge_enabled = strcmp(m, "nomerge") != 0 && batching_enabled;
    int nf = !strcmp(m, "nofilter") || !strcmp(m, "off");
    if (filter_enabled == nf) forget_state();   /* caches may be stale when filtering resumes */
    filter_enabled = !nf;
    if (st_file) { fprintf(st_file, "=== live mode -> %s\n", m); fflush(st_file); }
}

/* ---- in-place hot patches for main.exe (C:\mutools\mugl-hotpatch.txt: 1 = on, 0 = off; polled ~1/s) ----
   Applied from inside the process so Rosetta sees the code write and retranslates. Every patch is
   verified byte-for-byte against the original (or the replacement) before writing. */
#include "hotpatches.h"
#include "inlinesites.h"
#include "peepsites.h"
/* Sleep accounting: main.exe's frame cap sleeps in Sleep(); hooking its IAT slot lets the stats report
   real work per frame (frame time minus sleep) even when the game sits at the 25 fps cap. */
static void (WINAPI *real_sleep)(DWORD);
static DWORD render_tid;
/* Frame pacing fix (hotpatch bit 1024): the frame driver 0x01851d39 sleeps 40 - (previous frame's work) after the
   current frame, so frames whose work alternates lose time (e.g. 25/45 ms frames pace at 42.5 ms). With the fix
   its Sleep at 0x0185267a is skipped and mugl paces swaps to a 40 ms schedule instead. The driver's logic-time
   accumulator still tracks real time (the slept time it assumes reappears in its next elapsed measurement). */
static int pace_fix, pace_swapped; static long long pace_next;
/* Precise waits (also bit 1024): Wine's Sleep() waits in the client with select(), and macOS coalesces those timers
   heavily while the game is not the frontmost Mac app (measured: Sleep(7..14) took 17..45 ms, so the driver's cap
   gave ~19 fps at 28 ms work and pacing jittered between 25 and 70 ms frames). Waits on a waitable timer are timed
   by the wineserver and stay within 1 ms in the background as well (frontmost, both are accurate). */
static HANDLE pace_timer; static int pace_timer_failed;
static long pc_waits, pc_late, pc_restart, pc_iv[7], pc_os[4], pc_other; static long long pc_last_swap, pc_os_ticks; static unsigned pc_logic0;
static void precise_wait(long long ticks)
{
    if (ticks <= 0) return;
    if (!pace_timer && !pace_timer_failed) { pace_timer = CreateWaitableTimerW(NULL, TRUE, NULL); pace_timer_failed = !pace_timer; }
    LARGE_INTEGER due; due.QuadPart = -(ticks * 10000000 / qpf.QuadPart);   /* relative, 100 ns units */
    if (pace_timer && due.QuadPart < 0 && SetWaitableTimer(pace_timer, &due, 0, NULL, NULL, FALSE) &&
        WaitForSingleObject(pace_timer, (DWORD)(ticks * 1000 / qpf.QuadPart) + 1000) == WAIT_OBJECT_0) return;
    DWORD ms = (DWORD)((ticks * 1000 + qpf.QuadPart / 2) / qpf.QuadPart);
    if (ms) real_sleep(ms);
}
static void pace_stats(FILE *f)
{
    unsigned lg = MUGL_PRIVATE_TABLES && mugl_client ? *(volatile unsigned *)0x0bdc5eb0 : 0, dl = lg - pc_logic0; pc_logic0 = lg;   /* driver's logic-step counter (40 ms steps); publication adaptation: never read a client address in the compile-only build, which can be loaded by other processes */
    if (!pace_fix || !qpf.QuadPart) return;
    fprintf(f, "pace: logic steps=%u waits=%ld late=%ld restarts=%ld overshoot avg=%.2fms (<1:%ld 1-5:%ld 5-20:%ld 20+:%ld) other_sleeps=%ld"
               " | frame ms <30:%ld 30-38:%ld 38-42:%ld 42-50:%ld 50-60:%ld 60-80:%ld 80+:%ld\n",
            dl, pc_waits, pc_late, pc_restart, pc_waits ? pc_os_ticks * 1000.0 / qpf.QuadPart / pc_waits : 0.0, pc_os[0], pc_os[1], pc_os[2], pc_os[3],
            pc_other, pc_iv[0], pc_iv[1], pc_iv[2], pc_iv[3], pc_iv[4], pc_iv[5], pc_iv[6]);
    pc_waits = pc_late = pc_restart = pc_other = 0; pc_os_ticks = 0; memset(pc_os, 0, sizeof pc_os); memset(pc_iv, 0, sizeof pc_iv);
}
static void pace_interval(long long t)   /* swap-to-swap interval histogram */
{
    if (pc_last_swap) { long long ms = (t - pc_last_swap) * 1000 / qpf.QuadPart; pc_iv[ms < 30 ? 0 : ms < 38 ? 1 : ms < 42 ? 2 : ms < 50 ? 3 : ms < 60 ? 4 : ms < 80 ? 5 : 6]++; }
    pc_last_swap = t;
}
static void WINAPI hook_sleep(DWORD ms)
{
    if (GetCurrentThreadId() != render_tid) { real_sleep(ms); return; }
    void *ret = __builtin_return_address(0);
    if (pace_fix && pace_swapped && ret == (void *)0x01852680) { pace_swapped = 0; st_pace_skips++; return; }
    LARGE_INTEGER a, b; QueryPerformanceCounter(&a);
    if (pace_fix && ms && qpf.QuadPart) { pc_other++; precise_wait(qpf.QuadPart * ms / 1000); }   /* same semantics as Sleep(ms): non-alertable */
    else real_sleep(ms);
    QueryPerformanceCounter(&b); sleep_ticks += b.QuadPart - a.QuadPart;
}
/* Only in the in-game scene (scene state [0x01d1df70] == 6, see client-frame-loop.md); login/character screens and
   frames that do not swap keep the driver's sleep (made precise by the hook above). */
static void pace_wait(void)
{
    pace_swapped = 0;
    if (!pace_fix || !real_sleep || !qpf.QuadPart) { pace_next = 0; return; }
    LARGE_INTEGER now; QueryPerformanceCounter(&now);
    if (*(volatile int *)0x01d1df70 != 6) { pace_next = 0; pace_interval(now.QuadPart); return; }
    pace_swapped = 1;
    const long long period = qpf.QuadPart * 40 / 1000;
    if (!pace_next || now.QuadPart >= pace_next + period) { pace_next = now.QuadPart + period; pc_restart++; }   /* first or > 1 period late: restart */
    else {
        if (now.QuadPart < pace_next) {
            precise_wait(pace_next - now.QuadPart);
            LARGE_INTEGER b; QueryPerformanceCounter(&b); sleep_ticks += b.QuadPart - now.QuadPart;
            long long over = b.QuadPart - pace_next; if (over < 0) over = 0;
            double om = over * 1000.0 / qpf.QuadPart; pc_os[om < 1 ? 0 : om < 5 ? 1 : om < 20 ? 2 : 3]++; pc_os_ticks += over; pc_waits++;
            now = b;
        } else pc_late++;
        pace_next += period;   /* slightly late frames keep the schedule, so the next one can catch up */
    }
    pace_interval(now.QuadPart);
}
static void hook_sleep_iat(void)
{
    if (real_sleep) return;
    void *k = (void *)GetProcAddress(GetModuleHandleA("kernel32.dll"), "Sleep");
    void *kb = (void *)GetProcAddress(GetModuleHandleA("kernelbase.dll"), "Sleep");
    QueryPerformanceFrequency(&qpf);
    for (void **p = (void **)0x01a7c000; p < (void **)0x01a7d000; p++) {
        MEMORY_BASIC_INFORMATION mi;
        if (((size_t)p & 0xfff) == 0 && (!VirtualQuery(p, &mi, sizeof mi) || mi.State != MEM_COMMIT)) return;
        if (*p && (*p == k || *p == kb)) {
            DWORD old; real_sleep = (void (WINAPI *)(DWORD))*p;
            if (VirtualProtect(p, 4, PAGE_READWRITE, &old)) { *p = (void *)hook_sleep; VirtualProtect(p, 4, old, &old); }
            if (st_file) { fprintf(st_file, "sleep hook at IAT %p\n", (void *)p); fflush(st_file); }
            return;
        }
    }
}
static int hp_state = -1;   /* bitmask applied: 1 = function bodies, 2 = inlined call sites */
static int hp_funcs(int on)
{
    int n = 0;
    for (size_t i = 0; i < sizeof hot_patches / sizeof hot_patches[0]; i++) {
        const HotPatch *p = &hot_patches[i];
        unsigned char *a = (unsigned char *)(size_t)p->addr;
        MEMORY_BASIC_INFORMATION mi;
        if (!VirtualQuery(a, &mi, sizeof mi) || mi.State != MEM_COMMIT) continue;
        const unsigned char *want = on ? p->repl : p->orig, *from = on ? p->orig : p->repl;
        if (!memcmp(a, want, p->len)) { n++; continue; }
        if (memcmp(a, from, p->len)) { if (st_file) fprintf(st_file, "hotpatch %s: unexpected bytes, skipped\n", p->name); continue; }
        DWORD old;
        if (!VirtualProtect(a, p->len, PAGE_EXECUTE_READWRITE, &old)) continue;
        memcpy(a, want, p->len);
        VirtualProtect(a, p->len, old, &old);
        FlushInstructionCache(GetCurrentProcess(), a, p->len);
        n++;
    }
    return n;
}
static int hp_sites(int on)
{
    int n = 0, bad = 0; size_t cnt = sizeof inline_sites / sizeof inline_sites[0];
    for (size_t i = 0; i < cnt; ) {
        unsigned page = inline_sites[i].addr & ~0xfffu; size_t j = i;
        while (j < cnt && (inline_sites[j].addr & ~0xfffu) == page) j++;
        unsigned char *lo = (unsigned char *)(size_t)inline_sites[i].addr;
        size_t len = inline_sites[j - 1].addr + 5 - inline_sites[i].addr;
        DWORD old;
        if (VirtualProtect(lo, len, PAGE_EXECUTE_READWRITE, &old)) {
            for (size_t k = i; k < j; k++) {
                const InlineSite *s = &inline_sites[k]; unsigned char *a = (unsigned char *)(size_t)s->addr;
                const unsigned char *want = on ? s->repl : s->orig, *from = on ? s->orig : s->repl;
                if (!memcmp(a, want, 5)) { n++; continue; }
                if (memcmp(a, from, 5)) { bad++; continue; }
                memcpy(a, want, 5); n++;
            }
            VirtualProtect(lo, len, old, &old);
            FlushInstructionCache(GetCurrentProcess(), lo, len);
        }
        i = j;
    }
    if (st_file) fprintf(st_file, "inline sites %s: %d/%d (%d unexpected)\n", on ? "on" : "off", n, (int)cnt, bad);
    return n;
}
static int hp_peep(int on)
{
    int n = 0, bad = 0; size_t cnt = sizeof peep_sites / sizeof peep_sites[0];
    for (size_t i = 0; i < cnt; ) {
        unsigned page = peep_sites[i].addr & ~0xfffu; size_t j = i;
        while (j < cnt && (peep_sites[j].addr & ~0xfffu) == page) j++;
        unsigned char *lo = (unsigned char *)(size_t)peep_sites[i].addr;
        size_t len = peep_sites[j - 1].addr + peep_sites[j - 1].len - peep_sites[i].addr;
        DWORD old;
        if (VirtualProtect(lo, len, PAGE_EXECUTE_READWRITE, &old)) {
            for (size_t k = i; k < j; k++) {
                const PeepSite *s = &peep_sites[k]; unsigned char *a = (unsigned char *)(size_t)s->addr;
                const unsigned char *want = on ? s->repl : s->orig, *from = on ? s->orig : s->repl;
                if (!memcmp(a, want, s->len)) { n++; continue; }
                if (memcmp(a, from, s->len)) { bad++; continue; }
                memcpy(a, want, s->len); n++;
            }
            VirtualProtect(lo, len, old, &old);
            FlushInstructionCache(GetCurrentProcess(), lo, len);
        }
        i = j;
    }
    if (st_file) fprintf(st_file, "peephole sites %s: %d/%d (%d unexpected)\n", on ? "on" : "off", n, (int)cnt, bad);
    return n;
}
#include "xform.c"
#include "meshdraw.c"
#include "shadow.c"
#include "decal.c"
static void hp_set(int mask)
{
    if (!mugl_client) mask &= ~(1 | 2 | 4 | 8 | 16 | 32 | 64 | 128 | 256 | 512 | 1024 | 8192 | 2097152 | 4194304 | 8388608 | 16777216 | 33554432 | 67108864 | 134217728 | 268435456 | 536870912);   /* GL-level bits only (test programs) */
    int f = hp_funcs(mask & 1), s = hp_sites((mask & 2) != 0), p = hp_peep((mask & 4) != 0);
    int x = xf_install((mask & 8) != 0, (mask & 16) != 0);
    if (st_file) fprintf(st_file, "xform %s%s: %d\n", (mask & 8) ? "on" : "off", (mask & 16) ? " (verify)" : "", x);
    md_untested = (mask & 8192) != 0;
    int md = md_install((mask & 96) != 0, (mask & 64) != 0, (mask & 128) != 0);
    int ml = md_light_install((mask & 256) != 0 && (mask & 96) != 0), mt = md_timer_install((mask & 512) != 0);
    if (st_file) fprintf(st_file, "meshdraw %s%s%s: %d light %s: %d timer %s: %d\n", (mask & 96) ? "on" : "off", (mask & 128) ? " direct" : "",
                         (mask & 64) ? " (verify)" : "", md, (mask & 256) && (mask & 96) ? "on" : "off", ml, (mask & 512) ? "on" : "off", mt);
    int sh = sh_install((mask & 2097152) != 0, (mask & 4194304) != 0);
    if (st_file) fprintf(st_file, "shadow %s%s%s: %d\n", (mask & 2097152) ? "on" : "off", (mask & 128) ? " direct" : "", (mask & 4194304) ? " (verify)" : "", sh);
    md_fast = (mask & 33554432) != 0;
    int td = td_install((mask & 8388608) != 0, (mask & 16777216) != 0);
    if (st_file) fprintf(st_file, "decal %s%s%s: %d\n", (mask & 8388608) ? "on" : "off", (mask & 128) ? " direct" : "", (mask & 16777216) ? " (verify)" : "", td);
    int jp = jp_install((mask & 67108864) != 0, (mask & 134217728) != 0);
    if (st_file) fprintf(st_file, "jpeg %s%s: %d\n", (mask & 67108864) ? "on" : "off", (mask & 134217728) ? " (verify)" : "", jp);
    int cr = cr_install((mask & 268435456) != 0, (mask & 536870912) != 0);
    if (st_file) fprintf(st_file, "crc %s%s: %d\n", (mask & 268435456) ? "on" : "off", (mask & 536870912) ? " (verify)" : "", cr);
    pace_fix = (mask & 1024) != 0;
    ts_on_flag = (mask & 16384) != 0; ts_verify = (mask & 32768) != 0;
    qs_on_flag = (mask & 65536) != 0; qs_verify = (mask & 131072) != 0;
    cull_on = (mask & 524288) != 0; cull_verify = (mask & 1048576) != 0;
    if (lz_on != ((mask & 1073741824) != 0)) { flush_pending(); lz_apply(); lz_on = (mask & 1073741824) != 0; tp_gen++; update_busy(); }
    if (cs_lazy != ((mask & 262144) != 0)) { if (cs_lazy) { flush_pending(); cs_apply(); } cs_forget(); cs_lazy = (mask & 262144) != 0; update_busy(); }
    if (st_file) fprintf(st_file, "terrain sort %s%s, quad batching %s%s\n", ts_on_flag ? "on" : "off", ts_verify ? " (verify)" : "",
                         qs_on_flag ? "on" : "off", qs_verify ? " (verify)" : "");
    if (zero_copy_full != ((mask & 2048) != 0) || strided_arrays != ((mask & 4096) != 0)) {
        flush_pending(); release_arrays(); update_busy(); zero_copy_full = (mask & 2048) != 0; strided_arrays = (mask & 4096) != 0;
    }
    if (st_file) fprintf(st_file, "strided batch arrays %s\n", strided_arrays ? "on" : "off");
    if (st_file) fprintf(st_file, "zero-copy full-format batches %s\n", zero_copy_full ? "on" : "off");
    if (st_file) fprintf(st_file, "frame pacing fix %s\n", pace_fix ? "on" : "off");
    if (st_file) { fprintf(st_file, "=== hotpatch mask %d: funcs %d/%d sites %d peep %d\n", mask, f, (int)(sizeof hot_patches / sizeof hot_patches[0]), s, p); fflush(st_file); }
}
static DWORD hp_check;
static void check_hotpatch_file(void)
{
    DWORD now = GetTickCount();
    if (now - hp_check < 1000) return;
    hp_check = now;
    int want = 380460463; /* default (v7.6): 1|2|4|8 helpers/inlining/peephole/xform + 32|128|256 meshdraw + 1024|2048|4096 + 16384 terrain sort
                          + 65536 quad batching + 262144 deferred client-array enables + 524288 off-screen culling (v7.4: 875951)
                          + 2097152 native shadows + 8388608 native decals + 33554432 specialised mesh append (v7.5: 44916143)
                          + 67108864 native JPEG decode + 268435456 native CRC-32
                          (v7.3: 23983; v7.1/v7.2: 7599; v7.0: 15). Bits: 16 = xform verify, 32 = meshdraw, 64 = meshdraw verify, 128 = meshdraw
                          direct batch append, 256 = meshdraw light precompute (with 32/64), 512 = mesh routine timer, 1024 = frame pacing fix,
                          2048 = zero-copy T2F_C4F_N3F_V3F batches, 4096 = strided batch arrays, 8192 = meshdraw unverified vertex paths,
                          16384 = terrain face sorting, 32768 = terrain sort offscreen verification, 65536 = sprite/grass quad batching,
                          131072 = quad batching offscreen verification, 262144 = deferred client-array enables, 524288 = off-screen batch
                          culling, 1048576 = culling sample-count verification, 2097152 = native body shadows, 4194304 = shadow verification,
                          8388608 = native terrain decals, 16777216 = decal verification, 33554432 = specialised mesh-draw append,
                          67108864 = native JPEG decode, 134217728 = JPEG verification, 268435456 = native CRC-32, 536870912 = CRC verification */
    FILE *f = fopen("C:\\mutools\\mugl-hotpatch.txt", "r");
    if (f) { int v; if (fscanf(f, "%d", &v) == 1) want = v & 2147483647; fclose(f); }
    if (!mugl_client) { const char *e = getenv("MUGL_MASK"); if (e) want = atoi(e) & 2147483647; }   /* test programs: mask from the environment */
    if (want != hp_state) { hp_set(want); hp_state = want; }
}

static long total_frames; static HMODULE self_mod;
#include "stall.c"
#include "terrain.c"
#include "jpeg.c"
#include "crc.c"
BOOL WINAPI mugl_wglSwapBuffers(HDC dc)
{
    io_frame_end(); tr_frame_end();
    mugl_sync(); mx_epoch++;
    check_mode_file();
    if (++total_frames > 100 && MUGL_PRIVATE_TABLES && !mugl_client) check_hotpatch_file();   /* test programs: GL-level bits */
    if (total_frames > 100 && MUGL_PRIVATE_TABLES && mugl_client) { render_tid = GetCurrentThreadId(); check_hotpatch_file(); hook_sleep_iat(); if (total_frames == 101 && st_file) io_publish(); io_install(self_mod); tr_check(); prio_check(); }   /* main.exe code is unpacked long before the first frames */
    dc_finish(); if (samples_mode || dq_n) dq_frame();
    st_frames++; stats_tick();
    pace_wait();
    BOOL r_; TIMED(6, r_ = R(wglSwapBuffers, PFNswap)(dc)); return r_;
}

/* extension pointers: wrap so calls synchronize first */


static unsigned char *tramp_mem; static int tramp_used;
PROC WINAPI mugl_wglGetProcAddress(LPCSTR name)
{
    PROC p = R(wglGetProcAddress, PFNgpa)(name);
    if (p && name && (!strcmp(name, "glBindBuffer") || !strcmp(name, "glBindBufferARB"))) { vbo_seen = 1; if (!real_bindbuf) real_bindbuf = (void *)p; }
    if (!p || !name || getenv("MUGL_NOWRAP")) return p;
    if (!strcmp(name, "glActiveTexture") || !strcmp(name, "glActiveTextureARB")) { real_activetex = (void *)p; return (PROC)mugl_ActiveTexture; }
    if (!strcmp(name, "glBindBuffer") || !strcmp(name, "glBindBufferARB")) return (PROC)mugl_BindBuffer;
    if (!strcmp(name, "glBufferData") || !strcmp(name, "glBufferDataARB")) { real_bufdata = (void *)p; real_bufdata_p = (void *)p; return (PROC)mugl_BufferData; }
    if (!strcmp(name, "glBufferSubData") || !strcmp(name, "glBufferSubDataARB")) { real_bufsub = (void *)p; return (PROC)mugl_BufferSubData; }
    if (!strcmp(name, "glMapBuffer") || !strcmp(name, "glMapBufferARB")) { real_mapbuf = (void *)p; return (PROC)mugl_MapBuffer; }
    if (!strcmp(name, "glUnmapBuffer") || !strcmp(name, "glUnmapBufferARB")) { real_unmapbuf = (void *)p; return (PROC)mugl_UnmapBuffer; }
    if (!strcmp(name, "glGetBufferSubData") || !strcmp(name, "glGetBufferSubDataARB")) { real_getbufsub = (void *)p; return (PROC)mugl_GetBufferSubData; }
    if (!strcmp(name, "glGetBufferParameteriv") || !strcmp(name, "glGetBufferParameterivARB")) { real_getbufparam = (void *)p; return (PROC)mugl_GetBufferParameteriv; }
    if (!strcmp(name, "glDrawRangeElements") || !strcmp(name, "glDrawRangeElementsEXT")) { real_drawrange = (void *)p; return (PROC)mugl_DrawRangeElements; }
    if (!strcmp(name, "glVertexAttribPointer") || !strcmp(name, "glVertexAttribPointerARB")) { real_vattrib = (void *)p; return (PROC)mugl_VertexAttribPointer; }
    if (!strcmp(name, "glDeleteBuffers") || !strcmp(name, "glDeleteBuffersARB")) { real_delbuf = (void *)p; return (PROC)mugl_DeleteBuffers; }
    for (int i = 0; i < nexts; i++) if (!strcmp(exts[i].name, name) && exts[i].real == (void *)p) return (PROC)exts[i].tramp;
    if (nexts >= 512) return p;
    if (!tramp_mem) tramp_mem = VirtualAlloc(NULL, 65536, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
    if (!tramp_mem || tramp_used + 64 > 65536) return p;
    Ext *e = &exts[nexts++];
    strncpy(e->name, name, 63); e->real = (void *)p; e->flags = ext_flags(name);
    unsigned char *c = tramp_mem + tramp_used; tramp_used += 64; e->tramp = c;
    void **slot = &e->real;
    /* cmp byte [mugl_busy],0 ; jne +6 ; jmp [slot] ; pushad ; pushfd ; call mugl_sync ; popfd ; popad ; jmp [slot] */
    unsigned char *q = c;
    if (!strstr(name, "Matrix")) {   /* matrix extensions always reach mugl_sync_ext (matrix epoch for culling) */
        *q++ = 0x80; *q++ = 0x3d; *(void **)q = &mugl_busy; q += 4; *q++ = 0x00;
        *q++ = 0x75; *q++ = 0x06;
        *q++ = 0xff; *q++ = 0x25; *(void ***)q = slot; q += 4;
    }
    *q++ = 0x60; *q++ = 0x9c;
    *q++ = 0x68; *(int *)q = nexts - 1; q += 4;                                      /* push index */
    *q++ = 0xe8; *(int *)q = (int)((unsigned char *)mugl_sync_ext - (q + 4)); q += 4; /* call mugl_sync_ext */
    *q++ = 0x83; *q++ = 0xc4; *q++ = 0x04;                                           /* add esp, 4 */
    *q++ = 0x9d; *q++ = 0x61;
    *q++ = 0xff; *q++ = 0x25; *(void ***)q = slot; q += 4;
    FlushInstructionCache(GetCurrentProcess(), c, 64);
    return (PROC)c;
}

void mugl_sync_ext(int i)
{
    if (count_mode && i >= 0 && i < 512) st_ext[i]++;
    if (i >= 0 && i < nexts && strstr(exts[i].name, "Matrix")) mx_always = 1;   /* the real call follows this sync: no epoch can be set after it */
    TR("X %s\n", (i >= 0 && i < nexts) ? exts[i].name : "?");
    if (passthrough) return;
    unsigned char f = (i >= 0 && i < nexts) ? exts[i].flags : 7;
    flush_pending();
    lz_apply();   /* v7.6: an extension call may draw or read enables */
    if (i >= 0 && i < nexts && strstr(exts[i].name, "Matrix")) matrix_modified();
    if (f & 2) { cs_apply(); if (i >= 0 && i < nexts && strstr(exts[i].name, "ClientActiveTexture")) cs_forget(); }   /* texture coordinate enables are per client unit */
    if (f & 2) release_arrays();
    if (f & 1) send_current();
    if (f & 4) forget_gl_current();
    update_busy();
}
static unsigned char ext_flags(const char *n)
{
    int arrays = strstr(n, "Pointer") || strstr(n, "ClientState") || strstr(n, "ClientActiveTexture") || strstr(n, "ArrayElement") ||
                 strstr(n, "LockArrays") || strstr(n, "VertexAttribArray") || strstr(n, "VertexArray") || strstr(n, "Draw") ||
                 strstr(n, "PushClientAttrib") || strstr(n, "PopClientAttrib") || strstr(n, "BindBuffer");
    int draws = strstr(n, "Draw") || strstr(n, "ArrayElement") || strstr(n, "CallList") || strstr(n, "WindowPos") || strstr(n, "Eval");
    int queries = !strncmp(n, "glGet", 5) || !strncmp(n, "glIs", 4);
    if (queries) return 3;                       /* conservative: may read current values or array state */
    return (unsigned char)((arrays ? 2 : 0) | (draws ? 5 : 0));
}

/* ---- extra display modes ----
   The client offers only 16:10 modes with "round" sizes taken from EnumDisplaySettings;
   on a 1800x1169 Mac screen nothing between 1280x800 and 1920x1200 fits. If
   C:\mutools\mugl-modes.txt lists extra modes ("1600x1000 1728x1080"), they are inserted
   (copying the attributes of the next smaller real mode) into this process's enumeration. */
typedef struct { DWORD w, h; } ExtraMode;
static ExtraMode extra_modes[8]; static int nextra;
typedef BOOL (WINAPI *PFNedsexa)(LPCSTR, DWORD, DEVMODEA *, DWORD);
typedef BOOL (WINAPI *PFNedsexw)(LPCWSTR, DWORD, DEVMODEW *, DWORD);
static PFNedsexa real_edsexa; static PFNedsexw real_edsexw;
/* Virtual mode list built once: real entries plus synthetic copies of the preceding
   resolution group (same frequencies/bit depth) with replaced width/height. */
typedef struct { DWORD tmpl; DWORD w, h; } VMode;   /* w == 0: real mode as-is */
static VMode *vmodes; static int nvmodes = -1;
static void build_vmodes(void)
{
    DEVMODEA dm; int cap = 512, n = 0; vmodes = (VMode *)malloc(sizeof(VMode) * cap);
    int inserted[8] = {0}; DWORD r = 0; DWORD pw = 0, ph = 0, gstart = 0;
    for (;;) {
        dm.dmSize = sizeof dm; dm.dmDriverExtra = 0;
        BOOL ok = real_edsexa(NULL, r, &dm, 0);
        for (int k = 0; k < nextra; k++) {
            if (inserted[k] || r == 0) continue;
            if (!ok || dm.dmPelsWidth * dm.dmPelsHeight > extra_modes[k].w * extra_modes[k].h) {
                inserted[k] = 1;
                for (DWORD t = gstart; t < r && n < cap; t++) { vmodes[n].tmpl = t; vmodes[n].w = extra_modes[k].w; vmodes[n].h = extra_modes[k].h; n++; }
            }
        }
        if (!ok || n >= cap) break;
        if (dm.dmPelsWidth != pw || dm.dmPelsHeight != ph) { gstart = r; pw = dm.dmPelsWidth; ph = dm.dmPelsHeight; }
        vmodes[n].tmpl = r; vmodes[n].w = 0; vmodes[n].h = 0; n++; r++;
    }
    nvmodes = n;
}
static BOOL fill_mode_a(DWORD i, DEVMODEA *dm)
{
    if (nvmodes < 0) build_vmodes();
    if ((int)i >= nvmodes) return FALSE;
    if (!real_edsexa(NULL, vmodes[i].tmpl, dm, 0)) return FALSE;
    if (vmodes[i].w) { dm->dmPelsWidth = vmodes[i].w; dm->dmPelsHeight = vmodes[i].h; }
    return TRUE;
}
static BOOL fill_mode_w(DWORD i, DEVMODEW *dm)
{
    if (nvmodes < 0) build_vmodes();
    if ((int)i >= nvmodes) return FALSE;
    if (!real_edsexw(NULL, vmodes[i].tmpl, dm, 0)) return FALSE;
    if (vmodes[i].w) { dm->dmPelsWidth = vmodes[i].w; dm->dmPelsHeight = vmodes[i].h; }
    return TRUE;
}
static BOOL WINAPI hook_EnumDisplaySettingsA(LPCSTR dev, DWORD i, DEVMODEA *dm)
{
    if (dev || i == ENUM_CURRENT_SETTINGS || i == ENUM_REGISTRY_SETTINGS) return real_edsexa(dev, i, dm, 0);
    return fill_mode_a(i, dm);
}
static BOOL WINAPI hook_EnumDisplaySettingsW(LPCWSTR dev, DWORD i, DEVMODEW *dm)
{
    if (dev || i == ENUM_CURRENT_SETTINGS || i == ENUM_REGISTRY_SETTINGS) return real_edsexw(dev, i, dm, 0);
    return fill_mode_w(i, dm);
}
static void patch_jmp(void *from, void *to)
{
    DWORD old; unsigned char *p = (unsigned char *)from;
    if (!VirtualProtect(p, 5, PAGE_EXECUTE_READWRITE, &old)) return;
    p[0] = 0xE9; *(int *)(p + 1) = (int)((unsigned char *)to - (p + 5));
    VirtualProtect(p, 5, old, &old); FlushInstructionCache(GetCurrentProcess(), p, 5);
}
static void install_mode_hooks(void)
{
    FILE *f = fopen("C:\\mutools\\mugl-modes.txt", "r");
    if (st_file) { fprintf(st_file, "modes: file %s\n", f ? "found" : "missing"); fflush(st_file); }
    if (!f) return;
    unsigned w, h;
    while (nextra < 8 && fscanf(f, " %ux%u", &w, &h) == 2) { extra_modes[nextra].w = w; extra_modes[nextra].h = h; nextra++; }
    fclose(f);
    if (!nextra) return;
    HMODULE u = GetModuleHandleA("user32.dll"); if (!u) u = LoadLibraryA("user32.dll");
    real_edsexa = (PFNedsexa)GetProcAddress(u, "EnumDisplaySettingsExA");
    real_edsexw = (PFNedsexw)GetProcAddress(u, "EnumDisplaySettingsExW");
    void *a = (void *)GetProcAddress(u, "EnumDisplaySettingsA"), *wp = (void *)GetProcAddress(u, "EnumDisplaySettingsW");
    if (st_file) { fprintf(st_file, "modes: %d extra; EDSA=%p EDSW=%p EDSExA=%p EDSExW=%p bytes %02x %02x %02x %02x %02x\n", nextra, a, wp,
        (void *)real_edsexa, (void *)real_edsexw, a ? ((unsigned char *)a)[0] : 0, a ? ((unsigned char *)a)[1] : 0, a ? ((unsigned char *)a)[2] : 0,
        a ? ((unsigned char *)a)[3] : 0, a ? ((unsigned char *)a)[4] : 0); fflush(st_file); }
    if (!real_edsexa || !real_edsexw || !a || !wp) return;
    if (a == (void *)real_edsexa || wp == (void *)real_edsexw) return;   /* forwarded exports: never patch the implementation itself */
    patch_jmp(a, (void *)hook_EnumDisplaySettingsA);
    patch_jmp(wp, (void *)hook_EnumDisplaySettingsW);
    if (st_file) { fprintf(st_file, "modes: hooks installed\n"); fflush(st_file); }
}

/* ---- loading ---- */
static HMODULE real_mod;
static int load_real(HINSTANCE self)
{
    char path[MAX_PATH] = "";
    const char *env = getenv("MUGL_REAL");
    const char *cands[] = { env, "C:\\windows\\system32\\opengl32.dll",
        "Z:\\Applications\\CrossOver.app\\Contents\\SharedSupport\\CrossOver\\lib\\wine\\i386-windows\\opengl32.dll" };
    for (int i = 0; i < 3; i++) {
        if (!cands[i]) continue;
        HMODULE m = LoadLibraryA(cands[i]);
        if (m && m != self) { real_mod = m; GetModuleFileNameA(m, path, sizeof path); break; }
    }
    if (!real_mod) return 0;
    for (size_t i = 0; i < sizeof(mugl_names) / sizeof(mugl_names[0]); i++)
        *mugl_slots[i] = (void *)GetProcAddress(real_mod, mugl_names[i]);
    const char *mode = getenv("MUGL_MODE"); /* "off" = pure pass-through, "nomerge" = per-block */
    if (mode && !strcmp(mode, "off")) batching_enabled = 0;
    if (mode && !strcmp(mode, "nomerge")) merge_enabled = 0;
    if (getenv("MUGL_COUNT")) { count_mode = 1; mugl_busy = 1; }
    if (mode && !strcmp(mode, "nofilter")) filter_enabled = 0;
    mode_check = GetTickCount() - 5000; check_mode_file(); /* apply the mode file from the first frame */
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
        DisableThreadLibraryCalls(inst); self_mod = inst;
        { char exe[MAX_PATH] = ""; GetModuleFileNameA(NULL, exe, sizeof exe); const char *b = exe;
          for (const char *q = exe; *q; q++) if (*q == '\\' || *q == '/') b = q + 1;
          mugl_client = !lstrcmpiA(b, "main.exe"); }
        if (!load_real(inst)) return FALSE;
        modehook_install();   /* curated mode list shared with the launcher's version.dll proxy */
    }
    return TRUE;
}
