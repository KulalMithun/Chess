const App = (() => {
    const IMG_BASE = 'https://raw.githubusercontent.com/oakmac/chessboardjs/master/website/img/chesspieces/wikipedia/';
    const PIECE_KEYS = ['wK','wQ','wR','wB','wN','wP','bK','bQ','bR','bB','bN','bP'];
    const FILES = 'abcdefgh';
    const LEVEL_DESCS = {
        'Novice': 'Perfect for beginners',
        'Easy': 'Casual play',
        'Medium': 'Some challenge',
        'Hard': 'Strong opponent',
        'Expert': 'Very tough',
        'Master': 'Near-perfect play'
    };
    const TIME_OPTIONS = [
        { label: 'No Limit', secs: 0 },
        { label: '1 min', secs: 60 },
        { label: '3 min', secs: 180 },
        { label: '5 min', secs: 300 },
        { label: '10 min', secs: 600 },
        { label: '15 min', secs: 900 }
    ];
    const BOT_ELO = { Novice: 600, Easy: 900, Medium: 1200, Hard: 1500, Expert: 1800, Master: 2200 };

    let game = null;
    let gameMode = null;
    let botLevel = 'Medium';
    let playerColor = 'w';
    let selectedSquare = null;
    let legalMoves = [];
    let lastMove = null;
    let isFlipped = false;
    let moveHistory = [];
    let gameOver = false;
    let gameResult = '';
    let gameReason = '';
    let botThinking = false;
    let resultRecorded = false;

    let clockEnabled = false;
    let clockTotal = 0;
    let clockTime = { w: 0, b: 0 };
    let clockRunning = false;
    let clockInterval = null;
    let clockLastTick = 0;

    let scores = null;
    let confirmReset = false;
    let selectedLevel = 'Medium';
    let selectedTime = 0;
    let selectedColor = 'w';

    function init() {
        loadScores();
        preloadImages(() => {
            document.getElementById('loading').classList.remove('active');
            showScreen('menu');
            updateMenuDisplay();
        });
        setupEventListeners();
        createParticles('particles-menu', 40);
        createParticles('particles-setup', 25);
        createParticles('particles-scores', 20);
    }

    function preloadImages(callback) {
        let loaded = 0;
        PIECE_KEYS.forEach(key => {
            const img = new Image();
            img.onload = img.onerror = () => { if (++loaded === PIECE_KEYS.length) callback(); };
            img.src = IMG_BASE + key + '.png';
        });
    }

    function showScreen(name) {
        document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
        const el = document.getElementById('screen-' + name);
        if (el) el.classList.add('active');
    }

    function setupEventListeners() {
        const $ = id => document.getElementById(id);

        $('name-input').addEventListener('input', e => {
            const name = e.target.value.trim() || 'Player';
            $('menu-player-name').textContent = name;
        });

        $('btn-vs-bot').addEventListener('click', () => {
            saveName();
            showScreen('setup');
            buildSetupScreen();
        });

        $('btn-local2p').addEventListener('click', () => {
            saveName();
            startGame('local2p');
        });

        $('btn-scores').addEventListener('click', () => {
            saveName();
            showScreen('scores');
            updateScoresDisplay();
        });

        $('btn-setup-back').addEventListener('click', () => showScreen('menu'));
        $('btn-scores-back').addEventListener('click', () => {
            showScreen('menu');
            updateMenuDisplay();
        });

        $('btn-start-game').addEventListener('click', () => {
            botLevel = selectedLevel;
            playerColor = selectedColor;
            clockTotal = selectedTime;
            startGame('bot');
        });

        $('btn-game-menu').addEventListener('click', () => {
            stopClock();
            showScreen('menu');
            updateMenuDisplay();
        });

        $('btn-resign').addEventListener('click', onResign);
        $('btn-draw').addEventListener('click', onDraw);
        $('btn-new-game').addEventListener('click', () => {
            stopClock();
            if (gameMode === 'bot') {
                showScreen('setup');
                buildSetupScreen();
            } else {
                startGame(gameMode);
            }
        });

        $('overlay-gameover').addEventListener('click', () => {
            $('overlay-gameover').classList.add('hidden');
            showScreen('menu');
            updateMenuDisplay();
        });

        $('btn-reset-scores').addEventListener('click', () => {
            if (confirmReset) {
                resetScores();
                $('btn-reset-scores').textContent = 'Reset Scores';
                confirmReset = false;
                updateScoresDisplay();
                showToast('Scores reset', 'var(--green)');
            } else {
                confirmReset = true;
                $('btn-reset-scores').textContent = 'Confirm Reset?';
                setTimeout(() => {
                    confirmReset = false;
                    $('btn-reset-scores').textContent = 'Reset Scores';
                }, 3000);
            }
        });
    }

    function saveName() {
        const name = document.getElementById('name-input').value.trim() || 'Player';
        scores.player_name = name;
        saveScores();
    }

    function updateMenuDisplay() {
        const $ = id => document.getElementById(id);
        $('name-input').value = scores.player_name;
        $('menu-player-name').textContent = scores.player_name;
        $('menu-elo-badge').textContent = 'ELO  ' + scores.elo;
    }

    function buildSetupScreen() {
        const levelGrid = document.getElementById('level-grid');
        levelGrid.innerHTML = '';
        Object.keys(ChessBot.LEVELS).forEach(lvl => {
            const cfg = ChessBot.LEVELS[lvl];
            const btn = document.createElement('button');
            btn.className = 'level-btn' + (lvl === selectedLevel ? ' selected' : '');
            btn.innerHTML = lvl + '<span class="level-sub">' + LEVEL_DESCS[lvl] + '</span>';
            btn.addEventListener('click', () => {
                selectedLevel = lvl;
                levelGrid.querySelectorAll('.level-btn').forEach(b => b.classList.remove('selected'));
                btn.classList.add('selected');
                const c = ChessBot.LEVELS[lvl];
                document.getElementById('level-desc').textContent = LEVEL_DESCS[lvl];
                document.getElementById('level-info').textContent = 'Depth: ' + c.depth + ' | ELO ≈ ' + c.elo;
            });
            levelGrid.appendChild(btn);
        });

        const timeGrid = document.getElementById('time-grid');
        timeGrid.innerHTML = '';
        TIME_OPTIONS.forEach(opt => {
            const btn = document.createElement('button');
            btn.className = 'time-btn' + (opt.secs === selectedTime ? ' selected' : '');
            btn.textContent = opt.label;
            btn.addEventListener('click', () => {
                selectedTime = opt.secs;
                timeGrid.querySelectorAll('.time-btn').forEach(b => b.classList.remove('selected'));
                btn.classList.add('selected');
            });
            timeGrid.appendChild(btn);
        });

        document.querySelectorAll('.color-btn').forEach(btn => {
            btn.classList.toggle('selected', btn.dataset.color === selectedColor);
            btn.onclick = () => {
                selectedColor = btn.dataset.color;
                document.querySelectorAll('.color-btn').forEach(b => b.classList.remove('selected'));
                btn.classList.add('selected');
            };
        });

        const cfg = ChessBot.LEVELS[selectedLevel];
        document.getElementById('level-desc').textContent = LEVEL_DESCS[selectedLevel];
        document.getElementById('level-info').textContent = 'Depth: ' + cfg.depth + ' | ELO ≈ ' + cfg.elo;
    }

    function startGame(mode) {
        gameMode = mode;
        game = new Chess();
        selectedSquare = null;
        legalMoves = [];
        lastMove = null;
        moveHistory = [];
        gameOver = false;
        gameResult = '';
        gameReason = '';
        botThinking = false;
        resultRecorded = false;

        if (mode === 'bot') {
            isFlipped = playerColor === 'b';
        } else {
            isFlipped = false;
            playerColor = 'w';
        }

        const botInfo = document.getElementById('bot-info');
        if (mode === 'bot') {
            botInfo.style.display = 'flex';
            document.getElementById('bot-name').textContent = 'Bot · ' + botLevel;
            const cfg = ChessBot.LEVELS[botLevel];
            document.getElementById('bot-meta').textContent = 'ELO ≈ ' + cfg.elo + ' • Depth ' + cfg.depth;
        } else {
            botInfo.style.display = 'none';
        }

        clockEnabled = (mode === 'bot' ? clockTotal : 0) > 0;
        if (clockEnabled) {
            clockTime = { w: clockTotal, b: clockTotal };
        } else {
            clockTime = { w: 99999, b: 99999 };
        }
        clockRunning = false;

        showScreen('game');
        createBoard();
        updateBoard();
        updateMoveLog();
        updateClocks();

        if (mode === 'bot') {
            startClock();
            if (playerColor === 'b') {
                triggerBotMove();
            }
        } else {
            startClock();
        }
    }

    function createBoard() {
        const board = document.getElementById('board');
        board.innerHTML = '';
        for (let row = 0; row < 8; row++) {
            for (let col = 0; col < 8; col++) {
                const file = isFlipped ? 7 - col : col;
                const rank = isFlipped ? row : 7 - row;
                const sqName = FILES[file] + (rank + 1);

                const sq = document.createElement('div');
                const isLight = (file + rank) % 2 !== 0;
                sq.className = 'square ' + (isLight ? 'light' : 'dark');
                sq.dataset.square = sqName;
                sq.addEventListener('click', () => onSquareClick(sqName));

                if (col === 0) {
                    const label = document.createElement('span');
                    label.className = 'coord-rank';
                    label.textContent = rank + 1;
                    sq.appendChild(label);
                }
                if (row === 7) {
                    const label = document.createElement('span');
                    label.className = 'coord-file';
                    label.textContent = FILES[file];
                    sq.appendChild(label);
                }

                board.appendChild(sq);
            }
        }
    }

    function updateBoard() {
        document.querySelectorAll('.square').forEach(sq => {
            const img = sq.querySelector('.piece');
            if (img) img.remove();
            const dot = sq.querySelector('.move-dot');
            if (dot) dot.remove();
            const ring = sq.querySelector('.capture-ring');
            if (ring) ring.remove();
            sq.classList.remove('selected', 'last-move', 'check');
        });

        if (lastMove) {
            addSquareClass(lastMove.from, 'last-move');
            addSquareClass(lastMove.to, 'last-move');
        }
        if (selectedSquare) {
            addSquareClass(selectedSquare, 'selected');
        }

        if (game.in_check()) {
            const board = game.board();
            const turn = game.turn();
            for (let r = 0; r < 8; r++) {
                for (let c = 0; c < 8; c++) {
                    const p = board[r][c];
                    if (p && p.type === 'k' && p.color === turn) {
                        addSquareClass(FILES[c] + (8 - r), 'check');
                    }
                }
            }
        }

        legalMoves.forEach(move => {
            const sqEl = getSquareEl(move.to);
            if (!sqEl) return;
            if (move.captured) {
                const ring = document.createElement('div');
                ring.className = 'capture-ring';
                sqEl.appendChild(ring);
            } else {
                const dot = document.createElement('div');
                dot.className = 'move-dot';
                sqEl.appendChild(dot);
            }
        });

        const board = game.board();
        for (let r = 0; r < 8; r++) {
            for (let c = 0; c < 8; c++) {
                const piece = board[r][c];
                if (!piece) continue;
                const sqName = FILES[c] + (8 - r);
                const sqEl = getSquareEl(sqName);
                if (!sqEl) continue;
                const key = (piece.color === 'w' ? 'w' : 'b') + piece.type.toUpperCase();
                const img = document.createElement('img');
                img.className = 'piece';
                img.src = IMG_BASE + key + '.png';
                img.alt = key;
                img.draggable = false;
                sqEl.appendChild(img);
            }
        }
    }

    function getSquareEl(sqName) {
        return document.querySelector('.square[data-square="' + sqName + '"]');
    }

    function addSquareClass(sqName, cls) {
        const el = getSquareEl(sqName);
        if (el) el.classList.add(cls);
    }

    function onSquareClick(sqName) {
        if (gameOver || botThinking) return;
        if (gameMode === 'bot' && game.turn() !== playerColor) return;

        const piece = game.get(sqName);

        if (selectedSquare === null) {
            if (piece && piece.color === game.turn()) {
                selectedSquare = sqName;
                legalMoves = game.moves({ square: sqName, verbose: true });
                updateBoard();
            }
        } else {
            const targetMoves = legalMoves.filter(m => m.to === sqName);
            if (targetMoves.length > 0) {
                if (targetMoves.some(m => m.flags.includes('p'))) {
                    showPromotionDialog(selectedSquare, sqName);
                } else {
                    executeMove(selectedSquare, sqName);
                }
            } else if (piece && piece.color === game.turn()) {
                selectedSquare = sqName;
                legalMoves = game.moves({ square: sqName, verbose: true });
                updateBoard();
            } else {
                selectedSquare = null;
                legalMoves = [];
                updateBoard();
            }
        }
    }

    function executeMove(from, to, promotion) {
        const moveObj = game.move({ from, to, promotion: promotion || undefined });
        if (!moveObj) return false;

        lastMove = { from, to };
        moveHistory.push(moveObj.san);
        selectedSquare = null;
        legalMoves = [];

        updateBoard();
        updateMoveLog();
        switchClock();

        if (checkGameOver()) return true;

        if (gameMode === 'bot' && game.turn() !== playerColor && !botThinking) {
            triggerBotMove();
        }
        return true;
    }

    function triggerBotMove() {
        botThinking = true;
        document.getElementById('thinking').classList.remove('hidden');

        requestAnimationFrame(() => {
            setTimeout(() => {
                const move = ChessBot.getBestMove(game, botLevel);
                botThinking = false;
                document.getElementById('thinking').classList.add('hidden');
                if (move && !gameOver) {
                    executeMove(move.from, move.to, move.promotion);
                }
            }, 80);
        });
    }

    function showPromotionDialog(from, to) {
        const overlay = document.getElementById('overlay-promotion');
        const options = document.getElementById('promotion-options');
        const color = game.turn() === 'w' ? 'w' : 'b';
        options.innerHTML = '';

        ['q', 'r', 'b', 'n'].forEach(piece => {
            const btn = document.createElement('button');
            btn.className = 'promo-btn';
            const img = document.createElement('img');
            img.src = IMG_BASE + color + piece.toUpperCase() + '.png';
            img.alt = piece;
            btn.appendChild(img);
            btn.addEventListener('click', () => {
                overlay.classList.add('hidden');
                executeMove(from, to, piece);
            });
            options.appendChild(btn);
        });

        overlay.classList.remove('hidden');
    }

    function checkGameOver() {
        if (!game.game_over()) {
            if (clockEnabled) {
                const flagged = clockTime.w <= 0 ? 'w' : (clockTime.b <= 0 ? 'b' : null);
                if (flagged) {
                    gameOver = true;
                    stopClock();
                    gameResult = flagged === 'w' ? 'black_wins' : 'white_wins';
                    gameReason = 'Time';
                    recordResult();
                    showGameOver();
                    return true;
                }
            }
            return false;
        }

        gameOver = true;
        stopClock();

        if (game.in_checkmate()) {
            gameResult = game.turn() === 'w' ? 'black_wins' : 'white_wins';
            gameReason = 'Checkmate';
        } else if (game.in_stalemate()) {
            gameResult = 'draw';
            gameReason = 'Stalemate';
        } else if (game.in_threefold_repetition()) {
            gameResult = 'draw';
            gameReason = 'Threefold Repetition';
        } else if (game.insufficient_material()) {
            gameResult = 'draw';
            gameReason = 'Insufficient Material';
        } else if (game.in_draw()) {
            gameResult = 'draw';
            gameReason = 'Draw';
        }

        recordResult();
        showGameOver();
        return true;
    }

    function showGameOver() {
        const $ = id => document.getElementById(id);
        let title, icon, color;
        if (gameResult === 'draw') {
            title = 'DRAW';
            icon = '½';
            color = 'var(--gold)';
        } else if (gameResult === 'white_wins') {
            title = 'WHITE WINS';
            icon = '♔';
            color = '#f0ebe0';
        } else {
            title = 'BLACK WINS';
            icon = '♚';
            color = 'var(--accent2)';
        }
        $('gameover-icon').textContent = icon;
        $('gameover-icon').style.color = color;
        $('gameover-title').textContent = title;
        $('gameover-title').style.color = color;
        $('gameover-reason').textContent = gameReason;
        $('gameover-moves').textContent = 'Moves: ' + game.history().length;
        $('gameover-elo').textContent = 'Your ELO: ' + scores.elo;
        $('gameover-elo').style.display = gameMode === 'local2p' ? 'none' : 'block';
        $('overlay-gameover').classList.remove('hidden');
    }

    function onResign() {
        if (gameOver) return;
        gameOver = true;
        stopClock();
        if (gameMode === 'bot') {
            gameResult = playerColor === 'w' ? 'black_wins' : 'white_wins';
        } else {
            gameResult = game.turn() === 'w' ? 'black_wins' : 'white_wins';
        }
        gameReason = 'Resignation';
        recordResult();
        showGameOver();
    }

    function onDraw() {
        if (gameOver) return;
        if (gameMode === 'local2p') {
            gameOver = true;
            stopClock();
            gameResult = 'draw';
            gameReason = 'Draw by Agreement';
            recordResult();
            showGameOver();
        }
    }

    function updateMoveLog() {
        const log = document.getElementById('move-log');
        log.innerHTML = '';
        for (let i = 0; i < moveHistory.length; i += 2) {
            const row = document.createElement('div');
            row.className = 'move-row';
            const num = document.createElement('span');
            num.className = 'move-num';
            num.textContent = (i / 2 + 1) + '.';
            row.appendChild(num);

            const w = document.createElement('span');
            w.className = 'move-white' + (i === moveHistory.length - 1 ? ' move-latest' : '');
            w.textContent = moveHistory[i];
            row.appendChild(w);

            if (i + 1 < moveHistory.length) {
                const b = document.createElement('span');
                b.className = 'move-black' + (i + 1 === moveHistory.length - 1 ? ' move-latest' : '');
                b.textContent = moveHistory[i + 1];
                row.appendChild(b);
            }

            log.appendChild(row);
        }
        log.scrollTop = log.scrollHeight;
    }

    function updateClocks() {
        const $ = id => document.getElementById(id);
        const turn = game ? game.turn() : 'w';

        let topColor, bottomColor;
        if (isFlipped) {
            topColor = 'w';
            bottomColor = 'b';
        } else {
            topColor = 'b';
            bottomColor = 'w';
        }

        const topActive = turn === topColor && clockRunning;
        const bottomActive = turn === bottomColor && clockRunning;

        $('dot-top').className = 'clock-dot' + (topActive ? ' active' : '');
        $('dot-bottom').className = 'clock-dot' + (bottomActive ? ' active' : '');

        let topName, bottomName;
        if (gameMode === 'bot') {
            const botColor = playerColor === 'w' ? 'b' : 'w';
            topName = topColor === botColor ? 'Bot (' + botLevel + ')' : scores.player_name;
            bottomName = bottomColor === botColor ? 'Bot (' + botLevel + ')' : scores.player_name;
        } else {
            topName = topColor === 'w' ? 'White' : 'Black';
            bottomName = bottomColor === 'w' ? 'White' : 'Black';
        }

        $('name-top').textContent = topName;
        $('name-top').className = 'clock-name' + (topActive ? ' active' : '');
        $('name-bottom').textContent = bottomName;
        $('name-bottom').className = 'clock-name' + (bottomActive ? ' active' : '');

        if (clockEnabled) {
            $('time-top').textContent = formatTime(clockTime[topColor]);
            $('time-top').className = 'clock-time' + (topActive ? ' active' : '') +
                (topActive && clockTime[topColor] < 30 ? ' low' : '');
            $('time-bottom').textContent = formatTime(clockTime[bottomColor]);
            $('time-bottom').className = 'clock-time' + (bottomActive ? ' active' : '') +
                (bottomActive && clockTime[bottomColor] < 30 ? ' low' : '');
        } else {
            $('time-top').textContent = '--:--';
            $('time-top').className = 'clock-time';
            $('time-bottom').textContent = '--:--';
            $('time-bottom').className = 'clock-time';
        }
    }

    function formatTime(secs) {
        if (secs >= 99999) return '--:--';
        const m = Math.floor(Math.max(0, secs) / 60);
        const s = Math.floor(Math.max(0, secs)) % 60;
        return (m < 10 ? '0' : '') + m + ':' + (s < 10 ? '0' : '') + s;
    }

    function startClock() {
        clockRunning = true;
        clockLastTick = Date.now();
        stopClock();
        clockRunning = true;
        clockInterval = setInterval(tickClock, 100);
        updateClocks();
    }

    function stopClock() {
        clockRunning = false;
        if (clockInterval) {
            clearInterval(clockInterval);
            clockInterval = null;
        }
    }

    function switchClock() {
        if (!clockEnabled) {
            updateClocks();
            return;
        }
        const now = Date.now();
        const prevTurn = game.turn() === 'w' ? 'b' : 'w';
        clockTime[prevTurn] -= (now - clockLastTick) / 1000;
        if (clockTime[prevTurn] < 0) clockTime[prevTurn] = 0;
        clockLastTick = now;
        updateClocks();
    }

    function tickClock() {
        if (!clockRunning || !clockEnabled || gameOver) return;
        const now = Date.now();
        const activeTurn = game.turn();
        clockTime[activeTurn] -= (now - clockLastTick) / 1000;
        if (clockTime[activeTurn] < 0) clockTime[activeTurn] = 0;
        clockLastTick = now;
        updateClocks();

        if (clockTime[activeTurn] <= 0) {
            checkGameOver();
        }
    }

    function recordResult() {
        if (resultRecorded) return;
        resultRecorded = true;
        const moves = game.history().length;

        if (gameMode === 'bot') {
            const isWhitePlayer = playerColor === 'w';
            let result;
            if (gameResult === 'draw') result = 'draw';
            else if ((gameResult === 'white_wins' && isWhitePlayer) ||
                     (gameResult === 'black_wins' && !isWhitePlayer)) result = 'win';
            else result = 'loss';

            addGameRecord('vs_bot', result, moves, 'Bot (' + botLevel + ')', botLevel);
        } else if (gameMode === 'local2p') {
            // no score recording for local 2p
        }
    }

    function addGameRecord(mode, result, moves, opponentName, botLvl) {
        const d = scores[mode];
        if (result === 'win') { d.wins++; }
        else if (result === 'loss') { d.losses++; }
        else { d.draws++; }

        scores.total_games++;
        scores.total_moves += moves;

        const oppElo = mode === 'vs_bot' ? (BOT_ELO[botLvl] || 1200) : scores.elo;
        const sc = result === 'win' ? 1 : (result === 'loss' ? 0 : 0.5);
        const expected = 1 / (1 + Math.pow(10, (oppElo - scores.elo) / 400));
        const delta = Math.round(32 * (sc - expected));
        scores.elo = Math.max(100, scores.elo + delta);

        if (result === 'win') {
            if (scores.fastest_win === null || moves < scores.fastest_win)
                scores.fastest_win = moves;
        }
        if (moves > scores.longest_game) scores.longest_game = moves;

        scores.history.unshift({
            date: new Date().toISOString().slice(0, 16).replace('T', ' '),
            opponent: opponentName,
            result: result,
            moves: moves,
            elo_change: delta
        });
        scores.history = scores.history.slice(0, 50);

        saveScores();
    }

    function loadScores() {
        try {
            const raw = localStorage.getItem('chess_master_scores');
            if (raw) {
                scores = JSON.parse(raw);
                const defaults = getDefaultScores();
                Object.keys(defaults).forEach(k => {
                    if (!(k in scores)) scores[k] = defaults[k];
                });
                return;
            }
        } catch (e) {}
        scores = getDefaultScores();
    }

    function saveScores() {
        localStorage.setItem('chess_master_scores', JSON.stringify(scores));
    }

    function resetScores() {
        const name = scores.player_name;
        scores = getDefaultScores();
        scores.player_name = name;
        saveScores();
    }

    function getDefaultScores() {
        return {
            player_name: 'Player',
            elo: 1200,
            vs_bot: { wins: 0, losses: 0, draws: 0 },
            vs_human: { wins: 0, losses: 0, draws: 0 },
            total_games: 0,
            total_moves: 0,
            fastest_win: null,
            longest_game: 0,
            history: []
        };
    }

    function updateScoresDisplay() {
        const $ = id => document.getElementById(id);
        $('scores-elo').textContent = 'ELO  ' + scores.elo;

        const bot = scores.vs_bot;
        const botTotal = bot.wins + bot.losses + bot.draws;
        $('bot-played').textContent = botTotal;
        $('bot-wins').textContent = bot.wins;
        $('bot-losses').textContent = bot.losses;
        $('bot-draws').textContent = bot.draws;
        $('bot-winrate').textContent = botTotal ? (bot.wins / botTotal * 100).toFixed(1) + '%' : '0%';
        $('bot-bar-w').style.width = botTotal ? (bot.wins / botTotal * 100) + '%' : '0%';
        $('bot-bar-l').style.width = botTotal ? (bot.losses / botTotal * 100) + '%' : '0%';

        const hum = scores.vs_human;
        const humTotal = hum.wins + hum.losses + hum.draws;
        $('human-played').textContent = humTotal;
        $('human-wins').textContent = hum.wins;
        $('human-losses').textContent = hum.losses;
        $('human-draws').textContent = hum.draws;
        $('human-winrate').textContent = humTotal ? (hum.wins / humTotal * 100).toFixed(1) + '%' : '0%';
        $('human-bar-w').style.width = humTotal ? (hum.wins / humTotal * 100) + '%' : '0%';
        $('human-bar-l').style.width = humTotal ? (hum.losses / humTotal * 100) + '%' : '0%';

        $('total-games').textContent = scores.total_games;
        $('total-moves').textContent = scores.total_moves;
        $('fastest-win').textContent = scores.fastest_win !== null ? scores.fastest_win + ' moves' : '-';
        $('longest-game').textContent = scores.longest_game + ' moves';

        const body = $('history-body');
        body.innerHTML = '';
        scores.history.forEach(entry => {
            const row = document.createElement('div');
            row.className = 'history-row';

            const dateEl = document.createElement('span');
            dateEl.textContent = entry.date || '-';
            row.appendChild(dateEl);

            const oppEl = document.createElement('span');
            oppEl.textContent = entry.opponent || '-';
            row.appendChild(oppEl);

            const resEl = document.createElement('span');
            resEl.textContent = (entry.result || '?').charAt(0).toUpperCase() + (entry.result || '').slice(1);
            resEl.className = entry.result === 'win' ? 'result-win' :
                              (entry.result === 'loss' ? 'result-loss' : 'result-draw');
            row.appendChild(resEl);

            const movesEl = document.createElement('span');
            movesEl.textContent = entry.moves || '?';
            row.appendChild(movesEl);

            const eloEl = document.createElement('span');
            const d = entry.elo_change || 0;
            eloEl.textContent = (d >= 0 ? '+' : '') + d;
            eloEl.className = d >= 0 ? 'elo-pos' : 'elo-neg';
            row.appendChild(eloEl);

            body.appendChild(row);
        });
    }

    function showToast(message, bgColor) {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.style.background = bgColor || 'var(--green)';
        toast.textContent = message;
        container.appendChild(toast);
        setTimeout(() => {
            toast.classList.add('fade-out');
            setTimeout(() => toast.remove(), 300);
        }, 2200);
    }

    function createParticles(containerId, count) {
        const container = document.getElementById(containerId);
        if (!container) return;
        container.innerHTML = '';
        const colors = ['var(--accent)', 'var(--accent2)', 'var(--gold)'];
        for (let i = 0; i < count; i++) {
            const p = document.createElement('div');
            p.className = 'particle';
            const size = 4 + Math.random() * 8;
            p.style.width = size + 'px';
            p.style.height = size + 'px';
            p.style.left = Math.random() * 100 + '%';
            p.style.top = Math.random() * 100 + '%';
            p.style.background = colors[Math.floor(Math.random() * colors.length)];
            p.style.animationDuration = (8 + Math.random() * 12) + 's';
            p.style.animationDelay = (-Math.random() * 10) + 's';
            container.appendChild(p);
        }
    }

    return { init };
})();

document.addEventListener('DOMContentLoaded', App.init);
