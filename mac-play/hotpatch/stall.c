/* Long-frame diagnostics (v7.3, active only with MUGL_STATS in the private build). Included by mugl.c.
   Every presented frame of STALL_MS or more is logged immediately as
     stall: unix_ms=.. frame=.. ms=.. scene=.. open=n(ms) read=n/KB(ms) tex=n/KB(ms) gen=n | files: ...
   and each stats interval gets an "io:" line with the longest frame. The I/O counters are opt-in
   (C:\mutools\mugl-stall.txt exists): main.exe import slots for CreateFileA/W, ReadFile, glTexImage2D, glTexSubImage2D and
   glGenTextures are then pointed at wrappers that only count and time, then call the original (same IAT method as
   the Sleep hook). The address of the presented-frame counter is written to C:\mutools\mugl-shm.txt ("frames 0x...")
   for the external machprof/stallprof sampler. */
#define STALL_MS 100
typedef HANDLE (WINAPI *PFNcfa)(LPCSTR, DWORD, DWORD, LPSECURITY_ATTRIBUTES, DWORD, DWORD, HANDLE);
typedef HANDLE (WINAPI *PFNcfw)(LPCWSTR, DWORD, DWORD, LPSECURITY_ATTRIBUTES, DWORD, DWORD, HANDLE);
typedef BOOL (WINAPI *PFNrf)(HANDLE, LPVOID, DWORD, LPDWORD, LPOVERLAPPED);
typedef void (WINAPI *PFNti)(GLenum, GLint, GLint, GLsizei, GLsizei, GLint, GLenum, GLenum, const void *);
typedef void (WINAPI *PFNtsi)(GLenum, GLint, GLint, GLint, GLsizei, GLsizei, GLenum, GLenum, const void *);
typedef void (WINAPI *PFNgt)(GLsizei, GLuint *);
static PFNcfa sv_cfa; static PFNcfw sv_cfw; static PFNrf sv_rf; static PFNti sv_ti; static PFNtsi sv_tsi; static PFNgt sv_gt;
typedef struct { long open, read, tex, gen; long long read_b, tex_b, t_open, t_read, t_tex; } IoCnt;
static IoCnt io_f, io_iv, io_bg; static double io_ms(long long t);   /* this frame (render thread), this stats interval (render thread), other threads */
static char io_names[6][40]; static int io_nnames;
static long long io_last_swap, io_max_frame; static long io_stalls_iv;
static volatile long mugl_presented;   /* presented frames, read by stallprof */
static int io_hooked, io_hooked_off;

static IoCnt *io_cur(void) { return GetCurrentThreadId() == render_tid ? &io_f : &io_bg; }
static long long io_qpc(void) { LARGE_INTEGER t; QueryPerformanceCounter(&t); return t.QuadPart; }
static void io_name(const char *s)
{
    if (GetCurrentThreadId() != render_tid || io_nnames >= 6 || !s) return;
    const char *b = s; for (const char *p = s; *p; p++) if (*p == '\\' || *p == '/') b = p + 1;
    snprintf(io_names[io_nnames++], sizeof io_names[0], "%s", b);
}
static HANDLE WINAPI io_CreateFileA(LPCSTR n, DWORD a, DWORD s, LPSECURITY_ATTRIBUTES sa, DWORD c, DWORD f, HANDLE t)
{
    long long t0 = io_qpc(); HANDLE h = sv_cfa(n, a, s, sa, c, f, t); IoCnt *k = io_cur();
    k->open++; k->t_open += io_qpc() - t0; io_name(n); return h;
}
static HANDLE WINAPI io_CreateFileW(LPCWSTR n, DWORD a, DWORD s, LPSECURITY_ATTRIBUTES sa, DWORD c, DWORD f, HANDLE t)
{
    long long t0 = io_qpc(); HANDLE h = sv_cfw(n, a, s, sa, c, f, t); IoCnt *k = io_cur();
    k->open++; k->t_open += io_qpc() - t0;
    char nb[260] = ""; if (n) WideCharToMultiByte(CP_ACP, 0, n, -1, nb, sizeof nb, NULL, NULL); io_name(nb); return h;
}
static BOOL WINAPI io_ReadFile(HANDLE h, LPVOID b, DWORD n, LPDWORD got, LPOVERLAPPED o)
{
    long long t0 = io_qpc(); BOOL r = sv_rf(h, b, n, got, o); IoCnt *k = io_cur();
    k->read++; k->read_b += got ? *got : n; k->t_read += io_qpc() - t0; return r;
}
static void WINAPI io_TexImage2D(GLenum tg, GLint l, GLint fmt, GLsizei w, GLsizei h, GLint b, GLenum f, GLenum ty, const void *p)
{
    long long t0 = io_qpc(); sv_ti(tg, l, fmt, w, h, b, f, ty, p); IoCnt *k = io_cur();
    k->tex++; k->tex_b += (long long)w * h * 4; k->t_tex += io_qpc() - t0;
}
static void WINAPI io_TexSubImage2D(GLenum tg, GLint l, GLint x, GLint y, GLsizei w, GLsizei h, GLenum f, GLenum ty, const void *p)
{
    long long t0 = io_qpc(); sv_tsi(tg, l, x, y, w, h, f, ty, p); IoCnt *k = io_cur();
    k->tex++; k->tex_b += (long long)w * h * 4; k->t_tex += io_qpc() - t0;
}
static void WINAPI io_GenTextures(GLsizei n, GLuint *t) { sv_gt(n, t); io_cur()->gen += n; }

