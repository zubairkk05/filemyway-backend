"""CLI wrapper around :func:`app.workers.python_worker.run_job`.

Kept for the subprocess worker mode (``python -m app.workers.main --tool ...``).
"""

import json
import sys

from app.workers.python_worker import run_job


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="FileMyWay PDF Tools Worker")
    parser.add_argument("--tool", required=True, help="Tool slug")
    parser.add_argument("--job-dir", required=True, help="Absolute job directory")
    parser.add_argument("--inputs", required=True, help="JSON list of inputs")
    parser.add_argument("--options", default="{}", help="JSON options object")
    args = parser.parse_args()

    inputs = json.loads(args.inputs)
    options = json.loads(args.options) if args.options else {}
    result = run_job(args.tool, args.job_dir, inputs, options)
    if not result.get("ok"):
        sys.exit(1)


if __name__ == "__main__":
    main()
