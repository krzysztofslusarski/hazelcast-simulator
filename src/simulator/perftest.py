import datetime

import tempfile
import uuid
from datetime import datetime
import os
import yaml
import csv

from load_hosts import load_hosts
from simulator.hosts import public_ip, ssh_user, ssh_options
from simulator.ssh import SSH
from simulator.util import read, write, shell, run_parallel, bin_dir, exit_with_error, simulator_home, shell_logged
from simulator.log import info, warn, log_header


class PerfTest:

    def __init__(self, logfile=None, log_shell_command=False):
        self.logfile = logfile
        self.log_shell_command = True #log_shell_command
        pass


    def __kill_java(self, host):
        ssh = SSH(public_ip(host), ssh_user(host), ssh_options(host))
        ssh.scp_to_remote(f"{bin_dir}/hidden/kill_java", ".")
        ssh.exec("./kill_java")


    def terminate(self, host_pattern):
        log_header(f"perftest terminate: started")
        hosts = load_hosts(host_pattern)
        run_parallel(self.__kill_java, [(host,) for host in hosts])
        log_header(f"perftest terminate: started")

    def exec(self,
             test,
             run_path=None,
             performance_monitor_interval_seconds=None,
             worker_vm_startup_delay_ms=None,
             dedicated_member_machines=None,
             parallel=None,
             license_key=None,
             skip_download=None,
             node_group=None,
             duration=None,
             loadgenerator_group=None,
             client_args=None,
             member_args=None,
             members=None,
             clients=None,
             driver=None,
             version=None,
             fail_fast=None,
             verify_enabled=None,
             client_type=None):

        self.clean()

        args = ""

        if worker_vm_startup_delay_ms:
            args = f"{args} --workerVmStartupDelayMs {worker_vm_startup_delay_ms}"

        if dedicated_member_machines:
            args = f"{args} --dedicatedMemberMachines {dedicated_member_machines}"

        if parallel:
            args = f"{args} --parallel {parallel}"

        if license_key:
            args = f"{args} --licenseKey {license_key}"

        if skip_download:
            args = f"{args} --skipDownload {skip_download}"

        if run_path:
            args = f"{args} --runPath {run_path}"

        if duration:
            args = f"{args} --duration {duration}"

        if performance_monitor_interval_seconds:
            args = f"{args} --performanceMonitorInterval {performance_monitor_interval_seconds}"

        if node_group:
            args = f"{args} --nodeGroup {node_group}"

        if loadgenerator_group:
            args = f"{args} --loadGeneratorGroup {loadgenerator_group}"

        if members:
            args = f"{args} --members {members}"

        if member_args:
            args = f"""{args} --memberArgs "{member_args}" """

        if clients:
            args = f"{args} --clients {clients}"

        if client_args:
            args = f"""{args} --clientArgs "{client_args}" """

        if client_type:
            args = f"{args} --clientType {client_type}"

        if driver:
            args = f"{args} --driver {driver}"

        if version:
            args = f"{args} --version {version}"

        if fail_fast:
            args = f"{args} --failFast {fail_fast}"

        if verify_enabled:
            args = f"{args} --verifyEnabled {verify_enabled}"

        with tempfile.NamedTemporaryFile(mode="w", delete=False, prefix="perftest_", suffix=".txt") as tmp:
            for key, value in test.items():
                tmp.write(f"{key}={value}\n")
            tmp.flush()

            exitcode = self.__shell(f"{simulator_home}/bin/hidden/coordinator {args} {tmp.name}")
            if exitcode != 0:
                exit_with_error(f"Failed run coordinator, exitcode={exitcode}")
        return run_path

    def run(self, tests, tags):
        for test in tests:
            repetitions = test.get('repetitions')
            if not repetitions:
                repetitions = 1

            for i in range(0, repetitions):
                run_path = self.run_test(test)
                self.collect(run_path, tags)
        return

    def run_test(self, test, run_path=None):
        if not run_path:
            dt = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
            name = test['name']
            run_path = f"runs/{name}/{dt}"

        self.exec(
            test['test'],
            run_path=run_path,
            duration=test.get('duration'),
            performance_monitor_interval_seconds=test.get('performance_monitor_interval_seconds'),
            node_group=test.get('node_group'),
            loadgenerator_group=test.get('loadgenerator_group'),
            client_args=test.get('client_args'),
            member_args=test.get('member_args'),
            members=test['members'],
            clients=test.get('clients'),
            driver=test.get('driver'),
            version=test.get('version'),
            fail_fast=test.get('fail_fast'),
            verify_enabled=test.get('verify_enabled'),
            client_type=test.get('client_type'))

        return run_path

    def clean(self):
        exitcode = self.__shell(f"{simulator_home}/bin/hidden/coordinator --clean")
        if exitcode != 0:
            exit_with_error(f"Failed to clean, exitcode={exitcode}")

    def __shell(self, cmd):
        if self.log_shell_command:
            info(cmd)

        if self.logfile:
            return shell_logged(cmd, self.logfile, exit_on_error=False)
        else:
            return shell(cmd, use_print=True)

    def collect(self, dir, tags):
        report_dir = f"{dir}/report"

        if not os.path.exists(report_dir):
            self.__shell(f"perftest report  -o {report_dir} {dir}")

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
                    'operations': row[12],
                    'duration(ms)': row[13],
                    'throughput': row[14]}
                results[row[1]] = {'tags': tags, 'measurements': measurements}

        with open(f"{dir}/results.yaml", 'w') as results_yml:
            yaml.dump(results, results_yml)
