"""
The Python package and the VS Code extension are released together from one
git tag (vX.Y.Z), so their versions must always match.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_package_and_extension_versions_match():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    python_version = re.search(r'^version = "([^"]+)"', pyproject, re.MULTILINE).group(1)
    extension = json.loads((ROOT / "editors" / "vscode" / "package.json").read_text(encoding="utf-8"))
    assert python_version == extension["version"]
