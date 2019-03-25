#!/bin/python

"""
Run this script to authenticate with Yahoo!  It will pop up a web browser
window to confirm the permissions.

The credentials will be stored in a JSON file for future use.  So this only
needs to be done after a fresh git clone.
"""
from yahoo_baseball_assistant import auth


if __name__ == "__main__":
    auth.get_session()
