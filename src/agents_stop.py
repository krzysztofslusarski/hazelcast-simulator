#!/usr/bin/python3

import yaml
import sys
from simulator.hosts import public_ip, ssh_user, ssh_options
from simulator.util import run_parallel, simulator_version
from simulator.ssh import SSH


def __agent_stop(agent):
    ssh = SSH(public_ip(agent), ssh_user(agent), ssh_options(agent))
    ssh.exec(f"hazelcast-simulator-{simulator_version}/bin/hidden/kill_agent")


agents_yaml = yaml.safe_load(sys.argv[1])
print(f"[INFO]Stopping agents: starting")
run_parallel(__agent_stop, [(agent,) for agent in agents_yaml])
print(f"[INFO]Stopping agents:done")
