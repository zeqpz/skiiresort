"""Falcos win evaluation: clusters paid through the cell-multiplier grid and MAX cells."""

from src.executables.executables import Executables
from game_config import PAYING

PAYING_SET = frozenset(PAYING)


class GameCalculations(Executables):
    """Cluster evaluation with per-cell multipliers."""

    def find_clusters(self) -> list:
        """Every group of 5+ identical paying symbols joined up/down/left/right, as
        (symbol, [(reel,row), ...]) with cells in reel-major order."""
        board = self.board
        R, C = self.config.num_reels, self.config.num_rows[0]
        seen = [[False] * C for _ in range(R)]
        out = []
        for r in range(R):
            for c in range(C):
                if seen[r][c]:
                    continue
                name = board[r][c].name
                seen[r][c] = True
                if name not in PAYING_SET:
                    continue
                stack, cells = [(r, c)], []
                while stack:
                    x, y = stack.pop()
                    cells.append((x, y))
                    for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                        if 0 <= nx < R and 0 <= ny < C and not seen[nx][ny] and board[nx][ny].name == name:
                            seen[nx][ny] = True
                            stack.append((nx, ny))
                if len(cells) >= 5:
                    out.append((name, sorted(cells)))
        return out

    def evaluate_falcos_wins(self) -> None:
        """Pay every cluster on the board through the cells it covers.

        Multiplier = SUM of the cluster's cell multipliers that are at x2 or more; x1 when none
        are. A cluster covering a MAX cell (FULL TANK) pays the max win: its win is whatever is
        left to reach the cap. The board's total is trimmed so the round never pays more than the
        cap - the trimmed amounts are what the events carry, so the client never re-derives.
        """
        wins = []
        total = 0.0
        has_max = False
        for sym, cells in self.find_clusters():
            size = len(cells)
            pay = self.config.paytable[(size, sym)]
            cell_mults = [int(self.grid_mults[r][c]) for r, c in cells]
            boosted = [m for m in cell_mults if m >= 2]
            mult = sum(boosted) if boosted else 1
            touches_max = any((r, c) in self.max_cells for r, c in cells)
            win = round(pay * mult, 2)
            meta = {"clusterSize": size, "winWithoutMult": pay, "multiplier": mult, "cellMults": cell_mults}
            if touches_max:
                meta["maxWin"] = True
                has_max = True
            wins.append({
                "symbol": sym, "kind": size, "win": win,
                "positions": [{"reel": r, "row": c} for r, c in cells], "meta": meta,
            })
            total += win

        room = round(self.config.wincap - self.win_manager.running_bet_win, 2)
        if has_max or total > room:
            # MAX clusters (or a board that overshoots the cap) take exactly the room left:
            # ordinary clusters first at their own value, MAX clusters / overshoot absorb the rest.
            ordinary = [w for w in wins if not w["meta"].get("maxWin")]
            maxed = [w for w in wins if w["meta"].get("maxWin")]
            left = room
            for w in sorted(ordinary, key=lambda w: -w["win"]):
                w["win"] = round(min(w["win"], max(left, 0.0)), 2)
                left = round(left - w["win"], 2)
            for i, w in enumerate(maxed):
                w["win"] = round(max(left, 0.0), 2) if i == 0 else 0.0
                left = round(left - w["win"], 2)
            total = round(sum(w["win"] for w in wins), 2)

        self.win_data = {"totalWin": round(total, 2), "wins": wins}
