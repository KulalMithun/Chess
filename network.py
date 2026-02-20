import socket
import threading
import json
import random
import string
import time
from constants import DEFAULT_HOST, DEFAULT_PORT, BUFFER_SIZE

def _gen_room_code(n: int = 6) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=n))

class ChessServer:
    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        self.host   = host
        self.port   = port
        self.rooms: dict[str, dict] = {}
        self._lock  = threading.Lock()
        self._running = False
        self._server_sock = None

    def start(self):
        self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_sock.bind((self.host, self.port))
        self._server_sock.listen(10)
        self._running = True
        t = threading.Thread(target=self._accept_loop, daemon=True)
        t.start()
        print(f"[Server] Listening on {self.host}:{self.port}")

    def stop(self):
        self._running = False
        if self._server_sock:
            self._server_sock.close()

    def _accept_loop(self):
        while self._running:
            try:
                conn, addr = self._server_sock.accept()
                t = threading.Thread(target=self._handle_client,
                                     args=(conn, addr), daemon=True)
                t.start()
            except Exception:
                break

    def _send(self, conn: socket.socket, msg: dict):
        try:
            data = json.dumps(msg).encode() + b"\n"
            conn.sendall(data)
        except Exception:
            pass

    def _handle_client(self, conn: socket.socket, addr):
        buf = ""
        try:
            while True:
                chunk = conn.recv(BUFFER_SIZE).decode(errors="ignore")
                if not chunk:
                    break
                buf += chunk
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    line = line.strip()
                    if line:
                        msg = json.loads(line)
                        self._process(conn, msg)
        except Exception:
            pass
        finally:
            self._cleanup(conn)

    def _process(self, conn: socket.socket, msg: dict):
        action = msg.get("action")

        if action == "create_room":
            code = _gen_room_code()
            player_name = msg.get("name", "Host")
            with self._lock:
                self.rooms[code] = {
                    "players": [{"conn": conn, "color": "white", "name": player_name}],
                    "board_fen": "startpos",
                    "moves": [],
                    "chat": [],
                    "started": False,
                    "created": time.time(),
                }
            self._send(conn, {"action": "room_created", "code": code,
                              "color": "white", "name": player_name})

        elif action == "join_room":
            code = msg.get("code", "").upper()
            player_name = msg.get("name", "Guest")
            with self._lock:
                room = self.rooms.get(code)
                if room is None:
                    self._send(conn, {"action": "error", "msg": "Room not found"})
                    return
                if len(room["players"]) >= 2:
                    self._send(conn, {"action": "error", "msg": "Room is full"})
                    return
                room["players"].append({"conn": conn, "color": "black", "name": player_name})
                room["started"] = True
                host = room["players"][0]
                guest = room["players"][1]
                self._send(host["conn"], {"action": "game_start",
                                          "your_color": "white",
                                          "opponent": guest["name"]})
                self._send(guest["conn"], {"action": "game_start",
                                           "your_color": "black",
                                           "opponent": host["name"]})

        elif action == "move":
            code  = msg.get("code")
            move  = msg.get("move")
            fen   = msg.get("fen", "")
            with self._lock:
                room = self.rooms.get(code)
                if not room:
                    return
                room["moves"].append(move)
                room["board_fen"] = fen
                for p in room["players"]:
                    if p["conn"] is not conn:
                        self._send(p["conn"], {"action": "opponent_move",
                                               "move": move, "fen": fen})

        elif action == "chat":
            code = msg.get("code")
            text = msg.get("text", "")
            sender = msg.get("name", "?")
            with self._lock:
                room = self.rooms.get(code)
                if not room:
                    return
                room["chat"].append({"name": sender, "text": text})
                for p in room["players"]:
                    self._send(p["conn"], {"action": "chat",
                                           "name": sender, "text": text})

        elif action == "resign":
            code = msg.get("code")
            with self._lock:
                room = self.rooms.get(code)
                if not room:
                    return
                for p in room["players"]:
                    if p["conn"] is not conn:
                        self._send(p["conn"], {"action": "opponent_resigned"})

        elif action == "draw_offer":
            code = msg.get("code")
            with self._lock:
                room = self.rooms.get(code)
                if not room:
                    return
                for p in room["players"]:
                    if p["conn"] is not conn:
                        self._send(p["conn"], {"action": "draw_offer"})

        elif action == "draw_response":
            code     = msg.get("code")
            accepted = msg.get("accepted", False)
            with self._lock:
                room = self.rooms.get(code)
                if not room:
                    return
                for p in room["players"]:
                    self._send(p["conn"], {"action": "draw_result",
                                           "accepted": accepted})

        elif action == "ping":
            self._send(conn, {"action": "pong"})

    def _cleanup(self, conn: socket.socket):
        with self._lock:
            for code, room in list(self.rooms.items()):
                players = room["players"]
                room["players"] = [p for p in players if p["conn"] is not conn]
                if not room["players"]:
                    del self.rooms[code]
                elif room["started"]:
                    for p in room["players"]:
                        self._send(p["conn"], {"action": "opponent_disconnected"})
        try:
            conn.close()
        except Exception:
            pass

