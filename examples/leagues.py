#!/bin/python

"""Command line interface to list leagues a user is involved in

Usage:
  leagues.py <json> <sport> [<year>]

  <json>     The name of the JSON that has bearer token.  This can be generated
             from init_oauth_env.py.
  <sport>    The sport to list the leagues for.  Specify 'mlb' for baseball,
             'nhl' for hockey, etc.
  <year>     Will restrict all leagues listed to this year.
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
    gm = yfa.Game(sc, args['<sport>'])
    league_ids = gm.league_ids(year=args['<year>'])
    for league_id in league_ids:
        # Older leagues have this "auto" in that, which we cannot dump any
        # particulars about.
        if "auto" not in league_id:
            lg = yfa.League(sc, league_id)
            settings = lg.settings()
            print("{:30} {:15}".format(settings['name'], league_id))
            teams = lg.teams()
            for team in teams:
                print("    {:30} {:15}".format(team['name'], team['team_key']))
            print("")
