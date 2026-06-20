"""Algorithmic and contract tests for the area-sequencing solvers."""

from itertools import permutations
from math import hypot
from pathlib import Path

import pytest

from flight_sequence.models import Area, Problem, Visit, load_problem, route_cost
from flight_sequence.solver import (
    solve_basic,
    solve_closed_loop,
    solve_large,
    solve_with_flips,
)


ROOT = Path(__file__).resolve().parents[1]


def _problem(name: str, areas: tuple[Area, ...]) -> Problem:
    """Build a baseline problem without irrelevant polygon geometry."""
    return Problem(name=name, areas=areas)


def _area(area_id: str, entry: tuple[float, float], exit_: tuple[float, float]) -> Area:
    """Build a synthetic fixed-direction area from its relevant endpoints."""
    return Area(id=area_id, polygon=(), entry=entry, exit=exit_)


def _brute_force_optimum(problem: Problem) -> tuple[float, tuple[str, ...]]:
    """Exhaustively solve the open path without relying on solver internals."""

    def transition_cost(order: tuple[Area, ...]) -> float:
        return sum(
            hypot(current.exit[0] - next_.entry[0], current.exit[1] - next_.entry[1])
            for current, next_ in zip(order, order[1:])
        )

    best_order = min(permutations(problem.areas), key=transition_cost)
    return transition_cost(best_order), tuple(area.id for area in best_order)


ORACLE_PROBLEMS = (
    _problem(
        "four_area_directed_chain",
        (
            _area("C", (4.0, 9.0), (-3.0, 12.0)),
            _area("A", (-100.0, -100.0), (0.0, 0.0)),
            _area("D", (-4.0, 12.0), (100.0, 100.0)),
            _area("B", (1.0, 0.0), (4.0, 8.0)),
        ),
    ),
    _problem(
        "five_area_criss_cross",
        (
            _area("C", (2.0, 9.0), (12.0, 7.0)),
            _area("A", (-50.0, -50.0), (8.0, 1.0)),
            _area("E", (-1.0, 4.0), (50.0, 50.0)),
            _area("B", (9.0, 1.0), (2.0, 8.0)),
            _area("D", (13.0, 7.0), (-2.0, 4.0)),
        ),
    ),
    _problem(
        "six_area_irregular_chain",
        (
            _area("D", (-4.0, 12.0), (-10.0, 5.0)),
            _area("B", (1.0, 0.0), (4.0, 8.0)),
            _area("F", (-4.0, -2.0), (100.0, 100.0)),
            _area("A", (-100.0, -100.0), (0.0, 0.0)),
            _area("E", (-10.0, 4.0), (-5.0, -2.0)),
            _area("C", (4.0, 9.0), (-3.0, 12.0)),
        ),
    ),
    _problem(
        "seven_area_non_monotonic_geometry",
        (
            _area("G", (3.0, -5.0), (80.0, -80.0)),
            _area("C", (8.0, 9.0), (-2.0, 14.0)),
            _area("A", (-80.0, 80.0), (1.0, 1.0)),
            _area("F", (-8.0, -4.0), (2.0, -5.0)),
            _area("D", (-3.0, 14.0), (-12.0, 3.0)),
            _area("B", (2.0, 1.0), (8.0, 8.0)),
            _area("E", (-12.0, 2.0), (-9.0, -4.0)),
        ),
    ),
)


class TestCorrectnessAgainstBruteForce:
    """Compare the dynamic program with an independent exact oracle."""

    @pytest.mark.parametrize("problem", ORACLE_PROBLEMS, ids=lambda problem: problem.name)
    def test_solve_basic_matches_exhaustive_search_on_handcrafted_problems(
        self, problem: Problem
    ) -> None:
        """Small exhaustive cases establish global optimality beyond public fixtures."""
        oracle_cost, _ = _brute_force_optimum(problem)

        route = solve_basic(problem)

        assert route.cost == pytest.approx(oracle_cost)


class TestFixtureRegressions:
    """Lock down the exact results claimed in the submission notes."""

    def test_sample_small_has_the_claimed_optimal_cost_and_order(self) -> None:
        """The tiny fixture has a human-auditable unique left-to-right optimum."""
        problem = load_problem(ROOT / "data" / "sample_small.json")

        route = solve_basic(problem)

        assert route.cost == pytest.approx(4.0)
        assert tuple(visit.area_id for visit in route.visits) == (
            "A",
            "B",
            "C",
            "D",
            "E",
        )

    def test_mission_14_has_the_claimed_exact_cost(self) -> None:
        """The main fixture regression backs the optimization result in NOTES.md."""
        problem = load_problem(ROOT / "data" / "mission_14.json")

        route = solve_basic(problem)

        assert route.cost == pytest.approx(76.28690880558122)


class TestBaselineContractCompliance:
    """Exercise the public route contract across every tractable fixture."""

    @pytest.mark.parametrize(
        "fixture_name",
        (
            "sample_small.json",
            "mission_14.json",
            "direction_choices.json",
            "mission_14_home.json",
        ),
    )
    def test_every_basic_route_contains_each_area_once_without_flips_and_validates(
        self, fixture_name: str
    ) -> None:
        """Flags on optional fixtures must not leak flips or home legs into baseline mode."""
        problem = load_problem(ROOT / "data" / fixture_name)

        route = solve_basic(problem)
        input_ids = tuple(area.id for area in problem.areas)
        output_ids = tuple(visit.area_id for visit in route.visits)

        assert len(output_ids) == len(input_ids)
        assert set(output_ids) == set(input_ids)
        assert all(visit.flipped is False for visit in route.visits)

        # This call is also the authoritative validation for duplicates, missing
        # areas, and unknown IDs: any malformed route raises before the assertion.
        validated_cost = route_cost(problem, route.visits, closed_loop=False)
        assert route.cost == pytest.approx(validated_cost)


