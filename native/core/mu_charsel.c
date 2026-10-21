/* Native character-select scene (NATIVE-CHARSEL-001). See mu_charsel.h. */
#include "mu_charsel.h"

#include <ctype.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../../reconstructed/movement/client_movement.h"

/* Marker 1 (object type 14 of EncTerrain94.obj) as CreateObject stored it in the running client: live
 * single-run read of the object list (NATIVE-OBJECTS-001, docs/research/client-objects.md section 6). The
 * earlier window-capture fit was (13617, 12339, 169.5). */
const float mu_charsel_default_marker1[3] = {13629.30078125f, 12338.5654296875f, 164.49984741210938f};

static uint8_t *record(mu_charsel_session *s, int32_t index)
{
    return s->records + (size_t)index * MU_CHARSEL_RECORD;
}

static uint8_t *lookup(void *context, int32_t index)
{
    mu_charsel_session *s = context;
    if (index < 0 || index >= MU_CHARSEL_CHARACTERS)
        return NULL;
    return record(s, index);
}

static float getf(const uint8_t *p, uint32_t offset)
{
    float v;
    memcpy(&v, p + offset, sizeof v);
    return v;
}

static void putf(uint8_t *p, uint32_t offset, float v)
{
    memcpy(p + offset, &v, sizeof v);
}

static float fbits(uint32_t w)
{
    float v;
    memcpy(&v, &w, sizeof v);
    return v;
}

/* ---- list ---- */

void mu_charsel_list_default(mu_charsel_list *list)
{
    static const struct { uint8_t cls; uint16_t level; const char *name; } d[5] = {
        {0x00, 400, "Wizard"}, {0x01, 380, "Knight"}, {0x02, 350, "Archer"}, {0x03, 300, "Gladiator"},
        {0x04, 250, "Lord"}};
    memset(list, 0, sizeof *list);
    list->count = 5;
    for (int i = 0; i < 5; ++i) {
        list->entries[i].slot = i;
        list->entries[i].class_byte = d[i].cls;
        list->entries[i].level = d[i].level;
        snprintf(list->entries[i].name, sizeof list->entries[i].name, "%s", d[i].name);
    }
}

static int item_index(const char *key)
{
    static const char *names[MU_CHARACTER_ITEMS] = {"head", "helm", "armor", "pants", "gloves", "boots",
                                                    "weapon0", "weapon1", "wing"};
    for (int i = 0; i < MU_CHARACTER_ITEMS; ++i)
        if (!strcmp(key, names[i]))
            return i;
    return -1;
}

int mu_charsel_list_parse(const char *text, const char *root, mu_charsel_list *list, char *error, size_t error_size)
{
    memset(list, 0, sizeof *list);
    int line_number = 0;
    const char *p = text;
    while (*p) {
        const char *end = strchr(p, '\n');
        size_t n = end ? (size_t)(end - p) : strlen(p);
        char line[4096];
        if (n >= sizeof line)
            n = sizeof line - 1;
        memcpy(line, p, n);
        line[n] = 0;
        p += n + (end ? 1 : 0);
        ++line_number;
        char *hash = strchr(line, '#');
        if (hash)
            *hash = 0;
        char *tok[16];
        int count = 0;
        for (char *t = strtok(line, " \t\r"); t && count < 16; t = strtok(NULL, " \t\r"))
            tok[count++] = t;
        if (!count)
            continue;
        if (count < 4) {
            snprintf(error, error_size, "line %d: expected slot class level name", line_number);
            return 1;
        }
        if (list->count >= MU_CHARSEL_MAX_ENTRIES) {
            snprintf(error, error_size, "line %d: at most %d characters", line_number, MU_CHARSEL_MAX_ENTRIES);
            return 1;
        }
        mu_charsel_entry *e = &list->entries[list->count];
        char *stop;
        long slot = strtol(tok[0], &stop, 0);
        if (*stop || slot < 0 || slot >= MU_CHARSEL_LIST) {
            snprintf(error, error_size, "line %d: slot must be 0..9", line_number);
            return 1;
        }
        long cls = strtol(tok[1], &stop, 0);
        if (*stop || cls < 0 || cls > 255) {
            snprintf(error, error_size, "line %d: bad class byte", line_number);
            return 1;
        }
        long level = strtol(tok[2], &stop, 0);
        if (*stop || level < 0 || level > 65535) {
            snprintf(error, error_size, "line %d: bad level", line_number);
            return 1;
        }
        for (int i = 0; i < list->count; ++i)
            if (list->entries[i].slot == slot) {
                snprintf(error, error_size, "line %d: slot %ld used twice", line_number, slot);
                return 1;
            }
        e->slot = (int32_t)slot;
        e->class_byte = (uint8_t)cls;
        e->level = (uint16_t)level;
        snprintf(e->name, sizeof e->name, "%.10s", tok[3]);
        for (int i = 4; i < count; ++i) {
            char *eq = strchr(tok[i], '=');
            int k = -1;
            if (eq) {
                *eq = 0;
                k = item_index(tok[i]);
            }
            if (k < 1) {
                snprintf(error, error_size, "line %d: bad item '%s'", line_number, tok[i]);
                return 1;
            }
            if (eq[1] == '/')
                snprintf(e->items[k], MU_CHARSEL_PATH, "%s", eq + 1);
            else
                snprintf(e->items[k], MU_CHARSEL_PATH, "%s/Data/%s", root, eq + 1);
        }
        ++list->count;
    }
    if (!list->count) {
        snprintf(error, error_size, "empty character list");
        return 1;
    }
    return 0;
}

/* ---- session ---- */

int32_t mu_charsel_entry_of(const mu_charsel_session *s, int32_t slot)
{
    for (int32_t i = 0; i < s->list.count; ++i)
        if (s->list.entries[i].slot == slot)
            return i;
    return -1;
}

static int load_entry(mu_charsel_session *s, const char *root, int32_t i)
{
    const mu_charsel_entry *e = &s->list.entries[i];
    mu_character *ch = &s->characters[i];
    char player[4096];
    snprintf(player, sizeof player, "%s/Data/Player/Player.bmd", root);
    mu_model_params params;
    mu_model_scene_params(&params);   /* light override 1 (NATIVE-LIGHT-001) */
    params.world = MU_CHARSEL_WORLD;
    params.scene_state = MU_CHARSEL_SCENE;   /* the animation tick's scene-5 rule */
    if (mu_character_init(ch, player, &params, s->error, sizeof s->error))
        return 1;
    s->character_loaded[i] = 1;
    mu_character_apply_player_speeds(ch);
    for (int k = 1; k < MU_CHARACTER_ITEMS; ++k) {
        char path[4096];
        path[0] = 0;
        if (e->items[k][0])
            snprintf(path, sizeof path, "%s", e->items[k]);
        else if (k < MU_CHARACTER_PART_SLOTS && !mu_character_part_path(root, k, e->class_byte, path, sizeof path))
            path[0] = 0;
        if (!path[0])
            continue;
        FILE *f = fopen(path, "rb");
        if (!f) {
            if (e->items[k][0]) {
                snprintf(s->error, sizeof s->error, "%s: missing", path);
                return 1;
            }
            continue;   /* the installed client lacks this class part */
        }
        fclose(f);
        if (mu_character_set_item(ch, k, path, 0, s->error, sizeof s->error))
            return 1;
    }
    return 0;
}

