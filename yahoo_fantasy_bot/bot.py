#!/bin/python

from yahoo_oauth import OAuth2
import yahoo_fantasy_api as yfa
from yahoo_fantasy_bot import roster, utils
import logging
import pickle
import os
import math
import datetime
import pandas as pd
import numpy as np
import importlib
import copy


class ScoreComparer:
    """
    Class that compares the scores of two lineups and computes whether it is
    *better* (in the fantasy sense)
    """
    def __init__(self, scorer, opp_sum, lineup):
        self.scorer = scorer
        self.opp_sum = opp_sum
        (self.orig_w, self.orig_l, _, self.orig_cat_comp) = \
            self.compute_score(lineup)

    def compare_lineup(self, potential_lineup):
        better_lineup = False
        (new_w, new_l, _, new_cat_comp) = self.compute_score(potential_lineup)
        if self._is_new_score_better(new_w, new_l, new_cat_comp):
            self.orig_w = new_w
            self.orig_l = new_l
            better_lineup = True
        return better_lineup

    def compute_score(self, lineup):
        df = pd.DataFrame(data=lineup, columns=lineup[0].index)
        my_sum = self.scorer.summarize(df)
        (w, l, cat_comp) = self._compare_scores(my_sum, self.opp_sum)
        return (w, l, my_sum, cat_comp)

    def update_score(self, lineup):
        (self.orig_w, self.orig_l, _, self.orig_cat_comp) = \
            self.compute_score(lineup)

    def _is_new_score_better(self, new_w, new_l, new_cat_comp):
        if self.orig_w + self.orig_l > 0:
            orig_pct = self.orig_w / (self.orig_w + self.orig_l)
        else:
            orig_pct = 0.5

        if new_w + new_l > 0:
            new_pct = new_w / (new_w + new_l)
        else:
            new_pct = 0.5

        # Look for marginal improvements in categories we are tied or losing
        if math.isclose(orig_pct, new_pct):
            stat_improvement = 0.0
            for stat in new_cat_comp.keys():
                o_comp = self.orig_cat_comp[stat]
                n_comp = new_cat_comp[stat]
                if o_comp["outcome"] in ['L', 'T'] and \
                        n_comp["outcome"] == o_comp["outcome"]:
                    if math.isclose(o_comp["left"], n_comp["left"]):
                        pass
                    else:
                        stat_factor = 1 if self.scorer.is_highest_better(stat)\
                            else -1
                        stat_improvement += (n_comp["left"] - o_comp["left"]) \
                            / o_comp["left"] * stat_factor
            return stat_improvement > 0
        else:
            return orig_pct < new_pct

    def _compare_scores(self, left, right):
        """Determine how many points comparing two summarized stats together

        :param left: Summarized stats to compare
        :type left: Series
        :param right: Summarized stats to compare
        :type right: Series
        :return: Number of wins, number of losses and a category comparison
        :rtype: Tuple of two ints and a dict
        """
        category_compare = {}
        (win, loss) = (0, 0)
        for l, r, name in zip(left, right, left.index):
            if self.scorer.is_counting_stat(name):
                conv_l = int(l)
                conv_r = int(r)
            else:
                conv_l = round(l, 3)
                conv_r = round(r, 3)
            outcome = 'T'
            if self.scorer.is_highest_better(name):
                if conv_l > conv_r:
                    outcome = 'W'
                elif conv_r > conv_l:
                    outcome = 'L'
            else:
                if conv_l < conv_r:
                    outcome = 'W'
                elif conv_r < conv_l:
                    outcome = 'L'
            if outcome == 'W':
                win += 1
            elif outcome == 'L':
                loss += 1
            category_compare[name] = {"left": l, "right": r,
                                      "outcome": outcome}

        return (win, loss, category_compare)


