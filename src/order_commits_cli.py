#!/usr/bin/python3

import subprocess
import tempfile
import argparse

from simulator.util import validate_git_repo


def load_commits(repo):
    cmd = f"""
         set -e

         cd {repo}
         git log --pretty=format:"%H"
         """

    return subprocess.check_output(cmd, shell=True, text=True).splitlines()


# https://stackoverflow.com/questions/22714371/how-can-i-sort-a-set-of-git-commit-ids-in-topological-order
def order(commits, repo):
    with tempfile.NamedTemporaryFile(mode="w", delete=False, prefix="commit_", suffix=".txt") as tmp:
        tmp.write("\n".join(commits))
        tmp.write("\n")
        tmp.flush()

        cmd = f"""
            cd {repo}
            git rev-list --date-order  $(cat {tmp.name}) | grep --file {tmp.name} --max-count $(wc -l < {tmp.name})
            """
        out = subprocess.check_output(cmd, shell=True, text=True)
        result = out.splitlines()
        result.reverse()
        return result


class OrderCommitsCli:

    def __init__(self):
        parser = argparse.ArgumentParser(
            description='Returns an ordered list (from old to new) of commits')
        parser.add_argument("commits", nargs="+", help="The commits to order")
        parser.add_argument("-r", "--repo", help="The directory containing the git repo", nargs=1,
                            default=['hazelcast'])
        parser.add_argument("-d", "--debug", help="Print the commits including timestamp", action='store_true')
        args = parser.parse_args()
        repo = validate_git_repo(args.repo[0])
        commits = args.commits
        ordered = order(commits, repo)

        if args.debug:
            for commit in ordered:
                cmd = f"""
                      cd {repo}
                      git show -s --format='%H | %ad | %ci' {commit}
                  """
                subprocess.run(cmd, shell=True, text=True)
        else:
            for commit in ordered:
                print(commit)


if __name__ == '__main__':
    OrderCommitsCli()
