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
static IoCnt io_f, io_iv, io_bg;   /* this frame (render thread), this stats interval (render thread), other threads */
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
            fprintf(st_file, "\n"); fflush(st_file);
            io_stalls_iv++;
        }
    }
    io_last_swap = now;
    io_add(&io_iv, &io_f); memset(&io_f, 0, sizeof io_f); io_nnames = 0;
}
/* Called from stats_tick: one totals line per interval. */
static void io_stats(FILE *f)
{
    if (!io_hooked) { fprintf(f, "io: max_frame=%.1fms stalls=%ld\n", io_ms(io_max_frame), io_stalls_iv); io_max_frame = 0; io_stalls_iv = 0; return; }
    fprintf(f, "io: max_frame=%.1fms stalls=%ld open=%ld(%.1fms) read=%ld/%lldKB(%.1fms) tex=%ld/%lldKB(%.1fms) gen=%ld | bg open=%ld read=%ld/%lldKB tex=%ld\n",
            io_ms(io_max_frame), io_stalls_iv, io_iv.open, io_ms(io_iv.t_open), io_iv.read, io_iv.read_b / 1024, io_ms(io_iv.t_read),
            io_iv.tex, io_iv.tex_b / 1024, io_ms(io_iv.t_tex), io_iv.gen, io_bg.open, io_bg.read, io_bg.read_b / 1024, io_bg.tex);
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
