#!/usr/bin/env python
import argparse
import os
import sys

import yaml

from pony.bot import Pony


def parse_args():
    parser = argparse.ArgumentParser(
        description='Pony Standup Bot.'
    )
    parser.add_argument(
        '-c', '--config',
        type=str,
        help='Config file',
        required=True
    )
    return parser.parse_args()


def main():
    args = parse_args()

    config_file = args.config
    if not config_file.startswith('/'):
        config_file = os.path.join(os.getcwd(), config_file)

    with open(config_file) as config_file:
        config = yaml.load(config_file)

    bot = Pony(config)
    try:
        bot.start()
    except KeyboardInterrupt:
        bot.stop_gracefully()
        sys.exit(0)


if __name__ == "__main__":
    main()
