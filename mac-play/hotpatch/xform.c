/* xform.c: optimized drop-in for the client's CPU model transform 0x012b5bde (thiscall, 12 stack args,
   ret 0x30), the hottest unoptimized routine while many models are on screen.
   Semantics follow the validated reconstruction reconstructed/model-codec/skinning.c (CLIENT-SKIN-001,
   checked against the original instructions on 11,962 installed transforms): same binary32 operation
   order, the client's own angle-matrix / inverse-rotate / world-test helpers, same outputs.
   Included by mugl.c; installed by a jmp at the function entry (hotpatch mask bit 8). Mask bit 16 runs
   both implementations on every call (ours into scratch buffers, then the original via a trampoline) and
   counts byte mismatches in the stats file. Build with -msse2 -mfpmath=sse -ffp-contract=off. */
#include <stdint.h>

#define XF_ENTRY 0x012b5bde
#include "xform-prologue.h"
#define CF(a) (*(const float *)(uintptr_t)(a))   /* client read-only constant */

typedef void (__cdecl *pfn_angle_matrix)(const float *angles, float *matrix);
typedef void (__cdecl *pfn_irotate)(const float *in, const float *matrix, float *out);
typedef unsigned char (__cdecl *pfn_world_test)(int32_t world);
#define client_angle_matrix ((pfn_angle_matrix)0x00cff32a)
#define client_irotate ((pfn_irotate)0x00cfff3c)
#define client_world_test ((pfn_world_test)0x0095fb7c)

static void xf_set3(float *v, float x, float y, float z) { v[0] = x; v[1] = y; v[2] = z; }

/* The light vectors depend only on the light-angle bytes (model +0x98..+0xa3) and on which of the three
   base light vectors was chosen; the client's angle matrix (sin/cos) and inverse rotations are pure, so
   results are memoized on exactly those inputs. */
typedef struct { uint32_t ang[3]; int sel; int valid; float l1[3], l2[3]; } XfLight;
static XfLight xf_lcache[64]; static int xf_lcache_on = 1;
static void xf_lights(const uint8_t *model, const float *lv, int sel, float *l1, float *l2)
{
    uint32_t ang[3]; memcpy(ang, model + 0x98, 12);
    unsigned h = (ang[0] * 2654435761u ^ ang[1] * 40503u ^ ang[2] * 2246822519u ^ (unsigned)sel * 97u) >> 26;
    XfLight *c = &xf_lcache[h & 63];
    if (xf_lcache_on && c->valid && c->sel == sel && !memcmp(c->ang, ang, 12)) { memcpy(l1, c->l1, 12); memcpy(l2, c->l2, 12); return; }
    float lm[12], v2[3];
    client_angle_matrix((const float *)(model + 0x98), lm);
    client_irotate(lv, lm, l1);
    xf_set3(v2, CF(0x01a7e91c), CF(0x01a80118), CF(0x01a7ebc0));
    client_irotate(v2, lm, l2);
    memcpy(c->ang, ang, 12); c->sel = sel; c->valid = 1; memcpy(c->l1, l1, 12); memcpy(c->l2, l2, 12);
}

