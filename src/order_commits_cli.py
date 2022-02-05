#!/usr/bin/python3

import subprocess
import tempfile
import os
import argparse


def load_commit_directories(dir):
    commits = []
    for file in os.listdir(dir):
        if os.path.isdir(f"{dir}/{file}"):
            filename = os.fsdecode(file)
            commits.append(filename)
    return commits


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
        return out.splitlines()


class OrderCommitsCli:

    def __init__(self):
        parser = argparse.ArgumentParser(description='Returns an ordered list of commits for a results directory')
        parser.add_argument("dir", help="The directory containing the commit hashes", nargs=1)
        parser.add_argument("--repo", help="The directory containing the git repo", nargs=1, default=['hazelcast'])
        parser.add_argument("-d", "--debug", help="Print the commits including timestamp", action='store_true')
        args = parser.parse_args()
        dir = args.dir[0]
        repo = args.repo[0]
        if not os.path.isdir(dir):
            print(f"Directory [{dir}] does not exist")
            exit(1)


        if not os.path.isdir(repo):
            print(f"Repo directory [{repo}] does not exist")
            exit(1)

        commits = load_commit_directories(dir)
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
