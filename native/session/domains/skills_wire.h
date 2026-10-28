#ifndef MU_SKILLS_WIRE_H
#define MU_SKILLS_WIRE_H
#include <stddef.h>
#include <stdint.h>
/* 0x0182ff32, bounded key serialization and packet tail only. settings is the 17-byte
 * non-skill settings suffix supplied by the owning options domain; no settings are inferred here. */
size_t mu_skills_save_request(uint8_t *, size_t, const int32_t slots[10], const uint8_t settings[17]);
#endif
