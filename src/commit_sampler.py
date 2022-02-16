import argparse
import os
import random
import subprocess

from simulator.util import validate_git_dir


def to_commit(git_dir, commit):
    cmd = f"""git --git-dir {git_dir} rev-list -n 1 {commit} """
    return subprocess.check_output(cmd, shell=True, text=True).strip()


class CommitSamplerCli:

    def __init__(self, argv):
        parser = argparse.ArgumentParser(
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            description='Returns a randomly ordered subset of commits between the first/last commit (inclusive)')
        parser.add_argument("first", help="the first commit.", nargs=1)
        parser.add_argument("last", help="the last commit.", nargs=1)
        parser.add_argument("count", help="the maximum number of commits being sampled.", type=int, nargs=1, default=20)
        parser.add_argument("-l", "--length",
                            help="The hash length. 7 is sufficient for most projects. The maximum value is 40.",
                            type=int, nargs=1, default=[10])
        parser.add_argument("-g", "--git-dir", metavar='git_dir', help="The directory containing the git repo.",
                            nargs=1, default=[f"{os.getcwd()}/.git"])
        parser.add_argument("-d", "--debug", help="print the commits including timestamp", action='store_true')

        args = parser.parse_args(argv)

        debug = args.debug
        first = args.first[0]
        last = args.last[0]
        git_dir = validate_git_dir(args.git_dir[0])
        count = args.count[0]
        if count < 2:
            print("Count can't be smaller than 2.")
            exit(1)
        hash_length = args.length[0]
        if hash_length < 1:
            print("Hash length can't be smaller than zero")
        if hash_length > 40:
            print("Hash length can't be larger than 40")

        first_commit = to_commit(git_dir, first)
        if debug and first_commit != first:
            print(f"{first}->{first_commit}")

        last_commit = to_commit(git_dir, last)
        if debug and last_commit != last:
            print(f"{last}->{last_commit}")

        cmd = f"""git --git-dir {git_dir} rev-list --ancestry-path {first_commit}..{last_commit} """
        if debug:
            print(cmd)

        try:
            commits = subprocess.check_output(cmd, shell=True, text=True).splitlines()
        except subprocess.CalledProcessError as e:
            print(f"Failed to process command [{cmd}], exitcode: {e.returncode}")
            exit(1)

        if len(commits) < 2:
            samples = commits
        else:
            samples = random.sample(commits, min(count - 2, len(commits)))

            # and now we include the first/last so they are guaranteed to be included
            samples.append(first_commit)
            samples.append(last_commit)

        samples = [commit[0:hash_length] for commit in samples]
        print(" ".join(samples))

