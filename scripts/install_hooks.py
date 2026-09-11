"""Install the checked-in hook only into this repository's private Git directory."""

import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    top = subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"], cwd=ROOT, text=True
    ).strip()
    if Path(top).resolve() != ROOT:
        raise SystemExit("Refusing to install hooks in an ancestor repository.")
    configured = subprocess.run(
        ["git", "config", "--get", "core.hooksPath"], cwd=ROOT, text=True, capture_output=True
    )
    if configured.returncode == 0:
        raise SystemExit("A custom core.hooksPath exists; inspect it before installing this hook.")
    destination = Path(
        subprocess.check_output(
            ["git", "rev-parse", "--path-format=absolute", "--git-path", "hooks/pre-commit"],
            cwd=ROOT,
            text=True,
        ).strip()
    )
    source = ROOT / "scripts/pre-commit"
    if destination.exists() and destination.read_bytes() != source.read_bytes():
        raise SystemExit("A different pre-commit hook exists; inspect before replacing it.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    destination.chmod(0o755)
    print("Installed repository-local pre-commit hook.")


if __name__ == "__main__":
    main()
