"""Handles the state and output for a single Falcos simulation round."""

from game_override import GameStateOverride


class GameState(GameStateOverride):
    """Entry point for every bet mode.

    base / chance : a base spin (cells reset to x1), then FILL UP / PREMIUM / MIDNIGHT RUN if the
                    board it ends on shows the scatters.
    fillup        : the FILL UP collection game, bought (no base spin).
    premium       : PREMIUM's 10 sticky free spins, bought (no base spin).
    nitro         : one base spin with every cell preloaded x16..x2048; cannot trigger a bonus.
    midnight      : MIDNIGHT RUN's 10 sticky free spins from x4, bought (no base spin).
    """

    def run_spin(self, sim, simulation_seed=None):
        self.reset_seed(sim, simulation_seed)
        self.repeat = True
        while self.repeat:
            self.reset_book()
            conds = self.get_current_distribution_conditions()
            buy = conds.get("buy")
            if buy:
                self.run_bonus(buy, [], "DS" if buy == "midnight" else "BS", 0, bought=True)
            else:
                if "nitro_cells" in conds:
                    self.preload_nitro()
                self.run_board_spin()
                trigger = None if self.wincap_triggered else self.check_bonus_trigger()
                if trigger is not None:
                    kind, positions, symbol, count = trigger
                    if conds.get("bonus") in (kind, "any"):
                        self.run_bonus(kind, positions, symbol, count, bought=False)
                    else:
                        self.repeat = True
            self.evaluate_finalwin()
            self.record_bigwin()
            self.check_repeat()
        self.imprint_wins()

    def run_freespin(self):
        """PREMIUM / MIDNIGHT RUN loop (see GameExecutables.run_freespin)."""
        return super().run_freespin()
