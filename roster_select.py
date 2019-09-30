#!/bin/python

"""Command line interface to select a roster against an opponent

Usage:
  roster_select.py <cfg_file>

  <cfg_file>  The name of the configuration file.  See sample_config.ini for
              the sample format.
"""
from docopt import docopt
from yahoo_oauth import OAuth2
import yahoo_fantasy_api as yfa
from yahoo_baseball_assistant import roster
import logging
import pickle
import os
import pandas as pd
import numpy as np
import configparser
import importlib


logging.basicConfig(
    filename='roster_select.log',
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d %(module)s - %(funcName)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger()
pd.options.mode.chained_assignment = None  # default='warn'


def print_main_menu():
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
    print("X - Exit")
    print("")
    print("Pick a selection:")


def is_new_score_better(orig_w, orig_l, new_w, new_l):
    if orig_w + orig_l > 0:
        orig_pct = orig_w / (orig_w + orig_l)
    else:
        orig_pct = 0.5

    if new_w + new_l > 0:
        new_pct = new_w / (new_w + new_l)
    else:
        new_pct = 0.5

    return orig_pct < new_pct


def copy_roster(roster):
    new_roster = []
    for plyr in roster:
        new_roster.append(plyr.copy())
    return new_roster


def show_two_start_pitchers(my_df):
    two_starters = my_df[my_df.WK_GS > 1]
    for plyr in two_starters.iterrows():
        print(plyr[1]['name'])


def manual_select_players(ppool, lineup, opp_team_name, opp_sum, bot):
    if opp_sum is None:
        print("Must pick an opponent")
        return

    bot.print_roster(lineup)
    bot.show_score(lineup, opp_team_name, opp_sum)
    print("Enter the name of the player to remove: ")
    pname_rem = input().rstrip()
    print("Enter the name of the player to add: ")
    pname_add = input().rstrip()

    plyr_del = None
    for del_idx, p in enumerate(lineup):
        if p['name'] == pname_rem:
            plyr_del = p
            break
    if plyr_del is None:
        print("Could not find player in your lineup: {}".format(pname_rem))
        return

    plyr_add_df = ppool[ppool['name'] == pname_add]
    if(len(plyr_add_df.index) == 0):
        print("Could not find player in pool: {}".format(pname_add))
        return
    if(len(plyr_add_df.index) > 1):
        print("Found more than one player!: {}".format(pname_add))
        return

    plyr_add = plyr_add_df.iloc(0)[0]

    assert(type(plyr_del.selected_position) == str)
    if plyr_del.selected_position not in plyr_add['eligible_positions']:
        print("Position {} is not a valid position for {}: {}".format(
            plyr_del.selected_position,
            plyr_add['name'],
            plyr_add['eligible_positions']))
        return

    plyr_add['selected_position'] = plyr_del['selected_position']
    plyr_del['selected_position'] = np.nan
    lineup.append(plyr_add)
    del lineup[del_idx]

    bot.print_roster(lineup)
    bot.show_score(lineup, opp_team_name, opp_sum)


def print_blacklist_menu():
    print("")
    print("Blacklist Menu")
    print("==============")
    print("L - List players on black list")
    print("A - Add player to black list")
    print("D - Delete player from black list")
    print("X - Exit and return to previous menu")
    print("")
    print("Pick a selection: ")


def manage_blacklist(bot):
    while True:
        print_blacklist_menu()
        sel = input()

        if sel == "L":
            print("Contents of blacklist:")
            for p in bot.get_blacklist():
                print(p)
        elif sel == "A":
            print("Enter player name to add: ")
            name = input()
            bot.add_to_blacklist(name)
        elif sel == "D":
            print("Enter player name to delete: ")
            name = input()
            if not bot.remove_from_blacklist(name):
                print("Name not found in black list: {}".format(name))
        elif sel == "X":
            break
        else:
            print("Unknown option: {}".format(sel))


def list_players(ppool, bot):
    print("Enter position: ")
    pos = input()
    print("")
    bot.list_players(pos, ppool)


def list_teams(lg):
    for team in lg.teams():
        print("{:30} {:15}".format(team['name'], team['team_key']))


def get_team_name(lg, team_key):
    for team in lg.teams():
        if team['team_key'] == team_key:
            return team['name']
    raise LookupError("Could not find team for team key: {}".format(team_key))


def pick_opponent(bot):
    print("")
    print("Available teams")
    list_teams(bot.lg)
    print("")
    print("Enter team key of new opponent (or X to quit): ")
    opp_team_key = input()

    if opp_team_key == 'X':
        return (None, None)
    else:
        return bot.sum_opponent(opp_team_key)


class ManagerBot:
    """A class that encapsulates an automated Yahoo! fantasy manager.
    """
    def __init__(self, cfg):
        self.cfg = cfg
        self.sc = OAuth2(None, None, from_file=cfg['Connection']['oauthFile'])
        self.lg = yfa.League(self.sc, cfg['League']['id'])
        self.pred_bldr = None
        self.my_team_bldr = self._construct_roster_builder()
        self.ppool = None
        Scorer = self._get_scorer_class()
        self.scorer = Scorer(self.cfg)
        Display = self._get_display_class()
        self.display = Display(self.cfg)
        self.blacklist = self._load_blacklist()

    def cache_dir(self):
        dir = self.cfg['Cache']['dir']
        if not os.path.isdir(dir):
            os.mkdir(dir)
        return dir

    def roster_cache_file(self):
        dir = self.cache_dir()
        return "{}/my_roster.pkl".format(dir)

    def player_pool_cache_file(self):
        dir = self.cache_dir()
        return "{}/ppool.pkl".format(dir)

    def _blacklist_cache_file(self):
        dir = self.cache_dir()
        return "{}/blacklist.pkl".format(dir)

    def _load_blacklist(self):
        fn = self._blacklist_cache_file()
        if os.path.exists(fn):
            with open(fn, "rb") as f:
                blacklist = pickle.load(f)
        else:
            blacklist = []
        return blacklist

    def _save_blacklist(self):
        fn = self._blacklist_cache_file()
        with open(fn, "wb") as f:
            pickle.dump(self.blacklist, f)

    def add_to_blacklist(self, plyr_name):
        self.blacklist.append(plyr_name)
        self._save_blacklist()

    def remove_from_blacklist(self, plyr_name):
        if plyr_name not in self.blacklist:
            return False
        else:
            self.blacklist.remove(plyr_name)
            self._save_blacklist()
            return True

    def get_blacklist(self):
        return self.blacklist

    def init_prediction_builder(self):
        """Will load and return the prediction builder"""
        module = self._get_prediction_module()
        loader = getattr(module, self.cfg['Prediction']['builderClassLoader'])
        self.pred_bldr = loader(self.lg, self.cfg)
        return self.pred_bldr

    def save(self):
        with open(self.roster_cache_file(), "wb") as f:
            pickle.dump(my_roster, f)
        self.save_prediction_builder()

    def save_prediction_builder(self):
        """Save the contents of the prediction builder to disk"""
        if self.pred_bldr is None:
            raise RuntimeError("No prediction builder to save!")
        module = self._get_prediction_module()
        saver = getattr(module, self.cfg['Prediction']['builderClassSaver'])
        saver(self.pred_bldr, self.cfg)

    def fetch_player_pool(self):
        """Build the roster pool of players"""
        if self.ppool is None:
            if os.path.exists(self.player_pool_cache_file()):
                with open(self.player_pool_cache_file(), "rb") as f:
                    self.ppool = pickle.load(f)
            else:
                all_mine = self.lg.to_team(self.lg.team_key()).roster(
                    self.lg.current_week() + 1)
                for p in all_mine:
                    if p['selected_position'] == 'BN':
                        p['selected_position'] = np.nan
                logger.info("Fetching free agents")
                plyr_pool = self.lg.free_agents(None) + all_mine
                logger.info("Free agents fetch complete.  {} players in pool"
                            .format(len(plyr_pool)))

                rcont = roster.Container(None, None)
                rcont.add_players(plyr_pool)
                self.ppool = self.pred_bldr.predict(
                    rcont, *self.cfg['PredictionNamedArguments'])

                with open(self.player_pool_cache_file(), "wb") as f:
                    pickle.dump(self.ppool, f)
        return self.ppool

    def sum_opponent(self, opp_team_key):
        # Build up the predicted score of the opponent
        try:
            team_name = get_team_name(self.lg, opp_team_key)
        except LookupError:
            print("Not a valid team: {}:".format(opp_team_key))
            return(None, None)

        opp_team = roster.Container(self.lg, self.lg.to_team(opp_team_key))
        opp_df = self.pred_bldr.predict(opp_team,
                                        *self.cfg['PredictionNamedArguments'])
        opp_sum = self.scorer.summarize(opp_df)
        return (team_name, opp_sum)

    def load_roster(self):
        if os.path.exists(self.roster_cache_file()):
            with open(self.roster_cache_file(), "rb") as f:
                my_roster = pickle.load(f)
        else:
            my_roster = []
            stat_categories = self.lg.stat_categories()
            for pos_type in self._get_position_types():
                stats = []
                for sc in stat_categories:
                    if sc['position_type'] == pos_type and \
                            self._is_predicted_stat(sc['display_name']):
                        stats.append(sc['display_name'])
                self.initial_fit(stats, my_roster, pos_type)
        return my_roster

    def initial_fit(self, categories, my_roster, pos_type):
        selector = roster.PlayerSelector(self.ppool)
        selector.rank(categories)
        for plyr in selector.select():
            try:
                if plyr['name'] in self.blacklist:
                    continue
                if plyr['position_type'] != pos_type:
                    continue

                print("Player: {} Positions: {}".
                      format(plyr['name'], plyr['eligible_positions']))

                plyr['selected_position'] = np.nan
                my_roster = self.my_team_bldr.fit_if_space(my_roster, plyr)
            except LookupError:
                pass
            if len(my_roster) == self.my_team_bldr.max_players():
                break
        return my_roster

    def print_roster(self, lineup):
        self.display.printRoster(lineup)

    def auto_select_players(self, ppool, lineup, opp_sum):
        if opp_sum is None:
            print("Must pick an opponent")
            return lineup

        print("")
        print("Number of iterations: ")
        try:
            num_iters = int(input())
        except ValueError:
            print("*** input a valid number")
            return lineup
        print("Stat categories to rank (delimited with comma):")
        categories_combined = input()
        categories = categories_combined.rstrip().split(",")
        print(categories)

        # Filter out any players from the lineup as we don't want to consider
        # them again.
        indexColumn = self.cfg['Prediction']['indexColumn']
        lineup_ids = [e[indexColumn] for e in lineup]
        avail_plyrs = ppool[~ppool[indexColumn].isin(lineup_ids)]
        selector = roster.PlayerSelector(avail_plyrs)
        try:
            selector.rank(categories)
        except KeyError:
            print("Categories are not valid: {}".format(categories))
            return lineup

        (orig_w, orig_l, _) = self.compute_score(lineup, opp_sum)
        for i, plyr in enumerate(selector.select()):
            if i+1 > num_iters:
                break
            if plyr['name'] in self.blacklist:
                continue

            print("Player: {} Positions: {}".
                  format(plyr['name'], plyr['eligible_positions']))

            plyr['selected_position'] = np.nan
            best_lineup = copy_roster(lineup)
            for potential_lineup in self.my_team_bldr.enumerate_fit(lineup,
                                                                    plyr):
                (new_w, new_l, _) = self.compute_score(potential_lineup,
                                                       opp_sum)
                if is_new_score_better(orig_w, orig_l, new_w, new_l):
                    best_lineup = copy_roster(potential_lineup)
                    (orig_w, orig_l) = (new_w, new_l)
                    print("  *** Found better lineup")
                    self.print_roster(best_lineup)
            lineup = copy_roster(best_lineup)
        return lineup

    def compute_score(self, lineup, opp_sum):
        df = pd.DataFrame(data=lineup, columns=lineup[0].index)
        my_sum = self.scorer.summarize(df)
        (w, l) = self.compare_scores(my_sum, opp_sum)
        return (w, l, my_sum)

    def compare_scores(self, left, right):
        """Determine how many points comparing two summarized stats together

        :param left: Summarized stats to compare
        :type left: Series
        :param right: Summarized stats to compare
        :type right: Series
        :return: Number of wins and number of losses.
        :rtype: Tuple of two ints
        """
        (win, loss) = (0, 0)
        for l, r, name in zip(left, right, left.index):
            if self.scorer.is_counting_stat(name):
                conv_l = int(l)
                conv_r = int(r)
            else:
                conv_l = round(l, 3)
                conv_r = round(r, 3)
            if self.scorer.is_highest_better(name):
                if conv_l > conv_r:
                    win += 1
                elif conv_r > conv_l:
                    loss += 1
            else:
                if conv_l < conv_r:
                    win += 1
                elif conv_r < conv_l:
                    loss += 1

        return (win, loss)

    def show_score(self, lineup, opp_team_name, opp_sum):
        if opp_sum is None:
            print("No opponent selected")
        else:
            (w, l, my_sum) = self.compute_score(lineup, opp_sum)
            print("Against '{}' your roster will score: {} - {}".
                  format(opp_team_name, w, l))
            print("")
            for stat in my_sum.index:
                if stat in ["ERA", "WHIP"]:
                    if my_sum[stat] < opp_sum[stat]:
                        my_win = "*"
                        opp_win = ""
                    else:
                        my_win = ""
                        opp_win = "*"
                else:
                    if my_sum[stat] > opp_sum[stat]:
                        my_win = "*"
                        opp_win = ""
                    else:
                        my_win = ""
                        opp_win = "*"
                print("{:5} {:2.3f} {:1} v.s. {:2.3f} {:2}".format(
                    stat, my_sum[stat], my_win, opp_sum[stat], opp_win))

    def list_players(self, pos, ppool):
        self.display.printListPlayerHeading(pos)

        for plyr in ppool.iterrows():
            if pos in plyr[1]['eligible_positions']:
                self.display.printPlayer(pos, plyr)

    def _get_prediction_module(self):
        """Return the module to use for the prediction builder.

        The details about what prediction builder is taken from the config.
        """
        return importlib.import_module(
            self.cfg['Prediction']['builderModule'],
            package=self.cfg['Prediction']['builderPackage'])

    def _get_scorer_class(self):
        module = importlib.import_module(
            self.cfg['Scorer']['module'],
            package=self.cfg['Scorer']['package'])
        return getattr(module, self.cfg['Scorer']['class'])

    def _get_display_class(self):
        module = importlib.import_module(
            self.cfg['Display']['module'],
            package=self.cfg['Display']['package'])
        return getattr(module, self.cfg['Display']['class'])

    def _construct_roster_builder(self):
        pos_list = self.cfg['League']['positions'].split(",")
        return roster.Builder(pos_list)

    def _get_position_types(self):
        settings = self.lg.settings()
        position_types = {'mlb': ['B', 'P'], 'nhl': ['G', 'P']}
        return position_types[settings['game_code']]

    def _is_predicted_stat(self, stat):
        return stat in self.cfg['League']['predictedStatCategories'].split(',')


if __name__ == '__main__':
    args = docopt(__doc__, version='1.0')

    logging.basicConfig(
        filename='cli.log',
        level=logging.INFO,
        format='%(asctime)s.%(msecs)03d %(module)s-%(funcName)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logging.getLogger('yahoo_oauth').setLevel('WARNING')
    logging.getLogger('chardet.charsetprober').setLevel('WARNING')

    cfg = configparser.ConfigParser()
    if not os.path.exists(args['<cfg_file>']):
        raise RuntimeError("Config file does not exist: " + args['<cfg_file>'])
    cfg.read(args['<cfg_file>'])

    bot = ManagerBot(cfg)

    pred_bldr = bot.init_prediction_builder()

    # Opponent vars aren't populated until we pick an opponent
    opp_team_name = None
    opp_sum = None

    my_df = bot.fetch_player_pool()

    potential_team = roster.Container(None, None)
    my_roster = bot.load_roster()

    while True:
        print_main_menu()
        opt = input()

        if opt == "P":
            (opp_team_name, opp_sum) = pick_opponent(bot)
        elif opt == "R":
            bot.print_roster(my_roster)
        elif opt == "S":
            if opp_sum is None:
                print("No opponent selected")
            else:
                bot.show_score(my_roster, opp_team_name, opp_sum)
        elif opt == "A":
            if opp_sum is None:
                print("No opponent selected")
            else:
                my_roster = bot.auto_select_players(my_df, my_roster, opp_sum)
        elif opt == "M":
            if opp_sum is None:
                print("No opponent selected")
            else:
                manual_select_players(my_df, my_roster, opp_team_name, opp_sum,
                                      bot)
        elif opt == "T":
            show_two_start_pitchers(my_df)
        elif opt == "L":
            list_players(my_df, bot)
        elif opt == "B":
            manage_blacklist(bot)
        elif opt == "X":
            break
        else:
            print("Unknown option: {}".format(opt))

    bot.save()
