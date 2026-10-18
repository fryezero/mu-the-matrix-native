/* Terrain face sorting (hotpatch bit 16384, verify 32768; v7.3). Included by mugl.c.

   The terrain tile loop draws every visible tile as a 4-vertex GL_TRIANGLE_FAN: the layer-1 ("opaque") face from
   return address 0x016cfab3 with blending off, culling on and alpha test off, then, for tiles with a layer-2 alpha,
   the alpha face from 0x016cfb53 with blending on (SRC_ALPHA, ONE_MINUS_SRC_ALPHA), culling off and alpha test on.
   The state flips for every alpha tile and the texture changes between faces, so mugl submitted one draw per face:
   about 1,300 draws per frame in the default view and 3,500 zoomed out (F6 camera), for 6-24 vertices each.

   With the bit, a run of terrain faces (nothing but those two callers' fans, glEnable/glDisable of GL_BLEND,
   GL_CULL_FACE and GL_ALPHA_TEST, glBindTexture on unit 0, glBlendFunc, glDepthMask and glAlphaFunc) is recorded
   instead of drawn; the state calls become virtual. The run ends at the first other call. If every face is in one of
   two state classes (O: blending off; A: blending on), the run is drawn as all O faces grouped by texture in
   first-use order, then all A faces grouped by texture, each group one draw; otherwise it is drawn in the original
   order. Finally the real GL state is set to the state the original stream leaves.

   Why the order change keeps the image: an A face covers exactly the pixels of its own O face at identical depth
   (same tile corners), the depth test is LEQUAL and both classes write depth, so with depth-distinct surfaces each
   pixel ends as (A over O) of its nearest tile in either order. Order matters only for depth ties between different
   tiles at one pixel and for A faces without their O face underneath (back-facing tiles: O is culled, A is not).
   A back-facing or edge-on (ambiguous) alpha face and its O face are drawn in their original place between sorted
   sub-runs. Depth ties
   between different tiles are not excluded by construction; bit 32768 checks the result instead: on every 8th
   sorted run it draws the run both ways into an offscreen framebuffer with the window's depth size, from the same
   cleared start, reads back color and depth and counts differing pixels. */
#define TS_OPAQUE_CALLER ((void *)0x016cfab3)
#define TS_ALPHA_CALLER  ((void *)0x016cfb53)
#define TS_UNK 0xffffffffu
typedef struct { unsigned char blend, cull, atest, dm; GLuint tex; GLenum bs, bd, af; GLclampf ar; } TState;
typedef struct { int start, n; TState st; unsigned char alpha, unsafe, add, full, empty; int x0, y0, x1, y1; } TFace;   /* add..y1: quad runs */

#define ts_active ts_active_flag
static int ts_kind;                                  /* open run: 1 terrain faces, 2 effect/grass quads (quads.c) */
static void *qs_first_caller;
#define QS_SPRITE_CALLER ((void *)0x0184c914)
#define QS_GRASS_CALLER  ((void *)0x016d16bf)
static void qs_run_start(void); static void qs_end_run(const TState *fin); static int qs_cls(void);
#define ts_in_face ts_in_face_flag
static TState ts_v;                                  /* virtual state during a run */
static TFace *ts_f; static int ts_nf, ts_capf;
static Vtx *ts_store; static int ts_capv;
static float ts_mv[16], ts_pr[16]; static GLint ts_front, ts_cullmode;
static long ts_st_runs, ts_st_sorted, ts_st_faces, ts_st_draws, ts_st_back, ts_st_ambig, ts_st_classes, ts_st_pair,
            ts_st_checked, ts_st_bad, ts_st_badpx, ts_st_verr;
static long long ts_tot_checked, ts_tot_bad;

