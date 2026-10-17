/* meshdraw.c: native replacement for the per-corner triangle loop of the client's mesh draw routine
   0x012b8d1d (thiscall, 11 stack args, ret 0x2c). Included by mugl.c (after xform.c).

   The loop 0x012ba8a0..0x012bb229 is entered right after glBegin(GL_TRIANGLES) at 0x012ba893 and left at
   the glEnd call 0x012bb22e. We patch the 7 bytes at 0x012ba899 (nop; and [ebp-0x74],0; jmp 0x12ba8a7)
   with a jmp to md_entry, which calls md_hook(ebp). md_hook returns 1 when it emitted the whole loop
   natively (md_entry then jumps to the glEnd call) or 0 to run the original loop (md_entry re-executes the
   replaced instructions and jumps to 0x12ba8a7). Full decode: meshdraw-notes.md. Summary:

   Frame (ebp-relative) used by the loop:
     [ebp-0x10] model (this)          [ebp+0x08] mesh index i (>= 0)      [ebp+0x0c] render flags
     [ebp-0x20] mesh = model[0x28]+32i [ebp+0x10] transformed vertex base [ebp+0x1c] alpha (float)
     [ebp-0x38] draw mode              [ebp+0x28] u offset, [ebp+0x2c] v offset (floats)
     [ebp-0x31] byte: apply UV offset  [ebp-0x21] byte: per-normal light colours
   Mesh: +0x0a int16 triangle count, +0x14 texcoord array (2 floats), +0x18 triangle array (stride 0x24).
   Triangle: +0x00 int8 corner count, +0x02 int16 v[4], +0x0a int16 n[4], +0x12 int16 t[4].
   Vertex of corner: V = vbase + i*0x2bf20 + v*12. Light colour: 0x089c2120 + i*0x2bf20 + n*12 (3 floats).
   Normal-indexed texcoords: 0x072acfd8 + n*8. Object colour: model+0x54 (3 floats). Origin: model+0x78.
   K = 0.99f (0x01a82fe0). "colour(c)" = alpha >= K ? glColor3fv(c) : glColor4f(c[0], c[1], c[2], alpha).

   Per corner, by mode:
     2:                  glTexCoord2f(tc.u (+uoff), tc.v (+voff)) [offset if byte -0x31];
                         if byte -0x21: colour(light colour)
     4:                  colour(model+0x54); glTexCoord2f(nt.u, nt.v)
     0x1000, 0x80000,
     0x100000:           colour(model+0x54); glTexCoord2f(nt.u + uoff, nt.v + voff)
     0x8000:             mutates alpha (stack arg) and model+0x54 through client calls -> original loop
     anything else (1, 0x40): no attributes
   then the vertex, by flags (first match):
     0x20:     L = V - origin; L.x = ((L.x + 2000) * L.z) / (L.z - 4000) + L.x; L.z = 5; L += origin;
               glVertex3fv(L)                                     (planar shadow projection)
     0x400:    time/sin wobble through client sin() -> original loop
     0x200000: skip the vertex (attributes already sent) if voff > z of corners v[0], v[1] and v[2]
     else:     glVertex3fv(V)
   Constants are read from the client image (same binary32 values); single float operations in the original
   order, built with -msse2 -mfpmath=sse -ffp-contract=off.
   Side effects besides GL calls: only frame locals that nothing reads after the loop (the post-glEnd code
   uses -0x10, -0x20, -0x44, -0x12c, -0xfc). The accessor helpers it calls (0xcfc94a self, 0xcfc922 index)
   are pure. The mode 0x8000 / flag 0x400 paths (client calls with side effects) are left to the original.

   Mask bits: 32 install (calls through the import slots), 128 append straight into mugl's batch, 256 also replace
   the per-normal light precompute, 512 routine timer, 8192 enable the unverified 0x20/0x200000 vertex paths
   (otherwise those meshes run the original loop). Notes and results: meshdraw-notes.md.
   Bit 64 verifies: our loop runs record-only, then the IAT slots used by
   the loop are pointed at recorders and the original loop runs; at its glEnd both call streams (op + float
   bits) are compared, the slots restored and the real glEnd called. */
#include <stdint.h>
#include <xmmintrin.h>

#define MD_PATCH 0x012ba899
#define MD_RESUME 0x012ba8a7
#define MD_GLEND 0x012bb22e
/* Original bytes of the three patch sites (md_orig[7] at MD_PATCH: nop; and [ebp-0x74],0; jmp 0x12ba8a7; md_lorig[6] at
   MD_LPATCH; md_prologue[10] at MD_ENTRY) are generated locally into an ignored header from the owner-supplied pristine
   dump; targets.json "meshdraw_sites" pins their addresses, lengths and SHA-256. The compile-only build has zero tables. */
#include "meshdraw-orig.h"

