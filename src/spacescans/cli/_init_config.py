# src/spacescans/cli/_init_config.py
"""`spacescans init-config --out <dir>` — copy bundled templates to user dir."""
from __future__ import annotations
import sys
from importlib import resources
from pathlib import Path


def cmd_init_config(args) -> int:
    target = Path(args.out).resolve()
    target.mkdir(parents=True, exist_ok=True)

    # Iterate bundled templates using importlib.resources
    template_root = resources.files("spacescans.resources.configs.templates")
    written = 0
    for category in ("c3", "c4"):
        cat_dir = template_root / category
        if not cat_dir.is_dir():
            continue
        out_cat = target / category
        out_cat.mkdir(exist_ok=True)
        for entry in cat_dir.iterdir():
            if entry.name.endswith(".yaml"):
                out_path = out_cat / entry.name
                out_path.write_bytes(entry.read_bytes())
                written += 1
                print(f"  wrote {out_path}")

    if written == 0:
        print("Error: no templates found in package resources.", file=sys.stderr)
        return 1
    print(f"\n✓ {written} template(s) copied to {target}")
    print("Next: edit the yaml(s) and run `spacescans run <path-to-yaml>`")
    return 0
