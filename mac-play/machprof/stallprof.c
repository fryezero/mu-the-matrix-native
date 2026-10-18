/* stallprof: catch long frames of the 32-bit game thread of a Rosetta (CrossOver WoW64) process from outside.
   usage: stallprof <pid> <frame-counter-hex> <seconds> [threshold_ms=80] [interval_us=1000] [thread-index|-1] [arm_ms=50]
   The frame counter is a 32-bit value in the target that changes once per presented frame (mugl v7.3 writes its
   address to C:\mutools\mugl-shm.txt as "frames 0x..."). Every interval the tool reads the counter; once the
   current frame is older than arm_ms (so normal frames are not disturbed) it also briefly suspends the game thread (default: the busiest thread), reads its state and resumes it. Rosetta keeps x86
   EAX..EDI in ARM x0..x7 (ESP = x4), as stackprof.c; a sample whose x4 is a plausible x86 stack pointer is scanned
   for return addresses into main.exe (0x00401000..0x01a7c000) that follow a call instruction. Other samples are
   counted by the macOS region of the native pc (Rosetta runtime, Wine unix libraries, system frameworks).
   When the counter changes after a frame longer than the threshold, the frame's samples are summarised:
   "STALL <unix_ms_end> <frame_ms> samples=<n> x86=<n>", then "  callee <addr> <n>" (target of the call made at the
   first return address; 0 = indirect call), "  leaf <addr> <n> (-> callee)" (first return address, i.e. the
   caller of the running code), "  incl <addr> <n>" (any depth) and "  native <n> <region>". Output goes to stdout.
   NPC=1 (MAC-PERF-010) adds "  npc <region> +0x<offset> <n>": the 16 most frequent 256-byte offset bins of the native pcs
   inside their regions. Wall-clock times use gettimeofday so they can be matched with mugl's stall lines (same host clock). */
#include <mach/mach.h>
#include <mach/mach_vm.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/time.h>
#include <libproc.h>

#define LO 0x00401000u
#define HI 0x01a7c000u
#define MAXS 20000          /* samples kept for one frame */
#define DEPTH 16

typedef struct { unsigned a; unsigned n; } E;
static unsigned char *code;
static task_t task;
static int is_ret(unsigned v)
{
    if (v < LO + 8 || v >= HI) return 0;
    unsigned char *p = code + (v - LO);
    if (p[-5] == 0xE8) return 1;
    if (p[-2] == 0xFF && ((p[-1] >> 3) & 7) == 2 && (p[-1] >> 6) == 3) return 1;
    if (p[-2] == 0xFF && ((p[-1] >> 3) & 7) == 2 && (p[-1] >> 6) == 0 && (p[-1] & 7) != 4 && (p[-1] & 7) != 5) return 1;
    if (p[-3] == 0xFF && ((p[-2] >> 3) & 7) == 2 && (p[-2] >> 6) == 1) return 1;
    if (p[-6] == 0xFF && ((p[-5] >> 3) & 7) == 2 && ((p[-5] >> 6) == 2 || (p[-5] & 0xC7) == 5)) return 1;
    if (p[-4] == 0xFF && ((p[-3] >> 3) & 7) == 2 && (p[-3] & 7) == 4 && (p[-3] >> 6) == 1) return 1;
    return 0;
}
typedef struct { unsigned char n; unsigned r[DEPTH]; unsigned long long npc; } S;
static S smp[MAXS]; static int ns;

static void bump(E *h, int *n, int cap, unsigned a)
{
    for (int i = 0; i < *n; i++) if (h[i].a == a) { h[i].n++; return; }
    if (*n < cap) { h[*n].a = a; h[*n].n = 1; (*n)++; }
}
static unsigned call_target(unsigned ret)   /* target of a direct call ending at ret, else 0 */
{
    if (ret < LO + 5 || ret >= HI || code[ret - LO - 5] != 0xE8) return 0;
    int rel; memcpy(&rel, code + (ret - LO - 4), 4); return ret + (unsigned)rel;
}
static int cmp(const void *x, const void *y) { return (int)((const E *)y)->n - (int)((const E *)x)->n; }
static double now_ms(void) { struct timeval tv; gettimeofday(&tv, NULL); return tv.tv_sec * 1000.0 + tv.tv_usec / 1000.0; }