#define MD_IAT_C4 0x01a7c754
#define MD_IAT_END 0x01a7c760
#define MD_IAT_C3V 0x01a7c770
#define MD_IAT_TC 0x01a7c774
#define MD_IAT_V3V 0x01a7c778
typedef void (WINAPI *md_tc_fn)(GLfloat, GLfloat);
typedef void (WINAPI *md_c4_fn)(GLfloat, GLfloat, GLfloat, GLfloat);
typedef void (WINAPI *md_fv_fn)(const GLfloat *);
typedef void (WINAPI *md_v_fn)(void);
#define MD_SLOT(a) (*(void *volatile *)(uintptr_t)(a))

/* ---- call recording (verify) ---- */
typedef struct { uint32_t op; float f[4]; } MdRec;
enum { MD_TC = 1, MD_C3, MD_C4, MD_V };
static MdRec *md_a, *md_b; static int md_na, md_nb, md_capa, md_capb;
static void md_push(MdRec **buf, int *n, int *cap, int op, float a, float b, float c, float d)
{
    if (*n >= *cap) { int nc = *cap ? *cap * 2 : 1 << 14; MdRec *nb = realloc(*buf, sizeof(MdRec) * nc); if (!nb) return; *buf = nb; *cap = nc; }
    MdRec *r = &(*buf)[(*n)++]; memset(r, 0, sizeof *r); r->op = op; r->f[0] = a; r->f[1] = b; r->f[2] = c; r->f[3] = d;
}

/* ---- stats ---- */
static long md_calls, md_native, md_fallback, md_checked, md_bad;          /* per stats period */
static long long md_tot_calls, md_tot_native, md_tot_checked, md_tot_bad, md_tot_corners, md_tot_checked_corners;
static long long md_fb_mode8000, md_fb_flag400, md_fb_other, md_fb_untested;
static int md_untested;   /* hotpatch bit 8192: also run the (unverified) 0x20 shadow / 0x200000 cull vertex paths natively */
static long long md_rt_ticks; static long md_rt_calls;   /* whole-routine timer */
static long long md_seg_entry, md_seg_hook0, md_seg_hook1, md_seg_pre, md_seg_loop, md_seg_post; static long md_seg_n; static int md_seg_on;
enum { MDM_1, MDM_2, MDM_4, MDM_40, MDM_1000, MDM_8000, MDM_80000, MDM_100000, MDM_OTHER, MDM_N };
static const char *md_mode_names[MDM_N] = {"1", "2", "4", "40", "1000", "8000", "80000", "100000", "other"};
static long long md_mode_cnt[MDM_N], md_vk_cnt[4];                       /* meshes by mode / vertex kind */
static const char *md_vk_names[4] = {"plain", "shadow20", "wobble400", "cull200000"};
static int md_mode_idx(int32_t m)
{
    switch (m) { case 1: return MDM_1; case 2: return MDM_2; case 4: return MDM_4; case 0x40: return MDM_40; case 0x1000: return MDM_1000;
                 case 0x8000: return MDM_8000; case 0x80000: return MDM_80000; case 0x100000: return MDM_100000; default: return MDM_OTHER; }
}

/* ---- the loop ---- */
#define MD_K(a) (*(const float *)(uintptr_t)(a))
/* Output of md_run: MD_OUT_CALL calls GL through the client's import slots; MD_OUT_REC appends the calls to
   md_a (verify); MD_OUT_VTX does what mugl's own glTexCoord2f/glColor3fv/glColor4f/glVertex3fv do inside a
   batched glBegin block (track current texcoord/colour, append a Vtx per vertex) directly into vo. */
