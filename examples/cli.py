#!/bin/python

"""Command line interface to get predictions on a roster

Usage:
  predict.py [-o <team> | -a] [-c|-s] <json>

  <json>     The name of the JSON that has bearer token.  This can be generated
             from init_oauth_env.py.

Options to pick the team.  If any of these are ommitted, then we'll only
predict against the team you are playing next week:
  -a              Predict against all teams.
  -o <opp_team>   Opponent team to predict against.

Other options:
  -c              Read the roster from cache
  -s              Save the roster to a cache file
"""
from docopt import docopt
from yahoo_oauth import OAuth2
from yahoo_fantasy_api import league, game, team
from yahoo_baseball_assistant import prediction
from baseball_scraper import fangraphs, baseball_reference
import logging
import pickle
import os


def print_team(team_name, df, my_sum):
    print("")
    print("Team Name: {}".format(team_name))
    columns = ['Name', 'team', 'WK_G', 'G', 'AB', 'R', '2B', '3B',
               'HR', 'RBI', 'BB', 'SO', 'SB', 'AVG', 'OBP', 'W',
               'SO', 'SV', 'HLD', 'ERA', 'WHIP']
    cformat = "{:20} {:5} {:5} {:5} {:5} {:5} {:5} {:5} {:5} {:5} " \
        "{:5} {:5} {:5} {:5} {:5} {:5} {:5} {:5} {:5} {:5} {:5}"
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


def init_team_bldrs(args, lg, fg, ts):
    team_bldrs = {}
    for tm in lg.teams():
        if args['-c']:
            fn = "{}.pkl".format(tm['team_key'])
            if os.path.exists(fn):
                with open(fn, 'rb') as f:
                    team_bldrs[tm['team_key']] = pickle.load(f)
                continue
        team_bldrs[tm['team_key']] = prediction.Builder(
            lg, lg.to_team(tm['team_key']), fg, ts)
    return team_bldrs


def save_team_bldrs(team_bldrs):
    for team_key, bldr in team_bldrs.items():
        fn = "{}.pkl".format(team_key)
        with open(fn, "wb") as f:
            pickle.dump(bldr, f)


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
    gm = game.Game(sc, 'mlb')
    league_id = gm.league_ids(year=2019)
    lg = league.League(sc, league_id[0])
    team_key = lg.team_key()
    my_tm = team.Team(sc, team_key)
    fg = fangraphs.Scraper("Depth Charts (RoS)")
    ts = baseball_reference.TeamScraper()

    team_bldrs = init_team_bldrs(args, lg, fg, ts)
    df = team_bldrs[team_key].predict()
    my_sum = team_bldrs[team_key].sum_prediction(df)
    print_team("Lumber Kings", df, my_sum)

    # Compare against a bunch of teams
    teams = get_opp_teams(args, lg, my_tm)
    for tm in teams:
        df = team_bldrs[tm['team_key']].predict()
        opp_sum = team_bldrs[tm['team_key']].sum_prediction(df)
        print_team(tm['name'], df, opp_sum)
        (w, l) = team_bldrs[tm['team_key']].score(my_sum, opp_sum)
        print("Prediction result: {} - {}".format(w, l))

    if args['-s']:
        save_team_bldrs(team_bldrs)
