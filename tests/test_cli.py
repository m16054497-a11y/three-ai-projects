from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from three_ai_suite import __version__, cli


class UnifiedCliTests(unittest.TestCase):
    def run_cli(self, argv: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = cli.main(argv)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_version(self) -> None:
        code, stdout, _ = self.run_cli(["--version"])
        self.assertEqual(code, 0)
        self.assertIn(__version__, stdout)

    def test_help_lists_projects(self) -> None:
        code, stdout, _ = self.run_cli(["--help"])
        self.assertEqual(code, 0)
        for command in ("researcher", "scientist", "game"):
            self.assertIn(command, stdout)

    def test_researcher_dispatch(self) -> None:
        code, stdout, _ = self.run_cli(["researcher", "topics"])
        self.assertEqual(code, 0)
        self.assertIn("Transformers", stdout)

    def test_scientist_dispatch(self) -> None:
        code, stdout, _ = self.run_cli(["scientist", "domains"])
        self.assertEqual(code, 0)
        self.assertIn("conversion", stdout)

    def test_game_themes(self) -> None:
        code, stdout, _ = self.run_cli(["game", "themes"])
        self.assertEqual(code, 0)
        self.assertIn("dungeon", stdout)
        self.assertIn("cyberpunk", stdout)

    def test_game_export_writes_playable_html(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "game.html"
            code, stdout, _ = self.run_cli(
                [
                    "game",
                    "export",
                    "--seed",
                    "3",
                    "--theme",
                    "space",
                    "--output",
                    str(output),
                ]
            )
            self.assertEqual(code, 0)
            self.assertIn(str(output), stdout)
            document = output.read_text(encoding="utf-8")
        self.assertIn("<!doctype html>", document.lower())
        self.assertIn("Space Explorer", document)

    def test_unknown_command(self) -> None:
        code, _, stderr = self.run_cli(["unknown"])
        self.assertEqual(code, 2)
        self.assertIn("unknown command", stderr)

    def test_game_without_arguments_shows_help(self) -> None:
        code, stdout, _ = self.run_cli(["game"])
        self.assertEqual(code, 0)
        self.assertIn("serve", stdout)
        self.assertIn("export", stdout)


if __name__ == "__main__":
    unittest.main()
