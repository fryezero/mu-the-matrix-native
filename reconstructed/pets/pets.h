/* The data-driven pets of the pet process (NATIVE-HELPERS-002, pets sub-track).
 *
 * Client routines (restored text, main.exe SHA-256 3cf91f3c...b5527a); names are investigator choices, see
 * docs/research/client-pets.md:
 *
 *   PetProcess        0x00b990b0  singleton getter (0x614-byte object, constructor 0x00eb0990)
 *   load petdata      0x00eb0a7d  Data\Local\petdata.bmd: 32 records of 0x30 bytes + a checksum (0x00976895,
 *                                 key 0x3bb2), each record XOR-ed by BuxConvert 0x00976855 (fc cf ab)
 *   info map          0x00eb0c52  item code 0x1a00 + record item -> record; lookup 0x00eb0cdb
 *   CreatePet         0x00eb0e78  (item code, model, position, owner c, subtype, link): a PetObject in the
 *                                 std::map keyed by c->key * 10000 + item code; Create 0x00eac071
 *   UpdatePets        0x00eb0d64  -> 0x00eac414: FadeAlpha, the model tick 0x00eac84d, the move 0x00eac902 by
 *                                 the record's move type, the pick-up sound 0x00eaeacf
 *   RenderPets        0x00eb0dee  -> 0x00eac4e0: TestFrustrum2D, RenderObject, the pet's visuals 0x00eaeaf8
 *   DeletePet         0x00eb1015  (owner c, item code or -1)
 *
 * Every routine takes the client state it reads as plain inputs and calls the host for the engine services
 * (GetTickCount / timeGetTime, the model's animation tick, RequestTerrain-free frustum test, RenderObject, the
 * pose builder, CreateSprite / CreateParticle / CreateEffect, the pick-up request, sounds). rand() is the MSVC LCG
 * kept here. Float arithmetic follows the client's binary32 (SSE) order; comparisons follow its comiss/jcc pairs.
 */
#ifndef MU_PETS_H
#define MU_PETS_H

#include <stddef.h>
#include <stdint.h>

#include "../helpers/helpers.h"