class ChessClient:
    def __init__(self, host: str, port: int = DEFAULT_PORT):
        self.host    = host
        self.port    = port
        self._sock   = None
        self._buf    = ""
        self._lock   = threading.Lock()
        self.connected = False
        self.room_code = ""
        self.my_color  = ""
        self.player_name = "Player"
        self.callbacks: dict[str, list] = {}

    def on(self, action: str, fn):
        self.callbacks.setdefault(action, []).append(fn)

    def _fire(self, action: str, data: dict):
        for fn in self.callbacks.get(action, []):
            try:
                fn(data)
            except Exception as e:
                print(f"[Client callback error] {e}")

    def connect(self) -> bool:
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.settimeout(5)
            self._sock.connect((self.host, self.port))
            self._sock.settimeout(None)
            self.connected = True
            t = threading.Thread(target=self._recv_loop, daemon=True)
            t.start()
            return True
        except Exception as e:
            print(f"[Client] Connect error: {e}")
            return False

    def disconnect(self):
        self.connected = False
        try:
            self._sock.close()
        except Exception:
            pass

    def _send(self, msg: dict):
        try:
            data = json.dumps(msg).encode() + b"\n"
            self._sock.sendall(data)
        except Exception as e:
            print(f"[Client send error] {e}")

    def _recv_loop(self):
        while self.connected:
            try:
                chunk = self._sock.recv(BUFFER_SIZE).decode(errors="ignore")
                if not chunk:
                    self._fire("disconnected", {})
                    break
                self._buf += chunk
                while "\n" in self._buf:
                    line, self._buf = self._buf.split("\n", 1)
                    line = line.strip()
                    if line:
                        msg = json.loads(line)
                        self._fire(msg.get("action", ""), msg)
            except Exception:
                self._fire("disconnected", {})
                break

    def create_room(self):
        self._send({"action": "create_room", "name": self.player_name})

    def join_room(self, code: str):
        self.room_code = code.upper()
        self._send({"action": "join_room",
                    "code": self.room_code,
                    "name": self.player_name})

    def send_move(self, move_uci: str, fen: str):
        self._send({"action": "move", "code": self.room_code,
                    "move": move_uci, "fen": fen})

    def send_chat(self, text: str):
        self._send({"action": "chat", "code": self.room_code,
                    "name": self.player_name, "text": text})

    def resign(self):
        self._send({"action": "resign", "code": self.room_code})

    def offer_draw(self):
        self._send({"action": "draw_offer", "code": self.room_code})

    def respond_draw(self, accepted: bool):
        self._send({"action": "draw_response", "code": self.room_code,
                    "accepted": accepted})

    def ping(self):
        self._send({"action": "ping"})

