==================
Yahoo! Fantasy Bot
==================

A bot that can act as a manager in a Yahoo! fantasy league

A$re you in a Yahoo! fantasy league with inactive managers?  Do you face teams that start players on the IR, and have been for weeks?  Or do you need a few more teams in your league?  This program helps eleviate that pain by intelligently managing a Yahoo! fantasy team.  It can optimize the lineup, taken into consideration available players in the free agent pool.  Adjust the IR and bench spots to account for star players that are a little banged up.  Approve or reject trades that are made to the team.  It does all of this by talking directly to Yahoo! without having to enter the transactions manually.  You just run the program whenever you need to set up the lineup, which takes only a few minutes to run.

Build status
------------

.. image:: https://travis-ci.com/spilchen/yahoo_fantasy_bot.svg?branch=master
    :target: https://travis-ci.com/spilchen/yahoo_fantasy_bot

Restrictions
------------
This program will only optimize lineups for teams in a Yahoo! Head-to-Head league.  It only works for teams in mlb or nhl leagues.

Installation
------------

You first neet to setup the environment by installing the app.  You can pull the latest from github

::

  git clone https://github.com/spilchen/yahoo_fantasy_bot.git
  cd yahoo_fantasy_bot
  virtualenv --python=python3.7 env
  source env/bin/activate
  pip install -r requirements.txt

Or you can simply install the package from pip.

::

  pip install yahoo-fantasy-bot


Once the app is installed you need to setup the config file.  The config file is what you pass to the bot.  It includes details about what Yahoo! league you are going to run the bot against, the location of the file that holds the OAuth credentials, what league type it is.  There is a setup wizard that you can run that will get you a working config file for your league.

Before you can run the setup wizard you will first need to request an API key from Yahoo! from: https://developer.yahoo.com/apps/create.   The process is quick.  You will want to request read and write access, since we need write access to make changes to your roster.  Upon completion you will be given a consumer key and a consumer secret that you use with the setup wizard.

With key and secret, run the wizard like this:

::

  ybot_setup -k <consumer key> -s <consumer secret> oauth2.json my.cfg

`oauth2.json` is used to store the credentials to access the team.  Using the key and secret, it will pop up a webpage that will confirm you want to grant access to the application.  It will give you a code, which you then paste back into the window running the setup wizard.  The bearer token that it generates is then saved in `oauth2.json` for all subsequent access.

Follow the rest of the prompts in the setup wizard.  Upon completion it will write out a config file -- `my.cfg` in the example above.

Execution
---------

Once installed and the config file created, you can run the program via this command:

::

  ybot <cfg_file>

The script will choose a lineup based on available spots in the lineup.  You can have it do a dry run with the --dry-run option so that it doesn't make any roster moves with Yahoo.  These is also a prompt option that will confirm with you each time it is about to make a roster move with Yahoo.  To get a full help text use the `--help` option.

Example
-------

Here is a sample run through.  In this run it will optimize the lineup, print out the lineup then list the roster changes.  It will manage two players on the IR and replace one player in the lineup from the free agent pool.

::

  $> ybot hockey.cfg
  Evaluating trades
  Adjusting lineup for player status
  Optimizing open lineup spots using available free agents
  100%|################################################################################################################|
  Optimizing lineup using players available from bench
  100%|################################################################################################################|
  Optimized lineup
  B   :                        WK_G G/A/PPP/SOG/PIM
  C   : Aleksander Barkov         3 38.0/63.0/32.0/241.0/10.0
  C   : Brayden Point             3 38.0/55.0/38.0/223.0/26.0
  LW  : Andrei Svechnikov         3 30.0/25.0/12.0/261.0/72.0
  LW  : Evander Kane              4 31.0/26.0/12.0/279.0/132.0
  RW  : David Pastrnak            3 44.0/53.0/39.0/281.0/40.0
  RW  : Alexander Radulov         3 28.0/45.0/24.0/212.0/64.0
  D   : Tyson Barrie              3 13.0/44.0/24.0/191.0/30.0
  D   : Thomas Chabot             3 15.0/43.0/15.0/197.0/36.0
  D   : P.K. Subban               4 12.0/40.0/16.0/174.0/70.0
  D   : Aaron Ekblad              3 14.0/25.0/11.0/186.0/55.0
  
  G   :                        WK_G W/SV%
  G   : Ben Bishop                3 31.0/0.922
  G   : Connor Hellebuyck         3 36.0/0.916
  
  Bench
  Jeff Skinner
  Patrice Bergeron
  
  Injury Reserve
  Sidney Crosby
  Mitchell Marner
  
  Computing roster moves to apply
  Move Sidney Crosby to IR
  Move Mitchell Marner to IR
  Add Brayden Point and drop Anthony Mantha
  Move David Pastrnak to RW
  Move Aleksander Barkov to C
  Move Ben Bishop to G
  Move Connor Hellebuyck to G
  Move Brayden Point to C
  Move Andrei Svechnikov to LW
  Move Evander Kane to LW
  Move Alexander Radulov to RW
  Move Tyson Barrie to D
  Move Thomas Chabot to D
  Move P.K. Subban to D
  Move Aaron Ekblad to D
  Move Jeff Skinner to BN
  Move Patrice Bergeron to BN
