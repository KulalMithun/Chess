from __future__ import annotations
import pygame
import chess
import threading
import time
import math
import socket
from constants import *
from ui import (Button, InputBox, draw_panel, draw_gradient_bg,
                draw_text, draw_rounded_rect, ParticleField,
                Toast, draw_move_log, draw_chat, PromotionDialog,
                text_width)
from board_renderer import BoardRenderer
from assets import get_piece_surface
from scorecard import ScoreCard
from bot import ChessBot

def _font(sz, bold=False):
    try:
        return pygame.font.SysFont("Segoe UI", sz, bold=bold)
    except Exception:
        return pygame.font.SysFont(None, sz, bold=bold)

def _make_clock_str(seconds: float) -> str:
    m = int(seconds) // 60
    s = int(seconds) % 60
    return f"{m:02d}:{s:02d}"

class _Clock:
    def __init__(self, total_secs: float = 600.0):
        self.times = {chess.WHITE: total_secs, chess.BLACK: total_secs}
        self._last  = None
        self._active_color = chess.WHITE
        self._running = False

    def start(self):
        self._running = True
        self._last = time.time()

    def stop(self):
        self._running = False

    def switch(self, new_color):
        self._tick()
        self._active_color = new_color

    def _tick(self):
        if self._running and self._last is not None:
            now = time.time()
            self.times[self._active_color] -= (now - self._last)
            if self.times[self._active_color] < 0:
                self.times[self._active_color] = 0
            self._last = now

    def update(self):
        self._tick()
        self._last = time.time()

    def flagged(self):
        for c in (chess.WHITE, chess.BLACK):
            if self.times[c] <= 0:
                return c
        return None

    def str(self, color: chess.Color) -> str:
        return _make_clock_str(self.times[color])

