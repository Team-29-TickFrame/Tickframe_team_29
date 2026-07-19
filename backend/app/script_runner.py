from __future__ import annotations

import asyncio
import os
import re
import signal
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from .config import env_int


MAX_OUTPUT_BYTES = env_int("TICKFRAME_SCRIPT_MAX_OUTPUT_KB", 64, minimum=1) * 1024
MAX_STORED_RUNS = env_int("TICKFRAME_SCRIPT_MAX_STORED_RUNS", 100, minimum=1)
MAX_ACTIVE_RUNS = env_int("TICKFRAME_SCRIPT_MAX_ACTIVE_RUNS", 10, minimum=1)
DEFAULT_TIMEOUT_SECONDS = env_int(
    "TICKFRAME_SCRIPT_DEFAULT_TIMEOUT_SECONDS", 1800, minimum=1
)
ML_TIMEOUT_SECONDS = env_int("TICKFRAME_SCRIPT_ML_TIMEOUT_SECONDS", 7200, minimum=1)
QUALITY_TIMEOUT_SECONDS = env_int(
    "TICKFRAME_SCRIPT_QUALITY_TIMEOUT_SECONDS", 600, minimum=1
)
if MAX_ACTIVE_RUNS > MAX_STORED_RUNS:
    raise ValueError(
        "TICKFRAME_SCRIPT_MAX_ACTIVE_RUNS must not exceed "
        "TICKFRAME_SCRIPT_MAX_STORED_RUNS"
    )
