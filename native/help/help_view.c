/* SYS-MISC-001b isolated offline viewer. This is not a client input binding.
 * Real HelpWindow.swf + installed helpdata.bmd; no network or session state.
 * English headings are labelled native test labels. Rows use the existing
 * native Latin-1 conversion policy, not a recovered original code page.
 * No allocations are made by this tool's per-frame loop. */
#include <SDL.h>
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../gfx/mugfx/include/mugfx.h"
#include "../../reconstructed/help/help.h"
#include "../../reconstructed/hud/tooltip_html.h"
#include "../core/mu_png.h"

typedef struct {
    MuGfx *(*open)(const char *, int, int, char *, size_t);
    void (*close)(MuGfx *);
    void (*set_callback)(MuGfx *, mugfx_callback, void *);
    void (*start)(MuGfx *);
    void (*advance)(MuGfx *, double);
    int (*render)(MuGfx *, uint8_t *, size_t);
    const char *(*invoke)(MuGfx *, const char *, const char *, const char *);
    int (*set_variable)(MuGfx *, const char *, const char *);
    const char *(*get_variable)(MuGfx *, const char *);
    int (*mouse)(MuGfx *, int, int, double, double);
    int (*abi_version)(void);
} api;

typedef struct {
    api a;
    MuGfx *movie;
    char path[160];
    int closed, failed, hotkeys, chatkeys;
} view;