enum { MD_OUT_CALL, MD_OUT_REC, MD_OUT_VTX };
typedef struct { Vtx **buf; int *count, *cap; GLfloat t[2], c[4], n[3]; int set_t, set_c; } MdVtxOut;
static long md_run(uint8_t *bp, int out, MdVtxOut *vo)
{
    uint8_t *model = *(uint8_t **)(bp - 0x10);
    const int32_t mi = *(int32_t *)(bp + 0x08);
    const uint32_t flags = *(uint32_t *)(bp + 0x0c);
    uint8_t *vbase = *(uint8_t **)(bp + 0x10) + mi * 0x2bf20;
    const float alpha = *(float *)(bp + 0x1c), uoff = *(float *)(bp + 0x28), voff = *(float *)(bp + 0x2c);
    const uint8_t *mesh = *(uint8_t **)(bp - 0x20);
    const int32_t mode = *(int32_t *)(bp - 0x38);
    const int uvflag = *(uint8_t *)(bp - 0x31) != 0, light = *(uint8_t *)(bp - 0x21) != 0;
    const int ntri = *(const int16_t *)(mesh + 0x0a);
    const uint8_t *tris = *(uint8_t *const *)(mesh + 0x18);
    const float *tcs = *(const float *const *)(mesh + 0x14);
    const float *ltab = (const float *)(uintptr_t)(0x089c2120 + mi * 0x2bf20);
    const float *ntab = (const float *)(uintptr_t)0x072acfd8;
    const float *mcol = (const float *)(model + 0x54), *origin = (const float *)(model + 0x78);
    const int col3 = alpha >= MD_K(0x01a82fe0);
    const float calpha = col3 ? 1.0f : alpha;   /* glColor3fv sets alpha 1 */
    const int vk = (flags & 0x20) ? 1 : (flags & 0x200000) ? 3 : 0;   /* 0x400 never reaches here */
    const float k2000 = MD_K(0x01a802d8), k4000 = MD_K(0x01a9ff0c), k5 = MD_K(0x01a7e4cc);
    md_tc_fn tc = (md_tc_fn)MD_SLOT(MD_IAT_TC);
    md_c4_fn c4 = (md_c4_fn)MD_SLOT(MD_IAT_C4);
    md_fv_fn c3v = (md_fv_fn)MD_SLOT(MD_IAT_C3V), v3v = (md_fv_fn)MD_SLOT(MD_IAT_V3V);
    int kind;   /* attribute kind: 0 none, 1 mode 2, 2 mode 4, 3 mode 4 + uv offset */
    switch (mode) { case 2: kind = 1; break; case 4: kind = 2; break; case 0x1000: case 0x80000: case 0x100000: kind = 3; break; default: kind = 0; }
    long corners = 0;
    /* direct-append state (registers) */
    GLfloat vt0 = 0, vt1 = 0, vc0 = 0, vc1 = 0, vc2 = 0, vc3 = 0, vn0 = 0, vn1 = 0, vn2 = 0; int vst = 0, vsc = 0;
    Vtx *obuf = NULL; int ocount = 0, ocap = 0;
    if (out == MD_OUT_VTX) {
        vt0 = vo->t[0]; vt1 = vo->t[1]; vc0 = vo->c[0]; vc1 = vo->c[1]; vc2 = vo->c[2]; vc3 = vo->c[3];
        vn0 = vo->n[0]; vn1 = vo->n[1]; vn2 = vo->n[2]; obuf = *vo->buf; ocount = *vo->count; ocap = *vo->cap;
    }
#define MD_TCC(s, t) do { const float s_ = (s), t_ = (t); \
        if (out == MD_OUT_VTX) { vt0 = s_; vt1 = t_; vst = 1; } \
        else if (out == MD_OUT_REC) md_push(&md_a, &md_na, &md_capa, MD_TC, s_, t_, 0, 0); else tc(s_, t_); } while (0)
#define MD_COLOR(c) do { const float *c_ = (c); \
        if (out == MD_OUT_VTX) { vc0 = c_[0]; vc1 = c_[1]; vc2 = c_[2]; vc3 = calpha; vsc = 1; } \
        else if (col3) { if (out == MD_OUT_REC) md_push(&md_a, &md_na, &md_capa, MD_C3, c_[0], c_[1], c_[2], 0); else c3v(c_); } \
        else { if (out == MD_OUT_REC) md_push(&md_a, &md_na, &md_capa, MD_C4, c_[0], c_[1], c_[2], alpha); else c4(c_[0], c_[1], c_[2], alpha); } } while (0)
#define MD_VTX(p) do { const float *p_ = (p); \
        if (out == MD_OUT_VTX) { /* capacity reserved below; three-part vector store of the 48-byte Vtx */ \
            float *o_ = (float *)&obuf[ocount++]; \
            _mm_storeu_ps(o_, _mm_setr_ps(vt0, vt1, vc0, vc1)); _mm_storeu_ps(o_ + 4, _mm_setr_ps(vc2, vc3, vn0, vn1)); \
            o_[8] = vn2; _mm_storel_pi((__m64 *)(o_ + 9), _mm_loadl_pi(_mm_setzero_ps(), (const __m64 *)p_)); o_[11] = p_[2]; } \
        else if (out == MD_OUT_REC) md_push(&md_a, &md_na, &md_capa, MD_V, p_[0], p_[1], p_[2], 0); else v3v(p_); } while (0)
    if (out == MD_OUT_VTX) {   /* reserve room for every corner of the mesh once (same growth policy as mugl's push_vertex) */
        long need = ocount;
        for (int t = 0; t < ntri; t++) { const int n = *(const int8_t *)(tris + t * 0x24); if (n > 0) need += n; }
        if (need > ocap) {
            int nc = ocap ? ocap : 8192; while (nc < need) nc *= 2;
            Vtx *nb = realloc(obuf, sizeof(Vtx) * nc); if (!nb) abort(); obuf = nb; ocap = nc;
        }
    }
    for (int t = 0; t < ntri; t++) {
        const uint8_t *tri = tris + t * 0x24;
        const int n = *(const int8_t *)tri;
        const int16_t *tv = (const int16_t *)(tri + 0x02), *tn = (const int16_t *)(tri + 0x0a), *tt = (const int16_t *)(tri + 0x12);
        for (int j = 0; j < n; j++) {
            const int vi = tv[j];
            corners++;
            switch (kind) {
            case 1: {
                const float *uv = tcs + tt[j] * 2;
                if (uvflag) MD_TCC(uv[0] + uoff, uv[1] + voff); else MD_TCC(uv[0], uv[1]);
                if (light) MD_COLOR(ltab + tn[j] * 3);
                break;
            }
            case 2: { MD_COLOR(mcol); const float *e = ntab + tn[j] * 2; MD_TCC(e[0], e[1]); break; }
            case 3: { MD_COLOR(mcol); const float *e = ntab + tn[j] * 2; MD_TCC(e[0] + uoff, e[1] + voff); break; }
            default: break;
            }
            const float *v = (const float *)(vbase + vi * 12);
            if (vk == 1) {
                float l[3];
                l[0] = v[0] - origin[0]; l[1] = v[1] - origin[1]; l[2] = v[2] - origin[2];
                l[0] = (l[0] + k2000) * l[2] / (l[2] - k4000) + l[0];
                l[2] = k5;
                l[0] = l[0] + origin[0]; l[1] = l[1] + origin[1]; l[2] = l[2] + origin[2];
                MD_VTX(l);
            } else if (vk == 3) {
                const float z0 = ((const float *)(vbase + tv[0] * 12))[2], z1 = ((const float *)(vbase + tv[1] * 12))[2],
                            z2 = ((const float *)(vbase + tv[2] * 12))[2];
                if (voff > z0 && voff > z1 && voff > z2) continue;
                MD_VTX(v);
            } else MD_VTX(v);
        }
    }
