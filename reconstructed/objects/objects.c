#include "objects.h"

#include <stdio.h>
#include <string.h>

int32_t mu_objects_record_size(uint8_t version)
{
    int32_t size = 2 + 12 + 12 + 4;   /* type, position, angle, scale */
    if (version >= 1)
        size += 2;
    if (version >= 2)
        size += 1;
    if (version >= 3)
        size += 12;
    if (version >= 4)
        size += 1;
    if (version >= 5)
        size += 8;
    return size;
}

void mu_objects_record_init(mu_object_record *record)
{
    memset(record, 0, sizeof *record);
    record->scale = 1.0f;          /* [0x01a7dd48] */
    record->flag_2c = 1;
    record->flag_2d = 1;
    record->flag_2e = 1;
    record->hidden = 0;
    record->value_30 = 0.8f;       /* [0x01a7df18] */
    record->value_34 = 0.2f;       /* [0x01a7df08] */
}

static float read_f32(const uint8_t *p)
{
    float value;
    memcpy(&value, p, sizeof value);
    return value;
}

int mu_objects_parse(const uint8_t *plain, size_t size, mu_object_header *header, mu_object_record *records,
                     int32_t capacity, int32_t *parsed)
{
    if (parsed)
        *parsed = 0;
    if (!plain || !header || capacity < 0 || (capacity > 0 && !records))
        return MU_OBJECTS_BAD_ARGUMENT;
    memset(header, 0, sizeof *header);
    if (size < 4)
        return MU_OBJECTS_TRUNCATED;
    header->version = plain[0];
    header->map = plain[1];
    header->count = (int16_t)(uint16_t)(plain[2] | plain[3] << 8);
    header->record_size = mu_objects_record_size(header->version);
    const uint8_t v = header->version;
    size_t offset = 4;
    for (int32_t i = 0; i < header->count; ++i) {
        if (size - offset < (size_t)header->record_size)
            return MU_OBJECTS_TRUNCATED;
        mu_object_record r;
        mu_objects_record_init(&r);
        const uint8_t *p = plain + offset;
        r.type = (int16_t)(uint16_t)(p[0] | p[1] << 8);
        p += 2;
        for (int k = 0; k < 3; ++k)
            r.position[k] = read_f32(p + 4 * k);
        p += 12;
        for (int k = 0; k < 3; ++k)
            r.angle[k] = read_f32(p + 4 * k);
        p += 12;
        r.scale = read_f32(p);
        p += 4;
        if (v >= 1) {
            r.flag_2c = p[0];
            r.flag_2d = p[1];
            p += 2;
        }
        if (v >= 2)
            r.flag_2e = *p++;
        if (v >= 3) {
            for (int k = 0; k < 3; ++k)
                r.vector[k] = read_f32(p + 4 * k);
            p += 12;
        }
        if (v >= 4)
            r.hidden = *p++;
        if (v >= 5) {
            r.value_30 = read_f32(p);
            r.value_34 = read_f32(p + 4);
            p += 8;
        }
        offset += (size_t)header->record_size;
        if (i < capacity)
            records[i] = r;
        if (parsed && i < capacity)
            *parsed = i + 1;
    }
    return MU_OBJECTS_OK;
}

/* 0x018392db, world 0 case: AccessModel(first_type + k, "Data\Object1\", name, first_number + k)
 * for k < count, in the client's call order. Types 300 and above (Bird 402,
 * Fish 408) are not reachable from a .obj type through this table's range and
 * are left out. */
