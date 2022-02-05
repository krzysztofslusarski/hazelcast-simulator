#!/usr/bin/python3

import subprocess
from datetime import datetime
import time
import os
import argparse
from pathlib import Path


def bash(cmd):
    log = 'run.log'
    with open(log, "a") as f:
        result = subprocess.run(cmd, shell=True, text=True, stdout=f, stderr=f)
        if result.returncode != 0:
            print(f"Failed to run [{cmd}], exitcode: {result.returncode}. Check {log} for details.")
            exit(1)


def now_seconds():
    return round(time.time())


def get_project_version(dir):
    cmd = f"""
         set -e
         cd {dir}
         mvn -q -Dexec.executable=echo -Dexec.args='${{project.version}}' --non-recursive exec:exec
         """
    return subprocess.check_output(cmd, shell=True, text=True).strip()


def run(testname, commit, runs, repo):
    version = get_project_version(repo)
    commit_dir = f"{testname}/{commit}"
    print("--------------------------------------------------------")
    print(f"Running {commit_dir}, runs; "+runs)
    print(f"Version:[{version}]")
    for i in range(0, runs):
        dt = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
        session_id = f"{commit_dir}/{dt}"
        print(f"{run+1} {session_id}")

        bash(f"""
            $SIMULATOR_HOME/bin/hidden/coordinator     \
                        --duration 300s \
                        --driver "hazelcast5" \
                        --clients 2 \
                        --clientType "javaclient" \
                        --clientArgs "-Xms3g -Xmx3g" \
                        --loadGeneratorGroup loadgenerators \
                        --members 1 \
                        --memberArgs "-Xms3G -Xmx3G" \
                        --version maven={version} \
                        --nodeGroup nodes \
                        --sessionId {session_id} \
                        --performanceMonitorInterval 1 \
                        {testname}.properties
            """)

        bash(f"""
            perftest collect -t commit={commit} -t testname={testname} runs/{session_id}
            """)


def build(commit, repo):
    print(f"Building {commit} [{repo}]")
    bash(f"""
        set -e
        cd {repo}
        git pull origin master
        git checkout {commit}         
        mvn clean install -DskipTests -Dquick
    """)


class RunCli:
    def __init__(self):
        parser = argparse.ArgumentParser(description='Runs benchmarks')
        parser.add_argument("commits", nargs="+", help="The commits to build")
        parser.add_argument("-c", "--count", nargs=1, help="The number of runs per commit", default=3)
        parser.add_argument("-r", "--repo", help="The directory containing the git repo", nargs=1,
                            default=['hazelcast'])

        args = parser.parse_args()
        commits = args.commits
        count = args.count

        repo = args.repo[0]
        if not os.path.isdir(repo):
            print(f"Repo directory [{repo}] does not exist")
            exit(1)

        start = now_seconds()
        for commit in commits:
            test = "readonly"
            result_count = 0
            for p in Path(f"runs/{test}/{commit}").rglob('results.yaml'):
                result_count += 1
            remaining = count - result_count

            if remaining <= 0:
                print(f"Skipping commit {commit}, test {test}, sufficient runs")
                continue

            build(commit, repo)
            run(test, commit, remaining, repo)

        duration = now_seconds() - start
        print(f"Duration: {duration} s")

    # run('writeonly', commit, 3)


if __name__ == '__main__':
    RunCli()
