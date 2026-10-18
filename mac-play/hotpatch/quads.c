/* Effect-sprite and grass quad batching (hotpatch bit 65536, verify 131072; v7.4). Included by terrain.c.

   Zoomed out (F6 camera) the client draws about 780 effect sprite quads per frame from return address 0x0184c914 and
   about 830 grass quads from 0x016d16bf, each a 4-vertex glBegin(GL_QUADS) block. Between the quads it changes only the
   texture (grass alternates two, sprites cycle through several) and, for sprites, the blend function: a darkening
   quad (ZERO, ONE_MINUS_SRC_COLOR) and an additive one (ONE, ONE) are drawn in turn, so mugl drew about 1,200 tiny
   batches.

   With the bit, such a run is recorded like a terrain run (same virtual state: blending, culling, alpha test, depth
   mask, unit-0 texture, blend and alpha function) and then drawn as batches of faces with identical state. A face may
   move ahead of earlier faces only when it commutes with every face it passes:
     - their window-space bounding boxes (2 pixels of margin; whole window if any vertex has clip w <= 1e-5) do not
       intersect, so no pixel receives fragments from both, or
     - both are additive without depth writes (blend ONE, ONE, blend equation FUNC_ADD for color and alpha, logic op
       off, depth mask off): each then adds its own value to the pixel, and the depth buffer is not changed by either.
   Faces keep their original order inside a batch. Each face joins the latest batch with its state if it commutes with
   all later batches (at most QS_SCAN batches are searched), else it starts a new batch. Every pair of faces whose order
   changes has been checked, so the drawn sequence is reachable from the original by swapping commuting neighbours.
   Additive commutation assumes exact per-pixel addition with clamping in the 8-bit framebuffer; bit 131072 checks it:
   on every 16th run it draws the run in both orders offscreen, starting from a copy of the window's current color and
   depth when the framebuffer blit works (else from a cleared buffer), and counts differing pixels. */
#include <limits.h>
#define QS_SCAN 64
typedef struct { TState st; int x0, y0, x1, y1, head, tail, n, nempty; unsigned char all_add; } QBatch;   /* box of the non-empty faces */
static QBatch *qs_b; static int qs_nb, qs_capb; static int *qs_next; static int qs_capn;
static GLint qs_vp[4]; static int qs_add_ok, qs_depth_clamp;
static long qs_st_empty, qs_st_runs, qs_st_faces, qs_st_orig, qs_st_draws, qs_st_full, qs_st_add, qs_st_checked, qs_st_bad, qs_st_badpx, qs_st_verr, qs_st_blit;
static long long qs_tot_checked, qs_tot_bad;

/* Start of a quad run: viewport, and whether additive faces may commute (blend equations and factors as tracked). */
static void qs_run_start(void)
{
    void (WINAPI *gi)(GLenum, GLint *) = (void (WINAPI *)(GLenum, GLint *))real_glGetIntegerv;
    gi(GL_VIEWPORT, qs_vp);
    GLint eq = 0, eqa = 0, s = 0, d = 0, sa = 0, da = 0;
    gi(0x8009 /* BLEND_EQUATION_RGB */, &eq); gi(0x883D /* BLEND_EQUATION_ALPHA */, &eqa);
    gi(0x80C9 /* BLEND_SRC_RGB */, &s); gi(0x80C8 /* BLEND_DST_RGB */, &d); gi(0x80CB /* BLEND_SRC_ALPHA */, &sa); gi(0x80CA /* BLEND_DST_ALPHA */, &da);
    GLboolean lo = ((GLboolean (WINAPI *)(GLenum))real_glIsEnabled)(GL_COLOR_LOGIC_OP);
    qs_depth_clamp = ((GLboolean (WINAPI *)(GLenum))real_glIsEnabled)(0x864F /* DEPTH_CLAMP */) != 0;
    qs_add_ok = eq == 0x8006 && eqa == 0x8006 && !lo && blend_ok && (GLenum)s == blend_s && (GLenum)d == blend_d && sa == s && da == d;
}
/* Conservative window-space pixel box of a face. empty: every vertex lies outside one clip plane (x, y or w with a
   relative margin), so the face produces no fragment and commutes with everything. Otherwise each triangle is clipped
   to the near plane (z >= -w; skipped, and the face made unbounded, when depth clamping is on) and the clipped
   vertices are projected; full = may touch any pixel (a clipped vertex with w <= 1e-5, or huge coordinates). */
