#!/usr/bin/env python

import pandas as pd
import numpy as np
import pytest
from conftest import RBLDR_COLS
from yahoo_fantasy_bot import roster


def test_fit_empty(bldr, empty_roster):
    plyr = pd.Series([1, "Joe", ['C', '1B', '2B'], np.nan], index=RBLDR_COLS)
    rc = bldr.fit_if_space(empty_roster, plyr)
    r = rc.get_roster()
    print(r)
    assert(len(r) == 1)
    assert(r[0]['selected_position'] == 'C')


def test_fit_pick_2nd_pos(bldr, empty_roster):
    plyr = pd.Series([1, "Jack", ['C', '1B', '2B'], np.nan], index=RBLDR_COLS)
    rc = bldr.fit_if_space(empty_roster, plyr)
    plyr = pd.Series([2, "Kyle", ['C', '1B', '2B'], np.nan], index=RBLDR_COLS)
    rc = bldr.fit_if_space(rc, plyr)
    r = rc.get_roster()
    print(r)
    assert(len(r) == 2)
    assert(r[0]['selected_position'] == 'C')
    assert(r[0]['name'] == 'Jack')
    assert(r[1]['selected_position'] == '1B')
    assert(r[1]['name'] == 'Kyle')


def test_fit_move_multi_pos(bldr, empty_roster):
    plyr = pd.Series([1, "Cecil", ['C', '1B', '3B', 'LF'], np.nan],
                     index=RBLDR_COLS)
    rc = bldr.fit_if_space(empty_roster, plyr)
    r = rc.get_roster()
    assert(len(r) == 1)
    assert(r[0]['selected_position'] == 'C')
    plyr = pd.Series([2, "Ernie", ['C'], np.nan], index=RBLDR_COLS)
    rc = bldr.fit_if_space(rc, plyr)
    r = rc.get_roster()
    assert(len(r) == 2)
    assert(r[0]['selected_position'] == '1B')
    assert(r[0]['name'] == 'Cecil')
    assert(r[1]['selected_position'] == 'C')
    assert(r[1]['name'] == 'Ernie')
    plyr = pd.Series([3, "Fred", ['1B'], np.nan], index=RBLDR_COLS)
    rc = bldr.fit_if_space(rc, plyr)
    r = rc.get_roster()
    assert(len(r) == 3)
    assert(r[0]['selected_position'] == '3B')
    assert(r[1]['selected_position'] == 'C')
    assert(r[2]['selected_position'] == '1B')
    assert(r[2]['name'] == 'Fred')
    plyr = pd.Series([4, "George", ['LF', 'RF'], np.nan], index=RBLDR_COLS)
    rc = bldr.fit_if_space(rc, plyr)
    r = rc.get_roster()
    assert(len(r) == 4)
    assert(r[3]['selected_position'] == 'LF')
    assert(r[3]['name'] == 'George')
    plyr = pd.Series([5, "Rance", ['3B'], np.nan], index=RBLDR_COLS)
    rc = bldr.fit_if_space(rc, plyr)
    r = rc.get_roster()
    assert(len(r) == 5)
    assert(r[0]['selected_position'] == 'LF')
    assert(r[0]['name'] == 'Cecil')
    assert(r[3]['selected_position'] == 'RF')
    assert(r[3]['name'] == 'George')
    assert(r[4]['selected_position'] == '3B')
    assert(r[4]['name'] == 'Rance')


def test_fit_failure(bldr, empty_roster):
    plyr = pd.Series([1, "Cecil", ['1B', '3B', 'LF', 'C'], np.nan],
                     index=RBLDR_COLS)
    rc = bldr.fit_if_space(empty_roster, plyr)
    r = rc.get_roster()
    assert(len(r) == 1)
    plyr = pd.Series([2, "Fred", ['1B', 'LF'], np.nan], index=RBLDR_COLS)
    rc = bldr.fit_if_space(rc, plyr)
    r = rc.get_roster()
    assert(len(r) == 2)
    plyr = pd.Series([3, "Rance", ['3B', '2B'], np.nan], index=RBLDR_COLS)
    rc = bldr.fit_if_space(rc, plyr)
    r = rc.get_roster()
    assert(len(r) == 3)
    plyr = pd.Series([4, "Domaso", ['2B'], np.nan], index=RBLDR_COLS)
    rc = bldr.fit_if_space(rc, plyr)
    r = rc.get_roster()
    assert(len(r) == 4)
    plyr = pd.Series([5, "George", ['LF', 'RF'], np.nan], index=RBLDR_COLS)
    rc = bldr.fit_if_space(rc, plyr)
    r = rc.get_roster()
    assert(len(r) == 5)
    plyr = pd.Series([6, "Jesse", ['RF', 'CF'], np.nan], index=RBLDR_COLS)
    rc = bldr.fit_if_space(rc, plyr)
    r = rc.get_roster()
    assert(len(r) == 6)
    plyr = pd.Series([7, "Lloyd", ['CF'], np.nan], index=RBLDR_COLS)
    rc = bldr.fit_if_space(rc, plyr)
    r = rc.get_roster()
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
    plyr = pd.Series([8, "Ernie", ['C', '1B'], np.nan], index=RBLDR_COLS)
    with pytest.raises(LookupError):
        rc = bldr.fit_if_space(rc, plyr)


