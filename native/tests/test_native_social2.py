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
