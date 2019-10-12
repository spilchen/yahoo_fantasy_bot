#!/usr/bin/python

import unicodedata
import os


def normalized(name):
    """Normalize a name to remove any accents

    :param name: Input name to normalize
    :type name: str
    :return: Normalized name
    :rtype: str
    """
    return unicodedata.normalize('NFD', name).encode(
        'ascii', 'ignore').decode('utf-8')


class TeamCache:
    def __init__(self, cfg, team_key):
        self.cache_dir = "{}/{}".format(cfg['Cache']['dir'], team_key)
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

    def lineup_cache_file(self):
        return "{}/lineup.pkl".format(self.cache_dir)

    def bench_cache_file(self):
        return "{}/bench.pkl".format(self.cache_dir)

    def blacklist_cache_file(self):
        return "{}/blacklist.pkl".format(self.cache_dir)


class LeagueCache:
    def __init__(self, cfg):
        self.cache_dir = cfg['Cache']['dir']
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

    def free_agents_cache_file(self):
        return "{}/free_agents.pkl".format(self.cache_dir)

    def prediction_builder_cache_file(self):
        return "{}/pred_builder.pkl".format(self.cache_dir)