#undef MD_TCC
#undef MD_COLOR
#undef MD_VTX
    if (out == MD_OUT_VTX) {
        vo->t[0] = vt0; vo->t[1] = vt1; vo->c[0] = vc0; vo->c[1] = vc1; vo->c[2] = vc2; vo->c[3] = vc3;
        vo->set_t |= vst; vo->set_c |= vsc; *vo->buf = obuf; *vo->count = ocount; *vo->cap = ocap;
    }
    return corners;
}

/* ---- verification recorders (installed in the IAT only while the original loop runs) ---- */
static int md_verify, md_rec;
static void *md_saved[5];   /* real targets of c4, end, c3v, tc, v3v slots */
static void WINAPI md_rec_tc(GLfloat s, GLfloat t) { md_push(&md_b, &md_nb, &md_capb, MD_TC, s, t, 0, 0); ((md_tc_fn)md_saved[3])(s, t); }
static void WINAPI md_rec_c4(GLfloat r, GLfloat g, GLfloat b, GLfloat a) { md_push(&md_b, &md_nb, &md_capb, MD_C4, r, g, b, a); ((md_c4_fn)md_saved[0])(r, g, b, a); }
static void WINAPI md_rec_c3v(const GLfloat *v) { md_push(&md_b, &md_nb, &md_capb, MD_C3, v[0], v[1], v[2], 0); ((md_fv_fn)md_saved[2])(v); }
static void WINAPI md_rec_v3v(const GLfloat *v) { md_push(&md_b, &md_nb, &md_capb, MD_V, v[0], v[1], v[2], 0); ((md_fv_fn)md_saved[4])(v); }
static int32_t md_cur_mode; static uint32_t md_cur_flags; static long md_cur_corners;
static void WINAPI md_rec_end(void);
static void md_slots_set(int rec)
{
    static const uintptr_t sl[5] = {MD_IAT_C4, MD_IAT_END, MD_IAT_C3V, MD_IAT_TC, MD_IAT_V3V};
    void *rp[5] = {(void *)md_rec_c4, (void *)md_rec_end, (void *)md_rec_c3v, (void *)md_rec_tc, (void *)md_rec_v3v};
    for (int k = 0; k < 5; k++) {
        if (rec) { md_saved[k] = MD_SLOT(sl[k]); MD_SLOT(sl[k]) = rp[k]; }
        else MD_SLOT(sl[k]) = md_saved[k];
    }
    md_rec = rec;
}
static void WINAPI md_rec_end(void)
{
    md_slots_set(0);
    int bad = md_na != md_nb, at = -1;
    if (!bad) for (int k = 0; k < md_na; k++) if (memcmp(&md_a[k], &md_b[k], sizeof(MdRec))) { bad = 1; at = k; break; }
    md_checked++; md_tot_checked++; md_tot_checked_corners += md_cur_corners;
    if (bad) {
        md_bad++; md_tot_bad++;
        if (md_tot_bad <= 20 && st_file) {
            fprintf(st_file, "meshdraw MISMATCH mode %#x flags %#x corners %ld: native %d calls, original %d calls", (unsigned)md_cur_mode, (unsigned)md_cur_flags, md_cur_corners, md_na, md_nb);
            if (at >= 0) fprintf(st_file, "; first diff at %d: op %u (%g %g %g %g) vs op %u (%g %g %g %g)", at,
                                 md_a[at].op, md_a[at].f[0], md_a[at].f[1], md_a[at].f[2], md_a[at].f[3], md_b[at].op, md_b[at].f[0], md_b[at].f[1], md_b[at].f[2], md_b[at].f[3]);
            fprintf(st_file, "\n"); fflush(st_file);
        }
    }
    ((md_v_fn)md_saved[1])();
}

