from __future__ import annotations

import argparse
import json
from pathlib import Path

from rich.console import Console

from local_agents.router import LocalAgent

console = Console()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="local-agents")
    parser.add_argument("message", nargs="?", help="mensaje al agente")
    parser.add_argument("--session", default="default")
    parser.add_argument("--docs", default="samples/docs")
    parser.add_argument("--memory", default="data/sessions.db")
    parser.add_argument("--repl", action="store_true")
    args = parser.parse_args(argv)

    agent = LocalAgent(Path(args.docs), Path(args.memory))

    if args.repl:
        console.print("[bold]local-ai-agents[/bold] · Ctrl+C para salir")
        while True:
            try:
                msg = console.input("[cyan]you>[/cyan] ").strip()
            except (KeyboardInterrupt, EOFError):
                console.print()
                return 0
            if not msg:
                continue
            reply = agent.handle(msg, session_id=args.session)
            console.print(f"[green]agent>[/green] {reply.answer}")
            console.print(
                f"[dim]tools={reply.tools_used} citations={reply.citations} abstained={reply.abstained}[/dim]"
            )
        return 0

    if not args.message:
        parser.error("pasa un mensaje o usa --repl")

    reply = agent.handle(args.message, session_id=args.session)
    print(
        json.dumps(
            {
                "answer": reply.answer,
                "tools_used": reply.tools_used,
                "citations": reply.citations,
                "abstained": reply.abstained,
                "route": reply.route,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
