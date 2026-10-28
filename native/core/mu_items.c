/* Dropped items in the walk-around world (NATIVE-ITEMS-001). See mu_items.h. */
#include "mu_items.h"
#include "../session/mu_session.h"
#include "../fixture/mu_fixture.h"
#include "../fixture/items_demo.h"
#include "mu_label.h"
#include "../../reconstructed/items/item_sets.h"

#include <math.h>
#include <stdlib.h>
#include <string.h>

#include "../../reconstructed/camera/client_camera.h"
#include "../../reconstructed/combat/combat.h"
#include "../../reconstructed/movement/client_movement.h"
#include "../../reconstructed/objects/object_render.h"
#include "mu_combat.h"
#include "mu_lang.h"
#include "mu_particles.h"

#define CODE_LIMIT 0x2c00

static void log_line(mu_world_items *it, const char *text)
{
    int32_t slot = it->log_count < 32 ? it->log_count : 31;
    if (it->log_count >= 32)
        memmove(it->log[0], it->log[1], sizeof it->log[0] * 31);
    snprintf(it->log[slot], sizeof it->log[slot], "%s", text);
    if (it->log_count < 32)
        ++it->log_count;
}

void mu_world_items_default_config(mu_world_items_config *c)
{
    memset(c, 0, sizeof *c);
    c->seed = 20261018u;
    c->drop_latency = 14;          /* demo: after the death action starts (the die packet's dead counter) */
    c->pickup_latency = 4;         /* demo: the combat module's server latency */
    c->despawn_steps = 1500;       /* demo: one minute */
    c->drop_chance = 100;
    c->quality = 5;
    c->glow_color[0] = 0.4f;
    c->glow_color[1] = 0.6f;
    c->glow_color[2] = 1.0f;
    c->font_face = "Arial";
    c->font_height = 12;
}

/* ---------------------------------------------------------------- engine services */

static int32_t crt_rand(mu_world_items *it)
{
    it->crt_seed = it->crt_seed * 214013u + 2531011u;   /* rand() 0x01989721 (MSVC) */
    return (int32_t)((it->crt_seed >> 16) & 0x7fffu);
}

static const mu_gi_record *record_of(mu_world_items *it, int32_t code)
{
    if (code < 0 || code > CODE_LIMIT || !it->has_table)
        return NULL;
    if (it->record_state[code] == 0) {
        mu_item item;
        if (mu_item_find(&it->item_table, (uint32_t)code, &item) == 0) {
            mu_gi_record *r = &it->records[code];
            r->present = 1;
            r->kind_a = item.attributes.kind_a;
            r->kind_b = item.attributes.kind_b;
            r->type = item.attributes.type;
            r->pc_room = item.attributes.pc_room;
            snprintf(it->record_names[code], sizeof it->record_names[code], "%s", item.name);
            r->name = it->record_names[code];
            it->record_state[code] = 1;
        } else {
            it->record_state[code] = 2;
        }
    }
    return it->record_state[code] == 1 ? &it->records[code] : NULL;
}

static const mu_gi_record *host_record(void *context, int32_t code)
{
    return record_of(context, code);
}

static float host_height(void *context, float x, float y)
{
    mu_world_items *it = context;
    const mu_world *m = it->map;
    return m ? mu_request_terrain_height(m->height, m->attributes, m->water_height, 6, x, y) : 0.0f;
}

static void host_light(void *context, float x, float y, float out[3])
{
    mu_world_items *it = context;
    if (!it->map) {
        out[0] = out[1] = out[2] = 1.0f;
        return;
    }
    mu_obj_terrain_light(it->map->light, 6, 1, x, y, out);   /* RequestTerrainLight 0x016cb08d (frame light) */
}

static int32_t host_rand(void *context)
{
    return crt_rand(context);
}

static float host_sin(void *context, float x)
{
    (void)context;
    return (float)sin((double)x);
}

static float host_sqrt(void *context, float x)
{
    (void)context;
    return (float)sqrt((double)x);
}

static void host_sound(void *context, int32_t id)
{
    mu_world_items *it = context;
    ++it->stats.sounds;
    if (it->play_sound)
        it->play_sound(it->sound_context, id);
}

/* 0x00cd1534 is runtime-patched (a jump into an unanalysed module). Its
 * leftover code tests the record's grade byte against 1, 3, 5, 6, 7, 8 (and
 * two more predicates); the demo answers with that grade test (inference). */
static int32_t host_socket_like(void *context, const mu_gi_item_data *item)
{
    const mu_gi_record *r = record_of(context, item->code);
    if (!r)
        return 0;
    return r->type == 1 || r->type == 3 || r->type == 5 || r->type == 6 || r->type == 7 || r->type == 8;
}

/* ---------------------------------------------------------------- the name builder's text (stand-ins) */

static const char *name_text(void *context, int32_t id)
{
    mu_world_items *it = context;
    (void)context;
    const char *standin = NULL;
    switch (id) {   /* English stand-ins of the plain-item suffixes when Lang.mpr's tables are absent */
    /* GlobalText 176..178 hold "+Skill", "+Option", "+Luck" with no leading space and the builder appends them
     * with strcat (NATIVE-FIDELITY-001): "Short Sword +9+Skill+Option+Luck" */
    case 0xb0: standin = "+Skill"; break;
    case 0xb1: standin = "+Option"; break;
    case 0xb2: standin = "+Luck"; break;
    case 0xb3: standin = "Skill"; break;
    default: {
        char *b = it->name_ring[it->name_next++ & 7];
        snprintf(b, sizeof it->name_ring[0], "[Text %d]", (int)id);
        standin = b;
        break;
    }
    }
    return mu_lang_text_or(((mu_world_items *)context)->lang, id, standin);   /* GlobalText (NATIVE-LANG-001, MU_LANG_DIR) */
}