INSTRUMENT_RE = re.compile(r"^[A-Z0-9-]{2,24}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def script_access_allowed(email: str, configured: Optional[str] = None) -> bool:
    raw_value = (
        os.getenv("TICKFRAME_SCRIPT_RUNNER_EMAILS", "")
        if configured is None
        else configured
    )
    normalized = raw_value.replace(";", ",").replace("\n", ",")
    allowed_emails = {
        item.strip().lower() for item in normalized.split(",") if item.strip()
    }
    return email.strip().lower() in allowed_emails


@dataclass(frozen=True)
class Parameter:
    name: str
    label: str
    kind: str
    default: Any
    flag: str
    options: tuple[str, ...] = ()
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    placeholder: Optional[str] = None

    def to_api(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "name": self.name,
            "label": self.label,
            "kind": self.kind,
            "default": self.default,
        }
        if self.options:
            result["options"] = list(self.options)
        if self.minimum is not None:
            result["minimum"] = self.minimum
        if self.maximum is not None:
            result["maximum"] = self.maximum
        if self.placeholder:
            result["placeholder"] = self.placeholder
        return result


@dataclass(frozen=True)
class ScriptDefinition:
    id: str
    name: str
    description: str
    module: str
    category: str
    parameters: tuple[Parameter, ...] = ()
    fixed_args: tuple[str, ...] = ()
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS

    def to_api(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "parameters": [parameter.to_api() for parameter in self.parameters],
        }


BACKFILL_PARAMETERS = (
    Parameter("days", "Lookback days", "number", 1, "--days", minimum=1, maximum=3650),
    Parameter(
        "timeframe", "Timeframe", "select", "1m", "--timeframe", options=("1m", "1s")
    ),
    Parameter(
        "exchange",
        "Exchange",
        "select",
        "all",
        "--exchange",
        options=("all", "binance", "bybit"),
    ),
    Parameter(
        "instrument",
        "Instrument",
        "text",
        "",
        "--instrument",
        placeholder="BTC-USDT (optional)",
    ),
    Parameter("dryRun", "Dry run", "boolean", True, "--dry-run"),
)


SCRIPTS = {
    definition.id: definition
    for definition in (
        ScriptDefinition(
            "backfill-candles",
            "Backfill candles",
            "Load public OHLCV candles into historical storage.",
            "backend.scripts.backfill_candles",
            "Data",
            BACKFILL_PARAMETERS,
        ),
        ScriptDefinition(
            "parallel-history",
            "Parallel history backfill",
            "Backfill multiple markets concurrently.",
            "backend.scripts.history",
            "Data",
            BACKFILL_PARAMETERS
            + (
                Parameter(
                    "binanceConcurrency",
                    "Binance workers",
                    "number",
                    4,
                    "--binance-concurrency",
                    minimum=1,
                    maximum=20,
                ),
                Parameter(
                    "bybitConcurrency",
                    "Bybit workers",
                    "number",
                    2,
                    "--bybit-concurrency",
                    minimum=1,
                    maximum=20,
                ),
            ),
        ),
        ScriptDefinition(
            "prepare-ml-dataset",
            "Prepare ML dataset",
            "Download or rebuild the maintained Binance pattern dataset.",
            "ml.pattern_recognition.prepare_binance_dataset",
            "Machine learning",
            (
                Parameter(
                    "endDate",
                    "End date",
                    "text",
                    "",
                    "--end-date",
                    placeholder="YYYY-MM-DD (optional)",
                ),
                Parameter(
                    "skipDownload", "Skip download", "boolean", False, "--skip-download"
                ),
                Parameter(
                    "offlineNormalized",
                    "Offline normalized data",
                    "boolean",
                    False,
                    "--offline-normalized",
                ),
                Parameter(
                    "rebuildNormalized",
                    "Rebuild normalized data",
                    "boolean",
                    False,
                    "--rebuild-normalized",
                ),
            ),
            ("--config", "ml/pattern_recognition/config.json"),
            ML_TIMEOUT_SECONDS,
        ),
        ScriptDefinition(
            "train-pattern-model",
            "Train pattern model",
            "Train the maintained chart-pattern baseline from prepared data.",
            "ml.pattern_recognition.train_baseline",
            "Machine learning",
            (
                Parameter(
                    "timeframe",
                    "Timeframe",
                    "select",
                    "1m",
                    "--timeframe",
                    options=("1m", "5m", "15m", "1h", "1d"),
                ),
                Parameter(
                    "modelType",
                    "Model",
                    "select",
                    "auto",
                    "--model-type",
                    options=(
                        "auto",
                        "lightgbm",
                        "hist_gradient_boosting",
                        "gaussian_nb",
                    ),
                ),
                Parameter("smoke", "Fast smoke run", "boolean", True, "--smoke"),
            ),
            ("--config", "ml/pattern_recognition/config.json"),
            ML_TIMEOUT_SECONDS,
        ),
        ScriptDefinition(
            "check-critical-coverage",
            "Check critical coverage",
            "Run the backend tests and validate critical-module coverage.",
            "backend.scripts.run_quality_gate",
            "Quality",
            timeout_seconds=QUALITY_TIMEOUT_SECONDS,
        ),
    )
}


@dataclass
class ScriptRun:
    id: str
    script_id: str
    owner_id: str
    command: list[str]
    status: str = "queued"
    output: str = ""
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    exit_code: Optional[int] = None

    def to_api(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "scriptId": self.script_id,
            "status": self.status,
            "output": self.output,
            "startedAt": self.started_at,
            "finishedAt": self.finished_at,
            "exitCode": self.exit_code,
        }


def build_command(definition: ScriptDefinition, values: Dict[str, Any]) -> list[str]:
    allowed_names = {parameter.name for parameter in definition.parameters}
    unknown = set(values) - allowed_names
    if unknown:
        raise ValueError(f"Unknown parameters: {', '.join(sorted(unknown))}")

    command = [sys.executable, "-m", definition.module, *definition.fixed_args]
    for parameter in definition.parameters:
        value = values.get(parameter.name, parameter.default)
        if parameter.kind == "boolean":
            if not isinstance(value, bool):
                raise ValueError(f"{parameter.label} must be a boolean")
            if value:
                command.append(parameter.flag)
            continue
        if parameter.kind == "number":
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{parameter.label} must be a number")
            if parameter.minimum is not None and value < parameter.minimum:
                raise ValueError(f"{parameter.label} is below the minimum")
            if parameter.maximum is not None and value > parameter.maximum:
                raise ValueError(f"{parameter.label} is above the maximum")
        elif parameter.kind == "select" and value not in parameter.options:
            raise ValueError(f"Invalid value for {parameter.label}")
        elif parameter.kind == "text":
            if not isinstance(value, str):
                raise ValueError(f"{parameter.label} must be text")
            value = value.strip()
            if (
                parameter.name == "instrument"
                and value
                and not INSTRUMENT_RE.fullmatch(value)
            ):
                raise ValueError(
                    "Instrument must contain only uppercase letters, numbers, or dashes"
                )
            if parameter.name == "endDate" and value and not DATE_RE.fullmatch(value):
                raise ValueError("End date must use YYYY-MM-DD")
        if value != "":
            command.extend((parameter.flag, str(value)))
    return command


class ScriptRunner:
    def __init__(self) -> None:
        self.runs: Dict[str, ScriptRun] = {}
        self._lock = asyncio.Lock()
        self._tasks: set[asyncio.Task[None]] = set()
        self.root = Path(__file__).resolve().parents[2]

    def catalog(self) -> list[Dict[str, Any]]:
        return [definition.to_api() for definition in SCRIPTS.values()]

    async def start(
        self,
        script_id: str,
        values: Dict[str, Any],
        owner_id: str,
    ) -> ScriptRun:
        definition = SCRIPTS.get(script_id)
        if definition is None:
            raise KeyError(script_id)
        command = build_command(definition, values)
        self._prune_runs()
        active_runs = sum(
            run.status in {"queued", "running"} for run in self.runs.values()
        )
        if active_runs >= MAX_ACTIVE_RUNS:
            raise RuntimeError("Too many active script runs; try again later")
        if len(self.runs) >= MAX_STORED_RUNS:
            raise RuntimeError("Script run history is full; try again later")
        run = ScriptRun(uuid.uuid4().hex, script_id, owner_id, command)
        self.runs[run.id] = run
        task = asyncio.create_task(self._execute(run, definition.timeout_seconds))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return run

    def _prune_runs(self) -> None:
        for run_id, run in list(self.runs.items()):
            if len(self.runs) < MAX_STORED_RUNS:
                break
            if run.status not in {"queued", "running"}:
                self.runs.pop(run_id, None)

    async def shutdown(self) -> None:
        tasks = tuple(self._tasks)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _execute(self, run: ScriptRun, timeout_seconds: int) -> None:
        async with self._lock:
            run.status = "running"
            run.started_at = datetime.now(timezone.utc).isoformat()
            process: Optional[asyncio.subprocess.Process] = None
            try:
                process = await asyncio.create_subprocess_exec(
                    *run.command,
                    cwd=self.root,
                    env={**os.environ, "PYTHONUNBUFFERED": "1"},
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                    start_new_session=True,
                )
                await asyncio.wait_for(
                    self._capture_output(process, run), timeout_seconds
                )
                run.exit_code = process.returncode
                run.status = "succeeded" if process.returncode == 0 else "failed"
            except asyncio.TimeoutError:
                if process is not None:
                    await self._stop_process(process)
                self._append_output(
                    run,
                    f"\nScript exceeded its {timeout_seconds}-second timeout.\n",
                )
                run.status = "failed"
                run.exit_code = -1
            except asyncio.CancelledError:
                if process is not None:
                    await self._stop_process(process)
                self._append_output(
                    run,
                    "\nScript stopped because the service is shutting down.\n",
                )
                run.status = "cancelled"
                run.exit_code = -1
                raise
            except Exception as error:
                self._append_output(run, f"\n{error}\n")
                run.status = "failed"
                run.exit_code = -1
            finally:
                run.finished_at = datetime.now(timezone.utc).isoformat()

    async def _capture_output(
        self,
        process: asyncio.subprocess.Process,
        run: ScriptRun,
    ) -> None:
        if process.stdout is None:
            await process.wait()
            return
        while True:
            chunk = await process.stdout.read(4096)
            if not chunk:
                break
            self._append_output(run, chunk.decode("utf-8", errors="replace"))
        await process.wait()

    @staticmethod
    def _append_output(run: ScriptRun, value: str) -> None:
        run.output += value
        if len(run.output) > MAX_OUTPUT_BYTES:
            run.output = run.output[-MAX_OUTPUT_BYTES:]

    @staticmethod
    async def _stop_process(process: asyncio.subprocess.Process) -> None:
        if process.returncode is not None:
            return
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        try:
            await asyncio.wait_for(process.wait(), timeout=5)
        except asyncio.TimeoutError:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            await process.wait()

    def get(self, run_id: str) -> Optional[ScriptRun]:
        return self.runs.get(run_id)


script_runner = ScriptRunner()
