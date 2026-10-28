/* HelpWindow host. No frame hook, session or network dependencies. */
#include "world_gfx_help.h"
#include "../gfx/mu_gfx_layer.h"
#include "../core/mu_lang.h"
#include "../../reconstructed/help/help.h"
#include "../../reconstructed/hud/tooltip_html.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct { mu_gfx_layer *layer; int failed; } help_host;

static size_t quote(char *out, size_t cap, const char *raw)
{
    char utf8[512];
    mu_latin1_to_utf8(utf8, sizeof utf8, raw);
    size_t at = 0;
    out[at++] = '"';
    for (const unsigned char *s = (const unsigned char *)utf8; *s; ++s) {
        if (at + 7 >= cap) return 0;
        if (*s < 32) at += (size_t)snprintf(out + at, cap - at, "\\u%04x", *s);
        else {
            if (*s == '"' || *s == '\\') out[at++] = '\\';
            out[at++] = (char)*s;
        }
    }
    out[at++] = '"';
    out[at] = 0;
    return at;
}

static void invoke(void *user, const char *method, size_t argc, const char *const *args)
{
    help_host *host = user;
    char json[4096] = "[";
    size_t at = 1;
    for (size_t i = 0; i < argc; ++i) {
        char q[1024];
        if (!quote(q, sizeof q, args[i])) { host->failed = 1; return; }
        int n = snprintf(json + at, sizeof json - at, "%s%s", i ? "," : "", q);
        if (n < 0 || (size_t)n >= sizeof json - at - 2) { host->failed = 1; return; }
        at += (size_t)n;
    }
    snprintf(json + at, sizeof json - at, "]");
    mu_gfx_layer_invoke(host->layer, MU_GFX_HELP, NULL, method, json);
}

int world_gfx_help_load(mu_gfx_layer *layer, const char *root, const mu_lang *lang)
{
    if (!layer) return 0;
    mu_gfx_layer_help_ready(layer, 0);
    if (!*mu_gfx_layer_path(layer, MU_GFX_HELP)) return 0;
    mu_gfx_layer_invoke(layer, MU_GFX_HELP, NULL, "ClearDataProvider", "[]");
    if (!root) return 0;
    char path[4096];
    int n = snprintf(path, sizeof path, "%s/Data/Local/helpdata.bmd", root);
    if (n < 0 || (size_t)n >= sizeof path) return 0;
    mu_help_table *table = malloc(sizeof *table);
    mu_help_provider *provider = malloc(sizeof *provider);
    int ready = 0;
    if (table && provider) {
        mu_help_status status = mu_help_read(table, path);
        if (status == MU_HELP_OK) {
            static const char *const fallback[] = {"Help", "Hotkeys", "Chat commands", "Key", "Action"};
            const char *labels[5];
            for (int i = 0; i < 5; ++i)
                labels[i] = mu_lang_text_or(lang, 0xd57 + i, fallback[i]);
            mu_help_provider_init(provider);
            help_host host = {layer, 0};
            /* Native mode policy: standard input mode. The original mode
             * predicate is an input to the validated controller, not a
             * recovered platform/IME preference in this adapter. */
            ready = mu_help_load(provider, table, 1, 0, labels, invoke, &host) && !host.failed;
        } else fprintf(stderr, "HelpWindow: helpdata %s; native Ctrl+H unavailable\n", mu_help_status_name(status));
    }
    free(provider);
    free(table);
    mu_gfx_layer_help_ready(layer, ready);
    if (ready) fprintf(stderr, "HelpWindow: installed rows loaded; Ctrl+H is a native binding\n");
    return ready;
}