static const char *name_prefix(void *context, const mu_gi_item_data *item)
{
    /* 0x009953ef()->0x009e051c: the set manager's 0x009e0551(code, +0x3b) (reconstructed/items/item_sets.c,
     * verified); "" without the set tables */
    mu_world_items *it = context;
    const mu_gi_record *r = record_of(it, item->code);
    return mu_gi_set_prefix(it->sets, item->code, item->ancient, r ? r->kind_b : 0);
}

static int32_t name_set_tier(void *context, int32_t code)
{
    /* PentagramOption 0x011447ac on 0x06fbae4c, record +0x24 (Lang.mpr, NATIVE-LANG-001 tables) */
    (void)context;
    int32_t tier = 0;
    if (!mu_lang_pentagram_tier(((mu_world_items *)context)->lang, code, &tier))
        tier = 0;
    return tier;
}

static const char *name_table(void *context, int32_t key)
{
    mu_world_items *it = context;
    char *buf = it->entry_name;
    (void)context;
    snprintf(buf, sizeof it->entry_name, "[Entry %d]", (int)key);
    return buf;
}

/* 0x00961620 on 0x06fbb138 is the skill table's lookup (entry +8: the name). */
static const char *name_skill(void *context, int32_t key)
{
    const mu_lang_skill *sk = mu_lang_skill_get(((mu_world_items *)context)->lang, key);
    return sk && sk->name ? sk->name : name_table(context, key);
}

/* 0x011427c7 on 0x06fbb664 is the Npcname table's name getter. */
static const char *name_npc(void *context, int32_t key)
{
    const char *n = mu_lang_npc_name(((mu_world_items *)context)->lang, key);
    return n ? n : name_table(context, key);
}

static const char *name_text_string(void *context, int32_t id)
{
    return name_text(context, id);   /* 0x011753c3: GlobalText as a std::string */
}

static int32_t name_level_key(void *context, int32_t level)
{
    (void)context;
    return level;
}

static void name_build(void *context, mu_gi_item *gi)
{
    mu_world_items *it = context;
    mu_gi_name_env env = {it, host_record, name_text, name_prefix, name_set_tier, name_skill, name_text_string,
                          name_level_key, name_npc, 1};
    mu_gi_name_sink sink;
    memset(&sink, 0, sizeof sink);
    mu_gi_name_build(gi, &env, &sink);
}

/* ---------------------------------------------------------------- open / close */

static int sets_has_record(void *context, int32_t code)
{
    return record_of(context, code) != NULL;
}

static int sets_legendary(void *context, int32_t type, int32_t codes[4])
{
    (void)context;
    return mu_lang_legendary(((mu_world_items *)context)->lang, type, codes);
}

/* the set manager's start-up load 0x009e02a8: ItemSetType.bmd, ItemSetOption.bmd (Data/Local, decoded by
 * mu_data), then 0x009de132/0x009debe4 with Lang.mpr's LegendaryItemSetType and CashItemSetOption when
 * MU_LANG_DIR holds them */
static void load_sets(mu_world_items *it)
{
    char path[2048];
    snprintf(path, sizeof path, "%s/Data/Local/itemsettype.bmd", it->game_root);
    int a = mu_data_load(path, NULL, &it->set_type) == 0 && it->set_type.result.status == 0;
    snprintf(path, sizeof path, "%s/Data/Local/itemsetoption.bmd", it->game_root);
    int b = mu_data_load(path, NULL, &it->set_option) == 0 && it->set_option.result.status == 0;
    if (!a || !b || it->set_type.size < it->set_type.result.records_offset + MU_GI_SET_CODES * MU_GI_SET_TYPE_BYTES ||
        it->set_option.size < it->set_option.result.records_offset + MU_GI_SET_OPTIONS * MU_GI_SET_OPTION_BYTES)
        return;
    const mu_lang *lang = it->lang;
    const mu_lang_cash_set *cash = NULL;
    const mu_lang_cash_item *items = NULL;
    size_t nsets = mu_lang_cash_sets(lang, &cash), nitems = mu_lang_cash_items(lang, &items);
    const char **n1 = calloc(nsets + 1, sizeof *n1), **n2 = calloc(nsets + 1, sizeof *n2);
    int32_t *triples = calloc(3 * nitems + 1, sizeof *triples);
    if (n1 && n2 && triples) {
        for (size_t i = 0; i < nsets; ++i) {
            n1[i] = cash[i].name;
            n2[i] = cash[i].name2;
        }
        for (size_t i = 0; i < nitems; ++i) {
            triples[3 * i] = items[i].group;
            triples[3 * i + 1] = items[i].index;
            triples[3 * i + 2] = items[i].set;
        }
        mu_gi_set_inputs in = {it->set_type.bytes + it->set_type.result.records_offset,
                               it->set_option.bytes + it->set_option.result.records_offset, it, sets_has_record,
                               lang ? sets_legendary : NULL, nsets, n1, n2, nitems, triples};
        it->sets = mu_gi_sets_build(&in);
        char text[96];
        snprintf(text, sizeof text, "item sets: %zu (cash sets %zu, legendary table %s)", mu_gi_sets_count(it->sets),
                 nsets, lang ? "yes" : "no");
        log_line(it, text);
    }
    free(n1);
    free(n2);
    free(triples);
}