/* v7.6: more timed import slots (same opt-in), for the remaining map-load time: file mappings, handles, sizes and
   seeks, attributes and searches, virtual memory, waits, critical sections, heap and IsBadReadPtr. Per frame the five
   most expensive are appended to the stall line ("api: name=n/ms"). */
enum { AP_CLOSE, AP_CFM, AP_MAP, AP_UNMAP, AP_FSIZE, AP_FSIZEX, AP_SEEK, AP_ATTR, AP_FIND, AP_VALLOC, AP_VFREE, AP_WAIT, AP_ENTER,
       AP_LEAVE, AP_HALLOC, AP_HFREE, AP_BADREAD, AP_FTYPE, AP_N };
static const char *const ap_names[AP_N] = {"CloseHandle", "CreateFileMappingA", "MapViewOfFile", "UnmapViewOfFile", "GetFileSize",
    "GetFileSizeEx", "SetFilePointer", "GetFileAttributesA", "FindFirstFileA", "VirtualAlloc", "VirtualFree", "WaitForSingleObject",
    "RtlEnterCriticalSection", "RtlLeaveCriticalSection", "RtlAllocateHeap", "HeapFree", "IsBadReadPtr", "GetFileType"};
static void *ap_real[AP_N]; static long ap_n[AP_N], ap_niv[AP_N]; static long long ap_t[AP_N], ap_tiv[AP_N];
#define AP_HOOK(i, R, name, P, A) static R WINAPI ap_##name P { \
    if (GetCurrentThreadId() != render_tid) return ((R (WINAPI *)P)ap_real[i]) A; \
    long long t0 = io_qpc(); R r = ((R (WINAPI *)P)ap_real[i]) A; ap_t[i] += io_qpc() - t0; ap_n[i]++; return r; }
#define AP_HOOKV(i, name, P, A) static void WINAPI ap_##name P { \
    if (GetCurrentThreadId() != render_tid) { ((void (WINAPI *)P)ap_real[i]) A; return; } \
    long long t0 = io_qpc(); ((void (WINAPI *)P)ap_real[i]) A; ap_t[i] += io_qpc() - t0; ap_n[i]++; }
