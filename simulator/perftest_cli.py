#!/usr/bin/python3
import os
import shutil
import sys
import argparse
import getpass
from os import path

from inventory_flatten import load_flattened_inventory
from log import log_header, info
from ssh import new_key
from util import load_yaml_file, exit_with_error, remove, simulator_home, write, read
from perftest_report import PerfTestReportCli
from perftest_simulator import simulator_perftest_run, simulator_perftest_terminate, simulator_perftest_collect

default_testplan_path = 'testplan.yaml'
inventory_path = 'inventory.yaml'
usage = '''perftest <command> [<args>]

The available commands are:
    create      Clones an existing performance test.
    clone       Clones an existing performance test.
    collect     Collects the performance test data and stores it in result.yaml.
    run         Runs the performance test
    terminate   Terminate all running performance tests.   
    report      Generate performance report 
'''


# https://stackoverflow.com/questions/27146262/create-variable-key-value-pairs-with-argparse-python
def parse_tag(s):
    items = s.split('=')
    key = items[0].strip()  # we remove blanks around keys, as is logical
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
        parser = argparse.ArgumentParser("Creating a new performance test based a template.")
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
        parser = argparse.ArgumentParser(description="Clones an existing performance test")
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

        remove(f"{dest}/results")
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
        parser = argparse.ArgumentParser(description='Runs the testplan')
        parser.add_argument('file', nargs='?', help='The testplan file', default=default_testplan_path)
        parser.add_argument('-t', '--tag', metavar="KEY=VALUE", nargs='+', action='append')
        args = parser.parse_args(sys.argv[2:])
        testplan = load_yaml_file(args.file)
        tags = parse_tags(args.tag)

        loadgenerator = testplan['loadgenerator']

        if loadgenerator == "simulator":
            simulator_perftest_run(testplan, tags)
        else:
            exit_with_error(f"Unknown loadgenerator {loadgenerator}")


class PerftestTerminateCli:

    def __init__(self):
        parser = argparse.ArgumentParser(description='Terminates running testplan')
        args = parser.parse_args(sys.argv[2:])

        testplan = load_yaml_file(default_testplan_path)
        inventory = load_flattened_inventory()

        loadgenerator = testplan['loadgenerator']
        if loadgenerator == "simulator":
            simulator_perftest_terminate(inventory, testplan)
        else:
            exit_with_error(f"Unknown loadgenerator {loadgenerator}")


class PerftestCollectCli:

    def __init__(self):
        parser = argparse.ArgumentParser(description='Collects the results from a performance test')
        parser.add_argument("dir", help="The directory with the test results")
        parser.add_argument('-t', '--tag', metavar="KEY=VALUE", nargs='+', action='append')
        args = parser.parse_args(sys.argv[2:])
        tags = parse_tags(args.tag)

        testplan = load_yaml_file(default_testplan_path)
        loadgenerator = testplan['loadgenerator']
        if loadgenerator == "simulator":
            simulator_perftest_collect(args.dir, tags)
        else:
            exit_with_error(f"Unknown loadgenerator {loadgenerator}")


class PerftestCli:

    def __init__(self):
        parser = argparse.ArgumentParser(description='Execution and analysis of testplans', usage=usage)
        parser.add_argument('command', help='Subcommand to run')

        args = parser.parse_args(sys.argv[1:2])
        if not hasattr(self, args.command):
            print('Unrecognized command', parser.print_help())
            exit(1)

        getattr(self, args.command)()

    def create(self):
        PerftestCreateCli()

    def clone(self):
        PerftestCloneCli()

    def run(self):
        PerftestRunCli()

    def terminate(self):
        PerftestTerminateCli()

    def collect(self):
        PerftestCollectCli()

    def report(self):
        PerfTestReportCli()


if __name__ == '__main__':
    PerftestCli()