static int ts_same_class(const TState *a, const TState *b)
{
    /* the blend function matters only with blending on, the alpha function only with the alpha test on */
    return a->blend == b->blend && a->cull == b->cull && a->atest == b->atest && a->dm == b->dm &&
           (a->blend != 2 || (a->bs == b->bs && a->bd == b->bd)) && (a->atest != 2 || (a->af == b->af && a->ar == b->ar));
}
static void ts_real(TState *s)
{
    s->blend = cap_cache[0][GL_BLEND]; s->cull = cap_cache[0][GL_CULL_FACE]; s->atest = cap_cache[0][GL_ALPHA_TEST];
    s->dm = depth_mask_ok ? (depth_mask ? 2 : 1) : 0; s->tex = tex_cache[0];
    s->bs = blend_ok ? blend_s : TS_UNK; s->bd = blend_ok ? blend_d : TS_UNK;   /* unknown until the client sets it */
    s->af = alpha_ok ? alpha_func : TS_UNK; s->ar = alpha_ok ? alpha_ref : 0.0f;
}
/* Set the real GL state (and mugl's caches) to *w. */
static void ts_apply(const TState *w)
{
    TState r; ts_real(&r);
    if (r.blend != w->blend) { if (w->blend == 2) R(glEnable, PFN1u)(GL_BLEND); else R(glDisable, PFN1u)(GL_BLEND); cap_cache[0][GL_BLEND] = w->blend; }
    if (r.cull != w->cull) { if (w->cull == 2) R(glEnable, PFN1u)(GL_CULL_FACE); else R(glDisable, PFN1u)(GL_CULL_FACE); cap_cache[0][GL_CULL_FACE] = w->cull; }
    if (r.atest != w->atest) { if (w->atest == 2) R(glEnable, PFN1u)(GL_ALPHA_TEST); else R(glDisable, PFN1u)(GL_ALPHA_TEST); cap_cache[0][GL_ALPHA_TEST] = w->atest; }
    if (r.dm != w->dm) { R(glDepthMask, PFNdm)(w->dm == 2); depth_mask = w->dm == 2; }
    if (w->bs != TS_UNK && (r.bs != w->bs || r.bd != w->bd)) { R(glBlendFunc, PFN2u)(w->bs, w->bd); blend_s = w->bs; blend_d = w->bd; blend_ok = 1; }
    if (w->af != TS_UNK && (r.af != w->af || r.ar != w->ar)) { R(glAlphaFunc, PFNaf)(w->af, w->ar); alpha_func = w->af; alpha_ref = w->ar; alpha_ok = 1; }
    if (!tex_ok[0] || r.tex != w->tex) { R(glBindTexture, PFNbt)(GL_TEXTURE_2D, w->tex); tex_cache[0] = w->tex; tex_ok[0] = 1; }
}
/* Can a run start now? Needs every tracked state known, texture unit 0, filtering caches valid. */
static int ts_can_start(void)
{
    return active_unit == 0 && cap_cache[0][GL_BLEND] && cap_cache[0][GL_CULL_FACE] && cap_cache[0][GL_ALPHA_TEST] &&
           depth_mask_ok && tex_ok[0];
}
static void ts_end(void);
/* glBegin hook: 1 = taken as a terrain face. */
static int ts_glbegin(GLenum mode, void *ret)
{
    int terrain = mode == GL_TRIANGLE_FAN && (ret == TS_OPAQUE_CALLER || ret == TS_ALPHA_CALLER);
    /* v7.4: effect sprite and grass quads (quads.c); GL_QUADS become triangles only under smooth shading */
    int quads = qs_on_flag && mode == GL_QUADS && shade_model == GL_SMOOTH && (ret == QS_SPRITE_CALLER || ret == QS_GRASS_CALLER);
    int kind = terrain && ts_on_flag ? 1 : quads ? 2 : 0;
    if (!kind || (ts_active && kind != ts_kind)) { if (ts_active) ts_end(); if (!kind) return 0; }
    if (!ts_active) {
        if (!ts_can_start()) return 0;
        flush_pending();
        ts_real(&ts_v); ts_nf = 0; vcount = 0; set_t = set_c = set_n = 0; ts_active = 1; ts_kind = kind;
        R(glGetFloatv, PFNget)(GL_MODELVIEW_MATRIX, ts_mv); R(glGetFloatv, PFNget)(GL_PROJECTION_MATRIX, ts_pr);
        ((void (WINAPI *)(GLenum, GLint *))real_glGetIntegerv)(GL_FRONT_FACE, &ts_front);
        ((void (WINAPI *)(GLenum, GLint *))real_glGetIntegerv)(GL_CULL_FACE_MODE, &ts_cullmode);
        if (kind == 2) { qs_first_caller = ret; qs_run_start(); }
    }
    ensure_known();
    if (ts_nf == ts_capf) { ts_capf = ts_capf ? ts_capf * 2 : 4096; ts_f = realloc(ts_f, sizeof(TFace) * ts_capf); }
    TFace *f = &ts_f[ts_nf]; f->start = vcount; f->st = ts_v; f->alpha = ret == TS_ALPHA_CALLER; f->unsafe = 0;
    cur_mode = mode; block_start = vcount; mugl_in_begin = 1; pending = 0; ts_in_face = 1;
    update_busy();
    return 1;
}
static void ts_glend(void)
{
    mugl_in_begin = 0; ts_in_face = 0; st_blocks++; st_verts += vcount - block_start;
    st_modes[cur_mode]++; st_modeverts[cur_mode] += vcount - block_start;
    convert_open_block();
    ts_f[ts_nf].n = vcount - ts_f[ts_nf].start; ts_nf++;
    update_busy();
}
/* Virtual state calls during a run; return 1 when handled. */
static int ts_cap(GLenum cap, int on)
{
    if (!ts_active || ts_in_face) return 0;
    unsigned char v = on ? 2 : 1;
    if (cap == GL_BLEND) ts_v.blend = v; else if (cap == GL_CULL_FACE) ts_v.cull = v; else if (cap == GL_ALPHA_TEST) ts_v.atest = v;
    else return 0;
    return 1;
}
static int ts_tex(GLenum target, GLuint tex) { if (!ts_active || ts_in_face || target != GL_TEXTURE_2D || active_unit != 0) return 0; ts_v.tex = tex; return 1; }
static int ts_blendfunc(GLenum s, GLenum d) { if (!ts_active || ts_in_face) return 0; ts_v.bs = s; ts_v.bd = d; return 1; }
static int ts_depthmask(GLboolean m) { if (!ts_active || ts_in_face) return 0; ts_v.dm = m ? 2 : 1; return 1; }
static int ts_alphafunc(GLenum f, GLclampf r) { if (!ts_active || ts_in_face) return 0; ts_v.af = f; ts_v.ar = r; return 1; }

