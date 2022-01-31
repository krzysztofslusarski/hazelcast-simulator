#!/usr/bin/python3

import argparse
import sys

from log import info, log_header
from util import shell, simulator_home, exit_with_error, simulator_version

default_url = "https://download.java.net/java/ga/jdk11/openjdk-11_linux-x64_bin.tar.gz"

examples = """
Oracle JDK:

        https://www.oracle.com/java/technologies/javase-jdk15-downloads.html

        When selecting the url from the download page, you need to click the link and wait till you get a popop
        and then select the url.

        Examples:
        --url=https://simulator-jdk.s3.amazonaws.com/jdk-8u261-linux-x64.tar.gz
        --url=https://download.oracle.com/otn-pub/java/jdk/15+36/779bf45e88a44cbd9ea6621d33e33db1/jdk-15_linux-x64_bin.tar.gz

OpenJDK jdk.java.net:

        https://jdk.java.net/

        Examples:
        --url=https://download.java.net/java/GA/jdk9/9.0.4/binaries/openjdk-9.0.4_windows-x64_bin.tar.gz
        --url=https://download.java.net/java/ga/jdk11/openjdk-11_linux-x64_bin.tar.gz
        --url=https://download.java.net/java/GA/jdk15/779bf45e88a44cbd9ea6621d33e33db1/36/GPL/openjdk-15_linux-x64_bin.tar.gz

AdoptOpenJDK:

        https://github.com/AdoptOpenJDK/

        Examples of OpenJDK:
        --url=https://github.com/AdoptOpenJDK/openjdk8-binaries/releases/download/jdk8u265-b01_openj9-0.21.0/OpenJDK8U-jdk_x64_linux_openj9_8u265b01_openj9-0.21.0.tar.gz
        --url=https://github.com/AdoptOpenJDK/openjdk11-binaries/releases/download/jdk-11.0.8%2B10/OpenJDK11U-jdk_x64_linux_hotspot_11.0.8_10.tar.gz
        --url=https://github.com/AdoptOpenJDK/openjdk15-binaries/releases/download/jdk15u-2020-09-17-08-34/OpenJDK15U-jdk_x64_linux_hotspot_2020-09-17-08-34.tar.gz

        Examples of OpenJDK + J9:
        --url=https://github.com/AdoptOpenJDK/openjdk8-binaries/releases/download/jdk8u265-b01_openj9-0.21.0/OpenJDK8U-jdk_x64_linux_openj9_8u265b01_openj9-0.21.0.tar.gz
        --url=https://github.com/AdoptOpenJDK/openjdk11-binaries/releases/download/jdk-11.0.8%2B10_openj9-0.21.0/OpenJDK11U-jdk_x64_linux_openj9_11.0.8_10_openj9-0.21.0.tar.gz

Graal:

        https://github.com/graalvm/graalvm-ce-builds/

        Examples:
        --url=https://github.com/graalvm/graalvm-ce-builds/releases/download/vm-20.2.0/graalvm-ce-java8-linux-amd64-20.2.0.tar.gz
        --url=https://github.com/graalvm/graalvm-ce-builds/releases/download/vm-20.2.0/graalvm-ce-java11-linux-amd64-20.2.0.tar.gz

Amazon Coretto:

        https://aws.amazon.com/corretto/

        Examples:
        --url=https://corretto.aws/downloads/latest/amazon-corretto-8-x64-linux-jdk.tar.gz
        --url=https://corretto.aws/downloads/latest/amazon-corretto-11-x64-linux-jdk.tar.gz

Zulu:

        https://cdn.azul.com/zulu/bin/

        Examples:
        --url=https://cdn.azul.com/zulu/bin/zulu8.48.0.53-ca-jdk8.0.265-linux_x64.tar.gz
        --url=https://cdn.azul.com/zulu/bin/zulu11.41.23-ca-jdk11.0.8-linux_x64.tar.gz
        --url=https://cdn.azul.com/zulu/bin/zulu15.27.17-ca-jdk15.0.0-linux_x64.tar.gz

Bellsoft:

        https://bell-sw.com/pages/downloads

        Examples:
        --url=https://download.bell-sw.com/java/11.0.8+10/bellsoft-jdk11.0.8+10-linux-amd64.tar.gz
"""


