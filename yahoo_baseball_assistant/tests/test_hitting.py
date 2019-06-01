#!/bin/python

import pytest


def test_build_model_dataset_with_bad_parms(hitting_builder):
    hitting_builder.set_date_ranges(None)
    with pytest.raises(Exception):
        hitting_builder.model_dataset('HR')
    hitting_builder.set_date_ranges('2001-01-12')
    with pytest.raises(Exception):
        hitting_builder.model_dataset('HR')
    hitting_builder.set_date_ranges(['2001-01-12'])
    with pytest.raises(Exception):
        hitting_builder.model_dataset('HR')


def test_limit_for_small_PA(hitting_builder):
    dt = ['2018-09-01', '2018-09-10']
    hitting_builder.set_date_ranges(dt)
    ds_full = hitting_builder.model_dataset('HR')
    hitting_builder.set_min_PA(120)
    ds_filt = hitting_builder.model_dataset('HR')
    assert(len(ds_filt) < len(ds_full))


def test_build_predict_dataset_with_parms(hitting_builder):
    hitting_builder.set_date_ranges(None)
    with pytest.raises(Exception):
        hitting_builder.predict_dataset()
    hitting_builder.set_date_ranges('2001-01-12')
    with pytest.raises(Exception):
        hitting_builder.predict_dataset()


def test_build_predict_dataset(hitting_builder):
    dt = [['2018-09-01', '2018-09-10']]
    hitting_builder.set_date_ranges(dt)
    df = hitting_builder.predict_dataset()
    assert(len(df) > 0)


def test_build_predict_dataset_with_bad_parms(hitting_builder):
    # Expect a list of dates with a single entry
    hitting_builder.set_date_ranges(['2018-09-01', '2018-09-10'])
    with pytest.raises(Exception):
        hitting_builder.predict_dataset()
    # Expect a range with start/end date
    hitting_builder.set_date_ranges([['2018-09-01']])
    with pytest.raises(Exception):
        hitting_builder.predict_dataset()
    # Expect a range with 2 dates (start + end)
    hitting_builder.set_date_ranges([['2018-09-01', '2018-09-10',
                                      '2018-09-30']])
    with pytest.raises(Exception):
        hitting_builder.predict_dataset()


def test_build_dataset_for_roster(hitting_builder):
    hitting_builder.set_date_ranges([['2018-09-01', '2018-09-10']])
    hitting_builder.dataset_for_roster([{'player_id': 595918,
                                         'position_type': 'B'}])
