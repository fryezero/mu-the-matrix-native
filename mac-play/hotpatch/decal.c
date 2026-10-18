/* decal.c (v7.5, MAC-PERF-009): native replacement for the client's terrain decal routine 0x016cdd5f (cdecl, 11 args,
   plain ret) and the per-tile fan it calls, 0x016d197d. Included by mugl.c after shadow.c.

   Ground effects (skill circles, auras) are drawn as a texture laid over the terrain grid: one GL_TRIANGLE_FAN per
   visible terrain tile, with the tile corners lifted to the terrain heights. In the Tormenta Island boss fight this
   was about 14% of the main thread's x86 samples (some 30,000 fans per frame).

   0x016cdd5f(tex, x, y, sx, sy, const float *colour, angle, alpha, hadd, flat, vflip) (decoded from the pristine
   listing; K = 0x01a7dec4, C = 0x01a7df14, ONE = 0x01a7dd48):
     alpha == ONE (ordered) ? glColor3fv(colour) : glColor4f(colour[0..2], alpha)
     M = AngleMatrix({0, 0, angle}) (client 0x00cff32a, pure); bind texture tex (client 0x0184acf6)
     xf = x / K, yf = y / K, xi/yi = truncations; s = sx >= sy ? sx : sy
     ox = ((float)xi - xf) + C * s, oy likewise, inv = ONE / s, s2 = (float)((int)s + 1), ratio = sx / sy
     for (j = -s2; s2 >= j; j += ONE) for (i = -s2; s2 >= i; i += ONE):
         tx = (float)xi + i, ty = (float)yi + j; skip unless visible(tx, ty) (0x016d2050)
         corners (ox+i, oy+j), (ox+i+ONE, oy+j), (ox+i+ONE, oy+j+ONE), (ox+i, oy+j+ONE), each * inv, z 0:
             u -= C, v -= C, VectorRotate by M (client 0x00d000ad, pure), u *= ratio, u += C, v += C
         tile(tx, ty, ONE, 1, corners, 0, alpha, hadd, flat, vflip)
   visible(fx, fy): idx = ((int)fy << 8) + (int)fx (signed); false if idx < 0 or idx >= 0x10000, if attribute word
     0x0b795420[idx] & 0x200, or in world 0x8d if (attr & 8) or byte 0x0b735420[idx] == 14.
   tile(x, y, scale, step, uv, light = 0, alpha, hadd, flat, vflip) (0x016d197d):
     xi/yi = truncations; return unless 0 <= xi, yi < 255; S = K * scale, X = x * K, Y = y * K
     globals [0x0b6b4eac], [0x0b6b52e8], [0x0b6b52ec], [0x0b6b52f0] = (yi << 8) + xi, (yi << 8) + xi + step,
         ((yi + step) << 8) + xi + step, ((yi + step) << 8) + xi
     global vertices 0x0b6b5318[4][3] = (X, Y), (X + S, Y), (X + S, Y + S), (X, Y + S); z = flat ? H[g] + hadd : hadd
         (H = height map 0x0b6f5420)
     glBegin(GL_TRIANGLE_FAN); per corner: glTexCoord2f(u, vflip ? ONE - v : v); glVertex3fv(&vertex); glEnd
   The light-colour path of the tile (argument 6) is never used by this caller. Single binary32 operations in the
   original order; the global writes are reproduced (other client code may read them).

   Patch: the routine entry (5 of the 9 prologue bytes, pinned as "td_prologue" in targets.json) becomes a jmp to
   td_wrap. Mask bits: 8388608 install; with 128 the fans go straight into mugl (mugl_glBegin, a direct append of
   what mugl_glTexCoord2f/mugl_glVertex3fv do, mugl_glEnd) when the import slots point at mugl. 16777216 verify:
   our routine records its GL calls (no texture bind), then the original runs through a trampoline with the colour,
   begin, texcoord, vertex and end import slots pointed at recorders; streams and the written globals are compared. */
