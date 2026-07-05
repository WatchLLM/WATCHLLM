# This is fine
import os
import sys

# These are violations
import child_process
from child_process import exec
from vm import Script

# This is a violation
__import__('child_process')
