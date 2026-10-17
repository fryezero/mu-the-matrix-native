/* mu-audio: native audio module front end (NATIVE-AUDIO-001).
 *
 *   mu-audio list   [--table TSV] [--root GAME] [--music] [--id N]
 *                   sound table rows (id, path, legacy arguments, loader) and,
 *                   with --root, the decoded format of each file
 *   mu-audio render --script FILE --out OUT.wav [--table TSV] [--root GAME]
 *                   [--rate HZ] [--options INI | --no-options] [--verbose]
 *                   run a script through the reconstructed client audio logic
 *                   and the native mixer; prints the SHA-256 of the PCM data
 *   mu-audio decode FILE --out OUT.wav [--root GAME]
 *                   decode one file (WAV, or MP3/OGG with the platform decoder)
 *   mu-audio scan   --root GAME
 *                   decode every WAV under Data/Sound (read-only corpus pass)
 *
 * The table comes from scripts/extract_audio_tables.py and stays local.
 */
#define _POSIX_C_SOURCE 200809L
#include <dirent.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <sys/stat.h>

#include "../core/mu_audio.h"
#include "../core/mu_audio_host.h"
#include "../core/mu_png.h"
#include "../core/mu_wav.h"

typedef struct options {
    const char *command, *table, *root, *script, *out, *options, *file;
    uint32_t rate;
    int music, verbose, no_options, has_id;
    int32_t id;
} options;

static void usage(void)
{
    fprintf(stderr,
            "usage:\n"
            "  mu-audio list   [--table TSV] [--root GAME] [--music] [--id N]\n"
            "  mu-audio render --script FILE --out OUT.wav [--table TSV] [--root GAME] [--rate HZ]\n"
            "                  [--options INI | --no-options] [--verbose]\n"
            "  mu-audio decode FILE --out OUT.wav [--root GAME]\n"
            "  mu-audio scan   --root GAME\n");
}

static int parse(int argc, char **argv, options *o)
{
    memset(o, 0, sizeof *o);
    o->rate = 44100;
    if (argc < 2) return -1;
    o->command = argv[1];
    for (int i = 2; i < argc; i++) {
        const char *a = argv[i];
        const char *next = i + 1 < argc ? argv[i + 1] : NULL;
#define TAKE(field) do { if (!next) return -1; o->field = next; i++; } while (0)
        if (!strcmp(a, "--table")) TAKE(table);
        else if (!strcmp(a, "--root")) TAKE(root);
        else if (!strcmp(a, "--script")) TAKE(script);
        else if (!strcmp(a, "--out")) TAKE(out);
        else if (!strcmp(a, "--options")) TAKE(options);
        else if (!strcmp(a, "--rate")) {
            if (!next) return -1;
            long rate = strtol(next, NULL, 10);
            if (rate < 8000 || rate > 192000) return -1;
            o->rate = (uint32_t)rate;
            i++;
        } else if (!strcmp(a, "--id")) {
            if (!next) return -1;
            o->id = (int32_t)strtol(next, NULL, 0);
            o->has_id = 1;
            i++;
        } else if (!strcmp(a, "--music")) o->music = 1;
        else if (!strcmp(a, "--verbose")) o->verbose = 1;
        else if (!strcmp(a, "--no-options")) o->no_options = 1;
        else if (a[0] != '-' && !o->file) o->file = a;
        else return -1;
#undef TAKE
    }
    return 0;
}

static void log_line(void *ctx, const char *message)
{
    (void)ctx;
    fprintf(stderr, "mu-audio: %s\n", message);
}

static const char *format_name(uint16_t format)
{
    switch (format) {
    case 1: return "pcm";
    case 2: return "ms-adpcm";
    case 3: return "float";
    case 0x11: return "ima-adpcm";
    default: return "?";
    }
}

static void describe(const char *root, const char *path, char *out, size_t size)
{
    char host[4096];
    if (mu_audio_resolve_path(root, path, host, sizeof host)) {
        snprintf(out, size, "missing");
        return;
    }
    FILE *f = fopen(host, "rb");
    uint8_t header[4096];
    size_t got = f ? fread(header, 1, sizeof header, f) : 0;
    if (f) fclose(f);
    mu_pcm pcm;
    char error[256];
    if (got >= 12 && !memcmp(header, "RIFF", 4)) {
        /* Probe needs the data chunk header; read the whole file when the
         * 4 KiB prefix does not reach it. */
        if (mu_wav_probe(header, got, &pcm, error, sizeof error) == 0) {
            snprintf(out, size, "wav %s %u-bit %uch %u Hz", format_name(pcm.format), pcm.bits, pcm.channels, pcm.rate);
            return;
        }
        mu_pcm full;
        if (mu_audio_load_file(root, path, &full, error, sizeof error) == 0) {
            snprintf(out, size, "wav %s %u-bit %uch %u Hz %u frames", format_name(full.format), full.bits,
                     full.channels, full.rate, full.frames);
            mu_pcm_free(&full);
        } else {
            snprintf(out, size, "error: %s", error);
        }
        return;
    }
    const char *dot = strrchr(path, '.');
    snprintf(out, size, "%s (platform decoder)", dot ? dot + 1 : "compressed");
}

