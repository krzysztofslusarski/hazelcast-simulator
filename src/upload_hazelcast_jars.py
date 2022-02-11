#!/usr/bin/python3
import os.path
import subprocess

import yaml
import sys
from simulator.util import run_parallel, shell
from simulator.hosts import public_ip, ssh_user, ssh_options
from simulator.ssh import SSH


def __upload(agent, artifact_ids, version):
    print(f"[INFO]     {public_ip(agent)} starting")
    ssh = SSH(public_ip(agent), ssh_user(agent), ssh_options(agent))
    ssh.exec("mkdir -p hazelcast-simulator/driver-lib/")
    dest = f"hazelcast-simulator/driver-lib/{version_spec.replace('=', '-')}"
    ssh.exec(f"rm -fr {dest}")
    ssh.exec(f"mkdir -p {dest}")
    for artifact_id in artifact_ids:
        ssh.scp_to_remote(f"{local_jar_path(artifact_id, version)}", f"{dest}")

    print(f"[INFO]     {public_ip(agent)} done")


def local_repository_path_repo():
    cmd = "mvn help:evaluate -Dexpression=settings.localRepository -q -DforceStdout"
    return subprocess.check_output(cmd, shell=True, text=True)


def local_jar_path(artifact_id, version):
    return f"{local_repository_path_repo}/com/hazelcast/{artifact_id}/{version}/{artifact_id}-{version}.jar"


def download(artifact_id, version, repo):
    artifact = f"com.hazelcast:{artifact_id}:{version}"
    cmd = f"mvn org.apache.maven.plugins:maven-dependency-plugin:3.2.0:get -DremoteRepositories={repo} -Dartifact={artifact}"
    print(f"[INFO]{cmd}")
    exitcode = shell(cmd)
    if exitcode != 0:
        print(f"Failed {cmd}, exitcode: {exitcode}")
    path = local_jar_path(artifact_id, version)
    if not os.path.exists(path):
        print(f"[INFO] Could not find {path} in maven repo.")
        exit(1)


def artifact_ids(enterprise, version):
    if version.startswith("3.") or version.startswith("4."):
        if enterprise:
            return ['hazelcast-enterprise-all']
        else:
            return ['hazelcast-all']
    elif version.startswith("5"):
        if enterprise:
            return ['hazelcast-enterprise', 'hazelcast-sql', 'hazelcast-spring']
        else:
            return ['hazelcast', 'hazelcast-sql', 'hazelcast-spring']
    else:
        print(f"[ERROR] Unrecognized version {version}")


def repo(enteprise):
    if not enteprise:
        snapshot_repo = "https://oss.sonatype.org/content/repositories/snapshots"
        release_repo = "https://oss.sonatype.org/content/repositories/releases"
    else:
        snapshot_repo = "https://repository.hazelcast.com/snapshot"
        release_repo = "https://repository.hazelcast.com/release"

    return snapshot_repo if version.endswith("-SNAPSHOT") else release_repo


def enterprise(driver):
    if driver in ['hazelcast3', 'hazelcast4', 'hazelcast5']:
        return False
    elif driver in ['hazelcast-enterprise3', 'hazelcast-enterprise4', 'hazelcast-enterprise5']:
        return True
    else:
        print(f"Unknown driver {driver}")
        exit(1)


def version(version_spec):
    if not version_spec.startswith("maven="):
        print(f"Unhandled version spec: {version_spec}")
        exit(1)

    return version_spec[6:]


agents_yaml = yaml.safe_load(sys.argv[1])
version_spec = sys.argv[2]
driver = sys.argv[3]
enterprise = enterprise(driver)
version = version(version_spec)
repo = repo(enterprise)

print(f"[INFO]Uploading Hazelcast jars")

local_repository_path_repo = local_repository_path_repo()
artifact_ids = artifact_ids(enterprise, version)

for artifact_id in artifact_ids:
    if not os.path.exists(local_jar_path(artifact_id, version)):
        download(artifact_id, version, repo)

for artifact_id in artifact_ids:
    print(f"[INFO]Uploading {artifact_id}")

run_parallel(__upload, [(agent, artifact_ids, version) for agent in agents_yaml])
print(f"[INFO]Uploading Hazelcast jars: done")