int mu_charsel_init(mu_charsel_session *s, const char *root, const mu_charsel_list *list,
                    const float markers[MU_CHARSEL_MARKERS][3], uint32_t width, uint32_t height, float near_plane)
{
    memset(s, 0, sizeof *s);
    s->draw_entry = -1;
    s->list = *list;
    s->records = calloc(MU_CHARSEL_CHARACTERS, MU_CHARSEL_RECORD);
    if (!s->records) {
        snprintf(s->error, sizeof s->error, "out of memory");
        return 1;
    }
    char error[512];
    s->map = mu_world_load(root, MU_CHARSEL_WORLD, 1, 1, error, sizeof error);
    if (!s->map) {
        snprintf(s->error, sizeof s->error, "world 0x5d: %s", error);
        return 1;
    }
    /* RenderCharacterScene's highlight textures (OpenCharacterSceneData 0x0182a553 and 0x01821e7b) */
    mu_world_load_extra(s->map, root, 0x8036, "Skill/gmmzine.jpg", 1, 1);
    mu_world_load_extra(s->map, root, 0x8022, "Logo/chasellight.jpg", 0, 1);
    if (mu_camera_info_load(root, s->map->report.folder, &s->info, error, sizeof error)) {
        snprintf(s->error, sizeof s->error, "camera record: %s", error);
        return 1;
    }
    /* camera: scene 5, the world record (OpenWorld sets CameraFOV from it) */
    mu_frame_world *f = &s->frame;
    mu_frame_world_init(f, width, height, 128, 128);
    memcpy(f->heights, s->map->height, sizeof f->heights);
    memcpy(f->walls, s->map->attributes, sizeof f->walls);
    f->terrain.water_height = s->map->water_height;
    mu_world_camera *c = &f->camera;
    c->scene = MU_CHARSEL_SCENE;
    c->world = MU_CHARSEL_WORLD;
    c->world_fov = s->info.fov;
    c->far_scale[0] = s->info.distance;
    c->far_scale[1] = s->info.z_distance;
    c->far_scale[2] = 1.0f;
    memcpy(c->scene_angle, s->info.angle, sizeof c->scene_angle);
    memcpy(c->scene_position, s->info.position, sizeof c->scene_position);
    f->view.fov = s->info.fov;
    f->view.view_near = near_plane;
    mu_world_camera_enter(c, &f->view);
    /* the map objects load with the world: slot markers 13..17 (CreateObject 0x00daa2b2) */
    mu_charsel_scene_init(&s->scene);
    for (int k = 0; k < MU_CHARSEL_MARKERS; ++k) {
        mu_charsel_map_object o;
        memset(&o, 0, sizeof o);
        o.type = 0x0d + k;
        const float *m = markers ? markers[k] : mu_charsel_default_marker1;
        memcpy(o.position, m, sizeof o.position);
        mu_charsel_create_object(&s->scene, MU_CHARSEL_WORLD, &o, lookup, s);
    }
    /* CreateCharacterScene 0x01851540: SelectedHero = -1 */
    s->selected = -1;
    s->shown = -1;
    s->initialised = 1;
    /* the character list: CreateHero, then the handler's SetCharacterPosition */
    mu_charsel_scale_inputs scale = {MU_CHARSEL_SCENE, MU_CHARSEL_WORLD, 0, 0, 0};
    for (int32_t i = 0; i < s->list.count; ++i) {
        const mu_charsel_entry *e = &s->list.entries[i];
        uint8_t *r = record(s, e->slot);
        /* CreateCharacter 0x0137d8a1 (not reconstructed): live, visible, Player model, scale 0.9 */
        r[MU_CHARSEL_OBJECT + MU_OBJ_LIVE] = 1;
        r[MU_CHARSEL_OBJECT + MU_OBJ_VISIBLE] = 1;
        int32_t type = MU_CHARSEL_PLAYER_MODEL;
        memcpy(r + MU_CHARSEL_OBJECT + MU_OBJ_TYPE, &type, sizeof type);
        putf(r, MU_CHARSEL_OBJECT + MU_OBJ_SCALE, 0.9f);
        mu_charsel_create_hero(e->slot, e->class_byte, 0, 0.0f, 0.0f, 0.0f, &scale, lookup, s, NULL);
        r[0x144] = (uint8_t)e->level;
        r[0x145] = (uint8_t)(e->level >> 8);
        /* NATIVE-CHARSEL-003: what the pick and the GFx list read of CreateCharacter 0x0137d8a1 (static reading):
         * the Player box (-60, -60, 0)..(40, 40, 120) (0x0137dfe3, 0x0137e2d4), alpha 1 (+0xdc), kind 1 (+0x3b),
         * CHARACTER +0x10 = 1; the name as an inline std::string at +0x3658; guild status +0x17 = 0xff (none,
         * the offline list has no guilds) */
        static const float box_min[3] = {-60.0f, -60.0f, 0.0f}, box_max[3] = {40.0f, 40.0f, 120.0f};
        for (uint32_t k = 0; k < 3; ++k) {
            putf(r, MU_CHARSEL_OBJECT + 0x128 + 4 * k, box_min[k]);
            putf(r, MU_CHARSEL_OBJECT + 0x134 + 4 * k, box_max[k]);
        }
        putf(r, MU_CHARSEL_OBJECT + 0xdc, 1.0f);
        r[MU_CHARSEL_OBJECT + 0x3b] = 1;
        r[0x10] = 1;
        r[0x17] = 0xff;
        size_t name_len = strnlen(e->name, 15);
        memcpy(r + 0x3658, e->name, name_len);
        r[0x3658 + name_len] = 0;
        r[0x3658 + 0x10] = (uint8_t)name_len;
        r[0x3658 + 0x14] = 15;
        mu_charsel_set_character_position(&s->scene, e->slot, lookup, s);
        if (load_entry(s, root, i))
            return 1;
        mu_character *ch = &s->characters[i];
        int32_t action = mu_player_stop_action(e->class_byte);   /* SetPlayerStop 0x0138fe69 */
        mu_character_set_state(ch, (uint16_t)action, 0.0f, 0.0f, (uint16_t)action);
    }
    if (s->list.count)
        mu_charsel_select(s, s->list.entries[0].slot);
    s->tick.scene = MU_CHARSEL_SCENE;
    s->tick.protocol = 0x35;
    s->tick.initialised = 1;
    /* NATIVE-CHARSEL-002: the particle module (scene 5) and the first render's frustum (the frame-light box
     * of the first step) */
    if (!mu_world_particles_open(&s->particles, root, s->map, MU_CHARSEL_WORLD, 1, 0, error, sizeof error)) {
        s->has_particles = 1;
        s->particles.scene_state = MU_CHARSEL_SCENE;
    }
    mu_move_main_camera(&f->camera, &f->view, 0);
    mu_view_begin_opengl(&f->view, 0, 0, 640, 480);
    mu_charsel_frustum(s, &s->frustum);
    return 0;
}

int mu_charsel_attach_objects(mu_charsel_session *s, const char *root, mu_objects *objects)
{
    if (!objects || mu_objects_start(objects, root))   /* CreateObject per record, CGMCharacterScene_Ex slot 0x2c */
        return 1;
    s->objects = objects;
    s->has_objects = 1;
    if (s->has_particles)
        mu_world_particles_attach(&s->particles, objects, NULL);
    return 0;
}

void mu_charsel_free(mu_charsel_session *s)
{
    if (s->has_particles)
        mu_world_particles_close(&s->particles);
    for (int i = 0; i < MU_CHARSEL_MAX_ENTRIES; ++i)
        if (s->character_loaded[i])
            mu_character_free(&s->characters[i]);
    if (s->map)
        mu_world_free(s->map);
    free(s->records);
    memset(s, 0, sizeof *s);
}

void mu_charsel_select(mu_charsel_session *s, int32_t slot)
{
    s->selected = slot;
    s->shown = slot;
}

void mu_charsel_message(mu_charsel_session *s, uint32_t message, uint32_t wparam, uint32_t lparam)
{
    mu_frame_world_message(&s->frame, message, wparam, lparam);
}

void mu_charsel_key(mu_charsel_session *s, int vk, int down)
{
    mu_frame_world_key(&s->frame, vk, down);
}

