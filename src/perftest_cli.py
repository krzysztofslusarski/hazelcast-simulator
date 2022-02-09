#!/usr/bin/python3
import os
import shutil
import sys
import argparse
import getpass
from os import path

from simulator.log import log_header, info
from simulator.perftest import PerfTest
from simulator.ssh import new_key
from simulator.util import load_yaml_file, exit_with_error, remove, simulator_home, write, read
from simulator.perftest_report import PerfTestReportCli

default_tests_path = 'tests.yaml'
inventory_path = 'inventory.yaml'
usage = '''perftest <command> [<args>]

The available commands are:
    create      Creates a new performance test based on a template.
    clone       Clones an existing performance test.
    collect     Collects the performance test data and stores it in result.yaml.
    exec        Executes a performance test.'
    run         Runs a tests.yaml which is a self contained set of tests'
    terminate   Terminate all running performance tests.   
    report      Generate performance report 
'''


# https://stackoverflow.com/questions/27146262/create-variable-key-value-pairs-with-argparse-python
def parse_tag(s):
    items = s.split('=')
    key = items[0].strip()  # we remove blanks around keys, as is logical
    value = None
    if len(items) > 1:
        # rejoin the rest:
        value = '='.join(items[1:])
    return (key, value)


def parse_tags(items):
    d = {}
    if items:
        flat_list = [item for sublist in items for item in sublist]
        for item in flat_list:
            key, value = parse_tag(item)
            d[key] = value
    return d


class PerftestCreateCli:

    def __init__(self):
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                                         description="Creates a new performance test based on a template")
        parser.add_argument("name",
                            help="The name of the performance test.", nargs='?')
        parser.add_argument("--template",
                            help="The name of the performance test template.", default="hazelcast4")
        parser.add_argument("--id",
                            help="An extra id to make resources unique. By default the username is used.")
        parser.add_argument("--list", help="List available performance test templates", action='store_true')
        args = parser.parse_args(sys.argv[2:])

        if args.list:
            for template in os.listdir(f"{simulator_home}/templates"):
                info(template)
            return

        name = args.name
        template = args.template

        if not args.name:
            exit_with_error("Can't create performance test, name is missing")

        log_header(f"Creating performance test [{name}]")
        info(f"Using template: {template}")
        cwd = os.getcwd()
        target_dir = os.path.join(cwd, name)

        if os.path.exists(target_dir):
            exit_with_error(f"Can't create performance [{target_dir}], the file/directory already exists")

        self.__copy_template(target_dir, template)

        os.chdir(target_dir)
        new_key()
        id = args.id if args.id else getpass.getuser()
        self.__process_templates(target_dir, id)
        os.chdir(cwd)

        log_header(f"Creating performance test [{name}]: Done")

    def __copy_template(self, target_dir, template):
        templates_dir = f"{simulator_home}/templates"
        template_dir = os.path.join(templates_dir, template)
        if not os.path.exists(template_dir):
            exit_with_error(f"Template directory [{template_dir}] does not exist.")

        shutil.copytree(template_dir, target_dir)

    def __process_templates(self, target_dir, id):
        for subdir, dirs, files in os.walk(target_dir):
            for filename in files:
                filepath = subdir + os.sep + filename
                if os.access(filepath, os.W_OK):
                    new_text = read(filepath).replace("<id>", id)
                    write(filepath, new_text)


class PerftestCloneCli:

    def __init__(self):
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                                         description="Clones an existing performance test")
        parser.add_argument("source", help="The name of source performance test.")
        parser.add_argument("destination", help="The directory for the destination performance test.")
        parser.add_argument("--force", help="Force using the destination directory if it already exists",
                            action='store_true')

        log_header("Cloning Performance test")
        args = parser.parse_args(sys.argv[2:])
        src = args.source
        dest = args.destination
        self.__check_valid_perftest(src)

        if args.force:
            info(f"Removing [{dest}].")
            remove(dest)
        else:
            if path.exists(dest):
                exit_with_error(f"Can't copy performance test to [{dest}], the directory already exists.")

        self.__clone(src, dest)
        self.__add_parent(src, dest)

        log_header(f"Performance test  [{src}] successfully cloned to [{dest}]")

    def __check_valid_perftest(self, src):
        if not path.exists(src):
            exit_with_error(f"Directory [{src}] does not exist.")

        if not path.exists(f"{src}/inventory_plan.yaml"):
            exit_with_error(f"Directory [{src}] is not a valid performance test.")

    def __clone(self, src, dest):
        shutil.copytree(src, dest)

        remove(f"{dest}/runs")
        remove(f"{dest}/logs")
        remove(f"{dest}/venv")
        remove(f"{dest}/.idea")
        remove(f"{dest}/.git")
        remove(f"{dest}/key")
        remove(f"{dest}/key.pub")
        remove(f"{dest}/.gitignore")

        # get rid of the terraform created files.
        for subdir, dirs, files in os.walk(dest):
            for dir in dirs:
                if dir.startswith(".terraform"):
                    remove(subdir + os.sep + dir)
            for file in files:
                if file.startswith("terraform.tfstate") or file.startswith(".terraform"):
                    remove(subdir + os.sep + file)

    def __add_parent(self, src, dest):
        with open(f"{dest}/clone_parent.txt", "w") as file:
            file.write("# Name of the parent performance test this performance test is cloned from.\n")
            file.write(src)


