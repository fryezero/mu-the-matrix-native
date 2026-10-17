/* Terrain mode of mu-viewer (NATIVE-TERRAIN-001).
 *
 *   mu-viewer --terrain ROOT --world N [--width W --height H --seconds S]
 *   mu-viewer --terrain ROOT --world N --headless --out PNG [--backend gl|soft] [--compare]
 *             [--target X,Y --yaw D --pitch D --distance U --time MS]
 *
 * The tile stream of reconstructed/terrain goes to OpenGL 2.1 immediate mode:
 * the state wrappers become glEnable/glBlendFunc/glDepthMask/glCullFace
 * changes, bind() binds the world's bitmap, and the fan/quad calls are the
 * client's own. Free camera: W/S/A/D move the focus point over the ground,
 * Q/E turn, the mouse drag orbits, the wheel zooms, R resets, Space pauses the
 * clock (water and grass sway), G toggles wireframe, O saves a screenshot.
 * NATIVE-TERRAIN-002: L toggles dynamic lights (AddTerrainLight sources around
 * the focus point), F the client's frustum culling around the focus point
 * (CreateFrustrum box from this camera, CreateFrustrum2D polygon), K a decal
 * (Effect\flare01, RenderTerrainAlphaBitmap) under the focus point, 4 the
 * graphics option 4 (0x4000 neighbour faces). Headless: --lights --frustum
 * --decal --detail N. Game logic is not run; the clock only feeds the terrain
 * animation (water/lava scroll, sway, the 32-frame animated layer). */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <SDL.h>
#ifdef __APPLE__
#include <OpenGL/gl.h>
#else
#include <GL/gl.h>
#endif

#include "../core/mu_camera.h"
#include "../core/mu_png.h"
#include "../core/mu_raster.h"
#include "../core/mu_terrain.h"
#include "gl_backend.h"
#include "gl_headless.h"

typedef struct terrain_view {
    const char *root, *out, *backend;
    int32_t world, width, height;
    int headless, compare, wireframe, paused;
    int lights, frustum, decal, detail;
    float seconds, time;
    mu_camera camera;
    mu_world *map;
    GLuint names[MU_WORLD_BITMAPS], extra_names[MU_WORLD_EXTRA];
} terrain_view;

static GLuint gl_upload(const mu_image *image, int linear, int clamp)
{
    GLuint name = 0;
    glGenTextures(1, &name);
    glBindTexture(GL_TEXTURE_2D, name);
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
    GLint filter = linear ? GL_LINEAR : GL_NEAREST; /* loader argument 0x2601 / 0x2600 */
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, filter);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, filter);
    GLint wrap = clamp ? GL_CLAMP : GL_REPEAT;      /* 0x2900 / 0x2901 */
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, wrap);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, wrap);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, image->width, image->height, 0, GL_RGBA, GL_UNSIGNED_BYTE, image->rgba);
    return name;
}

static void gl_textures(terrain_view *v)
{
    for (int32_t i = 0; i < MU_WORLD_BITMAPS; ++i) {
        const mu_image *image = &v->map->bitmaps[i];
        v->names[i] = image->width > 0 ? gl_upload(image, v->map->bitmap_linear[i], 0) : 0;
    }
    for (int32_t i = 0; i < MU_WORLD_EXTRA; ++i) {
        const mu_image *image = &v->map->extra[i];
        v->extra_names[i] = image->width > 0 ? gl_upload(image, v->map->extra_linear[i], v->map->extra_clamp[i]) : 0;
    }
}

static void gl_release(terrain_view *v)
{
    for (int32_t i = 0; i < MU_WORLD_BITMAPS; ++i)
        if (v->names[i]) {
            glDeleteTextures(1, &v->names[i]);
            v->names[i] = 0;
        }
    for (int32_t i = 0; i < MU_WORLD_EXTRA; ++i)
        if (v->extra_names[i]) {
            glDeleteTextures(1, &v->extra_names[i]);
            v->extra_names[i] = 0;
        }
}

