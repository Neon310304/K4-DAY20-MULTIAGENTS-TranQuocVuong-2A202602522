import asyncio
import sys
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


class FakeModel:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.tools = []

    def bind_tools(self, tools):
        self.tools = tools
        return self

    def invoke(self, messages):
        self.calls.append(list(messages) if isinstance(messages, list) else messages)
        if not self.responses:
            raise AssertionError("Unexpected model call")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    async def ainvoke(self, messages):
        await asyncio.sleep(0)
        return self.invoke(messages)


@pytest.fixture
def fake_model():
    return lambda *responses: FakeModel(responses or [AIMessage(content="done")])


@pytest.fixture
def ai_response():
    def make(content="", *calls):
        return AIMessage(content=content, tool_calls=[
            {"name": name, "args": arguments, "id": str(index)}
            for index, (name, arguments) in enumerate(calls)
        ])
    return make
