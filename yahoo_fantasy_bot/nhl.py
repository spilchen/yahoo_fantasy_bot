#!/usr/bin/python

import pandas as pd
import numpy as np
from nhl_scraper import nhl
import logging
import datetime
from yahoo_fantasy_bot import source


logger = logging.getLogger()


class Builder:
    """Class that constructs prediction datasets for hockey players.

    The datasets it generates are fully populated with projected stats taken
    from csv files.

    :param lg: Yahoo! league
    :type lg: yahoo_fantasy_api.league.League
    :param csv_details: A map of details about the csv that contains the
        predicted stats
    """
    def __init__(self, lg, cfg, csv_details):
        skaters = self._read_csv(csv_details['skaters'])
        goalies = self._read_csv(csv_details['goalies'])
        self.ppool = pd.concat([skaters, goalies], sort=True)
        self.nhl_scraper = nhl.Scraper()
        wk_start_date = lg.edit_date()
        assert(wk_start_date.weekday() == 0)
        wk_end_date = wk_start_date + datetime.timedelta(days=6)
        self.team_game_count = self.nhl_scraper.games_count(wk_start_date,
                                                            wk_end_date)
        self.nhl_players = self.nhl_scraper.players()

    def predict(self, roster_cont):
        """Build a dataset of hockey predictions for the week

        The pool of players is passed into this function through roster_const.
        It will generate a DataFrame for these players with their predictions.

        The returning DataFrame has rows for each player, and columns for each
        prediction stat.

        :param roster_cont: Roster of players to generate predictions for
        :type roster_cont: roster.Container object
        :return: Dataset of predictions
        :rtype: DataFrame
        """
        # Produce a DataFrame using preds as the base.  We'll filter out
        # all of the players not in roster_cont by doing an inner join of the
        # two data frames.  This also has the affect of attaching eligible
        # positions and Yahoo! player ID from the input player pool.
        my_roster = pd.DataFrame(roster_cont.get_roster())
        df = my_roster.join(self.ppool, how='inner', on='name', lsuffix='_dup')

        # Then we'll figure out the number of games each player is playing
        # this week.  To do this, we'll verify the team each player players
        # for then using the game count added as a column.
        team_ids = []
        wk_g = []
        for plyr_series in df.iterrows():
            plyr = plyr_series[1]
            (team_id, g) = self._find_players_schedule(plyr['name'])
            team_ids.append(team_id)
            wk_g.append(g)
        df['team_id'] = team_ids
        df['WK_G'] = wk_g

        return df

    def _find_players_schedule(self, plyr_name):
        """Find a players schedule for the upcoming week

        :param plyr_name: Name of the player
        :type plyr_name: str
        :return: Pair of team_id (from NHL) and the number of games
        :rtype: (int, int)
        """
        df = self.nhl_players[self.nhl_players['name'] == plyr_name]
        if len(df.index) == 1:
            team_id = df['teamId'].iloc(0)[0]
            return (team_id, self.team_game_count[team_id])
        else:
            return(np.nan, 0)

    def _read_csv(self, csv_detail):
        '''Helper to read a csv file based on config settings'''
        if 'header' in csv_detail:
            header = int(csv_detail['header'])
        else:
            header = None
        if 'column_names' in csv_detail:
            return pd.read_csv(csv_detail['file_name'],
                               index_col=csv_detail['index_col'],
                               names=csv_detail['column_names'],
                               header=header,
                               na_values='-')
        else:
            return pd.read_csv(csv_detail['file_name'],
                               index_col=csv_detail['index_col'],
                               header=header,
                               na_values='-')


def init_prediction_builder(lg, cfg):
    if 'source' not in cfg['Prediction']:
        raise RuntimeError(
            "Missing 'source' config attribute in 'Prediction' section")

    if cfg['Prediction']['source'] == 'yahoo':
        ps = source.Yahoo(lg, cfg)
        return Builder(lg, cfg, ps.fetch_csv_details())
    elif cfg['Prediction']['source'] == 'csv':
        cs = source.CSV(cfg)
        return Builder(lg, cfg, cs.fetch_csv_details())
    else:
        raise RuntimeError(
            "Unknown prediction source: {}".format(
                cfg['Prediction']['source']))


