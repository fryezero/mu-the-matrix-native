#ifndef MU_COMBAT_WIRE_H
#define MU_COMBAT_WIRE_H
#include <stddef.h>
#include <stdint.h>
/* Plaintext body reconstruction only. No keyed transform or send wrap. */
typedef struct mu_combat_damage {
    uint16_t key;
    uint8_t shock, type, flags[8];
    int32_t amount, shield;
} mu_combat_damage;
int mu_combat_damage_body(const uint8_t *packet, size_t size, uint8_t *character,
                          uint8_t *attributes, uint16_t hero_key, mu_combat_damage *out);
int mu_combat_die_body(const uint8_t *packet, size_t size, uint8_t *character);
int mu_combat_action_body(const uint8_t *packet, size_t size, uint8_t *character,
                          int16_t target_index, int has_target, float target_angle);
size_t mu_combat_attack_request(uint8_t out[7], uint16_t key, uint8_t direction, int blocked);
size_t mu_combat_cast_request(uint8_t out[7], uint8_t x, uint8_t y, uint8_t skill, int type);
size_t mu_combat_move_request(uint8_t out[16], uint16_t hero_key, const uint8_t x[15],
                              const uint8_t y[15], uint8_t count, uint8_t target_x, uint8_t target_y,
                              float angle, int blocked, int32_t *delay);
#endif
