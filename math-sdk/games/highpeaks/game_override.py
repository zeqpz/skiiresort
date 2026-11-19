"""Falcos state resets and acceptance criteria."""

from game_executables import GameExecutables


class GameStateOverride(GameExecutables):
    """Overrides and extensions of the universal state.py functions."""

    def reset_book(self):
        super().reset_book()
        if not hasattr(self, "stats"):
            self.stats = {}
        self.bonus_kind = None
        self.forced_grades = {}          # id(pump symbol) -> grade key for a planted pump
        self.max_cells = set()           # FULL TANK MAX cells live on this spin / bonus
        self.fill_board = {}
        self.tumble_explode_positions = None
        self.set_grid(1)                 # base game: every cell starts each spin at x1

    def assign_special_sym_function(self):
        self.special_symbol_functions = {}

    def record_bigwin(self):
        """Force record for the optimiser's big-win fence (config.bigwin_threshold): a round that
        reaches the mode's threshold but not the max win."""
        t = self.config.bigwin_threshold.get(self.betmode)
        if t is not None and t <= self.final_win < self.config.wincap:
            self.record({"symbol": "bigwin"})
        h = self.config.highwin_threshold.get(self.betmode)
        if h is not None and h <= self.final_win < t:
            self.record({"symbol": "highwin"})

    def check_repeat(self):
        """Resimulate when the outcome does not satisfy the assigned criteria:
            * win_criteria (wincap 50,000x / "0" = no win) must match exactly;
            * the bonus played must be the one the criteria asked for (None = no bonus);
            * every other criteria must pay something (unless it sets require_win False).
        """
        if self.repeat is False:
            dist = self.get_current_betmode_distributions()
            conds = self.get_current_distribution_conditions()
            win_criteria = dist.get_win_criteria()
            if win_criteria is not None and self.final_win != win_criteria:
                self.repeat = True
            want = conds.get("bonus")
            if want != "any" and self.bonus_kind != want:
                self.repeat = True
            if win_criteria is None and conds.get("require_win", True) and self.final_win <= 0:
                self.repeat = True
        self.repeat_count += 1
        self.check_current_repeat_count()
