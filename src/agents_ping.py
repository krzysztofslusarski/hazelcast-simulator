#!/usr/bin/python3
import yaml
import sys
from simulator.hosts import public_ip, ssh_user, ssh_options
from simulator.ssh import Ssh
from simulator.util import run_parallel


def ___agent_ping(agent):
    print(f"[INFO]     {public_ip(agent)}: ping")
    ssh = Ssh(public_ip(agent), ssh_user(agent), ssh_options(agent))
    ssh.connect()
    print(f"[INFO]     {public_ip(agent)}: pong")


print(f"[INFO]Agent ping:starting")
agents_yaml = yaml.safe_load(sys.argv[1])
run_parallel(___agent_ping, [(agent,) for agent in agents_yaml])
print(f"[INFO]Agent ping:done")
