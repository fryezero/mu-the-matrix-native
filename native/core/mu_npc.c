/* Talking to NPCs in the walk-around world (NATIVE-NPC-001); see mu_npc.h. */
#define _POSIX_C_SOURCE 200809L
#include "mu_npc.h"

#include <math.h>
#include <stdlib.h>
#include <string.h>

/* ---- demo table ---------------------------------------------------------------------------- */

static int parse_item(const char *word, mu_npc_item *out)
{
    char *end = NULL;
    long code = strtol(word, &end, 0);
    if (end == word || code < 0 || code > 0xffff)
        return 1;
    out->code = (int32_t)code;
    out->level = 0;
    if (*end == '+') {
        char *e2 = NULL;
        long level = strtol(end + 1, &e2, 0);
        if (e2 == end + 1 || level < 0 || level > 15)
            return 1;
        out->level = (int32_t)level;
        end = e2;
    }
    return *end != 0;
}

int mu_npc_demo_parse(mu_npc_demo *demo, const char *text, char *error, size_t error_size)
{
    memset(demo, 0, sizeof *demo);
    int line_no = 0;
    const char *p = text;
    while (*p) {
        const char *eol = strchr(p, '\n');
        size_t n = eol ? (size_t)(eol - p) : strlen(p);
        char line[1024];
        if (n >= sizeof line)
            n = sizeof line - 1;
        memcpy(line, p, n);
        line[n] = 0;
        p += eol ? n + 1 : n;
        ++line_no;
        char *hash = strchr(line, '#');
        if (hash)
            *hash = 0;
        if (!strncmp(line, "actor", 5) && (line[5] == ' ' || line[5] == '\t')) {
            size_t len = strlen(line);
            if (demo->placement_length + len + 2 > sizeof demo->placement) {
                snprintf(error, error_size, "line %d: too many actor lines", line_no);
                return 1;
            }
            memcpy(demo->placement + demo->placement_length, line, len);
            demo->placement_length += len;
            demo->placement[demo->placement_length++] = '\n';
            demo->placement[demo->placement_length] = 0;
            continue;
        }
        if ((!strncmp(line, "quest", 5) && (line[5] == ' ' || line[5] == '\t')) ||
            (!strncmp(line, "guide", 5) && (line[5] == ' ' || line[5] == '\t')) ||
            (!strncmp(line, "classic", 7) && (line[7] == ' ' || line[7] == '\t'))) {
            size_t len = strlen(line);
            if (demo->quests_length + len + 2 > sizeof demo->quests) {
                snprintf(error, error_size, "line %d: too many quest lines", line_no);
                return 1;
            }
            memcpy(demo->quests + demo->quests_length, line, len);
            demo->quests_length += len;
            demo->quests[demo->quests_length++] = '\n';
            demo->quests[demo->quests_length] = 0;
            continue;
        }
        char *save = NULL, *word = strtok_r(line, " \t\r", &save);
        if (!word)
            continue;
        if (!strcmp(word, "dialog") || !strcmp(word, "classicnpc")) {
            int classic = !strcmp(word, "classicnpc");
            char *cls = strtok_r(NULL, " \t\r", &save), *npc = strtok_r(NULL, " \t\r", &save);
            char *contribution = strtok_r(NULL, " \t\r", &save);
            if (!cls || (!classic && !npc)) {
                snprintf(error, error_size, "line %d: dialog needs a server class and a dialogue NPC", line_no);
                return 1;
            }
            int32_t server_class = (int32_t)strtol(cls, NULL, 0);
            mu_npc_demo_row *row = (mu_npc_demo_row *)mu_npc_demo_find(demo, server_class);
            if (!row) {
                if (demo->count >= MU_NPC_DEMO_ROWS) {
                    snprintf(error, error_size, "line %d: more than %d NPC rows", line_no, MU_NPC_DEMO_ROWS);
                    return 1;
                }
                row = &demo->rows[demo->count++];
                memset(row, 0, sizeof *row);
                row->server_class = server_class;
                row->result = -1;
            }
            row->classic = classic;
            row->dialog_npc = npc && !classic ? (int32_t)strtol(npc, NULL, 0) : 0;
            row->contribution = contribution ? (int32_t)strtol(contribution, NULL, 0) : 0;
            continue;
        }
        if (!strcmp(word, "talk") || !strcmp(word, "shop")) {
            int is_talk = !strcmp(word, "talk");
            char *cls = strtok_r(NULL, " \t\r", &save);
            if (!cls) {
                snprintf(error, error_size, "line %d: %s needs a server class", line_no, word);
                return 1;
            }
            int32_t server_class = (int32_t)strtol(cls, NULL, 0);
            mu_npc_demo_row *row = (mu_npc_demo_row *)mu_npc_demo_find(demo, server_class);
            if (!row) {
                if (demo->count >= MU_NPC_DEMO_ROWS) {
                    snprintf(error, error_size, "line %d: more than %d NPC rows", line_no, MU_NPC_DEMO_ROWS);
                    return 1;
                }
                row = &demo->rows[demo->count++];
                memset(row, 0, sizeof *row);
                row->server_class = server_class;
                row->result = -1;
            }
            if (is_talk) {
                char *r = strtok_r(NULL, " \t\r", &save);
                char *end = NULL;
                long result = r ? strtol(r, &end, 0) : -1;
                if (!r || *end || result < 0 || result > 255) {
                    snprintf(error, error_size, "line %d: talk needs a result byte 0..255", line_no);
                    return 1;
                }
                row->result = (int32_t)result;
                int32_t *list = NULL, *count = NULL;
                while ((word = strtok_r(NULL, " \t\r", &save))) {
                    if (!strcmp(word, "dialog")) {
                        list = row->dialog;
                        count = &row->dialog_count;
                    } else if (!strcmp(word, "options")) {
                        list = row->options;
                        count = &row->option_count;
                    } else if (list && *count < MU_NPC_DIALOG) {
                        list[(*count)++] = (int32_t)strtol(word, NULL, 0);
                    } else {
                        snprintf(error, error_size, "line %d: unexpected '%s'", line_no, word);
                        return 1;
                    }
                }
            } else {
                while ((word = strtok_r(NULL, " \t\r", &save))) {
                    if (row->shop_count >= MU_NPC_ITEMS || parse_item(word, &row->shop[row->shop_count])) {
                        snprintf(error, error_size, "line %d: bad shop item '%s'", line_no, word);
                        return 1;
                    }
                    row->shop_count++;
                }
            }
        } else if (!strcmp(word, "storage")) {
            while ((word = strtok_r(NULL, " \t\r", &save))) {
                if (demo->storage_count >= MU_NPC_ITEMS || parse_item(word, &demo->storage[demo->storage_count])) {
                    snprintf(error, error_size, "line %d: bad storage item '%s'", line_no, word);
                    return 1;
                }
                demo->storage_count++;
            }
        } else {
            snprintf(error, error_size, "line %d: unknown keyword '%s'", line_no, word);
            return 1;
        }
    }
    return 0;
}

