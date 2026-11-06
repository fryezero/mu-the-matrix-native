/* Boss Battle (world 139): create 0x00d9c180, move 0x00d9c18d, visual 0x00d9c1a7. World 115: create 0x00d5cb99 and
 * move 0x00d5cc16, the BaseMap defaults. Each is `xor al, al` behind a frame: false, no request, no write. */
#include "worlds_s.h"
int mu_boss_battle_create(const uint8_t *o, int32_t world) { (void)o; (void)world; return 0; }
int mu_boss_battle_move(const uint8_t *o, int32_t world) { (void)o; (void)world; return 0; }
int mu_boss_battle_visual(const uint8_t *o, int32_t world) { (void)o; (void)world; return 0; }
int mu_world115_create(const uint8_t *o, int32_t world) { (void)o; (void)world; return 0; }
int mu_world115_move(const uint8_t *o, int32_t world) { (void)o; (void)world; return 0; }
