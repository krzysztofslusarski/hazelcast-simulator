#!/usr/bin/python3
import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
import simulator.log
from commit_sampler import CommitSamplerCli
from commit_sorter import CommitOrderCli
from perf_analysis_cli import PerfRegressionAnalysisCli
from simulator.log import info
from simulator.perftest import PerfTest
from simulator.util import shell_logged, now_seconds, validate_dir, load_yaml_file

default_tests_path = 'tests.yaml'
logfile_name = "run.log"

usage = '''perfregtest <command> [<args>]

The available commands are:
    run                 Runs performance regression tests.
    analyze             Analyzes the results of performance regression tests..
    commit_sampler      Retrieves a sample of commits between a start and end commit.
    commit_order        Returns an ordered list (from old to new) of commits.
'''


def get_project_version(path):
    cmd = f"""
         set -e
         cd {path}
         mvn -q -Dexec.executable=echo -Dexec.args='${{project.version}}' --non-recursive exec:exec
         """
    return subprocess.check_output(cmd, shell=True, text=True).strip()


def build(commit, path):
    exitcode = shell_logged(f"""
        set -e
        cd {path}
        git fetch --all --tags
        git reset --hard
        git checkout {commit}
        mvn clean install -DskipTests -Dquick
    """, log_file=logfile_name)
    return exitcode == 0


def run(test, commit, runs, path):
    version = get_project_version(path)
    test_name = test['name']
    test['version'] = f"maven={version}"
    commit_dir = f"runs/{test_name}/{commit}"
    info(f"Running {commit_dir}, runs {runs} ")
    info(f"Version:[{version}]")
    info(f"Test Duration: {test.get('duration')}")
    for i in range(0, runs):
        dt = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
        run_path = f"{commit_dir}/{dt}"
        info(f"{i + 1} {run_path}")

        perftest = PerfTest(logfile=logfile_name)
        perftest.run_test(test, run_path=run_path, )
        perftest.collect(f"{run_path}", {'commit': commit, "testname": test_name})


def run_all(commits, runs, path, tests):
    info(f"Source dir {path}")
    info(f"Number of commits {len(commits)}")
    start = now_seconds()
    for commitIndex, commit in enumerate(commits):
        commit_was_build = False

        for test in tests:
            test_name = test['name']
            result_count = 0
            for p in Path(f"runs/{test_name}/{commit}").rglob('results.yaml'):
                result_count += 1
            remaining = runs - result_count

            if remaining <= 0:
                info(f"Skipping commit {commit}, test {test_name}, sufficient runs")
                continue

            simulator.log.log_header(f"Commit {commit}")
            start_test = now_seconds()
            info(f"Commit {commitIndex + 1}/{len(commits)}")
            info(f"Building {commit}")
            if not commit_was_build:
                if build(commit, path):
                    commit_was_build = True
                else:
                    info("Build failed, skipping runs.")
                    continue

            run(test, commit, remaining, path)
            info(f"Testing {test_name} took {now_seconds() - start_test}s")
    duration = now_seconds() - start
    info(f"Duration: {duration}s")


class PerfRegTestRunCli:

    def __init__(self, argv):
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                                         description='Runs performance regression tests based on a series of commits')
        parser.add_argument("path", nargs=1, help="The path of the project to build")
        parser.add_argument("commits", nargs="+", help="The commits to build")
        parser.add_argument('--tests', nargs=1, help='The tests file', default=[default_tests_path])
        parser.add_argument("-r", "--runs", nargs=1, help="The number of runs per commit",
                            default=[3], type=int)

        args = parser.parse_args(argv)
        commits = args.commits
        runs = args.runs[0]
        path = validate_dir(args.path[0])
        tests = load_yaml_file(args.tests[0])

        run_all(commits, runs, path, tests)


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


if __name__ == '__main__':
    os.path.expanduser('~/your_directory')
    PerfRegtestCli()
