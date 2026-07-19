import asyncio
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from backend.app.script_runner import (
    MAX_ACTIVE_RUNS,
    MAX_STORED_RUNS,
    SCRIPTS,
    ScriptRun,
    ScriptRunner,
    build_command,
    script_access_allowed,
)
from backend.scripts.run_quality_gate import quality_environment


class ScriptRunnerCommandTests(unittest.TestCase):
    def test_script_access_uses_case_insensitive_email_allowlist(self) -> None:
        configured = "admin@example.com, Ops@Example.com"
        self.assertTrue(script_access_allowed("ops@example.com", configured))
        self.assertFalse(script_access_allowed("user@example.com", configured))
        self.assertFalse(script_access_allowed("admin@example.com", ""))

    def test_catalog_contains_only_maintained_scripts(self) -> None:
        self.assertEqual(
            set(SCRIPTS),
            {
                "backfill-candles",
                "parallel-history",
                "prepare-ml-dataset",
                "train-pattern-model",
                "check-critical-coverage",
            },
        )

    def test_backfill_arguments_are_validated_and_encoded(self) -> None:
        command = build_command(
            SCRIPTS["backfill-candles"],
            {
                "days": 7,
                "timeframe": "1m",
                "exchange": "binance",
                "instrument": "BTC-USDT",
                "dryRun": True,
            },
        )
        self.assertIn("backend.scripts.backfill_candles", command)
        self.assertIn("BTC-USDT", command)
        self.assertIn("--dry-run", command)

    def test_unknown_or_shell_like_parameters_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            build_command(SCRIPTS["backfill-candles"], {"command": "rm -rf /"})
        with self.assertRaises(ValueError):
            build_command(
                SCRIPTS["backfill-candles"],
                {"instrument": "BTC-USDT; touch /tmp/nope"},
            )

    def test_number_ranges_are_enforced(self) -> None:
        with self.assertRaises(ValueError):
            build_command(SCRIPTS["backfill-candles"], {"days": 100_000})

    def test_quality_gate_runs_self_contained_wrapper(self) -> None:
        command = build_command(SCRIPTS["check-critical-coverage"], {})
        self.assertIn("backend.scripts.run_quality_gate", command)
        self.assertNotIn("coverage.json", command)

    def test_quality_gate_ignores_deployment_overrides(self) -> None:
        with patch.dict(
            os.environ,
            {
                "DATABASE_URL": "postgresql://example/test",
                "TICKFRAME_ENABLED_INSTRUMENTS": "BTC-USDT",
            },
            clear=True,
        ):
            env = quality_environment(Path("/tmp/tickframe-quality"))

        self.assertEqual(env["DATABASE_URL"], "postgresql://example/test")
        self.assertNotIn("TICKFRAME_ENABLED_INSTRUMENTS", env)
        self.assertEqual(env["COVERAGE_FILE"], "/tmp/tickframe-quality/.coverage")

    def test_script_runner_limits_can_be_overridden_from_env(self) -> None:
        env = {
            **os.environ,
            "TICKFRAME_SCRIPT_MAX_ACTIVE_RUNS": "2",
            "TICKFRAME_SCRIPT_MAX_STORED_RUNS": "7",
            "TICKFRAME_SCRIPT_MAX_OUTPUT_KB": "8",
            "TICKFRAME_SCRIPT_DEFAULT_TIMEOUT_SECONDS": "11",
            "TICKFRAME_SCRIPT_ML_TIMEOUT_SECONDS": "12",
            "TICKFRAME_SCRIPT_QUALITY_TIMEOUT_SECONDS": "13",
        }
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "from backend.app.script_runner import "
                    "DEFAULT_TIMEOUT_SECONDS, MAX_ACTIVE_RUNS, MAX_OUTPUT_BYTES, "
                    "MAX_STORED_RUNS, ML_TIMEOUT_SECONDS, QUALITY_TIMEOUT_SECONDS; "
                    "print(MAX_ACTIVE_RUNS, MAX_STORED_RUNS, MAX_OUTPUT_BYTES, "
                    "DEFAULT_TIMEOUT_SECONDS, ML_TIMEOUT_SECONDS, "
                    "QUALITY_TIMEOUT_SECONDS)"
                ),
            ],
            check=True,
            capture_output=True,
            env=env,
            text=True,
        )

        self.assertEqual(result.stdout.strip(), "2 7 8192 11 12 13")


class ScriptRunnerLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_active_run_queue_is_bounded(self) -> None:
        runner = ScriptRunner()
        for index in range(MAX_ACTIVE_RUNS):
            runner.runs[str(index)] = ScriptRun(
                id=str(index),
                script_id="backfill-candles",
                owner_id="owner",
                command=[],
                status="queued",
            )

        with self.assertRaisesRegex(RuntimeError, "Too many active"):
            await runner.start("backfill-candles", {}, "owner")

    async def test_shutdown_cancels_tracked_tasks(self) -> None:
        runner = ScriptRunner()
        waiting = asyncio.Event()

        async def wait_forever(run: ScriptRun, timeout_seconds: int) -> None:
            del run, timeout_seconds
            await waiting.wait()

        with patch.object(runner, "_execute", side_effect=wait_forever):
            run = await runner.start("backfill-candles", {}, "owner")
            await asyncio.sleep(0)
            self.assertEqual(run.status, "queued")
            self.assertEqual(len(runner._tasks), 1)
            await runner.shutdown()

        self.assertFalse(runner._tasks)

    async def test_completed_runs_are_pruned_at_capacity(self) -> None:
        runner = ScriptRunner()
        for index in range(MAX_STORED_RUNS):
            runner.runs[str(index)] = ScriptRun(
                id=str(index),
                script_id="backfill-candles",
                owner_id="owner",
                command=[],
                status="succeeded",
            )

        waiting = asyncio.Event()

        async def wait_forever(run: ScriptRun, timeout_seconds: int) -> None:
            del run, timeout_seconds
            await waiting.wait()

        with patch.object(runner, "_execute", side_effect=wait_forever):
            run = await runner.start("backfill-candles", {}, "owner")
            self.assertIn(run.id, runner.runs)
            self.assertEqual(len(runner.runs), MAX_STORED_RUNS)
            await runner.shutdown()


if __name__ == "__main__":
    unittest.main()
