#!/bin/python

from baseball_scraper import fangraphs
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
    def __init__(self, team, week):
        self.id_lookup = Lookup
        self.fg = fangraphs.Scraper()
        self.team = team
        self.week = week
        self.roster = None
        if team is not None:
            self.roster = team.roster(week)

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
        for fg_id, name in zip(lk['fg_id'], lk['yahoo_name']):
            self.fg.set_player_id(fg_id)
            scrape_series = self.fg.scrape(instance='Steamer (R)').iloc(0)[0]
            meta_series = pd.Series(data=[fg_id, name],
                                    index=['fg_id', 'name'])
            combined_series = scrape_series.append(meta_series)
            df = df.append(combined_series, ignore_index=True)
        return df

    def _find_roster(self):
        yahoo_ids = [x['player_id'] for x in self.roster if
                     (x['position_type'] == 'B' and
                      x['selected_position'] != 'BN')]
        lk = self.id_lookup.from_yahoo_ids(yahoo_ids)
        # Do a lookup of names.  This lookup will find any player that doesn't
        # have a yahoo_id in the lookup cache.  This is done for new rookies
        # that are on the roster.
        names = [x['name'] for x in self.roster if
                 (x['position_type'] == 'B' and
                  x['selected_position'] != 'BN')]
        # Union the two lookup to have a complete picture of the roster
        lk_miss = self.id_lookup.from_names(names, filter_missing='yahoo_id')
        lk = lk.merge(lk_miss, how='outer')
        return lk
