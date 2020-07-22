#!/usr/bin/python

import copy
import importlib
import logging
import numpy as np
import pandas as pd

from yahoo_fantasy_bot import utils


class Container:
    """Class that holds a roster of players"""
    def __init__(self, cfg):
        self.roster = []
        self.pos_count = {}
        self.plyr_by_pos = {}
        StatAccumulator = self._get_scoreaccumulator_class(cfg)
        self.stat_accumulator = StatAccumulator(cfg)

    def get_roster(self):
        return self.roster

    def del_player(self, offset):
        """Removes a player given its offset in the self.roster list

        :param offset: The offset within self.roster to remove
        :type offset: int
        """
        assert(offset >= 0 and offset < len(self.roster))
        del_plyr = self.roster[offset]
        self.stat_accumulator.remove_player(del_plyr)
        pos = del_plyr['selected_position']
        self.pos_count[pos] -= 1
        self._del_from_plyr_by_pos(del_plyr)
        del self.roster[offset]

    def add_player(self, player):
        """Adds a player to the roster

        This will raise an error if the player already exists on the roster.

        :param player: Fully setup player object to add.
        :type player: dict
        """
        self.roster.append(player)
        self.stat_accumulator.add_player(player)
        pos = player['selected_position']
        self._incr_pos_count(pos)
        if pos not in self.plyr_by_pos:
            self.plyr_by_pos[pos]=[]
        self.plyr_by_pos[pos].append(player)

    def add_players(self, players):
        """Adds multiple players in bulk.

        :param players: List of players to add to the container
        :type players: List(dict)
        """
        for p in players:
            self.add_player(p)

    def change_position(self, plyr, pos):
        """Change the position of a player

        The player must be on your roster.

        :param plyr: Player to change the position
        :type plyr: dict
        :param pos: The short version of the position.
        :type pos: str
        """
        assert(isinstance(pos, str))

        # It the players selected position is not set, then lets include
        # it in the roster.
        if not isinstance(plyr['selected_position'], str):
            plyr['selected_position'] = pos
            self.add_player(plyr)
            return

        old_pos = plyr['selected_position']
        assert(old_pos in self.pos_count)
        self.pos_count[old_pos] -= 1
        self._del_from_plyr_by_pos(plyr)
        plyr['selected_position'] = pos
        self._incr_pos_count(pos)
        if pos not in self.plyr_by_pos:
            self.plyr_by_pos[pos] = []
        self.plyr_by_pos[pos].append(plyr)

    def get_num_players_at_pos(self, pos):
        """Return the number of players at the given position

        :param pos: Position to check
        :type pos: str
        :return: Number of players at the given position
        :rtype: int
        """
        if pos in self.pos_count:
            return self.pos_count[pos]
        else:
            return 0

    def get_player_by_pos(self, pos, occurrence):
        """Return the player at the given position and occurrence"""
        cum_occurrence = 0
        if pos in self.plyr_by_pos:
            for plyr in self.plyr_by_pos[pos]:
                if cum_occurrence == occurrence:
                    return plyr
                cum_occurrence += 1
        return None

    def compute_stat_summary(self):
        """Compute a summary of key stats for all players in the roster

        :return: Stat summary of key stats
        :rtype: pandas.DataFrame
        """
        return self.stat_accumulator.get_summary(self.roster)

    def _incr_pos_count(self, pos):
        if pos in self.pos_count:
            self.pos_count[pos] += 1
        else:
            self.pos_count[pos] = 1

    def _del_from_plyr_by_pos(self, plyr):
        """Helper to remove a player from self.plyr_by_pos"""
        old_pos = plyr['selected_position']
        for i, p in enumerate(self.plyr_by_pos[old_pos]):
            if p['player_id'] == plyr['player_id']:
                del self.plyr_by_pos[old_pos][i]
                break

    def _get_scoreaccumulator_class(self, cfg):
        module = importlib.import_module(
            cfg['ScoreAccumulator']['module'],
            package=cfg['ScoreAccumulator']['package'])
        return getattr(module, cfg['ScoreAccumulator']['class'])


