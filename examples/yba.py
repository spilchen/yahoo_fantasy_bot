#!/bin/python

"""Predict the stats for the players currently on your roster

Usage:
  predict.py <json>

  <json>     The name of the JSON that has bearer token.  This can be generated
             from init_oauth_env.py.
"""
from docopt import docopt
import npyscreen
import logging
import pickle
import os
import time
import math
from yahoo_oauth import OAuth2
from yahoo_fantasy_api import league, game, team
from yahoo_baseball_assistant import prediction
from baseball_scraper import fangraphs, baseball_reference


logging.basicConfig(
    filename='yba.log',
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d %(module)s - %(funcName)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger()
JSON_FILE = None


class CellColorPicker:
    def __init__(self, value=None, highest_is_best=True, is_ratio=False):
        self.value = value
        self.highest_is_best = highest_is_best
        self.is_ratio = is_ratio

    def pick_color(self, cval):
        if self.value is None:
            return 'DEFAULT'
        else:
            if self.is_ratio:
                other_val = float(cval)
                my_val = float(self.value)
                if math.isclose(other_val, my_val):
                    return 'DEFAULT'
                else:
                    if self.highest_is_best:
                        if other_val > my_val:
                            return 'DANGER'
                        else:
                            return 'GOOD'
                    else:
                        if other_val < my_val:
                            return 'DANGER'
                        else:
                            return 'GOOD'
            else:
                other_val = int(cval)
                my_val = int(self.value)
                if other_val == my_val:
                    return 'DEFAULT'
                else:
                    if self.highest_is_best:
                        if other_val > my_val:
                            return 'DANGER'
                        else:
                            return 'GOOD'
                    else:
                        if other_val < my_val:
                            return 'DANGER'
                        else:
                            return 'GOOD'

    def update_value(self, value):
        self.value = value


class ColorRosterGrid(npyscreen.GridColTitles):
    def set_cell_color_pickers(self, pickers):
        """Set color pickers for each column in the grid

        self.color_pickers is a list of CellColorPickers (one for each cell).
        It is used to pick the appropriate color for the cell.

        :param pickers: objects that pick the color for the column.  There
        should be one of these for each column in the grid.
        :type pickers: list(CellColorPicker)
        """
        self.pickers = pickers

    def get_cell_color_pickers(self):
        return self.pickers

    def custom_print_cell(self, actual_cell, cell_display_value):
        if actual_cell.grid_current_value_index != -1:
            row, col = actual_cell.grid_current_value_index
            picker = self.pickers[col]
            actual_cell.color = picker.pick_color(cell_display_value)


class MyRosterForm(npyscreen.ActionFormWithMenus):
    def create(self):
        self.add(npyscreen.MultiLineEdit,
                 value="""
Here are the players on your roster.  Press OK to predict the outcome of the
roster.  Press Cancel to quit the application.
""",
                 editable=False, max_height=4)
        self.team_name = self.add(npyscreen.TitleFixedText, name='Team Name',
                                  value='Lumber Kings')
        self.team_key = self.add(npyscreen.TitleFixedText, name='Team Key',
                                 value=self.parentApp.team_key)
        self.team_key = self.add(npyscreen.FixedText, name='space',
                                 editable=False)
        self.roster = self.add(npyscreen.GridColTitles, name='Roster',
                               col_titles=['Pos', 'Name'],
                               values=None)

        self.menu = self.new_menu(name="Options")
        self.menu.addItem(text="Change Position",
                          onSelect=self.change_position,
                          shortcut='^P')
        self.menu.addItem(text="Add Player",
                          onSelect=self.add_player,
                          shortcut='^A')
        self.menu.addItem(text="Delete Player",
                          onSelect=self.delete_player,
                          shortcut='^D')

    def beforeEditing(self):
        self.roster.values = []
        my_team = self.parentApp.team_bldrs[self.parentApp.team_key]
        for plyr in my_team.get_roster():
            self.roster.values.append([plyr['selected_position'],
                                       plyr['name']])

    def on_cancel(self):
        self.parentApp.setNextForm(None)

    def on_ok(self):
        self.parentApp.setNextForm('PREDICTSUMMARY')

    def change_position(self):
        if self.roster.edit_cell is not None:
            logging.info("Roster edit cell: {}".format(
                self.roster.edit_cell))
            self.parentApp.selected_player = self.roster.values[
                self.roster.edit_cell[0]][1]
            logger.info("Open diaglog to change position {}".format(
                self.parentApp.selected_player))
            self.parentApp.switchForm('CHANGEPOS')

    def add_player(self):
        self.parentApp.switchForm('ADDPLAYER')

    def delete_player(self):
        if self.roster.edit_cell is not None:
            logging.info("Roster edit cell: {}".format(
                self.roster.edit_cell))
            self.parentApp.selected_player = self.roster.values[
                self.roster.edit_cell[0]][1]
            logger.info("Open diaglog to delete {}".format(
                self.parentApp.selected_player))
            self.parentApp.switchForm('DELPLAYER')


class PredictedRosterStatForm(npyscreen.Form):
    def create(self):
        npyscreen.notify("Scraping data for detailed look at prediction.  " +
                         "Please wait...")
        self.team_name = self.add(npyscreen.TitleFixedText,
                                  name='Team Name',
                                  value=self.parentApp.predict_team['name'])
        self.team_key = self.add(npyscreen.TitleFixedText,
                                 name='Team Key',
                                 value=self.parentApp.predict_team['team_key'])
        df = self.parentApp.team_bldrs[
            self.parentApp.predict_team['team_key']].predict()
        self.roster = self.add(
            npyscreen.GridColTitles, name='Roster',
            col_titles=self.parentApp.get_columns(),
            values=self.parentApp.gen_team(df))

    def afterEditing(self):
        self.parentApp.switchFormPrevious()


class AddPlayerForm(npyscreen.ActionPopup):
    def create(self):
        self.name = self.add(npyscreen.TitleText, name='Name')
        self.pos = self.add(npyscreen.SelectOne, name='Position',
                            values=['C', '1B', '2B', '3B', 'SS', 'LF', 'CF',
                                    'RF', 'Util', 'SP', 'RP'])

    def on_ok(self):
        if self.pos.value is None or len(self.pos.value) == 0:
            npyscreen.notify_confirm('Select a position')
        else:
            try:
                self.parentApp.add_player(self.name.value,
                                          self.pos.values[self.pos.value[0]])
            except ValueError as e:
                npyscreen.notify_confirm('Error adding player: {}'.format(e))
            self.parentApp.switchFormPrevious()

    def on_cancel(self):
        self.parentApp.switchFormPrevious()


class DeletePlayerForm(npyscreen.ActionPopup):
    def create(self):
        self.add(npyscreen.FixedText,
                 name='Confirm Message',
                 value='Press OK to remove this player from your roster',
                 rely=3, editable=False)
        self.add(npyscreen.FixedText,
                 name='Player Name',
                 value=self.parentApp.selected_player,
                 editable=False, relx=5)

    def on_ok(self):
        self.parentApp.del_player(self.parentApp.selected_player)
        self.parentApp.switchFormPrevious()

    def on_cancel(self):
        self.parentApp.switchFormPrevious()


class ChangePositionForm(npyscreen.ActionPopup):
    def create(self):
        self.name = self.add(npyscreen.TitleText, name='Name')
        self.pos = self.add(npyscreen.SelectOne, name='Position',
                            values=['C', '1B', '2B', '3B', 'SS', 'LF', 'CF',
                                    'RF', 'Util', 'SP', 'RP', 'BN', 'DL'])

    def beforeEditing(self):
        self.name.value = self.parentApp.selected_player
        self.pos.value = [0]

    def on_ok(self):
        if self.pos.value is None or len(self.pos.value) == 0:
            pos = 'BN'
        else:
            pos = self.pos.values[self.pos.value[0]]

        try:
            self.parentApp.change_position(self.parentApp.selected_player, pos)
        except ValueError as e:
            npyscreen.notify_confirm('Error changing position: {}'.format(e))
        self.parentApp.switchFormPrevious()

    def on_cancel(self):
        self.parentApp.switchFormPrevious()


class PredictSummaryForm(npyscreen.ActionFormWithMenus):
    def create(self):
        help_text = """
Show the prediction of your roster and how it compares against your opponents.
The prediction is just for the next fantasy week and so only takes into account
the predicted amount of games each player will play.

Press OK to return back to your roster.  Press Cancel to quit the application.
"""
        self.add(npyscreen.MultiLineEdit, value=help_text, editable=False,
                 height=7)
        self.add(npyscreen.FixedText, value="Your predictions:",
                 editable=False)
        self.hit_stats = []
        for stat in self.parentApp.get_hit_stats():
            self.hit_stats.append(self.add(npyscreen.TitleFixedText,
                                           name=stat))
        self.pit_stats = []
        for stat in self.parentApp.get_pit_stats():
            self.pit_stats.append(self.add(npyscreen.TitleFixedText,
                                           name=stat))

        self.add(npyscreen.MultiLineEdit,
                 value="""
Comparison with your opponents.  The team with the prefixed '*' is the
opponent for your next week.
""",
                 editable=False, height=4)
        col_titles = ['Team', 'Win', 'Loss'] + self.parentApp.get_hit_stats() \
            + self.parentApp.get_pit_stats()
        self.roster = self.add(ColorRosterGrid, name='Summary',
                               col_titles=col_titles)
        color_pickers = [CellColorPicker(), CellColorPicker(),
                         CellColorPicker()]
        for _ in self.parentApp.get_counting_hit_stats():
            color_pickers.append(CellColorPicker(is_ratio=False,
                                                 highest_is_best=True))
        for _ in self.parentApp.get_ratio_hit_stats():
            color_pickers.append(CellColorPicker(is_ratio=True,
                                                 highest_is_best=True))
        for _ in self.parentApp.get_counting_pit_stats():
            color_pickers.append(CellColorPicker(is_ratio=False,
                                                 highest_is_best=True))
        for _ in self.parentApp.get_ratio_pit_stats():
            color_pickers.append(CellColorPicker(is_ratio=True,
                                                 highest_is_best=False))
        self.roster.set_cell_color_pickers(color_pickers)

        self.menu = self.new_menu(name="Options")
        self.menu.addItem(text="My predicted stats",
                          onSelect=self.show_my_predicted_stats_detail,
                          shortcut='^M')
        self.menu.addItem(text="Opponents predicted stats",
                          onSelect=self.show_opp_predicted_stats_detail,
                          shortcut='^O')

    def show_my_predicted_stats_detail(self):
        self.parentApp.predict_team = {'team_key': self.parentApp.team_key,
                                       'name': 'Lumberkings'}
        self.parentApp.switchForm('PREDICTROSTER')

    def show_opp_predicted_stats_detail(self):
        if self.roster.edit_cell is not None:
            teams = self.parentApp.get_opp_teams()
            logging.info("Show roster edit cell: {}".format(
                self.roster.edit_cell))
            self.parentApp.predict_team = teams[self.roster.edit_cell[0]]
            logging.info("Show roster of opponent: {}".format(
                self.parentApp.predict_team))
            self.parentApp.switchForm('PREDICTROSTER')

    def beforeEditing(self):
        npyscreen.notify("Scraping data for prediction.  Please wait...")
        my_sum = self.parentApp.team_bldrs[self.parentApp.team_key] \
            .sum_prediction(self.parentApp.df)
        logging.info(my_sum)
        for name, picker in zip([None, None, None] +
                                self.parentApp.get_hit_stats() +
                                self.parentApp.get_pit_stats(),
                                self.roster.pickers):
            if name is not None:
                picker.update_value(my_sum[name])

        for name, stat in zip(self.parentApp.get_hit_stats(), self.hit_stats):
            if name in self.parentApp.get_counting_hit_stats():
                stat.value = int(my_sum[name])
            else:
                stat.value = "{:.3f}".format(my_sum[name])
        for name, stat in zip(self.parentApp.get_pit_stats(), self.pit_stats):
            if name in self.parentApp.get_counting_pit_stats():
                stat.value = str(int(my_sum[name]))
            else:
                stat.value = "{:.3f}".format(my_sum[name])

        teams = self.parentApp.get_opp_teams()
        self.roster.values = []
        for tm in teams:
            logger.info("Scraping team: " + str(tm))
            df = self.parentApp.team_bldrs[tm['team_key']].predict()
            logger.info("Sum prediction: " + str(tm))
            opp_sum = self.parentApp.team_bldrs[tm['team_key']] \
                .sum_prediction(df)
            logger.info(opp_sum)
            logger.info("Score: " + str(tm))
            (w, l) = self.parentApp.team_bldrs[tm['team_key']].score(my_sum,
                                                                     opp_sum)
            logger.info("Scoring result: {} - {}".format(w, l))
            team_res = []
            # Add an asterisk beside the name to denote the week opponent
            if tm['team_key'] == self.parentApp.matchup:
                team_prefix = '(*) '
            else:
                team_prefix = ''
            team_res.append(team_prefix + tm['name'])
            team_res.append(w)
            team_res.append(l)
            for stat in self.parentApp.get_counting_hit_stats():
                team_res.append(int(opp_sum[stat]))
            for stat in self.parentApp.get_ratio_hit_stats():
                team_res.append("{:.3f}".format(opp_sum[stat]))
            for stat in self.parentApp.get_counting_pit_stats():
                team_res.append(int(opp_sum[stat]))
            for stat in self.parentApp.get_ratio_pit_stats():
                team_res.append("{:.3f}".format(opp_sum[stat]))
            self.roster.values.append(team_res)

    def on_cancel(self):
        self.parentApp.setNextForm(None)

    def on_ok(self):
        self.parentApp.setNextForm('MAIN')


class YahooAssistant(npyscreen.NPSAppManaged):
    def onStart(self):
        logging.getLogger('yahoo_oauth').setLevel('WARNING')
        logging.getLogger('chardet.charsetprober').setLevel('WARNING')
        self.sc = OAuth2(None, None, from_file=JSON_FILE)
        self.gm = game.Game(self.sc, 'mlb')
        league_id = self.gm.league_ids(year=2019)
        self.lg = league.League(self.sc, league_id[0])
        self.team_key = self.lg.team_key()
        self.predict_team = None
        self.my_tm = team.Team(self.sc, self.team_key)
        self.matchup = self.my_tm.matchup(self.lg.current_week() + 1)
        self.init_team_bldrs()
        self.df = self.team_bldrs[self.team_key].predict()
        self.teams = None
        self.selected_player = None

        self.addForm('MAIN', MyRosterForm, name='My Roster')
        self.addForm('PREDICTSUMMARY', PredictSummaryForm,
                     name='Prediction Summary')
        self.addFormClass('PREDICTROSTER', PredictedRosterStatForm,
                          name='Predicted Roster Stats')
        self.addFormClass('ADDPLAYER', AddPlayerForm,
                          name='Add Player')
        self.addFormClass('DELPLAYER', DeletePlayerForm,
                          name='Delete Player')
        self.addFormClass('CHANGEPOS', ChangePositionForm,
                          name='Change Position')

    def init_team_bldrs(self):
        self.team_bldrs = {}
        fg = fangraphs.Scraper("Depth Charts (RoS)")
        ts = baseball_reference.TeamScraper()
        for tm in self.lg.teams():
            fn = "{}.pkl".format(tm['team_key'])
            if os.path.exists(fn):
                mtime = os.path.getmtime(fn)
                cur_time = int(time.time())
                sec_per_day = 24 * 60 * 60
                if cur_time - mtime <= sec_per_day:
                    logger.info("Reading team {} from cache...".format(fn))
                    with open(fn, 'rb') as f:
                        self.team_bldrs[tm['team_key']] = pickle.load(f)
                        # Don't save this to file on exit.
                        self.team_bldrs[tm['team_key']].save_on_exit = False
                    continue
            logger.info("Building new team {} ...".format(tm['team_key']))
            self.team_bldrs[tm['team_key']] = prediction.Builder(
                self.lg, self.lg.to_team(tm['team_key']), fg, ts)
            self.team_bldrs[tm['team_key']].save_on_exit = True

    def save_cached_team_bldrs(self):
        for team_key, bldr in self.team_bldrs.items():
            if bldr.save_on_exit:
                fn = "{}.pkl".format(team_key)
                with open(fn, 'wb') as f:
                    pickle.dump(bldr, f)

    def gen_team(self, df):
        roster = []
        columns = self.get_columns()
        for plyr in df.iterrows():
            roster.append([plyr[1][x] for x in columns])
        return roster

    def get_columns(self):
        return ['Name', 'team', 'WK_G', 'G', 'AB'] + self.get_hit_stats() + \
            self.get_pit_stats()

    def get_hit_stats(self):
        return self.get_counting_hit_stats() + self.get_ratio_hit_stats()

    def get_counting_hit_stats(self):
        return ['R', 'HR', 'RBI', 'SB']

    def get_ratio_hit_stats(self):
        return ['AVG', 'OBP']

    def get_pit_stats(self):
        return self.get_counting_pit_stats() + self.get_ratio_pit_stats()

    def get_counting_pit_stats(self):
        return ['W', 'SO', 'SV', 'HLD']

    def get_ratio_pit_stats(self):
        return ['ERA', 'WHIP']

    def get_opp_teams(self):
        if self.teams is None:
            self.teams = []
            for tm in self.lg.teams():
                if tm['team_key'] == self.team_key:
                    continue
                self.teams.append(tm)
        return self.teams

    def del_player(self, player_name):
        self.team_bldrs[self.team_key].del_player(player_name)

    def add_player(self, player_name, pos):
        self.team_bldrs[self.team_key].add_player(player_name, pos)

    def change_position(self, player_name, pos):
        self.team_bldrs[self.team_key].change_position(player_name, pos)


if __name__ == '__main__':
    args = docopt(__doc__, version='1.0')
    JSON_FILE = args['<json>']
    app = YahooAssistant()
    app.run()
    app.save_cached_team_bldrs()
