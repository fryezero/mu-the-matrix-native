/* DDS top mip, transparent crop, and separable bilinear RGBA resampling.
 * Authored implementation of the Python oracle's integer rounding rules.
 * Filter weights use 22 fractional bits; RGBA is resampled in premultiplied
 * form, then converted back before SWF's floor-premultiplication. */
#include "gfxconvert.h"
#include <string.h>
#include <math.h>
static Image image(int w, int h) {
    if (w <= 0 || h <= 0 || w > 16384 || h > 16384 || (size_t)w * (size_t)h > 16777216)
        fail("invalid or oversized image %dx%d", w, h);
    return (Image){w, h, mem((size_t)w * (size_t)h * 4)};
}
static unsigned le16(const unsigned char *p) { return p[0] | (unsigned)p[1] << 8; }
static unsigned le32(const unsigned char *p) { return le16(p) | le16(p + 2) << 16; }
static unsigned channel(unsigned v, unsigned mask) {
    if (!mask) return 0;
    unsigned shift = 0; while (!(mask & 1)) { mask >>= 1; shift++; }
    return ((v >> shift) & mask) * 255 / mask;
}
Image decode_dds(Buf data) {
    Read r = {data.p, data.n, 0}; Read header = take(&r, 128); const unsigned char *p = header.p;
    if (memcmp(p, "DDS ", 4)) fail("not a DDS image");
    Image im = image((int)le32(p + 16), (int)le32(p + 12));
    unsigned flags = le32(p + 80), bits = le32(p + 88);
    if (flags & 4) {
        int kind = !memcmp(p + 84, "DXT1", 4) ? 1 : !memcmp(p + 84, "DXT3", 4) ? 3 :
                   !memcmp(p + 84, "DXT5", 4) ? 5 : 0;
        if (!kind) fail("unsupported DDS compression");
        for (int y = 0; y < im.h; y += 4) for (int x = 0; x < im.w; x += 4) {
            Read blk = take(&r, kind == 1 ? 8 : 16); const unsigned char *c = blk.p + (kind == 1 ? 0 : 8);
            unsigned c0 = le16(c), c1 = le16(c + 2); unsigned char pal[4][4] = {{0}};
            for (int i = 0; i < 2; i++) {
                unsigned v = i ? c1 : c0, rr = (v >> 11) & 31, g = (v >> 5) & 63, b = v & 31;
                pal[i][0] = (unsigned char)((rr << 3) | (rr >> 2));
                pal[i][1] = (unsigned char)((g << 2) | (g >> 4));
                pal[i][2] = (unsigned char)((b << 3) | (b >> 2)); pal[i][3] = 255;
            }
            for (int k = 0; k < 3; k++) {
                if (c0 > c1 || kind != 1) {
                    pal[2][k] = (unsigned char)((2 * pal[0][k] + pal[1][k]) / 3);
                    pal[3][k] = (unsigned char)((pal[0][k] + 2 * pal[1][k]) / 3);
                } else pal[2][k] = (unsigned char)((pal[0][k] + pal[1][k]) / 2);
            }
            pal[2][3] = 255; pal[3][3] = c0 > c1 || kind != 1 ? 255 : 0;
            unsigned char alpha[8] = {blk.p[0], blk.p[1]}; uint64_t abits = 0;
            if (kind == 5) {
                if (alpha[0] > alpha[1]) for (int i = 1; i <= 6; i++)
                    alpha[i + 1] = (unsigned char)(((7 - i) * alpha[0] + i * alpha[1]) / 7);
                else {
                    for (int i = 1; i <= 4; i++) alpha[i + 1] = (unsigned char)(((5 - i) * alpha[0] + i * alpha[1]) / 5);
                    alpha[6] = 0; alpha[7] = 255;
                }
                for (int i = 0; i < 6; i++) abits |= (uint64_t)blk.p[i + 2] << (8 * i);
            }
            unsigned colorbits = le32(c + 4);
            for (int i = 0; i < 16; i++) {
                int xx = x + i % 4, yy = y + i / 4;
                if (xx >= im.w || yy >= im.h) continue;
                unsigned char *dst = im.px + ((size_t)yy * (size_t)im.w + (size_t)xx) * 4;
                memcpy(dst, pal[(colorbits >> (2 * i)) & 3], 4);
                if (kind == 3) dst[3] = (unsigned char)(((blk.p[i / 2] >> (4 * (i % 2))) & 15) * 17);
                if (kind == 5) dst[3] = alpha[(abits >> (3 * i)) & 7];
            }
        }
    } else if ((flags & 0x40) && (bits == 24 || bits == 32)) {
        unsigned mask[4]; for (int i = 0; i < 4; i++) mask[i] = le32(p + 92 + 4 * i);
        for (size_t i = 0; i < (size_t)im.w * (size_t)im.h; i++) {
            Read px = take(&r, bits / 8); unsigned v = 0;
            for (unsigned k = 0; k < bits / 8; k++) v |= (unsigned)px.p[k] << (8 * k);
            for (int k = 0; k < 4; k++) im.px[i * 4 + (size_t)k] = (unsigned char)(k == 3 && !(flags & 1) ? 255 : channel(v, mask[k]));
        }
    } else fail("unsupported DDS pixel format");
    return im;
}
Image crop(Image src, int x1, int y1, int x2, int y2) {
    Image dst = image(x2 - x1, y2 - y1);
    for (int y = 0; y < dst.h; y++) for (int x = 0; x < dst.w; x++) {
        int xx = x + x1, yy = y + y1;
        if (xx >= 0 && xx < src.w && yy >= 0 && yy < src.h)
            memcpy(dst.px + ((size_t)y * (size_t)dst.w + (size_t)x) * 4,
                   src.px + ((size_t)yy * (size_t)src.w + (size_t)xx) * 4, 4);
    }
    return dst;
}
typedef struct { int start, n; int32_t *weights; } Filter;
static Filter *filters(int in, int out) {
    double scale = (double)in / out, support = scale > 1 ? scale : 1;
    Filter *f = mem((size_t)out * sizeof(*f));
    for (int i = 0; i < out; i++) {
        double center = (i + .5) * scale;
        int first = (int)(center - support + .5), last = (int)(center + support + .5);
        if (first < 0) first = 0; if (last > in) last = in;
        f[i].start = first; f[i].n = last - first;
        f[i].weights = mem((size_t)f[i].n * sizeof(int32_t));
        double *w = mem((size_t)f[i].n * sizeof(double)), total = 0;
        for (int k = 0; k < f[i].n; k++) {
            double distance = fabs((k + first - center + .5) * (1.0 / support));
            w[k] = distance < 1 ? 1 - distance : 0; total += w[k];
        }
        for (int k = 0; k < f[i].n; k++) f[i].weights[k] = (int32_t)(.5 + w[k] / total * (1 << 22));
    }
    return f;
}
static Image resample(Image src, int size, int vertical) {
    Image dst = image(vertical ? src.w : size, vertical ? size : src.h);
    Filter *f = filters(vertical ? src.h : src.w, size);
    for (int y = 0; y < dst.h; y++) for (int x = 0; x < dst.w; x++) {
        Filter at = f[vertical ? y : x];
        for (int c = 0; c < 4; c++) {
            int32_t sum = 1 << 21;
            for (int k = 0; k < at.n; k++) {
                int sx = vertical ? x : at.start + k, sy = vertical ? at.start + k : y;
                sum += src.px[((size_t)sy * (size_t)src.w + (size_t)sx) * 4 + (size_t)c] * at.weights[k];
            }
            int v = sum >> 22;
            dst.px[((size_t)y * (size_t)dst.w + (size_t)x) * 4 + (size_t)c] = (unsigned char)(v > 255 ? 255 : v < 0 ? 0 : v);
        }
    }
    return dst;
}
Image resize(Image src, int w, int h) {
    if (w == src.w && h == src.h) return src;
    Image work = image(src.w, src.h);
    for (size_t i = 0; i < (size_t)src.w * (size_t)src.h; i++) {
        unsigned a = src.px[i * 4 + 3]; work.px[i * 4 + 3] = (unsigned char)a;
        for (int k = 0; k < 3; k++) {
            unsigned v = src.px[i * 4 + (size_t)k] * a + 128;
            work.px[i * 4 + (size_t)k] = (unsigned char)(((v >> 8) + v) >> 8);
        }
    }
    if (src.w != w) work = resample(work, w, 0);
    if (src.h != h) work = resample(work, h, 1);
    for (size_t i = 0; i < (size_t)w * (size_t)h; i++) {
        unsigned a = work.px[i * 4 + 3];
        if (a && a != 255) for (int k = 0; k < 3; k++) {
            unsigned v = 255 * work.px[i * 4 + (size_t)k] / a;
            work.px[i * 4 + (size_t)k] = (unsigned char)(v > 255 ? 255 : v);
        }
    }
    return work;
}
Buf lossless(unsigned id, Image im) {
    size_t n = (size_t)im.w * (size_t)im.h * 4; unsigned char *argb = mem(n);
    for (size_t i = 0; i < n; i += 4) {
        unsigned a = im.px[i + 3]; argb[i] = (unsigned char)a;
        for (int c = 0; c < 3; c++) argb[i + 1 + (size_t)c] = (unsigned char)(im.px[i + (size_t)c] * a / 255);
    }
    Buf b = {0}; word(&b, id); byte(&b, 5); word(&b, (unsigned)im.w); word(&b, (unsigned)im.h);
    Buf z = deflate_buf(argb, n, 6); add(&b, z.p, z.n); return b;
}
