/* RENDER-WORLDS-B: native ownership of code-created map placements. */
#include "../../reconstructed/objects/worlds_b.h"
#include "mu_objects.h"
#include "../../reconstructed/objects/world_warp.h"
#include <stdlib.h>
#include <string.h>

int mu_objects_worlds_b_records(mu_objects *o)
{
    mu_object_record added[3];
    int32_t n = 0;
    if (o->world == 2)
        n = mu_devias_records(added);
    else if (o->world == 3)
        n = mu_noria_records(added);
    else if (o->world == 57 || o->world == 58)
        n = mu_raklion_records(o->world, added);
    if (!n)
        return 0;
    mu_object_record *records = realloc(o->records, (size_t)(o->count + n) * sizeof *records);
    if (!records)
        return 1;
    o->records = records;
    for (int32_t k = 0; k < n; ++k) {
        int present = 0;
        for (int32_t j = 0; j < o->count; ++j)
            if (records[j].type == added[k].type &&
                memcmp(records[j].position, added[k].position, sizeof added[k].position) == 0)
                present = 1;
        /* Live exports with --keep-all already contain the code-created placements.
         */
        if (!present)
            records[o->count++] = added[k];
    }
    return 0;
}

const char *mu_objects_worlds_b_model(int32_t world, int32_t type)
{
    if (world == 2) {
        if (type == 422)
            return "Data/Npc/obj_donkey.bmd";
        if (type == 423)
            return "Data/Npc/obj_flag.bmd";
        if (type == 424)
            return "Data/Npc/warp01.bmd";
    }
    if (world == 3 && type == 424)
        return "Data/Npc/warp01.bmd";
    if (world == 57 || world == 58) {
        if (type == 424)
            return "Data/Npc/warp01.bmd";
        if (type == 427)
            return "Data/Npc/warp01.bmd";
    }
    return NULL;
}