#ifdef __cplusplus
extern "C" {
#endif

enum {
    MU_PET_RECORDS = 32,
    MU_PET_RECORD_BYTES = 0x30,
    MU_PET_FILE_BYTES = MU_PET_RECORDS * MU_PET_RECORD_BYTES + 4,
    MU_PET_CHECKSUM_KEY = 0x3bb2,
    MU_PET_MAX = 32,            /* native capacity of the process's std::map */
    MU_PET_GROUND_ITEMS = 1000  /* the ground items 0x0b4780dc (stride 0x560) */
};

/* Item codes (group 13 * 512 + index) the visuals routine 0x00eaeaf8 names. */
enum {
    MU_PET_DEMON = 0x1a40, MU_PET_SPIRIT = 0x1a41, MU_PET_RUDOLPH = 0x1a43, MU_PET_PANDA = 0x1a50,
    MU_PET_UNICORN = 0x1a6a, MU_PET_SKELETON = 0x1a7b, MU_PET_PC_PANDA = 0x1bd5, MU_PET_PC_SKELETON = 0x1bd6
};
#define MU_PET_ZEN_TYPE 0x1c0f      /* ground item type the collectors pick up (14,15: zen) */
#define MU_PET_MODEL_BASE 0x24e6    /* model = 0x24e6 + item index (ChangeCharacterExt / the inventory) */
#define MU_PET_MODEL_SKELETON 0x2561 /* Create's y offset branch */

/* One petdata.bmd record (0x30 bytes, little endian) after BuxConvert. */
typedef struct mu_pet_info {
    int32_t seq;            /* +0x00 */
    int32_t item;           /* +0x04 item index in group 13 (0: end of the list) */
    uint8_t byte_08, byte_09;
    uint8_t slot;           /* +0x0a the hero's equipment slot the collector checks (8: the helper slot) */
    uint8_t move;           /* +0x0b move type: 0 fly after the owner, 1 collector */
    float range;            /* +0x0c */
    uint8_t follow;         /* +0x10 collector: 1 follow the owner, 0 circle around it */
    uint8_t pad_11[3];
    float scale;            /* +0x14 object scale */
    int32_t blend_mesh;     /* +0x18 object BlendMesh */
    float speed[5];         /* +0x1c play speed by state (0x00eb08c2) */
} mu_pet_info;

/* 0x00976895(data, size, key): the file checksum. */
uint32_t mu_pet_checksum(const uint8_t *data, uint32_t size, uint16_t key);
/* 0x00976855: XOR with the three-byte BuxCode (key at 0x01cf0448, fc cf ab). */
void mu_pet_bux(uint8_t *data, int32_t size);
/* The loader 0x00eb0a7d on a whole file image (NULL: missing). Fills table (zeroed first, like the client's memset
 * of the 0x600 bytes) and returns 0, 1 for a missing file or 2 for a checksum mismatch (the client then shows a
 * message box and leaves the table zero). A file shorter than 0x604 bytes reads as the client's short fread. */
int mu_pet_data_load(const uint8_t *file, size_t size, mu_pet_info table[MU_PET_RECORDS]);
/* The info map 0x00eb0c52 + 0x00eb0cdb: the record of item code 0x1a00 + item (records up to the first item 0;
 * std::map::insert keeps the first of equal keys). NULL when absent. */
const mu_pet_info *mu_pet_data_find(const mu_pet_info table[MU_PET_RECORDS], int32_t item_code);

/* A character as the pet routines read it. */
typedef struct mu_pet_owner {
    uint8_t live;           /* object +0x00 */
    uint8_t kind;           /* object +0x3b */
    uint16_t action;        /* object +0x2a (c + 0x327e) */
    int16_t key;            /* c + 0x3e */
    float position[3];      /* object +0x158 */
    float angle[3];         /* object +0x164 */
    float scale;            /* object +0xa0 */
    uint8_t buff_12;        /* 0x01295ade(object + 0x358, 0x12) */
    int32_t alt_pet;        /* 0x0129de01(c): -1 when the character shows its pet */
} mu_pet_owner;

/* A ground item as the collector sees it (item record +0 type, its OBJECT at +0x11c). */
typedef struct mu_pet_ground_item {
    uint8_t live;           /* OBJECT +0x00 */
    uint8_t visible;        /* OBJECT +0x0b */
    int32_t type;           /* +0x00 */
    float position[3];      /* OBJECT +0x158 */
} mu_pet_ground_item;

typedef struct mu_pet_inputs {
    int32_t scene;          /* SceneFlag 0x01d1df70 */
    int32_t hero;           /* owner index of the hero ([0x0a39d754]); -1 none */
    int32_t helper_type;    /* the hero's equipment entry +0x10 ([0x01d1df18] + 0x1b58 + slot * 0x12c) */
    uint8_t helper_92, helper_93;   /* that entry's +0x92 / +0x93 */
    float world_time;       /* WorldTime 0x06fce370 */
    const mu_pet_ground_item *items;   /* MU_PET_GROUND_ITEMS entries (NULL: none live) */
    int32_t before_items;   /* the dword at 0x0b477b7c that the collector's state 2 reads as the type of ground item -1
                             * once it has sent its pick-up (target -1): memory before the array, 0 natively */
} mu_pet_inputs;

typedef struct mu_pet_host {
    void *context;
    uint32_t (*tick)(void *context);   /* GetTickCount (IAT 0x01a7c49c) */
    uint32_t (*time)(void *context);   /* timeGetTime (IAT 0x01a7c9a4) */
    int (*has_model)(void *context, int32_t model);
    /* the model tick 0x00eac84d: model current action = object action, then 0x012b4dd3(frame, prior frame,
     * prior action, speed, position, angle) */
    void (*animate)(void *context, mu_hp_object *object, int32_t model, float speed);
    /* SetLive(object, 0) cleanup 0x009b0451 (optional) */
    void (*kill)(void *context, mu_hp_object *object);
    /* the pick-up request (0xC1 packet, the ground item index, global 0x01cf1028 set) */
    void (*pickup)(void *context, int32_t item);
    /* PlayBuffer 0x00a6ac96(sound, 0, 0) */
    void (*sound)(void *context, int32_t sound);
} mu_pet_host;

typedef struct mu_pet {
    int32_t key;            /* the map key */
    int32_t owner;          /* +0x04 owner index (the character) */
    mu_hp_object object;    /* *(+0x08) */
    int32_t item;           /* +0x0c item code */
    uint32_t created;       /* +0x10 GetTickCount at Create */
    int32_t target_item;    /* +0x14 ground item index the collector goes for (-1 none) */
    float target[3];        /* +0x18 */
    int32_t has_target;     /* +0x24 */
    uint32_t pick_tick;     /* +0x28 */
    uint32_t wait_tick;     /* +0x2c */
    int32_t state;          /* +0x34 */
    float angle1, angle2;   /* +0x38, +0x3c */
    const mu_pet_info *info;/* +0x40 */
} mu_pet;

typedef struct mu_pets {
    uint32_t rand_state;
    uint64_t rand_calls;
    int32_t pending_pickup; /* 0x01cf1028 (-1 none) */
    mu_pet_info table[MU_PET_RECORDS];
    mu_pet list[MU_PET_MAX];    /* sorted by key (std::map order) */
    int32_t count;
    mu_pet_owner *owners;
    int32_t owner_count;
    mu_pet_host host;
} mu_pets;

void mu_pets_init(mu_pets *p, uint32_t rand_seed, mu_pet_owner *owners, int32_t owner_count, const mu_pet_host *host);
int32_t mu_pets_rand(mu_pets *p);

/* PetObject::Create 0x00eac071 on a fresh pet (object constructed): returns 1, or 0 (no owner, live object). */
int mu_pet_create_object(mu_pets *p, mu_pet *pet, int32_t item, int32_t model, const float position[3], int32_t owner,
                         int32_t subtype);
/* CreatePet 0x00eb0e78: returns 1 when a pet was added. */
int mu_pets_create(mu_pets *p, int32_t item, int32_t model, const float position[3], int32_t owner, int32_t subtype);
/* DeletePet 0x00eb1015(c, item code or -1). Returns its result. */
int mu_pets_delete(mu_pets *p, int32_t owner, int32_t item);
mu_pet *mu_pets_find(mu_pets *p, int32_t owner, int32_t item);

/* PetObject::Update 0x00eac414 (returns its result) and the move 0x00eac902(elapsed). */
int mu_pet_update(mu_pets *p, mu_pet *pet, const mu_pet_inputs *in);
int mu_pet_move(mu_pets *p, mu_pet *pet, const mu_pet_inputs *in, uint32_t elapsed);
/* the collector's search 0x00eac65a */
void mu_pet_find_target(mu_pets *p, mu_pet *pet, const mu_pet_inputs *in);
/* UpdatePets 0x00eb0d64 */
void mu_pets_update(mu_pets *p, const mu_pet_inputs *in);

typedef struct mu_pet_render_host {
    void *context;
    /* TestFrustrum2D 0x016ccce7(x * 0.01, y * 0.01, -20) */
    int (*frustum)(void *context, float x, float y, float range);
    /* RenderObject 0x016d4fe4(object, 0, 0, buff ? 10 : 0, -1, -1) */
    void (*draw_object)(void *context, const mu_hp_object *object, int32_t a1, int32_t a2, int32_t a3, int32_t a4,
                        int32_t a5);
    /* the pose builder 0x012b5064 on BoneTransform 0x06fce398 for the object's model (frame, prior frame, prior
     * action, angle, head angle, 0, translate); before it the visuals set the model's origin (+0x78) to the object
     * position (translate 1) or its BodyScale (+0x74) to the object scale (translate 0, the skeletons) */
    void (*pose)(void *context, const mu_hp_object *object, int32_t model, int translate);
    /* BoneTransform 0x06fce398 + 0x30 * bone (NULL: TransformPosition leaves its output alone) */
    const float *(*bone_matrix)(void *context, int32_t model, int32_t bone);
    /* CreateSprite 0x01692eb7(bitmap, position, scale, light, object, 0, 0, 4, {1, 1, 1}) */
    void (*sprite)(void *context, int32_t bitmap, const float position[3], float scale, const float light[3],
                   const mu_hp_object *object);
    /* CreateParticle 0x0168fafd(bitmap, position, angle, light, subtype, scale, owner object or NULL, arg8) */
    void (*particle)(void *context, int32_t bitmap, const float position[3], const float angle[3],
                     const float light[3], int32_t subtype, float scale, const mu_hp_object *owner, int32_t arg8);
    /* CreateEffect 0x013c0eaa(type, position, angle, light, args[0..9]) */
    void (*effect)(void *context, int32_t type, const float position[3], const float angle[3], const float light[3],
                   const int32_t args[10]);
    /* the pet's list at +0x44: push_back 0x0096a485 (the kind just created), clear 0x00a8cbcd (kind -1) */
    void (*remember)(void *context, int32_t kind);
} mu_pet_render_host;

/* PetObject::Render 0x00eac4e0 and the visuals 0x00eaeaf8(elapsed). */
int mu_pet_render(mu_pets *p, mu_pet *pet, const mu_pet_inputs *in, const mu_pet_render_host *r);
int mu_pet_visuals(mu_pets *p, mu_pet *pet, const mu_pet_inputs *in, const mu_pet_render_host *r, uint32_t elapsed);
/* RenderPets 0x00eb0dee */
void mu_pets_render(mu_pets *p, const mu_pet_inputs *in, const mu_pet_render_host *r);

#ifdef __cplusplus
}
#endif

#endif
