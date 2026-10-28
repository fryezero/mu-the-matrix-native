#ifndef MU_PERF_MESH_H
#define MU_PERF_MESH_H
#include "mu_meshdraw.h"
/* Model-owned topology proof. Mutable transforms, lighting, textures and draw
 * state are never cached. Every hit compares all current triangle bytes and
 * all bounds used by the validator. A changed input requires a fresh proof. */
typedef struct mu_perf_mesh_cache mu_perf_mesh_cache;
mu_perf_mesh_cache *mu_perf_mesh_new(int32_t meshes);
void mu_perf_mesh_free(mu_perf_mesh_cache *cache);
int mu_perf_mesh_regular(mu_perf_mesh_cache *cache, int32_t index, const mu_meshdraw_mesh *mesh);
#endif
