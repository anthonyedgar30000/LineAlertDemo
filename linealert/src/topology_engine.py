"""Reason about machine topology and where drift first appears.

Topology reasoning is deterministic. The YAML file defines dependencies, the
engine builds a directed graph, and drift evidence is mapped onto dependency
edges. No statistical inference, AI, or learned model is involved.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from drift_engine import DriftFinding


@dataclass(frozen=True)
class DependencyEdge:
    """A directed machine dependency from one event/subsystem to another."""

    upstream: str
    downstream: str

    @property
    def observation_key(self) -> str:
        return f"lag:{self.upstream}->{self.downstream}"

    @property
    def label(self) -> str:
        return f"{self.upstream} -> {self.downstream}"


@dataclass(frozen=True)
class TopologyFinding:
    """Structured topology interpretation suitable for reports."""

    likely_fault_region: str
    reason: str
    first_drift_edge: str
    first_drift_observation_key: str
    status: str
    upstream_dependencies: list[str]
    downstream_dependencies: list[str]
    evidence_summary: str


class TopologyGraph:
    """Directed graph of machine dependencies."""

    def __init__(self, edges: list[DependencyEdge]) -> None:
        if not edges:
            raise ValueError("Topology requires at least one dependency edge")

        self._edges = edges
        self._adjacency: dict[str, list[str]] = {}
        self._reverse_adjacency: dict[str, list[str]] = {}

        for edge in edges:
            self._adjacency.setdefault(edge.upstream, []).append(edge.downstream)
            self._adjacency.setdefault(edge.downstream, [])
            self._reverse_adjacency.setdefault(edge.downstream, []).append(edge.upstream)
            self._reverse_adjacency.setdefault(edge.upstream, [])

        self._validate_acyclic()
        self._node_order = self._topological_nodes()
        self._node_rank = {
            node: rank for rank, node in enumerate(self._node_order)
        }

    @property
    def edges(self) -> list[DependencyEdge]:
        """Return dependencies in YAML order."""

        return list(self._edges)

    @property
    def nodes(self) -> list[str]:
        """Return all known topology nodes in deterministic order."""

        return list(self._node_order)

    @property
    def edges_in_dependency_order(self) -> list[DependencyEdge]:
        """Return edges sorted from upstream dependencies to downstream dependents."""

        return sorted(
            self._edges,
            key=lambda edge: (
                self._node_rank[edge.upstream],
                self._node_rank[edge.downstream],
                edge.label,
            ),
        )

    def upstream_dependencies(self, node: str) -> list[str]:
        """Return all transitive upstream dependencies for a node."""

        return self._walk_dependencies(
            start=node,
            adjacency=self._reverse_adjacency,
        )

    def downstream_dependencies(self, node: str) -> list[str]:
        """Return all transitive downstream dependencies for a node."""

        return self._walk_dependencies(
            start=node,
            adjacency=self._adjacency,
        )

    def _walk_dependencies(self, start: str, adjacency: dict[str, list[str]]) -> list[str]:
        if start not in adjacency:
            raise ValueError(f"Unknown topology node: {start}")

        visited: set[str] = set()
        queue = deque(sorted(adjacency[start]))

        while queue:
            node = queue.popleft()
            if node in visited:
                continue
            visited.add(node)
            queue.extend(sorted(adjacency[node]))

        return sorted(visited, key=lambda node: self._node_rank[node])

    def _validate_acyclic(self) -> None:
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node: str) -> None:
            if node in visited:
                return
            if node in visiting:
                raise ValueError("Topology dependencies must not contain cycles")

            visiting.add(node)
            for downstream in self._adjacency[node]:
                visit(downstream)
            visiting.remove(node)
            visited.add(node)

        for node in sorted(self._adjacency):
            visit(node)

    def _topological_nodes(self) -> list[str]:
        indegree = {node: 0 for node in self._adjacency}
        for upstream in self._adjacency:
            for downstream in self._adjacency[upstream]:
                indegree[downstream] += 1

        ready = deque(sorted(node for node, degree in indegree.items() if degree == 0))
        ordered: list[str] = []

        while ready:
            node = ready.popleft()
            ordered.append(node)
            for downstream in sorted(self._adjacency[node]):
                indegree[downstream] -= 1
                if indegree[downstream] == 0:
                    ready.append(downstream)

        if len(ordered) != len(indegree):
            raise ValueError("Topology dependencies must not contain cycles")

        return ordered


def load_topology(topology_path: str | Path) -> TopologyGraph:
    """Load dependency relationships from YAML and build a directed graph."""

    path = Path(topology_path)
    if not path.exists():
        raise FileNotFoundError(f"Topology YAML not found: {path}")

    with path.open("r", encoding="utf-8") as topology_file:
        raw_topology = yaml.safe_load(topology_file) or {}

    dependencies = raw_topology.get("dependencies")
    if not isinstance(dependencies, list):
        raise ValueError("Topology YAML must contain a 'dependencies' list")

    edges = [
        _parse_dependency(raw_dependency, index)
        for index, raw_dependency in enumerate(dependencies, start=1)
    ]
    return TopologyGraph(edges=edges)


def identify_first_drift_location(
    graph: TopologyGraph,
    drift_findings: list[DriftFinding],
) -> list[TopologyFinding]:
    """Identify the first dependency edge where threshold-violating drift appears.

    Edges are evaluated in topological dependency order. For a linear machine
    sequence, this returns the first delayed/early edge and assigns the likely
    fault region to the upstream subsystem for that edge.
    """

    findings_by_key = {
        finding.observation_key: finding for finding in drift_findings
    }

    for edge in graph.edges_in_dependency_order:
        finding = findings_by_key.get(edge.observation_key)
        if finding is None or not finding.threshold_violation:
            continue

        status = _status_from_finding(finding)
        return [
            TopologyFinding(
                likely_fault_region=f"{edge.upstream} subsystem",
                reason=_reason_for_first_drift(edge=edge, status=status),
                first_drift_edge=edge.label,
                first_drift_observation_key=edge.observation_key,
                status=status,
                upstream_dependencies=graph.upstream_dependencies(edge.upstream),
                downstream_dependencies=graph.downstream_dependencies(edge.upstream),
                evidence_summary=(
                    f"{edge.observation_key}: actual {finding.actual_seconds:.2f}s, "
                    f"baseline {finding.expected_seconds:.2f}s, "
                    f"drift {finding.drift_seconds:+.2f}s"
                ),
            )
        ]

    return []


def _parse_dependency(raw_dependency: Any, index: int) -> DependencyEdge:
    if not isinstance(raw_dependency, dict):
        raise ValueError(f"Topology dependency {index} must be a mapping")

    upstream = str(raw_dependency.get("from", "")).strip()
    downstream = str(raw_dependency.get("to", "")).strip()

    if not upstream or not downstream:
        raise ValueError(f"Topology dependency {index} requires from and to values")
    if upstream == downstream:
        raise ValueError(f"Topology dependency {index} cannot point to itself")

    return DependencyEdge(upstream=upstream, downstream=downstream)


def _status_from_finding(finding: DriftFinding) -> str:
    if finding.direction == "high":
        return "Delayed"
    if finding.direction == "low":
        return "Early"
    return "Drifted"


def _reason_for_first_drift(edge: DependencyEdge, status: str) -> str:
    if status == "Delayed":
        return f"Delay first appears after {edge.upstream}."
    if status == "Early":
        return f"Timing first shifts early after {edge.upstream}."
    return f"Drift first appears after {edge.upstream}."
