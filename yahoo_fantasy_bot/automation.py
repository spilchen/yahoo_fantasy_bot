#!/bin/python

import random
from yahoo_fantasy_bot import bot


class Driver(object):
    """
    Driver to do automated actions with the bot.

    :param cfg: ConfigParser read in
    """
    def __init__(self, cfg, dry_run, full_prob):
        self.bot = bot.ManagerBot(cfg)
        self.dry_run = dry_run
        self.full_prob = full_prob

    def run(self):
        self.bot.sync_lineup()
        print("Evaluating trades")
        self.bot.evaluate_trades(dry_run=self.dry_run, verbose=True)
        print("Adjusting lineup for player status")
        self.bot.pick_injury_reserve()
        self.bot.move_non_available_players()
        if self._do_full_lineup_overhaul():
            print("Optimizing full lineup using available free agents")
            self.bot.optimize_lineup_from_free_agents()
            self.bot.pick_bench()
        else:
            print("Optimizing open lineup spots using available free agents")
            self.bot.fill_empty_spots_from_bench()
            self.bot.fill_empty_spots()
            print("Optimizing lineup using players available from bench")
            self.bot.pick_bench()
            self.bot.optimize_lineup_from_bench()
        print("Optimized lineup")
        self.bot.print_roster()
        print("Computing roster moves to apply")
        self.bot.apply_roster_moves(dry_run=self.dry_run)

    def _do_full_lineup_overhaul(self):
        return random.randint(0, 100) <= int(self.full_prob)