static void step(mu_charsel_session *s)
{
    mu_frame_world *f = &s->frame;
    mu_key_scan(&f->keys, &f->sample);   /* 0x00ec5475 before every logic step */
    /* scene tick 0x01856e6c: the terrain frame light (0x016ca4fa) first, the primary light over the last
     * frustum box grown by 3 tiles (NATIVE-CHARSEL-002, as the login scene's tick head) */
    const mu_terrain_frustum *fr = &s->frustum;
    int32_t x0 = fr->x_min, y0 = fr->y_min, x1 = fr->x_max + 3, y1 = fr->y_max + 3;
    mu_world_frame_box(s->map, (float)f->now, x0 < 0 ? 0 : x0, y0 < 0 ? 0 : y0, x1 > 255 ? 255 : x1,
                       y1 > 255 ? 255 : y1);
    /* MoveObjects 0x016d82c7 with CGMCharacterScene_Ex slot 0x30 (NATIVE-CHARSEL-002) */
    if (s->has_objects) {
        mu_objects_set_clock(s->objects, f->now);
        mu_objects_step_inputs in = {MU_CHARSEL_SCENE, 0, s->map->time, {0.0f, 0.0f, 0.0f}, fr->x2d, fr->y2d};
        mu_objects_step(s->objects, &in);
        mu_objects_apply_lights(s->objects, s->map);
    }
    mu_charsel_tick *t = &s->tick;
    t->initialised = s->initialised;
    t->selected = s->selected;
    t->shown = s->shown;
    t->key_enter = (uint8_t)mu_key_is(&f->keys, f->sample.active, 0x0d, MU_KEY_PRESS);   /* 0x00ec53a7(0x0d) */
    t->key_escape = (uint8_t)mu_key_is(&f->keys, f->sample.active, 0x1b, MU_KEY_PRESS);
    mu_charsel_log log;
    memset(&log, 0, sizeof log);
    mu_charsel_tick_step(t, &log);
    s->selected = t->selected;
    for (int32_t i = 0; i < log.count; ++i)
        if (log.events[i].call == 0x0185a75a)
            ++s->enter_requests;
    /* MoveCharacters 0x0137a7ce: one animation step per character */
    for (int32_t i = 0; i < s->list.count; ++i) {
        if (!s->character_loaded[i])
            continue;
        mu_character *ch = &s->characters[i];
        uint8_t loop = 0;
        mu_character_tick(ch, mu_character_action_speed(ch, mu_model_action(&ch->player)), &loop);
    }
    /* MoveEffects 0x0150ddb1, MoveJoints 0x01589b06, MoveParticles 0x0159122d (NATIVE-CHARSEL-002) */
    if (s->has_particles)
        mu_world_particles_step(&s->particles, s->map->time);
    ++s->steps;
}

int32_t mu_charsel_update(mu_charsel_session *s, uint32_t now)
{
    int32_t steps = 0;
    s->frame.now = now;
    mu_frame_begin(&s->frame.clock);
    while (mu_frame_logic_step(&s->frame.clock)) {
        step(s);
        ++steps;
    }
    return steps;
}