/* ---- direct append (bit 128) and its verification ---- */
static int md_direct;
static long long md_tot_direct, md_tot_dchecked, md_tot_dbad;
static Vtx *md_sv; static int md_svn, md_svcap;      /* verify: our vertices for the block */
static MdVtxOut md_vexp; static int md_vstart;       /* verify: expected mugl state after the loop */
static void *md_saved_end;
/* The loop may append straight into mugl's batch only when its calls would reach mugl's own entry points
   while a batched glBegin block is open. */
static int md_direct_ok(void)
{
    return mugl_in_begin && !passthrough &&
           MD_SLOT(MD_IAT_TC) == (void *)mugl_glTexCoord2f && MD_SLOT(MD_IAT_C4) == (void *)mugl_glColor4f &&
           MD_SLOT(MD_IAT_C3V) == (void *)mugl_glColor3fv && MD_SLOT(MD_IAT_V3V) == (void *)mugl_glVertex3fv;
}
static void md_vo_init(MdVtxOut *vo, Vtx **buf, int *count, int *cap)
{
    vo->buf = buf; vo->count = count; vo->cap = cap;
    memcpy(vo->t, cur_t, sizeof vo->t); memcpy(vo->c, cur_c, sizeof vo->c); memcpy(vo->n, cur_n, sizeof vo->n);
    vo->set_t = set_t; vo->set_c = set_c;
}
static void WINAPI md_rec_end_direct(void)
{
    MD_SLOT(MD_IAT_END) = md_saved_end; md_rec = 0;
    int n = vcount - md_vstart;
    int bad = !mugl_in_begin || n != md_svn || (n > 0 && memcmp(&vb[md_vstart], md_sv, sizeof(Vtx) * n)) ||
              memcmp(cur_t, md_vexp.t, sizeof cur_t) || memcmp(cur_c, md_vexp.c, sizeof cur_c) ||
              set_t != md_vexp.set_t || set_c != md_vexp.set_c;
    md_checked++; md_tot_dchecked++; md_tot_checked_corners += md_cur_corners;
    if (bad) {
        md_bad++; md_tot_dbad++;
        if (md_tot_dbad <= 20 && st_file) {
            int at = -1; for (int k = 0; k < n && k < md_svn; k++) if (memcmp(&vb[md_vstart + k], &md_sv[k], sizeof(Vtx))) { at = k; break; }
            fprintf(st_file, "meshdraw DIRECT MISMATCH mode %#x flags %#x: native %d vertices, original %d, first diff %d, set %d%d/%d%d\n",
                    (unsigned)md_cur_mode, (unsigned)md_cur_flags, md_svn, n, at, md_vexp.set_t, md_vexp.set_c, set_t, set_c);
            fflush(st_file);
        }
    }
    ((md_v_fn)md_saved_end)();
}

/* ---- per-normal light colour precompute (bit 256) ----
   0x012b968c..0x012b996c, run when the light byte [ebp-0x21] is set (model[0x50] and i != model[0x94]):
   for n < (int16)mesh[6]: T[n][k] (T = 0x089c2120 + i*0x2bf20, 3 floats per normal), C = model+0x54,
     model[0xcb] == 1: T[n][k] = S[n] * C[k] + K   (S = 0x075a9ee8 + i*0xea60, K = 0x01a7df08 = 0.2f)
     otherwise:        T[n][k] = L[n] * C[k]       (L = [ebp+0x18] + i*0xea60)
   Its frame temporaries (-0x28, -0x114, -0x120, -0xc0.., -0xe4..) are not read outside that loop.
   Patched at 0x012b968c (and [ebp-0x28],0; jmp 0x12b9699) -> md_light_entry; loop exit is 0x012b9971.
   Verify: the native table goes to a scratch copy, the original loop runs, and the copy is compared with the
   real table at the next mesh loop hook of the same model/mesh (env modes scale model+0x54 later, so the
   native side must run at precompute time). */
#define MD_LPATCH 0x012b968c

