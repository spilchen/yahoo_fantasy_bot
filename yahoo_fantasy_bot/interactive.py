#!/bin/python

from yahoo_fantasy_bot import bot


class Driver:
    """
    Interactive driver for the program. Displays menus and prompts for actions.

    :param cfg: ConfigParser read in
    """
    def __init__(self, cfg):
        self.bot = bot.ManagerBot(cfg)

    def run(self):
        menu_opts = {"P": self._pick_opponent,
                     "R": self._print_roster,
                     "S": self._show_score,
                     "F": self._fill_empty_roster_spots,
                     "O": self._optimize_lineup_from_fa,
                     "N": self._optimize_lineup_from_bench,
                     "I": self._sync_lineup_with_yahoo,
                     "M": self._manual_select_players,
                     "T": self._show_two_start_pitchers,
                     "L": self._list_players,
                     "B": self._manage_blacklist,
                     "Y": self._apply_roster_moves,
                     "V": self._evaluate_trades}

        while True:
            self._print_main_menu()
            opt = input().upper()

            if opt in menu_opts:
                menu_opts[opt]()
            elif opt == "X":
                break
            else:
                print("Unknown option: {}".format(opt))
        self.bot.save()

    def _print_main_menu(self):
        print("")
        print("")
        print("Main Menu")
        print("=========")
        print("P - Pick opponent")
        print("R - Show roster")
        print("S - Show sumarized scores")
        print("F - Fill empty roster spots")
        print("O - Optimize lineup from free agents")
        print("N - Optimize lineup from bench")
        print("I - Reinit local lineup with Yahoo!")
        print("M - Manual select players")
        print("T - Show two start pitchers")
        print("L - List players")
        print("B - Blacklist players")
        print("Y - Apply roster moves")
        print("V - Evaluate trades")
        print("X - Exit")
        print("")
        print("Pick a selection:")

    def _pick_opponent(self):
        print("")
        print("Available teams")
        self._list_teams(self.bot.lg)
        print("")
        print("Enter team key of new opponent (or X to quit): ")
        opp_team_key = input()

        if opp_team_key != 'X':
            self.bot.pick_opponent(opp_team_key)

    def _list_teams(self, lg):
        for team in lg.teams():
            print("{:30} {:15}".format(team['name'], team['team_key']))

    def _apply_roster_moves(self):
        self.bot.apply_roster_moves(dry_run=True)
        print("")
        print("Type 'yes' to apply the roster moves:")
        proceed = input()
        if proceed == 'yes':
            self.bot.apply_roster_moves(dry_run=False)

    def _evaluate_trades(self):
        num_trades = self.bot.evaluate_trades(dry_run=True, verbose=True)
        if num_trades > 0:
            print("Type 'yes' to accept these evaluations:")
            proceed = input()
            if proceed == 'yes':
                self.bot.evaluate_trades(dry_run=False, verbose=False)
        else:
            print("No trade offers")

    def _print_roster(self):
        self.bot.print_roster()

    def _show_score(self):
        self.bot.show_score()

    def _fill_empty_roster_spots(self):
        self.bot.pick_injury_reserve()
        self.bot.move_non_available_players()
        self.bot.fill_empty_spots_from_bench()
        self.bot.fill_empty_spots()
        self.bot.pick_bench()

    def _optimize_lineup_from_fa(self):
        try:
            if self.bot.optimize_lineup_from_free_agents():
                self.bot.pick_bench()
                self.bot.print_roster()
        except KeyError as e:
            print(e)

    def _optimize_lineup_from_bench(self):
        self.bot.optimize_lineup_from_bench()

    def _sync_lineup_with_yahoo(self):
        self.bot.sync_lineup()

    def _manual_select_players(self):
        self.bot.print_roster()
        self.bot.show_score()
        df = pd.DataFrame(data=self.bot.lineup)
        score_sum = self.bot.scorer.summarize(df)
        old_score = self.bot.score_comparer.compute_score(score_sum)
        print("Enter the name of the player to remove: ")
        pname_rem = input().rstrip()
        print("Enter the name of the player to add (leave blank for none): ")
        pname_add = input().rstrip()

        try:
            self.bot.swap_player(pname_rem,
                                 pname_add if len(pname_add) > 0 else None)
        except (LookupError, ValueError) as e:
            print(e)
            return

        self.bot.print_roster()
        if pname_add:
            self.bot.show_score()
            df = pd.DataFrame(data=self.bot.lineup)
            score_sum = self.bot.scorer.summarize(df)
            new_score = self.bot.score_comparer.compute_score(score_sum)
            improved = new_score > old_score
            print("This lineup has {}".format("improved" if improved
                                              else "declined"))

    def _show_two_start_pitchers(self):
        if "WK_GS" in self.bot.ppool.columns:
            two_starters = self.bot.ppool[self.bot.ppool.WK_GS > 1]
            for plyr in two_starters.iterrows():
                print(plyr[1]['name'])
        else:
            print("WK_GS is not a category in the player pool")

    def _list_players(self):
        print("Enter position: ")
        pos = input()
        print("")
        self.bot.list_players(pos)

    def _manage_blacklist(self):
        while True:
            self._print_blacklist_menu()
            sel = input()

            if sel == "L":
                print("Contents of blacklist:")
                for p in self.bot.get_blacklist():
                    print(p)
            elif sel == "A":
                print("Enter player name to add: ")
                name = input()
                self.bot.add_to_blacklist(name)
            elif sel == "D":
                print("Enter player name to delete: ")
                name = input()
                if not self.bot.remove_from_blacklist(name):
                    print("Name not found in black list: {}".format(name))
            elif sel == "X":
                break
            else:
                print("Unknown option: {}".format(sel))

    def _print_blacklist_menu(self):
        print("")
        print("Blacklist Menu")
        print("==============")
        print("L - List players on black list")
        print("A - Add player to black list")
        print("D - Delete player from black list")
        print("X - Exit and return to previous menu")
        print("")
        print("Pick a selection: ")
