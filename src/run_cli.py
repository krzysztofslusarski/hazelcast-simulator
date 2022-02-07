#!/usr/bin/python3

import subprocess
from datetime import datetime
import argparse
from pathlib import Path

import simulator.log
from simulator.log import info
from simulator.perftest import PerfTest
from simulator.util import validate_git_repo, load_yaml_file, exit_with_error, shell_logged, now_seconds

default_tests_path = 'tests.yaml'
logfile_name="run.log"


def get_project_version(dir):
    cmd = f"""
         set -e
         cd {dir}
         mvn -q -Dexec.executable=echo -Dexec.args='${{project.version}}' --non-recursive exec:exec
         """
    return subprocess.check_output(cmd, shell=True, text=True).strip()


def run(test, commit, runs, repo):
    version = get_project_version(repo)
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


def build(commit, repo):
    exitcode = shell_logged(f"""
        set -e
        cd {repo}
        git pull origin master
        git checkout {commit}
        mvn clean install -DskipTests -Dquick
    """, log_file=logfile_name)
    return exitcode == 0


class RunCli:

    def __init__(self):
        parser = argparse.ArgumentParser(description='Runs benchmarks')
        parser.add_argument('--tests', nargs='?', help='The tests file', default=default_tests_path)

        parser.add_argument("commits", nargs="+", help="The commits to build")
        parser.add_argument("-c", "--count", nargs=1, help="The number of runs per commit", default=3)
        parser.add_argument("-r", "--repo", help="The directory containing the git repo", nargs=1,
                            default=['hazelcast'])

        args = parser.parse_args()
        commits = args.commits
        count = args.count
        repo = validate_git_repo(args.repo[0])
        tests = load_yaml_file(args.tests)

        info(f"Number of commits {len(commits)}")

        start = now_seconds()
        for commitIndex, commit in enumerate(commits):
            commit_was_build = False

            for test in tests:
                test_name = test['name']
                result_count = 0
                for p in Path(f"runs/{test_name}/{commit}").rglob('results.yaml'):
                    result_count += 1
                remaining = count - result_count

                if remaining <= 0:
                    info(f"Skipping commit {commit}, test {test_name}, sufficient runs")
                    continue

                simulator.log.log_header(f"Commit {commit}")
                start_test = now_seconds()
                info(f"Commit {commitIndex + 1}/{len(commits)}")
                info(f"Building {commit}")
                if not commit_was_build:
                    if build(commit, repo):
                        commit_was_build = True
                    else:
                        info("Build failed, skipping runs.")
                        continue

                run(test, commit, remaining, repo)
                info(f"Testing {test_name} took {now_seconds() - start_test}s")

        duration = now_seconds() - start
        info(f"Duration: {duration}s")


if __name__ == '__main__':
    RunCli()
