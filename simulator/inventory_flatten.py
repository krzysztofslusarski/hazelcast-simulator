#!/usr/bin/python3
import os.path
import subprocess

import yaml
from yaml import dump
from util import exit_with_error

inventory_plan_path = 'inventory_plan.yaml'
inventory_path = 'inventory.yaml'


def load_flattened_inventory():
    if not os.path.exists(inventory_path):
        exit_with_error(f"Could not find [{inventory_path}]")

    cmd = f"ansible-inventory -i {inventory_path} -y --list"
    out = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True).stdout

    inventory = yaml.safe_load(out)
    new_inventory = []
    children = inventory['all']['children']
    for group_name, group in children.items():
        hosts = group.get('hosts')
        if hosts:
            for hostname, host in hosts.items():
                new_host = {}
                new_inventory.append(new_host)
                new_host['public_ip'] = host.get('public_ip')
                new_host['private_ip'] = host.get('private_ip')
                new_host['ssh_user'] = host.get('ansible_user')
                new_host['groupname'] = group_name
                private_key = host.get("ansible_ssh_private_key_file")
                if private_key:
                    new_host['ssh_options'] = f"-i {private_key} -o StrictHostKeyChecking=no -o ConnectTimeout=60"

    return new_inventory


def flatten_inventory():
    inventory = load_flattened_inventory()
    print(dump(inventory))


if __name__ == '__main__':
    flatten_inventory()
