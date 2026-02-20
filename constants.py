import os

WINDOW_W = 1200
WINDOW_H = 800
BOARD_SIZE = 640
SQUARE_SIZE = BOARD_SIZE // 8
BOARD_OFFSET_X = 40
BOARD_OFFSET_Y = (WINDOW_H - BOARD_SIZE) // 2

C_BG         = (13,  17,  23)
C_PANEL      = (22,  27,  34)
C_PANEL2     = (30,  36,  44)
C_ACCENT     = (88, 166, 255)
C_ACCENT2    = (255, 123,  68)
C_GOLD       = (255, 215,   0)
C_GREEN      = ( 46, 204, 113)
C_RED        = (231,  76,  60)
C_TEXT       = (230, 237, 243)
C_TEXT_DIM   = (139, 148, 158)
C_WHITE_SQ   = (240, 217, 181)
C_BLACK_SQ   = (181, 136,  99)
C_HIGHLIGHT  = (106, 168, 107, 180)
C_SELECTED   = (255, 215,   0, 200)
C_LAST_MOVE  = (205, 210,  56, 140)
C_CHECK      = (231,  76,  60, 200)

BOT_LEVELS = {
    "Novice":      {"depth": 1, "label": "Novice",    "description": "Perfect for beginners"},
    "Easy":        {"depth": 2, "label": "Easy",      "description": "Casual play"},
    "Medium":      {"depth": 3, "label": "Medium",    "description": "Some challenge"},
    "Hard":        {"depth": 4, "label": "Hard",      "description": "Strong opponent"},
    "Expert":      {"depth": 5, "label": "Expert",    "description": "Very tough"},
    "Master":      {"depth": 6, "label": "Master",    "description": "Near-perfect play"},
}

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR  = os.path.join(BASE_DIR, "assets")
SCORES_FILE = os.path.join(BASE_DIR, "scores.json")

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 55765
BUFFER_SIZE  = 4096

PIECE_UNICODE = {
    "P": "♙", "N": "♘", "B": "♗", "R": "♖", "Q": "♕", "K": "♔",
    "p": "♟", "n": "♞", "b": "♝", "r": "♜", "q": "♛", "k": "♚",
}

FPS = 60

