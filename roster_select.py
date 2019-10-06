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
    print("Y - Apply roster moves")
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


def show_two_start_pitchers(bot):
    if "WK_GS" in bot.ppool.columns:
        two_starters = bot.ppool[bot.ppool.WK_GS > 1]
        for plyr in two_starters.iterrows():
            print(plyr[1]['name'])
    else:
        print("WK_GS is not a category in the player pool")


def manual_select_players(opp_team_name, opp_sum, bot):
    if opp_sum is None:
        print("Must pick an opponent")
        return

    bot.print_roster()
    bot.show_score(opp_team_name, opp_sum)
    print("Enter the name of the player to remove: ")
    pname_rem = input().rstrip()
    print("Enter the name of the player to add: ")
    pname_add = input().rstrip()

    try:
        bot.swap_player(pname_rem, pname_add)
    except (LookupError, ValueError) as e:
        print(e)
        return

    bot.print_roster()
    bot.show_score(opp_team_name, opp_sum)


def auto_select_players(opp_sum):
    if opp_sum is None:
        print("Must pick an opponent")
        return

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
        bot.auto_select_players(opp_sum, num_iters, categories)
    except KeyError as e:
        print(e)
        return


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


def list_players(bot):
    print("Enter position: ")
    pos = input()
    print("")
    bot.list_players(pos)


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