void mu_charsel_begin_render(mu_charsel_session *s, uint32_t now)
{
    mu_frame_world *f = &s->frame;
    f->now = now;
    mu_frame_render_start(&f->clock, now);
    /* MoveMainCamera reads the hero's tile for the lift zone; the scene's hero
     * pointer is not modelled (0: no lift) */
    f->camera.hero_tile_wall = 0;
    mu_move_main_camera(&f->camera, &f->view, now);
    mu_view_begin_opengl(&f->view, 0, 0, 640, 480);
    mu_view_create_screen_vector(&f->view, (float)f->mouse.x, (float)f->mouse.y, f->view.mouse_target, 1);
    mu_charsel_frame frame;
    memset(&frame, 0, sizeof frame);
    frame.initialised = s->initialised;
    frame.protocol = 0x35;
    frame.selected = s->selected;
    frame.shown = s->shown;
    frame.world_time = (float)now;
    frame.mouse_x = f->mouse.x;
    frame.mouse_y = f->mouse.y;
    memcpy(frame.record_position, s->info.position, sizeof frame.record_position);
    frame.pick = s->pick = mu_charsel_pick(s);   /* 0x016b47bf(1), NATIVE-CHARSEL-003 */
    frame.input_byte_1f = f->mouse.left_double;  /* CInput +0x1f: the double click (WM_LBUTTONDBLCLK) */
    if (f->mouse.left_double) {
        ++s->double_clicks;
        f->mouse.left_double = 0;
    }
    frame.screen_width = 640;
    uint8_t fog = 1;
    memset(&s->log, 0, sizeof s->log);
    mu_charsel_render(&frame, lookup, s, &fog, &s->log);
    s->draw_entry = -1;
    s->decal_count = 0;
    s->particles_created = 0;
    for (int32_t i = 0; i < s->log.count; ++i) {
        const mu_charsel_event *e = &s->log.events[i];
        switch (e->call) {
        case 0x016cacfc: {   /* AddTerrainLight(x, y, light, range, frame light) */
            float rgb[3] = {fbits(e->args[2]), fbits(e->args[3]), fbits(e->args[4])};
            mu_world_add_light(s->map, fbits(e->args[0]), fbits(e->args[1]), rgb, (int32_t)e->args[5]);
            break;
        }
        case 0x01363260:     /* RenderCharacter(shown) */
            s->draw_entry = mu_charsel_entry_of(s, s->shown);
            break;
        case 0x016cdd5f:     /* RenderTerrainAlphaBitmap(0x8036, ...) */
            if (s->decal_count < 2) {
                mu_charsel_decal *d = &s->decals[s->decal_count++];
                d->x = fbits(e->args[1]);
                d->y = fbits(e->args[2]);
                d->size = fbits(e->args[3]);
                d->light[0] = fbits(e->args[5]);
                d->light[1] = fbits(e->args[6]);
                d->light[2] = fbits(e->args[7]);
                d->rotation = fbits(e->args[8]);
            }
            break;
        case 0x0168fafd:     /* CreateParticle(0x8022 Logo\\chasellight.jpg, position, angle, light, 5, 1.0, NULL, 0) */
            ++s->particles_created;
            if (s->has_particles && e->count >= 12) {
                float position[3], angle[3], light[3];
                for (int k = 0; k < 3; ++k) {
                    position[k] = fbits(e->args[1 + k]);
                    angle[k] = fbits(e->args[4 + k]);
                    light[k] = fbits(e->args[7 + k]);
                }
                mu_world_particles_create(&s->particles, (int32_t)e->args[0], position, angle, light,
                                          (int32_t)e->args[10], fbits(e->args[11]));
            }
            break;
        case 0x0185a75a:
            ++s->enter_requests;
            break;
        default:
            break;
        }
    }
    /* the drawn character's object state */
    if (s->draw_entry >= 0) {
        const uint8_t *o = record(s, s->shown) + MU_CHARSEL_OBJECT;
        mu_character *ch = &s->characters[s->draw_entry];
        for (int k = 0; k < 3; ++k) {
            ch->params.position[k] = getf(o, MU_OBJ_POSITION + 4u * (uint32_t)k);
            ch->params.angles[k] = getf(o, MU_OBJ_ANGLE + 4u * (uint32_t)k);
        }
        ch->params.scale = getf(o, MU_OBJ_SCALE);
        /* RenderCharacter 0x01367530 (scene 5): body light = 0.4 + object light,
         * read at RenderCharacter time, i.e. before the highlight sets 0.15;
         * static reading */
        float object_light = s->selected == s->shown ? 1.0f : 0.0f;   /* reset 0, the selected one 1 */
        for (int k = 0; k < 3; ++k)
            ch->params.light[k] = 0.4f + object_light;
        mu_character_update(ch);
        /* RenderPartObject's Transform(bones, BoundingBoxMin, BoundingBoxMax, &OBB, ...) 0x017e68a6 (bounds mode
         * not 2): StartPos = min + body origin (the position), axes diag(max - min); NATIVE-CHARSEL-003 */
        uint8_t *w = record(s, s->shown) + MU_CHARSEL_OBJECT;
        for (uint32_t k = 0; k < 3; ++k) {
            float lo = getf(w, 0x128 + 4 * k), hi = getf(w, 0x134 + 4 * k);
            putf(w, 0x31c + 4 * k, lo + getf(w, MU_OBJ_POSITION + 4 * k));
            for (uint32_t a = 0; a < 3; ++a)
                putf(w, 0x328 + 0xc * a + 4 * k, a == k ? hi - lo : 0.0f);
        }
    }
    /* the render's frustum (CreateFrustrum) and the objects' clock (NATIVE-CHARSEL-002) */
    mu_charsel_frustum(s, &s->frustum);
    if (s->has_objects)
        mu_objects_set_clock(s->objects, now);
    if (s->has_particles)
        s->particles.world_time = s->map->time;
    ++s->frames;
}