static void report(int pid, double end_ms, double frame_ms)
{
    static E leaf[4096], incl[8192], tgt[4096]; int nl = 0, ni = 0, nt = 0, x86 = 0;
    static char *rn[256]; static unsigned rc[256]; int nr = 0;
    static E nb[4096]; int nn = 0; static char *nbn[4096];
    for (int k = 0; k < ns; k++) {
        S *s = &smp[k];
        if (!s->n) {
            char buf[1024] = "";
            if (proc_regionfilename(pid, s->npc, buf, sizeof buf) <= 0) strcpy(buf, "(anon)");
            const char *b = strrchr(buf, '/'); b = b ? b + 1 : buf;
            int j; for (j = 0; j < nr; j++) if (!strcmp(rn[j], b)) break;
            if (j == nr && nr < 256) { rn[nr] = strdup(b); rc[nr++] = 0; }
            if (j < nr) rc[j]++;
            if (getenv("NPC") && j < nr) {   /* native pc histogram: region index in the top byte, 256-byte bins of the offset */
                struct proc_regioninfo ri;
                unsigned off = 0;
                if (proc_pidinfo(pid, PROC_PIDREGIONINFO, s->npc, &ri, sizeof ri) == sizeof ri) off = (unsigned)(s->npc - ri.pri_address);
                unsigned key = ((unsigned)j << 24) | ((off >> 8) & 0xffffff);
                int before = nn; bump(nb, &nn, 4096, key); if (nn > before) nbn[nn - 1] = rn[j];
            }
            continue;
        }
        x86++;
        bump(leaf, &nl, 4096, s->r[0]); bump(tgt, &nt, 4096, call_target(s->r[0]));
        for (int d = 0; d < s->n; d++) {
            int dup = 0; for (int e = 0; e < d; e++) if (s->r[e] == s->r[d]) dup = 1;
            if (!dup) bump(incl, &ni, 8192, s->r[d]);
        }
    }
    printf("STALL %.0f %.1f samples=%d x86=%d\n", end_ms, frame_ms, ns, x86);
    qsort(leaf, nl, sizeof(E), cmp); qsort(incl, ni, sizeof(E), cmp);
    qsort(tgt, nt, sizeof(E), cmp);
    for (int i = 0; i < nt && i < 12; i++) printf("  callee %08x %u\n", tgt[i].a, tgt[i].n);
    for (int i = 0; i < nl && i < 12; i++) printf("  leaf %08x %u (-> %08x)\n", leaf[i].a, leaf[i].n, call_target(leaf[i].a));
    for (int i = 0; i < ni && i < 30; i++) printf("  incl %08x %u\n", incl[i].a, incl[i].n);
    if (nn) {
        qsort(nb, nn, sizeof(E), cmp);
        for (int i = 0; i < nn && i < 16; i++) printf("  npc %s +0x%x %u\n", rn[nb[i].a >> 24], (nb[i].a & 0xffffff) << 8, nb[i].n);
    }
    for (int j = 0; j < nr; j++) { printf("  native %u %s\n", rc[j], rn[j]); free(rn[j]); }
    fflush(stdout);
}