#define TD_ENTRY 0x016cdd5f
#define TD_IAT_BEGIN 0x01a7c750
#define TD_IAT_C4 0x01a7c754
#define TD_IAT_END 0x01a7c760
#define TD_IAT_C3V 0x01a7c770
#define TD_IAT_TC 0x01a7c774
#define TD_IAT_V3V 0x01a7c778
enum { TD_OP_BEGIN = 10, TD_OP_END = 11 };
typedef void (__cdecl *td_vrot_fn)(const float *in, const float *m, float *out);
typedef void (__cdecl *td_bind_fn)(uint32_t tex);
typedef void (__cdecl *td_orig_fn)(uint32_t, uint32_t, uint32_t, uint32_t, uint32_t, uint32_t, uint32_t, uint32_t, uint32_t, uint32_t, uint32_t);
#define td_client_vrot ((td_vrot_fn)0x00d000ad)
#define td_client_bind ((td_bind_fn)0x0184acf6)

static int td_on, td_verify, td_rec;
static td_orig_fn td_orig;
static long td_calls, td_tiles, td_checked, td_bad;
static long long td_tot_calls, td_tot_tiles, td_tot_checked, td_tot_bad, td_tot_direct;

static int td_visible(float fx, float fy)
{
    const int32_t xi = _mm_cvtt_ss2si(_mm_set_ss(fx)), yi = _mm_cvtt_ss2si(_mm_set_ss(fy));
    const int32_t idx = (int32_t)(((uint32_t)yi << 8) + (uint32_t)xi);
    if (idx < 0 || idx >= 0x10000) return 0;
    const uint16_t attr = ((const uint16_t *)(uintptr_t)0x0b795420)[idx];
    if (attr & 0x200) return 0;
    if (*(volatile int32_t *)0x01cf15fc == 0x8d && ((attr & 8) || ((const uint8_t *)(uintptr_t)0x0b735420)[idx] == 14)) return 0;
    return 1;
}

/* GL output of the native routine */
enum { TD_OUT_CALL, TD_OUT_REC, TD_OUT_DIRECT };
static int td_out;
static void td_begin(void)
{
    if (td_out == TD_OUT_REC) md_push(&md_a, &md_na, &md_capa, TD_OP_BEGIN, GL_TRIANGLE_FAN, 0, 0, 0);
    else if (td_out == TD_OUT_DIRECT) mugl_glBegin(GL_TRIANGLE_FAN);
    else ((PFN1u)MD_SLOT(TD_IAT_BEGIN))(GL_TRIANGLE_FAN);
}
static void td_end(void)
{
    if (td_out == TD_OUT_REC) md_push(&md_a, &md_na, &md_capa, TD_OP_END, 0, 0, 0, 0);
    else if (td_out == TD_OUT_DIRECT) mugl_glEnd();
    else ((PFN0)MD_SLOT(TD_IAT_END))();
}
static void td_corner(float u, float v, const float *p)
{
    if (td_out == TD_OUT_REC) { md_push(&md_a, &md_na, &md_capa, MD_TC, u, v, 0, 0); md_push(&md_a, &md_na, &md_capa, MD_V, p[0], p[1], p[2], 0); }
    else if (td_out == TD_OUT_DIRECT) {
        if (mugl_in_begin && !passthrough && !ts_in_face_flag) {   /* what mugl_glTexCoord2f + mugl_glVertex3fv do in a batched block */
            cur_t[0] = u; cur_t[1] = v; set_t = 1;
            push_vertex(p[0], p[1], p[2]);
        } else { mugl_glTexCoord2f(u, v); mugl_glVertex3fv(p); }
    } else { ((md_tc_fn)MD_SLOT(TD_IAT_TC))(u, v); ((md_fv_fn)MD_SLOT(TD_IAT_V3V))(p); }
}