class PerftestRunCli:

    def __init__(self):
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                                         description='Runs a tests.yaml which is a self contained set of tests')
        parser.add_argument('file', nargs='?', help='The tests file', default=default_tests_path)
        parser.add_argument('-t', '--tag', metavar="KEY=VALUE", nargs=1, action='append')
        args = parser.parse_args(sys.argv[2:])
        tags = parse_tags(args.tag)

        tests = load_yaml_file(args.file)
        perftest = PerfTest()
        perftest.run(tests, tags)


class PerftestExecCli:

    def __init__(self):
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                                         description='Executes a performance test.')
        parser.add_argument('file', nargs='?', help='The test file', default=default_tests_path)

        parser.add_argument('--performanceMonitorInterval',
                            nargs=1,
                            default=10,
                            help='Defines the interval for throughput and latency snapshots on the workers. # 0 disabled tracking performance.')

        parser.add_argument('--workerVmStartupDelayMs',
                            nargs=1,
                            default=0,
                            help="Amount of time in milliseconds to wait between starting up the next worker. This is useful to prevent"
                                 + "duplicate connection issues.")

        parser.add_argument('--driver',
                            default="hazelcast5",
                            nargs=1,
                            help="The driver to run. Available options hazelcast5,hazelcast5-enterprise,hazelcast4,hazelcast-enterprise4,"
                                 + "hazelcast3,hazelcast-enterprise3,ignite2,infinispan9,infinispan10,"
                                 + "infinispan11,couchbase,lettuce5,lettucecluster5,jedis3")

        parser.add_argument('--version',
                            nargs=1,
                            help="The version of the vendor to use. Only hazelcast3/4/5 (and enterprise) will use this version")

        parser.add_argument('--duration',
                            nargs=1,
                            default="0s",
                            help="Amount of time to execute the RUN phase per test, e.g. 10s, 1m, 2h or 3d. If duration is set to 0, "
                                 + "the test will run until the test decides to stop.")

        parser.add_argument('--members',
                            nargs=1,
                            default=-1,
                            help="Number of cluster member Worker JVMs. If no value is specified and no mixed members are specified,"
                                 + " then the number of cluster members will be equal to the number of machines in the agents file.")

        parser.add_argument('--clients',
                            nargs=1,
                            default=0,
                            help="Number of cluster client Worker JVMs.")

        parser.add_argument('--dedicatedMemberMachines',
                            nargs=1,
                            default=0,
                            help="Controls the number of dedicated member machines. For example when there are 4 machines,"
                                 + " 2 members and 9 clients with 1 dedicated member machine defined, then"
                                 + " 1 machine gets the 2 members and the 3 remaining machines get 3 clients each.")

        # parser.add_argument('--targetType',
        #                     nargs='1',
        #                     default=0,
        #                     help= "Controls the number of dedicated member machines. For example when there are 4 machines,"
        #                     + " 2 members and 9 clients with 1 dedicated member machine defined, then"
        #                     + " 1 machine gets the 2 members and the 3 remaining machines get 3 clients each.")

        parser.add_argument('--clientType',
                            nargs=1,
                            default="javaclient",
                            help="Defines the type of client e.g javaclient, litemember, etc.")

        parser.add_argument('--targetCount',
                            nargs=1,
                            default=0,
                            help="Defines the number of Workers which execute the RUN phase. The value 0 selects all Workers.")

        parser.add_argument('--runPath',
                            nargs=1,
                            help="Defines the ID of the Session. If not set the actual date will be used."
                                 + " The session ID is used for creating the working directory."
                                 + " The session ID can also contain a directory e.g. foo/mytest, in this case mytest is the sessionId "
                                 + " and simulator will make use of the foo/mytest directory to write the results."
                                 + " For repeated runs, the session can be set to e.g. somedir/@it. In this case the @it is replaced by "
                                 + " an automatically incrementing number.")

        parser.add_argument('--verifyEnabled',
                            default="true",
                            help="Defines if tests are verified.")

        parser.add_argument('--failFast',
                            default="true",
                            help="Defines if the TestSuite should fail immediately when a test from a TestSuite fails instead of continuing.")

        parser.add_argument('--parallel',
                            action='store_true',
                            help="If defined tests are run in parallel.")

        parser.add_argument('--memberArgs',
                            nargs=1,
                            default="-XX:+HeapDumpOnOutOfMemoryError",
                            help="Member Worker JVM options (quotes can be used). ")

        parser.add_argument('--clientArgs',
                            nargs=1,
                            default="-XX:+HeapDumpOnOutOfMemoryError",
                            help="Client Worker JVM options (quotes can be used). ")

        parser.add_argument('--licenseKey',
                            nargs=1,
                            default="-XX:+HeapDumpOnOutOfMemoryError",
                            help="Sets the license key for Hazelcast Enterprise Edition.")

        parser.add_argument('--skipDownload',
                            action='store_true',
                            help="Prevents downloading of the created worker artifacts.")

        parser.add_argument('--nodeGroup',
                            nargs=1,
                            help="The name of the group that makes up the nodes.")

        parser.add_argument('--loadGeneratorGroup',
                            nargs=1,
                            help="The name of the group that makes up the loadGenerator.")

        parser.add_argument('-t', '--tag', metavar="KEY=VALUE", nargs=1, action='append')
        args = parser.parse_args(sys.argv[2:])
        test = load_yaml_file(args.file)
        tags = parse_tags(args.tag)

        perftest = PerfTest()
        run_path = perftest.exec(
            test,
            run_path=args.sessionId,
            performance_monitor_interval_seconds=args.performanceMonitorInterval,
            worker_vm_startup_delay_ms=args.workerVmStartupDelayMs,
            parallel=args.parallel,
            license_key=args.licenseKey,
            driver=args.driver,
            version=args.version,
            duration=args.duration,
            members=args.members,
            member_args=args.memberArgs,
            client_args=args.clientArgs,
            clients=args.clients,
            dedicated_member_machines=args.dedicatedMemberMachines,
            node_group=args.nodeGroup,
            loadgenerator_group=args.loadGeneratorGroup,
            fail_fast=args.failFast,
            verify_enabled=args.verifyEnabled,
            client_type=args.clientType,
            skip_download=args.skipDownload)

        perftest.collect(run_path, tags)