int mu_npc_demo_load(mu_npc_demo *demo, const char *path, char *error, size_t error_size)
{
    FILE *f = fopen(path, "rb");
    if (!f) {
        snprintf(error, error_size, "%s: cannot open", path);
        return 1;
    }
    char *text = malloc(1 << 20);
    size_t n = text ? fread(text, 1, (1 << 20) - 1, f) : 0;
    fclose(f);
    if (!text) {
        snprintf(error, error_size, "out of memory");
        return 1;
    }
    text[n] = 0;
    int r = mu_npc_demo_parse(demo, text, error, error_size);
    free(text);
    return r;
}

const mu_npc_demo_row *mu_npc_demo_find(const mu_npc_demo *demo, int32_t server_class)
{
    for (int32_t i = 0; demo && i < demo->count; i++)
        if (demo->rows[i].server_class == server_class)
            return &demo->rows[i];
    return NULL;
}

/* ---- session --------------------------------------------------------------------------------- */

static void log_line(mu_npc *n, const char *text)
{
    if (n->log_count < 32)
        snprintf(n->log[n->log_count++], sizeof n->log[0], "%s", text);
}

void mu_npc_init(mu_npc *npc, mu_walk *walk, mu_world_actors *actors, const mu_npc_demo *demo)
{
    memset(npc, 0, sizeof *npc);
    npc->walk = walk;
    npc->actors = actors;
    npc->demo = demo;
    npc->latency = 4;
    npc->hero_level = 400;
    npc->selected = npc->target = npc->pending_actor = npc->last_pick = -1;
    npc->character_bit = 1;
    npc->arrivals_seen = walk ? walk->arrivals : 0;
}

