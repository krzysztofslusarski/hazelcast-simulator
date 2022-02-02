import tempfile
import uuid
from datetime import datetime
import os
import yaml
import csv
from hosts import public_ip, ssh_user, ssh_options
from ssh import SSH
from util import read, write, shell, run_parallel, bin_dir, exit_with_error
from log import info, warn, log_header


def __collect(inventory, desired_groupname=None):
    if not desired_groupname:
        return inventory

    filtered = []
    for host in inventory:
        if host['groupname'] == desired_groupname:
            filtered.append(host)

    return filtered


def __terminate(group_class, inventory, workload):
    hosts = __collect(inventory, workload[group_class]['group'])
    if not hosts:
        return
    run_parallel(__kill_java, [(host,) for host in hosts])


def __kill_java(host):
    ssh = SSH(public_ip(host), ssh_user(host), ssh_options(host))
    ssh.scp_to_remote(f"{bin_dir}/hidden/kill_java", ".")
    ssh.exec("./kill_java")


def simulator_perftest_terminate(inventory, workload):
    log_header(f"Workload Terminate: started")
    __terminate("nodes", inventory, workload)
    __terminate("loadgenerators", inventory, workload)
    log_header(f"Workload Terminate: started")


def simulator_perftest_run(testplan, tags):
    tests = testplan['tests']
    for test in tests:
        repetitions = test['repetitions']
        for i in range(0, repetitions):
            session_id = __run_test(test)
            simulator_perftest_collect(f"runs/{session_id}", tags)
    return


def __run_test(test):
    exitcode = shell("coordinator --clean", use_print=True)
    if exitcode != 0:
        exit_with_error(f"Failed to clean, exitcode={exitcode}")

    args = ""
    dt = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    name = test['name']
    session_id = f"{name}/{dt}"
    args = f"{args} --sessionId={session_id}"

    args = f"{args} --duration {test['duration_seconds']}s"

    performance_monitor_interval_seconds = test.get('performance_monitor_interval_seconds')
    if performance_monitor_interval_seconds:
        args = f"{args} --performanceMonitorInterval {performance_monitor_interval_seconds}"

    node_group = test.get('node_group')
    if node_group:
        args = f"{args} --nodeGroup {node_group}"

    loadgenerator_group = test.get('loadgenerator_group')
    if loadgenerator_group:
        args = f"{args} --loadGeneratorGroup {loadgenerator_group}"

    client_args = test.get('client_args')
    if client_args:
        args = f"{args} --clientArgs {client_args}"

    member_args = test.get('member_args')
    if member_args:
        args = f"{args} --memberArgs {member_args}"

    members = test['members']
    if members:
        args = f"{args} --members {members}"

    clients = test.get('clients')
    if clients:
        args = f"{args} --clients {clients}"

    driver = test.get('driver')
    if driver:
        args = f"{args} --driver {driver}"

    version = test.get('version')
    if version:
        args = f"{args} --version {version}"

    fail_fast = test.get('fail_fast')
    if fail_fast:
        args = f"{args} --failFast {fail_fast}"

    verify_enabled = test.get('verify_enabled')
    if verify_enabled:
        args = f"{args} --verifyEnabled {verify_enabled}"

    client_type = test.get('client_type')
    if client_type:
        args = f"{args} --clientType {client_type}"

    test = test['test']
    with tempfile.NamedTemporaryFile(mode="w", delete=False, prefix="perftest_", suffix=".txt") as tmp:
        for key, value in test.items():
            tmp.write(f"{key}={value}\n")
        tmp.flush()

        cmd = f"coordinator {args} {tmp.name}"
        info(cmd)
        exitcode = shell(cmd, use_print=True)
        if exitcode != 0:
            exit_with_error(f"Failed run coordinator, exitcode={exitcode}")
    return session_id


def simulator_perftest_collect(dir, tags):
    report_dir = f"{dir}/report"

    info(f"dir={dir}")

    if not os.path.exists(report_dir):
        shell(f"perftest report  -o {report_dir} {dir}")

    csv_path = f"{report_dir}/report.csv"
    if not os.path.exists(csv_path):
        warn(f"Could not find [{csv_path}]")
        return

    run_id_path = f"{dir}/run.id"
    if not os.path.exists(run_id_path):
        write(run_id_path, uuid.uuid4().hex)

    tags['run_id'] = read(run_id_path)

    results = {}
    with open(csv_path, newline='') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',', quotechar='|')
        # skip header
        next(csv_reader)
        for row in csv_reader:
            measurements = {
                '10%(us)': row[2],
                '20%(us)': row[3],
                '50%(us)': row[4],
                '75%(us)': row[5],
                '90%(us)': row[6],
                '95%(us)': row[7],
                '99%(us)': row[8],
                '99.9%(us)': row[9],
                '99.99%(us)': row[10],
                'max(us)': row[11],
                'operations': row[11],
                'duration(ms)': row[11],
                'throughput': row[14]}
            results[row[1]] = {'tags': tags, 'measurements': measurements}

    with open(f"{dir}/results.yaml", 'w') as results_yml:
        yaml.dump(results, results_yml)
