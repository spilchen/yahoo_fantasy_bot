#!/usr/bin/python

import pickle


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
