# SHOULD FAIL: imports subprocess — in the Python forbidden modules default set
import subprocess
import os

def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout
