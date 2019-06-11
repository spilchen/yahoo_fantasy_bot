#!/bin/python

import pytest
from yahoo_baseball_assistant import hitting
from baseball_id.factory import Factory


@pytest.fixture()
def hitting_builder():
    bldr = hitting.Builder()
    bldr.set_id_lookup(Factory.create_fake())
    yield bldr
