#!/bin/python

from baseball_scraper import baseball_reference, espn, fangraphs
from baseball_id import Lookup
from yahoo_fantasy_bot import utils
import pandas as pd
import numpy as np
import datetime
import logging
import pickle
import os


logger = logging.getLogger()


class Builder:
    """Class that constructs prediction datasets for hitters and pitchers.

    The datasets it generates are fully populated with projected stats.  The
    projection stats are scraped from fangraphs.com.

    :param lg: Yahoo! league
    :type lg: yahoo_fantasy_api.league.League
    :param fg: Scraper to use to pull data from FanGraphs
    :type fg: fangraphs.Scraper
    :param ts: Scraper to use to pull team data from baseball_reference.com
    :type ts: baseball_reference.TeamScraper
    :param es: Scraper to use to pull probable starters from espn
    :type es: espn.ProbableStartersScraper
    :param tss: Scraper to use to pull team list data from baseball_reference
    :type tss: baseball_reference.TeamSummaryScraper
    """
    def __init__(self, lg, fg, ts, es, tss):
        self.id_lookup = Lookup
        self.fg = fg
        self.ts = ts
        self.es = es
        self.tss = tss
        self.wk_start_date = lg.edit_date()
        assert(self.wk_start_date.weekday() == 0)
        self.wk_end_date = self.wk_start_date + datetime.timedelta(days=6)
        self.season_end_date = datetime.date(self.wk_end_date.year, 12, 31)

    def __getstate__(self):
        return (self.fg, self.ts, self.es, self.tss,
                self.wk_start_date, self.wk_end_date, self.season_end_date)

    def __setstate__(self, state):
        self.id_lookup = Lookup
        (self.fg, self.ts, self.es, self.tss, self.wk_start_date,
         self.wk_end_date, self.season_end_date) = state

    def set_id_lookup(self, lk):
        self.id_lookup = lk

    def predict(self, roster_cont, fail_on_missing=True, lk_id_system='fg_id',
                scrape_id_system='playerid', team_has='just_name'):
        """Build a dataset of hitting and pitching predictions for the week

        The roster is inputed into this function.  It will scrape the
        predictions from fangraphs returning a DataFrame.

        The returning DataFrame is the prediction of each stat.

        :param roster_cont: Roster of players to generate predictions for
        :type roster_cont: roster.Container object
        :param fail_on_missing: True we are to fail if any player in
        roster_cont can't be found in the prediction data set.  Set this to
        false to simply filter those out.
        :param lk_id_system: Name of the ID column in the baseball_id Lookup
        :type lk_id_system: str
        :param scrape_id_system: Name of the ID column in the scraped data that
        has the ID to match with Lookup
        :type scrape_id_system: str
        :param team_has: Indicate the Team field in the scraped data frame.
        Does it have 'just_name' (e.g. Blue Jays, Reds, etc.) or 'abbrev' (e.g.
        NYY, SEA, etc.)
        :type team_has: str
        :type fail_on_missing: bool
        :return: Dataset of predictions
        :rtype: DataFrame
        """
        res = pd.DataFrame()
        for roster_type, scrape_type in zip(['B', 'P'],
                                            [fangraphs.ScrapeType.HITTER,
                                             fangraphs.ScrapeType.PITCHER]):
            lk = self._find_roster(roster_type, roster_cont.get_roster(),
                                   fail_on_missing)
            if lk is None:
                continue
            # Filter out any players who don't have a fangraph ID.  We can't do
            # a lookup otherwise.
            lk = lk[lk[lk_id_system].notnull()]
            df = self.fg.scrape(lk[lk_id_system].to_list(),
                                scrape_as=scrape_type)

            # Remove any duplicates in the player list we scrape.
            df = df.drop_duplicates(scrape_id_system)

            # In case we weren't able to look up everyone, trim off the players
            # in lk who we could not find.  Both df and lk must end up matching
            # when we construct the DataFrame.
            if len(lk.index) > len(df.index):
                lk = lk[lk[lk_id_system].isin(df[scrape_id_system])]
                assert(len(lk.index) == len(df.index))

            # Need to sort both the roster lookup and the scrape data by
            # fangraph ID.  They both need to be in the same sorted order
            # because we are extracting out the espn_ID from lk and adding it
            # to the scrape data data frame.
            lk = lk.sort_values(by=lk_id_system, axis=0)
            df = df.sort_values(by=scrape_id_system, axis=0)
            logger.info(lk)
            logger.info(df)

            espn_ids = lk.espn_id.to_list()
            num_GS = self._num_gs(espn_ids)
            df = df.assign(WK_GS=pd.Series(num_GS, index=df.index))
            team_abbrevs = self._lookup_teams(df.Team.to_list(), team_has)
            df = df.assign(team=pd.Series(team_abbrevs, index=df.index))
            wk_g = self._num_games_for_teams(team_abbrevs, True)
            df = df.assign(WK_G=pd.Series(wk_g, index=df.index))
            sea_g = self._num_games_for_teams(team_abbrevs, False)
            df = df.assign(SEASON_G=pd.Series(sea_g, index=df.index))
            roster_type = [roster_type] * len(df.index)
            df = df.assign(roster_type=pd.Series(roster_type, index=df.index))
            e_pos = [e[1]["eligible_positions"] for e in lk.iterrows()]
            df = df.assign(eligible_positions=pd.Series(e_pos, index=df.index))

            # Filter out some of the batting categories from pitchers
            if roster_type == 'P':
                for hit_stat in ['HR', 'RBI', 'AVG', 'OBP', 'R', 'SB']:
                    df[hit_stat] = np.nan

            res = res.append(df, sort=False)

        # Add a column that will track the selected position of each player.
        # It is currently set to NaN since other modules fill that in.
        res = res.assign(selected_position=np.nan)

        return res

    def _lookup_teams(self, teams, team_has):
        if team_has == 'just_name':
            return self._lookup_teams_by_name(teams)
        else:
            return self._lookup_teams_by_abbrev(teams)

    def _lookup_teams_by_name(self, teams):
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

    def _lookup_teams_by_abbrev(self, teams):
        a = []
        abbrev_remap = {"WAS": "WSN"}
        for team in teams:
            if type(team) is str and team != 'FAA':
                if team in abbrev_remap:
                    team = abbrev_remap[team]
                a.append(team)
            else:
                a.append(None)
        return a

    def _find_roster(self, position_type, roster, fail_on_missing=True):
        lk = None
        for plyr in roster:
            if plyr['position_type'] != position_type or \
                    ('selected_position' in plyr and
                     plyr['selected_position'] in ['BN', 'DL']):
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
                    name = utils.normalized(name)
                    one_lk = self.id_lookup.from_names([name])

            if len(one_lk.index) == 0:
                if fail_on_missing:
                    raise ValueError("Was not able to lookup player: {}".
                                     format(plyr))
                else:
                    continue

            ep_series = pd.Series([plyr["eligible_positions"]], dtype="object",
                                  index=one_lk.index)
            one_lk = one_lk.assign(eligible_positions=ep_series)

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


