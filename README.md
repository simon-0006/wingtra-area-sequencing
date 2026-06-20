# Flight Area Sequencing Work Sample

This is a 2-3 hour Python take-home exercise.

You are given a set of already-planned survey areas. Each area has:

- endpoint coordinates nominated by an upstream planner
- a polygon outline, included for context only

The internal coverage path for each area is already planned by another system. Your task is to turn the area list into a good flight order.

## Core Task

Implement `solve_basic(problem)` in `flight_sequence/solver.py`.

For the baseline task:

- every area must be visited exactly once
- use the endpoints as provided in the fixture
- do not use a takeoff or landing point unless the fixture explicitly asks for one
- use the package's model helpers to evaluate route cost

Return a `Route` whose `visits` list contains one visit per area and whose `cost` is consistent with the package cost model.

Use `data/mission_14.json` as the main fixture for the baseline task. `data/sample_small.json` is intentionally tiny and exists mainly for smoke tests and quick CLI checks.

The included tests are smoke checks only. They are not intended to prove that your route choice is good. Add tests you think are appropriate and document how you validated your approach.

## Optional Extensions

These are not required for a complete submission. Attempt them only after the core task is working.

1. Direction choices: implement `solve_with_flips(problem)` for fixtures where area direction is allowed to vary.
2. Home point: implement `solve_closed_loop(problem)` for fixtures that include a `home` point, such as `data/mission_14_home.json`.
3. Larger missions: implement `solve_large(problem)` for fixtures with many areas. Choose a practical approach and explain its behavior.

## Setup

Use Python 3.10 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest
```

Run the CLI on a fixture:

```bash
python -m flight_sequence.cli data/mission_14.json
```

## Deliverables

Submit:

- your implementation
- any tests you add
- a short `NOTES.md` explaining your formulation, approach, assumptions, complexity, and any extensions attempted

## Evaluation

We will look for:

- route validity and consistency with the package cost model
- judgment about behavior beyond toy public fixtures
- simple, readable Python
- clear explanation of tradeoffs
- sensible handling of edge cases such as one area, repeated coordinates, and non-input order solutions
