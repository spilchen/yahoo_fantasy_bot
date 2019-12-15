#!/usr/bin/python

import logging
import pandas as pd
import tempfile

logger = logging.getLogger()


class Yahoo:
    """
    Class that reads stats from Yahoo! to form the basis for projections

    :param lg: Constructed League object
    :type lg: yahoo_fantasy_api.League
    :param cfg: Config details
    :type cfg: configparser
    """
    def __init__(self, lg, cfg):
        self.lg = lg
        self.cfg = cfg

    def scrape(self):
        """
        Pull the player stats from Yahoo!
        """
        print("Downloading player stats from Yahoo...")
        logger.info('Scraping stats for waivers')
        stats = self._scrape_players(self.lg.waivers())
        logger.info('Scraping stats for taken players')
        stats += self._scrape_players(self.lg.taken_players())
        logger.info('Scraping stats for free agents players')
        stats += self._scrape_players(self.lg.free_agents(None))
        logger.info('Scraped stats for {} players'.format(len(stats)))

        skaters_fn = self._create_csv(stats, 'P', 'skaters.csv')
        goalies_fn = self._create_csv(stats, 'G', 'goalies.csv')
        logger.info('File names created: skaters={}, goalies={}'.
                    format(skaters_fn, goalies_fn))
        return {'skaters': skaters_fn, 'goalies': goalies_fn}

    def fetch_csv_details(self):
        fns = self.scrape()
        return {'skaters': {'file_name': fns['skaters'],
                            'index_col': 'name',
                            'header': 0},
                'goalies': {'file_name': fns['goalies'],
                            'index_col': 'name',
                            'header': 0}}

    def _scrape_players(self, plyrs):
        ids = [e['player_id'] for e in plyrs]
        return self.lg.player_stats(ids, 'season')

    def _create_csv(self, stats, position_type, fn_suffix):
        filtered_stats = self._filter_stats(stats, position_type)
        df = pd.DataFrame(data=filtered_stats)
        tf = tempfile.NamedTemporaryFile(suffix=fn_suffix, delete=False)
        df.to_csv(tf.name)
        return tf.name

    def _filter_stats(self, stats, position_type):
        return [e for e in stats if e['position_type'] == position_type]


class CSV:
    '''
    Class that pulls details about stats predictions from csv in config file
    '''
    def __init__(self, cfg):
        self.cfg = cfg

    def fetch_csv_details(self):
        assert(self.cfg['Prediction']['source'] == 'csv')
        csv_details = {'skaters':
                       self.csv_details_from_cfg_for_pred('skaters_csv'),
                       'goalies':
                       self.csv_details_from_cfg_for_pred('goalies_csv')}
        return csv_details

    def csv_details_from_cfg_for_pred(self, pred):
        pcfg = self.cfg['Prediction']
        details = {'file_name': pcfg[pred + '_file'],
                   'index_col': pcfg[pred + '_index_col']}
        col_names_field = pred + '_column_names'
        if col_names_field in pcfg:
            details['column_names'] = pcfg.getlist(col_names_field)
        header_field = pred + '_header'
        if header_field in pcfg:
            details['header'] = pcfg[header_field]
        return details
