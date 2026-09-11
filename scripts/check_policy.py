"""Reject yfinance in production Python source, including literal dynamic imports."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    violations: list[str] = []
    for directory in (ROOT / "apps/api", ROOT / "packages/ingest"):
        for path in directory.rglob("*.py"):
            tree = ast.parse(path.read_text(), filename=str(path))
            dynamic_names = {"__import__"}
            for binding in ast.walk(tree):
                if isinstance(binding, ast.ImportFrom):
                    expected = {"importlib": "import_module", "builtins": "__import__"}
                    for alias in binding.names:
                        if alias.name == expected.get(binding.module or ""):
                            dynamic_names.add(alias.asname or alias.name)
            for node in ast.walk(tree):
                names: list[str] = []
                if isinstance(node, ast.Import):
                    names.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names.append(node.module)
                elif isinstance(node, ast.Call) and node.args:
                    function = node.func
                    dynamic = (isinstance(function, ast.Name) and function.id in dynamic_names) or (
                        isinstance(function, ast.Attribute) and function.attr == "import_module"
                    )
                    argument = node.args[0]
                    if dynamic and isinstance(argument, ast.Constant):
                        if isinstance(argument.value, str):
                            names.append(argument.value)
                if any(name.split(".")[0] == "yfinance" for name in names):
                    violations.append(
                        f"{path.relative_to(ROOT)}:{getattr(node, 'lineno', 0)}: forbidden yfinance"
                    )
    if violations:
        print("\n".join(violations))
        return 1
    print("Production import policy passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