class Builder:
    """Class that generates roster permuations suitable for evaluation"""
    def __init__(self, positions):
        self.logger = logging.getLogger()
        self.positions = positions
        self.pos_count = {}
        for p in positions:
            if p in self.pos_count:
                self.pos_count[p] += 1
            else:
                self.pos_count[p] = 1

    def fit_if_space(self, roster, player):
        """Fit a player onto a roster if there is space.

        The input roster must have the following columns:
            - eligible_positions: array of positions that the player can play
            - selected_position: the selected position we chose for the roster

        If successful, the result will be a roster with the new player added to
        it with a selected_position set to something non-NaN.

        :param roster: Roster to fit the player on.
        :type roster: Container
        :param player: Player to try and find a roster spot for.
        :type player: pandas.Series
        :return: The new roster with the player in it.  If an open spot is not
            available for the player then an LookupError assertion is returned.
        :rtype: list
        """
        assert(isinstance(roster, Container))
        self.logger.debug("Fit {}: positions={}".format(
            player['name'], player['eligible_positions']))
        # Search if any of the players eligible_positions are open.  Then it is
        # an easy fit.
        for pos in player.eligible_positions:
            if self._has_empty_position_slot(roster, pos):
                self.logger.debug("Fit at empty position: {}".format(pos))
                roster.change_position(player, pos)
                return roster

        # List to keep track of the players swapped in a given fit.  This
        # ensures the same player isn't moved more than once in a given
        # sequence of swaps.
        swapped_plyrs = []

        # Look through the other players already starting at the new players
        # positions.  If any of them can move to empty spot then we can fit.
        for pos in player.eligible_positions:
            for occurrence in range(self.pos_count[pos]):
                self.logger.debug("Attempt swap at position: {}".format(pos))
                plyr_at_pos = roster.get_player_by_pos(pos, occurrence)
                self.logger.debug("Swap out {}: {}".format(
                    plyr_at_pos['name'], pos))
                if self._swap_eligible_pos_recurse(roster, plyr_at_pos,
                                                   swapped_plyrs):
                    assert(self._has_empty_position_slot(roster, pos))
                    self.logger.debug('{}: {} -> {}'.format(
                        player['name'], player['selected_position'], pos))
                    roster.change_position(player, pos)
                    return roster

        raise LookupError("No space for player on roster")

    def max_players(self):
        return len(self.positions)

    def _has_empty_position_slot(self, roster, pos):
        # Not all positions may be tracked.  Player injury could be eligible to
        # go to the IR slot.
        if pos in self.pos_count:
            num = roster.get_num_players_at_pos(pos)
            return num < self.pos_count[pos]
        else:
            return False

    def _swap_eligible_pos_recurse(self, roster, player, swapped_plyrs):
        """Recursively swap positions with players until all positions are used

        :param roster: The roster to work with
        :type roster: Roster
        :param player: The player to try and swap around.
        :type player: pandas.Series
        :param swapped_plyrs: A list of players already swapped in this
            sequence of trying to fit the player.
        :type swapped: list
        :return: True if we were able to swap to an empty position
        :rtype: Boolean
        """
        assert(player.selected_position is not None)

        if player['player_id'] in swapped_plyrs:
            return False
        swapped_plyrs.append(player['player_id'])

        # Check if player can change their position to an empty spot
        for pos in player.eligible_positions:
            if pos != player.selected_position:
                if self._has_empty_position_slot(roster, pos):
                    self.logger.debug('{}: {} -> {}'.format(
                        player['name'], player['selected_position'], pos))
                    assert(isinstance(player['selected_position'], str))
                    roster.change_position(player, pos)
                    return True

        # Recursively check each of the positions that the player plays to
        # see if they can switch out to an empty spot.
        for pos in player.eligible_positions:
            if pos != player.selected_position:
                for occurrence in range(self.pos_count[pos]):
                    other_plyr = roster.get_player_by_pos(pos, occurrence)
                    assert(other_plyr is not None), "Nobody for " + pos
                    if self._swap_eligible_pos_recurse(roster, other_plyr,
                                                       swapped_plyrs):
                        assert(self._has_empty_position_slot(roster, pos))
                        self.logger.debug('{}: {} -> {}'.format(
                            player['name'], player['selected_position'], pos))
                        roster.change_position(player, pos)
                        return True

        swapped_plyrs.pop()
        return False


class PlayerSelector:
    """Class that will select players from a container to include on a roster.

    The roster container it is given should be a pool of all available players
    that can make up a roster.  The players select are players that are tops
    in the stats categories.

    :param player_pool: Pool of players that we will pick from
    :type player_pool: Container
    """
    def __init__(self, player_pool):
        self.ppool = player_pool
        self.rank_stats_descending = ["ERA", "WHIP", "percent_owned"]

    def rank(self, stat_categories):
        """Rank players in the player pool according to the stat categories

        :param stat_categories: List of the stat categories that the fantasy
               league uses.
        :type stat_categories: list(str)
        """
        self.ppool['rank'] = 0
        for stat in stat_categories:
            self.ppool['rank'] += self.ppool[stat].rank(
                    ascending=self._is_stat_ascending(stat))

    def shuffle(self):
        """
        Shuffle the player pool in order to produce a random roster
        """
        self.ppool = self.ppool.sample(frac=1).reset_index(drop=True)

    def select(self):
        """Iterate over players in the pool according to the rank

        This is to be called after rank().  It will return the players starting
        with the top ranked player.
        """
        df = self.ppool.sort_values(by=['rank'], ascending=False)
        for plyr_tuple in df.iterrows():
            yield plyr_tuple[1]

    def _is_stat_ascending(self, stat):
        if stat in self.rank_stats_descending:
            return False
        else:
            return True

    def set_descending_categories(self, cats):
        self.rank_stats_descending = cats