class MainMenu:
    def __init__(self, screen: pygame.Surface, scorecard: ScoreCard):
        self.screen    = screen
        self.scorecard = scorecard
        self.next      = None
        self._particles = ParticleField(WINDOW_W, WINDOW_H, 60)
        self._toasts: list[Toast] = []
        self._anim_t = time.time()

        bw, bh = 280, 52
        cx = WINDOW_W // 2
        self._btns = [
            Button(pygame.Rect(cx - bw // 2, 300, bw, bh),
                   "Play vs Bot", C_ACCENT, C_BG, 20),
            Button(pygame.Rect(cx - bw // 2, 368, bw, bh),
                   "Multiplayer (Online)", C_ACCENT2, C_BG, 20),
            Button(pygame.Rect(cx - bw // 2, 436, bw, bh),
                   "Local 2-Player", (88, 200, 120), C_BG, 20),
            Button(pygame.Rect(cx - bw // 2, 504, bw, bh),
                   "Score Card", (180, 100, 240), C_BG, 20),
            Button(pygame.Rect(cx - bw // 2, 572, bw, bh),
                   "Quit", C_RED, C_TEXT, 20),
        ]

        self._name_box = InputBox(
            pygame.Rect(cx - 140, 250, 280, 38),
            placeholder=self.scorecard.player_name,
            max_len=20, font_size=16
        )
        self._name_box.text = self.scorecard.player_name

    def handle_events(self, events):
        mouse = pygame.mouse.get_pos()
        for btn in self._btns:
            btn.update(mouse)
        for event in events:
            self._name_box.handle_event(event)
            for i, btn in enumerate(self._btns):
                if btn.handle_event(event):
                    name = self._name_box.text.strip() or "Player"
                    self.scorecard.set_name(name)
                    if i == 0:
                        self.next = ("bot_setup", None)
                    elif i == 1:
                        self.next = ("multiplayer", None)
                    elif i == 2:
                        self.next = ("local2p", None)
                    elif i == 3:
                        self.next = ("scorecard", None)
                    elif i == 4:
                        self.next = ("quit", None)

    def draw(self):
        draw_gradient_bg(self.screen)
        self._particles.update_draw(self.screen)

        t = time.time() - self._anim_t
        cx = WINDOW_W // 2

        title_font = _font(52, True)
        title = title_font.render("CHESS MASTER", True, C_TEXT)
        tx = cx - title.get_width() // 2
        ty = int(42 + math.sin(t * 0.8) * 3)
        self.screen.blit(title, (tx, ty))

        uw = title.get_width() // 2
        pygame.draw.line(self.screen, C_ACCENT,
                         (cx - uw // 2, ty + title.get_height() + 6),
                         (cx + uw // 2, ty + title.get_height() + 6), 3)

        elo_str = f"ELO  {self.scorecard.elo}"
        badge_w = max(120, len(elo_str) * 10 + 24)
        draw_rounded_rect(self.screen, C_ACCENT,
                          pygame.Rect(cx - badge_w // 2, 120, badge_w, 34), 17)
        draw_text(self.screen, elo_str, (cx, 137),
                  size=16, bold=True, color=C_BG, center=True)

        draw_text(self.screen, "Welcome back,",
                  (cx, 180), size=15, color=C_TEXT_DIM, center=True)
        draw_text(self.screen, self.scorecard.player_name,
                  (cx, 202), size=22, bold=True, center=True)

        draw_text(self.screen, "Your Name:",
                  (cx - 140, 232), size=13, color=C_TEXT_DIM)
        self._name_box.draw(self.screen)

        for btn in self._btns:
            btn.draw(self.screen)

        draw_text(self.screen, "Chess Master v2.0",
                  (cx, WINDOW_H - 20), size=12,
                  color=C_TEXT_DIM, center=True)

        self._toasts = [t for t in self._toasts if t.alive()]
        for toast in self._toasts:
            toast.draw(self.screen)

    def push_toast(self, msg: str, color=C_GREEN):
        self._toasts.append(Toast(msg, color=color))

class BotSetupScreen:
    LEVELS = list(BOT_LEVELS.keys())
    TIMES  = [("No Limit", 0), ("1 min", 60), ("3 min", 180),
              ("5 min", 300), ("10 min", 600), ("15 min", 900)]

    def __init__(self, screen, scorecard):
        self.screen    = screen
        self.scorecard = scorecard
        self.next      = None
        self._selected_level = "Medium"
        self._selected_time  = 0
        self._color_choice   = "white"
        self._particles      = ParticleField(WINDOW_W, WINDOW_H, 30)

        self._back = Button(pygame.Rect(30, 20, 100, 38),
                            "← Back", C_PANEL2, C_TEXT, 15)

        self._play = Button(pygame.Rect(WINDOW_W // 2 - 140, 680, 280, 52),
                            "Start Game", C_ACCENT, C_BG, 20)

        lbw = 130
        self._lvl_btns = {}
        for i, lvl in enumerate(self.LEVELS):
            col = i % 3
            row = i // 3
            x = WINDOW_W // 2 - 205 + col * (lbw + 10)
            y = 230 + row * 70
            color = C_ACCENT if lvl == self._selected_level else C_PANEL2
            self._lvl_btns[lvl] = Button(
                pygame.Rect(x, y, lbw, 54), lvl, color, C_TEXT, 15
            )

        tbw = 110
        self._time_btns = {}
        for i, (label, secs) in enumerate(self.TIMES):
            x = WINDOW_W // 2 - 345 + i * (tbw + 8)
            color = C_ACCENT if secs == self._selected_time else C_PANEL2
            self._time_btns[secs] = Button(
                pygame.Rect(x, 440, tbw, 44), label, color, C_TEXT, 14
            )

        self._col_btns = {
            "white": Button(pygame.Rect(WINDOW_W // 2 - 165, 550, 150, 50),
                            "White", (240, 235, 220), (30, 20, 10), 16),
            "black": Button(pygame.Rect(WINDOW_W // 2 + 15, 550, 150, 50),
                            "Black", (30, 25, 20), C_TEXT, 16),
        }

    def _refresh_colors(self):
        for lvl, btn in self._lvl_btns.items():
            btn.color = C_ACCENT if lvl == self._selected_level else C_PANEL2
        for secs, btn in self._time_btns.items():
            btn.color = C_ACCENT if secs == self._selected_time else C_PANEL2
        for col, btn in self._col_btns.items():
            btn.color = C_GOLD if col == self._color_choice else C_PANEL2

    def handle_events(self, events):
        mouse = pygame.mouse.get_pos()
        self._back.update(mouse)
        self._play.update(mouse)
        for btn in self._lvl_btns.values():
            btn.update(mouse)
        for btn in self._time_btns.values():
            btn.update(mouse)
        for btn in self._col_btns.values():
            btn.update(mouse)

        for event in events:
            if self._back.handle_event(event):
                self.next = ("menu", None)
            if self._play.handle_event(event):
                self.next = ("bot_game", {
                    "level": self._selected_level,
                    "time": self._selected_time,
                    "color": self._color_choice,
                })
            for lvl, btn in self._lvl_btns.items():
                if btn.handle_event(event):
                    self._selected_level = lvl
                    self._refresh_colors()
            for secs, btn in self._time_btns.items():
                if btn.handle_event(event):
                    self._selected_time = secs
                    self._refresh_colors()
            for col, btn in self._col_btns.items():
                if btn.handle_event(event):
                    self._color_choice = col
                    self._refresh_colors()

    def draw(self):
        draw_gradient_bg(self.screen)
        self._particles.update_draw(self.screen)

        draw_text(self.screen, "Configure Bot Game",
                  (WINDOW_W // 2, 45), 36, C_TEXT, bold=True, center=True)

        draw_rounded_rect(self.screen, C_PANEL,
                          pygame.Rect(WINDOW_W // 2 - 215, 160, 430, 210), 14)
        draw_text(self.screen, "Bot Difficulty",
                  (WINDOW_W // 2, 175), 18, C_ACCENT, bold=True, center=True)
        cfg = BOT_LEVELS[self._selected_level]
        draw_text(self.screen, cfg["description"],
                  (WINDOW_W // 2, 195), 13, C_TEXT_DIM, center=True)
        depth = cfg["depth"]
        draw_text(self.screen, f"Search Depth: {depth}  |  ELO ≈ {ChessBot(self._selected_level).elo_rating}",
                  (WINDOW_W // 2, 210), 13, C_TEXT_DIM, center=True)
        for btn in self._lvl_btns.values():
            btn.draw(self.screen)

        draw_rounded_rect(self.screen, C_PANEL,
                          pygame.Rect(WINDOW_W // 2 - 355, 400, 710, 80), 14)
        draw_text(self.screen, "Time Control",
                  (WINDOW_W // 2, 413), 16, C_ACCENT, bold=True, center=True)
        for btn in self._time_btns.values():
            btn.draw(self.screen)

        draw_rounded_rect(self.screen, C_PANEL,
                          pygame.Rect(WINDOW_W // 2 - 175, 520, 350, 100), 14)
        draw_text(self.screen, "Your Color",
                  (WINDOW_W // 2, 533), 16, C_ACCENT, bold=True, center=True)
        for btn in self._col_btns.values():
            btn.draw(self.screen)

        self._play.draw(self.screen)
        self._back.draw(self.screen)

class GameScreen:
    PANEL_LEFT_X  = BOARD_OFFSET_X + BOARD_SIZE + 20
    PANEL_W       = WINDOW_W - (BOARD_OFFSET_X + BOARD_SIZE + 20) - 10

    def __init__(self, screen, scorecard: ScoreCard,
                 mode: str = "bot", config: dict = None,
                 net_client=None):
        self.screen    = screen
        self.scorecard = scorecard
        self.mode      = mode
        self.config    = config or {}
        self.net       = net_client
        self.next      = None

        self.board     = chess.Board()
        self.renderer  = BoardRenderer(screen)

        self.bot: ChessBot | None = None
        self.bot_color: chess.Color | None = None
        self._bot_thinking = False
        self._bot_thread   = None

        if mode == "bot":
            level = self.config.get("level", "Medium")
            col   = self.config.get("color", "white")
            self.bot = ChessBot(level)
            self.bot_color = chess.BLACK if col == "white" else chess.WHITE
            self.renderer.flipped = (col == "black")

        elif mode == "online":
            my_color = self.config.get("my_color", "white")
            self.renderer.flipped = (my_color == "black")
            self._setup_net()

        total = self.config.get("time", 0)
        self._clock_on = total > 0
        self._clock = _Clock(total if total > 0 else 99999)

        self.selected_sq: int | None = None
        self.legal_dests: list[int] = []
        self.last_move:   chess.Move | None = None
        self.move_san_list: list[str] = []
        self.move_scroll   = 0

        self.game_over     = False
        self.game_result   = ""
        self.game_reason   = ""
        self._result_recorded = False

        self._promo_dialog: PromotionDialog | None = None
        self._promo_move_partial: chess.Move | None = None

        self.chat_messages: list[dict] = []
        self._chat_input = InputBox(
            pygame.Rect(self.PANEL_LEFT_X, WINDOW_H - 48, self.PANEL_W - 2, 36),
            placeholder="Type message…", max_len=80, font_size=14
        )
        self._show_chat = mode == "online"

        self._toasts: list[Toast] = []

        bx = self.PANEL_LEFT_X
        bw = self.PANEL_W // 2 - 4
        self._btn_resign = Button(pygame.Rect(bx, WINDOW_H - 100, bw, 38),
                                  "Resign", C_RED, C_TEXT, 15)
        self._btn_draw   = Button(pygame.Rect(bx + bw + 8, WINDOW_H - 100, bw, 38),
                                  "Draw", C_TEXT_DIM, C_BG, 15)
        self._btn_menu   = Button(pygame.Rect(30, 18, 110, 36),
                                  "← Menu", C_PANEL2, C_TEXT, 14)

        if not self._is_bot_turn():
            self._clock.start()
        elif mode == "bot":
            self._clock.start()
            self._trigger_bot_move()

    def _setup_net(self):
        if self.net is None:
            return
        self.net.on("opponent_move",      self._on_opponent_move)
        self.net.on("chat",               self._on_chat)
        self.net.on("opponent_resigned",  self._on_opponent_resigned)
        self.net.on("draw_offer",         self._on_draw_offer)
        self.net.on("draw_result",        self._on_draw_result)
        self.net.on("opponent_disconnected", self._on_disconnect)

    def _on_opponent_move(self, data):
        uci = data.get("move")
        if uci:
            move = chess.Move.from_uci(uci)
            if move in self.board.legal_moves:
                san = self.board.san(move)
                self.renderer.animate_move(self.board, move)
                self.board.push(move)
                self.last_move = move
                self.move_san_list.append(san)
                self._clock.switch(self.board.turn)
                self._check_game_over()
                self.selected_sq = None

    def _on_chat(self, data):
        self.chat_messages.append({
            "name": data.get("name", "?"),
            "text": data.get("text", ""),
            "self": False
        })

    def _on_opponent_resigned(self, _):
        self._push_toast("Opponent resigned! You win!", C_GREEN)
        self.game_over   = True
        my_color = self.config.get("my_color", "white")
        self.game_result = f"{'white' if my_color == 'white' else 'black'}_wins"
        self.game_reason = "Opponent resigned"
        self._record_result()

    def _on_draw_offer(self, _):
        self._push_toast("Opponent offers a draw — click Draw to accept", C_GOLD)

    def _on_draw_result(self, data):
        if data.get("accepted"):
            self._push_toast("Draw agreed!", C_GOLD)
            self.game_over   = True
            self.game_result = "draw"
            self.game_reason = "Draw by agreement"
            self._record_result()

    def _on_disconnect(self, _):
        self._push_toast("Opponent disconnected!", C_RED)
        self.game_over   = True
        self.game_result = "draw"
        self.game_reason = "Opponent disconnected"

    def _is_bot_turn(self) -> bool:
        return (self.mode == "bot" and
                self.bot is not None and
                self.board.turn == self.bot_color and
                not self.game_over)

    def _trigger_bot_move(self):
        if self._bot_thinking:
            return
        self._bot_thinking = True

        def worker():
            try:
                board_copy = self.board.copy()
                move = self.bot.get_move(board_copy)
                self._apply_bot_move(move)
            except Exception:
                pass
            finally:
                self._bot_thinking = False

        self._bot_thread = threading.Thread(target=worker, daemon=True)
        self._bot_thread.start()

    def _apply_bot_move(self, move: chess.Move | None):
        if move is None or move not in self.board.legal_moves:
            return
        san = self.board.san(move)
        self.renderer.animate_move(self.board, move)
        self.board.push(move)
        self.last_move  = move
        self.move_san_list.append(san)
        self._clock.switch(self.board.turn)
        self._check_game_over()

    def _try_move(self, from_sq: int, to_sq: int):
        piece = self.board.piece_at(from_sq)
        if piece is None:
            return

        if (piece.piece_type == chess.PAWN and
                ((piece.color == chess.WHITE and chess.square_rank(to_sq) == 7) or
                 (piece.color == chess.BLACK and chess.square_rank(to_sq) == 0))):
            partial = chess.Move(from_sq, to_sq, chess.QUEEN)
            if partial in self.board.legal_moves:
                is_white = piece.color == chess.WHITE
                self._promo_dialog = PromotionDialog(WINDOW_W, WINDOW_H, is_white)
                self._promo_move_partial = chess.Move(from_sq, to_sq)
                self.selected_sq = None
                self.legal_dests = []
                return

        move = chess.Move(from_sq, to_sq)
        if move not in self.board.legal_moves:
            return

        self._execute_move(move)

    def _execute_move(self, move: chess.Move):
        san = self.board.san(move)
        self.renderer.animate_move(self.board, move)
        self.board.push(move)
        self.last_move  = move
        self.move_san_list.append(san)
        self._clock.switch(self.board.turn)
        self.selected_sq = None
        self.legal_dests = []
        self._check_game_over()

        if self.mode == "online" and self.net:
            self.net.send_move(move.uci(), self.board.fen())

        if self._is_bot_turn():
            self._trigger_bot_move()

    def _check_game_over(self):
        if self.board.is_game_over():
            outcome = self.board.outcome()
            if outcome.winner is chess.WHITE:
                self.game_result = "white_wins"
                self.game_reason = outcome.result()
            elif outcome.winner is chess.BLACK:
                self.game_result = "black_wins"
                self.game_reason = outcome.result()
            else:
                self.game_result = "draw"
                self.game_reason = str(outcome.termination.name).replace("_", " ").title()
            self.game_over = True
            self._clock.stop()
            self._record_result()

    def _clock_flagged(self):
        flagged = self._clock.flagged()
        if flagged is not None:
            self.game_over = True
            self._clock.stop()
            if flagged == chess.WHITE:
                self.game_result = "black_wins"
            else:
                self.game_result = "white_wins"
            self.game_reason = "Time"
            self._record_result()

    def _record_result(self):
        if self._result_recorded:
            return
        self._result_recorded = True
        moves = len(self.board.move_stack)

        if self.mode == "bot":
            is_white_player = self.bot_color == chess.BLACK
            if self.game_result == "draw":
                result = "draw"
            elif (self.game_result == "white_wins" and is_white_player) or \
                 (self.game_result == "black_wins" and not is_white_player):
                result = "win"
            else:
                result = "loss"
            self.scorecard.record_game("vs_bot", result, moves,
                                       f"Bot ({self.bot.level})",
                                       self.bot.level)
        elif self.mode == "online":
            my_col = self.config.get("my_color", "white")
            if self.game_result == "draw":
                result = "draw"
            elif (self.game_result == "white_wins" and my_col == "white") or \
                 (self.game_result == "black_wins" and my_col == "black"):
                result = "win"
            else:
                result = "loss"
            self.scorecard.record_game(
                "vs_human", result, moves,
                self.config.get("opponent_name", "Online Opponent")
            )
        elif self.mode == "local2p":
            pass

    def handle_events(self, events):
        mouse = pygame.mouse.get_pos()
        self._btn_resign.update(mouse)
        self._btn_draw.update(mouse)
        self._btn_menu.update(mouse)

        for event in events:
            if self._btn_menu.handle_event(event):
                self.next = ("menu", None)
                return

            if self._promo_dialog:
                sym = self._promo_dialog.handle_event(event)
                if sym:
                    promo_piece = {"Q": chess.QUEEN, "R": chess.ROOK,
                                   "B": chess.BISHOP, "N": chess.KNIGHT}[sym]
                    move = chess.Move(self._promo_move_partial.from_square,
                                      self._promo_move_partial.to_square, promo_piece)
                    self._promo_dialog = None
                    self._promo_move_partial = None
                    if move in self.board.legal_moves:
                        self._execute_move(move)
                continue

            if self.game_over:
                if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                    self.next = ("menu", None)
                continue

            if self._btn_resign.handle_event(event):
                self.game_over = True
                self._clock.stop()
                if self.board.turn == chess.WHITE:
                    self.game_result = "black_wins"
                else:
                    self.game_result = "white_wins"
                self.game_reason = "Resignation"
                if self.mode == "online" and self.net:
                    self.net.resign()
                self._record_result()
                continue

            if self._btn_draw.handle_event(event):
                if self.mode == "online" and self.net:
                    self.net.offer_draw()
                    self._push_toast("Draw offer sent", C_GOLD)
                elif self.mode == "local2p":
                    self.game_over  = True
                    self._clock.stop()
                    self.game_result = "draw"
                    self.game_reason = "Draw by agreement"
                continue

            if self._show_chat:
                submitted = self._chat_input.handle_event(event)
                if submitted and self._chat_input.text.strip():
                    text = self._chat_input.text.strip()
                    self._chat_input.text = ""
                    self.chat_messages.append({
                        "name": self.scorecard.player_name,
                        "text": text, "self": True
                    })
                    if self.mode == "online" and self.net:
                        self.net.send_chat(text)
                    continue

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._on_board_click(event.pos)

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.selected_sq = None
                    self.legal_dests = []

    def _on_board_click(self, pos):
        if self.game_over:
            return
        if self.mode == "bot" and self.board.turn == self.bot_color:
            return
        if self.mode == "online":
            my_col = self.config.get("my_color", "white")
            my_chess_col = chess.WHITE if my_col == "white" else chess.BLACK
            if self.board.turn != my_chess_col:
                return

        sq = self.renderer.px_to_sq(*pos)
        if sq is None:
            self.selected_sq = None
            self.legal_dests = []
            return

        piece = self.board.piece_at(sq)

        if self.selected_sq is None:
            if piece and piece.color == self.board.turn:
                self.selected_sq = sq
                self.legal_dests = [
                    m.to_square for m in self.board.legal_moves
                    if m.from_square == sq
                ]
        else:
            if sq in self.legal_dests:
                self._try_move(self.selected_sq, sq)
            elif piece and piece.color == self.board.turn:
                self.selected_sq = sq
                self.legal_dests = [
                    m.to_square for m in self.board.legal_moves
                    if m.from_square == sq
                ]
            else:
                self.selected_sq = None
                self.legal_dests = []

    def draw(self):
        self._clock.update()
        self._clock_flagged()

        if (self._is_bot_turn() and not self._bot_thinking
                and not self.game_over):
            self._trigger_bot_move()

        draw_gradient_bg(self.screen)

        check_sq = None
        if self.board.is_check():
            check_sq = self.board.king(self.board.turn)

        self.renderer.draw(
            self.board,
            self.selected_sq,
            self.legal_dests,
            self.last_move,
            check_sq
        )

        self._draw_sidebar()
        self._draw_clocks()

        if self._promo_dialog:
            ov = pygame.Surface((WINDOW_W, WINDOW_H), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 140))
            self.screen.blit(ov, (0, 0))
            self._promo_dialog.draw(self.screen)

        if self.game_over:
            self._draw_game_over()

        self._btn_menu.draw(self.screen)

        self._toasts = [t for t in self._toasts if t.alive()]
        for toast in self._toasts:
            toast.draw(self.screen)

    def _draw_clocks(self):
        bx = BOARD_OFFSET_X
        for color, label_y, clock_y in [
            (chess.BLACK, BOARD_OFFSET_Y - 28, BOARD_OFFSET_Y - 10),
            (chess.WHITE, BOARD_OFFSET_Y + BOARD_SIZE + 4, BOARD_OFFSET_Y + BOARD_SIZE + 4),
        ]:
            cstr = self._clock.str(color)
            is_active = self.board.turn == color and self._clock._running

            if self.mode == "bot":
                name = f"Bot ({self.bot.label})" if color == self.bot_color \
                    else self.scorecard.player_name
            elif self.mode == "online":
                my_col = chess.WHITE if self.config.get("my_color") == "white" else chess.BLACK
                name = self.scorecard.player_name if color == my_col else \
                       self.config.get("opponent_name", "Opponent")
            else:
                name = "White" if color == chess.WHITE else "Black"

            if is_active:
                pygame.draw.circle(self.screen, C_GREEN, (bx - 2, clock_y + 8), 4)
            col = C_TEXT if is_active else C_TEXT_DIM
            draw_text(self.screen, name, (bx + 8, clock_y), 15, col, bold=is_active)

            if self._clock_on:
                cw = 90
                cr = pygame.Rect(bx + BOARD_SIZE - cw - 10, clock_y - 2, cw, 24)
                low_time = is_active and self._clock.times[color] < 30
                bg = C_RED if low_time else (C_PANEL if is_active else C_PANEL2)
                draw_rounded_rect(self.screen, bg, cr, 8)
                draw_text(self.screen, cstr, (cr.centerx, cr.centery),
                          15, C_TEXT, bold=True, center=True)

    def _draw_sidebar(self):
        px = self.PANEL_LEFT_X
        pw = self.PANEL_W

        log_h = 300 if self._show_chat else 480
        draw_move_log(self.screen,
                      pygame.Rect(px, BOARD_OFFSET_Y, pw, log_h),
                      self.move_san_list, self.move_scroll)

        if self.mode == "bot":
            y = BOARD_OFFSET_Y + log_h + 10
            info_rect = pygame.Rect(px, y, pw, 80)
            draw_rounded_rect(self.screen, C_PANEL, info_rect, 12)
            pygame.draw.rect(self.screen, C_ACCENT,
                             pygame.Rect(px, y, 4, 80),
                             border_radius=2)
            draw_text(self.screen, "OPPONENT", (px + 14, y + 8), 11, C_ACCENT, bold=True)
            draw_text(self.screen, f"Bot  ·  {self.bot.label}",
                      (px + 14, y + 26), 18, C_TEXT, bold=True)
            draw_text(self.screen, f"ELO ≈ {self.bot.elo_rating}  •  Depth {self.bot.depth}",
                      (px + 14, y + 52), 13, C_TEXT_DIM)
            if self._bot_thinking:
                t = time.time()
                dots = "•" * (int(t * 3) % 4 + 1)
                draw_text(self.screen, f"Thinking {dots}",
                          (px + pw - 10, y + 52), 13, C_GOLD)

        if self._show_chat:
            chat_rect = pygame.Rect(px, BOARD_OFFSET_Y + log_h + 10, pw, 200)
            draw_chat(self.screen, chat_rect, self.chat_messages)
            self._chat_input.draw(self.screen)

        self._btn_resign.draw(self.screen)
        self._btn_draw.draw(self.screen)

    def _draw_game_over(self):
        ov = pygame.Surface((WINDOW_W, WINDOW_H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 170))
        self.screen.blit(ov, (0, 0))

        box_w, box_h = 480, 320
        bx = WINDOW_W // 2 - box_w // 2
        by = WINDOW_H // 2 - box_h // 2

        for i in range(6, 0, -1):
            glow = pygame.Surface((box_w + i * 6, box_h + i * 6), pygame.SRCALPHA)
            pygame.draw.rect(glow, (88, 166, 255, 6 * i), glow.get_rect(),
                             border_radius=24)
            self.screen.blit(glow, (bx - i * 3, by - i * 3))

        draw_rounded_rect(self.screen, C_PANEL2,
                          pygame.Rect(bx, by, box_w, box_h), 20)
        pygame.draw.rect(self.screen, C_PANEL,
                         pygame.Rect(bx, by, box_w, box_h), 2,
                         border_radius=20)

        cx = WINDOW_W // 2

        if self.game_result == "draw":
            title = "DRAW"
            icon = "½"
            col = C_GOLD
        elif self.game_result == "white_wins":
            title = "WHITE WINS"
            icon = "♔"
            col = (240, 235, 220)
        else:
            title = "BLACK WINS"
            icon = "♚"
            col = C_ACCENT2

        icon_font = _font(52, True)
        icon_surf = icon_font.render(icon, True, col)
        self.screen.blit(icon_surf,
                         icon_surf.get_rect(center=(cx, by + 55)))

        draw_text(self.screen, title, (cx, by + 100),
                  32, col, bold=True, center=True)

        draw_text(self.screen, self.game_reason,
                  (cx, by + 140), 16, C_TEXT_DIM, center=True)

        moves = len(self.board.move_stack)
        draw_text(self.screen, f"Moves: {moves}",
                  (cx, by + 175), 15, C_TEXT_DIM, center=True)

        if self.mode != "local2p":
            draw_text(self.screen, f"Your ELO: {self.scorecard.elo}",
                      (cx, by + 210), 20, C_ACCENT, bold=True, center=True)

        pygame.draw.line(self.screen, C_TEXT_DIM,
                         (bx + 40, by + 250), (bx + box_w - 40, by + 250), 1)

        draw_text(self.screen, "Click anywhere to continue",
                  (cx, by + 280), 14, C_TEXT_DIM, center=True)

    def _push_toast(self, msg: str, color=C_GREEN):
        self._toasts.append(Toast(msg, color=color))

class MultiplayerScreen:
    def __init__(self, screen, scorecard: ScoreCard):
        self.screen    = screen
        self.scorecard = scorecard
        self.next      = None
        self._phase    = "lobby"
        self._particles = ParticleField(WINDOW_W, WINDOW_H, 30)
        self._toasts: list[Toast] = []

        self._server = None
        self._client = None

        self._room_code = ""
        self._my_color  = "white"
        self._opp_name  = "Opponent"
        self._local_ip  = self._get_local_ip()

        cx = WINDOW_W // 2
        self._back = Button(pygame.Rect(30, 20, 110, 38),
                            "← Back", C_PANEL2, C_TEXT, 14)

        self._name_input = InputBox(
            pygame.Rect(cx - 160, 220, 320, 42),
            "Your Name", 20, 17)
        self._name_input.text = scorecard.player_name

        self._create_btn = Button(
            pygame.Rect(cx - 185, 300, 175, 54),
            "Create Room", C_ACCENT, C_BG, 18)
        self._join_btn = Button(
            pygame.Rect(cx + 10, 300, 175, 54),
            "Join Room", C_ACCENT2, C_BG, 18)

        self._code_input = InputBox(
            pygame.Rect(cx - 120, 400, 180, 44),
            "Room Code", 10, 20)
        self._go_btn = Button(
            pygame.Rect(cx + 70, 400, 90, 44),
            "Join!", C_GREEN, C_BG, 16)
        self._go_btn.enabled = False

        self._status_msg = ""
        self._status_col = C_TEXT_DIM

    @staticmethod
    def _get_local_ip() -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def _start_hosting(self):
        from network import ChessServer, ChessClient
        name = self._name_input.text.strip() or "Player"
        self.scorecard.set_name(name)

        self._server = ChessServer()
        try:
            self._server.start()
        except Exception as e:
            self._push_toast(f"Server error: {e}", C_RED)
            return

        time.sleep(0.3)

        self._client = ChessClient("localhost")
        self._client.player_name = name
        self._client.on("room_created",  self._on_room_created)
        self._client.on("game_start",    self._on_game_start)
        self._client.on("error",         self._on_error)
        self._client.on("disconnected",  self._on_disconnect)

        if self._client.connect():
            self._client.create_room()
            self._phase = "waiting"
            self._status_msg = "Creating room…"
            self._status_col = C_GOLD
        else:
            self._push_toast("Could not start. Try again.", C_RED)

    def _start_joining(self):
        from network import ChessClient
        code = self._code_input.text.strip().upper()
        if len(code) < 4:
            self._push_toast("Enter a valid room code", C_RED)
            return

        name = self._name_input.text.strip() or "Player"
        self.scorecard.set_name(name)

        self._client = ChessClient("localhost")
        self._client.player_name = name
        self._client.on("game_start",    self._on_game_start)
        self._client.on("error",         self._on_error)
        self._client.on("disconnected",  self._on_disconnect)

        if self._client.connect():
            self._client.join_room(code)
            self._phase = "connecting"
            self._status_msg = "Joining room…"
            self._status_col = C_ACCENT
        else:
            self._push_toast("Could not connect to server", C_RED)
            self._status_msg = "Connection failed"
            self._status_col = C_RED

    def _on_room_created(self, data):
        self._room_code = data.get("code", "")
        self._client.room_code = self._room_code
        self._my_color = data.get("color", "white")
        self._status_msg = "Waiting for opponent to join…"
        self._status_col = C_GOLD
        self._push_toast(f"Room created: {self._room_code}", C_GREEN)

    def _on_game_start(self, data):
        self._my_color = data.get("your_color", "white")
        self._opp_name = data.get("opponent", "Opponent")
        self._phase = "game"

    def _on_error(self, data):
        msg = data.get("msg", "Error")
        self._push_toast(msg, C_RED)
        self._status_msg = msg
        self._status_col = C_RED
        self._phase = "lobby"

    def _on_disconnect(self, _):
        self._push_toast("Disconnected", C_RED)
        self._phase = "lobby"
        self._status_msg = "Disconnected."
        self._status_col = C_RED

    def handle_events(self, events):
        if self._phase == "game":
            return

        mouse = pygame.mouse.get_pos()
        self._back.update(mouse)
        self._create_btn.update(mouse)
        self._join_btn.update(mouse)
        self._go_btn.update(mouse)

        can_act = self._phase == "lobby"
        self._create_btn.enabled = can_act
        self._join_btn.enabled   = can_act
        self._go_btn.enabled     = can_act and len(self._code_input.text.strip()) >= 4

        for event in events:
            self._name_input.handle_event(event)
            code_submitted = self._code_input.handle_event(event)

            if self._back.handle_event(event):
                if self._client:
                    self._client.disconnect()
                if self._server:
                    self._server.stop()
                self.next = ("menu", None)

            if can_act:
                if self._create_btn.handle_event(event):
                    self._start_hosting()

                if self._join_btn.handle_event(event) or \
                   self._go_btn.handle_event(event) or \
                   (code_submitted and len(self._code_input.text.strip()) >= 4):
                    self._start_joining()

    def draw(self):
        if self._phase == "game":
            self.next = ("online_game", {
                "client": self._client,
                "my_color": self._my_color,
                "opponent_name": self._opp_name,
            })
            return

        draw_gradient_bg(self.screen)
        self._particles.update_draw(self.screen)

        cx = WINDOW_W // 2

        draw_text(self.screen, "Multiplayer",
                  (cx, 50), 40, C_TEXT, bold=True, center=True)
        draw_text(self.screen, "Play with a friend on the same network",
                  (cx, 95), 15, C_TEXT_DIM, center=True)

        panel = pygame.Rect(cx - 230, 155, 460, 430)
        draw_rounded_rect(self.screen, C_PANEL, panel, 18)

        draw_text(self.screen, "Your Name:", (cx - 160, 198), 13, C_TEXT_DIM)
        self._name_input.draw(self.screen)

        self._create_btn.draw(self.screen)
        self._join_btn.draw(self.screen)

        div_y = 375
        pygame.draw.line(self.screen, C_PANEL2,
                         (cx - 190, div_y), (cx + 190, div_y), 1)
        draw_text(self.screen, "— or join with a room code —",
                  (cx, div_y - 2), 12, C_TEXT_DIM, center=True)

        self._code_input.draw(self.screen)
        self._go_btn.draw(self.screen)

        if self._room_code:
            card = pygame.Rect(cx - 150, 460, 300, 80)
            draw_rounded_rect(self.screen, C_ACCENT, card, 14)
            draw_text(self.screen, "ROOM CODE",
                      (cx, 472), 11, C_BG, center=True)
            draw_text(self.screen, self._room_code,
                      (cx, 496), 28, C_BG, bold=True, center=True)
            draw_text(self.screen, f"Share this code  •  Your IP: {self._local_ip}",
                      (cx, 526), 11, (200, 230, 255), center=True)

        if self._phase == "waiting" and self._room_code:
            t = time.time()
            dots = "•" * (int(t * 2) % 4 + 1)
            draw_text(self.screen, f"Waiting for opponent {dots}",
                      (cx, 555), 15, C_GOLD, center=True)
        elif self._phase == "connecting":
            draw_text(self.screen, "Connecting…",
                      (cx, 555), 15, C_ACCENT, center=True)
        elif self._status_msg:
            draw_text(self.screen, self._status_msg,
                      (cx, 555), 14, self._status_col, center=True)

        self._back.draw(self.screen)

        self._toasts = [t for t in self._toasts if t.alive()]
        for toast in self._toasts:
            toast.draw(self.screen)

    def _push_toast(self, msg: str, color=C_GREEN):
        self._toasts.append(Toast(msg, color=color))

class ScoreScreen:
    def __init__(self, screen, scorecard: ScoreCard):
        self.screen    = screen
        self.scorecard = scorecard
        self.next      = None
        self._particles = ParticleField(WINDOW_W, WINDOW_H, 20)
        self._scroll   = 0
        self._back = Button(pygame.Rect(30, 20, 110, 38), "← Back", C_PANEL2, C_TEXT, 14)
        self._reset = Button(pygame.Rect(WINDOW_W - 150, 20, 120, 38),
                             "Reset", C_RED, C_TEXT, 14)
        self._confirm_reset = False

    def handle_events(self, events):
        mouse = pygame.mouse.get_pos()
        self._back.update(mouse)
        self._reset.update(mouse)
        for event in events:
            if self._back.handle_event(event):
                self.next = ("menu", None)
            if self._reset.handle_event(event):
                if self._confirm_reset:
                    self.scorecard.reset()
                    self._confirm_reset = False
                else:
                    self._confirm_reset = True
            if event.type == pygame.MOUSEWHEEL:
                self._scroll = max(0, self._scroll - event.y)
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self._confirm_reset = False

    def draw(self):
        draw_gradient_bg(self.screen)
        self._particles.update_draw(self.screen)

        cx = WINDOW_W // 2
        draw_text(self.screen, "Score Card",
                  (cx, 60), 38, C_TEXT, bold=True, center=True)

        sc = self.scorecard

        elo_rect = pygame.Rect(cx - 80, 90, 160, 50)
        draw_rounded_rect(self.screen, C_ACCENT, elo_rect, 14)
        draw_text(self.screen, f"ELO  {sc.elo}", (cx, 115),
                  22, C_BG, bold=True, center=True)

        stats_rect = pygame.Rect(40, 160, WINDOW_W - 80, 200)
        draw_rounded_rect(self.screen, C_PANEL, stats_rect, 16)

        self._draw_stat_col(self.screen, sc.vs_bot,
                            "vs Bot", 80, 190, sc.win_rate("vs_bot"))
        self._draw_stat_col(self.screen, sc.vs_human,
                            "vs Human", 370, 190, sc.win_rate("vs_human"))
        gen_x = 660
        gen_y = 190
        items = [
            ("Total Games",  str(sc.data["total_games"])),
            ("Total Moves",  str(sc.data["total_moves"])),
            ("Fastest Win",  str(sc.data["fastest_win_moves"] or "-") + " moves"),
            ("Longest Game", str(sc.data["longest_game_moves"]) + " moves"),
        ]
        draw_text(self.screen, "General", (gen_x, gen_y), 16, C_ACCENT, bold=True)
        for i, (label, val) in enumerate(items):
            draw_text(self.screen, label, (gen_x, gen_y + 24 + i * 28), 13, C_TEXT_DIM)
            draw_text(self.screen, val,   (gen_x + 130, gen_y + 24 + i * 28), 14,
                      C_TEXT, bold=True)

        draw_text(self.screen, "Game History",
                  (40, 378), 18, C_ACCENT, bold=True)
        history = sc.history
        hist_rect = pygame.Rect(40, 400, WINDOW_W - 80, WINDOW_H - 420)
        draw_rounded_rect(self.screen, C_PANEL, hist_rect, 12)

        cols = [(40, "Date"), (220, "Opponent"), (440, "Result"),
                (560, "Moves"), (660, "ELO Δ")]
        hy0 = 408
        for hx, hname in cols:
            draw_text(self.screen, hname, (hx + 8, hy0), 13, C_ACCENT, bold=True)
        pygame.draw.line(self.screen, C_PANEL2,
                         (48, hy0 + 18), (hist_rect.right - 8, hy0 + 18), 1)

        clip = self.screen.get_clip()
        self.screen.set_clip(hist_rect.inflate(-4, -8))
        max_show = min(len(history), 20)
        start = min(self._scroll, max(0, len(history) - max_show))
        for i, entry in enumerate(history[start:start + max_show]):
            ey = hy0 + 24 + i * 26
            bg = C_PANEL if i % 2 == 0 else C_PANEL2
            draw_rounded_rect(self.screen, bg,
                              pygame.Rect(44, ey - 2, hist_rect.width - 12, 24), 4)
            res = entry.get("result", "?")
            res_col = C_GREEN if res == "win" else (C_RED if res == "loss" else C_GOLD)
            delta = entry.get("elo_change", 0)
            delta_col = C_GREEN if delta >= 0 else C_RED

            draw_text(self.screen, entry.get("date", "?"),      (48,  ey), 12, C_TEXT_DIM)
            draw_text(self.screen, entry.get("opponent", "?"),  (228, ey), 13, C_TEXT)
            draw_text(self.screen, res.capitalize(),             (448, ey), 13, res_col, bold=True)
            draw_text(self.screen, str(entry.get("moves","?")), (568, ey), 13, C_TEXT)
            draw_text(self.screen, f"{'+' if delta>=0 else ''}{delta}",
                      (668, ey), 13, delta_col, bold=True)

        self.screen.set_clip(clip)

        self._back.draw(self.screen)
        self._reset.color = C_RED if not self._confirm_reset else (255, 40, 40)
        self._reset.label = "Reset" if not self._confirm_reset else "Confirm?"
        self._reset.draw(self.screen)

    @staticmethod
    def _draw_stat_col(surf, stats: dict, title: str, x: int, y: int, win_rate: float):
        draw_text(surf, title, (x, y), 16, C_ACCENT, bold=True)
        total = stats["wins"] + stats["losses"] + stats["draws"]
        draw_text(surf, f"Played: {total}", (x, y + 24), 14, C_TEXT)
        draw_text(surf, f"Wins: {stats['wins']}",   (x, y + 48), 14, C_GREEN)
        draw_text(surf, f"Losses: {stats['losses']}", (x, y + 72), 14, C_RED)
        draw_text(surf, f"Draws: {stats['draws']}",   (x, y + 96), 14, C_GOLD)
        draw_text(surf, f"Win Rate: {win_rate:.1f}%", (x, y + 124), 13, C_TEXT_DIM)
        bar_r = pygame.Rect(x, y + 148, 260, 12)
        draw_rounded_rect(surf, C_PANEL2, bar_r, 6)
        if total > 0:
            ww = int(260 * stats["wins"] / total)
            lw = int(260 * stats["losses"] / total)
            if ww > 0:
                draw_rounded_rect(surf, C_GREEN, pygame.Rect(x, y + 148, ww, 12), 6)
            if lw > 0:
                draw_rounded_rect(surf, C_RED,
                                  pygame.Rect(x + 260 - lw, y + 148, lw, 12), 6)

