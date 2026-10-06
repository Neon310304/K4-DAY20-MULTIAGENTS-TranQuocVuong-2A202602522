import asyncio
import json
import logging
import time

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from ..tools import BaseTool


class BaseWorker:
    def __init__(self, name: str, model, tools: list[BaseTool], system_prompt: str, max_iterations: int = 12):
        if not isinstance(name, str) or not name.strip() or not isinstance(system_prompt, str) or not system_prompt.strip() \
                or isinstance(max_iterations, bool) or not isinstance(max_iterations, int) or not 1 <= max_iterations <= 100:
            raise ValueError("Invalid worker configuration")
        if len({tool.name for tool in tools}) != len(tools):
            raise ValueError("Duplicate tool names")
        self.name = name
        self.tools = {tool.name: tool for tool in tools}
        self.model = model.bind_tools([tool.model_schema() for tool in tools]) if tools else model
        self.system_prompt = system_prompt
        self.max_iterations = max_iterations
        self.logger = logging.getLogger(name)

    def _build_prompt(self, task_content: str, parameters: dict | None = None) -> list:
        if not isinstance(task_content, str) or not task_content.strip():
            raise ValueError("task_content must be nonempty text")
        if parameters is not None and not isinstance(parameters, dict):
            raise ValueError("parameters must be a dictionary")
        payload = json.dumps({"task": task_content, "parameters": parameters or {}}, allow_nan=False)
        return [SystemMessage(content=self.system_prompt), HumanMessage(content=payload)]

    def _execute_tool(self, tool_name: str, tool_input: dict):
        if tool_name not in self.tools:
            raise ValueError(f"Unknown tool: {tool_name}")
        return self.tools[tool_name].invoke(tool_input)

    @staticmethod
    def _result(response, executed: list[str], iterations: int, started: float) -> dict:
        return {"status": "success", "result": response.content,
                "metadata": {"tools_used": len(executed), "tool_names": list(executed),
                             "iterations": iterations, "seconds": round(time.monotonic() - started, 4)}}

    def _error(self, error: Exception, executed: list[str], started: float) -> dict:
        self.logger.warning("worker_error worker=%s error_type=%s", self.name, type(error).__name__)
        return {"status": "error", "error": f"{type(error).__name__}: {error}", "result": None,
                "metadata": {"tools_used": len(executed), "tool_names": list(executed),
                             "seconds": round(time.monotonic() - started, 4)}}

    def process(self, task_content: str, parameters: dict | None = None) -> dict:
        executed = []
        started = time.monotonic()
        try:
            messages = self._build_prompt(task_content, parameters)
            for iteration in range(1, self.max_iterations + 1):
                response = self.model.invoke(messages)
                messages.append(response)
                if len(response.tool_calls) > 16:
                    raise ValueError("Too many tool calls in one response")
                if not response.tool_calls:
                    return self._result(response, executed, iteration, started)
                for call in response.tool_calls:
                    output = self._execute_tool(call["name"], call["args"])
                    executed.append(call["name"])
                    messages.append(ToolMessage(content=json.dumps(output, ensure_ascii=False, allow_nan=False),
                                                tool_call_id=call["id"], name=call["name"]))
            raise RuntimeError("Worker iteration limit exceeded")
        except Exception as error:
            return self._error(error, executed, started)

    async def process_async(self, task_content: str, parameters: dict | None = None) -> dict:
        executed = []
        started = time.monotonic()
        try:
            messages = self._build_prompt(task_content, parameters)
            for iteration in range(1, self.max_iterations + 1):
                if hasattr(self.model, "ainvoke"):
                    response = await self.model.ainvoke(messages)
                else:
                    response = await asyncio.to_thread(self.model.invoke, messages)
                messages.append(response)
                if len(response.tool_calls) > 16:
                    raise ValueError("Too many tool calls in one response")
                if not response.tool_calls:
                    return self._result(response, executed, iteration, started)
                for call in response.tool_calls:
                    if call["name"] not in self.tools:
                        raise ValueError(f"Unknown tool: {call['name']}")
                    output = await self.tools[call["name"]].ainvoke(call["args"])
                    executed.append(call["name"])
                    messages.append(ToolMessage(content=json.dumps(output, ensure_ascii=False, allow_nan=False),
                                                tool_call_id=call["id"], name=call["name"]))
            raise RuntimeError("Worker iteration limit exceeded")
        except Exception as error:
            return self._error(error, executed, started)
