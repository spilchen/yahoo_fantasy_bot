#!/usr/bin/python

from yahoo_baseball_assistant import utils
import pandas as pd
import numpy as np


class Container:
    """Class that holds a roster of players

    :param lg: Yahoo! league
    :type lg: yahoo_fantasy_api.league.League
    :param team: Yahoo! Team to do the predictions for
    :type team: yahoo_fantasy_api.team.Team
    """
    def __init__(self, lg, team):
        if lg is not None:
            self.week = lg.current_week() + 1
            if self.week > lg.end_week():
                raise RuntimeError("Season over no more weeks to predict")
            self.roster = team.roster(self.week)
        else:
            self.roster = []

    def get_roster(self):
        return self.roster

    def del_player(self, player_name):
        """Removes the given player from your roster

        :param player_name: Full name of the player to delete.  The player name
               must this exactly; with the exception of accents, which are
               normalized out
        :type player_name: str
        """
        for plyr in self.roster:
            if utils.normalized(player_name) == utils.normalized(plyr['name']):
                self.roster.remove(plyr)

    def player_exists(self, player_name):
        """Check if the given player is on your roster

        :param player_name: The player name to check
        :type player_name: string
        :return: True if the player, False otherwise
        :rtype: boolean
        """
        for plyr in self.roster:
            if player_name == utils.normalized(plyr['name']):
                return True
        return False

    def get_position_type(self, pos):
        if pos in ["C", "1B", "2B", "3B", "SS", "LF", "CF", "RF", "Util"]:
            return 'B'
        elif pos in ["SP", "RP"]:
            return 'P'
        else:
            raise ValueError("{} is not a valid position".format(pos))

    def add_player(self, player_name, pos):
        """Adds a player to the roster

        This will raise an error if the player already exists on the roster.

        :param player_name: Full name of the player to add.
        :type player_name: str
        :param pos: The short version of the selected position.
        :type pos: str
        """
        if self.player_exists(player_name):
            raise ValueError("Player is already on the roster")

        self.roster.append({'position_type': self.get_position_type(pos),
                            'selected_position': pos,
                            'name': player_name,
                            'player_id': -1})

    def add_players(self, players):
        """Adds multiple players in bulk.

        :param players: List of players to add to the container
        :type players: List(dict)
        """
        self.roster = self.roster + players

    def change_position(self, player_name, pos):
        """Change the position of a player

        The player must be on your roster.

        :param player_name: Full name of the player who's position is changing
        :type player_name: str
        :param pos: The short version of the position.
        :type pos: str
        """
        for plyr in self.roster:
            if utils.normalized(player_name) == utils.normalized(plyr['name']):
                plyr['selected_position'] = pos
                return
        raise ValueError("Player not found on roster")


