/* rtsample <pid> <presented-counter-address> <out.jsonl> [options]: RENDER-TIME-002 live temporal sampler.
   Read-only (mach_vm_read_overwrite): it never writes, suspends or injects. It emits only numeric summaries in the
   RENDER-TIME-001 schema order (docs/research/client-render-time.md), never record bytes or addresses of objects.

   The post-draw point is mugl's presented-frame counter (C:\mutools\mugl-shm.txt "frames 0x...", incremented at the
   start of every wglSwapBuffers, after the scene's draw calls). On each change the sampler reads a bracket (WorldTime
   0x06fce370, logic-step counter 0x0bdc5eb0, rendered-frame counter 0x0bdc5ebc, the presented counter), the sample
   groups, then the bracket again. A read whose counters moved is torn and retried at the next post-draw edge.
   Frame k of the plan is the first untorn post-draw edge whose logic counter is at least arm + k.

   Options: --frames N (201) --every N (10) --go PATH (created after frame 0: the injector's arm signal)
            --preflight (print the scene/hero/neighbour line and exit) --timeout-ms N (20000 without an edge)
            --shot-window ID --shot-dir DIR --shot-frames a,b,c (screencapture -l ID after those samples)

   Addresses (finding docs): world 0x01cf15fc; hero CHARACTER [0x0a39d754], its OBJECT at +0x3254;
   camera eye 0x0bdc5ab4, angle 0x0bdc58f0, FOV 0x01cf1634; static objects in 256 sector lists at 0x0bdb61f0
   (head +4, next +0x354, 0x3d8 bytes); particles std::list at 0x0a3a9adc (head node +0, size +4; node next +0,
   shared record pointer +8; 0xb4-byte records); effects 200 x 0x3d8 at 0x0a4ca430; joints 500 x 0xa64 at
   0x0a4fa4f0; boids 40 x 0x3d8 at 0x0bdb71f0; fish 10 x 0x3d8 at 0x0bdc0bb0; weather 200 x 0xb4 at 0x0a3a0e28;
   primary/frame light grids 0x0bab5430 / 0x0b9f5430. */
#include <mach/mach.h>
#include <mach/mach_time.h>
#include <mach/mach_vm.h>
#include <spawn.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

extern char **environ;
static task_t t;
static int rd(uint32_t a, void *out, size_t n)
{
    mach_vm_size_t got = 0;
    return mach_vm_read_overwrite(t, a, n, (mach_vm_address_t)out, &got) == KERN_SUCCESS && got == n ? 0 : -1;
}
static uint32_t rd32(uint32_t a) { uint32_t v = 0; return rd(a, &v, 4) ? 0 : v; }
static float f32(const uint8_t *p, size_t o) { float f; memcpy(&f, p + o, 4); return f; }
static int32_t i32(const uint8_t *p, size_t o) { int32_t v; memcpy(&v, p + o, 4); return v; }
static double now_us(void)
{
    static mach_timebase_info_data_t tb;
    if (!tb.denom) mach_timebase_info(&tb);
    return (double)mach_absolute_time() * tb.numer / tb.denom / 1000.0;
}

enum { OBJ = 0x3d8, OBJ_READ = 0x358, SECTORS = 0x0bdb61f0, HERO = 0x0a39d754, HERO_OBJECT = 0x3254,
       WORLD = 0x01cf15fc, WORLD_TIME = 0x06fce370, LOGIC = 0x0bdc5eb0, CFRAME = 0x0bdc5ebc,
       EYE = 0x0bdc5ab4, ANGLE = 0x0bdc58f0, FOV = 0x01cf1634, PARTICLES = 0x0a3a9adc, PT = 0xb4,
       EFFECTS = 0x0a4ca430, NEFFECTS = 200, JOINTS = 0x0a4fa4f0, NJOINTS = 500, JOINT = 0xa64,
       BOIDS = 0x0bdb71f0, NBOIDS = 40, FISH = 0x0bdc0bb0, NFISH = 10, LEAVES = 0x0a3a0e28, NLEAVES = 200,
       PRIMARY = 0x0bab5430, FRAMELIGHT = 0x0b9f5430, CELLS = 256 * 256, CHARS = 0x01d1dbbc, CHAR = 0x3670 };

