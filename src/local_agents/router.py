from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from local_agents.memory import SessionMemory
from local_agents.tools.analyze import CompareDocsTool, MultiHopSearchTool, SummarizeDocTool
from local_agents.tools.docs import DocSearchTool, ListDocsTool, ReadDocTool, tokenize
from local_agents.tools.misc import CalcTool, NowTool

ABSTAIN = "No cuento con evidencia suficiente en el corpus para responder."
STOP = {
    "politica",
    "política",
    "cuales",
    "cuáles",
    "cual",
    "cuál",
    "como",
    "cómo",
    "que",
    "qué",
    "tiene",
    "tienen",
    "para",
    "sobre",
}


@dataclass
class AgentReply:
    answer: str
    tools_used: list[str] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)
    abstained: bool = False
    route: str = "docs"


class LocalAgent:
    def __init__(self, docs_dir: Path, memory_db: Path):
        self.docs_dir = docs_dir
        self.memory = SessionMemory(memory_db)
        self.list_docs = ListDocsTool(docs_dir)
        self.read_doc = ReadDocTool(docs_dir)
        self.search_docs = DocSearchTool(docs_dir)
        self.summarize = SummarizeDocTool(self.read_doc)
        self.compare = CompareDocsTool(self.read_doc)
        self.multihop = MultiHopSearchTool(self.search_docs, self.read_doc)
        self.calc = CalcTool()
        self.now = NowTool()

    def handle(self, message: str, session_id: str = "default") -> AgentReply:
        self.memory.add(session_id, "user", message)
        route = self._route(message)

        if route == "calc":
            expr = self._extract_expression(message)
            result = self.calc.run(expression=expr)
            reply = AgentReply(
                answer=str(result.data) if result.ok else f"No pude calcular: {result.summary}",
                tools_used=["calc"],
                route="calc",
            )
        elif route == "now":
            result = self.now.run()
            reply = AgentReply(answer=result.summary, tools_used=["now"], route="now")
        elif route == "list":
            result = self.list_docs.run()
            reply = AgentReply(
                answer="Docs disponibles: " + ", ".join(result.data),
                tools_used=["list_docs"],
                route="list",
            )
        elif route == "summarize":
            reply = self._summarize(message)
        elif route == "compare":
            reply = self._compare(message)
        else:
            reply = self._answer_from_docs(message)

        self.memory.add(
            session_id,
            "assistant",
            reply.answer,
            meta={
                "tools": reply.tools_used,
                "citations": reply.citations,
                "abstained": reply.abstained,
                "route": reply.route,
            },
        )
        return reply

    def _route(self, message: str) -> str:
        lower = message.lower()
        if any(k in lower for k in ("hora", "fecha", "now", "qué día")):
            return "now"
        if any(k in lower for k in ("lista", "listar", "qué docs", "que docs", "documentos disponibles")):
            return "list"
        if "compara" in lower or "comparar" in lower:
            return "compare"
        if "resum" in lower:
            return "summarize"
        if "cuánto es" in lower or "cuanto es" in lower:
            return "calc"
        if re.search(r"\d", message) and any(op in message for op in "+-*/"):
            return "calc"
        return "docs"

    def _extract_expression(self, message: str) -> str:
        match = re.search(r"(\d+(?:\s*[+\-*/]\s*\d+)+)", message)
        if match:
            return match.group(1).replace(" ", "")
        match = re.search(r"(\d[\d.\s+\-*/()]+)", message)
        return match.group(1).strip() if match else ""

    def _guess_doc(self, message: str) -> str | None:
        lower = message.lower()
        catalog = {
            "a1": "politica_a1.txt",
            "politica": "politica_a1.txt",
            "a2": "requisitos_a2.txt",
            "requisitos": "requisitos_a2.txt",
            "limite": "limite_comercial.txt",
            "límite": "limite_comercial.txt",
        }
        for key, doc in catalog.items():
            if key in lower:
                return doc
        listed = self.list_docs.run().data
        for name in listed:
            if name.replace(".txt", "").lower() in lower:
                return name
        return listed[0] if listed else None

    def _summarize(self, message: str) -> AgentReply:
        doc = self._guess_doc(message)
        if not doc:
            return AgentReply(answer=ABSTAIN, tools_used=["list_docs"], abstained=True, route="summarize")
        result = self.summarize.run(doc_name=doc)
        return AgentReply(
            answer=result.summary if result.ok else ABSTAIN,
            tools_used=["summarize_doc"],
            citations=[Path(doc).stem],
            abstained=not result.ok,
            route="summarize",
        )

    def _compare(self, message: str) -> AgentReply:
        lower = message.lower()
        a = "politica_a1.txt" if "a1" in lower or "politica" in lower else None
        b = "requisitos_a2.txt" if "a2" in lower or "requisitos" in lower else None
        if not a or not b:
            a, b = "politica_a1.txt", "limite_comercial.txt"
        result = self.compare.run(doc_a=a, doc_b=b)
        return AgentReply(
            answer=result.summary if result.ok else ABSTAIN,
            tools_used=["compare_docs"],
            citations=[Path(a).stem, Path(b).stem],
            abstained=not result.ok,
            route="compare",
        )

    def _answer_from_docs(self, message: str) -> AgentReply:
        multi = self.multihop.run(query=message, k=2)
        tools = ["multihop_search"]
        if not multi.ok or not multi.data:
            return AgentReply(answer=ABSTAIN, tools_used=tools, abstained=True, route="docs")

        top = multi.data[0]
        if top["score"] < 0.12 or not self._has_evidence(message, top["text"]):
            return AgentReply(answer=ABSTAIN, tools_used=tools, abstained=True, route="docs")

        answer = self._compose(message, top["text"])
        citations = [item["doc_id"] for item in multi.data]
        return AgentReply(
            answer=answer,
            tools_used=tools,
            citations=citations,
            abstained=False,
            route="docs",
        )

    def _has_evidence(self, question: str, chunk_text: str) -> bool:
        content = [t for t in tokenize(question) if t not in STOP and len(t) > 3]
        if not content:
            return False
        ctx = set(tokenize(chunk_text))
        overlap = sum(1 for t in content if t in ctx)
        return (overlap / len(content)) >= 0.34

    def _compose(self, question: str, text: str) -> str:
        sentences = [s.strip() for s in text.replace("\n", " ").split(".") if s.strip()]
        q_words = {w for w in tokenize(question) if len(w) > 3}
        ranked = sorted(
            sentences,
            key=lambda s: sum(1 for w in q_words if w in s.lower()),
            reverse=True,
        )
        picked = ranked[:2] if ranked else [text[:220]]
        return ". ".join(picked).strip() + "."
