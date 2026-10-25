"""The transport, links and connections (NET-LINK-001) checks.

Portable, synthetic, loopback only (every peer is a socket this test opens on 127.0.0.1; nothing is
resolved or connected elsewhere), every lock in a temporary directory (the real game-lock directory
and the per-user lock are never touched: MU_CLIENT_LOCK_PATH and MU_GAME_LOCK_DIR point into the
test's own temp dir):

  * the allowlist refuses an endpoint that is not on it before any connect(2);
  * partial reads: a frame stream arriving one byte at a time comes out of mu_net_next as whole
    frames, in order, byte-identical;
  * partial writes: queued bytes the peer does not read stay pending across flushes and all arrive,
    in order, once it reads;
  * the 0x2000 receive guard: with 0x2000 bytes buffered and no complete frame, the connection
    stops (MU_DECODE_OVERFLOW), as the client's receive routine 0x01290792 stops at 0x012907a8;
  * the client lock: a second transport while one holds the per-user lock is MU_TRANSPORT_LOCKED with
    the owner line; freeing the first releases it; another process's flock is refused too; under
    MU_AGENT=1 the game lock's owner line must equal MU_LOCK_ID (a foreign one, a missing owner file
    and a missing MU_GAME_LOCK_DIR are refused); a running process named main.exe refuses.
Library: native/build/libmunet (ctypes).
"""
import ctypes
from ctypes import POINTER, Structure, byref, c_char, c_char_p, c_int, c_size_t, c_uint8, c_uint16, c_uint32, c_void_p
import fcntl
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import uuid

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent
LIB = NATIVE / 'build' / ('libmunet.dylib' if sys.platform == 'darwin' else 'libmunet.so')

MU_TRANSPORT_OK, MU_TRANSPORT_LOCKED, MU_TRANSPORT_ERROR = 0, 1, 2
MU_LINK_CONNECTING, MU_LINK_OPEN, MU_LINK_CLOSED, MU_LINK_REFUSED = 0, 1, 2, 3
MU_CONN_GAME = 1
MU_DECODE_OK, MU_DECODE_OVERFLOW = 0, 4
RECV_CAP = 0x2000


class Endpoint(Structure):
    _fields_ = [('host', c_char * 256), ('port', c_uint16)]


class Frame(Structure):
    _fields_ = [('conn', c_int), ('head', c_uint8), ('opcode', c_uint8), ('encrypted', c_int), ('length', c_uint32),
                ('bytes', c_uint8 * RECV_CAP), ('tick', c_uint32)]


class Counters(Structure):
    _fields_ = [('bytes_in', ctypes.c_uint64), ('bytes_out', ctypes.c_uint64), ('links_opened', c_uint32),
                ('links_refused', c_uint32), ('connects_attempted', c_uint32)]


def endpoint(host, port):
    e = Endpoint()
    e.host = host.encode()
    e.port = port
    return e


def load():
    L = ctypes.CDLL(str(LIB))
    L.mu_transport_sockets.restype = c_void_p
    L.mu_transport_sockets.argtypes = [POINTER(Endpoint), c_size_t, POINTER(c_int), c_char_p, c_size_t]
    L.mu_transport_free.argtypes = [c_void_p]
    L.mu_transport_poll.argtypes = [c_void_p, c_uint32]
    L.mu_transport_flush.restype = c_size_t
    L.mu_transport_flush.argtypes = [c_void_p]
    L.mu_transport_counters_get.argtypes = [c_void_p, POINTER(Counters)]
    L.mu_link_open.restype = c_int
    L.mu_link_open.argtypes = [c_void_p, POINTER(Endpoint)]
    L.mu_link_state_of.restype = c_int
    L.mu_link_state_of.argtypes = [c_void_p, c_int, POINTER(c_int)]
    L.mu_link_write.restype = c_int
    L.mu_link_write.argtypes = [c_void_p, c_int, c_char_p, c_size_t]
    L.mu_net_create.restype = c_void_p
    L.mu_net_create.argtypes = [c_void_p, c_char_p, c_size_t]
    L.mu_net_destroy.argtypes = [c_void_p]
    L.mu_net_connect.restype = c_int
    L.mu_net_connect.argtypes = [c_void_p, c_int, POINTER(Endpoint)]
    L.mu_net_allow.restype = c_int
    L.mu_net_allow.argtypes = [c_void_p, POINTER(Endpoint)]
    L.mu_net_state.restype = c_int
    L.mu_net_state.argtypes = [c_void_p, c_int, POINTER(c_int)]
    L.mu_net_next.restype = c_int
    L.mu_net_next.argtypes = [c_void_p, c_int, POINTER(Frame), POINTER(c_int)]
    return L


