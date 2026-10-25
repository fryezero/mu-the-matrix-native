#!/usr/bin/env python3
"""Compare the reconstructed click-to-move path finding and path following
(reconstructed/path) with the client's own instructions in Unicorn.

The pinned restored text and second image section are executed unchanged.
The path finder object is built by the client's own constructor and
SetMapDimensions; every search runs PathFinding2 0x012b0e85 (FindPath, the
binary-search-tree queue, BuildPath, the target marking) as client code.
MovePath, the angle helpers and MoveCharacterPosition run as client code too.
Only CRT heap/memset services, a log call and subsystem queries outside the
compared routines are replaced; each is listed in CLIENT_STUBS. Results are
compared bit for bit with the C library built from reconstructed/path.

Inputs: the 64-byte neighbour table 0x01cf1640 lies in the packed third
section. It is pinned by SHA-256 and read from a capture of that section: by
default the manifest-backed live read evidence/path-table-live-01 (memread,
2026-10-18); the earlier unpacked capture x86-linux-capture-04 has the same
bytes. Synthetic (labelled): the finder's touched range starts in its reset
state and its path arrays start zeroed (the client allocates them
uninitialised); heap memory returned to the client is filled with a poison
byte.

NATIVE-PATH-002 adds the long-distance helper 0x012b104c (budget 300,000,000,
BuildPath's trimming variant), the auto-move PATH_t methods (next segment,
reset, start, refresh), and the run counter and speed predicates: the
run-counter prefix of SetPlayerWalk, SetPlayerStop's reset and
CharacterMoveSpeed with its helper/mount/pet/world predicates executed as
client code, compared with reconstructed/movement.
"""
import argparse
import ctypes
import hashlib
import json
import math
import os
from pathlib import Path
import random
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import pins  # noqa: E402
TEXT_BASE, TEXT_BYTES = 0x401000, pins.TEXT.size
TEXT_SHA256 = pins.TEXT.sha256
DATA_BASE, DATA_BYTES = 0x1a7c000, pins.DATA.size
DATA_SHA256 = pins.DATA.sha256
FLAG_ADDRESS = 0x0bdd1cc8
FLAG_SHA256 = pins.FLAG.sha256
DIRECTIONS_ADDRESS = 0x01cf1640
DIRECTIONS_SECTION = 0x01ced000
DIRECTIONS_SHA256 = pins.DIRECTIONS.sha256

ROUTINES = {
    'path_finding2': (0x012b0e85, 0x1c7, '361a18e5813b76746f898f0b073663ca18207d8ae5d603f8e64ee0ac7599705c'),
    'move_path': (0x012b0846, 0x61f, 'dee0f6b9e70f485a900c7c2b6038e9a7dcfb21a38783b831170495fbffca819c'),
    'set_map': (0x012b0e65, 0x20, '96b33b1953b1ebd00f64ef8c742f01ed0543ca73fb42dd4c05a34eca1e9dd6f3'),
    'tree_insert': (0x012b198d, 0x15a, 'c6c5ed3d060b8775886befac8bd4b11f27a8c831fbc9d62a3f3483aa53a85ed7'),
    'finder_helpers': (0x012b1ae7, 0x15e, 'b9b8d3316ad6a48ab3631c489731445b6d5966a8500fd197d5026a782ad92f6f'),
    'find_path': (0x012b1c45, 0x581, '73c083787c9d97439b78c6a105dfe6dca87e5b819eda16817ad576a0555c83dd'),
    'build_path': (0x012b21c6, 0x207, '1cffd1fbfdeb1f6091590bb7cd51867dfeeb4c5b3ec5657fbf8fbac76666854a'),
    'finder_accessors': (0x012b23cd, 0x1b7, '3ff479c09314193787b123c4f0b4808b46650689ad0ce03b3b3ae3446f64db71'),
    'mark_targets': (0x012b2584, 0x29a, '98ed59736e351bff859e0b37d1ac332408f8a8317c23c0682347df1d0b6d8843'),
    'set_map_dimensions': (0x012b281e, 0xe8, 'c7a705ebb2d8a47a3996814c250c99a7c7805d352d35c61432ef78a6820bb804'),
    'finder_ctor': (0x012b1766, 0x131, '50ff1310dda85d31ceb0cc26cca47c08c47d26208507df0b81039765987dc881'),
    'tree_ops': (0x01212a40, 0x749, 'cbb2742b56dfbbfe79796f76dd283f42b0aaf2401d76c0af3652b5057b7b86f2'),
    'angles': (0x012aed9e, 0x553, 'eafaafa3f5d23ffbb61400f38455700d33cdaecdf2d17577cbdffff48df6e72f'),
    'move_character_position': (0x0137b351, 0x33b, '2c1235b690c6d2f7330a5e44cc7fda6ba6d1d2fd4818860bf76c4605ca77b2e8'),
    'move_characters': (0x0137a7ce, 0x17a, '5a1bc60ef62c416991af83b575b05881c5bc671f2d776e0397e23780f0ef13a9'),
    'atan_wrapper': (0x012b2bca, 0x16, '40175dd440c0e8ec1c4d211cdd9a3f010b7503d020c019bbe63e68c8ac995cc1'),
    'atan_float': (0x012b2d60, 0x1f, '7c0f2f64cd7f4d6188b1c26fc78c9642e3a8ea6f55b9d6cc299df0bdd9c21e10'),
    'sqrt_float': (0x00961a07, 0x1f, 'b76d7bde45ba4e3662747aeb55ea46f130798f820e4e50ea50f14b2fb52c1a1d'),
    'sqrt_wrapper': (0x009b0c87, 0x16, '24f03dde13bb98714ebee52905794e677c52999608ba9302a86ac0401b3652a9'),
    'fabs': (0x0184f8ff, 0x28, '13a551406032c0bea590fd9233cbc74cdd2c67640540461d7cc1a471d2277638'),
    'abs': (0x01983135, 0xf, 'd0bb562db7fb121bef551c43293337f7c6b59dc7ececb15358050a324b67e37d'),
    'tile_index': (0x016d34db, 0x1b, '0d1422308044ba115f6abd792d16efda7d30c1b55b539b7d2394281e0325e9ff'),
    'vec3_at': (0x00cfc922, 0x12, 'c50769ecd71f18b8e82733c7646941784b333ad85cf6f39a4654207733682839'),
    # NATIVE-PATH-002: every other client code span the long/auto/run/speed_state/predicates families execute
    # (coverage run; spans closer than 64 bytes merged; stubbed callees appear with their entry block only)
    'cov_008e6230': (0x8e6230, 0x3, 'e598d0c3ba86d917b177d7adde0556aa99bc355543c57aee0a3e50b684dd7e99'),
    'cov_008e7d10': (0x8e7d10, 0x5, '99712f5745d56904d51e658eeac81bb39a7a2acb4c8834e9af91b4ef58557a0d'),
    'cov_00944b5e': (0x944b5e, 0x2c, '9e90aa1982035596d25a59885b0697c8e1eb8be43cb9f01570c1792873a36102'),
    'cov_00944c29': (0x944c29, 0x5f, '7374926636828fe3a5b2737c477bf22cb8c81008c04313095f4d31597229d59c'),
    'cov_0094556b': (0x94556b, 0x49, '245f44b06dc07fdd779fbb2243a06714805754fc8901fe05771a54e3372441a7'),
    'cov_00947387': (0x947387, 0x27, '854cbd48867bae6e466c198294dd0e6274c7ba8c998559bb928287c25f0912e2'),
    'cov_00947851': (0x947851, 0xf, 'f1b8c5285cc5cbb4130c1c0e094bc4932f3e60ba22764af018700ca3e6610a29'),
    'cov_00948d35': (0x948d35, 0x2a, 'abdefcbe9e8aab0b5c2075e620824ff53a16558eca02335b17174f5c91ac2dfe'),
    'cov_0094a03b': (0x94a03b, 0xe, '258e1b13a66cc4c1dc497084014c46b5c89814b784e143b70e81227bf70fdbe5'),
    'cov_0094c02c': (0x94c02c, 0x6d, '5762b01fb3665306806d034077a78192fc17e5a4db7fba93c706e11fba35c057'),
    'cov_0094c103': (0x94c103, 0xe, '730fc06a51616d7ecec42226ed86d615f735fd9bee29033d26ec52813ce51845'),
    'cov_0094e68a': (0x94e68a, 0x9, '92c6d64d044b483d570bfd94cb01e9b9eef3d4c792e00f39baf084bd82571f9e'),
    'cov_0094e8d1': (0x94e8d1, 0x9, '92c6d64d044b483d570bfd94cb01e9b9eef3d4c792e00f39baf084bd82571f9e'),
    'cov_0095c550': (0x95c550, 0x12, '20a84d2ec69cfc74b436c87b1dc07b2323a6830c9b64f94ebd8371e841be7034'),
    'cov_0095d692': (0x95d692, 0x25, 'f20c89c29ed439c9edb3f06835b07554894d269555f71b64a7c0897ba20a807c'),
    'cov_0095eba6': (0x95eba6, 0x12, 'b63360c40c4caa9c954a90455f7ca244e8fd94d9ecbf08a1f6452d893665645c'),
    'cov_0095f09a': (0x95f09a, 0x10, 'ea43246fee6f3334cd2dd8969e7d3fcd77a6d26acd6749c8f029f13558477c14'),
    'base_class': (0x95f5cc, 0xb, '0ccb64b405499edf6e0778c5493520acecf7b9d1c8421c7ae277ca472664df46'),
    'safe_zone_byte': (0x95fb27, 0x10, '3927f59e7cd6ea52bf9ef85c8c29e1c9dfa93fd5a1c18c17a69f38179b6627f4'),
    'cov_00966c42': (0x966c42, 0x35, '470b7eae3e7cf336527d5084a40a3229c9b657b1a8dfd91e66c1e06211f280a5'),
    'cov_009c104e': (0x9c104e, 0x35, '1323ff7a28fb7999de10b19080035820634d4b11fc8e16ac8f1e3d2e9cd84001'),
    'world_forces_run': (0x9dacb8, 0x23, 'd2129e6fa8fc0b28ee3e75a44d60cdfbe7a75793a3189ea35f3e36675bdbbccb'),
    'cov_009fa30a': (0x9fa30a, 0x35, '531ec0623e647b48fb0c306e711bf849dedb02a66def0889bbc5597c4c4fd3a4'),
    'cov_009fbb31': (0x9fbb31, 0xe, '057869952537c3a4e2c23e0d9400a1b53e39aa05d50a8f2e0de23dbbb725c755'),
    'transformed': (0xb9929c, 0x13, '8e32024c02b57b1806076d37defbca6dea4eafa6459fb86472ca2e9157dfca2b'),
    'cov_00cd4ea8': (0xcd4ea8, 0x35, '2c365524212305203eec74feb12121ec7bcd68c20bb1a2f868a138d19f354b48'),
    'cov_00cd5d29': (0xcd5d29, 0x19, '66897a3d12d7ce642c4f48f03482e93964454d8b03cae457da13163421812263'),
    'item_kind_b': (0xcd6017, 0x48, 'b294148585c1193b312296cffd742d3950679814b3b3d27ed11aa918c3b083e4'),
    'world_safe_runs': (0xe0558b, 0x14, '87a23b1352584a2e22cf3c9f7b5c5fb2f889746c9dc2a4716a8ccd96afdac537'),
    'cov_0106bd76': (0x106bd76, 0x58, 'de26949f70814c6ef7c244bb7c20fc00de9f3cf13170307a234dbf2ded6cf936'),
    'buff_mount': (0x106c5e9, 0x2d4, '6bf3673effff9bcb8dcca5b3e58ea3c2695ff72740aa1680068fb00d6c12c84b'),
    'cov_0117b5eb': (0x117b5eb, 0x26, '56b623cea18800d1bfc22969c4013a626721823b9cca0afc3fa2eb4b502a566d'),
    'cov_01212655': (0x1212655, 0x9, '92c6d64d044b483d570bfd94cb01e9b9eef3d4c792e00f39baf084bd82571f9e'),
    'cov_0121290b': (0x121290b, 0x2a, '0d52a6abaee11932a6cb7164c64c935dae80f0075f250acf2f2455d37d17de72'),
    'cov_01295ade': (0x1295ade, 0x11, '940dfb9bb571fbb4d0f581f23093514dba2ad70e90ec61445818c55c86d7a861'),
    'auto_reset_refresh': (0x129c4d2, 0xb3, '71004324c99357d5be4b5953d0f874d856e6e9baa93a24bf02938b8c20bdf499'),
    'auto_refresh_start': (0x129c653, 0x18f, '567df55f0934a3e00cb8f166d4865a0b1f346aa6868810a0ac2c5016ec009288'),
    'auto_start_tail': (0x129c898, 0x3a, 'd3118c004ae0ede699004315b1410d45c20c4561f0944625db9b0f0883167e65'),
    'auto_next_segment': (0x129cc44, 0x170, 'cd9f281826fbc0ba5690847326438cde2ff117eb4f62253be8b6adf44e1cf126'),
    'helper_type': (0x129dcda, 0x13, '7ecb4a32b00d582fbdf41e34f8895840c775827e80523ffc7c6add7d9f1f181d'),
    'list_helpers_1': (0x129dee4, 0x1fa, '3c55bf4d7c99f59492151c4b51490c919bcd05105d7b22b4d90d7921e33046d4'),
    'path_ctor': (0x129e1b9, 0xbd, '57305f856930fff4bde3c1a64366c3e7eb979000500bce195ee892bdc7cdb7ad'),
    'list_helpers_4': (0x129e2bb, 0x22, '9ec4ed8ab9ca0dd55bcfa68dff1a079579d407e3131e26d93b1b5d15e2bdb40b'),
    'list_helpers_2': (0x129e35e, 0xbd, 'd132b686cf2b066ca58bf66a91a89a7ac7c5d1699357a2772e792b3e3413228b'),
    'list_helpers_3': (0x129e45d, 0x158, 'f169a9e35ea48efc9a62eb4ce960264f5b882fc86fe664d1b86981b89c927ce2'),
    'long_path_and_list_insert': (0x12b104c, 0x62b, '0d6a1afb019ea18eb21fbaab0b7f82437311f6b8e5cf00ace46ef9caa868479e'),
    'list_node_helpers': (0x12b16cb, 0x8b, '462fc9d25aae1e362884f0fb3b60bcf7f72237353ca76edb52d03b40d277f4e2'),
    'finder_misc': (0x12b1897, 0xf6, 'f6d1556af8fd48c9f9b7694982f8a6f614c08d9c5565e3fa45680f11fbb8e820'),
    'build_path_vector': (0x12b2908, 0x458, 'c31f316787a72e309a57a78b28aa69ab88a13d33d019f8097139cace439f09ce'),
    'set_player_stop_prefix': (0x138fe69, 0x23, '5da9fe20dfae1ff92da94f405f83a588c89cf129c0460b3ff83d1214c3c407ad'),
    'set_player_walk_run_prefix': (0x139002a, 0x42b, '1bac9607673654fcd59ec471a61af2dfd52b8ddb149b8daa747d02644b7444ea'),
    'cov_01391e53': (0x1391e53, 0x2, 'c4173085fbd9d83401f5d5703efd98f81db0643629655fe6e7e755f94622ab64'),
    'move_speed': (0x13957b5, 0x7b1, 'e1978e20f0e66b199628d64c4d996d24088cc4be4845117fb99f8f58544f46a4'),
    'class_never_runs': (0x139bd24, 0x92, '7bba1b3ee6379d107d07f5a53c4ab980ea667d5bfbf63b62fa172235cd50057c'),
    'riding_pet': (0x139fcbf, 0x43, '7148c3b9fc0c2a1edc58268ea9492ac44c7a9451cbc2c6a583b4e790495ffeaa'),
    'world_gloves_b': (0x16a8325, 0x1d, '17f0aeb57410d9ce218d45e624eb9623a350adabe6e9f3ee665410055c606b6f'),
    'world_gloves_a': (0x16a88ae, 0x56, 'a950c295ba9e42b6237edf0aa1d22cd90d6c93384b014c375a7ed5cdb636dd08'),
    'cov_0191ba7b': (0x191ba7b, 0x47, 'c1bef2e7a1d1165de25c5a5d27fb5dd1b5447203a88d82151d55392bef017346'),
    'cov_0191c490': (0x191c490, 0x5, 'd543fc9ed5d14dcc829eaa5ce6cf76c03e07bf94b7e3d8b05faa6c407b56ccaa'),
    'cov_0191c5a0': (0x191c5a0, 0x2b, 'f8675b4976f7b8efc0bd917aebab734d11ca90222d20bcd2a166ce9914ed2b6e'),
    'cov_0194c780': (0x194c780, 0x7e, 'a85b8ca735fe41c77891b856a31d5bf7b9adfef3eaf8a813e5d7760b88b9d60e'),
    'cov_0194c9a7': (0x194c9a7, 0x54, '7d611e8d751aa8323c20aa0a0bdfb3a826b31f155c698d231133659722e37591'),
    'cov_0194cc7b': (0x194cc7b, 0x3c, '21bc1288b991185718be8173454906f71342c430083019a29fe503f38f7634eb'),
    'cov_0194cd00': (0x194cd00, 0x17, '927e1af787e6ffd14fe66df2ef4638a9c762ec10cd9796cf762444e15eef35bf'),
    'cov_01983110': (0x1983110, 0xb, '8b641bf9120fd530c5eb92f525a94c7d6676eb4346c08f12cde44f35ab45b9d4'),
}

