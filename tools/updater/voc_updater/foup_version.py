from __future__ import annotations

import json
import socket
import struct
from dataclasses import dataclass


@dataclass(frozen=True)
class FoupVersion:
    ps_version: str
    pl_version: str


class FoupVersionClient:
    def __init__(self, host: str, port: int, timeout: float = 5.0) -> None:
        self.host = host
        self.port = int(port)
        self.timeout = float(timeout)

    def get_version(self) -> FoupVersion:
        with socket.create_connection((self.host, self.port), timeout=self.timeout) as sock:
            sock.settimeout(self.timeout)
            self._send_msg(sock, "get_version")
            response = self._recv_msg(sock)
        try:
            payload = json.loads(response)
        except json.JSONDecodeError as exc:
            raise ValueError("FOUP get_version response is not JSON") from exc
        ps_version = str(payload.get("ps_version") or "")
        pl_version = str(payload.get("pl_version") or "")
        if not ps_version:
            raise ValueError("FOUP get_version response missing ps_version")
        if not pl_version:
            raise ValueError("FOUP get_version response missing pl_version")
        return FoupVersion(ps_version=ps_version, pl_version=pl_version)

    @staticmethod
    def _send_msg(sock: socket.socket, text: str) -> None:
        body = text.encode("utf-8")
        sock.sendall(struct.pack(">I", len(body)) + body)

    @staticmethod
    def _recv_msg(sock: socket.socket) -> str:
        header = FoupVersionClient._recv_exact(sock, 4)
        size = struct.unpack(">I", header)[0]
        body = FoupVersionClient._recv_exact(sock, size)
        return body.decode("utf-8")

    @staticmethod
    def _recv_exact(sock: socket.socket, size: int) -> bytes:
        chunks = bytearray()
        while len(chunks) < size:
            chunk = sock.recv(size - len(chunks))
            if not chunk:
                raise ConnectionError("socket closed while reading FOUP response")
            chunks.extend(chunk)
        return bytes(chunks)