/* Facing of every triangle of an alpha face: NULL = all front-facing, else the reason counter to bump. The window-space
   orientation of a triangle (also of its visible part when it crosses the near plane) has the sign of the determinant
   of its clip-space (x, y, w) rows (homogeneous rasterization), so no perspective divide or near-plane case is
   needed. Determinants that are tiny relative to the row lengths count as ambiguous (edge-on). */
static long *ts_facing(const Vtx *v, int n)
{
    for (int t = 0; t + 2 < n; t += 3) {
        double m[3][3];
        for (int k = 0; k < 3; k++) {
            const float *p = v[t + k].v; double e[4];
            for (int r = 0; r < 4; r++) e[r] = (double)ts_mv[r] * p[0] + (double)ts_mv[4 + r] * p[1] + (double)ts_mv[8 + r] * p[2] + ts_mv[12 + r];
            double c[4];
            for (int r = 0; r < 4; r++) c[r] = ts_pr[r] * e[0] + ts_pr[4 + r] * e[1] + ts_pr[8 + r] * e[2] + ts_pr[12 + r] * e[3];
            m[k][0] = c[0]; m[k][1] = c[1]; m[k][2] = c[3];
        }
        double det = m[0][0] * (m[1][1] * m[2][2] - m[2][1] * m[1][2]) - m[0][1] * (m[1][0] * m[2][2] - m[2][0] * m[1][2]) +
                     m[0][2] * (m[1][0] * m[2][1] - m[2][0] * m[1][1]);
        double l = 1.0;
        for (int k = 0; k < 3; k++) l *= sqrt(m[k][0] * m[k][0] + m[k][1] * m[k][1] + m[k][2] * m[k][2]);
        if (fabs(det) <= 1e-6 * l) return &ts_st_ambig;
        int front = (det > 0) == (ts_front == GL_CCW);
        if (!front) return &ts_st_back;
    }
    return NULL;
}
static void ts_draw_group(const int *idx, int n)
{
    vcount = 0;
    for (int i = 0; i < n; i++) {
        const TFace *f = &ts_f[idx[i]];
        if (vcount + f->n > vcap) { vcap = (vcount + f->n) * 2; vb = realloc(vb, sizeof(Vtx) * vcap); }
        memcpy(&vb[vcount], &ts_store[f->start], sizeof(Vtx) * f->n); vcount += f->n;
    }
    if (!vcount) return;
    set_t = set_c = set_n = 1; batch_mode = GL_TRIANGLES; batch_cls = ts_kind == 2 ? qs_cls() : DC_TERRAIN; submit_batch(); ts_st_draws++;
}
static int *ts_order; static int ts_capo;
/* Original order, consecutive faces with identical state merged (what mugl did before). */
static void ts_emit_original(void)
{
    int i = 0;
    while (i < ts_nf) {
        int j = i; while (j < ts_nf && !memcmp(&ts_f[j].st, &ts_f[i].st, sizeof(TState))) j++;
        ts_apply(&ts_f[i].st);
        for (int k = i; k < j; k++) ts_order[k - i] = k;
        ts_draw_group(ts_order, j - i);
        i = j;
    }
}
static unsigned char *ts_done; static int ts_capd;
/* Faces [a, b): all O faces grouped by texture in first-use order, then all A faces likewise. */
static void ts_emit_sorted(int a, int b)
{
    if (ts_capd < ts_nf) { ts_capd = ts_nf * 2 + 16; ts_done = realloc(ts_done, ts_capd); }
    memset(ts_done + a, 0, b - a);
    for (int pass = 0; pass < 2; pass++)
        for (int i = a; i < b; i++) {
            if (ts_done[i] || ts_f[i].alpha != pass) continue;
            GLuint tex = ts_f[i].st.tex; int n = 0;
            for (int k = i; k < b; k++)
                if (!ts_done[k] && ts_f[k].alpha == pass && ts_f[k].st.tex == tex) { ts_order[n++] = k; ts_done[k] = 1; }
            ts_apply(&ts_f[i].st);
            ts_draw_group(ts_order, n);
        }
}
/* The sorted plan: an unsafe pair (an A face that may lack its O face underneath, and that O face) is drawn in its
   original place between sorted sub-runs, so order changes stay inside sub-runs whose A faces all lie on their O. */
