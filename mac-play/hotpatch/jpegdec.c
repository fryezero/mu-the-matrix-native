/* Native JPEG decode for mugl v7.6 (MAC-PERF-010), the libjpeg-turbo side.

   A separate translation unit (no windows.h, turbo's own `boolean`), built only when LJT_DIR names a libjpeg-turbo
   build made by build-libjpeg-turbo.sh (pinned 3.1.2 with two changes: no h1v2 fancy upsampling, as in IJG 6b, and
   SSE2 as the only SIMD level). mj_decode decodes a whole in-memory JPEG with the library defaults that the client's
   statically linked IJG 6b uses (islow IDCT, fancy upsampling, block smoothing, no quantization) and refuses
   anything the client's library would treat differently: a frame type other than SOF0/SOF1/SOF2 (6b has no
   arithmetic or lossless decoding), a precision other than 8, a colour space or component count different from what
   the client's own header parse found, or any warning or error. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <setjmp.h>
#include "jpeglib.h"
#include "jpegdec.h"

struct mj_err { struct jpeg_error_mgr pub; jmp_buf jb; };
static void mj_exit(j_common_ptr c) { longjmp(((struct mj_err *)c->err)->jb, 1); }
static void mj_output(j_common_ptr c) { (void)c; }

/* The frame marker before the first SOS, or -1 (also for a malformed segment walk). */
static int mj_frame_type(const unsigned char *b, unsigned long n)
{
    unsigned long i = 2;
    if (n < 4 || b[0] != 0xFF || b[1] != 0xD8) return -1;
    while (i + 4 <= n) {
        if (b[i] != 0xFF) return -1;
        while (i < n && b[i] == 0xFF) i++;
        if (i >= n) return -1;
        int m = b[i++];
        if (m == 0xD8 || (m >= 0xD0 && m <= 0xD7) || m == 0x01) continue;
        if (m == 0xD9 || m == 0xDA || i + 2 > n) return -1;
        if (m >= 0xC0 && m <= 0xCF && m != 0xC4 && m != 0xC8 && m != 0xCC) return m;
        i += ((unsigned)b[i] << 8) | b[i + 1];
    }
    return -1;
}

int mj_decode(const unsigned char *buf, unsigned long n, const MjWant *want, MjImg *o)
{
    struct jpeg_decompress_struct ci;
    struct mj_err e;
    JSAMPROW rows[64];
    int ft = mj_frame_type(buf, n);
    if (ft != 0xC0 && ft != 0xC1 && ft != 0xC2) return MJ_FRAME;
    memset(&ci, 0, sizeof ci);
    ci.err = jpeg_std_error(&e.pub);
    e.pub.error_exit = mj_exit;
    e.pub.output_message = mj_output;
    if (setjmp(e.jb)) { o->msg = e.pub.msg_code; jpeg_destroy_decompress(&ci); return MJ_ERROR; }
    jpeg_create_decompress(&ci);
    jpeg_mem_src(&ci, buf, n);
    if (jpeg_read_header(&ci, TRUE) != JPEG_HEADER_OK) { jpeg_destroy_decompress(&ci); return MJ_ERROR; }
    if ((int)ci.image_width != want->width || (int)ci.image_height != want->height || ci.num_components != want->ncomp ||
        (int)ci.jpeg_color_space != want->jcs_in || (int)ci.out_color_space != want->jcs_out || ci.data_precision != 8 ||
        ci.arith_code || (int)ci.progressive_mode != want->progressive || e.pub.num_warnings) {
        jpeg_destroy_decompress(&ci); return MJ_HEADER;
    }
    jpeg_start_decompress(&ci);
    size_t stride = (size_t)ci.output_width * ci.output_components, need = stride * ci.output_height;
    if (need > o->cap) {
        unsigned char *p = realloc(o->pix, need);
        if (!p) { jpeg_destroy_decompress(&ci); return MJ_ERROR; }
        o->pix = p; o->cap = need;
    }
    while (ci.output_scanline < ci.output_height) {
        unsigned k, left = ci.output_height - ci.output_scanline;
        if (left > 64) left = 64;
        for (k = 0; k < left; k++) rows[k] = o->pix + (ci.output_scanline + k) * stride;
        if (!jpeg_read_scanlines(&ci, rows, left)) { jpeg_destroy_decompress(&ci); return MJ_ERROR; }
    }
    jpeg_finish_decompress(&ci);
    o->width = ci.output_width; o->height = ci.output_height; o->comps = ci.output_components;
    o->out_comps = ci.out_color_components;
    long warn = e.pub.num_warnings;
    jpeg_destroy_decompress(&ci);
    return warn ? MJ_WARNING : MJ_OK;
}