static const char *callback(void *user, const char *name, const char *json)
{
    view *v = user;
    if (!strcmp(name, "UIInit")) {
        char uid[128];
        if (sscanf(json, "[\"%127[^\"]", uid) == 1 &&
            strspn(uid, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_") == strlen(uid))
            snprintf(v->path, sizeof v->path, "_level0.%s", uid);
    } else if (!strcmp(name, "CloseWindow")) {
        v->closed = 1;
    }
    return NULL;
}

static void quote(char *out, size_t cap, const char *raw)
{
    char utf8[512];
    mu_latin1_to_utf8(utf8, sizeof utf8, raw);
    size_t at = 0;
    out[at++] = '"';
    for (const unsigned char *s = (const unsigned char *)utf8; *s && at + 7 < cap; ++s) {
        if (*s < 32) at += (size_t)snprintf(out + at, cap - at, "\\u%04x", *s);
        else {
            if (*s == '"' || *s == '\\') out[at++] = '\\';
            out[at++] = (char)*s;
        }
    }
    out[at++] = '"';
    out[at] = 0;
}

static void invoke(void *user, const char *method, size_t argc, const char *const *args)
{
    view *v = user;
    char json[4096] = "[";
    size_t at = 1;
    for (size_t i = 0; i < argc; ++i) {
        char q[1024];
        quote(q, sizeof q, args[i]);
        int n = snprintf(json + at, sizeof json - at, "%s%s", i ? "," : "", q);
        if (n < 0 || (size_t)n >= sizeof json - at - 2) { v->failed = 1; return; }
        at += (size_t)n;
    }
    snprintf(json + at, sizeof json - at, "]");
    v->a.invoke(v->movie, v->path, method, json);
    v->hotkeys += !strcmp(method, "SetHotKeyData");
    v->chatkeys += !strcmp(method, "SetChatHotKeyData");
}

static int provider_count(view *v, const char *field)
{
    char path[256];
    snprintf(path, sizeof path, "%s.%s.dataProvider.length", v->path, field);
    const char *value = v->a.get_variable(v->movie, path);
    if (!value || *value < '0' || *value > '9') return -1;
    return atoi(value);
}

int main(int argc, char **argv)
{
    const char *movie = NULL, *data = NULL, *library = NULL, *output = NULL;
    int windowed = 0, chat = 0, mode = 0, frames = 40;
    for (int i = 1; i < argc; ++i) {
        if (!strcmp(argv[i], "--window")) windowed = 1;
        else if (!strcmp(argv[i], "--chat")) chat = 1;
        else if (i + 1 < argc && !strcmp(argv[i], "--movie")) movie = argv[++i];
        else if (i + 1 < argc && !strcmp(argv[i], "--data")) data = argv[++i];
        else if (i + 1 < argc && !strcmp(argv[i], "--lib")) library = argv[++i];
        else if (i + 1 < argc && !strcmp(argv[i], "--out")) output = argv[++i];
        else if (i + 1 < argc && !strcmp(argv[i], "--frames")) frames = atoi(argv[++i]);
        else if (i + 1 < argc && !strcmp(argv[i], "--mode")) mode = atoi(argv[++i]);
        else { fprintf(stderr, "Unknown/incomplete option: %s\n", argv[i]); return 2; }
    }
    if (!movie || !data || !library || frames < 1 || frames > 10000 || (mode != 0 && mode != 1)) {
        fprintf(stderr, "mu-help-view --movie FILE --data FILE --lib FILE [--out PNG] [--window] [--chat] [--mode 0|1] [--frames N]\n");
        return 2;
    }
    int result = 1;
    view v = {0};
    void *dl = NULL;
    SDL_Window *window = NULL;
    SDL_Renderer *renderer = NULL;
    SDL_Texture *texture = NULL;
    uint8_t *pixels = NULL;
    const int width = 1024, height = 768;
    const size_t bytes = (size_t)width * (size_t)height * 4;
    mu_help_table *table = malloc(sizeof *table);
    mu_help_provider *provider = malloc(sizeof *provider);
    if (!table || !provider) goto done;
    mu_help_status status = mu_help_read(table, data);
    if (status != MU_HELP_OK) {
        fprintf(stderr, "help reader: %s\n", mu_help_status_name(status));
        goto done;
    }
    dl = dlopen(library, RTLD_NOW | RTLD_LOCAL);
    if (!dl) { fprintf(stderr, "%s\n", dlerror()); goto done; }
#define LOAD(name) do { *(void **)(&v.a.name) = dlsym(dl, "mugfx_" #name); \
    if (!v.a.name) { fprintf(stderr, "Missing mugfx_%s\n", #name); goto done; } } while (0)
    LOAD(open); LOAD(close); LOAD(set_callback); LOAD(start); LOAD(advance); LOAD(render);
    LOAD(invoke); LOAD(set_variable); LOAD(get_variable); LOAD(mouse); LOAD(abi_version);
#undef LOAD
    if (v.a.abi_version() != MUGFX_ABI_VERSION) goto done;
    char error[512] = "";
    v.movie = v.a.open(movie, width, height, error, sizeof error);
    if (!v.movie) { fprintf(stderr, "movie: %s\n", error); goto done; }
    v.a.set_callback(v.movie, callback, &v);
    v.a.set_variable(v.movie, "_global.gSystem", "{\"isClient\":true}");
    v.a.set_variable(v.movie, "_global.gStandard", "{\"ResizeStageHeight\":768}");
    v.a.start(v.movie);
    for (int i = 0; i < 10; ++i) v.a.advance(v.movie, 40.0);
    if (!v.path[0]) { fprintf(stderr, "HelpWindow did not report UIInit\n"); goto done; }
    mu_help_provider_init(provider);
    const char *labels[] = {"Help", "Hotkeys", "Chat commands", "Key", "Action"};
    if (!mu_help_load(provider, table, 1, mode, labels, invoke, &v) || v.failed) {
        fprintf(stderr, "HelpWindow provider refused input\n");
        goto done;
    }
    v.a.invoke(v.movie, v.path, "SetVisible", "[true]");
    if (chat) v.a.invoke(v.movie, v.path, "OnClickChatHotKey", "[]");
    pixels = malloc(bytes);
    if (!pixels) goto done;
    if (windowed) {
        if (SDL_Init(SDL_INIT_VIDEO | SDL_INIT_EVENTS)) goto done;
        window = SDL_CreateWindow("HelpWindow isolated native test viewer", SDL_WINDOWPOS_CENTERED,
                                  SDL_WINDOWPOS_CENTERED, width, height, 0);
        if (!window) goto done;
        renderer = SDL_CreateRenderer(window, -1, SDL_RENDERER_ACCELERATED | SDL_RENDERER_PRESENTVSYNC);
        if (!renderer) goto done;
        texture = SDL_CreateTexture(renderer, SDL_PIXELFORMAT_RGBA32, SDL_TEXTUREACCESS_STREAMING, width, height);
        if (!texture) goto done;
        SDL_SetTextureBlendMode(texture, SDL_BLENDMODE_BLEND);
    }
    for (int frame = 0; frame < frames && !v.closed; ++frame) {
        SDL_Event event;
        while (windowed && SDL_PollEvent(&event)) {
            if (event.type == SDL_QUIT || (event.type == SDL_KEYDOWN && event.key.keysym.sym == SDLK_ESCAPE))
                v.closed = 1;
            if (event.type == SDL_MOUSEMOTION)
                v.a.mouse(v.movie, 0, 0, event.motion.x, event.motion.y);
            if (event.type == SDL_MOUSEBUTTONDOWN || event.type == SDL_MOUSEBUTTONUP)
                v.a.mouse(v.movie, event.type == SDL_MOUSEBUTTONDOWN ? 1 : 2, 0, event.button.x, event.button.y);
            if (event.type == SDL_MOUSEWHEEL) {
                int x, y;
                SDL_GetMouseState(&x, &y);
                v.a.mouse(v.movie, 3, event.wheel.y, x, y);
            }
        }
        v.a.advance(v.movie, 40.0);
        if (v.a.render(v.movie, pixels, bytes)) goto done;
        if (windowed) {
            SDL_UpdateTexture(texture, NULL, pixels, width * 4);
            SDL_SetRenderDrawColor(renderer, 36, 30, 42, 255);
            SDL_RenderClear(renderer);
            SDL_RenderCopy(renderer, texture, NULL, NULL);
            SDL_RenderPresent(renderer);
            SDL_Delay(24);
        }
    }
    int hotkeys = provider_count(&v, "scrollingHotKey"), chatkeys = provider_count(&v, "scrollingChatKey");
    printf("{\"mode\":%d,\"windowed\":%d,\"hotkeys_sent\":%d,\"chatkeys_sent\":%d,\"movie_hotkeys\":%d,\"movie_chatkeys\":%d}\n",
           mode, windowed, v.hotkeys, v.chatkeys, hotkeys, chatkeys);
    if (hotkeys != v.hotkeys || chatkeys != v.chatkeys) goto done;
    if (output && mu_png_write(output, pixels, width, height)) goto done;
    result = 0;
done:
    if (texture) SDL_DestroyTexture(texture);
    if (renderer) SDL_DestroyRenderer(renderer);
    if (window) SDL_DestroyWindow(window);
    if (windowed) SDL_Quit();
    if (v.movie) v.a.close(v.movie);
    if (dl) dlclose(dl);
    free(pixels);
    free(provider);
    free(table);
    return result;
}
