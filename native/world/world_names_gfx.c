/* hudPlayerName through the GFx layer (NATIVE-NAMES-001); see world_names_gfx.h. */
#include "world_names_gfx.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../gfx/mu_gfx_layer.h"

static void clip_path(const world_names_gfx *b, int32_t type, int32_t key, const char *member, char *out, size_t cap)
{
    snprintf(out, cap, "%s.%s%d%s%s", b->path, type == MU_HN_PLAYER ? "playerContainer.ply_" : "container.mon_",
             (int)key, member[0] ? "." : "", member);
}

static void quote(char *out, size_t cap, const char *s)
{
    size_t n = 0;
    if (cap < 3)
        return;
    out[n++] = '"';
    for (; *s && n + 8 < cap; ++s) {
        if (*s == '"' || *s == '\\') {
            out[n++] = '\\';
            out[n++] = *s;
        } else if ((unsigned char)*s < 0x20)
            n += (size_t)snprintf(out + n, cap - n, "\\u%04x", (unsigned char)*s);
        else
            out[n++] = *s;
    }
    out[n++] = '"';
    out[n] = 0;
}

static void invoke(world_names_gfx *b, const char *path, const char *method, const char *args)
{
    b->calls++;
    mu_gfx_layer_invoke(b->layer, MU_GFX_MAIN, path, method, args);
}

static void set(world_names_gfx *b, const char *path, const char *value)
{
    b->calls++;
    mu_gfx_layer_set_variable(b->layer, MU_GFX_MAIN, path, value);
}

static void add_json(world_names_gfx *b, const char *json)
{
    char args[4200];
    snprintf(args, sizeof args, "[%s]", json);
    invoke(b, b->path, "addInfo", args);
}

static void add_info(void *user, const mu_hn_info *info)
{
    world_names_gfx *b = user;
    if (!b->bound)
        return;
    mu_hn_info scaled = *info;   /* the clip's coordinates are stage points */
    scaled.x = (float)(info->x / b->scale);
    scaled.y = (float)(info->y / b->scale);
    char json[4096];
    mu_hn_info_json(&scaled, json, sizeof json);
    add_json(b, json);
}

static void remove_info(void *user, int32_t key, int32_t type)
{
    world_names_gfx *b = user;
    if (!b->bound)
        return;
    char args[64];
    snprintf(args, sizeof args, "[{\"key\":%d,\"type\":%d}]", (int)key, (int)type);
    invoke(b, b->path, "removeInfo", args);
}

static void op(void *user, int32_t type, const mu_hn_op *o)
{
    world_names_gfx *b = user;
    if (!b->bound || (type != MU_HN_PLAYER && type != MU_HN_MONSTER))
        return;
    char path[256], arg[600], q[560];
    const char *b01 = o->number != 0 ? "true" : "false";
    switch (o->kind) {
    case MU_HN_OP_INFO_VISIBLE:
        clip_path(b, type, o->key, "_info._visible", path, sizeof path);
        set(b, path, b01);
        break;
    case MU_HN_OP_MC_VISIBLE:
        clip_path(b, type, o->key, "_visible", path, sizeof path);
        set(b, path, "true");
        break;
    case MU_HN_OP_HP_VISIBLE:
        clip_path(b, type, o->key, "_info._hp._visible", path, sizeof path);
        set(b, path, b01);
        break;
    case MU_HN_OP_POSITION: {
        char v[48];
        clip_path(b, type, o->key, "_x", path, sizeof path);
        snprintf(v, sizeof v, "%.4f", o->number / b->scale);
        set(b, path, v);
        clip_path(b, type, o->key, "_y", path, sizeof path);
        snprintf(v, sizeof v, "%.4f", o->y / b->scale);
        set(b, path, v);
        clip_path(b, type, o->key, "_visible", path, sizeof path);
        set(b, path, "true");
        break;
    }
    case MU_HN_OP_TOP:
        clip_path(b, type, o->key, "", path, sizeof path);
        invoke(b, path, "setTopMovie", "[]");
        break;
    case MU_HN_OP_MESSAGE:
        clip_path(b, type, o->key, "", path, sizeof path);
        quote(q, sizeof q, o->text);
        snprintf(arg, sizeof arg, "[{\"msg\":%s,\"time\":%d}]", q, (int)o->number);
        invoke(b, path, "setMessage", arg);
        break;
    case MU_HN_OP_STORE: {   /* setStore 0x00c84731 / 0x00c848fa (NATIVE-PLAYERS-001) */
        clip_path(b, type, o->key, "", path, sizeof path);
        if (o->number == 0) {
            invoke(b, path, "setStore", "[{\"isOpen\":false}]");
            break;
        }
        char parts[3][200] = {{0}, {0}, {0}};
        const char *s = o->text;
        for (int k = 0; k < 3 && s; ++k) {
            const char *e = strchr(s, 0x1f);
            snprintf(parts[k], sizeof parts[k], "%.*s", e ? (int)(e - s) : (int)strlen(s), s);
            s = e ? e + 1 : NULL;
        }
        char qt[420], qi[420], ql[220];
        quote(qt, sizeof qt, parts[0]);
        quote(qi, sizeof qi, parts[1]);
        quote(ql, sizeof ql, parts[2]);
        snprintf(arg, sizeof arg, "[{\"isOpen\":true,\"store\":%s,\"id\":%s,\"title\":%s}]", ql, qi, qt);
        invoke(b, path, "setStore", arg);
        break;
    }
    default: {
        static const char *const methods[] = {
            [MU_HN_OP_NAME_SHOW] = "setPlayerNameShow", [MU_HN_OP_SET_HP] = "setHp", [MU_HN_OP_HP_SHOW] = "setHpShow",
            [MU_HN_OP_ELEMENTAL] = "setElemental", [MU_HN_OP_GENS] = "setGensFrame", [MU_HN_OP_GUILD] = "setGuildName",
            [MU_HN_OP_SERVER] = "setServerName", [MU_HN_OP_STRIFE] = "setStrifeGens"};
        if (o->kind <= 0 || o->kind >= (int)(sizeof methods / sizeof methods[0]) || !methods[o->kind])
            return;
        clip_path(b, type, o->key, "_info", path, sizeof path);
        if (o->kind == MU_HN_OP_GUILD || o->kind == MU_HN_OP_SERVER) {
            quote(q, sizeof q, o->text);
            snprintf(arg, sizeof arg, "[%s]", q);
        } else if (o->kind == MU_HN_OP_NAME_SHOW || o->kind == MU_HN_OP_HP_SHOW || o->kind == MU_HN_OP_STRIFE)
            snprintf(arg, sizeof arg, "[%s]", b01);
        else
            snprintf(arg, sizeof arg, "[%d]", (int)o->number);
        invoke(b, path, methods[o->kind], arg);
    }
    }
}