PATH_FINDING2, MOVE_PATH, FINDER_CTOR, SET_MAP_DIMENSIONS = 0x012b0e85, 0x012b0846, 0x012b1855, 0x012b281e
CREATE_ANGLE, ANGLE_DIFFERENCE, TURN_ANGLE = 0x012aed9e, 0x012af218, 0x012aefff
HEURISTIC, STEP_COST = 0x012b1bcf, 0x012b1b67
MOVE_CHARACTER_POSITION, MOVE_CHARACTERS = 0x0137b351, 0x0137a7ce
CLEAR_LOOP_END = 0x0137a814
FINDER_GLOBAL = 0x06fce374
TERRAIN_WALL = 0x0b795420
OBJECT_FLAGS = 0x0b7b5420
WORLD_GLOBAL = 0x01cf15fc
CRT_MATH_MODE = 0x0bdcfbc8
SKILL_CHARACTER_INDEX = 0x01cf1168
INFINITE = 0x743aa380

STACK, STACK_SIZE = 0x30000000, 0x400000
RETURN = 0x31000000
ARENA, ARENA_SIZE = 0x32000000, 0x4000000
STUBS = 0x37000000
TEB, GDT = 0x38000000, 0x38100000
BSS = ((0x01ced000, 0x00200000), (0x06f00000, 0x00100000), (0x0a300000, 0x01b00000))
INITIAL_ESP = STACK + STACK_SIZE - 0x1000
FPCW, MXCSR = 0x027f, 0x1f80
POISON = 0xcd

# Client callees replaced by recorded stubs: (argument bytes the callee pops, kind, reason).
CLIENT_STUBS = {
    0x01983110: (0, 'eax', 'CRT malloc (operator new 0x0191ba7b): harness arena, poison-filled'),
    0x0191c490: (0, 'eax', 'CRT free (operator delete): no-op'),
    0x0194cd00: (0, 'eax', 'CRT memset: performed by the harness'),
    0x01206598: (0, 'eax', 'log writer (out-of-range target index): recorded'),
    0x00db732d: (0, 'eax', 'PathFinding2 siege-skill predicate 1 (subsystem query)'),
    0x00dabe97: (0, 'eax', 'PathFinding2 siege-skill predicate 2 (subsystem query)'),
    0x0095f6db: (0, 'eax', 'character table lookup (subsystem query)'),
    0x009a13f4: (0, 'eax', 'character object getter (subsystem query)'),
    0x013957b5: (0, 'fld', 'CharacterMoveSpeed (equipment/buff state): synthetic speed'),
    0x016cc9e2: (0, 'fld', 'RequestTerrainHeight: synthetic height'),
    0x0129dcda: (0, 'eax', 'helper item getter (subsystem query)'),
    0x0095fb27: (0, 'eax', 'character predicate (subsystem query)'),
    # NATIVE-PATH-002 auto move: the arrival handler and the UI notice helpers (no path state)
    0x0129c8b0: (0, 'eax', 'auto-move arrival handler (NPC/quest/UI actions): recorded'),
    0x00d51b91: (0, 'eax', 'notice box constructor (UI): no-op'),
    0x00d51baf: (8, 'eax', 'notice box setup (UI): no-op'),
    0x0095c204: (4, 'eax', 'notice box text append (UI): no-op'),
    0x00d51d4f: (8, 'eax', 'notice box show (UI): no-op'),
    0x00d51ba6: (0, 'eax', 'notice box destructor (UI): no-op'),
    0x0095c550: (4, 'eax', 'chat window getter (UI): no-op'),
    0x0095f09a: (0, 'eax', 'chat window present (UI): false, so no system message'),
    0x0095eba6: (0, 'eax', 'chat window handle release (UI): no-op'),
    # NATIVE-PATH-002 run counter and speed: subsystem queries left opaque
    0x00cd4ea8: (0, 'eax', 'item attribute table singleton getter (TLS-guarded static init)'),
    0x00cd5d29: (4, 'eax', 'item attribute record find (std::map): synthetic records by code'),
    0x009c104e: (0, 'eax', 'character extra-state manager singleton getter'),
    0x0106bdb7: (4, 'eax', 'manager predicate: the safe zone keeps the run counter (opaque input)'),
    0x0106bd76: (4, 'eax', 'manager predicate: SetPlayerStop keeps the run counter (opaque input)'),
    0x01295ade: (4, 'eax', 'buff list lookup (std::map on c + 0x35ac): synthetic buff set'),
    0x009fa30a: (0, 'eax', 'event-state singleton getter'),
    0x009fbb31: (4, 'eax', 'event special-state predicate (speed 8): opaque input'),
    0x00966c42: (0, 'eax', 'skill/option table lookup (buff 0x18b bonus argument)'),
    0x0117b5eb: (0, 'fld', 'buff 0x18b speed bonus value: synthetic'),
}


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def fbits(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]


def same(a, b):
    if math.isnan(a) and math.isnan(b):
        return True
    return fbits(a) == fbits(b)


load_pinned = pins.loader(ValueError, 'Input does not match pinned {label}: {path}')


class Stop(Exception):
    pass


class Guest:
    def __init__(self, text, data, flag, directions):
        import unicorn
        from unicorn import x86_const
        self.u, self.x = unicorn, x86_const
        for name, (start, size, digest) in ROUTINES.items():
            if hashlib.sha256(text[start - TEXT_BASE:start - TEXT_BASE + size]).hexdigest() != digest:
                raise ValueError(f'routine bytes differ from the pinned digest: {name}')
        uc = unicorn.Uc(unicorn.UC_ARCH_X86, unicorn.UC_MODE_32)
        self.uc = uc
        uc.mem_map(TEXT_BASE, (TEXT_BYTES + 0xfff) & ~0xfff, unicorn.UC_PROT_READ | unicorn.UC_PROT_EXEC)
        uc.mem_write(TEXT_BASE, text)
        uc.mem_map(DATA_BASE, (DATA_BYTES + 0xfff) & ~0xfff, unicorn.UC_PROT_READ | unicorn.UC_PROT_EXEC)
        uc.mem_write(DATA_BASE, data)
        for base, size in BSS + ((STACK, STACK_SIZE), (ARENA, ARENA_SIZE), (TEB, 0x1000)):
            uc.mem_map(base, size, unicorn.UC_PROT_READ | unicorn.UC_PROT_WRITE)
        uc.mem_map(RETURN, 0x1000, unicorn.UC_PROT_ALL)
        uc.mem_map(STUBS, 0x10000, unicorn.UC_PROT_ALL)
        uc.mem_map(GDT, 0x1000, unicorn.UC_PROT_READ)
        teb = struct.pack('<HHBBBB', 0xfff, TEB & 0xffff, (TEB >> 16) & 0xff, 0x92, 0x40, (TEB >> 24) & 0xff)
        flat = struct.pack('<HHBBBB', 0xffff, 0, 0, 0x92, 0xcf, 0)
        uc.mem_write(GDT, bytes(8) + teb + flat)
        uc.reg_write(x86_const.UC_X86_REG_GDTR, (0, GDT, 23, 0))
        uc.reg_write(x86_const.UC_X86_REG_FS, 1 << 3)
        for register in (x86_const.UC_X86_REG_SS, x86_const.UC_X86_REG_DS, x86_const.UC_X86_REG_ES):
            uc.reg_write(register, 2 << 3)
        uc.mem_write(TEB, struct.pack('<I', 0xffffffff))
        uc.mem_write(FLAG_ADDRESS, flag)
        uc.mem_write(DIRECTIONS_ADDRESS, directions)
        uc.mem_write(CRT_MATH_MODE, struct.pack('<I', 1))
        uc.hook_add(unicorn.UC_HOOK_MEM_UNMAPPED, self._unmapped)
        self.violation = None
        self.calls = []
        self.values = {}
        self.arena_top = ARENA
        self.stubs = {}
        for index, (address, (cleanup, kind, reason)) in enumerate(sorted(CLIENT_STUBS.items())):
            snippet = STUBS + 0x20 * index
            slot = snippet + 0x18
            load = b'\xa1' if kind == 'eax' else b'\xd9\x05'
            tail = b'\xc3' if cleanup == 0 else b'\xc2' + struct.pack('<H', cleanup)
            uc.mem_write(snippet, load + struct.pack('<I', slot) + tail)
            self.stubs[address] = (snippet, slot, kind)
            uc.hook_add(unicorn.UC_HOOK_CODE, self._stub, begin=address, end=address)
        self.handlers = {
            0x01983110: self._malloc,
            0x0191c490: lambda args, ecx: 0,
            0x0194cd00: self._memset,
            0x01206598: lambda args, ecx: 0,
        }

    def _unmapped(self, uc, access, address, size, value, ignored):
        if self.violation is None:
            self.violation = ('unmapped', hex(address), size, hex(uc.reg_read(self.x.UC_X86_REG_EIP)))
        return False

    def _args(self, count):
        esp = self.uc.reg_read(self.x.UC_X86_REG_ESP)
        return struct.unpack(f'<{count + 1}I', bytes(self.uc.mem_read(esp, 4 + 4 * count)))

    def _stub(self, uc, address, size, ignored):
        if address not in self.stubs:
            return
        snippet, slot, kind = self.stubs[address]
        words = self._args(4)
        handler = self.handlers.get(address)
        ecx = uc.reg_read(self.x.UC_X86_REG_ECX)
        value = handler(words[1:], ecx) if handler else self.values.get(address, 0)
        self.calls.append((address, words[1:]))
        uc.mem_write(slot, struct.pack('<I', value & 0xffffffff) if kind == 'eax' else struct.pack('<f', value))
        uc.reg_write(self.x.UC_X86_REG_EIP, snippet)

    def _malloc(self, args, ecx):
        size = max(args[0], 1)
        address = (self.arena_top + 15) & ~15
        if address + size > ARENA + ARENA_SIZE:
            raise Stop('arena exhausted')
        self.arena_top = address + size
        self.uc.mem_write(address, bytes([POISON]) * size)
        return address

    def _memset(self, args, ecx):
        destination, value, count = args[0], args[1] & 0xff, args[2]
        self.uc.mem_write(destination, bytes([value]) * count)
        return destination

    def reset_arena(self):
        self.arena_top = ARENA

    def unstubbed(self, *addresses):
        """Run these callees as client code for the duration (they are stubbed for the other families)."""
        guest = self

        class Scope:
            def __enter__(self):
                self.saved = {a: guest.stubs.pop(a) for a in addresses if a in guest.stubs}

            def __exit__(self, *ignored):
                guest.stubs.update(self.saved)
        return Scope()

    def alloc(self, size, fill=0):
        address = self._malloc((size,), 0)
        self.put(address, bytes([fill]) * size)
        return address

    def put(self, address, payload):
        self.uc.mem_write(address, bytes(payload))

    def get(self, address, size):
        return bytes(self.uc.mem_read(address, size))

    def u32(self, address):
        return struct.unpack('<I', self.get(address, 4))[0]

    def i32(self, address):
        return struct.unpack('<i', self.get(address, 4))[0]

    def f32at(self, address):
        return struct.unpack('<f', self.get(address, 4))[0]

    def call(self, start, words, ecx=0, until=RETURN, count=400_000_000):
        uc, x = self.uc, self.x
        self.violation = None
        self.calls = []
        frame = struct.pack('<I', RETURN) + b''.join(struct.pack('<I', w & 0xffffffff) for w in words)
        esp = INITIAL_ESP - 0x100
        self.put(esp, frame)
        uc.reg_write(x.UC_X86_REG_ESP, esp)
        uc.reg_write(x.UC_X86_REG_EBP, 0x5a5a5a5a)
        uc.reg_write(x.UC_X86_REG_ECX, ecx)
        for reg in (x.UC_X86_REG_EAX, x.UC_X86_REG_EDX, x.UC_X86_REG_EBX, x.UC_X86_REG_ESI, x.UC_X86_REG_EDI):
            uc.reg_write(reg, 0xdeadbeef)
        uc.reg_write(x.UC_X86_REG_EFLAGS, 2)
        uc.reg_write(x.UC_X86_REG_FPCW, FPCW)
        uc.reg_write(x.UC_X86_REG_FPSW, 0)
        uc.reg_write(x.UC_X86_REG_FPTAG, 0xffff)
        uc.reg_write(x.UC_X86_REG_MXCSR, MXCSR)
        error = None
        try:
            uc.emu_start(start, until, count=count)
        except self.u.UcError as failure:
            error = str(failure)
        eip = uc.reg_read(x.UC_X86_REG_EIP)
        if self.violation or error or eip != until:
            raise Stop(f'{hex(start)}: {self.violation or error or "stopped at " + hex(eip)}')
        return uc.reg_read(x.UC_X86_REG_EAX)

    def st0_float(self):
        """x87 st(0) of a float-returning routine, as binary32 (the callers
        store it with fstp dword)."""
        top = (self.uc.reg_read(self.x.UC_X86_REG_FPSW) >> 11) & 7
        mantissa, high = self.uc.reg_read(self.x.UC_X86_REG_FP0 + top)
        sign = -1.0 if high & 0x8000 else 1.0
        exponent = high & 0x7fff
        if exponent == 0x7fff:
            return math.copysign(math.inf, sign) if mantissa == 1 << 63 else math.nan
        if mantissa == 0:
            return math.copysign(0.0, sign)
        return f32(sign * math.ldexp(mantissa, exponent - 16383 - 63))