def apply_roster_moves(bot):
    bot.apply_roster_moves(dry_run=True)
    print("")
    print("Type 'yes' to apply the roster moves:")
    proceed = input()
    if proceed == 'yes':
        bot.apply_roster_moves(dry_run=False)


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
        self.lineup = None
        self.bench = []
        self.injury_reserve = []

        self.init_prediction_builder()
        self.fetch_player_pool()
        self.load_lineup()
        self.load_bench()
        self.pick_injury_reserve()

    def cache_dir(self):
        dir = self.cfg['Cache']['dir']
        if not os.path.isdir(dir):
            os.mkdir(dir)
        return dir

    def lineup_cache_file(self):
        dir = self.cache_dir()
        return "{}/lineup.pkl".format(dir)

    def bench_cache_file(self):
        dir = self.cache_dir()
        return "{}/bench.pkl".format(dir)

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

    def pick_bench(self):
        """Pick the bench spots based on the current roster."""
        self.bench = []
        bench_spots = int(self.cfg['League']['benchSpots'])
        if bench_spots == 0:
            return

        # We'll pick the bench spots by picking players not in your lineup or
        # IR but have the highest ownership %.
        lineup_names = [e['name'] for e in self.lineup] + \
            [e['name'] for e in self.injury_reserve]
        top_owners = self.ppool.sort_values(by=["percent_owned"],
                                            ascending=False)
        for plyr in top_owners.iterrows():
            p = plyr[1]
            if p['name'] not in lineup_names:
                print("Adding {} to bench...".format(p['name']))
                self.bench.append(p)
                if len(self.bench) == bench_spots:
                    break

    def pick_injury_reserve(self):
        """Pick the injury reserve slots"""
        self.injury_reserve = []
        ir_spots = int(self.cfg['League']['irSpots'])
        if ir_spots == 0:
            return

        ir = []
        roster = self._get_orig_roster()
        for plyr in roster:
            if plyr['status'] == 'IR':
                ir.append(plyr)

        if len(ir) < ir_spots:
            self.injury_reserve = ir
        else:
            assert(False), "Need to implement pruning of IR"

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

    def save(self):
        with open(self.lineup_cache_file(), "wb") as f:
            pickle.dump(self.lineup, f)
        with open(self.bench_cache_file(), "wb") as f:
            pickle.dump(self.bench, f)
        self.save_prediction_builder()

    def save_prediction_builder(self):
        """Save the contents of the prediction builder to disk"""
        if self.pred_bldr is None:
            raise RuntimeError("No prediction builder to save!")
        module = self._get_prediction_module()
        saver = getattr(module, self.cfg['Prediction']['builderClassSaver'])
        saver(self.pred_bldr, self.cfg)

    def fetch_cur_lineup(self):
        """Fetch the current lineup as set in Yahoo!"""
        all_mine = self._get_orig_roster()
        pct_owned = self.lg.percent_owned([e['player_id'] for e in all_mine])
        for p, pct_own in zip(all_mine, pct_owned):
            if p['selected_position'] == 'BN':
                p['selected_position'] = np.nan
            assert(pct_own['player_id'] == p['player_id'])
            p['percent_owned'] = pct_own['percent_owned']
        return all_mine

    def fetch_player_pool(self):
        """Build the roster pool of players"""
        if self.ppool is None:
            if os.path.exists(self.player_pool_cache_file()):
                with open(self.player_pool_cache_file(), "rb") as f:
                    self.ppool = pickle.load(f)
            else:
                all_mine = self.fetch_cur_lineup()
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

    def load_lineup(self):
        if os.path.exists(self.lineup_cache_file()):
            with open(self.lineup_cache_file(), "rb") as f:
                self.lineup = pickle.load(f)
        else:
            self.lineup = []
            stat_categories = self.lg.stat_categories()
            for pos_type in self._get_position_types():
                stats = []
                for sc in stat_categories:
                    if sc['position_type'] == pos_type and \
                            self._is_predicted_stat(sc['display_name']):
                        stats.append(sc['display_name'])
                self.initial_fit(stats, pos_type)

    def load_bench(self):
        if os.path.exists(self.bench_cache_file()):
            with open(self.bench_cache_file(), "rb") as f:
                self.bench = pickle.load(f)
        else:
            self.pick_bench()

    def initial_fit(self, categories, pos_type):
        selector = roster.PlayerSelector(self.ppool)
        selector.rank(categories)
        for plyr in selector.select():
            try:
                if plyr['name'] in self.blacklist:
                    continue
                if plyr['position_type'] != pos_type:
                    continue
                if plyr['status'] != '':
                    continue

                print("Player: {} Positions: {}".
                      format(plyr['name'], plyr['eligible_positions']))

                plyr['selected_position'] = np.nan
                self.lineup = self.my_team_bldr.fit_if_space(self.lineup, plyr)
            except LookupError:
                pass
            if len(self.lineup) == self.my_team_bldr.max_players():
                break

    def print_roster(self):
        self.display.printRoster(self.lineup, self.bench, self.injury_reserve)

    def auto_select_players(self, opp_sum, num_iters, categories):
        # Filter out any players from the lineup as we don't want to consider
        # them again.
        indexColumn = self.cfg['Prediction']['indexColumn']
        lineup_ids = [e[indexColumn] for e in self.lineup]
        avail_plyrs = self.ppool[~self.ppool[indexColumn].isin(lineup_ids)]
        selector = roster.PlayerSelector(avail_plyrs)
        try:
            selector.rank(categories)
        except KeyError:
            raise KeyError("Categories are not valid: {}".format(categories))

        (orig_w, orig_l, _) = self.compute_score(self.lineup, opp_sum)
        for i, plyr in enumerate(selector.select()):
            if i+1 > num_iters:
                break
            if plyr['name'] in self.blacklist:
                continue

            print("Player: {} Positions: {}".
                  format(plyr['name'], plyr['eligible_positions']))

            plyr['selected_position'] = np.nan
            best_lineup = copy_roster(self.lineup)
            found_better = False
            for potential_lineup in \
                    self.my_team_bldr.enumerate_fit(self.lineup, plyr):
                (new_w, new_l, _) = self.compute_score(potential_lineup,
                                                       opp_sum)
                if is_new_score_better(orig_w, orig_l, new_w, new_l):
                    best_lineup = copy_roster(potential_lineup)
                    (orig_w, orig_l) = (new_w, new_l)
                    print("  *** Found better lineup")
                    found_better = True
            self.lineup = copy_roster(best_lineup)
            if found_better:
                self.pick_bench()
                self.print_roster()

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

    def show_score(self, opp_team_name, opp_sum):
        if opp_sum is None:
            print("No opponent selected")
        else:
            (w, l, my_sum) = self.compute_score(self.lineup, opp_sum)
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

    def list_players(self, pos):
        self.display.printListPlayerHeading(pos)

        for plyr in self.ppool.iterrows():
            if pos in plyr[1]['eligible_positions']:
                self.display.printPlayer(pos, plyr)

    def find_in_lineup(self, name):
        for idx, p in enumerate(self.lineup):
            if p['name'] == name:
                return idx
        raise LookupError("Could not find player: " + name)

    def swap_player(self, plyr_name_del, plyr_name_add):
        plyr_add_df = self.ppool[self.ppool['name'] == plyr_name_add]
        if(len(plyr_add_df.index) == 0):
            raise LookupError("Could not find player in pool: {}".format(
                plyr_name_add))
        if(len(plyr_add_df.index) > 1):
            raise LookupError("Found more than one player!: {}".format(
                plyr_name_add))
        plyr_add = plyr_add_df.iloc(0)[0]

        idx = self.find_in_lineup(plyr_name_del)
        plyr_del = self.lineup[idx]
        assert(type(plyr_del.selected_position) == str)
        if plyr_del.selected_position not in plyr_add['eligible_positions']:
            raise ValueError("Position {} is not a valid position for {}: {}".
                             format(plyr_del.selected_position,
                                    plyr_add['name'],
                                    plyr_add['eligible_positions']))

        plyr_add['selected_position'] = plyr_del['selected_position']
        plyr_del['selected_position'] = np.nan
        self.lineup[idx] = plyr_add
        self.pick_bench()

    def apply_roster_moves(self, dry_run):
        """Make roster changes with Yahoo!

        :param dry_run: Just enumerate the roster moves but don't apply yet
        :type dry_run: bool
        """
        roster_chg = RosterChanger(self.lg, dry_run, self._get_orig_roster(),
                                   self.lineup, self.bench,
                                   self.injury_reserve)
        roster_chg.apply()

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

    def _get_orig_roster(self):
        return self.lg.to_team(self.lg.team_key()).roster(
            day=self.lg.edit_date())


