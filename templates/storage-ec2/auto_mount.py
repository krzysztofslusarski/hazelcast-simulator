#!/usr/bin/python3

import os
import subprocess

filesystem = "ext3"


def unmounted_partitions():
    cmd = 'lsblk --noheadings --raw -o NAME,MOUNTPOINT'
    lines = subprocess.check_output(cmd, shell=True, text=True).strip().splitlines()

    devices = []
    partitions = []

    for line in lines:
        record = line.split()
        name = record[0]

        if not name.startswith("nvme"):
            continue

        if "p" in name:
            partitions.append(name)
        elif len(record)==1:
            devices.append(name)

    for dev in devices:
        for partition in partitions:
            if partition.startswith(dev):
                devices.remove(dev)
                break

    return devices

def format_and_mount(dev):
    cmd = f'sudo mkfs.{filesystem} /dev/{dev}'
    subprocess.run(cmd, shell=True, text=True)

    cmd = f'sudo mkdir -p /mnt/{dev}'
    subprocess.run(cmd, shell=True, text=True)

    cmd = f'sudo mount -t {filesystem} /dev/{dev} /mnt/{dev}'
    subprocess.run(cmd, shell=True, text=True)

    cmd = f'sudo chown ubuntu /mnt/{dev}'
    subprocess.run(cmd, shell=True, text=True)


unmounted = unmounted_partitions()
print(unmounted)

for dev in unmounted:
    print(dev)
    format_and_mount(dev)