/* 0x016d197d with light = 0 */
static void td_tile(float x, float y, float scale, int32_t step, const float *uv, float hadd, int flat, int vflip)
{
    const int32_t xi = _mm_cvtt_ss2si(_mm_set_ss(x)), yi = _mm_cvtt_ss2si(_mm_set_ss(y));
    if (xi < 0 || yi < 0 || xi >= 255 || yi >= 255) return;
    const float K = MD_K(0x01a7dec4);
    const float S = K * scale, X = x * K, Y = y * K;
    const uint32_t g0 = ((uint32_t)yi << 8) + (uint32_t)xi, g1 = ((uint32_t)yi << 8) + (uint32_t)(xi + step),
                   g2 = ((uint32_t)(yi + step) << 8) + (uint32_t)(xi + step), g3 = ((uint32_t)(yi + step) << 8) + (uint32_t)xi;
    *(volatile uint32_t *)0x0b6b4eac = g0; *(volatile uint32_t *)0x0b6b52e8 = g1;
    *(volatile uint32_t *)0x0b6b52ec = g2; *(volatile uint32_t *)0x0b6b52f0 = g3;
    float *V = (float *)(uintptr_t)0x0b6b5318;
    const float *H = (const float *)(uintptr_t)0x0b6f5420;
    V[0] = X; V[1] = Y; V[3] = X + S; V[4] = Y; V[6] = X + S; V[7] = Y + S; V[9] = X; V[10] = Y + S;
    if (flat) { V[2] = H[g0] + hadd; V[5] = H[g1] + hadd; V[8] = H[g2] + hadd; V[11] = H[g3] + hadd; }
    else { V[2] = hadd; V[5] = hadd; V[8] = hadd; V[11] = hadd; }
    const float one = MD_K(0x01a7dd48);
    td_begin();
    for (int k = 0; k < 4; k++) {
        const float u = uv[k * 3], v = vflip ? one - uv[k * 3 + 1] : uv[k * 3 + 1];
        td_corner(u, v, V + k * 3);
    }
    td_end();
    td_tiles++;
}

static void td_impl(uint32_t tex, float x, float y, float sx, float sy, const float *colour, float angle, float alpha, float hadd,
                    int flat, int vflip, int bind)
{
    const float one = MD_K(0x01a7dd48), K = MD_K(0x01a7dec4), C = MD_K(0x01a7df14);
    if (alpha == one) {
        if (td_out == TD_OUT_REC) md_push(&md_a, &md_na, &md_capa, MD_C3, colour[0], colour[1], colour[2], 0);
        else ((md_fv_fn)MD_SLOT(TD_IAT_C3V))(colour);
    } else {
        if (td_out == TD_OUT_REC) md_push(&md_a, &md_na, &md_capa, MD_C4, colour[0], colour[1], colour[2], alpha);
        else ((md_c4_fn)MD_SLOT(TD_IAT_C4))(colour[0], colour[1], colour[2], alpha);
    }
    float ang[3] = {0.0f, 0.0f, angle}, M[12];
    client_angle_matrix(ang, M);
    if (bind) td_client_bind(tex);
    const float xf = x / K, yf = y / K;
    const int32_t xi = _mm_cvtt_ss2si(_mm_set_ss(xf)), yi = _mm_cvtt_ss2si(_mm_set_ss(yf));
    float s = sx >= sy ? sx : sy;
    const float ox = ((float)xi - xf) + C * s, oy = ((float)yi - yf) + C * s;
    const float invx = one / s, invy = one / s;
    s = (float)(_mm_cvtt_ss2si(_mm_set_ss(s)) + 1);
    const float ratio = sx / sy;
    for (float j = -s; s >= j; j = j + one) {
        for (float i = -s; s >= i; i = i + one) {
            const float tx = (float)xi + i, ty = (float)yi + j;
            if (!td_visible(tx, ty)) continue;
            float uv[4][3], r[4][3];
            const float ui = ox + i, vj = oy + j;
            uv[0][0] = ui * invx;         uv[0][1] = vj * invy;         uv[0][2] = 0.0f;
            uv[1][0] = (ui + one) * invx; uv[1][1] = vj * invy;         uv[1][2] = 0.0f;
            uv[2][0] = (ui + one) * invx; uv[2][1] = (vj + one) * invy; uv[2][2] = 0.0f;
            uv[3][0] = ui * invx;         uv[3][1] = (vj + one) * invy; uv[3][2] = 0.0f;
            for (int k = 0; k < 4; k++) {
                uv[k][0] = uv[k][0] - C; uv[k][1] = uv[k][1] - C;
                td_client_vrot(uv[k], M, r[k]);
                r[k][0] = r[k][0] * ratio; r[k][0] = r[k][0] + C; r[k][1] = r[k][1] + C;
            }
            td_tile(tx, ty, one, 1, &r[0][0], hadd, flat, vflip);
        }
    }
}

