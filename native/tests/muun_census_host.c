/* Frozen-data appearance census. Outputs reviewed metadata, never decoded records. */
#include "../core/mu_muun_visual.h"
#include "../core/mu_data.h"
#include "../core/mu_objects.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
int main(int argc, char **argv)
{
    if (argc != 3) return 2;
    char path[2048], error[512];
    mu_data_table table = {0}, items = {0};
    if (!mu_objects_resolve(argv[1], "Data/Local/MuunRenderInfo.bmd", path, sizeof path) ||
        mu_data_load(path, NULL, &table) || table.result.status != MU_DATA_OK) return 2;
    if (!mu_objects_resolve(argv[1], "Data/Local/Item.bmd", path, sizeof path) ||
        mu_data_load(path, NULL, &items) || items.result.status != MU_DATA_OK) return 2;
    puts("appearance,model,slot,asset,loaded,meshes,actions,extra_draws,extra_refused,attachments,bone_refused,texture_missing,bone11,bone18,bone52");
    for (uint32_t k = 0; k < table.result.records; ++k) {
        const uint8_t *r = table.bytes + table.result.records_offset + (size_t)k * 612;
        int32_t id, item; memcpy(&id, r, 4); memcpy(&item, r + 4, 4);
        mu_item entry; memset(&entry, 0, sizeof entry);
        mu_item_model(&items, item + MU_ITEM_MODEL_BASE, &entry);
        mu_muun_visual *v = calloc(1, sizeof *v);
        if (!v) return 2;
        mu_mv_owner owner = {.key=77,.live=1};
        int loaded = !mu_muun_visual_open(v, argv[1], argv[2], id, &owner, 1, error, sizeof error);
        int valid[3] = {0}; const int bones[] = {11,18,52};
        for (int b=0;b<3;++b) valid[b] = loaded && bones[b] < v->bmd.bone_count &&
            !v->bmd.bones[bones[b]].dummy && !v->bmd.bones[bones[b]].unresolved;
        printf("%d,0x%x,%u,%s%s,%d,%d,%d,%d,%ld,%d,%ld,%d,%d,%d,%d\n", id,
            (unsigned)(item + MU_ITEM_MODEL_BASE), r[8], entry.folder, entry.file, loaded,
            v->bmd.mesh_count, v->bmd.action_count, v->mesh_count, v->refused_meshes,
            v->effects.count, v->refused_bones, v->textures.missing, valid[0],valid[1],valid[2]);
        mu_muun_visual_close(v); free(v);
    }
    mu_data_free(&items); mu_data_free(&table); return 0;
}