int mu_world_items_open(mu_world_items *it, const char *root, mu_walk *walk, const mu_world_items_config *config,
                        char *error, size_t error_size)
{
    memset(it, 0, sizeof *it);
    if (config)
        it->config = *config;
    else
        mu_world_items_default_config(&it->config);
    it->walk = walk;
    it->lang = mu_lang_load_default();
    it->map = walk ? walk->map : NULL;
    snprintf(it->game_root, sizeof it->game_root, "%s", root ? root : "");
    it->records = calloc(CODE_LIMIT + 1, sizeof *it->records);
    it->record_state = calloc(CODE_LIMIT + 1, 1);
    it->record_names = calloc(CODE_LIMIT + 1, sizeof *it->record_names);
    if (!it->records || !it->record_state || !it->record_names) {
        snprintf(error, error_size, "out of memory");
        return 1;
    }
    char path[2048];
    snprintf(path, sizeof path, "%s/Data/Local/item.bmd", it->game_root);
    if (mu_data_load(path, NULL, &it->item_table) == 0 && it->item_table.result.status == 0)
        it->has_table = 1;
    else {
        snprintf(path, sizeof path, "%s/Data/Local/Item.bmd", it->game_root);
        if (mu_data_load(path, NULL, &it->item_table) == 0 && it->item_table.result.status == 0)
            it->has_table = 1;
    }
    if (!it->has_table) {
        snprintf(error, error_size, "Data/Local/item.bmd could not be loaded");
        return 1;
    }
    load_sets(it);
    it->crt_seed = it->config.seed;
    for (int i = 0; i < 100; ++i)   /* WinMain 0x0120e96b: table[i] = rand() % 360 after srand(time(NULL)) */
        it->random_table[i] = crt_rand(it) % 360;
    it->host.context = it;
    it->host.record = host_record;
    it->host.terrain_height = host_height;
    it->host.terrain_light = host_light;
    it->host.rand = host_rand;
    it->host.sin = host_sin;
    it->host.sqrt = host_sqrt;
    it->host.play_sound = host_sound;
    it->host.socket_like = host_socket_like;
    it->host.world = walk ? walk->world : 0;
    it->view = 1;               /* constructor 0x00afaff8: +0x5c = 1 */
    it->selected = -1;
    it->pickup_target = -1;
    if (mu_ui_font_open(&it->font, it->config.font_face ? it->config.font_face : "Arial",
                        it->config.font_height > 0 ? it->config.font_height : 12, 400) == 0)
        it->has_font = 1;
    char text[112];
    snprintf(text, sizeof text, "item table: %zu records, demo drops %d", mu_item_count(&it->item_table),
             0);
    log_line(it, text);
    return 0;
}

void mu_world_items_close(mu_world_items *it)
{
    if(it->session)mu_session_items_bind(it->session,NULL,NULL);
    mu_lang_free(it->lang);
    mu_gi_sets_free(it->sets);
    mu_data_free(&it->set_type);
    mu_data_free(&it->set_option);
    if (it->mannequin) {
        mu_character_free(it->mannequin);
        free(it->mannequin);
    }
    for (int32_t i = 0; i < it->model_count; ++i) {
        mu_world_item_model *m = &it->models[i];
        if (m->loaded) {
            mu_textures_free(&m->textures);
            mu_model_free(&m->model);
            mu_bmd_free(&m->bmd);
        }
    }
    if (it->has_table)
        mu_data_free(&it->item_table);
    if (it->has_font)
        mu_ui_font_close(&it->font);
    free(it->records);
    free(it->record_state);
    free(it->record_names);
    memset(it, 0, sizeof *it);
}

/* ---------------------------------------------------------------- models */

static int is_armour(int32_t type)
{
    return type >= 0x18e6 && type < 0x22e6;   /* RenderItems poses the Player model for these (0x017e9520) */
}

static mu_character *mannequin(mu_world_items *it)
{
    if (it->mannequin || it->mannequin_failed)
        return it->mannequin;
    char path[2048], error[512];
    snprintf(path, sizeof path, "%s/Data/Player/Player.bmd", it->game_root);
    mu_model_params p;
    mu_model_default_params(&p);
    p.world = it->walk ? it->walk->world : 0;
    it->mannequin = calloc(1, sizeof *it->mannequin);
    if (!it->mannequin || mu_character_init(it->mannequin, path, &p, error, sizeof error)) {
        free(it->mannequin);
        it->mannequin = NULL;
        it->mannequin_failed = 1;
        log_line(it, "Player.bmd missing: armour parts are not drawn");
    }
    return it->mannequin;
}

