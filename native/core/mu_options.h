#ifndef MU_OPTIONS_H
#define MU_OPTIONS_H

#include <stddef.h>
#include <stdint.h>

#include "mu_camera.h"
#include "mu_model.h"
#include "mu_scene.h"

/* Command-line options shared by the headless tool and the windowed viewer. */
typedef struct mu_options {
    const char *model_path;
    const char *output;
    const char *case_output;   /* corners: also write the mesh-draw case */
    const char *tables_output; /* replay: tables each mesh draw wrote */
    const char *texture_dir;
    int no_textures;
    mu_model_params params;
    mu_draw_options draw;
    int32_t action, prior_action;
    float frame, prior_frame;
    int32_t ticks;
    float speed;
    int stop;
    int32_t width, height;
    float yaw, pitch, zoom, fov;
    int linear;                /* bilinear sampling for every texture (viewer choice; the client uses GL_NEAREST) */
    int front_cw;
    uint8_t background[4];
    const char *backend;       /* "soft" or "gl" */
    int headless;
    int compare;               /* headless: also render the other backend and report differences */
    float seconds;             /* windowed: quit after this many seconds (0 = run until closed) */
    /* Character mode (NATIVE-CHAR-001): the positional model is Player.bmd. */
    int character;             /* set by any character option */
    const char *game_root;     /* resolves Player.bmd and class parts */
    int32_t class_byte;        /* -1: no class parts; else low nibble class, high nibble evolution flags */
    int32_t part_mask;         /* class parts to load, bit = slot (default helm..boots) */
    const char *part_paths[6]; /* explicit part models per slot (override the class part) */
    const char *weapon_paths[2];
    const char *wing_path;
    int32_t weapon_actions[2];
    float wing_scale;          /* <= 0: same as --scale */
    int scale_set;             /* --scale given (character default 0.9 otherwise) */
    /* Actor mode (NATIVE-ACTOR-001, mu-render actor): see mu_actor.h. */
    int32_t actor_by;          /* MU_ACTOR_BY_*: --type (server class), --monster, --npc; 0 = none */
    int32_t actor_id;
    float time;                /* seconds of animation before the first rendered frame (40 ms steps) */
    int32_t frames;            /* frames for --strip/--gif (default 1) */
    int32_t frame_steps;       /* animation steps between rendered frames (default 2) */
    const char *strip_path;    /* PNG with the frames side by side */
    const char *gif_path;      /* animated GIF of the frames */
    int32_t player_action;     /* character mode: --pose stand|walk|attack (-1: use --action) */
    int32_t weapon_kind;       /* character mode: --weapon-kind for --pose (MU_WEAPON_*) */
} mu_options;

void mu_options_defaults(mu_options *options);
/* Parses argv[first..]; positional argument = model path. Returns 0 on
 * success, prints a message and returns 1 on error. */
int mu_options_parse(mu_options *options, int argc, char **argv, int first);
void mu_options_usage(const char *program);

/* Sets the animation state, runs the requested ticks, poses and skins. */
int mu_options_animate(const mu_options *options, mu_model *model, uint8_t *loop);
/* Character mode: loads Player.bmd, class parts, explicit parts, weapons and
 * wing into an initialised-by-this-call mu_character (mu_character.h), sets
 * its object parameters from --origin/--angles/--head/--scale/--color/
 * --lighting, applies the animation options to the Player and updates. */
struct mu_character;
int mu_options_character(const mu_options *options, struct mu_character *character, char *error, size_t error_size);
void mu_options_character_camera(const mu_options *options, const struct mu_character *character, mu_camera *camera);
/* Frames the camera on the model's current transform output. */
void mu_options_camera(const mu_options *options, const mu_model *model, mu_camera *camera);

#endif
