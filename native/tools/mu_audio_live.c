/* mu-audio-live: plays an audio script live through SDL2 audio.
 *
 *   mu-audio-live --script FILE [--table TSV] [--root GAME] [--rate HZ]
 *                 [--options INI | --no-options] [--verbose]
 *
 * The same host as `mu-audio render` (reconstructed client logic on the
 * native mixer, 40 ms client frames); each frame's samples are queued to an
 * SDL float32 stereo device and the loop is paced by the queue depth.
 */
#include <SDL.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../core/mu_audio_host.h"

typedef struct live {
    SDL_AudioDeviceID device;
    uint32_t rate;
} live;

static int queue_frame(void *ctx, const float *stereo, uint32_t frames)
{
    live *l = ctx;
    if (SDL_QueueAudio(l->device, stereo, frames*2u*(uint32_t)sizeof(float))) return -1;
    /* Keep about 120 ms queued: wait while more than that is pending. */
    const Uint32 limit = l->rate*2u*(Uint32)sizeof(float)*120u/1000u;
    while (SDL_GetQueuedAudioSize(l->device) > limit) SDL_Delay(5);
    return 0;
}

static void log_line(void *ctx, const char *message)
{
    (void)ctx;
    fprintf(stderr, "mu-audio-live: %s\n", message);
}

static char *read_all(const char *path)
{
    FILE *f = fopen(path, "rb");
    if (!f) return NULL;
    fseek(f, 0, SEEK_END);
    long n = ftell(f);
    fseek(f, 0, SEEK_SET);
    char *text = n >= 0 ? malloc((size_t)n + 1) : NULL;
    if (text && fread(text, 1, (size_t)n, f) != (size_t)n) {
        free(text);
        text = NULL;
    }
    fclose(f);
    if (text) text[n] = 0;
    return text;
}

int main(int argc, char **argv)
{
    const char *script_path = NULL, *table_path = NULL, *root = NULL, *options = NULL;
    int verbose = 0, no_options = 0;
    uint32_t rate = 44100;
    for (int i = 1; i < argc; i++) {
        const char *next = i + 1 < argc ? argv[i + 1] : NULL;
        if (!strcmp(argv[i], "--script") && next) script_path = argv[++i];
        else if (!strcmp(argv[i], "--table") && next) table_path = argv[++i];
        else if (!strcmp(argv[i], "--root") && next) root = argv[++i];
        else if (!strcmp(argv[i], "--options") && next) options = argv[++i];
        else if (!strcmp(argv[i], "--rate") && next) rate = (uint32_t)strtoul(argv[++i], NULL, 10);
        else if (!strcmp(argv[i], "--verbose")) verbose = 1;
        else if (!strcmp(argv[i], "--no-options")) no_options = 1;
        else {
            fprintf(stderr, "usage: mu-audio-live --script FILE [--table TSV] [--root GAME] [--rate HZ] "
                            "[--options INI | --no-options] [--verbose]\n");
            return 2;
        }
    }
    if (!script_path || rate < 8000 || rate > 192000) {
        fprintf(stderr, "mu-audio-live: --script is required (rate 8000..192000)\n");
        return 2;
    }
    char error[600];
    mu_audio_table table = {0};
    if (table_path && mu_audio_table_load(table_path, &table, error, sizeof error)) {
        fprintf(stderr, "%s\n", error);
        return 1;
    }
    char *text = read_all(script_path);
    mu_audio_script script;
    if (!text || mu_audio_script_parse(text, &script, error, sizeof error)) {
        fprintf(stderr, "%s: %s\n", script_path, text ? error : "cannot read");
        free(text);
        mu_audio_table_free(&table);
        return 1;
    }
    free(text);
    if (SDL_Init(SDL_INIT_AUDIO)) {
        fprintf(stderr, "SDL_Init: %s\n", SDL_GetError());
        return 1;
    }
    SDL_AudioSpec want = {0}, have;
    want.freq = (int)rate;
    want.format = AUDIO_F32SYS;
    want.channels = 2;
    want.samples = 1024;
    live l = {SDL_OpenAudioDevice(NULL, 0, &want, &have, 0), rate};
    if (!l.device) {
        fprintf(stderr, "SDL_OpenAudioDevice: %s\n", SDL_GetError());
        SDL_Quit();
        return 1;
    }
    SDL_PauseAudioDevice(l.device, 0);
    mu_audio_host_config config = {{rate, root, 0, NULL, verbose ? log_line : NULL},
                                   table_path ? &table : NULL, options, no_options};
    mu_audio_host *host = mu_audio_host_new(&config, error, sizeof error);
    int status = 1;
    if (host) {
        status = mu_audio_host_run(host, &script, queue_frame, &l, error, sizeof error) ? 1 : 0;
        while (SDL_GetQueuedAudioSize(l.device) > 0) SDL_Delay(10);
        mu_audio_host_free(host);
    }
    if (status) fprintf(stderr, "%s\n", error);
    SDL_CloseAudioDevice(l.device);
    SDL_Quit();
    mu_audio_script_free(&script);
    mu_audio_table_free(&table);
    return status;
}
