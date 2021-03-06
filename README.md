# Pony Standup Bot
[![Build Status](https://travis-ci.org/alexanderad/pony-standup-bot.svg?branch=master)](https://travis-ci.org/alexanderad/pony-standup-bot)

Tiny Standup Bot for Slack

### Features
* multiple standups per team
* multiple standups attendees
* private daily status collection
* public standup report summary on schedule
* understands holidays and weekends
* friendly reminders

### Usage
* [create a bot](https://my.slack.com/services/new/bot) for your team
* copy `pony.sample.yaml` to `pony.yaml`
* put a token for newly created bot under `SLACK_TOKEN`
* configure your timezone and set up standup members under `StandupPonyPlugin`
* create a virtual environment with `virtualenv .env`
* install requirements `pip install -r requirements.txt`
* run `rtmbot --config pony.yaml`

### Testing
Testing is easy, assuming you have [tox](https://pypi.python.org/pypi/tox) installed:

    $ tox