static mu_world_item_model *model_for(mu_world_items *it, int32_t type, int32_t *slot)
{
    for (int32_t i = 0; i < it->model_count; ++i)
        if (it->models[i].type == type) {
            *slot = i;
            return it->models[i].loaded ? &it->models[i] : NULL;
        }
    if (it->model_count >= MU_WORLD_ITEM_MODELS)
        return NULL;
    mu_world_item_model *m = &it->models[it->model_count];
    *slot = it->model_count++;
    memset(m, 0, sizeof *m);
    m->type = type;
    mu_item item;
    char path[2048], message[512], directory[2048], special[256];
    if (mu_item_model(&it->item_table, type, &item) == 1) {
        snprintf(path, sizeof path, "%s/%s%s", it->game_root, item.folder, item.file);
    } else if (mu_gi_special_model_file(type, special, sizeof special)) {
        /* models outside Item.bmd: the item-model loader 0x0183220e's AccessModel calls (NATIVE-FIDELITY-001) */
        snprintf(path, sizeof path, "%s/%s", it->game_root, special);
    } else {
        m->failed = 1;
        snprintf(message, sizeof message, "model 0x%x: no Item.bmd record and no loader entry", type);
        log_line(it, message);
        return NULL;
    }
    for (char *p = path; *p; ++p)
        if (*p == '\\')
            *p = '/';
    if (mu_bmd_load_file(path, &m->bmd, message, sizeof message) != MU_BMD_OK) {
        m->failed = 1;
        char text[112];
        snprintf(text, sizeof text, "model 0x%x missing (%s%s)", type, item.folder, item.file);
        log_line(it, text);
        return NULL;
    }
    mu_model_params p;
    mu_model_default_params(&p);
    p.world = it->walk ? it->walk->world : 0;
    if (mu_model_init(&m->model, &m->bmd, &p, message, sizeof message) != MU_MODEL_OK) {
        mu_bmd_free(&m->bmd);
        m->failed = 1;
        return NULL;
    }
    if (is_armour(type)) {   /* a body part: skinned against the Player skeleton's shared bones */
        mu_character *man = mannequin(it);
        if (!man) {
            mu_model_free(&m->model);
            mu_bmd_free(&m->bmd);
            m->failed = 1;
            return NULL;
        }
        mu_model_relocate(&m->model, &m->bmd);
        mu_model_share(&m->model, man->shared_bones, man->shared_root, man->shared_quaternions);
    }
    mu_path_directory(path, directory, sizeof directory);
    mu_textures_load(&m->textures, &m->bmd, directory);
    if (m->textures.missing && is_armour(type)) {
        /* viewer choice: armour models sit in Data/Item, their bitmaps in Data/Player (the classic loader's
         * OpenTexture(model, "Player\\")); the texture folder rule of this client is not traced */
        char player[2048], effect[2048];
        snprintf(effect, sizeof effect, "%s/Data/Effect", it->game_root);
        snprintf(player, sizeof player, "%s/Data/Player", it->game_root);
        mu_textures_free(&m->textures);
        mu_textures_load_with_effects(&m->textures, &m->bmd, player, effect);
    }
    m->loaded = 1;
    return m;
}

/* Animation 0x012b5064 on the pose model at the call's position, then the render model's transform: for
 * armour the Player skeleton (action and frames of the object, the group's +0x90 offset) and the part
 * skinned against it with the part light arguments (0.4, 0.8, 0.2) as the character render does; for
 * other items the item model itself. */
static int pose_item(mu_world_items *it, mu_world_item_model *m, const mu_gi_object *o, const float position[3],
                     float height)
{
    if (is_armour(o->type)) {
        mu_character *man = it->mannequin;
        if (!man)
            return 1;
        for (int q = 0; q < 3; ++q) {
            man->params.position[q] = position[q];
            man->params.angles[q] = o->angle[q];
        }
        man->params.head[0] = o->head_angle[0];
        man->params.head[1] = o->head_angle[1];
        man->params.scale = o->scale;
        mu_model_params pp = man->player.params;
        pp.height = height;
        mu_model_apply_params(&man->player, &pp);
        mu_character_set_state(man, o->action, o->frame, o->prior_frame, o->prior_action);
        if (mu_character_update(man) != MU_MODEL_OK)
            return 1;
        mu_model_params p = m->model.params;
        p.body_scale = o->scale;
        for (int q = 0; q < 3; ++q) {
            p.origin[q] = position[q];
            p.color[q] = 1.0f;
            p.angles[q] = 0.0f;
        }
        p.head_angles[0] = p.head_angles[1] = 0.0f;
        p.transform_translate = 1;
        p.vertex_scale = 0.0f;
        p.light_ambient = 0.4f;
        p.light_scale = 0.8f;
        p.light_minimum = 0.2f;
        p.height = 0.0f;
        mu_model_apply_params(&m->model, &p);
        return mu_model_transform_all(&m->model) != MU_MODEL_OK;
    }
    mu_model_params p = m->model.params;
    for (int q = 0; q < 3; ++q) {
        p.origin[q] = position[q];
        p.angles[q] = o->angle[q];
        p.color[q] = 1.0f;
    }
    p.body_scale = o->scale;
    p.height = height;
    mu_model_apply_params(&m->model, &p);
    mu_model_set_state(&m->model, o->action, o->frame, o->prior_frame, o->prior_action);
    if (mu_model_pose(&m->model) != MU_MODEL_OK || mu_model_transform_all(&m->model) != MU_MODEL_OK)
        return 1;
    return 0;
}

/* ---------------------------------------------------------------- drops */

int32_t mu_world_items_drop(mu_world_items *it, int32_t code, int32_t level_byte, uint8_t excellent, uint8_t ancient,
                            int32_t zen, float x, float y, int32_t drop_flag)
{
    return mu_items_demo_drop(it->fixture_items,code,level_byte,excellent,ancient,zen,x,y,drop_flag);
}

