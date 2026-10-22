"""Offline party/trade/friend flows over the native session, synthetic players only."""

from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import unittest

N = Path(__file__).resolve().parents[1]


class SocialSession(unittest.TestCase):
    def test_membership_survives_world_travel(self):
        from test_native_combat import write_combat_world
        from test_native_map import second_world, write_lang

        subprocess.run(["make", "-C", str(N)], check=True, capture_output=True)
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            root = write_combat_world(d / "game")
            second_world(root)
            write_lang(d / "lang")
            players = d / "players.txt"
            players.write_text("player Aeris class=0x01 at=123,120 party\n")
            p = subprocess.run(
                [
                    str(N / "build/mu-walk"),
                    "--game-root",
                    str(root),
                    "--players",
                    str(players),
                    "--hero-name",
                    "Hero",
                    "--headless",
                    "--backend",
                    "soft",
                    "--no-audio",
                    "--no-env",
                    "--no-particles",
                    "--no-helpers",
                    "--width",
                    "64",
                    "--height",
                    "64",
                    "--frames",
                    "20",
                    "--out-dir",
                    str(d / "renders"),
                    "--travel-script",
                    "3:move:2 10:move:1",
                ],
                capture_output=True,
                text=True,
                env={**os.environ, "MU_LANG_DIR": str(d / "lang")},
            )
            self.assertEqual(p.returncode, 0, p.stderr)
            rows = [json.loads(x) for x in p.stdout.splitlines() if x.startswith("{")]
            self.assertEqual(next(x for x in rows if x.get("map"))["travels"], 2)
            social = next(x for x in rows if x.get("social"))
            self.assertEqual((social["party"], social["friends"]), (2, 1))

    def test_inventory_messenger_marker_refresh_and_host_rebind(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            lib = d / ("libstub.dylib" if sys.platform == "darwin" else "libstub.so")
            subprocess.run(
                [
                    "clang",
                    "-std=c11",
                    "-shared",
                    "-fPIC",
                    str(N / "tests/gfx_stub_mugfx.c"),
                    "-o",
                    str(lib),
                ],
                check=True,
            )
            exe = d / "host"
            hud = N.parent / "reconstructed/hud"
            sources = [
                N / p
                for p in (
                    "tests/social_gfx_host.c",
                    "world/world_gfx_social.c",
                    "core/mu_social.c",
                    "core/mu_social_messages.c",
                    "gfx/mu_gfx_layer.c",
                )
            ]
            sources += [
                N.parent / "reconstructed/social/social.c",
                N.parent / "reconstructed/social/item_options.c",
                N.parent / "reconstructed/social/social_packets.c",
            ] + [hud / p for p in ("inv_grid.c", "item_slots.c", "tooltip_html.c")]
            subprocess.run(
                [
                    "clang",
                    "-std=c11",
                    "-DMU_GFX_NO_GL",
                    "-I",
                    str(N / "gfx"),
                    "-I",
                    str(hud),
                    *map(str, sources),
                    "-lm",
                    *(["-ldl"] if sys.platform != "darwin" else []),
                    "-o",
                    str(exe),
                ],
                check=True,
            )
            movies = d / "movies"
            movies.mkdir()
            for f in (
                "base",
                "main",
                "chat",
                "InventoryFrame",
                "InfoPopup",
                "CharacterInfoFrame",
                "Trade",
                "NpcShop",
                "StorageInven",
                "FriendMenu",
                "FriendWindow",
                "winParty",
            ):
                (movies / (f + ".swf")).touch()
            log = d / "stub.log"
            p = subprocess.run(
                [str(exe), str(movies), str(lib)],
                capture_output=True,
                text=True,
                env={**os.environ, "MUGFX_STUB_LOG": str(log)},
            )
            self.assertEqual(
                p.returncode, 0, p.stdout + p.stderr + log.read_text()[-6000:]
            )
            calls = log.read_text()
            after_clear = calls.split("delAllUnit []", 1)[1]
            self.assertIn("setPartyUnits [[", after_clear)
            self.assertIn('"text":"Shopkeep"', after_clear)
            self.assertIn("Trade completed (offline demo)", calls)
            self.assertIn('AddChatRoom1 [1,560,140,"Shopkeep"', calls)
            self.assertIn('AddChatText [1,0,"Hello friend"]', calls)
            self.assertIn('ChangeChatRoomInfo [1,201,"offline",0]', calls)
            self.assertIn('slTexts.dataProvider.push [{"label":"Again"}]', calls)
            self.assertIn(
                'slTexts.dataProvider.push [{"label":"Hero: Hello friend"}]', calls
            )
            self.assertIn('SetLetterText [3,"Draft survives travel"]', calls)
            self.assertIn(
                "The recipient's mailbox is full. Your draft is still open.", calls
            )
            self.assertIn("SetMailReaded [1,1]", calls)
            # Chat arrivals/reconnects must not reset mailbox checkboxes.
            segment = calls.split('AddChatText [1,0,"Hello friend"]', 1)[1].split(
                'slTexts.dataProvider.push [{"label":"Again"}]', 1
            )[0]
            self.assertNotIn("ClearMailBox", segment)
            self.assertIn(
                'AddChatText [1,0,"He said \\"hello\\" \\\\ end\\u000aé😀"]', calls
            )
            self.assertIn('"type":2,"name":"Hero","msg":"Secret message"', calls)

    def test_requests_membership_map_offer_cancel_and_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / "social"
            subprocess.run(
                [
                    "clang",
                    "-std=c11",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    str(N / "tests/social_session_host.c"),
                    str(N / "core/mu_social.c"),
                    str(N / "core/mu_social_messages.c"),
                    str(N.parent / "reconstructed/social/social.c"),
                    str(N.parent / "reconstructed/social/social_packets.c"),
                    "-o",
                    str(exe),
                ],
                check=True,
                capture_output=True,
            )
            p = subprocess.run([str(exe)], capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertTrue(json.loads(p.stdout)["passed"])


if __name__ == "__main__":
    unittest.main()
