#include "mu_wav.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { FMT_PCM = 1, FMT_MSADPCM = 2, FMT_FLOAT = 3, FMT_IMAADPCM = 0x11, FMT_EXTENSIBLE = 0xfffe };

static uint16_t le16(const uint8_t *p) { return (uint16_t)(p[0] | p[1] << 8); }
static uint32_t le32(const uint8_t *p) { return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24; }

static int fail(char *error, size_t size, const char *message)
{
    if (error && size) snprintf(error, size, "%s", message);
    return -1;
}

typedef struct wav_header {
    uint16_t format, channels, block_align, bits;
    uint32_t rate;
    uint16_t samples_per_block;  /* ADPCM */
    int16_t coefficients[32][2]; /* MS-ADPCM */
    uint16_t coefficient_count;
    const uint8_t *data;
    uint32_t data_size;
} wav_header;

static int parse(const uint8_t *data, size_t size, wav_header *h, char *error, size_t error_size)
{
    memset(h, 0, sizeof *h);
    if (size < 12 || memcmp(data, "RIFF", 4) || memcmp(data + 8, "WAVE", 4))
        return fail(error, error_size, "not a RIFF/WAVE file");
    size_t end = size;
    uint32_t riff = le32(data + 4);
    if ((size_t)riff + 8 < end) end = (size_t)riff + 8;
    int have_format = 0;
    for (size_t at = 12; at + 8 <= end;) {
        uint32_t chunk = le32(data + at + 4);
        const uint8_t *body = data + at + 8;
        size_t available = end - at - 8;
        if (!memcmp(data + at, "fmt ", 4)) {
            if (chunk < 16 || chunk > available) return fail(error, error_size, "truncated fmt chunk");
            h->format = le16(body);
            h->channels = le16(body + 2);
            h->rate = le32(body + 4);
            h->block_align = le16(body + 12);
            h->bits = le16(body + 14);
            uint16_t extra = chunk >= 18 ? le16(body + 16) : 0;
            if (h->format == FMT_EXTENSIBLE) {
                if (chunk < 40 || extra < 22) return fail(error, error_size, "truncated extensible fmt chunk");
                h->format = le16(body + 24);  /* first two bytes of the subformat GUID */
            } else if (h->format == FMT_MSADPCM) {
                if (chunk < 22 || extra < 4) return fail(error, error_size, "truncated MS-ADPCM fmt chunk");
                h->samples_per_block = le16(body + 18);
                h->coefficient_count = le16(body + 20);
                if (h->coefficient_count == 0 || h->coefficient_count > 32 ||
                    22u + 4u*h->coefficient_count > chunk)
                    return fail(error, error_size, "bad MS-ADPCM coefficient table");
                for (uint16_t i = 0; i < h->coefficient_count; i++) {
                    h->coefficients[i][0] = (int16_t)le16(body + 22 + 4*i);
                    h->coefficients[i][1] = (int16_t)le16(body + 24 + 4*i);
                }
            } else if (h->format == FMT_IMAADPCM) {
                if (chunk < 20 || extra < 2) return fail(error, error_size, "truncated IMA-ADPCM fmt chunk");
                h->samples_per_block = le16(body + 18);
            }
            have_format = 1;
        } else if (!memcmp(data + at, "data", 4)) {
            h->data = body;
            /* A data size beyond the file is truncated to what is present. */
            h->data_size = chunk <= available ? chunk : (uint32_t)available;
            if (have_format) break;
        }
        size_t step = 8 + (size_t)chunk + (chunk & 1);
        if (step > end - at) break;
        at += step;
    }
    if (!have_format) return fail(error, error_size, "missing fmt chunk");
    if (!h->data) return fail(error, error_size, "missing data chunk");
    if (h->channels == 0 || h->channels > 8) return fail(error, error_size, "unsupported channel count");
    if (h->rate == 0 || h->rate > 768000) return fail(error, error_size, "unsupported sample rate");
    switch (h->format) {
    case FMT_PCM:
        if (h->bits != 8 && h->bits != 16 && h->bits != 24 && h->bits != 32)
            return fail(error, error_size, "unsupported PCM bit depth");
        break;
    case FMT_FLOAT:
        if (h->bits != 32 && h->bits != 64) return fail(error, error_size, "unsupported float bit depth");
        break;
    case FMT_MSADPCM:
        if (h->bits != 4 || h->channels > 2) return fail(error, error_size, "unsupported MS-ADPCM layout");
        if (h->block_align < 7u*h->channels || h->samples_per_block < 2 ||
            (uint32_t)h->samples_per_block != 2u + ((uint32_t)h->block_align - 7u*h->channels)*2u/h->channels)
            return fail(error, error_size, "inconsistent MS-ADPCM block size");
        break;
    case FMT_IMAADPCM:
        if (h->bits != 4 || h->channels > 2) return fail(error, error_size, "unsupported IMA-ADPCM layout");
        if (h->block_align < 4u*h->channels || h->samples_per_block < 1 ||
            (uint32_t)h->samples_per_block != 1u + ((uint32_t)h->block_align - 4u*h->channels)*2u/h->channels)
            return fail(error, error_size, "inconsistent IMA-ADPCM block size");
        break;
    default:
        return fail(error, error_size, "unsupported WAVE format tag");
    }
    if (h->format == FMT_PCM || h->format == FMT_FLOAT) {
        uint32_t frame = (uint32_t)h->channels*(h->bits/8u);
        if (h->block_align != frame) h->block_align = (uint16_t)frame;  /* writers get this wrong */
    }
    return 0;
}

