/* Offline demo session (NATIVE-SHELL-001). See offline-session.h. */
#define _POSIX_C_SOURCE 200809L
#include "offline-session.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void copy_text(char *dst, size_t size, const char *src)
{
    snprintf(dst, size, "%s", src);
}

static char *read_file(const char *path)
{
    FILE *f = fopen(path, "rb");
    if (!f)
        return NULL;
    fseek(f, 0, SEEK_END);
    long n = ftell(f);
    fseek(f, 0, SEEK_SET);
    char *text = n >= 0 ? malloc((size_t)n + 1) : NULL;
    if (text && fread(text, 1, (size_t)n, f) != (size_t)n) {
        free(text);
        text = NULL;
    }
    if (text)
        text[n] = 0;
    fclose(f);
    return text;
}

static void default_servers(mu_ui_server_list *list)
{
    static const char *names[4] = {"Offline-1 (demo)", "Offline-2 (demo)", "Offline-3 (demo)", "Offline-4 (demo)"};
    static const int percents[4] = {20, 45, 70, 5};
    memset(list, 0, sizeof *list);
    copy_text(list->notice, sizeof list->notice, "OFFLINE DEMO: built-in server list, no server is contacted.");
    list->group_count = 1;
    mu_ui_server_group *g = &list->groups[0];
    g->id = 1;
    g->position = MU_UI_GROUP_LEFT;
    g->button = -1;
    copy_text(g->name, sizeof g->name, "Offline");
    copy_text(g->description, sizeof g->description, "Native client offline demo (no network)");
    g->server_count = 4;
    for (int i = 0; i < 4; ++i) {
        g->servers[i].slot = i;
        g->servers[i].percent = percents[i];
        g->servers[i].type = (uint8_t)(i % 4);
        copy_text(g->servers[i].name, sizeof g->servers[i].name, names[i]);
    }
}

void mu_offline_session_default(mu_offline_session *s)
{
    memset(s, 0, sizeof *s);
    default_servers(&s->servers);
    mu_charsel_list_default(&s->characters);
    s->server_group = s->server_slot = -1;
}

int mu_offline_session_parse_servers(const char *text, mu_ui_server_list *list, char *error, size_t error_size)
{
    memset(list, 0, sizeof *list);
    int line_number = 0;
    for (const char *p = text; *p;) {
        const char *end = strchr(p, '\n');
        size_t n = end ? (size_t)(end - p) : strlen(p);
        char line[512];
        if (n >= sizeof line)
            n = sizeof line - 1;
        memcpy(line, p, n);
        line[n] = 0;
        p += n + (end ? 1 : 0);
        ++line_number;
        char *cr = strchr(line, '\r');
        if (cr)
            *cr = 0;
        if (!line[0] || line[0] == '#')
            continue;
        if (!strncmp(line, "notice ", 7)) {
            copy_text(list->notice, sizeof list->notice, line + 7);
        } else if (!strncmp(line, "group ", 6)) {
            char where[16];
            int type, id, used = 0;
            if (list->group_count >= MU_UI_SERVER_GROUPS_MAX ||
                sscanf(line + 6, "%15s %d %d %n", where, &type, &id, &used) < 3) {
                snprintf(error, error_size, "servers line %d: expected group left|right|top TYPE ID NAME|TEXT",
                         line_number);
                return 1;
            }
            mu_ui_server_group *g = &list->groups[list->group_count++];
            g->position = !strcmp(where, "right") ? MU_UI_GROUP_RIGHT
                        : !strcmp(where, "top")   ? MU_UI_GROUP_TOP
                                                  : MU_UI_GROUP_LEFT;
            g->type = (uint8_t)type;
            g->id = id;
            g->button = -1;
            char *rest = line + 6 + used, *bar = strchr(rest, '|');
            if (bar) {
                *bar = 0;
                copy_text(g->description, sizeof g->description, bar + 1);
            }
            copy_text(g->name, sizeof g->name, rest);
        } else if (!strncmp(line, "server ", 7)) {
            int percent, type, used = 0;
            if (!list->group_count || sscanf(line + 7, "%d %d %n", &percent, &type, &used) < 2) {
                snprintf(error, error_size, "servers line %d: expected server PERCENT TYPE NAME after a group",
                         line_number);
                return 1;
            }
            mu_ui_server_group *g = &list->groups[list->group_count - 1];
            if (g->server_count >= MU_UI_GROUP_SERVERS_MAX) {
                snprintf(error, error_size, "servers line %d: more than %d servers in a group", line_number,
                         MU_UI_GROUP_SERVERS_MAX);
                return 1;
            }
            mu_ui_server *sv = &g->servers[g->server_count];
            sv->slot = g->server_count++;
            sv->percent = percent;
            sv->type = (uint8_t)type;
            copy_text(sv->name, sizeof sv->name, line + 7 + used);
        } else {
            snprintf(error, error_size, "servers line %d: unknown line", line_number);
            return 1;
        }
    }
    if (!list->group_count) {
        snprintf(error, error_size, "servers: no group");
        return 1;
    }
    return 0;
}

