#ifndef MU_CHARSEL_RT_INTERNAL_H
#define MU_CHARSEL_RT_INTERNAL_H
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "mu_charsel_rt.h"
#include "charsel_part.h"
#include "../core/mu_charsel_ui.h"
#include "../core/mu_objects.h"
#include "../core/mu_perf.h"
#include "../core/mu_scene.h"
#include "../core/mu_terrain.h"
#ifndef MU_CHARSEL_NO_GL
#ifdef __APPLE__
#include <OpenGL/gl.h>
#else
#include <GL/gl.h>
#endif
#include "../viewer/gl_backend.h"
#include "../viewer/gl_batch.h"
#endif
#define MU_CHARSEL_AFTER_MESHES 32

struct mu_charsel_rt {
    mu_charsel_rt_options options;
    mu_charsel_ui *ui;
    mu_raster *soft_raster; /* synchronous character backend callback context */
    mu_charsel_list list;
    mu_charsel_session *s;
    /* NATIVE-OBJECTS-001: static objects and markers from a local decoded EncTerrain94.plain */
    mu_objects objects;
    int has_objects;
    long objects_drawn;
#ifndef MU_CHARSEL_NO_GL
    struct {
        GLuint tiles[MU_WORLD_BITMAPS], extras[MU_WORLD_EXTRA];
        mu_gl_batch *batch; /* shared with the first objects pass */
    } terrain;
    struct {
        mu_gl_backend models[MU_OBJECT_TYPES], batched[MU_OBJECT_TYPES];
    } object_render;
    struct {
        mu_gl_backend items[MU_CHARSEL_MAX_ENTRIES][MU_CHARACTER_ITEMS];
    } character;
    struct {
        mu_gl_backend bitmaps, models[MU_WORLD_FX_MODELS];
    } effects;
    int gl_ready;
#endif
};

#define MU_CHARSEL_PART(id) extern const mu_charsel_part_ops mu_charsel_##id##_part;
#include "parts.def"
#undef MU_CHARSEL_PART
#ifndef MU_CHARSEL_NO_GL
void charsel_gl_state(void *context, int32_t state, int32_t argument);
void charsel_terrain_sink(mu_charsel_rt *rt, mu_terrain_sink *sink);
#endif
#endif
