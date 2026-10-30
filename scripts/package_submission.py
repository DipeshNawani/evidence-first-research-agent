"""Package only explicit submission paths; never include .env or local run state."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    "README.md",
    "EVALUATION.md",
    "SUBMISSION.md",
    "VERIFICATION.md",
    "pyproject.toml",
    "uv.lock",
    "pyrightconfig.json",
    "Makefile",
    ".env.example",
    ".gitignore",
]
DIRECTORIES = ["src", "tests", "eval", "samples", "scripts", "docs"]


def submission_files() -> list[Path]:
    selected = [ROOT / name for name in FILES if (ROOT / name).is_file()]
    for name in DIRECTORIES:
        selected.extend(
            path
            for path in (ROOT / name).rglob("*")
            if path.is_file()
            and "__pycache__" not in path.parts
            and path.suffix not in {".pyc", ".pyo"}
        )
    return sorted(set(selected))


def package() -> Path:
    destination = ROOT / "dist/research-agent-submission.zip"
    destination.parent.mkdir(exist_ok=True)
    with ZipFile(destination, "w", ZIP_DEFLATED) as archive:
        for path in submission_files():
            archive.write(path, path.relative_to(ROOT))
    print(f"Created {destination} ({destination.stat().st_size:,} bytes)")
    return destination


if __name__ == "__main__":
    package()
