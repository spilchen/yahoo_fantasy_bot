#!/bin/python

from yahoo_oauth import OAuth2
import os
import json


def get_session():
    """Does a login getting the session to use for subsequent Yahoo! API calls.

    Returns:
        oauth Session object.
    """
    # The first time that this is called after a fresh git clone, this will
    # redirect to a web-page where you are asked to permit Fantasy Sports read
    # access to this application.  To prevent this from happening each time, we
    # save off extra state in a .json file.  This file is only written if using
    # the `from_file` option to OAuth2.  Setup this file with the minimal info
    # to allow this extra state to be saved.
    if not os.path.exists(os.environ['YAHOO_AUTH_JSON']):
        creds = {}
        creds['consumer_key'] = os.environ['YAHOO_CONSUMER_ID']
        creds['consumer_secret'] = os.environ['YAHOO_CONSUMER_SECRET']
        with open(os.environ['YAHOO_AUTH_JSON'], "w") as f:
            f.write(json.dumps(creds))

    oauth = OAuth2(None, None, from_file=os.environ['YAHOO_AUTH_JSON'])

    if not oauth.token_is_valid():
        oauth.refresh_access_token()
    return oauth
