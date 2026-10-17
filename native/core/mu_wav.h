/* RIFF/WAVE decoding and writing for the native audio module.
 *
 * Data/Sound holds 1,358 WAV files: PCM 8/16-bit mono/stereo at rates from
 * 6116 to 55400 Hz, and one MS-ADPCM file. The client hands them to FMOD; this
 * decoder covers those formats plus 24/32-bit PCM, IEEE float, IMA-ADPCM and
 * WAVE_FORMAT_EXTENSIBLE, decoding to interleaved float in [-1, 1).
 */
#ifndef MU_WAV_H
#define MU_WAV_H

#include <stddef.h>
#include <stdint.h>

typedef struct mu_pcm {
    float *samples;     /* interleaved, frames*channels */
    uint32_t frames;
    uint16_t channels;
    uint32_t rate;
    uint16_t format;    /* WAVE format tag of the source (1, 2, 3, 0x11; 0xfffe resolved) */
    uint16_t bits;      /* bits per sample of the source */
} mu_pcm;

/* Returns 0 on success; on failure returns -1 and writes a message. */
int mu_wav_decode(const uint8_t *data, size_t size, mu_pcm *out, char *error, size_t error_size);
/* Reads only the header (no sample allocation). */
int mu_wav_probe(const uint8_t *data, size_t size, mu_pcm *out, char *error, size_t error_size);
void mu_pcm_free(mu_pcm *pcm);

/* 16-bit PCM WAV writer; samples are clamped and rounded to nearest. */
int mu_wav_write16(const char *path, const float *samples, uint32_t frames, uint16_t channels, uint32_t rate);
/* Same encoding into memory (caller frees *out). */
int mu_wav_encode16(const float *samples, uint32_t frames, uint16_t channels, uint32_t rate,
                    uint8_t **out, size_t *out_size);

#endif
