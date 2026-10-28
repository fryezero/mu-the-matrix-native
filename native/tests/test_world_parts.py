"""WORLD-RT-001: native/world/parts.def pins the world runtime's tick and draw orders.

world/main.c (3,622 lines, commit f997742) ran its subsystems in a fixed order in seven places: load(), the
pre-step hook combat_pre_step (main.c:331-341), the step hook on_step (main.c:758-826, the client's
MoveHero/MoveCharacters order), advance (main.c:1636-1688), draw_gl (main.c:2296-2518), draw_soft
(main.c:2549-2680) and the reports (main.c:2684-2919).  The runtime (world/world_rt.c) now calls each part's hook
in the order of a parts.def column.  These tests pin every column to main.c's order (a reordering is a visible
diff), check that each row's hooks exist exactly where its columns have a number, and check that each hook
still makes the subsystem call main.c made at that place, so a call moved to another part fails too.
WORLD-ORDER-001 later replaces the literal tick and draw lists with the order recorded from the reconstructed
MoveMainScene/RenderMainScene.
"""
import re
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORLD = HERE.parent / 'world'
COLUMNS = ('pre_tick', 'tick', 'frame', 'draw_gl', 'draw_soft', 'report')

# world/main.c at f997742, in call order (the row ids of parts.def).
MAIN_C_ORDER = {
    # load() main.c:459-744 (the rows that open something)
    'open': ['sound', 'npc_demo', 'actors', 'objects', 'env', 'particles', 'combat', 'progress', 'items', 'names',
             'npc', 'players', 'social', 'helpers', 'map'],
    # combat_pre_step main.c:331-341
    'pre_tick': ['items', 'npc', 'combat'],
    # on_step main.c:758-826
    'tick': ['sound', 'actors', 'npc', 'quest_step', 'combat', 'progress', 'players', 'social', 'helpers', 'items',
             'names', 'objects', 'env', 'particles', 'map'],
    # advance main.c:1660-1686, after mu_walk_update / mu_walk_place / mu_walk_begin_render (terrain_frame's object
    # lights are the objects row)
    'frame': ['items', 'terrain', 'objects', 'combat', 'particles', 'actors', 'players', 'map', 'social', 'names'],
    # draw_gl main.c:2296-2518
    'draw_gl': ['terrain', 'objects', 'hero', 'players', 'helpers', 'actors', 'items', 'objects_after', 'env', 'marker', 'particles',
                'actor_effects', 'combat', 'item_labels', 'names'],
    # draw_soft main.c:2549-2680
    'draw_soft': ['terrain', 'objects', 'hero', 'players', 'actors', 'items', 'objects_after', 'env', 'helpers', 'particles', 'marker',
                  'actor_effects', 'combat', 'item_labels', 'names'],
    # report_frame main.c:2707-2727 and report_summary main.c:2793-2915 (one order for both)
    'report': ['sound', 'env', 'particles', 'objects', 'actors', 'combat', 'progress', 'items', 'players', 'helpers',
               'names', 'npc', 'social', 'map'],
}

# The call each hook makes at its place in main.c (column -> row -> function called in the hook's body).
SIGNATURE = {
    'pre_tick': {'items': 'mu_world_items_pre_step', 'npc': 'mu_npc_pre_step', 'combat': 'mu_combat_pre_step'},
    'tick': {'sound': 'mu_world_sound_hero_step', 'actors': 'mu_world_actors_step', 'npc': 'mu_npc_step',
             'quest_step': 'world_gfx_quest_step', 'combat': 'mu_combat_step', 'progress': 'mu_progress_step',
             'players': 'mu_world_players_step', 'social': 'mu_social_step', 'helpers': 'mu_world_helpers_step',
             'items': 'mu_world_items_step', 'names': 'mu_world_names_step', 'objects': 'mu_objects_step',
             'env': 'mu_world_env_step', 'particles': 'mu_world_particles_step', 'map': 'mu_map_gate_step'},
    'frame': {'items': 'mu_world_items_select', 'terrain': 'mu_world_frame_box', 'objects': 'mu_objects_apply_lights',
              'combat': 'mu_combat_terrain_lights', 'particles': 'mu_world_particles_apply_lights',
              'actors': 'mu_world_actors_frame', 'players': 'mu_world_players_frame', 'map': 'world_gfx_map_frame',
              'social': 'world_gfx_social_frame', 'names': 'mu_world_names_frame'},
    'draw_gl': {'terrain': 'mu_terrain_render', 'objects': 'mu_objects_visibility', 'hero': 'mu_scene_draw_model',
                'players': 'player_item_draw', 'helpers': 'mu_world_helpers_draw', 'actors': 'npc_item_draw',
                'items': 'mu_world_items_draw', 'objects_after': 'mu_objects_after_visibility', 'env': 'mu_world_env_draw', 'marker': 'marker',
                'particles': 'mu_world_particles_draw', 'actor_effects': 'mu_effect_scene_render_to',
                'combat': 'combat_draw', 'item_labels': 'items_labels_gl', 'names': 'names_gl'},
    'draw_soft': {'terrain': 'mu_world_draw_raster_view', 'objects': 'mu_objects_render_raster',
                  'hero': 'mu_scene_draw_model', 'players': 'player_item_draw', 'actors': 'npc_item_draw',
                  'items': 'mu_world_items_draw', 'objects_after': 'mu_objects_after_visibility', 'env': 'mu_world_env_draw_raster',
                  'helpers': 'mu_world_helpers_draw_raster', 'particles': 'mu_world_particles_draw_raster',
                  'marker': 'marker', 'actor_effects': 'mu_effect_scene_render', 'combat': 'mu_combat_draw_raster',
                  'item_labels': 'mu_world_items_label_blit', 'names': 'mu_world_names_draw'},
}

