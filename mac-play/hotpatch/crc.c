/* Native CRC-32 update (v7.6, MAC-PERF-010; bits 268435456 and 536870912). Included by mugl.c.

   0x00aa2c62 is a thiscall table-driven CRC update, (this, buf, len, &crc), ret 0xc: with the table pointer at *this,
   crc = T[(crc ^ byte) & 0xff] ^ (crc >> 8) for each byte, the result stored back through &crc. The client runs it
   over whole files during map loads (about 9% of a 2.9 s map entry in stallprof, one byte per iteration under
   Rosetta). Bit 268435456 jumps from its entry (5 of the 6 pinned prologue bytes, `crc_prologue`) to cr_update,
   which computes the same value eight bytes at a time (slicing-by-8). The slicing tables are derived from the
   client's own table: Tk[i] = (Tk-1[i] >> 8) ^ T0[Tk-1[i] & 0xff]. That is exact for any table that is linear over
   GF(2) (T[a ^ b] = T[a] ^ T[b], as every CRC table is), which is checked whenever the table differs from the last one
   seen; another table, or a buffer shorter than 64 bytes, runs the byte loop. The return value (eax = &crc) is kept.
   Bit 536870912 (verification) also runs the original through a trampoline on a copy of the CRC and compares. */
#define CR_ENTRY 0x00aa2c62
/* crc_prologue[6] (push ebp; mov ebp,esp; push ecx; push ecx; push ebx) comes from meshdraw-orig.h */
typedef uint32_t *(__attribute__((thiscall)) *cr_fn)(void *, const unsigned char *, uint32_t, uint32_t *);
static cr_fn cr_orig;
static uint32_t cr_t[8][256], cr_base[256];
static const uint32_t *cr_src; static int cr_linear, cr_verify;
static long cr_calls, cr_fast, cr_checked, cr_bad; static long long cr_bytes, cr_ticks, cr_oticks, cr_tot_checked, cr_tot_bad;

static int cr_prepare(const uint32_t *t)
{
    if (t == cr_src && !memcmp(cr_base, t, sizeof cr_base)) return cr_linear;
    memcpy(cr_base, t, sizeof cr_base); cr_src = t;
    cr_linear = cr_base[0] == 0;
    for (int i = 1; i < 256 && cr_linear; i++) {
        uint32_t x = 0;
        for (int k = 0; k < 8; k++) if (i >> k & 1) x ^= cr_base[1 << k];
        if (x != cr_base[i]) cr_linear = 0;
    }
    if (cr_linear) {
        memcpy(cr_t[0], cr_base, sizeof cr_base);
        for (int k = 1; k < 8; k++) for (int i = 0; i < 256; i++) cr_t[k][i] = (cr_t[k - 1][i] >> 8) ^ cr_t[0][cr_t[k - 1][i] & 0xff];
    }
    return cr_linear;
}

static uint32_t cr_bytes_loop(const uint32_t *t, uint32_t c, const unsigned char *p, uint32_t n)
{
    while (n--) c = (c >> 8) ^ t[(c ^ *p++) & 0xff];
    return c;
}

static uint32_t cr_compute(const uint32_t *t, uint32_t c, const unsigned char *p, uint32_t n)
{
    if (n < 64 || !cr_prepare(t)) return cr_bytes_loop(t, c, p, n);
    cr_fast++;
    while (n && ((uintptr_t)p & 3)) { c = (c >> 8) ^ cr_t[0][(c ^ *p++) & 0xff]; n--; }
    while (n >= 8) {
        uint32_t a = *(const uint32_t *)p ^ c, b = *(const uint32_t *)(p + 4);
        c = cr_t[7][a & 0xff] ^ cr_t[6][(a >> 8) & 0xff] ^ cr_t[5][(a >> 16) & 0xff] ^ cr_t[4][a >> 24] ^
            cr_t[3][b & 0xff] ^ cr_t[2][(b >> 8) & 0xff] ^ cr_t[1][(b >> 16) & 0xff] ^ cr_t[0][b >> 24];
        p += 8; n -= 8;
    }
    while (n--) c = (c >> 8) ^ cr_t[0][(c ^ *p++) & 0xff];
    return c;
}

static uint32_t *__attribute__((thiscall)) cr_update(void *self, const unsigned char *buf, uint32_t len, uint32_t *pcrc)
{
    const uint32_t *t = *(const uint32_t *const *)self;
    long long t0 = io_qpc();
    uint32_t in = *pcrc, c = cr_compute(t, in, buf, len);
    cr_ticks += io_qpc() - t0; cr_calls++; cr_bytes += len;
    if (cr_verify) {
        uint32_t ref = in;
        long long t1 = io_qpc();
        cr_orig(self, buf, len, &ref);
        cr_oticks += io_qpc() - t1;
        cr_checked++; cr_tot_checked++;
        if (ref != c) {
            cr_bad++; cr_tot_bad++;
            if (cr_tot_bad <= 20 && st_file) { fprintf(st_file, "crc MISMATCH: len %u native %08x original %08x\n", len, c, ref); fflush(st_file); }
            c = ref;
        }
    }
    *pcrc = c;
    return pcrc;
}

static int cr_install(int on, int verify)
{
    if (!cr_orig) {   /* trampoline: the five prologue instructions (6 bytes), then jmp to the rest */
        unsigned char *t = VirtualAlloc(NULL, 32, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
        if (!t) return 0;
        memcpy(t, crc_prologue, 6);
        t[6] = 0xE9; *(int *)(t + 7) = (int)(((unsigned char *)CR_ENTRY + 6) - (t + 11));
        FlushInstructionCache(GetCurrentProcess(), t, 32);
        cr_orig = (cr_fn)t;
    }
    cr_verify = verify;
    unsigned char j[5]; j[0] = 0xE9; *(int *)(j + 1) = (int)((unsigned char *)cr_update - ((unsigned char *)CR_ENTRY + 5));
    return md_patch_bytes(CR_ENTRY, crc_prologue, j, 5, on, "crc entry");
}

static void cr_stats(FILE *f)
{
    if (!cr_calls) return;
    fprintf(f, "crc calls=%ld sliced=%ld bytes=%lldKB native=%.1fms", cr_calls, cr_fast, cr_bytes / 1024, qpf.QuadPart ? cr_ticks * 1000.0 / qpf.QuadPart : 0.0);
    if (cr_verify || cr_tot_checked) fprintf(f, " original=%.1fms checked=%ld mismatches=%ld total checked=%lld mismatches=%lld",
                                             qpf.QuadPart ? cr_oticks * 1000.0 / qpf.QuadPart : 0.0, cr_checked, cr_bad, cr_tot_checked, cr_tot_bad);
    fprintf(f, "\n");
    cr_calls = cr_fast = cr_checked = cr_bad = 0; cr_bytes = cr_ticks = cr_oticks = 0;
}
