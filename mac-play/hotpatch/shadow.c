/* shadow.c (v7.5, MAC-PERF-009): native replacement for the per-triangle loop of the client's body-shadow routine
   0x012bc07a (thiscall, 5 stack args, ret 0x14; RenderBodyShadow). Included by mugl.c after meshdraw.c.

   Profile (boss fight at Tormenta Island, many players): the routine and the terrain height lookup it calls once
   per corner (0x016cc9e2) were the hottest client code, about 21% of the main thread's x86 samples.

   Routine (decoded from the pristine listing):
     prelude: render state helpers, -0x1c = 2000.0 (0x01a802d8) or, in world 0x1e (0x0095fb7c), 0x01ac8d9c;
              -0x20 = 0x01a9ff0c; [ebp-0x24]..[ebp-0x28] = mesh range (args 3/4 when not -1)
     for each mesh i in range, skipping i == arg2, meshes without triangles and meshes whose texture slot
     (int16 mesh+2) == arg1:
         glBegin(GL_TRIANGLES) at 0x012bc17b                      <- return address 0x012bc181 is our patch site
         for each triangle t < (int16)mesh[0x0a] (stride 0x24 at mesh[0x18]), corner j < (int8)tri[0]:
             V = 0x078978a0 + i*0x2bf20 + (int16)tri[2+2j]*12      (the transformed vertex buffer), O = model+0x78
             l = V - O; l.x = ((l.x + K1c) * l.z) / (l.z - K20) + l.x
             x = l.x + O.x; y = l.y + O.y
             world != 0x91 (0x00d79e40): z = height(x, y) + 0x01a7e474; z = (float)arg5 + z
             world == 0x91:              z = 0x01a7e4d0 + O.z;      z = (float)arg5 + z
             glVertex3fv(x, y, z)
         glEnd at 0x012bc58c
   height (0x016cc9e2, cdecl, x87 float return, pure): scene [0x01d1df70] in {1, 2, 4} -> 0; 0 > x or 0 > y -> 0;
     x /= 0x01a7dec4, y /= 0x01a7dec4; xi, yi = truncations; (yi << 8) + xi >= 0x10000 (unsigned) or attribute
     word 0x0b795420[idx] & 0x40 -> [0x01cf15dc]; else bilinear over the height map 0x0b6f5420 at the four
     masked neighbours ((y & 255) << 8) + (x & 255), in the client's operation order.
   The x87 return (fld float / fstp float) and the world/scene tests are exact; the per-corner world test and
   the scene read are loop-invariant, so they are read once per mesh. Single binary32 operations in the
   original order (-msse2 -mfpmath=sse -ffp-contract=off).

   Patch: the 7 bytes at 0x012bc181 (nop; and [ebp-0x10],0; jmp 0x12bc18f) become jmp sh_entry; nop; nop.
   sh_hook(ebp) returns 1 when it emitted the mesh's vertices (sh_entry jumps to the glEnd call 0x012bc58c) or 0
   to run the original loop. The frame locals the loop writes (-0x10, -0x18, -0x2c, -0xc, -0x30, -0x3c..-0x34)
   are re-initialised per mesh and not read after it. The original bytes come from the generated private header
   (targets.json meshdraw_sites "sh_orig", SHA-256 pinned); the compile-only build has zeros and never patches.

   Mask bits: 2097152 install (glVertex3fv through the import slot, or with 128 appended straight into mugl's open
   batch like mugl_glVertex3fv), 4194304 verify: our loop records, the original runs with the glVertex3fv/glEnd
   import slots pointed at recorders, and both vertex streams are compared bit for bit at its glEnd; with 128 the
   direct-append result (vertex array and mugl state) is compared instead. */
#define SH_PATCH 0x012bc181
#define SH_GLEND 0x012bc58c
#define SH_IAT_V3V 0x01a7c778
#define SH_IAT_END 0x01a7c760

