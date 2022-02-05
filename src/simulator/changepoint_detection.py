#!/usr/bin/python3
import os
import statistics
import subprocess
from enum import Enum

import yaml
import numpy as np
import matplotlib.pyplot as plt
from statistics import mean
from signal_processing_algorithms.energy_statistics.energy_statistics import e_divisive

from simulator.util import load_yaml_file


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


def plot(ts, cps=None, aps=None):
    if cps and aps:
        plt.title(f"Changepoints and anomalies: {ts.name}")
    elif cps:
        plt.title(f"Changepoints: {ts.name}")
    elif aps:
        plt.title(f"Anomalies: {ts.name}")
    else:
        plt.title(f"{ts.name}")

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
    plt.show()


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


def load_timeseries(dir, repo):
    cmd = f"order_commits --repo {repo} {dir}"
    ordered_commits = subprocess.check_output(cmd, shell=True, text=True).splitlines()

    y_list = []
    x_list = []

    for commit in ordered_commits:
        commit_dir = f"{dir}/{commit}"
        min_throughput = None

        for run in os.listdir(commit_dir):
            yaml_file = f"{commit_dir}/{run}/results.yaml"
            if os.path.exists(yaml_file):
                perf_data = load_yaml_file(yaml_file)
                for test, map in perf_data.items():
                    measurements = map['measurements']
                    commit = map['tags']['commit']
                    print(commit)
                    throughput = float(measurements['throughput'])
                    if not min_throughput:
                        min_throughput = throughput
                    else:
                        min_throughput = min(min_throughput, throughput)

        if min_throughput:
            y_list.append(min_throughput)

    y_list.reverse()

    y = np.array(y_list, dtype=float)
    x = np.arange(0, len(y))
    return TimeSeries(x, y, x_label="Date", y_label="Throughput", name="Throughput")


def changepoint_detection(ts):
    indices = e_divisive(ts.y, permutations=1000)
    result = []
    for i in indices:
        result.append(ChangePoint(i, None))
    return result


# We need to determine if the time series has 'positive' or 'negative'

dir = "/home/eng/Hazelcast/perf-regression/2c1m/runs/readonly"
repo = "/home/eng/Hazelcast/perf-regression/2c1m/hazelcast"
ts = load_timeseries(dir, repo)  # .newest(50)
print(f"length timeseries {len(ts)}")
cps = changepoint_detection(ts)
aps = anomaly_detection(ts, n=4)
plot(ts, cps=cps, aps=aps)