static void beside(char *out, size_t size, const char *session_path, const char *name)
{
    if (name[0] == '/') {
        copy_text(out, size, name);
        return;
    }
    const char *slash = strrchr(session_path, '/');
    if (!slash)
        copy_text(out, size, name);
    else
        snprintf(out, size, "%.*s/%s", (int)(slash - session_path), session_path, name);
}

int mu_offline_session_load(mu_offline_session *s, const char *path, const char *root, char *error,
                            size_t error_size)
{
    mu_offline_session_default(s);
    char *text = read_file(path);
    if (!text) {
        snprintf(error, error_size, "%s: cannot read", path);
        return 1;
    }
    int status = 0, line_number = 0;
    for (char *p = text; *p && !status;) {
        char *end = strchr(p, '\n');
        if (end)
            *end = 0;
        ++line_number;
        char *hash = strchr(p, '#');
        if (hash)
            *hash = 0;
        char key[32], value[MU_OFFLINE_PATH];
        int fields = sscanf(p, "%31s %1023[^\r\n]", key, value);
        if (fields >= 1) {
            if (fields < 2) {
                snprintf(error, error_size, "%s line %d: missing value", path, line_number);
                status = 1;
            } else if (!strcmp(key, "servers")) {
                char *trim = value + strlen(value);
                while (trim > value && (trim[-1] == ' ' || trim[-1] == '\t'))
                    *--trim = 0;
                beside(s->servers_path, sizeof s->servers_path, path, value);
            } else if (!strcmp(key, "characters")) {
                char *trim = value + strlen(value);
                while (trim > value && (trim[-1] == ' ' || trim[-1] == '\t'))
                    *--trim = 0;
                beside(s->characters_path, sizeof s->characters_path, path, value);
            } else if (!strcmp(key, "join")) {
                mu_offline_join j = {0, 0, {0, 0}, 0.0f};
                int n = sscanf(value, "%d %d %d,%d %f", &j.slot, &j.world, &j.tile[0], &j.tile[1], &j.angle);
                if (n < 4 || j.slot < 0 || j.slot > 9 || j.world < 0 || j.tile[0] < 0 || j.tile[0] > 255 ||
                    j.tile[1] < 0 || j.tile[1] > 255 || s->join_count >= MU_OFFLINE_JOINS) {
                    snprintf(error, error_size, "%s line %d: expected join SLOT WORLD X,Y [ANGLE]", path, line_number);
                    status = 1;
                } else {
                    s->joins[s->join_count++] = j;
                }
            } else {
                snprintf(error, error_size, "%s line %d: unknown key %s", path, line_number, key);
                status = 1;
            }
        }
        p = end ? end + 1 : p + strlen(p);
    }
    free(text);
    if (status)
        return 1;
    if (s->servers_path[0]) {
        char *servers = read_file(s->servers_path);
        if (!servers) {
            snprintf(error, error_size, "%s: cannot read", s->servers_path);
            return 1;
        }
        status = mu_offline_session_parse_servers(servers, &s->servers, error, error_size);
        free(servers);
        if (status)
            return 1;
    }
    if (s->characters_path[0]) {
        char *characters = read_file(s->characters_path);
        if (!characters) {
            snprintf(error, error_size, "%s: cannot read", s->characters_path);
            return 1;
        }
        char message[256];
        status = mu_charsel_list_parse(characters, root, &s->characters, message, sizeof message);
        free(characters);
        if (status) {
            snprintf(error, error_size, "%s: %s", s->characters_path, message);
            return 1;
        }
    }
    return 0;
}

void mu_offline_session_choose_server(mu_offline_session *s, int32_t group, int32_t slot)
{
    s->server_group = group;
    s->server_slot = slot;
}

int32_t mu_offline_session_login(mu_offline_session *s)
{
    ++s->logins;
    s->protocol = 0x14;
    return s->protocol;
}

int32_t mu_offline_session_character_list(mu_offline_session *s)
{
    s->protocol = 0x33;
    return s->protocol;
}

mu_offline_join mu_offline_session_join(const mu_offline_session *s, int32_t slot)
{
    for (int32_t i = 0; i < s->join_count; ++i)
        if (s->joins[i].slot == slot)
            return s->joins[i];
    mu_offline_join j = {slot, 0, {133, 127}, 0.0f};
    return j;
}

const mu_charsel_entry *mu_offline_session_character(const mu_offline_session *s, int32_t slot)
{
    for (int32_t i = 0; i < s->characters.count; ++i)
        if (s->characters.entries[i].slot == slot)
            return &s->characters.entries[i];
    return NULL;
}