static int command_list(const options *o)
{
    mu_audio_table table = {0};
    char error[512];
    if (!o->table) {
        fprintf(stderr, "list needs --table (scripts/extract_audio_tables.py --tsv)\n");
        return 1;
    }
    if (mu_audio_table_load(o->table, &table, error, sizeof error)) {
        fprintf(stderr, "%s\n", error);
        return 1;
    }
    size_t shown = 0, missing = 0, ids = 0;
    int32_t previous = INT32_MIN;
    if (!o->music) {
        printf("%-6s %-6s %-4s %-3s %-10s %-56s%s\n", "id", "hex", "ch", "3d", "loader", "path", o->root ? " file" : "");
        for (size_t i = 0; i < table.count; i++) {
            const mu_audio_table_row *r = &table.rows[i];
            if (o->has_id && r->id != o->id) continue;
            if (r->id != previous) ids++;
            previous = r->id;
            char info[300] = "";
            if (o->root) {
                describe(o->root, r->path, info, sizeof info);
                if (!strcmp(info, "missing")) missing++;
            }
            char ch[8], d3[8];
            snprintf(ch, sizeof ch, r->legacy_channels < 0 ? "var" : "%d", r->legacy_channels);
            snprintf(d3, sizeof d3, r->legacy_3d < 0 ? "var" : "%d", r->legacy_3d);
            printf("%-6d 0x%-4x %-4s %-3s 0x%08x %-56s%s%s\n", r->id, (unsigned)r->id, ch, d3, r->loader, r->path,
                   o->root ? " " : "", info);
            shown++;
        }
        printf("# %zu rows, %zu ids%s", shown, ids, o->root ? "" : "\n");
        if (o->root) printf(", %zu missing files\n", missing);
    } else {
        for (int i = 0; i < MU_AUDIO_MUSIC_ENTRIES; i++) {
            if (o->has_id && i != o->id) continue;
            char info[300] = "";
            const char *path = table.music[i];
            if (o->root && path) describe(o->root, path, info, sizeof info);
            printf("%-3d %-48s %s\n", i, path ? path : "(unresolved)", info);
        }
    }
    mu_audio_table_free(&table);
    return 0;
}

typedef struct render_sink {
    float *samples;
    size_t frames, capacity;
} render_sink;

