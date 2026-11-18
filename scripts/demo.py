from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from local_agents.router import LocalAgent

PROMPTS = [
    "listar documentos",
    "resume A1",
    "compara A1 y A2",
    "¿Cuál es el límite comercial?",
    "cuánto es 15 * 3",
    "política de viajes interplanetarios 2099",
]


def main() -> int:
    agent = LocalAgent(ROOT / "samples" / "docs", ROOT / "data" / "demo_sessions.db")
    for prompt in PROMPTS:
        reply = agent.handle(prompt, session_id="demo")
        print(
            json.dumps(
                {
                    "prompt": prompt,
                    "route": reply.route,
                    "tools": reply.tools_used,
                    "citations": reply.citations,
                    "abstained": reply.abstained,
                    "answer": reply.answer,
                },
                ensure_ascii=False,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
