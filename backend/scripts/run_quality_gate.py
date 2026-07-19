from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path


def run(command: list[str], *, cwd: Path, env: dict[str, str]) -> None:
    print(f"$ {' '.join(command)}", flush=True)
    subprocess.run(command, check=True, cwd=cwd, env=env)


def quality_environment(temp_path: Path) -> dict[str, str]:
    """Keep verification deterministic regardless of deployment overrides."""
    env = {
        name: value
        for name, value in os.environ.items()
        if not name.startswith("TICKFRAME_")
    }
    env.update(
        {
            "COVERAGE_FILE": str(temp_path / ".coverage"),
            "HYPOTHESIS_STORAGE_DIRECTORY": str(temp_path / "hypothesis"),
        }
    )
    return env


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    with tempfile.TemporaryDirectory(prefix="tickframe-quality-") as temp_dir:
        temp_path = Path(temp_dir)
        coverage_json = temp_path / "coverage.json"
        env = quality_environment(temp_path)

        run(
            [
                sys.executable,
                "-m",
                "coverage",
                "run",
                "--source=backend.app,ml.pattern_recognition",
                "-m",
                "unittest",
                "discover",
                "-s",
                "backend/tests",
            ],
            cwd=root,
            env=env,
        )
        run(
            [
                sys.executable,
                "-m",
                "coverage",
                "json",
                "-o",
                str(coverage_json),
            ],
            cwd=root,
            env=env,
        )
        run(
            [
                sys.executable,
                "-m",
                "backend.scripts.check_critical_coverage",
                str(coverage_json),
            ],
            cwd=root,
            env=env,
        )


if __name__ == "__main__":
    main()