static long long md_l_native, md_l_normals, md_l_checked, md_l_bad, md_l_dropped;
static float *md_lt; static int md_ltcap;   /* verify scratch */
static int md_lpend, md_lpend_n, md_lpend_i; static uint8_t *md_lpend_model;
static void md_light_run(uint8_t *bp, float *T)
{
    uint8_t *model = *(uint8_t **)(bp - 0x10);
    const int32_t mi = *(int32_t *)(bp + 0x08);
    const uint8_t *mesh = *(uint8_t **)(bp - 0x20);
    const int nn = *(const int16_t *)(mesh + 6);
    const float *C = (const float *)(model + 0x54);
    const float c0 = C[0], c1 = C[1], c2 = C[2];
    if (model[0xcb] == 1) {
        const float *S = (const float *)(uintptr_t)(0x075a9ee8 + mi * 0xea60); const float K = MD_K(0x01a7df08);
        for (int n = 0; n < nn; n++) { const float sn = S[n]; T[n * 3] = sn * c0 + K; T[n * 3 + 1] = sn * c1 + K; T[n * 3 + 2] = sn * c2 + K; }
    } else {
        const float *L = (const float *)(*(uint8_t **)(bp + 0x18) + mi * 0xea60);
        for (int n = 0; n < nn; n++) { const float ln = L[n]; T[n * 3] = ln * c0; T[n * 3 + 1] = ln * c1; T[n * 3 + 2] = ln * c2; }
    }
}
static void md_light_check(uint8_t *bp)   /* called at the mesh loop hook */
{
    if (!md_lpend) return;
    md_lpend = 0;
    if (*(uint8_t **)(bp - 0x10) != md_lpend_model || *(int32_t *)(bp + 0x08) != md_lpend_i) { md_l_dropped++; return; }
    md_l_checked++;
    if (md_lpend_n > 0 && memcmp(md_lt, (void *)(uintptr_t)(0x089c2120 + md_lpend_i * 0x2bf20), md_lpend_n * 12)) {
        md_l_bad++;
        if (md_l_bad <= 20 && st_file) { fprintf(st_file, "meshdraw LIGHT MISMATCH model %p mesh %d normals %d\n", (void *)md_lpend_model, md_lpend_i, md_lpend_n); fflush(st_file); }
    }
}
int md_light_hook(uint8_t *bp)
{
    const uint8_t *mesh = *(uint8_t **)(bp - 0x20);
    const int nn = *(const int16_t *)(mesh + 6), mi = *(int32_t *)(bp + 0x08);
    LARGE_INTEGER t0, t1; if (time_mode) QueryPerformanceCounter(&t0);
    md_l_normals += nn > 0 ? nn : 0;
    if (!md_verify) {
        md_light_run(bp, (float *)(uintptr_t)(0x089c2120 + mi * 0x2bf20));
        *(int32_t *)(bp - 0x28) = nn > 0 ? nn : 0;   /* loop counter's final value, as the original leaves it */
        md_l_native++;
        if (time_mode) { QueryPerformanceCounter(&t1); tm_ticks[9] += t1.QuadPart - t0.QuadPart; tm_calls[9]++; }
        return 1;
    }
    if (md_lpend) md_l_dropped++;
    if (nn > md_ltcap) { free(md_lt); md_ltcap = nn * 2; md_lt = malloc(sizeof(float) * 3 * md_ltcap); }
    md_light_run(bp, md_lt);
    md_lpend = 1; md_lpend_n = nn; md_lpend_i = mi; md_lpend_model = *(uint8_t **)(bp - 0x10);
    return 0;
}
__asm__(
    ".text\n"
    ".globl _md_light_entry\n"
    "_md_light_entry:\n"
    "    push %ebp\n"
    "    call _md_light_hook\n"
    "    add $4, %esp\n"
    "    test %eax, %eax\n"
    "    jz 1f\n"
    "    mov $0x012b9971, %eax\n"          /* light loop exit */
    "    jmp *%eax\n"
    "1:  andl $0, -0x28(%ebp)\n"           /* replaced instruction */
    "    mov $0x012b9699, %eax\n"          /* original loop condition */
    "    jmp *%eax\n");
extern void md_light_entry(void);
static int md_patch_bytes(unsigned addr, const unsigned char *orig, const unsigned char *repl, int len, int on, const char *what)
{
    unsigned char *e = (unsigned char *)(uintptr_t)addr;
    MEMORY_BASIC_INFORMATION mi;
    if (!VirtualQuery(e, &mi, sizeof mi) || mi.State != MEM_COMMIT) return 0;
    const unsigned char *want = on ? repl : orig, *from = on ? orig : repl;
    if (!memcmp(e, want, len)) return 1;
    if (memcmp(e, from, len)) { if (st_file) fprintf(st_file, "meshdraw: unexpected %s bytes\n", what); return 0; }
    DWORD old;
    if (!VirtualProtect(e, len, PAGE_EXECUTE_READWRITE, &old)) return 0;
    memcpy(e, want, len);
    VirtualProtect(e, len, old, &old);
    FlushInstructionCache(GetCurrentProcess(), e, len);
    return 1;
}
static int md_light_install(int on)
{
    unsigned char j[6]; j[0] = 0xE9; *(int *)(j + 1) = (int)((unsigned char *)md_light_entry - ((unsigned char *)MD_LPATCH + 5)); j[5] = 0x90;
    md_lpend = 0;
    return md_patch_bytes(MD_LPATCH, md_lorig, j, 6, on, "light loop");
}