static int sh_on, sh_verify, sh_rec;
static long sh_calls, sh_native, sh_checked, sh_bad;
static long long sh_tot_native, sh_tot_corners, sh_tot_checked, sh_tot_bad, sh_tot_direct, sh_tot_ccorners;

/* the client's terrain height lookup 0x016cc9e2 */
static float sh_height(float x, float y, int32_t scene)
{
    if (scene == 1 || scene == 2 || scene == 4) return 0.0f;
    if (0.0f > x || 0.0f > y) return 0.0f;
    const float k = MD_K(0x01a7dec4);
    x = x / k; y = y / k;
    const int32_t xi = _mm_cvtt_ss2si(_mm_set_ss(x)), yi = _mm_cvtt_ss2si(_mm_set_ss(y));
    const uint32_t idx = ((uint32_t)yi << 8) + (uint32_t)xi;
    if (idx >= 0x10000u) return MD_K(0x01cf15dc);
    if (((const uint16_t *)(uintptr_t)0x0b795420)[idx] & 0x40) return MD_K(0x01cf15dc);
    const float fx = x - (float)xi, fy = y - (float)yi;
#define SH_IX(a, b) (((((uint32_t)(b)) & 0xff) << 8) + (((uint32_t)(a)) & 0xff))
    const uint32_t i00 = SH_IX(xi, yi), i01 = SH_IX(xi, yi + 1), i10 = SH_IX(xi + 1, yi), i11 = SH_IX(xi + 1, yi + 1);
#undef SH_IX
    const float *H = (const float *)(uintptr_t)0x0b6f5420;
    const float a = (H[i01] - H[i00]) * fy + H[i00];
    const float b = (H[i11] - H[i10]) * fy + H[i10];
    return (b - a) * fx + a;
}

/* out: MD_OUT_CALL (glVertex3fv through the slot), MD_OUT_REC (append to md_a as MD_V records), MD_OUT_VTX (vo) */
static long sh_run(uint8_t *bp, int out, MdVtxOut *vo)
{
    const uint8_t *model = *(uint8_t **)(bp - 0x04);
    const int32_t mi = *(int32_t *)(bp - 0x08);
    const uint8_t *mesh = *(uint8_t **)(bp - 0x14);
    const float k1c = *(float *)(bp - 0x1c), k20 = *(float *)(bp - 0x20);
    const float a5 = (float)*(int32_t *)(bp + 0x18);
    const int ntri = *(const int16_t *)(mesh + 0x0a);
    const uint8_t *tris = *(uint8_t *const *)(mesh + 0x18);
    const uint8_t *vbase = (const uint8_t *)(uintptr_t)(0x078978a0 + mi * 0x2bf20);
    const float *O = (const float *)(model + 0x78);
    const int w91 = *(volatile int32_t *)0x01cf15fc == 0x91;
    const int32_t scene = *(volatile int32_t *)0x01d1df70;
    const float kz = MD_K(0x01a7e474), kz91 = MD_K(0x01a7e4d0);
    md_fv_fn v3v = (md_fv_fn)MD_SLOT(SH_IAT_V3V);
    Vtx *obuf = NULL; int ocount = 0;
    if (out == MD_OUT_VTX) {
        obuf = *vo->buf; ocount = *vo->count; int ocap = *vo->cap;
        long need = ocount;
        for (int t = 0; t < ntri; t++) { const int n = *(const int8_t *)(tris + t * 0x24); if (n > 0) need += n; }
        if (need > ocap) {
            int nc = ocap ? ocap : 8192; while (nc < need) nc *= 2;
            Vtx *nb = realloc(obuf, sizeof(Vtx) * nc); if (!nb) abort(); obuf = nb; *vo->cap = nc;
        }
    }
    const __m128 tc0 = _mm_setr_ps(vo ? vo->t[0] : 0, vo ? vo->t[1] : 0, vo ? vo->c[0] : 0, vo ? vo->c[1] : 0);
    const __m128 tc1 = _mm_setr_ps(vo ? vo->c[2] : 0, vo ? vo->c[3] : 0, vo ? vo->n[0] : 0, vo ? vo->n[1] : 0);
    const float n2 = vo ? vo->n[2] : 0;
    long corners = 0;
    for (int t = 0; t < ntri; t++) {
        const uint8_t *tri = tris + t * 0x24;
        const int n = *(const int8_t *)tri;
        const int16_t *tv = (const int16_t *)(tri + 0x02);
        for (int j = 0; j < n; j++) {
            const float *V = (const float *)(vbase + tv[j] * 12);
            float l0 = V[0] - O[0];
            const float l1 = V[1] - O[1], l2 = V[2] - O[2];
            l0 = (l0 + k1c) * l2 / (l2 - k20) + l0;
            float p[3];
            p[0] = l0 + O[0]; p[1] = l1 + O[1];
            if (!w91) { const float h = sh_height(p[0], p[1], scene); p[2] = h + kz; }
            else p[2] = kz91 + O[2];
            p[2] = a5 + p[2];
            corners++;
            if (out == MD_OUT_VTX) {
                float *o = (float *)&obuf[ocount++];
                _mm_storeu_ps(o, tc0); _mm_storeu_ps(o + 4, tc1); o[8] = n2; o[9] = p[0]; o[10] = p[1]; o[11] = p[2];
            } else if (out == MD_OUT_REC) md_push(&md_a, &md_na, &md_capa, MD_V, p[0], p[1], p[2], 0);
            else v3v(p);
        }
    }
    if (out == MD_OUT_VTX) { *vo->buf = obuf; *vo->count = ocount; }
    return corners;
}