/* verify recorders */
static void *td_saved[6];
static const uintptr_t td_slots[6] = {TD_IAT_BEGIN, TD_IAT_C4, TD_IAT_END, TD_IAT_C3V, TD_IAT_TC, TD_IAT_V3V};
static void WINAPI td_rec_begin(GLenum m) { md_push(&md_b, &md_nb, &md_capb, TD_OP_BEGIN, (float)m, 0, 0, 0); ((PFN1u)td_saved[0])(m); }
static void WINAPI td_rec_c4(GLfloat r, GLfloat g, GLfloat b, GLfloat a) { md_push(&md_b, &md_nb, &md_capb, MD_C4, r, g, b, a); ((md_c4_fn)td_saved[1])(r, g, b, a); }
static void WINAPI td_rec_end(void) { md_push(&md_b, &md_nb, &md_capb, TD_OP_END, 0, 0, 0, 0); ((PFN0)td_saved[2])(); }
static void WINAPI td_rec_c3v(const GLfloat *v) { md_push(&md_b, &md_nb, &md_capb, MD_C3, v[0], v[1], v[2], 0); ((md_fv_fn)td_saved[3])(v); }
static void WINAPI td_rec_tc(GLfloat s, GLfloat t) { md_push(&md_b, &md_nb, &md_capb, MD_TC, s, t, 0, 0); ((md_tc_fn)td_saved[4])(s, t); }
static void WINAPI td_rec_v3v(const GLfloat *v) { md_push(&md_b, &md_nb, &md_capb, MD_V, v[0], v[1], v[2], 0); ((md_fv_fn)td_saved[5])(v); }