AP_HOOK(AP_CLOSE, BOOL, CloseHandle, (HANDLE h), (h))
AP_HOOK(AP_CFM, HANDLE, CreateFileMappingA, (HANDLE h, LPSECURITY_ATTRIBUTES a, DWORD p, DWORD hi, DWORD lo, LPCSTR n), (h, a, p, hi, lo, n))
AP_HOOK(AP_MAP, LPVOID, MapViewOfFile, (HANDLE h, DWORD a, DWORD hi, DWORD lo, SIZE_T n), (h, a, hi, lo, n))
AP_HOOK(AP_UNMAP, BOOL, UnmapViewOfFile, (LPCVOID p), (p))
AP_HOOK(AP_FSIZE, DWORD, GetFileSize, (HANDLE h, LPDWORD hi), (h, hi))
AP_HOOK(AP_FSIZEX, BOOL, GetFileSizeEx, (HANDLE h, PLARGE_INTEGER s), (h, s))
AP_HOOK(AP_SEEK, DWORD, SetFilePointer, (HANDLE h, LONG d, PLONG hi, DWORD m), (h, d, hi, m))
AP_HOOK(AP_ATTR, DWORD, GetFileAttributesA, (LPCSTR n), (n))
AP_HOOK(AP_FIND, HANDLE, FindFirstFileA, (LPCSTR n, LPWIN32_FIND_DATAA d), (n, d))
AP_HOOK(AP_VALLOC, LPVOID, VirtualAlloc, (LPVOID a, SIZE_T n, DWORD t, DWORD p), (a, n, t, p))
AP_HOOK(AP_VFREE, BOOL, VirtualFree, (LPVOID a, SIZE_T n, DWORD t), (a, n, t))
AP_HOOK(AP_WAIT, DWORD, WaitForSingleObject, (HANDLE h, DWORD ms), (h, ms))
/* callers of RtlEnterCriticalSection on the render thread (return addresses), for the stall line */
#define AP_CH 512
static uint32_t ap_ca[AP_CH]; static long ap_cn[AP_CH]; static int ap_trace_callers = 1;
/* First return address on the stack (above our frame) that lies in main.exe game code below the statically linked
   libraries (0x018b0000) and follows a call instruction: the game function behind a CRT/heap call. */
static uint32_t ap_game_caller(const uint32_t *sp)
{
    for (int i = 0; i < 48; i++) {
        uint32_t v = sp[i];
        if (v < 0x00401010 || v >= 0x018b0000) continue;
        const unsigned char *q = (const unsigned char *)(uintptr_t)v;
        if (q[-5] == 0xE8 || (q[-6] == 0xFF && q[-5] == 0x15) || (q[-2] == 0xFF && (q[-1] & 0xF8) == 0xD0) ||
            (q[-3] == 0xFF && (q[-2] & 0xF8) == 0x50)) return v;
    }
    return 0;
}
static void ap_count_caller(uint32_t ra)
{
    uint32_t h = (ra * 2654435761u) >> 23;
    for (int k = 0; k < 8; k++, h = (h + 1) & (AP_CH - 1)) if (!ap_ca[h] || ap_ca[h] == ra) { ap_ca[h] = ra; ap_cn[h]++; break; }
}
static void WINAPI ap_RtlEnterCriticalSection(void *c)
{
    if (GetCurrentThreadId() != render_tid) { ((void (WINAPI *)(void *))ap_real[AP_ENTER])(c); return; }
    if (ap_trace_callers) ap_count_caller(ap_game_caller((const uint32_t *)__builtin_frame_address(0) + 2));
    long long t0 = io_qpc(); ((void (WINAPI *)(void *))ap_real[AP_ENTER])(c); ap_t[AP_ENTER] += io_qpc() - t0; ap_n[AP_ENTER]++;
}
static void ap_callers(FILE *f)
{
    for (int k = 0; k < 10; k++) {
        int b = -1; for (int i = 0; i < AP_CH; i++) if (ap_cn[i] && (b < 0 || ap_cn[i] > ap_cn[b])) b = i;
        if (b < 0) break;
        fprintf(f, " %08x=%ld", ap_ca[b], ap_cn[b]); ap_cn[b] = -ap_cn[b];
    }
    memset(ap_ca, 0, sizeof ap_ca); memset(ap_cn, 0, sizeof ap_cn);
}
AP_HOOKV(AP_LEAVE, RtlLeaveCriticalSection, (void *c), (c))
static LPVOID WINAPI ap_RtlAllocateHeap(HANDLE h, ULONG f, SIZE_T n)
{
    if (GetCurrentThreadId() != render_tid) return ((LPVOID (WINAPI *)(HANDLE, ULONG, SIZE_T))ap_real[AP_HALLOC])(h, f, n);
    if (ap_trace_callers) ap_count_caller(ap_game_caller((const uint32_t *)__builtin_frame_address(0) + 2) | 1);   /* odd: heap */
    long long t0 = io_qpc(); LPVOID r = ((LPVOID (WINAPI *)(HANDLE, ULONG, SIZE_T))ap_real[AP_HALLOC])(h, f, n);
    ap_t[AP_HALLOC] += io_qpc() - t0; ap_n[AP_HALLOC]++; return r;
}
AP_HOOK(AP_HFREE, BOOL, HeapFree, (HANDLE h, DWORD f, LPVOID p), (h, f, p))
AP_HOOK(AP_BADREAD, BOOL, IsBadReadPtr, (const void *p, UINT_PTR n), (p, n))
AP_HOOK(AP_FTYPE, DWORD, GetFileType, (HANDLE h), (h))
static void *const ap_hooks[AP_N] = {(void *)ap_CloseHandle, (void *)ap_CreateFileMappingA, (void *)ap_MapViewOfFile, (void *)ap_UnmapViewOfFile,
    (void *)ap_GetFileSize, (void *)ap_GetFileSizeEx, (void *)ap_SetFilePointer, (void *)ap_GetFileAttributesA, (void *)ap_FindFirstFileA,
    (void *)ap_VirtualAlloc, (void *)ap_VirtualFree, (void *)ap_WaitForSingleObject, (void *)ap_RtlEnterCriticalSection,
    (void *)ap_RtlLeaveCriticalSection, (void *)ap_RtlAllocateHeap, (void *)ap_HeapFree, (void *)ap_IsBadReadPtr, (void *)ap_GetFileType};
