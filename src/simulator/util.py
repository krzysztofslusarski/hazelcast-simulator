import os.path
import shutil
import subprocess
import time
from os import path

from subprocess import Popen, PIPE
from selectors import EVENT_READ, DefaultSelector
from threading import Thread
from threading import Lock, Condition
import pkg_resources
import yaml

from simulator.log import Level, error, log

module_dir = os.path.dirname(pkg_resources.resource_filename(__name__, '__init__.py'))
simulator_home = os.environ.get('SIMULATOR_HOME')
bin_dir = os.path.join(simulator_home, "bin")


def read(file):
    f = open(file, 'r')
    s = f.read()
    f.close()
    return s


def write(file, text):
    f = open(file, 'w')
    f.write(text)
    f.close()


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


# Copied
class Future:

    def __init__(self):
        self.__ready = Condition(Lock())
        self.__val = None
        self.__completed = False

    def get(self):
        with self.__ready:
            while not self.__completed:
                self.__ready.wait()

            if isinstance(self.__val, Exception):
                raise Exception() from self.__val
            return self.__val

    def join(self):
        self.get()

    def complete(self, val):
        with self.__ready:
            if self.__completed:
                raise RuntimeError("Future has already been completed")
            self.__val = val
            self.__completed = True
            self.__ready.notify_all()

    def done(self):
        return self.__completed


# Copied
class Worker(Thread):

    def __init__(self, target, args):
        super().__init__(target=target, args=args)
        self.future = Future()
        self.exception = None

    def run(self):
        try:
            super().run()
            self.future.complete(True)
        except Exception as e:
            self.exception = e
            self.future.complete(e)


# Copied
def run_parallel(target, args_list, ignore_errors=False):
    workers = []
    for args in args_list:
        worker = Worker(target, args)
        worker.start()
        workers.append(worker)

    for worker in workers:
        worker.join()
        if not ignore_errors and worker.exception:
            raise Exception(f"Failed to execute {target} {args_list}") from worker.exception


# Copied
def join_all(*futures):
    for f in futures:
        f.join()


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


# Copied
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

            lines = data.splitlines()
            log_level = Level.info if key.fileobj is process.stdout else Level.warn
            for line in lines:
                if use_print:
                    print(line)
                else:
                    log(line, log_level)


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