static void g_state(void *c, int32_t state, int32_t argument)
{
    (void)c;
    mu_meshdraw_state s;
    mu_world_state(state, argument, &s);
    if (s.blend) {
        glEnable(GL_BLEND);
        glBlendFunc((GLenum)s.src, (GLenum)s.dst);  /* the client's GL enums */
    } else {
        glDisable(GL_BLEND);
    }
    if (s.cull)
        glEnable(GL_CULL_FACE);
    else
        glDisable(GL_CULL_FACE);
    glDepthMask(s.depth_mask ? GL_TRUE : GL_FALSE);
    if (s.alpha_test)
        glEnable(GL_ALPHA_TEST);
    else
        glDisable(GL_ALPHA_TEST);
}

static void g_bind(void *c, int32_t texture)
{
    terrain_view *v = c;
    const int32_t i = texture - MU_TERRAIN_TEXTURE_TILE;
    GLuint name = i >= 0 && i < MU_WORLD_BITMAPS ? v->names[i] : 0;
    for (int32_t k = 0; !name && k < MU_WORLD_EXTRA; ++k)
        if (v->map->extra[k].width > 0 && v->map->extra_id[k] == texture)
            name = v->extra_names[k];
    if (name) {
        glEnable(GL_TEXTURE_2D);
        glBindTexture(GL_TEXTURE_2D, name);
    } else {
        glDisable(GL_TEXTURE_2D);
    }
}

static void g_begin(void *c, int32_t mode)
{
    (void)c;
    glBegin(mode == MU_TERRAIN_GL_QUADS ? GL_QUADS : GL_TRIANGLE_FAN);
}
static void g_end(void *c) { (void)c; glEnd(); }
static void g_tex(void *c, float s, float t) { (void)c; glTexCoord2f(s, t); }
static void g_c3(void *c, const float rgb[3]) { (void)c; glColor3fv(rgb); }
static void g_c4(void *c, float r, float g, float b, float a) { (void)c; glColor4f(r, g, b, a); }
static void g_v(void *c, const float xyz[3]) { (void)c; glVertex3fv(xyz); }

static void place_camera(terrain_view *v)
{
    v->camera.target[2] = mu_world_height_at(v->map, v->camera.target[0], v->camera.target[1]);
}

/* The NATIVE-TERRAIN-002 frame for the focus point: visible box (the client's
 * frustum, or a square sized by the camera distance), light copy and waves
 * over it, then the demo light sources. */
static void frame_setup(terrain_view *v, int32_t w, mu_terrain_frustum *frustum)
{
    memset(frustum, 0, sizeof *frustum);
    if (v->frustum) {
        float view[16], eye[3], rows[12];
        mu_camera_view(&v->camera, view);
        mu_camera_eye(&v->camera, eye);
        for (int i = 0; i < 3; ++i)
            for (int j = 0; j < 4; ++j)
                rows[4 * i + j] = view[4 * j + i];
        mu_world_client_frustum(v->map, rows, eye, v->camera.target, -48.5f, w, 3, v->camera.distance * 1.4f,
                                v->camera.fov_y, frustum);
    } else {
        int32_t radius = (int32_t)(v->camera.distance * 2.5f / 100.0f) + 24;
        int32_t cx = (int32_t)(v->camera.target[0] / 100.0f), cy = (int32_t)(v->camera.target[1] / 100.0f);
        int32_t x0 = cx - radius, y0 = cy - radius, x1 = cx + radius, y1 = cy + radius;
        frustum->x_min = x0 < 0 ? 0 : x0 & ~3;
        frustum->y_min = y0 < 0 ? 0 : y0 & ~3;
        frustum->x_max = x1 > 251 ? 251 : x1;
        frustum->y_max = y1 > 251 ? 251 : y1;
    }
    mu_world_frame_box(v->map, v->time, frustum->x_min, frustum->y_min, frustum->x_max, frustum->y_max);
    if (v->lights) {
        const float *t = v->camera.target;
        static const float warm[3] = {1.0f, 0.55f, 0.25f}, blue[3] = {0.2f, 0.35f, 1.0f}, white[3] = {1.0f, 1.0f, 1.0f};
        mu_world_add_light(v->map, t[0], t[1], white, 1);              /* character-scene highlight: (1,1,1), 1 */
        mu_world_add_light(v->map, t[0] + 300.0f, t[1] + 200.0f, warm, 4);
        mu_world_add_light(v->map, t[0] - 500.0f, t[1] - 300.0f, blue, 3);
    }
}

