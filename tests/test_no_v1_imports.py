# tests/test_no_v1_imports.py
"""Static check: src/spacescans/ must not import from common.xxx or common_v2.xxx."""
import re
from pathlib import Path


def test_no_legacy_common_imports():
    pkg_root = Path(__file__).parent.parent / "src" / "spacescans"
    # Catch all forms: `from common.X`, `from common import X`, `import common`, `import common.X`
    pattern_common = re.compile(r"^\s*(from\s+common(\.|\s+import)|import\s+common(\.|\s|$))")
    pattern_v2 = re.compile(r"^\s*(from\s+common_v2(\.|\s+import)|import\s+common_v2(\.|\s|$))")

    violations = []
    for py in pkg_root.rglob("*.py"):
        text = py.read_text()
        for n, line in enumerate(text.splitlines(), 1):
            if pattern_common.search(line) or pattern_v2.search(line):
                violations.append(f"{py.relative_to(pkg_root)}:{n}: {line.strip()}")

    assert not violations, "Legacy imports found:\n" + "\n".join(violations)
