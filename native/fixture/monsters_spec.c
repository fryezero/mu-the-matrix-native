/* Authored fixture placement specification, moved from mu_world_actors. */
#include "monsters_demo.h"
#include <ctype.h>
#include <stdio.h>
#include <string.h>
int mu_monsters_parse(const char *text, mu_monster_spec *specs, int32_t *count, char *error, size_t error_size)
{
    int number = 0;
    const char *p = text;
    while (*p) {
        const char *end = strchr(p, '\n');
        size_t n = end ? (size_t)(end - p) : strlen(p);
        char line[512];
        if (n >= sizeof line)
            n = sizeof line - 1;
        memcpy(line, p, n);
        line[n] = 0;
        p += n + (end ? 1 : 0);
        ++number;
        char *hash = strchr(line, '#');
        if (hash)
            *hash = 0;
        char *q = line;
        while (isspace((unsigned char)*q))
            ++q;
        if (!*q)
            continue;
        int32_t server_class, x, y, direction, wander = 0;
        int used = 0;
        if (sscanf(q, "actor %d %d %d %d%n", &server_class, &x, &y, &direction, &used) != 4 || x < 0 || y < 0 ||
            x > 255 || y > 255) {
            snprintf(error, error_size, "placement line %d: expected \"actor CLASS X Y DIRECTION ...\"", number);

            return 1;
        }
        q += used;
        char label[48] = "";
        while (*q) {
            while (isspace((unsigned char)*q))
                ++q;
            if (!strncmp(q, "wander", 6)) {
                if (sscanf(q + 6, "%d%n", &wander, &used) != 1) {
                    snprintf(error, error_size, "placement line %d: wander needs a radius", number);

                    return 1;
                }
                q += 6 + used;
            } else if (!strncmp(q, "label", 5)) {
                q += 5;
                while (isspace((unsigned char)*q))
                    ++q;
                snprintf(label, sizeof label, "%s", q);
                size_t len = strlen(label);
                while (len && isspace((unsigned char)label[len - 1]))
                    label[--len] = 0;
                break;
            } else if (*q) {
                snprintf(error, error_size, "placement line %d: unknown field \"%s\"", number, q);

                return 1;
            }
        }
        if (*count == MU_WORLD_ACTORS_MAX) {
            snprintf(error, error_size, "placement: more than %d actors", MU_WORLD_ACTORS_MAX);

            return 1;
        }
        if (server_class < 0 || server_class > 1023 || wander > 255) {
            snprintf(error, error_size, "placement: class or wander outside supported range"); return 1;
        }
        mu_monster_spec *spec = &specs[(*count)++];
        *spec = (mu_monster_spec){.server_class=server_class,.x=x,.y=y,.direction=direction,.wander=wander < 0 ? 0 : wander};
        snprintf(spec->label, sizeof spec->label, "%s", label);
    }
    return 0;
}
