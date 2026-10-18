/* Draw-class and GPU diagnostics (v7.4). Included by mugl.c; active only through mode-file tokens and written only
   to the private stats log. None of them changes what is drawn.
     "+time"    also splits mugl's batched draws and the game's own glDrawArrays/glDrawElements by class: terrain
                faces, mesh-draw loop, effect sprite quads, grass quads, other glBegin blocks, game array draws.
     "+finish"  calls glFinish before wglSwapBuffers and times it: the GPU work still queued when the frame ends.
     "+samples" wraps each class run in a GL_SAMPLES_PASSED occlusion query: fragments that pass the depth test per
                class (fill demand; blended fragments count once per layer). Results are read at the swap. */
enum { DC_TERRAIN, DC_MESH, DC_SPRITE, DC_GRASS, DC_BEGIN, DC_ARRAYS, DC_N };
static const char *const dc_names[DC_N] = {"terrain", "mesh", "sprite", "grass", "begin", "gamearrays"};
static int batch_cls = DC_BEGIN;
static long long dc_ticks[DC_N], dc_verts[DC_N]; static long dc_draws[DC_N];
static int finish_mode, samples_mode; static long long finish_ticks; static long finish_n;
static int dc_of(void *ret)
{
    unsigned a = (unsigned)(size_t)ret;
    if (a == 0x016cfab3 || a == 0x016cfb53) return DC_TERRAIN;
    if (a == 0x012ba899) return DC_MESH;
    if (a == 0x0184c914 || a == 0x0184c2bc) return DC_SPRITE;
    if (a == 0x016d16bf) return DC_GRASS;
    return DC_BEGIN;
}
/* occlusion queries */
typedef void (WINAPI *PFNgenq)(GLsizei, GLuint *);
typedef void (WINAPI *PFNbegq)(GLenum, GLuint);
typedef void (WINAPI *PFNendq)(GLenum);
typedef void (WINAPI *PFNgqo)(GLuint, GLenum, GLuint *);
static PFNgenq dq_gen; static PFNbegq dq_begin; static PFNendq dq_end; static PFNgqo dq_get; static int dq_fail;
#define DQ_MAX 8192
static GLuint dq_ids[DQ_MAX]; static unsigned char dq_cls[DQ_MAX]; static int dq_n, dq_open = -1, dq_have;
static unsigned long long dc_samples[DC_N];
static int dq_init(void)
{
    if (dq_fail) return 0;
    if (dq_have) return 1;
    dq_gen = (PFNgenq)R(wglGetProcAddress, PFNgpa)("glGenQueriesARB"); dq_begin = (PFNbegq)R(wglGetProcAddress, PFNgpa)("glBeginQueryARB");
    dq_end = (PFNendq)R(wglGetProcAddress, PFNgpa)("glEndQueryARB"); dq_get = (PFNgqo)R(wglGetProcAddress, PFNgpa)("glGetQueryObjectuivARB");
    if (!dq_gen || !dq_begin || !dq_end || !dq_get) { dq_fail = 1; if (st_file) fprintf(st_file, "samples: no occlusion queries\n"); return 0; }
    dq_gen(DQ_MAX, dq_ids); dq_have = 1;
    return 1;
}
static void dq_switch(int cls)
{
    if (!samples_mode || passthrough || dq_open == cls || !dq_init()) return;
    if (dq_open >= 0) dq_end(0x8914 /* GL_SAMPLES_PASSED */);
    dq_open = -1;
    if (dq_n >= DQ_MAX) return;
    dq_begin(0x8914, dq_ids[dq_n]); dq_cls[dq_n++] = (unsigned char)cls; dq_open = cls;
}
static void dq_frame(void)
{
    if (dq_open >= 0) { dq_end(0x8914); dq_open = -1; }
    for (int i = 0; i < dq_n; i++) { GLuint r = 0; dq_get(dq_ids[i], 0x8866 /* GL_QUERY_RESULT */, &r); dc_samples[dq_cls[i]] += r; }
    dq_n = 0;
}
/* Account one draw of class cls taking t ticks (time mode only). */
static void dc_add(int cls, long long t, int verts) { dc_ticks[cls] += t; dc_draws[cls]++; dc_verts[cls] += verts; }
static void dc_stats(FILE *f, long frames)
{
    if (!frames || !qpf.QuadPart) return;
    if (time_mode) {
        fprintf(f, "  draw classes:");
        for (int k = 0; k < DC_N; k++) if (dc_draws[k])
            fprintf(f, " %s=%.2fms(%ld draws, %lld v)", dc_names[k], dc_ticks[k] * 1000.0 / qpf.QuadPart / frames, dc_draws[k] / frames, dc_verts[k] / frames);
        fprintf(f, "\n");
    }
    if (finish_mode && finish_n) fprintf(f, "  finish=%.2fms\n", finish_ticks * 1000.0 / qpf.QuadPart / finish_n);
    if (samples_mode) {
        fprintf(f, "  samples/frame (k):");
        for (int k = 0; k < DC_N; k++) if (dc_samples[k]) fprintf(f, " %s=%llu", dc_names[k], dc_samples[k] / 1000 / frames);
        fprintf(f, "\n");
    }
    memset(dc_ticks, 0, sizeof dc_ticks); memset(dc_verts, 0, sizeof dc_verts); memset(dc_draws, 0, sizeof dc_draws);
    memset(dc_samples, 0, sizeof dc_samples); finish_ticks = 0; finish_n = 0;
}
static void dc_finish(void)
{
    if (!finish_mode) return;
    LARGE_INTEGER a, b; QueryPerformanceCounter(&a); R(glFinish, PFN0)(); QueryPerformanceCounter(&b);
    finish_ticks += b.QuadPart - a.QuadPart; finish_n++;
}
/* The game's own array draws (effect VBOs, UI): pass-through like the generated stub, plus class accounting. */
static int dc_idx_drawarrays = -1;
typedef void (WINAPI *PFNdarr)(GLenum, GLint, GLsizei);
void WINAPI mugl_glDrawArrays(GLenum m, GLint first, GLsizei n)
{
    if (dc_idx_drawarrays < 0)
        for (int i = 0; i < (int)(sizeof mugl_names / sizeof mugl_names[0]); i++) if (!strcmp(mugl_names[i], "glDrawArrays")) { dc_idx_drawarrays = i; break; }
    if (mugl_busy) mugl_sync_from(dc_idx_drawarrays);
    if (!passthrough) dq_switch(DC_ARRAYS);
    if (time_mode) { LARGE_INTEGER a, b; QueryPerformanceCounter(&a); R(glDrawArrays, PFNdarr)(m, first, n); QueryPerformanceCounter(&b); dc_add(DC_ARRAYS, b.QuadPart - a.QuadPart, n); }
    else R(glDrawArrays, PFNdarr)(m, first, n);
}
/* "+cull" (diagnostic): for every batch, count the vertices of batches that lie entirely outside one clip plane
   (exact per-vertex outcodes) and of those that a cheap test on the 8 corners of the batch's bounding box rejects.
   Reads the matrices with glGetFloatv per batch, so it is slow; it only estimates what culling could save. */
