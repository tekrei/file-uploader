import subprocess


__version__ = subprocess.run(
    ["poetry", "version", "-s"], capture_output=True, text=True
).stdout.rstrip()
