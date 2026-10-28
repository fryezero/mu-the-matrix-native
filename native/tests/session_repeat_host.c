/* Invoke the real tool entry points repeatedly, with a fresh owner each time. */
#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef REPEAT_WORLD
int mu_world_tool_main(int argc, char **argv);
#else
int mu_session_tool_main(int argc, char **argv);
#endif
int main(int argc, char **argv)
{
    assert(argc >= 4 && (argc - 2) % 2 == 0);
    for (int i = 2; i < argc; i += 2) {
        char path[4096];
        snprintf(path, sizeof path, "%s/%d.txt", argv[1], (i - 2) / 2);
        assert(freopen(path, "w", stdout));
#ifdef REPEAT_WORLD
        assert(setenv("MU_LANG_DIR", argv[i+1], 1) == 0);
        char demo[4096], renders[4096];
        snprintf(renders, sizeof renders, "%s/repeat-frames", argv[i]);
        snprintf(demo, sizeof demo, "%s/demo.txt", argv[i+1]);
        assert(setenv("MU_SKILL_DEMO", demo, 1) == 0);
        char *args[] = {"mu-walk", "--game-root", argv[i], "--headless", "--backend", "soft",
                        "--no-audio", "--no-env", "--no-particles", "--width", "64", "--height", "64",
                        "--out-dir", renders, "--frames", "4", "--every", "1", "--helper", "imp", NULL};
        int rc = mu_world_tool_main((int)(sizeof args / sizeof args[0]) - 1, args);
#else
        char journal[4096];
        snprintf(journal, sizeof journal, "%s/%d.jnl", argv[1], (i - 2) / 2);
        char *args[] = {"mu-session", "fixture", argv[i], "--seed", argv[i+1], "--ticks", "100", "--journal", journal, NULL};
        int rc = mu_session_tool_main((int)(sizeof args / sizeof args[0]) - 1, args);
#endif
        if (rc) { fprintf(stderr, "repeat run %d failed: %d\n", i, rc); return rc; }
        fflush(stdout);
    }
    return 0;
}