static int cull_mode; static long long cu_verts[DC_N], cu_out[DC_N], cu_box[DC_N]; static long cu_bout[DC_N], cu_bbox[DC_N], cu_batches[DC_N];
/* v7.6: per-triangle potential of visible GL_TRIANGLES batches: vertices of triangles entirely outside one x/y/w plane,
   of 16-triangle chunks whose bounding box is, and of back-facing triangles while GL_CULL_FACE culls them (all w > 0). */
typedef GLboolean (WINAPI *PFNcuis)(GLenum); typedef void (WINAPI *PFNcugi)(GLenum, GLint *);
static long long cu_tri_out[DC_N], cu_chunk_out[DC_N], cu_back[DC_N], cu_cullon[DC_N];
static unsigned cu_code(const double *m, double x, double y, double z)
{
    double c[4]; for (int r = 0; r < 4; r++) c[r] = m[r] * x + m[4 + r] * y + m[8 + r] * z + m[12 + r];
    return (c[0] > c[3]) | (c[0] < -c[3]) << 1 | (c[1] > c[3]) << 2 | (c[1] < -c[3]) << 3 | (c[2] > c[3]) << 4 | (c[2] < -c[3]) << 5;
}
static void cull_diag(const Vtx *v, int n, int cls)
{
    float mv[16], pr[16]; double m[16];
    R(glGetFloatv, PFNget)(GL_MODELVIEW_MATRIX, mv); R(glGetFloatv, PFNget)(GL_PROJECTION_MATRIX, pr);
    for (int c = 0; c < 4; c++) for (int r = 0; r < 4; r++) { double s = 0; for (int k = 0; k < 4; k++) s += (double)pr[k * 4 + r] * mv[c * 4 + k]; m[c * 4 + r] = s; }
    unsigned all = 63; float lo[3] = {1e30f, 1e30f, 1e30f}, hi[3] = {-1e30f, -1e30f, -1e30f};
    for (int i = 0; i < n; i++) {
        all &= cu_code(m, v[i].v[0], v[i].v[1], v[i].v[2]);
        for (int k = 0; k < 3; k++) { if (v[i].v[k] < lo[k]) lo[k] = v[i].v[k]; if (v[i].v[k] > hi[k]) hi[k] = v[i].v[k]; }
    }
    unsigned box = 63;
    for (int k = 0; k < 8; k++) box &= cu_code(m, k & 1 ? hi[0] : lo[0], k & 2 ? hi[1] : lo[1], k & 4 ? hi[2] : lo[2]);
    if (!all && batch_mode == GL_TRIANGLES) {
        GLint cf = 0, cm = GL_BACK, ff = GL_CCW;
        cf = R(glIsEnabled, PFNcuis)(GL_CULL_FACE);
        R(glGetIntegerv, PFNcugi)(GL_CULL_FACE_MODE, &cm); R(glGetIntegerv, PFNcugi)(GL_FRONT_FACE, &ff);
        if (cf) cu_cullon[cls] += n;
        for (int t = 0; t + 2 < n; t += 3) {
            double c[3][4]; unsigned oc = 15;
            for (int j = 0; j < 3; j++) {
                const float *p = v[t + j].v;
                for (int r = 0; r < 4; r++) c[j][r] = m[r] * p[0] + m[4 + r] * p[1] + m[8 + r] * p[2] + m[12 + r];
                oc &= (c[j][0] > c[j][3]) | (c[j][0] < -c[j][3]) << 1 | (c[j][1] > c[j][3]) << 2 | (c[j][1] < -c[j][3]) << 3;
            }
            if (oc) { cu_tri_out[cls] += 3; continue; }
            if (cf && c[0][3] > 0 && c[1][3] > 0 && c[2][3] > 0) {
                double ax = c[0][0] / c[0][3], ay = c[0][1] / c[0][3], bx = c[1][0] / c[1][3], by = c[1][1] / c[1][3], qx = c[2][0] / c[2][3], qy = c[2][1] / c[2][3];
                double area = (bx - ax) * (qy - ay) - (qx - ax) * (by - ay);
                int front = ff == GL_CCW ? area > 0 : area < 0;
                if (cm == GL_FRONT_AND_BACK || (cm == GL_BACK && !front && area != 0) || (cm == GL_FRONT && front)) cu_back[cls] += 3;
            }
        }
        for (int t = 0; t + 2 < n; t += 48) {
            int e = t + 48 < n ? t + 48 : n - n % 3; float l[3] = {1e30f, 1e30f, 1e30f}, h[3] = {-1e30f, -1e30f, -1e30f};
            for (int i = t; i < e; i++) for (int k = 0; k < 3; k++) { if (v[i].v[k] < l[k]) l[k] = v[i].v[k]; if (v[i].v[k] > h[k]) h[k] = v[i].v[k]; }
            unsigned cb = 15; for (int k = 0; k < 8; k++) cb &= cu_code(m, k & 1 ? h[0] : l[0], k & 2 ? h[1] : l[1], k & 4 ? h[2] : l[2]) & 15;
            if (cb) cu_chunk_out[cls] += e - t;
        }
    }
    cu_batches[cls]++; cu_verts[cls] += n;
    if (all) { cu_bout[cls]++; cu_out[cls] += n; }
    if (box) { cu_bbox[cls]++; cu_box[cls] += n; }
}
static void cull_stats(FILE *f, long frames)
{
    if (!cull_mode || !frames) return;
    fprintf(f, "  cull potential/frame:");
    for (int k = 0; k < DC_N; k++) if (cu_batches[k])
        fprintf(f, " %s=%ld/%ld batches %lld/%lld v (box %ld, %lld v)", dc_names[k], cu_bout[k] / frames, cu_batches[k] / frames, cu_out[k] / frames, cu_verts[k] / frames,
                cu_bbox[k] / frames, cu_box[k] / frames);
    fprintf(f, "\n  per-triangle potential/frame (visible triangle batches):");
    for (int k = 0; k < DC_N; k++) if (cu_batches[k])
        fprintf(f, " %s=tri-out %lld chunk-out %lld back %lld (cull-on %lld v)", dc_names[k], cu_tri_out[k] / frames, cu_chunk_out[k] / frames, cu_back[k] / frames, cu_cullon[k] / frames);
    fprintf(f, "\n");
    memset(cu_tri_out, 0, sizeof cu_tri_out); memset(cu_chunk_out, 0, sizeof cu_chunk_out); memset(cu_back, 0, sizeof cu_back); memset(cu_cullon, 0, sizeof cu_cullon);
    memset(cu_verts, 0, sizeof cu_verts); memset(cu_out, 0, sizeof cu_out); memset(cu_box, 0, sizeof cu_box);
    memset(cu_bout, 0, sizeof cu_bout); memset(cu_bbox, 0, sizeof cu_bbox); memset(cu_batches, 0, sizeof cu_batches);
}
