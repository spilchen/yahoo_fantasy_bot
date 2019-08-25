#!/usr/bin/python

import pytest
import pandas as pd
from yahoo_baseball_assistant import roster

RBLDR_COLS = ["name", "eligible_positions", "selected_position"]


@pytest.fixture
def empty_roster():
    df = pd.DataFrame([], columns=RBLDR_COLS)
    yield df


@pytest.fixture
def bldr():
    b = roster.Builder()
    yield b
