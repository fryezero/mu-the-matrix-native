#include <windows.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "orig.h"
extern unsigned char hp_store8[];
extern unsigned char hp_vrot[], hp_vrot_end[], hp_vtrans[], hp_vtrans_end[], hp_self[], hp_index[], hp_deref16[], hp_eq[];
unsigned regs[3];
void cap_cdecl3(void *fn, void *a, void *b, void *c);
void cap_this(void *fn, void *thisp, int nargs, void *arg);
void cap_this2(void *fn, void *thisp, int a0, int a1);
static void *exe(const void *p, size_t n) { void *m = VirtualAlloc(0, 4096, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE); memcpy(m, p, n); return m; }
static unsigned rnd(void) { return (unsigned)rand() << 17 ^ (unsigned)rand() << 5 ^ rand(); }
static float rf(void) {
    unsigned r = rnd(); float f;
    switch (r % 16) {
    case 0: { unsigned u = rnd(); memcpy(&f, &u, 4); return f; }            /* any bit pattern incl. NaN/inf/denormal */
    case 1: return 0.0f; case 2: return -0.0f; case 3: return 1e-40f;
    default: return ((int)(rnd() % 2000001) - 1000000) / 997.0f;
    }
}
int main(int argc, char **argv) { int iters = argc > 1 ? atoi(argv[1]) : 1000; freopen("C:\\mutools\\hptest.log", "w", stdout); setvbuf(stdout, 0, _IONBF, 0);
    void *ov = exe(orig_vrot, sizeof orig_vrot), *nv = exe(hp_vrot, hp_vrot_end - hp_vrot);
    void *ot = exe(orig_vtrans, sizeof orig_vtrans), *nt = exe(hp_vtrans, hp_vtrans_end - hp_vtrans);
    void *os = exe(orig_self, sizeof orig_self), *ns = exe(hp_self, 16);
    void *oi = exe(orig_index, sizeof orig_index), *ni = exe(hp_index, 16);
    void *od = exe(orig_deref16, sizeof orig_deref16), *nd = exe(hp_deref16, 16);
    void *oe = exe(orig_eq, sizeof orig_eq), *ne = exe(hp_eq, 32);
    static const unsigned char ret4[] = {0xc2, 0x04, 0x00};
    void *oret4 = exe(ret4, 3);
    void *osa = exe(orig_st_a, sizeof orig_st_a), *osb = exe(orig_st_b, sizeof orig_st_b), *osc = exe(orig_st_c, sizeof orig_st_c), *nst = exe(hp_store8, 16);
    #define FIXCALL(copy, off, tgt) (*(int *)((unsigned char *)(copy) + (off) + 1) = (int)((unsigned char *)(tgt) - ((unsigned char *)(copy) + (off) + 5)))
    FIXCALL(osa, 0x15, oret4); FIXCALL(osb, 0x10, osa); FIXCALL(osc, 0x10, osb);
    long bad = 0, n = 0;
    for (int it = 0; it < iters; it++) {
        for (int w = 0; w < 2; w++) {
            void *of = w ? ot : ov, *nf = w ? nt : nv;
            float A[32], B[32]; for (int i = 0; i < 32; i++) A[i] = rf(); memcpy(B, A, sizeof A);
            int mode = it % 4;   /* 0: separate, 1: out==in, 2: out overlaps matrix, 3: in overlaps matrix */
            int in = 0, m = 4, out = 20;
            if (mode == 1) out = in; if (mode == 2) out = 5; if (mode == 3) in = 6;
            cap_cdecl3(of, A + in, A + m, A + out); unsigned r1[3]; memcpy(r1, regs, 12);
            cap_cdecl3(nf, B + in, B + m, B + out);
            n++;
            if (memcmp(A, B, sizeof A) || r1[0] != regs[0] || (r1[1] - (unsigned)A) != (regs[1] - (unsigned)B) || r1[2] != regs[2]) {
                if (bad++ < 5) printf("%s mismatch mode %d regs %x/%x %x/%x %x/%x\n", w ? "vtrans" : "vrot", mode, r1[0], regs[0], r1[1], regs[1], r1[2], regs[2]);
            }
        }
        int obj[8]; for (int i = 0; i < 8; i++) obj[i] = rnd(); int idx = (int)(rnd() % 64) - 32;
        unsigned r1[3];
        cap_this(os, obj, 0, 0); memcpy(r1, regs, 12); cap_this(ns, obj, 0, 0); if (r1[0] != regs[0] || r1[1] != regs[1]) bad++;
        cap_this(oi, obj, 1, (void *)idx); memcpy(r1, regs, 12); cap_this(ni, obj, 1, (void *)idx); if (r1[0] != regs[0] || r1[1] != regs[1]) bad++;
        int *pp[1] = { obj }; cap_this(od, pp, 0, 0); memcpy(r1, regs, 12); cap_this(nd, pp, 0, 0); if (r1[0] != regs[0] || r1[1] != regs[1]) bad++;
        int a = rnd() % 3, b = rnd() % 3; cap_this(oe, &a, 1, &b); memcpy(r1, regs, 12); cap_this(ne, &a, 1, &b); if (r1[0] != regs[0] || r1[1] != regs[1]) { if (bad++ < 10) printf("eq %x/%x %x/%x\n", r1[0], regs[0], r1[1], regs[1]); }
        {   /* store8 family: patch the original call targets inside st_b/st_c copies to point at the copied st_a/st_b */
            void *o3[3] = {osa, osb, osc};
            for (int q = 0; q < 3; q++) {
                int o1[2] = {rnd(), rnd()}, o2[2]; memcpy(o2, o1, 8); int v = rnd();
                cap_this2(o3[q], o1, v, 7); unsigned r1[3]; memcpy(r1, regs, 12);
                cap_this2(nst, o2, v, 7);
                if (memcmp(o1, o2, 8) || r1[0] - (unsigned)o1 != regs[0] - (unsigned)o2 || r1[1] - (unsigned)o1 != regs[1] - (unsigned)o2 || r1[2] != regs[2]) { if (bad++ < 10) printf("store8 %d mismatch\n", q); }
                n++;
            }
        }
        n += 4;
    }
    printf("tests=%ld mismatches=%ld\n", n, bad);
    return bad != 0;
}
