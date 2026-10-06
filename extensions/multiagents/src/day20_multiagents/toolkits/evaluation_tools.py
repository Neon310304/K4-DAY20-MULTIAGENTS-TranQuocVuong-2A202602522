import json
import math
from pathlib import Path

from ..tools import BaseTool, schema
from .code_tools import CreateFileTool, bounded_text


def validate_evaluation(value: dict) -> None:
    if not isinstance(value, dict) or set(value) != {"score", "feedback", "issues", "suggestions"}:
        raise ValueError("Invalid evaluator fields")
    score = value["score"]
    if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score) or not 0 <= score <= 100:
        raise ValueError("score must be finite and within 0-100")
    if not isinstance(value["feedback"], str) or not all(isinstance(value[key], list) for key in ("issues", "suggestions")):
        raise ValueError("Invalid feedback format")
    if not all(isinstance(item, str) for key in ("issues", "suggestions") for item in value[key]):
        raise ValueError("Expected lists of strings")


class ScoringTool(BaseTool):
    WEIGHTS = {"accuracy": 0.3, "completeness": 0.3, "clarity": 0.2, "performance": 0.2}

    def __init__(self):
        super().__init__("scoring", "Weight supplied criterion scores 30/30/20/20; not an independent quality judge.",
                         schema({name: {"type": "number", "minimum": 0, "maximum": 100} for name in self.WEIGHTS},
                                list(self.WEIGHTS)))

    @staticmethod
    def grade(score: float) -> str:
        for threshold, grade in ((90, "A"), (80, "B"), (70, "C"), (60, "D")):
            if score >= threshold:
                return grade
        return "F"

    def _execute(self, arguments: dict) -> dict:
        score = round(sum(arguments[name] * weight for name, weight in self.WEIGHTS.items()), 2)
        return {"score": score, "grade": self.grade(score), "scores": dict(arguments),
                "weights": dict(self.WEIGHTS)}


class ComparisonTool(BaseTool):
    def __init__(self):
        super().__init__("comparison", "Compare explicit scalar fields against supplied reference evidence; extras are ignored.",
                         schema({"actual": {"type": "object"}, "expected": {"type": "object"},
                                 "tolerance": {"type": "number", "minimum": 0, "maximum": 1000000}},
                                ["actual", "expected"]))

    def validate_input(self, arguments: dict) -> bool:
        super().validate_input(arguments)
        if not arguments["expected"] or len(arguments["expected"]) > 128 or len(arguments["actual"]) > 128:
            raise ValueError("Comparison requires 1-128 reference fields and at most 128 actual fields")
        for payload in (arguments["actual"], arguments["expected"]):
            for name, value in payload.items():
                if not isinstance(name, str) or not name or value is not None and not isinstance(value, (str, bool, int, float)):
                    raise ValueError("Comparison supports named scalar fields only")
                if isinstance(value, (int, float)) and not isinstance(value, bool) and not math.isfinite(value):
                    raise ValueError("Comparison numbers must be finite")
        return True

    def _execute(self, arguments: dict) -> dict:
        actual = arguments["actual"]
        tolerance = arguments.get("tolerance", 0)
        mismatches = []
        for name, expected in arguments["expected"].items():
            observed = actual.get(name)
            if isinstance(expected, (int, float)) and not isinstance(expected, bool):
                equal = isinstance(observed, (int, float)) and not isinstance(observed, bool) \
                    and abs(observed - expected) <= tolerance
            else:
                equal = type(observed) is type(expected) and observed == expected
            if name not in actual or not equal:
                mismatches.append({"field": name, "expected": expected, "actual": observed,
                                   "reason": "missing" if name not in actual else "mismatch"})
        return {"valid": not mismatches, "matched_fields": len(arguments["expected"]) - len(mismatches),
                "mismatches": mismatches}


class ReportGeneratorTool(BaseTool):
    def __init__(self, workspace: Path):
        self.file_tool = CreateFileTool(workspace)
        super().__init__("report_generator", "Write a bounded Markdown evaluation report with explicit source evidence.",
                         schema({"filename": {"type": "string"}, "title": {"type": "string"},
                                 "evaluation": schema({"score": {"type": "number", "minimum": 0, "maximum": 100},
                                                        "feedback": {"type": "string"},
                                                        "issues": {"type": "array", "items": {"type": "string"}},
                                                        "suggestions": {"type": "array", "items": {"type": "string"}}},
                                                       ["score", "feedback", "issues", "suggestions"]),
                                 "evidence": {"type": "object"}},
                                ["filename", "title", "evaluation", "evidence"]))

    def validate_input(self, arguments: dict) -> bool:
        super().validate_input(arguments)
        if Path(arguments["filename"]).suffix != ".md" or not arguments["title"].strip():
            raise ValueError("Report requires a .md filename and nonempty title")
        validate_evaluation(arguments["evaluation"])
        self.file_tool.validate_input({"filename": arguments["filename"], "content": ""})
        return True

    def _execute(self, arguments: dict) -> dict:
        evaluation = arguments["evaluation"]
        grade = ScoringTool.grade(evaluation["score"])
        issues = "\n".join("- " + item for item in evaluation["issues"]) or "- None reported."
        suggestions = "\n".join("- " + item for item in evaluation["suggestions"]) or "- None supplied."
        evidence = json.dumps(arguments["evidence"], ensure_ascii=False, allow_nan=False, indent=2)
        content = (f"# {arguments['title']}\n\nScore: {evaluation['score']}/100 ({grade})\n\n"
                   f"{evaluation['feedback']}\n\n## Issues\n{issues}\n\n## Suggestions\n{suggestions}\n\n"
                   f"## Supplied evidence\n\n```json\n{evidence}\n```\n\n"
                   "This report records supplied evidence and criterion scores; it is not an independent LLM quality benchmark.\n")
        bounded_text(content)
        return {**self.file_tool.invoke({"filename": arguments["filename"], "content": content}), "grade": grade}
