#!/usr/bin/python

import unicodedata
import os
import pickle
import time


def normalized(name):
    """Normalize a name to remove any accents

    :param name: Input name to normalize
    :type name: str
    :return: Normalized name
    :rtype: str
    """
    return unicodedata.normalize('NFD', name).encode(
        'ascii', 'ignore').decode('utf-8')


def pickle_if_recent(fn):
    if os.path.exists(fn):
        mtime = os.path.getmtime(fn)
        cur_time = int(time.time())
        sec_per_day = 24 * 60 * 60
        if cur_time - mtime <= sec_per_day:
            with open(fn, 'rb') as f:
                obj = pickle.load(f)
                # Don't save this to file on exit.
                obj.save_on_exit = False
                return obj
    return None
