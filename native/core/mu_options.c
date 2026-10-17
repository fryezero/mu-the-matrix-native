/* Shared command-line options. See mu_options.h. */
#include "mu_options.h"

#include "mu_character.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void mu_options_defaults(mu_options *o)
{
    memset(o, 0, sizeof *o);
    mu_model_default_params(&o->params);
    mu_draw_default_options(&o->draw);
    o->speed = 0.25f;
    o->width = 640;
    o->height = 480;
    o->yaw = -60.0f;
    o->pitch = 15.0f;
    o->zoom = 1.0f;
    o->fov = 35.0f;
    o->background[0] = 40;
    o->background[1] = 44;
    o->background[2] = 52;
    o->background[3] = 255;
    o->backend = "soft";
    o->class_byte = -1;
    o->part_mask = 0x3e;
}

void mu_options_usage(const char *program)
{
    fprintf(stderr,
            "usage: %s [options] MODEL.bmd\n"
            "  animation: --action N --frame F --prior-action N --prior-frame F --ticks N --speed F --stop\n"
            "  draw:      --mode M --flags F --alpha F --uv-offset U V --uv-mesh I --alpha-test --cull 0|1\n"
            "  model:     --scale F --origin X Y Z --angles X Y Z --head X Y --color R G B --lighting 0|1\n"
            "             --light-angles X Y Z --secondary 0|1 --ambient F --light-scale F --light-min F\n"
            "             --vertex-scale F --bone-scale F --world N --scene N --bounds-mode N --light-override 0|1\n"
            "             --pose-translate 0|1 --translate 0|1 --special-bone N --light-skip-mesh N --root-height F\n"
            "  view:      --width W --height H --yaw D --pitch D --zoom F --fov D --nearest --front-cw\n"
            "             --background R G B --textures DIR --no-textures --out PATH --backend soft|gl --headless --compare --seconds S\n"
            "  character: --character --game-root DIR --class C --parts MASK --part SLOT PATH --weapon SLOT PATH\n"
            "             --weapon-action SLOT N --wing PATH --wing-scale F   (MODEL = Player.bmd, default from --game-root;\n"
            "             --origin/--angles/--head/--scale/--color/--lighting set the object; slots 1..5 helm..boots)\n",
            program);
}

static int number(const char *text, double *value)
{
    char *end = NULL;
    if (!text)
        return 0;
    if ((text[0] == '0' && (text[1] == 'x' || text[1] == 'X')) ||
        (text[0] == '-' && text[1] == '0' && (text[2] == 'x' || text[2] == 'X')))
        *value = (double)strtoll(text, &end, 16);
    else
        *value = strtod(text, &end);
    return end && *end == 0;
}