/* a[0..11] = the twelve stack arguments; secondary = per-normal secondary light table (0x075a9ee8). */
static void xf_impl(uint8_t *model, const uint32_t *a, uint8_t *secondary)
{
    const uint8_t *bones = (const uint8_t *)(uintptr_t)a[0];
    uint8_t *verts = (uint8_t *)(uintptr_t)a[1], *norms = (uint8_t *)(uintptr_t)a[2], *lights = (uint8_t *)(uintptr_t)a[3];
    const float *bmin = (const float *)(uintptr_t)a[4], *bmax = (const float *)(uintptr_t)a[5];
    float *box = (float *)(uintptr_t)a[6];
    const uint8_t translate = (uint8_t)a[7];
    float vscale, ambient, lscale, lmin;
    memcpy(&vscale, &a[8], 4); memcpy(&ambient, &a[9], 4); memcpy(&lscale, &a[10], 4); memcpy(&lmin, &a[11], 4);
    float lv[3], l1[3], l2[3], mn[3], mx[3], local[3]; int sel;

    if (!bones) return;
    if (model[0x50]) {
        if (*(volatile uint8_t *)0x01cf1048) { xf_set3(lv, CF(0x01a7e91c), 0.0f, CF(0x01a7e474)); sel = 0; }
        else if (client_world_test(*(volatile int32_t *)0x01cf15fc)) {
            xf_set3(lv, CF(0x01a7df14), CF(0x01a7e4ec), CF(0x01a7dd48)); sel = 1;
            *(float *)(model + 0x98) = 0.0f; *(float *)(model + 0x9c) = 0.0f; *(float *)(model + 0xa0) = CF(0x01a7fb2c);
        } else { xf_set3(lv, 0.0f, CF(0x01aa5f18), 0.0f); sel = 2; }
        xf_lights(model, lv, sel, l1, l2);
    }
    const int bounds = *(volatile int32_t *)0x0b437bfc == 2;
    if (bounds) { xf_set3(mn, CF(0x01ac8da0), CF(0x01ac8da0), CF(0x01ac8da0)); xf_set3(mx, CF(0x01ac8da4), CF(0x01ac8da4), CF(0x01ac8da4)); }
    const float bone_scale = *(volatile float *)0x01cf104c;
    const float body = *(const float *)(model + 0x74);
    const float *origin = (const float *)(model + 0x78);
    const int meshes = *(const int16_t *)(model + 0x24);
    const uint8_t *mesh_array = *(uint8_t *const *)(model + 0x28);
    for (int i = 0; i < meshes; i++) {
        const uint8_t *mesh = mesh_array + i * 0x20;
        const int nv = *(const int16_t *)(mesh + 4), nn = *(const int16_t *)(mesh + 6);
        const uint8_t *vrec = *(uint8_t *const *)(mesh + 0xc), *nrec = *(uint8_t *const *)(mesh + 0x10);
        float *out = (float *)(verts + i * 0x2bf20);
        for (int j = 0; j < nv; j++, out += 3) {
            const uint8_t *r = vrec + j * 16;
            const float *p = (const float *)(r + 4);
            const float *m = (const float *)(bones + *(const int16_t *)r * 0x30);
            if (bone_scale == 1.0f) {
                const float *src = p;
                if (vscale != 0.0f) { local[0] = vscale * p[0]; local[1] = vscale * p[1]; local[2] = vscale * p[2]; src = local; }
                const float s0 = src[0], s1 = src[1], s2 = src[2];
                out[0] = s0 * m[0] + s1 * m[1] + s2 * m[2] + m[3];
                out[1] = s0 * m[4] + s1 * m[5] + s2 * m[6] + m[7];
                out[2] = s0 * m[8] + s1 * m[9] + s2 * m[10] + m[11];
            } else {
                const float s0 = p[0], s1 = p[1], s2 = p[2];
                out[0] = (s0 * m[0] + s1 * m[1] + s2 * m[2]) * bone_scale + m[3];
                out[1] = (s0 * m[4] + s1 * m[5] + s2 * m[6]) * bone_scale + m[7];
                out[2] = (s0 * m[8] + s1 * m[9] + s2 * m[10]) * bone_scale + m[11];
            }
            if (translate) { out[0] = body * out[0]; out[1] = body * out[1]; out[2] = body * out[2]; }
            if (bounds)
                for (int k = 0; k < 3; k++) { if (mn[k] > out[k]) mn[k] = out[k]; if (out[k] > mx[k]) mx[k] = out[k]; }
            if (translate) { out[0] = out[0] + origin[0]; out[1] = out[1] + origin[1]; out[2] = out[2] + origin[2]; }
        }
        float *nout = (float *)(norms + i * 0x2bf20);
        float *lout = (float *)(lights + i * 0xea60), *sout = (float *)(secondary + i * 0xea60);
        const float k08 = CF(0x01a7df18), k02 = CF(0x01a7df08);
        for (int j = 0; j < nn; j++, nout += 3) {
            const uint8_t *r = nrec + j * 20;
            const float *p = (const float *)(r + 4);
            const float *m = (const float *)(bones + *(const int16_t *)r * 0x30);
            const float s0 = p[0], s1 = p[1], s2 = p[2];
            nout[0] = s0 * m[0] + s1 * m[1] + s2 * m[2];
            nout[1] = s0 * m[4] + s1 * m[5] + s2 * m[6];
            nout[2] = s0 * m[8] + s1 * m[9] + s2 * m[10];
            if (!model[0x50]) continue;
            float v = (nout[0] * l1[0] + nout[1] * l1[1] + nout[2] * l1[2]) * lscale + ambient;
            if (lmin > v) v = lmin;
            lout[j] = v;
            float w = (nout[0] * l2[0] + nout[1] * l2[1] + nout[2] * l2[2]) * k08 + ambient;
            sout[j] = k02 > w ? k02 : w;
        }
    }
    if (bounds) {
        box[0] = mn[0]; box[1] = mn[1]; box[2] = mn[2];
        for (int k = 0; k < 3; k++) box[3 * (k + 1) + k] = mx[k] - mn[k];
    } else {
        memcpy(box, bmin, 12);
        for (int k = 0; k < 3; k++) box[3 * (k + 1) + k] = bmax[k] - bmin[k];
    }
    box[0] = box[0] + origin[0]; box[1] = box[1] + origin[1]; box[2] = box[2] + origin[2];
    box[4] = 0.0f; box[5] = 0.0f; box[6] = 0.0f; box[8] = 0.0f; box[9] = 0.0f; box[10] = 0.0f;
}

/* ---- verification: run both, compare ---- */
typedef void (__attribute__((thiscall)) *pfn_xform)(uint8_t *, uint32_t, uint32_t, uint32_t, uint32_t, uint32_t, uint32_t,
                                                     uint32_t, uint32_t, uint32_t, uint32_t, uint32_t, uint32_t);
