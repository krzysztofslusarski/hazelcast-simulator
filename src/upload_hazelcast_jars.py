#!/usr/bin/python3

import yaml
import sys
from simulator.util import run_parallel,bin_dir
from simulator.hosts import public_ip, ssh_user, ssh_options
from simulator.ssh import SSH


def __upload(agent):
    print(f"[INFO]     {public_ip(agent)} starting")
    ssh = SSH(public_ip(agent), ssh_user(agent), ssh_options(agent))
    ssh.exec("rm -fr agent_start")
    ssh.scp_to_remote(f"{bin_dir}/hidden/agent_start", ".")
    ssh.exec(f"./agent_start {agent['agent_index']} {public_ip(agent)} {agent['agent_port']}")


print(f"[INFO]Uploading Hazelcast jars")
agents_yaml = yaml.safe_load(sys.argv[1])
run_parallel(__upload, [(agent,) for agent in agents_yaml])
print(f"[INFO]Uploading Hazelcast jars: done")
