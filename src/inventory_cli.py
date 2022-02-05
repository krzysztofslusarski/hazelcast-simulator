#!/usr/bin/python3
import sys
import argparse
from os import path

from simulator.inventory_terraform import terraform_import, terraform_destroy, terraform_apply
from simulator.util import load_yaml_file, exit_with_error, simulator_home, shell, simulator_version
from simulator.log import info, log_header
from simulator.ssh import new_key

inventory_plan_path = 'inventory_plan.yaml'

usage = '''inventory <command> [<args>]

The available commands are:
    apply               Applies the plan and updates the inventory
    destroy             Destroy the resources in the inventory
    import              Imports the inventory from the terraform plan
    install             Installs software on the inventory
    shell               Executes a shell command on the inventory
'''


# for git like arg parsing:
# https://chase-seibert.github.io/blog/2014/03/21/python-multilevel-argparse.html


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


class InventoryInstallCli:

    def __init__(self):
        parser = argparse.ArgumentParser(description='Installs software', usage=usage)
        parser.add_argument('command', help='Subcommand to run')

        args = parser.parse_args(sys.argv[2:3])
        if not hasattr(self, args.command):
            print('Unrecognized command', parser.print_help())
            exit(1)

        getattr(self, args.command)()

    def java(self):
        parser = argparse.ArgumentParser(description='Install Java')
        parser.add_argument("--url", help="The url of the JDK tar.gz file", default=default_url)
        parser.add_argument("--examples", help="Shows example urls", action='store_true')
        parser.add_argument("--hosts", help="The target hosts.", default="all")

        args = parser.parse_args(sys.argv[3:])

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

        args = parser.parse_args(sys.argv[3:])

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

        args = parser.parse_args(sys.argv[3:])

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
        args = parser.parse_args(sys.argv[3:])

        hosts = args.hosts

        log_header("Installing Simulator")
        info(f"hosts={hosts}")
        cmd = f"ansible-playbook --limit {hosts} --inventory inventory.yaml {simulator_home}/playbooks/install_simulator.yaml -e simulator_home='{simulator_home}' -e simulator_version='{simulator_version}'"
        info(cmd)
        exitcode = shell(cmd)
        if exitcode != 0:
            exit_with_error(f'Failed to install Simulator, exitcode={exitcode} command=[{cmd}])')
        log_header("Installing Simulator: Done")


class InventoryImportCli:
    def __init__(self):
        parser = argparse.ArgumentParser(description='Imports the inventory from a terraform installation.')
        parser.parse_args(sys.argv[2:])

        log_header("Inventory import")

        inventory_plan = load_yaml_file(inventory_plan_path)
        provisioner = inventory_plan['provisioner']

        if provisioner == "static":
            exit_with_error("Can't import inventory on static environment")
        elif provisioner == "terraform":
            terraform_plan = inventory_plan["terraform_plan"]
            terraform_import(terraform_plan)
        else:
            exit_with_error(f"Unrecognized provisioner [{provisioner}]")

        log_header("Inventory import: Done")


class InventoryApplyCli:
    def __init__(self):
        parser = argparse.ArgumentParser(description='Creates the inventory')
        parser.add_argument("-f", "--force",
                            help="Forces the destruction of the inventory (even when inventory.yaml doesn't exist)",
                            action='store_true')
        args = parser.parse_args(sys.argv[2:])

        log_header("Inventory apply")

        inventory_plan = load_yaml_file(inventory_plan_path)
        provisioner = inventory_plan['provisioner']
        force = args.force

        if not path.exists("key.pub"):
            new_key()

        if provisioner == "static":
            info(f"Ignoring create on static environment")
            return
        elif provisioner == "terraform":
            terraform_apply(inventory_plan, force)
        else:
            exit_with_error(f"Unrecognized provisioner [{provisioner}]")

        log_header("Inventory apply: Done")


class InventoryDestroyCli:
    def __init__(self):
        parser = argparse.ArgumentParser(description='Destroys the inventory')
        parser.add_argument("-f", "--force",
                            help="Forces the destruction of the inventory (even when inventory.yaml doesn't exist)",
                            action='store_true')
        args = parser.parse_args(sys.argv[2:])

        log_header("Inventory destroy")

        force = args.force

        if not force and not path.exists("inventory.yaml"):
            info("Ignoring destroy because inventory.yaml does not exit.")
            return

        inventory_plan = load_yaml_file(inventory_plan_path)
        provisioner = inventory_plan['provisioner']

        if provisioner == "static":
            info(f"Ignoring destroy on static environment")
            return
        elif provisioner == "terraform":
            terraform_destroy(inventory_plan, force)
        else:
            exit_with_error(f"Unrecognized provisioner [{provisioner}]")

        log_header("Inventory destroy: Done")


class InventoryShellCli:
    def __init__(self):
        parser = argparse.ArgumentParser(description='Executes a shell command on the inventory', )
        parser.add_argument("command", help="The command to execute", nargs='?')
        parser.add_argument("--hosts", help="The target hosts.", default="all")
        parser.add_argument('-p', "--ping", help="Checks if the inventory is reachable", action='store_true')

        args = parser.parse_args(sys.argv[2:])

        hosts = args.hosts

        if args.ping:
            self.remote_ping(hosts)
        else:
            if not args.command:
                exit_with_error("Command is mandatory")
            self.remote_shell(args.command, hosts)

    def remote_ping(self, hosts):
        log_header("Inventory Ping")
        cmd = f"""ansible-playbook --limit {hosts} --inventory inventory.yaml \
                      {simulator_home}/playbooks/shell.yaml -e "cmd='exit 0'" """
        info(cmd)
        exitcode = shell(cmd)
        if exitcode != 0:
            exit_with_error(f'Inventory Ping: Failed. Command [{cmd}], exitcode={exitcode}.)')

        log_header("Inventory Ping: Done")

    def remote_shell(self, shell_cmd, hosts):
        log_header("Inventory Remote Shell")
        info(f"cmd: {shell_cmd}")
        cmd = f"""ansible-playbook --limit {hosts} --inventory inventory.yaml \
                        {simulator_home}/playbooks/shell.yaml -e "cmd='{shell_cmd}'" """
        info(cmd)
        exitcode = shell(cmd)
        if exitcode != 0:
            exit_with_error(f'Remote command failed, command [{cmd}], exitcode={exitcode}.)')

        log_header("Inventory Remote Shell: Done")


class InventoryCli:

    def __init__(self):
        parser = argparse.ArgumentParser(description='Manages the inventory of resources', usage=usage)
        parser.add_argument('command', help='Subcommand to run')

        args = parser.parse_args(sys.argv[1:2])
        if not hasattr(self, args.command) and args.command != "import":
            print('Unrecognized command', parser.print_help())
            exit(1)

        if args.command == "import":
            self.import_inventory()
        else:
            getattr(self, args.command)()

    def import_inventory(self):
        InventoryImportCli()

    def apply(self):
        InventoryApplyCli()

    def shell(self):
        InventoryShellCli()

    def destroy(self):
        InventoryDestroyCli()

    def install(self):
        InventoryInstallCli()


if __name__ == '__main__':
    InventoryCli()