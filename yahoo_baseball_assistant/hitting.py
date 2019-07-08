#!/bin/python

from baseball_scraper import fangraphs, baseball_reference
from baseball_id import Lookup
import pandas as pd


class Builder:
    """Class that constructs prediction datasets for hitters.

    The datasets it generates are fully populated with projected stats.  The
    projection stats are scraped from fangraphs.com.

    :param team: Yahoo! Team to do the predictions for
    :type team: yahoo_fantasy_api.team.Team
    :param week: Week number to build the predictions for
    :type week: int
    """
    def __init__(self, lg, team):
        self.id_lookup = Lookup
        self.fg = fangraphs.Scraper()
        self.team = team
        self.week = lg.current_week() + 1
        if self.week >= lg.end_week():
            raise RuntimeError("Season over no more weeks to predict")
        (self.start_date, self.end_date) = lg.week_date_range(self.week)
        self.mlb_team = {}
        self.roster = None
        if team is not None:
            self.roster = team.roster(self.week)

    def set_id_lookup(self, lk):
        self.id_lookup = lk

    def set_fg_scraper(self, fg):
        self.fg = fg

    def set_roster(self, roster):
        self.roster = roster

    def roster_predict(self):
        """Build a dataset of predictions for a given roster

        :return: Dataset of predictions
        :rtype: DataFrame
        """
        lk = self._find_roster()
        df = pd.DataFrame()
        for fg_id, name, team in zip(lk['fg_id'], lk['yahoo_name'],
                                     lk['mlb_team']):
            # TODO: use lahman database instead of this mapping.  The
            # abbreviation from baseball_id is different then at
            # baseball_reference.
            if team == 'WSH':
                team = 'WSN'
            if team == 'CWS':
                team = 'CHW'
            self.fg.set_player_id(fg_id)
            scrape_series = self.fg.scrape(instance='Steamer (R)').iloc(0)[0]
            wk_games = self._num_games_for_team(team)
            meta_series = pd.Series(data=[fg_id, name, team, wk_games],
                                    index=['fg_id', 'name', 'team',
                                           'WK_G'])
            combined_series = scrape_series.append(meta_series)
            df = df.append(combined_series, ignore_index=True)
        return df

    def sum_prediction(self, df):
        """Summarize the predictions into stat categories

        :param df: Roster predictions to summarize
        :type df: DataFrame
        :return: Summarized predictions
        :rtype: Series
        """
        res = pd.Series()
        for stat in ['R', 'HR', 'RBI', 'SB', 'AB', 'H', 'BB']:
            val = 0
            for plyr in df.iterrows():
                if plyr[1]['G'] > 0:
                    val += plyr[1][stat] / plyr[1]['G'] * plyr[1]['WK_G']
            res = res.append(pd.Series(data=[val], index=[stat]))

        # Handle ratio stats
        if res['AB'] > 0:
            avg = res['H'] / res['AB']
        else:
            avg = 0
        if res['AB'] + res['BB'] > 0:
            oba = (res['H'] + res['BB']) / (res['AB'] + res['BB'])
        else:
            oba = 0
        res = res.append(pd.Series(data=[avg, oba], index=['AVG', 'OBP']))

        # Delete the temporary values used to calculate the ratio stats
        res = res.drop(index=['AB', 'H', 'BB'])

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
        for l, r in zip(left, right):
            if l > r:
                win += 1
            elif r > l:
                loss += 1
        return (win, loss)

    def _find_roster(self):
        lk = None
        for plyr in self.roster:
            if plyr['position_type'] != 'B' or \
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
                    one_lk = self.id_lookup.from_names([name])

            if len(one_lk.index) == 0:
                raise ValueError("Was not able to lookup player: {}".format(
                    plyr))

            if lk is None:
                lk = one_lk
            else:
                lk = lk.merge(one_lk, how='outer')
        return lk

    def _num_games_for_team(self, abrev):
        if abrev not in self.mlb_team:
            self.mlb_team[abrev] = baseball_reference.TeamScraper(abrev)
            self.mlb_team[abrev].set_date_range(self.start_date, self.end_date)
        df = self.mlb_team[abrev].scrape()
        return len(df.index)
