# Chess Master

A feature-rich chess game built with Python and Pygame. Play against an AI bot, a friend locally, or online via multiplayer.

## Features

- **Play vs Bot** — 6 difficulty levels (Novice to Master) with adjustable time controls
- **Local 2-Player** — Play against a friend on the same computer
- **Online Multiplayer** — Create or join a room using a simple room code(STILL IN DEVELOPMENT MODE)
- **ELO Rating** — Persistent score tracking with ELO system
- **Move History** — Full algebraic notation move log
- **Animated Pieces** — Smooth move animations and piece highlighting
- **Pawn Promotion** — Interactive promotion dialog
- **Chat** — In-game chat for online matches

## Requirements

- Python 3.10+

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/Chess.git
   cd Chess
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the game**
   ```bash
   python main.py
   ```

Chess piece images are downloaded automatically on first launch.

## How to Play

### vs Bot
1. Launch the game and enter your name
2. Click **Play vs Bot**
3. Choose difficulty, time control, and your color
4. Click **Start Game**

### Local 2-Player
1. Click **Local 2-Player**
2. Players take turns on the same screen

### Online Multiplayer
1. Click **Multiplayer (Online)**
2. **Host:** Click **Create Room** — share the displayed room code with your friend
3. **Join:** Enter the room code and click **Join Room**
4. Both players must be on the same network

## Controls

| Action | Control |
|---|---|
| Select/move piece | Left click |
| Deselect piece | Escape / click empty square |
| Toggle fullscreen | F11 |
| Resign | Resign button |
| Offer draw | Draw button |

## Project Structure

```
main.py             Entry point and screen manager
constants.py        Window size, colors, bot levels, paths
screens.py          All game screens (menu, setup, game, multiplayer, scores)
board_renderer.py   Chess board drawing and animation
bot.py              AI engine (minimax + alpha-beta pruning)
network.py          Socket-based multiplayer server and client
assets.py           Chess piece image loading
ui.py               Reusable UI components (buttons, panels, inputs)
scorecard.py        ELO tracking and score persistence
scores.json         Saved player data
requirements.txt    Python dependencies
web/                Web version (deployable to Vercel)
```

## Web Version (Vercel Deployment)

A standalone web version is included in the `web/` directory. It supports **Play vs Bot** and **Local 2-Player** modes with the same UI, ELO tracking, and AI engine — no server required.

### Deploy to Vercel

1. **Push this repo to GitHub** (or any Git provider Vercel supports)

2. **Import in Vercel**
   - Go to [vercel.com](https://vercel.com) → **Add New Project**
   - Import your repository

3. **Configure**
   - **Root Directory**: set to `web`
   - **Framework Preset**: select `Other`
   - Leave Build Command and Output Directory empty

4. **Deploy** — click Deploy and your chess game will be live

### Run Locally

```bash
cd web
npx serve .
```

Or open `web/index.html` directly in a browser.

## License

This project uses chess piece images from [chessboardjs](https://github.com/oakmac/chessboardjs) (MIT License).
