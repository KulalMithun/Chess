import chess
import random
import time
from constants import BOT_LEVELS

PST = {
    chess.PAWN: [
         0,  0,  0,  0,  0,  0,  0,  0,
        50, 50, 50, 50, 50, 50, 50, 50,
        10, 10, 20, 30, 30, 20, 10, 10,
         5,  5, 10, 25, 25, 10,  5,  5,
         0,  0,  0, 20, 20,  0,  0,  0,
         5, -5,-10,  0,  0,-10, -5,  5,
         5, 10, 10,-20,-20, 10, 10,  5,
         0,  0,  0,  0,  0,  0,  0,  0
    ],
    chess.KNIGHT: [
        -50,-40,-30,-30,-30,-30,-40,-50,
        -40,-20,  0,  0,  0,  0,-20,-40,
        -30,  0, 10, 15, 15, 10,  0,-30,
        -30,  5, 15, 20, 20, 15,  5,-30,
        -30,  0, 15, 20, 20, 15,  0,-30,
        -30,  5, 10, 15, 15, 10,  5,-30,
        -40,-20,  0,  5,  5,  0,-20,-40,
        -50,-40,-30,-30,-30,-30,-40,-50,
    ],
    chess.BISHOP: [
        -20,-10,-10,-10,-10,-10,-10,-20,
        -10,  0,  0,  0,  0,  0,  0,-10,
        -10,  0,  5, 10, 10,  5,  0,-10,
        -10,  5,  5, 10, 10,  5,  5,-10,
        -10,  0, 10, 10, 10, 10,  0,-10,
        -10, 10, 10, 10, 10, 10, 10,-10,
        -10,  5,  0,  0,  0,  0,  5,-10,
        -20,-10,-10,-10,-10,-10,-10,-20,
    ],
    chess.ROOK: [
         0,  0,  0,  0,  0,  0,  0,  0,
         5, 10, 10, 10, 10, 10, 10,  5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
         0,  0,  0,  5,  5,  0,  0,  0,
    ],
    chess.QUEEN: [
        -20,-10,-10, -5, -5,-10,-10,-20,
        -10,  0,  0,  0,  0,  0,  0,-10,
        -10,  0,  5,  5,  5,  5,  0,-10,
         -5,  0,  5,  5,  5,  5,  0, -5,
          0,  0,  5,  5,  5,  5,  0, -5,
        -10,  5,  5,  5,  5,  5,  0,-10,
        -10,  0,  5,  0,  0,  0,  0,-10,
        -20,-10,-10, -5, -5,-10,-10,-20,
    ],
    chess.KING: [
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -20,-30,-30,-40,-40,-30,-30,-20,
        -10,-20,-20,-20,-20,-20,-20,-10,
         20, 20,  0,  0,  0,  0, 20, 20,
         20, 30, 10,  0,  0, 10, 30, 20,
    ],
}

PIECE_VALUE = {
    chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330,
    chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 20000,
}

def _sq_idx(square: int, is_white: bool) -> int:
    rank = chess.square_rank(square)
    file = chess.square_file(square)
    if is_white:
        return (7 - rank) * 8 + file
    else:
        return rank * 8 + file

def _evaluate(board: chess.Board) -> int:
    if board.is_checkmate():
        return -20000 if board.turn == chess.WHITE else 20000
    if board.is_stalemate() or board.is_insufficient_material():
        return 0

    score = 0
    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if piece is None:
            continue
        val = PIECE_VALUE[piece.piece_type]
        pst = PST[piece.piece_type][_sq_idx(sq, piece.color == chess.WHITE)]
        if piece.color == chess.WHITE:
            score += val + pst
        else:
            score -= val + pst

    if board.turn == chess.WHITE:
        score += len(list(board.legal_moves)) * 5
        board.push(chess.Move.null())
        score -= len(list(board.legal_moves)) * 5
        board.pop()
    else:
        score -= len(list(board.legal_moves)) * 5
        board.push(chess.Move.null())
        score += len(list(board.legal_moves)) * 5
        board.pop()

    return score

def _order_moves(board: chess.Board):
    def score(move):
        s = 0
        if board.is_capture(move):
            victim = board.piece_at(move.to_square)
            attacker = board.piece_at(move.from_square)
            if victim and attacker:
                s += 10 * PIECE_VALUE[victim.piece_type] - PIECE_VALUE[attacker.piece_type]
        if move.promotion:
            s += PIECE_VALUE[move.promotion]
        if board.gives_check(move):
            s += 50
        return s
    return sorted(board.legal_moves, key=score, reverse=True)

def _minimax(board: chess.Board, depth: int, alpha: int, beta: int,
             maximising: bool, start_time: float, time_limit: float) -> int:
    if time.time() - start_time > time_limit:
        raise TimeoutError

    if depth == 0 or board.is_game_over():
        return _evaluate(board)

    if maximising:
        best = -99999
        for move in _order_moves(board):
            board.push(move)
            val = _minimax(board, depth - 1, alpha, beta, False, start_time, time_limit)
            board.pop()
            best = max(best, val)
            alpha = max(alpha, best)
            if beta <= alpha:
                break
        return best
    else:
        best = 99999
        for move in _order_moves(board):
            board.push(move)
            val = _minimax(board, depth - 1, alpha, beta, True, start_time, time_limit)
            board.pop()
            best = min(best, val)
            beta = min(beta, best)
            if beta <= alpha:
                break
        return best

class ChessBot:
    def __init__(self, level: str = "Medium"):
        self.set_level(level)

    def set_level(self, level: str):
        cfg = BOT_LEVELS.get(level, BOT_LEVELS["Medium"])
        self.level   = level
        self.depth   = cfg["depth"]
        self.label   = cfg["label"]
        self._time_limits = {
            "Novice": 0.3, "Easy": 0.5, "Medium": 1.0,
            "Hard": 2.0, "Expert": 4.0, "Master": 8.0,
        }
        self.time_limit = self._time_limits.get(level, 2.0)

    def get_move(self, board: chess.Board) -> chess.Move:
        legal = list(board.legal_moves)
        if not legal:
            return None
        if len(legal) == 1:
            return legal[0]

        if self.level == "Novice":
            if random.random() < 0.7:
                return random.choice(legal)

        if self.level == "Easy":
            if random.random() < 0.3:
                return random.choice(legal)

        best_move = None
        best_val  = -99999 if board.turn == chess.WHITE else 99999
        maximising = board.turn == chess.WHITE
        start_time = time.time()

        for cur_depth in range(1, self.depth + 1):
            try:
                candidate_move = None
                candidate_val  = -99999 if maximising else 99999

                for move in _order_moves(board):
                    board.push(move)
                    val = _minimax(board, cur_depth - 1, -99999, 99999,
                                   not maximising, start_time, self.time_limit)
                    board.pop()

                    if maximising and val > candidate_val:
                        candidate_val = val
                        candidate_move = move
                    elif not maximising and val < candidate_val:
                        candidate_val = val
                        candidate_move = move

                if candidate_move:
                    best_move = candidate_move
                    best_val  = candidate_val

            except TimeoutError:
                break

        return best_move or random.choice(legal)

    @property
    def elo_rating(self) -> int:
        from constants import BOT_LEVELS
        elos = {"Novice": 600, "Easy": 900, "Medium": 1200,
                "Hard": 1500, "Expert": 1800, "Master": 2200}
        return elos.get(self.level, 1200)