static uint32_t frame_count(const wav_header *h)
{
    if (h->format == FMT_PCM || h->format == FMT_FLOAT) return h->data_size/h->block_align;
    uint32_t blocks = h->data_size/h->block_align;
    uint32_t frames = blocks*h->samples_per_block;
    uint32_t rest = h->data_size % h->block_align;
    if (h->format == FMT_MSADPCM && rest >= 7u*h->channels)
        frames += 2u + (rest - 7u*h->channels)*2u/h->channels;
    if (h->format == FMT_IMAADPCM && rest >= 4u*h->channels)
        frames += 1u + ((rest - 4u*h->channels)/(4u*h->channels))*8u;
    return frames;
}

static int16_t clamp16(int32_t v) { return (int16_t)(v < -32768 ? -32768 : v > 32767 ? 32767 : v); }

/* MS-ADPCM block decoding (Microsoft ADPCM, as in msadpcm.c of the Windows SDK). */
static uint32_t decode_msadpcm_block(const wav_header *h, const uint8_t *block, uint32_t size, float *out,
                                     uint32_t limit)
{
    static const int32_t adaptation[16] = {230, 230, 230, 230, 307, 409, 512, 614,
                                           768, 614, 512, 409, 307, 230, 230, 230};
    const uint16_t channels = h->channels;
    int32_t coefficient1[2], coefficient2[2], delta[2], sample1[2], sample2[2];
    if (size < 7u*channels) return 0;
    const uint8_t *p = block;
    for (uint16_t c = 0; c < channels; c++) {
        uint8_t predictor = *p++;
        if (predictor >= h->coefficient_count) predictor = 0;
        coefficient1[c] = h->coefficients[predictor][0];
        coefficient2[c] = h->coefficients[predictor][1];
    }
    for (uint16_t c = 0; c < channels; c++, p += 2) delta[c] = (int16_t)le16(p);
    for (uint16_t c = 0; c < channels; c++, p += 2) sample1[c] = (int16_t)le16(p);
    for (uint16_t c = 0; c < channels; c++, p += 2) sample2[c] = (int16_t)le16(p);
    uint32_t frames = 0;
    if (frames < limit) {
        for (uint16_t c = 0; c < channels; c++) out[c] = (float)sample2[c]/32768.0f;
        frames++;
    }
    if (frames < limit) {
        for (uint16_t c = 0; c < channels; c++) out[channels + c] = (float)sample1[c]/32768.0f;
        frames++;
    }
    const uint8_t *end = block + size;
    uint32_t nibble_index = 0;
    while (frames < limit && p < end) {
        for (uint16_t c = 0; c < channels && p < end; c++) {
            int32_t nibble = (nibble_index++ & 1) ? (*p++ & 0x0f) : (*p >> 4);
            int32_t signed_nibble = nibble >= 8 ? nibble - 16 : nibble;
            int32_t predicted = (sample1[c]*coefficient1[c] + sample2[c]*coefficient2[c])/256;
            int32_t value = clamp16(predicted + signed_nibble*delta[c]);
            sample2[c] = sample1[c];
            sample1[c] = value;
            delta[c] = adaptation[nibble]*delta[c]/256;
            if (delta[c] < 16) delta[c] = 16;
            if (delta[c] > INT32_MAX/768) delta[c] = INT32_MAX/768;  /* corrupt input: no overflow */
            out[(size_t)frames*channels + c] = (float)value/32768.0f;
        }
        frames++;
    }
    return frames;
}