/* verify recorders: installed in the glVertex3fv / glEnd slots only while the original loop runs */
static void *sh_saved_v3v, *sh_saved_end; static long sh_cur_corners; static int sh_vstart;
static Vtx *sh_sv; static int sh_svn, sh_svcap;
static void WINAPI sh_rec_v3v(const GLfloat *v) { md_push(&md_b, &md_nb, &md_capb, MD_V, v[0], v[1], v[2], 0); ((md_fv_fn)sh_saved_v3v)(v); }
static void sh_report(int bad, const char *what, int na, int nb, int at)
{
    sh_checked++; sh_tot_checked++; sh_tot_ccorners += sh_cur_corners;
    if (!bad) return;
    sh_bad++; sh_tot_bad++;
    if (sh_tot_bad <= 20 && st_file) { fprintf(st_file, "shadow %s MISMATCH: native %d, original %d, first diff %d\n", what, na, nb, at); fflush(st_file); }
}
static void WINAPI sh_rec_end(void)
{
    MD_SLOT(SH_IAT_V3V) = sh_saved_v3v; MD_SLOT(SH_IAT_END) = sh_saved_end; sh_rec = 0;
    int bad = md_na != md_nb, at = -1;
    if (!bad) for (int k = 0; k < md_na; k++) if (memcmp(&md_a[k], &md_b[k], sizeof(MdRec))) { bad = 1; at = k; break; }
    sh_report(bad, "call", md_na, md_nb, at);
    ((md_v_fn)sh_saved_end)();
}
static void WINAPI sh_rec_end_direct(void)
{
    MD_SLOT(SH_IAT_END) = sh_saved_end; sh_rec = 0;
    int n = vcount - sh_vstart, at = -1;
    int bad = !mugl_in_begin || n != sh_svn || (n > 0 && memcmp(&vb[sh_vstart], sh_sv, sizeof(Vtx) * n));
    if (bad) for (int k = 0; k < n && k < sh_svn; k++) if (memcmp(&vb[sh_vstart + k], &sh_sv[k], sizeof(Vtx))) { at = k; break; }
    sh_report(bad, "direct", sh_svn, n, at);
    ((md_v_fn)sh_saved_end)();
}
static int sh_direct_ok(void)
{
    return mugl_in_begin && !passthrough && !ts_in_face_flag && MD_SLOT(SH_IAT_V3V) == (void *)mugl_glVertex3fv;
}

