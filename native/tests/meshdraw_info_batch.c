/* TEST-SPEED-002: execute the existing info command unchanged, with fewer processes.
 * One JSON line per input, including {} for the failures the validator skips. */
#define main mu_render_single_main
#include "../tools/mu_render.c"
#undef main

int main(int argc, char **argv)
{
    for (int i = 1; i < argc; ++i) {
        char *single[] = {argv[0], "info", argv[i], NULL};
        if (mu_render_single_main(3, single))
            puts("{}");
    }
    return ferror(stdout) ? 1 : 0;
}
