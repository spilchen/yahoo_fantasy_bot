#!/usr/bin/python

import os
import pickle
import time
from baseball_scraper import fangraphs, baseball_reference, espn
from yahoo_baseball_assistant import prediction


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
    fg = fangraphs.Scraper("Depth Charts (RoS)")
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