static pfn_xform xf_original;          /* trampoline: saved prologue + jmp back */
static int xf_verify; static long xf_calls, xf_checked, xf_bad;
static uint8_t *xf_sv, *xf_sn, *xf_sl, *xf_ss; static size_t xf_scap;
static float xf_sbox[12];

static void xf_compare(uint8_t *model, const uint32_t *a)
{
    const int meshes = *(const int16_t *)(model + 0x24);
    const uint8_t *mesh_array = *(uint8_t *const *)(model + 0x28);
    long bad = 0;
    for (int i = 0; i < meshes; i++) {
        const uint8_t *mesh = mesh_array + i * 0x20;
        int nv = *(const int16_t *)(mesh + 4), nn = *(const int16_t *)(mesh + 6);
        if (nv > 0 && memcmp(xf_sv + i * 0x2bf20, (uint8_t *)(uintptr_t)a[1] + i * 0x2bf20, nv * 12)) bad++;
        if (nn > 0 && memcmp(xf_sn + i * 0x2bf20, (uint8_t *)(uintptr_t)a[2] + i * 0x2bf20, nn * 12)) bad++;
        if (nn > 0 && model[0x50]) {
            if (memcmp(xf_sl + i * 0xea60, (uint8_t *)(uintptr_t)a[3] + i * 0xea60, nn * 4)) bad++;
            if (memcmp(xf_ss + i * 0xea60, (uint8_t *)0x075a9ee8 + i * 0xea60, nn * 4)) bad++;
        }
    }
    if (memcmp(xf_sbox, (void *)(uintptr_t)a[6], 48)) bad++;
    xf_checked++;
    if (bad) { if (xf_bad < 20 && st_file) { fprintf(st_file, "xform MISMATCH model %p meshes %d (%ld parts)\n", (void *)model, meshes, bad); fflush(st_file); } xf_bad++; }
}

static void __attribute__((thiscall)) xf_hook(uint8_t *model, uint32_t a0, uint32_t a1, uint32_t a2, uint32_t a3, uint32_t a4,
                                              uint32_t a5, uint32_t a6, uint32_t a7, uint32_t a8, uint32_t a9, uint32_t a10, uint32_t a11)
{
    uint32_t a[12] = {a0, a1, a2, a3, a4, a5, a6, a7, a8, a9, a10, a11};
    xf_calls++;
    if (!xf_verify || !a0) { xf_impl(model, a, (uint8_t *)0x075a9ee8); return; }
    const int meshes = *(const int16_t *)(model + 0x24);
    size_t need = (size_t)(meshes > 0 ? meshes : 1) * 0x2bf20;
    if (need > xf_scap) {
        free(xf_sv); free(xf_sn); free(xf_sl); free(xf_ss);
        xf_sv = malloc(need); xf_sn = malloc(need); xf_sl = malloc(need); xf_ss = malloc(need); xf_scap = need;
    }
    uint32_t b[12]; memcpy(b, a, sizeof b);
    b[1] = (uint32_t)(uintptr_t)xf_sv; b[2] = (uint32_t)(uintptr_t)xf_sn; b[3] = (uint32_t)(uintptr_t)xf_sl; b[6] = (uint32_t)(uintptr_t)xf_sbox;
    xf_impl(model, b, xf_ss);
    xf_original(model, a0, a1, a2, a3, a4, a5, a6, a7, a8, a9, a10, a11);
    xf_compare(model, a);
}

/* install (on) or remove (off) the entry jump; returns 1 when in the requested state */
static int xf_install(int on, int verify)
{
    unsigned char *e = (unsigned char *)XF_ENTRY;
    MEMORY_BASIC_INFORMATION mi;
    if (!VirtualQuery(e, &mi, sizeof mi) || mi.State != MEM_COMMIT) return 0;
    xf_verify = verify;
    if (!xf_original) {
        unsigned char *t = VirtualAlloc(NULL, 64, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
        if (!t) return 0;
        memcpy(t, xf_prologue, 9);                                   /* push ebp; mov ebp,esp; sub esp,0xcc */
        t[9] = 0xE9; *(int *)(t + 10) = (int)((e + 9) - (t + 14));   /* jmp entry+9 */
        FlushInstructionCache(GetCurrentProcess(), t, 64);
        xf_original = (pfn_xform)t;
    }
    unsigned char jmp[5]; jmp[0] = 0xE9; *(int *)(jmp + 1) = (int)((unsigned char *)xf_hook - (e + 5));
    if (on) {
        if (!memcmp(e, jmp, 5)) return 1;
        if (memcmp(e, xf_prologue, sizeof xf_prologue)) { if (st_file) fprintf(st_file, "xform: unexpected entry bytes\n"); return 0; }
    } else {
        if (!memcmp(e, xf_prologue, 5)) return 1;
        if (memcmp(e, jmp, 5)) return 0;
    }
    DWORD old;
    if (!VirtualProtect(e, 5, PAGE_EXECUTE_READWRITE, &old)) return 0;
    memcpy(e, on ? jmp : xf_prologue, 5);
    VirtualProtect(e, 5, old, &old);
    FlushInstructionCache(GetCurrentProcess(), e, 5);
    return 1;
}