typedef struct { uint32_t presented, logic, cframe; float wt; double us; } bracket;
static uint32_t presented_addr;
static int read_bracket(bracket *b)
{
    b->us = now_us();
    return rd(presented_addr, &b->presented, 4) || rd(LOGIC, &b->logic, 4) || rd(CFRAME, &b->cframe, 4) ||
           rd(WORLD_TIME, &b->wt, 4);
}

/* Object addresses from the sector lists, read in merged ranges per sample. */
static uint32_t *objs; static int nobjs; static uint8_t sector_table[256 * 16];
typedef struct { uint32_t lo, hi; uint8_t *buf; } range;
static range *ranges; static int nranges;
static int cmp_u32(const void *a, const void *b) { uint32_t x = *(const uint32_t *)a, y = *(const uint32_t *)b; return x < y ? -1 : x > y; }
static int walk_objects(void)
{
    if (rd(SECTORS, sector_table, sizeof sector_table)) return -1;
    free(objs); objs = NULL; nobjs = 0; int cap = 0;
    uint8_t o[OBJ_READ];
    for (int s = 0; s < 256; ++s) {
        uint32_t p; memcpy(&p, sector_table + 16 * s + 4, 4);
        for (int guard = 0; p && guard < 100000; ++guard) {
            if (rd(p, o, sizeof o)) return -1;
            if (nobjs == cap) { cap = cap ? cap * 2 : 4096; objs = realloc(objs, (size_t)cap * 4); }
            objs[nobjs++] = p;
            memcpy(&p, o + 0x354, 4);
        }
    }
    uint32_t *sorted = malloc((size_t)(nobjs ? nobjs : 1) * 4);
    memcpy(sorted, objs, (size_t)nobjs * 4);
    qsort(sorted, (size_t)nobjs, 4, cmp_u32);
    for (int i = 0; i < nranges; ++i) free(ranges[i].buf);
    free(ranges); ranges = calloc((size_t)(nobjs ? nobjs : 1), sizeof *ranges); nranges = 0;
    for (int i = 0; i < nobjs; ++i) {
        uint32_t lo = sorted[i], hi = sorted[i] + OBJ_READ;
        if (nranges && lo <= ranges[nranges - 1].hi + 0x4000) { if (hi > ranges[nranges - 1].hi) ranges[nranges - 1].hi = hi; }
        else ranges[nranges++] = (range){lo, hi, NULL};
    }
    for (int i = 0; i < nranges; ++i) ranges[i].buf = malloc(ranges[i].hi - ranges[i].lo);
    free(sorted);
    return 0;
}
static const uint8_t *object_bytes(uint32_t a)
{
    int lo = 0, hi = nranges - 1;
    while (lo <= hi) {
        int m = (lo + hi) / 2;
        if (a < ranges[m].lo) hi = m - 1;
        else if (a + OBJ_READ > ranges[m].hi) lo = m + 1;
        else return ranges[m].buf + (a - ranges[m].lo);
    }
    return NULL;
}

static void values(FILE *f, const char *name, const double *v, int n)
{
    fprintf(f, ",\"%s\":[", name);
    for (int i = 0; i < n; ++i) fprintf(f, "%s%.12g", i ? "," : "", v[i]);
    fprintf(f, "]");
}

