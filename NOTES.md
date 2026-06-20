# Notes — Area Sequencing Work Sample

## How I understood and framed the problem

The problem is a classical NP-hard problem. It is called Hamilton-Path problem and is used as a basis for a lot of examples that I saw also in my classes at ETH.

Basically we have a graph with a set of nodes, weighted edges and we want to pass through all of them with minimal cost and visiting each node only once.

## Which solution ideas I considered

### 1. The trivial solution $O(n!)$

The trivial solution is to iterate (or recurse) through all possible $O(n!)$ paths and calculate their cost. Then take the path with the minimum cost.

### 2. The DP solution $O(n^2\cdot 2^n)$

The DP solution that is based on Held-Karp's solution is considering each optimal solution for the different path lengths starting from length 1 up to n - for all the different subsets of nodes of that size.

So it breaks down the problem into a simple recursive step:

DP[S-i][j] := minimal length of path including the nodes in $S \setminus i$ ending in the city *j*.

$$
DP[S][i] = \min_j DP[S\setminus i][j] + \text{cost}(j \to i)
$$

### 3. The binary ILP solution (NP-hard in theory; practical in practice up to $n \approx 100$)

This solution maps the Hamilton path problem onto a linear program. 
The beneficial part about that solution is, that it is really easily written - as there exist great libraries like mip that make it very easy to write down linear programs - and in practice (if using e.g. the concept of `LazyConstrGenerator`) it is actually a lot faster.

The following is the standard binary ILP (DFJ) formulation for the symmetric Hamilton cycle:

$$
\begin{array}{rrcll}
\min & \displaystyle\sum_{e\in E} d_e x_e\\
     & x(\delta(v)) & =   & 2 & \forall v\in V \\
     & x(\delta(S)) & \ge & 2 & \forall S\subsetneq V, S\neq\emptyset\\
     & x            & \in & \{0, 1\}
\end{array}
$$

This formulation is for the symmetric undirected Hamilton cycle. For the asymmetric directed open path one has to consider that edges are directed $x[i][j] \not = x[j][i]$, degree constraints split into separate in- and out-degree constraints, and a dummy node with zero-cost edges closes the open path into a cycle for the solver.

The part that is concerning is the amount of constraints (because $\forall S \subsetneq V$) but exactly that can be approached with `LazyConstrGenerator`. As we can only always add the necessary sets to LP (after evaluating if there is a violation) rather than adding all the possible sets from the beginning on. 
This turns out to work quite well in practice because there are a lot of sets that are never considered to be optimal and therefore we never add them to the LP.

 > Branch-and-cut solvers should be able to handle instances up to $n \approx 100$ efficiently in practice.

### 4. The *heuristic* solution $O(k \cdot n^3)$

I created an algorithm that sequentially executes some smaller (partially greedy) algorithms that iteratively try to improve the solution.

a. First just get n different paths, each of which starts exactly on one distinct starting node. Then iteratively choose the next best neighbor\
 > greedy construction algorithm $O(n^2)$ per start, $O(n^3)$ total for $n$ starts

b. Scan for all single-location-moves that can be applied to reduce the cost for every given path.\
 > scan $O(n^2)$ combinations for each calculate cost $O(n)$ yields $O(n^3)$ per swap. Number of swaps unknown by $k$. So in total $O(k \cdot n^3)$ 

c. Scan for all pair-of-location-moves that can be applied to reduce the cost for every given path.\
 > same as in b

d. Scan for all triples-of-location-moves that can be applied to reduce the cost for every given path. 
 > same as in b


## Why I chose the approach I implemented

I implemented all extensions - but with a short note that the solve_large_milp does not handle direction and closed-loop routes. 

I chose for all but the large problem the DP solution which is a straightforward approach to address this issue especially for $n \le 14$. 
The runtime is $O(n^2\cdot 2^n)$ which is for $n = 14 : O(3.2 \cdot 10^6)$ operations which is feasible in around a second.

For the large approach I chose the binary ILP solution. I recently learned about this approach in a course called mathematical optimization lab and found it quite impressive. It is NP-hard in the worst case, but branch-and-cut solvers perform very well in practice for instances at this scale.

Short note: Already for $n=26$ the DP solution would take: $O(43\cdot 10^9)$ operations, which is infeasible on standard hardware within reasonable time.

## What assumptions or tradeoffs I made

A tradeoff that I considered was to write one solve function that takes into account the different angles of the functions all at once. This general solving function is genuinely a bit less readable than each of the individual functions would have been, but overall I think it improves the `solver.py` file structure because it consolidates the DP logic from three separate function bodies into one shared kernel.

Another tradeoff I made is prioritising solution optimality over runtime.
I would lean toward the heuristic approach in other scenarios, because it might be interesting for huge problems (with hundreds of targets) to actually shift the objective from having **the** optimal solution to having a *pretty* good solution in **acceptable** runtime.

## What I would improve or extend if I had more time

If I had more time I would have liked to benchmark all of my approaches to see

1. The deterministic algorithms: at what cap $n$ do they start to struggle / take a long time
2. How good would the approximation by the heuristic algorithm be

Also as the heuristic algorithm would just be going through a fixed set of improvement steps there would be a lot of potential to think through a more sophisticated approach or additional heuristics that could improve the approximations.

## AI-assistance disclosure (generated by the assistants used)

### OpenAI Codex 5.5

**Model:** OpenAI Codex 5.5, reasoning effort set to extra high.

**Setup:** Repository-aware agent with local shell access, using the project's virtual environment and `pytest` for validation.

**Experience:** I used it as a pair-programming and review tool to discuss algorithm choices, refine code and tests, and run repeatable checks. It was particularly useful for systematic edge-case coverage and independent brute-force oracle tests. Its output still required review: testing exposed an empty-input bug, and a later consistency check found that all three implemented optional solvers still had stale skip markers in their tests. I verified results against `route_cost` and executable tests. The reasoning sections were written by me; this disclosure was drafted by Codex.

### Anthropic Claude Sonnet 4.6

**Model:** Anthropic Claude Sonnet 4.6 via Claude Code (VS Code extension), reasoning effort set to high.

**Setup:** Repository-aware agent with shell access, using the project's virtual environment and `pytest` for validation.

**Experience:** I used it as a pair-programming and sounding-board tool — discussing algorithm options and trade-offs, co-designing code blocks from agreed-upon approaches, and running tests. All architectural and algorithmic decisions were mine; the model helped execute and validate them. The reasoning sections of this document were written by me. This disclosure is the only part drafted by the model.