HOOK = {'pre_tick': ('pre_tick',), 'tick': ('tick',), 'frame': ('frame',), 'draw_gl': ('draw_gl',),
        'draw_soft': ('draw_soft',), 'report': ('report_frame', 'report_summary')}


def parse_rows():
    rows = []
    for line in (WORLD / 'parts.def').read_text().splitlines():
        m = re.match(r'\s*MU_PART\(\s*(\w+)\s*,\s*(\w+)\s*,' + r'\s*(\d+)\s*,' * 5 + r'\s*(\d+)\s*\)', line)
        if m:
            rows.append({'id': m.group(1), 'ops': m.group(2),
                         **{c: int(m.group(3 + k)) for k, c in enumerate(COLUMNS)}})
    return rows


def part_sources():
    return {p.name: p.read_text() for p in sorted((WORLD / 'parts').glob('*.c'))}


def ops_initializer(sources, ops):
    """(file, {field: function}) of `const mu_world_part_ops OPS = {...};`."""
    for name, text in sources.items():
        m = re.search(r'const mu_world_part_ops ' + re.escape(ops) + r' = \{(.*?)\n\};', text, re.S)
        if m:
            return name, dict(re.findall(r'\.(\w+) = (\w+)', m.group(1)))
    return None, None


def function_body(text, name):
    m = re.search(r'^static [^\n]*\b' + re.escape(name) + r'\(.*?\n\{\n(.*?)\n\}\n', text, re.S | re.M)
    return m.group(1) if m else None


def column_order(rows, column):
    return [r['id'] for r in sorted((r for r in rows if r[column]), key=lambda r: r[column])]


class PartsDefTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = parse_rows()
        cls.sources = part_sources()
        cls.ops = {}
        for r in cls.rows:
            cls.ops[r['id']] = ops_initializer(cls.sources, r['ops'])

    def test_rows_parse_and_ids_are_unique(self):
        ids = [r['id'] for r in self.rows]
        self.assertEqual(len(ids), 22)
        self.assertEqual(len(set(ids)), len(ids))
        self.assertEqual([r['ops'] for r in self.rows], [f'mu_part_{i}' for i in ids])

    def test_each_column_is_world_main_c_order(self):
        for column in COLUMNS:
            with self.subTest(column=column):
                self.assertEqual(column_order(self.rows, column), MAIN_C_ORDER[column])

    def test_numbers_are_unique_per_column(self):
        for column in COLUMNS:
            numbers = [r[column] for r in self.rows if r[column]]
            self.assertEqual(len(numbers), len(set(numbers)), column)

    def test_open_order_is_the_row_order(self):
        opening = [r['id'] for r in self.rows if 'open' in self.ops[r['id']][1]]
        self.assertEqual(opening, MAIN_C_ORDER['open'])

    def test_every_row_has_its_ops_in_a_part_file(self):
        for r in self.rows:
            with self.subTest(part=r['id']):
                name, fields = self.ops[r['id']]
                self.assertIsNotNone(name, f"{r['ops']} not defined in native/world/parts/")
                self.assertEqual(fields.get('name'), None)   # .name is a string, not a function
                self.assertIn(f'.name = "{r["id"]}"', self.sources[name])

    def test_hooks_exist_exactly_where_columns_have_numbers(self):
        for r in self.rows:
            _, fields = self.ops[r['id']]
            for column in COLUMNS:
                with self.subTest(part=r['id'], column=column):
                    has = any(h in fields for h in HOOK[column])
                    self.assertEqual(has, r[column] != 0)

    def test_each_hook_makes_main_c_call_at_that_place(self):
        for column, calls in SIGNATURE.items():
            for part, call in calls.items():
                with self.subTest(column=column, part=part):
                    name, fields = self.ops[part]
                    body = function_body(self.sources[name], fields[column])
                    self.assertIsNotNone(body, f'{fields[column]} in {name}')
                    self.assertRegex(body, r'\b' + re.escape(call) + r'\(')

    def test_runtime_dispatches_through_the_columns(self):
        rt = (WORLD / 'world_rt.c').read_text()
        self.assertIn('#include "parts.def"', rt)
        for column in ('COL_PRE_TICK', 'COL_TICK', 'COL_FRAME', 'COL_DRAW_GL', 'COL_DRAW_SOFT', 'COL_REPORT'):
            self.assertRegex(rt, r'EACH\(' + column + r', i\)')
        # the embed and world/main.c are gone: one runtime, one copy
        self.assertFalse((WORLD / 'main.c').exists())
        self.assertFalse((WORLD / 'world_embed.c').exists())
        self.assertFalse((WORLD / 'world_embed.h').exists())


if __name__ == '__main__':
    unittest.main()
