#!/usr/bin/python3
import sys
import argparse
from os import path

from inventory_terraform import terraform_import, terraform_destroy, terraform_apply
from util import load_yaml_file, exit_with_error, simulator_home, shell
from log import info, log_header
from ssh import new_key

inventory_plan_path = 'inventory_plan.yaml'

usage = '''inventory <command> [<args>]

The available commands are:
    apply               Applies the plan and updates the inventory
    destroy             Destroy the resources in the inventory
    import              Imports the inventory from the terraform plan
    shell               Executes a shell command on the inventory
'''


# for git like arg parsing:
# https://chase-seibert.github.io/blog/2014/03/21/python-multilevel-argparse.html


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


if __name__ == '__main__':
    InventoryCli()
