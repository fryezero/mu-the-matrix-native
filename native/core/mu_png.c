/* Minimal PNG writer and SHA-256. See mu_png.h. */
#include "mu_png.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static uint32_t crc_table[256];
static int crc_ready;

static uint32_t crc32_update(uint32_t crc, const uint8_t *data, size_t size)
{
    if (!crc_ready) {
        for (uint32_t n = 0; n < 256; ++n) {
            uint32_t c = n;
            for (int k = 0; k < 8; ++k)
                c = (c & 1) ? 0xedb88320u ^ (c >> 1) : c >> 1;
            crc_table[n] = c;
        }
        crc_ready = 1;
    }
    for (size_t i = 0; i < size; ++i)
        crc = crc_table[(crc ^ data[i]) & 0xff] ^ (crc >> 8);
    return crc;
}

static void be32(uint8_t *p, uint32_t v)
{
    p[0] = (uint8_t)(v >> 24); p[1] = (uint8_t)(v >> 16); p[2] = (uint8_t)(v >> 8); p[3] = (uint8_t)v;
}

static int chunk(FILE *file, const char *type, const uint8_t *data, uint32_t size)
{
    uint8_t header[8];
    be32(header, size);
    memcpy(header + 4, type, 4);
    uint32_t crc = crc32_update(0xffffffffu, header + 4, 4);
    crc = crc32_update(crc, data, size) ^ 0xffffffffu;
    uint8_t trailer[4];
    be32(trailer, crc);
    return fwrite(header, 1, 8, file) == 8 && (size == 0 || fwrite(data, 1, size, file) == size) &&
           fwrite(trailer, 1, 4, file) == 4;
}

int mu_png_write(const char *path, const uint8_t *rgba, int32_t width, int32_t height)
{
    if (width <= 0 || height <= 0)
        return 1;
    const size_t row = (size_t)width * 4 + 1;
    const size_t raw_size = row * (size_t)height;
    const size_t blocks = (raw_size + 65534) / 65535;
    const size_t z_size = 2 + raw_size + blocks * 5 + 4;
    uint8_t *z = malloc(z_size);
    if (!z)
        return 1;
    size_t o = 0;
    z[o++] = 0x78;
    z[o++] = 0x01;
    uint32_t a = 1, b = 0;
    size_t emitted = 0, y = 0, x = 0;  /* position in the filtered raw stream */
    while (emitted < raw_size) {
        size_t n = raw_size - emitted;
        if (n > 65535)
            n = 65535;
        z[o++] = emitted + n == raw_size ? 1 : 0;
        z[o++] = (uint8_t)n; z[o++] = (uint8_t)(n >> 8);
        z[o++] = (uint8_t)~n; z[o++] = (uint8_t)(~n >> 8);
        for (size_t k = 0; k < n; ++k) {
            uint8_t value = x == 0 ? 0 : rgba[y * (size_t)width * 4 + (x - 1)];
            z[o++] = value;
            a = (a + value) % 65521u;
            b = (b + a) % 65521u;
            if (++x == row) {
                x = 0;
                ++y;
            }
        }
        emitted += n;
    }
    be32(z + o, (b << 16) | a);
    o += 4;
    FILE *file = fopen(path, "wb");
    if (!file) {
        free(z);
        return 1;
    }
    static const uint8_t signature[8] = {0x89, 'P', 'N', 'G', '\r', '\n', 0x1a, '\n'};
    uint8_t ihdr[13];
    be32(ihdr, (uint32_t)width);
    be32(ihdr + 4, (uint32_t)height);
    ihdr[8] = 8; ihdr[9] = 6; ihdr[10] = 0; ihdr[11] = 0; ihdr[12] = 0;
    int ok = fwrite(signature, 1, 8, file) == 8 && chunk(file, "IHDR", ihdr, 13) &&
             chunk(file, "IDAT", z, (uint32_t)o) && chunk(file, "IEND", NULL, 0);
    ok = fclose(file) == 0 && ok;
    free(z);
    return ok ? 0 : 1;
}

/* SHA-256 (FIPS 180-4). */
static const uint32_t k256[64] = {
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2};

static uint32_t rotr(uint32_t x, unsigned n) { return (x >> n) | (x << (32 - n)); }

static void sha_block(uint32_t h[8], const uint8_t *p)
{
    uint32_t w[64];
    for (int i = 0; i < 16; ++i)
        w[i] = ((uint32_t)p[4 * i] << 24) | ((uint32_t)p[4 * i + 1] << 16) | ((uint32_t)p[4 * i + 2] << 8) | p[4 * i + 3];
    for (int i = 16; i < 64; ++i) {
        uint32_t s0 = rotr(w[i - 15], 7) ^ rotr(w[i - 15], 18) ^ (w[i - 15] >> 3);
        uint32_t s1 = rotr(w[i - 2], 17) ^ rotr(w[i - 2], 19) ^ (w[i - 2] >> 10);
        w[i] = w[i - 16] + s0 + w[i - 7] + s1;
    }
    uint32_t a = h[0], b = h[1], c = h[2], d = h[3], e = h[4], f = h[5], g = h[6], hh = h[7];
    for (int i = 0; i < 64; ++i) {
        uint32_t t1 = hh + (rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25)) + ((e & f) ^ (~e & g)) + k256[i] + w[i];
        uint32_t t2 = (rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22)) + ((a & b) ^ (a & c) ^ (b & c));
        hh = g; g = f; f = e; e = d + t1; d = c; c = b; b = a; a = t1 + t2;
    }
    h[0] += a; h[1] += b; h[2] += c; h[3] += d; h[4] += e; h[5] += f; h[6] += g; h[7] += hh;
}

void mu_sha256_hex(const uint8_t *data, uint64_t size, char out[65])
{
    uint32_t h[8] = {0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19};
    uint64_t full = size / 64;
    for (uint64_t i = 0; i < full; ++i)
        sha_block(h, data + 64 * i);
    uint8_t tail[128];
    uint64_t rest = size - full * 64;
    memset(tail, 0, sizeof tail);
    memcpy(tail, data + full * 64, (size_t)rest);
    tail[rest] = 0x80;
    size_t blocks = rest + 9 > 64 ? 2 : 1;
    uint64_t bits = size * 8;
    for (int k = 0; k < 8; ++k)
        tail[blocks * 64 - 1 - (size_t)k] = (uint8_t)(bits >> (8 * k));
    for (size_t i = 0; i < blocks; ++i)
        sha_block(h, tail + 64 * i);
    static const char hex[] = "0123456789abcdef";
    for (int i = 0; i < 8; ++i)
        for (int k = 0; k < 4; ++k) {
            uint8_t byte = (uint8_t)(h[i] >> (24 - 8 * k));
            out[8 * i + 2 * k] = hex[byte >> 4];
            out[8 * i + 2 * k + 1] = hex[byte & 15];
        }
    out[64] = 0;
}
