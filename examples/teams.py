#!/bin/python

"""Command line interface to list tables in a league

Usage:
  teams.py <json>

  <json>     The name of the JSON that has bearer token.  This can be generated
             from init_oauth_env.py.
"""
from docopt import docopt
from yahoo_oauth import OAuth2
import yahoo_fantasy_api as yfa
import logging


if __name__ == '__main__':
    args = docopt(__doc__, version='1.0')
    logging.basicConfig(
        filename='cli.log',
        level=logging.INFO,
        format='%(asctime)s.%(msecs)03d %(module)s-%(funcName)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logging.getLogger('yahoo_oauth').setLevel('WARNING')
    logging.getLogger('chardet.charsetprober').setLevel('WARNING')
    sc = OAuth2(None, None, from_file=args['<json>'])
    gm = yfa.Game(sc, 'mlb')
    league_id = gm.league_ids(year=2019)
    lg = yfa.League(sc, league_id[0])
    teams = lg.teams()
    for team in teams:
        print("{:30} {:15}".format(team['name'], team['team_key']))