static void draw_gl(terrain_view *v, int32_t w, int32_t h, mu_terrain_tile_stats *stats)
{
    static const uint8_t background[4] = {0, 0, 0, 255};
    float view[16], projection[16];
    mu_camera_view(&v->camera, view);
    mu_camera_projection(&v->camera, (float)w / (float)h, projection);
    mu_gl_frame(w, h, background, view, projection);
    glEnable(GL_DEPTH_TEST);
    glFrontFace(GL_CCW);
    glPolygonMode(GL_FRONT_AND_BACK, v->wireframe ? GL_LINE : GL_FILL);
    mu_terrain_frustum frustum;
    frame_setup(v, w, &frustum);
    mu_terrain_sink sink = {v, g_state, g_bind, g_begin, g_tex, g_c3, g_c4, g_v, g_end};
    mu_terrain_scene scene;
    mu_world_scene(v->map, &scene);
    mu_terrain_tile_stats local;
    memset(&local, 0, sizeof local);
    if (v->frustum)
        mu_terrain_render(&scene, &frustum, 5, 0, mu_terrain_alpha_layers(v->map->world), &sink, &local);
    else
        mu_terrain_draw(&scene, frustum.x_min, frustum.y_min, frustum.x_max, frustum.y_max,
                        mu_terrain_alpha_layers(v->map->world), &sink, &local);
    if (v->decal) {
        static const float white[3] = {1.0f, 1.0f, 1.0f};
        g_state(v, MU_TERRAIN_STATE_ADDITIVE, 0);
        mu_terrain_decal(&scene, 0x7ef7, v->camera.target[0], v->camera.target[1], 2.0f, 2.0f, white, v->time * 0.05f,
                         1.0f, 5.0f, 1, 0, &sink);
    }
    if (stats)
        *stats = local;
}

static int render_soft(terrain_view *v, uint8_t *pixels)
{
    mu_raster raster;
    if (mu_raster_init(&raster, v->width, v->height))
        return 1;
    raster.front_ccw = 1;
    mu_camera_view(&v->camera, raster.view);
    mu_camera_projection(&v->camera, (float)v->width / (float)v->height, raster.projection);
    static const uint8_t background[4] = {0, 0, 0, 255};
    mu_raster_clear(&raster, background);
    mu_world_draw_stats stats;
    if (v->lights || v->frustum || v->decal) {
        mu_terrain_frustum frustum;
        frame_setup(v, v->width, &frustum);
        if (v->frustum)
            mu_world_draw_raster_view(v->map, &raster, &frustum, 5, 0, &stats);
        else
            mu_world_draw_raster(v->map, &raster, frustum.x_min, frustum.y_min, frustum.x_max, frustum.y_max, &stats);
        if (v->decal) {
            static const float white[3] = {1.0f, 1.0f, 1.0f};
            mu_world_decal_raster(v->map, &raster, 0x7ef7, v->camera.target[0], v->camera.target[1], 2.0f, 2.0f, white,
                                  v->time * 0.05f, 1.0f, 5.0f, 1, 0, MU_TERRAIN_STATE_ADDITIVE);
        }
    } else {
        mu_world_frame(v->map, v->time);
        mu_world_draw_raster(v->map, &raster, 0, 0, 251, 251, &stats);
    }
    memcpy(pixels, raster.color, (size_t)v->width * (size_t)v->height * 4);
    mu_raster_free(&raster);
    return 0;
}