class TestImprovementOverInputOrder:
    """Prove the solver optimizes rather than echoing fixture order."""

    @pytest.mark.parametrize("fixture_name", ("sample_small.json", "mission_14.json"))
    def test_solve_basic_beats_the_deliberately_suboptimal_input_order(
        self, fixture_name: str
    ) -> None:
        """Both baseline fixtures are arranged so preserving their order wastes travel."""
        problem = load_problem(ROOT / "data" / fixture_name)
        input_order = tuple(Visit(area.id) for area in problem.areas)

        route = solve_basic(problem)
        input_cost = route_cost(problem, input_order, closed_loop=False)

        assert route.cost < input_cost


class TestEdgeCases:
    """Define behavior at small cardinalities and degenerate geometry."""

    def test_empty_problem_returns_an_empty_zero_cost_route(self) -> None:
        """The no-area identity case should agree with route_cost's zero behavior."""
        problem = _problem("empty", ())

        route = solve_basic(problem)

        assert route.visits == ()
        assert route.cost == pytest.approx(0.0)

    def test_single_area_has_no_deadhead_cost(self) -> None:
        """An open route pays neither the first entry nor the final exit leg."""
        problem = _problem(
            "single",
            (_area("only", (-100.0, 4.0), (200.0, -9.0)),),
        )

        route = solve_basic(problem)

        assert route.visits == (Visit("only", flipped=False),)
        assert route.cost == pytest.approx(0.0)

    def test_two_areas_are_visited_in_the_cheaper_directed_order(self) -> None:
        """With two areas, asymmetric endpoints still determine route direction."""
        problem = _problem(
            "two_directed_areas",
            (
                _area("B", (2.0, 0.0), (50.0, 0.0)),
                _area("A", (0.0, 0.0), (0.0, 0.0)),
            ),
        )

        route = solve_basic(problem)

        assert route.visits == (Visit("A"), Visit("B"))
        assert route.cost == pytest.approx(2.0)

    def test_repeated_coordinates_allow_zero_cost_transitions(self) -> None:
        """Coincident exits and entries are valid geometry, not duplicate areas."""
        problem = _problem(
            "coincident_endpoints",
            (
                _area("C", (2.0, 2.0), (-100.0, -100.0)),
                _area("A", (100.0, 100.0), (1.0, 1.0)),
                _area("B", (1.0, 1.0), (2.0, 2.0)),
            ),
        )

        route = solve_basic(problem)

        assert route.visits == (Visit("A"), Visit("B"), Visit("C"))
        assert route.cost == pytest.approx(0.0)


class TestDeterminism:
    """Require stable tie resolution from identical solver inputs."""

    def test_repeated_calls_return_identical_routes_when_every_order_ties(self) -> None:
        """All-zero geometry catches accidental dependence on unordered iteration."""
        problem = _problem(
            "all_orders_tie",
            tuple(_area(area_id, (0.0, 0.0), (0.0, 0.0)) for area_id in "ABCDE"),
        )

        first = solve_basic(problem)
        second = solve_basic(problem)

        assert first.visits == second.visits
        assert first.cost == pytest.approx(second.cost)


class TestAsymmetricTransitionCosts:
    """Target the distinction between directed transitions and symmetric TSP edges."""

    def test_solver_prefers_the_cheap_direction_when_the_reverse_is_expensive(self) -> None:
        """Free boundaries cannot justify reversing a strongly directed three-area path."""
        problem = _problem(
            "strongly_asymmetric",
            (
                _area("C", (11.0, 0.0), (-100.0, -100.0)),
                _area("B", (1.0, 0.0), (10.0, 0.0)),
                _area("A", (100.0, 100.0), (0.0, 0.0)),
            ),
        )
        reverse = (Visit("C"), Visit("B"), Visit("A"))

        route = solve_basic(problem)
        reverse_cost = route_cost(problem, reverse, closed_loop=False)

        assert route.visits == (Visit("A"), Visit("B"), Visit("C"))
        assert route.cost == pytest.approx(2.0)
        assert route.cost < reverse_cost / 100.0


class TestOptionalExtensions:
    """Validate the implemented optional solver APIs on their fixtures."""

    def test_solve_with_flips_chooses_the_optimal_orientation(self) -> None:
        """Direction choices must achieve the fixture's known optimum."""
        problem = load_problem(ROOT / "data" / "direction_choices.json")

        route = solve_with_flips(problem)

        assert route.cost == pytest.approx(2.0)

    def test_solve_closed_loop_includes_both_home_legs(self) -> None:
        """Closed-loop routing must include both legs to and from home."""
        problem = load_problem(ROOT / "data" / "mission_14_home.json")

        route = solve_closed_loop(problem)

        assert route.cost == pytest.approx(94.28590952224741)

    def test_solve_large_returns_a_valid_route_for_the_26_area_fixture(self) -> None:
        """The exact MILP route must satisfy the authoritative cost model."""
        problem = load_problem(ROOT / "data" / "large_areas.json")

        route = solve_large(problem)

        assert route.cost == pytest.approx(
            route_cost(problem, route.visits, closed_loop=False)
        )