static void ap_print(FILE *f, const long *n, const long long *t)
{
    int used[AP_N] = {0};
    for (int k = 0; k < 5; k++) {
        int b = -1;
        for (int i = 0; i < AP_N; i++) if (!used[i] && n[i] && (b < 0 || t[i] > t[b])) b = i;
        if (b < 0) break;
        used[b] = 1; fprintf(f, " %s=%ld/%.1fms", ap_names[b], n[b], io_ms(t[b]));
    }
}

/* Point every main.exe import slot holding one of fns[] at the matching hook; returns slots changed. */
static int iat_hook(void *const *fns, void *const *hooks, void **saved, int nf)
{
    int changed = 0;
    for (void **p = (void **)0x01a7c000; p < (void **)0x01a7e000; p++) {
        MEMORY_BASIC_INFORMATION mi;
        if (((size_t)p & 0xfff) == 0 && (!VirtualQuery(p, &mi, sizeof mi) || mi.State != MEM_COMMIT)) break;
        for (int i = 0; i < nf; i++) {
            if (!fns[i] || *p != fns[i]) continue;
            DWORD old;
            if (VirtualProtect(p, 4, PAGE_READWRITE, &old)) { saved[i] = *p; *p = hooks[i]; VirtualProtect(p, 4, old, &old); changed++; }
        }
    }
    return changed;
}
static void io_install(HMODULE self)
{
    if (io_hooked || io_hooked_off || !st_file) return;
    io_hooked = 1;
    DWORD fa = GetFileAttributesA("C:\\mutools\\mugl-stall.txt");   /* opt-in: the import-slot counters are diagnostic */
    if (fa == INVALID_FILE_ATTRIBUTES) { io_hooked = 0; io_hooked_off = 1; return; }
    HMODULE k32 = GetModuleHandleA("kernel32.dll"), kb = GetModuleHandleA("kernelbase.dll");
    void *fns[9] = { (void *)GetProcAddress(k32, "CreateFileA"), (void *)GetProcAddress(kb, "CreateFileA"),
                     (void *)GetProcAddress(k32, "CreateFileW"), (void *)GetProcAddress(kb, "CreateFileW"),
                     (void *)GetProcAddress(k32, "ReadFile"), (void *)GetProcAddress(kb, "ReadFile"),
                     (void *)GetProcAddress(self, "glTexImage2D"), (void *)GetProcAddress(self, "glTexSubImage2D"),
                     (void *)GetProcAddress(self, "glGenTextures") };
    void *hooks[9] = { (void *)io_CreateFileA, (void *)io_CreateFileA, (void *)io_CreateFileW, (void *)io_CreateFileW,
                       (void *)io_ReadFile, (void *)io_ReadFile, (void *)io_TexImage2D, (void *)io_TexSubImage2D, (void *)io_GenTextures };
    void *saved[9] = {0};
    int n = iat_hook(fns, hooks, saved, 9);
    sv_cfa = (PFNcfa)(saved[0] ? saved[0] : saved[1]); sv_cfw = (PFNcfw)(saved[2] ? saved[2] : saved[3]);
    sv_rf = (PFNrf)(saved[4] ? saved[4] : saved[5]); sv_ti = (PFNti)saved[6]; sv_tsi = (PFNtsi)saved[7]; sv_gt = (PFNgt)saved[8];
    {   /* v7.6 timed slots: the export of kernel32, kernelbase or ntdll that main.exe imports */
        HMODULE nt = GetModuleHandleA("ntdll.dll");
        int na = 0;
        for (int i = 0; i < AP_N; i++) {
            void *cand[3] = { (void *)GetProcAddress(k32, ap_names[i]), (void *)GetProcAddress(kb, ap_names[i]), (void *)GetProcAddress(nt, ap_names[i]) };
            for (int c = 0; c < 3; c++) {
                if (!cand[c]) continue;
                void *saved_one = NULL; int got = iat_hook(&cand[c], &ap_hooks[i], &saved_one, 1);
                if (got) { ap_real[i] = saved_one; na += got; break; }
            }
        }
        fprintf(st_file, "api hooks: %d slots\n", na);
    }
    fprintf(st_file, "io hooks: %d slots (CreateFileA %d W %d ReadFile %d TexImage2D %d TexSubImage2D %d GenTextures %d)\n", n,
            sv_cfa != NULL, sv_cfw != NULL, sv_rf != NULL, sv_ti != NULL, sv_tsi != NULL, sv_gt != NULL);
    fflush(st_file);
}
static void io_publish(void)
{
    FILE *f = fopen("C:\\mutools\\mugl-shm.txt", "w");
    if (f) { fprintf(f, "frames %p\n", (void *)&mugl_presented); fclose(f); }
}
static double io_ms(long long t) { return qpf.QuadPart ? t * 1000.0 / qpf.QuadPart : 0.0; }
static void io_add(IoCnt *d, const IoCnt *s)
{
    d->open += s->open; d->read += s->read; d->tex += s->tex; d->gen += s->gen;
    d->read_b += s->read_b; d->tex_b += s->tex_b; d->t_open += s->t_open; d->t_read += s->t_read; d->t_tex += s->t_tex;
}
/* Called at the start of every wglSwapBuffers (render thread). */
static void io_frame_end(void)
{
    mugl_presented++;
    if (!st_file || !qpf.QuadPart) return;
    long long now = io_qpc();
    if (io_last_swap) {
        long long dt = now - io_last_swap;
        if (dt > io_max_frame) io_max_frame = dt;
        if (dt * 1000 >= (long long)STALL_MS * qpf.QuadPart) {
            FILETIME ft; GetSystemTimeAsFileTime(&ft);
            unsigned long long u = ((unsigned long long)ft.dwHighDateTime << 32 | ft.dwLowDateTime) / 10000 - 11644473600000ULL;
            fprintf(st_file, "stall: unix_ms=%llu frame=%ld ms=%.1f scene=%d open=%ld(%.1fms) read=%ld/%lldKB(%.1fms) tex=%ld/%lldKB(%.1fms) gen=%ld |",
                    u, total_frames, io_ms(dt), MUGL_PRIVATE_TABLES && mugl_client ? *(volatile int *)0x01d1df70 : -1, io_f.open, io_ms(io_f.t_open), io_f.read,
                    io_f.read_b / 1024, io_ms(io_f.t_read), io_f.tex, io_f.tex_b / 1024, io_ms(io_f.t_tex), io_f.gen);
            for (int i = 0; i < io_nnames; i++) fprintf(st_file, " %s", io_names[i]);
            if (io_hooked) { fprintf(st_file, " | api:"); ap_print(st_file, ap_n, ap_t); fprintf(st_file, " | game callers (odd = heap):"); ap_callers(st_file); }
            fprintf(st_file, "\n"); fflush(st_file);
            io_stalls_iv++;
        }
    }
    io_last_swap = now;
    io_add(&io_iv, &io_f); memset(&io_f, 0, sizeof io_f); io_nnames = 0;
    for (int i = 0; i < AP_N; i++) { ap_niv[i] += ap_n[i]; ap_tiv[i] += ap_t[i]; ap_n[i] = 0; ap_t[i] = 0; }
}
/* Called from stats_tick: one totals line per interval. */
static void io_stats(FILE *f)
{
    if (!io_hooked) { fprintf(f, "io: max_frame=%.1fms stalls=%ld\n", io_ms(io_max_frame), io_stalls_iv); io_max_frame = 0; io_stalls_iv = 0; return; }
    fprintf(f, "io: max_frame=%.1fms stalls=%ld open=%ld(%.1fms) read=%ld/%lldKB(%.1fms) tex=%ld/%lldKB(%.1fms) gen=%ld | bg open=%ld read=%ld/%lldKB tex=%ld\n",
            io_ms(io_max_frame), io_stalls_iv, io_iv.open, io_ms(io_iv.t_open), io_iv.read, io_iv.read_b / 1024, io_ms(io_iv.t_read),
            io_iv.tex, io_iv.tex_b / 1024, io_ms(io_iv.t_tex), io_iv.gen, io_bg.open, io_bg.read, io_bg.read_b / 1024, io_bg.tex);
    fprintf(f, "  api:"); ap_print(f, ap_niv, ap_tiv); fprintf(f, " | game callers (odd = heap):"); ap_callers(f); fprintf(f, "\n");
    memset(ap_niv, 0, sizeof ap_niv); memset(ap_tiv, 0, sizeof ap_tiv);
    memset(&io_iv, 0, sizeof io_iv); memset(&io_bg, 0, sizeof io_bg); io_max_frame = 0; io_stalls_iv = 0;
}

