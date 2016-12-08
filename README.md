# Pony Standup Bot
Tiny Standup Bot for Slack

### Features
* multiple standups per team
* private daily status collection
* public standup report summary on schedule
* love and harmony

### Usage
* [create a bot](https://my.slack.com/services/new/bot) for your team
* copy `pony.sample.conf` to `pony.conf`
* put a token for newly created bot under `SLACK_TOKEN`
* configure your timezone and set up standup members under `StandupPonyPlugin`
* create a virtual environment with `virtualenv .env`
* install requirements `pip install -r requirements.txt`
* run `rtmbot --config pony.conf`
