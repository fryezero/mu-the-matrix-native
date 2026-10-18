/* Native JPEG decode in place of the client's IJG 6b (v7.6, MAC-PERF-010; bits 67108864 and 134217728). Included by
   mugl.c.

   The client links IJG libjpeg 6b statically (jpeg_CreateDecompress version 62, struct size 0x1b0, `boolean` is one
   byte) and its six JPEG loaders (OpenJpeg 0x00c982ea and five others) all use the same call sequence:
   jpeg_stdio_src on a CRT FILE, jpeg_read_header, jpeg_start_decompress, jpeg_read_scanlines one row at a time,
   jpeg_finish_decompress, jpeg_destroy_decompress. The decoder modules are compiled MSVC code running under Rosetta;
   texture-heavy map loads spend most of their CPU time in them.

   Bit 67108864 jumps from the entries of four API routines to the wrappers below (7 pinned prologue bytes each;
   trampolines run the originals) and redirects the jump thunk of jpeg_destroy_decompress:
   - jpeg_read_header: when the source is the client's stdio source and nothing has been read yet, the rest of the file
     is read with the client's own fread into one buffer and put back with the client's fseek (SEEK_CUR). The
     original routine then runs unchanged and reads the header from the file as before.
   - jpeg_start_decompress: if the caller is one of the three loaders that open the file in binary mode ("rb":
     OpenJpeg and two at 0x00a90000), the client's parameters are the library defaults, and the stream is one the
     client's 6b decodes the same way,
     libjpeg-turbo decodes the whole copy (jpegdec.c) and the output fields the callers read are set (output size and
     components, rec_outbuf_height 1, no colormap, output_scanline 0, state DSTATE_SCANNING). Otherwise, or if turbo
     reports any error or warning, the original routine runs and decodes from the file.
   - jpeg_read_scanlines copies the next decoded row; jpeg_finish_decompress keeps 6b's checks (too few scanlines is
     the same error_exit call), calls the source's term_source and the client's jpeg_abort, as 6b does after reaching
     EOI. Calls in other states go to the originals.
   Bit 134217728 (verification): the original routines decode as well, and every row
   the original jpeg_read_scanlines returns is compared with turbo's row; output sizes too. Both decode times are
   summed for the `jpeg:` stats line.
   Only decodes on the render thread are taken (one at a time); others are left to the client. */
#ifdef MUGL_JPEG
#include "jpegdec.h"
#define JP_READ_HEADER 0x018b50a0
#define JP_START 0x018b5480
#define JP_READ_SCANLINES 0x018b53e0
#define JP_FINISH 0x018b4f50
#define JP_DESTROY_THUNK 0x018b4f40   /* jmp jpeg_destroy (0x018b8f30) */
#define JP_DESTROY 0x018b8f30
#define JP_ABORT 0x018b8e90
#define JP_FREAD 0x01989230
#define JP_FSEEK 0x01989dab
#define JP_SRC_INIT 0x018b51a0
#define JP_SRC_FILL 0x018b5120
/* jpeg_decompress_struct (6b, one-byte boolean) and the stdio source manager */
#define CI32(c, o) (*(uint32_t *)((unsigned char *)(c) + (o)))
#define CI8(c, o) (*(unsigned char *)((unsigned char *)(c) + (o)))
enum { O_ERR = 0, O_PROGRESS = 0x08, O_STATE = 0x14, O_SRC = 0x18, O_IMG_W = 0x1c, O_IMG_H = 0x20, O_NCOMP = 0x24, O_JCS = 0x28,
       O_OUT_JCS = 0x2c, O_SCALE_NUM = 0x30, O_SCALE_DEN = 0x34, O_GAMMA = 0x38, O_BUFFERED = 0x40, O_RAW = 0x41, O_DCT = 0x44,
       O_FANCY = 0x48, O_SMOOTH = 0x49, O_QUANT = 0x4a, O_OUT_W = 0x5c, O_OUT_H = 0x60, O_OUT_CC = 0x64, O_OUT_COMPS = 0x68,
       O_REC_OUTBUF = 0x6c, O_NCOLORS = 0x70, O_COLORMAP = 0x74, O_SCANLINE = 0x78, O_PRECISION = 0xc0, O_PROGRESSIVE = 0xc8,
       O_ARITH = 0xc9, O_CCIR = 0x10a };