class Scorer:
    """Class that scores rosters that it is given"""
    def __init__(self):
        pass

    def summarize(self, df):
        """Summarize the dataframe into individual stat categories

        :param df: Roster predictions to summarize
        :type df: DataFrame
        :return: Summarized predictions
        :rtype: Series
        """
        res = self._sum_hit_prediction(df)
        res = res.append(self._sum_pit_prediction(df))
        return res

    def compare(self, left, right):
        """Determine how many points comparing two summarized stats together

        :param left: Summarized stats to compare
        :type left: Series
        :param right: Summarized stats to compare
        :type right: Series
        :return: Number of wins and number of losses.
        :rtype: Tuple of two ints
        """
        (win, loss) = (0, 0)
        for l, r, name in zip(left, right, left.index):
            if self._is_counting_stat(name):
                conv_l = int(l)
                conv_r = int(r)
            else:
                conv_l = round(l, 3)
                conv_r = round(r, 3)
            if self._is_highest_better(name):
                if conv_l > conv_r:
                    win += 1
                elif conv_r > conv_l:
                    loss += 1
            else:
                if conv_l < conv_r:
                    win += 1
                elif conv_r < conv_l:
                    loss += 1

        return (win, loss)

    def _sum_hit_prediction(self, df):
        temp_stat_cols = ['AB', 'H', 'BB']
        hit_stat_cols = ['R', 'HR', 'RBI', 'SB'] + temp_stat_cols

        res = pd.Series()
        for stat in hit_stat_cols:
            val = 0
            for plyr in df.iterrows():
                if plyr[1]['roster_type'] != 'B':
                    continue
                if plyr[1]['SEASON_G'] > 0:
                    val += plyr[1][stat] / plyr[1]['SEASON_G'] * \
                        plyr[1]['WK_G']
            res[stat] = val

        # Handle ratio stats
        if res['AB'] > 0:
            res['AVG'] = res['H'] / res['AB']
        else:
            res['AVG'] = None
        if res['AB'] + res['BB'] > 0:
            res['OBP'] = (res['H'] + res['BB']) / \
                (res['AB'] + res['BB'])
        else:
            res['OBP'] = None

        # Drop the temporary values used to calculate the ratio stats
        res = res.drop(index=temp_stat_cols)

        return res

    def _sum_pit_prediction(self, df):
        temp_stat_cols = ['G', 'ER', 'IP', 'BB', 'H']
        pit_stat_cols = ['SO', 'SV', 'HLD', 'W'] + temp_stat_cols

        res = pd.Series()
        for stat in pit_stat_cols:
            val = 0
            for plyr in df.iterrows():
                if plyr[1]['roster_type'] != 'P':
                    continue
                # Account for number of known starts (if applicable).
                # Otherwise, just revert to an average over the remaining games
                # on the team's schedule.
                if plyr[1]['WK_GS'] > 0:
                    val += plyr[1][stat] / plyr[1]['G'] \
                        * plyr[1]['WK_GS']
                elif plyr[1]['WK_G'] > 0:
                    val += plyr[1][stat] / plyr[1]['SEASON_G'] \
                        * plyr[1]['WK_G']
            res[stat] = val

        # Handle ratio stats
        if res['IP'] > 0:
            res['WHIP'] = (res['BB'] + res['H']) / res['IP']
            res['ERA'] = res['ER'] * 9 / res['IP']
        else:
            res['WHIP'] = None
            res['ERA'] = None

        # Delete the temporary values used to calculate the ratio stats
        res = res.drop(index=temp_stat_cols)

        return res

    def _is_counting_stat(self, stat):
        return stat in ['R', 'HR', 'RBI', 'SB', 'W', 'SO', 'SV', 'HLD']

    def _is_highest_better(self, stat):
        return stat not in ['ERA', 'WHIP']


