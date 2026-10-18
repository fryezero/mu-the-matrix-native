/* Off-screen batch culling (hotpatch bit 524288, v7.4). Included by mugl.c before submit_batch.

   Zoomed out (F6 camera) about a third of the mesh-draw batches (575 of 1,704 per frame, 377k of 1.17M vertices) lie
   entirely outside the view: the client's object culling is coarser than the view frustum. A batch whose vertices
   all lie outside one of the clip planes x = w, x = -w, y = w, y = -w, or behind the eye (w < 0), produces no
   fragment, so with the bit mugl does not submit it. Only those planes are used (near/far clipping is off with depth
   clamping, and user clip planes only remove more). A vertex counts as outside only with a relative margin of 1e-5,
   computed in double precision from the same float inputs, so rounding differences to the GPU cannot turn a
   rejected vertex into a visible one. The first vertex is tested first: a batch whose first vertex is inside every
   plane is drawn after one transform; otherwise the 8 corners of the batch's bounding box are tested, and the batch
   is dropped when all corners are outside one plane (then so is every vertex).

   The matrices are read with glGetFloatv only after a change: every matrix call (translate, rotate, scale, multiply,
   load, ortho, frustum, load identity, pop, display lists, matrix extensions) advances mx_epoch, and so does every
   frame, and a matrix extension makes every later test read them. Culling is off while the render mode is not GL_RENDER (selection or feedback count primitives). */
#include <xmmintrin.h>
static unsigned mx_epoch = 1, mx_seen; static int mx_always; static double mx_mvp[16]; static int cull_on, cull_rendermode_ok = 1;
static long st_cull_batches, st_cull_verts, st_cull_tested, st_cv_checked, st_cv_bad; static long long cv_tot_checked, cv_tot_bad;
static int cull_verify;
static void release_arrays(void);
/* Bit 1048576 (diagnostic): every 16th culled batch is rasterized anyway with color and depth writes off and the depth,
   alpha, stencil, scissor and face-culling tests disabled, inside a GL_SAMPLES_PASSED query; the count must be 0.
   Positions only (coverage does not depend on the other attributes); the enable, color, depth and stencil state is
   saved and restored with glPushAttrib/glPopAttrib around it. */
static void cull_check(const Vtx *v, int n)
{
    if (samples_mode || !dq_init()) return;
    release_arrays();
    R(glPushAttrib, PFNpca)(GL_ENABLE_BIT | GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT | GL_STENCIL_BUFFER_BIT | GL_SCISSOR_BIT);
    R(glDisable, PFN1u)(GL_DEPTH_TEST); R(glDisable, PFN1u)(GL_ALPHA_TEST); R(glDisable, PFN1u)(GL_STENCIL_TEST);
    R(glDisable, PFN1u)(GL_SCISSOR_TEST); R(glDisable, PFN1u)(GL_CULL_FACE);
    ((void (WINAPI *)(GLboolean, GLboolean, GLboolean, GLboolean))real_glColorMask)(0, 0, 0, 0); ((void (WINAPI *)(GLboolean))real_glDepthMask)(0);
    dq_begin(0x8914, dq_ids[DQ_MAX - 1]);
    R(glBegin, PFN1u)(GL_TRIANGLES);
    for (int i = 0; i < n; i++) R(glVertex3fv, PFNfv)(v[i].v);
    R(glEnd, PFN0)();
    dq_end(0x8914);
    GLuint r = 0; dq_get(dq_ids[DQ_MAX - 1], 0x8866, &r);
    R(glPopAttrib, PFN0)();
    st_cv_checked++; cv_tot_checked++;
    if (r) { st_cv_bad++; cv_tot_bad++; if (st_file && cv_tot_bad <= 10) fprintf(st_file, "cull verify: culled batch of %d vertices produced %u samples\n", n, r); }
}
static unsigned cull_code(const float *p)
{
    const double *m = mx_mvp; double c[4];
    for (int r = 0; r < 4; r++) c[r] = m[r] * p[0] + m[4 + r] * p[1] + m[8 + r] * p[2] + m[12 + r];
    double e = 1e-5 * (1.0 + fabs(c[0]) + fabs(c[1]) + fabs(c[3]));
    return (unsigned)(c[0] > c[3] + e) | (unsigned)(c[0] < -c[3] - e) << 1 | (unsigned)(c[1] > c[3] + e) << 2 |
           (unsigned)(c[1] < -c[3] - e) << 3 | (unsigned)(c[3] < -e) << 4;
}
/* 1 = vb[0..n) cannot produce a fragment. */
static int cull_batch(const Vtx *v, int n)
{
    if (!cull_on || !cull_rendermode_ok || n < 3) return 0;
    if (mx_seen != mx_epoch || mx_always) {
        float mv[16], pr[16];
        R(glGetFloatv, PFNget)(GL_MODELVIEW_MATRIX, mv); R(glGetFloatv, PFNget)(GL_PROJECTION_MATRIX, pr);
        for (int c = 0; c < 4; c++) for (int r = 0; r < 4; r++) {
            double s = 0; for (int k = 0; k < 4; k++) s += (double)pr[k * 4 + r] * mv[c * 4 + k]; mx_mvp[c * 4 + r] = s;
        }
        mx_seen = mx_epoch;
    }
    st_cull_tested++;
    if (!cull_code(v[0].v)) return 0;   /* first vertex inside every plane: visible candidate, drawn */
    /* bounding box of the positions (lanes 1..3 of the load at n[2] hold v[0..2]); the batch is culled when all 8
       corners lie outside one plane, which implies every vertex does */
    __m128 lo = _mm_loadu_ps(&v[0].n[2]), hi = lo, bad = _mm_cmpunord_ps(lo, lo);
    for (int i = 1; i < n; i++) { __m128 p = _mm_loadu_ps(&v[i].n[2]); lo = _mm_min_ps(lo, p); hi = _mm_max_ps(hi, p); bad = _mm_or_ps(bad, _mm_cmpunord_ps(p, p)); }
    if (_mm_movemask_ps(bad) & 14) return 0;   /* a NaN position: leave the batch to GL */
    float l[4], h[4]; _mm_storeu_ps(l, lo); _mm_storeu_ps(h, hi);
    unsigned all = 31;
    for (int k = 0; all && k < 8; k++) { float c[3] = {k & 1 ? h[1] : l[1], k & 2 ? h[2] : l[2], k & 4 ? h[3] : l[3]}; all &= cull_code(c); }
    if (!all) return 0;
    st_cull_batches++; st_cull_verts += n;
    if (cull_verify && (st_cull_batches & 15) == 1) cull_check(v, n);
    return 1;
}