def init_scrapers():
    fg = GenericCsvScraper('BaseballHQ_M_B_P.csv', 'BaseballHQ_M_P_P.csv')
    ts = baseball_reference.TeamScraper()
    tss = baseball_reference.TeamSummaryScraper()
    return (fg, ts, tss)


def init_prediction_builder(lg, cfg):
    (fg, ts, tss) = init_scrapers()
    (start_date, end_date) = lg.week_date_range(lg.current_week() + 1)
    es = espn.ProbableStartersScraper(start_date, end_date)
    return Builder(lg, fg, ts, es, tss)


class GenericCsvScraper:
    def __init__(self, batter_proj_file, pitcher_proj_file):
        self.batter_cache = pd.read_csv(batter_proj_file,
                                        encoding='iso-8859-1',
                                        header=1,
                                        skipfooter=1,
                                        engine='python')
        self.pitcher_cache = pd.read_csv(pitcher_proj_file,
                                         encoding='iso-8859-1',
                                         header=1,
                                         skipfooter=1,
                                         engine='python')

    def scrape(self, mlb_ids, scrape_as):
        """Scrape the csv file and return those match mlb_ids"""
        cache = self._get_cache(scrape_as)
        df = cache[cache['MLBAM ID'].isin(mlb_ids)]
        df['Name'] = df['Firstname'] + " " + df['Lastname']
        df = df.rename(columns={"Tm": "Team"})
        if scrape_as == fangraphs.ScrapeType.PITCHER:
            df = df.rename(columns={"Sv": "SV", "Hld": "HLD", "K": "SO"})
        return df

    def _get_cache(self, scrape_as):
        if scrape_as == fangraphs.ScrapeType.HITTER:
            return self.batter_cache
        else:
            return self.pitcher_cache


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
        print("{:4}: {:20}   "
              "{}/{}/{}/{}/{}/{}".
              format('B', '', 'R', 'HR', 'RBI', 'SB', 'AVG', 'OBP'))
        for pos in ['C', '1B', '2B', '3B', 'SS', 'LF', 'CF', 'RF', 'Util',
                    'SP', 'SP', 'SP', 'SP', 'SP', 'RP', 'RP', 'RP', 'RP',
                    'RP']:
            for plyr in lineup:
                if plyr['selected_position'] == pos:
                    if pos in ["SP", "RP"]:
                        print("{:4}: {:20}   "
                              "{:.1f}/{:.1f}/{:.1f}/{:.1f}/{:.3f}/{:.3f}".
                              format(plyr['selected_position'],
                                     plyr['name'], plyr['W'], plyr['HLD'],
                                     plyr['SV'], plyr['SO'], plyr['ERA'],
                                     plyr['WHIP']))
                    else:
                        print("{:4}: {:20}   "
                              "{:.1f}/{:.1f}/{:.1f}/{:.1f}/{:.3f}/{:.3f}".
                              format(plyr['selected_position'], plyr['name'],
                                     plyr['R'], plyr['HR'], plyr['RBI'],
                                     plyr['SB'], plyr['AVG'], plyr['OBP']))
                    if pos == 'Util':
                        print("")
                        print("{:4}: {:20}   "
                              "{}/{}/{}/{}/{}/{}".
                              format('P', '', 'W', 'HLD', 'SV', 'SO', 'ERA',
                                     'WHIP'))
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
        if pos in ['C', '1B', '2B', 'SS', '3B', 'LF', 'CF', 'RF', 'Util']:
            print("{:20}   {}/{}/{}/{}/{}/{}".format('name', 'R', 'HR', 'RBI',
                                                     'SB', 'AVG', 'OBP'))
        else:
            print("{:20}   {}/{}/{}/{}/{}/{}".format('name', 'W', 'HLD', 'SV',
                                                     'SO', 'ERA', 'WHIP'))

    def printPlayer(self, pos, plyr):
        if pos in ['C', '1B', '2B', 'SS', '3B', 'LF', 'CF', 'RF', 'Util']:
            print("{:20}   {:.1f}/{:.1f}/{:.1f}/{:.1f}/{:.3f}/{:.3f}".
                  format(plyr[1]['name'], plyr[1]['R'], plyr[1]['HR'],
                         plyr[1]['RBI'], plyr[1]['SB'], plyr[1]['AVG'],
                         plyr[1]['OBP']))
        else:
            print("{:20}   {:.1f}/{:.1f}/{:.1f}/{:.1f}/{:.3f}/{:.3f}".
                  format(plyr[1]['name'], plyr[1]['W'], plyr[1]['HLD'],
                         plyr[1]['SV'], plyr[1]['SO'], plyr[1]['ERA'],
                         plyr[1]['WHIP']))


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
                if plyr[1]['SEASON_G'] > 0:
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

    def is_counting_stat(self, stat):
        return stat in ['R', 'HR', 'RBI', 'SB', 'W', 'SO', 'SV', 'HLD']

    def is_highest_better(self, stat):
        return stat not in ['ERA', 'WHIP']