static int32_t receive_entry(mu_world_items *it,int32_t slot,const uint8_t b[15],float x,float y,int32_t drop_flag)
{
    if(slot<0 || slot>=MU_GI_ITEMS)return -1;
    int32_t code=mu_gi_item_code(b);
    /* ReceiveCreateItemViewport: reset, key, the label view byte, then CreateItem */
    mu_gi_item *gi = &it->pool[slot];
    memset(gi, 0, sizeof *gi);
    gi->key = (uint16_t)slot;
    gi->label_view = (uint8_t)it->view;
    mu_gi_create_hooks hooks;
    mu_gi_default_hooks(&hooks, &it->host);   /* reset, SetLive, ItemObjectAttribute, ItemAngle */
    float position[3] = {x, y, 0.0f};
    it->host.world = it->walk ? it->walk->world : 0;
    it->host.world_time = it->map ? it->map->time : 0.0f;
    int32_t status = mu_gi_create(gi, b, position, drop_flag, &it->host, &hooks);
    if (status != MU_GI_CREATE_OK) {
        ++it->stats.no_record;
        memset(gi, 0, sizeof *gi);
        return -1;
    }
    name_build(it, gi);                           /* the last call of CreateItem 0x016db59b */
    ++it->stats.creates;
    if (drop_flag)
        ++it->stats.drops;
    char text[112];
    snprintf(text, sizeof text, "step %d: item %d code 0x%x '%s' class %d at %.0f,%.0f", it->step, slot, code,
             gi->name, gi->name_class, x, y);
    log_line(it, text);
    return slot;
}

static void present_entry(void *ctx,int32_t slot,const uint8_t entry[19])
{
    mu_world_items *it=ctx;
    unsigned key=((unsigned)entry[0]<<8)|entry[1];
    receive_entry(it,slot,entry+4,((float)entry[2]+0.5f)*100,((float)entry[3]+0.5f)*100,(int32_t)(key>>15));
}
void mu_world_items_bind(mu_world_items *it,mu_session *s,void *fixture_items)
{
    it->session=s; it->fixture_items=fixture_items;
    /* Pointer refers to session storage. Replicated fields are changed only by handlers;
     * MoveItems/render/selection write object motion/view fields. */
    it->pool=(mu_gi_item *)mu_session_items(s).pool;
    mu_session_items_bind(s,present_entry,it);
}

static void move_angle(void *context, mu_gi_object *o)
{
    mu_world_items *it = context;
    mu_gi_angle_env env;
    memset(&env, 0, sizeof env);
    const mu_gi_record *r = record_of(it, o->type - MU_GI_MODEL_ITEM);
    if (r)
        env.record = *r;
    mu_gi_item_angle(o, &env);
    ++it->stats.lands;
}

static void move_particle(void *context, int32_t type, const float position[3], const float angle[3],
                          const float light[3], int32_t subtype, float scale)
{
    mu_world_items *it = context;
    ++it->stats.sparkle_particles;
    if (it->particles)
        mu_world_particles_create(it->particles, type, position, angle, light, subtype, scale);
}

static void request_pickup(mu_world_items *it, int32_t slot)
{
    if (it->pickup_wait)
        return;
    if (!it->session) return;
    mu_intent in={0}; in.kind=MU_INTENT_ITEM_PICKUP; in.u.item_pickup.slot=slot;
    mu_submit r=mu_session_submit(it->session,&in);
    if (r.status==MU_SUBMIT_REFUSED) return;
    /* Explicit synthetic server removal; the encrypted request is journaled unsent.
     * There is no recorded pickup answer route in this milestone. */
    mu_items_demo_remove(it->fixture_items,slot);
    it->pickup_wait = 1;
    ++it->stats.picks_requested;
    char text[112];
    snprintf(text, sizeof text, "step %d: pick-up request for item %d", it->step, slot);
    log_line(it, text);
}

void mu_world_items_step(mu_world_items *it)
{
    ++it->step;
    it->host.world = it->walk ? it->walk->world : 0;
    it->host.world_time = it->map ? it->map->time : 0.0f;
    if (!it->pool) return;
    uint32_t deleted=mu_session_items(it->session).deletes;
    uint32_t removed=deleted-it->deletes_seen; it->deletes_seen=deleted;
    if (it->pickup_wait && removed && mu_session_items(it->session).pending < 0) {
        it->pickup_wait=0; ++it->stats.picks_done; --removed;
    }
    it->stats.despawns+=removed;
    /* MoveItems 0x017ea1aa */
    mu_gi_move_hooks hooks = {it, move_angle, move_particle};
    for (int32_t i = 0; i < MU_GI_ITEMS; ++i) {
        mu_gi_object *o = &it->pool[i].object;
        if (!o->live)
            continue;
        int32_t before = o->sparkle;
        mu_gi_move_item(o, &it->host, &hooks);
        if (before % 48 == 0)
            ++it->stats.sparkles;

    }
    /* MoveHero's pick-up mode (0x016983b2): within 1.5 tiles of the target, or forced by the space bar */
    if (it->pickup_target >= 0 && it->walk) {
        mu_gi_item *gi = &it->pool[it->pickup_target];
        if (!gi->object.live) {
            it->pickup_target = -1;
        } else {
            const mu_hero *h = &it->walk->hero;
            int32_t tx = (int32_t)(gi->object.position[0] / 100.0f), ty = (int32_t)(gi->object.position[1] / 100.0f);
            if (it->pickup_force || mu_in_range(h->tile[0], h->tile[1], tx, ty, 1.5f)) {
                request_pickup(it, it->pickup_target);
                it->pickup_target = -1;
                it->pickup_force = 0;
            }
        }
    }
}

/* ---------------------------------------------------------------- selection and input */

