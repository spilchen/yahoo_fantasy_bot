#!/usr/bin/python

import os
import pickle
import time
from baseball_scraper import baseball_reference, espn, fangraphs
from yahoo_baseball_assistant import prediction
import pandas as pd


def pickle_if_recent(fn):
    if os.path.exists(fn):
        mtime = os.path.getmtime(fn)
        cur_time = int(time.time())
        sec_per_day = 24 * 60 * 60
        if cur_time - mtime <= sec_per_day:
            with open(fn, 'rb') as f:
                obj = pickle.load(f)
                # Don't save this to file on exit.
                obj.save_on_exit = False
                return obj
    return None


def save_prediction_builder(pred_bldr):
    if pred_bldr.save_on_exit:
        fn = "Builder.pkl"
        with open(fn, "wb") as f:
            pickle.dump(pred_bldr, f)


def save(fg, ts, tss):
    fn = "fangraphs.predictions.pkl"
    with open(fn, "wb") as f:
        pickle.dump(fg, f)
    fn = "bref.teams.pkl"
    with open(fn, "wb") as f:
        pickle.dump(ts, f)
    fn = "bref.teamsummary.pkl"
    with open(fn, "wb") as f:
        pickle.dump(tss, f)


def init_scrapers():
    fg = GenericCsvScraper('BaseballHQ_M_B_P.csv', 'BaseballHQ_M_P_P.csv')
    ts = baseball_reference.TeamScraper()
    tss = baseball_reference.TeamSummaryScraper()
    return (fg, ts, tss)


def init_prediction_builder(lg, start_date, end_date):
    pred_bldr = pickle_if_recent("Builder.pkl")
    if pred_bldr is not None:
        pred_bldr.save_on_exit = False
        return pred_bldr
    (fg, ts, tss) = init_scrapers()
    es = espn.ProbableStartersScraper(start_date, end_date)
    pred_bldr = prediction.Builder(lg, fg, ts, es, tss)
    pred_bldr.save_on_exit = True
    return pred_bldr


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
