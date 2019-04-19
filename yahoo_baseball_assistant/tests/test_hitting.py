#!/bin/python

from yahoo_baseball_assistant import hitting
import pytest
import pandas as pd
import os


def gen_sample_batting_stats(start_date, end_date):
    """Generate mock data for the batting_stats_range API"""
    dir_path = os.path.dirname(os.path.realpath(__file__))
    return(pd.read_csv(dir_path + "/sample.batting_stats_range.csv"))


def test_build_model_dataset_with_bad_parms():
    with pytest.raises(Exception):
        hitting.build_model_dataset(None, 'HR')
    with pytest.raises(Exception):
        hitting.build_model_dataset('2001-01-12', 'HR')
    with pytest.raises(Exception):
        hitting.build_model_dataset(['2001-01-12'], 'HR')


def test_limit_for_small_PA():
    dt = ['2018-09-01', '2018-09-10']
    ds_full = hitting.build_model_dataset(dt, 'HR',
                                          generator=gen_sample_batting_stats)
    ds_filt = hitting.build_model_dataset(dt, 'HR',
                                          generator=gen_sample_batting_stats,
                                          min_PA=120)
    assert(len(ds_filt) < len(ds_full))


def test_build_predict_dataset_with_parms():
    with pytest.raises(Exception):
        hitting.build_predict_dataset(None, generator=gen_sample_batting_stats)
    with pytest.raises(Exception):
        hitting.build_predict_dataset('2001-01-12',
                                      generator=gen_sample_batting_stats)


def test_build_predict_dataset():
    dt = ['2018-09-01', '2018-09-10']
    df = hitting.build_predict_dataset(dt, generator=gen_sample_batting_stats)
    assert(len(df) > 0)