enum { S_NEXT = 0, S_AVAIL = 4, S_INIT = 8, S_FILL = 0xc, S_TERM = 0x18, S_FILE = 0x1c, S_BUFFER = 0x20, S_START = 0x24 };
enum { DS_START = 200, DS_READY = 202, DS_SCANNING = 205, DS_STOPPING = 210 };
/* jp_rh_orig, jp_sd_orig, jp_rs_orig, jp_fd_orig (7 bytes: push ebp; mov ebp,esp; push esi; mov esi,[ebp+8]) and jp_dt_orig
   (the 5-byte jmp thunk) come from meshdraw-orig.h (targets.json, SHA-256 pinned). */

typedef int (__cdecl *jp_fn1)(void *);
typedef int (__cdecl *jp_fn2)(void *, int);
typedef int (__cdecl *jp_fn3)(void *, unsigned char **, unsigned);
typedef void (__cdecl *jp_void1)(void *);
typedef size_t (__cdecl *jp_fread_fn)(void *, size_t, size_t, void *);
typedef int (__cdecl *jp_fseek_fn)(void *, long, int);
static jp_fn2 jp_rh_tr; static jp_fn1 jp_sd_tr; static jp_fn3 jp_rs_tr; static jp_fn1 jp_fd_tr;
static int jp_on, jp_verify;

typedef struct {
    void *ci; DWORD tid;
    unsigned char *data; unsigned long n;   /* the whole stream (from the position at jpeg_read_header) */
    int native;                              /* rows come from img */
    int check;                               /* verification: compare original rows with img */
} JpSlot;
static JpSlot jp_s;
static MjImg jp_img;
static long jp_n_img, jp_n_native, jp_n_fb[8], jp_n_checked, jp_rows_checked, jp_rows_bad, jp_n_bad;
static long long jp_t_native, jp_t_orig, jp_t_read, jp_bytes;
static long long jp_tot_native, jp_tot_checked, jp_tot_bad;

static void jp_release(void)
{
    if (jp_s.data) free(jp_s.data);
    memset(&jp_s, 0, sizeof jp_s);
}
/* Called whenever the decode on jp_s.ci ends (finish or destroy). */
static void jp_end(void *ci)
{
    if (jp_s.ci && jp_s.ci == ci) jp_release();
}

static int __cdecl jp_read_header(void *ci, int require_image)
{
    unsigned char *src = (unsigned char *)(uintptr_t)CI32(ci, O_SRC);
    if (GetCurrentThreadId() != render_tid) { jp_n_fb[6]++; return jp_rh_tr(ci, require_image); }
    jp_release();   /* a decode that never reached finish or destroy (not seen in the client) */
    uint32_t ret = (uint32_t)(uintptr_t)__builtin_return_address(0);
    if (ret != 0x00c98438 && ret != 0x00a900a3 && ret != 0x00a90263) { jp_n_fb[7]++; return jp_rh_tr(ci, require_image); }
    if (CI32(ci, O_STATE) != DS_START || !src || CI32(src, S_INIT) != JP_SRC_INIT || CI32(src, S_FILL) != JP_SRC_FILL ||
        CI32(src, S_NEXT) != 0 || CI32(src, S_AVAIL) != 0 || !CI32(src, S_FILE) || !CI32(src, S_BUFFER))
        { jp_n_fb[0]++; return jp_rh_tr(ci, require_image); }
    long long t0 = io_qpc();
    void *f = (void *)(uintptr_t)CI32(src, S_FILE);
    unsigned long cap = 1 << 16, n = 0;
    int bad = 0;
    unsigned char *d = malloc(cap);
    if (!d) bad = 1;
    while (!bad) {
        if (cap - n < (1u << 15)) {
            unsigned char *p = cap < (32u << 20) ? realloc(d, cap * 2) : NULL;
            if (!p) { bad = 1; break; }
            d = p; cap *= 2;
        }
        size_t want = cap - n, got = ((jp_fread_fn)JP_FREAD)(d + n, 1, want, f);
        n += got;
        if (got < want) break;
    }
    if (bad || n == 0) {   /* nothing read, allocation failure or too large: put the bytes back */
        if (n) ((jp_fseek_fn)JP_FSEEK)(f, -(long)n, 1);
        free(d); jp_n_fb[0]++; return jp_rh_tr(ci, require_image);
    }
    ((jp_fseek_fn)JP_FSEEK)(f, -(long)n, 1);   /* put the bytes back: the client's header parse reads the file as before */
    jp_s.ci = ci; jp_s.tid = GetCurrentThreadId(); jp_s.data = d; jp_s.n = n;
    jp_t_read += io_qpc() - t0; jp_bytes += n;
    return jp_rh_tr(ci, require_image);
}

