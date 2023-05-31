#!/usr/bin/env python3
import subprocess
import time
import os
import redis
import logging

#  generate a web control panel to administrate this processes,modularized with login, and to see the output of the scripts
# with csv task file edit in a table to update tasks for the tasks to be executed by the scripts


# Set up logging
logging.basicConfig(filename='process.log', level=logging.INFO)

# Set up Redis
r = redis.Redis(host='localhost', port=6379, db=0)

# Define the scripts to run
scripts = ["script1.py", "script2.py", "script3.py"]



# Check if the scripts have been downloaded before
print("Checking for has req files andSdependencies...")
result = subprocess.run(['python3', 'environment.py'], capture_output=True, text=True)

print("Script first run output:")
print(result.stdout)

print("Script first run errors (if any):")
print(result.stderr)



# Define a function to start a script
def start_script(script):
    logging.info(f"Starting {script}")
    process = subprocess.Popen(["python3", script], stdout=subprocess.PIPE)
    r.set(f"{script}_pid", process.pid)
    return process

# Start all the scripts
processes = {script: start_script(script) for script in scripts}

# Monitor the scripts
while True:
    for script, process in processes.items():
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            logging.error(f"{script} has stopped, restarting it")
            processes[script] = start_script(script)
        if output:
            print(output.strip())
            logging.info(f"{script} output: {output.strip()}")
            r.lpush(f"{script}_output", output.strip())
    time.sleep(5)
