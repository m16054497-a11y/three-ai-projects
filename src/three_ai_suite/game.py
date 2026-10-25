#!/usr/bin/env python3
"""AI Game Developer - generate playable, self-contained game prototypes.

The service exposes a small FastAPI API for creating and playing a deterministic
dungeon crawler. Every game can be exported as a single HTML file that runs
offline in any modern browser, with no server, assets, or CDN required.

Run the API:
    three-ai game serve --reload

Open the interactive docs:
    http://127.0.0.1:8000/docs

Create and export a game:
    three-ai game export --seed 42 --theme dungeon --output dungeon.html

Alternatively, use the HTTP API:
    curl -X POST http://127.0.0.1:8000/games \
         -H 'Content-Type: application/json' \
         -d '{"seed": 42, "theme": "dungeon"}'
    curl -OJ http://127.0.0.1:8000/games/<GAME_ID>/export

License: MIT
"""

from __future__ import annotations

import html
import json
import math
import random
import threading
from dataclasses import asdict, dataclass, field, replace
from itertools import pairwise
from typing import Any, Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from . import __version__

WALL, FLOOR, PLAYER, ENEMY, ITEM, EXIT = "#", ".", "@", "E", "I", "X"
LEVELS_PER_GAME = 3
MAX_GAMES = 500
MAX_LOG_ENTRIES = 60

MIN_WIDTH, MAX_WIDTH = 9, 60
MIN_HEIGHT, MAX_HEIGHT = 7, 40

DIRECTIONS: dict[str, tuple[int, int]] = {
    "n": (0, -1),
    "s": (0, 1),
    "e": (1, 0),
    "w": (-1, 0),
}


@dataclass(frozen=True)
class Theme:
    """Visual and combat configuration for a game theme."""

    id: str
    label: str
    description: str
    player_emoji: str
    enemy_emoji: str
    item_emoji: str
    exit_emoji: str
    floor_emoji: str
    player_hp: int
    player_atk: int
    enemy_hp: int
    enemy_atk: int
    item_hp: int


THEMES: dict[str, Theme] = {
    "dungeon": Theme(
        id="dungeon",
        label="Dungeon Crawler",
        description="Explore a stone dungeon, defeat its guardians, and find the exit.",
        player_emoji="\U0001f9d9",
        enemy_emoji="\U0001f409",
        item_emoji="\U0001f48e",
        exit_emoji="\U0001f6aa",
        floor_emoji=".",
        player_hp=20,
        player_atk=5,
        enemy_hp=8,
        enemy_atk=2,
        item_hp=5,
    ),
    "space": Theme(
        id="space",
        label="Space Explorer",
        description="Cross a hostile station, outgun the aliens, and reach the airlock.",
        player_emoji="\U0001f680",
        enemy_emoji="\U0001f47d",
        item_emoji="\u2b50",
        exit_emoji="\U0001f30c",
        floor_emoji=".",
        player_hp=15,
        player_atk=6,
        enemy_hp=10,
        enemy_atk=3,
        item_hp=4,
    ),
    "forest": Theme(
        id="forest",
        label="Forest Adventure",
        description="Navigate the deep woods, survive the wolves, and find the camp.",
        player_emoji="\U0001f333",
        enemy_emoji="\U0001f43a",
        item_emoji="\U0001f34e",
        exit_emoji="\u26fa",
        floor_emoji=".",
        player_hp=25,
        player_atk=4,
        enemy_hp=12,
        enemy_atk=1,
        item_hp=6,
    ),
    "cyberpunk": Theme(
        id="cyberpunk",
        label="Cyberpunk Hacker",
        description="Breach the mainframe, dodge security programs, and reach the core.",
        player_emoji="\U0001f916",
        enemy_emoji="\U0001f4bb",
        item_emoji="\U0001f50b",
        exit_emoji="\U0001f50c",
        floor_emoji=".",
        player_hp=18,
        player_atk=7,
        enemy_hp=9,
        enemy_atk=5,
        item_hp=3,
    ),
}

DEFAULT_THEME = "dungeon"


@dataclass(frozen=True)
class Cell:
    """An integer grid coordinate."""

    x: int
    y: int


@dataclass
class Level:
    """One dungeon floor. The tile grid is authoritative during play."""

    width: int
    height: int
    tiles: list[list[str]]
    start: Cell
    exit: Cell
    enemies: list[Cell]
    items: list[Cell]

    def to_dict(self) -> dict[str, Any]:
        return {
            "width": self.width,
            "height": self.height,
            "tiles": ["".join(row) for row in self.tiles],
            "start": {"x": self.start.x, "y": self.start.y},
            "exit": {"x": self.exit.x, "y": self.exit.y},
            "enemies": [{"x": cell.x, "y": cell.y} for cell in self.enemies],
            "items": [{"x": cell.x, "y": cell.y} for cell in self.items],
        }


