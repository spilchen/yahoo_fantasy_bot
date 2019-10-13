#!/bin/python

"""A bot that acts as a manager for Yahoo! fantasy team

Usage:
  ybot.py <cfg_file>

  <cfg_file>  The name of the configuration file.  See sample_config.ini for
              the format.
"""
from docopt import docopt
from yahoo_fantasy_bot import cli
import logging
import os
import pandas as pd
import configparser


pd.options.mode.chained_assignment = None  # default='warn'


if __name__ == '__main__':
    args = docopt(__doc__, version='1.0')

    cfg = configparser.ConfigParser()
    if not os.path.exists(args['<cfg_file>']):
        raise RuntimeError("Config file does not exist: " + args['<cfg_file>'])
    cfg.read(args['<cfg_file>'])

    logging.basicConfig(
        filename=cfg['Logger']['file'],
        level=logging.INFO,
        format='%(asctime)s.%(msecs)03d %(module)s-%(funcName)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logging.getLogger('yahoo_oauth').setLevel('WARNING')
    logging.getLogger('chardet.charsetprober').setLevel('WARNING')

    cli = cli.Driver(cfg)
    cli.run()
