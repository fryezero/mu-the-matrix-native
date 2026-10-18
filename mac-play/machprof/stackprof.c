/* stackprof: profile the 32-bit x86 game thread of a Rosetta (CrossOver WoW64) process from outside.
   Rosetta keeps x86 EAX..EDI in ARM x0..x7, so ESP = x4, EBP = x5. For each sample we scan the x86 stack
   for return addresses into [lo,hi) that follow a call instruction.
   usage: stackprof <pid> <thread-index|-1 busiest> <seconds> <lo-hex> <hi-hex> [interval_us]
   output: "L <addr> n" (first return address = caller of the running leaf), "I <addr> n" (inclusive, any depth)
   MOD=<hex address inside a PE module> (v7.5) also accepts return addresses inside that module (found by its MZ header
   at a 64K boundary and SizeOfImage), so EBP walks continue through a frame-pointer build of mugl. */
#include <mach/mach.h>
#include <mach/mach_vm.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <libproc.h>
#define HS (1 << 18)
typedef struct { unsigned a; unsigned n; } E;
static E L[HS], I[HS]; static char *rnames[4096]; static unsigned rcount[4096]; static int nr;
static FILE *npc; static void addnative(int pid, unsigned long long pc) { if (npc) fprintf(npc, "%llx\n", pc); char buf[1024] = ""; if (proc_regionfilename(pid, pc, buf, sizeof buf) <= 0) strcpy(buf, "(anon)"); for (int i = 0; i < nr; i++) if (!strcmp(rnames[i], buf)) { rcount[i]++; return; } if (nr < 4096) { rnames[nr] = strdup(buf); rcount[nr++] = 1; } } static FILE *chains;
static void add(E *h, unsigned a) { unsigned i = (a * 2654435761u) >> 14 & (HS - 1); while (h[i].n && h[i].a != a) i = (i + 1) & (HS - 1); h[i].a = a; h[i].n++; }
static int cmp(const void *x, const void *y) { return (int)((E *)y)->n - (int)((E *)x)->n; }
static task_t task; static unsigned lo, hi; static int ebpwalk;
static unsigned char *code; /* snapshot of [lo,hi) */
static unsigned lo2, hi2; static unsigned char *code2;
static int is_ret(unsigned v) {
    unsigned char *p;
    if (v >= lo + 8 && v < hi) p = code + (v - lo);
    else if (code2 && v >= lo2 + 8 && v < hi2) p = code2 + (v - lo2);
    else return 0;
    if (p[-5] == 0xE8) return 1;                                   /* call rel32 */
    if (p[-2] == 0xFF && ((p[-1] >> 3) & 7) == 2 && (p[-1] >> 6) == 3) return 1;   /* call reg */
    if (p[-2] == 0xFF && ((p[-1] >> 3) & 7) == 2 && (p[-1] >> 6) == 0 && (p[-1] & 7) != 4 && (p[-1] & 7) != 5) return 1; /* call [reg] */
    if (p[-3] == 0xFF && ((p[-2] >> 3) & 7) == 2 && (p[-2] >> 6) == 1) return 1;   /* call [reg+d8] */
    if (p[-6] == 0xFF && ((p[-5] >> 3) & 7) == 2 && ((p[-5] >> 6) == 2 || (p[-5] & 0xC7) == 5)) return 1; /* call [reg+d32] / [abs] */
    if (p[-4] == 0xFF && ((p[-3] >> 3) & 7) == 2 && (p[-3] & 7) == 4 && (p[-3] >> 6) == 1) return 1; /* call [sib+d8] */
    return 0;
}
int main(int argc, char **argv) {
    int pid = atoi(argv[1]); int want = atoi(argv[2]); double secs = atof(argv[3]);
    lo = strtoul(argv[4], 0, 16); hi = strtoul(argv[5], 0, 16); int us = argc > 6 ? atoi(argv[6]) : 1000;
    if (task_for_pid(mach_task_self(), pid, &task)) { fprintf(stderr, "task_for_pid failed\n"); return 1; }
    code = malloc(hi - lo);
    for (unsigned a = lo; a < hi; a += 4096) { mach_vm_size_t got = 0; if (mach_vm_read_overwrite(task, a, 4096, (mach_vm_address_t)(code + (a - lo)), &got)) memset(code + (a - lo), 0, 4096); }
    if (getenv("MOD")) {
        unsigned a = strtoul(getenv("MOD"), 0, 16) & ~0xffffu; unsigned char hb[4096];
        for (int k = 0; k < 256; k++, a -= 0x10000) { mach_vm_size_t g = 0; if (!mach_vm_read_overwrite(task, a, 4096, (mach_vm_address_t)hb, &g) && hb[0] == 'M' && hb[1] == 'Z') break; }
        unsigned pe = *(unsigned *)(hb + 0x3c); unsigned size = *(unsigned *)(hb + pe + 0x50);
        lo2 = a; hi2 = a + size; code2 = malloc(size);
        for (unsigned b = lo2; b < hi2; b += 4096) { mach_vm_size_t got = 0; if (mach_vm_read_overwrite(task, b, 4096, (mach_vm_address_t)(code2 + (b - lo2)), &got)) memset(code2 + (b - lo2), 0, 4096); }
        fprintf(stderr, "module %x-%x\n", lo2, hi2);
    }
    thread_act_array_t th; mach_msg_type_number_t nth; task_threads(task, &th, &nth);
    if (want < 0) {
        unsigned long long t0[512] = {0};
        for (int pass = 0; pass < 2; pass++) { for (unsigned i = 0; i < nth && i < 512; i++) { thread_basic_info_data_t bi; mach_msg_type_number_t c = THREAD_BASIC_INFO_COUNT;
            if (thread_info(th[i], THREAD_BASIC_INFO, (thread_info_t)&bi, &c)) continue; unsigned long long t = bi.user_time.seconds * 1000000ULL + bi.user_time.microseconds;
            t0[i] = pass ? t - t0[i] : t; } if (!pass) usleep(300000); }
        want = 0; for (unsigned i = 1; i < nth && i < 512; i++) if (t0[i] > t0[want]) want = i;
    }
    thread_t t = th[want];
    if (getenv("CHAINS")) chains = fopen(getenv("CHAINS"), "w");
    if (getenv("NPC")) npc = fopen(getenv("NPC"), "w");
    ebpwalk = getenv("EBPWALK") != NULL;
    long samples = 0, x86 = 0, noret = 0; int iters = (int)(secs * 1e6 / us);
    unsigned stk[1024];
    for (int k = 0; k < iters; k++) {
        usleep(us);
        if (thread_suspend(t)) continue;
        struct { unsigned flavor, count; unsigned long long x[29], fp, lr, sp, pc; unsigned cpsr, pad; } st;
        mach_msg_type_number_t c = sizeof st / 4;
        kern_return_t kr = thread_get_state(t, 1, (thread_state_t)&st, &c);
        unsigned esp = (unsigned)st.x[4]; if (0) fprintf(stderr, "kr=%d c=%u fl=%u x4=%llx pc=%llx\n", kr, c, st.flavor, st.x[4], st.pc);
        int ok = !kr && st.x[4] < 0x80000000ULL && esp > 0x10000;
        mach_vm_size_t got = 0;
        unsigned ebpchain[32]; int nchain = 0;
        if (ok && ebpwalk) {   /* follow saved-EBP frames: [ebp] = caller's ebp, [ebp+4] = return address */
            unsigned bp = (unsigned)st.x[5];
            for (int d = 0; d < 32 && bp > 0x10000 && bp < 0x80000000u; d++) {
                unsigned fr[2]; mach_vm_size_t g2 = 0;
                if (mach_vm_read_overwrite(task, bp, 8, (mach_vm_address_t)fr, &g2) || g2 != 8) break;
                if (!is_ret(fr[1])) break;
                ebpchain[nchain++] = fr[1];
                if (fr[0] <= bp) break;
                bp = fr[0];
            }
        }
        if (ok && mach_vm_read_overwrite(task, esp, sizeof stk, (mach_vm_address_t)stk, &got)) ok = 0;
        thread_resume(t);
        samples++;
        if (!ok) { if (!kr) addnative(pid, st.pc); continue; }
        x86++;
        if (ebpwalk) {
            if (nchain) { add(L, ebpchain[0]); for (int j = 0; j < nchain; j++) add(I, ebpchain[j]); } else noret++;
            if (chains) { fprintf(chains, "S"); for (int j = 0; j < nchain; j++) fprintf(chains, " %x", ebpchain[j]); fprintf(chains, "\n"); }
            continue;
        }
        int first = 1; unsigned seen[64]; int ns = 0; int nc = 0;
        if (chains) fprintf(chains, "S");
        for (unsigned i = 0; i < got / 4; i++) {
            unsigned v = stk[i]; if (!is_ret(v)) continue;
            if (first) { add(L, v); first = 0; }
            if (chains && nc < 24) { fprintf(chains, " %x", v); nc++; }
            int dup = 0; for (int j = 0; j < ns; j++) if (seen[j] == v) dup = 1;
            if (!dup && ns < 64) { seen[ns++] = v; add(I, v); }
        }
        if (chains) fprintf(chains, "\n");
        if (first) noret++;
    }
    fprintf(stderr, "thread=%d samples=%ld x86=%ld noret=%ld\n", want, samples, x86, noret);
    for (int i = 0; i < nr; i++) fprintf(stderr, "native %6u %s\n", rcount[i], rnames[i]);
    qsort(L, HS, sizeof(E), cmp); qsort(I, HS, sizeof(E), cmp);
    for (int i = 0; i < 300 && L[i].n; i++) printf("L %08x %u\n", L[i].a, L[i].n);
    for (int i = 0; i < 600 && I[i].n; i++) printf("I %08x %u\n", I[i].a, I[i].n);
    return 0;
}
