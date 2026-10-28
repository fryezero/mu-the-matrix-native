#include "../charsel_rt_internal.h"

static int open_ui(mu_charsel_rt *a)
{
    if (!a->options.no_ui) {
        a->ui = calloc(1, sizeof *a->ui);
        if (!a->ui || mu_charsel_ui_init(a->ui, a->options.root, a->options.width, a->options.height, a->options.font, a->s, a->options.tip)) {
            fprintf(stderr, "2D layer initialisation failed\n");
            return 1;
        }
    }
    return 0;
}

static void close_ui(mu_charsel_rt *a)
{
    if (a->ui) {
        mu_charsel_ui_free(a->ui);
        free(a->ui);
        a->ui = NULL;
    }
}

const mu_charsel_part_ops mu_charsel_ui_part = {
    .open = open_ui,
    .close = close_ui,
};
