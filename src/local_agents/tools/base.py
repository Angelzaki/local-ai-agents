from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class ToolResult:
    name: str
    ok: bool
    data: Any
    summary: str


class Tool(Protocol):
    name: str

    def run(self, **kwargs: Any) -> ToolResult: ...
