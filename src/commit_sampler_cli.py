#!/usr/bin/python3

import subprocess
import os
import argparse
import random


class CommitSamplerCli:

    def __init__(self):
        parser = argparse.ArgumentParser(description='Returns a sample of commits between 2 commits')
        parser.add_argument("first", help="The first commit", nargs=1)
        parser.add_argument("last", help="The last commit", nargs=1)
        parser.add_argument("count", help="The last commit", type=int, nargs=1, default=20)
        parser.add_argument("-r", "--repo", help="The directory containing the git repo", nargs=1,
                            default=['.'])
        parser.add_argument("-d", "--debug", help="Print the commits including timestamp", action='store_true')
        args = parser.parse_args()

        first = args.first[0]
        last = args.last[0]
        repo = args.repo[0]
        count = args.count[0]

        if not os.path.isdir(f"{repo}/"):
            print(f"Repo directory [{repo}] does not exist")
            exit(1)

        if not os.path.isdir(f"{repo}/.git"):
            print(f"Repo directory [{repo}] does not contain a git repository")
            exit(1)

        cmd = f"""
            set -e
            cd {repo}
            git rev-list --ancestry-path {first}..{last}
            """
        commits = subprocess.check_output(cmd, shell=True, text=True).splitlines()
        picked = random.sample(commits, count)
        print(" ".join(picked))


if __name__ == '__main__':
    CommitSamplerCli()
