"""Remote execution helper for resource-intensive tasks.

Usage:
    python -m skills.backtest-run.scripts.cloud backtest          # run backtest remotely
    python -m skills.backtest-run.scripts.cloud backtest --help   # show backtest options

Designed for the backtest-run skill. Configure via environment or JSON.
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path


CONFIG_PATHS = [
    Path(".opencode/cloud.json"),
    Path.home() / ".config/opencode/cloud.json",
    Path("cloud.json"),
]


def load_config() -> dict:
    for path in CONFIG_PATHS:
        if path.exists():
            return json.loads(path.read_text("utf-8"))
    return {
        "host": os.environ.get("CLOUD_HOST", ""),
        "user": os.environ.get("CLOUD_USER", ""),
        "key": os.environ.get("CLOUD_KEY", ""),
        "workdir": os.environ.get("CLOUD_WORKDIR", "/home/user/backtests"),
        "python": os.environ.get("CLOUD_PYTHON", "python3"),
    }


def cmd_backtest(args: list[str]) -> None:
    cfg = load_config()
    if not cfg.get("host"):
        print("No cloud host configured. Set CLOUD_HOST env or create .opencode/cloud.json.")
        sys.exit(1)

    safe_args = [shlex.quote(a) for a in args]
    script = [
        "cd", shlex.quote(cfg["workdir"]), "&&",
        shlex.quote(cfg["python"]), "-m", "backtest_runner", *safe_args,
        "--output", f"results/$(date +%Y%m%d_%H%M%S).json",
    ]

    ssh_cmd = ["ssh"]
    if cfg.get("key"):
        ssh_cmd += ["-i", cfg["key"]]
    ssh_cmd += [f"{cfg['user']}@{cfg['host']}", " ".join(script)]

    print(f"remote: {cfg['user']}@{cfg['host']}")
    print(f"running: {' '.join(script)}")
    result = subprocess.run(ssh_cmd)
    sys.exit(result.returncode)


COMMANDS: dict[str, callable] = {
    "backtest": cmd_backtest,
}


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        print(f"Commands: {', '.join(COMMANDS)}")
        sys.exit(0)

    cmd = sys.argv[1]
    if cmd not in COMMANDS:
        print(f"Unknown command: {cmd}")
        print(f"Available: {', '.join(COMMANDS)}")
        sys.exit(1)

    COMMANDS[cmd](sys.argv[2:])


if __name__ == "__main__":
    main()