# ---------------- C library ----------------

class QueueEntry(ctypes.Structure):
    _fields_ = [('index', ctypes.c_int32), ('cost', ctypes.c_int32), ('sequence', ctypes.c_uint32)]


class Finder(ctypes.Structure):
    _fields_ = [('width', ctypes.c_int32), ('height', ctypes.c_int32), ('size', ctypes.c_int32),
                ('wall', ctypes.POINTER(ctypes.c_uint16)), ('object_flags', ctypes.POINTER(ctypes.c_uint32)),
                ('count', ctypes.c_int32), ('path_x', ctypes.c_uint8 * 500), ('path_y', ctypes.c_uint8 * 500),
                ('end_x', ctypes.c_int16), ('end_y', ctypes.c_int16), ('mark', ctypes.POINTER(ctypes.c_uint8)),
                ('touched_min', ctypes.c_int32), ('touched_max', ctypes.c_int32),
                ('cost', ctypes.POINTER(ctypes.c_int32)), ('parent_x', ctypes.POINTER(ctypes.c_int32)),
                ('parent_y', ctypes.POINTER(ctypes.c_int32)), ('queue', ctypes.POINTER(QueueEntry)),
                ('queue_count', ctypes.c_int32), ('queue_capacity', ctypes.c_int32),
                ('queue_sequence', ctypes.c_uint32), ('pops', ctypes.c_int32), ('pushes', ctypes.c_int32),
                ('index_errors', ctypes.c_int32), ('directions', ctypes.c_void_p)]


class ClientPath(ctypes.Structure):
    _fields_ = [('current', ctypes.c_uint8), ('current_float', ctypes.c_uint8), ('count', ctypes.c_uint8),
                ('x', ctypes.c_uint8 * 15), ('y', ctypes.c_uint8 * 15)]


class AutoPath(ctypes.Structure):
    _fields_ = [('path', ClientPath), ('mode', ctypes.c_int32), ('waypoint_x', ctypes.c_int16),
                ('waypoint_y', ctypes.c_int16), ('flag', ctypes.c_int32), ('target_x', ctypes.c_int16),
                ('target_y', ctypes.c_int16), ('list_head', ctypes.c_int32), ('list_count', ctypes.c_int32),
                ('list_x', ctypes.c_int16 * 500), ('list_y', ctypes.c_int16 * 500)]


class AutoEffects(ctypes.Structure):
    _fields_ = [('target_set', ctypes.c_uint8), ('target', ctypes.c_int32 * 2), ('selection_cleared', ctypes.c_uint8),
                ('arrived', ctypes.c_uint8), ('failure_notice', ctypes.c_uint8)]


class Mover(ctypes.Structure):
    _fields_ = [('tile_x', ctypes.c_int32), ('tile_y', ctypes.c_int32), ('position', ctypes.c_float * 3),
                ('angle', ctypes.c_float * 3), ('path', ClientPath)]


def load_library(directory=None):
    directory = Path(directory) if directory else ROOT / 'reconstructed' / 'path'
    subprocess.run(['make', '-C', str(directory)], check=True, capture_output=True)
    suffix = 'dylib' if sys.platform == 'darwin' else 'so'
    lib = ctypes.CDLL(str(directory / f'libclient_path.{suffix}'))
    P = ctypes.POINTER
    lib.mu_path_finder_init.argtypes = [P(Finder), ctypes.c_int32, ctypes.c_int32, P(ctypes.c_uint16),
                                        P(ctypes.c_uint32)]
    lib.mu_path_finder_free.argtypes = [P(Finder)]
    lib.mu_path_find.argtypes = [P(Finder)] + [ctypes.c_int32] * 4 + [ctypes.c_int, ctypes.c_int32, ctypes.c_int,
                                                                      ctypes.c_float, ctypes.c_int32, ctypes.c_int32]
    lib.mu_path_finding2.argtypes = [P(Finder)] + [ctypes.c_int32] * 4 + [P(ClientPath), ctypes.c_float,
                                                                          ctypes.c_int32, ctypes.c_int]
    lib.mu_path_heuristic.argtypes = [ctypes.c_int32] * 4
    lib.mu_path_step_cost.argtypes = [ctypes.c_int32] * 2
    for name in ('mu_path_create_angle',):
        getattr(lib, name).argtypes = [ctypes.c_float] * 4
        getattr(lib, name).restype = ctypes.c_float
    lib.mu_path_angle_difference.argtypes = [ctypes.c_float, ctypes.c_float, ctypes.c_int]
    lib.mu_path_angle_difference.restype = ctypes.c_float
    lib.mu_path_turn_angle.argtypes = [ctypes.c_float] * 3
    lib.mu_path_turn_angle.restype = ctypes.c_float
    lib.mu_path_move.argtypes = [P(Mover), ctypes.c_int, P(ctypes.c_float)]
    lib.mu_path_step_position.argtypes = [P(ctypes.c_float), P(ctypes.c_float), ctypes.c_float]
    lib.mu_path_long.argtypes = [P(Finder)] + [ctypes.c_int32] * 4 + [ctypes.c_int, P(AutoPath), ctypes.c_float,
                                                                      ctypes.c_int32]
    lib.mu_auto_path_init.argtypes = [P(AutoPath)]
    lib.mu_auto_path_reset.argtypes = [P(AutoPath)]
    lib.mu_auto_path_next.argtypes = [P(AutoPath)]
    lib.mu_auto_path_start.argtypes = [P(AutoPath), P(Finder)] + [ctypes.c_int32] * 7 + [P(AutoEffects)]
    lib.mu_auto_path_refresh.argtypes = [P(AutoPath), P(Finder)] + [ctypes.c_int32] * 4 + [P(AutoEffects)]
    lib.mu_auto_path_refresh.restype = None
    lib.mu_auto_path_arrive.argtypes = [P(AutoPath)]
    lib.mu_auto_path_arrive.restype = None
    lib.mu_path_clear_characters.argtypes = [P(ctypes.c_uint16), ctypes.c_int32]
    lib.mu_path_stamp_character.argtypes = [P(ctypes.c_uint16), ctypes.c_int32, ctypes.c_int32]
    return lib


class Tally:
    def __init__(self):
        self.results = {}

    def add(self, family, ok, detail=None):
        entry = self.results.setdefault(family, {'cases': 0, 'mismatches': 0, 'first': None})
        entry['cases'] += 1
        if not ok:
            entry['mismatches'] += 1
            if entry['first'] is None:
                entry['first'] = detail


# ---------------- grids ----------------

WALL_VALUES = [0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x0c, 0x14, 0x21, 0x22, 0x24, 0x100, 0x1000, 0x05]


def grid_noise(rng, density, values=None):
    values = values or WALL_VALUES
    grid = [0] * 65536
    for i in range(65536):
        if rng.random() < density:
            grid[i] = rng.choice(values)
    return grid


def grid_rooms(rng):
    grid = [0] * 65536
    for _ in range(rng.randrange(40, 160)):
        x0, y0 = rng.randrange(0, 250), rng.randrange(0, 250)
        w, h = rng.randrange(1, 30), rng.randrange(1, 30)
        value = rng.choice([0x04, 0x08, 0x10, 0x0c, 0x04])
        hollow = rng.random() < 0.5
        for y in range(y0, min(256, y0 + h)):
            for x in range(x0, min(256, x0 + w)):
                if not hollow or x in (x0, x0 + w - 1) or y in (y0, y0 + h - 1):
                    grid[y * 256 + x] = value
        if hollow and w > 2 and h > 2 and rng.random() < 0.6:   # a door
            grid[y0 * 256 + x0 + w // 2] = 0
    for _ in range(rng.randrange(0, 400)):
        grid[rng.randrange(65536)] |= rng.choice([0x01, 0x02, 0x20])
    return grid


def grid_maze(rng):
    grid = [0x04] * 65536
    cells = 64
    seen = set()
    stack = [(rng.randrange(cells), rng.randrange(cells))]
    while stack:
        cx, cy = stack[-1]
        seen.add((cx, cy))
        grid[(cy * 4 + 1) * 256 + cx * 4 + 1] = 0
        grid[(cy * 4 + 1) * 256 + cx * 4 + 2] = 0
        grid[(cy * 4 + 2) * 256 + cx * 4 + 1] = 0
        grid[(cy * 4 + 2) * 256 + cx * 4 + 2] = 0
        options = [(cx + dx, cy + dy, dx, dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                   if 0 <= cx + dx < cells and 0 <= cy + dy < cells and (cx + dx, cy + dy) not in seen]
        if not options:
            stack.pop()
            continue
        nx, ny, dx, dy = rng.choice(options)
        for k in range(1, 4):
            for o in (1, 2):
                if dx:
                    grid[(cy * 4 + o) * 256 + cx * 4 + (2 if dx > 0 else 1) + dx * k] = 0
                else:
                    grid[(cy * 4 + (2 if dy > 0 else 1) + dy * k) * 256 + cx * 4 + o] = 0
        stack.append((nx, ny))
    return grid


CROSS = {'lib': None}   # optional second port (--cross-library), compared on distance-0 searches


def load_cross_library(path):
    lib = ctypes.CDLL(str(path))
    lib.mu_path_finder_bytes.restype = ctypes.c_uint32
    lib.mu_path_finder_init.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint16)]
    lib.mu_path_finding2.argtypes = [ctypes.c_void_p] + [ctypes.c_int32] * 4 + [
        ctypes.POINTER(ClientPath), ctypes.c_float, ctypes.c_int32, ctypes.c_uint8,
        ctypes.POINTER((ctypes.c_int32 * 2) * 8), ctypes.POINTER(ctypes.c_uint32)]
    return lib


class World:
    """One TerrainWall/object-flag state, mirrored in the guest and in C."""

    def __init__(self, guest, lib, grid, objects=None):
        self.guest, self.lib = guest, lib
        self.wall = (ctypes.c_uint16 * 65536)(*grid)
        self.objects = (ctypes.c_uint32 * 65536)(*(objects or [0] * 65536))
        guest.put(TERRAIN_WALL, bytes(self.wall))
        guest.put(OBJECT_FLAGS, bytes(self.objects))
        # client finder object: operator new + ctor + SetMapDimensions(256, 256, TerrainWall)
        guest.reset_arena()
        self.object = guest.alloc(0x428, POISON)
        guest.call(FINDER_CTOR, [], ecx=self.object)
        guest.call(SET_MAP_DIMENSIONS, [256, 256, TERRAIN_WALL], ecx=self.object)
        guest.put(self.object + 0x10, bytes(0x3fc - 0x10))   # count + path arrays: zero (harness)
        guest.put(self.object + 0x404, struct.pack('<Ii', INFINITE, -1))   # reset state (harness)
        guest.put(FINDER_GLOBAL, struct.pack('<I', self.object))
        self.c = Finder()
        if lib.mu_path_finder_init(ctypes.byref(self.c), 256, 256, self.wall, self.objects):
            raise MemoryError
        self.out = guest.alloc(0x40)
        self.cross = None
        if CROSS['lib'] is not None:
            other = CROSS['lib']
            self.cross_wall = (ctypes.c_uint16 * 65536)(*grid)
            self.cross = ctypes.create_string_buffer(other.mu_path_finder_bytes())
            other.mu_path_finder_init(self.cross, self.cross_wall)
            self.cross_directions = ((ctypes.c_int32 * 2) * 8)(*[(ctypes.c_int32 * 2)(*d) for d in
                                                               [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0),
                                                                (-1, 1), (0, 1), (1, 1)]])

    def close(self):
        self.lib.mu_path_finder_free(ctypes.byref(self.c))

    def set_wall(self, index, value):
        self.wall[index] = value
        if self.cross is not None:
            self.cross_wall[index] = value
        self.guest.put(TERRAIN_WALL + 2 * index, struct.pack('<H', value))

    def search(self, sx, sy, tx, ty, distance, wall_level, siege=False):
        g, o = self.guest, self.object
        filler = bytes([0x5a] * 0x21)
        g.put(self.out, filler)
        g.values[0x00db732d] = 1 if siege else 0
        g.values[0x00dabe97] = 1
        g.values[0x0095f6db] = 0
        character = g.alloc(0x3300)
        g.put(character + 0x32b0, struct.pack('<I', 0xa3b))
        g.values[0x009a13f4] = character
        g.put(SKILL_CHARACTER_INDEX, struct.pack('<I', 7))
        result = g.call(PATH_FINDING2, [sx, sy, tx, ty, self.out, fbits(distance), wall_level]) & 0xff
        guest_state = {
            'result': result,
            'path': g.get(self.out, 0x21),
            'count': g.i32(o + 0x10),
            'path_x': g.get(o + 0x14, 500), 'path_y': g.get(o + 0x208, 500),
            'end': struct.unpack('<hh', g.get(o + 0x3fc, 4)),
            'touched': struct.unpack('<ii', g.get(o + 0x404, 8)),
            'tree': struct.unpack('<II', g.get(o + 0x418 + 4, 8)),
            'wall': g.get(TERRAIN_WALL, 0x20000),
        }
        mark = g.get(g.u32(o + 0x400), 65536)
        cost = struct.unpack('<65536i', g.get(g.u32(o + 0x40c), 0x40000))
        px = struct.unpack('<65536i', g.get(g.u32(o + 0x410), 0x40000))
        py = struct.unpack('<65536i', g.get(g.u32(o + 0x414), 0x40000))
        path = ClientPath()
        ctypes.memmove(ctypes.byref(path), filler, 0x21)
        c = self.c
        want = self.lib.mu_path_finding2(ctypes.byref(c), sx, sy, tx, ty, ctypes.byref(path), distance, wall_level,
                                         1 if siege else 0)
        c_mark = ctypes.string_at(c.mark, 65536)
        c_state = {
            'result': want & 0xff,
            'path': bytes(path),
            'count': c.count,
            'path_x': bytes(c.path_x), 'path_y': bytes(c.path_y),
            'end': (c.end_x, c.end_y),
            'touched': (c.touched_min, c.touched_max),
            'tree': (0, 0),
            'wall': bytes(self.wall),
        }
        diff = {k: 'differs' for k in guest_state if guest_state[k] != c_state[k]}
        if mark != c_mark:
            diff['mark'] = 'differs'
        start = (sy * 256 + sx) if 0 <= sx < 256 and 0 <= sy < 256 else -1
        for i in range(65536):
            m = mark[i]
            if m & 2 and cost[i] != c.cost[i]:
                diff['cost'] = (i, cost[i], c.cost[i])
                break
            if m & 1 and i != start and (px[i] != c.parent_x[i] or py[i] != c.parent_y[i]):
                diff['parent'] = (i, (px[i], py[i]), (c.parent_x[i], c.parent_y[i]))
                break
        if self.cross is not None and distance == 0.0:
            other = ClientPath()
            ctypes.memmove(ctypes.byref(other), filler, 0x21)
            r = CROSS['lib'].mu_path_finding2(self.cross, sx, sy, tx, ty, ctypes.byref(other), distance, wall_level,
                                              1 if siege else 0, ctypes.byref(self.cross_directions), self.objects)
            self.cross_result = (r & 0xff == result and bytes(other) == guest_state['path']
                                 and bytes(self.cross_wall) == guest_state['wall'])
            self.cross_detail = {'case': (sx, sy, tx, ty, wall_level, siege), 'client': (result, guest_state['path'].hex()),
                                 'cross': (r, bytes(other).hex()),
                                 'start_wall': self.wall[sy * 256 + sx] if 0 <= sx < 256 and 0 <= sy < 256 else None,
                                 'target_wall': self.wall[ty * 256 + tx] if 0 <= tx < 256 and 0 <= ty < 256 else None}
        else:
            self.cross_result = None
        stats = {'nodes': path.count if want else 0, 'pops': c.pops, 'closed': sum(1 for m in mark if m & 2)}
        return diff, guest_state, c_state, stats