static int is_npc(const mu_npc *n, int32_t i)
{
    return n->actors && i >= 0 && i < n->actors->count && n->actors->list[i].actor.spec.npc_index >= 0;
}

int32_t mu_npc_find_actor(const mu_npc *n, const char *name)
{
    if (!n->actors || !name)
        return -1;
    char *end = NULL;
    long index = strtol(name, &end, 10);
    if (end && end != name && *end == 0)
        return index >= 0 && index < n->actors->count ? (int32_t)index : -1;
    for (int32_t i = 0; i < n->actors->count; i++)
        if (!strcmp(n->actors->list[i].label, name))
            return i;
    return -1;
}

void mu_npc_pick_inputs(mu_npc *n)
{
    memset(n->pick, 0, sizeof n->pick);
    for (int32_t i = 0; i < MU_PICK_CHARACTERS; i++)
        n->pick[i].kind = 0xff;   /* empty slots never match a mask */
    for (int32_t i = 0; n->actors && i < n->actors->count && i < MU_PICK_CHARACTERS; i++) {
        const mu_world_actor *a = &n->actors->list[i];
        mu_pick_character *c = &n->pick[i];
        c->live = 1;
        c->visible = 1;
        c->alpha = 1.0f;
        c->kind = a->actor.spec.npc_index >= 0 ? 4 : 2;   /* KIND_NPC / KIND_MONSTER (o + 0x3b) */
        c->type = a->actor.spec.model_index;
        c->c10 = 1;
        memcpy(c->position, a->position, sizeof c->position);
        float mn[3], mx[3];
        mu_character_box(c->type, mn, mx);
        mu_character_obb(mn, mx, a->position, &c->obb);
    }
}

/* MoveCharacters 0x0137a7ce (static): clear bit 2 of every tile, then set it
 * on the tile of every live, not dead character whose kind is not 8. */
static void character_bits(mu_npc *n)
{
    uint16_t *walls = n->walk->frame.walls;
    for (int32_t i = 0; i < MU_TERRAIN_SIZE * MU_TERRAIN_SIZE; i++)
        if (walls[i] & 2)
            walls[i] = (uint16_t)(walls[i] - 2);
    const mu_hero *h = &n->walk->hero;
    walls[((h->tile[1] & 0xff) << 8) + (h->tile[0] & 0xff)] |= 2;
    for (int32_t i = 0; n->actors && i < n->actors->count; i++) {
        const mu_world_actor *a = &n->actors->list[i];
        walls[((a->tile[1] & 0xff) << 8) + (a->tile[0] & 0xff)] |= 2;
    }
}

/* Action case 2 (0x0169901c, static): stop, the local refusals, the repair
 * flag, the talk request (C1 0x95 key: network, the demo server answers). */
static void talk(mu_npc *n)
{
    mu_walk *w = n->walk;
    int32_t i = n->target;
    n->movement_type = 0;
    if (w->hero.movement)
        mu_walk_stop(w);                                  /* SetPlayerStop, c + 0x38 = 0 */
    if (!is_npc(n, i)) {                                  /* character +0x328f must be 4 */
        n->target = -1;
        return;
    }
    const mu_world_actor *a = &n->actors->list[i];
    mu_talk_gate gate = {a->server_class, n->hero_level, 0, 0};
    int32_t refusal = mu_npc_talk_refusal(&gate);
    char text[112];
    if (refusal >= 0) {
        ++n->stats.refusals;
        snprintf(text, sizeof text, "step %d: talk to %s refused (GlobalText %#x)", n->step, a->label, refusal);
        log_line(n, text);
        n->target = -1;
        return;
    }
    ++n->stats.talks;
    n->pending_actor = i;
    n->pending_step = n->step + n->latency;
    snprintf(text, sizeof text, "step %d: talk request to %s (class %d, repair %d)", n->step, a->label,
             a->server_class, mu_npc_repair_shop(a->server_class));
    log_line(n, text);
    n->target = -1;                                       /* 0x0169c08d */
}

