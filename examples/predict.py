#!/bin/python

"""Predict the stats for the players currently on your roster

Usage:
  predict.py <json>

  <json>  The name of the JSON that has bearer token.  This can be generated
          from init_oauth_env.py.
"""
from docopt import docopt
from yahoo_oauth import OAuth2
from yahoo_fantasy_api import league, game, team
from yahoo_baseball_assistant import hitting
import logging


if __name__ == '__main__':
    args = docopt(__doc__, version='1.0')
    logging.getLogger('yahoo_oauth').setLevel('WARNING')
    logging.getLogger('chardet.charsetprober').setLevel('WARNING')
    sc = OAuth2(None, None, from_file=args['<json>'])
    gm = game.Game(sc, 'mlb')
    league_id = gm.league_ids(year=2019)
    lg = league.League(sc, league_id[0])
    cur_wk = lg.current_week()
    if cur_wk >= lg.end_week():
        raise RuntimeError("Season over no more weeks to predict")
    team_key = lg.team_key()
    my_tm = team.Team(sc, team_key)
    bldr = hitting.Builder(my_tm, cur_wk + 1)
    df = bldr.roster_predict()
    columns = ['name', 'G', 'AB', 'R', '1B', '2B', '3B', 'HR', 'RBI', 'BB',
               'SO', 'SB', 'AVG', 'OBP']
    cformat = "{:20} {:5} {:5} {:5} {:5} {:5} {:5} {:5} {:5} {:5} " \
        "{:5} {:5} {:5} {:5}"
    print(cformat.format(*columns))
    for plyr in df.iterrows():
        print(cformat.format(*[plyr[1][x] for x in columns]))
