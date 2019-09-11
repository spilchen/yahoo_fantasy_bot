#!/bin/python

"""Command line interface to select a roster against an opponent

Usage:
  teams.py <json> <team_key>

  <json>      The name of the JSON that has bearer token.  This can be
              generated from init_oauth_env.py.
  <team_key>  The team key of the opponent to match up against.
"""
from docopt import docopt
from yahoo_oauth import OAuth2
import yahoo_fantasy_api as yfa
from yahoo_baseball_assistant import roster, scraper
import logging
import pickle
import os
import pandas as pd
import numpy as np


logging.basicConfig(
    filename='roster_select.log',
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d %(module)s - %(funcName)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger()
MY_ROSTER_PKL = "my_roster.pkl"
PPOOL_PKL = "ppool.pkl"
BLACKLIST_PKL = "blacklist.pkl"
pd.options.mode.chained_assignment = None  # default='warn'


def initial_fit(ppool, categories, my_roster, my_team_bldr, max_players,
                blacklist):
    selector = roster.PlayerSelector(ppool)
    selector.rank(categories)
    for plyr in selector.select():
        try:
            if plyr['Name'] in blacklist:
                continue

            print("Player: {} Positions: {}".
                  format(plyr['Name'], plyr['eligible_positions']))

            plyr['selected_position'] = np.nan
            my_roster = my_team_bldr.fit_if_space(my_roster, plyr)
        except LookupError:
            pass
        if len(my_roster) == max_players:
            break
    return my_roster


def print_main_menu():
    print("")
    print("")
    print("Main Menu")
    print("=========")
    print("R - Show roster")
    print("S - Show sumarized scores")
    print("A - Auto select players")
    print("M - Manual select players")
    print("T - Show two start pitchers")
    print("L - List players")
    print("B - Blacklist players")
    print("X - Exit")
    print("")
    print("Pick a selection:")


def print_roster(lineup):
    POSITION_ORDER = ["C", "1B", "2B", "SS", "3B", "LF", "CF", "RF", "Util",
                      "SP", "RP"]
    print("{:4}: {:20}   "
          "{}/{}/{}/{}/{}/{}".
          format('B', '', 'R', 'HR', 'RBI', 'SB', 'AVG', 'OBP'))
    for pos in POSITION_ORDER:
        for plyr in lineup:
            if plyr['selected_position'] == pos:
                if pos in ["SP", "RP"]:
                    print("{:4}: {:20}   "
                          "{:.1f}/{:.1f}/{:.1f}/{:.1f}/{:.3f}/{:.3f}".
                          format(plyr['selected_position'],
                                 plyr['Name'], plyr['W'], plyr['HLD'],
                                 plyr['SV'], plyr['SO'], plyr['ERA'],
                                 plyr['WHIP']))
                else:
                    print("{:4}: {:20}   "
                          "{:.1f}/{:.1f}/{:.1f}/{:.1f}/{:.3f}/{:.3f}".
                          format(plyr['selected_position'], plyr['Name'],
                                 plyr['R'], plyr['HR'], plyr['RBI'],
                                 plyr['SB'], plyr['AVG'], plyr['OBP']))
        if pos == 'Util':
            print("")
            print("{:4}: {:20}   "
                  "{}/{}/{}/{}/{}/{}".
                  format('P', '', 'W', 'HLD', 'SV', 'SO', 'ERA', 'WHIP'))


def compute_score(lineup, opp_sum):
    df = pd.DataFrame(data=lineup, columns=lineup[0].index)
    scorer = roster.Scorer()
    my_sum = scorer.summarize(df)
    (w, l) = scorer.compare(my_sum, opp_sum)
    return (w, l, my_sum)


def show_score(lineup, opp_sum):
    (w, l, my_sum) = compute_score(lineup, opp_sum)
    print("Estimate roster will score: {} - {}".format(w, l))
    print("")
    for stat in my_sum.index:
        if stat in ["ERA", "WHIP"]:
            if my_sum[stat] < opp_sum[stat]:
                my_win = "*"
                opp_win = ""
            else:
                my_win = ""
                opp_win = "*"
        else:
            if my_sum[stat] > opp_sum[stat]:
                my_win = "*"
                opp_win = ""
            else:
                my_win = ""
                opp_win = "*"
        print("{:5} {:2.3f} {:1} v.s. {:2.3f} {:2}".format(stat,
                                                           my_sum[stat],
                                                           my_win,
                                                           opp_sum[stat],
                                                           opp_win))


def is_new_score_better(orig_w, orig_l, new_w, new_l):
    if orig_w + orig_l > 0:
        orig_pct = orig_w / (orig_w + orig_l)
    else:
        orig_pct = 0.5

    if new_w + new_l > 0:
        new_pct = new_w / (new_w + new_l)
    else:
        new_pct = 0.5

    return orig_pct < new_pct


def copy_roster(roster):
    new_roster = []
    for plyr in roster:
        new_roster.append(plyr.copy())
    return new_roster


def show_two_start_pitchers(my_df):
    two_starters = my_df[my_df.WK_GS > 1]
    for plyr in two_starters.iterrows():
        print(plyr[1]['Name'])


def auto_select_players(ppool, my_team_bldr, lineup, opp_sum, blacklist,
                        id_system='playerid'):
    print("")
    print("Number of iterations: ")
    try:
        num_iters = int(input())
    except ValueError:
        print("*** input a valid number")
        return lineup
    print("Stat categories to rank (delimited with comma):")
    categories_combined = input()
    categories = categories_combined.rstrip().split(",")
    print(categories)

    # Filter out any players from the lineup as we don't want to consider them
    # again.
    lineup_ids = [e[id_system] for e in lineup]
    avail_plyrs = ppool[~ppool[id_system].isin(lineup_ids)]
    selector = roster.PlayerSelector(avail_plyrs)
    try:
        selector.rank(categories)
    except KeyError:
        print("Categories are not valid: {}".format(categories))
        return lineup

    (orig_w, orig_l, _) = compute_score(lineup, opp_sum)
    for i, plyr in enumerate(selector.select()):
        if i+1 > num_iters:
            break
        if plyr['Name'] in blacklist:
            continue

        print("Player: {} Positions: {}".
              format(plyr['Name'], plyr['eligible_positions']))

        plyr['selected_position'] = np.nan
        best_lineup = copy_roster(lineup)
        for potential_lineup in my_team_bldr.enumerate_fit(lineup, plyr):
            (new_w, new_l, _) = compute_score(potential_lineup, opp_sum)
            if is_new_score_better(orig_w, orig_l, new_w, new_l):
                best_lineup = copy_roster(potential_lineup)
                (orig_w, orig_l) = (new_w, new_l)
                print("  *** Found better lineup")
                print_roster(best_lineup)
        lineup = copy_roster(best_lineup)
    return lineup


def manual_select_players(ppool, lineup, opp_sum):
    print_roster(lineup)
    show_score(lineup, opp_sum)
    print("Enter the name of the player to remove: ")
    pname_rem = input().rstrip()
    print("Enter the name of the player to add: ")
    pname_add = input().rstrip()

    plyr_del = None
    for del_idx, p in enumerate(lineup):
        if p['Name'] == pname_rem:
            plyr_del = p
            break
    if plyr_del is None:
        print("Could not find player in your lineup: {}".format(pname_rem))
        return

    plyr_add_df = ppool[ppool['Name'] == pname_add]
    if(len(plyr_add_df.index) == 0):
        print("Could not find player in pool: {}".format(pname_add))
        return
    if(len(plyr_add_df.index) > 1):
        print("Found more than one player!: {}".format(pname_add))
        return

    plyr_add = plyr_add_df.iloc(0)[0]

    assert(type(plyr_del.selected_position) == str)
    if plyr_del.selected_position not in plyr_add['eligible_positions']:
        print("Position {} is not a valid position for {}: {}".format(
            plyr_del.selected_position,
            plyr_add['Name'],
            plyr_add['eligible_positions']))
        return

    plyr_add['selected_position'] = plyr_del['selected_position']
    plyr_del['selected_position'] = np.nan
    lineup.append(plyr_add)
    del lineup[del_idx]

    print_roster(lineup)
    show_score(lineup, opp_sum)


def fetch_player_pool(lg, pred_bldr):
    if os.path.exists(PPOOL_PKL):
        with open(PPOOL_PKL, "rb") as f:
            my_df = pickle.load(f)
    else:
        all_mine = lg.to_team(lg.team_key()).roster(lg.current_week() + 1)
        hitters_mine = []
        pitchers_mine = []
        for p in all_mine:
            if p['selected_position'] == 'BN':
                p['selected_position'] = np.nan
            if p['position_type'] == 'P':
                pitchers_mine.append(p)
            else:
                hitters_mine.append(p)
        logger.info("Fetching free agents")
        batter_pool = lg.free_agents('B') + hitters_mine
        pitcher_pool = lg.free_agents('P') + pitchers_mine
        logger.info("Free agents fetch complete.  "
                    "{} hitters and {} pitchers in pool"
                    .format(len(batter_pool), len(pitcher_pool)))
        rcont = roster.Container(None, None)
        rcont.add_players(batter_pool)
        batter_preds = pred_bldr.predict(rcont, fail_on_missing=False,
                                         lk_id_system='mlb_id',
                                         scrape_id_system='MLBAM ID',
                                         team_has='abbrev')
        rcont = roster.Container(None, None)
        rcont.add_players(pitcher_pool)
        pitcher_preds = pred_bldr.predict(rcont, fail_on_missing=False,
                                          lk_id_system='mlb_id',
                                          scrape_id_system='MLBAM ID',
                                          team_has='abbrev')

        # Filter out some of the batting categories from pitchers
        for hit_stat in ['HR', 'RBI', 'AVG', 'OBP', 'R', 'SB']:
            pitcher_preds[hit_stat] = np.nan

        my_df = batter_preds.append(pitcher_preds)

        with open(PPOOL_PKL, "wb") as f:
            pickle.dump(my_df, f)

    return my_df


def print_blacklist_menu():
    print("")
    print("Blacklist Menu")
    print("==============")
    print("L - List players on black list")
    print("A - Add player to black list")
    print("D - Delete player from black list")
    print("X - Exit and return to previous menu")
    print("")
    print("Pick a selection: ")


def manage_blacklist(blacklist):
    while True:
        print_blacklist_menu()
        sel = input()

        if sel == "L":
            print("Contents of blacklist:")
            for p in blacklist:
                print(p)
        elif sel == "A":
            print("Enter player name to add: ")
            blacklist.append(input())
            with open(BLACKLIST_PKL, "wb") as f:
                pickle.dump(blacklist, f)
        elif sel == "D":
            print("Enter player name to delete: ")
            name = input()
            if name not in blacklist:
                print("Name not found in black list: {}".format(name))
            else:
                blacklist.remove(name)
                with open(BLACKLIST_PKL, "wb") as f:
                    pickle.dump(blacklist, f)
        elif sel == "X":
            break
        else:
            print("Unknown option: {}".format(sel))


def list_players(ppool):
    print("Enter position: ")
    pos = input()
    print("")

    if pos in ['C', '1B', '2B', 'SS', '3B', 'LF', 'CF', 'RF', 'Util']:
        print("{:20}   {}/{}/{}/{}/{}/{}".format('Name', 'R', 'HR', 'RBI',
                                                 'SB', 'AVG', 'OBP'))
    else:
        print("{:20}   {}/{}/{}/{}/{}/{}".format('Name', 'W', 'HLD', 'SV',
                                                 'SO', 'ERA', 'WHIP'))

    for plyr in ppool.iterrows():
        if pos in plyr[1]['eligible_positions']:
            if pos in ['C', '1B', '2B', 'SS', '3B', 'LF', 'CF', 'RF', 'Util']:
                print("{:20}   {:.1f}/{:.1f}/{:.1f}/{:.1f}/{:.3f}/{:.3f}".
                      format(plyr[1]['Name'], plyr[1]['R'], plyr[1]['HR'],
                             plyr[1]['RBI'], plyr[1]['SB'], plyr[1]['AVG'],
                             plyr[1]['OBP']))
            else:
                print("{:20}   {:.1f}/{:.1f}/{:.1f}/{:.1f}/{:.3f}/{:.3f}".
                      format(plyr[1]['Name'], plyr[1]['W'], plyr[1]['HLD'],
                             plyr[1]['SV'], plyr[1]['SO'], plyr[1]['ERA'],
                             plyr[1]['WHIP']))


def load_roster(ppool, blacklist, my_team_bldr):
    if os.path.exists(MY_ROSTER_PKL):
        with open(MY_ROSTER_PKL, "rb") as f:
            my_roster = pickle.load(f)
    else:
        my_roster = []
        initial_fit(ppool, ["ERA", "WHIP", "W", "SV", "HLD", "SO"], my_roster,
                    my_team_bldr, 10, blacklist)
        initial_fit(ppool, ["AVG", "OBP", "HR", "R", "RBI", "SB"], my_roster,
                    my_team_bldr, 19, blacklist)
    return my_roster


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

    opp_team = roster.Container(lg, lg.to_team(args['<team_key>']))
    (start_date, end_date) = lg.week_date_range(lg.current_week() + 1)
    pred_bldr = scraper.init_prediction_builder(lg, start_date, end_date)

    # Build the roster pool of players
    my_df = fetch_player_pool(lg, pred_bldr)

    # Build up the predicted score of the opponent
    opp_df = pred_bldr.predict(opp_team,
                               lk_id_system='mlb_id',
                               scrape_id_system='MLBAM ID',
                               team_has='abbrev')
    scorer = roster.Scorer()
    opp_sum = scorer.summarize(opp_df)

    # Load the black list
    if os.path.exists(BLACKLIST_PKL):
        with open(BLACKLIST_PKL, "rb") as f:
            blacklist = pickle.load(f)
    else:
        blacklist = []

    potential_team = roster.Container(None, None)
    my_team_bldr = roster.Builder(["C", "1B", "2B", "SS", "3B", "LF", "CF",
                                   "RF", "Util", "SP", "SP", "SP", "SP", "SP",
                                   "RP", "RP", "RP", "RP", "RP"])
    my_roster = load_roster(my_df, blacklist, my_team_bldr)

    while True:
        print_main_menu()
        opt = input()

        if opt == "R":
            print_roster(my_roster)
        elif opt == "S":
            show_score(my_roster, opp_sum)
        elif opt == "A":
            my_roster = auto_select_players(my_df, my_team_bldr, my_roster,
                                            opp_sum, blacklist,
                                            id_system='MLBAM ID')
        elif opt == "M":
            manual_select_players(my_df, my_roster, opp_sum)
        elif opt == "T":
            show_two_start_pitchers(my_df)
        elif opt == "L":
            list_players(my_df)
        elif opt == "B":
            manage_blacklist(blacklist)
        elif opt == "X":
            break
        else:
            print("Unknown option: {}".format(opt))

    with open(MY_ROSTER_PKL, "wb") as f:
        pickle.dump(my_roster, f)
    scraper.save_prediction_builder(pred_bldr)
