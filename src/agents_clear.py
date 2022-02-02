#!/usr/bin/python3

import yaml
import sys
from simulator.ssh import SSH
from simulator.util import simulator_version, run_parallel
from simulator.hosts import public_ip, ssh_user, ssh_options


def __agent_clear(agent):
    print(f"[INFO]     {public_ip(agent)} Clearing agent")
    ssh = SSH(public_ip(agent), ssh_user(agent), ssh_options(agent))
    ssh.exec(f"rm -fr hazelcast-simulator-{simulator_version}/workers/*")


agents_yaml = yaml.safe_load(sys.argv[1])
print(f"[INFO]Clearing agents: starting")
run_parallel(__agent_clear, [(agent,) for agent in agents_yaml])
print(f"[INFO]Clearing agents: done")