def test_fit_failure_cycles(bldr, empty_roster):
    plyr = pd.Series([1, "Cecil", ['1B', '3B', 'LF'], np.nan],
                     index=RBLDR_COLS)
    rc = bldr.fit_if_space(empty_roster, plyr)
    plyr = pd.Series([2, "Rance", ['1B', '3B', 'LF'], np.nan],
                     index=RBLDR_COLS)
    rc = bldr.fit_if_space(rc, plyr)
    plyr = pd.Series([3, "Garth", ['1B', '3B', 'LF'], np.nan],
                     index=RBLDR_COLS)
    rc = bldr.fit_if_space(rc, plyr)
    plyr = pd.Series([4, "George", ['LF'], np.nan], index=RBLDR_COLS)
    with pytest.raises(LookupError):
        rc = bldr.fit_if_space(rc, plyr)
    r = rc.get_roster()
    print(r)
    assert(len(r) == 3)
    assert(r[0]['name'] == 'Cecil')
    assert(r[0]['selected_position'] == '1B')
    assert(r[1]['name'] == 'Rance')
    assert(r[1]['selected_position'] == '3B')
    assert(r[2]['name'] == 'Garth')
    assert(r[2]['selected_position'] == 'LF')


def test_fit_with_lookup_error(bldr, empty_roster):
    plyr = pd.Series([1, "Ben", ['1B', '3B', 'LF'], np.nan], index=RBLDR_COLS)
    rc = bldr.fit_if_space(empty_roster, plyr)
    plyr = pd.Series([2, "Rance", ['1B', '3B', 'LF'], np.nan],
                     index=RBLDR_COLS)
    rc = bldr.fit_if_space(rc, plyr)
    plyr = pd.Series([3, "Garth", ['1B', '3B', 'LF'], np.nan],
                     index=RBLDR_COLS)
    rc = bldr.fit_if_space(rc, plyr)
    r = rc.get_roster()
    assert(r[0]['name'] == 'Ben')
    assert(r[0]['selected_position'] == '1B')
    assert(r[1]['name'] == 'Rance')
    assert(r[1]['selected_position'] == '3B')
    assert(r[2]['name'] == 'Garth')
    assert(r[2]['selected_position'] == 'LF')
    plyr = pd.Series([4, "George", ['LF'], np.nan], index=RBLDR_COLS)
    with pytest.raises(LookupError):
        rc = bldr.fit_if_space(rc, plyr)


def test_fit_with_lookup_error_2(bldr, empty_roster):
    plyr = pd.Series([1, "Paul", ['3B'], np.nan], index=RBLDR_COLS)
    rc = bldr.fit_if_space(empty_roster, plyr)
    plyr = pd.Series([2, "Robin", ['CF', 'SS'], np.nan], index=RBLDR_COLS)
    rc = bldr.fit_if_space(rc, plyr)
    plyr = pd.Series([3, "Gorman", ['CF'], np.nan], index=RBLDR_COLS)
    rc = bldr.fit_if_space(rc, plyr)
    r = rc.get_roster()
    assert(r[0]['name'] == 'Paul')
    assert(r[0]['selected_position'] == '3B')
    assert(r[1]['name'] == 'Robin')
    assert(r[1]['selected_position'] == 'SS')
    assert(r[2]['name'] == 'Gorman')
    assert(r[2]['selected_position'] == 'CF')
    plyr = pd.Series([4, "Kevin", ['CF', 'SS'], np.nan], index=RBLDR_COLS)
    with pytest.raises(LookupError):
        rc = bldr.fit_if_space(rc, plyr)


