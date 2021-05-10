import subprocess
import time
import os

def startReverseProxy(id):
    key_parent_path=os.path.dirname(os.path.realpath(__file__))
    killCommand = "sudo killall autossh"
    procKill = subprocess.Popen(killCommand, stdout=subprocess.PIPE, shell=True)
    time.sleep(2)
    command = 'autossh -f -N -M  0  -o "ServerAliveInterval=180" -o "ServerAliveCountMax=3" -o "PubkeyAuthentication=yes" -o "PasswordAuthentication=no" -o "UserKnownHostsFile=/dev/null" -o "StrictHostKeyChecking=no" -i {:s}/keys/grafana.pem  -R  {:s}:localhost:22 ubuntu@ec2-18-198-146-168.eu-central-1.compute.amazonaws.com'.format(
        key_parent_path,str(1024 + id))
    procAutoSsh = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
    time.sleep(2)
    print(procKill.__dict__)
    print(procAutoSsh.__dict__)
