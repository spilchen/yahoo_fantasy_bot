#!/bin/python

from yahoo_fantasy_bot import bot


class Driver(object):
    """
    Driver to do automated actions with the bot.

    :param cfg: ConfigParser read in
    :param dry_run: True if no writes to the Yahoo APIs
    :param full: True if we are to optimize using the free agents.  False means
        we just optimize for our bench.
    :param prompt: True if we are to prompt for each roster move.  False means
        we answer yes for each prompt.
    :param reset_cache: True if the cache files should be removed before running
    """
    def __init__(self, cfg, dry_run, full, prompt, reset_cache):
        self.bot = bot.ManagerBot(cfg, reset_cache)
        self.dry_run = dry_run
        self.full = full
        self.prompt = prompt

    def run(self):
        print("Evaluating trades")
        self.bot.evaluate_trades(dry_run=self.dry_run, verbose=True,
                                 prompt=self.prompt)
        print("Adjusting lineup for player status")
        self.bot.pick_injury_reserve()
        self.bot.move_non_available_players()
        self.bot.move_recovered_il_to_bench()
        if self.full:
            print("Optimizing full lineup using available free agents")
            self.bot.optimize_lineup_from_free_agents()
        else:
            print("Optimizing open lineup spots using available free agents")
            self.bot.fill_empty_spots_from_bench()
            self.bot.fill_empty_spots()
            print("Optimizing lineup using players available from bench")
            self.bot.pick_bench()
            self.bot.optimize_lineup_from_bench()
        self.bot.pick_bench()
        print("Optimized lineup")
        self.bot.print_roster()
        print("Computing roster moves to apply")
        self.bot.apply_roster_moves(dry_run=self.dry_run, prompt=self.prompt)
