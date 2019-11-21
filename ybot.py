#!/bin/python

"""A bot that acts as a manager for Yahoo! fantasy team

Usage:
  ybot.py [-id] [--full=<pct>] <cfg_file>

  <cfg_file>  The name of the configuration file.  See sample_config.ini for
              the format.

Options:
  -i, --interactive   Run the program in interactive mode.
  -d, --dry-run       Does a dry run of the roster change.  No roster change
                      will actually occur.
  --full=<pct>        Does a full analysis of the entire lineup meaning all
                      players will be evaluated in an optimized lineup.  This
                      can potentially add a lot of churn to your lineup.  The
                      alternative is to just consider optimizing the open slots
                      in the lineup and the bench.  The value for this option
                      is a probability that a full optimization will occur.
                      The value ranges from 0-100.    [Default: 10]

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
    logging.getLogger('chardet.charsetprober').setLevel('WARNING')

    if args['--interactive']:
        intr = interactive.Driver(cfg)
        intr.run()
    else:
        auto = automation.Driver(cfg, args['--dry-run'], args['--full'])
        auto.run()
