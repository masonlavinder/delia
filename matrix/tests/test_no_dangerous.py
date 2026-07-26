"""Crude but effective: assert dangerous constructs appear nowhere in the package.
Looks blunt; will catch a real regression eventually."""
import pathlib

SRC = pathlib.Path(__file__).resolve().parents[1] / "src" / "panel"

FORBIDDEN = [
    "subprocess",
    "os.system",
    "shell=True",
    "eval(",
    "exec(",
    "pickle",
    "yaml.load",
]


def test_no_dangerous_constructs():
    offenders = []
    for path in SRC.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in FORBIDDEN:
            if token in text:
                offenders.append(f"{path.relative_to(SRC)}: {token!r}")
    assert not offenders, "dangerous constructs found: " + "; ".join(offenders)
