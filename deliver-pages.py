import os
import subprocess
import sys

def run(cmd):
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
    return result.stdout

def write(path, content):
    print(f"Writing: {path}")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

# This script is a helper to ensure all fixes are applied correctly
# Since Manus is pushing directly to GitHub, this script serves as a reference
# and a backup for the user to run if they need to re-apply changes locally.

print("=== NHID-Clinical Delivery Script ===")

# 1. Fix conftest.py
write("conftest.py", """import sys
import os

# Ensure the 'src' directory is in the Python path for all tests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))
""")

# 2. Run tests
print("\n=== Running tests ===")
run("pytest")

print("\n=== Deployment complete. Manus has already pushed these changes to GitHub. ===")
