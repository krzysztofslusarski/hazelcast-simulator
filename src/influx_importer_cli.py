#!/usr/bin/python3
import os.path
import argparse
import subprocess
import time
from pathlib import Path

from simulator.log import info, log_header
from simulator.util import exit_with_error, load_yaml_file


class InfluxImporterCli:

    def __init__(self):
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument("directory", help="The directory to scan recursively", nargs=1)
        parser.add_argument("--database", help="The name of database", default="mydb")
        parser.add_argument("--port", help="The port", default="8086")
        parser.add_argument("--host", help="The host", default="localhost")
        parser.add_argument("-v", "--verbose", help="Verbose output", action='store_true')

        args = parser.parse_args()

        log_header("Importing results into Influxdb")

        database = args.database
        host = args.host
        port = args.port
        verbose = args.verbose
        directory = args.directory[0]
        if not os.path.exists(directory):
            exit_with_error(f"Directory [{directory}] does not exist.")

        info(f"Database: {database}")
        info(f"Host: {host}")
        info(f"Port: {port}")
        info(f"Directory: [{directory}]")

        file_count = 0
        measurement_count = 0
        for path in Path(directory).rglob('results.yaml'):
            file_count += 1
            results = load_yaml_file(path)
            info(f"Exporting [{path}]")
            for test_name, map in results.items():
                tags = map['tags']
                measurements = map['measurements']
                tag_string = ""
                for tag_name, tag_value in tags.items():
                    if tag_name != "":
                        tag_string = f"{tag_name}={tag_value}"
                    else:
                        tag_string = f"{tag_string},{tag_name}={tag_value}"
                for key, value in measurements.items():
                    measurement_count += 1
                    cmd = f"curl -i --show-error  --silent --fail -XPOST 'http://{host}:{port}/write?db={database}' --data-binary '{key},{tag_string} value={value} {time.time_ns()}'"
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    if result.returncode != 0 or verbose:
                        print(f"return code:{result.returncode}")
                        print(result.stdout)
                        print(result.stderr)
                    if result.returncode != 0:
                        exit_with_error("Failed to import")

        info(f"Exporting complete")
        info(f"Files imported {file_count}")
        info(f"Measurements imported {measurement_count}")

        log_header("Importing results into Influxdb: Done")


if __name__ == '__main__':
    InfluxImporterCli()
