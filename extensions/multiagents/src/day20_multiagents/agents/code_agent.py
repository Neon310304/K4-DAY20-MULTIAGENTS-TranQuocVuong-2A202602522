from pathlib import Path

from ..toolkits.code_tools import CreateFileTool, EditFileTool, PythonREPLTool, RunScriptTool
from .base_worker import BaseWorker


class CodeAgent(BaseWorker):
    def __init__(self, model, workspace: Path, timeout: float = 5, max_iterations: int = 12):
        self.workspace = Path(workspace).resolve()
        python_tool = PythonREPLTool(self.workspace, timeout=timeout)
        self.sandbox = python_tool.sandbox
        tools = [
            python_tool, CreateFileTool(self.workspace), EditFileTool(self.workspace), RunScriptTool(self.sandbox),
        ]
        super().__init__("code_agent", model, tools,
                         "You are a code implementation specialist. Work only on the requested workspace files. "
                         "Use create/edit tools and run the actual script or relevant checks before reporting success. "
                         "Never claim an artifact exists without tool evidence. Return its relative path and verified "
                         "output, or an explicit error. Execution tools are for trusted code inside Docker only, "
                         "not a security sandbox for adversarial Python. Do not access secrets, network or other files.",
                         max_iterations)

