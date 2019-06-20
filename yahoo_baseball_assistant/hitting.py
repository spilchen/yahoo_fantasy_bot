#!/bin/python

from baseball_scraper import fangraphs
from baseball_id import Lookup
import pandas as pd


class Builder:
    """Class that constructs prediction datasets for hitters.

    The datasets it generates are fully populated with projected stats.  The
    projection stats are scraped from fangraphs.com.
    """
    def __init__(self):
        self.id_lookup = Lookup
        self.fg = fangraphs.Scraper()

    def set_id_lookup(self, lk):
        self.id_lookup = lk

    def set_fg_scraper(self, fg):
        self.fg = fg

    def roster_predict(self, roster):
        """Build a dataset of predictions for a given roster

        :param roster: Set of players to generate the predictions for
        :type team: yahoo_fantasy_api.Team
        :return: Dataset of predictions
        :rtype: DataFrame
        """
        yahoo_ids = [x['player_id'] for x in roster if
                     x['position_type'] == 'B']
        lk = self.id_lookup.from_yahoo_ids(yahoo_ids)
        df = pd.DataFrame()
        for fg_id in lk['fg_id']:
            self.fg.set_player_id(fg_id)
            df = df.append(self.fg.scrape(instance='ZiPS (R)'),
                           ignore_index=True)
        if len(df.index) > 0:
            df['player_id'] = pd.Series(yahoo_ids, index=df.index)
        return df

    def _cache_roster(self, roster):
        yahoo_ids = [x['player_id'] for x in roster if
                     x['position_type'] == 'B']
        lk = self.id_lookup.from_yahoo_ids(yahoo_ids)
        for fg_id in lk['fg_id']:
            if fg_id not in self.scrape_cache:
                self.scrape_cache[fg_id] = fangraphs.Scraper(player_id=fg_id)
