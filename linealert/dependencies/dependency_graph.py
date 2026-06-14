"""Dependency graph utilities for configured dependency chains."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from linealert.dependencies.dependency_chain import DependencyChain


@dataclass(frozen=True)
class DependencyGraph:
    """Directed graph derived from dependency chains."""

    chains: list[DependencyChain]

    @property
    def nodes(self) -> list[str]:
        return sorted({event for chain in self.chains for event in chain.events})

    @property
    def direct_edges(self) -> list[tuple[str, str]]:
        edges: set[tuple[str, str]] = set()
        for chain in self.chains:
            edges.update(chain.direct_edges)
        return sorted(edges)

    def adjacency(self) -> dict[str, list[str]]:
        adjacency = {node: [] for node in self.nodes}
        for source, target in self.direct_edges:
            adjacency.setdefault(source, []).append(target)
            adjacency.setdefault(target, [])
        return {source: sorted(targets) for source, targets in adjacency.items()}

    def direct_dependencies(self, event_name: str) -> list[str]:
        return list(self.adjacency().get(event_name, []))

    def transitive_dependencies(self, event_name: str) -> list[str]:
        adjacency = self.adjacency()
        visited: set[str] = set()
        ordered: list[str] = []
        queue = deque(adjacency.get(event_name, []))

        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            ordered.append(current)
            queue.extend(adjacency.get(current, []))

        return ordered

    def as_dict(self) -> dict[str, object]:
        return {
            "chains": [chain.as_dict() for chain in self.chains],
            "nodes": self.nodes,
            "direct_edges": [
                {"source": source, "target": target}
                for source, target in self.direct_edges
            ],
        }


def build_dependency_graph(chains: list[DependencyChain]) -> DependencyGraph:
    if not chains:
        raise ValueError("At least one dependency chain is required")
    return DependencyGraph(chains=chains)

