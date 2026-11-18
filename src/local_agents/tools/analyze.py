from __future__ import annotations

from typing import Any

from local_agents.tools.base import ToolResult
from local_agents.tools.docs import DocSearchTool, ReadDocTool, tokenize


class SummarizeDocTool:
    name = "summarize_doc"

    def __init__(self, read_doc: ReadDocTool):
        self.read_doc = read_doc

    def run(self, doc_name: str = "", **kwargs: Any) -> ToolResult:
        got = self.read_doc.run(doc_name=doc_name)
        if not got.ok:
            return ToolResult(name=self.name, ok=False, data=None, summary=got.summary)
        text = got.data["text"]
        sentences = [s.strip() for s in text.replace("\n", " ").split(".") if s.strip()]
        summary = ". ".join(sentences[:3]).strip() + "."
        return ToolResult(
            name=self.name,
            ok=True,
            data={"doc": doc_name, "summary": summary},
            summary=summary,
        )


class CompareDocsTool:
    name = "compare_docs"

    def __init__(self, read_doc: ReadDocTool):
        self.read_doc = read_doc

    def run(self, doc_a: str = "", doc_b: str = "", **kwargs: Any) -> ToolResult:
        a = self.read_doc.run(doc_name=doc_a)
        b = self.read_doc.run(doc_name=doc_b)
        if not a.ok or not b.ok:
            return ToolResult(name=self.name, ok=False, data=None, summary="no se pudieron leer ambos docs")
        ta = set(tokenize(a.data["text"]))
        tb = set(tokenize(b.data["text"]))
        shared = sorted(ta & tb)
        only_a = sorted(ta - tb)
        only_b = sorted(tb - ta)
        data = {
            "shared_terms": shared[:20],
            "only_a": only_a[:15],
            "only_b": only_b[:15],
            "overlap_ratio": round(len(shared) / max(len(ta | tb), 1), 4),
        }
        summary = (
            f"overlap={data['overlap_ratio']:.0%} | "
            f"compartidos={', '.join(shared[:8]) or 'ninguno'}"
        )
        return ToolResult(name=self.name, ok=True, data=data, summary=summary)


class MultiHopSearchTool:
    name = "multihop_search"

    def __init__(self, search: DocSearchTool, read_doc: ReadDocTool):
        self.search = search
        self.read_doc = read_doc

    def run(self, query: str = "", k: int = 2, **kwargs: Any) -> ToolResult:
        hits = self.search.run(query=query, k=k)
        if not hits.ok:
            return ToolResult(name=self.name, ok=False, data=[], summary="sin evidencia")
        bundle = []
        for item in hits.data:
            full = self.read_doc.run(doc_name=f"{item['doc_id']}.txt")
            bundle.append(
                {
                    "doc_id": item["doc_id"],
                    "score": item["score"],
                    "text": full.data["text"] if full.ok else item["snippet"],
                }
            )
        return ToolResult(
            name=self.name,
            ok=True,
            data=bundle,
            summary=",".join(x["doc_id"] for x in bundle),
        )