static void qs_bbox(TFace *f, const double *mvp)
{
    double x0 = 1e300, y0 = 1e300, x1 = -1e300, y1 = -1e300;
    unsigned all_out = 31;
    f->full = 0; f->empty = 0;
    for (int t = 0; t + 2 < f->n; t += 3) {
        double c[3][4]; double d[3];
        for (int k = 0; k < 3; k++) {
            const float *p = ts_store[f->start + t + k].v;
            for (int r = 0; r < 4; r++) c[k][r] = mvp[r] * p[0] + mvp[4 + r] * p[1] + mvp[8 + r] * p[2] + mvp[12 + r];
            double m = 1e-5 * (1.0 + fabs(c[k][0]) + fabs(c[k][1]) + fabs(c[k][3]));
            unsigned o = (c[k][0] > c[k][3] + m) | (c[k][0] < -c[k][3] - m) << 1 | (c[k][1] > c[k][3] + m) << 2 |
                         (c[k][1] < -c[k][3] - m) << 3 | (c[k][3] < -m) << 4;
            all_out &= o;
            d[k] = c[k][2] + c[k][3];   /* near plane: inside when >= 0 */
        }
        if (qs_depth_clamp) { f->full = 1; continue; }
        /* Sutherland-Hodgman against the near plane: at most 4 points */
        double q[4][4]; int nq = 0;
        for (int k = 0; k < 3; k++) {
            int k2 = (k + 1) % 3;
            if (d[k] >= 0) memcpy(q[nq++], c[k], sizeof c[k]);
            if ((d[k] >= 0) != (d[k2] >= 0)) {
                double a = d[k] / (d[k] - d[k2]);
                for (int r = 0; r < 4; r++) q[nq][r] = c[k][r] + a * (c[k2][r] - c[k][r]);
                nq++;
            }
        }
        for (int k = 0; k < nq; k++) {
            if (!(q[k][3] > 1e-5)) { f->full = 1; break; }
            double wx = qs_vp[0] + (q[k][0] / q[k][3] + 1.0) * 0.5 * qs_vp[2], wy = qs_vp[1] + (q[k][1] / q[k][3] + 1.0) * 0.5 * qs_vp[3];
            if (wx < x0) x0 = wx;
            if (wx > x1) x1 = wx;
            if (wy < y0) y0 = wy;
            if (wy > y1) y1 = wy;
        }
    }
    if (all_out && f->n >= 3) { f->empty = 1; f->full = 0; return; }
    if (f->full) return;
    if (x0 > x1) { f->empty = 1; return; }   /* every triangle entirely behind the near plane */
    if (!(x0 > -1e7 && x1 < 1e7 && y0 > -1e7 && y1 < 1e7)) { f->full = 1; return; }
    f->x0 = (int)floor(x0) - 2; f->x1 = (int)ceil(x1) + 2; f->y0 = (int)floor(y0) - 2; f->y1 = (int)ceil(y1) + 2;
}
static int qs_disjoint(const TFace *f, const QBatch *b)
{
    if (f->empty || b->n == b->nempty) return 1;
    return !f->full && (f->x1 < b->x0 || b->x1 < f->x0 || f->y1 < b->y0 || b->y1 < f->y0);
}
static void qs_plan(void)
{
    double mvp[16];
    for (int c = 0; c < 4; c++) for (int r = 0; r < 4; r++) {
        double v = 0; for (int k = 0; k < 4; k++) v += (double)ts_pr[k * 4 + r] * ts_mv[c * 4 + k]; mvp[c * 4 + r] = v;
    }
    if (qs_capn < ts_nf) { qs_capn = ts_nf * 2 + 16; qs_next = realloc(qs_next, sizeof(int) * qs_capn); }
    qs_nb = 0;
    for (int i = 0; i < ts_nf; i++) {
        TFace *f = &ts_f[i];
        qs_bbox(f, mvp);
        f->add = qs_add_ok && f->st.blend == 2 && f->st.bs == GL_ONE && f->st.bd == GL_ONE && f->st.dm == 1;
        qs_st_full += f->full; qs_st_add += f->add; qs_st_empty += f->empty;
        int join = -1;
        for (int k = qs_nb - 1; k >= 0 && k >= qs_nb - QS_SCAN; k--) {
            QBatch *b = &qs_b[k];
            if (!memcmp(&b->st, &f->st, sizeof(TState))) { join = k; break; }
            if (!(qs_disjoint(f, b) || (f->add && b->all_add))) break;
        }
        if (join < 0) {
            if (qs_nb == qs_capb) { qs_capb = qs_capb ? qs_capb * 2 : 256; qs_b = realloc(qs_b, sizeof(QBatch) * qs_capb); }
            QBatch *b = &qs_b[qs_nb++]; b->st = f->st; b->head = b->tail = -1; b->n = b->nempty = 0; b->all_add = 1;
            b->x0 = 1; b->x1 = 0; b->y0 = 1; b->y1 = 0;   /* empty box */
            join = qs_nb - 1;
        }
        QBatch *b = &qs_b[join];
        qs_next[i] = -1; if (b->tail >= 0) qs_next[b->tail] = i; else b->head = i; b->tail = i; b->n++;
        if (f->empty) { b->nempty++; continue; }   /* draws nothing: no effect on the box or the additive flag */
        b->all_add &= f->add;
        if (f->full) { b->x0 = INT_MIN / 2; b->x1 = INT_MAX / 2; b->y0 = INT_MIN / 2; b->y1 = INT_MAX / 2; }
        else if (b->n - b->nempty == 1) { b->x0 = f->x0; b->x1 = f->x1; b->y0 = f->y0; b->y1 = f->y1; }
        else { if (f->x0 < b->x0) b->x0 = f->x0; if (f->x1 > b->x1) b->x1 = f->x1; if (f->y0 < b->y0) b->y0 = f->y0; if (f->y1 > b->y1) b->y1 = f->y1; }
    }
}
static void qs_emit_plan(void)
{
    for (int k = 0; k < qs_nb; k++) {
        const QBatch *b = &qs_b[k]; int n = 0;
        for (int i = b->head; i >= 0; i = qs_next[i]) ts_order[n++] = i;
        ts_apply(&b->st);
        ts_draw_group(ts_order, n);
    }
}
static int qs_cls(void) { return qs_first_caller == QS_SPRITE_CALLER ? DC_SPRITE : DC_GRASS; }
/* End of a quad run (from ts_end, faces in ts_f/ts_store): plan, optional verify, draw, final state. */
static void qs_end_run(const TState *fin)
{
    qs_st_runs++; qs_st_faces += ts_nf;
    for (int i = 0; i < ts_nf; i++) if (!i || memcmp(&ts_f[i].st, &ts_f[i - 1].st, sizeof(TState))) qs_st_orig++;
    if (ts_nf) {
        TState start = ts_f[0].st;
        int saved_cls = batch_cls; long d0 = ts_st_draws;
        qs_plan();
        batch_cls = qs_cls();
        if (qs_verify && (qs_st_runs & 15) == 1) {
            int blit = 0; long bad = ts_verify_px(&start, qs_emit_plan, 1, &blit);
            if (bad < 0) qs_st_verr++;
            else { qs_st_checked++; qs_tot_checked++; qs_st_blit += blit; if (bad) { qs_st_bad++; qs_st_badpx += bad; qs_tot_bad++; } }
        }
        long d1 = ts_st_draws; qs_emit_plan(); qs_st_draws += ts_st_draws - d1; ts_st_draws = d0;
        batch_cls = saved_cls;
    }
    ts_apply(fin);
}
/* Window color+depth into the verification framebuffer (bound as GL_FRAMEBUFFER_EXT); 0 = not available. */
typedef void (WINAPI *PFNblit)(GLint, GLint, GLint, GLint, GLint, GLint, GLint, GLint, GLbitfield, GLenum);
static PFNblit qs_blitfn; static int qs_blit_fail;
static int ts_blit_start(int w, int h)
{
    if (qs_blit_fail) return 0;
    if (!qs_blitfn) { qs_blitfn = (PFNblit)R(wglGetProcAddress, PFNgpa)("glBlitFramebufferEXT"); if (!qs_blitfn) { qs_blit_fail = 1; return 0; } }
    GLenum (WINAPI *ge)(void) = (GLenum (WINAPI *)(void))real_glGetError;
    while (ge() != GL_NO_ERROR) {}   /* diagnostic only; glGetError does not occur in the traced client frames */
    ts_bindfb(0x8CA8 /* READ_FRAMEBUFFER */, 0); ts_bindfb(0x8CA9 /* DRAW_FRAMEBUFFER */, ts_fbo);
    qs_blitfn(0, 0, w, h, 0, 0, w, h, GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT, GL_NEAREST);
    ts_bindfb(0x8D40, ts_fbo);
    GLenum e = ge();
    if (e != GL_NO_ERROR) { qs_blit_fail = 1; if (st_file) fprintf(st_file, "qsort verify: blit failed %x, using cleared buffers\n", e); return 0; }
    return 1;
}
static void qs_stats(FILE *f)
{
    if (!qs_on_flag && !qs_st_runs) return;
    fprintf(f, "qsort: runs=%ld faces=%ld state-groups=%ld draws=%ld unbounded=%ld offscreen=%ld additive=%ld", qs_st_runs, qs_st_faces, qs_st_orig, qs_st_draws, qs_st_full, qs_st_empty, qs_st_add);
    if (qs_verify || qs_tot_checked)
        fprintf(f, " verify checked=%ld (from window copy %ld) mismatched_runs=%ld mismatched_px=%ld errors=%ld | total checked=%lld mismatched=%lld",
                qs_st_checked, qs_st_blit, qs_st_bad, qs_st_badpx, qs_st_verr, qs_tot_checked, qs_tot_bad);
    fprintf(f, "\n");
    qs_st_empty = qs_st_runs = qs_st_faces = qs_st_orig = qs_st_draws = qs_st_full = qs_st_add = qs_st_checked = qs_st_bad = qs_st_badpx = qs_st_verr = qs_st_blit = 0;
}