static int jp_params_default(void *ci)
{
    return CI32(ci, O_PROGRESS) == 0 && CI32(ci, O_SCALE_NUM) == 1 && CI32(ci, O_SCALE_DEN) == 1 && *(double *)((char *)ci + O_GAMMA) == 1.0 &&
           !CI8(ci, O_BUFFERED) && !CI8(ci, O_RAW) && CI32(ci, O_DCT) == 0 && CI8(ci, O_FANCY) == 1 && CI8(ci, O_SMOOTH) == 1 &&
           !CI8(ci, O_QUANT) && CI32(ci, O_PRECISION) == 8 && !CI8(ci, O_ARITH) && !CI8(ci, O_CCIR) && CI32(ci, O_COLORMAP) == 0;
}

static int __cdecl jp_start(void *ci)
{
    jp_n_img++;
    if (jp_s.ci != ci || jp_s.tid != GetCurrentThreadId() || CI32(ci, O_STATE) != DS_READY || !jp_params_default(ci))
        { jp_n_fb[1]++; return jp_sd_tr(ci); }
    /* Only the loaders that open the file with fopen(..., "rb") (OpenJpeg and the two at 0x00a90000), so our copy is
       byte for byte what the client's source reads. */
    uint32_t ret = (uint32_t)(uintptr_t)__builtin_return_address(0);
    if (ret != 0x00c98446 && ret != 0x00a900bb && ret != 0x00a9027b) { jp_n_fb[7]++; return jp_sd_tr(ci); }
    MjWant w = { (int)CI32(ci, O_IMG_W), (int)CI32(ci, O_IMG_H), (int)CI32(ci, O_NCOMP), (int)CI32(ci, O_JCS), (int)CI32(ci, O_OUT_JCS),
                 CI8(ci, O_PROGRESSIVE) };
    long long t0 = io_qpc();
    int r = mj_decode(jp_s.data, jp_s.n, &w, &jp_img);
    long long t1 = io_qpc();
    if (r != MJ_OK) { jp_n_fb[1 + r]++; return jp_sd_tr(ci); }
    jp_t_native += t1 - t0;
    if (jp_verify) {
        jp_s.check = 1;
        long long t2 = io_qpc();
        int ok = jp_sd_tr(ci);
        jp_t_orig += io_qpc() - t2;
        if ((int)CI32(ci, O_OUT_W) != jp_img.width || (int)CI32(ci, O_OUT_H) != jp_img.height || (int)CI32(ci, O_OUT_COMPS) != jp_img.comps ||
            (int)CI32(ci, O_OUT_CC) != jp_img.out_comps || CI32(ci, O_REC_OUTBUF) != 1) {
            jp_s.check = 0; jp_n_bad++; jp_tot_bad++;
            if (jp_tot_bad <= 20 && st_file) { fprintf(st_file, "jpeg MISMATCH: output %ux%ux%u vs native %dx%dx%d\n", CI32(ci, O_OUT_W), CI32(ci, O_OUT_H),
                                                       CI32(ci, O_OUT_COMPS), jp_img.width, jp_img.height, jp_img.comps); fflush(st_file); }
        }
        return ok;
    }
    CI32(ci, O_OUT_W) = jp_img.width; CI32(ci, O_OUT_H) = jp_img.height;
    CI32(ci, O_OUT_CC) = jp_img.out_comps; CI32(ci, O_OUT_COMPS) = jp_img.comps;
    CI32(ci, O_REC_OUTBUF) = 1; CI32(ci, O_NCOLORS) = 0; CI32(ci, O_COLORMAP) = 0; CI32(ci, O_SCANLINE) = 0;
    CI32(ci, O_STATE) = DS_SCANNING;
    jp_s.native = 1; jp_n_native++; jp_tot_native++;
    return 1;
}

