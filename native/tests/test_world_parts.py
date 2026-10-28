"""WORLD-ORDER-001: check part orders against the compiled call-record family.

Open/pre_tick/frame/report retain the WORLD-RT-001 regression pins. Tick and
both draw columns derive from MoveMainScene/RenderMainScene records, with
explicit native adapters in reconstructed/world-order/parts_order.py.
"""
import re
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORLD = HERE.parent / 'world'
COLUMNS = ('pre_tick', 'tick', 'frame', 'draw_gl', 'draw_soft', 'report')

# WORLD-RT-001 non-simulation columns, in the native baseline order.
MAIN_C_ORDER = {
    # load() main.c:459-744 (the rows that open something)
    'open': ['sound', 'npc_demo', 'actors', 'objects', 'env', 'particles', 'combat', 'progress', 'items', 'names',
             'npc', 'players', 'social', 'helpers', 'map', 'characters', 'haze'],
    # combat_pre_step main.c:331-341
    'pre_tick': ['items', 'npc', 'combat'],
    # advance main.c:1660-1686, after mu_walk_update / mu_walk_place / mu_walk_begin_render (terrain_frame's object
    # lights are the objects row)
    'frame': ['items', 'terrain', 'objects', 'combat', 'particles', 'actors', 'players', 'map', 'social', 'names'],
    # report_frame main.c:2707-2727 and report_summary main.c:2793-2915 (one order for both)
    'report': ['sound', 'env', 'particles', 'objects', 'actors', 'combat', 'progress', 'items', 'players', 'helpers',
               'names', 'npc', 'social', 'map', 'quest_step'],
}

