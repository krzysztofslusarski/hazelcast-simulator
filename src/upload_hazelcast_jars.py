#!/usr/bin/python3
import os.path
import subprocess

import yaml
import sys
from simulator.util import run_parallel, shell
from simulator.hosts import public_ip, ssh_user, ssh_options
from simulator.ssh import SSH


def __upload(agent):
    print(f"[INFO]     {public_ip(agent)} starting")
    ssh = SSH(public_ip(agent), ssh_user(agent), ssh_options(agent))
    ssh.exec("mkdir -p hazelcast-simulator/driver-lib/")
    dest = f"hazelcast-simulator/driver-lib/{version_spec.replace('=', '-')}"
    ssh.exec(f"rm -fr {dest}")
    ssh.exec(f"mkdir -p {dest}")
    for artifact_id in artifact_ids:
        ssh.scp_to_remote(f"{local_jar_path(artifact_id)}", f"{dest}")

    print(f"[INFO]     {public_ip(agent)} done")


def local_repository_path_repo():
    cmd = "mvn help:evaluate -Dexpression=settings.localRepository -q -DforceStdout"
    return subprocess.check_output(cmd, shell=True, text=True)


def local_jar_path(artifact_id):
    return f"{local_repository_path_repo}/com/hazelcast/{artifact_id}/{version}/{artifact_id}-{version}.jar"


def download(artifact_id):
    artifact = f"com.hazelcast:{artifact_id}:{version}"
    cmd = f"mvn org.apache.maven.plugins:maven-dependency-plugin:3.2.0:get -Dartifact={artifact}"
    exitcode = shell(cmd)
    if exitcode != 0:
        print(f"Failed {cmd}, exitcode: {exitcode}")
    path = local_jar_path(artifact_id)
    if not os.path.exists(path):
        print(f"[INFO] Could not find {path} in maven repo.")
        exit(1)


def artifact_ids():
    if version.startswith("3.") or version.startswith("4."):
        return ['hazelcast-all']
    elif version.startswith("5"):
        return ['hazelcast', 'hazelcast-sql', 'hazelcast-spring']
    else:
        print(f"[ERROR] Unrecognized version {version}")


agents_yaml = yaml.safe_load(sys.argv[1])
version_spec = sys.argv[2]

print(f"[INFO]Uploading Hazelcast jars")

if not version_spec.startswith("maven="):
    print(f"Unhandled version spec: {version_spec}")
    exit(1)

version = version_spec[6:]

local_repository_path_repo = local_repository_path_repo()
artifact_ids = artifact_ids()

for artifact_id in artifact_ids:
    if not os.path.exists(local_jar_path(artifact_id)):
        download(artifact_id)

for artifact_id in artifact_ids:
    print(f"[INFO]Uploading {artifact_id}")

run_parallel(__upload, [(agent,) for agent in agents_yaml])
print(f"[INFO]Uploading Hazelcast jars: done")
