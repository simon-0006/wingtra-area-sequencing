from __future__ import annotations

from dataclasses import dataclass
import json
from math import hypot
from pathlib import Path
from typing import Iterable

Point = tuple[float, float]


@dataclass(frozen=True)
class Area:
    id: str
    polygon: tuple[Point, ...]
    entry: Point
    exit: Point


@dataclass(frozen=True)
class Problem:
    name: str
    areas: tuple[Area, ...]
    allow_flips: bool = False
    closed_loop: bool = False
    home: Point | None = None


@dataclass(frozen=True)
class Visit:
    area_id: str
    flipped: bool = False


@dataclass(frozen=True)
class Route:
    visits: tuple[Visit, ...]
    cost: float


def load_problem(path: str | Path) -> Problem:
    with Path(path).open() as f:
        raw = json.load(f)

    areas = tuple(
        Area(
            id=str(item["id"]),
            polygon=tuple(_point(p) for p in item.get("polygon", ())),
            entry=_point(item["entry"]),
            exit=_point(item["exit"]),
        )
        for item in raw["areas"]
    )

    home = _point(raw["home"]) if raw.get("home") is not None else None
    return Problem(
        name=str(raw.get("name", Path(path).stem)),
        areas=areas,
        allow_flips=bool(raw.get("allow_flips", False)),
        closed_loop=bool(raw.get("closed_loop", False)),
        home=home,
    )


def route_cost(
    problem: Problem,
    visits: Iterable[Visit],
    *,
    closed_loop: bool | None = None,
) -> float:
    visits = tuple(visits)
    if not visits:
        return 0.0

    closed = problem.closed_loop if closed_loop is None else closed_loop
    by_id = {area.id: area for area in problem.areas}
    seen: set[str] = set()

    total = 0.0
    previous_exit: Point | None = None

    if closed:
        if problem.home is None:
            raise ValueError("closed_loop route requires problem.home")
        previous_exit = problem.home

    for visit in visits:
        if visit.area_id in seen:
            raise ValueError(f"area visited more than once: {visit.area_id}")
        seen.add(visit.area_id)

        area = by_id[visit.area_id]
        entry, exit_ = endpoints(area, visit.flipped)
        if previous_exit is not None:
            total += distance(previous_exit, entry)
        previous_exit = exit_

    if seen != set(by_id):
        missing = sorted(set(by_id) - seen)
        raise ValueError(f"route is missing areas: {missing}")

    if closed:
        total += distance(previous_exit, problem.home)  # type: ignore[arg-type]

    return total


def endpoints(area: Area, flipped: bool = False) -> tuple[Point, Point]:
    if flipped:
        return area.exit, area.entry
    return area.entry, area.exit


def distance(a: Point, b: Point) -> float:
    return hypot(a[0] - b[0], a[1] - b[1])


def _point(value: object) -> Point:
    if not isinstance(value, list | tuple) or len(value) != 2:
        raise ValueError(f"expected [x, y] point, got {value!r}")
    return float(value[0]), float(value[1])