class RosterChanger:
    def __init__(self, lg, dry_run, orig_roster, lineup, bench,
                 injury_reserve):
        self.lg = lg
        self.tm = lg.to_team(lg.team_key())
        self.dry_run = dry_run
        self.orig_roster = orig_roster
        self.lineup = lineup
        self.bench = bench
        self.injury_reserve = injury_reserve
        self.orig_roster_ids = [e['player_id'] for e in orig_roster]
        self.new_roster_ids = [e['player_id'] for e in lineup] + \
            [e['player_id'] for e in bench] + \
            [e['player_id'] for e in injury_reserve]
        self.adds = []
        self.drops = []

    def apply(self):
        self._calc_player_drops()
        self._calc_player_adds()
        self._apply_ir_moves()
        self._apply_player_adds_and_drops()
        self._apply_position_selector()

    def _calc_player_drops(self):
        self.drops = []
        for plyr in self.orig_roster:
            if plyr['player_id'] not in self.new_roster_ids:
                self.drops.append(plyr)

    def _calc_player_adds(self):
        self.adds = []
        for plyr in self.lineup:
            if plyr['player_id'] not in self.orig_roster_ids:
                self.adds.append(plyr)

    def _apply_player_adds_and_drops(self):
        while len(self.drops) != len(self.adds):
            if len(self.drops) > len(self.adds):
                plyr = self.drops.pop()
                print("Drop " + plyr['name'])
                if not self.dry_run:
                    self.tm.drop_player(plyr['player_id'])
            else:
                plyr = self.adds.pop()
                print("Add " + plyr['name'])
                if not self.dry_run:
                    self.tm.add_player(plyr['player_id'])

        for add_plyr, drop_plyr in zip(self.adds, self.drops):
            print("Add {} and drop {}".format(add_plyr['name'],
                                              drop_plyr['name']))
            if not self.dry_run:
                self.tm.add_and_drop_players(add_plyr['player_id'],
                                             drop_plyr['player_id'])

    def _apply_one_player_drop(self):
        if len(self.drops) > 0:
            plyr = self.drops.pop()
            print("Drop " + plyr['name'])
            if not self.dry_run:
                self.tm.drop_player(plyr['player_id'])

    def _apply_ir_moves(self):
        orig_ir = [e for e in self.orig_roster
                   if e['selected_position'] == 'IR']
        new_ir_ids = [e['player_id'] for e in self.injury_reserve]
        pos_change = []
        num_drops = 0
        for plyr in orig_ir:
            if plyr['player_id'] in self.new_roster_ids and \
                    plyr['player_id'] not in new_ir_ids:
                pos_change.append({'player_id': plyr['player_id'],
                                   'selected_position': 'BN',
                                   'name': plyr['name']})
                num_drops += 1

        for plyr in self.injury_reserve:
            assert(plyr['player_id'] in self.orig_roster_ids)
            pos_change.append({'player_id': plyr['player_id'],
                               'selected_position': 'IR',
                               'name': plyr['name']})
            num_drops -= 1

        # Prior to changing any of the IR spots, we may need to drop players.
        # The number has been precalculated in the above loops.  Basically the
        # different in the number of players moving out of IR v.s. moving into
        # IR.
        for _ in range(num_drops):
            self._apply_one_player_drop()

        for plyr in pos_change:
            print("Move {} to {}".format(plyr['name'],
                                         plyr['selected_position']))
        if len(pos_change) > 0 and not self.dry_run:
            self.tm.change_positions(self.lg.edit_date(), pos_change)

    def _apply_position_selector(self):
        pos_change = []
        for plyr in self.lineup:
            pos_change.append({'player_id': plyr['player_id'],
                               'selected_position': plyr['selected_position']})
            print("Move {} to {}".format(plyr['name'],
                                         plyr['selected_position']))
        for plyr in self.bench:
            pos_change.append({'player_id': plyr['player_id'],
                               'selected_position': 'BN'})
            print("Move {} to BN".format(plyr['name']))

        if not self.dry_run:
            self.tm.change_positions(self.lg.edit_date(), pos_change)


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

    # Opponent vars aren't populated until we pick an opponent
    opp_team_name = None
    opp_sum = None

    while True:
        print_main_menu()
        opt = input()

        if opt == "P":
            (opp_team_name, opp_sum) = pick_opponent(bot)
        elif opt == "R":
            bot.print_roster()
        elif opt == "S":
            if opp_sum is None:
                print("No opponent selected")
            else:
                bot.show_score(opp_team_name, opp_sum)
        elif opt == "A":
            if opp_sum is None:
                print("No opponent selected")
            else:
                auto_select_players(opp_sum)
        elif opt == "M":
            if opp_sum is None:
                print("No opponent selected")
            else:
                manual_select_players(opp_team_name, opp_sum, bot)
        elif opt == "T":
            show_two_start_pitchers(bot)
        elif opt == "L":
            list_players(bot)
        elif opt == "B":
            manage_blacklist(bot)
        elif opt == "Y":
            apply_roster_moves(bot)
        elif opt == "X":
            break
        else:
            print("Unknown option: {}".format(opt))

    bot.save()
