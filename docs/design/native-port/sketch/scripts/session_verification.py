"""Verification side of the session core (sketch, signatures only).

New evidence kinds, each with the project's usual shape (pinned inputs from scripts/pins.py,
seeded cases, planted mistakes, explicit skips when private inputs are missing):

  gen_dispatch.py / validate_dispatch.py    the route table IS the client's routing
  validate_crypto.py / validate_decode.py   function families under Unicorn (client_ui_machine)
  session fixture runs (portable, CI)       full stack over real framed bytes, synthetic root
  replay_oracle.py (private)                every inbound frame of a journal re-run through the
                                            ORIGINAL 0x01287ead, seeded from the native records
  session_compare.py (private)              native session records vs the original's memory,
                                            WorldTime-aligned, from a recorded stream (gate 3)
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# ---- scripts/gen_dispatch.py + scripts/validate_dispatch.py ---------------------------------


@dataclass(frozen=True)
class ClientRoute:
    opcode: int
    sub: int | None          # None: not sub-dispatched
    head_family: str         # "c1" (C1/C3) or "c2" (C2/C4)
    handler: int             # client address the original reaches


def extract_client_routes(text_section: Path, text_sha256: str) -> list[ClientRoute]:
    """Reads the 254-entry jump table 0x0128e59d and each sub-dispatcher's cases from the
    restored text, then confirms every route by running 0x01287ead under Unicorn with the
    handlers stubbed (recording which stub ran with which arguments) over every opcode, every
    sub byte and both head families."""
    raise NotImplementedError


def write_dispatch_def(routes: list[ClientRoute], out: Path) -> None:
    """Writes native/net/dispatch.def (MU_FAMILY / MU_ROUTE rows tagged MU_VERIFIED). Checked in;
    a later run that would change it fails unless --update is given (a client re-pin)."""
    raise NotImplementedError


def compare_routes(client: list[ClientRoute], dispatch_def: Path) -> dict:
    """Every client route has exactly one dispatch.def row with the same handler address and
    vice versa. Planted mistakes: a swapped row, a dropped family offset, a wrong head family."""
    raise NotImplementedError


def coverage(mu_session_tool: Path, journal: Path | None = None) -> dict:
    """`mu-session routes` + (optionally) a journal: bound / unbound / ignored routes by client
    address, and per unbound route the number of frames a run actually hit. This is the
    remaining-work list for the network side, derived, never hand-kept."""
    raise NotImplementedError


# ---- native/tests/test_session_fixture.py (portable, CI) ------------------------------------


def run_fixture(binary: str, scenario: Path, script: str, frames: int) -> dict:
    """verify-mu-native style run: `mu-shell --headless --fixture SCENARIO --script ...
    --journal OUT` on the synthetic game root; returns the frame rows plus the journal summary
    (frames in/out, intents by status, unbound frames, cues). Asserts: scene 6 reached through
    real framed C1/C3 bytes, unbound == 0 for the scenario's routes, the CryptoModule path
    exercised (C3 frames > 0), a non-loopback connect attempt never happens (the transport's
    own counter)."""
    raise NotImplementedError


# ---- scripts/replay_oracle.py (private; graft from the re-hosted-image candidate) -----------


def replay_oracle(journal: Path, text: Path, data: Path, layout_json: Path,
                  scope: str = "touched") -> dict:
    """For every inbound FRAME record of a journal (fixture or recorded), take the SNAPSHOT of
    the session's client-layout records just before it, map them into client_ui_machine at
    their client addresses (layout.json says where), run the ORIGINAL 0x01287ead(opcode,
    packet, length, encrypted) with callees stubbed, and require (a) the record bytes the
    original writes and (b) its call stream to equal what the native apply wrote and cued.
    Because the session stores the handlers' own record types, seeding needs no marshalling
    beyond the generated layout. Reads of bytes the snapshot does not define stop the case (the
    machine's definedness tracking), so an incomplete layout shows up as a coverage number, not
    as a false pass. Planted mistakes: a wrong apply bound to a route, a dropped write-back in
    a projection adapter, an off-by-one field in the layout manifest."""
    raise NotImplementedError


# ---- scripts/session_compare.py (private, gate 3) -------------------------------------------


@dataclass(frozen=True)
class LiveSnapshot:
    world_time: float        # [0x06fce370] read with the snapshot
    records: dict[str, bytes]  # record name (layout.json) -> bytes read by memread


def compare_session(native_journal: Path, live: list[LiveSnapshot], layout_json: Path) -> dict:
    """Replays a recorded original-client stream (CAPTURE-KIT-001 recording of the owner's own
    session) into `mu-session replay`, dumping every domain in client layout at the WorldTime of
    each live snapshot, and diffs field by field using layout.json (the same manifest the lease
    audit, the projection adapters and the journal dump are generated from). Reports per record:
    equal fields, differing fields with both values, fields not compared (MOTION zone within a
    stated tolerance; VIEW zone; fields the manifest does not bind)."""
    raise NotImplementedError
