import pygame
import math
import time
from constants import *

def _font(size: int, bold: bool = False):
    try:
        return pygame.font.SysFont("Segoe UI", size, bold=bold)
    except Exception:
        return pygame.font.SysFont(None, size, bold=bold)

def draw_rounded_rect(surf: pygame.Surface, color, rect: pygame.Rect, radius: int = 12, alpha: int = 255):
    if alpha < 255:
        s = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(s, (*color[:3], alpha), s.get_rect(), border_radius=radius)
        surf.blit(s, rect.topleft)
    else:
        pygame.draw.rect(surf, color, rect, border_radius=radius)

def draw_text(surf: pygame.Surface, text: str, pos, size: int = 18,
              color=C_TEXT, bold: bool = False, center: bool = False):
    font = _font(size, bold)
    rendered = font.render(text, True, color)
    if center:
        pos = (pos[0] - rendered.get_width() // 2,
               pos[1] - rendered.get_height() // 2)
    surf.blit(rendered, pos)
    return rendered.get_rect(topleft=pos)

def text_width(text: str, size: int = 18, bold: bool = False) -> int:
    return _font(size, bold).size(text)[0]

class Button:
    def __init__(self, rect: pygame.Rect, label: str,
                 color=C_ACCENT, text_color=C_BG,
                 font_size: int = 18, radius: int = 10,
                 icon: str = ""):
        self.rect       = rect
        self.label      = label
        self.color      = color
        self.text_color = text_color
        self.font_size  = font_size
        self.radius     = radius
        self.icon       = icon
        self._hover     = False
        self._press_t   = 0.0
        self.enabled    = True

    def update(self, mouse_pos):
        self._hover = self.rect.collidepoint(mouse_pos) and self.enabled

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.enabled:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self._press_t = time.time()
                return True
        return False

    def draw(self, surf: pygame.Surface):
        press_anim = max(0.0, 1.0 - (time.time() - self._press_t) * 4)
        scale = 1.0 - press_anim * 0.04

        col = self.color if self.enabled else C_TEXT_DIM
        if self._hover and self.enabled:
            col = tuple(min(255, int(c * 1.15)) for c in col[:3])

        r = self.rect.inflate(0, 0)
        if scale < 1.0:
            sw = int(r.width * scale)
            sh = int(r.height * scale)
            r = pygame.Rect(r.centerx - sw // 2, r.centery - sh // 2, sw, sh)

        shadow_col = tuple(max(0, c - 40) for c in col[:3])
        pygame.draw.rect(surf, shadow_col,
                         r.inflate(2, 2).move(0, 3), border_radius=self.radius)

        draw_rounded_rect(surf, col, r, self.radius)

        text = (self.icon + " " + self.label).strip()
        font = _font(self.font_size, True)
        ts   = font.render(text, True, self.text_color)
        surf.blit(ts, ts.get_rect(center=r.center))

class InputBox:
    def __init__(self, rect: pygame.Rect, placeholder: str = "",
                 max_len: int = 30, font_size: int = 18):
        self.rect        = rect
        self.placeholder = placeholder
        self.text        = ""
        self.max_len     = max_len
        self.font_size   = font_size
        self.active      = False
        self._cursor_t   = 0.0

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
        if not self.active:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key == pygame.K_RETURN:
                return True
            elif len(self.text) < self.max_len:
                if event.unicode.isprintable():
                    self.text += event.unicode
        return False

    def draw(self, surf: pygame.Surface):
        border_col = C_ACCENT if self.active else C_TEXT_DIM
        draw_rounded_rect(surf, C_PANEL2, self.rect, 8)
        pygame.draw.rect(surf, border_col, self.rect, 2, border_radius=8)
        font = _font(self.font_size)
        if self.text:
            ts = font.render(self.text, True, C_TEXT)
        else:
            ts = font.render(self.placeholder, True, C_TEXT_DIM)
        surf.blit(ts, ts.get_rect(midleft=(self.rect.left + 12, self.rect.centery)))
        if self.active and int(time.time() * 2) % 2 == 0:
            cx = self.rect.left + 12 + font.size(self.text)[0] + 1
            pygame.draw.rect(surf, C_TEXT,
                             pygame.Rect(cx, self.rect.y + 8, 2, self.rect.h - 16))

def draw_panel(surf: pygame.Surface, rect: pygame.Rect,
               title: str = "", alpha: int = 255):
    draw_rounded_rect(surf, C_PANEL, rect, 14, alpha)
    pygame.draw.rect(surf, C_PANEL2, rect, 1, border_radius=14)
    if title:
        bar = pygame.Rect(rect.x, rect.y, rect.width, 30)
        draw_rounded_rect(surf, C_PANEL2, bar, 14, alpha)
        fix = pygame.Rect(rect.x, rect.y + 16, rect.width, 14)
        draw_rounded_rect(surf, C_PANEL2, fix, 0, alpha)
        draw_text(surf, title, (rect.x + 14, rect.y + 7),
                  size=13, color=C_ACCENT, bold=True)

_bg_cache = None

def draw_gradient_bg(surf: pygame.Surface):
    global _bg_cache
    w, h = surf.get_size()
    if _bg_cache is None or _bg_cache.get_size() != (w, h):
        _bg_cache = pygame.Surface((w, h))
        top    = (10, 14, 20)
        mid    = (15, 20, 30)
        bottom = (12, 18, 28)
        for y in range(h):
            t = y / h
            if t < 0.5:
                t2 = t * 2
                col = tuple(int(top[i] + (mid[i] - top[i]) * t2)
                            for i in range(3))
            else:
                t2 = (t - 0.5) * 2
                col = tuple(int(mid[i] + (bottom[i] - mid[i]) * t2)
                            for i in range(3))
            pygame.draw.line(_bg_cache, col, (0, y), (w, y))
    surf.blit(_bg_cache, (0, 0))

class ParticleField:
    def __init__(self, w: int, h: int, n: int = 40):
        import random
        self._w = w
        self._h = h
        self._orbs = [
            {
                "x": random.uniform(0, w),
                "y": random.uniform(0, h),
                "r": random.uniform(2, 6),
                "vx": random.uniform(-0.2, 0.2),
                "vy": random.uniform(-0.15, 0.15),
                "alpha": random.uniform(30, 100),
                "col": random.choice([C_ACCENT, C_ACCENT2, C_GOLD]),
            }
            for _ in range(n)
        ]

    def update_draw(self, surf: pygame.Surface):
        for o in self._orbs:
            o["x"] = (o["x"] + o["vx"]) % self._w
            o["y"] = (o["y"] + o["vy"]) % self._h
            s = pygame.Surface((int(o["r"]) * 2 + 2, int(o["r"]) * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*o["col"][:3], int(o["alpha"])),
                               (int(o["r"]) + 1, int(o["r"]) + 1), int(o["r"]))
            surf.blit(s, (o["x"] - o["r"], o["y"] - o["r"]))

class Toast:
    def __init__(self, message: str, duration: float = 2.5,
                 color=C_GREEN):
        self.message  = message
        self.duration = duration
        self.color    = color
        self._birth   = time.time()

    def alive(self) -> bool:
        return time.time() - self._birth < self.duration

    def draw(self, surf: pygame.Surface):
        elapsed = time.time() - self._birth
        alpha   = 255
        if elapsed > self.duration - 0.4:
            alpha = int(255 * (self.duration - elapsed) / 0.4)
        alpha = max(0, min(255, alpha))

        font  = _font(18, True)
        ts    = font.render(self.message, True, C_TEXT)
        pad   = 16
        w     = ts.get_width() + pad * 2
        h     = ts.get_height() + pad
        x     = (surf.get_width() - w) // 2
        y     = surf.get_height() - 90

        s = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(s, (*self.color[:3], int(alpha * 0.9)),
                         s.get_rect(), border_radius=10)
        s.blit(ts, ts.get_rect(center=(w // 2, h // 2)))
        surf.blit(s, (x, y))

def draw_move_log(surf: pygame.Surface, rect: pygame.Rect,
                  moves: list[str], scroll: int = 0):
    draw_panel(surf, rect, "Move History")
    clip = surf.get_clip()
    surf.set_clip(rect.inflate(-4, -4))
    font_s = _font(13)
    font_b = _font(13, True)
    line_h = 20
    x0 = rect.x + 8
    y0 = rect.y + 34
    max_lines = (rect.height - 40) // line_h
    start = max(0, len(moves) // 2 - max_lines + 1 - scroll)
    drawn = 0
    for i in range(start, len(moves) // 2 + 1):
        if drawn >= max_lines:
            break
        y = y0 + drawn * line_h
        white_i = i * 2
        black_i = i * 2 + 1
        surf.blit(_font(12).render(f"{i+1}.", True, C_TEXT_DIM),
                  (x0, y))
        if white_i < len(moves):
            col = C_ACCENT if white_i == len(moves) - 1 else C_TEXT
            ts = font_b.render(moves[white_i], True, col)
            surf.blit(ts, (x0 + 26, y))
        if black_i < len(moves):
            col = C_ACCENT if black_i == len(moves) - 1 else C_TEXT
            ts = font_s.render(moves[black_i], True, col)
            surf.blit(ts, (x0 + 80, y))
        drawn += 1
    surf.set_clip(clip)

def draw_chat(surf: pygame.Surface, rect: pygame.Rect,
              messages: list[dict]):
    draw_panel(surf, rect, "Chat")
    font = _font(13)
    line_h = 18
    lines_area = rect.height - 44
    max_lines = lines_area // line_h
    clip = surf.get_clip()
    surf.set_clip(rect.inflate(-4, -24))
    shown = messages[-max_lines:]
    for idx, msg in enumerate(shown):
        y = rect.y + 36 + idx * line_h
        name_col = C_ACCENT if msg.get("self") else C_ACCENT2
        name = msg.get("name", "?")
        text = msg.get("text", "")
        nw = font.size(name + ": ")[0]
        surf.blit(font.render(name + ": ", True, name_col), (rect.x + 8, y))
        surf.blit(font.render(text, True, C_TEXT), (rect.x + 8 + nw, y))
    surf.set_clip(clip)

class PromotionDialog:
    PIECES = [("Q", "Queen"), ("R", "Rook"), ("B", "Bishop"), ("N", "Knight")]

    def __init__(self, surf_w: int, surf_h: int, is_white: bool):
        self.is_white = is_white
        w, h = 360, 100
        self.rect = pygame.Rect((surf_w - w) // 2, (surf_h - h) // 2, w, h)
        self.chosen = None
        self._buttons = []
        bw = 80
        for i, (sym, name) in enumerate(self.PIECES):
            br = pygame.Rect(self.rect.x + 10 + i * (bw + 5), self.rect.y + 34, bw, 50)
            self._buttons.append((sym, name, Button(br, name, C_ACCENT2, C_BG, 13)))

    def handle_event(self, event: pygame.event.Event) -> str | None:
        for sym, _, btn in self._buttons:
            if btn.handle_event(event):
                self.chosen = sym
                return sym
        return None

    def draw(self, surf: pygame.Surface):
        from assets import get_piece_surface
        draw_rounded_rect(surf, C_PANEL2, self.rect.inflate(4, 4), 14)
        draw_rounded_rect(surf, C_PANEL, self.rect, 12)
        draw_text(surf, "Choose Promotion Piece",
                  (self.rect.centerx, self.rect.y + 10),
                  size=15, bold=True, center=True)
        mouse = pygame.mouse.get_pos()
        for sym, name, btn in self._buttons:
            if self.is_white:
                piece_sym = sym
            else:
                piece_sym = sym.lower()
            btn.update(mouse)
            btn.draw(surf)