int mu_options_parse(mu_options *o, int argc, char **argv, int first)
{
    for (int i = first; i < argc; ++i) {
        const char *a = argv[i];
        double v[3];
#define NEED(n) do { for (int k_ = 0; k_ < (n); ++k_) if (i + 1 + k_ >= argc || !number(argv[i + 1 + k_], &v[k_])) { \
            fprintf(stderr, "%s needs %d numeric value(s)\n", a, (n)); return 1; } i += (n); } while (0)
        if (!strcmp(a, "--action")) { NEED(1); o->action = (int32_t)v[0]; }
        else if (!strcmp(a, "--frame")) { NEED(1); o->frame = (float)v[0]; }
        else if (!strcmp(a, "--prior-action")) { NEED(1); o->prior_action = (int32_t)v[0]; }
        else if (!strcmp(a, "--prior-frame")) { NEED(1); o->prior_frame = (float)v[0]; }
        else if (!strcmp(a, "--ticks")) { NEED(1); o->ticks = (int32_t)v[0]; }
        else if (!strcmp(a, "--speed")) { NEED(1); o->speed = (float)v[0]; }
        else if (!strcmp(a, "--stop")) o->stop = 1;
        else if (!strcmp(a, "--mode")) { NEED(1); o->draw.mode = (int32_t)v[0]; }
        else if (!strcmp(a, "--flags")) { NEED(1); o->draw.flags = (uint32_t)(int64_t)v[0]; }
        else if (!strcmp(a, "--alpha")) { NEED(1); o->draw.alpha = (float)v[0]; }
        else if (!strcmp(a, "--uv-offset")) { NEED(2); o->draw.u_offset = (float)v[0]; o->draw.v_offset = (float)v[1]; }
        else if (!strcmp(a, "--uv-mesh")) { NEED(1); o->draw.uv_offset_mesh = (int32_t)v[0]; }
        else if (!strcmp(a, "--alpha-test")) o->draw.alpha_test = 1;
        else if (!strcmp(a, "--cull")) { NEED(1); o->draw.cull = (int8_t)v[0]; }
        else if (!strcmp(a, "--scale")) { NEED(1); o->params.body_scale = (float)v[0]; o->scale_set = 1; }
        else if (!strcmp(a, "--origin")) { NEED(3); for (int k = 0; k < 3; ++k) o->params.origin[k] = (float)v[k]; }
        else if (!strcmp(a, "--angles")) { NEED(3); for (int k = 0; k < 3; ++k) o->params.angles[k] = (float)v[k]; }
        else if (!strcmp(a, "--head")) { NEED(2); o->params.head_angles[0] = (float)v[0]; o->params.head_angles[1] = (float)v[1]; }
        else if (!strcmp(a, "--color")) { NEED(3); for (int k = 0; k < 3; ++k) o->params.color[k] = (float)v[k]; }
        else if (!strcmp(a, "--lighting")) { NEED(1); o->params.lighting = (uint8_t)v[0]; }
        else if (!strcmp(a, "--light-angles")) { NEED(3); for (int k = 0; k < 3; ++k) o->params.light_angles[k] = (float)v[k]; }
        else if (!strcmp(a, "--secondary")) { NEED(1); o->params.secondary_light = (uint8_t)v[0]; }
        else if (!strcmp(a, "--ambient")) { NEED(1); o->params.light_ambient = (float)v[0]; }
        else if (!strcmp(a, "--light-scale")) { NEED(1); o->params.light_scale = (float)v[0]; }
        else if (!strcmp(a, "--light-min")) { NEED(1); o->params.light_minimum = (float)v[0]; }
        else if (!strcmp(a, "--vertex-scale")) { NEED(1); o->params.vertex_scale = (float)v[0]; }
        else if (!strcmp(a, "--bone-scale")) { NEED(1); o->params.bone_scale = (float)v[0]; }
        else if (!strcmp(a, "--world")) { NEED(1); o->params.world = (int32_t)v[0]; }
        else if (!strcmp(a, "--scene")) { NEED(1); o->params.scene_state = (int32_t)v[0]; }
        else if (!strcmp(a, "--bounds-mode")) { NEED(1); o->params.bounds_mode = (int32_t)v[0]; }
        else if (!strcmp(a, "--light-override")) { NEED(1); o->params.light_override = (uint8_t)v[0]; }
        else if (!strcmp(a, "--pose-translate")) { NEED(1); o->params.pose_translate = (uint8_t)v[0]; }
        else if (!strcmp(a, "--translate")) { NEED(1); o->params.transform_translate = (uint8_t)v[0]; }
        else if (!strcmp(a, "--special-bone")) { NEED(1); o->params.special_bone = (int32_t)v[0]; }
        else if (!strcmp(a, "--light-skip-mesh")) { NEED(1); o->params.light_skip_mesh = (int32_t)v[0]; }
        else if (!strcmp(a, "--root-height")) { NEED(1); o->params.height = (float)v[0]; }
        else if (!strcmp(a, "--width")) { NEED(1); o->width = (int32_t)v[0]; }
        else if (!strcmp(a, "--height")) { NEED(1); o->height = (int32_t)v[0]; }
        else if (!strcmp(a, "--size")) { NEED(2); o->width = (int32_t)v[0]; o->height = (int32_t)v[1]; }
        else if (!strcmp(a, "--yaw")) { NEED(1); o->yaw = (float)v[0]; }
        else if (!strcmp(a, "--pitch")) { NEED(1); o->pitch = (float)v[0]; }
        else if (!strcmp(a, "--zoom")) { NEED(1); o->zoom = (float)v[0]; }
        else if (!strcmp(a, "--fov")) { NEED(1); o->fov = (float)v[0]; }
        else if (!strcmp(a, "--nearest")) o->nearest = 1;
        else if (!strcmp(a, "--front-cw")) o->front_cw = 1;
        else if (!strcmp(a, "--background")) { NEED(3); for (int k = 0; k < 3; ++k) o->background[k] = (uint8_t)v[k]; }
        else if (!strcmp(a, "--textures")) { if (++i >= argc) return 1; o->texture_dir = argv[i]; }
        else if (!strcmp(a, "--no-textures")) o->no_textures = 1;
        else if (!strcmp(a, "--out")) { if (++i >= argc) return 1; o->output = argv[i]; }
        else if (!strcmp(a, "--backend")) { if (++i >= argc) return 1; o->backend = argv[i]; }
        else if (!strcmp(a, "--headless")) o->headless = 1;
        else if (!strcmp(a, "--compare")) o->compare = 1;
        else if (!strcmp(a, "--seconds")) { NEED(1); o->seconds = (float)v[0]; }
        else if (!strcmp(a, "--character")) o->character = 1;
        else if (!strcmp(a, "--game-root")) { if (++i >= argc) return 1; o->game_root = argv[i]; o->character = 1; }
        else if (!strcmp(a, "--class")) { NEED(1); o->class_byte = (int32_t)v[0] & 0xff; o->character = 1; }
        else if (!strcmp(a, "--parts")) { NEED(1); o->part_mask = (int32_t)v[0]; o->character = 1; }
        else if (!strcmp(a, "--part") || !strcmp(a, "--weapon")) {
            int weapon = a[2] == 'w';
            NEED(1);
            int slot = (int)v[0];
            if (slot < 0 || slot >= (weapon ? 2 : 6) || ++i >= argc) { fprintf(stderr, "%s SLOT PATH\n", a); return 1; }
            if (weapon) o->weapon_paths[slot] = argv[i]; else o->part_paths[slot] = argv[i];
            o->character = 1;
        }
        else if (!strcmp(a, "--weapon-action")) { NEED(2); if (v[0] < 0 || v[0] > 1) return 1; o->weapon_actions[(int)v[0]] = (int32_t)v[1]; }
        else if (!strcmp(a, "--wing")) { if (++i >= argc) return 1; o->wing_path = argv[i]; o->character = 1; }
        else if (!strcmp(a, "--wing-scale")) { NEED(1); o->wing_scale = (float)v[0]; }
        else if (a[0] == '-' && a[1] == '-') { fprintf(stderr, "unknown option %s\n", a); return 1; }
        else if (!o->model_path) o->model_path = a;
        else { fprintf(stderr, "unexpected argument %s\n", a); return 1; }