/* GL stream trace control. Line format: "G mode caller" glBegin, "/ n" glEnd with the block's vertex count,
   "DRAW mode n fmt=.." a batch submitted by mugl, "E/D cap", "T tex", "B s d", "M mask", "A func ref", "Z func"
   (" =" marks a call dropped by the redundant-state filter; E/D/T carry the caller address), "S name" any other
   export, "X name" an extension, "push"/"pop"/"loadidentity", "F frame" at each wglSwapBuffers. */
static DWORD tr_poll;
static void tr_check(void)
{
    DWORD now = GetTickCount();
    if (tr_on || now - tr_poll < 1000) return;
    tr_poll = now;
    FILE *f = fopen("C:\\mutools\\mugl-trace.txt", "r");
    if (!f) return;
    int n = 1; if (fscanf(f, "%d", &n) != 1) n = 1; fclose(f);
    DeleteFileA("C:\\mutools\\mugl-trace.txt");
    tr_frames = n < 1 ? 1 : n > 20 ? 20 : n; tr_len = 0; tr_on = 1; update_busy();
}
static void tr_frame_end(void)
{
    if (!tr_on) return;
    TR("F %ld\n", total_frames);
    if (--tr_frames > 0) return;
    tr_on = 0; update_busy();
    char name[64]; snprintf(name, sizeof name, "C:\\mutools\\mugl-trace-%ld.txt", total_frames);
    FILE *f = fopen(name, "wb");
    if (f) { fwrite(tr_buf, 1, tr_len, f); fclose(f); }
    if (st_file) { fprintf(st_file, "trace written: %s (%lu bytes)\n", name, (unsigned long)tr_len); fflush(st_file); }
}

