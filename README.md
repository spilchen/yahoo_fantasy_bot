# Yahoo! Baseball Assistant

_Python script for assisting with a Yahoo! Baseball Fantasy team_

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
# You can get your key/secret from https://developer.yahoo.com/apps/create/
python examples/init_oauth_env.py -k <yahoo_consumer_key> -s <yahoo_secret_key> oauth2.json
```

Once installed you can run the program via this command:
```
python examples/yba.py oauth2.json
```

## User Guide
Once you start the program, it will list out your current as pulled from Yahoo!

![Image of roster](https://github.com/images/roster.png)

If you press OK from this screen, it will scrape data from the internet to predict the outcome for your next week of play.  The summary of prediction will list your team along with all of other teams in the league.

![Image of prediction](https://github.com/images/prediction.png)
