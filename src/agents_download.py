#!/usr/bin/python3
import yaml
import sys
from simulator.util import shell, run_parallel,simulator_version
from simulator.hosts import public_ip, ssh_user, ssh_options


root_dir = sys.argv[1]
session_id = sys.argv[2]
agents_yaml = yaml.safe_load(sys.argv[3])


def __agent_download(agent):
    print(f"[INFO]     {public_ip(agent)} Download")

    if "session_id" == "*":
        download_path = f"hazelcast-simulator-{simulator_version}/workers/"
    else:
        download_path = f"hazelcast-simulator-{simulator_version}/workers/{session_id}"

    # copy the files
    # we exclude the uploads directory because it could be very big e.g jars
    shell(f"""rsync --copy-links -avvz --compress-level=9 -e "ssh {ssh_options(agent)}" --exclude 'upload' {ssh_user(agent)}@{public_ip(agent)}:{download_path} {root_dir}""")

    # delete the files on the agent (no point in keeping them around if they are already copied locally)
    if session_id == "*":
        shell(f"""ssh {ssh_options(agent)} {ssh_user(agent)}@{public_ip(agent)} "rm -fr {download_path}/*" """)
    else:
        shell(f"""ssh {ssh_options(agent)} {ssh_user(agent)}@{public_ip(agent)} "rm -fr {download_path}/" """)

    print(f"[INFO]     {public_ip(agent)} Download completed")


print(f"[INFO]Downloading: starting")
run_parallel(__agent_download, [(agent,) for agent in agents_yaml])
print(f"[INFO]Downloading: done")