static int render_gl(terrain_view *v, uint8_t *pixels)
{
    char error[256];
    if (mu_gl_headless_begin(v->width, v->height, error, sizeof error)) {
        fprintf(stderr, "headless GL: %s\n", error);
        return 1;
    }
    gl_textures(v);
    draw_gl(v, v->width, v->height, NULL);
    glFinish();
    mu_gl_read(v->width, v->height, pixels);
    fprintf(stderr, "GL renderer: %s\n", mu_gl_renderer());
    gl_release(v);
    mu_gl_headless_end();
    return 0;
}

static int headless(terrain_view *v)
{
    const size_t bytes = (size_t)v->width * (size_t)v->height * 4;
    uint8_t *pixels = malloc(bytes), *other = malloc(bytes);
    if (!pixels || !other)
        return 1;
    int gl = v->backend && !strcmp(v->backend, "gl");
    int status = gl ? render_gl(v, pixels) : render_soft(v, pixels);
    if (!status && v->out && mu_png_write(v->out, pixels, v->width, v->height))
        status = 1;
    char hash[65];
    mu_sha256_hex(pixels, bytes, hash);
    printf("{\"backend\": \"%s\", \"sha256\": \"%s\"", gl ? "gl" : "soft", hash);
    if (!status && v->compare) {
        status = gl ? render_soft(v, other) : render_gl(v, other);
        long differ = 0;
        double sum = 0.0;
        for (size_t i = 0; i < bytes; i += 4) {
            int worst = 0;
            for (int k = 0; k < 3; ++k) {
                int d = abs((int)pixels[i + (size_t)k] - (int)other[i + (size_t)k]);
                sum += d;
                if (d > worst)
                    worst = d;
            }
            differ += worst > 8;
        }
        printf(", \"pixels_over_8\": %ld, \"pixels\": %ld, \"mean_channel_difference\": %.4f", differ,
               (long)(bytes / 4), sum / (double)(bytes / 4 * 3));
    }
    printf("}\n");
    free(pixels);
    free(other);
    return status;
}

