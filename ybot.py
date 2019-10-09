#!/bin/python

"""A bot that acts as a manager for Yahoo! fantasy team

Usage:
  ybot.py <cfg_file>

  <cfg_file>  The name of the configuration file.  See sample_config.ini for
              the format.
"""
from docopt import docopt
from yahoo_baseball_assistant import cli
import logging
import os
import pandas as pd
import configparser


pd.options.mode.chained_assignment = None  # default='warn'


if __name__ == '__main__':
    args = docopt(__doc__, version='1.0')

    logging.basicConfig(
        filename='ybot.log',
        level=logging.INFO,
        format='%(asctime)s.%(msecs)03d %(module)s-%(funcName)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logging.getLogger('yahoo_oauth').setLevel('WARNING')
    logging.getLogger('chardet.charsetprober').setLevel('WARNING')

    cfg = configparser.ConfigParser()
    if not os.path.exists(args['<cfg_file>']):
        raise RuntimeError("Config file does not exist: " + args['<cfg_file>'])
    cfg.read(args['<cfg_file>'])

    cli = cli.Driver(cfg)
    cli.run()
