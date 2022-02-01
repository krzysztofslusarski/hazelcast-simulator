import os
import selectors
import subprocess
import time

from util import shell, exit_with_error
from log import Level, log_host


def new_key(key_path="key"):
    if os.path.exists(key_path):
        exit_with_error(f'Key [{key_path}] already exists')

    if shell(f"""ssh-keygen -P "" -m PEM -f {key_path}""") != 0:
        exit_with_error(f'Failed to generate new key')
    shell(f"chmod 400 {key_path}")


# Copied
class SSH:

    def __init__(self,
                 ip,
                 ssh_user,
                 ssh_options,
                 silent_seconds=30,
                 use_control_socket=True,
                 log_enabled=False):
        self.ip = ip
        self.ssh_user = ssh_user
        self.ssh_options = ssh_options
        self.silent_seconds = silent_seconds
        self.log_enabled = log_enabled
        if use_control_socket:
            self.control_socket_file = f"/tmp/{self.ssh_user}@{self.ip}.socket"
        else:
            self.control_socket_file = None

    def wait(self):
        self.__wait()

    def __wait(self):
        args = f"-o ConnectTimeout=1 -o ConnectionAttempts=1 {self.ssh_options}"
        if self.control_socket_file:
            if os.path.exists(self.control_socket_file):
                return
            args = f"{args} -M -S {self.control_socket_file} -o ControlPersist=5m"
        cmd = f'ssh {args} {self.ssh_user}@{self.ip} exit'
        # print(f"[INFO]{cmd}")
        exitcode = None
        max_attempts = 300
        for attempt in range(1, max_attempts):
            if attempt > self.silent_seconds:
                log_host(self.ip, f'Trying to connect, attempt [{attempt}/{max_attempts}], command [{cmd}]')
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.stdout:
                    lines = result.stdout.splitlines()
                    for line in lines:
                        log_host(self.ip, line, level=Level.info)
                if result.stderr:
                    lines = result.stderr.splitlines()
                    for line in lines:
                        log_host(self.ip, line, level=Level.warn)
                exitcode = result.returncode
            else:
                exitcode = subprocess.call(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            if exitcode == 0 or exitcode == 1:  # todo: we need to deal better with exit code
                self.wait_for_connect = False
                return
            time.sleep(1)

        raise Exception(f"Failed to connect to {self.ip}, exitcode={exitcode}")

    def __is_connected(self):
        return self.control_socket_file and os.path.exists(self.control_socket_file)

    def scp_from_remote(self, src, dst_dir):
        os.makedirs(dst_dir, exist_ok=True)
        cmd = f'scp {self.ssh_options} -r -q {self.ssh_user}@{self.ip}:{src} {dst_dir}'
        self.__scp(cmd)

    def scp_to_remote(self, src, dst):
        cmd = f'scp {self.ssh_options} -r -q {src} {self.ssh_user}@{self.ip}:{dst}'
        self.__scp(cmd)

    def __scp(self, cmd):
        self.__wait()
        exitcode = subprocess.call(cmd, shell=True)
        # raise Exception(f"Failed to execute {cmd} after {self.max_attempts} attempts")

    def exec(self, command, ignore_errors=False):
        self.__wait()

        cmd_list = ["ssh"]
        if self.__is_connected():
            cmd_list.append("-S")
            cmd_list.append(f"{self.control_socket_file}")
        cmd_list.extend(self.ssh_options.split())
        cmd_list.append(f"{self.ssh_user}@{self.ip}")
        cmd_list.append(command)

        if self.log_enabled:
            log_host(self.ip, cmd_list)

        process = subprocess.Popen(cmd_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        sel = selectors.DefaultSelector()
        sel.register(process.stdout, selectors.EVENT_READ)
        sel.register(process.stderr, selectors.EVENT_READ)

        while True:
            for key, _ in sel.select():
                data = key.fileobj.read1().decode()
                if not data:
                    exitcode = process.poll()
                    if exitcode == 0 or ignore_errors:
                        return
                    else:
                        raise Exception(f"Failed to execute [{cmd_list}], exitcode={exitcode}")
                lines = data.splitlines()
                log_level = Level.info if key.fileobj is process.stdout else Level.warn
                for line in lines:
                    log_host(self.ip, line, log_level)