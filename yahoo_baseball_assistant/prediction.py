#!/bin/python

from baseball_scraper import fangraphs
from baseball_id import Lookup
from yahoo_baseball_assistant import utils
import pandas as pd
import numpy as np
import datetime
import logging


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
        week = lg.current_week() + 1
        (self.wk_start_date, self.wk_end_date) = lg.week_date_range(week)
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

    def predict(self, roster_cont, fail_on_missing=True, id_system='fg_id'):
        """Build a dataset of hitting and pitching predictions for the week

        The roster is inputed into this function.  It will scrape the
        predictions from fangraphs returning a DataFrame.

        The returning DataFrame is the prediction of each stat.

        :param roster_cont: Roster of players to generate predictions for
        :type roster_cont: roster.Container object
        :param fail_on_missing: True we are to fail if any player in
        roster_cont can't be found in the prediction data set.  Set this to
        false to simply filter those out.
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
            lk = lk[lk[id_system].notnull()]
            df = self.fg.scrape(lk[id_system].to_list(), scrape_as=scrape_type)

            # Remove any duplicates in the player list we scrape.
            df = df.drop_duplicates('playerid')

            # In case we weren't able to look up everyone, trim off the players
            # in lk who we could not find.  Both df and lk must end up matching
            # when we construct the DataFrame.
            if len(lk.index) > len(df.index):
                lk = lk[lk[id_system].isin(df.playerid)]
                assert(len(lk.index) == len(df.index))

            # Need to sort both the roster lookup and the scrape data by
            # fangraph ID.  They both need to be in the same sorted order
            # because we are extracting out the espn_ID from lk and adding it
            # to the scrape data data frame.
            lk = lk.sort_values(by=id_system, axis=0)
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
            e_pos = [e[1]["eligible_positions"] for e in lk.iterrows()]
            df = df.assign(eligible_positions=pd.Series(e_pos, index=df.index))
            res = res.append(df, sort=False)

        # Add a column that will track the selected position of each player.
        # It is currently set to NaN since other modules fill that in.
        df = df.assign(selected_position=np.nan)

        return res

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