@dataclass
class Player:
    """Mutable player statistics."""

    x: int
    y: int
    hp: int
    max_hp: int
    atk: int
    score: int = 0


@dataclass
class GameState:
    """A complete game session, including all three floors."""

    id: str
    seed: int
    theme_id: str
    width: int
    height: int
    levels: list[Level]
    player: Player
    level_index: int = 0
    turn: int = 0
    status: str = "playing"
    log: list[str] = field(default_factory=list)

    @property
    def level(self) -> Level:
        return self.levels[self.level_index]

    def to_dict(self) -> dict[str, Any]:
        theme = THEMES[self.theme_id]
        return {
            "id": self.id,
            "seed": self.seed,
            "theme": self.theme_id,
            "theme_label": theme.label,
            "level_index": self.level_index,
            "level_number": self.level_index + 1,
            "levels_total": len(self.levels),
            "level": self.level.to_dict(),
            "player": asdict(self.player),
            "turn": self.turn,
            "status": self.status,
            "log": list(self.log),
        }


@dataclass(frozen=True)
class MoveResult:
    """The outcome of one player action."""

    moved: bool
    message: str
    game_over: bool = False
    won: bool = False
    level_complete: bool = False
    combat: dict[str, int] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class _Rect:
    x: int
    y: int
    width: int
    height: int

    @property
    def center(self) -> Cell:
        return Cell(self.x + self.width // 2, self.y + self.height // 2)

    def overlaps(self, other: _Rect, margin: int = 1) -> bool:
        return not (
            self.x + self.width + margin <= other.x
            or other.x + other.width + margin <= self.x
            or self.y + self.height + margin <= other.y
            or other.y + other.height + margin <= self.y
        )


def _validate_dimensions(width: int, height: int) -> None:
    if not MIN_WIDTH <= width <= MAX_WIDTH:
        raise ValueError(f"width must be between {MIN_WIDTH} and {MAX_WIDTH}")
    if not MIN_HEIGHT <= height <= MAX_HEIGHT:
        raise ValueError(f"height must be between {MIN_HEIGHT} and {MAX_HEIGHT}")


def _carve_room(tiles: list[list[str]], room: _Rect) -> None:
    for y in range(room.y, room.y + room.height):
        for x in range(room.x, room.x + room.width):
            tiles[y][x] = FLOOR


def _carve_horizontal(tiles: list[list[str]], x1: int, x2: int, y: int) -> None:
    for x in range(min(x1, x2), max(x1, x2) + 1):
        tiles[y][x] = FLOOR


def _carve_vertical(tiles: list[list[str]], y1: int, y2: int, x: int) -> None:
    for y in range(min(y1, y2), max(y1, y2) + 1):
        tiles[y][x] = FLOOR


def _reachable(tiles: list[list[str]], start: Cell, target: Cell) -> bool:
    height, width = len(tiles), len(tiles[0])
    queue = [(start.x, start.y)]
    seen = {(start.x, start.y)}
    while queue:
        x, y = queue.pop(0)
        if (x, y) == (target.x, target.y):
            return True
        for dx, dy in DIRECTIONS.values():
            nx, ny = x + dx, y + dy
            if not (0 <= nx < width and 0 <= ny < height):
                continue
            if (nx, ny) in seen or tiles[ny][nx] == WALL:
                continue
            seen.add((nx, ny))
            queue.append((nx, ny))
    return False


def generate_level(seed: int, width: int = 20, height: int = 12) -> Level:
    """Generate a connected room-and-corridor level from a seed."""
    _validate_dimensions(width, height)
    rng = random.Random(seed)
    tiles = [[WALL for _ in range(width)] for _ in range(height)]

    target_rooms = max(3, min(8, (width * height) // 48))
    rooms: list[_Rect] = []
    for _ in range(120):
        if len(rooms) >= target_rooms:
            break
        room_width = rng.randint(3, min(8, width - 4))
        room_height = rng.randint(3, min(6, height - 4))
        room = _Rect(
            x=rng.randint(1, width - room_width - 2),
            y=rng.randint(1, height - room_height - 2),
            width=room_width,
            height=room_height,
        )
        if any(room.overlaps(existing) for existing in rooms):
            continue
        rooms.append(room)
        _carve_room(tiles, room)

    if not rooms:
        room = _Rect(1, 1, max(3, width - 2), max(3, height - 2))
        rooms.append(room)
        _carve_room(tiles, room)

    for previous, current in pairwise(rooms):
        if rng.random() < 0.5:
            _carve_horizontal(tiles, previous.center.x, current.center.x, previous.center.y)
            _carve_vertical(tiles, previous.center.y, current.center.y, current.center.x)
        else:
            _carve_vertical(tiles, previous.center.y, current.center.y, previous.center.x)
            _carve_horizontal(tiles, previous.center.x, current.center.x, current.center.y)

    start = rooms[0].center
    exit_cell = rooms[-1].center
    if start == exit_cell:
        floors = [Cell(x, y) for y in range(height) for x in range(width) if tiles[y][x] == FLOOR]
        exit_cell = max(floors, key=lambda cell: abs(cell.x - start.x) + abs(cell.y - start.y))

    if not _reachable(tiles, start, exit_cell):
        _carve_horizontal(tiles, start.x, exit_cell.x, start.y)
        _carve_vertical(tiles, start.y, exit_cell.y, exit_cell.x)

    available = [
        Cell(x, y)
        for y in range(height)
        for x in range(width)
        if tiles[y][x] == FLOOR and Cell(x, y) != start and Cell(x, y) != exit_cell
    ]
    rng.shuffle(available)

    enemy_count = max(1, len(available) // 12)
    item_count = max(1, len(available) // 20)
    while enemy_count + item_count > len(available):
        if enemy_count >= item_count and enemy_count > 1:
            enemy_count -= 1
        elif item_count > 1:
            item_count -= 1
        else:
            break

    enemies = available[:enemy_count]
    items = available[enemy_count : enemy_count + item_count]
    for cell in enemies:
        tiles[cell.y][cell.x] = ENEMY
    for cell in items:
        tiles[cell.y][cell.x] = ITEM
    tiles[exit_cell.y][exit_cell.x] = EXIT
    tiles[start.y][start.x] = PLAYER

    return Level(
        width=width,
        height=height,
        tiles=tiles,
        start=start,
        exit=exit_cell,
        enemies=enemies,
        items=items,
    )


def create_game(
    seed: int = 42,
    theme_id: str = DEFAULT_THEME,
    width: int = 20,
    height: int = 12,
) -> GameState:
    """Create a deterministic three-level game."""
    if theme_id not in THEMES:
        raise ValueError(f"unknown theme: {theme_id}")
    _validate_dimensions(width, height)

    levels = [
        generate_level(seed + index * 1000, width, height) for index in range(LEVELS_PER_GAME)
    ]
    theme = THEMES[theme_id]
    player = Player(
        x=levels[0].start.x,
        y=levels[0].start.y,
        hp=theme.player_hp,
        max_hp=theme.player_hp,
        atk=theme.player_atk,
    )
    state = GameState(
        id=uuid4().hex,
        seed=seed,
        theme_id=theme_id,
        width=width,
        height=height,
        levels=levels,
        player=player,
    )
    _append_log(
        state,
        f"Welcome to {theme.label}. Find the exit on all {LEVELS_PER_GAME} levels.",
    )
    return state


def _append_log(state: GameState, message: str) -> None:
    state.log.append(message)
    if len(state.log) > MAX_LOG_ENTRIES:
        del state.log[: len(state.log) - MAX_LOG_ENTRIES]


def _move_to(state: GameState, x: int, y: int) -> None:
    level = state.level
    level.tiles[state.player.y][state.player.x] = FLOOR
    level.tiles[y][x] = PLAYER
    state.player = replace(state.player, x=x, y=y)


def _resolve_combat(state: GameState, target: Cell) -> MoveResult:
    theme = THEMES[state.theme_id]
    rounds_needed = max(1, math.ceil(theme.enemy_hp / max(1, state.player.atk)))
    enemy_hits = max(0, rounds_needed - 1)
    damage_taken = enemy_hits * theme.enemy_atk

    state.player = replace(
        state.player,
        hp=max(0, state.player.hp - damage_taken),
        score=state.player.score + 10,
    )
    state.turn += 1
    _append_log(state, f"You strike {theme.enemy_emoji} {rounds_needed} time(s).")
    if damage_taken > 0:
        _append_log(state, f"{theme.enemy_emoji} hits back for {damage_taken} HP.")

    if state.player.hp <= 0:
        state.status = "lost"
        _append_log(state, "You died. The adventure ends here.")
        return MoveResult(
            moved=False,
            message="You died.",
            game_over=True,
            combat={"rounds": rounds_needed, "damage_taken": damage_taken},
        )

    state.level.enemies = [
        cell for cell in state.level.enemies if (cell.x, cell.y) != (target.x, target.y)
    ]
    _move_to(state, target.x, target.y)
    _append_log(state, "Enemy defeated. +10 score.")
    return MoveResult(
        moved=True,
        message=f"Slew {theme.enemy_emoji}.",
        combat={"rounds": rounds_needed, "damage_taken": damage_taken},
    )


def _pick_up_item(state: GameState, target: Cell) -> MoveResult:
    theme = THEMES[state.theme_id]
    healed = min(theme.item_hp, state.player.max_hp - state.player.hp)
    state.player = replace(
        state.player,
        hp=state.player.hp + healed,
        score=state.player.score + 5,
    )
    state.level.items = [
        cell for cell in state.level.items if (cell.x, cell.y) != (target.x, target.y)
    ]
    _move_to(state, target.x, target.y)
    state.turn += 1
    _append_log(state, f"Picked up {theme.item_emoji} (+{healed} HP, +5 score).")
    return MoveResult(moved=True, message=f"Picked up {theme.item_emoji} (+{healed} HP).")


def _take_exit(state: GameState) -> MoveResult:
    theme = THEMES[state.theme_id]
    state.level.tiles[state.player.y][state.player.x] = FLOOR
    state.turn += 1

    if state.level_index >= len(state.levels) - 1:
        state.status = "won"
        state.player = replace(state.player, score=state.player.score + 100)
        _append_log(state, "You reached the final exit. You win!")
        return MoveResult(moved=True, message="You won!", won=True)

    state.level_index += 1
    state.player = replace(
        state.player,
        x=state.level.start.x,
        y=state.level.start.y,
        hp=min(state.player.max_hp, state.player.hp + theme.item_hp * 2),
        score=state.player.score + 50,
    )
    state.level.tiles[state.player.y][state.player.x] = PLAYER
    _append_log(state, f"Level {state.level_index + 1}. +50 score and a small heal.")
    return MoveResult(
        moved=True,
        message=f"Level {state.level_index + 1}!",
        level_complete=True,
    )


def move_player(state: GameState, direction: str) -> MoveResult:
    """Apply one movement or interaction and return the outcome."""
    direction = direction.lower()
    if direction not in DIRECTIONS:
        raise ValueError("invalid direction")
    if state.status != "playing":
        return MoveResult(moved=False, message="Game over.")

    dx, dy = DIRECTIONS[direction]
    nx, ny = state.player.x + dx, state.player.y + dy
    if not (0 <= nx < state.level.width and 0 <= ny < state.level.height):
        return MoveResult(moved=False, message="The edge of the map blocks you.")

    target_tile = state.level.tiles[ny][nx]
    if target_tile == WALL:
        return MoveResult(moved=False, message="A wall blocks the path.")

    target = Cell(nx, ny)
    if target_tile == ENEMY:
        return _resolve_combat(state, target)
    if target_tile == ITEM:
        return _pick_up_item(state, target)
    if target_tile == EXIT:
        return _take_exit(state)

    _move_to(state, nx, ny)
    state.turn += 1
    _append_log(state, "You move.")
    return MoveResult(moved=True, message="You move.")


def _json_for_script(payload: Any) -> str:
    serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return (
        serialized.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def render_export_html(state: GameState) -> str:
    """Render a playable, fully offline HTML snapshot of the game."""
    theme = THEMES[state.theme_id]
    initial_levels = [
        generate_level(state.seed + index * 1000, state.width, state.height)
        for index in range(LEVELS_PER_GAME)
    ]
    initial_player = Player(
        x=initial_levels[0].start.x,
        y=initial_levels[0].start.y,
        hp=theme.player_hp,
        max_hp=theme.player_hp,
        atk=theme.player_atk,
    )

    payload = {
        "version": __version__,
        "id": state.id,
        "seed": state.seed,
        "theme": asdict(theme),
        "current": {
            "levels": [level.to_dict() for level in state.levels],
            "levelIndex": state.level_index,
            "player": asdict(state.player),
            "turn": state.turn,
            "status": state.status,
            "log": list(state.log),
        },
        "initial": {
            "levels": [level.to_dict() for level in initial_levels],
            "levelIndex": 0,
            "player": asdict(initial_player),
            "turn": 0,
            "status": "playing",
            "log": [f"Welcome to {theme.label}. Find the exit on all {LEVELS_PER_GAME} levels."],
        },
    }

    replacements = {
        "@@TITLE@@": html.escape(theme.label, quote=True),
        "@@DESCRIPTION@@": html.escape(theme.description, quote=True),
        "@@THEME_ID@@": html.escape(theme.id, quote=True),
        "@@SEED@@": str(state.seed),
        "@@VERSION@@": html.escape(__version__, quote=True),
        "@@GAME_JSON@@": _json_for_script(payload),
    }
    rendered = HTML_TEMPLATE
    for key, value in replacements.items():
        rendered = rendered.replace(key, value)
    return rendered


HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy"
      content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'">
<title>@@TITLE@@ - AI Game Developer</title>
<style>
  :root {
    color-scheme: dark;
    --bg: #070b16;
    --panel: #101a30;
    --panel-2: #16233f;
    --line: #26385f;
    --text: #e8eefc;
    --muted: #96a6c8;
    --accent: #5eead4;
    --gold: #fbbf24;
    --danger: #fb7185;
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; min-height: 100%; }
  body {
    background:
      radial-gradient(circle at 20% 0%, #16244a 0, transparent 42%),
      radial-gradient(circle at 100% 100%, #1d1735 0, transparent 40%),
      var(--bg);
    color: var(--text);
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    display: flex;
    justify-content: center;
    padding: 24px;
  }
  .shell { width: min(1100px, 100%); }
  .eyebrow {
    color: var(--accent);
    text-transform: uppercase;
    letter-spacing: .16em;
    font-size: 11px;
    margin: 0 0 8px;
  }
  h1 { font-size: clamp(24px, 4vw, 40px); margin: 0 0 8px; letter-spacing: -.02em; }
  h2 { margin: 0 0 12px; font-size: 14px; text-transform: uppercase; letter-spacing: .12em; color: var(--muted); }
  .lede { color: var(--muted); max-width: 72ch; line-height: 1.6; margin: 0 0 20px; }
  .hud { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 16px; }
  .stat {
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 10px;
    padding: 8px 12px;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: .08em;
    color: var(--muted);
  }
  .stat strong { color: var(--text); font-size: 14px; letter-spacing: 0; margin-left: 4px; }
  .stage { display: grid; grid-template-columns: minmax(0, 1fr) 300px; gap: 16px; align-items: start; }
  .map-wrap {
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 14px;
    padding: 12px;
    overflow: auto;
    min-height: 240px;
  }
  .map { --cell: 30px; display: grid; gap: 1px; width: max-content; margin: auto; }
  .cell {
    width: var(--cell);
    height: var(--cell);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    line-height: 1;
    border-radius: 3px;
    user-select: none;
  }
  .cell.wall { background: #1b2a4a; box-shadow: inset 0 0 0 1px #22365c; }
  .cell.floor { background: #0e1830; }
  .cell.player { box-shadow: 0 0 0 2px var(--accent), 0 0 16px rgba(94, 234, 212, .45); z-index: 1; }
  .cell.enemy { background: #2a1220; }
  .cell.item { background: #2a2412; }
  .cell.exit { background: #122a24; }
  .panel {
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 14px;
    padding: 16px;
  }
  #log {
    list-style: none;
    margin: 0 0 14px;
    padding: 0;
    max-height: 340px;
    overflow: auto;
    display: flex;
    flex-direction: column;
    gap: 8px;
    font-size: 12px;
    line-height: 1.45;
    color: var(--muted);
  }
  #log li { border-left: 2px solid var(--line); padding-left: 10px; }
  #log li:first-child { color: var(--text); border-color: var(--accent); }
  button {
    appearance: none;
    border: 1px solid var(--line);
    background: var(--panel-2);
    color: var(--text);
    border-radius: 9px;
    padding: 9px 14px;
    font: inherit;
    font-size: 12px;
    cursor: pointer;
    transition: border-color .15s ease, transform .15s ease;
  }
  button:hover { border-color: var(--accent); transform: translateY(-1px); }
  button:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  .controls { display: flex; align-items: center; gap: 18px; margin-top: 16px; flex-wrap: wrap; }
  .dpad { display: grid; grid-template-columns: repeat(3, 48px); grid-template-rows: repeat(3, 44px); gap: 6px; }
  .dpad button { padding: 0; font-size: 16px; }
  .dpad .up { grid-column: 2; grid-row: 1; }
  .dpad .left { grid-column: 1; grid-row: 2; }
  .dpad .down { grid-column: 2; grid-row: 3; }
  .dpad .right { grid-column: 3; grid-row: 2; }
  .hint { color: var(--muted); font-size: 12px; line-height: 1.6; margin: 0; max-width: 40ch; }
  footer { color: var(--muted); font-size: 11px; line-height: 1.6; margin-top: 20px; border-top: 1px solid var(--line); padding-top: 12px; }
  .overlay {
    position: fixed;
    inset: 0;
    background: rgba(4, 8, 18, .82);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
    z-index: 10;
    backdrop-filter: blur(4px);
  }
  .overlay.hidden { display: none; }
  .card {
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 16px;
    padding: 24px;
    width: min(420px, 100%);
    box-shadow: 0 24px 80px rgba(0, 0, 0, .55);
  }
  .card h2 { color: var(--text); font-size: 26px; text-transform: none; letter-spacing: -.02em; margin-bottom: 8px; }
  .card p { color: var(--muted); line-height: 1.6; }
  .won { color: var(--gold) !important; }
  .lost { color: var(--danger) !important; }
  @media (max-width: 820px) {
    body { padding: 14px; }
    .stage { grid-template-columns: 1fr; }
  }
  @media (max-width: 640px) {
    .map { --cell: 22px; }
    .cell { font-size: 14px; }
  }
</style>
</head>
<body>
<main class="shell">
  <header>
    <p class="eyebrow">AI Game Developer / standalone export</p>
    <h1>@@TITLE@@</h1>
    <p class="lede">
      @@DESCRIPTION@@ This snapshot is fully self-contained: the map, rules, and
      game state are embedded in this file, so it works offline with no server.
    </p>
  </header>

  <section class="hud" aria-label="Game status">
    <div class="stat">Level <strong><span id="level">1</span>/<span id="levels">3</span></strong></div>
    <div class="stat">HP <strong><span id="hp">0</span>/<span id="maxhp">0</span></strong></div>
    <div class="stat">Score <strong id="score">0</strong></div>
    <div class="stat">Turn <strong id="turn">0</strong></div>
    <div class="stat">Status <strong id="status">playing</strong></div>
  </section>

  <section class="stage">
    <div class="map-wrap">
      <div id="map" class="map" role="img" aria-label="Dungeon map"></div>
    </div>
    <aside class="panel" aria-label="Adventure log">
      <h2>Adventure log</h2>
      <ol id="log" aria-live="polite"></ol>
      <button id="reset" type="button">Reset to new game</button>
    </aside>
  </section>

  <section class="controls" aria-label="Controls">
    <div class="dpad">
      <button class="up" data-dir="n" type="button" aria-label="Move up">&uarr;</button>
      <button class="left" data-dir="w" type="button" aria-label="Move left">&larr;</button>
      <button class="right" data-dir="e" type="button" aria-label="Move right">&rarr;</button>
      <button class="down" data-dir="s" type="button" aria-label="Move down">&darr;</button>
    </div>
    <p class="hint">
      Use WASD or the arrow keys. Walk into enemies to fight, collect items to
      heal, and step on the exit to advance. Clear all three levels to win.
    </p>
  </section>

  <footer>
    Generated by AI Game Developer v@@VERSION@@ &middot; Theme: @@THEME_ID@@ &middot;
    Seed: @@SEED@@ &middot; No network access required.
  </footer>
</main>

<div id="overlay" class="overlay hidden" role="dialog" aria-modal="true" aria-labelledby="overlay-title">
  <div class="card">
    <p class="eyebrow">Adventure complete</p>
    <h2 id="overlay-title">Game over</h2>
    <p id="overlay-text"></p>
    <button id="overlay-action" type="button">Start a new game</button>
  </div>
</div>

<script>
const GAME = @@GAME_JSON@@;

(() => {
  "use strict";

  const DIRS = { n: [0, -1], s: [0, 1], e: [1, 0], w: [-1, 0] };
  const KEYMAP = {
    ArrowUp: "n", w: "n", W: "n",
    ArrowDown: "s", s: "s", S: "s",
    ArrowLeft: "w", a: "w", A: "w",
    ArrowRight: "e", d: "e", D: "e"
  };
  const SPRITES = {
    "@": GAME.theme.player_emoji,
    "E": GAME.theme.enemy_emoji,
    "I": GAME.theme.item_emoji,
    "X": GAME.theme.exit_emoji
  };

  const $ = (id) => document.getElementById(id);
  const els = {
    map: $("map"),
    log: $("log"),
    level: $("level"),
    levels: $("levels"),
    hp: $("hp"),
    maxhp: $("maxhp"),
    score: $("score"),
    turn: $("turn"),
    status: $("status"),
    overlay: $("overlay"),
    overlayTitle: $("overlay-title"),
    overlayText: $("overlay-text")
  };

  let state;

  function cloneLevels(levels) {
    return levels.map((level) => ({
      width: level.width,
      height: level.height,
      tiles: level.tiles.map((row) => row.split("")),
      start: { ...level.start },
      exit: { ...level.exit },
      enemies: level.enemies.map((cell) => ({ ...cell })),
      items: level.items.map((cell) => ({ ...cell }))
    }));
  }

  function buildState(source) {
    return {
      levels: cloneLevels(source.levels),
      levelIndex: source.levelIndex,
      player: { ...source.player },
      turn: source.turn,
      status: source.status,
      log: source.log.slice()
    };
  }

  function currentLevel() {
    return state.levels[state.levelIndex];
  }

  function addLog(message) {
    state.log.push(message);
    if (state.log.length > 60) {
      state.log.splice(0, state.log.length - 60);
    }
  }

  function renderMap() {
    const level = currentLevel();
    els.map.style.gridTemplateColumns = `repeat(${level.width}, var(--cell))`;
    const fragment = document.createDocumentFragment();
    for (let y = 0; y < level.height; y += 1) {
      for (let x = 0; x < level.width; x += 1) {
        const tile = level.tiles[y][x];
        const cell = document.createElement("div");
        cell.className = "cell " + (tile === "#" ? "wall" : "floor");
        if (tile === "@") cell.classList.add("player");
        if (tile === "E") cell.classList.add("enemy");
        if (tile === "I") cell.classList.add("item");
        if (tile === "X") cell.classList.add("exit");
        if (SPRITES[tile]) cell.textContent = SPRITES[tile];
        fragment.appendChild(cell);
      }
    }
    els.map.replaceChildren(fragment);
  }

  function renderHud() {
    els.level.textContent = String(state.levelIndex + 1);
    els.levels.textContent = String(state.levels.length);
    els.hp.textContent = String(Math.max(0, state.player.hp));
    els.maxhp.textContent = String(state.player.max_hp);
    els.score.textContent = String(state.player.score);
    els.turn.textContent = String(state.turn);
    els.status.textContent = state.status === "playing" ? "in progress" : state.status;
  }

  function renderLog() {
    const recent = state.log.slice(-12).reverse();
    const items = recent.map((message) => {
      const item = document.createElement("li");
      item.textContent = message;
      return item;
    });
    els.log.replaceChildren(...items);
  }

  function render() {
    renderMap();
    renderHud();
    renderLog();
  }

  function showOverlay(title, text, tone) {
    els.overlayTitle.textContent = title;
    els.overlayTitle.className = tone || "";
    els.overlayText.textContent = text;
    els.overlay.classList.remove("hidden");
    $("overlay-action").focus();
  }

  function stepTo(x, y, message) {
    const level = currentLevel();
    level.tiles[state.player.y][state.player.x] = ".";
    state.player.x = x;
    state.player.y = y;
    level.tiles[y][x] = "@";
    state.turn += 1;
    addLog(message);
    render();
  }

  function resolveCombat(x, y) {
    const level = currentLevel();
    const theme = GAME.theme;
    const rounds = Math.max(1, Math.ceil(theme.enemy_hp / Math.max(1, state.player.atk)));
    const hits = Math.max(0, rounds - 1);
    const damage = hits * theme.enemy_atk;

    addLog(`You strike ${theme.enemy_emoji} ${rounds} time(s).`);
    if (damage > 0) {
      addLog(`${theme.enemy_emoji} hits back for ${damage} HP.`);
    }
    state.player.hp -= damage;
    state.player.score += 10;

    if (state.player.hp <= 0) {
      state.player.hp = 0;
      state.status = "lost";
      addLog("You died. The adventure ends here.");
      render();
      showOverlay(
        "Game over",
        `You scored ${state.player.score} points on level ${state.levelIndex + 1}.`,
        "lost"
      );
      return;
    }

    level.enemies = level.enemies.filter((cell) => cell.x !== x || cell.y !== y);
    level.tiles[state.player.y][state.player.x] = ".";
    state.player.x = x;
    state.player.y = y;
    level.tiles[y][x] = "@";
    state.turn += 1;
    addLog("Enemy defeated. +10 score.");
    render();
  }

  function pickUpItem(x, y) {
    const level = currentLevel();
    const theme = GAME.theme;
    const healed = Math.min(theme.item_hp, state.player.max_hp - state.player.hp);
    state.player.hp += healed;
    state.player.score += 5;
    level.items = level.items.filter((cell) => cell.x !== x || cell.y !== y);
    stepTo(x, y, `Picked up ${theme.item_emoji} (+${healed} HP, +5 score).`);
  }

  function takeExit() {
    const level = currentLevel();
    level.tiles[state.player.y][state.player.x] = ".";
    state.turn += 1;

    if (state.levelIndex >= state.levels.length - 1) {
      state.status = "won";
      state.player.score += 100;
      addLog("You reached the final exit. You win!");
      render();
      showOverlay(
        "You won",
        `Final score: ${state.player.score}. Every level is complete.`,
        "won"
      );
      return;
    }

    state.levelIndex += 1;
    const next = currentLevel();
    state.player.hp = Math.min(
      state.player.max_hp,
      state.player.hp + GAME.theme.item_hp * 2
    );
    state.player.score += 50;
    state.player.x = next.start.x;
    state.player.y = next.start.y;
    next.tiles[state.player.y][state.player.x] = "@";
    addLog(`Level ${state.levelIndex + 1}. +50 score and a small heal.`);
    render();
  }

  function move(direction) {
    if (state.status !== "playing") return;
    const delta = DIRS[direction];
    if (!delta) return;

    const level = currentLevel();
    const x = state.player.x + delta[0];
    const y = state.player.y + delta[1];

    if (x < 0 || y < 0 || x >= level.width || y >= level.height) {
      addLog("The edge of the map blocks you.");
      render();
      return;
    }

    const tile = level.tiles[y][x];
    if (tile === "#") {
      addLog("A wall blocks the path.");
      render();
      return;
    }
    if (tile === "E") {
      resolveCombat(x, y);
      return;
    }
    if (tile === "I") {
      pickUpItem(x, y);
      return;
    }
    if (tile === "X") {
      takeExit();
      return;
    }
    stepTo(x, y, "You move.");
  }

  function reset() {
    state = buildState(GAME.initial);
    els.overlay.classList.add("hidden");
    render();
  }

  document.addEventListener("keydown", (event) => {
    const direction = KEYMAP[event.key];
    if (!direction) return;
    event.preventDefault();
    move(direction);
  });

  document.querySelectorAll("[data-dir]").forEach((button) => {
    button.addEventListener("click", () => move(button.dataset.dir));
  });
  $("reset").addEventListener("click", reset);
  $("overlay-action").addEventListener("click", reset);

  state = buildState(GAME.current);
  render();
  if (state.status === "won") {
    showOverlay(
      "You won",
      `Final score: ${state.player.score}. Every level is complete.`,
      "won"
    );
  } else if (state.status === "lost") {
    showOverlay(
      "Game over",
      `You scored ${state.player.score} points on level ${state.levelIndex + 1}.`,
      "lost"
    );
  }
})();
</script>
</body>
</html>
"""


class NewGameIn(BaseModel):
    """Request body for creating a game."""

    seed: int = Field(default=42, ge=0, le=2**32 - 1)
    theme: Literal["dungeon", "space", "forest", "cyberpunk"] = DEFAULT_THEME
    width: int = Field(default=20, ge=MIN_WIDTH, le=MAX_WIDTH)
    height: int = Field(default=12, ge=MIN_HEIGHT, le=MAX_HEIGHT)


class MoveIn(BaseModel):
    """Request body for a player move."""

    direction: str = Field(pattern=r"^[nsewNSEW]$")


GAMES: dict[str, GameState] = {}
GAMES_LOCK = threading.Lock()

app = FastAPI(
    title="AI Game Developer",
    version=__version__,
    description=(
        "Generate deterministic dungeon-crawler prototypes and export each one "
        "as a fully playable, self-contained HTML file."
    ),
)


def run() -> None:
    """Run the API with uvicorn (used by the ``ai-game`` console script)."""
    import uvicorn

    uvicorn.run("three_ai_suite.game:app", host="127.0.0.1", port=8000, reload=False)


def _get_game(game_id: str) -> GameState:
    state = GAMES.get(game_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Game not found")
    return state


@app.get("/")
def index() -> dict[str, Any]:
    return {
        "name": "AI Game Developer",
        "version": __version__,
        "docs": "/docs",
        "health": "/health",
        "themes": "/themes",
    }


@app.get("/health")
def health() -> dict[str, Any]:
    with GAMES_LOCK:
        active = len(GAMES)
    return {
        "status": "ok",
        "version": __version__,
        "active_games": active,
        "max_games": MAX_GAMES,
    }


@app.get("/themes")
def list_themes() -> list[dict[str, Any]]:
    return [
        {
            "id": theme.id,
            "label": theme.label,
            "description": theme.description,
            "stats": {
                "player_hp": theme.player_hp,
                "player_atk": theme.player_atk,
                "enemy_hp": theme.enemy_hp,
                "enemy_atk": theme.enemy_atk,
                "item_hp": theme.item_hp,
            },
        }
        for theme in THEMES.values()
    ]


@app.post("/games", status_code=201)
def create_game_endpoint(payload: NewGameIn) -> dict[str, Any]:
    try:
        state = create_game(
            seed=payload.seed,
            theme_id=payload.theme,
            width=payload.width,
            height=payload.height,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    with GAMES_LOCK:
        if len(GAMES) >= MAX_GAMES:
            GAMES.pop(next(iter(GAMES)))
        GAMES[state.id] = state
    return state.to_dict()


@app.get("/games/{game_id}")
def get_game(game_id: str) -> dict[str, Any]:
    with GAMES_LOCK:
        state = _get_game(game_id)
        return state.to_dict()


@app.post("/games/{game_id}/move")
def move_endpoint(game_id: str, payload: MoveIn) -> dict[str, Any]:
    with GAMES_LOCK:
        state = _get_game(game_id)
        try:
            result = move_player(state, payload.direction)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"result": result.to_dict(), "game": state.to_dict()}


@app.delete("/games/{game_id}")
def delete_game(game_id: str) -> dict[str, str]:
    with GAMES_LOCK:
        if GAMES.pop(game_id, None) is None:
            raise HTTPException(status_code=404, detail="Game not found")
    return {"deleted": game_id}


@app.get("/games/{game_id}/export", response_class=HTMLResponse)
def export_game(game_id: str, download: bool = True) -> HTMLResponse:
    with GAMES_LOCK:
        state = _get_game(game_id)
        document = render_export_html(state)

    filename = f"{state.theme_id}-{state.id[:8]}.html"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'} if download else {}
    return HTMLResponse(content=document, headers=headers)
