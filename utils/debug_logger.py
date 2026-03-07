# debug_logger.py

import json
import time
import os


class DebugLogger:

    def __init__(self, enabled=True, save_to_file=False, log_file="logs/debug.log"):

        self.enabled = enabled
        self.save_to_file = save_to_file
        self.log_file = log_file

        if save_to_file:
            os.makedirs("logs", exist_ok=True)

    def log(self, title, data=None):

        if not self.enabled:
            return

        timestamp = time.strftime("%H:%M:%S")

        header = f"\n[{timestamp}] ===== {title} ====="

        print(header)

        message = ""

        if data is None:
            message = ""
        elif isinstance(data, (dict, list)):
            message = json.dumps(data, indent=2)
            print(message)
        else:
            message = str(data)
            print(message)

        # optionally save logs to file
        if self.save_to_file:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(header + "\n")
                if message:
                    f.write(message + "\n")