import asyncio
import json
import os

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage


class OfflineModel:
    """Deterministic tool driver; never calls an API."""

    def __init__(self, role: str):
        self.role = role

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        payload = json.loads(next(message.content for message in messages if isinstance(message, HumanMessage)))
        parameters = payload["parameters"]
        outputs = {message.name: json.loads(message.content) for message in messages if isinstance(message, ToolMessage)}

        def call(name, arguments):
            return AIMessage(content="", tool_calls=[{"name": name, "args": arguments, "id": str(len(messages))}])

        if self.role == "data_agent":
            if "query_database" not in outputs:
                return call("query_database", {"query": "SELECT SUM(amount) AS revenue, COUNT(*) AS rows FROM sales WHERE quarter=3"})
            row = outputs["query_database"]["rows"][0]
            value = {"revenue": row[0], "rows": row[1]}
        elif self.role == "code_agent":
            if "create_file" not in outputs:
                code = ("import csv, json\nfrom pathlib import Path\n"
                        "with open('sales.csv') as source:\n    amounts = [int(row['amount']) for row in csv.DictReader(source) if row['quarter'] == '3']\n"
                        "value = {'revenue': sum(amounts), 'rows': len(amounts)}\n"
                        "Path('outputs/answer.json').write_text(json.dumps(value))\n")
                if parameters.get("chart"):
                    code += ("import matplotlib\nmatplotlib.use('Agg')\nimport matplotlib.pyplot as plt\n"
                             "figure, axis = plt.subplots(figsize=(4, 2.5))\naxis.bar(range(len(amounts)), amounts)\n"
                             "figure.tight_layout()\nfigure.savefig('outputs/sales_chart.png', dpi=90)\nplt.close(figure)\n")
                return call("create_file", {"filename": "outputs/report.py", "content": code + "print(json.dumps(value))\n"})
            if "run_script" not in outputs:
                return call("run_script", {"filename": "outputs/report.py"})
            value = {"script": "outputs/report.py", "answer": "outputs/answer.json",
                     "chart": "outputs/sales_chart.png" if parameters.get("chart") else None}
        else:
            if "comparison" not in outputs:
                return call("comparison", {"actual": parameters["actual"], "expected": parameters["expected"]})
            if "scoring" not in outputs:
                return call("scoring", parameters["ratings"])
            value = {"score": outputs["scoring"]["score"], "feedback": "Fixture evidence checked",
                     "issues": [] if outputs["comparison"]["valid"] else ["Reference mismatch"], "suggestions": []}
            if "report_generator" not in outputs:
                return call("report_generator", {"filename": "outputs/evaluation.md", "title": "Fixture verification",
                                                  "evaluation": value, "evidence": parameters})
        return AIMessage(content=json.dumps(value))

    async def ainvoke(self, messages):
        await asyncio.sleep(0)
        return self.invoke(messages)


def offline_factory(role, workspace):
    return OfflineModel(role)


def environment_value(name: str) -> str:
    value = os.getenv(name, "").strip()
    return value[1:-1] if len(value) >= 2 and value[0] == value[-1] and value[0] in {"\"", "'"} else value


def live_factory(role, workspace):
    from langchain_openai import AzureChatOpenAI, ChatOpenAI

    endpoint = environment_value("AZURE_OPENAI_ENDPOINT")
    key = environment_value("AZURE_OPENAI_KEY") or environment_value("AZURE_OPENAI_API_KEY") or environment_value("OPENAI_API_KEY")
    model = environment_value("AZURE_OPENAI_DEPLOYMENT_MODEL") or environment_value("LLM_MODEL")
    if not endpoint or not key or not model:
        raise ValueError("Live mode needs gateway endpoint, key and model in the ignored environment file")
    settings = {"api_key": key, "temperature": 0, "timeout": 30, "max_retries": 2}
    if "openai.azure.com" in endpoint or "cognitiveservices.azure.com" in endpoint:
        return AzureChatOpenAI(azure_endpoint=endpoint, azure_deployment=model,
                              api_version=environment_value("AZURE_OPENAI_API_VERSION") or "2024-12-01-preview", **settings)
    return ChatOpenAI(base_url=endpoint, model=model, **settings)
