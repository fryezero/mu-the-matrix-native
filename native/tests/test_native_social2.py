"""Synthetic multi-room and mailbox lifecycle through original receive parsers."""

from pathlib import Path
import subprocess
import struct
import os
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class SocialMessages(unittest.TestCase):
    def test_rooms_mail_cache_requests_and_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / "messages"
            subprocess.run(
                [
                    "clang",
                    "-std=c11",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-Wconversion",
                    str(ROOT / "native/tests/social_messages_host.c"),
                    str(ROOT / "native/core/mu_social_messages.c"),
                    str(ROOT / "reconstructed/social/social_packets.c"),
                    "-o",
                    str(exe),
                ],
                check=True,
            )
            p = subprocess.run([str(exe)], capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertIn("social messages passed", p.stdout)


class SocialItemTables(unittest.TestCase):
    def test_typed_tables_preserve_composite_keys_and_reject_truncation(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            local = d / "game/Data/Local"
            local.mkdir(parents=True)
            lang = d / "lang"
            lang.mkdir()
            values = "\t".join(str(i) for i in range(1, 26))
            (lang / "social-options.tsv").write_text(
                "guardian_name\t7\tOption %d\\\\literal\\n\n"
                "guardian_value\t7\t3\t7\t19\t22\t34\t\n"
                "guardian_bonus_name\t2\tBonus %d\n"
                "guardian_bonus\t9\t3\t9\t2\t24\t0\t99\t17\t0\t\n"
                "advanced\t3\t5\t10\t20\t30\t40\t2\tAdvanced %\n"
                "artifact_name\t12\t2\tArtifact\n"
                "artifact\t8\t12\t" + values + "\tRow\n"
                "artifact\t99\t12\t1\tTruncated\n"
            )
            key = bytes([0xFC, 0xCF, 0xAB])
            # Preserve each fixed table decoder unit and its XOR phase.
            socket = bytearray(150 * 168)
            for i in range(150):
                off = i * 168
                struct.pack_into("<iii", socket, off, i, 1, 2)
                for j in range(20):
                    struct.pack_into("<i", socket, off + 0x50 + 4 * j, i * 10 + j)
            # SocketItem uses a separate XOR unit per 168-byte record.
            for off in range(0, len(socket), 168):
                for j in range(168):
                    socket[off + j] ^= key[j % 3]
            (local / "socketitem.bmd").write_bytes(socket)
            harmony = bytearray(750 * 180)
            for i in range(750):
                off = i * 180
                struct.pack_into("<i", harmony, off, i % 250 + 1)
                for j in range(14):
                    struct.pack_into("<i", harmony, off + 0x44 + 4 * j, i * 100 + j)
                    struct.pack_into(
                        "<i", harmony, off + 0x7C + 4 * j, i * 1000 + 100 + j
                    )
            (local / "jewelofharmonyoption.bmd").write_bytes(
                bytes(x ^ key[i % 3] for i, x in enumerate(harmony))
            )
            exe = d / "item-tables"
            sources = [
                "native/tests/social_item_tables_host.c",
                "native/core/mu_social_item_tables.c",
                "reconstructed/social/item_formula.c",
                "native/core/mu_data.c",
                "native/core/mu_lang.c",
                "reconstructed/items/item_sets.c",
                "reconstructed/data/data_tables.c",
                "reconstructed/data/data_codec.c",
                "reconstructed/data/item_attributes.c",
                "reconstructed/data/table_layouts.c",
            ]
            subprocess.run(
                [
                    "clang",
                    "-std=c11",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    *[str(ROOT / x) for x in sources],
                    "-lm",
                    "-o",
                    str(exe),
                ],
                check=True,
            )
            result = subprocess.run(
                [str(exe), str(d / "game"), str(lang)], capture_output=True, text=True
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class SocialItemView(unittest.TestCase):
    def test_complete_wire_families_and_missing_activation_context(self):
        from test_native_data import item_record, item_file, xor3, checksum

        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            local = d / "game/Data/Local"
            local.mkdir(parents=True)
            lang = d / "lang"
            lang.mkdir()
            records = []
            for code in range(100, 108):
                r = bytearray(
                    item_record(code, b"", b"", ("Synthetic %d" % code).encode())
                )
                r[0x250] = [1, 1, 20, 28, 19, 26, 25, 1][code - 100]
                r[0x251] = 1
                r[0x252] = [0, 2, 0, 0, 0, 0, 0, 4][code - 100]
                r[0x256] = 255
                r[0x25A] = r[0x25B] = 1
                r[0x2A9] = 1
                r[0x2B8] = int(code == 106)
                struct.pack_into("<H", r, 0x254, 3)
                struct.pack_into("<H", r, 0x258, 17)
                struct.pack_into("<H", r, 0x286, 50)
                records.append(bytes(r))
            (local / "item.bmd").write_bytes(item_file(records))
            row = bytearray(120)
            row[0] = 1
            row[1] = 0
            row[2:102] = b"Excellent damage %d".ljust(100, b"\0")
            row[0x66] = 6
            struct.pack_into("<ii", row, 0x68, 11, 0)
            encoded = xor3(row)
            (local / "excellentcommonoption.bmd").write_bytes(
                struct.pack("<I", 1)
                + encoded
                + struct.pack("<I", checksum(encoded, 0xE2F1))
            )
            sockets = bytearray(150 * 168)
            for i in range(150):
                off = i * 168
                struct.pack_into("<iii", sockets, off, i, 1, 0)
                sockets[off + 12 : off + 76] = b"Socket power".ljust(64, b"\0")
                struct.pack_into("<i", sockets, off + 0x4C, 1)
                for j in range(20):
                    struct.pack_into("<i", sockets, off + 0x50 + j * 4, 7 + j)
            (local / "socketitem.bmd").write_bytes(
                b"".join(
                    xor3(sockets[x : x + 168]) for x in range(0, len(sockets), 168)
                )
            )
            formulas = {
                1: {7: "%d+%d"},
                8: {19: "%d*2"},
                9: {27: "%d*10"},
                11: {22: "%d+%d"},
            }
            payload = b""
            total = 0
            for family, rows in formulas.items():
                payload += xor3(struct.pack("<I", family)) + xor3(
                    struct.pack("<I", len(rows))
                )
                for index, pattern in rows.items():
                    payload += xor3(
                        struct.pack("<i", index) + pattern.encode().ljust(256, b"\0")
                    )
                    total += 1
            (local / "formuladata.bmd").write_bytes(
                struct.pack("<II", total, len(formulas))
                + payload
                + struct.pack("<I", checksum(payload, 0xE2F1))
            )
            (lang / "globaltext.txt").write_text(
                "88\tExtra damage %d\n87\tLuck %d\n6648\tRank %d %s\n3737\tFire\n"
            )
            artifact = list(range(1, 26))
            artifact[20] = 0
            artifact[21] = 22
            jewel = (
                [105, 1, 1, 0, 0, 0]
                + [i * 10 for i in range(11)]
                + [i * 100 for i in range(11)]
            )
            rows = [
                ("guardian_name", [7], "Guardian %d"),
                ("guardian_value", [7, 3, 0, 19, 0, 0], ""),
                ("artifact_name", [12, 2], "Artifact power"),
                ("artifact", [8, 12] + artifact, "unused"),
                ("earring_primary", [104, 1, 1], "Earring"),
                ("earring_name", [28, 1], "Mastery power"),
                ("earring_value", [1, 0, 0, 27, 1], ""),
                ("jewel", jewel, "Elemental Power %d"),
                ("advanced", [1, 1, 1, 2, 3, 4, 2], "Advanced strength"),
                ("pentagram", [106, 1, 1, 0, 0, 0, 0, 0, 0], "Pentagram"),
                ("pentagram_option", [1, 5, 0, 2] + [-1, -1, 0] * 4, "Bonus +5%%"),
            ]
            (lang / "social-options.tsv").write_text(
                "".join(
                    "\t".join([kind] + [str(v) for v in values] + [text]) + "\n"
                    for kind, values, text in rows
                )
            )
            sources = [
                "native/tests/social_item_view_host.c",
                "native/core/mu_social_item_view.c",
                "native/core/mu_social_item_tables.c",
                "native/core/mu_hud_tip.c",
                "native/core/mu_data.c",
                "native/core/mu_lang.c",
                "reconstructed/items/item_sets.c",
                "reconstructed/social/item_options.c",
                "reconstructed/social/item_formula.c",
                "reconstructed/social/item_display.c",
                "reconstructed/hud/tooltip_format.c",
                "reconstructed/hud/tooltip_html.c",
                "reconstructed/data/data_tables.c",
                "reconstructed/data/data_codec.c",
                "reconstructed/data/item_attributes.c",
                "reconstructed/data/table_layouts.c",
            ]
            exe = d / "views"
            subprocess.run(
                [
                    "clang",
                    "-std=c11",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-Wconversion",
                    *[str(ROOT / x) for x in sources],
                    "-lm",
                    "-o",
                    str(exe),
                ],
                check=True,
            )
            r = subprocess.run(
                [str(exe), str(d / "game"), str(lang)], capture_output=True, text=True
            )
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
