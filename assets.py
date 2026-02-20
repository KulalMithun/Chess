import pygame
import os
import time
import urllib.request
from constants import SQUARE_SIZE, ASSETS_DIR

_piece_cache: dict = {}
_PIECES_DIR = os.path.join(ASSETS_DIR, "pieces")
_raw_images: dict = {}
_init_done = False

_GH_BASE = ("https://raw.githubusercontent.com/"
            "oakmac/chessboardjs/master/website/img/chesspieces/wikipedia")
_PIECE_FILES = {
    "K": "wK.png", "Q": "wQ.png", "R": "wR.png",
    "B": "wB.png", "N": "wN.png", "P": "wP.png",
    "k": "bK.png", "q": "bQ.png", "r": "bR.png",
    "b": "bB.png", "n": "bN.png", "p": "bP.png",
}

def _download_pieces() -> bool:
    os.makedirs(_PIECES_DIR, exist_ok=True)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36"
    }
    ok = True
    for sym, fname in _PIECE_FILES.items():
        fpath = os.path.join(_PIECES_DIR, fname)
        if os.path.exists(fpath) and os.path.getsize(fpath) > 100:
            continue
        url = f"{_GH_BASE}/{fname}"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = resp.read()
            if len(data) > 100:
                with open(fpath, "wb") as f:
                    f.write(data)
            else:
                ok = False
            time.sleep(0.05)
        except Exception as e:
            print(f"[Assets] Could not download '{sym}': {e}")
            ok = False
    return ok

def _load_images():
    global _init_done
    if _init_done:
        return
    _init_done = True

    _download_pieces()

    loaded = 0
    has_display = pygame.display.get_surface() is not None
    for sym, fname in _PIECE_FILES.items():
        fpath = os.path.join(_PIECES_DIR, fname)
        if os.path.exists(fpath):
            try:
                img = pygame.image.load(fpath)
                _raw_images[sym] = img.convert_alpha() if has_display else img
                loaded += 1
            except Exception:
                pass

    if loaded == 12:
        print(f"[Assets] Loaded all 12 piece images")
    elif loaded > 0:
        print(f"[Assets] Loaded {loaded}/12 piece images (rest: procedural)")
    else:
        print("[Assets] Using procedural piece rendering")

def get_piece_surface(symbol: str, size: int = SQUARE_SIZE) -> pygame.Surface:
    key = (symbol, size)
    if key not in _piece_cache:
        _load_images()
        if symbol in _raw_images:
            _piece_cache[key] = pygame.transform.smoothscale(
                _raw_images[symbol], (size, size)
            )
        else:
            _piece_cache[key] = _draw_piece_hq(symbol, size)
    return _piece_cache[key]

def clear_cache():
    _piece_cache.clear()

def _draw_piece_hq(symbol: str, target_size: int) -> pygame.Surface:
    big = _draw_piece_raw(symbol, target_size * 4)
    return pygame.transform.smoothscale(big, (target_size, target_size))

