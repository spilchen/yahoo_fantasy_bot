#!/bin/python

from yahoo_baseball_assistant import baseball_date
from datetime import date, timedelta


def test_is_baseball_played():
    assert baseball_date.is_game_on(date(2019, 1, 1)) is False
    assert baseball_date.is_game_on(date(2018, 9, 28)) is True


def test_interval():
    dt = date(2019, 7, 3)
    g = baseball_date.Generator(num_pairs=6, range_day_len=30, end_date=dt)
    dts = g.produce()
    assert(len(dts) == 6)
    assert(dts[5][1] == baseball_date.to_s(dt))
    start_of_last_range = dt - timedelta(days=30)
    assert(dts[5][0] == baseball_date.to_s(start_of_last_range))
