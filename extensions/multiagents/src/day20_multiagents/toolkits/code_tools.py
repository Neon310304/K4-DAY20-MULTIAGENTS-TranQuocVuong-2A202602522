from pathlib import Path

from ..tools import BaseTool, PythonSandbox, resolve_path, schema


def bounded_text(text: str) -> None:
    if not isinstance(text, str) or len(text.encode("utf-8")) > 65536:
        raise ValueError("text must be at most 64 KiB")


class PythonREPLTool(BaseTool):
    def __init__(self, workspace: Path, timeout: float = 5, memory_mb: int = 512):
        self.sandbox = PythonSandbox(workspace, timeout=timeout, memory_mb=memory_mb)
        super().__init__("python_repl", "Execute trusted Python in a bounded Linux subprocess, without inherited secrets.",
                         schema({"code": {"type": "string"}}, ["code"]))

    def validate_input(self, arguments: dict) -> bool:
        super().validate_input(arguments)
        bounded_text(arguments["code"])
        return True

    def _execute(self, arguments: dict) -> dict:
        return self.sandbox.execute(arguments["code"])


class CreateFileTool(BaseTool):
    def __init__(self, workspace: Path):
        self.workspace = Path(workspace).resolve()
        super().__init__("create_file", "Create a UTF-8 workspace file without overwriting existing files.",
                         schema({"filename": {"type": "string"}, "content": {"type": "string"}},
                                ["filename", "content"]))

    def validate_input(self, arguments: dict) -> bool:
        super().validate_input(arguments)
        resolve_path(self.workspace, arguments["filename"])
        bounded_text(arguments["content"])
        return True

    def _execute(self, arguments: dict) -> dict:
        path = resolve_path(self.workspace, arguments["filename"])
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8") as destination:
            destination.write(arguments["content"])
        return {"path": arguments["filename"], "bytes": len(arguments["content"].encode("utf-8"))}


class EditFileTool(BaseTool):
    def __init__(self, workspace: Path):
        self.workspace = Path(workspace).resolve()
        super().__init__("edit_file", "Replace exactly one matching text fragment in a workspace file.",
                         schema({"filename": {"type": "string"}, "old_text": {"type": "string"},
                                 "new_text": {"type": "string"}}, ["filename", "old_text", "new_text"]))

    def validate_input(self, arguments: dict) -> bool:
        super().validate_input(arguments)
        resolve_path(self.workspace, arguments["filename"])
        bounded_text(arguments["old_text"])
        bounded_text(arguments["new_text"])
        if not arguments["old_text"]:
            raise ValueError("old_text must be nonempty")
        return True

    def _execute(self, arguments: dict) -> dict:
        path = resolve_path(self.workspace, arguments["filename"])
        if path.stat().st_size > 65536:
            raise ValueError("File exceeds the edit size limit")
        original = path.read_text(encoding="utf-8")
        if original.count(arguments["old_text"]) != 1:
            raise ValueError("old_text must match exactly once")
        replacement = original.replace(arguments["old_text"], arguments["new_text"], 1)
        bounded_text(replacement)
        path.write_text(replacement, encoding="utf-8")
        return {"path": arguments["filename"], "replacements": 1}


class RunScriptTool(BaseTool):
    def __init__(self, sandbox: PythonSandbox):
        self.sandbox = sandbox
        super().__init__("run_script", "Execute a trusted workspace Python script with timeout and resource limits.",
                         schema({"filename": {"type": "string"}}, ["filename"]))

    def validate_input(self, arguments: dict) -> bool:
        super().validate_input(arguments)
        path = resolve_path(self.sandbox.root, arguments["filename"])
        if path.suffix != ".py":
            raise ValueError("Expected a Python script")
        return True

    def _execute(self, arguments: dict) -> dict:
        return self.sandbox.execute_script(arguments["filename"])
