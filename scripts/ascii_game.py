#!/usr/bin/env python3
"""Update and render the collaborative ASCII game in the profile README."""

from __future__ import annotations

import html
import json
import sys
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / ".game-state.json"
SVG_PATH = ROOT / "assets" / "game.svg"

WIDTH, HEIGHT = 31, 13
START = (2, 2)
GOAL = (28, 2)
NODES = ((11, 2), (19, 6), (27, 10))
MOVES = {
    "up": (0, -1),
    "down": (0, 1),
    "left": (-1, 0),
    "right": (1, 0),
}


def make_walls() -> set[tuple[int, int]]:
    walls = {
        (x, y)
        for y in range(HEIGHT)
        for x in range(WIDTH)
        if x in (0, WIDTH - 1) or y in (0, HEIGHT - 1)
    }
    walls.update((7, y) for y in range(1, 11) if y != 6)
    walls.update((15, y) for y in range(2, 12) if y not in (4, 9))
    walls.update((23, y) for y in range(1, 11) if y not in (3, 8))
    walls.update((x, 4) for x in range(1, 7) if x != 3)
    walls.update((x, 8) for x in range(8, 15) if x != 11)
    walls.update((x, 6) for x in range(16, 23) if x != 19)
    walls.update((x, 10) for x in range(16, 23) if x != 20)
    return walls


WALLS = make_walls()


def fresh_state(wins: int = 0) -> dict:
    return {
        "player": list(START),
        "collected": [],
        "moves": 0,
        "wins": wins,
        "status": "Find 3 signal nodes, then reach the uplink.",
    }