def walkable(grid, x, y, level=2):
    return 0 <= x < 256 and 0 <= y < 256 and (grid[y * 256 + x] & 0x1e) < level


# distances equal to sqrt(k*k + i*i) for some outer-ring offset (the > test)
EXACT_DISTANCES = [5.0, f32(math.sqrt(5)), f32(math.sqrt(8)), f32(math.sqrt(13)), 3.0, 0.5]


def grid_safezone(rng):
    """Whole map safe zone with dense character tiles: level 2 often fails
    where PathFinding2's level-4 retry passes."""
    density = rng.choice([0.2, 0.35, 0.5])
    grid = [0x01] * 65536
    for i in range(65536):
        r = rng.random()
        if r < density:
            grid[i] = 0x03
        elif r < density + 0.03:
            grid[i] = 0x05
    return grid


def pick_search(rng, grid):
    for _ in range(200):
        sx, sy = rng.randrange(1, 255), rng.randrange(1, 255)
        if walkable(grid, sx, sy) or rng.random() < 0.05:
            break
    span = rng.choice([2, 4, 8, 15, 25, 40])
    tx = min(255, max(0, sx + rng.randint(-span, span)))
    ty = min(255, max(0, sy + rng.randint(-span, span)))
    if rng.random() < 0.03:
        sx = 0 if rng.random() < 0.5 else sx
        sy = 0 if sx else sy
    if rng.random() < 0.03:
        tx, ty = sx, sy
    distance = rng.choice([0.0] * 6 + [1.0, 1.0, 1.5, 2.0, 2.9, 4.0] + EXACT_DISTANCES)
    level = rng.choice([2] * 6 + [4, 4, 1, 8, 0x20, 3])
    siege = rng.random() < 0.08
    return sx, sy, tx, ty, distance, level, siege


def run_search_family(guest, lib, tally, rng, count, family='PathFinding2 synthetic', grids=None, stats=None):
    makers = grids or [lambda r: grid_noise(r, 0.1), grid_safezone, lambda r: grid_noise(r, 0.25), grid_rooms,
                       lambda r: grid_noise(r, 0.0), grid_maze, lambda r: grid_noise(r, 0.4)]
    done, made = 0, 0
    while done < count:
        maker = makers[made % len(makers)] if isinstance(makers, list) else makers
        made += 1
        grid = maker(rng)
        objects = None
        if rng.random() < 0.3:
            objects = [1 if rng.random() < 0.03 else 0 for _ in range(65536)]
        world = World(guest, lib, grid, objects)
        try:
            for _ in range(min(6, count - done)):
                sx, sy, tx, ty, distance, level, siege = pick_search(rng, grid)
                if maker is grid_safezone and rng.random() < 0.8 and 2 <= sx <= 253 and 2 <= sy <= 253 and \
                        max(abs(tx - sx), abs(ty - sy)) > 1:
                    # start enclosed by characters inside the safe zone: only the level-4 retry escapes
                    for dx in (-1, 0, 1):
                        for dy in (-1, 0, 1):
                            if dx or dy:
                                world.set_wall((sy + dy) * 256 + sx + dx, 0x03)
                    level, distance, siege = 2, rng.choice([0.0, 0.0, 1.0]), False
                    world.set_wall(ty * 256 + tx, 0x01)
                if rng.random() < 0.3:   # a character tile appears or leaves between searches
                    index = rng.randrange(65536)
                    world.set_wall(index, world.wall[index] ^ 0x02)
                try:
                    diff, got, want, st = world.search(sx, sy, tx, ty, distance, level, siege)
                except Stop as stop:
                    tally.add(family, False, {'stop': str(stop), 'case': (sx, sy, tx, ty, distance, level, siege)})
                    done += 1
                    continue
                if stats is not None:
                    stats.append(st)
                tally.add(family, not diff, {'diff': diff, 'case': (sx, sy, tx, ty, distance, level, siege),
                                             'got': got['result'], 'want': want['result']})
                if world.cross_result is not None:
                    tally.add('cross: second port vs client (synthetic)', world.cross_result, world.cross_detail)
                done += 1
        finally:
            world.close()


def installed_grid(tool, root, world):
    out = subprocess.run([str(tool), 'att', root, '--world', str(world), '--out', '-'], capture_output=True)
    if out.returncode != 0 or len(out.stdout) != 0x20000:
        return None
    return list(struct.unpack('<65536H', out.stdout))


