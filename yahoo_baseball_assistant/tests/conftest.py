#!/bin/python

import os
import pandas as pd
import pytest
from yahoo_baseball_assistant import hitting
from baseball_id.factory import Factory


def gen_sample_batting_stats(start_date, end_date):
    """Generate mock data for the batting_stats_range API"""
    dir_path = os.path.dirname(os.path.realpath(__file__))
    return(pd.read_csv(dir_path + "/sample.batting_stats_range.csv"))


@pytest.fixture()
def hitting_builder():
    bldr = hitting.Builder(None)
    bldr.set_stats_source(gen_sample_batting_stats)
    bldr.set_id_lookup(Factory.create_fake())
    yield bldr
