const ChessBot = (() => {
    const PIECE_VALUE = { p: 100, n: 320, b: 330, r: 500, q: 900, k: 20000 };

    const PST = {
        p: [
             0,  0,  0,  0,  0,  0,  0,  0,
            50, 50, 50, 50, 50, 50, 50, 50,
            10, 10, 20, 30, 30, 20, 10, 10,
             5,  5, 10, 25, 25, 10,  5,  5,
             0,  0,  0, 20, 20,  0,  0,  0,
             5, -5,-10,  0,  0,-10, -5,  5,
             5, 10, 10,-20,-20, 10, 10,  5,
             0,  0,  0,  0,  0,  0,  0,  0
        ],
        n: [
            -50,-40,-30,-30,-30,-30,-40,-50,
            -40,-20,  0,  0,  0,  0,-20,-40,
            -30,  0, 10, 15, 15, 10,  0,-30,
            -30,  5, 15, 20, 20, 15,  5,-30,
            -30,  0, 15, 20, 20, 15,  0,-30,
            -30,  5, 10, 15, 15, 10,  5,-30,
            -40,-20,  0,  5,  5,  0,-20,-40,
            -50,-40,-30,-30,-30,-30,-40,-50
        ],
        b: [
            -20,-10,-10,-10,-10,-10,-10,-20,
            -10,  0,  0,  0,  0,  0,  0,-10,
            -10,  0,  5, 10, 10,  5,  0,-10,
            -10,  5,  5, 10, 10,  5,  5,-10,
            -10,  0, 10, 10, 10, 10,  0,-10,
            -10, 10, 10, 10, 10, 10, 10,-10,
            -10,  5,  0,  0,  0,  0,  5,-10,
            -20,-10,-10,-10,-10,-10,-10,-20
        ],
        r: [
             0,  0,  0,  0,  0,  0,  0,  0,
             5, 10, 10, 10, 10, 10, 10,  5,
            -5,  0,  0,  0,  0,  0,  0, -5,
            -5,  0,  0,  0,  0,  0,  0, -5,
            -5,  0,  0,  0,  0,  0,  0, -5,
            -5,  0,  0,  0,  0,  0,  0, -5,
            -5,  0,  0,  0,  0,  0,  0, -5,
             0,  0,  0,  5,  5,  0,  0,  0
        ],
        q: [
            -20,-10,-10, -5, -5,-10,-10,-20,
            -10,  0,  0,  0,  0,  0,  0,-10,
            -10,  0,  5,  5,  5,  5,  0,-10,
             -5,  0,  5,  5,  5,  5,  0, -5,
              0,  0,  5,  5,  5,  5,  0, -5,
            -10,  5,  5,  5,  5,  5,  0,-10,
            -10,  0,  5,  0,  0,  0,  0,-10,
            -20,-10,-10, -5, -5,-10,-10,-20
        ],
        k: [
            -30,-40,-40,-50,-50,-40,-40,-30,
            -30,-40,-40,-50,-50,-40,-40,-30,
            -30,-40,-40,-50,-50,-40,-40,-30,
            -30,-40,-40,-50,-50,-40,-40,-30,
            -20,-30,-30,-40,-40,-30,-30,-20,
            -10,-20,-20,-20,-20,-20,-20,-10,
             20, 20,  0,  0,  0,  0, 20, 20,
             20, 30, 10,  0,  0, 10, 30, 20
        ]
    };

    const LEVELS = {
        'Novice':  { depth: 1, time: 300,  elo: 600 },
        'Easy':    { depth: 2, time: 500,  elo: 900 },
        'Medium':  { depth: 3, time: 1000, elo: 1200 },
        'Hard':    { depth: 4, time: 2000, elo: 1500 },
        'Expert':  { depth: 5, time: 4000, elo: 1800 },
        'Master':  { depth: 6, time: 8000, elo: 2200 }
    };

    function evaluate(game) {
        if (game.in_checkmate()) {
            return game.turn() === 'w' ? -20000 : 20000;
        }
        if (game.in_draw() || game.in_stalemate() || game.insufficient_material()) {
            return 0;
        }

        const board = game.board();
        let score = 0;

        for (let row = 0; row < 8; row++) {
            for (let col = 0; col < 8; col++) {
                const piece = board[row][col];
                if (!piece) continue;
                const val = PIECE_VALUE[piece.type];
                const idx = piece.color === 'w' ? row * 8 + col : (7 - row) * 8 + col;
                const pst = PST[piece.type][idx];
                if (piece.color === 'w') {
                    score += val + pst;
                } else {
                    score -= val + pst;
                }
            }
        }

        const mobility = game.moves().length;
        if (game.turn() === 'w') {
            score += mobility * 5;
        } else {
            score -= mobility * 5;
        }

        return score;
    }

    function orderMoves(game) {
        const moves = game.moves({ verbose: true });
        return moves.sort((a, b) => {
            let sa = 0, sb = 0;
            if (a.captured) sa += 10 * PIECE_VALUE[a.captured] - PIECE_VALUE[a.piece];
            if (b.captured) sb += 10 * PIECE_VALUE[b.captured] - PIECE_VALUE[b.piece];
            if (a.promotion) sa += PIECE_VALUE[a.promotion];
            if (b.promotion) sb += PIECE_VALUE[b.promotion];
            if (a.san.includes('+')) sa += 50;
            if (b.san.includes('+')) sb += 50;
            return sb - sa;
        });
    }

    function minimax(game, depth, alpha, beta, maximizing, deadline) {
        if (Date.now() > deadline) throw 'timeout';
        if (depth === 0 || game.game_over()) return evaluate(game);

        const moves = orderMoves(game);

        if (maximizing) {
            let best = -99999;
            for (const move of moves) {
                game.move(move.san);
                const val = minimax(game, depth - 1, alpha, beta, false, deadline);
                game.undo();
                best = Math.max(best, val);
                alpha = Math.max(alpha, best);
                if (beta <= alpha) break;
            }
            return best;
        } else {
            let best = 99999;
            for (const move of moves) {
                game.move(move.san);
                const val = minimax(game, depth - 1, alpha, beta, true, deadline);
                game.undo();
                best = Math.min(best, val);
                beta = Math.min(beta, best);
                if (beta <= alpha) break;
            }
            return best;
        }
    }

    function getBestMove(game, level) {
        const config = LEVELS[level] || LEVELS['Medium'];
        const moves = game.moves({ verbose: true });

        if (moves.length === 0) return null;
        if (moves.length === 1) return moves[0];

        if (level === 'Novice' && Math.random() < 0.7) {
            return moves[Math.floor(Math.random() * moves.length)];
        }
        if (level === 'Easy' && Math.random() < 0.3) {
            return moves[Math.floor(Math.random() * moves.length)];
        }

        const maximizing = game.turn() === 'w';
        const deadline = Date.now() + config.time;
        let bestMove = moves[0];

        for (let d = 1; d <= config.depth; d++) {
            try {
                let candidateMove = null;
                let candidateVal = maximizing ? -99999 : 99999;

                for (const move of orderMoves(game)) {
                    game.move(move.san);
                    const val = minimax(game, d - 1, -99999, 99999, !maximizing, deadline);
                    game.undo();

                    if (maximizing && val > candidateVal) {
                        candidateVal = val;
                        candidateMove = move;
                    } else if (!maximizing && val < candidateVal) {
                        candidateVal = val;
                        candidateMove = move;
                    }
                }

                if (candidateMove) {
                    bestMove = candidateMove;
                }
            } catch (e) {
                break;
            }
        }

        return bestMove;
    }

    return { getBestMove, LEVELS };
})();
