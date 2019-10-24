#!/bin/python

import copy
import numpy as np
from yahoo_fantasy_bot import roster


def optimize_single_player_at_a_time(cfg, score_comparer, roster_bldr,
                                     avail_plyrs, lineup):
    """
    Optimize by swapping in a single player to a constructed lineup

    :param cfg: Loaded config object
    :type cfg: configparser.ConfigParser
    :param score_comparer: Object that is used to compare two lineups to
    determine the better one
    :type score_comparer: bot.ScoreComparer
    :param roster_bldr: Object that is used to construct a roster given the
    constraints of the league
    :type roster_bldr: roster.Builder
    :param avail_plyrs: Pool of available players that can be included in
    a lineup
    :type avail_plyrs: DataFrame
    :param lineup: The currently constructed lineup
    :type lineup: list
    :return: If a better lineup was found, this will return it.  If no better
    lineup was found this returns None
    :rtype: list or None
    """
    selector = roster.PlayerSelector(avail_plyrs)
    categories = cfg['LineupOptimizer']['categories'].split(",")
    try:
        selector.rank(categories)
    except KeyError:
        raise KeyError("Categories are not valid: {}".format(categories))

    found_better = False
    score_comparer.update_score(lineup)
    for i, plyr in enumerate(selector.select()):
        if i+1 > int(cfg['LineupOptimizer']['iterations']):
            break

        print("Player: {} Positions: {}".
              format(plyr['name'], plyr['eligible_positions']))

        plyr['selected_position'] = np.nan
        best_lineup = copy.deepcopy(lineup)
        for potential_lineup in roster_bldr.enumerate_fit(best_lineup, plyr):
            if score_comparer.compare_lineup(potential_lineup):
                print("  *** Found better lineup when including {}"
                      .format(plyr['name']))
                lineup = copy.deepcopy(potential_lineup)
                score_comparer.update_score(lineup)
                found_better = True
    return lineup if found_better else None