void world_names_gfx_attach(world_names_gfx *b, world_gfx *g, mu_names *names, double scale)
{
    memset(b, 0, sizeof *b);
    b->layer = world_gfx_layer(g);
    b->names = names;
    b->scale = scale > 0.0 ? scale : 1.0;
    mu_names_sink sink = {b, add_info, remove_info, op};
    mu_names_set_sink(names, &sink);
}

/* The plates created before the movie loaded: addInfo from the model, then its state. */
static void replay(world_names_gfx *b)
{
    const mu_names *n = b->names;
    for (int32_t i = 0; i < n->plate_count; ++i) {
        const mu_names_plate *p = &n->plates[i];
        char name[600], guild[600], server[600], json[2200];
        quote(name, sizeof name, p->name);
        quote(guild, sizeof guild, p->guild);
        quote(server, sizeof server, p->server);
        snprintf(json, sizeof json,
                 "{\"key\":%d,\"type\":%d,\"name\":%s,\"GuildName\":%s,\"ServerName\":%s,\"elemental\":%d,"
                 "\"mark\":%d,\"x\":%.4f,\"y\":%.4f,\"hp\":%d,\"isShow\":%s,\"isPlayerHpShow\":%s,"
                 "\"isPlayerNameShow\":%s,\"isStrifeGens\":%s,\"GensFrame\":%d,\"attArray\":[],\"damageTypeArray\":[]}",
                 (int)p->key, (int)p->type, name, guild, server, (int)p->elemental, (int)p->mark, p->x / b->scale,
                 p->y / b->scale, (int)p->hp,
                 (p->type == MU_HN_PLAYER ? p->mc_visible : p->info_visible) ? "true" : "false",
                 p->hp_show ? "true" : "false", p->name_show ? "true" : "false", p->strife ? "true" : "false",
                 (int)p->gens);
        add_json(b, json);
        if (p->message[0] && (int32_t)(p->message_until - n->now) > 0) {
            mu_hn_op m = {p->key, MU_HN_OP_MESSAGE, (double)(p->message_until - n->now), 0, {0}};
            snprintf(m.text, sizeof m.text, "%s", p->message);
            op(b, p->type, &m);
        }
    }
}

void world_names_gfx_frame(world_names_gfx *b)
{
    if (b->bound && getenv("MU_NAMES_GFX_PROBE") && ++b->probe % 40 == 0) {   /* debugging aid */
        static const char *const props[] = {"_x", "_y", "_visible", "_info._visible", "_info._txPlayerName.text",
                                            "_info._txPlayerName._visible", "_info._txPlayerName._y", "_ChatMC._visible", "_ChatMC._y", "_ChatMC._txt.text", "_ChatMC._bg._width"};
        for (int32_t i = 0; i < b->names->plate_count; ++i)
            for (size_t k = 0; k < sizeof props / sizeof props[0]; ++k) {
                char path[256];
                clip_path(b, b->names->plates[i].type, b->names->plates[i].key, props[k], path, sizeof path);
                const char *v = mu_gfx_layer_get_variable(b->layer, MU_GFX_MAIN, path);
                fprintf(stderr, "probe %s = %.120s\n", path + strlen(b->path), v ? v : "(null)");
            }
    }
    if (!b->layer || b->bound || !mu_gfx_layer_base_mode(b->layer) || !b->names->stats.frames)
        return;   /* bind after the first update: the replayed clips take addInfo's x/y in onLoad */
    const char *path = mu_gfx_layer_channel_path(b->layer, "hudPlayerName");
    if (!path || !path[0])
        return;
    snprintf(b->path, sizeof b->path, "%s", path);
    b->bound = 1;
    replay(b);
}

int world_names_gfx_active(const world_names_gfx *b)
{
    return b && b->bound;
}
