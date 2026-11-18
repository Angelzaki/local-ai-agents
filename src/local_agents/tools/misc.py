from __future__ import annotations

import ast
import operator
from datetime import datetime
from typing import Any

from local_agents.tools.base import ToolResult

OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.USub: operator.neg,
}


def _eval(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.BinOp) and type(node.op) in OPS:
        return OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in OPS:
        return OPS[type(node.op)](_eval(node.operand))
    raise ValueError("expresión no permitida")


class CalcTool:
    name = "calc"

    def run(self, expression: str = "", **kwargs: Any) -> ToolResult:
        try:
            tree = ast.parse(expression, mode="eval")
            value = _eval(tree.body)
            return ToolResult(name=self.name, ok=True, data=value, summary=str(value))
        except Exception as exc:
            return ToolResult(name=self.name, ok=False, data=None, summary=str(exc))


class NowTool:
    name = "now"

    def run(self, **kwargs: Any) -> ToolResult:
        stamp = datetime.now().isoformat(timespec="seconds")
        return ToolResult(name=self.name, ok=True, data=stamp, summary=stamp)
