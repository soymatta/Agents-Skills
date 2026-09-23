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
        print(
            "No cloud host configured. Set CLOUD_HOST env or create "
            ".opencode/cloud.json. Falling back to local execution."
        )
        # Graceful fallback: run the backtest locally instead of hard-failing.
        local_cmd = ["python", "-m", "skills.backtest-run.scripts.backtest_runner", *args]
        print(f"running locally: {' '.join(local_cmd)}")
        result = subprocess.run(local_cmd)
        sys.exit(result.returncode)

    if not cfg.get("python"):
        cfg["python"] = "python3"

    safe_args = [shlex.quote(a) for a in args]
    # `backtest_runner` must exist on the remote (installed or on PYTHONPATH).
    # The skill's local runner is `scripts/backtest_runner.py`; copy it over if
    # the remote does not already provide the module.
    runner_remote = "backtest_runner.py"
    if Path(__file__).with_name("backtest_runner.py").exists():
        remote = f"{cfg['user']}@{cfg['host']}"
        copy = subprocess.run(["scp", "-i", cfg["key"]] if cfg.get("key") else ["scp"],
                              [str(Path(__file__).with_name("backtest_runner.py")),
                               f"{remote}:{shlex.quote(cfg['workdir'])}/{runner_remote}"])
        if copy.returncode != 0:
            print("warning: could not copy backtest_runner.py to remote; "
                  "assuming it is already installed there")

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
