import base64
import hashlib
import os
import socket
import ssl
import struct
import threading

try:
    from urllib.parse import urlsplit
except ImportError:
    from urlparse import urlsplit

GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
OP_CONT, OP_TEXT, OP_BIN, OP_CLOSE, OP_PING, OP_PONG = 0, 1, 2, 8, 9, 10


class WebSocketError(Exception):
    pass


class WebSocketClosed(WebSocketError):
    pass


class WebSocketClient(object):
    def __init__(self, url, connect_timeout=10.0, read_timeout=30.0):
        self._url = url
        self._connect_timeout = connect_timeout
        self._read_timeout = read_timeout
        self._socket = None
        self._send_lock = threading.Lock()
        self._buffer = b""

    def connect(self):
        parts = urlsplit(self._url)
        secure = parts.scheme in ("wss", "https")
        port = parts.port or (443 if secure else 80)
        raw = socket.create_connection((parts.hostname, port), self._connect_timeout)
        if secure:
            raw = ssl.create_default_context().wrap_socket(raw, server_hostname=parts.hostname)
        raw.settimeout(self._connect_timeout)
        self._socket = raw
        path = parts.path or "/"
        if parts.query:
            path += "?" + parts.query
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        request = (
            "GET %s HTTP/1.1\r\nHost: %s\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
            "Sec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n" % (path, parts.netloc, key)
        )
        raw.sendall(request.encode("ascii"))
        head = self._read_until(b"\r\n\r\n")
        lines = head.decode("latin-1").split("\r\n")
        if " 101 " not in lines[0] + " ":
            raise WebSocketError("handshake rejected: %s" % lines[0])
        headers = {}
        for line in lines[1:]:
            if ":" in line:
                name, value = line.split(":", 1)
                headers[name.strip().lower()] = value.strip()
        expected = base64.b64encode(hashlib.sha1((key + GUID).encode("ascii")).digest()).decode("ascii")
        if headers.get("sec-websocket-accept") != expected:
            raise WebSocketError("bad accept key")
        raw.settimeout(self._read_timeout)

    def _read_until(self, marker):
        while marker not in self._buffer:
            chunk = self._socket.recv(4096)
            if not chunk:
                raise WebSocketClosed("closed during handshake")
            self._buffer += chunk
        head, _, rest = self._buffer.partition(marker)
        self._buffer = rest
        return head

    def _read_exact(self, size):
        while len(self._buffer) < size:
            chunk = self._socket.recv(max(4096, size - len(self._buffer)))
            if not chunk:
                raise WebSocketClosed("connection closed")
            self._buffer += chunk
        data, self._buffer = self._buffer[:size], self._buffer[size:]
        return data

    def send_text(self, text):
        self._send(OP_TEXT, text.encode("utf-8"))

    def _send(self, opcode, payload):
        header = bytearray([0x80 | opcode])
        length = len(payload)
        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.append(0x80 | 126)
            header.extend(struct.pack("!H", length))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack("!Q", length))
        mask = os.urandom(4)
        header.extend(mask)
        masked = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        with self._send_lock:
            try:
                self._socket.sendall(bytes(header) + masked)
            except (OSError, AttributeError) as error:
                raise WebSocketClosed(str(error))

    def receive_text(self):
        message = bytearray()
        while True:
            try:
                first, second = struct.unpack("!BB", self._read_exact(2))
            except socket.timeout:
                self._send(OP_PING, b"")
                continue
            opcode = first & 0x0F
            final = bool(first & 0x80)
            length = second & 0x7F
            if length == 126:
                length = struct.unpack("!H", self._read_exact(2))[0]
            elif length == 127:
                length = struct.unpack("!Q", self._read_exact(8))[0]
            payload = self._read_exact(length)
            if opcode == OP_PING:
                self._send(OP_PONG, payload)
            elif opcode == OP_PONG:
                continue
            elif opcode == OP_CLOSE:
                self.close()
                raise WebSocketClosed("closed by peer")
            elif opcode in (OP_TEXT, OP_BIN, OP_CONT):
                message.extend(payload)
                if final:
                    return bytes(message).decode("utf-8")

    def close(self):
        sock, self._socket = self._socket, None
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass
