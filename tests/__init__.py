import subprocess

__version__ = subprocess.run(
    ["pyproject-info", "project.version"], capture_output=True, text=True
).stdout.rstrip().replace("\"","")