static uint8_t big[NJOINTS * JOINT];
static float grid[CELLS * 3];
/* One sample of every group; returns 0, or -1 when a fixed read failed. */
static int sample(FILE *f, int frame, int attempt, const bracket *pre)
{
    uint8_t chk[256 * 16];
    if (rd(SECTORS, chk, sizeof chk)) return -1;
    int rewalked = 0;
    if (memcmp(chk, sector_table, sizeof chk)) { if (walk_objects()) return -1; rewalked = 1; }
    int32_t world = -1; rd(WORLD, &world, 4);
    double camera[9] = {0}, objects[19] = {0}, particles[10] = {0}, environment[8] = {0}, lights[6] = {0};
    uint8_t ho[0x180];
    uint32_t hero = rd32(HERO);
    if (!hero || rd(hero + HERO_OBJECT, ho, sizeof ho)) return -1;
    float eye[3], angle[3], fov;
    if (rd(EYE, eye, 12) || rd(ANGLE, angle, 12) || rd(FOV, &fov, 4)) return -1;
    double c[] = {f32(ho, 0x158), f32(ho, 0x15c), f32(ho, 0x160), f32(ho, 0xd0), eye[0], eye[1], eye[2], fov, angle[0]};
    memcpy(camera, c, sizeof c);
    for (int i = 0; i < nranges; ++i)
        if (rd(ranges[i].lo, ranges[i].buf, ranges[i].hi - ranges[i].lo)) return -1;
    static const int offsets[16] = {0xd0, 0xd4, 0xdc, 0xac, 0xb0, 0xa8, 0x158, 0x15c, 0x160, 0x164, 0x168, 0x16c,
                                    0xec, 0xf0, 0xf4, 0xb4};
    for (int i = 0; i < nobjs; ++i) {
        const uint8_t *o = object_bytes(objs[i]);
        if (!o || !o[0]) continue;
        uint16_t action; memcpy(&action, o + 0x2a, 2);
        objects[0]++; objects[17] += o[0x0b]; objects[18] += action;
        for (int k = 0; k < 16; ++k) objects[k + 1] += f32(o, (size_t)offsets[k]);
    }
    /* particles: walk the list; the walked count is checked against the list size */
    uint32_t head = rd32(PARTICLES), size = rd32(PARTICLES + 4), walked = 0, node = head ? rd32(head) : 0;
    uint8_t p[PT];
    for (; head && node && node != head && walked <= size + 4; ++walked) {
        uint32_t rec = rd32(node + 8);
        if (rec && !rd(rec, p, sizeof p) && p[8]) {
            particles[0]++;
            particles[1] += f32(p, 0x20); particles[2] += f32(p, 0x24); particles[3] += f32(p, 0x28);
            particles[4] += f32(p, 0x60); particles[5] += f32(p, 0x44); particles[6] += f32(p, 0x18);
            particles[7] += i32(p, 0x48); particles[8] += i32(p, 0x0c);
        }
        node = rd32(node);
    }
    if (rd(EFFECTS, big, NEFFECTS * OBJ)) return -1;
    for (int i = 0; i < NEFFECTS; ++i) particles[9] += big[i * OBJ] != 0;
    for (int pass = 0; pass < 2; ++pass) {
        int n = pass ? NFISH : NBOIDS;
        if (rd(pass ? FISH : BOIDS, big, (size_t)n * OBJ)) return -1;
        for (int i = 0; i < n; ++i) {
            const uint8_t *o = big + (size_t)i * OBJ;
            if (!o[0]) continue;
            environment[0]++;
            environment[1] += f32(o, 0x158); environment[2] += f32(o, 0x15c); environment[3] += f32(o, 0x160);
            environment[4] += f32(o, 0xd0); environment[5] += f32(o, 0xdc);
        }
    }
    if (rd(LEAVES, big, NLEAVES * PT)) return -1;
    for (int i = 0; i < NLEAVES; ++i)
        if (big[i * PT + 8]) { environment[6]++; environment[7] += f32(big, (size_t)i * PT + 0x60); }
    for (int g = 0; g < 2; ++g) {
        if (rd(g ? FRAMELIGHT : PRIMARY, grid, sizeof grid)) return -1;
        for (int i = 0; i < 3 * CELLS; ++i) lights[3 * g + i % 3] += grid[i] / (double)CELLS;
    }
    if (rd(JOINTS, big, sizeof big)) return -1;
    int joints = 0;
    for (int i = 0; i < NJOINTS; ++i) joints += big[(size_t)i * JOINT] != 0;
    bracket post;
    if (read_bracket(&post)) return -1;
    fprintf(f, "{\"kind\":\"sample\",\"frame\":%d,\"attempt\":%d,\"world\":%d,\"objects_rewalked\":%d", frame, attempt, world, rewalked);
    fprintf(f, ",\"pre\":{\"presented\":%u,\"logic\":%u,\"cframe\":%u,\"world_time\":%.9g,\"host_us\":%.1f}",
            pre->presented, pre->logic, pre->cframe, pre->wt, pre->us);
    fprintf(f, ",\"post\":{\"presented\":%u,\"logic\":%u,\"cframe\":%u,\"world_time\":%.9g,\"host_us\":%.1f}",
            post.presented, post.logic, post.cframe, post.wt, post.us);
    values(f, "camera", camera, 9);
    values(f, "objects", objects, 19);
    values(f, "particles", particles, 10);
    values(f, "environment", environment, 8);
    values(f, "lights", lights, 6);
    fprintf(f, ",\"joints\":%d,\"particle_list\":{\"size\":%u,\"walked\":%u}}\n", joints, size, walked);
    fflush(f);
    return post.presented != pre->presented || post.logic != pre->logic || post.cframe != pre->cframe ? 1 : 0;
}

