import re
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
ENV_ASSIGNMENT_RE = re.compile(r"^\s*#?\s*([A-Z][A-Z0-9_]*)=", re.MULTILINE)
COMPOSE_VARIABLE_RE = re.compile(r"\$\{([A-Z][A-Z0-9_]*)")
TICKFRAME_VARIABLE_RE = re.compile(r"\bTICKFRAME_[A-Z0-9_]+\b")


class EnvironmentContractTests(unittest.TestCase):
    def test_env_example_covers_compose_and_backend_variables(self) -> None:
        env_example = ROOT / ".env.example"
        compose_file = ROOT / "docker-compose.yml"
        if not env_example.exists() or not compose_file.exists():
            self.skipTest(
                "repository deployment files are not part of the runtime image"
            )

        env_names = set(
            ENV_ASSIGNMENT_RE.findall(env_example.read_text(encoding="utf-8"))
        )
        compose_names = set(
            COMPOSE_VARIABLE_RE.findall(compose_file.read_text(encoding="utf-8"))
        )
        backend_names: set[str] = set()
        for directory in (ROOT / "backend" / "app", ROOT / "backend" / "scripts"):
            for path in directory.rglob("*.py"):
                backend_names.update(
                    TICKFRAME_VARIABLE_RE.findall(path.read_text(encoding="utf-8"))
                )

        self.assertEqual(compose_names - env_names, set())
        self.assertEqual(backend_names - env_names, set())


if __name__ == "__main__":
    unittest.main()
