from __future__ import annotations
import pygame
import chess
import time
from constants import *
from assets import get_piece_surface
from ui import draw_rounded_rect, draw_text

class BoardRenderer:
    def __init__(self, surf: pygame.Surface,
                 ox: int = BOARD_OFFSET_X, oy: int = BOARD_OFFSET_Y,
                 sq: int = SQUARE_SIZE):
        self.surf    = surf
        self.ox      = ox
        self.oy      = oy
        self.sq      = sq
        self.flipped = False

        self._anim_piece: str | None = None
        self._anim_from: tuple | None = None
        self._anim_to:   tuple | None = None
        self._anim_to_sq: int | None = None
        self._anim_t: float = 0.0
        self._anim_dur: float = 0.20

    def sq_to_px(self, sq: int) -> tuple:
        r = chess.square_rank(sq)
        f = chess.square_file(sq)
        if self.flipped:
            col = 7 - f
            row = r
        else:
            col = f
            row = 7 - r
        return (self.ox + col * self.sq + self.sq // 2,
                self.oy + row * self.sq + self.sq // 2)

    def px_to_sq(self, px: int, py: int):
        col = (px - self.ox) // self.sq
        row = (py - self.oy) // self.sq
        if not (0 <= col <= 7 and 0 <= row <= 7):
            return None
        if self.flipped:
            return chess.square(7 - col, row)
        else:
            return chess.square(col, 7 - row)

    def sq_topleft(self, sq: int) -> tuple:
        cx, cy = self.sq_to_px(sq)
        return (cx - self.sq // 2, cy - self.sq // 2)

    def animate_move(self, board_before: chess.Board, move: chess.Move):
        piece = board_before.piece_at(move.from_square)
        if piece:
            self._anim_piece  = piece.symbol()
            self._anim_from   = self.sq_to_px(move.from_square)
            self._anim_to     = self.sq_to_px(move.to_square)
            self._anim_to_sq  = move.to_square
            self._anim_t      = time.time()

    def _anim_done(self) -> bool:
        return self._anim_piece is None or \
               (time.time() - self._anim_t) >= self._anim_dur

    def draw(self, board: chess.Board,
             selected_sq: int | None = None,
             legal_dests: list[int] | None = None,
             last_move: chess.Move | None = None,
             check_sq: int | None = None):

        self._draw_squares(board, selected_sq, legal_dests, last_move, check_sq)
        self._draw_pieces(board, selected_sq)
        self._draw_coords()
        self._draw_border()
        self._draw_animation()

    def _draw_squares(self, board, selected_sq, legal_dests, last_move, check_sq):
        for sq in chess.SQUARES:
            tl  = self.sq_topleft(sq)
            r   = chess.square_rank(sq)
            f   = chess.square_file(sq)
            col = C_WHITE_SQ if (r + f) % 2 == 0 else C_BLACK_SQ
            pygame.draw.rect(self.surf, col, pygame.Rect(*tl, self.sq, self.sq))

        if last_move:
            for tsq in (last_move.from_square, last_move.to_square):
                tl = self.sq_topleft(tsq)
                s  = pygame.Surface((self.sq, self.sq), pygame.SRCALPHA)
                s.fill(C_LAST_MOVE)
                self.surf.blit(s, tl)

        if check_sq is not None:
            tl = self.sq_topleft(check_sq)
            s  = pygame.Surface((self.sq, self.sq), pygame.SRCALPHA)
            s.fill(C_CHECK)
            self.surf.blit(s, tl)

        if selected_sq is not None:
            tl = self.sq_topleft(selected_sq)
            s  = pygame.Surface((self.sq, self.sq), pygame.SRCALPHA)
            s.fill(C_SELECTED)
            self.surf.blit(s, tl)

        if legal_dests:
            for dest in legal_dests:
                cx, cy = self.sq_to_px(dest)
                dot_surf = pygame.Surface((self.sq, self.sq), pygame.SRCALPHA)
                if board.piece_at(dest):
                    pygame.draw.circle(dot_surf, C_HIGHLIGHT,
                                       (self.sq // 2, self.sq // 2),
                                       self.sq // 2 - 3, 5)
                else:
                    pygame.draw.circle(dot_surf, C_HIGHLIGHT,
                                       (self.sq // 2, self.sq // 2),
                                       self.sq // 7)
                tl = self.sq_topleft(dest)
                self.surf.blit(dot_surf, tl)

    def _draw_pieces(self, board: chess.Board, dragged_sq: int | None = None):
        for sq in chess.SQUARES:
            if sq == dragged_sq:
                continue
            if self._anim_piece and not self._anim_done() and sq == self._anim_to_sq:
                continue
            piece = board.piece_at(sq)
            if piece is None:
                continue
            psurf = get_piece_surface(piece.symbol(), self.sq - 8)
            cx, cy = self.sq_to_px(sq)
            self.surf.blit(psurf, psurf.get_rect(center=(cx, cy)))

        if dragged_sq is not None:
            piece = board.piece_at(dragged_sq)
            if piece:
                psurf = get_piece_surface(piece.symbol(), self.sq)
                mx, my = pygame.mouse.get_pos()
                self.surf.blit(psurf, psurf.get_rect(center=(mx, my)))

    def _draw_animation(self):
        if self._anim_piece is None:
            return
        elapsed = time.time() - self._anim_t
        if elapsed >= self._anim_dur:
            self._anim_piece = None
            self._anim_to_sq = None
            return
        t = elapsed / self._anim_dur
        t = 1 - (1 - t) ** 3
        sx, sy = self._anim_from
        ex, ey = self._anim_to
        cx = int(sx + (ex - sx) * t)
        cy = int(sy + (ey - sy) * t)
        psurf = get_piece_surface(self._anim_piece, self.sq - 8)
        self.surf.blit(psurf, psurf.get_rect(center=(cx, cy)))

    def _draw_coords(self):
        font = pygame.font.SysFont("Segoe UI", 12, bold=True)
        files = "abcdefgh"
        ranks = "12345678"
        for i in range(8):
            f_col = C_BLACK_SQ if i % 2 == 0 else C_WHITE_SQ
            fl = files[7 - i] if self.flipped else files[i]
            ts = font.render(fl, True, f_col)
            self.surf.blit(ts, (self.ox + i * self.sq + self.sq - 12,
                                self.oy + BOARD_SIZE - 15))
            r_col = C_WHITE_SQ if i % 2 == 0 else C_BLACK_SQ
            rk = ranks[i] if self.flipped else ranks[7 - i]
            ts = font.render(rk, True, r_col)
            self.surf.blit(ts, (self.ox + 3, self.oy + i * self.sq + 2))

    def _draw_border(self):
        for i in range(4, 0, -1):
            alpha = 15 * i
            shadow = pygame.Surface(
                (BOARD_SIZE + i * 4, BOARD_SIZE + i * 4), pygame.SRCALPHA
            )
            pygame.draw.rect(
                shadow, (0, 0, 0, alpha), shadow.get_rect(),
                border_radius=6
            )
            self.surf.blit(shadow,
                           (self.ox - i * 2, self.oy - i * 2))
        pygame.draw.rect(self.surf, (40, 35, 30),
                         pygame.Rect(self.ox - 2, self.oy - 2,
                                     BOARD_SIZE + 4, BOARD_SIZE + 4), 3,
                         border_radius=2)

