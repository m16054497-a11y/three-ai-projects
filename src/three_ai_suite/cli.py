"""Unified command-line interface for the three projects."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from . import __version__

THEME_IDS = ("dungeon", "space", "forest", "cyberpunk")

HELP = f"""three-ai {__version__}

Usage:
  three-ai researcher <command> [options]
  three-ai scientist <command> [options]
  three-ai game <command> [options]

Projects:
  researcher   Search and summarize a local research corpus
  scientist    Run a Bayesian hypothesis and experiment loop
  game         Generate playable HTML games or serve the game API

Examples:
  three-ai researcher topics
  three-ai researcher search "retrieval augmented generation"
  three-ai scientist run "How do we reduce churn?"
  three-ai game export --seed 42 --theme dungeon --output dungeon.html
  three-ai game serve --host 127.0.0.1 --port 8000

Run 'three-ai <project> --help' for project-specific options.
"""


def _game_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="three-ai game",
        description="Generate a playable HTML game or run the FastAPI game service.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    serve = commands.add_parser("serve", help="run the FastAPI game service")
    serve.add_argument("--host", default="127.0.0.1", help="bind address (default: 127.0.0.1)")
    serve.add_argument("--port", type=int, default=8000, help="TCP port (default: 8000)")
    serve.add_argument(
        "--reload",
        action="store_true",
        help="restart automatically when source files change (development only)",
    )

    export = commands.add_parser("export", help="write a self-contained playable HTML file")
    export.add_argument("--seed", type=int, default=42, help="deterministic game seed")
    export.add_argument("--theme", choices=THEME_IDS, default="dungeon", help="visual theme")
    export.add_argument("--width", type=int, default=20, help="map width (default: 20)")
    export.add_argument("--height", type=int, default=12, help="map height (default: 12)")
    export.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        metavar="PATH",
        help="output path (default: <theme>-<seed>.html)",
    )

    commands.add_parser("themes", help="list available visual themes")
    return parser


def _missing_game_dependency(exc: ModuleNotFoundError) -> int:
    package = exc.name or "the game dependencies"
    print(
        f"error: {package} is required for the game project.\n"
        "Install it with:\n"
        "  python -m pip install 'three-ai-suite[game]'",
        file=sys.stderr,
    )
    return 2


def researcher_main(argv: Sequence[str] | None = None) -> int:
    """Run the AI Researcher CLI."""
    from .researcher import main

    return main(argv)


def scientist_main(argv: Sequence[str] | None = None) -> int:
    """Run the AI Scientist CLI."""
    from .scientist import main

    return main(argv)


def game_main(argv: Sequence[str] | None = None) -> int:
    """Run the AI Game Developer commands."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    parser = _game_parser()
    if not arguments:
        parser.print_help()
        return 0
    args = parser.parse_args(arguments)

    try:
        from . import game
    except ModuleNotFoundError as exc:
        return _missing_game_dependency(exc)

    if args.command == "themes":
        for theme in game.THEMES.values():
            print(f"{theme.id:<10} {theme.label}: {theme.description}")
        return 0

    if args.command == "serve":
        try:
            import uvicorn
        except ModuleNotFoundError as exc:
            return _missing_game_dependency(exc)
        uvicorn.run(
            "three_ai_suite.game:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
        )
        return 0

    try:
        state = game.create_game(
            seed=args.seed,
            theme_id=args.theme,
            width=args.width,
            height=args.height,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    document = game.render_export_html(state)
    output = args.output or Path(f"{args.theme}-{args.seed}.html")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(document, encoding="utf-8")
    print(f"Wrote {output} ({len(document):,} bytes)")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Dispatch to one of the three projects."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments or arguments[0] in {"-h", "--help", "help"}:
        print(HELP, end="")
        return 0
    if arguments[0] in {"-V", "--version", "version"}:
        print(f"three-ai {__version__}")
        return 0

    command, rest = arguments[0], arguments[1:]
    if command in {"researcher", "research"}:
        return researcher_main(rest)
    if command in {"scientist", "science"}:
        return scientist_main(rest)
    if command in {"game", "games"}:
        return game_main(rest)

    print(f"error: unknown command {command!r}\nTry 'three-ai --help'.", file=sys.stderr)
    return 2
