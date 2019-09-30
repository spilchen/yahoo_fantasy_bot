#!/bin/python

"""Command line interface to get predictions on a roster against an opponent(s)

Usage:
  opponent_match.py [-o <team> | -a] [-cs] <json>

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
import yahoo_fantasy_api as yfa
from yahoo_baseball_assistant import baseball_prediction, roster
from baseball_scraper import espn
import logging
import pickle
import os


def print_team(team_name, df, my_sum):
    print("")
    print("Team Name: {}".format(team_name))
    columns = ['Name', 'team', 'WK_G', 'WK_GS', 'G', 'AB', 'R', '2B', '3B',
               'HR', 'RBI', 'BB', 'SO', 'SB', 'AVG', 'OBP', 'W',
               'SO', 'SV', 'HLD', 'ERA', 'WHIP']
    cformat = "{:20} {:5} {:5} {:5} {:5} {:5} {:5} {:5} {:5} {:5} {:5} " \
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


def init_teams(args, lg, fg, ts, es, tss):
    pred_bldr = None
    if args['-c']:
        fn = "Builder.pkl"
        if os.path.exists(fn):
            with open(fn, 'rb') as f:
                pred_bldr = pickle.load(f)
    if pred_bldr is None:
        pred_bldr = baseball_prediction.Builder(lg, fg, ts, es, tss)
    team_containers = {}
    for tm in lg.teams():
        if args['-c']:
            fn = "Container.{}.pkl".format(tm['team_key'])
            if os.path.exists(fn):
                with open(fn, 'rb') as f:
                    team_containers[tm['team_key']] = pickle.load(f)
                continue
        team_containers[tm['team_key']] = roster.Container(
            lg, lg.to_team(tm['team_key']))
    return (pred_bldr, team_containers)


def save_teams(pred_bldr, team_containers):
    fn = "Builder.pkl"
    with open(fn, "wb") as f:
        pickle.dump(pred_bldr, f)
    for team_key, cont in team_containers.items():
        fn = "Container.{}.pkl".format(team_key)
        with open(fn, "wb") as f:
            pickle.dump(cont, f)


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
    team_key = lg.team_key()
    my_tm = yfa.Team(sc, team_key)
    (fg, ts, tss) = baseball_prediction.init_scrapers()
    (start_date, end_date) = lg.week_date_range(lg.current_week() + 1)
    es = espn.ProbableStartersScraper(start_date, end_date)

    (pred_bldr, team_containers) = init_teams(args, lg, fg, ts, es, tss)
    df = pred_bldr.predict(team_containers[team_key])

    scorer = roster.Scorer()
    my_sum = scorer.summarize(df)
    print_team("Lumber Kings", df, my_sum)

    # Compare against a bunch of teams
    teams = get_opp_teams(args, lg, my_tm)
    for tm in teams:
        df = pred_bldr.predict(team_containers[tm['team_key']])
        opp_sum = scorer.summarize(df)
        print_team(tm['name'], df, opp_sum)
        (w, l) = scorer.compare(my_sum, opp_sum)
        print("Prediction result: {} - {}".format(w, l))

    if args['-s']:
        save_teams(pred_bldr, team_containers)
