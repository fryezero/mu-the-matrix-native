#include "world_warp.h"

int32_t mu_noria_records(mu_object_record *r)
{
    mu_objects_record_init(r);
    r->type = 0x1a8;
    r->position[0] = 22300.0f;
    r->position[1] = 3000.0f;
    r->angle[2] = 10.0f;
    return 1;
}