int mu_npc_click(mu_npc *n, int32_t i)
{
    mu_walk *w = n->walk;
    if (!is_npc(n, i))
        return 0;
    if (n->window_open) {                                 /* NpcShop or StorageInven visible: 0x016aae23 */
        ++n->stats.clicks_ignored;
        return 0;
    }
    const mu_world_actor *a = &n->actors->list[i];
    n->selected = i;
    n->movement_type = 2;
    n->target = i;
    char text[112];
    if (a->actor.spec.model_index == 0xa3e) {             /* within 550 units: Action at once */
        float dx = w->hero.position[0] - a->position[0], dy = w->hero.position[1] - a->position[1];
        if (sqrtf(dx * dx + dy * dy) <= 550.0f) {
            ++n->stats.immediate_talks;
            talk(n);
            return 1;
        }
    }
    if (n->character_bit)
        character_bits(n);
    if (mu_walk_path_to(w, a->tile[0], a->tile[1])) {
        ++n->stats.walks;
        n->arrivals_seen = w->arrivals;
        snprintf(text, sizeof text, "step %d: walk to %s at tile %d,%d", n->step, a->label, a->tile[0], a->tile[1]);
        log_line(n, text);
    } else {
        ++n->stats.immediate_talks;                       /* no path of more than one node: Action now */
        talk(n);
    }
    return 1;
}

void mu_npc_pre_step(mu_npc *n)
{
    mu_frame_world *f = &n->walk->frame;
    if (!f->mouse.left_push)
        return;
    ++n->stats.picks;
    mu_npc_pick_inputs(n);
    mu_pick_scene scene;
    memset(&scene, 0, sizeof scene);
    scene.scene = 6;
    scene.world = n->walk->world;
    memcpy(scene.ray_start, f->view.mouse_position, sizeof scene.ray_start);
    memcpy(scene.ray_end, f->view.mouse_target, sizeof scene.ray_end);
    memcpy(scene.camera, f->view.position, sizeof scene.camera);
    /* worlds 0 and 2 read a per-tile byte map (0x0b735420) that the native world does not fill; with no
     * map the world-2 refusal never applies (layer choice) */
    int32_t i = mu_npc_pick(n->pick, n->actors ? n->actors->count : 0, 4, &scene);
    n->last_pick = i;
    if (i < 0) {
        n->movement_type = 0;                             /* a click elsewhere: MoveHero's other branches */
        return;
    }
    ++n->stats.pick_hits;
    if (!n->window_open) {
        f->mouse.left_push = 0;                           /* the click selects the NPC, not a tile */
        f->mouse.left = 0;
    }
    mu_npc_click(n, i);
}