class ManagerBot:
    """A class that encapsulates an automated Yahoo! fantasy manager.
    """
    def __init__(self, cfg):
        self.logger = logging.getLogger()
        self.cfg = cfg
        self.sc = OAuth2(None, None, from_file=cfg['Connection']['oauthFile'])
        self.lg = yfa.League(self.sc, cfg['League']['id'])
        self.tm = self.lg.to_team(self.lg.team_key())
        self.tm_cache = utils.TeamCache(self.cfg, self.lg.team_key())
        self.lg_cache = utils.LeagueCache(self.cfg)
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
        self.opp_sum = None
        self.opp_team_name = None

        self.init_prediction_builder()
        self.fetch_player_pool()
        self.load_lineup()
        self.load_bench()
        self.pick_injury_reserve()
        self.auto_pick_opponent()

    def _load_blacklist(self):
        fn = self.tm_cache.blacklist_cache_file()
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
                self.logger.info("Adding {} to bench...".format(p['name']))
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
                for idx, lp in enumerate(self.lineup):
                    if lp['player_id'] == plyr['player_id']:
                        del self.lineup[idx]
                        break

        if len(self.lineup) <= self.my_team_bldr.max_players():
            self.fill_empty_spots()

        if len(ir) < ir_spots:
            self.injury_reserve = ir
        else:
            assert(False), "Need to implement pruning of IR"

    def move_non_available_players(self):
        """Remove any player that has a status (e.g. DTD, SUSP, etc.).

        If the player is important enough, they will be added back to the bench
        pending the ownership percentage.
        """
        roster = self._get_orig_roster()
        for plyr in roster:
            if plyr['status'].strip() != '':
                for idx, lp in enumerate(self.lineup):
                    if lp['player_id'] == plyr['player_id']:
                        self.logger.info(
                            "Moving {} out of the starting lineup because "
                            "they are not available ({})".format(
                                plyr['name'], plyr['status']))
                        del self.lineup[idx]
                        break

    def _save_blacklist(self):
        fn = self.tm_cache._blacklist_cache_file()
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
        with open(self.tm_cache.lineup_cache_file(), "wb") as f:
            pickle.dump(self.lineup, f)
        with open(self.tm_cache.bench_cache_file(), "wb") as f:
            pickle.dump(self.bench, f)
        with open(self.lg_cache.prediction_builder_cache_file(), "wb") as f:
            pickle.dump(self.pred_bldr, f)

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
            plyr_pool = self.fetch_free_agents() + self.fetch_cur_lineup()
            rcont = roster.Container(None, None)
            rcont.add_players(plyr_pool)
            self.ppool = self.pred_bldr.predict(
                rcont, *self.cfg['PredictionNamedArguments'])

    def fetch_free_agents(self):
        free_agents = None

        if os.path.exists(self.lg_cache.free_agents_cache_file()):
            with open(self.lg_cache.free_agents_cache_file(), "rb") as f:
                free_agents = pickle.load(f)
            if datetime.datetime.now() > free_agents["expiry"]:
                self.logger.info("Free agent cache is stale.  Expires at {}".
                                 format(free_agents["expiry"]))
                free_agents = None

        if free_agents is None:
            self.logger.info("Fetching free agents")
            free_agents = {}
            free_agents["players"] = self.lg.free_agents(None)
            free_agents["expiry"] = datetime.datetime.now() + \
                datetime.timedelta(
                    minutes=int(self.cfg['Cache']['freeAgentExpiry']))
            self.logger.info(
                "Free agents fetch complete.  {} players in pool".
                format(len(free_agents["players"])))

            with open(self.lg_cache.free_agents_cache_file(), "wb") as f:
                pickle.dump(free_agents, f)

        return free_agents["players"]

    def invalidate_free_agents(self, plyrs):
        if os.path.exists(self.lg_cache.free_agents_cache_file()):
            with open(self.lg_cache.free_agents_cache_file(), "rb") as f:
                free_agents = pickle.load(f)

            plyr_ids = [e["player_id"] for e in plyrs]
            self.logger.info("Removing player IDs from free agent cache".
                             format(plyr_ids))
            new_players = [e for e in free_agents["players"]
                           if e['player_id'] not in plyr_ids]
            free_agents['players'] = new_players
            with open(self.lg_cache.free_agents_cache_file(), "wb") as f:
                pickle.dump(free_agents, f)

    def sum_opponent(self, opp_team_key):
        # Build up the predicted score of the opponent
        try:
            team_name = self._get_team_name(self.lg, opp_team_key)
        except LookupError:
            print("Not a valid team: {}:".format(opp_team_key))
            return(None, None)

        opp_team = roster.Container(self.lg, self.lg.to_team(opp_team_key))
        opp_df = self.pred_bldr.predict(opp_team,
                                        *self.cfg['PredictionNamedArguments'])
        opp_sum = self.scorer.summarize(opp_df)
        return (team_name, opp_sum)

    def load_lineup(self):
        if os.path.exists(self.tm_cache.lineup_cache_file()):
            with open(self.tm_cache.lineup_cache_file(), "rb") as f:
                self.lineup = pickle.load(f)
        else:
            self.lineup = []
            self.fill_empty_spots()

    def load_bench(self):
        if os.path.exists(self.tm_cache.bench_cache_file()):
            with open(self.tm_cache.bench_cache_file(), "rb") as f:
                self.bench = pickle.load(f)
        else:
            self.pick_bench()

    def fill_empty_spots(self):
        if len(self.lineup) <= self.my_team_bldr.max_players():
            stat_categories = self.lg.stat_categories()
            for pos_type in self._get_position_types():
                stats = []
                for sc in stat_categories:
                    if sc['position_type'] == pos_type and \
                            self._is_predicted_stat(sc['display_name']):
                        stats.append(sc['display_name'])
                self.initial_fit(stats, pos_type)

    def initial_fit(self, categories, pos_type):
        selector = roster.PlayerSelector(self.ppool)
        selector.rank(categories)
        ids_in_roster = [e['player_id'] for e in self.lineup]
        for plyr in selector.select():
            try:
                if plyr['name'] in self.blacklist:
                    continue
                if plyr['position_type'] != pos_type:
                    continue
                if plyr['status'] != '':
                    continue
                if plyr['player_id'] in ids_in_roster:
                    continue

                self.logger.info("Player: {} Positions: {}".
                                 format(plyr['name'],
                                        plyr['eligible_positions']))

                plyr['selected_position'] = np.nan
                self.lineup = self.my_team_bldr.fit_if_space(self.lineup, plyr)
            except LookupError:
                pass
            if len(self.lineup) == self.my_team_bldr.max_players():
                break

    def print_roster(self):
        self.display.printRoster(self.lineup, self.bench, self.injury_reserve)

    def sync_lineup(self):
        """Reset the local lineup to the one that is set in Yahoo!"""
        yahoo_roster = self._get_orig_roster()
        roster_ids = [e['player_id'] for e in yahoo_roster]
        bench_ids = [e['player_id'] for e in yahoo_roster
                     if e['selected_position'] == 'BN']
        ir_ids = [e['player_id'] for e in yahoo_roster
                  if e['selected_position'] == 'DL']
        sel_plyrs = self.ppool[self.ppool['player_id'].isin(roster_ids)]
        lineup = []
        bench = []
        ir = []
        for plyr in sel_plyrs.iterrows():
            if plyr[1]['player_id'] in bench_ids:
                bench.append(plyr[1])
            elif plyr[1]['player_id'] in ir_ids:
                ir.append(plyr[1])
            else:
                lineup.append(plyr[1])
        self.lineup = lineup
        self.bench = bench
        self.injury_reserve = ir

    def optimize_lineup(self):
        # Filter out any players from the lineup as we don't want to consider
        # them again.
        indexColumn = self.cfg['Prediction']['indexColumn']
        lineup_ids = [e[indexColumn] for e in self.lineup]
        avail_plyrs = self.ppool[~self.ppool[indexColumn].isin(lineup_ids) &
                                 ~self.ppool['name'].isin(self.blacklist)]
        avail_plyrs = avail_plyrs[avail_plyrs['percent_owned'] > 10]

        score_comparer = ScoreComparer(self.scorer, self.opp_sum, self.lineup)
        optimizer_func = self._get_lineup_optimizer_function()
        best_lineup = optimizer_func(self.cfg, score_comparer,
                                     self.my_team_bldr, avail_plyrs,
                                     self.lineup)
        if best_lineup:
            self.lineup = copy.deepcopy(best_lineup)
            self.pick_bench()
            self.print_roster()

    def show_score(self):
        if self.opp_sum is None:
            raise RuntimeError("No opponent selected")

        score_comparer = ScoreComparer(self.scorer, self.opp_sum, self.lineup)
        (w, l, my_sum, _) = score_comparer.compute_score(self.lineup)
        print("Against '{}' your roster will score: {} - {}".
              format(self.opp_team_name, w, l))
        print("")
        for stat in my_sum.index:
            if stat in ["ERA", "WHIP"]:
                if my_sum[stat] < self.opp_sum[stat]:
                    my_win = "*"
                    opp_win = ""
                else:
                    my_win = ""
                    opp_win = "*"
            else:
                if my_sum[stat] > self.opp_sum[stat]:
                    my_win = "*"
                    opp_win = ""
                else:
                    my_win = ""
                    opp_win = "*"
            print("{:5} {:2.3f} {:1} v.s. {:2.3f} {:2}".format(
                stat, my_sum[stat], my_win, self.opp_sum[stat], opp_win))

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

        # Change the free agent cache to remove the players we added
        if not dry_run:
            adds = roster_chg.get_adds_completed()
            self.invalidate_free_agents(adds)

    def pick_opponent(self, opp_team_key):
        (self.opp_team_name, self.opp_sum) = self.sum_opponent(opp_team_key)

    def auto_pick_opponent(self):
        edit_wk = self.lg.current_week()
        (wk_start, wk_end) = self.lg.week_date_range(edit_wk)
        edit_date = self.lg.edit_date()
        if edit_date > wk_end:
            edit_wk += 1

        try:
            opp_team_key = self.tm.matchup(edit_wk)
        except RuntimeError:
            self.logger.info("Could not find opponent.  Picking ourselves...")
            opp_team_key = self.lg.team_key()

        self.pick_opponent(opp_team_key)

    def _get_team_name(self, lg, team_key):
        for team in lg.teams():
            if team['team_key'] == team_key:
                return team['name']
        raise LookupError("Could not find team for team key: {}".format(
            team_key))

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

    def _get_lineup_optimizer_function(self):
        """Return the function used to optimize a lineup.

        The config file is used to determine the appropriate function.
        """
        module = importlib.import_module(
            self.cfg['LineupOptimizer']['module'],
            package=self.cfg['LineupOptimizer']['package'])
        return getattr(module, self.cfg['LineupOptimizer']['function'])

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
        self.adds_completed = []

    def apply(self):
        self._calc_player_drops()
        self._calc_player_adds()
        self._apply_ir_moves()
        self._apply_player_adds_and_drops()
        self._apply_position_selector()

    def get_adds_completed(self):
        return self.adds_completed

    def _calc_player_drops(self):
        self.drops = []
        for plyr in self.orig_roster:
            if plyr['player_id'] not in self.new_roster_ids:
                self.drops.append(plyr)

    def _calc_player_adds(self):
        self.adds = []
        for plyr in self.lineup + self.bench:
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
                self.adds_completed.append(plyr)
                print("Add " + plyr['name'])
                if not self.dry_run:
                    self.tm.add_player(plyr['player_id'])

        for add_plyr, drop_plyr in zip(self.adds, self.drops):
            self.adds_completed.append(add_plyr)
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