int main(int argc, char **argv)
{
    if (argc < 4) { fprintf(stderr, "usage: stallprof <pid> <frame-counter-hex> <seconds> [threshold_ms] [interval_us] [thread|-1] [arm_ms]\n"); return 2; }
    int pid = atoi(argv[1]); unsigned ctr = (unsigned)strtoul(argv[2], 0, 16); double secs = atof(argv[3]);
    double thr = argc > 4 ? atof(argv[4]) : 80; int us = argc > 5 ? atoi(argv[5]) : 1000; int want = argc > 6 ? atoi(argv[6]) : -1; double arm = argc > 7 ? atof(argv[7]) : 50;
    if (task_for_pid(mach_task_self(), pid, &task)) { fprintf(stderr, "task_for_pid failed\n"); return 1; }
    code = malloc(HI - LO);
    for (unsigned a = LO; a < HI; a += 4096) {
        mach_vm_size_t got = 0;
        if (mach_vm_read_overwrite(task, a, 4096, (mach_vm_address_t)(code + (a - LO)), &got)) memset(code + (a - LO), 0, 4096);
    }
    thread_act_array_t th; mach_msg_type_number_t nth;
    if (task_threads(task, &th, &nth)) { fprintf(stderr, "task_threads failed\n"); return 1; }
    if (want < 0) {   /* busiest thread over 300 ms */
        static unsigned long long t0[512];
        for (int pass = 0; pass < 2; pass++) {
            for (unsigned i = 0; i < nth && i < 512; i++) {
                thread_basic_info_data_t bi; mach_msg_type_number_t c = THREAD_BASIC_INFO_COUNT;
                if (thread_info(th[i], THREAD_BASIC_INFO, (thread_info_t)&bi, &c)) continue;
                unsigned long long t = bi.user_time.seconds * 1000000ULL + bi.user_time.microseconds;
                t0[i] = pass ? t - t0[i] : t;
            }
            if (!pass) usleep(300000);
        }
        want = 0; for (unsigned i = 1; i < nth && i < 512; i++) if (t0[i] > t0[want]) want = i;
    }
    thread_t t = th[want];
    unsigned last = 0; mach_vm_size_t got = 0;
    if (mach_vm_read_overwrite(task, ctr, 4, (mach_vm_address_t)&last, &got)) { fprintf(stderr, "cannot read counter\n"); return 1; }
    double t_frame = now_ms(), t_end = t_frame + secs * 1000; long frames = 0, stalls = 0, total = 0;
    unsigned stk[512];
    fprintf(stderr, "stallprof: thread %d, counter %u\n", want, last);
    while (now_ms() < t_end) {
        usleep(us);
        unsigned c = last; got = 0;
        if (mach_vm_read_overwrite(task, ctr, 4, (mach_vm_address_t)&c, &got)) break;   /* process gone */
        double tn = now_ms();
        if (c != last) {
            double fm = tn - t_frame;
            if (fm >= thr) { report(pid, tn, fm); stalls++; }
            frames += (long)(c - last); last = c; t_frame = tn; ns = 0;
        }
        if (tn - t_frame < arm) continue;
        if (thread_suspend(t)) continue;
        struct { unsigned flavor, count; unsigned long long x[29], fp, lr, sp, pc; unsigned cpsr, pad; } st;
        mach_msg_type_number_t cnt = sizeof st / 4;
        kern_return_t kr = thread_get_state(t, 1, (thread_state_t)&st, &cnt);
        unsigned esp = (unsigned)st.x[4];
        int ok = !kr && st.x[4] < 0x80000000ULL && esp > 0x10000;
        got = 0;
        if (ok && mach_vm_read_overwrite(task, esp, sizeof stk, (mach_vm_address_t)stk, &got)) ok = 0;
        thread_resume(t);
        if (kr || ns >= MAXS) continue;
        total++;
        S *s = &smp[ns++]; s->n = 0; s->npc = st.pc;
        if (ok) for (unsigned i = 0; i < got / 4 && s->n < DEPTH; i++) if (is_ret(stk[i])) s->r[s->n++] = stk[i];
    }
    fprintf(stderr, "stallprof: frames=%ld stalls=%ld samples=%ld\n", frames, stalls, total);
    return 0;
}
