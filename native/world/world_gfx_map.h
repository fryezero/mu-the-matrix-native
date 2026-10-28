/* The map overlay and the Move window over the GFx layer (NATIVE-MAP-001, docs/research/client-maps.md).
 *
 * hudMap (a child of the base movie) gets the client's game side: InitData on
 * load, LoadWorldMap per world, the session's frame-fed overlay records through addUnit, the showMap rule (Tab in the movie, "View Map" in
 * the Move window) and every frame the hero marker's rotation and the map's
 * offset (0x00c6af22).  MoveCommand gets InitFixtedText, the list rows
 * (SetMoveMapList), the sort orders, favourites and the row click with the
 * demo server's teleport (core/mu_map); M toggles it (layer choice, the
 * client's key scan is not reconstructed). */
#ifndef MU_WORLD_GFX_MAP_H
#define MU_WORLD_GFX_MAP_H

#include "../core/mu_map.h"

struct mu_gfx_layer;
typedef struct world_gfx_map world_gfx_map;

world_gfx_map *world_gfx_map_open(struct mu_gfx_layer *layer, mu_map_session *session, const char *game_root);
void world_gfx_map_close(world_gfx_map *m);
/* Every rendered frame: the movie's setup, the world image and units, the hero marker and map offset. */
void world_gfx_map_frame(world_gfx_map *m, const float hero_pos[2], float hero_angle_z);
/* Scripted verbs: "tab", "move" (toggle the Move window), "sort" order, "click" row (1: a teleport is pending). */
int world_gfx_map_action(world_gfx_map *m, const char *verb, int arg);
int world_gfx_map_click(world_gfx_map *m, int index);
const char *world_gfx_map_last(const world_gfx_map *m);

#endif
