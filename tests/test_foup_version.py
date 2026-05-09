import json
import socket
import struct
import sys
import threading
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
UPDATER_DIR = ROOT_DIR / "tools" / "updater"
if str(UPDATER_DIR) not in sys.path:
    sys.path.insert(0, str(UPDATER_DIR))

from voc_updater.foup_version import FoupVersionClient


def _recv_msg(conn: socket.socket) -> str:
    header = conn.recv(4)
    size = struct.unpack(">I", header)[0]
    return conn.recv(size).decode("utf-8")


def _send_msg(conn: socket.socket, text: str) -> None:
    body = text.encode("utf-8")
    conn.sendall(struct.pack(">I", len(body)) + body)


def test_foup_version_client_sends_get_version_and_parses_json() -> None:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]
    received = []

    def run_server() -> None:
        conn, _ = server.accept()
        with conn:
            received.append(_recv_msg(conn))
            _send_msg(
                conn,
                json.dumps({"ps_version": "2.0.1", "pl_version": "2026.05.09"}),
            )
        server.close()

    thread = threading.Thread(target=run_server)
    thread.start()

    version = FoupVersionClient("127.0.0.1", port, timeout=2.0).get_version()

    thread.join(timeout=2)
    assert received == ["get_version"]
    assert version.ps_version == "2.0.1"
    assert version.pl_version == "2026.05.09"


def test_foup_version_client_rejects_missing_fields() -> None:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]

    def run_server() -> None:
        conn, _ = server.accept()
        with conn:
            _recv_msg(conn)
            _send_msg(conn, json.dumps({"ps_version": "2.0.1"}))
        server.close()

    thread = threading.Thread(target=run_server)
    thread.start()

    try:
        FoupVersionClient("127.0.0.1", port, timeout=2.0).get_version()
    except ValueError as exc:
        assert "pl_version" in str(exc)
    else:
        raise AssertionError("expected ValueError")
