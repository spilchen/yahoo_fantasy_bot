#!/bin/python


def test_roster_predict(hitting_builder):
    roster = [{'player_id': 9842, 'position_type': 'B',
               'selected_position': '1B', 'name': 'Joe'},
              {'player_id': 8967, 'position_type': 'B',
               'selected_position': '2B', 'name': 'Bob'}]
    hitting_builder.set_roster(roster)
    df = hitting_builder.roster_predict()
    print(df)
    assert(len(df) == 2)
    assert(df.HR[0] == 16)
    assert(df.RBI[0] == 48)
    assert(df.SB[0] == 6)
    assert(df.HR[1] == 11)
    assert(df.RBI[1] == 35)
    assert(df.SB[1] == 8)


def test_empty_roster_predict(hitting_builder):
    hitting_builder.set_roster([])
    df = hitting_builder.roster_predict()
    print(df)
    assert(len(df) == 0)
    roster = [{'player_id': 0, 'position_type': 'B',
               'selected_position': '1B', 'name': 'Fred'}]
    hitting_builder.set_roster(roster)
    df = hitting_builder.roster_predict()
    print(df)
    assert(len(df) == 0)
