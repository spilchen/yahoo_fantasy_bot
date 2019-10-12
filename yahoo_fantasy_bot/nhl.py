#!/usr/bin/python

import pandas as pd
import numpy as np
from nhl_scraper import nhl
import logging
import pickle
import os
import datetime
from yahoo_fantasy_bot import utils


logger = logging.getLogger()


class Builder:
    """Class that constructs prediction datasets for hockey players.

    The datasets it generates are fully populated with projected stats taken
    from csv files.

    :param lg: Yahoo! league
    :type lg: yahoo_fantasy_api.league.League
    :param skaters_csv: csv file containing skater predictions
    :type skaters_csv: str
    :param goalies_csv: csv file containing goalie predictions
    :type goalies_csv: str
    """
    def __init__(self, lg, skaters_csv, goalies_csv):
        skaters = pd.read_csv(skaters_csv, index_col='name')
        goalies = pd.read_csv(goalies_csv, index_col='name')
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
        # all of the players not in roster_cont by doing a join of the two
        # data frames.  This also has the affect of attaching eligible
        # positions and Yahoo! player ID from the input player pool.
        my_roster = pd.DataFrame(roster_cont.get_roster())
        df = my_roster.join(self.ppool, on='name')

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


def init_prediction_builder(lg, cfg):
    bldr = None
    cache = utils.LeagueCache(cfg)
    fn = cache.prediction_builder_cache_file()
    if os.path.exists(fn):
        with open(fn, "rb") as f:
            bldr = pickle.load(f)
        if datetime.datetime.now() > bldr.expiry:
            bldr = None

    if bldr is None:
        bldr = Builder(lg, "espn.skaters.proj.csv", "espn.goalies.proj.csv")
        bldr.expiry = datetime.datetime.now() + datetime.timedelta(
            minutes=int(cfg['Cache']['predictionBuilderExpiry']))

    return bldr


class PlayerPrinter:
    def __init__(self, cfg):
        pass

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
              format('B', '', 'WK_G', 'G', 'A', 'PPP', 'SOG', 'PIM'))
        for pos in ['C', 'LW', 'RW', 'D', 'G']:
            for plyr in lineup:
                if plyr['selected_position'] == pos:
                    if pos in ["G"]:
                        if first_goalie:
                            print("")
                            print("{:4}: {:20}   "
                                  "{:4} {}/{}".
                                  format('G', '', 'WK_G', 'W', 'SV%'))
                            first_goalie = False

                        print("{:4}: {:20}   "
                              "{:4} {:.1f}/{:.3f}".
                              format(plyr['selected_position'],
                                     plyr['name'], plyr['WK_G'], plyr['W'],
                                     plyr['SV%']))
                    else:
                        print("{:4}: {:20}   "
                              "{:4} {:.1f}/{:.1f}/{:.1f}/{:.1f}/{:.1f}".
                              format(plyr['selected_position'], plyr['name'],
                                     plyr['WK_G'], plyr['G'], plyr['A'],
                                     plyr['PPP'], plyr['SOG'], plyr['PIM']))
        print("")
        print("Bench")
        for plyr in bench:
            print(plyr['name'])
        print("")
        print("Injury Reserve")
        for plyr in injury_reserve:
            print(plyr['name'])

    def printListPlayerHeading(self, pos):
        if pos in ['G']:
            print("{:20}   {} {}/{}".format('name', 'WK_G', 'W', 'SV%'))
        else:
            print("{:20}   {} {}/{}/{}/{}/{}".format('name', 'WK_G', 'G', 'A',
                                                     'PPP', 'SOG', 'PIM'))

    def printPlayer(self, pos, plyr):
        if pos in ['G']:
            if self._does_player_have_valid_stats(plyr, ['W', 'SV%']):
                print("{:20}   {:.1f}/{:.3f}".
                      format(plyr[1]['name'], plyr[1]['W'], plyr[1]['SV%']))
        else:
            if self._does_player_have_valid_stats(plyr, ['G', 'A', 'PPP',
                                                         'SOG', 'PIM']):
                print("{:20}   {} {:.1f}/{:.1f}/{:.1f}/{:.1f}/{:.1f}".
                      format(plyr[1]['name'], plyr[1]['WK_G'], plyr[1]['G'],
                             plyr[1]['A'], plyr[1]['PPP'], plyr[1]['SOG'],
                             plyr[1]['PIM']))

    def _does_player_have_valid_stats(self, plyr, stats):
        for stat in stats:
            if np.isnan(plyr[1][stat]):
                return False
        return True


class Scorer:
    """Class that scores rosters that it is given"""
    def __init__(self, cfg):
        pass

    def summarize(self, df):
        """Summarize the dataframe into individual stat categories

        :param df: Roster predictions to summarize
        :type df: DataFrame
        :return: Summarized predictions
        :rtype: Series
        """
        temp_stat_cols = ['GA', 'SV']
        stat_cols = ['G', 'A', 'SOG', 'PPP', 'PIM', 'W'] + temp_stat_cols

        res = pd.Series()
        for stat in stat_cols:
            val = 0
            for plyr in df.iterrows():
                if not np.isnan(plyr[1][stat]):
                    val += plyr[1][stat] / 82 * plyr[1]['WK_G']
            res[stat] = val

        # Handle ratio stats
        if res['SV'] > 0:
            res['SV%'] = res['SV'] / (res['SV'] + res['GA'])
        else:
            res['SV%'] = None

        # Drop the temporary values used to calculate the ratio stats
        res = res.drop(index=temp_stat_cols)

        return res

    def is_counting_stat(self, stat):
        return stat not in ['SV%']

    def is_highest_better(self, stat):
        return True
