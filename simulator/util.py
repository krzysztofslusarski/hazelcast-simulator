import os.path
import shutil
from os import path

from subprocess import Popen, PIPE
from selectors import EVENT_READ, DefaultSelector
from threading import Thread
from threading import Lock, Condition
import pkg_resources
import yaml

from log import Level, error, log

module_dir = os.path.dirname(pkg_resources.resource_filename(__name__, '__init__.py'))
simulator_version = "0.14-SNAPSHOT"
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

def remove(file):
    if not path.exists(file):
        return

    if path.isfile(file):
        os.remove(file)
    else:
        shutil.rmtree(file)


def load_yaml_file(path):
    if not os.path.exists(path):
        exit_with_error(f"Could not find file [{path}]")

    with open(path) as f:
        return yaml.load(f, Loader=yaml.FullLoader)


# Copied
class Future:

    def __init__(self):
        self.__condition = Condition(Lock())
        self.__val = None
        self.__is_set = False

    def get(self):
        with self.__condition:
            while not self.__is_set:
                self.__condition.wait()

            if isinstance(self.__val, Exception):
                raise Exception() from self.__val
            return self.__val

    def join(self):
        self.get()

    def set(self, val):
        with self.__condition:
            if self.__is_set:
                raise RuntimeError("Future has already been set")
            self.__val = val
            self.__is_set = True
            self.__condition.notify_all()

    def done(self):
        return self.__is_set


# Copied
class Worker(Thread):

    def __init__(self, target, args):
        super().__init__(target=target, args=args)
        self.future = Future()

    def run(self):
        self.exception = None
        try:
            super().run()
            self.future.set(True)
        except Exception as e:
            self.exception = e
            self.future.set(e)


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