/* Render-thread priority (v7.3). The wineserver maps Win32 thread priorities to Mach precedence on macOS. With other
   processes loading the four performance cores, the game thread at normal priority was preempted and moved around:
   in a same-session A/B at load average ~14 the spawn view ran 14 fps / 70 ms work with 5-9 frames over 100 ms per
   15 s, and 24.5 fps / 37 ms with none at THREAD_PRIORITY_HIGHEST. Default 2 (HIGHEST); C:\mutools\mugl-prio.txt
   overrides it (-2..2; 0 = normal; TIME_CRITICAL is refused). Polled every 2 s. */
static int prio_cur, prio_poll0; static DWORD prio_poll;
static void prio_check(void)
{
    DWORD now = GetTickCount();
    if (now - prio_poll < 2000) return;
    prio_poll = now;
    int p = 2; FILE *f = fopen("C:\\mutools\\mugl-prio.txt", "r");
    if (f) { if (fscanf(f, "%d", &p) != 1) p = 2; fclose(f); }
    if (p < -2 || p > 2) p = 0;
    if (p == prio_cur && prio_poll0) return;
    prio_poll0 = 1;
    BOOL ok = SetThreadPriority(GetCurrentThread(), p);
    if (ok) prio_cur = p;
    if (st_file) { fprintf(st_file, "render thread priority %d: %s (now %d)\n", p, ok ? "set" : "failed", GetThreadPriority(GetCurrentThread())); fflush(st_file); }
}
