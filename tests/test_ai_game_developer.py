from __future__ import annotations

import json
import unittest
from dataclasses import replace

from fastapi.testclient import TestClient

import ai_game_developer as game


def make_state(seed: int = 7) -> game.GameState:
    return game.create_game(seed=seed, theme_id="dungeon", width=14, height=10)


def adjacent_floor(state: game.GameState) -> game.Cell:
    level = state.level
    for dx, dy in ((0, -1), (0, 1), (1, 0), (-1, 0)):
        x, y = state.player.x + dx, state.player.y + dy
        if 0 <= x < level.width and 0 <= y < level.height and level.tiles[y][x] == game.FLOOR:
            return game.Cell(x, y)
    raise AssertionError("no adjacent floor tile")


def set_adjacent(state: game.GameState, tile: str) -> game.Cell:
    cell = adjacent_floor(state)
    state.level.tiles[cell.y][cell.x] = tile
    return cell


class LevelGenerationTests(unittest.TestCase):
    def test_level_has_required_entities(self) -> None:
        level = game.generate_level(seed=1, width=14, height=10)
        self.assertEqual(level.tiles[level.start.y][level.start.x], game.PLAYER)
        self.assertEqual(level.tiles[level.exit.y][level.exit.x], game.EXIT)
        self.assertGreaterEqual(len(level.enemies), 1)
        self.assertGreaterEqual(len(level.items), 1)
        self.assertTrue(game._reachable(level.tiles, level.start, level.exit))

    def test_generation_is_deterministic(self) -> None:
        first = game.generate_level(seed=99, width=16, height=11)
        second = game.generate_level(seed=99, width=16, height=11)
        self.assertEqual(first.to_dict(), second.to_dict())

    def test_dimensions_are_validated(self) -> None:
        with self.assertRaises(ValueError):
            game.generate_level(seed=1, width=4, height=4)
        with self.assertRaises(ValueError):
            game.create_game(width=100, height=100)

    def test_unknown_theme_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            game.create_game(theme_id="unknown")


class GameplayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.state = make_state()

    def test_create_game_starts_on_first_level(self) -> None:
        self.assertEqual(self.state.level_index, 0)
        self.assertEqual(self.state.status, "playing")
        self.assertEqual(self.state.player.hp, game.THEMES["dungeon"].player_hp)
        self.assertEqual(
            (self.state.player.x, self.state.player.y),
            (self.state.level.start.x, self.state.level.start.y),
        )

    def test_wall_blocks_movement(self) -> None:
        target = set_adjacent(self.state, game.WALL)
        result = game.move_player(self.state, self._direction_to(target))
        self.assertFalse(result.moved)
        self.assertIn("wall", result.message.lower())

    def test_floor_movement_updates_position_and_turn(self) -> None:
        target = adjacent_floor(self.state)
        dx = target.x - self.state.player.x
        dy = target.y - self.state.player.y
        direction = next(key for key, value in game.DIRECTIONS.items() if value == (dx, dy))
        result = game.move_player(self.state, direction)
        self.assertTrue(result.moved)
        self.assertEqual((self.state.player.x, self.state.player.y), (target.x, target.y))
        self.assertEqual(self.state.turn, 1)

    def test_combat_can_kill_an_enemy(self) -> None:
        self.state.player = replace(self.state.player, atk=10)
        target = set_adjacent(self.state, game.ENEMY)
        hp_before = self.state.player.hp
        result = game.move_player(self.state, self._direction_to(target))
        self.assertTrue(result.moved)
        self.assertIsNotNone(result.combat)
        self.assertEqual(self.state.player.hp, hp_before)
        self.assertEqual(self.state.player.score, 10)
        self.assertEqual(self.state.level.tiles[target.y][target.x], game.PLAYER)

    def test_combat_damage_is_applied(self) -> None:
        self.state.player = replace(self.state.player, atk=3, hp=20)
        target = set_adjacent(self.state, game.ENEMY)
        result = game.move_player(self.state, self._direction_to(target))
        self.assertTrue(result.moved)
        self.assertEqual(result.combat, {"rounds": 3, "damage_taken": 4})
        self.assertEqual(self.state.player.hp, 16)

    def test_death_ends_the_game(self) -> None:
        self.state.player = replace(self.state.player, atk=1, hp=1)
        target = set_adjacent(self.state, game.ENEMY)
        result = game.move_player(self.state, self._direction_to(target))
        self.assertFalse(result.moved)
        self.assertTrue(result.game_over)
        self.assertEqual(self.state.status, "lost")
        self.assertEqual(self.state.player.hp, 0)

    def test_item_heals_and_scores(self) -> None:
        self.state.player = replace(self.state.player, hp=10)
        target = set_adjacent(self.state, game.ITEM)
        result = game.move_player(self.state, self._direction_to(target))
        self.assertTrue(result.moved)
        self.assertEqual(self.state.player.hp, 15)
        self.assertEqual(self.state.player.score, 5)

    def test_exit_advances_to_next_level(self) -> None:
        target = set_adjacent(self.state, game.EXIT)
        result = game.move_player(self.state, self._direction_to(target))
        self.assertTrue(result.moved)
        self.assertTrue(result.level_complete)
        self.assertEqual(self.state.level_index, 1)
        self.assertEqual(self.state.player.score, 50)
        self.assertEqual(
            (self.state.player.x, self.state.player.y),
            (self.state.level.start.x, self.state.level.start.y),
        )

    def test_final_exit_wins_the_game(self) -> None:
        self.state.level_index = 2
        self.state.player = replace(
            self.state.player,
            x=self.state.level.start.x,
            y=self.state.level.start.y,
        )
        target = set_adjacent(self.state, game.EXIT)
        result = game.move_player(self.state, self._direction_to(target))
        self.assertTrue(result.moved)
        self.assertTrue(result.won)
        self.assertEqual(self.state.status, "won")
        self.assertEqual(self.state.player.score, 100)

    def test_moves_after_game_over_are_ignored(self) -> None:
        self.state.status = "won"
        result = game.move_player(self.state, "n")
        self.assertFalse(result.moved)
        self.assertEqual(result.message, "Game over.")

    def _direction_to(self, target: game.Cell) -> str:
        delta = (target.x - self.state.player.x, target.y - self.state.player.y)
        return next(key for key, value in game.DIRECTIONS.items() if value == delta)


class ExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.state = make_state(seed=3)
        self.document = game.render_export_html(self.state)

    def test_export_is_self_contained(self) -> None:
        self.assertIn("<!doctype html>", self.document)
        self.assertIn("const GAME = ", self.document)
        self.assertIn("Content-Security-Policy", self.document)
        self.assertNotIn("@@", self.document)
        self.assertNotIn("cdn.", self.document.lower())

    def test_embedded_payload_contains_all_levels(self) -> None:
        marker = "const GAME = "
        start = self.document.index(marker) + len(marker)
        end = self.document.index(";\n\n(() => {")
        payload = json.loads(self.document[start:end])
        self.assertEqual(len(payload["current"]["levels"]), 3)
        self.assertEqual(len(payload["initial"]["levels"]), 3)
        self.assertEqual(payload["current"]["player"]["hp"], self.state.player.hp)
        self.assertEqual(payload["theme"]["id"], "dungeon")


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(game.app)

    def setUp(self) -> None:
        with game.GAMES_LOCK:
            game.GAMES.clear()

    def test_health_and_themes(self) -> None:
        health = self.client.get("/health")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["status"], "ok")

        themes = self.client.get("/themes")
        self.assertEqual(themes.status_code, 200)
        self.assertEqual({theme["id"] for theme in themes.json()}, set(game.THEMES))

    def test_create_move_and_export(self) -> None:
        created = self.client.post(
            "/games",
            json={"seed": 42, "theme": "space", "width": 14, "height": 10},
        )
        self.assertEqual(created.status_code, 201)
        payload = created.json()
        game_id = payload["id"]
        self.assertEqual(payload["theme"], "space")

        fetched = self.client.get(f"/games/{game_id}")
        self.assertEqual(fetched.status_code, 200)

        moved = self.client.post(f"/games/{game_id}/move", json={"direction": "n"})
        self.assertEqual(moved.status_code, 200)
        self.assertIn("result", moved.json())

        exported = self.client.get(f"/games/{game_id}/export")
        self.assertEqual(exported.status_code, 200)
        self.assertIn("<!doctype html>", exported.text)
        self.assertIn("attachment;", exported.headers["content-disposition"])

        inline = self.client.get(f"/games/{game_id}/export?download=false")
        self.assertEqual(inline.status_code, 200)
        self.assertNotIn("content-disposition", inline.headers)

    def test_validation_and_not_found(self) -> None:
        invalid_theme = self.client.post("/games", json={"theme": "unknown"})
        self.assertEqual(invalid_theme.status_code, 422)

        invalid_size = self.client.post("/games", json={"width": 4, "height": 4})
        self.assertEqual(invalid_size.status_code, 422)

        missing = self.client.get("/games/not-a-game")
        self.assertEqual(missing.status_code, 404)

        invalid_direction = self.client.post(
            "/games/not-a-game/move",
            json={"direction": "x"},
        )
        self.assertEqual(invalid_direction.status_code, 422)

    def test_delete(self) -> None:
        created = self.client.post("/games", json={"seed": 1})
        game_id = created.json()["id"]
        deleted = self.client.delete(f"/games/{game_id}")
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(self.client.get(f"/games/{game_id}").status_code, 404)


if __name__ == "__main__":
    unittest.main()
