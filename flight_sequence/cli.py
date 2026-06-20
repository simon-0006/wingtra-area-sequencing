from __future__ import annotations

import argparse
import json

from .models import Visit, load_problem
from .solver import solve_basic, solve_closed_loop, solve_large, solve_with_flips


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("fixture", help="Path to a JSON fixture")
    parser.add_argument("--flips", action="store_true", help="Use the optional flip solver")
    parser.add_argument("--closed-loop", action="store_true", help="Use the optional home solver")
    parser.add_argument("--large", action="store_true", help="Use the optional large-mission solver")
    args = parser.parse_args()

    problem = load_problem(args.fixture)
    if args.large:
        route = solve_large(problem)
    elif args.closed_loop:
        route = solve_closed_loop(problem)
    elif args.flips:
        route = solve_with_flips(problem)
    else:
        route = solve_basic(problem)

    print(
        json.dumps(
            {
                "problem": problem.name,
                "cost": route.cost,
                "visits": [_visit_json(visit) for visit in route.visits],
            },
            indent=2,
        )
    )


def _visit_json(visit: Visit) -> dict[str, object]:
    return {"area_id": visit.area_id, "flipped": visit.flipped}


if __name__ == "__main__":
    main()
