#!/bin/python

from yahoo_baseball_assistant import hitting
import pytest
import pandas as pd


def test_build_dataset_with_bad_parms():
    with pytest.raises(Exception):
        hitting.build_dataset(None, 'HR')
    with pytest.raises(Exception):
        hitting.build_dataset('2001-01-12', 'HR')
    with pytest.raises(Exception):
        hitting.build_dataset(['2001-01-12'], 'HR')


def test_limit_for_small_PA():
    def generator(start_date, end_date):
        d = {'Name': {1: 'Jose', 2: 'Ronald', 3: 'Willy', 4: 'Lane'},
             'Age': {1: 31, 2: 20, 3: 22, 4: 28},
             '#days': {1: 175, 2: 161, 3: 161, 4: 161},
             'Lev': {1: 'MLB-AL', 2: 'MLB-NL', 3: 'MLB-AL', 4: 'MLB-NL'},
             'Tm': {1: 'Chicago', 2: 'Atlanta', 3: 'Tampa Bay', 4: 'Atlanta'},
             'G': {1: 6, 2: 28, 3: 25, 4: 11},
             'PA': {1: 27, 2: 127, 3: 98, 4: 8},
             'AB': {1: 24, 2: 109, 3: 85, 4: 8},
             'R': {1: 1, 2: 20, 3: 13, 4: 5},
             'H': {1: 3, 2: 33, 3: 29, 4: 2},
             '2B': {1: 0, 2: 5, 3: 2, 4: 1},
             '3B': {1: 0, 2: 3, 3: 0, 4: 0},
             'HR': {1: 0, 2: 4, 3: 2, 4: 1},
             'RBI': {1: 0, 2: 16, 3: 11, 4: 2},
             'BB': {1: 1, 2: 16, 3: 13, 4: 0},
             'IBB': {1: 0, 2: 2, 3: 2, 4: 0},
             'SO': {1: 7, 2: 31, 3: 26, 4: 4},
             'HBP': {1: 2, 2: 1, 3: 0, 4: 0},
             'SH': {1: 0, 2: 0, 3: 0, 4: 0},
             'SF': {1: 0, 2: 1, 3: 0, 4: 0},
             'GDP': {1: 0, 2: 1, 3: 3, 4: 0},
             'SB': {1: 0, 2: 5, 3: 0, 4: 1},
             'CS': {1: 0, 2: 1, 3: 2, 4: 0},
             'BA': {1: 0.125, 2: 0.303, 3: 0.341, 4: 0.25},
             'OBP': {1: 0.222, 2: 0.394, 3: 0.429, 4: 0.25},
             'SLG': {1: 0.125, 2: 0.514, 3: 0.435, 4: 0.75},
             'OPS': {1: 0.347, 2: 0.907, 3: 0.864, 4: 1.0}}
        return pd.DataFrame(data=d)
    ds = hitting.build_dataset(['2018-09-01', '2018-09-10'], 'HR',
                               generator=generator,
                               min_PA=100)
    assert(len(ds) == 1)