def load_state() -> dict:
    try:
        state = json.loads(STATE_PATH.read_text())
        position = tuple(state["player"])
        if position in WALLS or not (0 <= position[0] < WIDTH and 0 <= position[1] < HEIGHT):
            raise ValueError("player is outside the maze")
        return state
    except (FileNotFoundError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return fresh_state()


def apply_move(state: dict, command: str) -> dict:
    if command == "restart":
        return fresh_state(int(state.get("wins", 0)))
    if command == "render":
        return state
    if command not in MOVES:
        raise ValueError(f"unsupported game command: {command[:24]}")

    dx, dy = MOVES[command]
    x, y = state["player"]
    target = (x + dx, y + dy)
    state["moves"] = int(state.get("moves", 0)) + 1

    if target in WALLS:
        state["status"] = "Wall detected. Try another direction."
        return state

    state["player"] = list(target)
    collected = {tuple(node) for node in state.get("collected", [])}
    if target in NODES and target not in collected:
        collected.add(target)
        state["collected"] = [list(node) for node in sorted(collected)]
        state["status"] = f"Signal node captured: {len(collected)}/3."
    elif target == GOAL and len(collected) == len(NODES):
        state["wins"] = int(state.get("wins", 0)) + 1
        state["status"] = "UPLINK COMPLETE — you connected the system!"
    elif target == GOAL:
        state["status"] = f"Uplink locked. {len(NODES) - len(collected)} node(s) remain."
    else:
        state["status"] = "Scanning… keep moving."
    return state


def board_lines(state: dict) -> list[str]:
    player = tuple(state["player"])
    collected = {tuple(node) for node in state.get("collected", [])}
    lines: list[str] = []
    for y in range(HEIGHT):
        line = []
        for x in range(WIDTH):
            point = (x, y)
            if point == player:
                char = "@"
            elif point == GOAL:
                char = "X"
            elif point in NODES and point not in collected:
                char = "*"
            elif point in WALLS:
                char = "#"
            else:
                char = "."
            line.append(char)
        lines.append("".join(line))
    return lines


def styled_line(line: str) -> str:
    colors = {"#": "#344054", ".": "#273244", "@": "#4df7c8", "*": "#ffd166", "X": "#cb7cff"}
    chunks: list[str] = []
    current_color = None
    buffer = ""
    for char in line:
        color = colors[char]
        if color != current_color and buffer:
            chunks.append(f'<tspan fill="{current_color}">{html.escape(buffer)}</tspan>')
            buffer = ""
        current_color = color
        buffer += char
    if buffer:
        chunks.append(f'<tspan fill="{current_color}">{html.escape(buffer)}</tspan>')
    return "".join(chunks)


def render_svg(state: dict) -> str:
    captured = len(state.get("collected", []))
    moves = int(state.get("moves", 0))
    wins = int(state.get("wins", 0))
    status = html.escape(str(state.get("status", "")))
    rows = []
    for index, line in enumerate(board_lines(state)):
        rows.append(f'<text x="50" y="{105 + index * 19}" class="maze">{styled_line(line)}</text>')

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="420" viewBox="0 0 900 420" role="img" aria-labelledby="title desc">
  <title id="title">Signal Runner collaborative ASCII game</title>
  <desc id="desc">The player is at {state["player"]}. {captured} of 3 nodes collected after {moves} moves.</desc>
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#070a12"/><stop offset="1" stop-color="#0b1520"/></linearGradient>
    <filter id="glow"><feGaussianBlur stdDeviation="2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
    <style>
      text {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
      .maze {{ font-size: 16px; letter-spacing: 4px; }}
      .label {{ fill: #667085; font-size: 12px; letter-spacing: 1px; }}
      .value {{ fill: #d0d5dd; font-size: 14px; }}
    </style>
  </defs>
  <rect width="900" height="420" rx="16" fill="url(#bg)"/>
  <rect x="1" y="1" width="898" height="418" rx="15" fill="none" stroke="#29364a"/>
  <text x="42" y="39" fill="#4df7c8" font-size="15" font-weight="700">SIGNAL_RUNNER.exe</text>
  <text x="858" y="39" text-anchor="end" class="label">LIVE COMMUNITY STATE</text>
  <path d="M40 57H860" stroke="#263247"/>
  <g filter="url(#glow)">{''.join(rows)}</g>
  <g transform="translate(610 91)">
    <text class="label">MISSION</text>
    <text y="28" class="value">capture * * * → reach X</text>
    <text y="72" class="label">TELEMETRY</text>
    <text y="100" class="value">nodes  {captured}/3</text>
    <text y="126" class="value">moves  {moves}</text>
    <text y="152" class="value">wins   {wins}</text>
    <text y="198" class="label">LEGEND</text>
    <text y="226" fill="#4df7c8" font-size="14">@  you</text>
    <text y="250" fill="#ffd166" font-size="14">*  signal node</text>
    <text y="274" fill="#cb7cff" font-size="14">X  uplink</text>
    <circle cx="228" cy="-3" r="4" fill="#4df7c8"><animate attributeName="opacity" values="1;.15;1" dur="1.2s" repeatCount="indefinite"/></circle>
  </g>
  <path d="M40 373H860" stroke="#263247"/>
  <text x="42" y="400" fill="#8a94a7" font-size="13">&gt; {status}</text>
</svg>
'''


def reachable(start: tuple[int, int]) -> set[tuple[int, int]]:
    seen = {start}
    queue = deque([start])
    while queue:
        x, y = queue.popleft()
        for dx, dy in MOVES.values():
            point = (x + dx, y + dy)
            if point not in WALLS and point not in seen:
                seen.add(point)
                queue.append(point)
    return seen


def main() -> None:
    command = (sys.argv[1] if len(sys.argv) > 1 else "render").lower()
    command = command.removeprefix("ascii-game:").strip()
    state = apply_move(load_state(), command)
    required = set(NODES) | {GOAL}
    if not required.issubset(reachable(START)):
        raise RuntimeError("maze contains an unreachable objective")
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n")
    SVG_PATH.parent.mkdir(parents=True, exist_ok=True)
    SVG_PATH.write_text(render_svg(state))
    print(state["status"])


if __name__ == "__main__":
    main()