void mu_charsel_frame_objects(mu_charsel_session *s)
{
    const uint64_t sprites = s->particles.stats.sprites_created;
    if (s->has_objects) {
        mu_objects *o = s->objects;
        mu_objects_visibility(o, &s->frustum, MU_CHARSEL_SCENE);
        for (int32_t k = 0; k < o->rt.draw_count; ++k) {
            mu_draw_options options;
            mu_objects_prepare(o, k, s->map, MU_CHARSEL_SCENE, &options);
        }
        mu_objects_after_visibility(o, &s->frustum, MU_CHARSEL_SCENE);
    }
    if (s->has_particles) {
        s->frame_sprites = (int32_t)(s->particles.stats.sprites_created - sprites);
        mu_world_particles_discard_sprites(&s->particles);   /* a frame without drawing: RenderSprites' kill */
    }
}

/* ---- SelectCharacter 0x016b47bf (NATIVE-CHARSEL-003) ---- */

static float dot3(const float a[3], const float b[3]) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }

static void cross3(const float a[3], const float b[3], float o[3])
{
    o[0] = a[1] * b[2] - a[2] * b[1];
    o[1] = a[2] * b[0] - a[0] * b[2];
    o[2] = a[0] * b[1] - a[1] * b[0];
}

/* 0x01850d88: the segment and the box projected on an axis overlap */
static int axis_overlap(const float axis[3], const float p1[3], const float p2[3], const float obb[12])
{
    float d1 = dot3(axis, p1), d2 = dot3(axis, p2);
    float lo = dot3(axis, obb), hi = lo;
    for (int k = 1; k < 4; ++k) {
        float d = dot3(axis, obb + 3 * k);
        if (d < 0.0f)
            lo += d;
        else
            hi += d;
    }
    float smin = d1 < d2 ? d1 : d2, smax = d1 < d2 ? d2 : d1;
    return !(smax < lo || smin > hi);
}

/* 0x018500bf: no separating axis among (p2 - p1) x X, x Y, x Z, X, Y, Z */
static int segment_obb(const float p1[3], const float p2[3], const float obb[12])
{
    float d[3] = {p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2]}, n[3];
    for (int k = 1; k < 4; ++k) {
        cross3(d, obb + 3 * k, n);
        if (!axis_overlap(n, p1, p2, obb))
            return 0;
    }
    for (int k = 1; k < 4; ++k)
        if (!axis_overlap(obb + 3 * k, p1, p2, obb))
            return 0;
    return 1;
}

