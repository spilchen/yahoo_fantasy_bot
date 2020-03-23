#!/usr/bin/python

import datetime
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
        self.game_code = lg.settings()['game_code']

    def fetch_csv_details(self):
        """
        Pull the player stats from Yahoo!
        """
        self.cfg['Prediction']['source'] == 'yahoo'

        print("Downloading player stats from Yahoo...")
        logger.info('Scraping stats for waivers')
        stats = self._scrape_players(self.lg.waivers())
        logger.info('Scraping stats for taken players')
        stats += self._scrape_players(self.lg.taken_players())
        logger.info('Scraping stats for free agents players')
        stats += self._scrape_players(self.lg.free_agents(None))
        logger.info('Scraped stats for {} players'.format(len(stats)))

        if self.game_code == 'nhl':
            skaters_fn = self._create_csv(stats, 'P', 'skaters.csv')
            goalies_fn = self._create_csv(stats, 'G', 'goalies.csv')
            logger.info('File names created: skaters={}, goalies={}'.
                        format(skaters_fn, goalies_fn))
            return {'skaters': {'file_name': skaters_fn,
                                'index_col': 'name',
                                'header': 0},
                    'goalies': {'file_name': goalies_fn,
                                'index_col': 'name',
                                'header': 0}}
        elif self.game_code == 'mlb':
            hitters_fn = self._create_csv(stats, 'B', 'hitters.csv')
            pitchers_fn = self._create_csv(stats, 'P', 'pitcher.csv')
            logger.info('File names created: hitters={}, pitchers={}'.
                        format(hitters_fn, pitchers_fn))
            return {'hitters': {'file_name': hitters_fn,
                                'index_col': 'name',
                                'header': 0},
                    'pitchers': {'file_name': pitchers_fn,
                                 'index_col': 'name',
                                 'header': 0}}
        else:
            raise RuntimeError("Unsupported game code: {}".format(
                self.game_code))

    def _scrape_players(self, plyrs):
        ids = [e['player_id'] for e in plyrs]
        parms = self._get_stat_parms()
        return self.lg.player_stats(ids, parms['req_type'],
                                    season=parms['season'])

    def _get_stat_parms(self):
        src = self.cfg['Prediction']['source']
        if src == 'yahoo' or src == 'yahoo_season':
            return {'req_type': 'season', 'season': None}
        elif src == 'yahoo_lastseason':
            this_year = datetime.datetime.now().year
            return {'req_type': 'season', 'season': this_year - 1}
        elif src == 'yahoo_lastmonth':
            return {'req_type': 'lastmonth', 'season': None}
        else:
            raise RuntimeError('Unknown yahoo source: {}'.format(src))

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
    def __init__(self, lg, cfg):
        self.lg = lg
        self.cfg = cfg
        self.game_code = lg.settings()['game_code']

    def fetch_csv_details(self):
        assert(self.cfg['Prediction']['source'] == 'csv')
        if self.game_code == 'nhl':
            return {'skaters':
                    self.csv_details_from_cfg_for_pred('skaters_csv'),
                    'goalies':
                    self.csv_details_from_cfg_for_pred('goalies_csv')}
        elif self.game_code == 'mlb':
            return {'hitters':
                    self.csv_details_from_cfg_for_pred('hitters_csv'),
                    'pitchers':
                    self.csv_details_from_cfg_for_pred('pitchers_csv')}
        else:
            raise RuntimeError("Game code not supported " + self.game_code)

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


def read_csv(csv_detail):
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
