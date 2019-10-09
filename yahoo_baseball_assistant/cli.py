#!/bin/python

from yahoo_baseball_assistant import bot


class Driver:
    """
    Driver for the CLI program.  Displays menus and prompts for actions.

    :param cfg: ConfigParser read in
    """
    def __init__(self, cfg):
        self.bot = bot.ManagerBot(cfg)

    def run(self):
        menu_opts = {"P": self._pick_opponent,
                     "R": self._print_roster,
                     "S": self._show_score,
                     "A": self._auto_select_players,
                     "M": self._manual_select_players,
                     "T": self._show_two_start_pitchers,
                     "L": self._list_players,
                     "B": self._manage_blacklist,
                     "Y": self._apply_roster_moves}

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
        print("A - Auto select players")
        print("M - Manual select players")
        print("T - Show two start pitchers")
        print("L - List players")
        print("B - Blacklist players")
        print("Y - Apply roster moves")
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

    def _print_roster(self):
        self.bot.print_roster()

    def _show_score(self):
        self.bot.show_score()

    def _auto_select_players(self):
        print("")
        print("Number of iterations: ")
        try:
            num_iters = int(input())
        except ValueError:
            print("*** input a valid number")
            return
        print("Stat categories to rank (delimited with comma):")
        categories_combined = input()
        categories = categories_combined.rstrip().split(",")
        print(categories)

        try:
            self.bot.auto_select_players(num_iters, categories)
        except KeyError as e:
            print(e)

    def _manual_select_players(self):
        self.bot.print_roster()
        self.bot.show_score()
        score_comparer = bot.ScoreComparer(self.bot.scorer, self.bot.opp_sum,
                                           self.bot.lineup)
        print("Enter the name of the player to remove: ")
        pname_rem = input().rstrip()
        print("Enter the name of the player to add: ")
        pname_add = input().rstrip()

        try:
            self.bot.swap_player(pname_rem, pname_add)
        except (LookupError, ValueError) as e:
            print(e)
            return

        self.bot.print_roster()
        self.bot.show_score()
        improved = score_comparer.compare_lineup(self.bot.lineup)
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
