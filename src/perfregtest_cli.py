#!/usr/bin/python3
import argparse
import os
import subprocess
import sys
import random
from datetime import datetime
from pathlib import Path

import commit_sampler
import simulator.util
from commit_sampler import CommitSamplerCli
from commit_sorter import CommitOrderCli
from perf_analysis_cli import PerfRegressionAnalysisCli, PerfRegressionSummaryCli
from simulator.log import info, log_header
from simulator.perftest import PerfTest
from simulator.util import shell_logged, now_seconds, validate_dir, load_yaml_file, exit_with_error

default_tests_path = 'tests.yaml'
logfile_name = "run.log"

usage = '''perfregtest <command> [<args>]

The available commands are:
    analyze             Analyzes the results of performance regression tests..
    commit_sampler      Creates a sample of commits between a start and end commit.
    commit_order        Returns an ordered list (from old to new) of commits.
    run                 Runs performance regression tests.
    summary             Shows a summary of a set of performance regression tests
'''


def get_project_version(project_path):
    cmd = f"""
         set -e
         cd {project_path}
         mvn -q -Dexec.executable=echo -Dexec.args='${{project.version}}' --non-recursive exec:exec
         """
    return subprocess.check_output(cmd, shell=True, text=True).strip()


def build(commit, project_path):
    broken_builds_dir = simulator.util.mkdir("broken-builds")
    build_error_file = f"{broken_builds_dir}/{commit}"
    if os.path.exists(build_error_file):
        return False

    exitcode = shell_logged(f"""
        set -e
        cd {project_path}
        git fetch --all --tags
        git reset --hard
        git checkout {commit}
        mvn clean install -DskipTests -Dquick
    """, log_file=logfile_name)

    if exitcode == 0:
        return True
    else:
        open(build_error_file, "w").close()
        return False


def run(test, commit, runs, project_path, debug=False):
    version = get_project_version(project_path)
    test_name = test['name']
    test['version'] = f"maven={version}"
    commit_dir = f"runs/{test_name}/{commit}"
    info(f"Running {commit_dir}, runs {runs} ")
    info(f"Version:[{version}]")
    info(f"Test Duration: {test.get('duration')}")
    warmup = test.get("warmup")
    if not warmup:
        warmup = 0
    cooldown = test.get("cooldown")
    if not cooldown:
        cooldown = 0

    for i in range(0, runs):
        dt = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
        run_path = f"{commit_dir}/{dt}"
        info(f"{i + 1} {run_path}")

        perftest = PerfTest(logfile=logfile_name, log_shell_command=debug)
        perftest.run_test(test, run_path=run_path, )
        perftest.collect(f"{run_path}", {'commit': commit, "testname": test_name}, warmup=warmup, cooldown=cooldown)


def run_all(commits, runs, project_path, tests, debug):
    if not tests:
        exit_with_error("No tests found.")

    if not commits:
        exit_with_error("No commits found.")

    info(f"Source dir {project_path}")
    info(f"Number of commits {len(commits)}")
    info(f"Tests to execute: {[t['name'] for t in tests]}")

    start = now_seconds()
    builds_failed = 0
    for commitIndex, commit in enumerate(commits):
        commit_was_build = False
        c = commit_sampler.to_commit(f"{project_path}/.git", commit)
        if not c.startswith(commit):
            info(f"{commit}->{c}")
            commit = c

        for test in tests:
            test_name = test['name']
            commit_dir = f"runs/{test_name}/{commit}"
            result_count = sum(r is r for r in Path(commit_dir).rglob('results.yaml'))
            remaining = runs - result_count

            if remaining <= 0:
                info(f"Skipping commit {commit}, test {test_name}, sufficient runs")
                continue

            log_header(f"Commit {commit}")
            start_test = now_seconds()
            info(f"Commit {commitIndex + 1}/{len(commits)}")
            info(f"Building {commit}")

            if not commit_was_build:
                if build(commit, project_path):
                    commit_was_build = True
                else:
                    builds_failed += 1
                    info(f"Build failed, {builds_failed}/{len(commits)}, skipping runs.")
                    break

            run(test, commit, remaining, project_path, debug)
            info(f"Testing {test_name} took {now_seconds() - start_test}s")
    duration = now_seconds() - start
    info(f"Duration: {duration}s")
    info(f"Builds failed: {builds_failed}")
    info(f"Builds failed: {100 * builds_failed / len(commits)}%")
    info(f"Builds succeeded: {len(commits) - builds_failed}")


class PerfRegTestRunCli:

    def __init__(self, argv):
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                                         description='Runs performance regression tests based on a series of commits')
        parser.add_argument("path", nargs=1, help="The path of the project to build")
        parser.add_argument("commits", nargs="+", help="The commits to build")
        parser.add_argument('-f', '--file', nargs=1, help='The tests file', default=[default_tests_path])
        parser.add_argument("-r", "--runs", nargs=1, help="The number of runs per commit",
                            default=[3], type=int)
        parser.add_argument('-t', '--test', nargs=1,
                            help='The names of the tests to run. By default all tests are run.')
        parser.add_argument("-r", "--randomize", help="Randomizes the commits", action='store_true')
        parser.add_argument("-d", "--debug", help="Print debug info", action='store_true')

        args = parser.parse_args(argv)
        commits = args.commits
        if args.randomize:
            random.shuffle(commits)
        runs = args.runs[0]
        project_path = validate_dir(args.path[0])
        tests = load_yaml_file(args.file[0])
        filtered_tests = []
        if args.test:
            for test in tests:
                test_name = test['name']
                if test_name in args.test:
                    filtered_tests.append(test)
        else:
            filtered_tests = tests

        run_all(commits, runs, project_path, filtered_tests, args.debug)


class PerfRegtestCli:

    def __init__(self):
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                                         description='Contains tools for performance regression testing.', usage=usage)
        parser.add_argument('command', help='Subcommand to run')

        args = parser.parse_args(sys.argv[1:2])
        if not hasattr(self, args.command):
            print('Unrecognized command', parser.print_help())
            exit(1)

        getattr(self, args.command)(sys.argv[2:])

    def run(self, argv):
        PerfRegTestRunCli(argv)

    def commit_sampler(self, argv):
        CommitSamplerCli(argv)

    def commit_sorter(self, argv):
        CommitOrderCli(argv)

    def analyze(self, argv):
        PerfRegressionAnalysisCli(argv)

    def summary(self, argv):
        PerfRegressionSummaryCli(argv)


if __name__ == '__main__':
    os.path.expanduser('~/your_directory')
    PerfRegtestCli()
