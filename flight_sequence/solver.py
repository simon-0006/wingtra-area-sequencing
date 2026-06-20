from __future__ import annotations

try:
    import mip
except ImportError as exc:
    raise ImportError(
        "solve_large_milp requires python-mip; install it with `pip install mip`"
    ) from exc

from .models import Problem, Route, Visit, route_cost, distance, endpoints


def solve_basic(problem: Problem) -> Route:
    """Return an optimal open route with fixed area directions."""
    return _solve_exact(problem, allow_flips=False, closed_loop=False)


def solve_with_flips(problem: Problem) -> Route:
    """Optional extension: allow area direction choices."""
    if not problem.allow_flips:
        raise ValueError("problem does not permit direction flips")
    return _solve_exact(problem, allow_flips=True, closed_loop=False)


def solve_closed_loop(problem: Problem) -> Route:
    """Optional extension: closed loop from and back to problem.home."""
    if problem.home is None:
        raise ValueError("closed_loop route requires problem.home")
    return _solve_exact(problem, allow_flips=False, closed_loop=True)


def solve_large(problem: Problem) -> Route:
    """Open route for larger missions; delegates to the exact MILP solver."""
    return solve_large_milp(problem)


def _solve_exact(
    problem: Problem,
    *,
    allow_flips: bool,
    closed_loop: bool,
) -> Route:
    """DP using state (S, j, d): minimum transition cost of a path visiting exactly the
    area subset S, ending at area j in direction d.

    Using a combined index: idx = city * nd + direction_index, where nd = len(dirs).
    """
    areas = problem.areas
    n = len(areas)

    if n == 0:
        return Route(visits=(), cost=0.0)

    dirs = [False, True] if allow_flips else [False]
    nd = len(dirs)
    home = problem.home if closed_loop else None

    # ep[j][dj] = (entry, exit) for area j in direction index dj
    ep = [[endpoints(area, d) for d in dirs] for area in areas]

    sz = n * nd
    dp   = [[None] * sz for _ in range(1 << n)]
    pred = [[None] * sz for _ in range(1 << n)]

    # Base Case: single-area paths
    for cit in range(n):
        for dj in range(nd):
            entry_j, _ = ep[cit][dj]
            dp[1 << cit][cit * nd + dj] = distance(home, entry_j) if home is not None else 0.0

    # Step Case: extend every subset by one area not yet in it
    for path in sorted(range(1, 1 << n), key=lambda x: x.bit_count()):
        for city in range(n):
            if path & (1 << city) != 0:
                continue
            path_with_city = path | (1 << city)
            for dj in range(nd):
                entry_j, _ = ep[city][dj]
                best, best_pred = min(
                    (dp[path][prev * nd + di] + distance(ep[prev][di][1], entry_j), prev * nd + di)
                    for prev in range(n)
                    for di in range(nd)
                    if path & (1 << prev) != 0
                )
                dp[path_with_city][city * nd + dj] = best
                pred[path_with_city][city * nd + dj] = best_pred

    # Backtrack to get the target path
    full = (1 << n) - 1
    _, best_idx = min(
        (dp[full][idx] + (distance(ep[idx // nd][idx % nd][1], home) if home is not None else 0.0), idx)
        for idx in range(sz)
    )

    city_list_reverted = []
    S = full
    idx = best_idx
    while S != 0:
        city, dj = divmod(idx, nd)
        city_list_reverted.append((city, dirs[dj]))
        idx = pred[S][idx]
        S ^= (1 << city)

    city_list_reverted.reverse()
    visits = tuple(Visit(areas[city].id, flipped=d) for city, d in city_list_reverted)
    return Route(visits=visits, cost=route_cost(problem, visits, closed_loop=closed_loop))


def solve_large_milp(problem: Problem) -> Route:
    """Exact open route via MILP"""
    areas = problem.areas
    n = len(areas)

    if n == 0:
        return Route(visits=(), cost=0.0)

    # node n = zero-cost dummy closing path into a cycle
    nodes = n + 1

    # trans[i][j] = arc cost i->j; 0 if dummy involved
    trans = [
        [
            distance(areas[i].exit, areas[j].entry) if i < n and j < n else 0.0
            for j in range(nodes)
        ]
        for i in range(nodes)
    ]

    m = mip.Model(sense=mip.MINIMIZE, solver_name=mip.CBC)

    x = {
        i: {j: m.add_var(var_type=mip.BINARY) for j in range(nodes) if j != i}
        for i in range(nodes)
    }

    # degree: one out, one in per node
    for node in range(nodes):
        m += mip.xsum(x[node][j] for j in range(nodes) if j != node) == 1
        m += mip.xsum(x[i][node] for i in range(nodes) if i != node) == 1

    m.objective = mip.xsum(
        trans[i][j] * x[i][j] for i in range(nodes) for j in range(nodes) if j != i
    )

    m.lazy_constrs_generator = LazyConstrGenerator(x, nodes)

    status = m.optimize()
    assert status == mip.OptimizationStatus.OPTIMAL

    # successor map -> walk the cycle
    succ = {}
    for i in range(nodes):
        for j in range(nodes):
            if j != i and x[i][j].x >= 0.5:
                succ[i] = j

    order = []
    cur = succ[n]  # dummy's successor = first real node
    while cur != n:
        order.append(cur)
        cur = succ[cur]

    visits = tuple(Visit(areas[city].id, flipped=False) for city in order)
    return Route(visits=visits, cost=route_cost(problem, visits, closed_loop=False))


class LazyConstrGenerator(mip.ConstrsGenerator):
    """Subtour elimination: cut any directed cycle short of all nodes."""

    def __init__(self, x, n):
        self.x = x
        self.n = n

    def generate_constrs(self, model, depth=0, npass=0):
        x = model.translate(self.x)  # needed to read variable values

        # CBC may expose all-None vars at intermediate nodes
        if all(
            x[i][j] is None
            for i in range(self.n)
            for j in range(self.n)
            if j != i
        ):
            return

        # BFS each component via selected outgoing arcs
        visited = set()
        for start in range(self.n):
            if start in visited:
                continue
            sn = {start}
            nn = {start}
            is_change = True
            while is_change:
                nn_tmp = set()
                for node in nn:
                    for i in range(self.n):
                        if i != node and x[node][i].x >= 0.5 and i not in sn:
                            sn.add(i)
                            nn_tmp.add(i)

                if len(nn_tmp) == 0:
                    is_change = False
                nn = nn_tmp

            for node in sn:
                visited.add(node)

            if len(sn) == self.n:
                continue

            model.add_lazy_constr(
                mip.xsum(
                    x[i][j] for i in sn for j in range(self.n) if j not in sn
                )
                >= 1
            )
