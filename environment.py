import os
import requests
from urllib.parse import urljoin
import redis
import subprocess

# download files and Install packages from requirements.txt
########################################
#
# Set up Redis connection
r = redis.Redis(host='localhost', port=6379, db=0)

# Base URL where scripts are located
base_url = 'https://i.markos.ninja'

# List of scripts names
scripts_names = ['script_1.py', 'script_2.py', 'script_3.py', 'script_4.py']

# Requirements file name
requirements_file = 'requirements.txt'

def install_requirements():
    print(f'Installing packages from {requirements_file}...')
    subprocess.check_call(['python3', '-m', 'pip', 'install', '-r', requirements_file])
    print(f'Installation complete.')

def download_script(script_name):
    print(f'Downloading {script_name}...')
    script_url = urljoin(base_url, script_name)
    response = requests.get(script_url)
    with open(script_name, 'wb') as f:
        f.write(response.content)
    print(f'Download complete for {script_name}.')

def set_permissions(script_name):
    print(f'Setting execute permissions for {script_name}...')
    os.chmod(script_name, 0o755) # This will set the execute permissions
    print(f'Execute permissions set for {script_name}.')

def main():

    should_exit = False
    # Check if the scripts have been downloaded before
    if not r.get('scripts_downloaded'):
        for script_name in scripts_names:
            # Check if the script file exists and has execute permissions
            if not os.path.exists(script_name) or not os.access(script_name, os.X_OK):
                if os.path.exists(script_name):
                    print(f'{script_name} exists but does not have execute permissions.')
                else:
                    download_script(script_name)
                set_permissions(script_name)
                should_exit = True
        # Set the Redis variable to skip this initialization next time
        r.set('scripts_downloaded', 1)
        
    if os.path.exists(requirements_file):
        install_requirements()
    else:
        download_script(requirements_file)
        install_requirements()

    if should_exit:
        print("Scripts downloaded and permissions set. Exiting to allow for restart.")
        exit(0)
    else:
        print("Scripts have been downloaded before and have correct permissions, skipping download.")

if __name__ == "__main__":
    main()
