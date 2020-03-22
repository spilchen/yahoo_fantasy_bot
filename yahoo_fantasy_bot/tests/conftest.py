#!/usr/bin/python

import pytest
import pandas as pd
import numpy as np
from yahoo_fantasy_bot import roster

RBLDR_COLS = ["player_id", "name", "eligible_positions", "selected_position"]
RSEL_COLS = ["player_id", "name", "HR", "OBP", "W", "ERA"]


@pytest.fixture
def empty_roster():
    rcont = roster.Container()
    yield rcont


@pytest.fixture
def bldr():
    b = roster.Builder(["C", "1B", "2B", "SS", "3B", "LF", "CF", "RF", "Util",
                        "SP", "SP", "SP", "SP", "SP",
                        "RP", "RP", "RP", "RP", "RP"])
    yield b


@pytest.fixture
def fake_player_selector():
    player_pool = pd.DataFrame(
        [[1, "Borders", 15, 0.319, np.nan, np.nan],
         [2, "Lee", 6, 0.288, np.nan, np.nan],
         [3, "McGriff", 35, 0.400, np.nan, np.nan],
         [4, "Fernandez", 4, 0.352, np.nan, np.nan],
         [5, "Gruber", 31, 0.330, np.nan, np.nan],
         [6, "Bell", 21, 0.303, np.nan, np.nan],
         [7, "Wilson", 3, 0.300, np.nan, np.nan],
         [8, "Felix", 15, 0.318, np.nan, np.nan],
         [9, "Olerud", 14, 0.364, np.nan, np.nan],
         [10, "Hill", 12, 0.281, np.nan, np.nan],
         [11, "Steib", np.nan, np.nan, 18, 2.93],
         [12, "Stottlemyre", np.nan, np.nan, 13, 4.34],
         [13, "Wells", np.nan, np.nan, 11, 3.14],
         [14, "Key", np.nan, np.nan, 13, 4.25],
         [15, "Cerutti", np.nan, np.nan, 9, 4.76]], columns=RSEL_COLS)
    plyr_sel = roster.PlayerSelector(player_pool)
    yield plyr_sel
