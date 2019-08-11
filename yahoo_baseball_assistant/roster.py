#!/usr/bin/python

from yahoo_baseball_assistant import utils
import pandas as pd


class Container:
    """Class that holds a roster of players

    :param lg: Yahoo! league
    :type lg: yahoo_fantasy_api.league.League
    :param team: Yahoo! Team to do the predictions for
    :type team: yahoo_fantasy_api.team.Team
    """
    def __init__(self, lg, team):
        self.week = lg.current_week() + 1
        if self.week >= lg.end_week():
            raise RuntimeError("Season over no more weeks to predict")
        self.roster = team.roster(self.week)

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

        :param player_name: Full name of the player to delete.  The player name
               must this exactly; with the exception of accents, which are
               normalized out
        :type player_name: str
        :param pos: The short version of the position.
        :type pos: str
        """
        if self.player_exists(player_name):
            raise ValueError("Player is already on the roster")

        self.roster.append({'position_type': self.get_position_type(pos),
                            'selected_position': pos,
                            'name': player_name,
                            'player_id': -1})

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
            if conv_l > conv_r:
                win += 1
            elif conv_r > conv_l:
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
                if plyr[1]['G'] > 0:
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