/* Scene, hero tile and the distance of every other live character to the hero (no names, no records). */
static void preflight(FILE *f)
{
    int32_t world = -1; rd(WORLD, &world, 4);
    uint32_t hero = rd32(HERO);
    uint8_t ho[0x180] = {0};
    if (hero) rd(hero + HERO_OBJECT, ho, sizeof ho);
    float hx = f32(ho, 0x158), hy = f32(ho, 0x15c);
    bracket b; read_bracket(&b);
    float eye[3] = {0}, angle[3] = {0}, fov = 0; rd(EYE, eye, 12); rd(ANGLE, angle, 12); rd(FOV, &fov, 4);
    fprintf(f, "{\"kind\":\"preflight\",\"world\":%d,\"hero_live\":%d,\"hero\":[%.3f,%.3f,%.3f],\"tile\":[%d,%d]",
            world, ho[0], hx, hy, f32(ho, 0x160), (int)(hx / 100), (int)(hy / 100));
    fprintf(f, ",\"hero_frame\":%.4f,\"hero_action\":%u,\"eye\":[%.3f,%.3f,%.3f],\"angle\":[%.4f,%.4f,%.4f],\"fov\":%.4f",
            f32(ho, 0xd0), (unsigned)(ho[0x2a] | ho[0x2b] << 8), eye[0], eye[1], eye[2], angle[0], angle[1], angle[2], fov);
    fprintf(f, ",\"world_time\":%.9g,\"logic\":%u,\"cframe\":%u,\"presented\":%u,\"objects\":%d,\"ranges\":%d,\"others\":[",
            b.wt, b.logic, b.cframe, b.presented, nobjs, nranges);
    uint32_t manager = rd32(CHARS), table = manager ? rd32(manager + 8) : 0;
    int first = 1;
    uint8_t co[0x180];
    for (uint32_t i = 0; table && i < 400; ++i) {
        uint32_t base = table + i * CHAR;
        if (base == hero || rd(base + HERO_OBJECT, co, sizeof co) || !co[0]) continue;
        float dx = f32(co, 0x158) - hx, dy = f32(co, 0x15c) - hy;
        fprintf(f, "%s%.1f", first ? "" : ",", __builtin_sqrtf(dx * dx + dy * dy));
        first = 0;
    }
    fprintf(f, "]}\n");
    fflush(f);
}

static void shot(const char *window, const char *dir, int frame)
{
    char path[4096]; snprintf(path, sizeof path, "%s/frame-%03d.png", dir, frame);
    char *argv[] = {"/usr/sbin/screencapture", "-x", "-o", "-l", (char *)window, path, NULL};
    pid_t pid;
    posix_spawn(&pid, argv[0], NULL, NULL, argv, environ);   /* reaped at exit; never blocks a sample */
}