static void answer(mu_npc *n)
{
    int32_t i = n->pending_actor;
    n->pending_actor = -1;
    if (!is_npc(n, i))
        return;
    const mu_world_actor *a = &n->actors->list[i];
    const mu_npc_demo_row *row = mu_npc_demo_find(n->demo, a->server_class);
    if (row && (row->dialog_npc > 0 || row->classic)) {
        /* NATIVE-QUEST-001: the NPC dialogue packet F9 01 (npc, contribution); its handler 0x0126d5da opens
         * npcdialogue for that dialogue NPC (no ReceiveTalk: no close-all, no sounds) */
        ++n->stats.answers;
        mu_npc_open open;
        memset(&open, 0, sizeof open);
        open.actor = i;
        open.server_class = a->server_class;
        open.npc_index = a->actor.spec.npc_index;
        open.model = a->actor.spec.model_index;
        open.kind = row->classic ? MU_NPC_WINDOW_CLASSIC : MU_NPC_WINDOW_DIALOG;
        open.window.dialogue = row->dialog_npc;
        open.window.movie = row->classic ? "NpcJobChangeQuest" : "npcdialogue";
        open.dialog_packet = !row->classic;
        open.contribution = row->contribution;
        open.demo = row;
        char text[112];
        snprintf(text, sizeof text, "step %d: answer %s from %s: NPC %d", n->step,
                 row->classic ? "C1 A1 (quest demo)" : "F9 01", a->label, row->dialog_npc);
        log_line(n, text);
        ++n->stats.windows;
        if (n->open)
            n->open(n->context, &open);
        return;
    }
    uint8_t packet[16] = {0xc1, 16, 0xdf, 0};
    packet[3] = row && row->result >= 0 ? (uint8_t)row->result : 0xff;   /* demo: NPCs without a row answer 0xff */
    packet[0xb] = 1;                                                  /* one shop tab */
    mu_talk_input in;
    memset(&in, 0, sizeof in);
    in.packet = packet;
    in.length = sizeof packet;
    in.encrypted = 1;
    in.has_b0 = in.has_b4 = in.has_ac = 1;
    in.hero_x = n->walk->hero.tile[0];
    in.hero_y = n->walk->hero.tile[1];
    in.cursor_lock = 1;                                   /* the native client does not move the OS cursor */
    mu_talk_output out;
    mu_npc_talk_result(&in, &out);                        /* ReceiveTalk 0x01280659 (verified) */
    ++n->stats.answers;
    mu_npc_open open;
    memset(&open, 0, sizeof open);
    open.actor = i;
    open.server_class = a->server_class;
    open.npc_index = a->actor.spec.npc_index;
    open.model = a->actor.spec.model_index;
    open.result = packet[3];
    open.repair = mu_npc_repair_shop(a->server_class);
    open.shop_tabs = packet[0xb];
    open.demo = row;
    mu_npc_talk_window(packet[3], &open.window);
    for (int k = 0; k < out.count; k++) {
        const mu_talk_event *e = &out.events[k];
        if (e->callee == MU_TALK_CLOSE_ALL && e->self == MU_TALK_SELF_MANAGER)
            open.close_all = 1;
        if (e->callee == MU_TALK_SND_PLAY) {
            ++n->stats.sounds;
            if (n->sound)
                n->sound(n->context, (int32_t)e->args[0]);
        }
    }
    if (open.close_all && n->close_all)
        n->close_all(n->context);
    switch (open.window.kind) {
    case MU_TALK_KIND_DIALOGUE: open.kind = MU_NPC_WINDOW_DIALOG; break;
    case MU_TALK_KIND_OPEN:
        open.kind = open.window.slot == 0x0f4 ? MU_NPC_WINDOW_SHOP
                  : open.window.slot == 0x100 ? MU_NPC_WINDOW_STORAGE : MU_NPC_WINDOW_OTHER;
        break;
    case MU_TALK_KIND_NONE: open.kind = MU_NPC_WINDOW_NONE; break;
    default: open.kind = MU_NPC_WINDOW_OTHER; break;
    }
    char text[112];
    snprintf(text, sizeof text, "step %d: answer %#04x from %s: %s%s", n->step, open.result, a->label,
             open.window.movie[0] ? open.window.movie : "(no window)",
             open.kind == MU_NPC_WINDOW_OTHER ? " (not played natively)" : "");
    log_line(n, text);
    if (open.kind == MU_NPC_WINDOW_OTHER)
        ++n->stats.not_played;
    if (open.kind != MU_NPC_WINDOW_NONE && open.kind != MU_NPC_WINDOW_OTHER) {
        ++n->stats.windows;
        n->window_open = open.kind == MU_NPC_WINDOW_SHOP || open.kind == MU_NPC_WINDOW_STORAGE;
    }
    if (n->open)
        n->open(n->context, &open);
}

void mu_npc_step(mu_npc *n)
{
    ++n->step;
    if (n->character_bit)
        character_bits(n);
    mu_walk *w = n->walk;
    if (n->movement_type == 2 && w->arrivals != n->arrivals_seen) {
        /* MoveHero's walk end: MovePath arrived, SetPlayerStop, Action(c, o, 0) (0x016a9c7c..0x016a9ccc) */
        n->arrivals_seen = w->arrivals;
        talk(n);
    }
    n->arrivals_seen = w->arrivals;
    if (n->pending_actor >= 0 && n->step >= n->pending_step)
        answer(n);
}

void mu_npc_window_closed(mu_npc *n)
{
    n->window_open = 0;
}

/* ---- reports and script ---------------------------------------------------------------------------- */

