import asyncio
import json
import logging
import math
import os
import subprocess
import sys
import tempfile
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable


class BaseTool(ABC):
    def __init__(self, name: str, description: str, parameters: dict):
        if not isinstance(name, str) or not name.strip() or not isinstance(description, str) or not description.strip():
            raise ValueError("Tool name and description must be nonempty strings")
        self.name = name
        self.description = description
        self.parameters = parameters
        self.logger = logging.getLogger("day20_multiagents.tools")

    def model_schema(self) -> dict:
        return {"type": "function", "function": {
            "name": self.name, "description": self.description, "parameters": self.parameters}}

    def validate_input(self, arguments: dict) -> bool:
        if not isinstance(arguments, dict):
            raise ValueError("Tool arguments must be a dictionary")
        required = set(self.parameters.get("required", []))
        allowed = set(self.parameters.get("properties", {}))
        if required - arguments.keys() or arguments.keys() - allowed:
            raise ValueError(f"Invalid argument keys for {self.name}")
        types = {"string": str, "integer": int, "number": (int, float),
                 "boolean": bool, "array": list, "object": dict}
        for name, value in arguments.items():
            definition = self.parameters["properties"][name]
            expected = definition.get("type")
            if expected in types and (not isinstance(value, types[expected])
                                      or expected in {"integer", "number"} and isinstance(value, bool)):
                raise ValueError(f"Invalid type for {name}")
            if expected in {"integer", "number"} and (not math.isfinite(value)
                    or value < definition.get("minimum", -math.inf)
                    or value > definition.get("maximum", math.inf)):
                raise ValueError(f"Invalid numeric range for {name}")
            if "enum" in definition and value not in definition["enum"]:
                raise ValueError(f"Invalid value for {name}")
        if len(json.dumps(arguments, allow_nan=False).encode("utf-8")) > 131072:
            raise ValueError("Tool arguments exceed the 128 KiB limit")
        return True

    def invoke(self, arguments: dict):
        started = time.monotonic()
        self.logger.info("tool_start tool=%s", self.name)
        try:
            self.validate_input(arguments)
            output = self._execute(arguments)
            json.dumps(output, allow_nan=False)
        except Exception as error:
            self.logger.warning("tool_end tool=%s status=error error_type=%s seconds=%.4f",
                                self.name, type(error).__name__, time.monotonic() - started)
            raise
        self.logger.info("tool_end tool=%s status=success seconds=%.4f",
                         self.name, time.monotonic() - started)
        return output

    @abstractmethod
    def _execute(self, arguments: dict):
        pass

    async def ainvoke(self, arguments: dict):
        return await asyncio.to_thread(self.invoke, arguments)


class Tool(BaseTool):
    def __init__(self, name: str, description: str, parameters: dict, handler: Callable):
        super().__init__(name, description, parameters)
        self.handler = handler

    def _execute(self, arguments: dict):
        return self.handler(**arguments)


def schema(properties: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": properties, "required": required,
            "additionalProperties": False}


def resolve_path(root: Path, filename: str) -> Path:
    if not isinstance(filename, str) or not filename.strip():
        raise ValueError("path must be a nonempty string")
    relative = Path(filename)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("path must stay inside the workspace")
    destination = (root / relative).resolve()
    if not destination.is_relative_to(root.resolve()):
        raise ValueError("path escapes the workspace")
    return destination


class PythonSandbox:
    """Bounded subprocess for trusted Python, not a security boundary."""

    def __init__(self, root: Path, timeout: float = 5, memory_mb: int = 512):
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0 \
                or isinstance(memory_mb, bool) or not isinstance(memory_mb, int) or memory_mb < 64:
            raise ValueError("Invalid execution limits")
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.memory_mb = memory_mb

    def execute_script(self, filename: str) -> dict:
        path = resolve_path(self.root, filename)
        if path.suffix != ".py" or path.stat().st_size > 65536:
            raise ValueError("Expected a Python script at most 64 KiB")
        driver = (f"import runpy, sys\nsys.path.insert(0, {str(path.parent)!r})\n"
                  f"sys.argv = [{str(path)!r}]\nrunpy.run_path({str(path)!r}, run_name='__main__')\n")
        return self.execute(driver)

    def execute(self, code: str) -> dict:
        if sys.platform != "linux":
            raise RuntimeError("Run Python execution tools inside Linux/Docker")
        if not isinstance(code, str) or len(code.encode("utf-8")) > 65536:
            raise ValueError("code must be text at most 64 KiB")
        wrapper = (
            "import resource, sys\n"
            f"resource.setrlimit(resource.RLIMIT_AS, ({self.memory_mb * 1024 * 1024},) * 2)\n"
            f"resource.setrlimit(resource.RLIMIT_CPU, ({max(1, math.ceil(self.timeout))},) * 2)\n"
            "resource.setrlimit(resource.RLIMIT_FSIZE, (65536,) * 2)\n"
            "resource.setrlimit(resource.RLIMIT_NOFILE, (64,) * 2)\n"
            "exec(compile(sys.stdin.read(), '<worker>', 'exec'))\n"
        )
        environment = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": str(self.root),
                       "PYTHONDONTWRITEBYTECODE": "1", "OPENBLAS_NUM_THREADS": "1",
                       "OMP_NUM_THREADS": "1"}
        with tempfile.TemporaryDirectory(prefix="day20-worker-output-") as directory:
            environment["MPLCONFIGDIR"] = str(Path(directory) / "matplotlib")
            with open(Path(directory) / "stdout", "w+b") as stdout, open(Path(directory) / "stderr", "w+b") as stderr:
                process = subprocess.Popen([sys.executable, "-I", "-c", wrapper], cwd=self.root,
                                           env=environment, stdin=subprocess.PIPE,
                                           stdout=stdout, stderr=stderr, start_new_session=True)
                try:
                    process.communicate(code.encode("utf-8"), timeout=self.timeout)
                except subprocess.TimeoutExpired as error:
                    try:
                        os.killpg(process.pid, 9)
                    except ProcessLookupError:
                        pass
                    process.communicate()
                    raise TimeoutError("Python tool exceeded its timeout") from error
                finally:
                    try:
                        os.killpg(process.pid, 9)
                    except ProcessLookupError:
                        pass
                    process.wait()
                stdout.seek(0)
                stderr.seek(0)
                output_bytes = stdout.read(8193)
                error_bytes = stderr.read(8193)
                result = {"exit_code": process.returncode,
                          "stdout": output_bytes[:8192].decode("utf-8", errors="replace"),
                          "stderr": error_bytes[:8192].decode("utf-8", errors="replace"),
                          "stdout_truncated": len(output_bytes) > 8192,
                          "stderr_truncated": len(error_bytes) > 8192}
                if process.returncode != 0:
                    raise RuntimeError(f"Python exited {process.returncode}: {result['stderr']}")
                return result