/* Viewer choice: the ray against the item's bounding box (+-30, scaled), axis aligned. */
static int ray_hits(const mu_world_items *it, int32_t i)
{
    const mu_client_view *v = &it->walk->frame.view;
    const mu_gi_object *o = &it->pool[i].object;
    float org[3], dir[3];
    for (int k = 0; k < 3; ++k) {
        org[k] = v->mouse_position[k];
        dir[k] = v->mouse_target[k] - v->mouse_position[k];
    }
    float t0 = 0.0f, t1 = 1.0f;
    for (int k = 0; k < 3; ++k) {
        float s = o->scale > 0.0f ? o->scale : 1.0f;
        float lo = o->position[k] + o->bbox_min[k] * s, hi = o->position[k] + o->bbox_max[k] * s;
        if (fabsf(dir[k]) < 1e-6f) {
            if (org[k] < lo || org[k] > hi)
                return 0;
            continue;
        }
        float a = (lo - org[k]) / dir[k], b = (hi - org[k]) / dir[k];
        if (a > b) {
            float t = a;
            a = b;
            b = t;
        }
        if (a > t0)
            t0 = a;
        if (b < t1)
            t1 = b;
        if (t0 > t1)
            return 0;
    }
    return 1;
}

static int32_t select_hit(void *context, int32_t index)
{
    return ray_hits(context, index);
}

int32_t mu_world_items_select(mu_world_items *it, int alt, int no_character)
{
    if (!it->walk)
        return -1;
    int32_t before = it->selected;
    if (alt || no_character)
        it->selected = mu_gi_select(it->pool, MU_GI_ITEMS, select_hit, it);
    else
        it->selected = -1;
    if (it->selected >= 0)
        ++it->stats.hover_frames;
    (void)before;
    return it->selected;
}

int mu_world_items_pre_step(mu_world_items *it)
{
    if (!it->walk)
        return 0;
    mu_frame_world *f = &it->walk->frame;
    if (f->mouse.left_push && it->selected >= 0 && it->pool[it->selected].object.live) {
        /* MoveHero: a click on the selected item: walk to its tile in pick-up mode (0x01cf1148 = 6) */
        int32_t slot = it->selected;
        const mu_gi_object *o = &it->pool[slot].object;
        int32_t tx = (int32_t)(o->position[0] / 100.0f), ty = (int32_t)(o->position[1] / 100.0f);
        f->mouse.left_push = 0;
        f->mouse.left = 0;
        it->pickup_target = slot;
        it->pickup_force = 0;
        const mu_hero *h = &it->walk->hero;
        if (!mu_in_range(h->tile[0], h->tile[1], tx, ty, 1.5f))
            mu_walk_path_to(it->walk, tx, ty);
        char text[112];
        snprintf(text, sizeof text, "step %d: walk to item %d at %d,%d", it->step, slot, tx, ty);
        log_line(it, text);
        return 1;
    }
    return 0;
}

void mu_world_items_alt(mu_world_items *it)
{
    it->view = !it->view;           /* 0x00efc7d3: setItemView(!getItemView()) on the Alt press */
    ++it->stats.alt_toggles;
}

int mu_world_items_space(mu_world_items *it)
{
    /* 0x00efd9ab: the nearest live, visible item within 300 units of the hero (3D distance) */
    if (!it->walk)
        return 0;
    const float *p = it->walk->hero.position;
    for (int32_t i = 0; i < MU_GI_ITEMS; ++i) {
        const mu_gi_object *o = &it->pool[i].object;
        if (!o->live || !o->visible)
            continue;
        float d[3] = {o->position[0] - p[0], o->position[1] - p[1], o->position[2] - p[2]};
        float len = sqrtf(d[0] * d[0] + d[1] * d[1] + d[2] * d[2]);
        if (len < 300.0f) {
            it->pickup_target = i;
            it->pickup_force = 1;   /* 0x0b43656d = 1: MoveHero's range test is skipped */
            ++it->stats.space_picks;
            return 1;
        }
    }
    return 0;
}

/* ---------------------------------------------------------------- drawing */

static void project_render(void *context, const float world[3], int32_t *x, int32_t *y)
{
    mu_world_items *it = context;
    mu_view_projection(&it->walk->frame.view, world, x, y);
}

int32_t mu_world_items_draw(mu_world_items *it, mu_world_item_draw_fn draw, void *context)
{
    int32_t drawn = 0;
    if (!it->walk)
        return 0;
    it->host.world_time = it->map ? it->map->time : 0.0f;
    for (int32_t i = 0; i < MU_GI_ITEMS; ++i) {
        mu_gi_item *gi = &it->pool[i];
        mu_gi_object *o = &gi->object;
        if (!o->live)
            continue;
        /* TestFrustrum 0x016ccc14(position, 400) against the frame's CreateFrustrum planes */
        int visible = it->frustum ? mu_gi_test_frustum(it->frustum->normal, it->frustum->d, o->position, 400.0f) : 1;
        int32_t slot = -1;
        mu_world_item_model *m = visible ? model_for(it, o->type, &slot) : NULL;
        mu_gi_render_env env;
        memset(&env, 0, sizeof env);
        env.visible = visible;
        env.pose_model_exists = 1;
        env.render_model_exists = 1;
        env.random_table = it->random_table;
        env.project = project_render;
        env.context = it;
        mu_gi_render_plan_t plan;
        mu_gi_render_plan(gi, i, &it->host, &env, &plan);
        o->visible = (uint8_t)plan.visible;
        if (!visible)
            continue;
        o->screen_x = plan.screen_x;
        o->screen_y = plan.screen_y;
        if (!m) {
            ++it->stats.model_missing;
            continue;
        }
        for (int32_t k = 0; k < plan.call_count; ++k) {
            const mu_gi_render_call *c = &plan.calls[k];
            if (pose_item(it, m, o, c->position, plan.pose_head_offset))
                continue;
            mu_world_item_draw d;
            d.model = &m->model;
            d.textures = &m->textures;
            d.slot = slot;
            d.type = c->type;
            d.level = (c->item_level >> 3) & 15;
            d.option1 = c->option;
            d.ext = c->ext;
            for (int q = 0; q < 3; ++q)
                d.light[q] = c->light[q];
            d.alpha = c->alpha;
            const mu_gi_record *r = record_of(it, c->type - MU_GI_MODEL_ITEM);
            d.has_record = r != NULL;
            d.kind_a = r ? r->kind_a : 0;
            d.kind_b = r ? r->kind_b : 0;
            d.item_kind = r ? r->type : 0;
            draw(context, &d);
            ++drawn;
            ++it->stats.render_calls;
            if (o->type == 0x26f5)
                ++it->stats.zen_coins;
        }
        ++it->stats.models_drawn;
    }
    return drawn;
}