def _draw_piece_raw(symbol: str, size: int) -> pygame.Surface:
    surf = pygame.Surface((size, size), pygame.SRCALPHA)

    is_white = symbol.isupper()
    piece = symbol.upper()

    if is_white:
        body = (252, 250, 245)
        shade = (215, 205, 185)
        outline = (90, 70, 50)
        highlight = (255, 255, 255, 100)
    else:
        body = (60, 55, 50)
        shade = (35, 30, 25)
        outline = (180, 170, 155)
        highlight = (120, 115, 105, 60)

    cx, cy = size // 2, size // 2
    s = size / 64

    def ci(v):
        return int(v * s)

    def base():
        shadow_pts = [
            (cx - ci(22), cy + ci(30)),
            (cx + ci(22), cy + ci(30)),
            (cx + ci(18), cy + ci(24)),
            (cx - ci(18), cy + ci(24)),
        ]
        pygame.draw.polygon(surf, (0, 0, 0, 40), shadow_pts)

        pts = [
            (cx - ci(22), cy + ci(28)),
            (cx + ci(22), cy + ci(28)),
            (cx + ci(18), cy + ci(22)),
            (cx - ci(18), cy + ci(22)),
        ]
        pygame.draw.polygon(surf, shade, pts)
        pts_top = [(p[0], p[1] - ci(2)) for p in pts]
        pygame.draw.polygon(surf, body, pts_top)
        pygame.draw.polygon(surf, outline, pts, max(1, ci(2)))

    def pawn():
        base()
        r = pygame.Rect(cx - ci(6), cy + ci(4), ci(12), ci(18))
        pygame.draw.rect(surf, shade, r, border_radius=ci(3))
        r2 = r.move(0, -ci(1))
        pygame.draw.rect(surf, body, r2, border_radius=ci(3))
        pygame.draw.rect(surf, outline, r, max(1, ci(1)), border_radius=ci(3))
        pygame.draw.circle(surf, shade, (cx, cy - ci(4)), ci(12))
        pygame.draw.circle(surf, body, (cx, cy - ci(5)), ci(11))
        pygame.draw.circle(surf, outline, (cx, cy - ci(5)), ci(11), max(1, ci(2)))
        pygame.draw.circle(surf, highlight, (cx - ci(3), cy - ci(8)), ci(4))

    def rook():
        base()
        r = pygame.Rect(cx - ci(15), cy - ci(10), ci(30), ci(32))
        pygame.draw.rect(surf, shade, r, border_radius=ci(2))
        r2 = r.move(0, -ci(1))
        pygame.draw.rect(surf, body, r2, border_radius=ci(2))
        pygame.draw.rect(surf, outline, r, max(1, ci(2)), border_radius=ci(2))
        for dx in [-ci(10), -ci(2), ci(6)]:
            mr = pygame.Rect(cx + dx - ci(1), cy - ci(24), ci(7), ci(16))
            pygame.draw.rect(surf, body, mr)
            pygame.draw.rect(surf, outline, mr, max(1, ci(1)))
        hl = pygame.Rect(cx - ci(10), cy - ci(6), ci(6), ci(20))
        pygame.draw.rect(surf, highlight, hl)

    def knight():
        base()
        pts = [
            (cx - ci(6), cy + ci(20)),
            (cx + ci(10), cy + ci(20)),
            (cx + ci(14), cy - ci(2)),
            (cx + ci(10), cy - ci(12)),
            (cx + ci(2), cy - ci(20)),
            (cx - ci(10), cy - ci(18)),
            (cx - ci(14), cy - ci(8)),
            (cx - ci(8), cy + ci(2)),
        ]
        pygame.draw.polygon(surf, shade, pts)
        pts2 = [(p[0], p[1] - ci(1)) for p in pts]
        pygame.draw.polygon(surf, body, pts2)
        pygame.draw.polygon(surf, outline, pts, max(1, ci(2)))
        pygame.draw.circle(surf, outline, (cx + ci(5), cy - ci(10)), ci(2))
        pygame.draw.circle(surf, highlight,
                           (cx - ci(4), cy - ci(12)), ci(5))

    def bishop():
        base()
        pts = [
            (cx - ci(10), cy + ci(20)),
            (cx + ci(10), cy + ci(20)),
            (cx + ci(6), cy + ci(5)),
            (cx + ci(2), cy - ci(12)),
            (cx - ci(2), cy - ci(12)),
            (cx - ci(6), cy + ci(5)),
        ]
        pygame.draw.polygon(surf, shade, pts)
        pygame.draw.polygon(surf, body,
                            [(p[0], p[1] - ci(1)) for p in pts])
        pygame.draw.polygon(surf, outline, pts, max(1, ci(2)))
        pygame.draw.circle(surf, body, (cx, cy - ci(18)), ci(6))
        pygame.draw.circle(surf, outline, (cx, cy - ci(18)), ci(6),
                           max(1, ci(2)))
        pygame.draw.circle(surf, outline, (cx, cy - ci(25)), ci(2))
        pygame.draw.line(surf, outline,
                         (cx, cy - ci(12)), (cx, cy + ci(2)), max(1, ci(1)))

    def queen():
        base()
        pts = [
            (cx - ci(18), cy + ci(20)),
            (cx + ci(18), cy + ci(20)),
            (cx + ci(12), cy + ci(2)),
            (cx + ci(4), cy - ci(14)),
            (cx, cy - ci(22)),
            (cx - ci(4), cy - ci(14)),
            (cx - ci(12), cy + ci(2)),
        ]
        pygame.draw.polygon(surf, shade, pts)
        pygame.draw.polygon(surf, body,
                            [(p[0], p[1] - ci(1)) for p in pts])
        pygame.draw.polygon(surf, outline, pts, max(1, ci(2)))
        for px_, py_ in [(cx - ci(18), cy + ci(18)),
                         (cx - ci(4), cy - ci(15)),
                         (cx, cy - ci(23)),
                         (cx + ci(4), cy - ci(15)),
                         (cx + ci(18), cy + ci(18))]:
            pygame.draw.circle(surf, body, (px_, py_), ci(4))
            pygame.draw.circle(surf, outline, (px_, py_), ci(4),
                               max(1, ci(1)))
        pygame.draw.ellipse(surf, highlight,
                            pygame.Rect(cx - ci(8), cy - ci(18), ci(10), ci(8)))

    def king():
        base()
        pts = [
            (cx - ci(14), cy + ci(20)),
            (cx + ci(14), cy + ci(20)),
            (cx + ci(10), cy + ci(4)),
            (cx + ci(10), cy - ci(8)),
            (cx - ci(10), cy - ci(8)),
            (cx - ci(10), cy + ci(4)),
        ]
        pygame.draw.polygon(surf, shade, pts)
        pygame.draw.polygon(surf, body,
                            [(p[0], p[1] - ci(1)) for p in pts])
        pygame.draw.polygon(surf, outline, pts, max(1, ci(2)))
        cross_col = body
        pygame.draw.rect(surf, cross_col,
                         pygame.Rect(cx - ci(3), cy - ci(24), ci(6), ci(18)))
        pygame.draw.rect(surf, cross_col,
                         pygame.Rect(cx - ci(9), cy - ci(19), ci(18), ci(6)))
        pygame.draw.rect(surf, outline,
                         pygame.Rect(cx - ci(3), cy - ci(24), ci(6), ci(18)),
                         max(1, ci(1)))
        pygame.draw.rect(surf, outline,
                         pygame.Rect(cx - ci(9), cy - ci(19), ci(18), ci(6)),
                         max(1, ci(1)))
        pygame.draw.ellipse(surf, highlight,
                            pygame.Rect(cx - ci(6), cy - ci(4), ci(8), ci(14)))

    drawers = {
        'P': pawn, 'R': rook, 'N': knight,
        'B': bishop, 'Q': queen, 'K': king,
    }
    drawers[piece]()

    return surf