static int __cdecl jp_read_scanlines(void *ci, unsigned char **rows, unsigned max_lines)
{
    if (jp_s.ci == ci && jp_s.native && CI32(ci, O_STATE) == DS_SCANNING) {
        unsigned y = CI32(ci, O_SCANLINE);
        if (y < CI32(ci, O_OUT_H)) {
            unsigned char *pr = (unsigned char *)(uintptr_t)CI32(ci, O_PROGRESS);
            if (pr) { CI32(pr, 4) = y; CI32(pr, 8) = CI32(ci, O_OUT_H); ((jp_void1)(uintptr_t)CI32(pr, 0))(ci); }
            if (max_lines == 0) return 0;
            size_t stride = (size_t)jp_img.width * jp_img.comps;
            memcpy(rows[0], jp_img.pix + y * stride, stride);
            CI32(ci, O_SCANLINE) = y + 1;
            return 1;
        }
    }
    if (jp_s.ci == ci && jp_s.check) {
        unsigned y = CI32(ci, O_SCANLINE);
        long long t0 = io_qpc();
        int got = jp_rs_tr(ci, rows, max_lines);
        jp_t_orig += io_qpc() - t0;
        size_t stride = (size_t)jp_img.width * jp_img.comps;
        for (int k = 0; k < got; k++, y++) {
            jp_rows_checked++;
            if (y >= (unsigned)jp_img.height || memcmp(rows[k], jp_img.pix + y * stride, stride)) {
                jp_rows_bad++;
                if (jp_s.check == 1) { jp_s.check = 2; jp_n_bad++; jp_tot_bad++;
                    if (jp_tot_bad <= 20 && st_file) { fprintf(st_file, "jpeg MISMATCH: %dx%d row %u\n", jp_img.width, jp_img.height, y); fflush(st_file); } }
            }
        }
        return got;
    }
    return jp_rs_tr(ci, rows, max_lines);
}

static int __cdecl jp_finish(void *ci)
{
    if (jp_s.ci == ci && jp_s.native && CI32(ci, O_STATE) == DS_SCANNING) {
        if (CI32(ci, O_SCANLINE) < CI32(ci, O_OUT_H)) {   /* ERREXIT(cinfo, JERR_TOO_LITTLE_DATA) as in 6b */
            unsigned char *err = (unsigned char *)(uintptr_t)CI32(ci, O_ERR);
            CI32(err, 0x14) = 0x43; ((jp_void1)(uintptr_t)CI32(err, 0))(ci);
        }
        CI32(ci, O_STATE) = DS_STOPPING;
        unsigned char *src = (unsigned char *)(uintptr_t)CI32(ci, O_SRC);
        ((jp_void1)(uintptr_t)CI32(src, S_TERM))(ci);
        ((jp_void1)JP_ABORT)(ci);
        jp_end(ci);
        return 1;
    }
    long long t0 = io_qpc();
    int r = jp_fd_tr(ci);
    if (jp_s.ci == ci && jp_s.check) {
        jp_t_orig += io_qpc() - t0;
        if (jp_s.check == 1) jp_n_checked++, jp_tot_checked++;
    }
    jp_end(ci);
    return r;
}

static void __cdecl jp_destroy(void *ci)
{
    jp_end(ci);
    ((jp_void1)JP_DESTROY)(ci);
}

