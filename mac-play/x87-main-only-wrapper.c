/* SPDX-License-Identifier: MIT
 * Copyright (c) 2026 Frye
 * Authored loader routing for Mu The Matrix. See ../LICENSE.
 */
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <unistd.h>

/* Match arguments, not argv[0] (the wrapper's own path). Empty/unset means all. */
static int use_fast_runtime(int argc, char **argv)
{
    const char *filter = getenv("TIMEWALKER_X87_ONLY");
    if (filter == NULL || *filter == '\0')
        return 1;
    size_t length = strlen(filter);
    for (int i = 1; i < argc; ++i) {
        for (const char *candidate = argv[i]; *candidate; ++candidate) {
            if (strncasecmp(candidate, filter, length) == 0)
                return 1;
        }
    }
    return 0;
}

int main(int argc, char **argv)
{
    const char *runtime = getenv("TIMEWALKER_X87_RUNTIME_LOADER");
    const char *loader = getenv("TIMEWALKER_X87_REAL_LOADER");
    if (runtime == NULL || *runtime == '\0' || loader == NULL || *loader == '\0') {
        fputs("mu-x87: TIMEWALKER_X87_RUNTIME_LOADER and "
              "TIMEWALKER_X87_REAL_LOADER must be set\n", stderr);
        return 127;
    }
    if (access(runtime, X_OK) != 0 || access(loader, X_OK) != 0) {
        fprintf(stderr, "mu-x87: loader is not executable: %s\n", strerror(errno));
        return 127;
    }
    if (!use_fast_runtime(argc, argv)) {
        argv[0] = (char *)loader;
        execv(loader, argv);
        fprintf(stderr, "mu-x87: could not launch real loader: %s\n", strerror(errno));
        return 127;
    }
    /* Insert the real loader before the original arguments, preserving boundaries. */
    char **forwarded = calloc((size_t)argc + 2, sizeof(*forwarded));
    if (forwarded == NULL) {
        fputs("mu-x87: cannot allocate loader arguments\n", stderr);
        return 127;
    }
    forwarded[0] = (char *)runtime;
    forwarded[1] = (char *)loader;
    for (int i = 1; i < argc; ++i)
        forwarded[i + 1] = argv[i];
    execv(runtime, forwarded);
    fprintf(stderr, "mu-x87: could not launch runtime loader: %s\n", strerror(errno));
    free(forwarded);
    return 127;
}
