#!/bin/python

"""A bot that acts as a manager for Yahoo! fantasy team

Usage:
  ybot.py [-a] <cfg_file>

  <cfg_file>  The name of the configuration file.  See sample_config.ini for
              the format.

Options:
  -a, --auto   Run the program in automated mode.  CAUTION: All lineup
               decisions are done without any human intervention.
"""
from docopt import docopt
from yahoo_fantasy_bot import interactive, automation
import logging
import os
import pandas as pd
import configparser
from imp import reload


pd.options.mode.chained_assignment = None  # default='warn'


if __name__ == '__main__':
    args = docopt(__doc__, version='1.0')

    cfg = configparser.ConfigParser()
    if not os.path.exists(args['<cfg_file>']):
        raise RuntimeError("Config file does not exist: " + args['<cfg_file>'])
    cfg.read(args['<cfg_file>'])

    reload(logging)
    logging.basicConfig(
        filename=cfg['Logger']['file'],
        filemode="w",
        level=cfg['Logger']['level'],
        format='%(asctime)s.%(msecs)03d %(module)s-%(funcName)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logging.getLogger('yahoo_oauth').setLevel('WARNING')
    logging.getLogger('chardet.charsetprober').setLevel('WARNING')

    if args['--auto']:
        auto = automation.Driver(cfg)
        auto.run()
    else:
        intr = interactive.Driver(cfg)
        intr.run()
