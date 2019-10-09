# Yahoo! Fantasy Bot

_A bot that can act as a manager in a Yahoo! fantasy league_

## Build status

[![Build Status](https://travis-ci.com/spilchen/yahoo_baseball_assistant.svg?branch=master)](https://travis-ci.com/spilchen/yahoo_baseball_assistant)

## Installation

One time setup:
```
git clone https://github.com/spilchen/yahoo_baseball_assistant.git
cd yahoo_baseball_assistant
virtualenv --python=python3.7 env
source env/bin/activate
pip install -r requirements.txt
# You can get your key/secret from https://developer.yahoo.com/apps/create/.  You must request read/write access.
python examples/init_oauth_env.py -k <yahoo_consumer_key> -s <yahoo_secret_key> oauth2.json
```

You need to setup a config file to tune the program for your specific league.  Use sample_config.ini as a guide.

Once installed and the config file created, you can run the program via this command:
```
python ybot.py <cfg_file>
```