usage = '''install <command> [<args>]

The available commands are:
    java            Installs Java
    simulator       Installs Simulator
    perf            Installs Linux Perf
    async_profiler  Installs Async Profiler
'''


class InstallCli:

    def __init__(self):
        parser = argparse.ArgumentParser(description='Installs software', usage=usage)
        parser.add_argument('command', help='Subcommand to run')

        args = parser.parse_args(sys.argv[1:2])
        if not hasattr(self, args.command):
            print('Unrecognized command', parser.print_help())
            exit(1)

        getattr(self, args.command)()

    def java(self):
        parser = argparse.ArgumentParser(description='Install Java')
        parser.add_argument("--url", help="The url of the JDK tar.gz file", default=default_url)
        parser.add_argument("--examples", help="Shows example urls", action='store_true')
        parser.add_argument("--hosts", help="The target hosts.", default="all")

        args = parser.parse_args(sys.argv[2:])

        if args.examples:
            print(examples)
            return

        hosts = args.hosts
        url = args.url

        log_header("Installing Java")
        info(f"url={url}")
        info(f"hosts={hosts}")
        cmd = f"ansible-playbook --limit {hosts} --inventory inventory.yaml {simulator_home}/playbooks/install_java.yaml -e jdk_url='{url}'"
        info(cmd)
        exitcode = shell(cmd)
        if exitcode != 0:
            exit_with_error(f'Failed to install Java, exitcode={exitcode} command=[{cmd}])')
        log_header("Installing Java: Done")

    def async_profiler(self):
        parser = argparse.ArgumentParser(description='Install Async Profiler')
        parser.add_argument("--version", help="Async profiler version", default="2.6")
        parser.add_argument("--hosts", help="The target hosts.", default="all")

        args = parser.parse_args(sys.argv[2:])

        hosts = args.hosts
        version = args.version
        log_header("Installing Async Profiler")
        info(f"hosts={hosts}")
        info(f"version={version}")
        cmd = f"ansible-playbook --limit {hosts} --inventory inventory.yaml {simulator_home}/playbooks/install_async_profiler.yaml -e version='{version}'"
        info(cmd)
        exitcode = shell(cmd)
        if exitcode != 0:
            exit_with_error(f'Failed to install Perf, exitcode={exitcode} command=[{cmd}])')
        log_header("Installing Async Profiler: Done")

    def perf(self):
        parser = argparse.ArgumentParser(description='Install Linux Perf')
        parser.add_argument("--hosts", help="The target hosts.", default="all")

        args = parser.parse_args(sys.argv[2:])

        hosts = args.hosts
        log_header("Installing Perf")
        cmd = f"ansible-playbook --limit {hosts} --inventory inventory.yaml {simulator_home}/playbooks/install_perf.yaml"
        info(cmd)
        exitcode = shell(cmd)
        if exitcode != 0:
            exit_with_error(f'Failed to install Perf, exitcode={exitcode} command=[{cmd}])')
        log_header("Installing Perf: Done")

    def simulator(self):
        parser = argparse.ArgumentParser(description='Install Simulator')
        parser.add_argument("--hosts", help="The target hosts.", default="all")
        args = parser.parse_args(sys.argv[2:])

        hosts = args.hosts

        log_header("Installing Simulator")
        info(f"hosts={hosts}")
        cmd = f"ansible-playbook --limit {hosts} --inventory inventory.yaml {simulator_home}/playbooks/install_simulator.yaml -e simulator_home='{simulator_home}' -e simulator_version='{simulator_version}'"
        info(cmd)
        exitcode = shell(cmd)
        if exitcode != 0:
            exit_with_error(f'Failed to install Simulator, exitcode={exitcode} command=[{cmd}])')
        log_header("Installing Simulator: Done")


if __name__ == '__main__':
    InstallCli()