# The call each hook makes at its place in main.c (column -> row -> function called in the hook's body).
SIGNATURE = {
    'pre_tick': {'items': 'mu_world_items_pre_step', 'npc': 'mu_npc_pre_step', 'combat': 'mu_combat_pre_step'},
    'tick': {'sound': 'mu_world_sound_hero_step', 'npc': 'mu_npc_step',
             'quest_step': 'world_gfx_quest_step', 'combat': 'mu_combat_step', 'progress': 'mu_progress_step',
             'characters': 'mu_world_players_step_one', 'social': 'mu_social_step', 'helpers': 'mu_world_helpers_step',
             'items': 'mu_world_items_step', 'names': 'mu_world_names_step', 'objects': 'mu_objects_step',
             'env': 'mu_world_env_step', 'particles': 'mu_world_particles_step', 'map': 'mu_map_gate_step'},
    'frame': {'items': 'mu_world_items_select', 'terrain': 'mu_world_frame_box', 'objects': 'mu_objects_apply_lights',
              'combat': 'mu_combat_terrain_lights', 'particles': 'mu_world_particles_apply_lights',
              'actors': 'mu_world_actors_frame', 'players': 'mu_world_players_frame', 'map': 'world_gfx_map_frame',
              'social': 'world_gfx_social_frame', 'names': 'mu_world_names_frame'},
    'draw_gl': {'terrain': 'mu_terrain_render', 'objects': 'mu_objects_visibility', 'hero': 'hero_item_draw',
                'players': 'player_item_draw', 'helpers': 'mu_world_helpers_draw', 'actors': 'npc_item_draw',
                'items': 'mu_world_items_draw', 'objects_after': 'mu_objects_after_visibility', 'env': 'mu_world_env_draw', 'marker': 'marker',
                'particles': 'mu_world_particles_draw', 'actor_effects': 'mu_effect_scene_render_to',
                'combat': 'combat_draw', 'haze': 'mu_world_haze_draw', 'item_labels': 'items_labels_gl', 'names': 'names_gl'},
    'draw_soft': {'terrain': 'mu_world_draw_raster_view', 'objects': 'mu_objects_render_raster',
                  'hero': 'hero_item_draw', 'players': 'player_item_draw', 'actors': 'npc_item_draw',
                  'items': 'mu_world_items_draw', 'objects_after': 'mu_objects_after_visibility', 'env': 'mu_world_env_draw_raster',
                  'helpers': 'mu_world_helpers_draw_raster', 'particles': 'mu_world_particles_draw_raster',
                  'marker': 'marker', 'actor_effects': 'mu_effect_scene_render', 'combat': 'mu_combat_draw_raster',
                  'haze': 'mu_world_haze_draw_raster', 'item_labels': 'mu_world_items_label_blit', 'names': 'mu_world_names_draw'},
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
        root = HERE.parents[1]
        sys.path.insert(0, str(root / 'scripts'))
        import validate_world_order as validator
        cls.validator = validator
        spec = importlib.util.spec_from_file_location('world_parts_order', root / 'reconstructed/world-order/parts_order.py')
        cls.adapter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.adapter)
        cls.temp = tempfile.TemporaryDirectory(prefix='mu-world-parts-')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.lib = validator.build(cls.temp.name)
        cls.recorded = {}
        for family in ('tick', 'draw'):
            host = validator.RecordingHost(validator.case())
            host.run(cls.lib, family)
            cls.recorded[family] = host.trace
        cls.rows = parse_rows()
        cls.sources = part_sources()
        cls.ops = {}
        for r in cls.rows:
            cls.ops[r['id']] = ops_initializer(cls.sources, r['ops'])

    def test_rows_parse_and_ids_are_unique(self):
        ids = [r['id'] for r in self.rows]
        self.assertEqual(len(ids), 24)
        self.assertEqual(len(set(ids)), len(ids))
        self.assertEqual([r['ops'] for r in self.rows], [f'mu_part_{i}' for i in ids])

    def test_non_simulation_columns_keep_native_baseline_order(self):
        for column in ('pre_tick', 'frame', 'report'):
            with self.subTest(column=column):
                self.assertEqual(column_order(self.rows, column), MAIN_C_ORDER[column])

    def test_tick_and_draw_columns_follow_recorded_calls(self):
        for column in ('tick', 'draw_gl', 'draw_soft'):
            trace = self.recorded['tick' if column == 'tick' else 'draw']
            self.assertEqual(column_order(self.rows, column), self.adapter.projected_order(trace, column), column)

    def test_missing_recorded_anchor_is_rejected(self):
        for column in ('tick', 'draw_gl', 'draw_soft'):
            family = 'tick' if column == 'tick' else 'draw'
            for anchor in self.adapter.ANCHORS[family]:
                trace = [c for c in self.recorded[family] if c[0] != anchor]
                with self.subTest(column=column, anchor=hex(anchor)), self.assertRaises(ValueError):
                    self.adapter.projected_order(trace, column)

    def test_part_order_mutations_are_detected(self):
        for column in ('tick', 'draw_gl', 'draw_soft'):
            expected = self.adapter.projected_order(self.recorded['tick' if column == 'tick' else 'draw'], column)
            for i in range(len(expected) - 1):
                rows = [dict(r) for r in self.rows]
                a, b = ([r for r in rows if r['id'] == part][0] for part in expected[i:i+2])
                a[column], b[column] = b[column], a[column]
                self.assertNotEqual(column_order(rows, column), expected)

    def test_client_reordering_propagates_to_part_expectation(self):
        for column, a, b in (('tick', 0x016a9150, 0x0137a7ce),
                             ('draw_gl', 0x016cd468, 0x016d5020),
                             ('draw_soft', 0x016cd468, 0x016d5020),
                             ('draw_gl', 0x01538145, 0x016d6949),
                             ('draw_soft', 0x01538145, 0x016d6949)):
            trace = list(self.recorded['tick' if column == 'tick' else 'draw'])
            i, j = next(i for i, c in enumerate(trace) if c[0] == a), next(i for i, c in enumerate(trace) if c[0] == b)
            trace[i], trace[j] = trace[j], trace[i]
            self.assertNotEqual(column_order(self.rows, column), self.adapter.projected_order(trace, column))

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'private original-instruction comparison')
    def test_original_world_order_instructions(self):
        subprocess.run([sys.executable, str(HERE.parents[1] / 'scripts/validate_world_order.py'),
                        '--cases', '1200', '--mutations', '--output', str(Path(self.temp.name) / 'comparison.json')], check=True)

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

    def test_actors_step_only_inside_shared_character_loop(self):
        characters = (WORLD / 'parts/characters.c').read_text()
        actors = (WORLD / 'parts/actors.c').read_text()
        self.assertIn('mu_world_actors_step_one(', characters)
        self.assertNotIn('mu_world_actors_step(', actors)

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