static void ts_emit_plan(void)
{
    int s0 = 0;
    for (int i = 0; i < ts_nf; i++) {
        if (!ts_f[i].unsafe) continue;
        int pair = i - 1;   /* the O face of this A face (pairing checked) */
        ts_emit_sorted(s0, pair);
        for (int k = pair; k <= i; k++) { ts_apply(&ts_f[k].st); ts_order[0] = k; ts_draw_group(ts_order, 1); }
        s0 = i + 1;
    }
    ts_emit_sorted(s0, ts_nf);
}

/* ---- offscreen verification (bit 32768) ---- */
typedef void (WINAPI *PFNgen)(GLsizei, GLuint *);
typedef void (WINAPI *PFNbindfb)(GLenum, GLuint);
typedef void (WINAPI *PFNrbs)(GLenum, GLenum, GLsizei, GLsizei);
typedef void (WINAPI *PFNfbrb)(GLenum, GLenum, GLenum, GLuint);
typedef GLenum (WINAPI *PFNcfs)(GLenum);
typedef void (WINAPI *PFNrp)(GLint, GLint, GLsizei, GLsizei, GLenum, GLenum, void *);
static GLuint ts_fbo, ts_rb[2]; static int ts_fbw, ts_fbh, ts_fbfail; static unsigned char *ts_px[2]; static size_t ts_pxcap;
static PFNbindfb ts_bindfb;
static int ts_fbo_ready(int w, int h)
{
    if (ts_fbfail) return 0;
    if (ts_fbo && ts_fbw == w && ts_fbh == h) return 1;
    PFNgen genfb = (PFNgen)R(wglGetProcAddress, PFNgpa)("glGenFramebuffersEXT"), genrb = (PFNgen)R(wglGetProcAddress, PFNgpa)("glGenRenderbuffersEXT");
    PFNbindfb bindrb = (PFNbindfb)R(wglGetProcAddress, PFNgpa)("glBindRenderbufferEXT");
    PFNrbs rbs = (PFNrbs)R(wglGetProcAddress, PFNgpa)("glRenderbufferStorageEXT");
    PFNfbrb fbrb = (PFNfbrb)R(wglGetProcAddress, PFNgpa)("glFramebufferRenderbufferEXT");
    PFNcfs cfs = (PFNcfs)R(wglGetProcAddress, PFNgpa)("glCheckFramebufferStatusEXT");
    ts_bindfb = (PFNbindfb)R(wglGetProcAddress, PFNgpa)("glBindFramebufferEXT");
    if (!genfb || !genrb || !bindrb || !rbs || !fbrb || !cfs || !ts_bindfb) { ts_fbfail = 1; return 0; }
    GLint dbits = 0; ((void (WINAPI *)(GLenum, GLint *))real_glGetIntegerv)(GL_DEPTH_BITS, &dbits);
    GLenum dfmt = dbits >= 32 ? 0x81A7 /* DEPTH_COMPONENT32 */ : dbits >= 24 ? 0x81A6 /* 24 */ : 0x81A5 /* 16 */;
    if (!ts_fbo) { genfb(1, &ts_fbo); genrb(2, ts_rb); }
    bindrb(0x8D41, ts_rb[0]); rbs(0x8D41, GL_RGBA8, w, h);
    bindrb(0x8D41, ts_rb[1]); rbs(0x8D41, dfmt, w, h);
    bindrb(0x8D41, 0);
    ts_bindfb(0x8D40, ts_fbo);
    fbrb(0x8D40, 0x8CE0 /* COLOR_ATTACHMENT0 */, 0x8D41, ts_rb[0]);
    fbrb(0x8D40, 0x8D00 /* DEPTH_ATTACHMENT */, 0x8D41, ts_rb[1]);
    GLenum st = cfs(0x8D40);
    ts_bindfb(0x8D40, 0);
    if (st != 0x8CD5 /* COMPLETE */) { ts_fbfail = 1; if (st_file) fprintf(st_file, "tsort verify: framebuffer incomplete %x\n", st); return 0; }
    ts_fbw = w; ts_fbh = h;
    if (st_file) fprintf(st_file, "tsort verify: offscreen %dx%d depth bits %d\n", w, h, dbits);
    return 1;
}
static void ts_read(int k, int w, int h)
{
    size_t need = (size_t)w * h * 8;
    if (ts_pxcap < need) { free(ts_px[0]); free(ts_px[1]); ts_px[0] = malloc(need); ts_px[1] = malloc(need); ts_pxcap = need; }
    R(glReadPixels, PFNrp)(0, 0, w, h, GL_RGBA, GL_UNSIGNED_BYTE, ts_px[k]);
    R(glReadPixels, PFNrp)(0, 0, w, h, GL_DEPTH_COMPONENT, GL_UNSIGNED_INT, ts_px[k] + (size_t)w * h * 4);
}
static void ts_emit_plan(void);
static int ts_blit_start(int w, int h);
/* Draw the run in the original order and with plan() offscreen from the same start (cleared, or with blit the
   window's current color and depth), read both back and count differing pixels. */
