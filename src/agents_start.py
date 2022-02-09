#!/usr/bin/python3

import yaml
import sys
from simulator.util import run_parallel
from simulator.hosts import public_ip, ssh_user, ssh_options
from simulator.ssh import SSH


def __start_agent(agent):
    print(f"[INFO]     {public_ip(agent)} starting")
    ssh = SSH(public_ip(agent), ssh_user(agent), ssh_options(agent))
    ssh.exec(
        f"hazelcast-simulator/bin/hidden/agent_start {agent['agent_index']} {public_ip(agent)} {agent['agent_port']}")


# def __verify_installation(agent):
#    print(f"[INFO]     {public_ip(agent)} starting")
#    ssh = SSH(public_ip(agent), ssh_user(agent), ssh_options(agent))
#    ssh.exec("rm -fr agent_start.sh")
#    ssh.scp_to_remote(f"{scripts_dir}/agent_start.sh", ".")
#    ssh.exec(
#        f"./agent_start.sh {agent['agent_index']} {public_ip(agent)} {agent['agent_port']} {simulator_version}")


print(f"[INFO]Starting agents: starting")
agents_yaml = yaml.safe_load(sys.argv[1])
# util.run_parallel(__verify_installation, [(agent,) for agent in agents_yaml])
run_parallel(__start_agent, [(agent,) for agent in agents_yaml])
print(f"[INFO]Starting agents: done")
#
# #!/bin/bash
#
# # exit on failure
# set -e
#
# # comma separated list of agent ip addresses
# hidden=$1
#
# verify_installation(){
#     if [ "$CLOUD_PROVIDER" != "local" ]; then
#         for agent in ${hidden//,/ } ; do
#             status=$(ssh $SSH_OPTIONS $SSH_USER@$agent \
#                 "[[ -f hazelcast-simulator-$SIMULATOR_VERSION/bin/agent ]] && echo OK || echo FAIL")
#
#              if [ $status != "OK" ] ; then
#                 echo "[ERROR]Simulator is not installed correctly on $agent. Please run 'install simulator' to fix this."
#                 exit 1
#             fi
#         done
#     fi
# }
#
# start_remote(){
#     agent=$1
#     agent_index=$2
#
#     echo "[INFO]    Agent [A$agent_index] $agent starting"
#
#     ssh $SSH_OPTIONS $SSH_USER@$agent "killall -9 java || true"
#     ssh $SSH_OPTIONS $SSH_USER@$agent "rm -f agent.pid"
#     ssh $SSH_OPTIONS $SSH_USER@$agent "rm -f agent.out"
#     ssh $SSH_OPTIONS $SSH_USER@$agent "rm -f agent.err"
#
#     args="--addressIndex $agent_index --publicAddress $agent --port $AGENT_PORT"
#
#     ssh $SSH_OPTIONS $SSH_USER@$agent \
#         "nohup hazelcast-simulator-$SIMULATOR_VERSION/bin/agent $args > agent.out 2> agent.err < /dev/null &"
#
#     ssh $SSH_OPTIONS $SSH_USER@$agent "hazelcast-simulator-$SIMULATOR_VERSION/bin/await-file-exists agent.pid"
#
#     echo "[INFO]    Agent [A$agent_index] $agent started successfully"
# }
#
# start_local(){
#     echo "[INFO]Local agent [A1] starting..."
#
#     if [ -f agent.pid ]; then
#         $SIMULATOR_HOME/bin/kill-from-pid-file agent.pid
#         rm agent.pid || true
#     fi
#
#     rm agent.out || true
#     rm agent.err || true
#
#     args="--addressIndex 1 --publicAddress 127.0.0.1 --port $AGENT_PORT --parentPid $parentPid"
#
#     nohup $SIMULATOR_HOME/bin/agent $args > agent.out 2> agent.err < /dev/null &
#
#     $SIMULATOR_HOME/bin/await-file-exists agent.pid
#
#     echo "[INFO]Local agent [A1] started"
# }
#
# start(){
#     if [ "$CLOUD_PROVIDER" = "local" ]; then
#         start_local
#     else
#         echo "[INFO]Remote hidden starting"
#         agent_index=1
#         for agent in ${hidden//,/ } ; do
#             start_remote $agent $agent_index &
#             ((agent_index++))
#         done
#
#         # todo: no feedback if the agent was actually started.
#         wait
#         echo "[INFO]Remote hidden started"
#     fi
# }
#
# # no starting required when embedded
# if [ "$CLOUD_PROVIDER" = "embedded" ]; then
#     exit 0
# fi
#
# verify_installation
# start
