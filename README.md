# yahoo-baseball-assistant

*ML notebooks and scripts for assisting with a Yahoo! Baseball Fantasy team

## Build status

[![Build Status](https://travis-ci.com/spilchen/yahoo_baseball_assistant.svg?branch=master)](https://travis-ci.com/spilchen/yahoo_baseball_assistant)

## Setup

The environment to run the notebooks and scripts is encapsulated in an anaconda-project.  Read the [docs](https://anaconda-project.readthedocs.io/en/latest/install.html) on how to install anaconda-project.  

To run scripts that rely on Yahoo! Fantasy APIs, you need to request credentials from [Yahoo!](https://developer.yahoo.com/apps/create/)  When requesting be sure to get Read access to Fantasy Sports.

After you have acquired the credentials you need to store them in the anaconda-project.yml as variables so the scripts can use them.  The credentials are initially stored with place holder values.  To add your actual values, you can do so with the following commands:
```
anaconda-project set-variable YAHOO_CONSUMER_ID=<yourID>
anaconda-project set-variable YAHOO_CONSUMER_SECRET=<yourSecret>
```

To authenticate with Yahoo! you need to run a script to confirm the permissions.  This only needs to be run once:
```
anaconda-project run python src/yahoo_auth.py
```

Once anaconda-project is installed and credentials have been added and setup, you can start a notebook via:

```
anaconda-project run notebook
```

Or to start up a bash shell to run the scripts:

```
anaconda-project run bash
```