/* ---- whole-routine timer (bit 512): entry jmp to a wrapper that times the original via a trampoline ---- */
#define MD_ENTRY 0x012b8d1d
/* md_prologue[10] (push ebp; mov ebp,esp; push -1; push 0x1a1cef7) comes from meshdraw-orig.h */
typedef void (__attribute__((thiscall)) *pfn_mesh)(void *, uint32_t, uint32_t, uint32_t, uint32_t, uint32_t, uint32_t, uint32_t, uint32_t, uint32_t, uint32_t, uint32_t);
static pfn_mesh md_mesh_orig;
static void __attribute__((thiscall)) md_time_wrap(void *self, uint32_t a0, uint32_t a1, uint32_t a2, uint32_t a3, uint32_t a4, uint32_t a5,
                                                    uint32_t a6, uint32_t a7, uint32_t a8, uint32_t a9, uint32_t a10)
{
    LARGE_INTEGER t0, t1; QueryPerformanceCounter(&t0);
    md_seg_entry = t0.QuadPart; md_seg_hook0 = 0; md_seg_on = 1;
    md_mesh_orig(self, a0, a1, a2, a3, a4, a5, a6, a7, a8, a9, a10);
    QueryPerformanceCounter(&t1); md_rt_ticks += t1.QuadPart - t0.QuadPart; md_rt_calls++; md_seg_on = 0;
    if (md_seg_hook0) { md_seg_pre += md_seg_hook0 - t0.QuadPart; md_seg_loop += md_seg_hook1 - md_seg_hook0; md_seg_post += t1.QuadPart - md_seg_hook1; md_seg_n++; }
}
static int md_timer_install(int on)
{
    if (!md_mesh_orig) {
        unsigned char *t = VirtualAlloc(NULL, 64, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
        if (!t) return 0;
        memcpy(t, md_prologue, 10);
        t[10] = 0xE9; *(int *)(t + 11) = (int)(((unsigned char *)MD_ENTRY + 10) - (t + 15));
        FlushInstructionCache(GetCurrentProcess(), t, 64);
        md_mesh_orig = (pfn_mesh)t;
    }
    unsigned char j[5]; j[0] = 0xE9; *(int *)(j + 1) = (int)((unsigned char *)md_time_wrap - ((unsigned char *)MD_ENTRY + 5));
    return md_patch_bytes(MD_ENTRY, md_prologue, j, 5, on, "routine entry");
}

/* cdecl, called from md_entry with the routine's frame pointer: 1 = loop done natively, 0 = run original */
int md_hook(uint8_t *bp)
{
    md_calls++; md_tot_calls++;
    md_light_check(bp);
    const int32_t mode = *(int32_t *)(bp - 0x38);
    const uint32_t flags = *(uint32_t *)(bp + 0x0c);
    md_mode_cnt[md_mode_idx(mode)]++;
    md_vk_cnt[(flags & 0x20) ? 1 : (flags & 0x400) ? 2 : (flags & 0x200000) ? 3 : 0]++;
    if (mode == 0x8000) { md_fallback++; md_fb_mode8000++; return 0; }
    if ((flags & 0x420) == 0x400) { md_fallback++; md_fb_flag400++; return 0; }
    if ((flags & 0x200020) && !md_untested) { md_fallback++; md_fb_untested++; return 0; }   /* never seen in game: unverified */
    if (md_rec) { md_fallback++; md_fb_other++; return 0; }   /* re-entry while recording: cannot happen, be safe */
    if (!md_verify) {
        LARGE_INTEGER t0, t1; if (time_mode || md_seg_on) QueryPerformanceCounter(&t0);
        md_native++; md_tot_native++;
        if (md_direct && md_direct_ok()) {
            MdVtxOut vo; md_vo_init(&vo, &vb, &vcount, &vcap);
            md_tot_corners += md_run(bp, MD_OUT_VTX, &vo);
            memcpy(cur_t, vo.t, sizeof cur_t); memcpy(cur_c, vo.c, sizeof cur_c); set_t = vo.set_t; set_c = vo.set_c;
            md_tot_direct++;
        } else md_tot_corners += md_run(bp, MD_OUT_CALL, NULL);
        if (time_mode || md_seg_on) QueryPerformanceCounter(&t1);
        if (time_mode) { tm_ticks[8] += t1.QuadPart - t0.QuadPart; tm_calls[8]++; }
        if (md_seg_on) { md_seg_hook0 = t0.QuadPart; md_seg_hook1 = t1.QuadPart; }
        return 1;
    }
    md_cur_mode = mode; md_cur_flags = flags;
    if (md_direct && md_direct_ok()) {
        md_svn = 0; md_vo_init(&md_vexp, &md_sv, &md_svn, &md_svcap);
        md_cur_corners = md_run(bp, MD_OUT_VTX, &md_vexp);
        md_vstart = vcount;
        md_saved_end = MD_SLOT(MD_IAT_END); MD_SLOT(MD_IAT_END) = (void *)md_rec_end_direct; md_rec = 2;
        return 0;
    }
    md_na = 0; md_nb = 0;
    md_cur_corners = md_run(bp, MD_OUT_REC, NULL);
    md_slots_set(1);
    return 0;
}

__asm__(
    ".text\n"
    ".globl _md_entry\n"
    "_md_entry:\n"
    "    push %ebp\n"
    "    call _md_hook\n"
    "    add $4, %esp\n"
    "    test %eax, %eax\n"
    "    jz 1f\n"
    "    mov $0x012bb22e, %eax\n"          /* MD_GLEND: call [glEnd] */
    "    jmp *%eax\n"
    "1:  andl $0, -0x74(%ebp)\n"           /* replaced instruction */
    "    mov $0x012ba8a7, %eax\n"          /* MD_RESUME: original loop condition */
    "    jmp *%eax\n");
extern void md_entry(void);

static DWORD md_iat_old; static int md_iat_rw;
/* install (on) or remove (off) the loop jump; returns 1 when in the requested state */
static int md_install(int on, int verify, int direct)
{
    unsigned char *e = (unsigned char *)MD_PATCH;
    MEMORY_BASIC_INFORMATION mi;
    if (!VirtualQuery(e, &mi, sizeof mi) || mi.State != MEM_COMMIT) return 0;
    if (md_rec) return 0;   /* never switch in the middle of a recorded loop */
    if (verify && on && !md_iat_rw) {
        if (!VirtualProtect((void *)MD_IAT_C4, 0x30, PAGE_READWRITE, &md_iat_old)) { if (st_file) fprintf(st_file, "meshdraw: IAT not writable\n"); verify = 0; }
        else md_iat_rw = 1;
    }
    md_verify = verify; md_direct = direct;
    unsigned char jmp[7]; jmp[0] = 0xE9; *(int *)(jmp + 1) = (int)((unsigned char *)md_entry - (e + 5)); jmp[5] = 0x90; jmp[6] = 0x90;
    if (on) {
        if (!memcmp(e, jmp, 7)) return 1;
        if (memcmp(e, md_orig, 7)) { if (st_file) fprintf(st_file, "meshdraw: unexpected loop bytes\n"); return 0; }
    } else {
        if (!memcmp(e, md_orig, 7)) return 1;
        if (memcmp(e, jmp, 7)) return 0;
    }
    DWORD old;
    if (!VirtualProtect(e, 7, PAGE_EXECUTE_READWRITE, &old)) return 0;
    memcpy(e, on ? jmp : md_orig, 7);
    VirtualProtect(e, 7, old, &old);
    FlushInstructionCache(GetCurrentProcess(), e, 7);
    return 1;
}

static void md_stats(FILE *f)
{
    if (!md_tot_calls) return;
    fprintf(f, "meshdraw calls=%ld native=%ld fallback=%ld checked=%ld mismatches=%ld | total calls=%lld native=%lld direct=%lld corners=%lld checked=%lld+%lld(direct)/%lld corners mismatches=%lld+%lld(direct) fb(8000=%lld 400=%lld untested20/200000=%lld other=%lld)\n",
            md_calls, md_native, md_fallback, md_checked, md_bad, md_tot_calls, md_tot_native, md_tot_direct, md_tot_corners, md_tot_checked, md_tot_dchecked,
            md_tot_checked_corners, md_tot_bad, md_tot_dbad, md_fb_mode8000, md_fb_flag400, md_fb_untested, md_fb_other);
    fprintf(f, "  meshdraw modes:");
    for (int k = 0; k < MDM_N; k++) if (md_mode_cnt[k]) fprintf(f, " %s=%lld", md_mode_names[k], md_mode_cnt[k]);
    fprintf(f, " | vertex:");
    for (int k = 0; k < 4; k++) if (md_vk_cnt[k]) fprintf(f, " %s=%lld", md_vk_names[k], md_vk_cnt[k]);
    fprintf(f, "\n");
    if (md_l_native || md_l_checked || md_l_dropped)
        fprintf(f, "  meshdraw light: native=%lld normals=%lld checked=%lld mismatches=%lld unverified=%lld\n", md_l_native, md_l_normals, md_l_checked, md_l_bad, md_l_dropped);
    if (md_rt_calls && qpf.QuadPart && st_frames)
        fprintf(f, "  meshdraw routine: %.2fms/frame (%ld calls/frame); native calls: pre %.2f loop %.2f post %.2f ms/frame (%ld/frame)\n",
                md_rt_ticks * 1000.0 / qpf.QuadPart / st_frames, md_rt_calls / st_frames, md_seg_pre * 1000.0 / qpf.QuadPart / st_frames,
                md_seg_loop * 1000.0 / qpf.QuadPart / st_frames, md_seg_post * 1000.0 / qpf.QuadPart / st_frames, md_seg_n / st_frames);
    md_rt_ticks = 0; md_rt_calls = 0; md_seg_pre = md_seg_loop = md_seg_post = 0; md_seg_n = 0;
    md_calls = md_native = md_fallback = md_checked = md_bad = 0;
}
