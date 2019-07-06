#!/bin/python

import pytest
from yahoo_baseball_assistant import hitting
from baseball_id.factory import Factory
from baseball_scraper import fangraphs


@pytest.fixture()
def hitting_builder():
    bldr = hitting.Builder(None, 1)
    bldr.set_id_lookup(Factory.create_fake())
    fg = fangraphs.Scraper()
    fg.load_fake_cache()
    bldr.set_fg_scraper(fg)
    yield bldr