int main(int c, char **v)
{
    if (c < 4) { fprintf(stderr, "usage: rtsample pid presented-address out.jsonl [options]\n"); return 2; }
    int frames = 201, every = 10, only_preflight = 0, timeout_ms = 20000;
    const char *go = NULL, *window = NULL, *shot_dir = NULL, *shot_frames = "";
    for (int i = 4; i < c; ++i) {
        if (!strcmp(v[i], "--preflight")) only_preflight = 1;
        else if (i + 1 < c && !strcmp(v[i], "--frames")) frames = atoi(v[++i]);
        else if (i + 1 < c && !strcmp(v[i], "--every")) every = atoi(v[++i]);
        else if (i + 1 < c && !strcmp(v[i], "--go")) go = v[++i];
        else if (i + 1 < c && !strcmp(v[i], "--timeout-ms")) timeout_ms = atoi(v[++i]);
        else if (i + 1 < c && !strcmp(v[i], "--shot-window")) window = v[++i];
        else if (i + 1 < c && !strcmp(v[i], "--shot-dir")) shot_dir = v[++i];
        else if (i + 1 < c && !strcmp(v[i], "--shot-frames")) shot_frames = v[++i];
        else { fprintf(stderr, "bad option %s\n", v[i]); return 2; }
    }
    if (frames < 21 || frames > 10001 || every < 1 || every > 10000) { fprintf(stderr, "bad plan\n"); return 2; }
    if (task_for_pid(mach_task_self(), atoi(v[1]), &t)) { fprintf(stderr, "task_for_pid failed\n"); return 1; }
    presented_addr = (uint32_t)strtoul(v[2], NULL, 16);
    FILE *f = fopen(v[3], "w");
    if (!f) return 1;
    if (walk_objects()) { fprintf(stderr, "object lists unreadable\n"); return 1; }
    preflight(f);
    if (only_preflight) { fclose(f); return 0; }
    /* frames 0, every, 2 every, ..., and the last frame (render_time.schedule) */
    int targets[1002], ntargets = 0;
    for (int k = 0; k < frames; k += every) targets[ntargets++] = k;
    if (targets[ntargets - 1] != frames - 1) targets[ntargets++] = frames - 1;
    bracket b, pre;
    if (read_bracket(&b)) { fprintf(stderr, "bracket unreadable\n"); return 1; }
    uint32_t last = b.presented, arm = 0, edges = 0, torn = 0;
    double last_edge = now_us();
    int next = 0, attempt = 0;
    while (next < ntargets) {
        if (read_bracket(&pre)) { fprintf(stderr, "bracket unreadable\n"); return 1; }
        if (pre.presented == last) {
            if (now_us() - last_edge > timeout_ms * 1000.0) { fprintf(stderr, "no post-draw edge for %d ms\n", timeout_ms); return 1; }
            usleep(100);
            continue;
        }
        if (pre.presented != last + 1 && edges) fprintf(f, "{\"kind\":\"skipped_edges\",\"from\":%u,\"to\":%u}\n", last, pre.presented);
        last = pre.presented; last_edge = pre.us; ++edges;
        if (next == 0) arm = pre.logic;
        if (pre.logic - arm < (uint32_t)targets[next]) continue;
        ++attempt;
        int r = sample(f, targets[next], attempt, &pre);
        if (r < 0) { fprintf(stderr, "sample read failed\n"); return 1; }
        if (r) { ++torn; continue; }
        if (next == 0 && go) {
            FILE *g = fopen(go, "w");
            if (g) { fprintf(g, "%u\n", arm); fclose(g); }
            bracket a; read_bracket(&a);
            fprintf(f, "{\"kind\":\"arm\",\"logic\":%u,\"cframe\":%u,\"presented\":%u,\"world_time\":%.9g,\"host_us\":%.1f}\n",
                    a.logic, a.cframe, a.presented, a.wt, a.us);
        }
        if (window && shot_dir) {
            char key[16]; snprintf(key, sizeof key, ",%d,", targets[next]);
            char list[1024]; snprintf(list, sizeof list, ",%s,", shot_frames);
            if (strstr(list, key)) shot(window, shot_dir, targets[next]);
        }
        ++next; attempt = 0;
    }
    fprintf(f, "{\"kind\":\"end\",\"edges\":%u,\"torn\":%u,\"arm_logic\":%u}\n", edges, torn, arm);
    fclose(f);
    return 0;
}
