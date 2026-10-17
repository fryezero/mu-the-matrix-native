/* SPDX-License-Identifier: MIT */
/* eipprof: poor-man's sampling profiler for a 32-bit Wine process.
   Usage: eipprof.exe <exe-name> <seconds> <out.txt>
   Periodically suspends each thread, reads EIP, resumes; writes per-thread
   module histograms and top EIP buckets (64-byte granularity). */
#include <windows.h>
#include <tlhelp32.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct { DWORD base, size; char name[64]; } Mod;
static Mod mods[512]; static int nmods;
typedef struct { DWORD tid; HANDLE h; long samples, inwait; } Thr;
static Thr thr[256]; static int nthr;
typedef struct { DWORD key; long n; int t; } Bucket;
#define NB 262144
static Bucket bk[NB];
static long dropped;

static void load_mods(DWORD pid) {
    HANDLE s = CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid);
    MODULEENTRY32 me = { sizeof me }; nmods = 0;
    if (s == INVALID_HANDLE_VALUE) return;
    for (BOOL ok = Module32First(s, &me); ok && nmods < 512; ok = Module32Next(s, &me)) {
        mods[nmods].base = (DWORD)(ULONG_PTR)me.modBaseAddr; mods[nmods].size = me.modBaseSize;
        strncpy(mods[nmods].name, me.szModule, 63); nmods++;
    }
    CloseHandle(s);
}
static const char *modof(DWORD eip, DWORD *off) {
    for (int i = 0; i < nmods; i++) if (eip >= mods[i].base && eip < mods[i].base + mods[i].size) { *off = eip - mods[i].base; return mods[i].name; }
    *off = eip; return "<anon>";
}
static void add(DWORD eip, int t) {
    DWORD key = eip & ~63u; unsigned h = (key * 2654435761u ^ t) % NB;
    unsigned probes = 0;
    while (bk[h].n && (bk[h].key != key || bk[h].t != t)) {
        if (++probes == NB) { dropped++; return; }
        h = (h + 1) % NB;
    }
    bk[h].key = key; bk[h].t = t; bk[h].n++;
}
static int cmpb(const void *a, const void *b) { return ((Bucket *)b)->n - ((Bucket *)a)->n; }

int main(int argc, char **argv) {
    if (argc < 4) { printf("usage: eipprof exe seconds out\n"); return 1; }
    int seconds = atoi(argv[2]);
    if (seconds <= 0 || seconds > 3600) { fprintf(stderr, "Use 1..3600 seconds\n"); return 1; }
    FILE *f = fopen(argv[3], "w");
    if (!f) { perror("profile output"); return 1; }
    DWORD pid = 0;
    HANDLE s = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0); PROCESSENTRY32 pe = { sizeof pe };
    for (BOOL ok = Process32First(s, &pe); ok; ok = Process32Next(s, &pe)) if (!_stricmp(pe.szExeFile, argv[1])) pid = pe.th32ProcessID;
    CloseHandle(s);
    if (!pid) { printf("process %s not found\n", argv[1]); return 2; }
    load_mods(pid);
    s = CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0); THREADENTRY32 te = { sizeof te };
    for (BOOL ok = Thread32First(s, &te); ok; ok = Thread32Next(s, &te))
        if (te.th32OwnerProcessID == pid && nthr < 256) {
            HANDLE h = OpenThread(THREAD_SUSPEND_RESUME | THREAD_GET_CONTEXT | THREAD_QUERY_INFORMATION, FALSE, te.th32ThreadID);
            if (h) { thr[nthr].tid = te.th32ThreadID; thr[nthr].h = h; nthr++; }
        }
    CloseHandle(s);
    printf("pid %lu: %d modules, %d threads\n", pid, nmods, nthr);
    DWORD start = GetTickCount(); long rounds = 0;
    while (GetTickCount() - start < (DWORD)seconds * 1000) {
        for (int i = 0; i < nthr; i++) {
            if (SuspendThread(thr[i].h) == (DWORD)-1) continue;
            CONTEXT c; c.ContextFlags = CONTEXT_CONTROL;
            BOOL got = GetThreadContext(thr[i].h, &c);
            ResumeThread(thr[i].h);
            if (got) { thr[i].samples++; add(c.Eip, i); }
        }
        rounds++; Sleep(1);
    }
    fprintf(f, "rounds %ld dropped %ld\n", rounds, dropped);
    for (int i = 0; i < nmods; i++) fprintf(f, "MOD %08lx %08lx %s\n", mods[i].base, mods[i].size, mods[i].name);
    int used = 0; for (int i = 0; i < NB; i++) if (bk[i].n) bk[used++] = bk[i];
    qsort(bk, used, sizeof(Bucket), cmpb);
    /* per-thread: top buckets; the busiest thread is the one with the most distinct hot code */
    for (int t = 0; t < nthr; t++) {
        long tot = 0, top = 0; int distinct = 0;
        for (int i = 0; i < used; i++) if (bk[i].t == t) { tot += bk[i].n; distinct++; if (bk[i].n > top) top = bk[i].n; }
        fprintf(f, "THREAD %d tid %04lx samples %ld distinct %d topshare %.2f\n", t, thr[t].tid, tot, distinct, tot ? (double)top / tot : 0);
    }
    for (int i = 0; i < used && i < 4000; i++) { DWORD off; const char *m = modof(bk[i].key, &off); fprintf(f, "B t%d %08lx %s+%lx %ld\n", bk[i].t, bk[i].key, m, off, bk[i].n); }
    for (int i = 0; i < nthr; i++) CloseHandle(thr[i].h);
    fclose(f); printf("wrote %s (%d buckets)\n", argv[3], used);
    return 0;
}
