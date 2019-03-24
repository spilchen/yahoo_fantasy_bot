#!/bin/python

"""
Run this script to authenticate with Yahoo!  It will pop up a web browser
window to confirm the permissions.

The credentials will be stored in a JSON file for future use.
"""
from yahoo_oauth import OAuth2
import os
import json


if not os.path.exists(os.environ['YAHOO_AUTH_JSON']):
    creds = {}
    creds['consumer_key'] = os.environ['YAHOO_CLIENT_ID']
    creds['consumer_secret'] = os.environ['YAHOO_CLIENT_SECRET']
    with open(os.environ['YAHOO_AUTH_JSON'], "w") as f:
        f.write(json.dumps(creds))

oauth = OAuth2(None, None, from_file=os.environ['YAHOO_AUTH_JSON'])

if not oauth.token_is_valid():
    oauth.refresh_access_token()