def run_installed_family(guest, lib, tally, rng, count, root, tool, worlds, stats=None):
    per = max(1, count // max(1, len(worlds)))
    loaded, seen = [], set()
    for world_index in worlds:
        grid = installed_grid(tool, root, world_index)
        if grid is None:
            continue
        digest = hashlib.sha256(struct.pack('<65536H', *grid)).hexdigest()
        if digest in seen:   # event worlds sharing a folder
            continue
        seen.add(digest)
        free = [i for i in range(65536) if (grid[i] & 0x1e) < 2 and 0 < i % 256 and i >= 256]
        if not free:
            continue
        loaded.append(world_index)
        world = World(guest, lib, grid)
        try:
            for _ in range(per):
                s = rng.choice(free)
                sx, sy = s % 256, s // 256
                span = rng.choice([3, 8, 15, 25, 40])
                if rng.random() < 0.7:
                    near = [rng.choice(free) for _ in range(40)]
                    near = [i for i in near if abs(i % 256 - sx) <= span and abs(i // 256 - sy) <= span] or [s]
                    t = rng.choice(near)
                    tx, ty = t % 256, t // 256
                else:   # anywhere nearby, walls included (unreachable targets)
                    tx = min(255, max(0, sx + rng.randint(-span, span)))
                    ty = min(255, max(0, sy + rng.randint(-span, span)))
                distance = rng.choice([0.0, 0.0, 0.0, 1.0])
                try:
                    diff, got, want, st = world.search(sx, sy, tx, ty, distance, 2)
                except Stop as stop:
                    tally.add(f'PathFinding2 installed', False, {'stop': str(stop), 'world': world_index})
                    continue
                if stats is not None:
                    stats.append(st)
                tally.add('PathFinding2 installed', not diff,
                          {'diff': diff, 'world': world_index, 'case': (sx, sy, tx, ty, distance)})
                if world.cross_result is not None:
                    tally.add('cross: second port vs client (installed)', world.cross_result, world.cross_detail)
                path = got['path']
                if got['result'] and rng.random() < 0.35:
                    n = path[2]
                    xs, ys = list(path[3:3 + n]), list(path[0x12:0x12 + n])
                    walker = guest.alloc(CHAR_SIZE)
                    ok, detail, steps = compare_walk(guest, lib, walker, xs, ys, random_angle(rng),
                                                     rng.choice(SPEEDS))
                    tally.add('walk on installed paths', ok, detail)
        finally:
            world.close()
    tally.results.setdefault('PathFinding2 installed', {'cases': 0, 'mismatches': 0, 'first': None})['worlds'] = loaded


# ---------------- following ----------------

CHAR_SIZE = 0x3600
OBJ = 0x3254


def random_path(rng, count=None):
    count = count or rng.randint(1, 15)
    x, y = rng.randrange(20, 236), rng.randrange(20, 236)
    xs, ys = [x], [y]
    for _ in range(count - 1):
        dx, dy = rng.choice([(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)])
        x, y = x + dx, y + dy
        xs.append(x)
        ys.append(y)
    return xs, ys


def write_mover(guest, address, m):
    guest.put(address + 0x180, struct.pack('<ii', m.tile_x, m.tile_y))
    guest.put(address + 0x3194, bytes(m.path))
    guest.put(address + OBJ + 0x158, struct.pack('<3f', *m.position))
    guest.put(address + OBJ + 0x164, struct.pack('<3f', *m.angle))


def read_mover(guest, address):
    return {'tile': struct.unpack('<ii', guest.get(address + 0x180, 8)),
            'path': guest.get(address + 0x3194, 0x21),
            'position': struct.unpack('<3f', guest.get(address + OBJ + 0x158, 12)),
            'angle': struct.unpack('<3f', guest.get(address + OBJ + 0x164, 12))}


def c_mover_state(m):
    return {'tile': (m.tile_x, m.tile_y), 'path': bytes(m.path), 'position': tuple(m.position),
            'angle': tuple(m.angle)}


def states_equal(a, b):
    for key in a:
        x, y = a[key], b[key]
        if isinstance(x, tuple) and x and isinstance(x[0], float):
            if not all(same(p, q) for p, q in zip(x, y)):
                return False
        elif x != y:
            return False
    return True


def random_angle(rng):
    r = rng.random()
    if r < 0.1:
        return rng.choice([0.0, 45.0, 90.0, 180.0, 270.0, 360.0, -0.0, -45.0, -180.0, 359.99997, 180.00002, 179.99998])
    if r < 0.2:
        return f32(rng.uniform(-360.0, 720.0))
    return f32(rng.uniform(0.0, 360.0))


def run_move_family(guest, lib, tally, rng, count):
    guest.reset_arena()
    address = guest.alloc(CHAR_SIZE)
    for _ in range(count):
        xs, ys = random_path(rng)
        m = Mover()
        m.path.count = len(xs)
        for i, (x, y) in enumerate(zip(xs, ys)):
            m.path.x[i], m.path.y[i] = x, y
        if rng.random() < 0.05:
            m.path.count = rng.choice([0, len(xs) + rng.randint(0, 3)])
        m.path.current = rng.randrange(0, max(1, m.path.count + (1 if rng.random() < 0.1 else 0)))
        m.path.current_float = rng.choice([0, 0, 1, 2, 3, 4 if rng.random() < 0.05 else 0])
        m.tile_x, m.tile_y = rng.randrange(256), rng.randrange(256)
        i = min(m.path.current, max(0, len(xs) - 1))
        cx, cy = (xs[i] + 0.5) * 100, (ys[i] + 0.5) * 100
        spread = rng.choice([5.0, 25.0, 31.0, 60.0, 150.0])
        m.position[0] = f32(cx + rng.uniform(-spread, spread))
        m.position[1] = f32(cy + rng.uniform(-spread, spread))
        m.position[2] = f32(rng.uniform(0, 500))
        m.angle[0], m.angle[1], m.angle[2] = 0.0, 0.0, random_angle(rng)
        turn = rng.choice([0, 1, 1, 1])
        if rng.random() < 0.25:   # straight path along x or y, position on the line: exact axis angles
            along_x = rng.random() < 0.5
            n = rng.randint(2, 15)
            x0, y0 = rng.randrange(20, 220), rng.randrange(20, 220)
            step = rng.choice([1, -1])
            m.path.count = n
            for i in range(n):
                m.path.x[i] = x0 + (i * step if along_x else 0)
                m.path.y[i] = y0 + (0 if along_x else i * step)
            m.path.current = rng.randrange(0, n)
            m.path.current_float = rng.choice([0, 1, 2, 3])
            i = m.path.current
            if along_x:
                m.position[0] = f32((m.path.x[i] + 0.5) * 100 + rng.uniform(-80, 80))
                m.position[1] = f32((y0 + 0.5) * 100)
            else:
                m.position[0] = f32((x0 + 0.5) * 100)
                m.position[1] = f32((m.path.y[i] + 0.5) * 100 + rng.uniform(-80, 80))
            m.angle[2] = rng.choice([0.0, 45.0, 135.0, 225.0, 315.0, 90.0, 270.0, 180.0, 44.99999, 45.00001])
            turn = 1
        write_mover(guest, address, m)
        try:
            result = guest.call(MOVE_PATH, [address, turn]) & 0xff
        except Stop as stop:
            tally.add('MovePath', False, {'stop': str(stop)})
            continue
        got = read_mover(guest, address)
        want_result = lib.mu_path_move(ctypes.byref(m), turn, None)
        want = c_mover_state(m)
        ok = result == (want_result & 0xff) and states_equal(got, want)
        tally.add('MovePath', ok, {'got': got, 'want': want, 'result': (result, want_result)})


def compare_walk(guest, lib, address, xs, ys, angle, speed):
    """MovePath (turning) then MoveCharacterPosition per 40 ms step from the
    first node to the arrival, compared after every step."""
    m = Mover()
    m.path.count = len(xs)
    for i, (x, y) in enumerate(zip(xs, ys)):
        m.path.x[i], m.path.y[i] = x, y
    m.tile_x, m.tile_y = xs[0], ys[0]
    m.position[0], m.position[1] = f32((xs[0] + 0.5) * 100), f32((ys[0] + 0.5) * 100)
    m.position[2] = 0.0
    m.angle[2] = angle
    guest.values[0x013957b5] = speed
    guest.values[0x016cc9e2] = 0.0
    guest.put(WORLD_GLOBAL, struct.pack('<i', -1))
    guest.put(address + OBJ + 0x5c, struct.pack('<I', 0xa91))
    write_mover(guest, address, m)
    for step in range(400):
        try:
            result = guest.call(MOVE_PATH, [address, 1]) & 0xff
            if not result:
                guest.call(MOVE_CHARACTER_POSITION, [address])
        except Stop as stop:
            return False, {'stop': str(stop), 'step': step}, step
        want_result = lib.mu_path_move(ctypes.byref(m), 1, None)
        if not want_result:
            lib.mu_path_step_position(m.position, m.angle, speed)
            m.position[2] = 0.0
        got, want = read_mover(guest, address), c_mover_state(m)
        if result != (want_result & 0xff) or not states_equal(got, want):
            return False, {'step': step, 'got': got, 'want': want, 'speed': speed}, step + 1
        if result:
            return True, None, step + 1
    return True, {'note': 'no arrival in 400 steps'}, 400


SPEEDS = [12.0, 15.0, 8.0, 16.0, 17.0, 19.0, 20.0, 7.5, 4.95]


def run_walk_family(guest, lib, tally, rng, count):
    guest.reset_arena()
    address = guest.alloc(CHAR_SIZE)
    for _ in range(count):
        xs, ys = random_path(rng, rng.randint(2, 15))
        ok, detail, steps = compare_walk(guest, lib, address, xs, ys, random_angle(rng), rng.choice(SPEEDS))
        tally.add('walk (MovePath + MoveCharacterPosition)', ok, detail)


def run_angle_family(guest, lib, tally, rng, count):
    specials = [0.0, -0.0, 0.00005, -0.00005, 0.0001, -0.0001, 0.00011, math.inf, -math.inf, math.nan, 1e30, -1e30]
    for _ in range(count):
        if rng.random() < 0.15:
            x1, y1 = rng.choice(specials), rng.choice(specials)
            x2, y2 = rng.choice(specials), rng.choice(specials)
        else:
            x1, y1 = f32(rng.uniform(0, 25600)), f32(rng.uniform(0, 25600))
            x2, y2 = f32(x1 + rng.uniform(-300, 300)), f32(y1 + rng.uniform(-300, 300))
            if rng.random() < 0.15:
                x2 = x1
            if rng.random() < 0.15:
                y2 = y1
        guest.call(CREATE_ANGLE, [fbits(x1), fbits(y1), fbits(x2), fbits(y2)])
        got = guest.st0_float()
        want = lib.mu_path_create_angle(x1, y1, x2, y2)
        tally.add('CreateAngle 0x012aed9e', same(got, want), {'in': (x1, y1, x2, y2), 'got': got, 'want': want})
        a, b = random_angle(rng), random_angle(rng)
        if rng.random() < 0.05:
            a = rng.choice([math.nan, math.inf, -math.inf])
        flag = rng.choice([0, 1, 1, 2])
        guest.call(ANGLE_DIFFERENCE, [fbits(a), fbits(b), flag])
        got = guest.st0_float()
        want = lib.mu_path_angle_difference(a, b, flag)
        tally.add('angle difference 0x012af218', same(got, want), {'in': (a, b, flag), 'got': got, 'want': want})
        step = f32(rng.choice([rng.uniform(0, 22.5), rng.uniform(0, 200), 0.0, 22.5, 90.0]))
        if rng.random() < 0.3:   # boundary equalities of the TurnAngle branches
            a = f32(rng.choice([rng.uniform(0, 180), rng.uniform(180, 360), 0.0, 90.0, 180.0, 270.0]))
            step = f32(rng.choice([a, f32(360.0 - a), rng.uniform(0, 45), f32(a - 180.0) if a >= 180 else a]))
            b = rng.choice([f32(a + step), f32(a + 180.0), f32(a - step), f32(a - 180.0), f32(f32(a + step) - 360.0),
                            f32(f32(a - step) + 360.0), f32(f32(a + step) - 360.0), rng.uniform(0, 360)])
            b = f32(b)
        if rng.random() < 0.1:   # step equal to the angle: the lo == 0 boundary of both wrap tests
            a = f32(rng.uniform(1.0, 179.0))
            step = a
            b = f32(rng.choice([f32(a + 180.0), rng.uniform(a + 180.0, 360.0), rng.uniform(0.0, a)]))
        guest.call(TURN_ANGLE, [fbits(a), fbits(b), fbits(step)])
        got = guest.st0_float()
        want = lib.mu_path_turn_angle(a, b, step)
        tally.add('TurnAngle 0x012aefff', same(got, want), {'in': (a, b, step), 'got': got, 'want': want})
        tx, ty, x, y = (rng.randint(-300, 600) for _ in range(4))
        got = guest.call(HEURISTIC, [tx, ty, x, y], ecx=ARENA)
        tally.add('heuristic 0x012b1bcf', got == (lib.mu_path_heuristic(tx, ty, x, y) & 0xffffffff), (tx, ty, x, y))
        dx, dy = rng.randint(-1, 1), rng.randint(-1, 1)
        got = guest.call(STEP_COST, [dx, dy], ecx=ARENA)
        tally.add('step cost 0x012b1b67', got == lib.mu_path_step_cost(dx, dy), (dx, dy))


def run_occupancy_family(guest, lib, tally, rng, count):
    for _ in range(count):
        grid = grid_noise(rng, rng.choice([0.05, 0.3, 0.9]),
                          [0x02, 0x03, 0x06, 0x22, 0x01, 0x04, 0xffff, 0xfffe, 0x8002])
        guest.put(TERRAIN_WALL, struct.pack('<65536H', *grid))
        try:
            guest.call(MOVE_CHARACTERS, [], until=CLEAR_LOOP_END)
        except Stop as stop:
            tally.add('occupancy clear 0x0137a7ce', False, {'stop': str(stop)})
            continue
        got = guest.get(TERRAIN_WALL, 0x20000)
        wall = (ctypes.c_uint16 * 65536)(*grid)
        lib.mu_path_clear_characters(wall, 65536)
        tally.add('occupancy clear 0x0137a7ce', got == bytes(wall), None)


# ---------------- long-distance path and auto move (NATIVE-PATH-002) ----------------

LONG_PATH, AUTO_RESET, AUTO_REFRESH, AUTO_START, AUTO_NEXT = 0x012b104c, 0x0129c4d2, 0x0129c51d, 0x0129c6be, 0x0129cc44
PATH_CTOR, LIST_PUSH_BACK, ARRIVAL = 0x0129e1b9, 0x012b2d0f, 0x0129c8b0
TARGET_XY = 0x0b449ac0
SELECTION = 0x01cf114c   # six dwords 0x01cf114c..0x01cf1160
AUTO_SIZE = 0x80
LONG_COUNT = 4_000_000_000   # instruction limit: a whole-map search through the unbalanced tree queue


def finder_state_diff(guest, world, sx, sy):
    """The finder object after a search, guest against C (as World.search compares it)."""
    g, o, c = guest, world.object, world.c
    diff = {}
    if g.i32(o + 0x10) != c.count:
        diff['count'] = (g.i32(o + 0x10), c.count)
    if g.get(o + 0x14, 500) != bytes(c.path_x) or g.get(o + 0x208, 500) != bytes(c.path_y):
        diff['path arrays'] = 'differ'
    if struct.unpack('<hh', g.get(o + 0x3fc, 4)) != (c.end_x, c.end_y):
        diff['end'] = (struct.unpack('<hh', g.get(o + 0x3fc, 4)), (c.end_x, c.end_y))
    if struct.unpack('<ii', g.get(o + 0x404, 8)) != (c.touched_min, c.touched_max):
        diff['touched'] = 'differs'
    if struct.unpack('<II', g.get(o + 0x418 + 4, 8)) != (0, 0):
        diff['tree'] = 'not empty'
    if g.get(TERRAIN_WALL, 0x20000) != bytes(world.wall):
        diff['wall'] = 'differs'
    mark = g.get(g.u32(o + 0x400), 65536)
    if mark != ctypes.string_at(c.mark, 65536):
        diff['mark'] = 'differs'
    cost = struct.unpack('<65536i', g.get(g.u32(o + 0x40c), 0x40000))
    px = struct.unpack('<65536i', g.get(g.u32(o + 0x410), 0x40000))
    py = struct.unpack('<65536i', g.get(g.u32(o + 0x414), 0x40000))
    start = (sy * 256 + sx) if 0 <= sx < 256 and 0 <= sy < 256 else -1
    for i in range(65536):
        m = mark[i]
        if m & 2 and cost[i] != c.cost[i]:
            diff['cost'] = (i, cost[i], c.cost[i])
            break
        if m & 1 and i != start and (px[i] != c.parent_x[i] or py[i] != c.parent_y[i]):
            diff['parent'] = (i, (px[i], py[i]), (c.parent_x[i], c.parent_y[i]))
            break
    return diff


def guest_list(guest, address):
    """std::list<{int16 x, int16 y}> at PATH_t + 0x3c: {head, size}; nodes {next, prev, value}."""
    head, size = struct.unpack('<II', guest.get(address + 0x3c, 8))
    out, node = [], guest.u32(head)
    while node != head and len(out) <= size + 1:
        out.append(struct.unpack('<hh', guest.get(node + 8, 4)))
        node = guest.u32(node)
    return size, out


def c_list(a):
    return [(a.list_x[a.list_head + i], a.list_y[a.list_head + i]) for i in range(a.list_count)]


def guest_auto(guest, address):
    size, nodes = guest_list(guest, address)
    return {'path': guest.get(address, 0x21), 'mode': guest.i32(address + 0x2c),
            'waypoint': struct.unpack('<hh', guest.get(address + 0x30, 4)), 'flag': guest.i32(address + 0x34),
            'target': struct.unpack('<hh', guest.get(address + 0x38, 4)), 'list_size': size, 'list': nodes}


def c_auto(a):
    return {'path': bytes(a.path), 'mode': a.mode, 'waypoint': (a.waypoint_x, a.waypoint_y), 'flag': a.flag,
            'target': (a.target_x, a.target_y), 'list_size': a.list_count, 'list': c_list(a)}


def new_auto(guest):
    address = guest.alloc(AUTO_SIZE, POISON)
    guest.call(PATH_CTOR, [], ecx=address)
    a = AutoPath()
    return address, a


def set_auto(guest, address, a, lib, rng, nodes=None):
    """Same random auto-move state in the guest object and in C (list through the client's push_back)."""
    guest.call(0x0129e4e0, [], ecx=address + 0x3c)   # list clear
    lib.mu_auto_path_init(ctypes.byref(a))
    path = ClientPath()
    count = rng.randint(0, 15)
    path.current, path.current_float, path.count = rng.randrange(0, 16), rng.randrange(0, 4), count
    for i in range(15):
        path.x[i], path.y[i] = rng.randrange(256), rng.randrange(256)
    a.path = path
    a.mode = rng.choice([0, 1, 2, 2, 2, 3, 4, 5])
    a.flag = rng.choice([0, 1, 2, 2, 3])
    a.waypoint_x, a.waypoint_y = rng.choice([(-1, -1), (rng.randrange(256), rng.randrange(256))])
    a.target_x, a.target_y = rng.choice([(-1, -1), (rng.randrange(256), rng.randrange(256))])
    guest.put(address, bytes(path))
    guest.put(address + 0x2c, struct.pack('<ihhihh', a.mode, a.waypoint_x, a.waypoint_y, a.flag, a.target_x,
                                          a.target_y))
    value = guest.alloc(4)
    nodes = nodes if nodes is not None else [(rng.randrange(256), rng.randrange(256))
                                             for _ in range(rng.choice([0, 1, 2, 3, 4, 5, 7, 40]))]
    for i, (x, y) in enumerate(nodes):
        guest.put(value, struct.pack('<hh', x, y))
        guest.call(LIST_PUSH_BACK, [value], ecx=address + 0x3c)
        a.list_x[i], a.list_y[i] = x, y
    a.list_count = len(nodes)


def effects_snapshot(guest):
    return {'target': struct.unpack('<ii', guest.get(TARGET_XY, 8)),
            'selection': struct.unpack('<6i', guest.get(SELECTION, 24))}


def guest_effects(guest, before):
    after = effects_snapshot(guest)
    called = [address for address, _ in guest.calls]
    return {'target_set': after['target'] != before['target'], 'target': list(after['target']),
            'selection_cleared': after['selection'] == (-1,) * 6, 'arrived': ARRIVAL in called,
            'failure_notice': 0x00d51b91 in called}


def c_effects(e, before):
    target = list(e.target) if e.target_set else list(before['target'])
    return {'target_set': bool(e.target_set), 'target': target, 'selection_cleared': bool(e.selection_cleared),
            'arrived': bool(e.arrived), 'failure_notice': bool(e.failure_notice)}


def reset_effect_globals(guest, rng):
    guest.put(TARGET_XY, struct.pack('<ii', rng.randrange(-5, 300), rng.randrange(-5, 300)))
    guest.put(SELECTION, struct.pack('<6i', *[rng.randrange(0, 400) for _ in range(6)]))


def grid_enclosures(rng):
    """Open ground with closed rings (unreachable targets inside) and a few walls."""
    grid = grid_noise(rng, rng.choice([0.0, 0.05, 0.15]), [0x04, 0x08, 0x10, 0x02, 0x22, 0x01])
    for _ in range(rng.randrange(20, 80)):
        cx, cy, r = rng.randrange(4, 252), rng.randrange(4, 252), rng.randrange(1, 4)
        for dy in range(-r - 1, r + 2):
            for dx in range(-r - 1, r + 2):
                if max(abs(dx), abs(dy)) == r + 1 and 0 <= cx + dx < 256 and 0 <= cy + dy < 256:
                    grid[(cy + dy) * 256 + cx + dx] = rng.choice([0x04, 0x08, 0x10])
    return grid


def grid_corridor(rng):
    """A serpentine corridor: paths of several hundred nodes (BuildPath trimming at 500)."""
    grid = [0x04] * 65536
    for row in range(2, 254, 4):
        for x in range(2, 254):
            grid[row * 256 + x] = 0
        link = 252 if (row // 4) % 2 == 0 else 2
        for y in range(row, min(254, row + 5)):
            grid[y * 256 + link] = 0
    for _ in range(rng.randrange(0, 200)):
        grid[rng.randrange(65536)] |= rng.choice([0x01, 0x02, 0x20])
    return grid


LONG_GRIDS = [grid_corridor, grid_maze, grid_enclosures, lambda r: grid_noise(r, 0.3), grid_rooms,
              lambda r: grid_noise(r, 0.0), grid_safezone]


def long_case(rng, grid, maker):
    for _ in range(200):
        sx, sy = rng.randrange(1, 255), rng.randrange(1, 255)
        if (grid[sy * 256 + sx] & 0x1c) < 4 or rng.random() < 0.03:
            break
    span = rng.choice([10, 40, 120, 255])
    tx = min(255, max(0, sx + rng.randint(-span, span)))
    ty = min(255, max(0, sy + rng.randint(-span, span)))
    if maker is grid_corridor and rng.random() < 0.7:
        sx, sy, tx, ty = rng.choice([2, 3]), rng.choice([2, 6, 10]), rng.randrange(2, 253), rng.choice([242, 246, 250])
    r = rng.random()
    if r < 0.04:
        tx, ty = sx, sy
    elif r < 0.07:
        tx, ty = rng.choice([(-1, ty), (tx, -3), (300, ty)])
    error_check = rng.random() < 0.5
    distance = rng.choice([0.0] * 8 + [1.0, 2.5])
    level = rng.choice([4] * 6 + [2, 8, 0x20])
    return sx, sy, tx, ty, error_check, distance, level


def compare_long(guest, lib, world, address, a, case):
    sx, sy, tx, ty, error_check, distance, level = case
    result = guest.call(LONG_PATH, [sx, sy, tx, ty, int(error_check), address, fbits(distance), level],
                        count=LONG_COUNT) & 0xff
    got = guest_auto(guest, address)
    want_result = lib.mu_path_long(ctypes.byref(world.c), sx, sy, tx, ty, int(error_check), ctypes.byref(a),
                                   distance, level) & 0xff
    want = c_auto(a)
    if tx >= 0 and ty >= 0:   # a negative target returns before FindPath: the finder keeps the last search
        world.last_start = (sx, sy)
    diff = finder_state_diff(guest, world, *getattr(world, 'last_start', (sx, sy)))
    if result != want_result:
        diff['result'] = (result, want_result)
    for key in got:
        if got[key] != want[key]:
            diff[key] = 'differs'
    return diff, result, world.c.count


def run_long_family(guest, lib, tally, rng, count, stats=None):
    done, made = 0, 0
    while done < count:
        maker = LONG_GRIDS[made % len(LONG_GRIDS)]
        made += 1
        grid = maker(rng)
        world = World(guest, lib, grid)
        try:
            address, a = new_auto(guest)
            for _ in range(min(2, count - done)):
                case = long_case(rng, grid, maker)
                set_auto(guest, address, a, lib, rng)
                try:
                    diff, result, nodes = compare_long(guest, lib, world, address, a, case)
                except Stop as stop:
                    tally.add('long path 0x012b104c', False, {'stop': str(stop), 'case': case})
                    done += 1
                    continue
                if stats is not None:
                    stats.append({'result': result, 'nodes': nodes, 'trimmed': nodes == 499 and result,
                                  'pops': world.c.pops})
                tally.add('long path 0x012b104c', not diff, {'diff': diff, 'case': case})
                done += 1
        finally:
            world.close()


def run_installed_long_family(guest, lib, tally, rng, count, root, tool, worlds, stats=None):
    grids, seen = [], set()
    for world_index in worlds:
        grid = installed_grid(tool, root, world_index)
        if grid is None:
            continue
        digest = hashlib.sha256(struct.pack('<65536H', *grid)).hexdigest()
        if digest not in seen:
            seen.add(digest)
            grids.append((world_index, grid))
    if not grids:
        return
    for k in range(count):
        world_index, grid = grids[k % len(grids)]
        free = [i for i in range(65536) if (grid[i] & 0x1c) < 4 and i % 256 and i >= 256]
        if len(free) < 2:
            continue
        world = World(guest, lib, grid)
        try:
            address, a = new_auto(guest)
            s, t = rng.choice(free), rng.choice(free)
            case = (s % 256, s // 256, t % 256, t // 256, rng.random() < 0.3, 0.0, 4)
            set_auto(guest, address, a, lib, rng)
            try:
                diff, result, nodes = compare_long(guest, lib, world, address, a, case)
            except Stop as stop:
                tally.add('long path, installed maps', False, {'stop': str(stop), 'world': world_index})
                continue
            if stats is not None:
                stats.append({'result': result, 'nodes': nodes, 'trimmed': nodes == 499 and result,
                              'pops': world.c.pops})
            tally.add('long path, installed maps', not diff, {'diff': diff, 'world': world_index, 'case': case})
        finally:
            world.close()


def run_auto_family(guest, lib, tally, rng, count):
    """0x0129cc44 next segment, 0x0129c4d2 reset, 0x0129c6be start and 0x0129c51d refresh."""
    made = 0
    done = 0
    while done < count:
        grid = [grid_enclosures, lambda r: grid_noise(r, 0.1), grid_rooms][made % 3](rng)
        made += 1
        world = World(guest, lib, grid)
        try:
            address, a = new_auto(guest)
            for _ in range(min(12, count - done)):
                done += 1
                set_auto(guest, address, a, lib, rng)
                kind = rng.choice(['next', 'next', 'reset', 'start', 'start', 'start', 'refresh'])
                reset_effect_globals(guest, rng)
                before = effects_snapshot(guest)
                effects = AutoEffects()
                if kind == 'next':
                    result = guest.call(AUTO_NEXT, [], ecx=address) & 0xff
                    want = lib.mu_auto_path_next(ctypes.byref(a)) & 0xff
                    case = None
                elif kind == 'reset':
                    guest.call(AUTO_RESET, [], ecx=address)
                    lib.mu_auto_path_reset(ctypes.byref(a))
                    result = want = 0
                    case = None
                else:
                    sx, sy = rng.randrange(1, 255), rng.randrange(1, 255)
                    span = rng.choice([3, 10, 30])
                    tx = min(255, max(0, sx + rng.randint(-span, span)))
                    ty = min(255, max(0, sy + rng.randint(-span, span)))
                    if rng.random() < 0.12:
                        tx, ty = sx, sy
                    if kind == 'start':
                        flag, mode = rng.choice([1, 2, 2, 2, 3, 0]), rng.choice([0, 1, 2, 2, 3, 4, 5])
                        ec = rng.choice([0, 0, 1, 2])
                        case = ('start', flag, sx, sy, tx, ty, mode, ec)
                        result = guest.call(AUTO_START, [flag, sx, sy, tx, ty, mode, ec], ecx=address,
                                            count=LONG_COUNT) & 0xff
                        want = lib.mu_auto_path_start(ctypes.byref(a), ctypes.byref(world.c), flag, sx, sy, tx, ty,
                                                      mode, ec, ctypes.byref(effects)) & 0xff
                    else:
                        case = ('refresh', sx, sy, tx, ty)
                        guest.call(AUTO_REFRESH, [sx, sy, tx, ty], ecx=address, count=LONG_COUNT)
                        lib.mu_auto_path_refresh(ctypes.byref(a), ctypes.byref(world.c), sx, sy, tx, ty,
                                                 ctypes.byref(effects))
                        result = want = 0
                got_e = guest_effects(guest, before)
                want_e = c_effects(effects, before) if kind in ('start', 'refresh') else got_e
                got, mine = guest_auto(guest, address), c_auto(a)
                diff = {k: (got[k], mine[k]) for k in got if got[k] != mine[k]}
                if result != want:
                    diff['result'] = (result, want)
                if got_e != want_e:
                    diff['effects'] = (got_e, want_e)
                tally.add(f'auto move {kind}', not diff, {'diff': str(diff)[:600], 'case': case})
        except Stop as stop:
            tally.add('auto move', False, {'stop': str(stop)})
        finally:
            world.close()


# ---------------- run counter and speed predicates (NATIVE-PATH-002) ----------------

SET_PLAYER_WALK, RUN_PREFIX_END, SET_PLAYER_STOP, MOVE_SPEED = 0x0139002a, 0x01390455, 0x0138fe69, 0x013957b5
HERO_EQUIPMENT = 0x01d1df18   # pointer to the hero's character machine (equipment at +0x1b58, 0x12c each)
RIDE_BUFFS = [0xd0, 0x133, 0x142, 0x143, 0x176, 0x177, 0x193, 0x194, 0x1a2, 0x1a3, 0x1b2, 0x1b3, 0x1bc, 0x1bd]
MOUNT_BUFFS = [0xcd, 0xce, 0xcf, 0x1ae] + RIDE_BUFFS
SPEED_BUFFS = [0x18b, 0x38, 0xb8, 0xba, 0xd1, 0xd2, 0xf0, 0x56, 0x112, 0x116, 0x20]
NOISE_BUFFS = [0x01, 0x1c, 0xcc, 0xd3, 0x134, 0x1ad, 0x1af, 0x200]
NEVER_RUN = [0x216, 0x21b, 0x349, 0x34c, 0x371, 0x373, 0x3c1, 0x3d5]


class BuffSet(ctypes.Structure):
    _fields_ = [('ids', ctypes.POINTER(ctypes.c_int32)), ('count', ctypes.c_int32)]


class RunInput(ctypes.Structure):
    _fields_ = [('stunned', ctypes.c_uint8), ('safe_zone', ctypes.c_uint8), ('class_byte', ctypes.c_uint8),
                ('class_value', ctypes.c_int16), ('world', ctypes.c_int32), ('safe_zone_keeps_run', ctypes.c_uint8),
                ('mounted_item', ctypes.c_uint8), ('gloves_type', ctypes.c_int16), ('boots_type', ctypes.c_int16),
                ('gloves_level', ctypes.c_int8), ('boots_level', ctypes.c_int8),
                ('hero_gloves_level', ctypes.c_int32), ('hero_boots_level', ctypes.c_int32),
                ('subtype', ctypes.c_int32), ('buffs', BuffSet)]


class SpeedInput(ctypes.Structure):
    _fields_ = [('move_speed', ctypes.c_uint16), ('object_type', ctypes.c_int32), ('object_kind', ctypes.c_uint8),
                ('special_state', ctypes.c_uint8), ('helper_type', ctypes.c_uint16), ('mount_type', ctypes.c_int32),
                ('helper_option', ctypes.c_uint8), ('safe_zone', ctypes.c_uint8), ('subtype', ctypes.c_int32),
                ('mounted_item', ctypes.c_uint8), ('wing_type', ctypes.c_int16), ('transformed', ctypes.c_uint8),
                ('world_runs', ctypes.c_uint8), ('stunned', ctypes.c_uint8), ('buffs', ctypes.c_uint32),
                ('buff_18b_bonus', ctypes.c_double)]


class SpeedFields(ctypes.Structure):
    _fields_ = [('move_speed', ctypes.c_uint16), ('object_type', ctypes.c_int32), ('object_kind', ctypes.c_uint8),
                ('special_state', ctypes.c_uint8), ('helper_type', ctypes.c_uint16), ('helper_option', ctypes.c_uint8),
                ('safe_zone', ctypes.c_uint8), ('subtype', ctypes.c_int32), ('mounted_item', ctypes.c_uint8),
                ('wing_type', ctypes.c_int16), ('transformed', ctypes.c_uint8), ('world', ctypes.c_int32),
                ('stunned', ctypes.c_uint8), ('buffs', BuffSet), ('buff_18b_bonus', ctypes.c_double)]


def load_movement_library(directory=None):
    directory = Path(directory) if directory else ROOT / 'reconstructed' / 'movement'
    subprocess.run(['make', '-C', str(directory)], check=True, capture_output=True)
    suffix = 'dylib' if sys.platform == 'darwin' else 'so'
    lib = ctypes.CDLL(str(directory / f'libclient_movement.{suffix}'))
    P, I, U8 = ctypes.POINTER, ctypes.c_int32, ctypes.c_uint8
    signatures = {
        'mu_buff_set_has': ([P(BuffSet), I], ctypes.c_int),
        'mu_mount_from_buffs': ([P(BuffSet)], ctypes.c_uint16),
        'mu_world_safe_zone_runs': ([I], ctypes.c_int),
        'mu_world_gloves_run': ([I], ctypes.c_int),
        'mu_world_forces_run': ([I], ctypes.c_int),
        'mu_class_never_runs': ([I], ctypes.c_int),
        'mu_pet_slots_ride': ([P(I), P(U8), P(U8)], ctypes.c_int),
        'mu_player_run_counter': ([P(RunInput), U8], U8),
        'mu_player_stop_run_counter': ([U8, U8], U8),
        'mu_move_speed_input_from': ([P(SpeedFields), P(SpeedInput)], None),
        'mu_character_move_speed': ([P(SpeedInput), P(U8)], ctypes.c_float),
    }
    for name, (argtypes, restype) in signatures.items():
        function = getattr(lib, name)
        function.argtypes, function.restype = argtypes, restype
    return lib


class Equipment:
    """One random character state, written into guest memory and given to the C ports."""

    def __init__(self, rng):
        r = rng
        self.safe_zone = r.choice([0, 0, 0, 1, 1, 2])
        self.class_byte = r.choice([r.randrange(256), r.choice([3, 4, 6, 7, 0x13, 0x26]), 0, 1, 2, 5])
        self.class_value = r.choice([0, 0, 0, r.choice(NEVER_RUN), r.randrange(0x500), 0x215, 0x21c])
        self.world = r.choice([0, 0, 2, 3, 7, 0x12, 0x17, 0x18, 0x1d, 0x24, 0x35, 0x61, 0x80, 0x82, 0x83, 0x84, 0x8d,
                               r.randrange(-3, 200)])
        self.keeps = r.random() < 0.15
        self.stop_keeps = r.random() < 0.3
        self.stunned = r.choice([0] * 12 + [1, 3])
        self.parts = [(r.choice([-1, -1, r.randrange(0x7fff)]), r.choice([0, 3, 4, 5, 6, 13, -1, -128, 127]))
                      for _ in range(6)]
        self.hero_levels = [r.choice([0, 8, 32, 39, 40, 41, 47, 120, -8]) for _ in range(12)]
        self.subtype = r.choice([0, 0, 0, 0x431, 0x432, 7, 0x430])
        self.pet_codes = [r.choice([-1, 0, 0x1a00, 0x1a03, 0x2c00, 0x2c01, r.randrange(0x3000), 0x7fffffff])
                          for _ in range(3)]
        self.records = {}
        for code in self.pet_codes + [self.parts[0][0] - 0xae6]:
            if r.random() < 0.7:
                self.records[code & 0xffffffff] = r.choice([0x40, 0x40, 0x3f, 0x41, 0x2b, 0])
        buffs = set()
        for pool, p in ((RIDE_BUFFS, 0.05), (MOUNT_BUFFS, 0.04), (SPEED_BUFFS, 0.06), (NOISE_BUFFS, 0.2)):
            for b in pool:
                if r.random() < p:
                    buffs.add(b)
        self.buffs = sorted(buffs)
        self.helper = r.choice([0xffff] * 5 + [0x1833, 0x1a03, 0x1a04, 0x1a25, 0x28f7, r.randrange(0x10000)])
        self.helper_option = r.choice([0, 1])
        self.wing = r.choice([-1, -1, -1, 0x22eb, 0x230a, 0x1800])
        self.transformed = 1 if r.random() < 0.05 else 0
        self.special = 1 if r.random() < 0.04 else 0
        self.move_speed = r.choice([0, 10, 12, r.randrange(65536)])
        self.object_type = r.choice([0xa91] * 6 + [0x7a7, r.randrange(0x4000)])
        self.object_kind = r.choice([1] * 6 + [0, 2])
        self.bonus = f32(r.choice([0.0, 1.5, 3.0, r.uniform(-5, 5)]))
        self.run = r.choice([0, 1, 5, 9, 10, 19, 20, 38, 39, 40, 41, 200, 255])
        if r.random() < 0.6:
            self.focus(r)

    def focus(self, r):
        """A neutral walker (no gear, buff, pet or special state, outside the safe zone) with one to three
        features set to boundary values, so that each rule decides the outcome on its own."""
        self.safe_zone, self.class_byte, self.class_value, self.world = 0, r.choice([0, 1, 2, 5, 8, 0x10]), 0, 0
        self.keeps = self.stop_keeps = False
        self.stunned, self.subtype, self.helper, self.wing = 0, 0, 0xffff, -1
        self.parts = [(-1, 0)] * 6
        self.hero_levels = [0] * 12
        self.pet_codes, self.records, self.buffs = [-1, -1, -1], {}, []
        self.transformed = self.special = 0
        self.object_type, self.object_kind = 0xa91, 1
        self.run = r.choice([0, 1, 38, 39, 40, 41])
        features = ['safe', 'class', 'never', 'world', 'boots', 'gloves', 'hero_boots', 'hero_gloves', 'subtype',
                    'ride_buff', 'mount_buff', 'speed_buff', 'pet', 'helper', 'wing', 'transformed', 'special',
                    'stunned', 'keeps']
        for feature in r.sample(features, r.choice([1, 1, 2, 3])):
            if feature == 'safe':
                self.safe_zone = r.choice([1, 2])
            elif feature == 'class':
                self.class_byte = r.choice([3, 4, 6, 7, 0x13, 0x27, 2, 5])
            elif feature == 'never':
                self.class_value = r.choice(NEVER_RUN + [0x215, 0x21c, 0x348, 0x34d, 0x370, 0x374, 0x3c0, 0x3d6])
            elif feature == 'world':
                self.world = r.choice([7, 0x17, 0x18, 0x1d, 0x1e, 0x24, 0x80, 0x82, 0x83, 0x84, 0x12, 0x11, 0x35,
                                       0x61, 0x62])
            elif feature in ('boots', 'gloves'):
                k = 5 if feature == 'boots' else 4
                self.parts[k] = (r.choice([0, 0x1234, -1]), r.choice([4, 5, 6, -1, 127]))
            elif feature in ('hero_boots', 'hero_gloves'):
                self.hero_levels[6 if feature == 'hero_boots' else 5] = r.choice([39, 40, 41, 47, -40])
            elif feature == 'subtype':
                self.subtype = r.choice([0x431, 0x432, 0x430, 0x433])
            elif feature == 'ride_buff':
                self.buffs = sorted(set(self.buffs + [r.choice(RIDE_BUFFS)]))
            elif feature == 'mount_buff':
                self.buffs = sorted(set(self.buffs + [r.choice(MOUNT_BUFFS)]))
            elif feature == 'speed_buff':
                self.buffs = sorted(set(self.buffs + [r.choice(SPEED_BUFFS)]))
            elif feature == 'pet':
                k = r.randrange(3)
                self.pet_codes[k] = r.choice([0x1a00, 0x2c00, 0x2c01, 0, -5])
                self.records[self.pet_codes[k] & 0xffffffff] = r.choice([0x40, 0x40, 0x41, 0x3f])
            elif feature == 'helper':
                self.helper = r.choice([0x1833, 0x1836, 0x1853, 0x185e, 0x184b, 0x19d7, 0x19e4, 0x1a02, 0x1a03,
                                        0x1a04, 0x28f7, 0x1a25, 0x1a00])
                self.helper_option = r.choice([0, 1])
            elif feature == 'wing':
                self.wing = r.choice([0x22eb, 0x230a, 0x248d, 0x2495, 0x1800])
            elif feature == 'transformed':
                self.transformed = 1
            elif feature == 'special':
                self.special = 1
            elif feature == 'stunned':
                self.stunned = r.choice([1, 2])
            elif feature == 'keeps':
                self.keeps = True
                self.stop_keeps = True

    def write(self, guest, records_base):
        ch = bytearray(0x3700)
        ch[4] = self.safe_zone
        ch[0x12] = self.class_byte
        ch[0x24] = self.run
        struct.pack_into('<h', ch, 0x146, self.class_value)
        struct.pack_into('<H', ch, 0x14c, self.move_speed)
        ch[0x190] = self.stunned
        for k, (kind, level) in enumerate(self.parts):
            struct.pack_into('<hb', ch, 0x1c4 + k * 0x3fc, kind, level)
        struct.pack_into('<h', ch, 0x21a4, self.wing)
        ch[0x299f] = self.helper_option
        struct.pack_into('<H', ch, 0x322e, self.helper)
        ch[0x3234] = self.transformed
        struct.pack_into('<3i', ch, 0x3238, *self.pet_codes)
        struct.pack_into('<i', ch, 0x32b0, self.object_type)
        struct.pack_into('<i', ch, 0x32b4, self.subtype)
        ch[0x3254 + 0x3b] = self.object_kind
        character = guest.alloc(len(ch))
        guest.put(character, bytes(ch))
        machine = guest.alloc(0x1b58 + 12 * 0x12c)
        for k, level in enumerate(self.hero_levels):
            guest.put(machine + 0x1b58 + k * 0x12c + 0x14, struct.pack('<i', level))
        guest.put(HERO_EQUIPMENT, struct.pack('<I', machine))
        guest.put(WORLD_GLOBAL, struct.pack('<i', self.world))
        addresses = {}
        for code, kind_b in self.records.items():
            record = guest.alloc(0x2c4, POISON)
            guest.put(record + 0x251, bytes([kind_b]))
            addresses[code] = record
        guest.handlers[0x00cd5d29] = lambda args, ecx: addresses.get(args[0] & 0xffffffff, 0)
        guest.handlers[0x01295ade] = lambda args, ecx: int((args[0] & 0xffffffff) in self.buffs and
                                                           ecx == character + 0x35ac)
        guest.values.update({0x00cd4ea8: records_base, 0x009c104e: records_base + 0x40,
                             0x0106bdb7: int(self.keeps) | 0x5a5a5a00, 0x0106bd76: int(self.stop_keeps) | 0x5a5a5a00,
                             0x009fa30a: records_base + 0x80, 0x009fbb31: self.special | 0x5a5a5a00,
                             0x00966c42: records_base + 0xc0, 0x0117b5eb: self.bonus})
        return character

    def buff_set(self):
        self._ids = (ctypes.c_int32 * max(1, len(self.buffs)))(*self.buffs)
        return BuffSet(self._ids, len(self.buffs))

    def mounted(self, mlib):
        codes = (ctypes.c_int32 * 3)(*self.pet_codes)
        present = (ctypes.c_uint8 * 3)(*[int((c & 0xffffffff) in self.records) for c in self.pet_codes])
        kinds = (ctypes.c_uint8 * 3)(*[self.records.get(c & 0xffffffff, 0) for c in self.pet_codes])
        return mlib.mu_pet_slots_ride(codes, present, kinds)

    def run_input(self, mlib):
        i = RunInput()
        i.stunned, i.safe_zone, i.class_byte, i.class_value = self.stunned, self.safe_zone, self.class_byte, \
            self.class_value
        i.world, i.safe_zone_keeps_run, i.mounted_item = self.world, int(self.keeps), self.mounted(mlib)
        i.gloves_type, i.gloves_level = self.parts[4]
        i.boots_type, i.boots_level = self.parts[5]
        i.hero_gloves_level, i.hero_boots_level = self.hero_levels[5], self.hero_levels[6]
        i.subtype = self.subtype
        i.buffs = self.buff_set()
        return i

    def speed_fields(self, mlib):
        f = SpeedFields()
        f.move_speed, f.object_type, f.object_kind, f.special_state = self.move_speed, self.object_type, \
            self.object_kind, self.special
        f.helper_type, f.helper_option, f.safe_zone, f.subtype = self.helper, self.helper_option, self.safe_zone, \
            self.subtype
        f.mounted_item, f.wing_type, f.transformed, f.world = self.mounted(mlib), self.wing, self.transformed, self.world
        f.stunned, f.buffs, f.buff_18b_bonus = self.stunned, self.buff_set(), self.bonus
        return f


def boundary_states(rng):
    """Each run rule alone at its boundary, on a neutral walker (see Equipment.focus), for run 0, 39 and 40."""
    variants = []
    for run in (0, 39, 40):
        variants += [('class_byte', c, run) for c in range(16)]
        variants += [('buffs', [b], run) for b in MOUNT_BUFFS + SPEED_BUFFS[:2]]
        variants += [('boots', level, run) for level in (4, 5, 6)]
        variants += [('gloves', level, run) for level in (4, 5, 6)]
        variants += [('hero_boots', level, run) for level in (39, 40, 41)]
        variants += [('hero_gloves', level, run) for level in (39, 40, 41)]
        variants += [('subtype', v, run) for v in (0x430, 0x431, 0x432, 0x433)]
        variants += [('safe', (zone, world, keeps), run) for zone in (0, 1, 2) for world in (0, 0x84)
                     for keeps in (False, True)]
        variants += [('never', v, run) for v in NEVER_RUN + [0x215, 0x3d6]]
        variants += [('pet', (code, kind), run) for code in (0x1a00, 0x2c00, 0x2c01) for kind in (0x40, 0x41)]
    for feature, value, run in variants:
        for world in ((0, 0x18) if feature in ('boots', 'gloves', 'hero_boots', 'hero_gloves') else (0,)):
            e = Equipment(rng)
            e.focus(random.Random(0))
            e.safe_zone, e.class_byte, e.world, e.buffs, e.run = 0, 0, world, [], run
            e.parts, e.hero_levels, e.subtype, e.class_value = [(-1, 0)] * 6, [0] * 12, 0, 0
            e.pet_codes, e.records, e.keeps = [-1, -1, -1], {}, False
            if feature == 'class_byte':
                e.class_byte = value
            elif feature == 'buffs':
                e.buffs = value
            elif feature in ('boots', 'gloves'):
                e.parts[5 if feature == 'boots' else 4] = (0x1234, value)
            elif feature in ('hero_boots', 'hero_gloves'):
                e.hero_levels[6 if feature == 'hero_boots' else 5] = value
            elif feature == 'subtype':
                e.subtype = value
            elif feature == 'safe':
                e.safe_zone, e.world, e.keeps = value
                e.class_byte = 3
            elif feature == 'never':
                e.class_value, e.class_byte = value, 3
            elif feature == 'pet':
                e.pet_codes[1] = value[0]
                e.records[value[0]] = value[1]
            yield e


def run_run_family(guest, mlib, tally, rng, count):
    """The run-counter prefix of SetPlayerWalk and SetPlayerStop's reset, as client code."""
    states = list(boundary_states(rng))
    with guest.unstubbed(0x0095fb27):
        for k in range(len(states) + count):
            guest.reset_arena()
            records = guest.alloc(0x100)
            e = states[k] if k < len(states) else Equipment(rng)
            character = e.write(guest, records)
            try:
                if e.stunned:
                    guest.call(SET_PLAYER_WALK, [character])   # returns at once
                else:
                    guest.call(SET_PLAYER_WALK, [character], until=RUN_PREFIX_END)
            except Stop as stop:
                tally.add('run counter 0x0139002a', False, {'stop': str(stop)})
                continue
            got = guest.get(character + 0x24, 1)[0]
            want = mlib.mu_player_run_counter(ctypes.byref(e.run_input(mlib)), e.run)
            tally.add('run counter 0x0139002a', got == want,
                      {'got': got, 'want': want, 'state': {k: v for k, v in vars(e).items() if not k.startswith('_')}})
            guest.put(character + 0x24, bytes([e.run]))
            try:
                guest.call(SET_PLAYER_STOP, [character], until=0x0138fe8c)
            except Stop as stop:
                tally.add('stop run counter 0x0138fe69', False, {'stop': str(stop)})
                continue
            got = guest.get(character + 0x24, 1)[0]
            want = mlib.mu_player_stop_run_counter(int(e.stop_keeps), e.run)
            tally.add('stop run counter 0x0138fe69', got == want, {'got': got, 'want': want})


def run_speed_state_family(guest, mlib, tally, rng, count):
    """CharacterMoveSpeed with its predicates (helper, buff mount, riding pet, transformation, world) as client
    code; the C side derives its input from the same character fields."""
    states = list(boundary_states(rng))
    with guest.unstubbed(0x0095fb27, 0x0129dcda, MOVE_SPEED):
        for k in range(len(states) + count):
            guest.reset_arena()
            records = guest.alloc(0x100)
            e = states[k] if k < len(states) else Equipment(rng)
            character = e.write(guest, records)
            try:
                guest.call(MOVE_SPEED, [character])
            except Stop as stop:
                tally.add('move speed with predicates 0x013957b5', False, {'stop': str(stop)})
                continue
            got, got_run = guest.st0_float(), guest.get(character + 0x24, 1)[0]
            speed_input = SpeedInput()
            mlib.mu_move_speed_input_from(ctypes.byref(e.speed_fields(mlib)), ctypes.byref(speed_input))
            run = ctypes.c_uint8(e.run)
            want = mlib.mu_character_move_speed(ctypes.byref(speed_input), ctypes.byref(run))
            ok = same(f32(got), f32(want)) and got_run == run.value
            tally.add('move speed with predicates 0x013957b5', ok,
                      {'got': [got, got_run], 'want': [want, run.value],
                       'state': {k: v for k, v in vars(e).items() if not k.startswith('_')}})


def run_predicate_family(guest, mlib, tally, rng, count):
    worlds = list(range(-4, 300)) + [rng.randrange(-2 ** 31, 2 ** 31) for _ in range(20)]
    for world in worlds:
        for address, name in ((0x00e0558b, 'mu_world_safe_zone_runs'), (0x016a88d3, 'mu_world_gloves_run'),
                              (0x009dacb8, 'mu_world_forces_run')):
            got = guest.call(address, [world]) & 0xff
            tally.add(f'world predicate {hex(address)}', got == getattr(mlib, name)(world), world)
    for value in list(range(0, 0x500)) + [rng.randrange(-2 ** 15, 2 ** 15) for _ in range(50)]:
        got = guest.call(0x0139bd24, [value]) & 0xff
        tally.add('class predicate 0x0139bd24', got == mlib.mu_class_never_runs(value), value)
    guest.reset_arena()
    holder = guest.alloc(0x3700)
    for _ in range(count):
        ids = sorted(set(rng.sample(MOUNT_BUFFS + NOISE_BUFFS, rng.randrange(0, 4))))
        guest.handlers[0x01295ade] = lambda args, ecx, ids=ids: int((args[0] & 0xffffffff) in ids and
                                                                    ecx == holder + 0x35ac)
        got = guest.call(0x0106c5e9, [holder]) & 0xffffffff
        array = (ctypes.c_int32 * max(1, len(ids)))(*ids)
        want = mlib.mu_mount_from_buffs(ctypes.byref(BuffSet(array, len(ids))))
        tally.add('buff mount 0x0106c5e9', got == want, {'buffs': ids, 'got': got, 'want': want})


CLIENT_DIRECTIONS = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]


MOVEMENT_FAMILIES = ('run', 'speed_state', 'predicates')

# Plausible reconstruction mistakes; each must be detected (mutation check).
MUTATIONS = [
    ('queue ties popped last-in first-out', 'client_path.c',
     '(a->cost == b->cost && a->sequence < b->sequence)', '(a->cost == b->cost && a->sequence > b->sequence)',
     'search'),
    ('diagonal step cost 5', 'client_path.c', 'return dx != 0 && dy != 0 ? 7 : 5;', 'return dx != 0 && dy != 0 ? 5 : 5;', 'search'),
    ('heuristic without +1', 'client_path.c', '(abs(dx - dy) * 5 + m * 7 + 1) * 3 / 4',
     '(abs(dx - dy) * 5 + m * 7) * 3 / 4', 'search'),
    ('classic A* priority g(parent)+step+h', 'client_path.c',
     'mu_path_heuristic(tx, ty, nx, ny) + f->cost[current]',
     'mu_path_heuristic(tx, ty, nx, ny) + f->cost[current] + mu_path_step_cost(dirs[d][0], dirs[d][1])',
     'search'),
    ('passability mask 0x1c (character tiles walkable)', 'client_path.h', '#define MU_PATH_WALL_MASK 0x1e',
     '#define MU_PATH_WALL_MASK 0x1c', 'search'),
    ('no safe-zone retry level 4', 'client_path.c', '            wall = 4;', '            wall = wall_level;',
     'search'),
    ('path capacity 16', 'client_path.h', '#define MU_PATH_CLIENT_NODES 15', '#define MU_PATH_CLIENT_NODES 14',
     'search'),
    ('distance marking with >=', 'client_path.c', 'if (!(distance > s))', 'if (!(distance >= s))', 'search'),
    # from the NATIVE-WORLD-001 path mutations (scripts/validate_movement.py)
    ('parent replaced on equal cost', 'client_path.c', 'if (g < f->cost[current]) {', 'if (g <= f->cost[current]) {',
     'search'),
    ('wall test without the mask', 'client_path.c', 'int32_t w = (int32_t)f->wall[n] & wall_mask;',
     'int32_t w = (int32_t)f->wall[n] & (wall_mask | 0xffff);', 'search'),
    ('object block ignored', 'client_path.c', 'if (f->object_flags && (f->object_flags[n] & 1u)',
     'if (0 && f->object_flags && (f->object_flags[n] & 1u)', 'search'),
    ('arrival radius < 30', 'client_path.c', 'if (whole <= 30)', 'if (whole < 30)', 'move'),
    ('spline t = 0.5 weights everywhere', 'client_path.c', '{-0.0703125f, 0.8671875f, 0.2265625f, -0.0234375f},',
     '{-0.0625f, 0.5625f, 0.5625f, -0.0625f},', 'move'),
    ('turn snaps above 45 only', 'client_path.c', 'if (difference >= 45.0f)', 'if (difference > 45.0f)', 'move'),
    ('exact binary32 pi in CreateAngle', 'client_path.c', 'a = a / 3.14159274f;', 'a = a * 0.318309886f;',
     'angles'),
    ('TurnAngle wraps with >', 'client_path.c', 'if (lo >= 0.0f && (b >= a + 180.0f || lo > b))',
     'if (lo > 0.0f && (b >= a + 180.0f || lo > b))', 'angles'),
    # NATIVE-PATH-002: long-distance path and auto move
    ('no BuildPath trimming above budget 500', 'client_path.c',
     'return build_path(f, sx, sy, x, y, max_pops > MU_PATH_MAX_STEPS);', 'return build_path(f, sx, sy, x, y, 0);',
     'long'),
    ('trimming keeps 500 nodes', 'client_path.c', 'int32_t k = n - (MU_PATH_MAX_STEPS - 1);',
     'int32_t k = n - MU_PATH_MAX_STEPS;', 'long'),
    ('long path mask 0x1e (characters block)', 'client_path.h', '#define MU_PATH_LONG_MASK 0x1c',
     '#define MU_PATH_LONG_MASK 0x1e', 'long'),
    ('long path target not moved to the end tile', 'client_path.c', '''        a->target_x = f->end_x;
        a->target_y = f->end_y;''', '''        a->target_x = (int16_t)tx;
        a->target_y = (int16_t)ty;''', 'long'),
    ('segments of 4 nodes', 'client_path.h', '#define MU_PATH_SEGMENT_NODES 3', '#define MU_PATH_SEGMENT_NODES 4',
     'auto'),
    ('start ignores the armed flag', 'client_path.c', '''    if (a->flag == 1)
        return 0;''', '''    if (a->flag == 9)
        return 0;''', 'auto'),
    # run counter and speed predicates (reconstructed/movement)
    ('boots need level 6', 'client_movement.c', '(!gloves && in->boots_type != -1 && in->boots_level >= 5)',
     '(!gloves && in->boots_type != -1 && in->boots_level >= 6)', 'run'),
    ('safe zone keeps the counter', 'client_movement.c', '''    if (in->safe_zone == 1 && !safe_runs && !in->safe_zone_keeps_run)
        run = 0;''', '''    if (in->safe_zone == 9 && !safe_runs && !in->safe_zone_keeps_run)
        run = 0;''', 'run'),
    ('hero boots field >= 41', 'client_movement.c', '(!gloves && in->hero_boots_level >= 40)',
     '(!gloves && in->hero_boots_level >= 41)', 'run'),
    ('ride buff 0x1bd missing', 'client_movement.c', '0x1a2, 0x1a3, 0x1b2, 0x1b3, 0x1bc, 0x1bd};',
     '0x1a2, 0x1a3, 0x1b2, 0x1b3, 0x1bc, 0x1bc};', 'run'),
    ('riding pet kind 0x41', 'client_movement.c', 'kind_b[i] == 0x40', 'kind_b[i] == 0x41', 'speed_state'),
    ('buff mount order 0xcd/0xce swapped', 'client_movement.c', '{0xcd, 0x1a02}, {0xce, 0x1a03}',
     '{0xce, 0x1a03}, {0xcd, 0x1a02}', 'predicates'),
    ('gloves worlds without 0x24', 'client_movement.c', 'return (world >= 0x18 && world <= 0x1d) || world == 0x24;',
     'return (world >= 0x18 && world <= 0x1d);', 'predicates'),
    ('never-running classes without 0x3d5', 'client_movement.c', '''v == 0x3c1 ||
           v == 0x3d5;''', '''v == 0x3c1;''', 'predicates'),
]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--text', default=pins.TEXT.default_str())
    parser.add_argument('--data', default=pins.DATA.default_str())
    parser.add_argument('--flag', default=pins.FLAG.default_str())
    parser.add_argument('--directions', default=pins.DIRECTIONS.default_str(),
        help='capture of the third section from 0x01ced000 holding the neighbour table 0x01cf1640 '
             '(the live read path-table-live-01 or x86-linux-capture-04/main-01ced000.bin)')
    parser.add_argument('--game-root', default=os.environ.get('MU_GAME_ROOT'))
    parser.add_argument('--tool', default=str(ROOT / 'native/build/mu-path'))
    parser.add_argument('--worlds', default='0,1,2,3,4,7,8,9,10,32,33,37,38,40,41,56,62,79,90,141,142')
    parser.add_argument('--cases', type=int, default=200, help='cases per family')
    parser.add_argument('--seed', type=int, default=0x50415448)
    parser.add_argument('--only', default=None, help='comma list: search,installed,move,walk,angles,occupancy,'
                                                     'long,auto,installed_long')
    parser.add_argument('--mutations', action='store_true')
    parser.add_argument('--output', default=None)
    parser.add_argument('--cross-library', default=None,
                        help='another path-finder port (NATIVE-WORLD-001 libclient_movement) to compare on '
                             'distance-0 searches')
    args = parser.parse_args(argv)

    text = load_pinned(args.text, TEXT_BYTES, TEXT_SHA256, 'restored text')
    data = load_pinned(args.data, DATA_BYTES, DATA_SHA256, 'second section')
    flag = load_pinned(args.flag, 4, FLAG_SHA256, 'dispatch flag')
    directions = load_pinned(args.directions, 64, DIRECTIONS_SHA256, 'neighbour table',
                             offset=DIRECTIONS_ADDRESS - DIRECTIONS_SECTION)
    guest = Guest(text, data, flag, directions)
    lib = load_library()
    mlib = load_movement_library()
    if args.cross_library:
        CROSS['lib'] = load_cross_library(args.cross_library)
    only = set(args.only.split(',')) if args.only else None
    n = args.cases
    tally = Tally()
    stats = []
    long_stats = []
    families = {
        'search': lambda lib_, t, r, c: run_search_family(guest, lib_, t, r, c, stats=stats),
        'move': lambda lib_, t, r, c: run_move_family(guest, lib_, t, r, c),
        'walk': lambda lib_, t, r, c: run_walk_family(guest, lib_, t, r, max(1, c // 4)),
        'angles': lambda lib_, t, r, c: run_angle_family(guest, lib_, t, r, c),
        'occupancy': lambda lib_, t, r, c: run_occupancy_family(guest, lib_, t, r, max(1, c // 20)),
        'long': lambda lib_, t, r, c: run_long_family(guest, lib_, t, r, max(3, c // 10), stats=long_stats),
        'auto': lambda lib_, t, r, c: run_auto_family(guest, lib_, t, r, max(12, c // 2)),
        # these take the movement library (reconstructed/movement)
        'run': lambda mlib_, t, r, c: run_run_family(guest, mlib_, t, r, 4 * c),
        'speed_state': lambda mlib_, t, r, c: run_speed_state_family(guest, mlib_, t, r, 2 * c),
        'predicates': lambda mlib_, t, r, c: run_predicate_family(guest, mlib_, t, r, c),
    }
    if args.game_root and Path(args.tool).exists():
        worlds = list(range(0, 160)) if args.worlds == 'all' else [int(w) for w in args.worlds.split(',')]
        families['installed'] = lambda lib_, t, r, c: run_installed_family(guest, lib_, t, r, c, args.game_root,
                                                                           args.tool, worlds, stats=stats)
        families['installed_long'] = lambda lib_, t, r, c: run_installed_long_family(
            guest, lib_, t, r, max(2, c // 25), args.game_root, args.tool, worlds, stats=long_stats)
    for name, function in families.items():
        if only and name not in only:
            continue
        function(mlib if name in MOVEMENT_FAMILIES else lib, tally, random.Random(f'{args.seed}:{name}'), n)
    total = sum(r['cases'] for r in tally.results.values())
    bad = sum(r['mismatches'] for r in tally.results.values())
    for family, r in tally.results.items():
        print(f"{family:44s} {r['cases']:6d} cases {r['mismatches']:5d} mismatches")
        if r['first']:
            print('    first:', json.dumps(r['first'], default=str)[:800])
    found = [s for s in stats if s['nodes']]
    summary = {'searches': len(stats), 'found': len(found),
               'max_pops': max((s['pops'] for s in stats), default=0),
               'max_closed': max((s['closed'] for s in stats), default=0),
               'mean_nodes': (sum(s['nodes'] for s in found) / len(found)) if found else 0}
    summary['long'] = {'searches': len(long_stats), 'found': sum(1 for x in long_stats if x['result']),
                       'trimmed': sum(1 for x in long_stats if x['trimmed']),
                       'max_nodes': max((x['nodes'] for x in long_stats if x['result']), default=0),
                       'max_pops': max((x['pops'] for x in long_stats), default=0)}
    print(f'total {total} comparisons, {bad} mismatches; searches {json.dumps(summary)}')

    mutation_results = None
    if args.mutations:
        import shutil
        import tempfile
        mutation_results = []
        with tempfile.TemporaryDirectory() as scratch:
            scratch = Path(scratch)
            shutil.copytree(ROOT / 'reconstructed' / 'record-math', scratch / 'record-math',
                            ignore=shutil.ignore_patterns('*.dylib', '*.so'))
            for index, (label, filename, old, new, family) in enumerate(MUTATIONS):
                module = 'movement' if family in MOVEMENT_FAMILIES else 'path'
                target = scratch / f'{module}{index}'
                shutil.copytree(ROOT / 'reconstructed' / module, target, ignore=shutil.ignore_patterns('*.dylib', '*.so'))
                source = (target / filename).read_text()
                if source.count(old) != 1:
                    raise ValueError(f'mutation anchor not unique: {label}')
                (target / filename).write_text(source.replace(old, new))
                mutated = load_movement_library(target) if module == 'movement' else load_library(target)
                t = Tally()
                name = {'search': 'search', 'move': 'walk', 'angles': 'angles', 'long': 'long', 'auto': 'auto',
                        'run': 'run', 'speed_state': 'speed_state', 'predicates': 'predicates'}[family]
                count = max(40, n // 2)
                if family == 'long':
                    count = max(count, 140)   # 14 searches: every grid kind of LONG_GRIDS twice
                if family == 'move':
                    families['move'](mutated, t, random.Random(f'{args.seed}:mut:{label}'), count)
                families[name](mutated, t, random.Random(f'{args.seed}:mut:{label}'), count)
                misses = sum(r['mismatches'] for r in t.results.values())
                cases = sum(r['cases'] for r in t.results.values())
                mutation_results.append({'mutation': label, 'mismatches': misses, 'cases': cases})
                print(f'mutation {label:52s} {misses:5d}/{cases} detected')
    report = {'total': total, 'mismatches': bad, 'families': tally.results, 'searches': summary,
              'mutations': mutation_results,
              'stubs': {hex(k): v[2] for k, v in CLIENT_STUBS.items()},
              'routines': {k: {'start': hex(v[0]), 'bytes': v[1], 'sha256': v[2]} for k, v in ROUTINES.items()}}
    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=1, default=str))
    undetected = [m['mutation'] for m in (mutation_results or []) if m['mismatches'] == 0]
    if undetected:
        print('undetected mutations:', undetected)
    return 1 if bad or undetected else 0


if __name__ == '__main__':
    sys.exit(main())