static void project_label(void *context, const float world[3], float *x, float *y)
{
    mu_world_items *it = context;
    mu_view_projection_float(&it->walk->frame.view, world, x, y);
}

static void hex_rgb(const char *hex, float rgb[3])
{
    unsigned v = (unsigned)strtoul(hex + 1, NULL, 16);
    rgb[0] = (float)((v >> 16) & 0xff) / 255.0f;
    rgb[1] = (float)((v >> 8) & 0xff) / 255.0f;
    rgb[2] = (float)(v & 0xff) / 255.0f;
}

int32_t mu_world_items_labels(mu_world_items *it, mu_world_item_label *labels, int32_t max)
{
    int32_t n = 0;
    if (!it->walk || !it->view)
        return 0;   /* setItemView(false) hides the item container */
    const mu_frame_world *f = &it->walk->frame;
    mu_gi_label_env env = {project_label, it, it->selected, f->mouse.x, f->mouse.y, f->mouse.scale_x,
                           f->mouse.scale_y};
    for (int32_t i = 0; i < MU_GI_ITEMS && n < max; ++i) {
        const mu_gi_item *gi = &it->pool[i];
        if (!gi->object.live)
            continue;
        mu_world_item_label *l = &labels[n];
        memset(l, 0, sizeof *l);
        l->index = i;
        snprintf(l->text, sizeof l->text, "%s", gi->name);
        l->color = mu_gi_label_color(gi->name_class);
        hex_rgb(l->color, l->rgb);
        mu_gi_label_anchor(gi, i, &env, &l->anchor[0], &l->anchor[1]);
        int32_t w = (int32_t)strlen(l->text) * 7, h = 12;
        if (it->has_font) {
            mu_ui_gdi gdi = mu_ui_font_gdi(&it->font);
            gdi.extent(gdi.user, l->text, (int)strlen(l->text), &w, &h);
        }
        l->text_width = w;
        l->text_height = h;
        mu_gi_label_layout((float)w, (float)h, &l->box);
        l->hovered = i == it->selected;
        ++n;
    }
    it->stats.labels += (uint32_t)n;
    return n;
}

int mu_world_items_label_bitmap(mu_world_items *it, const mu_world_item_label *l, uint8_t *rgba, int32_t width,
                                int32_t height)
{
    /* the shared glyph path of the overhead labels (core/mu_label, NATIVE-NAMES-001) */
    return it->has_font ? mu_label_plain(&it->font, l->text, rgba, width, height) : 1;
}

void mu_world_items_label_blit(mu_world_items *it, const mu_world_item_label *l, uint8_t *frame, int32_t width,
                               int32_t height)
{
    int32_t bx = (int32_t)(l->anchor[0] + l->box.bg_x), by = (int32_t)(l->anchor[1] + l->box.bg_y);
    int32_t bw = (int32_t)l->box.bg_w, bh = (int32_t)l->box.bg_h;
    for (int32_t y = by; y < by + bh; ++y)       /* the background: black at 50% (viewer choice) */
        for (int32_t x = bx; x < bx + bw; ++x) {
            if (x < 0 || y < 0 || x >= width || y >= height)
                continue;
            uint8_t *p = frame + ((size_t)y * (size_t)width + (size_t)x) * 4;
            for (int k = 0; k < 3; ++k)
                p[k] = (uint8_t)(p[k] / 2);
        }
    int32_t tw = l->text_width, th = l->text_height;
    if (tw <= 0 || th <= 0 || tw > 1024 || th > 256)
        return;
    uint8_t *glyphs = malloc((size_t)tw * (size_t)th * 4);
    if (!glyphs || mu_world_items_label_bitmap(it, l, glyphs, tw, th)) {
        free(glyphs);
        return;
    }
    int32_t tx = (int32_t)(l->anchor[0] + l->box.text_x + 3.0f), ty = (int32_t)(l->anchor[1] + l->box.text_y + 2.0f);
    for (int32_t y = 0; y < th; ++y)
        for (int32_t x = 0; x < tw; ++x) {
            int32_t X = tx + x, Y = ty + y;
            if (X < 0 || Y < 0 || X >= width || Y >= height)
                continue;
            uint8_t a = glyphs[((size_t)y * (size_t)tw + (size_t)x) * 4 + 3];
            if (!a)
                continue;
            uint8_t *p = frame + ((size_t)Y * (size_t)width + (size_t)X) * 4;
            for (int k = 0; k < 3; ++k) {
                float c = l->rgb[k] * 255.0f;
                p[k] = (uint8_t)(((float)p[k] * (float)(255 - a) + c * (float)a) / 255.0f);
            }
        }
    free(glyphs);
}