void mu_npc_report_frame(const mu_npc *n, FILE *out, int32_t frame)
{
    fprintf(out, "{\"npc_frame\": %d, \"step\": %d, \"selected\": %d, \"target\": %d, \"movement_type\": %u,"
            " \"pending\": %d, \"window_open\": %d, \"last_pick\": %d, \"hero_tile\": [%d, %d], \"moving\": %u}\n",
            frame, n->step, n->selected, n->target, n->movement_type, n->pending_actor, n->window_open, n->last_pick,
            n->walk->hero.tile[0], n->walk->hero.tile[1], n->walk->hero.movement);
}

void mu_npc_report_summary(const mu_npc *n, FILE *out, int quiet)
{
    const mu_npc_stats *s = &n->stats;
    fprintf(out, "{\"npc\": true, \"picks\": %u, \"pick_hits\": %u, \"clicks_ignored\": %u, \"walks\": %u,"
            " \"immediate_talks\": %u, \"talks\": %u, \"refusals\": %u, \"answers\": %u, \"windows\": %u,"
            " \"not_played\": %u, \"sounds\": %u, \"demo_rows\": %d}\n", s->picks, s->pick_hits, s->clicks_ignored,
            s->walks, s->immediate_talks, s->talks, s->refusals, s->answers, s->windows, s->not_played, s->sounds,
            n->demo ? n->demo->count : 0);
    if (!quiet)
        for (int32_t i = 0; i < n->log_count; i++)
            fprintf(out, "{\"npc_log\": \"%s\"}\n", n->log[i]);
}

static int item_start(const char *p)
{
    const char *q = p;
    while (*q >= '0' && *q <= '9')
        ++q;
    return q > p && *q == ':';
}

int mu_npc_script_parse(mu_npc_script *script, const char *text)
{
    memset(script, 0, sizeof *script);
    const char *p = text;
    while (*p) {
        while (*p == ' ' || *p == '\t' || *p == ';' || *p == ',')
            ++p;
        if (!*p)
            break;
        if (script->count >= MU_NPC_SCRIPT)
            return 1;
        size_t n = 0;
        while (p[n] && p[n] != ';' && p[n] != ',') {
            if ((p[n] == ' ' || p[n] == '\t') && n > 0) {
                size_t k = n;
                while (p[k] == ' ' || p[k] == '\t')
                    ++k;
                if (!p[k] || item_start(p + k))
                    break;
            }
            ++n;
        }
        char token[128];
        if (n + 1 > sizeof token)
            return 1;
        memcpy(token, p, n);
        token[n] = 0;
        p += n;
        while (n > 0 && (token[n - 1] == ' ' || token[n - 1] == '\t'))
            token[--n] = 0;
        mu_npc_script_item *it = &script->items[script->count];
        char *a = strchr(token, ':');
        if (!a)
            return 1;
        *a++ = 0;
        it->frame = atoi(token);
        char *b = strchr(a, ':');
        if (b)
            *b++ = 0;
        snprintf(it->verb, sizeof it->verb, "%s", a);
        snprintf(it->arg, sizeof it->arg, "%s", b ? b : "");
        static const char *const VERBS[] = {"click", "talk", "buy", "sell", "take", "put", "option", "next", "close",
                                            "tip", "tipinv", "bufftip",
                                            /* NATIVE-QUEST-001 (world_gfx's quest verbs) */
                                            "qnext", "qno", "qok", "qclose", "qwin", "qtab", "qsel", "qgo", "qgiveup",
                                            "qkill", "qset", "qtrack", "qclass", "qcnext", "qcok", "qgset", "qcheck"};
        int known = 0;
        for (size_t v = 0; v < sizeof VERBS / sizeof VERBS[0]; v++)
            known |= !strcmp(it->verb, VERBS[v]);
        if (!known)
            return 1;
        if ((!strcmp(it->verb, "click") || !strcmp(it->verb, "talk") || !strcmp(it->verb, "buy") ||
             !strcmp(it->verb, "sell") || !strcmp(it->verb, "take") || !strcmp(it->verb, "put") ||
             !strcmp(it->verb, "option")) && !b)
            return 1;
        ++script->count;
    }
    return 0;
}
