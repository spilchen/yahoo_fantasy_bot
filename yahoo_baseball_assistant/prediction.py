#!/bin/python

from baseball_scraper import fangraphs
from baseball_id import Lookup
import pandas as pd
import numpy as np
import unicodedata
import datetime
import logging


logger = logging.getLogger()


class Builder:
    """Class that constructs prediction datasets for hitters and pitchers.

    The datasets it generates are fully populated with projected stats.  The
    projection stats are scraped from fangraphs.com.

    :param team: Yahoo! Team to do the predictions for
    :type team: yahoo_fantasy_api.team.Team
    :param week: Week number to build the predictions for
    :type week: int
    :param fg: Scraper to use to pull data from FanGraphs
    :type fg: fangraphs.Scraper
    :param ts: Scraper to use to pull team data from baseball_reference.com
    :type ts: baseball_reference.TeamScraper
    :param es: Scraper to use to pull probable starters from espn
    :type es: espn.ProbableStartersScraper
    :param tss: Scraper to use to pull team list data from baseball_reference
    :type tss: baseball_reference.TeamSummaryScraper
    """
    def __init__(self, lg, team, fg, ts, es, tss):
        self.id_lookup = Lookup
        self.fg = fg
        self.ts = ts
        self.es = es
        self.tss = tss
        self.week = lg.current_week() + 1
        if self.week >= lg.end_week():
            raise RuntimeError("Season over no more weeks to predict")
        (self.wk_start_date, self.wk_end_date) = lg.week_date_range(self.week)
        self.season_end_date = datetime.date(self.wk_end_date.year, 12, 31)
        self.roster = None
        if team is not None:
            self.roster = team.roster(self.week)

    def __getstate__(self):
        return (self.fg, self.ts, self.es, self.tss, self.week,
                self.wk_start_date, self.wk_end_date, self.season_end_date,
                self.roster)

    def __setstate__(self, state):
        self.id_lookup = Lookup
        (self.fg, self.ts, self.es, self.tss, self.week, self.wk_start_date,
         self.wk_end_date, self.season_end_date, self.roster) = state

    def set_id_lookup(self, lk):
        self.id_lookup = lk

    def set_roster(self, roster):
        self.roster = roster

    def get_roster(self):
        return self.roster

    def predict(self):
        """Build a dataset of hitting and pitching predictions for the week

        The roster is inputed when the object was first created.  It will
        scrape the predictions from fangraphs returning a DataFrame.

        The returning DataFrame is the prediction of each stat for the
        remainder of the season.

        :return: Dataset of predictions
        :rtype: DataFrame
        """
        res = pd.DataFrame()
        for roster_type, scrape_type in zip(['B', 'P'],
                                            [fangraphs.ScrapeType.HITTER,
                                             fangraphs.ScrapeType.PITCHER]):
            lk = self._find_roster(roster_type)
            # Need to separate the list since we two kinds of scraping.  One by
            # fangraph IDs (common) and one by names.  The later is only used
            # if the fangraphs ID is missing.
            names = lk[lk.fg_id.isna()].mlb_name.to_list()
            ids = lk.fg_id.dropna().to_list()
            if len(names) > 0:
                names_df = self.fg.scrape(names, id_name='Name',
                                          scrape_as=scrape_type)
                assert(False), "Need to sub in the player ID into lk"
            else:
                names_df = pd.DataFrame()
            if len(ids) > 0:
                ids_df = self.fg.scrape(ids, scrape_as=scrape_type)
            else:
                ids_df = pd.DataFrame()
            df = ids_df.append(names_df, sort=False)

            # Need to sort both the roster lookup and the scrape data by
            # fangraph ID.  They both need to be in the same sorted order
            # because we are extracting out the espn_ID from lk and adding it
            # to the scrape data data frame.
            lk = lk.sort_values(by='fg_id', axis=0)
            df = df.sort_values(by='playerid', axis=0)
            logger.info(lk)
            logger.info(df)

            espn_ids = lk.espn_id.to_list()
            num_GS = self._num_gs(espn_ids)
            df = df.assign(WK_GS=pd.Series(num_GS, index=df.index))
            team_abbrevs = self._lookup_teams(df.Team.to_list())
            df = df.assign(team=pd.Series(team_abbrevs, index=df.index))
            wk_g = self._num_games_for_teams(team_abbrevs, True)
            df = df.assign(WK_G=pd.Series(wk_g, index=df.index))
            sea_g = self._num_games_for_teams(team_abbrevs, False)
            df = df.assign(SEASON_G=pd.Series(sea_g, index=df.index))
            roster_type = [roster_type] * len(df.index)
            df = df.assign(roster_type=pd.Series(roster_type, index=df.index))
            res = res.append(df, sort=False)
        return res

    def is_counting_stat(self, stat):
        return stat in ['R', 'HR', 'RBI', 'SB', 'W', 'SO', 'SV', 'HLD']

    def sum_prediction(self, df):
        """Summarize the predictions into stat categories

        :param df: Roster predictions to summarize
        :type df: DataFrame
        :return: Summarized predictions
        :rtype: Series
        """
        res = self._sum_hit_prediction(df)
        res = res.append(self._sum_pit_prediction(df))
        return res

    def _sum_hit_prediction(self, df):
        temp_stat_cols = ['AB', 'H', 'BB']
        hit_stat_cols = ['R', 'HR', 'RBI', 'SB'] + temp_stat_cols

        res = pd.Series()
        for stat in hit_stat_cols:
            val = 0
            for plyr in df.iterrows():
                if plyr[1]['roster_type'] != 'B':
                    continue
                if plyr[1]['G'] > 0:
                    val += plyr[1][stat] / plyr[1]['SEASON_G'] * \
                        plyr[1]['WK_G']
            res[stat] = val

        # Handle ratio stats
        if res['AB'] > 0:
            res['AVG'] = res['H'] / res['AB']
        else:
            res['AVG'] = None
        if res['AB'] + res['BB'] > 0:
            res['OBP'] = (res['H'] + res['BB']) / \
                (res['AB'] + res['BB'])
        else:
            res['OBP'] = None

        # Drop the temporary values used to calculate the ratio stats
        res = res.drop(index=temp_stat_cols)

        return res

    def _sum_pit_prediction(self, df):
        temp_stat_cols = ['G', 'ER', 'IP', 'BB', 'H']
        pit_stat_cols = ['SO', 'SV', 'HLD', 'W'] + temp_stat_cols

        res = pd.Series()
        for stat in pit_stat_cols:
            val = 0
            for plyr in df.iterrows():
                if plyr[1]['roster_type'] != 'P':
                    continue
                # Account for number of known starts (if applicable).
                # Otherwise, just revert to an average over the remaining games
                # on the team's schedule.
                if plyr[1]['WK_GS'] > 0:
                    val += plyr[1][stat] / plyr[1]['G'] \
                        * plyr[1]['WK_GS']
                elif plyr[1]['WK_G'] > 0:
                    val += plyr[1][stat] / plyr[1]['SEASON_G'] \
                        * plyr[1]['WK_G']
            res[stat] = val

        # Handle ratio stats
        if res['IP'] > 0:
            res['WHIP'] = (res['BB'] + res['H']) / res['IP']
            res['ERA'] = res['ER'] * 9 / res['IP']
        else:
            res['WHIP'] = None
            res['ERA'] = None

        # Delete the temporary values used to calculate the ratio stats
        res = res.drop(index=temp_stat_cols)

        return res

    def score(self, left, right):
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
            if self.is_counting_stat(name):
                conv_l = int(l)
                conv_r = int(r)
            else:
                conv_l = round(l, 3)
                conv_r = round(r, 3)
            if conv_l > conv_r:
                win += 1
            elif conv_r > conv_l:
                loss += 1
        return (win, loss)

    def _lookup_teams(self, teams):
        a = []
        tl_df = self.tss.scrape(self.wk_start_date.year)
        for team in teams:
            # In case we are given a team list with NaN (i.e. player isn't on
            # any team)
            if type(team) is str:
                a.append(tl_df[tl_df.Franchise.str.endswith(team)].
                         abbrev.iloc(0)[0])
            else:
                assert(np.isnan(team))
                a.append(None)
        return a

    def _find_roster(self, position_type):
        lk = None
        for plyr in self.roster:
            if plyr['position_type'] != position_type or \
                    plyr['selected_position'] in ['BN', 'DL']:
                continue

            one_lk = self.id_lookup.from_yahoo_ids([plyr['player_id']])
            # Do a lookup of names if the ID lookup didn't work.  We do two of
            # them.  The first one is to filter on any name that has a missing
            # yahoo_id.  This is better then just a plain name lookup because
            # it has a better chance of being unique.  A missing ID typically
            # happens for rookies.
            if len(one_lk.index) == 0:
                one_lk = self.id_lookup.from_names(
                    [plyr['name']], filter_missing='yahoo_id')
                # Failback to a pure-name lookup.  There have been instances
                # with hitter/pitchers where they have two IDs: one for
                # pitchers and one for hitters.  The id_lookup only keeps
                # track of one of those IDs.  We will strip off the '(Batter)'
                # from their name.
                if len(one_lk.index) == 0:
                    paren = plyr['name'].find('(')
                    if paren > 0:
                        name = plyr['name'][0:paren-1].strip()
                    else:
                        name = plyr['name']
                    # Get rid of any accents
                    name = self.normalized(name)
                    one_lk = self.id_lookup.from_names([name])

            if len(one_lk.index) == 0:
                raise ValueError("Was not able to lookup player: {}".format(
                    plyr))

            if lk is None:
                lk = one_lk
            else:
                lk = lk.append(one_lk)
        return lk

    def _num_games_for_team(self, abrev, week):
        if abrev is None:
            return 0
        if week:
            self.ts.set_date_range(self.wk_start_date, self.wk_end_date)
        else:
            self.ts.set_date_range(self.wk_start_date, self.season_end_date)
        df = self.ts.scrape(abrev)
        return len(df.index)

    def _num_games_for_teams(self, abrevs, week):
        games = []
        for abrev in abrevs:
            games.append(self._num_games_for_team(abrev, week))
        return games

    def _num_gs(self, espn_ids):
        df = self.es.scrape()
        num_GS = []
        for espn_id in espn_ids:
            gs = len(df[df.espn_id == espn_id].index)
            num_GS.append(gs)
        return num_GS

    def normalized(self, name):
        return unicodedata.normalize('NFD', name).encode(
            'ascii', 'ignore').decode('utf-8')

    def player_exists(self, player_name):
        """Check if the given player is on your roster

        :param player_name: The player name to check
        :type player_name: string
        :return: True if the player, False otherwise
        :rtype: boolean
        """
        for plyr in self.roster:
            if player_name == self.normalized(plyr['name']):
                return True
        return False

    def del_player(self, player_name):
        """Removes the given player from your roster

        :param player_name: Full name of the player to delete.  The player name
               must this exactly; with the exception of accents, which are
               normalized out
        :type player_name: str
        """
        for plyr in self.roster:
            if self.normalized(player_name) == self.normalized(plyr['name']):
                self.roster.remove(plyr)

    def get_position_type(self, pos):
        if pos in ["C", "1B", "2B", "3B", "SS", "LF", "CF", "RF", "Util"]:
            return 'B'
        elif pos in ["SP", "RP"]:
            return 'P'
        else:
            raise ValueError("{} is not a valid position".format(pos))

    def add_player(self, player_name, pos):
        """Adds a player to the roster

        This will raise an error if the player already exists on the roster.

        :param player_name: Full name of the player to delete.  The player name
               must this exactly; with the exception of accents, which are
               normalized out
        :type player_name: str
        :param pos: The short version of the position.
        :type pos: str
        """
        if self.player_exists(player_name):
            raise ValueError("Player is already on the roster")

        self.roster.append({'position_type': self.get_position_type(pos),
                            'selected_position': pos,
                            'name': player_name,
                            'player_id': -1})

    def change_position(self, player_name, pos):
        """Change the position of a player

        The player must be on your roster.

        :param player_name: Full name of the player who's position is changing
        :type player_name: str
        :param pos: The short version of the position.
        :type pos: str
        """
        for plyr in self.roster:
            if self.normalized(player_name) == self.normalized(plyr['name']):
                plyr['selected_position'] = pos
                return
        raise ValueError("Player not found on roster")
