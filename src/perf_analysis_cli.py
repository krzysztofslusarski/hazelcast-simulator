#!/usr/bin/python3
import argparse
import os
import statistics
from enum import Enum
import numpy as np
import matplotlib.pyplot as plt
from signal_processing_algorithms.energy_statistics.energy_statistics import e_divisive

import commit_sorter
from simulator.util import load_yaml_file, validate_dir, mkdir


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
        self.fake_x = np.arange(0, len(y))

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


def plot(ts, filename, cps=None, aps=None, ymin=0, width=1600, height=900):
    if cps and aps:
        plt.title(f"Changepoints and anomalies: {ts.name}")
    elif cps:
        plt.title(f"Changepoints: {ts.name}")
    elif aps:
        plt.title(f"Anomalies: {ts.name}")
    else:
        plt.title(f"{ts.name}")

    my_dpi = 96
    plt.figure(figsize=(width / my_dpi, height / my_dpi), dpi=my_dpi)
    plt.xticks(rotation=90)
    plt.grid()
    plt.xlabel(ts.x_label)
    plt.ylabel(ts.y_label)
    plt.plot(ts.fake_x, ts.y, color="orange")

    if cps:
        for p in cps:
            x = ts.fake_x[p.index]
            y = ts.y[p.index]
            commit = ts.x[p.index]
            plt.plot(x, y, 'o', color="green", label=f"cp: {commit}")

    if aps:
        for p in aps:
            x = ts.fake_x[p.index]
            y = ts.y[p.index]
            commit = ts.x[p.index]
            if p.direction == Change.POSITIVE:
                plt.plot(x, y, 'o', color="green", label=f"pa: {commit}")
            else:
                plt.plot(x, y, 'o', color="red", label=f"na: {commit}")

    plt.legend()
    plt.ylim(ymin=ymin)
    plt.subplots_adjust(bottom=0.4)
    plt.savefig(filename)


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


def ordered_commits(dir, git_dir):
    commits = []
    for file in os.listdir(dir):
        if os.path.isdir(f"{dir}/{file}"):
            filename = os.fsdecode(file)
            commits.append(filename)

    if not commits:
        return []

    print(git_dir)
    return commit_sorter.order(commits, git_dir)


def load_timeseries(dir, git_dir):
    y_map = {}
    x_map = {}
    for commit in ordered_commits(dir, git_dir):
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


class PerfRegressionAnalysisCli:

    def __init__(self, argv):
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                                         description='Does performance analysis')
        parser.add_argument("dir", help="The directory containing the results (per commit hash)", nargs=1)
        parser.add_argument("-g", "--git-dir", metavar='git_dir', help="The directory containing the git repo", nargs=1,
                            default=[f"{os.getcwd()}/.git"])
        parser.add_argument("-d", "--debug", help="Print debug info", action='store_true')
        parser.add_argument("-z", "--zero", help="Plot from zero", action='store_true')
        parser.add_argument("-l", "--latest", nargs=1, help="Take the n latest items", type=int)
        parser.add_argument("--width", nargs=1, help="The width of the images", type=int, default=1600)
        parser.add_argument("--height", nargs=1, help="The height of the images", type=int, default=900)
        parser.add_argument("-o", "--output", help="The directory to write the output", nargs=1, default=os.getcwd())

        args = parser.parse_args(argv)
        git_dir = validate_dir(args.git_dir[0])
        latest = args.latest[0]
        width = args.width
        height = args.height
        dir = validate_dir(args.dir[0])
        output = mkdir(args.output[0])

        # We need to determine if the time series has 'positive' or 'negative'

        result = load_timeseries(dir, git_dir)
        for metric, ts in result.items():
            if latest:
                print(f"Taking the last {latest} items of timeseries with {len(ts)} items")
                ts = ts.newest(latest)

            print(f"length timeseries {len(ts)}")
            cps = changepoint_detection(ts)
            aps = anomaly_detection(ts, n=4)

            ymin = 0 if args.zero else None

            filename = f"{output}/{metric}.png"
            print(filename)
            plot(ts, filename, cps=cps, aps=aps, ymin=ymin, width=width, height=height)
