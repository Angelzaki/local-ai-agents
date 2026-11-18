from pathlib import Path

from local_agents.router import LocalAgent

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "samples" / "docs"


def test_docs_answer(tmp_path):
    agent = LocalAgent(DOCS, tmp_path / "sessions.db")
    reply = agent.handle("¿Cuál es el descuento máximo en A1?")
    assert not reply.abstained
    assert "multihop_search" in reply.tools_used
    assert "politica_a1" in reply.citations


def test_summarize_and_compare(tmp_path):
    agent = LocalAgent(DOCS, tmp_path / "sessions.db")
    summary = agent.handle("resume A1")
    assert summary.route == "summarize"
    assert not summary.abstained
    cmp = agent.handle("compara A1 y A2")
    assert cmp.route == "compare"
    assert "compare_docs" in cmp.tools_used


def test_abstain(tmp_path):
    agent = LocalAgent(DOCS, tmp_path / "sessions.db")
    reply = agent.handle("política de viajes interplanetarios 2099")
    assert reply.abstained


def test_calc_route(tmp_path):
    agent = LocalAgent(DOCS, tmp_path / "sessions.db")
    reply = agent.handle("cuánto es 12 * 4")
    assert reply.route == "calc"
    assert reply.answer == "48.0"


def test_memory_persists(tmp_path):
    db = tmp_path / "sessions.db"
    agent = LocalAgent(DOCS, db)
    agent.handle("listar documentos", session_id="s1")
    history = agent.memory.history("s1")
    assert len(history) >= 2
    assert history[0]["role"] == "user"