static int windowed(terrain_view *v)
{
    if (SDL_Init(SDL_INIT_VIDEO) != 0) {
        fprintf(stderr, "SDL_Init: %s\n", SDL_GetError());
        return 1;
    }
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION, 2);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION, 1);
    SDL_GL_SetAttribute(SDL_GL_DEPTH_SIZE, 24);
    SDL_GL_SetAttribute(SDL_GL_DOUBLEBUFFER, 1);
    SDL_Window *window = SDL_CreateWindow("mu-viewer terrain", SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED,
                                          v->width, v->height,
                                          SDL_WINDOW_OPENGL | SDL_WINDOW_RESIZABLE | SDL_WINDOW_ALLOW_HIGHDPI);
    SDL_GLContext context = window ? SDL_GL_CreateContext(window) : NULL;
    if (!context) {
        fprintf(stderr, "SDL: %s\n", SDL_GetError());
        return 1;
    }
    SDL_GL_SetSwapInterval(1);
    gl_textures(v);
    uint64_t frequency = SDL_GetPerformanceFrequency(), last = SDL_GetPerformanceCounter(), start = last;
    long frames = 0;
    int running = 1, dragging = 0;
    while (running) {
        SDL_Event e;
        while (SDL_PollEvent(&e)) {
            if (e.type == SDL_QUIT)
                running = 0;
            else if (e.type == SDL_MOUSEBUTTONDOWN)
                dragging = 1;
            else if (e.type == SDL_MOUSEBUTTONUP)
                dragging = 0;
            else if (e.type == SDL_MOUSEMOTION && dragging) {
                v->camera.yaw -= (float)e.motion.xrel * 0.3f;
                v->camera.pitch += (float)e.motion.yrel * 0.3f;
                if (v->camera.pitch < 5.0f) v->camera.pitch = 5.0f;
                if (v->camera.pitch > 89.0f) v->camera.pitch = 89.0f;
            } else if (e.type == SDL_MOUSEWHEEL) {
                v->camera.distance *= e.wheel.y > 0 ? 0.9f : 1.1f;
                if (v->camera.distance < 300.0f) v->camera.distance = 300.0f;
                if (v->camera.distance > 60000.0f) v->camera.distance = 60000.0f;
            } else if (e.type == SDL_KEYDOWN) {
                switch (e.key.keysym.sym) {
                case SDLK_ESCAPE: running = 0; break;
                case SDLK_SPACE: v->paused = !v->paused; break;
                case SDLK_g: v->wireframe = !v->wireframe; break;
                case SDLK_l: v->lights = !v->lights; break;
                case SDLK_f: v->frustum = !v->frustum; break;
                case SDLK_k: v->decal = !v->decal; break;
                case SDLK_4: v->map->detail = v->map->detail >= 4 ? 0 : 4; break;
                case SDLK_r:
                    v->camera.target[0] = v->camera.target[1] = 12800.0f;
                    v->camera.distance = 6000.0f;
                    v->camera.pitch = 40.0f;
                    break;
                case SDLK_o: {
                    int w, h;
                    SDL_GL_GetDrawableSize(window, &w, &h);
                    uint8_t *pixels = malloc((size_t)w * (size_t)h * 4);
                    if (pixels) {
                        mu_gl_read(w, h, pixels);
                        mu_png_write("mu-terrain-screenshot.png", pixels, w, h);
                        free(pixels);
                    }
                    break;
                }
                default: break;
                }
            }
        }
        uint64_t now = SDL_GetPerformanceCounter();
        float dt = (float)((double)(now - last) / (double)frequency);
        last = now;
        if (!v->paused)
            v->time += dt * 1000.0f;
        const Uint8 *keys = SDL_GetKeyboardState(NULL);
        float speed = v->camera.distance * 0.8f * dt;
        double yaw = (double)v->camera.yaw * 3.14159265358979323846 / 180.0;
        float fx = (float)-cos(yaw), fy = (float)-sin(yaw);   /* towards the view direction */
        float rx = -fy, ry = fx;
        if (keys[SDL_SCANCODE_W]) { v->camera.target[0] += fx * speed; v->camera.target[1] += fy * speed; }
        if (keys[SDL_SCANCODE_S]) { v->camera.target[0] -= fx * speed; v->camera.target[1] -= fy * speed; }
        if (keys[SDL_SCANCODE_D]) { v->camera.target[0] -= rx * speed; v->camera.target[1] -= ry * speed; }
        if (keys[SDL_SCANCODE_A]) { v->camera.target[0] += rx * speed; v->camera.target[1] += ry * speed; }
        if (keys[SDL_SCANCODE_Q]) v->camera.yaw += 60.0f * dt;
        if (keys[SDL_SCANCODE_E]) v->camera.yaw -= 60.0f * dt;
        for (int k = 0; k < 2; ++k) {
            if (v->camera.target[k] < 0.0f) v->camera.target[k] = 0.0f;
            if (v->camera.target[k] > 25500.0f) v->camera.target[k] = 25500.0f;
        }
        place_camera(v);
        int w, h;
        SDL_GL_GetDrawableSize(window, &w, &h);
        mu_terrain_tile_stats stats;
        draw_gl(v, w, h, &stats);
        SDL_GL_SwapWindow(window);
        ++frames;
        if (frames % 60 == 0) {
            char text[256];
            snprintf(text, sizeof text,
                     "World%d  faces %ld  alpha %ld  grass %ld  refused %ld  t=%.1fs  [L]ights %s [F]rustum %s "
                     "[K] decal %s [4] detail %d",
                     v->map->report.folder, stats.faces, stats.alpha_faces, stats.grass, stats.unsupported,
                     (double)v->time / 1000.0, v->lights ? "on" : "off", v->frustum ? "on" : "off",
                     v->decal ? "on" : "off", v->map->detail);
            SDL_SetWindowTitle(window, text);
        }
        if (v->seconds > 0.0f && (double)(now - start) / (double)frequency >= (double)v->seconds)
            running = 0;
    }
    double elapsed = (double)(SDL_GetPerformanceCounter() - start) / (double)frequency;
    fprintf(stderr, "%ld frames in %.2f s (%.1f fps)\n", frames, elapsed, (double)frames / elapsed);
    gl_release(v);
    SDL_GL_DeleteContext(context);
    SDL_DestroyWindow(window);
    SDL_Quit();
    return 0;
}