class PlayerPrinter:
    def __init__(self, cfg):
        self.cfg = cfg
        self.cats = self.cfg['League'].getlist('predictedStatCategories')
        self.skater_cats, self.goalie_cats = \
            self._separate_categories_by_type()

    def printRoster(self, lineup, bench, injury_reserve):
        """Print out the roster to standard out

        :param cfg: Instance of the config
        :type cfg: configparser
        :param lineup: Roster to print out
        :type lineup: List
        :param bench: Players on the bench
        :type bench: List
        :param injury_reserve: Players on the injury reserve
        :type injury_reserve: List
        """
        first_goalie = True
        print("{:4}: {:20}   "
              "{:4} {}/{}/{}/{}/{}".
              format('S', '', 'WK_G', *self.skater_cats))
        for pos in ['C', 'LW', 'RW', 'D', 'G']:
            for plyr in lineup:
                if plyr['selected_position'] == pos:
                    if pos in ["G"]:
                        if first_goalie:
                            print("")
                            print("{:4}: {:20}   "
                                  "{:4} {}/{}".
                                  format('G', '', 'WK_G', *self.goalie_cats))
                            first_goalie = False

                        s = "{:4}: {:20}   {:4} ". \
                            format(plyr['selected_position'],
                                   plyr['name'], plyr['WK_G'])
                        for i, c in enumerate(self.goalie_cats):
                            if i != 0:
                                s += "/"
                            s += "{:.3f}".format(plyr[c])
                        print(s)
                    else:
                        s = "{:4}: {:20}   {:4} ". \
                            format(plyr['selected_position'], plyr['name'],
                                   plyr['WK_G'])
                        for i, c in enumerate(self.skater_cats):
                            if i != 0:
                                s += "/"
                            s += "{:.1f}".format(plyr[c])
                        print(s)
        print("")
        print("Bench")
        for plyr in bench:
            print(plyr['name'])
        print("")
        print("Injury Reserve")
        for plyr in injury_reserve:
            print(plyr['name'])
        print("")

    def printListPlayerHeading(self, pos):
        if pos in ['G']:
            self._print_list_plyr_heading(pos, self.goalie_cats)
        else:
            self._print_list_plyr_heading(pos, self.skater_cats)

    def _print_list_plyr_heading(self, pos, cats):
        header = "{:20}   {} ".format('name', 'WK_G')
        for i, s in enumerate(cats):
            if i != 0:
                header += "/"
            header += "{}".format(s)
        print(header)

    def printPlayer(self, pos, plyr):
        if pos in ['G']:
            self._print_player(pos, plyr, self.goalie_cats)
        else:
            self._print_player(pos, plyr, self.skater_cats)

    def _print_player(self, pos, plyr, cats):
        if self._does_player_have_valid_stats(plyr, cats):
            ln = "{:20}   {} ".format(plyr[1]['name'], plyr[1]['WK_G'])
            for i, s in enumerate(cats):
                if i != 0:
                    ln += "/"
                ln += "{:.3f}".format(plyr[1][s])
            print(ln)

    def _does_player_have_valid_stats(self, plyr, stats):
        for stat in stats:
            if np.isnan(plyr[1][stat]):
                return False
        return True

    @staticmethod
    def _get_stat_category(stat):
        '''Helper to determine if a given stat is for a skater or goalie

        :param stat: Stat to check
        :return: 'G' for a goalie stat or 'S' for skater stat
        '''
        goalie_stats = ['W', 'SV%', 'SHO']
        if stat in goalie_stats:
            return 'G'
        else:
            return 'S'

    def _separate_categories_by_type(self):
        skater_cats = []
        goalie_cats = []
        for c in self.cats:
            if self._get_stat_category(c) == 'G':
                goalie_cats.append(c)
            else:
                skater_cats.append(c)
        return skater_cats, goalie_cats


class Scorer:
    """Class that scores rosters that it is given"""
    def __init__(self, cfg):
        self.cfg = cfg
        self.cats = self.cfg['League'].getlist('predictedStatCategories')
        self.use_weekly_sched = cfg['Scorer'].getboolean('useWeeklySchedule')

    def summarize(self, df):
        """Summarize the dataframe into individual stat categories

        :param df: Roster predictions to summarize
        :type df: DataFrame
        :return: Summarized predictions
        :rtype: Series
        """
        stat_cols = [e for e in self.cats
                     if self.is_counting_stat(e)]
        if 'SV%' in self.cats:
            temp_stat_cols = ['GA', 'SV']
            stat_cols += temp_stat_cols

        res = dict.fromkeys(stat_cols, 0)
        for plyr in df.iterrows():
            p = plyr[1]
            for stat in stat_cols:
                if self.is_numeric(p[stat]):
                    if self.use_weekly_sched:
                        res[stat] += float(p[stat]) / 82 * p['WK_G']
                    else:
                        res[stat] += float(p[stat])

        # Handle ratio stats
        if 'SV%' in self.cats:
            if res['SV'] > 0:
                res['SV%'] = res['SV'] / (res['SV'] + res['GA'])
            else:
                res['SV%'] = None

        # Drop the temporary values used to calculate the ratio stats
        for stat in temp_stat_cols:
            del res[stat]

        return res

    def is_numeric(self, v):
        '''Helper to check if v is a numeric type we can use in math'''
        if type(v) is float:
            return not np.isnan(v)
        elif type(v) is str:
            try:
                float(v)
                return True
            except ValueError:
                return False
        else:
            assert(False), "Unknown type: " + str(type(v))

    def is_counting_stat(self, stat):
        return stat not in ['SV%']

    def is_highest_better(self, stat):
        return True