static int collect(void *ctx, const float *stereo, uint32_t frames)
{
    render_sink *s = ctx;
    if (s->frames + frames > s->capacity) {
        size_t capacity = s->capacity ? s->capacity*2 : 1u << 18;
        while (capacity < s->frames + frames) capacity *= 2;
        float *grown = realloc(s->samples, capacity*2*sizeof(float));
        if (!grown) return -1;
        s->samples = grown;
        s->capacity = capacity;
    }
    memcpy(s->samples + 2*s->frames, stereo, (size_t)frames*2*sizeof(float));
    s->frames += frames;
    return 0;
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

static int command_render(const options *o)
{
    if (!o->script || !o->out) {
        usage();
        return 2;
    }
    char error[600];
    mu_audio_table table = {0};
    if (o->table && mu_audio_table_load(o->table, &table, error, sizeof error)) {
        fprintf(stderr, "%s\n", error);
        return 1;
    }
    char *text = read_all(o->script);
    if (!text) {
        fprintf(stderr, "cannot read %s\n", o->script);
        mu_audio_table_free(&table);
        return 1;
    }
    mu_audio_script script;
    int status = mu_audio_script_parse(text, &script, error, sizeof error);
    free(text);
    if (status) {
        fprintf(stderr, "%s: %s\n", o->script, error);
        mu_audio_table_free(&table);
        return 1;
    }
    mu_audio_host_config config = {{o->rate, o->root, 0, NULL, o->verbose ? log_line : NULL},
                                   o->table ? &table : NULL, o->options, o->no_options};
    mu_audio_host *host = mu_audio_host_new(&config, error, sizeof error);
    if (!host) {
        fprintf(stderr, "%s\n", error);
        mu_audio_script_free(&script);
        mu_audio_table_free(&table);
        return 1;
    }
    render_sink sink = {0};
    status = mu_audio_host_run(host, &script, collect, &sink, error, sizeof error);
    mu_audio_host_free(host);
    mu_audio_script_free(&script);
    mu_audio_table_free(&table);
    if (status) {
        fprintf(stderr, "%s\n", error);
        free(sink.samples);
        return 1;
    }
    uint8_t *wav;
    size_t size;
    if (mu_wav_encode16(sink.samples, (uint32_t)sink.frames, 2, o->rate, &wav, &size)) {
        fprintf(stderr, "cannot encode output\n");
        free(sink.samples);
        return 1;
    }
    FILE *f = fopen(o->out, "wb");
    int ok = f && fwrite(wav, 1, size, f) == size;
    if (f && fclose(f)) ok = 0;
    char digest[65];
    mu_sha256_hex(wav + 44, size - 44, digest);
    float peak = 0.0f;
    for (size_t i = 0; i < 2*sink.frames; i++) {
        float v = sink.samples[i] < 0 ? -sink.samples[i] : sink.samples[i];
        if (v > peak) peak = v;
    }
    free(wav);
    free(sink.samples);
    if (!ok) {
        fprintf(stderr, "cannot write %s\n", o->out);
        return 1;
    }
    printf("{\"frames\": %zu, \"rate\": %u, \"seconds\": %.3f, \"peak\": %.6f, \"pcm_sha256\": \"%s\"}\n",
           sink.frames, o->rate, (double)sink.frames/o->rate, (double)peak, digest);
    return 0;
}

static int command_decode(const options *o)
{
    if (!o->file || !o->out) {
        usage();
        return 2;
    }
    mu_pcm pcm;
    char error[600];
    int status;
    const char *root = o->root ? o->root : o->file[0] == '/' ? "/" : ".";
    status = mu_audio_load_file(root, o->file, &pcm, error, sizeof error);
    if (status) {
        fprintf(stderr, "%s\n", error);
        return 1;
    }
    if (mu_wav_write16(o->out, pcm.samples, pcm.frames, pcm.channels, pcm.rate)) {
        fprintf(stderr, "cannot write %s\n", o->out);
        mu_pcm_free(&pcm);
        return 1;
    }
    printf("{\"format\": \"%s\", \"bits\": %u, \"channels\": %u, \"rate\": %u, \"frames\": %u}\n",
           format_name(pcm.format), pcm.bits, pcm.channels, pcm.rate, pcm.frames);
    mu_pcm_free(&pcm);
    return 0;
}

typedef struct scan_totals {
    size_t files, decoded, failed, frames;
    size_t by_format[4];
} scan_totals;

static void scan_dir(const char *directory, scan_totals *t)
{
    DIR *dir = opendir(directory);
    if (!dir) return;
    struct dirent *entry;
    while ((entry = readdir(dir))) {
        if (entry->d_name[0] == '.') continue;
        char path[4096];
        snprintf(path, sizeof path, "%s/%s", directory, entry->d_name);
        struct stat st;
        if (lstat(path, &st)) continue;
        if (S_ISDIR(st.st_mode)) {
            scan_dir(path, t);
            continue;
        }
        size_t n = strlen(entry->d_name);
        if (n < 4 || strcasecmp(entry->d_name + n - 4, ".wav")) continue;
        t->files++;
        mu_pcm pcm;
        char error[600];
        if (mu_audio_load_file("/", path, &pcm, error, sizeof error)) {
            t->failed++;
            fprintf(stderr, "%s\n", error);
            continue;
        }
        t->decoded++;
        t->frames += pcm.frames;
        t->by_format[pcm.format == 1 ? (pcm.bits == 8 ? 0 : 1) : pcm.format == 2 ? 2 : 3]++;
        mu_pcm_free(&pcm);
    }
    closedir(dir);
}

static int command_scan(const options *o)
{
    if (!o->root) {
        usage();
        return 2;
    }
    char sound[4096];
    if (mu_audio_resolve_path(o->root, "Data/Sound", sound, sizeof sound)) {
        fprintf(stderr, "no Data/Sound under %s\n", o->root);
        return 1;
    }
    scan_totals t = {0};
    scan_dir(sound, &t);
    printf("{\"wav_files\": %zu, \"decoded\": %zu, \"failed\": %zu, \"pcm8\": %zu, \"pcm16\": %zu, "
           "\"ms_adpcm\": %zu, \"other\": %zu, \"frames\": %zu}\n",
           t.files, t.decoded, t.failed, t.by_format[0], t.by_format[1], t.by_format[2], t.by_format[3], t.frames);
    return t.failed ? 1 : 0;
}

int main(int argc, char **argv)
{
    options o;
    if (parse(argc, argv, &o)) {
        usage();
        return 2;
    }
    if (!strcmp(o.command, "list")) return command_list(&o);
    if (!strcmp(o.command, "render")) return command_render(&o);
    if (!strcmp(o.command, "decode")) return command_decode(&o);
    if (!strcmp(o.command, "scan")) return command_scan(&o);
    usage();
    return 2;
}