#undef NEED
    }
    return 0;
}

int mu_options_animate(const mu_options *o, mu_model *model, uint8_t *loop)
{
    mu_model_apply_params(model, &o->params);
    mu_model_set_state(model, (uint16_t)o->action, o->frame, o->prior_frame, (uint16_t)o->prior_action);
    if (o->stop)
        mu_model_set_action_stop(model, (uint16_t)o->action, 1);
    uint8_t result = 1;
    for (int32_t k = 0; k < o->ticks; ++k)
        if (mu_model_tick(model, o->speed, &result) != MU_MODEL_OK)
            return MU_MODEL_ERROR;
    if (loop)
        *loop = result;
    return mu_model_update(model);
}

void mu_options_camera(const mu_options *o, const mu_model *model, mu_camera *camera)
{
    float lo[3] = {1e30f, 1e30f, 1e30f}, hi[3] = {-1e30f, -1e30f, -1e30f};
    int any = 0;
    for (int32_t i = 0; i < model->bmd->mesh_count; ++i) {
        const float *v = mu_model_vertices(model, i);
        for (int32_t j = 0; j < model->bmd->meshes[i].vertex_count; ++j)
            for (int k = 0; k < 3; ++k) {
                float x = v[3 * j + k];
                if (x < lo[k]) lo[k] = x;
                if (x > hi[k]) hi[k] = x;
                any = 1;
            }
    }
    if (!any)
        for (int k = 0; k < 3; ++k) {
            lo[k] = -50.0f;
            hi[k] = 50.0f;
        }
    memset(camera, 0, sizeof *camera);
    camera->fov_y = o->fov;
    mu_camera_frame(camera, lo, hi);
    camera->yaw = o->yaw;
    camera->pitch = o->pitch;
    camera->distance = camera->distance * o->zoom;
    camera->near_plane = camera->near_plane * o->zoom;
    camera->far_plane = camera->far_plane * o->zoom;
}

