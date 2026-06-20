from pathlib import Path

import pytest

from flight_sequence.models import Visit, load_problem, route_cost
from flight_sequence.solver import solve_basic


ROOT = Path(__file__).resolve().parents[1]


def test_package_smoke() -> None:
    problem = load_problem(ROOT / "data" / "sample_small.json")

    route = solve_basic(problem)

    assert len(route.visits) == len(problem.areas)
    assert route.cost == pytest.approx(route_cost(problem, route.visits, closed_loop=False))


def test_cost_model_smoke() -> None:
    problem = load_problem(ROOT / "data" / "sample_small.json")
    input_order = tuple(Visit(area.id) for area in problem.areas)

    assert route_cost(problem, input_order, closed_loop=False) > 0
