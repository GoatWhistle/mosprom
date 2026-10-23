import base64
import hashlib
import json
import queue
import socket
import struct
import threading

GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


class FakeSocketServer(object):
    def __init__(self, accept=True):
        self.accept = accept
        self.received = queue.Queue()
        self.connections = []
        self.paths = []
        self._listener = socket.socket()
        self._listener.bind(("127.0.0.1", 0))
        self._listener.listen(5)
        self.port = self._listener.getsockname()[1]
        self._thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._thread.start()

    def url(self):
        return "http://127.0.0.1:%d" % self.port

    def _accept_loop(self):
        while True:
            try:
                conn, _ = self._listener.accept()
            except OSError:
                return
            threading.Thread(target=self._serve, args=(conn,), daemon=True).start()

    def _serve(self, conn):
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = conn.recv(4096)
            if not chunk:
                return
            data += chunk
        head = data.decode("latin-1")
        self.paths.append(head.split(" ")[1])
        if not self.accept:
            conn.sendall(b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\n\r\n")
            conn.close()
            return
        key = [line.split(":", 1)[1].strip() for line in head.split("\r\n") if line.lower().startswith("sec-websocket-key")][0]
        accept = base64.b64encode(hashlib.sha1((key + GUID).encode()).digest()).decode()
        conn.sendall(("HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                      "Sec-WebSocket-Accept: %s\r\n\r\n" % accept).encode())
        self.connections.append(conn)
        try:
            while True:
                text = self._read(conn)
                if text is None:
                    return
                self.received.put(json.loads(text))
        except OSError:
            return

    def _read(self, conn):
        header = self._exact(conn, 2)
        if header is None:
            return None
        opcode = header[0] & 0x0F
        length = header[1] & 0x7F
        if length == 126:
            length = struct.unpack("!H", self._exact(conn, 2))[0]
        elif length == 127:
            length = struct.unpack("!Q", self._exact(conn, 8))[0]
        mask = self._exact(conn, 4)
        payload = bytes(b ^ mask[i % 4] for i, b in enumerate(self._exact(conn, length)))
        if opcode == 8:
            return None
        if opcode in (9, 10):
            return self._read(conn)
        return payload.decode("utf-8")

    def _exact(self, conn, size):
        data = b""
        while len(data) < size:
            chunk = conn.recv(size - len(data))
            if not chunk:
                return None
            data += chunk
        return data

    def send(self, frame, index=-1):
        payload = json.dumps(frame).encode("utf-8")
        header = bytearray([0x81])
        if len(payload) < 126:
            header.append(len(payload))
        elif len(payload) < 65536:
            header.append(126)
            header.extend(struct.pack("!H", len(payload)))
        else:
            header.append(127)
            header.extend(struct.pack("!Q", len(payload)))
        self.connections[index].sendall(bytes(header) + payload)

    def drop(self, index=-1):
        try:
            self.connections[index].shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self.connections[index].close()

    def get(self, timeout=5.0):
        return self.received.get(timeout=timeout)

    def close(self):
        self._listener.close()
        for conn in self.connections:
            try:
                conn.close()
            except OSError:
                pass
