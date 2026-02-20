import json
import os
import time
from constants import SCORES_FILE

_DEFAULT = {
    "player_name": "Player",
    "elo": 1200,
    "vs_bot": {"wins": 0, "losses": 0, "draws": 0},
    "vs_human": {"wins": 0, "losses": 0, "draws": 0},
    "total_games": 0,
    "total_moves": 0,
    "fastest_win_moves": None,
    "longest_game_moves": 0,
    "history": []
}

def _load() -> dict:
    if os.path.exists(SCORES_FILE):
        try:
            with open(SCORES_FILE, "r") as f:
                data = json.load(f)
            for k, v in _DEFAULT.items():
                if k not in data:
                    data[k] = v
            return data
        except Exception:
            pass
    return dict(_DEFAULT)

def _save(data: dict):
    with open(SCORES_FILE, "w") as f:
        json.dump(data, f, indent=2)

def _elo_change(my_elo: int, opp_elo: int, result: float, k: int = 32) -> int:
    expected = 1 / (1 + 10 ** ((opp_elo - my_elo) / 400))
    return round(k * (result - expected))

BOT_ELO = {
    "Novice": 600, "Easy": 900, "Medium": 1200,
    "Hard": 1500, "Expert": 1800, "Master": 2200,
}

class ScoreCard:
    def __init__(self):
        self.data = _load()

    @property
    def player_name(self) -> str:
        return self.data.get("player_name", "Player")

    @property
    def elo(self) -> int:
        return self.data.get("elo", 1200)

    @property
    def vs_bot(self) -> dict:
        return self.data["vs_bot"]

    @property
    def vs_human(self) -> dict:
        return self.data["vs_human"]

    @property
    def history(self) -> list:
        return self.data["history"]

    def win_rate(self, mode: str = "vs_bot") -> float:
        d = self.data[mode]
        total = d["wins"] + d["losses"] + d["draws"]
        return (d["wins"] / total * 100) if total else 0.0

    def set_name(self, name: str):
        self.data["player_name"] = name.strip() or "Player"
        _save(self.data)

    def record_game(self, mode: str, result: str, moves: int,
                    opponent_name: str = "Bot", bot_level: str = None):
        d = self.data[mode]
        if result == "win":
            d["wins"] += 1
            score = 1.0
        elif result == "loss":
            d["losses"] += 1
            score = 0.0
        else:
            d["draws"] += 1
            score = 0.5

        self.data["total_games"] += 1
        self.data["total_moves"] += moves

        opp_elo = BOT_ELO.get(bot_level, 1200) if mode == "vs_bot" else self.elo
        delta = _elo_change(self.elo, opp_elo, score)
        self.data["elo"] = max(100, self.elo + delta)

        if result == "win":
            if self.data["fastest_win_moves"] is None or moves < self.data["fastest_win_moves"]:
                self.data["fastest_win_moves"] = moves
        if moves > self.data["longest_game_moves"]:
            self.data["longest_game_moves"] = moves

        self.data["history"].insert(0, {
            "date": time.strftime("%Y-%m-%d %H:%M"),
            "opponent": opponent_name,
            "result": result,
            "moves": moves,
            "elo_change": delta,
        })
        self.data["history"] = self.data["history"][:50]

        _save(self.data)

    def reset(self):
        name = self.data.get("player_name", "Player")
        self.data = dict(_DEFAULT)
        self.data["player_name"] = name
        _save(self.data)