static const struct {
    int16_t first_type;
    const char *name;
    int8_t first_number, count;
} lorencia[] = {
    {0, "Tree", 1, 13},          {20, "Grass", 1, 8},       {30, "Stone", 1, 5},
    {40, "StoneStatue", 1, 3},   {43, "SteelStatue", 1, 1}, {44, "Tomb", 1, 3},
    {50, "FireLight", 1, 2},     {52, "Bonfire", 1, 1},     {55, "DoungeonGate", 1, 1},
    {58, "TreasureDrum", 1, 1},  {59, "TreasureChest", 1, 1}, {60, "Ship", 1, 1},
    {69, "StoneWall", 1, 6},     {75, "StoneMuWall", 1, 4}, {65, "SteelWall", 1, 3},
    {68, "SteelDoor", 1, 1},     {91, "Cannon", 1, 3},      {80, "Bridge", 1, 1},
    {81, "Fence", 1, 4},         {85, "BridgeStone", 1, 1}, {90, "StreetLight", 1, 1},
    {95, "Curtain", 1, 1},       {98, "Carriage", 1, 4},    {102, "Straw", 1, 2},
    {96, "Sign", 1, 2},          {56, "MerchantAnimal", 1, 2}, {105, "Waterspout", 1, 1},
    {106, "Well", 1, 4},         {110, "Hanging", 1, 1},    {115, "House", 1, 5},
    {120, "Tent", 1, 1},         {111, "Stair", 1, 1},      {121, "HouseWall", 1, 6},
    {127, "HouseEtc", 1, 3},     {130, "Light", 1, 3},      {133, "PoseBox", 1, 1},
    {140, "Furniture", 1, 7},    {150, "Candle", 1, 1},     {151, "Beer", 1, 3},
};

int32_t mu_objects_lorencia_groups(void)
{
    return (int32_t)(sizeof lorencia / sizeof lorencia[0]);
}

int mu_objects_lorencia_group(int32_t index, int32_t *first_type, const char **name, int32_t *first_number,
                              int32_t *count)
{
    if (index < 0 || index >= mu_objects_lorencia_groups())
        return 0;
    if (first_type)
        *first_type = lorencia[index].first_type;
    if (name)
        *name = lorencia[index].name;
    if (first_number)
        *first_number = lorencia[index].first_number;
    if (count)
        *count = lorencia[index].count;
    return 1;
}

/* AccessModel 0x018202b4's file name: "%s.bmd" for -1, "%s0%d.bmd" below 10, "%s%d.bmd" otherwise. */
static int model_name(char *out, size_t out_size, int32_t folder, const char *name, int32_t number)
{
    int n;
    if (number == -1)
        n = snprintf(out, out_size, "Data/Object%d/%s.bmd", folder, name);
    else if (number < 10)
        n = snprintf(out, out_size, "Data/Object%d/%s0%d.bmd", folder, name, number);
    else
        n = snprintf(out, out_size, "Data/Object%d/%s%d.bmd", folder, name, number);
    return n > 0 && (size_t)n < out_size;
}

int32_t mu_objects_folder(int32_t world)
{
    if ((world >= 11 && world <= 17) || world == 52)                    /* 0x009dacec */
        return 12;
    if ((world >= 18 && world <= 23) || world == 53 || world == 97)     /* 0x009dacb8 */
        return 19;
    if ((world >= 24 && world <= 29) || world == 36)                    /* 0x009b0418 */
        return 25;
    if ((world >= 98 && world <= 99) || (world >= 45 && world <= 50))   /* 0x0095fba9 */
        return 47;
    if (world >= 82 && world <= 90)                                     /* 0x00e3068f */
        return 83;
    /* 0x0095c652(0x5c)->0x00d7b35d / 0x00d7b225: runtime custom-map table, not reconstructed */
    if (world >= 123 && world <= 127)                                   /* 0x00e1e4b6 */
        return 124;
    if (world >= 128 && world <= 130)                                   /* 0x016a8325 */
        return 131;
    if (world == 131)                                                   /* 0x00e45d40 */
        return 132;
    if (world == 132)                                                   /* 0x00e0558b */
        return 133;
    return world + 1;
}

int mu_objects_model_file(int32_t world, int32_t type, char *out, size_t out_size)
{
    if (!out || out_size == 0 || type < 0 || type >= 300)
        return 0;
    out[0] = 0;
    if (world == 0) {
        /* No two groups share a type. */
        int found = -1;
        for (int32_t i = 0; i < mu_objects_lorencia_groups(); ++i)
            if (type >= lorencia[i].first_type && type < lorencia[i].first_type + lorencia[i].count)
                found = i;
        if (found < 0)
            return 0;
        return model_name(out, out_size, 1, lorencia[found].name,
                          lorencia[found].first_number + (type - lorencia[found].first_type));
    }
    /* 0x01842c7a: world 0x80 loads types 0x42..0x46 from its own folder number. */
    if (world == 0x80 && type >= 0x42 && type <= 0x46)
        return model_name(out, out_size, world + 1, "Object", type + 1);
    return model_name(out, out_size, mu_objects_folder(world), "Object", type + 1);
}