/* IMA/DVI ADPCM block decoding (WAVE_FORMAT_DVI_ADPCM layout: 4-byte groups per channel). */
static uint32_t decode_ima_block(const wav_header *h, const uint8_t *block, uint32_t size, float *out,
                                 uint32_t limit)
{
    static const int32_t steps[89] = {
        7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 19, 21, 23, 25, 28, 31, 34, 37, 41, 45, 50, 55, 60, 66, 73, 80,
        88, 97, 107, 118, 130, 143, 157, 173, 190, 209, 230, 253, 279, 307, 337, 371, 408, 449, 494, 544, 598,
        658, 724, 796, 876, 963, 1060, 1166, 1282, 1411, 1552, 1707, 1878, 2066, 2272, 2499, 2749, 3024, 3327,
        3660, 4026, 4428, 4871, 5358, 5894, 6484, 7132, 7845, 8630, 9493, 10442, 11487, 12635, 13899, 15289,
        16818, 18500, 20350, 22385, 24623, 27086, 29794, 32767};
    static const int32_t index_table[8] = {-1, -1, -1, -1, 2, 4, 6, 8};
    const uint16_t channels = h->channels;
    int32_t predictor[2], index[2];
    if (size < 4u*channels) return 0;
    for (uint16_t c = 0; c < channels; c++) {
        predictor[c] = (int16_t)le16(block + 4*c);
        index[c] = block[4*c + 2];
        if (index[c] > 88) index[c] = 88;
        if (limit) out[c] = (float)predictor[c]/32768.0f;
    }
    uint32_t frames = limit ? 1 : 0;
    const uint8_t *p = block + 4u*channels;
    const uint8_t *end = block + size;
    while (frames < limit && (size_t)(end - p) >= 4u*channels) {
        for (uint16_t c = 0; c < channels; c++) {
            const uint8_t *group = p + 4*c;
            for (uint32_t k = 0; k < 8 && frames + k < limit; k++) {
                int32_t nibble = (k & 1) ? group[k/2] >> 4 : group[k/2] & 0x0f;
                int32_t step = steps[index[c]];
                int32_t diff = step >> 3;
                if (nibble & 1) diff += step >> 2;
                if (nibble & 2) diff += step >> 1;
                if (nibble & 4) diff += step;
                if (nibble & 8) diff = -diff;
                predictor[c] = clamp16(predictor[c] + diff);
                index[c] += index_table[nibble & 7];
                if (index[c] < 0) index[c] = 0;
                if (index[c] > 88) index[c] = 88;
                out[(size_t)(frames + k)*channels + c] = (float)predictor[c]/32768.0f;
            }
        }
        p += 4u*channels;
        frames = frames + 8 < limit ? frames + 8 : limit;
    }
    return frames;
}