/* cdecl, called from sh_entry with the routine's frame pointer: 1 = mesh done natively, 0 = run original loop */
int sh_hook(uint8_t *bp)
{
    sh_calls++;
    if (sh_rec || md_rec) return 0;   /* never nest with a recorded loop */
    LARGE_INTEGER t0, t1; if (time_mode) QueryPerformanceCounter(&t0);
    if (!sh_verify) {
        long c;
        if (md_direct && sh_direct_ok()) {
            MdVtxOut vo; md_vo_init(&vo, &vb, &vcount, &vcap);
            c = sh_run(bp, MD_OUT_VTX, &vo); sh_tot_direct++;
        } else c = sh_run(bp, MD_OUT_CALL, NULL);
        sh_native++; sh_tot_native++; sh_tot_corners += c;
        if (time_mode) { QueryPerformanceCounter(&t1); tm_ticks[10] += t1.QuadPart - t0.QuadPart; tm_calls[10]++; }
        return 1;
    }
    if (md_direct && sh_direct_ok()) {
        MdVtxOut vo; sh_svn = 0; md_vo_init(&vo, &sh_sv, &sh_svn, &sh_svcap);
        sh_cur_corners = sh_run(bp, MD_OUT_VTX, &vo);
        sh_vstart = vcount;
        sh_saved_end = MD_SLOT(SH_IAT_END); MD_SLOT(SH_IAT_END) = (void *)sh_rec_end_direct; sh_rec = 2;
        return 0;
    }
    md_na = 0; md_nb = 0;
    sh_cur_corners = sh_run(bp, MD_OUT_REC, NULL);
    sh_saved_v3v = MD_SLOT(SH_IAT_V3V); sh_saved_end = MD_SLOT(SH_IAT_END);
    MD_SLOT(SH_IAT_V3V) = (void *)sh_rec_v3v; MD_SLOT(SH_IAT_END) = (void *)sh_rec_end; sh_rec = 1;
    return 0;
}

__asm__(
    ".text\n"
    ".globl _sh_entry\n"
    "_sh_entry:\n"
    "    push %ebp\n"
    "    call _sh_hook\n"
    "    add $4, %esp\n"
    "    test %eax, %eax\n"
    "    jz 1f\n"
    "    mov $0x012bc58c, %eax\n"          /* SH_GLEND: call [glEnd] */
    "    jmp *%eax\n"
    "1:  andl $0, -0x10(%ebp)\n"           /* replaced instruction */
    "    mov $0x012bc18f, %eax\n"          /* original triangle loop condition */
    "    jmp *%eax\n");
extern void sh_entry(void);

static int sh_iat_rw;
static int sh_install(int on, int verify)
{
    if (sh_rec) return 0;   /* never switch in the middle of a recorded loop */
    if (verify && on && !sh_iat_rw) {
        DWORD old;
        if (!VirtualProtect((void *)SH_IAT_END, 0x20, PAGE_READWRITE, &old)) { if (st_file) fprintf(st_file, "shadow: IAT not writable\n"); verify = 0; }
        else sh_iat_rw = 1;
    }
    unsigned char j[7]; j[0] = 0xE9; *(int *)(j + 1) = (int)((unsigned char *)sh_entry - ((unsigned char *)SH_PATCH + 5)); j[5] = 0x90; j[6] = 0x90;
    int r = md_patch_bytes(SH_PATCH, sh_orig, j, 7, on, "shadow loop");
    sh_on = on && r; sh_verify = verify;
    return r;
}

static void sh_stats(FILE *f)
{
    if (!sh_calls && !sh_tot_native && !sh_tot_checked) return;
    fprintf(f, "shadow calls=%ld native=%ld checked=%ld mismatches=%ld | total native=%lld direct=%lld corners=%lld checked=%lld (%lld corners) mismatches=%lld\n",
            sh_calls, sh_native, sh_checked, sh_bad, sh_tot_native, sh_tot_direct, sh_tot_corners, sh_tot_checked, sh_tot_ccorners, sh_tot_bad);
    sh_calls = sh_native = sh_checked = sh_bad = 0;
}
