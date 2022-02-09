#!/usr/bin/python3
import argparse

from simulator.ssh import new_key


class NewKeyCli:

    def __init__(self):
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                                         description='Creates a new public/private keypair')
        parser.add_argument("name", help="The name of the key", nargs=1)
        args = parser.parse_args()

        new_key(args.name[0])


if __name__ == '__main__':
    NewKeyCli()