class PerftestTerminateCli:

    def __init__(self):
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                                         description='Terminates running performance test')
        parser.add_argument("--hosts", help="The target hosts.", default="all:!mc")
        args = parser.parse_args(sys.argv[2:])

        hosts = args.hosts

        perftest = PerfTest()
        perftest.terminate(hosts)


class PerftestCollectCli:

    def __init__(self):
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                                         description='Collects the results from a performance test')
        parser.add_argument("dir", help="The directory with the test runs")
        parser.add_argument('-t', '--tag', metavar="KEY=VALUE", nargs=1, action='append')
        args = parser.parse_args(sys.argv[2:])

        tags = parse_tags(args.tag)

        log_header("perftest collect")

        perftest = PerfTest()
        perftest.collect(args.dir, tags)

        log_header("perftest collect: done")


class PerftestCleanCli:

    def __init__(self):
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                                         description='Cleans to  load generators')
        args = parser.parse_args(sys.argv[2:])

        log_header("perftest clean")

        perftest = PerfTest()
        perftest.clean()

        log_header("perftest clean: done")


class PerftestCli:

    def __init__(self):
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                                         description='Management and execution of performance tests', usage=usage)
        parser.add_argument('command', help='Subcommand to run')

        args = parser.parse_args(sys.argv[1:2])
        if not hasattr(self, args.command):
            print('Unrecognized command', parser.print_help())
            exit(1)

        getattr(self, args.command)()

    def create(self):
        PerftestCreateCli()

    def clean(self):
        PerftestCleanCli()

    def clone(self):
        PerftestCloneCli()

    def run(self):
        PerftestRunCli()

    def exec(self):
        PerftestExecCli()

    def terminate(self):
        PerftestTerminateCli()

    def collect(self):
        PerftestCollectCli()

    def report(self):
        PerfTestReportCli()


if __name__ == '__main__':
    PerftestCli()
