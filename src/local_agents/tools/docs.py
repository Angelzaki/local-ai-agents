from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

from local_agents.tools.base import ToolResult

TOKEN = re.compile(r"[a-zA-ZáéíóúñÁÉÍÓÚÑ0-9]+")
SUPPORTED = {".txt", ".md"}


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN.findall(text)]


class ListDocsTool:
    name = "list_docs"

    def __init__(self, docs_dir: Path):
        self.docs_dir = docs_dir

    def run(self, **kwargs: Any) -> ToolResult:
        files = sorted(
            p.name for p in self.docs_dir.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED
        )
        return ToolResult(name=self.name, ok=True, data=files, summary=f"{len(files)} docs")


class ReadDocTool:
    name = "read_doc"

    def __init__(self, docs_dir: Path):
        self.docs_dir = docs_dir

    def run(self, doc_name: str = "", **kwargs: Any) -> ToolResult:
        path = self.docs_dir / doc_name
        if not path.exists():
            matches = list(self.docs_dir.rglob(doc_name))
            path = matches[0] if matches else path
        if not path.exists() or not path.is_file():
            return ToolResult(name=self.name, ok=False, data=None, summary="doc no encontrado")
        text = path.read_text(encoding="utf-8")
        return ToolResult(name=self.name, ok=True, data={"path": str(path), "text": text}, summary=path.stem)


class DocSearchTool:
    name = "search_docs"

    def __init__(self, docs_dir: Path):
        self.docs_dir = docs_dir
        self._docs = self._load()

    def _load(self) -> list[tuple[str, str]]:
        docs: list[tuple[str, str]] = []
        for path in sorted(self.docs_dir.rglob("*")):
            if path.is_file() and path.suffix.lower() in SUPPORTED:
                docs.append((path.stem, path.read_text(encoding="utf-8")))
        return docs

    def run(self, query: str = "", k: int = 3, **kwargs: Any) -> ToolResult:
        if not self._docs:
            return ToolResult(name=self.name, ok=False, data=[], summary="corpus vacío")
        tokenized = [tokenize(text) for _, text in self._docs]
        df: Counter[str] = Counter()
        for tokens in tokenized:
            df.update(set(tokens))
        n = len(tokenized)
        idf = {t: math.log((n + 1) / (f + 1)) + 1.0 for t, f in df.items()}

        def vec(tokens: list[str]) -> dict[str, float]:
            tf = Counter(tokens)
            length = len(tokens) or 1
            return {t: (c / length) * idf.get(t, 0.0) for t, c in tf.items()}

        def cosine(a: dict[str, float], b: dict[str, float]) -> float:
            keys = set(a) | set(b)
            if not keys:
                return 0.0
            dot = sum(a.get(x, 0.0) * b.get(x, 0.0) for x in keys)
            na = math.sqrt(sum(v * v for v in a.values()))
            nb = math.sqrt(sum(v * v for v in b.values()))
            if na == 0 or nb == 0:
                return 0.0
            return dot / (na * nb)

        q = vec(tokenize(query))
        ranked = []
        for (doc_id, text), tokens in zip(self._docs, tokenized):
            score = cosine(q, vec(tokens))
            ranked.append({"doc_id": doc_id, "score": round(score, 4), "snippet": text[:220]})
        ranked.sort(key=lambda x: x["score"], reverse=True)
        top = ranked[:k]
        return ToolResult(
            name=self.name,
            ok=bool(top),
            data=top,
            summary=top[0]["doc_id"] if top else "sin hits",
        )
