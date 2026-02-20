import sys
import pygame
from constants import WINDOW_W, WINDOW_H, FPS, C_BG
from scorecard import ScoreCard
from screens import (MainMenu, BotSetupScreen, GameScreen,
                     MultiplayerScreen, ScoreScreen)

def run():
    pygame.init()
    pygame.display.set_caption("Chess Master")
    pygame.display.set_icon(
        pygame.Surface((32, 32))
    )

    try:
        icon = pygame.Surface((32, 32), pygame.SRCALPHA)
        icon.fill((0, 0, 0, 0))
        font = pygame.font.SysFont("Segoe UI", 26, bold=True)
        ts = font.render("♟", True, (88, 166, 255))
        icon.blit(ts, ts.get_rect(center=(16, 16)))
        pygame.display.set_icon(icon)
    except Exception:
        pass

    screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
    clock  = pygame.time.Clock()

    scorecard = ScoreCard()

    current_screen = MainMenu(screen, scorecard)
    state = "menu"

    running = True
    while running:
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                running = False
                break
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                pygame.display.toggle_fullscreen()

        if not running:
            break

        current_screen.handle_events(events)
        current_screen.draw()

        if hasattr(current_screen, "next") and current_screen.next:
            target, payload = current_screen.next
            current_screen.next = None

            if target == "quit":
                running = False

            elif target == "menu":
                current_screen = MainMenu(screen, scorecard)
                state = "menu"

            elif target == "bot_setup":
                current_screen = BotSetupScreen(screen, scorecard)
                state = "bot_setup"

            elif target == "bot_game":
                current_screen = GameScreen(
                    screen, scorecard,
                    mode="bot", config=payload
                )
                state = "bot_game"

            elif target == "local2p":
                current_screen = GameScreen(
                    screen, scorecard,
                    mode="local2p", config={}
                )
                state = "local2p"

            elif target == "multiplayer":
                current_screen = MultiplayerScreen(screen, scorecard)
                state = "multiplayer"

            elif target == "online_game":
                client    = payload.get("client")
                my_color  = payload.get("my_color", "white")
                opp_name  = payload.get("opponent_name", "Opponent")
                current_screen = GameScreen(
                    screen, scorecard,
                    mode="online",
                    config={
                        "my_color": my_color,
                        "opponent_name": opp_name,
                        "time": 0,
                    },
                    net_client=client
                )
                state = "online_game"

            elif target == "scorecard":
                current_screen = ScoreScreen(screen, scorecard)
                state = "scorecard"

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit(0)

if __name__ == "__main__":
    run()

