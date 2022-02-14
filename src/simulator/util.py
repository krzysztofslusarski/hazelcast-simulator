import os.path
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from os import path

from subprocess import Popen, PIPE
from selectors import EVENT_READ, DefaultSelector
import pkg_resources
import yaml

from simulator.log import Level, error, log

module_dir = os.path.dirname(pkg_resources.resource_filename(__name__, '__init__.py'))
simulator_home = os.environ.get('SIMULATOR_HOME')
bin_dir = os.path.join(simulator_home, "bin")


def read(file):
    with open(file, 'r') as f:
        return f.read()


def write(file, text):
    with open(file, 'w') as f:
        return f.write(text)


def now_seconds():
    return round(time.time())


def remove(file):
    if not path.exists(file):
        return

    if path.isfile(file):
        os.remove(file)
    else:
        shutil.rmtree(file)


def validate_dir(path):
    path = os.path.expanduser(path)

    if not os.path.exists(path):
        print(f"Directory [{path}] does not exist")
        exit(1)

    if not os.path.isdir(f"{path}/"):
        print(f"Directory [{path}] is not a directory")
        exit(1)

    return path


def mkdir(path):
    path = os.path.expanduser(path)

    if os.path.isdir(path):
        return path

    if os.path.exists(path):
        exit_with_error(f"Can't create directory [{path}], file with the same name already exists.")

    os.makedirs(path)
    return path


def dump(obj):
    for attr in dir(obj):
        print(("obj.%s = %s" % (attr, getattr(obj, attr))))


def load_yaml_file(path):
    if not os.path.exists(path):
        exit_with_error(f"Could not find file [{path}]")

    with open(path) as f:
        return yaml.load(f, Loader=yaml.FullLoader)


def run_parallel(target, args_list, max_workers=8):
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []

        for args in args_list:
            futures.append(executor.submit(target, *args))

        for f in futures:
            f.result()


def exit_with_error(text):
    error(text)
    exit(1)


def shell_logged(cmd, log_file, exit_on_error=False):
    with open(log_file, "a") as f:
        result = subprocess.run(cmd, shell=True, text=True, stdout=f, stderr=f)
        if result.returncode != 0 and exit_on_error:
            print(f"Failed to run [{cmd}], exitcode: {result.returncode}. Check {log} for details.")
            exit(1)
        return result.returncode


def shell(cmd, shell=True, split=False, use_print=False):
    if split:
        cmd = cmd.split()
    process = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=shell)

    selector = DefaultSelector()
    selector.register(process.stdout, EVENT_READ)
    selector.register(process.stderr, EVENT_READ)

    while True:
        for key, _ in selector.select():
            data = key.fileobj.read1().decode()

            if not data:
                process.wait()
                return process.poll()

            log_level = Level.info if key.fileobj is process.stdout else Level.warn
            for line in data.splitlines():
                if use_print:
                    print(line)
                else:
                    log(line, log_level)


def parse_tag(s):
    items = s.split('=')
    key = items[0].strip()
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