class Peer:
    """A loopback server socket the test drives (the only kind of peer these tests ever use)."""

    def __init__(self, rcvbuf=None):
        self.ls = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ls.bind(('127.0.0.1', 0))
        if rcvbuf:
            self.ls.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, rcvbuf)
        self.ls.listen(1)
        self.port = self.ls.getsockname()[1]
        self.conn = None

    def accept(self):
        self.ls.settimeout(5)
        self.conn, _ = self.ls.accept()
        return self.conn

    def close(self):
        if self.conn:
            self.conn.close()
        self.ls.close()


@unittest.skipUnless(LIB.exists(), 'libmunet not built (make -C native)')
class Transport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.L = load()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = dict(os.environ)
        for k in ('MU_AGENT', 'MU_LOCK_ID', 'MU_GAME_LOCK_DIR'):
            os.environ.pop(k, None)
        os.environ['MU_CLIENT_LOCK_PATH'] = os.path.join(self.tmp.name, 'client.lock')
        # a name no real process has: the owner's own game must not decide these tests
        os.environ['MU_CLIENT_PROCESS_NAMES'] = 'mu-test-%s.exe' % uuid.uuid4().hex[:12]

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.env)
        self.tmp.cleanup()

    def sockets(self, *eps):
        arr = (Endpoint * max(1, len(eps)))(*eps)
        st = c_int(-1)
        err = ctypes.create_string_buffer(512)
        t = self.L.mu_transport_sockets(arr, len(eps), byref(st), err, 512)
        return t, st.value, err.value.decode()

    def open_net(self, peer):
        t, st, err = self.sockets(endpoint('127.0.0.1', peer.port))
        self.assertEqual(st, MU_TRANSPORT_OK, err)
        n = self.L.mu_net_create(t, None, 0)
        self.assertEqual(self.L.mu_net_connect(n, MU_CONN_GAME, byref(endpoint('127.0.0.1', peer.port))), 0)
        peer.accept()
        deadline = time.time() + 5
        while self.L.mu_net_state(n, MU_CONN_GAME, None) != MU_LINK_OPEN and time.time() < deadline:
            self.L.mu_transport_poll(t, 0)
            time.sleep(0.005)
        self.assertEqual(self.L.mu_net_state(n, MU_CONN_GAME, None), MU_LINK_OPEN)
        return t, n

    def frames(self, t, n, want, timeout=5.0):
        out, f, ds = [], Frame(), c_int()
        deadline = time.time() + timeout
        while len(out) < want and time.time() < deadline:
            self.L.mu_transport_poll(t, 0)
            while self.L.mu_net_next(n, MU_CONN_GAME, byref(f), byref(ds)):
                self.assertEqual(ds.value, MU_DECODE_OK)
                out.append(bytes(f.bytes[:f.length]))
            time.sleep(0.002)
        return out

    # ---- allowlist ------------------------------------------------------------------------------

    def test_allowlist_refuses_before_connect(self):
        allowed, other = Peer(), Peer()
        try:
            t, st, err = self.sockets(endpoint('127.0.0.1', allowed.port))
            self.assertEqual(st, MU_TRANSPORT_OK, err)
            link = self.L.mu_link_open(t, byref(endpoint('127.0.0.1', other.port)))
            self.assertGreaterEqual(link, 0)
            self.assertEqual(self.L.mu_link_state_of(t, link, None), MU_LINK_REFUSED)
            self.assertEqual(self.L.mu_link_write(t, link, b'\xc1\x03\x00', 3), -1)
            c = Counters()
            self.L.mu_transport_counters_get(t, byref(c))
            self.assertEqual((c.links_refused, c.connects_attempted, c.links_opened), (1, 0, 0))
            other.ls.settimeout(0.2)
            with self.assertRaises(socket.timeout):   # nothing ever reached the refused peer
                other.ls.accept()
            # the allowed one connects
            ok = self.L.mu_link_open(t, byref(endpoint('127.0.0.1', allowed.port)))
            allowed.accept()
            self.L.mu_transport_poll(t, 0)
            self.assertIn(self.L.mu_link_state_of(t, ok, None), (MU_LINK_CONNECTING, MU_LINK_OPEN))
            self.L.mu_transport_free(t)
        finally:
            allowed.close()
            other.close()

    def test_connection_does_not_widen_the_allowlist(self):
        allowed, other = Peer(), Peer()
        try:
            t, st, err = self.sockets(endpoint('127.0.0.1', allowed.port))
            self.assertEqual(st, MU_TRANSPORT_OK, err)
            n = self.L.mu_net_create(t, None, 0)
            # a connection to an endpoint nobody allowed is refused; only mu_net_allow (an endpoint the
            # session learned from the service) widens the list
            self.assertEqual(self.L.mu_net_connect(n, MU_CONN_GAME, byref(endpoint('127.0.0.1', other.port))), 0)
            self.assertEqual(self.L.mu_net_state(n, MU_CONN_GAME, None), MU_LINK_REFUSED)
            self.L.mu_net_allow(n, byref(endpoint('127.0.0.1', other.port)))
            self.assertEqual(self.L.mu_net_connect(n, MU_CONN_GAME, byref(endpoint('127.0.0.1', other.port))), 0)
            other.accept()
            self.assertIn(self.L.mu_net_state(n, MU_CONN_GAME, None), (MU_LINK_CONNECTING, MU_LINK_OPEN))
            self.L.mu_net_destroy(n)
            self.L.mu_transport_free(t)
        finally:
            allowed.close()
            other.close()

    # ---- partial reads and writes ---------------------------------------------------------------

    def test_partial_reads_reassemble_frames(self):
        peer = Peer()
        try:
            t, n = self.open_net(peer)
            frames = [bytes([0xc1, 5, 0xa0, 0x06, 0x01]), bytes([0xc2, 0x00, 0x07, 0x55, 0x57, 9, 9]),
                      bytes([0xc1, 0x0c, 0xa0, 0x11]) + bytes(range(8)), bytes([0xc1, 3, 0x16])]
            stream = b''.join(frames)

            def trickle():
                for b in stream:
                    peer.conn.sendall(bytes([b]))
                    time.sleep(0.002)
            th = threading.Thread(target=trickle)
            th.start()
            got = self.frames(t, n, len(frames))
            th.join()
            self.assertEqual(got, frames)
            self.L.mu_net_destroy(n)
            self.L.mu_transport_free(t)
        finally:
            peer.close()

    def test_partial_writes_stay_queued(self):
        peer = Peer(rcvbuf=4096)
        try:
            t, st, err = self.sockets(endpoint('127.0.0.1', peer.port))
            self.assertEqual(st, MU_TRANSPORT_OK, err)
            link = self.L.mu_link_open(t, byref(endpoint('127.0.0.1', peer.port)))
            peer.accept()
            for _ in range(200):
                self.L.mu_transport_poll(t, 0)
                if self.L.mu_link_state_of(t, link, None) == MU_LINK_OPEN:
                    break
                time.sleep(0.005)
            payload = os.urandom(8 << 20)
            self.assertEqual(self.L.mu_link_write(t, link, payload, len(payload)), 0)
            pending = self.L.mu_transport_flush(t)
            self.assertGreater(pending, 0)                  # the kernel took only part of it
            self.assertLess(pending, len(payload) + 1)
            self.assertGreater(self.L.mu_transport_flush(t), 0)   # still pending while the peer reads nothing
            received = bytearray()
            peer.conn.settimeout(5)
            deadline = time.time() + 20
            while len(received) < len(payload) and time.time() < deadline:
                received += peer.conn.recv(1 << 16)
                self.L.mu_transport_flush(t)
            self.assertEqual(self.L.mu_transport_flush(t), 0)
            self.assertEqual(bytes(received), payload)
            c = Counters()
            self.L.mu_transport_counters_get(t, byref(c))
            self.assertEqual(c.bytes_out, len(payload))
            self.L.mu_transport_free(t)
        finally:
            peer.close()

    # ---- the 0x2000 receive guard ---------------------------------------------------------------

    def test_receive_guard_stops_the_connection(self):
        peer = Peer()
        try:
            t, n = self.open_net(peer)
            # a C2 frame declaring 0x3000 bytes can never complete in the 0x2000 ring
            peer.conn.sendall(bytes([0xc2, 0x30, 0x00, 0x99]) + bytes(RECV_CAP + 0x400))
            f, ds = Frame(), c_int(-1)
            deadline = time.time() + 5
            stopped = False
            while time.time() < deadline and not stopped:
                self.L.mu_transport_poll(t, 0)
                got = self.L.mu_net_next(n, MU_CONN_GAME, byref(f), byref(ds))
                self.assertEqual(got, 0)                     # no frame is ever delivered
                stopped = ds.value == MU_DECODE_OVERFLOW
                time.sleep(0.002)
            self.assertTrue(stopped, 'the connection did not stop at the 0x2000 guard')
            # sticky: later calls stay stopped and deliver nothing
            self.assertEqual(self.L.mu_net_next(n, MU_CONN_GAME, byref(f), byref(ds)), 0)
            self.assertEqual(ds.value, MU_DECODE_OVERFLOW)
            self.L.mu_net_destroy(n)
            self.L.mu_transport_free(t)
        finally:
            peer.close()

    def test_frames_before_the_guard_are_delivered(self):
        peer = Peer()
        try:
            t, n = self.open_net(peer)
            good = [bytes([0xc1, 0x04, 0x55, 0x94])] * 3
            peer.conn.sendall(b''.join(good))
            self.assertEqual(self.frames(t, n, 3), good)
            self.L.mu_net_destroy(n)
            self.L.mu_transport_free(t)
        finally:
            peer.close()

    # ---- the client lock ------------------------------------------------------------------------

    def test_lock_held_then_released_on_free(self):
        peer = Peer()
        try:
            ep = endpoint('127.0.0.1', peer.port)
            t1, st, err = self.sockets(ep)
            self.assertEqual(st, MU_TRANSPORT_OK, err)
            t2, st2, err2 = self.sockets(ep)
            self.assertIsNone(t2)
            self.assertEqual(st2, MU_TRANSPORT_LOCKED)
            self.assertIn('mu-native pid %d' % os.getpid(), err2)   # the owner line
            self.L.mu_transport_free(t1)
            t3, st3, err3 = self.sockets(ep)
            self.assertEqual(st3, MU_TRANSPORT_OK, err3)
            self.L.mu_transport_free(t3)
        finally:
            peer.close()

    def test_lock_held_by_another_process(self):
        path = os.environ['MU_CLIENT_LOCK_PATH']
        with open(path, 'w') as f:
            f.write('other-client pid 1\n')
        holder = subprocess.Popen([sys.executable, '-c',
                                   'import fcntl,sys,time\nf=open(sys.argv[1],"a")\nfcntl.flock(f,fcntl.LOCK_EX)\n'
                                   'print("held",flush=True)\ntime.sleep(30)', path], stdout=subprocess.PIPE, text=True)
        try:
            self.assertEqual(holder.stdout.readline().strip(), 'held')
            t, st, err = self.sockets(endpoint('127.0.0.1', 1))
            self.assertIsNone(t)
            self.assertEqual(st, MU_TRANSPORT_LOCKED)
            self.assertIn('other-client pid 1', err)
        finally:
            holder.kill()
            holder.wait()
            holder.stdout.close()
        t, st, err = self.sockets(endpoint('127.0.0.1', 1))
        self.assertEqual(st, MU_TRANSPORT_OK, err)
        self.L.mu_transport_free(t)

    def test_agent_game_lock_owner_check(self):
        lockdir = Path(self.tmp.name) / 'game-lock'
        os.environ['MU_AGENT'] = '1'
        ep = endpoint('127.0.0.1', 1)
        # no MU_GAME_LOCK_DIR: no lock path is compiled in
        t, st, err = self.sockets(ep)
        self.assertEqual((t, st), (None, MU_TRANSPORT_ERROR))
        self.assertIn('MU_GAME_LOCK_DIR', err)
        os.environ['MU_GAME_LOCK_DIR'] = str(lockdir)
        # the lock is not held at all
        t, st, err = self.sockets(ep)
        self.assertEqual((t, st), (None, MU_TRANSPORT_LOCKED))
        self.assertIn('not held', err)
        lockdir.mkdir()
        (lockdir / 'owner').write_text('agent-transport-test Sat Oct 25 2026\nsecond line ignored\n')
        # a foreign MU_LOCK_ID
        os.environ['MU_LOCK_ID'] = 'someone-else'
        t, st, err = self.sockets(ep)
        self.assertEqual((t, st), (None, MU_TRANSPORT_LOCKED))
        self.assertIn('agent-transport-test Sat Oct 25 2026', err)
        # no MU_LOCK_ID at all
        del os.environ['MU_LOCK_ID']
        t, st, err = self.sockets(ep)
        self.assertEqual((t, st), (None, MU_TRANSPORT_LOCKED))
        # the owner line itself
        os.environ['MU_LOCK_ID'] = 'agent-transport-test Sat Oct 25 2026'
        t, st, err = self.sockets(ep)
        self.assertEqual(st, MU_TRANSPORT_OK, err)
        self.L.mu_transport_free(t)
        self.assertTrue((lockdir / 'owner').exists())   # the transport never removes the agent's lock

    def test_original_client_running_refuses(self):
        # a stand-in process whose argument list names the client the way Wine shows it
        name = os.environ['MU_CLIENT_PROCESS_NAMES']
        fake = subprocess.Popen(['C:\\MuTheMatrix\\' + name, '30'], executable='/bin/sleep')
        try:
            time.sleep(0.2)
            t, st, err = self.sockets(endpoint('127.0.0.1', 1))
            self.assertEqual((t, st), (None, MU_TRANSPORT_LOCKED))
            self.assertIn(name, err)
            self.assertIn('pid %d' % fake.pid, err)
        finally:
            fake.kill()
            fake.wait()
        t, st, err = self.sockets(endpoint('127.0.0.1', 1))
        self.assertEqual(st, MU_TRANSPORT_OK, err)
        self.L.mu_transport_free(t)

    def test_default_names_include_main_exe(self):
        # without the test override, main.exe and MuTheMatrix.exe are the names refused (whether or not the
        # owner's own client also runs right now, a stand-in named main.exe must be refused)
        del os.environ['MU_CLIENT_PROCESS_NAMES']
        for exe in ('main.exe', 'MuTheMatrix.exe'):
            fake = subprocess.Popen(['C:\\MuTheMatrix\\' + exe, '30'], executable='/bin/sleep')
            try:
                time.sleep(0.2)
                t, st, err = self.sockets(endpoint('127.0.0.1', 1))
                self.assertEqual((t, st), (None, MU_TRANSPORT_LOCKED))
                self.assertIn('original client is running', err)
            finally:
                fake.kill()
                fake.wait()


if __name__ == '__main__':
    unittest.main()