def test_fit_with_duplicate_positions(bldr, empty_roster):
    plyr = pd.Series([1, "Stieb", ['SP'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(empty_roster, plyr)
    plyr = pd.Series([2, "Clancy", ['SP'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    plyr = pd.Series([3, "Cerutti", ['SP'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    plyr = pd.Series([4, "Flanigan", ['SP'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    plyr = pd.Series([5, "Alexander", ['SP'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    plyr = pd.Series([6, "Fernandez", ['SP'], np.nan], index=RBLDR_COLS)
    with pytest.raises(LookupError):
        r = bldr.fit_if_space(r, plyr)
    plyr = pd.Series([7, "Claudell", ['SP', 'RP'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    rst = r.get_roster()
    print(rst)
    assert(len(rst) == 6)
    assert(rst[5]['name'] == 'Claudell')
    assert(rst[5]['selected_position'] == 'RP')


def test_fit_with_multiple_duplicate_positions_1(bldr, empty_roster):
    plyr = pd.Series([1, "Stieb", ['SP'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(empty_roster, plyr)
    plyr = pd.Series([2, "Clancy", ['SP'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    plyr = pd.Series([3, "Cerutti", ['SP', 'RP'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    plyr = pd.Series([4, "Flanigan", ['SP', 'RP'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    plyr = pd.Series([5, "Alexander", ['SP', 'RP'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    print(r.get_roster())
    for plyr in r.get_roster():
        assert(plyr.selected_position == 'SP')
    plyr = pd.Series([6, "Fernandez", ['SP'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    plyr = pd.Series([7, "Claudell", ['SP'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    plyr = pd.Series([8, "Key", ['SP'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    plyr = pd.Series([9, "Guzman", ['SP'], np.nan], index=RBLDR_COLS)
    print(r.get_roster())
    for i in [2, 3, 4]:
        assert(r.get_roster()[i]['selected_position'] == 'RP')
    with pytest.raises(LookupError):
        r = bldr.fit_if_space(r, plyr)


def test_fit_with_multiple_duplicate_positions_2(bldr, empty_roster):
    plyr = pd.Series([1, "Martinez", ['LF', 'RF', 'Util'], np.nan],
                     index=RBLDR_COLS)
    r = bldr.fit_if_space(empty_roster, plyr)
    plyr = pd.Series([2, "Murphy", ['1B', '2B', 'Util'], np.nan],
                     index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    plyr = pd.Series([3, "Arenado", ['3B', 'Util'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    plyr = pd.Series([4, "Arraez", ['2B', '3B', 'LF', 'Util'], np.nan],
                     index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    plyr = pd.Series([5, "Soto", ['LF', 'Util'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    plyr = pd.Series([6, "Daza", ['CF', 'Util'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    plyr = pd.Series([7, "Flores", ['1B', '2B', '3B', 'Util'], np.nan],
                     index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    print(r)
    expected_positions = ['RF', '2B', 'Util', '3B', 'LF', 'CF', '1B']
    for plyr, exp_pos in zip(r.get_roster(), expected_positions):
        assert(plyr['selected_position'] == exp_pos)


def test_fit_with_multiple_duplicate_positions_3(empty_roster):
    bldr = roster.Builder(['C', 'C', 'RW', 'RW', 'LW', 'LW', 'D', 'D', 'D',
                           'D', 'G', 'G'])
    rst = empty_roster
    rst.add_player(pd.Series([1, 'Marchand', ['LW'], 'LW'], index=RBLDR_COLS))
    rst.add_player(pd.Series([2, 'Vasilevskiy', ['G'], 'G'], index=RBLDR_COLS))
    rst.add_player(pd.Series([3, 'Draisaitl', ['C', 'LW'], 'C'], index=RBLDR_COLS))
    rst.add_player(pd.Series([4, 'Letang', ['D'], 'D'], index=RBLDR_COLS))
    rst.add_player(pd.Series([5, 'Josi', ['D'], 'D'], index=RBLDR_COLS))
    rst.add_player(pd.Series([6, 'Kane', ['RW'], 'RW'], index=RBLDR_COLS))
    rst.add_player(pd.Series([7, 'Giroux', ['C', 'LW', 'RW'], 'C'],
                             index=RBLDR_COLS))
    rst.add_player(pd.Series([8, 'Doughty', ['D'], 'D'], index=RBLDR_COLS))
    rst.add_player(pd.Series([9, 'Ellis', ['D'], 'D'], index=RBLDR_COLS))
    rst.add_player(pd.Series([10, 'Hertl', ['C', 'LW'], 'LW'], index=RBLDR_COLS))

    plyr = pd.Series([11, 'Pacioretty', ['LW'], np.nan], index=RBLDR_COLS)
    rst = bldr.fit_if_space(rst, plyr)
    r = rst.get_roster()
    assert(len(r) == 11)
    assert(r[10]['name'] == 'Pacioretty')
    assert(r[10]['selected_position'] == 'LW')
    assert(r[9]['name'] == 'Hertl')
    assert(r[9]['selected_position'] == 'C')
    assert(r[6]['name'] == 'Giroux')
    assert(r[6]['selected_position'] == 'RW')
    assert(r[2]['name'] == 'Draisaitl')
    assert(r[2]['selected_position'] == 'C')


def test_fit_with_dup_position(bldr, empty_roster):
    plyr = pd.Series([1, "Henke", ['RP'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(empty_roster, plyr)
    plyr = pd.Series([2, "Ward", ['RP'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    plyr = pd.Series([3, "Timlin", ['RP'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    plyr = pd.Series([4, "Eichorn", ['RP'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    plyr = pd.Series([5, "Cox", ['RP'], np.nan], index=RBLDR_COLS)
    r = bldr.fit_if_space(r, plyr)
    plyr = pd.Series([6, "Castillo", ['RP'], np.nan], index=RBLDR_COLS)
    with pytest.raises(LookupError):
        r = bldr.fit_if_space(r, plyr)


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


def test_roster_del_player(empty_roster):
    rc = empty_roster
    plyr = pd.Series([1, "Cecil", ['1B', '3B', 'LF', 'C'], '1B'],
                     index=RBLDR_COLS)
    rc.add_player(plyr)
    assert(rc.get_num_players_at_pos('1B') == 1)
    assert(rc.get_player_by_pos('1B', 0)['name'] == 'Cecil')
    rc.del_player(0)
    assert(rc.get_num_players_at_pos('1B') == 0)
    assert(rc.get_player_by_pos('1B', 0) is None)