int mu_terrain_viewer_main(int argc, char **argv)
{
    static terrain_view v;
    memset(&v, 0, sizeof v);
    v.width = 1280;
    v.height = 800;
    v.camera.target[0] = v.camera.target[1] = 12800.0f;
    v.camera.yaw = -90.0f;
    v.camera.pitch = 40.0f;
    v.camera.distance = 6000.0f;
    v.camera.fov_y = 50.0f;
    v.camera.near_plane = 50.0f;
    v.camera.far_plane = 80000.0f;
    if (argc < 3) {
        fprintf(stderr, "usage: mu-viewer --terrain ROOT --world N [--headless --out PNG --backend gl|soft]\n");
        return 2;
    }
    v.root = argv[2];
    for (int i = 3; i < argc; ++i) {
        const char *k = argv[i], *val = i + 1 < argc ? argv[i + 1] : "";
        if (!strcmp(k, "--headless")) v.headless = 1;
        else if (!strcmp(k, "--lights")) v.lights = 1;
        else if (!strcmp(k, "--frustum")) v.frustum = 1;
        else if (!strcmp(k, "--decal")) v.decal = 1;
        else if (!strcmp(k, "--detail")) { v.detail = atoi(val); ++i; }
        else if (!strcmp(k, "--compare")) v.compare = 1;
        else if (!strcmp(k, "--world")) { v.world = atoi(val); ++i; }
        else if (!strcmp(k, "--out")) { v.out = val; ++i; }
        else if (!strcmp(k, "--backend")) { v.backend = val; ++i; }
        else if (!strcmp(k, "--width")) { v.width = atoi(val); ++i; }
        else if (!strcmp(k, "--height")) { v.height = atoi(val); ++i; }
        else if (!strcmp(k, "--seconds")) { v.seconds = strtof(val, NULL); ++i; }
        else if (!strcmp(k, "--time")) { v.time = strtof(val, NULL); ++i; }
        else if (!strcmp(k, "--yaw")) { v.camera.yaw = strtof(val, NULL); ++i; }
        else if (!strcmp(k, "--pitch")) { v.camera.pitch = strtof(val, NULL); ++i; }
        else if (!strcmp(k, "--distance")) { v.camera.distance = strtof(val, NULL); ++i; }
        else if (!strcmp(k, "--target")) {
            if (sscanf(val, "%f,%f", &v.camera.target[0], &v.camera.target[1]) != 2)
                return 2;
            ++i;
        } else {
            fprintf(stderr, "unknown option %s\n", k);
            return 2;
        }
    }
    char error[512];
    v.map = mu_world_load(v.root, v.world, 1, 1, error, sizeof error);
    if (!v.map) {
        fprintf(stderr, "%s\n", error);
        return 1;
    }
    v.map->detail = v.detail;
    mu_world_load_extra(v.map, v.root, 0x7ef7, "Effect/flare01.jpg", 1, 1);   /* decal texture, LINEAR + CLAMP */
    place_camera(&v);
    int status = v.headless ? headless(&v) : windowed(&v);
    mu_world_free(v.map);
    return status;
}
