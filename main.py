import subprocess
import time

while True:
    subprocess.run(["python3", "sat.py"])
    subprocess.run(["python3", "sun.py"])

    time.sleep(3600)  # 1小时