static long ts_verify_px(const TState *start, void (*plan)(void), int blit, int *used_blit)
{
    GLint vp[4]; ((void (WINAPI *)(GLenum, GLint *))real_glGetIntegerv)(GL_VIEWPORT, vp);
    int w = vp[0] + vp[2], h = vp[1] + vp[3];
    if (w <= 0 || h <= 0 || w > 8192 || h > 8192 || !ts_fbo_ready(w, h)) return -1;
    release_arrays();
    ts_bindfb(0x8D40, ts_fbo);
    TState st0 = *start; GLboolean sc = ((GLboolean (WINAPI *)(GLenum))real_glIsEnabled)(GL_SCISSOR_TEST);
    if (sc) R(glDisable, PFN1u)(GL_SCISSOR_TEST);
    if (used_blit) *used_blit = 0;
    for (int k = 0; k < 2; k++) {
        TState clr = st0; clr.dm = 2; ts_apply(&clr);
        if (!(blit && ts_blit_start(w, h))) R(glClear, PFNpca)(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
        else if (used_blit) *used_blit = 1;
        ts_apply(&st0);
        if (k == 0) ts_emit_original(); else plan();
        release_arrays();
        ts_read(k, w, h);
    }
    if (sc) R(glEnable, PFN1u)(GL_SCISSOR_TEST);
    ts_bindfb(0x8D40, 0);
    long bad = 0; const unsigned *a = (const unsigned *)ts_px[0], *b = (const unsigned *)ts_px[1]; size_t np = (size_t)w * h;
    for (size_t i = 0; i < np; i++) if (a[i] != b[i] || a[np + i] != b[np + i]) bad++;
    ts_apply(&st0);
    return bad;
}
static void ts_verify_run(const TState *start)
{
    long bad = ts_verify_px(start, ts_emit_plan, 0, NULL);
    if (bad < 0) { ts_st_verr++; return; }
    ts_st_checked++; ts_tot_checked++;
    if (bad) { ts_st_bad++; ts_st_badpx += bad; ts_tot_bad++; }
}

/* End of a run: draw it and leave the real state as the original stream would. */
static void ts_end(void)
{
    if (!ts_active) return;
    /* A foreign call inside a face (not seen for these callers): draw the complete faces, then hand the open face back
       to mugl as an ordinary open block under the real state it was begun with, so its fallback replays it. */
    int open_n = 0; Vtx *open_v = NULL;
    if (ts_in_face) {
        open_n = vcount - block_start;
        if (open_n > 0) { open_v = malloc(sizeof(Vtx) * open_n); memcpy(open_v, &vb[block_start], sizeof(Vtx) * open_n); }
        vcount = block_start; ts_in_face = 0; mugl_in_begin = 0;
    }
    ts_active = 0;
    TState fin = ts_v;
    int nv = vcount;
    if (ts_capv < nv) { ts_capv = nv * 2; ts_store = realloc(ts_store, sizeof(Vtx) * ts_capv); }
    memcpy(ts_store, vb, sizeof(Vtx) * nv); vcount = 0; set_t = set_c = set_n = 0;
    if (ts_capo < ts_nf) { ts_capo = ts_nf * 2 + 16; ts_order = realloc(ts_order, sizeof(int) * ts_capo); }
    if (ts_kind == 2) { qs_end_run(&fin); goto reopen; }
    ts_st_runs++; ts_st_faces += ts_nf;
    /* classes: all O faces must share one blend-off class, all A faces one blend-on class */
    int ocls = -1, acls = -1, ok = ts_nf > 0;
    for (int i = 0; i < ts_nf && ok; i++) {
        int *c = ts_f[i].alpha ? &acls : &ocls;
        if (ts_f[i].st.dm != 2 || ts_f[i].st.blend != (ts_f[i].alpha ? 2 : 1)) { ok = 0; break; }
        if (*c < 0) *c = i; else if (!ts_same_class(&ts_f[*c].st, &ts_f[i].st)) ok = 0;
    }
    if (!ok) ts_st_classes++;
    /* every A face must directly follow its own O face (same corner positions), and when the O class culls back
       faces but the A class does not, every A face must be front-facing (else it is drawn without its O face) */
    if (ok && acls >= 0) {
        int need_facing = ocls >= 0 && ts_f[ocls].st.cull == 2 && ts_cullmode == GL_BACK && !(ts_f[acls].st.cull == 2);
        for (int i = 0; i < ts_nf && ok; i++) {
            const TFace *f = &ts_f[i];
            if (!f->alpha) continue;
            const TFace *o = i ? &ts_f[i - 1] : NULL;
            int paired = o && !o->alpha && o->n == f->n;
            for (int k = 0; paired && k < f->n; k++) paired = !memcmp(ts_store[o->start + k].v, ts_store[f->start + k].v, sizeof(float) * 3);
            if (!paired) {
                static int dumped;
                if (st_file && dumped < 4) {
                    dumped++;
                    fprintf(st_file, "tsort pair fail: face %d alpha n=%d prev %s n=%d\n", i, f->n, o ? (o->alpha ? "alpha" : "opaque") : "none", o ? o->n : 0);
                    for (int k = 0; k < f->n && k < 6; k++)
                        fprintf(st_file, "  A %d: %.9g %.9g %.9g | O %.9g %.9g %.9g\n", k, ts_store[f->start + k].v[0], ts_store[f->start + k].v[1], ts_store[f->start + k].v[2],
                                o ? ts_store[o->start + k].v[0] : 0.0, o ? ts_store[o->start + k].v[1] : 0.0, o ? ts_store[o->start + k].v[2] : 0.0);
                }
                ts_st_pair++; ok = 0; break;
            }
            if (need_facing) { long *why = ts_facing(&ts_store[f->start], f->n); if (why) { (*why)++; ts_f[i].unsafe = 1; } }
        }
    }
    TState start = ts_nf ? ts_f[0].st : fin;   /* real state when the run began = state of its first face */
    if (ok) {
        ts_st_sorted++;
        if (ts_verify && (ts_st_sorted & 7) == 1) ts_verify_run(&start);
        ts_emit_plan();
    } else ts_emit_original();
    ts_apply(&fin);
reopen:
    vcount = 0; set_t = set_c = set_n = 0; pending = 0;
    if (open_v || open_n) {
        if (open_n > vcap) { vcap = open_n * 2; vb = realloc(vb, sizeof(Vtx) * vcap); }
        if (open_n) memcpy(vb, open_v, sizeof(Vtx) * open_n);
        free(open_v); vcount = open_n; block_start = 0; cur_mode = GL_TRIANGLE_FAN; batch_mode = GL_TRIANGLES; mugl_in_begin = 1;
    }
    update_busy();
}
static void qs_stats(FILE *f);
static void ts_stats(FILE *f)
{
    qs_stats(f);
    if (!ts_on_flag && !ts_st_runs) return;
    fprintf(f, "tsort: runs=%ld sorted=%ld faces=%ld draws=%ld in-place pairs(back=%ld ambiguous=%ld) fallback(classes=%ld pair=%ld)",
            ts_st_runs, ts_st_sorted, ts_st_faces, ts_st_draws, ts_st_back, ts_st_ambig, ts_st_classes, ts_st_pair);
    if (ts_verify || ts_tot_checked)
        fprintf(f, " verify checked=%ld mismatched_runs=%ld mismatched_px=%ld errors=%ld | total checked=%lld mismatched=%lld",
                ts_st_checked, ts_st_bad, ts_st_badpx, ts_st_verr, ts_tot_checked, ts_tot_bad);
    fprintf(f, "\n");
    ts_st_runs = ts_st_sorted = ts_st_faces = ts_st_draws = ts_st_back =ts_st_ambig = ts_st_classes = ts_st_pair = 0;
    ts_st_checked = ts_st_bad = ts_st_badpx = ts_st_verr = 0;
}

static void ts_end_hook(void) { ts_end(); }
static int ts_begin_hook(GLenum mode, void *ret) { return ts_glbegin(mode, ret); }
static void ts_glend_hook(void) { ts_glend(); }

#include "quads.c"
