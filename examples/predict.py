#!/bin/python

"""Predict the stats for the players currently on your roster

Usage:
  predict.py [-o <team> | -a] <json>

  <json>     The name of the JSON that has bearer token.  This can be generated
             from init_oauth_env.py.

Options to pick the team.  If any of these are ommitted, then we'll only
predict against the team you are playing next week:
  -a              Predict against all teams.
  -o <opp_team>   Opponent team to predict against.
"""
from docopt import docopt
from yahoo_oauth import OAuth2
from yahoo_fantasy_api import league, game, team
from yahoo_baseball_assistant import hitting
import logging


def print_team(team_name, df, my_sum):
    print("")
    print("Team Name: {}".format(team_name))
    columns = ['name', 'team', 'WK_G', 'G', 'AB', 'R', '1B', '2B', '3B',
               'HR', 'RBI', 'BB', 'SO', 'SB', 'AVG', 'OBP']
    cformat = "{:20} {:5} {:5} {:5} {:5} {:5} {:5} {:5} {:5} {:5} {:5} " \
        "{:5} {:5} {:5} {:5} {:5}"
    print(cformat.format(*columns))
    for plyr in df.iterrows():
        print(cformat.format(*[plyr[1][x] for x in columns]))
    print("")
    print("Stat prediction for week")
    print(my_sum)


def get_opp_teams(args, lg, my_tm):
    teams = []
    if args['-a']:
        for tm in lg.teams():
            if tm['team_key'] == my_tm.team_key:
                continue
            teams.append(tm)
    elif args['-o']:
        for tm in lg.teams():
            if tm['name'] == args['-o']:
                teams.append(tm)
                break
    else:
        key = my_tm.matchup(lg.current_week() + 1)
        for tm in lg.teams():
            if tm['team_key'] == key:
                teams.append(tm)
                break
    return teams


if __name__ == '__main__':
    args = docopt(__doc__, version='1.0')
    logging.getLogger('yahoo_oauth').setLevel('WARNING')
    logging.getLogger('chardet.charsetprober').setLevel('WARNING')
    sc = OAuth2(None, None, from_file=args['<json>'])
    gm = game.Game(sc, 'mlb')
    league_id = gm.league_ids(year=2019)
    lg = league.League(sc, league_id[0])
    team_key = lg.team_key()
    my_tm = team.Team(sc, team_key)
    bldr = hitting.Builder(lg, my_tm)
    df = bldr.roster_predict()
    my_sum = bldr.sum_prediction(df)
    print_team("Lumber Kings", df, my_sum)

    # Compare against a bunch of teams
    teams = get_opp_teams(args, lg, my_tm)
    for tm in teams:
        opp_tm = team.Team(sc, tm['team_key'])
        bldr = hitting.Builder(lg, opp_tm)
        df = bldr.roster_predict()
        opp_sum = bldr.sum_prediction(df)
        print_team(tm['name'], df, opp_sum)
        (w, l) = bldr.score(my_sum, opp_sum)
        print("Prediction result: {} - {}".format(w, l))
