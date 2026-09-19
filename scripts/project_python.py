"""Launch this project's Python with its own validated editable pointer visible.

Some macOS/iCloud environments mark generated .pth files UF_HIDDEN. Python
correctly ignores hidden .pth files. Restore only the pointer generated for this
project after checking that its single path is our strict editable build tree;
never execute or unhide arbitrary .pth files or modify the Python installation.
"""

import os
import stat
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv/bin/python"


def main() -> None:
    if hasattr(os, "chflags"):
        sites = ROOT / ".venv/lib"
        for pointer in sites.glob(
            "python*/site-packages/__editable__.equity_valuation_workbench-*.pth"
        ):
            lines = pointer.read_text().splitlines()
            if len(lines) != 1:
                raise RuntimeError("Unexpected project editable pointer")
            target = Path(lines[0])
            if (
                not target.is_absolute()
                or target.parent != ROOT / "build"
                or not target.name.startswith("__editable__.equity_valuation_workbench-")
                or not target.is_dir()
                or pointer.is_symlink()
            ):
                raise RuntimeError("Project editable pointer escapes its generated build")
            flags = pointer.stat().st_flags
            if flags & stat.UF_HIDDEN:
                os.chflags(pointer, flags & ~stat.UF_HIDDEN)
    os.execv(str(PYTHON), [str(PYTHON), *sys.argv[1:]])


if __name__ == "__main__":
    main()
