#!/usr/bin/python

import pandas as pd
import numpy as np
import pytest
from conftest import RBLDR_COLS


def test_fit_empty(bldr, empty_roster):
    plyr = pd.Series(["Joe", ['C', '1B', '2B'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(empty_roster, plyr)
    print(r)
    assert(len(r) == 1)
    assert(r[0]['selected_position'] == 'C')


def test_fit_pick_2nd_pos(bldr, empty_roster):
    plyr = pd.Series(["Jack", ['C', '1B', '2B'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(empty_roster, plyr)
    plyr = pd.Series(["Kyle", ['C', '1B', '2B'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    print(r)
    assert(len(r) == 2)
    assert(r[0]['selected_position'] == 'C')
    assert(r[0]['name'] == 'Jack')
    assert(r[1]['selected_position'] == '1B')
    assert(r[1]['name'] == 'Kyle')


def test_fit_move_multi_pos(bldr, empty_roster):
    plyr = pd.Series(["Cecil", ['C', '1B', '3B', 'LF'], np.nan],
                     index=RBLDR_COLS)
    r = bldr.fit_if_space(empty_roster, plyr)
    assert(len(r) == 1)
    assert(r[0]['selected_position'] == 'C')
    plyr = pd.Series(["Ernie", ['C'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    assert(len(r) == 2)
    assert(r[0]['selected_position'] == '1B')
    assert(r[0]['name'] == 'Cecil')
    assert(r[1]['selected_position'] == 'C')
    assert(r[1]['name'] == 'Ernie')
    plyr = pd.Series(["Fred", ['1B'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    assert(len(r) == 3)
    assert(r[0]['selected_position'] == '3B')
    assert(r[1]['selected_position'] == 'C')
    assert(r[2]['selected_position'] == '1B')
    assert(r[2]['name'] == 'Fred')
    plyr = pd.Series(["George", ['LF', 'RF'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    assert(len(r) == 4)
    assert(r[3]['selected_position'] == 'LF')
    assert(r[3]['name'] == 'George')
    plyr = pd.Series(["Rance", ['3B'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    assert(len(r) == 5)
    assert(r[0]['selected_position'] == 'LF')
    assert(r[0]['name'] == 'Cecil')
    assert(r[3]['selected_position'] == 'RF')
    assert(r[3]['name'] == 'George')
    assert(r[4]['selected_position'] == '3B')
    assert(r[4]['name'] == 'Rance')


def test_fit_failure(bldr, empty_roster):
    plyr = pd.Series(["Cecil", ['1B', '3B', 'LF', 'C'], np.nan],
                     index=RBLDR_COLS)
    r = bldr.fit_if_space(empty_roster, plyr)
    assert(len(r) == 1)
    plyr = pd.Series(["Fred", ['1B', 'LF'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    assert(len(r) == 2)
    plyr = pd.Series(["Rance", ['3B', '2B'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    assert(len(r) == 3)
    plyr = pd.Series(["Domaso", ['2B'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    assert(len(r) == 4)
    plyr = pd.Series(["George", ['LF', 'RF'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    assert(len(r) == 5)
    plyr = pd.Series(["Jesse", ['RF', 'CF'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    assert(len(r) == 6)
    plyr = pd.Series(["Lloyd", ['CF'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    print(r)
    assert(len(r) == 7)
    assert(r[0]['name'] == 'Cecil')
    assert(r[0]['selected_position'] == 'C')
    assert(r[1]['name'] == 'Fred')
    assert(r[1]['selected_position'] == '1B')
    assert(r[2]['name'] == 'Rance')
    assert(r[2]['selected_position'] == '3B')
    assert(r[3]['name'] == 'Domaso')
    assert(r[3]['selected_position'] == '2B')
    assert(r[4]['name'] == 'George')
    assert(r[4]['selected_position'] == 'LF')
    assert(r[5]['name'] == 'Jesse')
    assert(r[5]['selected_position'] == 'RF')
    assert(r[6]['name'] == 'Lloyd')
    assert(r[6]['selected_position'] == 'CF')
    plyr = pd.Series(["Ernie", ['C', '1B'], np.nan], index=RBLDR_COLS)
    with pytest.raises(LookupError):
        r = bldr.fit_if_space(r, plyr)


def test_fit_failure_cycles(bldr, empty_roster):
    plyr = pd.Series(["Cecil", ['1B', '3B', 'LF'], np.nan],
                     index=RBLDR_COLS)
    r = bldr.fit_if_space(empty_roster, plyr)
    plyr = pd.Series(["Rance", ['1B', '3B', 'LF'], np.nan],
                     index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    plyr = pd.Series(["Garth", ['1B', '3B', 'LF'], np.nan],
                     index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    plyr = pd.Series(["George", ['LF'], np.nan], index=RBLDR_COLS)
    with pytest.raises(LookupError):
        r = bldr.fit_if_space(r, plyr)
    print(r)
    assert(len(r) == 3)
    assert(r[0]['name'] == 'Cecil')
    assert(r[0]['selected_position'] == '1B')
    assert(r[1]['name'] == 'Rance')
    assert(r[1]['selected_position'] == '3B')
    assert(r[2]['name'] == 'Garth')
    assert(r[2]['selected_position'] == 'LF')


def test_fit_enumerate_3(bldr, empty_roster):
    plyr = pd.Series(["Ben", ['1B', '3B', 'LF'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(empty_roster, plyr)
    plyr = pd.Series(["Rance", ['1B', '3B', 'LF'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    plyr = pd.Series(["Garth", ['1B', '3B', 'LF'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    assert(r[0]['name'] == 'Ben')
    assert(r[0]['selected_position'] == '1B')
    assert(r[1]['name'] == 'Rance')
    assert(r[1]['selected_position'] == '3B')
    assert(r[2]['name'] == 'Garth')
    assert(r[2]['selected_position'] == 'LF')
    plyr = pd.Series(["George", ['LF'], np.nan], index=RBLDR_COLS)
    itr = bldr.enumerate_fit(r, plyr)
    er = next(itr)
    print(er)
    assert(er[0]['name'] == 'Ben')
    assert(np.isnan(er[0]['selected_position']))
    assert(er[1]['name'] == 'Rance')
    assert(er[1]['selected_position'] == '3B')
    assert(er[2]['name'] == 'Garth')
    assert(er[2]['selected_position'] == '1B')
    assert(er[3]['name'] == 'George')
    assert(er[3]['selected_position'] == 'LF')
    er = next(itr)
    print(er)
    assert(er[0]['name'] == 'Ben')
    assert(er[0]['selected_position'] == '1B')
    assert(er[1]['name'] == 'Rance')
    assert(np.isnan(er[1]['selected_position']))
    assert(er[2]['name'] == 'Garth')
    assert(er[2]['selected_position'] == '3B')
    assert(er[3]['name'] == 'George')
    assert(er[3]['selected_position'] == 'LF')
    er = next(itr)
    print(er)
    assert(er[0]['name'] == 'Ben')
    assert(er[0]['selected_position'] == '1B')
    assert(er[1]['name'] == 'Rance')
    assert(er[1]['selected_position'] == '3B')
    assert(er[2]['name'] == 'Garth')
    assert(np.isnan(er[2]['selected_position']))
    assert(er[3]['name'] == 'George')
    assert(er[3]['selected_position'] == 'LF')
    with pytest.raises(StopIteration):
        er = next(itr)


def test_fit_enumerate_2(bldr, empty_roster):
    plyr = pd.Series(["Paul", ['3B'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(empty_roster, plyr)
    plyr = pd.Series(["Robin", ['CF', 'SS'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    plyr = pd.Series(["Gorman", ['CF'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    assert(r[0]['name'] == 'Paul')
    assert(r[0]['selected_position'] == '3B')
    assert(r[1]['name'] == 'Robin')
    assert(r[1]['selected_position'] == 'SS')
    assert(r[2]['name'] == 'Gorman')
    assert(r[2]['selected_position'] == 'CF')
    plyr = pd.Series(["Kevin", ['CF', 'SS'], np.nan], index=RBLDR_COLS)
    itr = bldr.enumerate_fit(r, plyr)
    er = next(itr)
    print(er)
    assert(er[0]['selected_position'] == '3B')
    assert(np.isnan(er[1]['selected_position']))
    assert(er[2]['selected_position'] == 'CF')
    assert(er[3]['selected_position'] == 'SS')
    er = next(itr)
    print(er)
    assert(er[0]['selected_position'] == '3B')
    assert(er[1]['selected_position'] == 'SS')
    assert(np.isnan(er[2]['selected_position']))
    assert(er[3]['selected_position'] == 'CF')
    with pytest.raises(StopIteration):
        er = next(itr)


def test_fit_with_duplicate_positions(bldr, empty_roster):
    plyr = pd.Series(["Stieb", ['SP'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(empty_roster, plyr)
    plyr = pd.Series(["Clancy", ['SP'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    plyr = pd.Series(["Cerutti", ['SP'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    plyr = pd.Series(["Flanigan", ['SP'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    plyr = pd.Series(["Alexander", ['SP'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    plyr = pd.Series(["Fernandez", ['SP'], np.nan], index=RBLDR_COLS)
    with pytest.raises(LookupError):
        r = bldr.fit_if_space(r, plyr)
    plyr = pd.Series(["Claudell", ['SP', 'RP'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    print(r)
    assert(len(r) == 6)
    assert(r[5]['name'] == 'Claudell')
    assert(r[5]['selected_position'] == 'RP')


def test_fit_with_multiple_duplicate_positions_1(bldr, empty_roster):
    plyr = pd.Series(["Stieb", ['SP'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(empty_roster, plyr)
    plyr = pd.Series(["Clancy", ['SP'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    plyr = pd.Series(["Cerutti", ['SP', 'RP'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    plyr = pd.Series(["Flanigan", ['SP', 'RP'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    plyr = pd.Series(["Alexander", ['SP', 'RP'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    print(r)
    for plyr in r:
        assert(plyr.selected_position == 'SP')
    plyr = pd.Series(["Fernandez", ['SP'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    plyr = pd.Series(["Claudell", ['SP'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    plyr = pd.Series(["Key", ['SP'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    plyr = pd.Series(["Guzman", ['SP'], np.nan], index=RBLDR_COLS)
    print(r)
    for i in [2, 3, 4]:
        assert(r[i]['selected_position'] == 'RP')
    with pytest.raises(LookupError):
        r = bldr.fit_if_space(r, plyr)


def test_fit_with_multiple_duplicate_positions_2(bldr, empty_roster):
    plyr = pd.Series(["Martinez", ['LF', 'RF', 'Util'], np.nan],
                     index=RBLDR_COLS)
    r = bldr.fit_if_space(empty_roster, plyr)
    plyr = pd.Series(["Murphy", ['1B', '2B', 'Util'], np.nan],
                     index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    plyr = pd.Series(["Arenado", ['3B', 'Util'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    plyr = pd.Series(["Arraez", ['2B', '3B', 'LF', 'Util'], np.nan],
                     index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    plyr = pd.Series(["Soto", ['LF', 'Util'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    plyr = pd.Series(["Daza", ['CF', 'Util'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    plyr = pd.Series(["Flores", ['1B', '2B', '3B', 'Util'], np.nan],
                     index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    print(r)
    expected_positions = ['RF', '2B', 'Util', '3B', 'LF', 'CF', '1B']
    for plyr, exp_pos in zip(r, expected_positions):
        assert(plyr['selected_position'] == exp_pos)


def test_fit_enumerate_dup_position(bldr, empty_roster):
    plyr = pd.Series(["Henke", ['RP'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(empty_roster, plyr)
    plyr = pd.Series(["Ward", ['RP'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    plyr = pd.Series(["Timlin", ['RP'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    plyr = pd.Series(["Eichorn", ['RP'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    plyr = pd.Series(["Cox", ['RP'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    plyr = pd.Series(["Castillo", ['RP'], np.nan], index=RBLDR_COLS)
    with pytest.raises(LookupError):
        r = bldr.fit_if_space(r, plyr)
    itr = bldr.enumerate_fit(r, plyr)

    def names(r):
        n = []
        for plyr in r:
            if type(plyr['selected_position']) == str:
                n.append(plyr['name'])
        return n

    er = next(itr)
    print(er)
    assert(names(er) == ['Ward', 'Timlin', 'Eichorn', 'Cox', 'Castillo'])
    er = next(itr)
    print(er)
    assert(names(er) == ['Henke', 'Timlin', 'Eichorn', 'Cox', 'Castillo'])
    er = next(itr)
    print(er)
    assert(names(er) == ['Henke', 'Ward', 'Eichorn', 'Cox', 'Castillo'])
    er = next(itr)
    print(er)
    assert(names(er) == ['Henke', 'Ward', 'Timlin', 'Cox', 'Castillo'])
    er = next(itr)
    print(er)
    assert(names(er) == ['Henke', 'Ward', 'Timlin', 'Eichorn', 'Castillo'])
    with pytest.raises(StopIteration):
        er = next(itr)


def test_selector_rank_hitters(fake_player_selector):
    ppool = fake_player_selector.ppool
    fake_player_selector.rank(['HR', 'OBP'])
    r = ppool.sort_values(by=['rank'], ascending=False)
    print(r)
    assert(len(ppool) == 15)
    itr = r.iterrows()
    (i, p) = next(itr)
    assert(p['name'] == 'McGriff')
    (i, p) = next(itr)
    assert(p['name'] == 'Gruber')
    (i, p) = next(itr)
    assert(p['name'] == 'Olerud')
    (i, p) = next(itr)
    assert(p['name'] == 'Borders')


def test_selector_rank_pitchers(fake_player_selector):
    ppool = fake_player_selector.ppool
    fake_player_selector.rank(['W', 'ERA'])
    r = ppool.sort_values(by=['rank'], ascending=False)
    print(r)
    assert(len(ppool.index) == 15)
    itr = r.iterrows()
    (i, p) = next(itr)
    print(p)
    assert(p['name'] == 'Steib')
    (i, p) = next(itr)
    print(p)
    assert(p['name'] == 'Key')
    (i, p) = next(itr)
    print(p)
    assert(p['name'] == 'Wells')
    (i, p) = next(itr)
    print(p)
    assert(p['name'] == 'Stottlemyre')
    (i, p) = next(itr)
    print(p)
    assert(p['name'] == 'Cerutti')


def test_selector_hitters_iter(fake_player_selector):
    fake_player_selector.rank(['HR', 'OBP'])
    expected_order = ["McGriff", "Gruber", "Olerud", "Borders", "Bell",
                      "Felix", "Fernandez", "Lee", "Hill", "Wilson"]
    for exp, plyr in zip(expected_order, fake_player_selector.select()):
        print(plyr)
        assert(plyr['name'] == exp)


def test_selector_pitchers_iter(fake_player_selector):
    fake_player_selector.rank(['ERA', 'W'])
    expected_order = ["Steib", "Key", "Wells", "Stottlemyre", "Cerutti"]
    for exp, plyr in zip(expected_order, fake_player_selector.select()):
        print(plyr)
        assert(plyr['name'] == exp)