/* Matrix calls: the generated stubs, plus the matrix epoch and matrix_modified() also when mugl is idle (a stub
   reaches mugl only when it is busy). */
static int mx_idx(const char *n, int *cache)
{
    if (*cache < 0) for (int i = 0; i < (int)(sizeof mugl_names / sizeof mugl_names[0]); i++) if (!strcmp(mugl_names[i], n)) { *cache = i; break; }
    return *cache;
}
/* The epoch advances after the real call: the synchronization before it may draw (and re-read the matrices for)
   batches recorded under the old matrix. */
#define MX_PRE(name) static int ix_ = -1; if (mugl_busy) mugl_sync_from(mx_idx(name, &ix_)); if (!passthrough) matrix_modified()
#define MX_POST mx_epoch++
/* v7.6 (bit 1073741824): matrix calls made after a glPushMatrix are queued; a glPopMatrix that finds its push still
   queued drops the push and everything after it (the matrix stack ends exactly as before and nothing in between could
   observe it). Anything that may observe the matrices sends the queue first, in order (mq_replay in mugl.c): glBegin,
   every exported call except the filtered state calls and glViewport, glGet*, glMatrixMode, attribute pops, display
   lists and full synchronization. */
enum { MQ_PUSH, MQ_LOADID, MQ_TRANSF, MQ_ROTF, MQ_ROTD, MQ_SCALEF, MQ_SCALED, MQ_MULTF, MQ_MULTD, MQ_LOADF, MQ_LOADD, MQ_ORTHO, MQ_FRUSTUM };
typedef struct { unsigned char kind; float f[16]; double d[16]; } MqOp;
static MqOp mq[48]; static int mq_n, mq_enabled = 1; static long st_mq_dropped, st_mq_sent;
static int mq_can(void) { return lz_on && mq_enabled && !passthrough && !lz_list && filter_enabled; }
/* 1 = queued (only inside a queued push span) */
static int mq_add(int kind, const float *f, int nf, const double *d, int nd)
{
    if (!mq_n || !mq_can() || mq_n == 48) return 0;
    MqOp *o = &mq[mq_n++]; o->kind = (unsigned char)kind;
    for (int i = 0; i < nf; i++) o->f[i] = f[i];
    for (int i = 0; i < nd; i++) o->d[i] = d[i];
    matrix_modified(); mx_epoch++;
    return 1;
}
typedef void (WINAPI *PFNtf)(GLfloat, GLfloat, GLfloat); typedef void (WINAPI *PFNtd)(GLdouble, GLdouble, GLdouble);
typedef void (WINAPI *PFNmxr)(GLfloat, GLfloat, GLfloat, GLfloat); typedef void (WINAPI *PFNrd)(GLdouble, GLdouble, GLdouble, GLdouble);
typedef void (WINAPI *PFNmf)(const GLfloat *); typedef void (WINAPI *PFNmd)(const GLdouble *);
typedef void (WINAPI *PFNod)(GLdouble, GLdouble, GLdouble, GLdouble, GLdouble, GLdouble);
typedef GLint (WINAPI *PFNrm)(GLenum);
void WINAPI mugl_glTranslatef(GLfloat x, GLfloat y, GLfloat z) { { float a[3] = {x, y, z}; if (mq_add(MQ_TRANSF, a, 3, 0, 0)) return; if (mq_n) mq_replay(); } MX_PRE("glTranslatef"); R(glTranslatef, PFNtf)(x, y, z); MX_POST; }
void WINAPI mugl_glRotatef(GLfloat a, GLfloat x, GLfloat y, GLfloat z) { { float v[4] = {a, x, y, z}; if (mq_add(MQ_ROTF, v, 4, 0, 0)) return; if (mq_n) mq_replay(); } MX_PRE("glRotatef"); R(glRotatef, PFNmxr)(a, x, y, z); MX_POST; }
void WINAPI mugl_glRotated(GLdouble a, GLdouble x, GLdouble y, GLdouble z) { { double v[4] = {a, x, y, z}; if (mq_add(MQ_ROTD, 0, 0, v, 4)) return; if (mq_n) mq_replay(); } MX_PRE("glRotated"); R(glRotated, PFNrd)(a, x, y, z); MX_POST; }
void WINAPI mugl_glScalef(GLfloat x, GLfloat y, GLfloat z) { { float a[3] = {x, y, z}; if (mq_add(MQ_SCALEF, a, 3, 0, 0)) return; if (mq_n) mq_replay(); } MX_PRE("glScalef"); R(glScalef, PFNtf)(x, y, z); MX_POST; }
void WINAPI mugl_glScaled(GLdouble x, GLdouble y, GLdouble z) { { double a[3] = {x, y, z}; if (mq_add(MQ_SCALED, 0, 0, a, 3)) return; if (mq_n) mq_replay(); } MX_PRE("glScaled"); R(glScaled, PFNtd)(x, y, z); MX_POST; }
void WINAPI mugl_glMultMatrixf(const GLfloat *m) { if (mq_add(MQ_MULTF, m, 16, 0, 0)) return; if (mq_n) mq_replay(); MX_PRE("glMultMatrixf"); R(glMultMatrixf, PFNmf)(m); MX_POST; }
void WINAPI mugl_glMultMatrixd(const GLdouble *m) { if (mq_add(MQ_MULTD, 0, 0, m, 16)) return; if (mq_n) mq_replay(); MX_PRE("glMultMatrixd"); R(glMultMatrixd, PFNmd)(m); MX_POST; }
void WINAPI mugl_glLoadMatrixf(const GLfloat *m) { if (mq_add(MQ_LOADF, m, 16, 0, 0)) return; if (mq_n) mq_replay(); MX_PRE("glLoadMatrixf"); R(glLoadMatrixf, PFNmf)(m); MX_POST; }
void WINAPI mugl_glLoadMatrixd(const GLdouble *m) { if (mq_add(MQ_LOADD, 0, 0, m, 16)) return; if (mq_n) mq_replay(); MX_PRE("glLoadMatrixd"); R(glLoadMatrixd, PFNmd)(m); MX_POST; }
void WINAPI mugl_glOrtho(GLdouble l, GLdouble r, GLdouble b, GLdouble t, GLdouble n, GLdouble f) { { double a[6] = {l, r, b, t, n, f}; if (mq_add(MQ_ORTHO, 0, 0, a, 6)) return; if (mq_n) mq_replay(); } MX_PRE("glOrtho"); R(glOrtho, PFNod)(l, r, b, t, n, f); MX_POST; }
void WINAPI mugl_glFrustum(GLdouble l, GLdouble r, GLdouble b, GLdouble t, GLdouble n, GLdouble f) { { double a[6] = {l, r, b, t, n, f}; if (mq_add(MQ_FRUSTUM, 0, 0, a, 6)) return; if (mq_n) mq_replay(); } MX_PRE("glFrustum"); R(glFrustum, PFNod)(l, r, b, t, n, f); MX_POST; }
GLint WINAPI mugl_glRenderMode(GLenum m)
{
    if (mq_n) mq_replay();
    static int ix_ = -1; if (mugl_busy) mugl_sync_from(mx_idx("glRenderMode", &ix_));
    GLint r = R(glRenderMode, PFNrm)(m);
    if (!passthrough) cull_rendermode_ok = m == GL_RENDER;
    return r;
}
