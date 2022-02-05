#!/usr/bin/python3
import argparse
import os
import statistics
import subprocess
from enum import Enum
import numpy as np
import matplotlib.pyplot as plt
from signal_processing_algorithms.energy_statistics.energy_statistics import e_divisive

from simulator.util import load_yaml_file, validate_git_repo, validate_dir, exit_with_error


class TimeSeries:
    def __init__(self,
                 x,
                 y,
                 x_label=None,
                 y_label=None,
                 name=None,
                 increase_is_positive=True):
        assert len(x) == len(y)
        self.x = x
        self.y = y
        self.x_label = x_label
        self.y_label = y_label
        self.name = name
        self.increase_is_positive = increase_is_positive

    # Creates a new TimeSeries containing the newest n items.
    def newest(self, n):
        length = len(self.x)
        if length <= n:
            return self

        start = length - n
        x = self.x[start:]
        y = self.y[start:]
        return TimeSeries(x, y, x_label=self.x_label, y_label=self.y_label, name=self.name,
                          increase_is_positive=self.increase_is_positive)

    def __len__(self):
        return len(self.x)


def plot(ts, filename, cps=None, aps=None, ymin=0, ):
    if cps and aps:
        plt.title(f"Changepoints and anomalies: {ts.name}")
    elif cps:
        plt.title(f"Changepoints: {ts.name}")
    elif aps:
        plt.title(f"Anomalies: {ts.name}")
    else:
        plt.title(f"{ts.name}")

    my_dpi = 96
    plt.figure(figsize=(1600 / my_dpi, 900 / my_dpi), dpi=my_dpi)
    plt.xticks(rotation=90)
    plt.grid()
    plt.xlabel(ts.x_label)
    plt.ylabel(ts.y_label)
    plt.plot(ts.x, ts.y, color="orange")

    if cps:
        for p in cps:
            plt.plot(ts.x[p.index], ts.y[p.index], 'ro', color="blue")

    if aps:
        x, y = collect_anomalies(ts, aps, direction=Change.POSITIVE)
        plt.plot(x, y, 'ro', color='green', label='positive anomalies')

        x, y = collect_anomalies(ts, aps, direction=Change.NEGATIVE)
        plt.plot(x, y, 'ro', color='red', label='negative anomalies')

    plt.legend()

    if ymin == 0:
        plt.ylim(ymin=0)
    elif ymin:
        plt.ylim(ymin=ymin)
    plt.subplots_adjust(bottom=0.4)
    plt.savefig(filename)


def collect_anomalies(ts, aps, direction):
    x = []
    y = []
    if not aps:
        return x, y
    for p in aps:
        if direction == p.direction:
            x.append(ts.x[p.index])
            y.append(ts.y[p.index])
    return x, y


def collect_changepoints(ts, cps, direction):
    x = []
    y = []
    if not cps:
        return x, y
    for p in cps:
        if direction == p.direction:
            x.append(ts.x[p.index])
            y.append(ts.y[p.index])
    return x, y


class Change(Enum):
    POSITIVE = 1
    NEGATIVE = 2


# https://netflixtechblog.com/fixing-performance-regressions-before-they-happen-eab2602b86fe
# m is the number of samples
# n is the number of standard deviation away from the mean
def anomaly_detection(ts, m=40, n=4):
    history = []
    anomalies = []
    for i in range(1, len(ts.x)):
        history.append(ts.y[i - 1])

        if len(history) > m:
            del history[0]

        if len(history) == 1:
            continue
        mean = statistics.mean(history)
        std = statistics.pstdev(history)
        diff = ts.y[i] - mean
        if abs(diff) > n * std:
            direction = Change.POSITIVE if diff > 0 else Change.NEGATIVE
            anomalies.append(AnomalyPoint(i, direction))

    return anomalies


class AnomalyPoint:

    def __init__(self, index, direction):
        self.index = index
        self.direction = direction


class ChangePoint:

    def __init__(self, index, direction):
        self.index = index
        self.direction = direction


def load_commit_dir(dir, commit):
    commit_dir = f"{dir}/{commit}"
    result = {}
    for run in os.listdir(commit_dir):
        results_file = f"{commit_dir}/{run}/results.yaml"
        if not os.path.exists(results_file):
            continue

        results_yaml = load_yaml_file(results_file)
        for test, map in results_yaml.items():
            measurements = map['measurements']
            for name, value in measurements.items():
                values = result.get(value)
                if not values:
                    values = []
                    result[name] = values
                values.append((commit, value))
    return result


def pick_best_value(values):
    best = None
    for (commit, value) in values:
        if not best or value < best[1]:
            best = (commit, value)
    return best


def get_ordered_commits(dir, repo):
    commits = []
    for file in os.listdir(dir):
        if os.path.isdir(f"{dir}/{file}"):
            filename = os.fsdecode(file)
            commits.append(filename)

    if not commits:
        exit_with_error(f"No commits found in directory [dir]")

    cmd = f"order_commits --repo {repo} {' '.join(commits)}"
    ordered_commits = subprocess.check_output(cmd, shell=True, text=True).splitlines()
    return ordered_commits


def load_timeseries(dir, repo):
    y_map = {}
    x_map = {}
    for commit in get_ordered_commits(dir, repo):
        result = load_commit_dir(dir, commit)

        for metric_name, values in result.items():
            (commit, value) = pick_best_value(values)

            y = y_map.get(metric_name)
            x = x_map.get(metric_name)
            if not y:
                y = []
                y_map[metric_name] = y
                x = []
                x_map[metric_name] = x
            y.append(value)
            x.append(commit)

    result = {}
    for metric_name in y_map.keys():
        y = np.array(y_map[metric_name], dtype=float)
        x = np.array(x_map[metric_name])
        result[metric_name] = TimeSeries(x, y, x_label="Commit", y_label=metric_name, name=metric_name)
    return result


def changepoint_detection(ts):
    indices = e_divisive(ts.y, permutations=1000)
    result = []
    for i in indices:
        result.append(ChangePoint(i, None))
    return result


class PerfAnalysisCli:

    def __init__(self):
        parser = argparse.ArgumentParser(description='Does performance analysis')
        parser.add_argument("dir", help="The directory containing the commit hashes", nargs=1)
        parser.add_argument("-r", "--repo", help="The directory containing the git repo", nargs=1,
                            default=['hazelcast'])
        parser.add_argument("-d", "--debug", help="Print debug info", action='store_true')
        parser.add_argument("-z", "--zero", help="Plot from zero", action='store_true')
        parser.add_argument("-l", "--latest", nargs=1, help="Take the n latest items", type=int)

        args = parser.parse_args()
        repo = validate_git_repo(args.repo[0])
        latest = args.latest[0]
        dir = validate_dir(args.dir[0])
        # We need to determine if the time series has 'positive' or 'negative'

        result = load_timeseries(dir, repo)
        for metric, ts in result.items():
            if latest:
                print(f"Taking the last {latest} items of timeseries with {len(ts)} items")
                ts = ts.newest(latest)

            print(f"length timeseries {len(ts)}")
            cps = changepoint_detection(ts)
            aps = anomaly_detection(ts, n=4)

            ymin = 0 if args.zero else None

            filename = f"/home/pveentjer/tmp/{metric}.png"
            plot(ts, filename, cps=cps, aps=aps, ymin=ymin )


if __name__ == '__main__':
    PerfAnalysisCli()
