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

