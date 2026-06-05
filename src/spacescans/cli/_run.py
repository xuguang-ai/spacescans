"""`spacescans run` — execute a pipeline config."""
from __future__ import annotations
import sys
from pathlib import Path
from spacescans.pipeline.runner import Pipeline


def cmd_run(args) -> int:
    cfg = Path(args.config).resolve()
    if not cfg.is_file():
        print(f"Error: config not found: {cfg}", file=sys.stderr)
        return 2

    try:
        pipeline = Pipeline.from_config(
            cfg,
            data_dir=args.data_dir,
            output_dir=args.output_dir,
        )
        result = pipeline.run()
        print(f"Output: {result}")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