int32_t mu_charsel_pick(mu_charsel_session *s)
{
    const mu_client_view *v = &s->frame.view;
    static const float LIGHT[5][3] = {{0.2f, 0.2f, 0.2f}, {-0.4f, -0.4f, -0.4f}, {0.2f, -0.6f, -0.6f},
                                      {1.5f, 1.5f, 1.5f}, {0.3f, 0.2f, -0.5f}};
    /* first pass: every live, visible character of kind 1 gets LightEnable and the level-indexed light (the
     * render resets the lights of 0..9 right after) */
    for (int32_t i = 0; i < MU_CHARSEL_CHARACTERS; ++i) {
        uint8_t *c = record(s, i), *o = c + MU_CHARSEL_OBJECT;
        if ((o[0x3b] & 1) != o[0x3b] || !o[MU_OBJ_LIVE] || !o[MU_OBJ_VISIBLE] || !(getf(o, 0xdc) > 0.0f))
            continue;
        o[5] = 1;
        uint16_t level = (uint16_t)(c[0x144] | c[0x145] << 8);
        if (level < 5)
            for (uint32_t k = 0; k < 3; ++k)
                putf(o, MU_OBJ_LIGHT + 4 * k, LIGHT[level][k]);
        if (c[0x1f] >= 6)
            for (uint32_t k = 0; k < 3; ++k)
                putf(o, MU_OBJ_LIGHT + 4 * k, -0.4f);
    }
    int32_t best = -1;
    float best_d = 1e12f;
    ++s->picks;
    for (int32_t i = 0; i < MU_CHARSEL_CHARACTERS; ++i) {
        uint8_t *c = record(s, i), *o = c + MU_CHARSEL_OBJECT;
        if (!o[MU_OBJ_LIVE] || !o[MU_OBJ_VISIBLE] || !(getf(o, 0xdc) > 0.0f) || c[0x23] || !c[0x10])
            continue;   /* scene 5: the hero is not skipped; no buff 0x1b on the select screen's records */
        if ((o[0x3b] & 1) != o[0x3b])
            continue;
        float obb[12];
        for (uint32_t k = 0; k < 12; ++k)
            obb[k] = getf(o, 0x31c + 4 * k);
        obb[11] = obb[11] + 100.0f;   /* world 0x5d: ZAxis.z += 100, written back */
        putf(o, 0x31c + 44, obb[11]);
        if (!segment_obb(v->mouse_position, v->mouse_target, obb))
            continue;
        float d[3];
        for (uint32_t k = 0; k < 3; ++k)
            d[k] = getf(o, MU_OBJ_POSITION + 4 * k) - v->position[k];
        float dist = d[0] * d[0] + d[1] * d[1] + d[2] * d[2];
        if (dist < best_d) {
            best_d = dist;
            best = i;
        }
    }
    if (best >= 0)
        ++s->pick_hits;
    return best;
}

int32_t mu_charsel_end_render(mu_charsel_session *s)
{
    return mu_frame_finish(&s->frame.clock);
}

int mu_charsel_frustum(const mu_charsel_session *s, mu_terrain_frustum *frustum)
{
    const mu_client_view *v = &s->frame.view;
    float rows[12];
    for (int r = 0; r < 3; ++r)
        for (int c = 0; c < 4; ++c)
            rows[r * 4 + c] = v->modelview[r + 4 * c];
    /* CreateFrustrum2D zoom mode 0 takes the camera record (NATIVE-CHARSEL-002): s = 640 / 640 * Distance *
     * Z_Distance * manager scale (0x0098ac7c), distance = 2400 * Distance * Z_Distance * scale (0x0098ac45);
     * TestFrustrum2D does not pass everything in scene 5 (only 1..4), so the polygon culls the objects */
    float scale = 640.0f / 640.0f;
    scale = scale * s->info.distance;
    scale = scale * s->info.z_distance;
    scale = scale * 1.0f;
    float distance = 2400.0f * s->info.distance;
    distance = distance * s->info.z_distance;
    distance = distance * 1.0f;
    return mu_world_client_frustum_scaled(s->map, rows, v->position, s->info.position, v->angle[0], 640, 0,
                                          v->view_far, v->fov, scale, distance, frustum);
}