class Builder:
    """Class that generates roster permuations suitable for evaluation"""
    def __init__(self, positions):
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
        :type roster: list
        :param player: Player to try and find a roster spot for.
        :type player: pandas.Series
        :return: The new roster with the player in it.  If an open spot is not
        available for the player then an LookupError assertion is returned.
        :rtype: list
        """
        # Search if any of the players eligible_positions are open.  Then it is
        # an easy fit.
        for pos in player.eligible_positions:
            if self._has_empty_position_slot(roster, pos):
                player.selected_position = pos
                roster.append(player)
                return roster

        checked_pos = {}
        for p in self.positions:
            checked_pos[p] = 0

        # Look through the other players already starting at the new players
        # positions.  If any of them can move to empty spot then we can fit.
        for pos in player.eligible_positions:
            for occurance in range(self.pos_count[pos]):
                plyr_at_pos = self._get_player_by_pos(roster, pos, occurance)
                if self._swap_eligible_pos_recurse(roster, plyr_at_pos,
                                                   checked_pos):
                    assert(self._has_empty_position_slot(roster, pos))
                    player.selected_position = pos
                    roster.append(player)
                    return roster

        raise LookupError("No space for player on roster")

    def enumerate_fit(self, roster, player):
        """Generate possible enumerations by fitting the player on the roster

        This function will actively remove players in order to get the player
        to fit.

        :param roster: Base roster to try and add the player too
        :type roster: list
        :param player: Player to try and fit into the roster
        :type player: pandas.Series
        :return: An iterable that will enumerate all possible roster
        combinations to get the player to fit.
        :rtype: iterable
        """
        # Keeps track of the number of times we checked each position
        checked_pos = {}

        for pos in self.positions:
            orig_roster = []
            for plyr in roster:
                orig_roster.append(plyr.copy())
            if pos not in checked_pos:
                checked_pos[pos] = 0
            else:
                checked_pos[pos] += 1
            pos_player = self._get_player_by_pos(roster, pos, checked_pos[pos])
            if pos_player is None:
                continue
            pos_player.selected_position = np.nan
            try:
                new_roster = self.fit_if_space(roster, player)

                # Remove anyone from the roster that doesn't have a selected
                # position
                pruned_roster = []
                for plyr in new_roster:
                    if type(plyr['selected_position']) == str:
                        pruned_roster.append(plyr)

                yield pruned_roster
            except LookupError:
                pass
            finally:
                roster = orig_roster
                player.selected_position = np.nan

    def _get_player_by_pos(self, roster, pos, occurance):
        cum_occurance = 0
        for plyr in roster:
            if plyr.selected_position == pos:
                if cum_occurance == occurance:
                    return plyr
                cum_occurance += 1
        return None

    def _get_num_players_at_pos(self, roster, pos):
        """Return the number of players the roster has at the given position"""
        cum_occurance = 0
        for plyr in roster:
            if plyr.selected_position == pos:
                cum_occurance += 1
        return cum_occurance

    def _has_empty_position_slot(self, roster, pos):
        assert(pos in self.pos_count)
        num = self._get_num_players_at_pos(roster, pos)
        return num < self.pos_count[pos]

    def _swap_eligible_pos_recurse(self, roster, player, checked_pos):
        """Recursively swap positions with players until all positions are used

        :param roster: The roster to work with
        :type roster: pandas.DataFrame
        :param player: The player to try and swap around.
        :type player: pandas.Series
        :param checked_pos: A list of positions that have been recursed on.
        This is used to prevent infinite recursion on positions we have already
        checked.
        :type cheecked_pos: list
        :return: True if we were able to swap to an empty position
        :rtype: Boolean
        """
        assert(player.selected_position is not None)

        # Check if player can change their position to an empty spot
        for pos in player.eligible_positions:
            if pos != player.selected_position:
                if self._has_empty_position_slot(roster, pos):
                    player.selected_position = pos
                    return True

        # Recursively check each of the positions that the player plays to
        # see if they can switch out to an empty spot.
        for pos in player.eligible_positions:
            for _ in range(self.pos_count[pos]):
                if pos != player.selected_position and \
                        checked_pos[pos] < self.pos_count[pos]:
                    other_plyr = self._get_player_by_pos(roster, pos,
                                                         checked_pos[pos])
                    assert(other_plyr is not None), "Nobody for " + pos
                    checked_pos[pos] += 1
                    if self._swap_eligible_pos_recurse(roster, other_plyr,
                                                       checked_pos):
                        assert(self._has_empty_position_slot(roster, pos))
                        player.selected_position = pos
                        return True
        return False


class PlayerSelector:
    RANK_STATS_DESCENDING = ["ERA", "WHIP"]

    """Class that will select players from a container to include on a roster.

    The roster container it is given should be a pool of all available players
    that can make up a roster.  The players select are players that are tops
    in the stats categories.

    :param player_pool: Pool of players that we will pick from
    :type player_pool: Container
    """
    def __init__(self, player_pool):
        self.ppool = player_pool

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

    def select(self):
        """Iterate over players in the pool according to the rank

        This is to be called after rank().  It will return the players starting
        with the top ranked player.
        """
        df = self.ppool.sort_values(by=['rank'], ascending=False)
        for plyr_tuple in df.iterrows():
            yield plyr_tuple[1]

    def _is_stat_ascending(self, stat):
        if stat in self.RANK_STATS_DESCENDING:
            return False
        else:
            return True