static void __cdecl td_wrap(uint32_t tex, uint32_t x, uint32_t y, uint32_t sx, uint32_t sy, uint32_t colour, uint32_t angle, uint32_t alpha,
                            uint32_t hadd, uint32_t flat, uint32_t vflip)
{
    float f[7]; memcpy(&f[0], &x, 4); memcpy(&f[1], &y, 4); memcpy(&f[2], &sx, 4); memcpy(&f[3], &sy, 4);
    memcpy(&f[4], &angle, 4); memcpy(&f[5], &alpha, 4); memcpy(&f[6], &hadd, 4);
    td_calls++; td_tot_calls++;
    if (!td_verify || td_rec || md_rec || sh_rec) {
        LARGE_INTEGER t0, t1; if (time_mode) QueryPerformanceCounter(&t0);
        int direct = md_direct && !passthrough && MD_SLOT(TD_IAT_BEGIN) == (void *)mugl_glBegin && MD_SLOT(TD_IAT_END) == (void *)mugl_glEnd &&
                     MD_SLOT(TD_IAT_TC) == (void *)mugl_glTexCoord2f && MD_SLOT(TD_IAT_V3V) == (void *)mugl_glVertex3fv;
        long t = td_tiles;
        td_out = direct ? TD_OUT_DIRECT : TD_OUT_CALL;
        td_impl(tex, f[0], f[1], f[2], f[3], (const float *)(uintptr_t)colour, f[4], f[5], f[6], (uint8_t)flat, (uint8_t)vflip, 1);
        td_tot_tiles += td_tiles - t; if (direct) td_tot_direct++;
        if (time_mode) { QueryPerformanceCounter(&t1); tm_ticks[10] += t1.QuadPart - t0.QuadPart; tm_calls[10]++; }
        return;
    }
    /* verify: native record-only run, then the original with recorders */
    md_na = 0; md_nb = 0; td_out = TD_OUT_REC;
    td_impl(tex, f[0], f[1], f[2], f[3], (const float *)(uintptr_t)colour, f[4], f[5], f[6], (uint8_t)flat, (uint8_t)vflip, 0);
    uint32_t g[4] = {*(volatile uint32_t *)0x0b6b4eac, *(volatile uint32_t *)0x0b6b52e8, *(volatile uint32_t *)0x0b6b52ec, *(volatile uint32_t *)0x0b6b52f0};
    float V[12]; memcpy(V, (void *)(uintptr_t)0x0b6b5318, sizeof V);
    for (int k = 0; k < 6; k++) td_saved[k] = MD_SLOT(td_slots[k]);
    void *rp[6] = {(void *)td_rec_begin, (void *)td_rec_c4, (void *)td_rec_end, (void *)td_rec_c3v, (void *)td_rec_tc, (void *)td_rec_v3v};
    for (int k = 0; k < 6; k++) MD_SLOT(td_slots[k]) = rp[k];
    td_rec = 1;
    td_orig(tex, x, y, sx, sy, colour, angle, alpha, hadd, flat, vflip);
    for (int k = 0; k < 6; k++) MD_SLOT(td_slots[k]) = td_saved[k];
    td_rec = 0;
    int bad = md_na != md_nb, at = -1;
    if (!bad) for (int k = 0; k < md_na; k++) if (memcmp(&md_a[k], &md_b[k], sizeof(MdRec))) { bad = 1; at = k; break; }
    int gbad = md_na > 1 && (memcmp(g, (void *)0x0b6b4eac, 4) || memcmp(g + 1, (void *)0x0b6b52e8, 12) || memcmp(V, (void *)(uintptr_t)0x0b6b5318, sizeof V));
    td_checked++; td_tot_checked++;
    if (bad || gbad) {
        td_bad++; td_tot_bad++;
        if (td_tot_bad <= 20 && st_file) {
            fprintf(st_file, "decal MISMATCH: native %d calls, original %d, first diff %d, globals %s", md_na, md_nb, at, gbad ? "differ" : "equal");
            if (at >= 0) fprintf(st_file, "; op %u (%g %g %g %g) vs op %u (%g %g %g %g)", md_a[at].op, md_a[at].f[0], md_a[at].f[1], md_a[at].f[2], md_a[at].f[3],
                                 md_b[at].op, md_b[at].f[0], md_b[at].f[1], md_b[at].f[2], md_b[at].f[3]);
            fprintf(st_file, "\n"); fflush(st_file);
        }
    }
}

static int td_iat_rw;
static int td_install(int on, int verify)
{
    if (td_rec) return 0;
    if (!td_orig) {   /* trampoline: the three prologue instructions (9 bytes), then jmp to the rest */
        unsigned char *t = VirtualAlloc(NULL, 64, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
        if (!t) return 0;
        memcpy(t, td_prologue, 9);
        t[9] = 0xE9; *(int *)(t + 10) = (int)(((unsigned char *)TD_ENTRY + 9) - (t + 14));
        FlushInstructionCache(GetCurrentProcess(), t, 64);
        td_orig = (td_orig_fn)t;
    }
    if (verify && on && !td_iat_rw) {
        DWORD old;
        if (!VirtualProtect((void *)TD_IAT_BEGIN, 0x30, PAGE_READWRITE, &old)) { if (st_file) fprintf(st_file, "decal: IAT not writable\n"); verify = 0; }
        else td_iat_rw = 1;
    }
    unsigned char j[5]; j[0] = 0xE9; *(int *)(j + 1) = (int)((unsigned char *)td_wrap - ((unsigned char *)TD_ENTRY + 5));
    int r = md_patch_bytes(TD_ENTRY, td_prologue, j, 5, on, "decal entry");
    td_on = on && r; td_verify = verify;
    return r;
}

static void td_stats(FILE *f)
{
    if (!td_calls && !td_tot_checked) return;
    fprintf(f, "decal calls=%ld tiles=%ld checked=%ld mismatches=%ld | total calls=%lld tiles=%lld direct=%lld checked=%lld mismatches=%lld\n",
            td_calls, td_tiles, td_checked, td_bad, td_tot_calls, td_tot_tiles, td_tot_direct, td_tot_checked, td_tot_bad);
    td_calls = td_tiles = td_checked = td_bad = 0;
}