/* ---------------------------------------------------------------- script and reports */

int mu_world_items_script_parse(mu_world_item_script *s, const char *text)
{
    memset(s, 0, sizeof *s);
    const char *p = text;
    while (p && *p) {
        while (*p == ' ' || *p == ';')
            ++p;
        if (!*p)
            break;
        if (s->count >= MU_WORLD_ITEM_SCRIPT)
            return 1;
        mu_world_item_script_entry *e = &s->items[s->count];
        char verb[16] = {0};
        int consumed = 0;
        if (sscanf(p, "%d:%15[a-z]%n", &e->frame, verb, &consumed) < 2)
            return 1;
        snprintf(e->verb, sizeof e->verb, "%s", verb);
        p += consumed;
        e->a = e->b = -1;
        if (*p == ':') {
            ++p;
            char *end;
            e->a = (int32_t)strtol(p, &end, 0);
            p = end;
            if (*p == ':') {
                ++p;
                e->b = (int32_t)strtol(p, &end, 0);
                p = end;
                if (*p == ':') {
                    ++p;
                    e->x = strtof(p, &end);
                    p = end;
                    if (*p == ',') {
                        ++p;
                        e->y = strtof(p, &end);
                        p = end;
                        e->has_xy = 1;
                        if (*p == ':') {
                            ++p;
                            e->ancient = (int32_t)strtol(p, &end, 0);
                            p = end;
                        }
                    }
                }
            }
        }
        ++s->count;
        while (*p && *p != ' ' && *p != ';')
            ++p;
    }
    return 0;
}

int32_t mu_world_items_live(const mu_world_items *it)
{
    int32_t n = 0;
    for (int32_t i = 0; i < MU_GI_ITEMS; ++i)
        n += it->pool[i].object.live != 0;
    return n;
}

void mu_world_items_report_frame(const mu_world_items *it, FILE *out, int32_t frame)
{
    fprintf(out, "{\"items_frame\": %d, \"live\": %d, \"selected\": %d, \"view\": %d, \"pickup\": %d, \"list\": [", frame,
            mu_world_items_live(it), it->selected, it->view, it->pickup_target);
    int first = 1;
    for (int32_t i = 0; i < MU_GI_ITEMS; ++i) {
        const mu_gi_item *gi = &it->pool[i];
        const mu_gi_object *o = &gi->object;
        if (!o->live)
            continue;
        fprintf(out, "%s{\"slot\": %d, \"type\": %d, \"name\": \"", first ? "" : ", ", i, o->type);
        for (const char *c = gi->name; *c; ++c)
            fputc(*c == '"' || *c == '\\' || (unsigned char)*c < 32 ? '?' : *c, out);
        fprintf(out, "\", \"class\": %d, \"z\": %.2f, \"gravity\": %.1f, \"angle\": [%.1f, %.1f, %.1f], \"scale\": %.2f}",
                gi->name_class, o->position[2], o->gravity, o->angle[0], o->angle[1], o->angle[2], o->scale);
        first = 0;
    }
    fprintf(out, "]}\n");
}

void mu_world_items_report_summary(const mu_world_items *it, FILE *out)
{
    int effect_textures = 0;
    for (int32_t i = 0; i < it->model_count; ++i) {
        const mu_textures *t = &it->models[i].textures;
        for (int k = 0; it->models[i].loaded && t->slots && k < MU_TEXTURE_SPECIAL_COUNT &&
                        t->model_count + k < t->count; ++k)
            if (t->slots[t->model_count + k])
                ++effect_textures;
    }
    const mu_world_items_stats *s = &it->stats;
    fprintf(out, "{\"items\": true, \"live\": %d, \"drops\": %u, \"creates\": %u, \"no_record\": %u, \"lands\": %u,"
            " \"sparkles\": %u, \"sparkle_particles\": %u, \"picks_requested\": %u, \"picks_done\": %u,"
            " \"space_picks\": %u, \"despawns\": %u, \"hover_frames\": %u, \"labels\": %u, \"models_drawn\": %u,"
            " \"model_missing\": %u, \"render_calls\": %u, \"zen_coins\": %u, \"sounds\": %u, \"alt_toggles\": %u,"
            " \"kills_seen\": %u, \"demo_table\": %d, \"view\": %d, \"effect_textures_loaded\": %d, \"log\": [",
            mu_world_items_live(it), s->drops, s->creates, s->no_record, s->lands, s->sparkles, s->sparkle_particles,
            s->picks_requested, s->picks_done, s->space_picks, s->despawns, s->hover_frames, s->labels,
            s->models_drawn, s->model_missing, s->render_calls, s->zen_coins, s->sounds, s->alt_toggles,
            s->kills_seen, 0, it->view, effect_textures);
    for (int32_t i = 0; i < it->log_count; ++i) {
        fprintf(out, "%s\"", i ? ", " : "");
        for (const char *c = it->log[i]; *c; ++c)
            fputc(*c == '"' || *c == '\\' || (unsigned char)*c < 32 ? '?' : *c, out);
        fputc('"', out);
    }
    fprintf(out, "]}\n");
}