int mu_options_character(const mu_options *o, mu_character *c, char *error, size_t error_size)
{
    char player[4096];
    if (o->model_path)
        snprintf(player, sizeof player, "%s", o->model_path);
    else if (o->game_root)
        snprintf(player, sizeof player, "%s/Data/Player/Player.bmd", o->game_root);
    else {
        snprintf(error, error_size, "character mode needs Player.bmd or --game-root");
        return 1;
    }
    if (mu_character_init(c, player, &o->params, error, error_size))
        return 1;
    for (int slot = 0; slot < MU_CHARACTER_PART_SLOTS; ++slot) {
        char path[4096];
        const char *chosen = o->part_paths[slot];
        if (!chosen && o->class_byte >= 0 && o->game_root && (o->part_mask >> slot & 1) &&
            mu_character_part_path(o->game_root, slot, (uint8_t)o->class_byte, path, sizeof path))
            chosen = path;
        if (chosen && mu_character_set_item(c, slot, chosen, o->no_textures, error, error_size))
            return 1;
    }
    for (int slot = 0; slot < MU_CHARACTER_WEAPON_SLOTS; ++slot) {
        c->items[MU_CHARACTER_WEAPON_ITEM(slot)].action = (uint16_t)o->weapon_actions[slot];
        if (o->weapon_paths[slot] &&
            mu_character_set_item(c, MU_CHARACTER_WEAPON_ITEM(slot), o->weapon_paths[slot], o->no_textures, error,
                                  error_size))
            return 1;
    }
    if (o->wing_path && mu_character_set_item(c, MU_CHARACTER_WING_ITEM, o->wing_path, o->no_textures, error,
                                              error_size))
        return 1;
    mu_character_params *p = &c->params;
    for (int k = 0; k < 3; ++k) {
        p->position[k] = o->params.origin[k];
        p->angles[k] = o->params.angles[k];
        p->light[k] = o->params.color[k];
    }
    p->head[0] = o->params.head_angles[0];
    p->head[1] = o->params.head_angles[1];
    /* Object scale: creation default 0.9 (0x0137d9dd) unless --scale is given. */
    p->scale = o->scale_set ? o->params.body_scale : 0.9f;
    p->wing_scale = o->wing_scale > 0 ? o->wing_scale : p->scale;
    p->lighting = o->params.lighting;
    mu_character_set_state(c, (uint16_t)o->action, o->frame, o->prior_frame, (uint16_t)o->prior_action);
    if (o->stop)
        mu_model_set_action_stop(&c->player, (uint16_t)o->action, 1);
    for (int32_t k = 0; k < o->ticks; ++k)
        if (mu_character_tick(c, o->speed, NULL) != MU_MODEL_OK) {
            snprintf(error, error_size, "tick failed");
            return 1;
        }
    if (mu_character_update(c) != MU_MODEL_OK) {
        snprintf(error, error_size, "character update failed");
        return 1;
    }
    return 0;
}

void mu_options_character_camera(const mu_options *o, const mu_character *c, mu_camera *camera)
{
    float lo[3], hi[3];
    if (!mu_character_bounds(c, lo, hi))
        for (int k = 0; k < 3; ++k) {
            lo[k] = -100.0f;
            hi[k] = 100.0f;
        }
    memset(camera, 0, sizeof *camera);
    camera->fov_y = o->fov;
    mu_camera_frame(camera, lo, hi);
    camera->yaw = o->yaw;
    camera->pitch = o->pitch;
    camera->distance = camera->distance * o->zoom;
    camera->near_plane = camera->near_plane * o->zoom;
    camera->far_plane = camera->far_plane * o->zoom;
}
