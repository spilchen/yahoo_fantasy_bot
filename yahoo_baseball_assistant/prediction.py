#!/bin/python

from baseball_scraper import fangraphs
from baseball_id import Lookup
import pandas as pd
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
    """
    def __init__(self, lg, team, fg, ts):
        self.id_lookup = Lookup
        self.fg = fg
        self.ts = ts
        self.week = lg.current_week() + 1
        if self.week >= lg.end_week():
            raise RuntimeError("Season over no more weeks to predict")
        (self.wk_start_date, self.wk_end_date) = lg.week_date_range(self.week)
        self.season_end_date = datetime.date(self.wk_end_date.year, 12, 31)
        self.roster = None
        if team is not None:
            self.roster = team.roster(self.week)

    def __getstate__(self):
        return (self.fg, self.ts, self.week, self.wk_start_date,
                self.wk_end_date, self.season_end_date, self.roster)

    def __setstate__(self, state):
        self.id_lookup = Lookup
        (self.fg, self.ts, self.week, self.wk_start_date, self.wk_end_date,
         self.season_end_date, self.roster) = state

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
            names = lk[lk.fg_id.isna()].mlb_name.to_list()
            ids = lk.fg_id.dropna().to_list()
            if len(names) > 0:
                names_df = self.fg.scrape(names, id_name='Name',
                                          scrape_as=scrape_type)
            else:
                names_df = None
            if len(ids) > 0:
                ids_df = self.fg.scrape(ids, scrape_as=scrape_type)
            else:
                ids_df = None
            df = ids_df.append(names_df, sort=False)
            logger.info(df)
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
        # Map of the hitter and pitcher stats.  The key is the stat name in the
        # data frame and the value is the stat name we store in the series.  We
        # have this split so that we can have separate aggregate stats for
        # hitters and pitchers (e.g. BB, H, etc.)
        hit_stat_cols = {'R': 'R', 'HR': 'HR', 'RBI': 'RBI', 'SB': 'SB',
                         'AB': 'AB_B', 'H': 'H_B', 'BB': 'BB_B'}
        pit_stat_cols = {'SO': 'SO', 'SV': 'SV', 'HLD': 'HLD', 'W': 'W',
                         'G': 'G_P', 'ER': 'ER_P', 'IP': 'IP_P', 'BB': 'BB_P',
                         'H': 'H_P'}

        res = pd.Series()
        for stat_in, stat_out in hit_stat_cols.items():
            val = 0
            for plyr in df.iterrows():
                if plyr[1]['roster_type'] != 'B':
                    continue
                if plyr[1]['G'] > 0:
                    val += plyr[1][stat_in] / plyr[1]['G'] * plyr[1]['WK_G']
            res[stat_out] = val

        for stat_in, stat_out in pit_stat_cols.items():
            val = 0
            for plyr in df.iterrows():
                if plyr[1]['roster_type'] != 'P':
                    continue
                if plyr[1]['IP'] > 0:
                    val += plyr[1][stat_in] / plyr[1]['SEASON_G'] \
                        * plyr[1]['WK_G']
            res[stat_out] = val

        # Handle ratio stats
        if res['AB_B'] > 0:
            res['AVG'] = res['H_B'] / res['AB_B']
        else:
            res['AVG'] = None
        if res['AB_B'] + res['BB_B'] > 0:
            res['OBP'] = (res['H_B'] + res['BB_B']) / \
                (res['AB_B'] + res['BB_B'])
        else:
            res['OBP'] = None
        if res['IP_P'] > 0:
            res['WHIP'] = (res['BB_P'] + res['H_P']) / res['IP_P']
            res['ERA'] = res['ER_P'] * 9 / res['IP_P']
        else:
            res['WHIP'] = None
            res['ERA'] = None

        # Delete the temporary values used to calculate the ratio stats
        res = res.drop(index=['AB_B', 'H_B', 'H_P', 'BB_B', 'BB_P',  'IP_P',
                              'ER_P', 'G_P'])

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

    def _lookup_team(self, team):
        # TODO: use lahman database instead of this mapping.  The
        # abbreviation from baseball_id is different then at
        # baseball_reference.
        if team == 'WSH':
            return 'WSN'
        if team == 'CWS':
            return 'CHW'
        return team

    def _lookup_teams(self, teams):
        # TODO: use lahman database instead of this mapping.
        a = []
        for team in teams:
            if team == "Yankees":
                a.append("NYY")
            elif team == "Rays":
                a.append("TB")
            elif team == "Red Sox":
                a.append("BOS")
            elif team == "Blue Jays":
                a.append("TOR")
            elif team == "Orioles":
                a.append("BAL")
            elif team == "Twins":
                a.append("MIN")
            elif team == "Indians":
                a.append("CLE")
            elif team == "White Sox":
                a.append("CHW")
            elif team == "Royals":
                a.append("KC")
            elif team == "Tigers":
                a.append("DET")
            elif team == "Astros":
                a.append("HOU")
            elif team == "Athletics":
                a.append("OAK")
            elif team == "Angels":
                a.append("LAA")
            elif team == "Rangers":
                a.append("TEX")
            elif team == "Mariners":
                a.append("SEA")
            elif team == "Braves":
                a.append("ATL")
            elif team == "Nationals":
                a.append("WSN")
            elif team == "Phillies":
                a.append("PHI")
            elif team == "Mets":
                a.append("NYM")
            elif team == "Marlins":
                a.append("MIA")
            elif team == "Cardinals":
                a.append("STL")
            elif team == "Cubs":
                a.append("CHC")
            elif team == "Brewers":
                a.append("MIL")
            elif team == "Reds":
                a.append("CIN")
            elif team == "Pirates":
                a.append("PIT")
            elif team == "Dodgers":
                a.append("LAD")
            elif team == "Giants":
                a.append("SF")
            elif team == "Diamondbacks":
                a.append("ARI")
            elif team == "Padres":
                a.append("SD")
            elif team == "Rockies":
                a.append("COL")
            else:
                raise RuntimeError("Unknown team: {}".format(team))
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
        if not self.player_exists(player_name):
            raise ValueError("Player not found on roster")

        for plyr in self.roster:
            if self.normalized(player_name) == self.normalized(plyr['name']):
                plyr['selected_position'] = pos