static int decode(const uint8_t *data, size_t size, mu_pcm *out, int samples, char *error, size_t error_size)
{
    wav_header h;
    memset(out, 0, sizeof *out);
    if (parse(data, size, &h, error, error_size)) return -1;
    uint32_t frames = frame_count(&h);
    out->frames = frames;
    out->channels = h.channels;
    out->rate = h.rate;
    out->format = h.format;
    out->bits = h.bits;
    if (!samples) return 0;
    size_t count = (size_t)frames*h.channels;
    out->samples = malloc(count ? count*sizeof(float) : sizeof(float));
    if (!out->samples) return fail(error, error_size, "out of memory");
    float *o = out->samples;
    const uint8_t *p = h.data;
    switch (h.format) {
    case FMT_PCM:
        for (size_t i = 0; i < count; i++) {
            switch (h.bits) {
            case 8: o[i] = ((float)p[i] - 128.0f)/128.0f; break;
            case 16: o[i] = (float)(int16_t)le16(p + 2*i)/32768.0f; break;
            case 24: {
                int32_t v = (int32_t)((uint32_t)p[3*i] << 8 | (uint32_t)p[3*i + 1] << 16 | (uint32_t)p[3*i + 2] << 24) >> 8;
                o[i] = (float)v/8388608.0f;
                break;
            }
            default: o[i] = (float)((double)(int32_t)le32(p + 4*i)/2147483648.0); break;
            }
        }
        break;
    case FMT_FLOAT:
        for (size_t i = 0; i < count; i++) {
            if (h.bits == 32) {
                uint32_t bits = le32(p + 4*i);
                float v;
                memcpy(&v, &bits, 4);
                o[i] = v;
            } else {
                uint64_t bits = (uint64_t)le32(p + 8*i) | (uint64_t)le32(p + 8*i + 4) << 32;
                double v;
                memcpy(&v, &bits, 8);
                o[i] = (float)v;
            }
            if (!isfinite(o[i])) o[i] = 0.0f;
        }
        break;
    case FMT_MSADPCM:
    case FMT_IMAADPCM: {
        uint32_t done = 0;
        for (uint32_t at = 0; at < h.data_size && done < frames; at += h.block_align) {
            uint32_t block = h.data_size - at < h.block_align ? h.data_size - at : h.block_align;
            uint32_t got = h.format == FMT_MSADPCM
                               ? decode_msadpcm_block(&h, p + at, block, o + (size_t)done*h.channels, frames - done)
                               : decode_ima_block(&h, p + at, block, o + (size_t)done*h.channels, frames - done);
            if (!got) break;
            done += got;
        }
        out->frames = done;
        break;
    }
    default:
        break;
    }
    return 0;
}

int mu_wav_decode(const uint8_t *data, size_t size, mu_pcm *out, char *error, size_t error_size)
{
    return decode(data, size, out, 1, error, error_size);
}

int mu_wav_probe(const uint8_t *data, size_t size, mu_pcm *out, char *error, size_t error_size)
{
    return decode(data, size, out, 0, error, error_size);
}

void mu_pcm_free(mu_pcm *pcm)
{
    if (!pcm) return;
    free(pcm->samples);
    memset(pcm, 0, sizeof *pcm);
}

static void put16(uint8_t *p, uint32_t v) { p[0] = (uint8_t)v; p[1] = (uint8_t)(v >> 8); }
static void put32(uint8_t *p, uint32_t v) { put16(p, v & 0xffff); put16(p + 2, v >> 16); }

int mu_wav_encode16(const float *samples, uint32_t frames, uint16_t channels, uint32_t rate,
                    uint8_t **out, size_t *out_size)
{
    uint64_t data_size = (uint64_t)frames*channels*2;
    if (!channels || data_size > 0xffffffffu - 44) return -1;
    uint8_t *b = malloc((size_t)data_size + 44);
    if (!b) return -1;
    memcpy(b, "RIFF", 4);
    put32(b + 4, (uint32_t)data_size + 36);
    memcpy(b + 8, "WAVEfmt ", 8);
    put32(b + 16, 16);
    put16(b + 20, 1);
    put16(b + 22, channels);
    put32(b + 24, rate);
    put32(b + 28, rate*channels*2u);
    put16(b + 32, (uint32_t)channels*2u);
    put16(b + 34, 16);
    memcpy(b + 36, "data", 4);
    put32(b + 40, (uint32_t)data_size);
    for (uint64_t i = 0; i < (uint64_t)frames*channels; i++) {
        float v = samples[i];
        if (!(v == v)) v = 0.0f;
        double scaled = (double)v*32768.0;
        long q = lrint(scaled);
        if (q > 32767) q = 32767;
        if (q < -32768) q = -32768;
        put16(b + 44 + 2*i, (uint16_t)(int16_t)q);
    }
    *out = b;
    *out_size = (size_t)data_size + 44;
    return 0;
}

int mu_wav_write16(const char *path, const float *samples, uint32_t frames, uint16_t channels, uint32_t rate)
{
    uint8_t *buffer;
    size_t size;
    if (mu_wav_encode16(samples, frames, channels, rate, &buffer, &size)) return -1;
    FILE *f = fopen(path, "wb");
    int ok = f && fwrite(buffer, 1, size, f) == size;
    if (f && fclose(f)) ok = 0;
    free(buffer);
    return ok ? 0 : -1;
}