static unsigned char *jp_tramp(const unsigned char *orig, int len, unsigned addr)
{
    unsigned char *t = VirtualAlloc(NULL, 32, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
    if (!t) return NULL;
    memcpy(t, orig, len);
    t[len] = 0xE9; *(int *)(t + len + 1) = (int)(((unsigned char *)(uintptr_t)addr + len) - (t + len + 5));
    FlushInstructionCache(GetCurrentProcess(), t, 32);
    return t;
}
static int jp_patch(unsigned addr, const unsigned char *orig, void *hook, int on, const char *what)
{
    unsigned char j[7]; memcpy(j, orig, 7);
    j[0] = 0xE9; *(int *)(j + 1) = (int)((unsigned char *)hook - ((unsigned char *)(uintptr_t)addr + 5));
    return md_patch_bytes(addr, orig, j, 5, on, what);
}
static int jp_install(int on, int verify)
{
    jp_release();   /* hp_set runs between frames on the render thread, never inside a decode */
    if (!jp_rh_tr) {
        jp_rh_tr = (jp_fn2)jp_tramp(jp_rh_orig, 7, JP_READ_HEADER); jp_sd_tr = (jp_fn1)jp_tramp(jp_sd_orig, 7, JP_START);
        jp_rs_tr = (jp_fn3)jp_tramp(jp_rs_orig, 7, JP_READ_SCANLINES); jp_fd_tr = (jp_fn1)jp_tramp(jp_fd_orig, 7, JP_FINISH);
        if (!jp_rh_tr || !jp_sd_tr || !jp_rs_tr || !jp_fd_tr) { jp_rh_tr = NULL; return 0; }
    }
    /* the destroy thunk must still be the original jmp to jpeg_destroy */
    if (jp_dt_orig[0] != 0xE9 || (unsigned)(JP_DESTROY_THUNK + 5 + *(const int *)(jp_dt_orig + 1)) != JP_DESTROY) return 0;
    jp_verify = verify;
    int n = jp_patch(JP_READ_HEADER, jp_rh_orig, (void *)jp_read_header, on, "jpeg_read_header") +
            jp_patch(JP_START, jp_sd_orig, (void *)jp_start, on, "jpeg_start_decompress") +
            jp_patch(JP_READ_SCANLINES, jp_rs_orig, (void *)jp_read_scanlines, on, "jpeg_read_scanlines") +
            jp_patch(JP_FINISH, jp_fd_orig, (void *)jp_finish, on, "jpeg_finish_decompress");
    unsigned char j[5]; j[0] = 0xE9; *(int *)(j + 1) = (int)((unsigned char *)jp_destroy - ((unsigned char *)JP_DESTROY_THUNK + 5));
    n += md_patch_bytes(JP_DESTROY_THUNK, jp_dt_orig, j, 5, on, "jpeg_destroy thunk");
    jp_on = on && n == 5;
    return n;
}

static void jp_stats(FILE *f)
{
    if (!jp_n_img && !jp_n_fb[0]) return;
    double ms = qpf.QuadPart ? 1000.0 / qpf.QuadPart : 0;
    fprintf(f, "jpeg images=%ld native=%ld fallback src=%ld state=%ld frame=%ld header=%ld error=%ld warning=%ld thread=%ld caller=%ld read=%lldKB(%.1fms) native=%.1fms",
            jp_n_img, jp_n_native, jp_n_fb[0], jp_n_fb[1], jp_n_fb[2], jp_n_fb[3], jp_n_fb[4], jp_n_fb[5], jp_n_fb[6], jp_n_fb[7], jp_bytes / 1024, jp_t_read * ms, jp_t_native * ms);
    if (jp_verify || jp_tot_checked) fprintf(f, " | verify images=%ld rows=%ld bad_rows=%ld bad_images=%ld original=%.1fms total checked=%lld bad=%lld",
                                             jp_n_checked, jp_rows_checked, jp_rows_bad, jp_n_bad, jp_t_orig * ms, jp_tot_checked, jp_tot_bad);
    fprintf(f, " | total native=%lld\n", jp_tot_native);
    jp_n_img = jp_n_native = jp_n_checked = jp_rows_checked = jp_rows_bad = jp_n_bad = 0; memset(jp_n_fb, 0, sizeof jp_n_fb);
    jp_t_native = jp_t_orig = jp_t_read = jp_bytes = 0;
}
#else
static int jp_install(int on, int verify) { (void)on; (void)verify; return 0; }   /* built without LJT_DIR: no native JPEG decode */
static void jp_stats(FILE *f) { (void)f; }
#endif
